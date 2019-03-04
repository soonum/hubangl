# -*- coding: utf-8 -*-

# This file is part of HUBAngl.
# HUBAngl Uses Broadcaster Angle
#
# HUBAngl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# HUBAngl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with HUBAngl.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (c) 2016-2019 David Testé

import abc
import logging
import os
import socket
import time

from gi.repository import Gtk
import ipaddress

from core import process
from core import watch
from gui import status_bar
from gui import utils


AUDIO_VIDEO_STREAM = process.AUDIO_VIDEO_STREAM
VIDEO_ONLY_STREAM = process.VIDEO_ONLY_STREAM
AUDIO_ONLY_STREAM = process.AUDIO_ONLY_STREAM

_PROPERTIES_SET = "[gui] Properties set in {section} menu"
_PRESS_STOP_MESSAGE = "Press STOP for changes to be taken into account"

logger = logging.getLogger("gui.main_window")


def get_pending_confirm(menus):
    """
    Get a list of all the menus having changes waiting to be confirmed.

    :param menus: :class:`dict` formatted as ``{"menu_name": menu_object}``

    :return: :class:`list` of menu names as :class:`str`
    """
    pendings = []
    for key, menu in menus.items():
        if hasattr(menu, "feeds"):
            for section in menu.feeds:
                if section.confirm_button.get_sensitive():
                    pendings.append(" ".join((key, str(section.index))))
        elif menu.confirm_button.get_sensitive():
            pendings.append(key)

    return pendings


