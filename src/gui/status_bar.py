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
import concurrent.futures
import logging
import time

from gi.repository import Gtk

from gui import images
from gui import utils


# Duration in seconds between two status update wave
UPDATE_STATUS_FREQUENCY = .5

_images = images.HubanglImages()

logger = logging.getLogger("gui.status_bar")


class StatusBar:
    """
    Widget giving information about the state of watched elements via
    :mod:`~core.watch`.
    """
    def __init__(self):
        self._is_shutting_down = False

        self._stream_icon = _images.icons["streaming"]["regular_16px"]
        self._store_icon = _images.icons["storage"]["regular_16px"]

        self._elements = set()

        (self.container,
         self._hbox_remote,
         self._hbox_local) = self._build_status_bar()

        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._update_task = self._executor.submit(self._update_status)

    def _build_status_bar(self):
        hbox_main = Gtk.Box()
        hbox_main.connect("destroy", self._on_destroy)
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

    def _on_destroy(self, widget):
        self._is_shutting_down = True
        self._update_task.cancel()
        self._update_task.done()
        self._executor.shutdown()

    def _update_status(self):
        """
        Update periodically the status of all watched elements.
        This method is supposed to be run in an executor.
        """
        while not self._is_shutting_down:
            for watched_element in self._elements:
                watched_element.update_content()

            time.sleep(UPDATE_STATUS_FREQUENCY)

    def get_watched_element(self, element):
        for watched_element in self._elements:
            if element is watched_element.element:
                return watched_element

    def add_local_element(self, element):
        """
        Add a local watched ``element`` into the status bar.

        :param element: :class:`core.watch.LocalElement`
        """
        try:
            watched_element = WatchedLocal(element)
            self._add_watched_element(self._hbox_local, watched_element)
        except Exception:
            logger.exception(
                "Unexpected error on adding local element into status bar")

    def add_remote_element(self, element):
        """
        Add a remote watched ``element`` into the status bar.

        :param element: :class:`core.watch.RemoteElement`
        """
        try:
            watched_element = WatchedRemote(element)
            self._add_watched_element(self._hbox_remote, watched_element)
        except Exception:
            logger.exception(
                "Unexpected error on adding remote element into status bar")

    def _add_watched_element(self, box, watched_element):
        # Keeping a reference is needed to handle its callbacks properly
        self._elements.add(watched_element)
        box.pack_start(watched_element.button, True, True, 0)

        if box.get_no_show_all():
            box.set_no_show_all(False)
        box.show_all()

    def remove_local_element(self, element):
        """
        Remove a local watched ``element`` from the status bar.

        :param element: :class:`core.watch.LocalElement`
        """
        self._remove_watched_element(self._hbox_local, element)

    def remove_remote_element(self, element):
        """
        Remove a remote watched ``element`` from the status bar.

        :param element: :class:`core.watch.RemoteElement`
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
        self._red_square = _images.icons["square_red"]["regular_16px"]
        self._green_square = _images.icons["square_green"]["regular_16px"]

        self.element = element

        self.button = self._build_color_button()

    def _build_color_button(self):
        button = Gtk.ToolButton()
        # Set color as "unavailable element" by default
        button.set_icon_widget(self._red_square)
        button.connect("clicked", self._on_clicked)
        return button

    def _on_clicked(self, widget):
        self.info_popover.set_relative_to(widget)
        self.info_popover.show_all()

    @abc.abstractmethod
    def _build_info_popover(self):
        """
        Build a popover for this watched element.
        """

    @abc.abstractmethod
    def update_content(self):
        """
        Update button color and content popover content.
        """


class WatchedLocal(WatchedElement):
    """
    Representation of a local watched element.

    :param element: :class:`~core.watch.LocalElement`
    """
    def __init__(self, element):
        super().__init__(element)
        self.info_popover = self._build_info_popover()

    def _build_info_popover(self):
        # Build an empty popover
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        popover = Gtk.Popover()
        popover.add(vbox)
        popover.set_position(Gtk.PositionType.TOP)

        return popover

    def update_content(self):
        pass


class WatchedRemote(WatchedElement):
    """
    Representation of a remote watched element.

    :param element: :class:`~core.watch.RemoteElement`
    """
    def __init__(self, element):
        super().__init__(element)

        self._host_running_values = {True: "Up", False: "Down", None: "N/A"}
        self._port_open_values = {True: "Open", False: "Closed", None: "N/A"}

        self._hostname = Gtk.Label(self.element.hostname)
        self._hostname.set_tooltip_text("Hostname")
        self._host_running = Gtk.Label(
            self._host_running_values[self.element.host_running])
        self._port = Gtk.Label(self.element.port)
        self._port.set_tooltip_text("Server port")
        self._port_open = Gtk.Label(
            self._port_open_values[self.element.port_open])
        self._latency = Gtk.Label(str(self.element.latency))
        self._unavailable_duration = Gtk.Label(
            self._get_unavailability_duration())

        self._host_box = None
        self._port_box = None
        self._latency_box = None
        self._unavailable_duration_box = None

        self.info_popover = self._build_info_popover()

    def _build_info_popover(self):
        self._host_box = utils.build_multi_widgets_hbox(
            [self._hostname, ], [self._host_running, ], padding=6)
        self._port_box = utils.build_multi_widgets_hbox(
            [self._port, ], [self._port_open, ], padding=6)
        self._latency_box = utils.build_multi_widgets_hbox(
            [Gtk.Label("Latency (ms)"), ], [self._latency, ], padding=6)
        self._unavailable_duration_box = utils.build_multi_widgets_hbox(
            [Gtk.Label("Unavailable since (s)"), ],
            [self._unavailable_duration, ], padding=6)
        # Hide the box until the element becomes unavailable
        self._unavailable_duration_box.set_no_show_all(True)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for widget in (self._host_box, self._port_box, self._latency_box,
                       self._unavailable_duration_box):
            vbox.pack_start(widget, False, False, 6)

        popover = Gtk.Popover()
        popover.add(vbox)
        popover.set_position(Gtk.PositionType.TOP)

        return popover

    def _get_unavailability_duration(self):
        try:
            duration = time.time() - self.element.unavailable_since
            return str(round(duration, 1))
        except TypeError:
            return "N/A"

    def update_content(self):
        if self.element.available:
            self.button.set_icon_widget(self._green_square)
            self._unavailable_duration_box.set_no_show_all(True)
            self._unavailable_duration_box.hide()
        else:
            self.button.set_icon_widget(self._red_square)
            self._unavailable_duration_box.set_no_show_all(False)
            self._unavailable_duration_box.show()
            self._unavailable_duration.set_text(
                self._get_unavailability_duration())

        self.button.show_all()

        self._host_running.set_text(
            self._host_running_values[self.element.host_running])
        self._port_open.set_text(
            self._port_open_values[self.element.port_open])
        self._latency.set_text(str(self.element.latency))


_status_bar = StatusBar()


def get_status_bar():
    return _status_bar
