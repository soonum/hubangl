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

import json
import pathlib

from gi.repository import Gtk
from gi.repository import Gdk

from user_interface import feed
from user_interface import images


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
        self.images = images.HubanglImages()
        self._load_custom_css()

        self.window = Gtk.Window()
        self.window.set_title("HUBAngl")
        #self.window.connect("delete_event", lambda w, e: Gtk.main_quit())
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.set_icon_from_file(self.images.logo_favicon_path)
        self.window.connect("delete_event", self.on_mainwindow_close)

        if default_app:
            self.current_app = default_app
        else:
            self.current_app = BaseApp(self.window, "standalone", self.images)
            self.current_app_container = self.current_app.container

        self.menu_bar = Gtk.MenuBar()
        self.menu_item_new = self._build_menu_new(self.menu_bar)
        self.menu_item_feed = self._build_menu_feed(self.menu_bar)
        self.menu_item_view, self.current_view_mode = self._build_menu_view(
                self.menu_bar
        )
        self.menu_item_help = self._build_menu_help(self.menu_bar)

        self.main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_vbox.pack_start(self.menu_bar, False, False, 0)
        self.main_vbox.pack_end(self.current_app_container, True, True, 0)

        self.window.add(self.main_vbox)
        self.window.show_all()

        self.current_app.make_app()

    def _load_custom_css(self):
        css_filepath = pathlib.Path(__file__).parent.joinpath("gui_style.css")
        with css_filepath.open("rb") as css_file:
            css_data = css_file.read()

        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css_data)

        Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(), style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

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
        self.subitem_save_configuration = self._build_menu_item(
            "Save configuration", self.dropmenu_new,
            image=Gtk.STOCK_SAVE, callback=self.on_save_clicked
        )
        self.subitem_load_configuration = self._build_menu_item(
            "Load Configuration", self.dropmenu_new,
            image=Gtk.STOCK_FILE, callback=self.on_load_clicked
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
                image=self.images.icons["play"]["regular_16px"],
                callback=self.on_play_clicked
        )
        self.subitem_stop = self._build_menu_item(
                "Stop", self.dropmenu_feed,
                image=self.images.icons["stop"]["regular_16px"],
                callback=self.on_stop_clicked
        )
        self._build_separatormenuitem(self.dropmenu_feed)

        # Inputs
        self.subitem_inputs = self._build_menu_item(
            "Inputs", self.dropmenu_feed
        )
        # Submenu Inputs
        self.dropmenu_inputs = Gtk.Menu()
        self.subitem_inputs.set_submenu(self.dropmenu_inputs)
        self.subitem_audio = self._build_menu_item(
                "Audio", self.dropmenu_inputs,
                image=self.images.icons["micro"]["regular_16px"],
                callback=self.on_audio_input_clicked
        )
        self.subitem_video = self._build_menu_item(
                "Video", self.dropmenu_inputs,
                image=self.images.icons["camera"]["regular_16px"],
                callback=self.on_video_input_clicked
        )

        # Outputs
        self.subitem_outputs = self._build_menu_item(
            "Outputs", self.dropmenu_feed
        )
        # Submenu outputs
        self.dropmenu_outputs = Gtk.Menu()
        self.subitem_outputs.set_submenu(self.dropmenu_outputs)
        self.subitem_stream = self._build_menu_item(
                "Stream", self.dropmenu_outputs,
                image=self.images.icons["streaming"]["regular_16px"],
                callback=self.on_stream_clicked
        )
        self.subitem_store = self._build_menu_item(
                "Store", self.dropmenu_outputs,
                image=self.images.icons["storage"]["regular_16px"],
                callback=self.on_store_clicked
        )
        self._build_separatormenuitem(self.dropmenu_feed)
        self.subitem_info = self._build_menu_item(
                "Info", self.dropmenu_feed,
                image=self.images.icons["settings"]["regular_16px"],
                callback=self.on_settings_clicked
        )

        return menu_item

    def _build_menu_view(self, menu_bar):
        """
        Build the whole View menu item.
        """
        menu_item = self._build_menu_item("View", menu_bar)
        self.dropmenu_view = Gtk.Menu()
        menu_item.set_submenu(self.dropmenu_view)

        # Modes
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
        self.subradioitem_controlroom = self._build_radiomenuitem(
            "Control Room (soon)",
            self.dropmenu_mode,
            group=self.subradioitem_standalone,
            on_signal="activate",
            callback=self.on_controlroom_mode
        )
        self.subradioitem_monitoring = self._build_radiomenuitem(
            "Monitoring (soon)",
            self.dropmenu_mode,
            group=self.subradioitem_standalone,
            on_signal="activate",
            callback=self.on_monitoring_mode
        )

        current_view_mode = self.subradioitem_standalone
        self.subradioitem_controlroom.set_sensitive(False)  # DEV
        self.subradioitem_monitoring.set_sensitive(False)  # DEV

        return menu_item, current_view_mode

    def _build_menu_help(self, menu_bar):
        """
        Build the whole Help menu item.
        """
        menu_item = self._build_menu_item("Help", menu_bar)
        # TODO:
        # Implement About dialogbox
        # Implement documentation
        # Implement possible tutorial

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
            try:
                icon = Gtk.Image.new_from_icon_name(image, 1)
            except TypeError:
                # ``image`` is a Gtk.Image already loaded.
                icon = image
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

    def build_confirm_dialog(self, message_type, message_label,
                             on_signal=None, callback=None):
        """
        Create a :class:`Gtk.MessageDialog` asking user for confirmation.

        :param message_type: :class:`Gtk.MessageType`
        :param message_label: text displayed to user as :class`str`
        :param on_signal: Gtk signal as :class:`str`
        :param callback: callback to connect to ``signal``
        """
        confirm_dialog = Gtk.MessageDialog(
            message_type=message_type, message_format=message_label)
        confirm_dialog.set_icon_from_file(self.images.logo_favicon_path)
        confirm_dialog.set_title("Confirmation")
        confirm_dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        confirm_dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT)
        confirm_dialog.set_modal(True)
        if on_signal and callback:
            confirm_dialog.connect(on_signal, callback)

        confirm_dialog.run()

    def build_error_dialog(self, message_label, on_signal=None, callback=None):
        """
        Create a :class:`Gtk.MessageDialog` to notifiy user that an error
        occurred.

        :param message_label: text displayed to user as :class`str`
        :param on_signal: Gtk signal as :class:`str`
        :param callback: callback to connect to ``signal``
        """
        error_dialog = Gtk.MessageDialog(
            message_type=Gtk.MessageType.ERROR, message_format=message_label)
        error_dialog.set_icon_from_file(self.images.logo_favicon_path)
        error_dialog.set_title("Error")
        error_dialog.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        error_dialog.set_modal(True)
        if on_signal and callback:
            error_dialog.connect(on_signal, callback)
        else:
            error_dialog.connect("response", self.default_error_callback)

        error_dialog.run()

    def default_error_callback(self, dialog, response_id):
        """
        Default callback called when there is no callback provided to
        :meth:`build_error_dialog`.
        """
        if (response_id == Gtk.ResponseType.CLOSE
                or response_id == Gtk.ResponseType.DELETE_EVENT):
            dialog.destroy()

    def change_application(self, new_application, new_application_container):
        """
        """
        # IMPORTANT / FIXME:
        # Application change won't take place as long as BaseApp is initiated
        # in MainWindow constructor

        if isinstance(new_application, type(self.current_app)):
            #new_application.__del__()
            return

        self.main_vbox.remove(self.current_app_container)
        self.current_app = new_application
        self.current_app_container = new_application_container
        # TODO: improve packing routine
        self.main_vbox.pack_end(self.current_app_container, False, False, 0)
        self.main_vbox.show_all()

    def on_mainwindow_close(self, *args):
        self.current_app.feed.placeholder_pipeline.set_stop_state()
        self.current_app.feed.pipeline.close()
        Gtk.main_quit()

    def on_save_clicked(self, widget):
        file_save_dialog = Gtk.FileChooserDialog(
                title="Save Session",
                action=Gtk.FileChooserAction.SAVE,
                buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT)
        )
        file_save_dialog.set_icon_from_file(self.images.logo_favicon_path)
        file_save_dialog.set_current_name("Untilted.huba")
        file_save_dialog.set_do_overwrite_confirmation(True)
        file_save_dialog.set_modal(True)
        file_save_dialog.connect("response", self.on_save_response)
        file_save_dialog.run()

    def on_save_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.ACCEPT:
            file_saved = dialog.get_filename()
            if ".huba" not in file_saved:
                file_saved += ".huba"
            self.session_properties = self.current_app.feed.gather_properties()
            with open(file_saved, "w") as f:
                json.dump(self.session_properties, f)

        dialog.destroy()

    def on_load_clicked(self, widget):
        file_load_dialog = Gtk.FileChooserDialog(
                title="Load Session",
                action=Gtk.FileChooserAction.OPEN,
                buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT)
        )
        file_load_dialog.set_icon_from_file(self.images.logo_favicon_path)
        file_load_dialog.set_modal(True)
        file_load_dialog.connect("response", self.on_load_response)
        file_load_dialog.run()

    def on_load_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.ACCEPT:
            confirmation_message = "Current settings will be overwritten."
            self.build_confirm_dialog(
                    Gtk.MessageType.WARNING, confirmation_message,
                    on_signal="response", callback=self.on_load_confirmation)
            if self.load_confirmed:
                file_to_load = dialog.get_filename()
                with open(file_to_load) as f:
                    try:
                        loaded_session = json.load(f)
                        self.current_app.feed.spread_properties(
                                **loaded_session)
                    except ValueError:
                        message = "An error occurred during file decoding."
                        self.build_error_dialog(message)
                    except Exception:
                        # An error occurred while setting properties
                        message = "An error occurred during file loading."
                        self.build_error_dialog(message)
                        raise

        dialog.destroy()

    def on_load_confirmation(self, dialog, response_id):
        if response_id == Gtk.ResponseType.ACCEPT:
            self.load_confirmed = True
        elif (response_id == Gtk.ResponseType.CANCEL
              or response_id == Gtk.ResponseType.DELETE_EVENT):
            self.load_confirmed = False

        dialog.destroy()

    def on_play_clicked(self, widget):
        if not self.current_app.feed.controls.play_button.get_sensitive():
            return

        self.current_app.feed.controls.on_play_clicked(
                self.current_app.feed.controls.play_button)

    def on_stop_clicked(self, widget):
        if not self.current_app.feed.controls.stop_button.get_sensitive():
            return

        self.current_app.feed.controls.on_stop_clicked(
                self.current_app.feed.controls.stop_button)

    def on_video_input_clicked(self, widget):
        self.current_app.feed.controls.on_video_clicked(
                self.current_app.feed.controls.video_button)

    def on_audio_input_clicked(self, widget):
        self.current_app.feed.controls.on_audio_clicked(
                self.current_app.feed.controls.audio_button)

    def on_stream_clicked(self, widget):
        self.current_app.feed.controls.on_stream_clicked(
                self.current_app.feed.controls.stream_button)

    def on_store_clicked(self, widget):
        self.current_app.feed.controls.on_store_clicked(
                self.current_app.feed.controls.store_button)

    def on_settings_clicked(self, widget):
        self.current_app.feed.controls.on_settings_clicked(
                self.current_app.feed.controls.settings_button)

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
    def __init__(self, main_window, mode, images):
        self.main_window = main_window
        self.feed = feed.NewFeed(mode, images)
        self.container = self.feed.hbox

    def make_app(self):  # DEBUG
        # Get Window ID
        self.feed.set_xid()
        # Set placeholder pipeline in play mode
        self.feed.placeholder_pipeline.set_play_state()

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