class AbstractMenu:
    """
    """
    def __init__(self, pipeline, menu_revealer, placeholder_pipeline=None):
        self.pipeline = pipeline
        self.placeholder_pipeline = placeholder_pipeline
        self.menu_revealer = menu_revealer

    def _build_header(self, title):
        """
        Build a header bar containing the ``title`` of the menu as well as a
        close button which collapses the revealer.

        :param title: title of the menu

        :return: :class:`Gtk.HeaderBar`
        """
        close_button = Gtk.Button()
        image = Gtk.Image.new_from_icon_name("window-close-symbolic",
                                             Gtk.IconSize.MENU)
        close_button.set_image(image)
        close_button.set_relief(Gtk.ReliefStyle.NONE)
        close_button.connect("clicked", self.on_close_clicked)

        header_bar = Gtk.HeaderBar()
        header_bar.set_title(title)
        header_bar.pack_end(close_button)
        return header_bar

    def _build_subsection(self, *widgets):
        """
        Build a menu subsection visually indented. It is made of a vertical
        :class:`Gtk.Box` coontaining all the widgets used in the subsection.
        This box is packed in a horizontal :class:`Gtk.Box` along with a
        separator.

        :param widgets: :class:`Gtk.Widget`

        :return: horizontal :class:`Gtk.Box` and vertical :class:`Gtk.Box`
        """
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        utils.pack_widgets(vbox, *widgets)

        separator = Gtk.VSeparator()
        separator.set_margin_start(12)
        separator.set_margin_end(6)

        hbox = Gtk.Box()
        hbox.set_margin_top(6)
        utils.pack_widgets(hbox, separator, vbox)

        return hbox, vbox

    def _build_revealer(self,
                        transition=Gtk.RevealerTransitionType.SLIDE_DOWN):
        """
        """
        revealer = Gtk.Revealer()
        revealer.set_transition_type(transition)
        revealer.set_transition_duration(400)
        return revealer

    def _manage_revealer(self, revealer_widget, container_widget):
        """
        :return: ``True`` if revealer is shown, ``False`` if it is hidden.
        """
        child = revealer_widget.get_child()

        if revealer_widget.get_child_revealed():
            if child == container_widget:
                revealer_widget.set_reveal_child(False)
                # Hack to make the top-level window shrink back to
                # its original size.
                utils.get_video_monitor().set_size_request(1, -1)
                return False

        if child:
            revealer_widget.remove(child)

        revealer_widget.add(container_widget)
        container_widget.show_all()
        revealer_widget.set_reveal_child(True)
        return True

    def _make_widget_available(self, *widgets):
        """
        Make widgets available to user.
        """
        for widget in widgets:
            widget.set_sensitive(True)

    def _make_widget_unavailable(self, *widgets):
        """
        Make widgets unavailable but visible to user.
        """
        for widget in widgets:
            widget.set_sensitive(False)

    def _make_scrolled_window(self, container):
        """
        Make ``container`` a vertically scrollable one.

        :param container: :class:`Gtk.Box` or :class:`Gtk.Grid`
        """
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.add_with_viewport(container)
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER,
                                        Gtk.PolicyType.AUTOMATIC)

    def _build_confirm_changes_button(self, label=None, on_signal="clicked",
                                      callback=None):
        """
        Build a confirmation button used in every side bar menus.
        This button triggers interaction with the core in case of settings
        changes. Otherwise it stays insensitive.
        """
        if not label:
            label = "Confirm"
        button = Gtk.Button(label)
        button.set_sensitive(False)
        button.set_margin_top(12)
        if callback:
            button.connect(on_signal, callback)

        return button

    def _build_add_button(self, label=None, on_signal="clicked",
                          callback=None):
        """
        Build an add button usable in side bar menu.
        This button triggers allow the creation of a new element in the menu.
        """
        if not label:
            label = "Add"
        button = Gtk.Button(label, stock=Gtk.STOCK_ADD)
        button.set_margin_top(12)
        button.set_size_request(250, 20)
        if callback:
            button.connect(on_signal, callback)

        return button

    def _build_address_entries(self):
        """
        """
        self.host_entry = Gtk.Entry()
        self.host_entry.set_placeholder_text("Hostname or IP address")
        self.host_entry.connect("changed", self.on_host_change)

        self.port_entry = Gtk.Entry()
        self.port_entry.set_max_length(5)
        self.port_entry.set_width_chars(5)
        if hasattr(self.port_entry, "set_max_width_chars"):
            self.port_entry.set_max_width_chars(5)
        self.port_entry.set_placeholder_text("Port")
        self.port_entry.set_input_purpose(Gtk.InputPurpose.DIGITS)
        self.port_entry.connect("changed", self.on_port_change)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        utils.pack_widgets(hbox,
                           self.host_entry,
                           Gtk.Label(":"),
                           self.port_entry)

        return hbox

    @abc.abstractmethod
    def get_properties(self):
        """
        Get properties set in the menu.

        :return: :class:`dict` as property_key: value
        """

    @abc.abstractmethod
    def set_properties(self):
        """
        Set properties in the menu.

        :param kargs: :class:`dict` containing properties related to this menu
        """

    def get_ip_address(self):
        """
        Resolve the host and get the port to connect to.

        :return: address, port
        """
        try:
            port = int(self.port_entry.get_text())
        except ValueError:
            utils.build_error_dialog("Bad input",
                                     "Port must contains only digits")
            raise

        host_ip_value = self.host_entry.get_text()
        try:
            address = str(ipaddress.ip_address(host_ip_value))
        except ValueError:
            try:
                info = socket.getaddrinfo(host_ip_value, port,
                                          proto=socket.IPPROTO_TCP)
                address = info[0][4][0]
            except socket.gaierror as e:
                if e.errno == -3:
                    msg = "Network issue"
                    sub_msg = ("Hostname {} cannot be resolved.\n"
                               "Verify your connection.".format(host_ip_value))
                else:
                    msg = "Bad input"
                    sub_msg = ("Hostname {} is not known.\n"
                               "Verify address entry.".format(host_ip_value))
                utils.build_error_dialog(msg, sub_msg)
                raise

        return address, port

    def _build_format_section(self, radio_button_label, format_labels,
                              callback_radio=None, callback_combo=None,
                              radio_group=None):
        """
        """
        radio_button = Gtk.RadioButton(
            radio_button_label, group=radio_group)
        if callback_radio:
            radio_button.connect("toggled", callback_radio)

        text_label = Gtk.Label("Format : ")
        combo_box = Gtk.ComboBoxText()
        for label in format_labels:
            combo_box.append_text(label)
            combo_box.set_active(0)
        # This version accept only one format for each stream type.
        # There is not point to allow user to use this combo box.
        # That way the format is displayed as information.
        combo_box.set_sensitive(False)
        if callback_combo:
            combo_box.connect("changed", callback_combo)

        hbox = Gtk.Box(Gtk.Orientation.HORIZONTAL)
        hbox.set_margin_start(24)
        utils.pack_widgets(hbox, text_label, combo_box)

        return (radio_button, hbox, combo_box)

    def _build_format_group(self):
        """
        """
        self.audio_formats = (".ogg",)
        self.video_formats = (".mkv",)
        self.audiovideo_formats = (".webm",)

        (self.audiovideo_radiobutton,
         self._audiovideo_format_hbox,
         self._audiovideo_format_combobox) = self._build_format_section(
             "Audio/Video", self.audiovideo_formats,
             callback_radio=self.on_format_radiobutton_toggle)
        self.audiovideo_radiobutton.set_active(True)

        self.current_stream_type = AUDIO_VIDEO_STREAM

        (self.video_radiobutton,
         self._video_format_hbox,
         self._video_format_combobox) = self._build_format_section(
             "Video Only", self.video_formats,
             callback_radio=self.on_format_radiobutton_toggle,
             radio_group=self.audiovideo_radiobutton)

        (self.audio_radiobutton,
         self._audio_format_hbox,
         self._audio_format_combobox) = self._build_format_section(
             "Audio Only", self.audio_formats,
             callback_radio=self.on_format_radiobutton_toggle,
             radio_group=self.audiovideo_radiobutton)

        radiobutton_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        utils.pack_widgets(radiobutton_hbox,
                           self.audiovideo_radiobutton,
                           self.video_radiobutton,
                           self.audio_radiobutton)

        return radiobutton_hbox

    def _build_summary_box(self, index, filename):
        """
        Build a container that sums up information about an output sink.

        :param index: section index
        :param filename: filename of stored stream as :class:`str`

        :return: :class:`Gtk.Box`
        """
        index_label = Gtk.Label(str(index) + ". ")
        self.full_filename_label = Gtk.Label(filename)
        settings_button = Gtk.Button(stock=Gtk.STOCK_PROPERTIES)
        settings_button.connect("clicked", self.on_settings_clicked)
        summary_hbox = utils.build_multi_widgets_hbox(
            [index_label, self.full_filename_label], [settings_button, ])
        summary_hbox.set_margin_top(6)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(6)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        utils.pack_widgets(vbox,
                           summary_hbox,
                           self._revealer,
                           separator)
        return vbox

    def _get_format_hbox(self):
        """
        Get format horizontal box currently displayed.

        :return: :class:`Gtk.Box`
        """
        for format_hbox in (self._audiovideo_format_hbox,
                            self._video_format_hbox,
                            self._audio_format_hbox):
            if format_hbox.get_parent():
                return format_hbox

    def _get_format_extension(self):
        """
        Get format extension from the combo box currently displayed.

        :return: a dotted extension as :class:`str`
        """
        hbox = self._get_format_hbox()
        for combobox in (self._audiovideo_format_combobox,
                         self._video_format_combobox,
                         self._audio_format_combobox):
            if combobox.get_parent() == hbox:
                return combobox.get_active_text()

    def _set_format_extension(self, format_selected):
        """
        Set format extension for the combo box currently displayed.
        """
        combobox_formats = {
            self._audiovideo_format_combobox: self.audiovideo_formats,
            self._video_format_combobox: self.video_formats,
            self._audio_format_combobox: self.audio_formats
        }
        hbox = self._get_format_hbox()
        for combobox, formats in combobox_formats.items():
            if combobox.get_parent() == hbox:
                self.set_active_text(combobox, formats, format_selected)

    def _change_output_format(self, widget):
        """
        """
        current_hbox = self._get_format_hbox()
        self.vbox.remove(current_hbox)

        button_label = widget.get_label()
        if button_label == self.audiovideo_radiobutton.get_label():
            child = self._audiovideo_format_hbox
            self.current_stream_type = AUDIO_VIDEO_STREAM
        elif button_label == self.video_radiobutton.get_label():
            child = self._video_format_hbox
            self.current_stream_type = VIDEO_ONLY_STREAM
        elif button_label == self.audio_radiobutton.get_label():
            child = self._audio_format_hbox
            self.current_stream_type = AUDIO_ONLY_STREAM

        self.vbox.pack_start(child, False, False, 0)
        self.vbox.reorder_child(child, -2)
        self.vbox.show_all()

    def _get_feed_type(self):
        for button in (self.audio_radiobutton, self.audiovideo_radiobutton,
                       self.video_radiobutton):
            if button.get_active():
                return button.get_label()

    def set_active_text(self, comboboxtext_widget, text_list, text):
        """
        Set active text of ``comboboxtext_widget`` to ``text`` if ``text`` is
        in ``text_list``.

        :param comboboxtext_widget: :class:`Gtk.ComboBoxText`
        :param text_list: list of string appened to ``comboboxtext_widget``
        :param text: string to set active as :class:`str`
        """
        for index, text_element in enumerate(text_list):
            if text == text_element:
                comboboxtext_widget.set_active(index)
                return

        logger.error("[gui] Device '{}' has not been found"
                     " (available devices: {})".format(text, text_list))

    def has_sink_set(self):
        """
        Check if, at least, one  output sink has been set.

        :return: ``True`` if a sink has been set, ``False`` otherwise
        """
        if not self.feeds:
            return False

        for feed in self.feeds:
            if feed.sink:
                return True

    def on_close_clicked(self, widget):
        self._manage_revealer(self.menu_revealer, self.scrolled_window)

    def on_format_radiobutton_toggle(self, widget):
        raise NotImplementedError

    def on_comboxboxtext_change(self, widget):
        raise NotImplementedError

    def on_host_change(self, widget):
        raise NotImplementedError

    def on_port_change(self, widget):
        raise NotImplementedError


