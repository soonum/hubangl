#!/usr/bin/env python34
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

import sys

from gi.repository import Gtk

import feed
sys.path.insert(0, "..")  # NOQA # DEBUG
from backend import ioelements  # DEBUG
from backend import iofetch  # DEBUG
from backend import process


def _pack_widgets(box, *widgets):
        """
        Pack each ``widget`` in ``box``.

        FIXME: Documentation to complete.

        TODO: Add kwargs for managing the 3 last args of pack_start.

        :param box: :class:`Gtk.HBox` or :class:`Gtk.VBox`
        :param widgets: Gtk widgets
        """
        for widget in widgets:
            box.pack_start(widget, False, False, 0)


class MainWindow:
    """
    Main window of user interface.
    Specific application is pluged to it depending on view mode selected,
    default application launched is StandaloneApp.
    """
    def __init__(self, default_app=None):
        self.window = Gtk.Window()
        self.window.set_title("HUBAngl")
        self.window.connect("delete_event", lambda w, e: Gtk.main_quit())
        self.window.set_size_request(400, 300)
        self.window.set_position(Gtk.WindowPosition.CENTER)

        if default_app:
            self.current_app = default_app
        else:
            #self.current_app = StandaloneApp()  # DEBUG
            #self.current_app = BaseApp(self.window)  # DEBUG
            self.current_app = BaseApp(self.window, "standalone")
            #self.current_app = BaseApp(self.window, "monitoring")
            self.current_app_container = self.current_app.container
            #self.current_app = ControlRoomApp()  # DEBUG
            #self.current_app_container = self.current_app.grid  # DEBUG

        self.menu_bar = Gtk.MenuBar()
        self.menu_item_new = self._build_menu_new(self.menu_bar)
        self.menu_item_feed = self._build_menu_feed(self.menu_bar)
        self.menu_item_view, self.current_view_mode = self._build_menu_view(
                self.menu_bar
        )
        self.menu_item_help = self._build_menu_help(self.menu_bar)

        self.main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        _pack_widgets(self.main_vbox,
                      self.menu_bar,
                      self.current_app_container)
        self.window.add(self.main_vbox)
        self.window.show_all()

        self.current_app.make_app()

    def _build_menu_new(self, menu_bar):
        """
        Build the whole New menu item.
        """
        menu_item = self._build_menu_item("New", menu_bar)
        self.dropmenu_new = Gtk.Menu()
        menu_item.set_submenu(self.dropmenu_new)
        self.subitem_new_session = self._build_menu_item(
            "New Session", self.dropmenu_new,
            image=Gtk.STOCK_NEW
        )
        self.subitel_save_configuration = self._build_menu_item(
            "Save configuration", self.dropmenu_new,
            image=Gtk.STOCK_SAVE
        )
        self.subitem_load_configuration = self._build_menu_item(
            "Load Configuration", self.dropmenu_new,
            image=Gtk.STOCK_FILE
        )
        self.subitem_recent_session = self._build_menu_item(
            "Recent Session", self.dropmenu_new,
            image=Gtk.STOCK_REVERT_TO_SAVED
        )
        self.subitem_preferences = self._build_menu_item(
            "Preferences", self.dropmenu_new,
            image=Gtk.STOCK_PREFERENCES
        )
        self._build_separatormenuitem(self.dropmenu_new)
        self.subitem_quit = self._build_menu_item(
            "Quit", self.dropmenu_new,
            image=Gtk.STOCK_QUIT, callback=Gtk.main_quit
        )

        return menu_item

    def _build_menu_feed(self, menu_bar):
        """
        Build the whole Feed menu item.
        """
        menu_item = self._build_menu_item("Feed", menu_bar)
        self.dropmenu_feed = Gtk.Menu()
        menu_item.set_submenu(self.dropmenu_feed)
        self.subitem_play = self._build_menu_item(
                "Play", self.dropmenu_feed,
                callback=self.current_app.feed.controls.on_play_clicked
        )
        self.subitem_stop = self._build_menu_item(
                "Stop", self.dropmenu_feed,
                callback=self.current_app.feed.controls.on_stop_clicked
        )
        self._build_separatormenuitem(self.dropmenu_feed)
        # Inputs______________________________________________________
        self.subitem_inputs = self._build_menu_item(
            "Inputs", self.dropmenu_feed
        )
        # Submenu Inputs
        self.dropmenu_inputs = Gtk.Menu()
        self.subitem_inputs.set_submenu(self.dropmenu_inputs)
        self.subitem_audio = self._build_menu_item(
                "Audio", self.dropmenu_inputs,
                callback=self.current_app.feed.controls.audio_menu.on_audio_input_clicked
        )
        self.subitem_video = self._build_menu_item(
                "Video", self.dropmenu_inputs,
                callback=self.current_app.feed.controls.video_menu.on_video_input_clicked
        )
        # Outputs_____________________________________________________
        self.subitem_outputs = self._build_menu_item(
            "Outputs", self.dropmenu_feed
        )
        # Submenu outputs
        self.dropmenu_outputs = Gtk.Menu()
        self.subitem_outputs.set_submenu(self.dropmenu_outputs)
        self.subitem_stream = self._build_menu_item(
                "Stream", self.dropmenu_outputs,
                callback=self.current_app.feed.controls.stream_menu.on_stream_clicked
        )
        self.subitem_store = self._build_menu_item(
                "Store", self.dropmenu_outputs,
                callback=self.current_app.feed.controls.store_menu.on_store_clicked
        )
        self._build_separatormenuitem(self.dropmenu_feed)
        self.subitem_info = self._build_menu_item(
                "Info", self.dropmenu_feed,
                callback=self.current_app.feed.controls.info_menu.on_info_clicked
        )

        return menu_item

    def _build_menu_view(self, menu_bar):
        """
        Build the whole View menu item.
        """
        menu_item = self._build_menu_item("View", menu_bar)
        self.dropmenu_view = Gtk.Menu()
        menu_item.set_submenu(self.dropmenu_view)
        # Modes_______________________________________________________
        self.subitem_mode = self._build_menu_item(
            "Mode", self.dropmenu_view
        )
        self.dropmenu_mode = Gtk.Menu()
        self.subitem_mode.set_submenu(self.dropmenu_mode)
        self.subradioitem_standalone = self._build_radiomenuitem(
            "Standalone",
            self.dropmenu_mode,
            set_active=True,
            on_signal="activate",
            callback=self.on_standalone_mode
        )
        current_view_mode = self.subradioitem_standalone
        self.subradioitem_controlroom = self._build_radiomenuitem(
            "Control Room",
            self.dropmenu_mode,
            group=self.subradioitem_standalone,
            on_signal="activate",
            callback=self.on_controlroom_mode
        )
        self.subradioitem_monitoring = self._build_radiomenuitem(
            "Monitoring",
            self.dropmenu_mode,
            group=self.subradioitem_standalone,
            on_signal="activate",
            callback=self.on_monitoring_mode
        )

        return menu_item, current_view_mode

    def _build_menu_help(self, menu_bar):
        """
        Build the whole Help menu item.
        """
        menu_item = self._build_menu_item("Help", menu_bar)
        # TODO:
        # Implement About dialogbox
        # Implement documentation
        # Implement tutorial ?

        return menu_item

    def _build_menu_item(self, name, menu,
                         image=None,
                         on_signal="activate",
                         callback=None):
        """
        """
        menu_item = Gtk.MenuItem()
        if image:
            hbox = Gtk.Box(Gtk.Orientation.HORIZONTAL)
            icon = Gtk.Image.new_from_icon_name(image, 1)
            label = Gtk.Label(name)
            # accelerator = ?
            _pack_widgets(hbox, icon, label)
            menu_item.add(hbox)
            # use pack_end() to add an accelerator in a menu item with an image
        else:
            menu_item.set_label(name)

        if callback:
            menu_item.connect(on_signal, callback)

        menu.append(menu_item)
        return menu_item

    def _build_radiomenuitem(self, name, menu,
                             group=None,
                             set_active=False,
                             on_signal="toggled",
                             callback=None):
        """
        """
        menu_item = Gtk.RadioMenuItem(name, group=group)
        menu_item.set_active(set_active)

        if callback:
            menu_item.connect(on_signal, callback)

        menu.append(menu_item)
        return menu_item

    def _build_separatormenuitem(self, menu):
        _separator = Gtk.SeparatorMenuItem()
        menu.append(_separator)

    def _build_separator(self, orientation=0):
        if orientation == 0:
            return Gtk.Separator(Gtk.Orientation.HORIZONTAL)
        elif orientation == 1:
            return Gtk.Separator(Gtk.Orientation.VERTICAL)
        else:
            raise ValueError

    def change_application(self, new_application, new_application_container):
        """
        """
        # IMPORTANT / FIXME:
        # Application change won't take place as long as BaseApp is initiated
        # in MainWindow constructor

        if isinstance(new_application, type(self.current_app)):
            #new_application.__del__()
            print("New instance deleted")  # DEBUG
            return

        self.main_vbox.remove(self.current_app_container)
        self.current_app = new_application
        self.current_app_container = new_application_container
        # TODO: improve packing routine
        self.main_vbox.pack_end(self.current_app_container, False, False, 0)
        self.main_vbox.show_all()
        print("New instance added to main window")  # DEBUG

    def on_menu_item_new_activate(self, widget):
        pass

    def on_standalone_mode(self, widget):
        """
        Callback launching standalone mode.
        """
        if not widget.get_active():
            return
        if self.current_view_mode == self.subradioitem_standalone:
            return

        standalone_app = self.current_app._display_confirmation_message(
                "standalone", StandaloneApp)
        self.change_application(standalone_app, standalone_app.new_feed_vbox)
        self.current_view_mode = self.subradioitem_standalone

    def on_controlroom_mode(self, widget):
        """
        Callback launching controlroom mode.
        """
        if not widget.get_active():
            return
        if self.current_view_mode == self.subradioitem_controlroom:
            return

        controlroom_app = self.current_app._display_confirmation_message(
            "control room", ControlRoomApp)
        self.change_application(controlroom_app, controlroom_app.container)
        self.current_view_mode = self.subradioitem_controlroom

    def on_monitoring_mode(self, widget):
        """
        Callback launching monitoring mode.
        """
        if not widget.get_active():
            return
        if self.current_view_mode == self.subradioitem_monitoring:
            return

        monitoring_app = self.current_app._display_confirmation_message(
            "monitoring", MonitoringApp)
        self.change_application(monitoring_app, monitoring_app.new_feed_vbox)
        self.current_view_mode = self.subradioitem_monitoring


