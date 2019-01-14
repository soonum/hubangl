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

from gi.repository import Gtk

from gui import images


images = images.HubanglImages()


def pack_widgets(box, *widgets):
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


def build_multi_widgets_hbox(left_widgets, right_widgets, padding=0):
    """
    Build a formatted horizontal box. All the ``left_widgets`` will be packed
    at the start of the box. All the ``right_widgets`` will be packed at the
    end of the box.

    :param label: iterable of :class:`Gtk.Widget`
    :param value: iterable of :class:`Gtk.Widget`
    :param padding: padding to add to a widget on packing

    :return: :class:`Gtk.Box`
    """
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    for left_widget in left_widgets:
        box.pack_start(left_widget, False, False, padding)
    for right_widget in right_widgets:
        box.pack_end(right_widget, False, False, padding)
    return box


def build_confirm_dialog(message_type, primary_text, secondary_text=None,
                         on_signal=None, callback=None):
    """
    Create a :class:`Gtk.MessageDialog` asking user for confirmation.

    :param message_type: :class:`Gtk.MessageType`
    :param primary_text: primary text displayed to user as :class`str`
    :param secondary_text: secondary text displayed to user as :class`str`
    :param on_signal: Gtk signal as :class:`str`
    :param callback: callback to connect to ``signal``
    """
    dialog = Gtk.MessageDialog(
        message_type=message_type, message_format=primary_text)
    dialog.set_icon_from_file(images.logo_favicon_path)
    dialog.set_title("Confirmation")
    dialog.format_secondary_text(secondary_text)
    dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
    dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT)
    dialog.set_modal(True)
    if on_signal and callback:
        dialog.connect(on_signal, callback)

    dialog.run()


def build_info_dialog(primary_text, secondary_text=None, title="Info"):
    """
    Create a :class:`Gtk.MessageDialog` displaying user information.

    :param primary_text: primary text displayed to user as :class`str`
    :param secondary_text: secondary text displayed to user as :class`str`
    """
    dialog = Gtk.MessageDialog(
        message_type=Gtk.MessageType.INFO, message_format=primary_text)
    dialog.set_icon_from_file(images.logo_favicon_path)
    dialog.set_title(title)
    dialog.format_secondary_text(secondary_text)
    dialog.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
    dialog.set_modal(True)
    dialog.connect("response", default_callback)

    dialog.run()


def build_error_dialog(primary_text, secondary_text=None, on_signal=None,
                       callback=None):
    """
    Create a :class:`Gtk.MessageDialog` to notifiy user that an error
    occurred.

    :param primary_text: primary text displayed to user as :class`str`
    :param secondary_text: secondary text displayed to user as :class`str`
    :param on_signal: Gtk signal as :class:`str`
    :param callback: callback to connect to ``signal``
    """
    dialog = Gtk.MessageDialog(
        message_type=Gtk.MessageType.ERROR, message_format=primary_text)
    dialog.set_icon_from_file(images.logo_favicon_path)
    dialog.set_title("Error")
    dialog.format_secondary_text(secondary_text)
    dialog.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
    dialog.set_modal(True)
    if on_signal and callback:
        dialog.connect(on_signal, callback)
    else:
        dialog.connect("response", default_callback)

    dialog.run()


def default_callback(dialog, response_id):
    """
    Default callback called when there is no callback provided to a dialog box.
    """
    if (response_id == Gtk.ResponseType.CLOSE
            or response_id == Gtk.ResponseType.DELETE_EVENT):
        dialog.destroy()