class VideoMenu(AbstractMenu):
    """
    """
    def __init__(self, pipeline, menu_revealer, placeholder_pipeline=None):
        super().__init__(pipeline, menu_revealer, placeholder_pipeline)
        self.video_usb_widgets = []
        self.video_ip_widgets = []
        self.sources_list = []
        self.video_vbox = self._build_video_vbox()

        self.current_video_source = None
        self.requested_video_source = None

    def _build_video_vbox(self):
        """
        """
        header = self._build_header("Video Source")

        self.usb_radiobutton = Gtk.RadioButton("USB")
        self.usb_radiobutton.set_active(True)
        self.usb_radiobutton.connect("toggled", self.on_commtype_toggle)
        self.usb_sources = Gtk.ComboBoxText()
        if not self.pipeline.video_sources:
            self.usb_sources.append_text("")
        else:
            for source in self.pipeline.video_sources:
                self.usb_sources.append_text(source.name)
                self.sources_list.append(source.name)
        self.usb_sources.connect("changed", self.on_usb_input_change)
        self.usb_sources.set_margin_start(24)
        self.video_usb_widgets.append(self.usb_sources)

        self.ip_radiobutton = Gtk.RadioButton(
            label="IP (soon)", group=self.usb_radiobutton)
        self.ip_radiobutton.connect("toggled", self.on_commtype_toggle)
        # TODO: Remove the next line once IP camera are handled in a pipeline.
        self.ip_radiobutton.set_sensitive(False)

        self.address_entries = self._build_address_entries()
        self.address_entries.set_margin_start(24)

        self.video_ip_widgets.append(self.address_entries)
        self._make_widget_unavailable(*self.video_ip_widgets)

        self.confirm_button = self._build_confirm_changes_button(
            callback=self.on_confirm_clicked)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_margin_top(6)
        vbox.set_margin_end(6)
        utils.pack_widgets(vbox,
                           header,
                           self.usb_radiobutton,
                           self.usb_sources,
                           self.ip_radiobutton,
                           self.address_entries,
                           self.confirm_button)
        self._make_scrolled_window(vbox)
        return vbox

    def get_properties(self):
        """
        Get properties set in the menu.

        :return: :class:`dict` as property_key: value
        """
        usb_radiobutton_value = self.usb_radiobutton.get_active()
        usb_source_selected = self.usb_sources.get_active_text()
        ip_radiobutton_value = self.ip_radiobutton.get_active()

        return {"usb_radiobutton": usb_radiobutton_value,
                "usb_source_selected": usb_source_selected,
                "ip_radiobutton": ip_radiobutton_value, }

    def set_properties(self, **kargs):
        """
        Set properties in the menu.

        :param kargs: :class:`dict` containing properties related to this menu
        """
        usb_radiobutton_value = kargs.get("usb_radiobutton")
        usb_source_selected = kargs.get("usb_source_selected")
        ip_radiobutton_value = kargs.get("ip_radiobutton")

        self.usb_radiobutton.set_active(usb_radiobutton_value)
        self.requested_video_source = None
        self.current_video_source = None
        self.set_active_text(
            self.usb_sources, self.sources_list, usb_source_selected)
        self.on_usb_input_change(self.usb_sources)

        self.ip_radiobutton.set_active(ip_radiobutton_value)

        # TODO: add an OR operator with ip_source_selected once ip based
        #       source is implemented
        if usb_source_selected:
            self.on_confirm_clicked(self.confirm_button)

        logger.debug(_PROPERTIES_SET.format(section="video"))

    def on_video_input_clicked(self, widget):
        return self._manage_revealer(self.menu_revealer, self.scrolled_window)

    def on_commtype_toggle(self, widget):
        is_active = widget.get_active()
        if widget.get_label() == "USB" and is_active:
            self._make_widget_available(*self.video_usb_widgets)
            self._make_widget_unavailable(*self.video_ip_widgets)
        elif widget.get_label() == "IP" and is_active:
            self._make_widget_available(*self.video_ip_widgets)
            self._make_widget_unavailable(*self.video_usb_widgets)

    def on_usb_input_change(self, widget):
        active_text = widget.get_active_text()
        if active_text:
            self.confirm_button.set_sensitive(True)
            self.requested_video_source = self.pipeline.get_source_by_name(
                active_text)

    def on_confirm_clicked(self, widget):
        if self.requested_video_source == self.current_video_source:
            return

        self.pipeline.set_input_source(self.requested_video_source)
        self.current_video_source = self.requested_video_source
        self.requested_video_source = None

        self.confirm_button.set_sensitive(False)

        if self.placeholder_pipeline.is_playing_state():
            self.placeholder_pipeline.set_stop_state()
            self.pipeline.set_preview_state("audio")
        elif self.pipeline.get_current_text() == "No video source":
            # An audio source is already set
            self.pipeline.set_text_overlay("", "left", "top")


