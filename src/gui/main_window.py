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

import json
import logging
import pathlib

from gi.repository import Gtk
from gi.repository import Gdk

from gui import feed
from gui import images
from gui import status_bar
from gui import utils


logger = logging.getLogger("gui.main_window")


class MainWindow:
    """
    Graphical user interface main window.

    :param options: input arguments as :class:`argparse.Namespace`
    """
    def __init__(self, options, *args, **kwargs):
        #: Filename of a session to load
        self.session = options.load

        self.images = images.HubanglImages()
        self._load_custom_css()

        self.accel_group = Gtk.AccelGroup()

        self.window = Gtk.Window()
        self.window.set_title("HUBAngl")
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.set_icon_from_file(self.images.logo_favicon_path)
        self.window.connect("delete_event", self.on_mainwindow_close)
        self.window.add_accel_group(self.accel_group)
        utils.set_main_window(self.window)

        self.feed = feed.Feed(self.images)

        self.menu_bar = Gtk.MenuBar()
        self.menu_item_file = self._build_menu_file(self.menu_bar)
        self.menu_item_feed = self._build_menu_feed(self.menu_bar)
        self.menu_item_help = self._build_menu_help(self.menu_bar)

        self.status_bar = status_bar.get_status_bar()

        self.main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_vbox.pack_start(self.menu_bar, False, False, 0)
        self.main_vbox.pack_end(self.status_bar.container, False, False, 0)
        self.main_vbox.pack_end(self.feed.hbox, True, True, 0)

        self.window.add(self.main_vbox)
        self.window.show_all()

        # Get Window ID
        self.feed.set_xid()

        self.feed.placeholder_pipeline.set_play_state()

        if self.session:
            self.load_session(self.session)

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

    def _build_menu_file(self, menu_bar):
        """
        Build the whole File menu item.
        """
        menu_item = self._build_menu_item("File", menu_bar)
        self.dropmenu_file = Gtk.Menu()
        menu_item.set_submenu(self.dropmenu_file)
        self.subitem_new_session = self._build_menu_item(
            "New Session", self.dropmenu_file,
            image=Gtk.STOCK_NEW,
            accelerator_key="<control>N"
        )
        self.subitem_save_configuration = self._build_menu_item(
            "Save configuration", self.dropmenu_file,
            image=Gtk.STOCK_SAVE, callback=self.on_save_clicked,
            accelerator_key="<control>S"
        )
        self.subitem_load_configuration = self._build_menu_item(
            "Load Configuration", self.dropmenu_file,
            image=Gtk.STOCK_FILE, callback=self.on_load_clicked,
            accelerator_key="<control>L"
        )
        self.subitem_recent_session = self._build_menu_item(
            "Recent Session", self.dropmenu_file,
            image=Gtk.STOCK_REVERT_TO_SAVED
        )
        self.subitem_preferences = self._build_menu_item(
            "Preferences", self.dropmenu_file,
            image=Gtk.STOCK_PREFERENCES,
            accelerator_key="<control>R"
        )
        self._build_separatormenuitem(self.dropmenu_file)
        self.subitem_quit = self._build_menu_item(
            "Quit", self.dropmenu_file,
            image=Gtk.STOCK_QUIT, callback=self.on_mainwindow_close,
            accelerator_key="<control>Q"
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
                callback=self.on_play_clicked,
                accelerator_key="<alt>P"
        )
        self.subitem_stop = self._build_menu_item(
                "Stop", self.dropmenu_feed,
                image=self.images.icons["stop"]["regular_16px"],
                callback=self.on_stop_clicked,
                accelerator_key="<alt>S"
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
                callback=self.on_audio_input_clicked,
                accelerator_key="<alt>U"
        )
        self.subitem_video = self._build_menu_item(
                "Video", self.dropmenu_inputs,
                image=self.images.icons["camera"]["regular_16px"],
                callback=self.on_video_input_clicked,
                accelerator_key="<alt>V"
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
                callback=self.on_stream_clicked,
                accelerator_key="<alt>R"
        )
        self.subitem_store = self._build_menu_item(
                "Store", self.dropmenu_outputs,
                image=self.images.icons["storage"]["regular_16px"],
                callback=self.on_store_clicked,
                accelerator_key="<alt>O"
        )
        self._build_separatormenuitem(self.dropmenu_feed)
        self.subitem_info = self._build_menu_item(
                "Info", self.dropmenu_feed,
                image=self.images.icons["settings"]["regular_16px"],
                callback=self.on_settings_clicked,
                accelerator_key="<alt>G"
        )

        return menu_item

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
                         image=None, on_signal="activate", callback=None,
                         accelerator_key=None):
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
            utils.pack_widgets(hbox, icon, label)
            menu_item.add(hbox)
        else:
            menu_item.set_label(name)

        if callback:
            menu_item.connect(on_signal, callback)

        if accelerator_key:
            key, modifier = Gtk.accelerator_parse(accelerator_key)
            menu_item.add_accelerator("activate", self.accel_group,
                                      key, modifier, Gtk.AccelFlags.VISIBLE)
            accel_label = Gtk.AccelLabel()
            accel_label.set_accel_widget(menu_item)
            hbox.pack_end(accel_label, True, True, 0)

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

    def on_mainwindow_close(self, *args):
        self.feed.placeholder_pipeline.set_stop_state()
        self.feed.pipeline.close()
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
        file_save_dialog.set_transient_for(self.window)
        file_save_dialog.connect("response", self.on_save_response)
        file_save_dialog.run()

    def on_save_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.ACCEPT:
            file_saved = dialog.get_filename()
            if ".huba" not in file_saved:
                file_saved += ".huba"
            self.session_properties = self.feed.gather_properties()
            with open(file_saved, "w") as f:
                json.dump(self.session_properties, f, indent="\t")

            logger.info("Session configuration saved to %s" % file_saved)

        dialog.destroy()

    def load_session(self, filepath):
        """
        Load a *.huba file as a session.

        :param filepath: path to session file as :class:`str`
        """
        with open(filepath) as f:
            try:
                loaded_session = json.load(f)
                self.feed.spread_properties(**loaded_session)
            except ValueError:
                message = "An error occurred during file decoding."
                utils.build_error_dialog(message)
            except Exception:
                # An error occurred while setting properties
                logger.exception("Unexpected error occurred during file loading")
                message = "An error occurred during file loading."
                utils.build_error_dialog(message)
            else:
                logger.info("Session configuration loaded from %s" % filepath)

    def _need_load_confirmation(self):
        """
        Determine if a user confirmation is needed before loading a session.

        :return: ``True`` if a confirmation is needed, ``False`` otherwise
        """
        if not self.feed.placeholder_pipeline.is_playing:
            stream_sinks = self.feed.pipeline.stream_sinks
            store_sinks = self.feed.pipeline.store_sinks
            for streamstore_elements in (stream_sinks, store_sinks):
                for feed_type in streamstore_elements:
                    # This is the placeholder pipeline but an output sinks has
                    # already been set, the settings will be lost in case of
                    # session loading, we need to ask a confirmation from user.
                    return True
            else:
                return False

    def on_load_clicked(self, widget):
        file_load_dialog = Gtk.FileChooserDialog(
                title="Load Session",
                action=Gtk.FileChooserAction.OPEN,
                buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT)
        )
        file_load_dialog.set_icon_from_file(self.images.logo_favicon_path)
        file_load_dialog.set_modal(True)
        file_load_dialog.set_transient_for(self.window)
        file_load_dialog.connect("response", self.on_load_response)
        file_load_dialog.run()

    def on_load_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.ACCEPT:
            confirmation_message = "Current settings will be overwritten."
            if self._need_load_confirmation():
                utils.build_confirm_dialog(Gtk.MessageType.WARNING,
                                           confirmation_message,
                                           on_signal="response",
                                           callback=self.on_load_confirmation)
            else:
                self.load_confirmed = True

            if self.load_confirmed:
                file_to_load = dialog.get_filename()
                self.load_session(file_to_load)

        dialog.destroy()

    def on_load_confirmation(self, dialog, response_id):
        if response_id == Gtk.ResponseType.ACCEPT:
            self.load_confirmed = True
        elif (response_id == Gtk.ResponseType.CANCEL
              or response_id == Gtk.ResponseType.DELETE_EVENT):
            self.load_confirmed = False

        dialog.destroy()

    def on_play_clicked(self, widget):
        if not self.feed.controls.play_button.get_sensitive():
            return

        self.feed.controls.on_play_clicked(
                self.feed.controls.play_button)

    def on_stop_clicked(self, widget):
        if not self.feed.controls.stop_button.get_sensitive():
            return

        self.feed.controls.on_stop_clicked(
                self.feed.controls.stop_button)

    def on_video_input_clicked(self, widget):
        self.feed.video_menu.on_video_input_clicked(widget)

    def on_audio_input_clicked(self, widget):
        self.feed.audio_menu.on_audio_input_clicked(widget)

    def on_stream_clicked(self, widget):
        self.feed.stream_menu.on_stream_clicked(widget)

    def on_store_clicked(self, widget):
        self.feed.store_menu.on_store_clicked(widget)

    def on_settings_clicked(self, widget):
        self.feed.settings_menu.on_settings_clicked(widget)

    def on_menu_item_file_activate(self, widget):
        pass
