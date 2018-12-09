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

import gi
gi.require_version("GstVideo", "1.0")  # NOQA
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkX11
from gi.repository import GstVideo
from gi.repository import GObject

from core import process
from gui import audio_displays
from gui import menus
from gui import utils


class Feed:
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

        self.video_menu = menus.VideoMenu(self.pipeline, self.menu_revealer,
                                          self.placeholder_pipeline)
        self.audio_menu = menus.AudioMenu(self.pipeline, self.menu_revealer,
                                          self.placeholder_pipeline)
        self.stream_menu = menus.StreamMenu(self.pipeline, self.menu_revealer)
        self.store_menu = menus.StoreMenu(self.pipeline, self.menu_revealer)
        self.settings_menu = menus.SettingsMenu(self.pipeline,
                                                self.menu_revealer)

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

        self.audio_level_display = audio_displays.AudioLevelDisplay(
            Gtk.DrawingArea())
        self.audio_level_box = self._build_audio_level_box()
        self.controls.overlay_container.add_overlay(self.audio_level_box)

        self.hbox.pack_start(self.controls.overlay_container, True, True, 0)
        self.hbox.pack_start(self.menu_revealer, False, False, 0)

    def set_xid(self):
        self.xid = self.video_monitor.get_property("window").get_xid()

    def get_placeholder_pipeline(self):
        """
        Get a placeholder pipeline from
        :class:`~core.process.PlaceholderPipeline`
        """
        return process.PlaceholderPipeline()

    def create_pipeline_instance(self, mode):
        """
        Create pipeline instance and attaches it to GUI.

        :param mode: application mode as :class:`str`

        :return: :class:`~core.process.Pipeline` or one of it subclasses
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

    def _build_audio_level_box(self):
        """
        """
        hbox = Gtk.Box(Gtk.Orientation.HORIZONTAL)
        hbox.set_halign(Gtk.Align.END)
        hbox.set_margin_top(6)
        hbox.set_margin_bottom(6)
        # Hide the box until an audio signal is received
        hbox.set_no_show_all(True)
        utils.pack_widgets(hbox, self.audio_level_display.drawing_area)

        return hbox

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
        self.pipeline.set_null_state()

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

        # Forcing to switch back to preview mode
        self.pipeline.set_stop_state()

    def remove_all_inputs(self):
        """
        Remove all inputs created in video and audio menus.
        """
        self.pipeline.remove_input_sources()

    def remove_all_outputs(self):
        """
        Remove all outputs created in stream and store menus.
        """
        self.pipeline.remove_output_branches()

        for menu in (self.stream_menu, self.store_menu):
            for section in menu.feeds:
                menu.main_vbox.remove(section.summary_vbox)
            menu.feeds = []

    def on_message(self, bus, message):
        # Getting the RMS audio level value:
        message_structure = Gst.Message.get_structure(message)
        message_type = message.type

        if message_type == Gst.MessageType.ELEMENT:
            if str(Gst.Structure.get_name(message_structure)) == "level":
                if not self.audio_level_box.get_visible():
                    self.audio_level_box.set_no_show_all(False)
                    self.audio_level_box.show_all()

                rms = message_structure.get_value("rms")
                peak = message_structure.get_value("peak")
                decay = message_structure.get_value("decay")
                self.audio_level_display.on_level(rms, peak, decay)
        elif message_type == Gst.MessageType.EOS:
            self.pipeline.set_null_state()
        elif message_type == Gst.MessageType.ERROR:
            if self.pipeline.is_from_streaming(message):
                self.pipeline.reconnect_streaming_branch(message)
            else:
                err, debug = message.parse_error()
                print('%s' % err, debug)  # DEBUG
                # Watching for feed loss during streaming:
                # if '(651)' not in debug:
                #    # The error is not a socket error.
                #    self.pipel.stream_stop()
                #    self.build_filename(streamfailed=True)
                #    self.create_backup_pipeline()


class ControlBar:
    """
    Class creating an horizontal control bar containing media controls.
    """
    def __init__(self, pipeline, menu_revealer, images,
                 video_menu, audio_menu, stream_menu, store_menu,
                 settings_menu, placeholder_pipeline=None):
        self.images = images

        self._pipeline = pipeline
        self._placeholder_pipeline = placeholder_pipeline
        self._menu_revealer = menu_revealer
        self.abstract_menu = menus.AbstractMenu(
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
        utils.pack_widgets(self.controlbox, self.toolbar)
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
        self.mute_button = self._build_toolbutton(
            "Mute",
            self.images.icons["speaker"]["striked"],
            on_signal="clicked",
            callback=self.on_mute_clicked
        )

        self._populate_toolbar(toolbar,
                               self.play_button,
                               self.stop_button,
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
        icon = self.images.switch_icon_version(icon_id,
                                               widget.get_icon_widget())
        widget.set_icon_widget(icon)
        widget.show_all()

    def on_play_clicked(self, widget):

        self.stop_button.set_icon_widget(self.images.get_regular_icon("stop"))
        self.stop_button.set_sensitive(True)

        if (not self.video_menu.current_video_source
                and not self.audio_menu.current_audio_source):
            utils.build_info_dialog("Select an input source",
                                    secondary_text="Go to Feed > Inputs")
            return
        elif (not self.stream_menu.has_sink_set()
                and not self.store_menu.has_sink_set()):
            utils.build_info_dialog("Select an output sink",
                                    secondary_text="Go to Feed > Outputs")
            return

        self._switch_widget_icons(widget, "play")

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
                feed_streamed.sink, **feed_streamed.get_properties())
            feed_streamed.full_filename_label.set_label(
                feed_streamed.element_name)

        for feed_recorded in self.store_menu.feeds:
            feed_recorded.create_unique_filename()
            feed_recorded.build_filepath()
            self._pipeline.update_gstelement_properties(
                feed_recorded.sink, **feed_recorded.get_properties())
            feed_recorded.full_filename_label.set_label(
                feed_recorded.full_filename)

    def on_mute_clicked(self, widget):
        if self._pipeline.speaker_volume.get_property("mute"):
            self._pipeline.speaker_volume.set_property("mute", False)
            widget.set_icon_widget(self.images.icons["speaker"]["regular"])
        else:
            self._pipeline.speaker_volume.set_property("mute", True)
            widget.set_icon_widget(self.images.icons["speaker"]["striked"])
        widget.show_all()