class AudioMenu(AbstractMenu):
    """
    """
    def __init__(self, pipeline, menu_revealer, placeholder_pipeline=None):
        super().__init__(pipeline, menu_revealer, placeholder_pipeline)
        self.sources_list = []
        self.sinks_list = []
        self.audio_vbox = self._build_audio_vbox()

        self.current_audio_source = None
        self.requested_audio_source = None

    def _build_audio_vbox(self):
        """
        """
        header = self._build_header("Audio Source")

        self.mute_input_checkbutton = Gtk.CheckButton("Mute")
        self.mute_input_checkbutton.connect(
            "toggled", self.on_mute_input_toggle)
        # Set tooltip text
        self.on_mute_input_toggle(self.mute_input_checkbutton)

        input_hbox = Gtk.Box()
        input_hbox.pack_start(Gtk.Label("Input"), False, False, 0)
        input_hbox.pack_end(self.mute_input_checkbutton, False, False, 0)

        self.mic_sources = Gtk.ComboBoxText()
        for source in self.pipeline.audio_sources:
            self.mic_sources.append_text(source.name)
            self.sources_list.append(source.name)
        self.mic_sources.connect("changed", self.on_input_change)

        self.compressor_switch = Gtk.Switch()
        self.compressor_switch.connect(
            "notify::active", self.on_switch_activated)
        self.compressor_switch.set_active(False)
        compressor_hbox = utils.build_multi_widgets_hbox(
            [Gtk.Label("Compressor")], [self.compressor_switch])

        self.ratio = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 1, 0.01)
        self.ratio.set_value_pos(Gtk.PositionType.RIGHT)
        self.ratio.set_value(1)
        self.ratio.set_size_request(120, -1)
        self.ratio.connect("value_changed", self.on_ratio_value_changed)
        self.ratio.set_tooltip_text(
            "Ratio of compression that should be applied.\n"
            "0 = Limiter mode\n0.25 = Output a quarter of the input value\n"
            "0.5 = Output a half of the input value\n1 = No compression")
        ratio_hbox = utils.build_multi_widgets_hbox(
            [Gtk.Label("Ratio")], [self.ratio], padding=6)

        self.threshold = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.threshold.set_value_pos(Gtk.PositionType.RIGHT)
        self.threshold.set_value(100)
        self.threshold.set_size_request(120, -1)
        self.threshold.connect("value_changed",
                               self.on_threshold_value_changed)
        self.threshold.set_tooltip_text(
            "Threshold above which the compressor is activated.\n"
            "(As a percentage of the input level)")
        threshold_hbox = utils.build_multi_widgets_hbox(
            [Gtk.Label("Threshold")], [self.threshold], padding=6)

        self.soft_knee_checkbutton = Gtk.CheckButton("Soft Knee")
        self.soft_knee_checkbutton.connect(
            "toggled", self.on_soft_knee_toggle)
        self.soft_knee_checkbutton.set_tooltip_text(
            "If enabled the ratio would be applied smoothly")

        self.compressor_settings_hbox, _ = self._build_subsection(
            ratio_hbox, threshold_hbox, self.soft_knee_checkbutton)
        self._compressor_settings_revealer = self._build_revealer()

        sources_hbox, _ = self._build_subsection(
            self.mic_sources,
            compressor_hbox,
            self._compressor_settings_revealer)

        self.mute_monitor_checkbutton = Gtk.CheckButton("Mute")
        self.mute_monitor_checkbutton.connect(
            "toggled", self.on_mute_monitor_toggle)
        # Mute loudspeakers by default
        self.mute_monitor_checkbutton.set_active(True)
        # Check button activable from another place (gui.feed)
        self.mute_monitor_checkbutton.set_sensitive(False)

        monitor_hbox = Gtk.Box()
        monitor_hbox.pack_start(Gtk.Label("Monitor"), False, False, 0)
        monitor_hbox.pack_end(self.mute_monitor_checkbutton, False, False, 0)

        self.output_sinks = Gtk.ComboBoxText()
        index = 0
        for name, device in self.pipeline.speaker_sinks.items():
            self.output_sinks.append_text(name)
            self.sinks_list.append(name)
            if device == self.pipeline.speaker_sink.get_property("device"):
                self.output_sinks.set_active(index)
            index += 1
        self.output_sinks.connect("changed", self.on_output_change)

        sinks_hbox, _ = self._build_subsection(self.output_sinks)

        self.confirm_button = self._build_confirm_changes_button(
            callback=self.on_confirm_clicked)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_margin_top(6)
        vbox.set_margin_end(6)
        utils.pack_widgets(vbox,
                           header,
                           input_hbox,
                           sources_hbox,
                           monitor_hbox,
                           sinks_hbox,
                           self.confirm_button)
        self._make_scrolled_window(vbox)
        return vbox

    def get_properties(self):
        """
        Get properties set in the menu.

        :return: :class:`dict` as property_key: value
        """
        audio_source_selected = self.mic_sources.get_active_text()
        audio_sink_selected = self.output_sinks.get_active_text()
        source_muted = self.mute_input_checkbutton.get_active()
        monitor_muted = self.mute_monitor_checkbutton.get_active()
        compressor_enabled = self.compressor_switch.get_active()
        compressor_ratio = self.ratio.get_value()
        compressor_threshold = self.threshold.get_value()
        compressor_soft_knee = self.soft_knee_checkbutton.get_active()

        return {"audio_source_selected": audio_source_selected,
                "audio_sink_selected": audio_sink_selected,
                "source_muted": source_muted,
                "monitor_muted": monitor_muted,
                "compressor_enabled": compressor_enabled,
                "compressor_ratio": compressor_ratio,
                "compressor_threshold": compressor_threshold,
                "compressor_soft_knee": compressor_soft_knee}

    def set_properties(self, **kargs):
        """
        Set properties in the menu.

        :param kargs: :class:`dict` containing properties related to this menu
        """
        audio_source_selected = kargs.get("audio_source_selected")
        audio_sink_selected = kargs.get("audio_sink_selected")
        source_muted = kargs.get("source_muted", False)
        monitor_muted = kargs.get("monitor_muted", True)
        compressor_enabled = kargs.get("compressor_enabled", False)
        compressor_ratio = kargs.get("compressor_ratio", 1)
        compressor_threshold = kargs.get("compressor_threshold", 100)
        compressor_soft_knee = kargs.get("compressor_soft_knee", False)

        self.requested_audio_source = None
        self.current_audio_source = None
        self.set_active_text(
            self.mic_sources, self.sources_list, audio_source_selected)
        self.on_input_change(self.mic_sources)
        self.mute_input_checkbutton.set_active(source_muted)
        self.mute_monitor_checkbutton.set_active(monitor_muted)
        self.ratio.set_value(compressor_ratio)
        self.threshold.set_value(compressor_threshold)
        self.soft_knee_checkbutton.set_active(compressor_soft_knee)
        # Compressor checkbutton must done last so that the above settings can
        # be applied beforehand even if the compressor is disabled.
        self.compressor_switch.set_active(compressor_enabled)
        if not compressor_enabled:
            self.on_switch_activated(self.compressor_switch, None)
            # Reveal again to avoid inversion on user selection
            # (revealing on disabling and folding on enabling)
            self._manage_revealer(self._compressor_settings_revealer,
                                  self.compressor_settings_hbox)

        # TODO: Handle user choice for output audio sink, currently this
        # implementation overrides user's choice by setting automatically
        # default speaker output.
        index = 0
        for name, device in self.pipeline.speaker_sinks.items():
            if device == self.pipeline.speaker_sink.get_property("device"):
                self.output_sinks.set_active(index)
            index += 1

        if audio_source_selected:
            self.on_confirm_clicked(self.confirm_button)

        logger.debug(_PROPERTIES_SET.format(section="audio"))

    def on_audio_input_clicked(self, widget):
        return self._manage_revealer(self.menu_revealer, self.scrolled_window)

    def on_input_change(self, widget):
        self.confirm_button.set_sensitive(True)
        self.requested_audio_source = self.pipeline.get_source_by_name(
            widget.get_active_text())

    def on_output_change(self, widget):
        self.confirm_button.set_sensitive(True)
        # self.requested_audio_sink = self.pipeline.get_source_by_name(
        #    widget.get_active_text())  # DEV

    def on_mute_input_toggle(self, widget):
        """
        Mute audio input in the pipeline. This take effect immediatly.
        """
        self.pipeline.mute_audio_input(widget.get_active())
        action = "Unmute" if widget.get_active() else "Mute"
        widget.set_tooltip_text("{} audio input".format(action))

    def on_mute_monitor_toggle(self, widget):
        """
        Mute the loudspeakers/headphones output. This take effect immediatly.
        """
        self.pipeline.speaker_volume.set_property("mute", widget.get_active())

        action = "Unmute" if widget.get_active() else "Mute"
        widget.set_tooltip_text(
            "{} audio monitor output.\n"
            "State can be only changed from media control bar".format(
                action))
        logger.debug("Changed audio output state to {}D".format(
            action.upper()))

    def on_switch_activated(self, widget, gparam):
        if widget.get_active():
            self.on_ratio_value_changed(self.ratio)
            self.on_threshold_value_changed(self.threshold)
            state = "enabled"
        else:
            # Set compressor in by-pass mode
            self.pipeline.compressor.set_property("ratio", 1)
            self.pipeline.compressor.set_property("threshold", 1)
            state = "disabled"

        logger.info("[gui] audio compressor has been {}".format(state))

        time.sleep(.4)  # 400ms delay to avoid revealer issue with double-click
        return self._manage_revealer(self._compressor_settings_revealer,
                                     self.compressor_settings_hbox)

    def on_ratio_value_changed(self, widget):
        """
        Change ratio of the compressor in the pipeline.
        This take effect immediatly.
        """
        self.pipeline.compressor.set_property("ratio", widget.get_value())

    def on_threshold_value_changed(self, widget):
        """
        Change threshold of the compressor in the pipeline.
        This take effect immediatly.
        """
        self.pipeline.compressor.set_property("threshold",
                                              widget.get_value() / 100.0)

    def on_soft_knee_toggle(self, widget):
        """
        Set mode of the compressor in the pipeline.
        This take effect immediatly.
        """
        if widget.get_active():
            knee = "soft-knee"
        else:
            knee = "hard-knee"
        self.pipeline.compressor.set_property("characteristics", knee)

    def on_confirm_clicked(self, widget):
        if self.requested_audio_source != self.current_audio_source:
            self.pipeline.set_input_source(self.requested_audio_source)
            self.current_audio_source = self.requested_audio_source

        # if self.requested_audio_sink != self.current_audio_sink:  # DEV
        #    self.pipeline.set_speaker_sink(self.requested_audio_sink)  # DEV
        #    self.current_audio_sink = self.requested_audio_sink  # DEV

        self.confirm_button.set_sensitive(False)

        if self.placeholder_pipeline.is_playing_state():
            self.placeholder_pipeline.set_stop_state()
            self.pipeline.set_preview_state("video")


