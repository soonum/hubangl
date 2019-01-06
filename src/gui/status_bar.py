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

from gi.repository import Gtk

from gui import images


class StatusBar:
    """
    Give information about the status of watched elements via
    :mod:`~core.watch`.
    """
    def __init__(self):
        self._images = images.HubanglImages()
        self._stream_icon = self._images.icons["streaming"]["regular_16px"]
        self._store_icon = self._images.icons["storage"]["regular_16px"]

        self._elements = set()

        (self.container,
         self._hbox_remote,
         self._hbox_local) = self._build_status_bar()

    def _build_status_bar(self):
        hbox_main = Gtk.Box()
        hbox_remote = self._build_watching_box(self._stream_icon)
        hbox_local = self._build_watching_box(self._store_icon)
        separator = Gtk.VSeparator()

        for widget in (hbox_local, separator, hbox_remote):
            hbox_main.pack_end(widget, False, False, 6)

        return hbox_main, hbox_remote, hbox_local

    def _build_watching_box(self, image):
        hbox = Gtk.Box()
        hbox.pack_start(image, False, False, 6)
        # Hide the box until a watched element is added into it
        hbox.set_no_show_all(True)
        return hbox

    def get_watched_element(self, element):
        for watched_element in self._elements:
            if element is watched_element.element:
                return watched_element

    def add_local_element(self, element):
        """
        """
        watched_element = WatchedLocal(element)
        self._add_watched_element(self._hbox_local, watched_element)

    def add_remote_element(self, element):
        """
        """
        watched_element = WatchedRemote(element)
        self._add_watched_element(self._hbox_remote, watched_element)

    def _add_watched_element(self, box, watched_element):
        # Keeping a reference is needed to handle its callbacks properly
        self._elements.add(watched_element)
        box.pack_start(watched_element.button, True, True, 3)

        if box.get_no_show_all():
            box.set_no_show_all(False)
        box.show_all()

    def remove_local_element(self, element):
        """
        """
        self._remove_watched_element(self._hbox_local, element)

    def remove_remote_element(self, element):
        """
        """
        self._remove_watched_element(self._hbox_remote, element)

    def _remove_watched_element(self, box, element):
        watched_element = self.get_watched_element(element)
        if not watched_element:
            return

        box.remove(watched_element.button)
        if len(box.get_children()) == 1:
            # The icon is the only remaining widget, there is no need to
            # display the box.
            box.hide()

        self._elements.remove(watched_element)


class WatchedElement:
    def __init__(self, element):
        self.element = element
        self.button = self._build_color_button()

    def _build_color_button(self):
        button = Gtk.Button()
        button.connect("clicked", self._on_clicked)
        # DEV note: Ajouter une image à ce bouton (un cercle vert et un switch en cercle rouge)
        # DEV note: retirer le relief du bouton une fois l'image ajoutée

        return button

    def _on_clicked(self, widget):
        self.info_popover.set_relative_to(widget)
        self.info_popover.show_all()

    @abc.abstractmethod
    def _build_info_popover(self):
        """
        Build a popover for this watched element
        """

    def _build_subbox(self, label, value):
        """
        Build an horizontal box meant to be packed in a packed in a popover

        :param label: :class:`Gtk.Widget` to display at the left of the box
        :param value: :class:`Gtk.Widget` to display at the right of the box
        """
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(label, False, False, 6)
        box.pack_end(value, False, False, 6)
        return box


class WatchedLocal(WatchedElement):
    """
    """
    def __init__(self, element):
        super().__init__(element)
        self.info_popover = self._build_info_popover()

    def _build_info_popover(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        popover = Gtk.Popover()
        popover.add(vbox)
        popover.set_position(Gtk.PositionType.TOP)

        return popover


class WatchedRemote(WatchedElement):
    """
    """
    def __init__(self, element):
        super().__init__(element)

        self._hostname = Gtk.Label(self.element.hostname)
        print("\thostname :", self.element.hostname, flush=True)
        self._host_running = Gtk.Label(self.element.host_running)
        self._port = Gtk.Label(self.element.port)
        self._port_open = Gtk.Label(self.element.port_open)
        self._latency = Gtk.Label(self.element.latency)

        self.info_popover = self._build_info_popover()

    def _build_info_popover(self):
        host_box = self._build_subbox(self._hostname, self._host_running)
        port_box = self._build_subbox(self._port, self._port_open)
        latency_box = self._build_subbox(Gtk.Label("Latency"), self._latency)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for widget in (host_box, port_box, latency_box):
            vbox.pack_start(widget, False, False, 6)

        popover = Gtk.Popover()
        popover.add(vbox)
        popover.set_position(Gtk.PositionType.TOP)

        return popover


_status_bar = StatusBar()


def get_status_bar():
    return _status_bar
