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
# Copyright (c) 2016-2018 David Testé

import abc
import os
import socket
import time

from gi.repository import Gtk
import ipaddress

from backend import process
from user_interface import utils


AUDIO_VIDEO_STREAM = process.AUDIO_VIDEO_STREAM
VIDEO_ONLY_STREAM = process.VIDEO_ONLY_STREAM
AUDIO_ONLY_STREAM = process.AUDIO_ONLY_STREAM


class AbstractMenu:
    """
    """
    def __init__(self, pipeline, menu_revealer, placeholder_pipeline=None):
        self.pipeline = pipeline
        self.placeholder_pipeline = placeholder_pipeline
        self.menu_revealer = menu_revealer

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
        This button triggers interaction with the backend in case of settings
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
        self.host_entry.set_placeholder_text("hostname or IP address")
        self.host_entry.connect("changed", self.on_host_change)

        self.port_entry = Gtk.Entry()
        self.port_entry.set_max_length(5)
        self.port_entry.set_width_chars(5)
        if hasattr(self.port_entry, "set_max_width_chars"):
            self.port_entry.set_max_width_chars(5)
        self.port_entry.set_placeholder_text("port")
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
            except socket.gaierror:
                utils.build_error_dialog("Bad input", "Hostname is not known")
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
        hbox.set_margin_left(24)
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

    def _build_summary_box(self, filename):
        """
        Build a container that sums up information about an output sink.

        :param filename: filename of stored stream as :class:`str`

        :return: :class:`Gtk.Box`
        """
        self.full_filename_label = Gtk.Label(filename)
        settings_button = Gtk.Button(stock=Gtk.STOCK_PROPERTIES)
        settings_button.connect("clicked", self.on_settings_clicked)

        summary_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        summary_hbox.set_margin_top(6)
        utils.pack_widgets(summary_hbox,
                           self.full_filename_label,
                           settings_button)

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
                break

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
        title = Gtk.Label("Video Source")
        title.set_margin_top(6)

        self.usb_radiobutton = Gtk.RadioButton("USB")
        self.usb_radiobutton.set_active(True)
        self.usb_radiobutton.connect("toggled", self.on_commtype_toggle)
        self.usb_sources = Gtk.ComboBoxText()
        if not self.pipeline.video_sources:
            self.usb_sources.append_text("")
        else:
            for source in self.pipeline.video_sources:
                self.usb_sources.append_text(source.description)
                self.sources_list.append(source.description)
        self.usb_sources.connect("changed", self.on_usb_input_change)
        self.usb_sources.set_margin_left(24)
        self.video_usb_widgets.append(self.usb_sources)

        self.ip_radiobutton = Gtk.RadioButton(
            label="IP (soon)", group=self.usb_radiobutton)
        self.ip_radiobutton.connect("toggled", self.on_commtype_toggle)
        # TODO: Remove the next line once IP camera are handled in a pipeline.
        self.ip_radiobutton.set_sensitive(False)

        self.address_entries = self._build_address_entries()
        self.address_entries.set_margin_left(24)

        self.video_ip_widgets.append(self.address_entries)
        self._make_widget_unavailable(*self.video_ip_widgets)

        self.video_confirm_button = self._build_confirm_changes_button(
            callback=self.on_confirm_clicked)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(6)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_margin_right(6)
        utils.pack_widgets(vbox,
                           title,
                           self.usb_radiobutton,
                           self.usb_sources,
                           self.ip_radiobutton,
                           self.address_entries,
                           self.video_confirm_button,
                           separator)
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
            self.on_confirm_clicked(self.video_confirm_button)

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
            self.video_confirm_button.set_sensitive(True)
            self.requested_video_source = self.pipeline.get_source_by_description(
                active_text)

    def on_confirm_clicked(self, widget):
        if self.requested_video_source == self.current_video_source:
            return

        self.pipeline.set_input_source(self.requested_video_source)
        self.current_video_source = self.requested_video_source
        self.requested_video_source = None

        self.video_confirm_button.set_sensitive(False)

        if self.placeholder_pipeline.is_playing_state():
            self.placeholder_pipeline.set_stop_state()
            self.pipeline.set_preview_state("audio")
        elif self.pipeline.get_current_text() == "No video source":
            # An audio source is already set
            self.pipeline.set_text_overlay("PREVIEW", "left", "top")


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
        title = Gtk.Label("Audio Source")
        title.set_margin_top(6)

        self.mic_sources = Gtk.ComboBoxText()
        for source in self.pipeline.audio_sources:
            self.mic_sources.append_text(source.description)
            self.sources_list.append(source.description)
        self.mic_sources.connect("changed", self.on_input_change)
        self.mic_sources.set_margin_left(24)

        self.mute_checkbutton = Gtk.CheckButton("Mute (soon)")
        self.mute_checkbutton.connect("toggled", self.on_mute_toggle)
        self.mute_checkbutton.set_sensitive(False)

        self.output_sinks = Gtk.ComboBoxText()
        index = 0
        for description, device in self.pipeline.speaker_sinks.items():
            self.output_sinks.append_text(description)
            self.sinks_list.append(description)
            if device == self.pipeline.speaker_sink.get_property("device"):
                self.output_sinks.set_active(index)
            index += 1
        self.output_sinks.connect("changed", self.on_output_change)
        self.output_sinks.set_margin_left(24)

        self.audio_confirm_button = self._build_confirm_changes_button(
            callback=self.on_confirm_clicked)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(6)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_margin_right(6)
        utils.pack_widgets(vbox,
                           title,
                           self.mic_sources,
                           self.mute_checkbutton,
                           self.output_sinks,
                           self.audio_confirm_button,
                           separator)
        self._make_scrolled_window(vbox)
        return vbox

    def get_properties(self):
        """
        Get properties set in the menu.

        :return: :class:`dict` as property_key: value
        """
        audio_source_selected = self.mic_sources.get_active_text()
        audio_sink_selected = self.output_sinks.get_active_text()
        source_muted = self.mute_checkbutton.get_active()

        return {"audio_source_selected": audio_source_selected,
                "audio_sink_selected": audio_sink_selected,
                "source_muted": source_muted}

    def set_properties(self, **kargs):
        """
        Set properties in the menu.

        :param kargs: :class:`dict` containing properties related to this menu
        """
        audio_source_selected = kargs.get("audio_source_selected")
        audio_sink_selected = kargs.get("audio_sink_selected")
        source_muted = kargs.get("source_muted")

        self.requested_audio_source = None
        self.current_audio_source = None
        self.set_active_text(
            self.mic_sources, self.sources_list, audio_source_selected)
        self.on_input_change(self.mic_sources)
        self.mute_checkbutton.set_active(source_muted)

        # TODO: Handle user choice for output audio sink, currently this
        # implementation overrides user's choice by setting automatically
        # default speaker output.
        index = 0
        for description, device in self.pipeline.speaker_sinks.items():
            if device == self.pipeline.speaker_sink.get_property("device"):
                self.output_sinks.set_active(index)
            index += 1

        if audio_source_selected:
            self.on_confirm_clicked(self.audio_confirm_button)

    def on_audio_input_clicked(self, widget):
        return self._manage_revealer(self.menu_revealer, self.scrolled_window)

    def on_input_change(self, widget):
        self.audio_confirm_button.set_sensitive(True)
        self.requested_audio_source = self.pipeline.get_source_by_description(
            widget.get_active_text())

    def on_output_change(self, widget):
        self.audio_confirm_button.set_sensitive(True)
        # self.requested_audio_sink = self.pipeline.get_source_by_description(
        #    widget.get_active_text())  # DEV

    def on_mute_toggle(self, widget):
        """
        Mute audio input in the pipeline. This take effect immediatly.
        """
        raise NotImplementedError

    def on_confirm_clicked(self, widget):
        if self.requested_audio_source != self.current_audio_source:
            self.pipeline.set_input_source(self.requested_audio_source)
            self.current_audio_source = self.requested_audio_source

        # if self.requested_audio_sink != self.current_audio_sink:  # DEV
        #    self.pipeline.set_speaker_sink(self.requested_audio_sink)  # DEV
        #    self.current_audio_sink = self.requested_audio_sink  # DEV

        self.audio_confirm_button.set_sensitive(False)

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
        title = Gtk.Label("Streaming server")
        title.set_margin_top(6)

        self.stream_add_button = self._build_add_button(
            callback=self.on_add_clicked)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(6)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_margin_right(6)
        utils.pack_widgets(vbox,
                           title,
                           self.settings_revealer,
                           separator,
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
        self._manage_revealer(self.settings_revealer, stream_element.vbox)

    class StreamSection(AbstractMenu):
        def __init__(self, pipeline, settings_revealer, parent_container,
                     index):
            super().__init__(pipeline, None)
            self._parent_container = parent_container
            self._settings_revealer = settings_revealer
            self._revealer = self._build_revealer()
            self._index = index

            self.server_address_entries = None
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

            self.store_confirm_button = None

            self.vbox = self._build_newstream_vbox()
            self.summary_vbox = None

            self.streamsink = None

        def _build_newstream_vbox(self):
            """
            """
            address_hbox = Gtk.Box(Gtk.Orientation.HORIZONTAL)
            address_label = Gtk.Label("Address :    ")
            self.address_entries = self._build_address_entries()
            utils.pack_widgets(address_hbox,
                               address_label,
                               self.address_entries)

            mountpoint_hbox = Gtk.Box(Gtk.Orientation.HORIZONTAL)
            mountpoint_label = Gtk.Label("Mountpoint : ")
            self.mountpoint_entry = Gtk.Entry()
            self.mountpoint_entry.connect("changed", self.on_mountpoint_change)
            utils.pack_widgets(
                mountpoint_hbox, mountpoint_label, self.mountpoint_entry)

            password_hbox = Gtk.Box(Gtk.Orientation.HORIZONTAL)
            password_label = Gtk.Label("Password :   ")
            self.password_entry = Gtk.Entry()
            self.password_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
            self.password_entry.set_visibility(False)
            self.password_entry.connect("changed", self.on_password_change)
            utils.pack_widgets(password_hbox,
                               password_label,
                               self.password_entry)

            radiobutton_hbox = self._build_format_group()
            # FIXME: .mkv format is not supported by shout2send Gst element.
            # It has to be either .ogg or .webm format in order to stream
            # video only feed.
            self.video_radiobutton.set_sensitive(False)

            self.stream_confirm_button = self._build_confirm_changes_button(
                callback=self.on_confirm_clicked)
            # Label only used at initialization
            self.stream_confirm_button.set_label("Create")

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            vbox.set_margin_right(6)
            utils.pack_widgets(vbox,
                               address_hbox,
                               mountpoint_hbox,
                               password_hbox,
                               radiobutton_hbox,
                               self._audiovideo_format_hbox,
                               self.stream_confirm_button,)
            return vbox

        def build_full_mountpoint(self):
            """
            Build mountpoint used by :class:`~backend.ioelements.StreamElement`
            based on mountpoint entry and extension choosen.
            """
            self.full_mountpoint = (self.mountpoint
                                    + self._get_format_extension())

        def get_properties(self):
            """
            Get Gstreamer properties of
            :class:`~user_interface.StreamMenu.StreamSection` instance.

            :return: :class:`dict` as property_key: value
            """
            audiovideo_radiobutton_value = self.audiovideo_radiobutton.get_active()
            video_radiobutton_value = self.video_radiobutton.get_active()
            audio_radiobutton_value = self.audio_radiobutton.get_active()
            feed_format = self._get_format_extension()

            return {"host": self.host_entry.get_text(),
                    "port": self.port_entry.get_text(),
                    "mountpoint": self.mountpoint,
                    "mount": self.full_mountpoint,  # Used only by StremElement
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
            self.port_entry.set_text(port_value)
            self.mountpoint_entry.set_text(mountpoint_value)
            self.password_entry.set_text(password_value)

            self.audiovideo_radiobutton.set_active(
                audiovideo_radiobutton_value)
            self.video_radiobutton.set_active(video_radiobutton_value)
            self.audio_radiobutton.set_active(audio_radiobutton_value)
            self._set_format_extension(feed_format_value)

            self.on_confirm_clicked(self.stream_confirm_button)

        def on_host_change(self, widget):
            if self.port_entry.get_text() and self.mountpoint:
                self.stream_confirm_button.set_sensitive(True)

        def on_port_change(self, widget):
            if self.host_entry.get_text() and self.mountpoint:
                self.stream_confirm_button.set_sensitive(True)

        def on_mountpoint_change(self, widget):
            text = widget.get_text()
            if text != self.mountpoint:
                self.mountpoint = text
                if self.port_entry.get_text():
                    self.stream_confirm_button.set_sensitive(True)

        def on_password_change(self, widget):
            text = widget.get_text()
            if text != self.password:
                self.password = text

        def on_format_radiobutton_toggle(self, widget):
            self._change_output_format(widget)
            self.vbox.reorder_child(self.stream_confirm_button, -1)

            if (self.server_address_entries
                    and self.port_entry
                    and self.mountpoint_entry):
                self.stream_confirm_button.set_sensitive(True)

        def on_confirm_clicked(self, widget):
            try:
                self.address, self.port = self.get_ip_address()
            except Exception:
                # Bad input for host or port, the stream endpoint must not be
                # created.
                return

            self.element_name = self.mountpoint.split("/")[-1]
            self.build_full_mountpoint()
            if not self.streamsink:
                self.streamsink = self.pipeline.create_stream_sink(
                    self.element_name, self.current_stream_type, self.address,
                    self.port, self.full_mountpoint, self.password)

            if not self.summary_vbox:
                self.summary_vbox = self._build_summary_box(self.element_name)
                self._parent_container.pack_start(
                    self.summary_vbox, False, False, 0)
                self._parent_container.reorder_child(
                    self.summary_vbox, self._index)

                self._settings_revealer.remove(self.vbox)
                self._parent_container.show_all()

            self.stream_confirm_button.set_label("Confirm")
            self.stream_confirm_button.set_sensitive(False)

        def on_settings_clicked(self, widget):
            return self._manage_revealer(self._revealer, self.vbox)


class StoreMenu(AbstractMenu):
    """
    """
    def __init__(self, pipeline, menu_revealer):
        super().__init__(pipeline, menu_revealer)
        self.settings_revealer = self._build_revealer()
        self.main_vbox = self._build_store_vbox()

        self.feeds = []

    def _build_store_vbox(self):
        title = Gtk.Label("Storing")
        title.set_margin_top(6)

        self.store_add_button = self._build_add_button(
            callback=self.on_add_clicked)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(6)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_margin_right(6)
        utils.pack_widgets(vbox,
                           title,
                           self.settings_revealer,
                           separator,
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
        self._manage_revealer(self.settings_revealer, store_element.vbox)

    class StoreSection(AbstractMenu):
        def __init__(self, pipeline, settings_revealer, parent_container,
                     index):
            super().__init__(pipeline, None)
            self._parent_container = parent_container
            self._settings_revealer = settings_revealer
            self._revealer = self._build_revealer()
            self._index = index

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
            self.store_confirm_button = None

            self.vbox = self._build_newfile_vbox()
            self.summary_vbox = None

            self.filesink = None

        def _build_newfile_vbox(self):
            """
            """
            self.folder_chooser_button = Gtk.FileChooserButton(
                action=Gtk.FileChooserAction.SELECT_FOLDER)
            self.folder_chooser_button.set_title("Select a folder")
            self.folder_chooser_button.connect("file-set",
                                               self.on_folder_selected)
            self.folder_chooser_button.set_margin_top(6)

            name_label = Gtk.Label("Name ")
            self.name_entry = Gtk.Entry()
            self.name_entry.set_width_chars(25)
            self.name_entry.set_input_purpose(Gtk.InputPurpose.ALPHA)
            self.name_entry.set_placeholder_text("Type a filename")
            self.name_entry.connect("changed", self.on_entry_change)
            name_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            utils.pack_widgets(name_hbox, name_label, self.name_entry)

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

            self.store_confirm_button = self._build_confirm_changes_button(
                callback=self.on_confirm_clicked)
            # Label only used at initialization
            self.store_confirm_button.set_label("Create")

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            utils.pack_widgets(vbox,
                               self.folder_chooser_button,
                               name_hbox,
                               automatic_naming_hbox,
                               radiobutton_hbox,
                               self._audiovideo_format_hbox,
                               self.store_confirm_button)
            return vbox

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
            :class:`~backend.ioelements.StoreElement`
            """
            self.filepath = os.path.join(
                self.folder_selection, self.full_filename)

        def get_properties(self):
            """
            Get Gstreamer properties of
            :class:`~user_interface.StoreMenu.StoreSection` instance.

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
            self.folder_selection = folder_selected
            self.name_entry.set_text(name_entry_value)
            self.filename = name_entry_value
            self.automatic_naming_checkbutton.set_active(
                automatic_naming_value)
            self.audiovideo_radiobutton.set_active(
                audiovideo_radiobutton_value)
            self.video_radiobutton.set_active(video_radiobutton_value)
            self.audio_radiobutton.set_active(audio_radiobutton_value)
            self._set_format_extension(feed_format_value)

            self.on_confirm_clicked(self.store_confirm_button)

        def on_folder_selected(self, widget):
            self.folder_selection = widget.get_filename()
            if self.filename:
                self.store_confirm_button.set_sensitive(True)

        def on_entry_change(self, widget):
            text = widget.get_text()
            if text != self.filename:
                self.filename = text
                if self.folder_selection:
                    self.store_confirm_button.set_sensitive(True)

        def on_format_radiobutton_toggle(self, widget):
            self._change_output_format(widget)
            self.vbox.reorder_child(self.store_confirm_button, -1)

            if self.folder_selection and self.filename:
                self.store_confirm_button.set_sensitive(True)

        def on_confirm_clicked(self, widget):
            self.create_unique_filename()
            self.build_filepath()
            element_name = self.current_stream_type + "_" + self.filename
            if not self.filesink:
                self.filesink = self.pipeline.create_store_sink(
                    self.current_stream_type, self.filepath, element_name)

            if not self.summary_vbox:
                self.summary_vbox = self._build_summary_box(self.full_filename)
                self._parent_container.pack_start(
                    self.summary_vbox, False, False, 0)
                self._parent_container.reorder_child(
                    self.summary_vbox, self._index)

                self._settings_revealer.remove(self.vbox)
                self._parent_container.show_all()

            self.store_confirm_button.set_label("Confirm")
            self.store_confirm_button.set_sensitive(False)

        def on_settings_clicked(self, widget):
            return self._manage_revealer(self._revealer, self.vbox)


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
        title = Gtk.Label("Settings")
        title.set_margin_bottom(6)

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
        self.text_position_combobox.set_margin_left(24)
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
        self.image_position_combobox.set_margin_left(24)
        self.image_position_combobox.set_sensitive(False)  # DEV

        self.hide_image_checkbutton = Gtk.CheckButton("Hide Image")
        self.hide_image_checkbutton.connect(
            "toggled", self.on_hide_image_toggle)

        self.settings_confirm_button = self._build_confirm_changes_button(
                callback=self.on_confirm_clicked)
        self.settings_confirm_button.set_label("Confirm")
        self.settings_confirm_button.set_size_request(250, 20)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(6)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_margin_right(6)
        utils.pack_widgets(vbox,
                           title,
                           self.text_overlay_entry,
                           self.text_position_combobox,
                           self.hide_text_checkbutton,
                           self.image_chooser_button,
                           self.image_position_combobox,
                           self.hide_image_checkbutton,
                           self.settings_confirm_button,
                           separator)
        self._make_scrolled_window(vbox)
        return vbox

    def get_text_overlay(self):
        """
        Return a :class:`tuple` containing setting for text_overlay.
        """
        return (self.requested_text_overlay,
                self.h_alignment, self.v_alignment)

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

        self.on_confirm_clicked(self.settings_confirm_button)

    def on_settings_clicked(self, widget):
        return self._manage_revealer(self.menu_revealer, self.scrolled_window)

    def on_text_change(self, widget):
        self.requested_text_overlay = widget.get_text()
        self.settings_confirm_button.set_sensitive(True)

    def on_image_selected(self, widget):
        self.requested_image_path = widget.get_filename()
        self.settings_confirm_button.set_sensitive(True)

    def on_hide_text_toggle(self, widget):
        self.hide_text_requested = widget.get_active()
        self.settings_confirm_button.set_sensitive(True)

    def on_hide_image_toggle(self, widget):
        self.hide_image_requested = widget.get_active()
        self.settings_confirm_button.set_sensitive(True)

    def on_confirm_clicked(self, widget):
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

        self.settings_confirm_button.set_sensitive(False)
