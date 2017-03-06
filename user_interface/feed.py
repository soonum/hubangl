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
# Copyright (c) 2016 David Testé

import abc
import os
import sys
import time

import gi
#gi.require_version("Gtk", "3.0")  # NOQA # DEBUG
gi.require_version("Gst", "1.0")  # NOQA # DEBUG
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import GdkX11
from gi.repository import GstVideo
from gi.repository import GObject

sys.path.insert(0, "..")  # NOQA # TODO: use __init__.py for managing backend package
from backend import process
from backend import iofetch


AUDIO_VIDEO_STREAM = process.AUDIO_VIDEO_STREAM
VIDEO_ONLY_STREAM = process.VIDEO_ONLY_STREAM
AUDIO_ONLY_STREAM = process.AUDIO_ONLY_STREAM


def _pack_widgets(box, *widgets):
    """
    Pack each ``widget`` in ``box``.

    FIXME: Documentation to complete.

    TODO: Add kwargs for managing the 3 last args of pack_start.
          ``expand``, ``fill``, ``padding``

    :param box: :class:`Gtk.HBox` or :class:`Gtk.VBox`
    :param widgets: Gtk widgets
    """
    for widget in widgets:
        box.pack_start(widget, False, False, 0)


class NewFeed:
    """
    """
    def __init__(self, mode, images):
        self.hbox = Gtk.Box(Gtk.Orientation.HORIZONTAL)

        self.menu_revealer = self._build_revealer()

        self.video_monitor = Gtk.DrawingArea()
        self.video_monitor.set_margin_left(6)
        self.video_monitor.set_margin_right(6)
        self.video_monitor.set_margin_bottom(6)
        self.video_monitor.set_halign(Gtk.Align.FILL)
        self.video_monitor.set_valign(Gtk.Align.FILL)
        self.video_monitor.set_size_request(700, 400)

        self.placeholder_pipeline = self.get_placeholder_pipeline()
        self.placeholder_bus = self.create_gstreamer_bus(
            self.placeholder_pipeline.pipeline)

        self.pipeline = self.create_pipeline_instance(mode)
        self.bus = self.create_gstreamer_bus(self.pipeline.pipeline)
        self.xid = None

        self.video_menu = VideoMenu(
            self.pipeline, self.menu_revealer, self.placeholder_pipeline)
        self.audio_menu = AudioMenu(
            self.pipeline, self.menu_revealer, self.placeholder_pipeline)
        self.stream_menu = StreamMenu(self.pipeline, self.menu_revealer)
        self.store_menu = StoreMenu(self.pipeline, self.menu_revealer)
        self.settings_menu = SettingsMenu(self.pipeline, self.menu_revealer)

        self.images = images
        self.controls = ControlBar(self.pipeline, self.menu_revealer,
                                   self.images,
                                   self.video_menu,
                                   self.audio_menu,
                                   self.stream_menu,
                                   self.store_menu,
                                   self.settings_menu,
                                   self.placeholder_pipeline)
        self.controls.overlay_container.add(self.video_monitor)
        self.controls.display_controls()

        self.vumeter_box = self._build_vumeter()
        self.controls.overlay_container.add_overlay(self.vumeter_box)

        self.hbox.pack_start(self.controls.overlay_container, True, True, 0)
        self.hbox.pack_start(self.menu_revealer, False, False, 0)

    def set_xid(self):
        self.xid = self.video_monitor.get_property("window").get_xid()

    def get_placeholder_pipeline(self):
        """
        Get a placeholder pipeline from
        :class:`~backend.process.PlaceholderPipeline`
        """
        return process.PlaceholderPipeline()

    def create_pipeline_instance(self, mode):
        """
        Create pipeline instance and attaches it to GUI.

        :param mode: application mode as :class:`str`

        :return: :class:`~backend.process.Pipeline` or one of it subclasses
        """
        if mode == "standalone":
            return process.Pipeline()
        elif mode == "monitoring":
            return process.Monitoring()
        elif mode == "controlroom":
            return process.ControlRoom()
        else:
            raise ValueError

    def create_gstreamer_bus(self, pipeline_element):
        """
        """
        bus = pipeline_element.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        # Used to get messages that GStreamer emits.
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)
        return bus

    def _build_revealer(self):
        """
        """
        revealer = Gtk.Revealer()
        revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_LEFT)
        revealer.set_transition_duration(250)
        return revealer

    def _build_vumeter(self):
        """
        """
        # TODO: True stereo feed has to be implemented.
        self.vumeter_left = Gtk.ProgressBar()
        self.vumeter_left.set_orientation(Gtk.Orientation.VERTICAL)
        self.vumeter_left.set_inverted(True)
        self.vumeter_right = Gtk.ProgressBar()
        self.vumeter_right.set_orientation(Gtk.Orientation.VERTICAL)
        self.vumeter_right.set_inverted(True)

        vumeter_hbox = Gtk.Box(Gtk.Orientation.HORIZONTAL)
        vumeter_hbox.set_halign(Gtk.Align.END)
        vumeter_hbox.set_margin_top(6)
        vumeter_hbox.set_margin_bottom(6)
        _pack_widgets(vumeter_hbox,
                      self.vumeter_left,
                      self.vumeter_right)

        return vumeter_hbox

    def iec_scale(self, db):
        """
        Returns the meter deflection percentage given a db value.
        """
        percentage = 0.0

        if db < -70.0:
            percentage = 0.0
        elif db < -60.0:
            percentage = (db + 70.0) * 0.25
        elif db < -50.0:
            percentage = (db + 60.0) * 0.5 + 2.5
        elif db < -40.0:
            percentage = (db + 50.0) * 0.75 + 7.5
        elif db < -30.0:
            percentage = (db + 40.0) * 1.5 + 15.0
        elif db < -20.0:
            percentage = (db + 30.0) * 2.0 + 30.0
        elif db < 0.0:
            percentage = (db + 20.0) * 2.5 + 50.0
        else:
            percentage = 100.0

        return percentage / 100

    def on_sync_message(self, bus, message):
        if message.get_structure().get_name() == 'prepare-window-handle':
            imagesink = message.src
            imagesink.set_property('force-aspect-ratio', True)
            imagesink.set_window_handle(self.xid)

    def gather_properties(self):
        """
        """
        session_properties = {}
        session_properties["video"] = self.video_menu.get_properties()
        session_properties["audio"] = self.audio_menu.get_properties()
        session_properties["settings"] = self.settings_menu.get_properties()

        for index, stream_section in enumerate(self.stream_menu.feeds):
            key = "stream_" + str(index)
            session_properties[key] = stream_section.get_properties()

        for index, store_section in enumerate(self.store_menu.feeds):
            key = "store_" + str(index)
            session_properties[key] = store_section.get_properties()

        return session_properties

    def spread_properties(self, **kargs):
        """
        """
        self.controls.on_stop_clicked(self.controls.stop_button)
        self.placeholder_pipeline.set_play_state()

        self.remove_all_inputs()
        self.remove_all_outputs()

        video = kargs.pop("video")
        audio = kargs.pop("audio")
        settings = kargs.pop("settings")

        self.video_menu.set_properties(**video)
        self.audio_menu.set_properties(**audio)
        self.settings_menu.set_properties(**settings)

        for key, sub_dict in kargs.items():
            if "stream_" in key:
                self.stream_menu.on_add_clicked(
                    self.stream_menu.stream_add_button)
                self.stream_menu.feeds[-1].set_properties(**sub_dict)
            elif "store_" in key:
                self.store_menu.on_add_clicked(
                    self.store_menu.store_add_button)
                self.store_menu.feeds[-1].set_properties(**sub_dict)

    def remove_all_inputs(self):
        """
        Remove all inputs created in video and audio menus.
        """
        self.pipeline.remove_input_sources()

    def remove_all_outputs(self):
        """
        Remove all outputs created in stream and store menus.
        """
        self.pipeline.remove_output_sinks()

        for menu in (self.stream_menu, self.store_menu):
            for section in menu.feeds:
                menu.main_vbox.remove(section.summary_vbox)
            menu.feeds = []

    def on_message(self, bus, message):
        # Getting the RMS audio level value:
        s = Gst.Message.get_structure(message)
        if message.type == Gst.MessageType.ELEMENT:
            if str(Gst.Structure.get_name(s)) == "level":
                percentage = self.iec_scale(s.get_value("rms")[0])
                # This is not a true stereo signal.
                self.vumeter_left.set_fraction(percentage)
                self.vumeter_right.set_fraction(percentage)

        t = message.type
        if t == Gst.MessageType.EOS:
            self.streampipe.set_state(Gst.State.NULL)
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print ('%s' % err, debug)  # DEBUG
            # Watching for feed loss during streaming:
            #if '(651)' not in debug:
            #    # The error is not a socket error.
            #    self.pipel.stream_stop()
            #    self.build_filename(streamfailed=True)
            #    self.create_backup_pipeline()