class StreamMenu(AbstractMenu):
    """
    """
    def __init__(self, pipeline, menu_revealer):
        super().__init__(pipeline, menu_revealer)
        self.settings_revealer = self._build_revealer()
        self.main_vbox = self._build_stream_vbox()

        self.feeds = []

    def _build_stream_vbox(self):
        header = self._build_header("Streaming Servers")

        self.stream_add_button = self._build_add_button(
            callback=self.on_add_clicked)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_margin_end(6)
        utils.pack_widgets(vbox,
                           header,
                           self.settings_revealer,
                           self.stream_add_button)
        self._make_scrolled_window(vbox)
        return vbox

    def on_stream_clicked(self, widget):
        return self._manage_revealer(self.menu_revealer, self.scrolled_window)

    def on_add_clicked(self, widget):
        stream_element = self.StreamSection(
            self.pipeline, self.settings_revealer,
            self.main_vbox, len(self.feeds) + 1)
        self.feeds.append(stream_element)
        self._manage_revealer(self.settings_revealer, stream_element.hbox)

    class StreamSection(AbstractMenu):
        def __init__(self, pipeline, settings_revealer, parent_container,
                     index):
            super().__init__(pipeline, None)
            self._parent_container = parent_container
            self._settings_revealer = settings_revealer
            self._revealer = self._build_revealer()
            self.index = index

            self.server_address_entries = None
            self.hostname = None
            self.address = None
            self.port = None
            self.mountpoint = None
            self.password = None

            self.element_name = None

            self.current_stream_type = None

            self.audiovideo_radiobutton = None
            self.video_radiobutton = None
            self.audio_radiobutton = None
            self.radiobuttons_hbox = None

            self._audiovideo_format_combobox = None
            self._video_format_combobox = None
            self._audio_format_combobox = None
            self._audiovideo_format_hbox = None
            self._video_format_hbox = None
            self._audio_format_hbox = None

            self.confirm_button = None

            self.hbox, self.vbox = self._build_newstream_vbox()
            self.summary_vbox = None

            self.sink = None

        def _build_newstream_vbox(self):
            """
            """
            self.address_entries = self._build_address_entries()
            address_hbox = utils.build_multi_widgets_hbox(
                [Gtk.Label("Address :"), ], [self.address_entries, ])

            self.mountpoint_entry = Gtk.Entry()
            self.mountpoint_entry.connect("changed", self.on_mountpoint_change)
            self.mountpoint_entry.set_placeholder_text("Type a stream name")
            mountpoint_hbox = utils.build_multi_widgets_hbox(
                [Gtk.Label("Mountpoint :"), ], [self.mountpoint_entry, ])

            self.password_entry = Gtk.Entry()
            self.password_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
            self.password_entry.set_visibility(False)
            self.password_entry.connect("changed", self.on_password_change)
            self.password_entry.set_placeholder_text("Type Icecast's password")
            password_hbox = utils.build_multi_widgets_hbox(
                [Gtk.Label("Password :"), ], [self.password_entry, ])

            radiobutton_hbox = self._build_format_group()
            # FIXME: .mkv format is not supported by shout2send Gst element.
            # It has to be either .ogg or .webm format in order to stream
            # video only feed.
            self.video_radiobutton.set_sensitive(False)

            self.confirm_button = self._build_confirm_changes_button(
                callback=self.on_confirm_clicked)
            # Label only used at initialization
            self.confirm_button.set_label("Create")

            hbox, vbox = self._build_subsection(address_hbox,
                                                mountpoint_hbox,
                                                password_hbox,
                                                radiobutton_hbox,
                                                self._audiovideo_format_hbox,
                                                self.confirm_button)
            return hbox, vbox

        def build_full_mountpoint(self):
            """
            Build mountpoint used by :class:`~core.ioelements.StreamElement`
            based on mountpoint entry and extension choosen.
            """
            self.mountpoint = self.mountpoint_entry.get_text()
            self.full_mountpoint = (self.mountpoint
                                    + self._get_format_extension())

        def _log_changes(self):
            for name, previous_value, new_value in (
                    ("hostname", self.hostname, self.host_entry.get_text()),
                    ("port", self.port, self.port_entry.get_text()),
                    ("mount point", self.mountpoint, self.mountpoint_entry.get_text()),
                    ("password", self.password, self.password_entry.get_text()),
                    ("feed type", self.current_stream_type, self._get_feed_type())):
                if previous_value != new_value:
                    if name == "password":
                        # Don't print password in logs
                        new_value = "*"
                    logger.info("[gui] stream_{index} {name} set to"
                                " '{value}'".format(index=self.index,
                                                    name=name,
                                                    value=new_value))

        def get_properties(self):
            """
            Get Gstreamer properties of
            :class:`~gui.menus.StreamMenu.StreamSection` instance.

            :return: :class:`dict` as property_key: value
            """
            audiovideo_radiobutton_value = self.audiovideo_radiobutton.get_active()
            video_radiobutton_value = self.video_radiobutton.get_active()
            audio_radiobutton_value = self.audio_radiobutton.get_active()
            feed_format = self._get_format_extension()
            try:
                address, port = self.get_ip_address()
            except socket.gaierror:
                address = self.address
                port = self.port

            return {"host": self.host_entry.get_text(),
                    "port": port,
                    "ip": address,  # Only used by StreamElement
                    "mountpoint": self.mountpoint,
                    "mount": self.full_mountpoint,  # Only used by StreamElement
                    "password": self.password,
                    "audiovideo_radiobutton": audiovideo_radiobutton_value,
                    "video_radiobutton": video_radiobutton_value,
                    "audio_radiobutton": audio_radiobutton_value,
                    "feed_format": feed_format}

        def set_properties(self, **kargs):
            """
            Set properties in the menu.

            :param kargs: :class:`dict` containing properties related to this
                menu
            """
            host_value = kargs.get("host")
            port_value = kargs.get("port")
            mountpoint_value = kargs.get("mountpoint")
            password_value = kargs.get("password")
            audiovideo_radiobutton_value = kargs.get("audiovideo_radiobutton")
            video_radiobutton_value = kargs.get("video_radiobutton")
            audio_radiobutton_value = kargs.get("audio_radiobutton")
            feed_format_value = kargs.get("feed_format")

            self.host_entry.set_text(host_value)
            self.port_entry.set_text(str(port_value))
            self.mountpoint_entry.set_text(mountpoint_value)
            self.password_entry.set_text(password_value)

            self.audiovideo_radiobutton.set_active(
                audiovideo_radiobutton_value)
            self.video_radiobutton.set_active(video_radiobutton_value)
            self.audio_radiobutton.set_active(audio_radiobutton_value)
            self._set_format_extension(feed_format_value)

            self.on_confirm_clicked(self.confirm_button)
            logger.debug(_PROPERTIES_SET.format(section="stream"))

        def on_host_change(self, widget):
            if self.port_entry.get_text() and self.mountpoint:
                self.confirm_button.set_sensitive(True)

        def on_port_change(self, widget):
            if self.host_entry.get_text() and self.mountpoint:
                self.confirm_button.set_sensitive(True)

        def on_mountpoint_change(self, widget):
            if widget.get_text() != self.mountpoint and self.port_entry.get_text():
                self.confirm_button.set_sensitive(True)

        def on_password_change(self, widget):
            if (self.host_entry.get_text()
                    and self.port_entry.get_text()
                    and self.mountpoint):
                self.confirm_button.set_sensitive(True)

        def on_format_radiobutton_toggle(self, widget):
            self._change_output_format(widget)
            self.vbox.reorder_child(self.confirm_button, -1)

            if (self.host_entry.get_text()
                    and self.port_entry.get_text()
                    and self.mountpoint_entry.get_text()):
                self.confirm_button.set_sensitive(True)

        def on_confirm_clicked(self, widget):
            self._log_changes()

            self.hostname = self.host_entry.get_text()
            previous_address = self.address
            previous_port = self.port
            try:
                self.address, self.port = self.get_ip_address()
            except Exception:
                # Bad input for host or port, the stream endpoint must not be
                # created.
                return

            element = watch.get_remote_watcher().remove_watcher(
                (previous_address, previous_port))
            if element:
                status_bar.get_status_bar().remove_remote_element(element)

            self.feed_type = self._get_feed_type()
            self.build_full_mountpoint()
            self.password = self.password_entry.get_text()
            self.element_name = self.mountpoint.split("/")[-1]
            if not self.sink:
                self.sink = self.pipeline.create_stream_branch(
                    self.element_name, self.current_stream_type, self.address,
                    self.port, self.full_mountpoint, self.password)
            else:
                if self.pipeline.is_playing:
                    utils.build_info_dialog(_PRESS_STOP_MESSAGE)

            try:
                element = watch.get_remote_watcher().add_watcher((self.address,
                                                                  self.port))
            except socket.herror:
                sub_message = ("Unknown host ({}) for `{}` mountpoint.\n"
                               "Verify the address entry.".format(
                                   self.address, self.mountpoint))
                utils.build_error_dialog("Bad input", sub_message)
                watch.get_remote_watcher().remove_watcher(
                    (previous_address, previous_port))
            else:
                status_bar.get_status_bar().add_remote_element(element)

            if not self.summary_vbox:
                self.summary_vbox = self._build_summary_box(self.index,
                                                            self.element_name)
                self._parent_container.pack_start(
                    self.summary_vbox, False, False, 0)
                self._parent_container.reorder_child(
                    self.summary_vbox, self.index)

                self._settings_revealer.remove(self.hbox)
                self._parent_container.show_all()

                logger.info("[gui] stream_{} '{}' endpoint created".format(
                    self.index, self.element_name))

            self.confirm_button.set_label("Confirm")
            self.confirm_button.set_sensitive(False)

        def on_settings_clicked(self, widget):
            return self._manage_revealer(self._revealer, self.hbox)