class BaseApp:
    """
    Base application class.
    """
    def __init__(self, main_window, mode):
        self.main_window = main_window
        self.feed = feed.NewFeed(mode)
        self.container = self.feed.hbox

    def make_app(self):  # DEBUG
        # DEBUG SECTION______________________________________________
        # We need to show the widgets before trying to attach video
        # feed to the main window

        # Microphone init
        audio_devices = iofetch.find_audio()
        for key in audio_devices:
            # Get the built-in microphone
            if audio_devices[key]["type"] == "input" and "hdmi" not in key:
                a_device = key
                break
        microphone = ioelements.AudioInput("Empty description", a_device)
#        self.feed.pipeline.set_input_source(microphone)

        # Camera init
        usbcam_devices = iofetch.find_usbcam()
        #if len(usbcam_devices) > 1:
        for key in usbcam_devices:
            # Try not to get built-in usb cam
            if usbcam_devices[key]["description"] != "TOSHIBA Web Camera":
                v_device = key
                break
        else:
            # Built-in camera
            v_device = key

        usbcam = ioelements.VideoInput("Empty description",
                                       "usb",
                                       v_device,)
        #self.feed.pipeline.set_input_source(usbcam)

        # Get Window ID
        self.feed.set_xid()
        # Set placeholder pipeline in play mode
        self.feed.placeholder_pipeline.set_play_state()
        # Pipeline in play mode
        #self.feed.pipeline.set_play_state()  # DEBUG

        # SECTION END________________________________________________

    def _display_confirmation_message(self, new_mode, app):
        """
        Display a popup message to confirm the mode switch.
        """
        text = "Switching to " + new_mode + " mode will end current stream."
        messagebox = Gtk.MessageDialog(
            buttons=Gtk.ButtonsType.OK_CANCEL,
            message_type=Gtk.MessageType.WARNING,
            message_format=text
        )
        messagebox.set_title("Confirmation")

        try:
            response = messagebox.run()
            if response == Gtk.ResponseType.OK:
                application = app()
        finally:
            messagebox.destroy()
            return application