class ControlBar:
    """
    Class creating an horizontal control bar containing media controls.
    """
    def __init__(self, pipeline, menu_revealer, images,
                 video_menu, audio_menu, stream_menu, store_menu, settings_menu,
                 placeholder_pipeline=None):
        self.images = images

        self._pipeline = pipeline
        self._placeholder_pipeline = placeholder_pipeline
        self._menu_revealer = menu_revealer
        self.abstract_menu = AbstractMenu(
            self._pipeline, self._menu_revealer, self._placeholder_pipeline)  # DEBUG

        self.video_menu = video_menu
        self.audio_menu = audio_menu
        self.stream_menu = stream_menu
        self.store_menu = store_menu
        self.settings_menu = settings_menu

        self.overlay_container = Gtk.Overlay()
        self.controlbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.controlbox.set_valign(Gtk.Align.END)
        self.controlbox.set_margin_bottom(6)
        self.controlbox.set_halign(Gtk.Align.CENTER)

        self.toolbar = self._build_toolbar()

    def display_controls(self):
        _pack_widgets(self.controlbox, self.toolbar)
        self.overlay_container.add_overlay(self.controlbox)

    def _build_toolbutton(self, name, icon,
                          on_signal=None, callback=None, tooltip_text=None):
        toolbutton = Gtk.ToolButton(name)
        # FIXME: Tooltip text does not appear on the screen
        if not tooltip_text:
            toolbutton.set_tooltip_text(name)
        else:
            toolbutton.set_tooltip_text(tooltip_text)
        toolbutton.set_icon_widget(icon)

        if on_signal and callback:
            toolbutton.connect(on_signal, callback)
        return toolbutton

    def _build_toolbar(self):
        """
        """
        toolbar = Gtk.Toolbar()

        self.play_button = self._build_toolbutton(
            "Play",
            self.images.icons["play"]["regular"],
            on_signal="clicked",
            callback=self.on_play_clicked
        )
        self.stop_button = self._build_toolbutton(
            "Stop",
            self.images.icons["stop"]["regular"],
            on_signal="clicked",
            callback=self.on_stop_clicked
        )
        self.video_button = self._build_toolbutton(
            "VIDEO",
            self.images.icons["camera"]["regular"],
            on_signal="clicked",
            callback=self.on_video_clicked,
        )
        self.audio_button = self._build_toolbutton(
            "Audio",
            self.images.icons["micro"]["regular"],
            on_signal="clicked",
            callback=self.on_audio_clicked
        )
        self.stream_button = self._build_toolbutton(
            "Stream",
            self.images.icons["streaming"]["regular"],
            on_signal="clicked",
            callback=self.on_stream_clicked
        )
        self.store_button = self._build_toolbutton(
            "Store",
            self.images.icons["storage"]["regular"],
            on_signal="clicked",
            callback=self.on_store_clicked
        )
        self.settings_button = self._build_toolbutton(
            "Settings",
            self.images.icons["settings"]["regular"],
            on_signal="clicked",
            callback=self.on_settings_clicked
        )
        self.mute_button = self._build_toolbutton(
            "Mute",
            self.images.icons["speaker"]["striked"],
            on_signal="clicked",
            callback=self.on_mute_clicked
        )

        self._populate_toolbar(toolbar,
                               self.play_button,
                               self.stop_button,
                               self.video_button,
                               self.audio_button,
                               self.stream_button,
                               self.store_button,
                               self.settings_button,
                               self.mute_button)
        return toolbar

    def _populate_toolbar(self, toolbar, *toolbuttons):
        """
        Populate a :class:`Gtk.Toolbar` with several :class:`Gtk.ToolButton`.

        .. note:: Tool buttons will be insert into ``toolbar`` following input
            arguments order.
        """
        for ind, toolbutton in enumerate(toolbuttons):
            toolbar.insert(toolbutton, ind)

    def _switch_widget_icons(self, widget, icon_id):
        """
        Switch icon type version ``regular`` to ``activated`` or the other way
        around depending on ``widget`` current icon.

        :param widget: :class:`Gtk.ToolButton`
        :param icon_id: icon name as :class:`str`
        """
        icon = self.images.switch_icon_version(icon_id, widget.get_icon_widget())
        widget.set_icon_widget(icon)
        widget.show_all()

    def set_regular_icons(self):
        """
        Switch icons that open a menu to their regular version.
        """
        icon_mapping = {self.video_button: "camera",
                        self.audio_button: "micro",
                        self.stream_button: "streaming",
                        self.store_button: "storage",
                        self.settings_button: "settings"}

        for widget, icon_name in icon_mapping.items():
            widget.set_icon_widget(self.images.get_regular_icon(icon_name))
            widget.show_all()

    def on_play_clicked(self, widget):

        self.stop_button.set_icon_widget(self.images.get_regular_icon("stop"))
        self.stop_button.set_sensitive(True)

        self._switch_widget_icons(widget, "play")
        if (not self.video_menu.current_video_source
                and not self.audio_menu.current_audio_source):
            return

        self._pipeline.set_text_overlay(*self.settings_menu.get_text_overlay())

        # Ensure placeholder pipeline is stopped first in case of
        # loading a session configuration
        self._placeholder_pipeline.set_stop_state()
        self._pipeline.set_play_state()
        self.play_button.set_sensitive(False)

    # TODO: Warn user about the need to press STOP button if any changes are
    # requested in any feed ouput. Maybe warn the user via a notification
    # window or a pop-up window.

    def on_stop_clicked(self, widget):
        if not self._pipeline.is_playing:
            return

        self.play_button.set_icon_widget(self.images.get_regular_icon("play"))
        self.play_button.set_sensitive(True)

        self._switch_widget_icons(widget, "stop")
        self._pipeline.set_stop_state()
        self.stop_button.set_sensitive(False)

        # FIXME: a change of feed type does not create a new output element
        # neither remove the current one. As a consequence, once a feed type
        # is chosen, after user click play this not possible (yet) to change
        # that type. A new output element must be created via `Add` button.
        for feed_streamed in self.stream_menu.feeds:
            feed_streamed.build_full_mountpoint()
            self._pipeline.update_gstelement_properties(
                feed_streamed.streamsink, **feed_streamed.get_properties())
            feed_streamed.full_filename_label.set_label(
                feed_streamed.element_name)

        for feed_recorded in self.store_menu.feeds:
            feed_recorded.create_unique_filename()
            feed_recorded.build_filepath()
            self._pipeline.update_gstelement_properties(
                feed_recorded.filesink, **feed_recorded.get_properties())
            feed_recorded.full_filename_label.set_label(
                feed_recorded.full_filename)

    def on_video_clicked(self, widget):
        self.set_regular_icons()
        if self.video_menu.on_video_input_clicked(widget):
            self._switch_widget_icons(widget, "camera")

    def on_audio_clicked(self, widget):
        self.set_regular_icons()
        if self.audio_menu.on_audio_input_clicked(widget):
            self._switch_widget_icons(widget, "micro")

    def on_stream_clicked(self, widget):
        self.set_regular_icons()
        if self.stream_menu.on_stream_clicked(widget):
            self._switch_widget_icons(widget, "streaming")

    def on_store_clicked(self, widget):
        self.set_regular_icons()
        if self.store_menu.on_store_clicked(widget):
            self._switch_widget_icons(widget, "storage")

    def on_settings_clicked(self, widget):
        self.set_regular_icons()
        if self.settings_menu.on_settings_clicked(widget):
            self._switch_widget_icons(widget, "settings")

    def on_mute_clicked(self, widget):
        if self._pipeline.speaker_volume.get_property("mute"):
            self._pipeline.speaker_volume.set_property("mute", False)
            widget.set_icon_widget(self.images.icons["speaker"]["regular"])
        else:
            self._pipeline.speaker_volume.set_property("mute", True)
            widget.set_icon_widget(self.images.icons["speaker"]["striked"])
        widget.show_all()


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

    def _build_ipv4_entries(self):
        """
        """
        self.ipv4_field1 = Gtk.Entry()
        self.ipv4_field2 = Gtk.Entry()
        self.ipv4_field3 = Gtk.Entry()
        self.ipv4_field4 = Gtk.Entry()

        for field in (self.ipv4_field1, self.ipv4_field2,
                      self.ipv4_field3, self.ipv4_field4):
            field.set_max_length(3)
            field.set_width_chars(3)
            field.set_max_width_chars(3)
            field.set_input_purpose(Gtk.InputPurpose.DIGITS)

        self.port_entry = Gtk.Entry()
        self.port_entry.set_max_length(5)
        self.port_entry.set_width_chars(5)
        self.port_entry.set_max_width_chars(5)
        self.port_entry.set_input_purpose(Gtk.InputPurpose.DIGITS)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        _pack_widgets(hbox,
                      self.ipv4_field1, Gtk.Label("."),
                      self.ipv4_field2, Gtk.Label("."),
                      self.ipv4_field3, Gtk.Label("."),
                      self.ipv4_field4, Gtk.Label(":"),
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

    def _build_ipv6_entry(self):
        """
        """
        raise NotImplementedError

    def get_ipv4_address(self):
        """
        """
        ip_fields_values = []
        for field in (self.ipv4_field1, self.ipv4_field2,
                      self.ipv4_field3, self.ipv4_field4):
            text = field.get_text()
            if not text:
                raise TypeError
                break
            ip_fields_values.append(text)
        else:
            port_value = self.port_entry.get_text()
            if not port_value:
                raise TypeError
            else:
                ip_address = ".".join(ip_fields_values)
                port = int(port_value)
                return ip_address, port

    def set_ip_fields(self, ip_entries, ip_address, port):
        """
        Set entries relative to an IP address to ``ip_address`` and ``port``.

        :param ip_entries: container containing entries
        :param ip_address: full ip address as :class:`str`
        :param port: port to connect to as :class:`int`
        """
        if "." in ip_address:
            # This is an IPv4 address
            ip_fields_values = ip_address.split(".")
            for index, field in enumerate((self.ipv4_field1, self.ipv4_field2,
                                           self.ipv4_field3, self.ipv4_field4)):
                field.set_text(ip_fields_values[index])
            self.port_entry.set_text(str(port))
        elif ":" in ip_address:
            # This is an IPv6 address
            ip_fields_values = ip_address.split(":")
            # TODO: populate this case once IPv6 handling is implemented.

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
        _pack_widgets(hbox, text_label, combo_box)

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
        _pack_widgets(radiobutton_hbox,
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
        _pack_widgets(summary_hbox,
                      self.full_filename_label, settings_button)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(6)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        _pack_widgets(vbox,
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

    def on_ipv46_toggle(self, widget):
        pass


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
        # ---------------------------------

        ipv46_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        ipv46_hbox.set_margin_left(24)

        self.ipv4_radiobutton = Gtk.RadioButton("v4")
        self.ipv4_radiobutton.set_active(True)
        self.ipv4_radiobutton.connect("toggled", self.on_ipv46_toggle)

        self.ipv6_radiobutton = Gtk.RadioButton("v6", group=self.ipv4_radiobutton)
        self.ipv6_radiobutton.connect("toggled", self.on_ipv46_toggle)
        _pack_widgets(ipv46_hbox, self.ipv4_radiobutton, self.ipv6_radiobutton)

        self.ipv4_entries = self._build_ipv4_entries()
        self.ipv4_entries.set_margin_left(24)

        # TODO: Implement ipv6_entry
        # ipv6_entry = self._build_ipv6_entry()
        # ipv6_entry.set_margin_left(24)

        self.video_ip_widgets.extend(
            (self.ipv4_radiobutton, self.ipv6_radiobutton, self.ipv4_entries))
        self._make_widget_unavailable(*self.video_ip_widgets)

        self.video_confirm_button = self._build_confirm_changes_button(
            callback=self.on_confirm_clicked)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(6)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_margin_right(6)
        _pack_widgets(vbox,
                      title,
                      self.usb_radiobutton,
                      self.usb_sources,
                      self.ip_radiobutton,
                      ipv46_hbox,
                      self.ipv4_entries,
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
        ipv4_radiobutton_value = self.ipv4_radiobutton.get_active()
        ipv6_radiobutton_value = self.ipv6_radiobutton.get_active()

        return {"usb_radiobutton": usb_radiobutton_value,
                "usb_source_selected": usb_source_selected,
                "ip_radiobutton": ip_radiobutton_value,
                "ipv4_radiobutton": ipv4_radiobutton_value,
                "ipv6_radiobutton": ipv6_radiobutton_value, }

    def set_properties(self, **kargs):
        """
        Set properties in the menu.

        :param kargs: :class:`dict` containing properties related to this menu
        """
        usb_radiobutton_value = kargs.get("usb_radiobutton")
        usb_source_selected = kargs.get("usb_source_selected")
        ip_radiobutton_value = kargs.get("ip_radiobutton")
        ipv4_radiobutton_value = kargs.get("ipv4_radiobutton")
        ipv6_radiobutton_value = kargs.get("ipv6_radiobutton")

        self.usb_radiobutton.set_active(usb_radiobutton_value)
        self.requested_video_source = None
        self.current_video_source = None
        self.set_active_text(
            self.usb_sources, self.sources_list, usb_source_selected)
        self.on_usb_input_change(self.usb_sources)

        self.ip_radiobutton.set_active(ip_radiobutton_value)
        self.ipv4_radiobutton.set_active(ipv4_radiobutton_value)
        self.ipv6_radiobutton.set_active(ipv6_radiobutton_value)

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

    def on_ipv46_toggle(self, widget):
        raise NotImplementedError

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
        _pack_widgets(vbox,
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
        #self.requested_audio_sink = self.pipeline.get_source_by_description(
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

        #if self.requested_audio_sink != self.current_audio_sink:  # DEV
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
        _pack_widgets(vbox,
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
        def __init__(self, pipeline, settings_revealer, parent_container, index):
            super().__init__(pipeline, None)
            self._parent_container = parent_container
            self._settings_revealer = settings_revealer
            self._revealer = self._build_revealer()
            self._index = index

            self.remote_server_radiobutton = None
            self.local_server_radiobutton = None
            self.server_address_entries = None
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

            self.stream_remote_widgets = []
            self.stream_local_widgets = []

            self.vbox = self._build_newstream_vbox()
            self.summary_vbox = None

            self.streamsink = None

        def _build_newstream_vbox(self):
            """
            """
            self.remote_server_radiobutton = Gtk.RadioButton("Remote")
            self.remote_server_radiobutton.set_active(True)
            self.remote_server_radiobutton.connect(
                "clicked", self.on_remote_server_toggle)

            self.local_server_radiobutton = Gtk.RadioButton(
                label="Local (soon)", group=self.remote_server_radiobutton)
            self.local_server_radiobutton.connect(
                "clicked", self.on_local_server_toggle)
            self.local_server_radiobutton.set_sensitive(False)  # DEV

            server_type_hbox = Gtk.Box(Gtk.Orientation.HORIZONTAL)
            _pack_widgets(server_type_hbox,
                          self.remote_server_radiobutton,
                          self.local_server_radiobutton)

            ipv46_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            ipv46_hbox.set_margin_left(24)
            self.ipv4_radiobutton = Gtk.RadioButton("v4")
            self.ipv4_radiobutton.set_active(True)
            self.ipv4_radiobutton.connect("toggled", self.on_ipv46_toggle)
            self.ipv6_radiobutton = Gtk.RadioButton(
                "v6 (soon)", group=self.ipv4_radiobutton)
            self.ipv6_radiobutton.connect("toggled", self.on_ipv46_toggle)
            self.ipv6_radiobutton.set_sensitive(False)  # DEV
            _pack_widgets(ipv46_hbox,
                          self.ipv4_radiobutton,
                          self.ipv6_radiobutton)

            self.ipv4_entries = self._build_ipv4_entries()
            self.ipv4_entries.set_margin_left(24)

            # TODO: Implement ipv6_entry
            # ipv6_entry = self._build_ipv6_entry()
            # ipv6_entry.set_margin_left(24)

            self.stream_remote_widgets.extend((self.ipv4_radiobutton,
                                               self.ipv6_radiobutton,
                                               self.ipv4_entries))

            mountpoint_hbox = Gtk.Box(Gtk.Orientation.HORIZONTAL)
            mountpoint_label = Gtk.Label("Mountpoint : ")
            self.mountpoint_entry = Gtk.Entry()
            self.mountpoint_entry.connect("changed", self.on_mountpoint_change)
            _pack_widgets(
                mountpoint_hbox, mountpoint_label, self.mountpoint_entry)

            password_hbox = Gtk.Box(Gtk.Orientation.HORIZONTAL)
            password_label = Gtk.Label("Password :   ")
            self.password_entry = Gtk.Entry()
            self.password_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
            self.password_entry.set_visibility(False)
            self.password_entry.connect("changed", self.on_password_change)
            _pack_widgets(password_hbox, password_label, self.password_entry)

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
            _pack_widgets(vbox,
                          server_type_hbox,
                          ipv46_hbox,
                          self.ipv4_entries,
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
            self.full_mountpoint = self.mountpoint + self._get_format_extension()

        def get_properties(self):
            """
            Get Gstreamer properties of
            :class:`~user_interface.StreamMenu.StreamSection` instance.

            :return: :class:`dict` as property_key: value
            """
            remote_radiobutton_value = self.remote_server_radiobutton.get_active()
            local_radiobutton_value = self.local_server_radiobutton.get_active()

            ipv4_radiobutton_value = self.ipv4_radiobutton.get_active()
            ipv6_radiobutton_value = self.ipv6_radiobutton.get_active()

            audiovideo_radiobutton_value = self.audiovideo_radiobutton.get_active()
            video_radiobutton_value = self.video_radiobutton.get_active()
            audio_radiobutton_value = self.audio_radiobutton.get_active()
            feed_format = self._get_format_extension()

            return {"remote_radiobutton": remote_radiobutton_value,
                    "local_radiobutton": local_radiobutton_value,
                    "ipv4_radiobutton": ipv4_radiobutton_value,
                    "ipv6_radiobutton": ipv6_radiobutton_value,
                    "ip_address": self.ip_address,
                    "port": self.port,
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

            :param kargs: :class:`dict` containing properties related to this menu
            """
            remote_radiobutton_value = kargs.get("remote_radiobutton")
            local_radiobutton_value = kargs.get("local_radiobutton")
            ipv4_radiobutton_value = kargs.get("ipv4_radiobutton")
            ipv6_radiobutton_value = kargs.get("ipv6_radiobutton")
            ip_address_value = kargs.get("ip_address")
            port_value = kargs.get("port")
            mountpoint_value = kargs.get("mountpoint")
            password_value = kargs.get("password")
            audiovideo_radiobutton_value = kargs.get("audiovideo_radiobutton")
            video_radiobutton_value = kargs.get("video_radiobutton")
            audio_radiobutton_value = kargs.get("audio_radiobutton")
            feed_format_value = kargs.get("feed_format")

            self.remote_server_radiobutton.set_active(remote_radiobutton_value)
            self.local_server_radiobutton.set_active(local_radiobutton_value)
            self.ipv4_radiobutton.set_active(ipv4_radiobutton_value)
            self.ipv6_radiobutton.set_active(ipv6_radiobutton_value)

            self.set_ip_fields(
                self.ipv4_entries, ip_address_value, port_value)
            self.mountpoint_entry.set_text(mountpoint_value)
            self.password_entry.set_text(password_value)

            self.audiovideo_radiobutton.set_active(audiovideo_radiobutton_value)
            self.video_radiobutton.set_active(video_radiobutton_value)
            self.audio_radiobutton.set_active(audio_radiobutton_value)
            self._set_format_extension(feed_format_value)

            self.on_confirm_clicked(self.stream_confirm_button)

        def on_remote_server_toggle(self, widget):
            if widget.get_active():
                # TODO: hide widgets related to local_server and then show
                # remote_server related ones.
                pass

        def on_local_server_toggle(self, widget):
            if widget.get_active():
                # TODO: hide widgets related to remote_server and then show
                # local_server related ones.
                pass

        def on_mountpoint_change(self, widget):
            text = widget.get_text()
            if text != self.mountpoint:
                self.mountpoint = text
                if self.port_entry:
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
                self.ip_address, self.port = self.get_ipv4_address()
            except TypeError:
                # All IP/port fields are not filled
                return

            self.element_name = self.mountpoint.split("/")[-1]
            self.build_full_mountpoint()
            if not self.streamsink:
                self.streamsink = self.pipeline.create_stream_sink(
                    self.element_name, self.current_stream_type, self.ip_address,
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
        _pack_widgets(vbox,
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
        def __init__(self, pipeline, settings_revealer, parent_container, index):
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
            self.folder_chooser_button.connect("file-set", self.on_folder_selected)
            self.folder_chooser_button.set_margin_top(6)

            name_label = Gtk.Label("Name ")
            self.name_entry = Gtk.Entry()
            self.name_entry.set_width_chars(25)
            self.name_entry.set_input_purpose(Gtk.InputPurpose.ALPHA)
            self.name_entry.set_placeholder_text("Type a filename")
            self.name_entry.connect("changed", self.on_entry_change)
            name_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            _pack_widgets(name_hbox, name_label, self.name_entry)

            self.automatic_naming_checkbutton = Gtk.CheckButton()
            self.automatic_naming_checkbutton.set_active(True)
            self.automatic_naming_checkbutton.set_sensitive(False)  # DEV
            automatic_naming_label = Gtk.Label("Make Unique filename")
            automatic_naming_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            _pack_widgets(automatic_naming_hbox,
                          self.automatic_naming_checkbutton,
                          automatic_naming_label)

            radiobutton_hbox = self._build_format_group()

            self.store_confirm_button = self._build_confirm_changes_button(
                callback=self.on_confirm_clicked)
            # Label only used at initialization
            self.store_confirm_button.set_label("Create")

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            _pack_widgets(vbox,
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
                return time.strftime("_%Y%m%d__%H-%M-%S", time.gmtime())
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

            :param kargs: :class:`dict` containing properties related to this menu
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
            self.automatic_naming_checkbutton.set_active(automatic_naming_value)
            self.audiovideo_radiobutton.set_active(audiovideo_radiobutton_value)
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
        self.text_overlay_entry.set_placeholder_text("Text displayed on screen")
        self.text_overlay_entry.set_width_chars(30)
        self.text_overlay_entry.connect("changed", self.on_text_change)
        self.text_overlay_entry.set_sensitive(False)  # DEV

        self.text_position_combobox = Gtk.ComboBoxText()
        for position in self.positions:
            self.text_position_combobox.append_text(position)
        self.text_position_combobox.set_active(0)
        self.text_position_combobox.set_margin_left(24)
        self.text_position_combobox.set_sensitive(False)  # DEV

        self.image_chooser_button = Gtk.FileChooserButton()
        self.image_chooser_button.set_title("Select an image to display")
        self.image_chooser_button.connect("file-set", self.on_image_selected)
        self.image_chooser_button.set_sensitive(False)  # DEV

        self.image_position_combobox = Gtk.ComboBoxText()
        for position in self.positions:
            self.image_position_combobox.append_text(position)
        self.image_position_combobox.set_active(1)
        self.image_position_combobox.set_margin_left(24)
        self.image_position_combobox.set_sensitive(False)  # DEV

        self.settings_confirm_button = self._build_confirm_changes_button(
                callback=self.on_confirm_clicked)
        self.settings_confirm_button.set_label("Confirm")
        self.settings_confirm_button.set_size_request(250, 20)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(6)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_margin_right(6)
        _pack_widgets(vbox,
                      title,
                      self.text_overlay_entry,
                      self.text_position_combobox,
                      self.image_chooser_button,
                      self.image_position_combobox,
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
        image_filename = self.image_chooser_button.get_filename()
        image_position_value = self.image_position_combobox.get_active_text()

        return {"text_overlay_entry": text_overlay_value,
                "text_position_combobox": text_position_value,
                "image_chooser_button": image_filename,
                "image_position_combobox": image_position_value}

    def set_properties(self, **kargs):
        """
        Set properties in the menu.

        :param kargs: :class:`dict` containing properties related to this menu
        """
        text_overlay_value = kargs.get("text_overlay_entry")
        text_position_value = kargs.get("text_position_combobox")
        image_filename = kargs.get("image_chooser_button")
        image_position_value = kargs.get("image_position_combobox")

        self.text_overlay_entry.set_text(text_overlay_value)
        self.set_active_text(self.text_position_combobox,
                             self.positions,
                             text_position_value)
        try:
            self.image_chooser_button.set_filename(image_filename)
        except TypeError:
            # No image has been choosen, just ignore the exception.
            pass
        self.set_active_text(self.image_position_combobox,
                             self.positions,
                             image_position_value)

        self.on_confirm_clicked(self.settings_confirm_button)

    def on_settings_clicked(self, widget):
        return self._manage_revealer(self.menu_revealer, self.scrolled_window)

    def on_text_change(self, widget):
        self.requested_text_overlay = widget.get_text()
        self.settings_confirm_button.set_sensitive(True)

    def on_image_selected(self, widget):
        self.requested_image_path = widget.get_filename()
        self.settings_confirm_button.set_sensitive(True)

    def on_confirm_clicked(self, widget):
        if self.requested_text_overlay != self.current_text_overlay:
            self.pipeline.set_text_overlay(
                self.requested_text_overlay, "left", "top")
            self.current_text_overlay = self.requested_text_overlay

        if self.requested_image_path != self.current_image_path:
            self.pipeline.set_image_overlay(self.requested_image_path, -6, 6)
            self.current_image_path = self.requested_image_path

        self.settings_confirm_button.set_sensitive(False)