class StoreMenu(AbstractMenu):
    """
    """
    def __init__(self, pipeline, menu_revealer):
        super().__init__(pipeline, menu_revealer)
        self.settings_revealer = self._build_revealer()
        self.main_vbox = self._build_store_vbox()

        self.feeds = []

    def _build_store_vbox(self):
        header = self._build_header("Storing")

        self.store_add_button = self._build_add_button(
            callback=self.on_add_clicked)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_margin_end(6)
        utils.pack_widgets(vbox,
                           header,
                           self.settings_revealer,
                           self.store_add_button)
        self._make_scrolled_window(vbox)
        return vbox

    def on_store_clicked(self, widget):
        return self._manage_revealer(self.menu_revealer, self.scrolled_window)

    def on_add_clicked(self, widget):
        store_element = self.StoreSection(
            self.pipeline, self.settings_revealer,
            self.main_vbox, len(self.feeds) + 1)
        self.feeds.append(store_element)
        self._manage_revealer(self.settings_revealer, store_element.hbox)

    class StoreSection(AbstractMenu):
        def __init__(self, pipeline, settings_revealer, parent_container,
                     index):
            super().__init__(pipeline, None)
            self._parent_container = parent_container
            self._settings_revealer = settings_revealer
            self._revealer = self._build_revealer()
            self.index = index

            self.folder_selection = None
            self.filename = ""
            self.full_filename_label = None
            self.current_stream_type = None

            self.audiovideo_radiobutton = None
            self.video_radiobutton = None
            self.audio_radiobutton = None
            self.radiobuttons_hbox = None

            self._audiovideo_format_combobox = None
            self._video_format_combobox = None
            self._audio_format_combobox = None
            self._audiovideo_format_hbox = None
            self._video_format_hbox = None
            self._audio_format_hbox = None
            self.confirm_button = None

            self.hbox, self.vbox = self._build_newfile_vbox()
            self.summary_vbox = None

            self.sink = None

        def _build_newfile_vbox(self):
            """
            """
            self.folder_chooser_button = Gtk.FileChooserButton(
                action=Gtk.FileChooserAction.SELECT_FOLDER)
            self.folder_chooser_button.set_title("Select a folder")
            self.folder_chooser_button.connect("file-set",
                                               self.on_folder_selected)
            self.folder_chooser_button.set_margin_top(6)

            self.name_entry = Gtk.Entry()
            self.name_entry.set_width_chars(25)
            self.name_entry.set_input_purpose(Gtk.InputPurpose.ALPHA)
            self.name_entry.set_placeholder_text("Type a filename")
            self.name_entry.connect("changed", self.on_name_change)
            name_hbox = utils.build_multi_widgets_hbox(
                [Gtk.Label("Name :"), ], [self.name_entry, ])

            self.automatic_naming_checkbutton = Gtk.CheckButton()
            self.automatic_naming_checkbutton.set_active(True)
            self.automatic_naming_checkbutton.set_sensitive(False)  # DEV
            automatic_naming_label = Gtk.Label("Make Unique filename")
            automatic_naming_hbox = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL)
            utils.pack_widgets(automatic_naming_hbox,
                               self.automatic_naming_checkbutton,
                               automatic_naming_label)

            radiobutton_hbox = self._build_format_group()

            self.confirm_button = self._build_confirm_changes_button(
                callback=self.on_confirm_clicked)
            # Label only used at initialization
            self.confirm_button.set_label("Create")

            hbox, vbox = self._build_subsection(self.folder_chooser_button,
                                                name_hbox,
                                                automatic_naming_hbox,
                                                radiobutton_hbox,
                                                self._audiovideo_format_hbox,
                                                self.confirm_button)
            return hbox, vbox

        def _get_formatted_timestamp(self):
            """
            Get a formatted suffix, mainly used to make unique filename.

            :return: :class:`str`
            """
            if self.automatic_naming_checkbutton.get_active():
                return time.strftime("_%Y%m%d__%H-%M-%S", time.localtime())
            return ""

        def create_unique_filename(self):
            """
            Create a unique filename.
            """
            self.full_filename = (self.filename
                                  + self._get_formatted_timestamp()
                                  + self._get_format_extension())

        def build_filepath(self):
            """
            Set filepath that is used by
            :class:`~core.ioelements.StoreElement`
            """
            self.filepath = os.path.join(
                self.folder_selection, self.full_filename)

        def _log_changes(self):
            for name, previous_value, new_value in (
                    ("directory", self.folder_selection, self.folder_chooser_button.get_filename()),
                    ("filename", self.filename, self.name_entry.get_text()),
                    ("feed type", self.current_stream_type, self._get_feed_type())):
                if previous_value != new_value:
                    logger.info("[gui] store_{index} {name} set to"
                                " '{value}'".format(index=self.index,
                                                    name=name,
                                                    value=new_value))

        def get_properties(self):
            """
            Get Gstreamer properties of
            :class:`~gui.menus.StoreMenu.StoreSection` instance.

            :return: :class:`dict` as property_key: value
            """
            folder_selected = self.folder_chooser_button.get_filename()
            name_entry_value = self.name_entry.get_text()
            automatic_naming_value = self.automatic_naming_checkbutton.get_active()

            audiovideo_radiobutton_value = self.audiovideo_radiobutton.get_active()
            video_radiobutton_value = self.video_radiobutton.get_active()
            audio_radiobutton_value = self.audio_radiobutton.get_active()
            feed_format = self._get_format_extension()

            return {"folder_selection": folder_selected,
                    "name_entry": name_entry_value,
                    "automatic_naming_checkbutton": automatic_naming_value,
                    "location": self.filepath,
                    "audiovideo_radiobutton": audiovideo_radiobutton_value,
                    "video_radiobutton": video_radiobutton_value,
                    "audio_radiobutton": audio_radiobutton_value,
                    "feed_format": feed_format}

        def set_properties(self, **kargs):
            """
            Set properties in the menu.

            :param kargs: :class:`dict` containing properties related to this
                menu
            """
            folder_selected = kargs.get("folder_selection")
            name_entry_value = kargs.get("name_entry")
            automatic_naming_value = kargs.get("automatic_naming_checkbutton")
            audiovideo_radiobutton_value = kargs.get("audiovideo_radiobutton")
            video_radiobutton_value = kargs.get("video_radiobutton")
            audio_radiobutton_value = kargs.get("audio_radiobutton")
            feed_format_value = kargs.get("feed_format")

            self.folder_chooser_button.set_filename(folder_selected)
            self.name_entry.set_text(name_entry_value)
            self.automatic_naming_checkbutton.set_active(
                automatic_naming_value)
            self.audiovideo_radiobutton.set_active(
                audiovideo_radiobutton_value)
            self.video_radiobutton.set_active(video_radiobutton_value)
            self.audio_radiobutton.set_active(audio_radiobutton_value)
            self._set_format_extension(feed_format_value)

            self.on_confirm_clicked(self.confirm_button)
            logger.debug(_PROPERTIES_SET.format(section="store"))

        def on_folder_selected(self, widget):
            if self.name_entry.get_text():
                self.confirm_button.set_sensitive(True)

        def on_name_change(self, widget):
            if (widget.get_text() != self.filename
                    and self.folder_chooser_button.get_filename()):
                self.confirm_button.set_sensitive(True)

        def on_format_radiobutton_toggle(self, widget):
            self._change_output_format(widget)
            self.vbox.reorder_child(self.confirm_button, -1)

            if (self.folder_chooser_button.get_filename()
                    and self.name_entry.get_text()):
                self.confirm_button.set_sensitive(True)

        def on_confirm_clicked(self, widget):
            self._log_changes()

            self.filename = self.name_entry.get_text()
            self.create_unique_filename()
            self.folder_selection = self.folder_chooser_button.get_filename()
            self.build_filepath()
            element_name = self.current_stream_type + "_" + self.filename
            if not self.sink:
                self.sink = self.pipeline.create_store_branch(
                    self.current_stream_type, self.filepath, element_name)
            else:
                if self.pipeline.is_playing:
                    utils.build_info_dialog(_PRESS_STOP_MESSAGE)

            if not self.summary_vbox:
                self.summary_vbox = self._build_summary_box(self.index,
                                                            self.full_filename)
                self._parent_container.pack_start(
                    self.summary_vbox, False, False, 0)
                self._parent_container.reorder_child(
                    self.summary_vbox, self.index)

                self._settings_revealer.remove(self.hbox)
                self._parent_container.show_all()

                logger.info("[gui] store_{} '{}' endpoint created".format(
                    self.index, self.full_filename))

            self.confirm_button.set_label("Confirm")
            self.confirm_button.set_sensitive(False)

        def on_settings_clicked(self, widget):
            return self._manage_revealer(self._revealer, self.hbox)