class ControlRoomApp(BaseApp):
    """
    Window settings for multi-feed display.
    """
    def __init__(self):
        self.placeholder_image = Gtk.Image.new_from_icon_name(
            Gtk.STOCK_NEW, Gtk.IconSize.DIALOG)
        self.new_feed_button = Gtk.Button("New Feed")

        self.new_feed_vbox = Gtk.Box(Gtk.Orientation.VERTICAL)
        self.new_feed_vbox.set_halign(Gtk.Align.CENTER)
        self.new_feed_vbox.set_valign(Gtk.Align.CENTER)
        _pack_widgets(self.new_feed_vbox,
                      self.placeholder_image,
                      self.new_feed_button)

        self._grid = Gtk.Grid()
        self._grid.set_row_homogeneous(True)
        self._grid.set_column_homogeneous(True)
        self._grid.attach(self.new_feed_vbox, 0, 0, 1, 1)
        self._grid.attach(Gtk.Label("FEED ELEMENT DEBUG1"), 1, 0, 1, 1)  # DEBUG
        self._grid.attach(Gtk.Label("FEED ELEMENT DEBUG2"), 0, 1, 1, 1)  # DEBUG
        self._grid.attach(Gtk.Label("FEED ELEMENT DEBUG3"), 1, 1, 1, 1)  # DEBUG
        self._grid.show_all()

        self.container = self._grid


