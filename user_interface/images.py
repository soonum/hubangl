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
                               "activated": None},
                      "pause": {"regular": None,
                               "activated": None},
                      "stop": {"regular": None,
                               "activated": None},
                      "camera": {"regular": None,
                                 "activated": None},
                      "micro": {"regular": None,
                              "activated": None},
                      "streaming": {"regular": None,
                                    "activated": None},
                      "storage": {"regular": None,
                                  "activated": None},
                      "info": {"regular": None,
                               "activated": None},
                      "speaker": {"regular": None,
                                  "activated": None},
                      "chat": {"regular": None,
                               "activated": None},
                      "slides": {"regular": None,
                                 "activated": None},
        }

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
                    if "_or_" in filename:  # TODO: use better filename for activated version
                        self.icons[key]["activated"] = icon
                    else:
                        self.icons[key]["regular"] = icon

    def load_logos(self):
        """
        Load logos used as images and as favicon.
        """
        self.logo_512_px = None
        self.logo_256_px = None
        self.logo_favicon = None

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

    def _create_image(self):
        """
        Create
        """