class SettingsMenu(AbstractMenu):
    """
    """
    def __init__(self, pipeline, menu_revealer):
        super().__init__(pipeline, menu_revealer)
        self.current_text_overlay = None
        self.requested_text_overlay = None
        self.current_image_path = None
        self.requested_image_path = None
        self.hide_text_requested = False
        self.hide_image_requested = False

        self.h_alignment = "left"  # DEV
        self.v_alignment = "top"  # DEV
        self.positions = ("Top-Left", "Top-Right",
                          "Bottom-Left", "Bottom-Right",
                          "Center")

        self.settings_vbox = self._build_settings_vbox()

    def _build_settings_vbox(self):
        header = self._build_header("Settings")

        self.text_overlay_entry = Gtk.Entry()
        self.text_overlay_entry.set_placeholder_text(
            "Text displayed on screen")
        self.text_overlay_entry.set_width_chars(30)
        self.text_overlay_entry.connect("changed", self.on_text_change)
        self.text_overlay_entry.set_sensitive(True)  # DEV

        self.text_position_combobox = Gtk.ComboBoxText()
        for position in self.positions:
            self.text_position_combobox.append_text(position)
        self.text_position_combobox.set_active(0)
        self.text_position_combobox.set_margin_start(24)
        self.text_position_combobox.set_sensitive(False)  # DEV

        self.hide_text_checkbutton = Gtk.CheckButton("Hide Text")
        self.hide_text_checkbutton.connect("toggled", self.on_hide_text_toggle)

        self.image_chooser_button = Gtk.FileChooserButton()
        self.image_chooser_button.set_title("Select an image to display")
        self.image_chooser_button.connect("file-set", self.on_image_selected)
        self.image_chooser_button.set_sensitive(True)  # DEV

        self.image_position_combobox = Gtk.ComboBoxText()
        for position in self.positions:
            self.image_position_combobox.append_text(position)
        self.image_position_combobox.set_active(1)
        self.image_position_combobox.set_margin_start(24)
        self.image_position_combobox.set_sensitive(False)  # DEV

        self.hide_image_checkbutton = Gtk.CheckButton("Hide Image")
        self.hide_image_checkbutton.connect(
            "toggled", self.on_hide_image_toggle)

        self.confirm_button = self._build_confirm_changes_button(
                callback=self.on_confirm_clicked)
        self.confirm_button.set_label("Confirm")
        self.confirm_button.set_size_request(250, 20)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_margin_top(6)
        vbox.set_margin_end(6)
        utils.pack_widgets(vbox,
                           header,
                           self.text_overlay_entry,
                           self.text_position_combobox,
                           self.hide_text_checkbutton,
                           self.image_chooser_button,
                           self.image_position_combobox,
                           self.hide_image_checkbutton,
                           self.confirm_button)
        self._make_scrolled_window(vbox)
        return vbox

    def get_text_overlay(self):
        """
        Return a :class:`tuple` containing setting for text_overlay.
        """
        return (self.requested_text_overlay,
                self.h_alignment, self.v_alignment)

    def _log_changes(self):
        for name, previous_value, new_value in (
                ("Text overlay", self.requested_text_overlay, self.text_overlay_entry.get_text()),
                ("Image overlay path", self.requested_image_path, self.image_chooser_button.get_filename()),
                ("Hide text", self.hide_text_requested, self.hide_text_checkbutton.get_active()),
                ("Hide image", self.hide_image_requested, self.hide_image_checkbutton.get_active())):
            if previous_value != new_value:
                logger.info("[gui] {name} set to '{value}'".format(
                    name=name, value=new_value))

    def get_properties(self):
        """
        Get properties set in the menu.

        :return: :class:`dict` as property_key: value
        """
        text_overlay_value = self.text_overlay_entry.get_text()
        text_position_value = self.text_position_combobox.get_active_text()
        hide_text_value = self.hide_text_checkbutton.get_active()
        image_filename = self.image_chooser_button.get_filename()
        image_position_value = self.image_position_combobox.get_active_text()
        hide_image_value = self.hide_image_checkbutton.get_active()

        return {"text_overlay_entry": text_overlay_value,
                "text_position_combobox": text_position_value,
                "hide_text_checkbutton": hide_text_value,
                "image_chooser_button": image_filename,
                "image_position_combobox": image_position_value,
                "hide_image_checkbutton": hide_image_value}

    def set_properties(self, **kargs):
        """
        Set properties in the menu.

        :param kargs: :class:`dict` containing properties related to this menu
        """
        text_overlay_value = kargs.get("text_overlay_entry")
        text_position_value = kargs.get("text_position_combobox")
        hide_text_value = kargs.get("hide_text_checkbutton", False)
        image_filename = kargs.get("image_chooser_button")
        image_position_value = kargs.get("image_position_combobox")
        hide_image_value = kargs.get("hide_image_checkbutton", False)

        self.text_overlay_entry.set_text(text_overlay_value)
        self.set_active_text(self.text_position_combobox,
                             self.positions,
                             text_position_value)
        self.hide_text_checkbutton.set_active(hide_text_value)

        try:
            self.image_chooser_button.set_filename(image_filename)
            self.pipeline.set_image_overlay(image_filename, -6, 6)
        except TypeError:
            # No image has been choosen, just ignore the exception.
            pass
        self.set_active_text(self.image_position_combobox,
                             self.positions,
                             image_position_value)
        self.hide_image_checkbutton.set_active(hide_image_value)

        self.on_confirm_clicked(self.confirm_button)
        logger.debug(_PROPERTIES_SET.format(section="settings"))

    def on_settings_clicked(self, widget):
        return self._manage_revealer(self.menu_revealer, self.scrolled_window)

    def on_text_change(self, widget):
        self.confirm_button.set_sensitive(True)

    def on_image_selected(self, widget):
        self.confirm_button.set_sensitive(True)

    def on_hide_text_toggle(self, widget):
        self.confirm_button.set_sensitive(True)

    def on_hide_image_toggle(self, widget):
        self.confirm_button.set_sensitive(True)

    def on_confirm_clicked(self, widget):
        self._log_changes()

        self.requested_text_overlay = self.text_overlay_entry.get_text()
        self.requested_image_path = self.image_chooser_button.get_filename()
        self.hide_text_requested = self.hide_text_checkbutton.get_active()
        self.hide_image_requested = self.hide_image_checkbutton.get_active()

        if not self.hide_text_requested:
            self.pipeline.set_text_overlay(
                self.requested_text_overlay, "left", "top")
        else:
            self.pipeline.set_text_overlay("", "left", "top")

        if not self.hide_image_requested and not self.current_image_path:
            self.pipeline.set_image_overlay(
                self.requested_image_path, -6, 6, 1)
            self.current_image_path = self.requested_image_path
        else:
            # Hack to hide an image.
            self.pipeline.set_image_overlay(alpha=0.0001)

        self.confirm_button.set_sensitive(False)
