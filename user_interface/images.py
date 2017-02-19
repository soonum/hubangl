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

import pathlib

from gi.repository import Gtk


class HubanglImages:
    def __init__(self):
        self.artwork_path = self.get_artwork_path()
        self.icons = {"play": {"regular": None,
                               "regular_16px": None,
                               "activated": None},
                      "stop": {"regular": None,
                               "regular_16px": None,
                               "activated": None},
                      "camera": {"regular": None,
                                 "regular_16px": None,
                                 "activated": None,
                                 "striked": None},
                      "micro": {"regular": None,
                                "regular_16px": None,
                                "activated": None,
                                "striked": None},
                      "streaming": {"regular": None,
                                    "regular_16px": None,
                                    "activated": None},
                      "storage": {"regular": None,
                                  "regular_16px": None,
                                  "activated": None},
                      "settings": {"regular": None,
                                   "regular_16px": None,
                                   "activated": None},
                      "speaker": {"regular": None,
                                  "activated": None,
                                  "striked": None},
                      "chat": {"regular": None,
                               "regular_16px": None,
                               "activated": None},
                      "slides": {"regular": None,
                                 "regular_16px": None,
                                 "activated": None},
        }
        self.load_icons()
        self.load_logos()

    def get_artwork_path(self):
        root = pathlib.Path(__file__).parents[1]
        artwork_path = root.joinpath("artwork")
        if not artwork_path.is_dir():
            raise Exception.FileNotFoundError
        return artwork_path

    def load_icons(self):
        """
        Load all icons used for buttons.
        """
        for icon_path in self.artwork_path.iterdir():
            for key in self.icons:
                filename = icon_path.name.lower()
                if key in filename:
                    icon = Gtk.Image()
                    icon.set_from_file(icon_path.as_posix())
                    if ("_activated_" in filename
                            and "_striked_" not in filename):
                        self.icons[key]["activated"] = icon
                    elif "_striked_" in filename:
                        self.icons[key]["striked"] = icon
                    elif "_16-16_" in filename:
                        self.icons[key]["regular_16px"] = icon
                    else:
                        self.icons[key]["regular"] = icon

    def load_logos(self):
        """
        Load logos used as images and as favicon.
        """
        for logo_path in self.artwork_path.iterdir():
            filename = logo_path.name.lower()
            if "_logo_" in filename and "_512-512_" in filename:
                self.logo_512_px = Gtk.Image()
                self.logo_512_px.set_from_file(logo_path.as_posix())
            elif "_logo_" in filename and "_256-256_" in filename:
                self.logo_256_px = Gtk.Image()
                self.logo_256_px_path = logo_path.as_posix()
                self.logo_256_px.set_from_file(self.logo_256_px_path)
            elif "_logo_" in filename and "_16-16_" in filename:
                self.logo_favicon = Gtk.Image()
                self.logo_favicon_path = logo_path.as_posix()
                self.logo_favicon.set_from_file(self.logo_favicon_path)

    def get_activated_icon(self, icon_id):
        """
        Return a :class:`Gtk.Image` containing the activated version of ``icon``.

        :param icon_id: id of the icon

        :return: :class:`Gtk.Image` or ``None``
        """
        icon_values = self.icons.get(icon_id, None)
        if not icon_values:
            return

        return icon_values["activated"]

    def get_regular_icon(self, icon_id):
        """
        Return a :class:`Gtk.Image` containing the regular version of ``icon``.

        :param icon_id: id of the icon

        :return: :class:`Gtk.Image` or ``None``
        """
        icon_values = self.icons.get(icon_id, None)
        if not icon_values:
            return

        return icon_values["regular"]

    def switch_icon_version(self, icon_id, current_icon):
        """
        Switch version of ``icon``.

        :param icon_id: id of the icon

        :return: :class:`Gtk.Image` or ``None``
        """
        icon_values = self.icons.get(icon_id, None)
        if not icon_values:
            return

        if current_icon is icon_values["regular"]:
            return icon_values["activated"]
        elif current_icon is icon_values["activated"]:
            return icon_values["regular"]