class StandaloneApp(BaseApp):
    """
    Window settings for one feed display.
    """
    def __init__(self):
        self.placeholder_image = Gtk.Image.new_from_icon_name(
            Gtk.STOCK_MEDIA_PLAY, Gtk.IconSize.DIALOG)
        self.new_feed_button = Gtk.Button("New Feed")

        self.new_feed_vbox = Gtk.Box(Gtk.Orientation.VERTICAL)
        self.new_feed_vbox.set_halign(Gtk.Align.CENTER)
        self.new_feed_vbox.set_valign(Gtk.Align.CENTER)
        _pack_widgets(self.new_feed_vbox,
                      self.placeholder_image,
                      self.new_feed_button)


class MonitoringApp(BaseApp):
    """
    Window settings for monitoring one feed that is sent to a ControlRoom
    HUBAngl instance.
    """
    def __init__(self):
        self.placeholder_image = Gtk.Image.new_from_icon_name(
            Gtk.STOCK_NEW, Gtk.IconSize.DIALOG)
        self.new_feed_button = Gtk.Button("New Feed")

        self.new_feed_vbox = Gtk.Box(Gtk.Orientation.VERTICAL)
        self.new_feed_vbox.set_halign(Gtk.Align.CENTER)
        self.new_feed_vbox.set_valign(Gtk.Align.CENTER)
        _pack_widgets(self.new_feed_vbox,
                      self.placeholder_image,
                      self.new_feed_button)


if __name__ == "__main__":
    from gi.repository import Gst
    Gst.init()

    MainWindow()
    Gtk.main()
