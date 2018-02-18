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
# Copyright (c) 2016-2017 David Testé

from gi.repository import Gtk

from user_interface import images


images = images.HubanglImages()


def build_confirm_dialog(message_type, message_label,
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
    confirm_dialog.set_icon_from_file(images.logo_favicon_path)
    confirm_dialog.set_title("Confirmation")
    confirm_dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
    confirm_dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT)
    confirm_dialog.set_modal(True)
    if on_signal and callback:
        confirm_dialog.connect(on_signal, callback)

    confirm_dialog.run()


def build_error_dialog(message_label, on_signal=None, callback=None):
    """
    Create a :class:`Gtk.MessageDialog` to notifiy user that an error
    occurred.

    :param message_label: text displayed to user as :class`str`
    :param on_signal: Gtk signal as :class:`str`
    :param callback: callback to connect to ``signal``
    """
    error_dialog = Gtk.MessageDialog(
        message_type=Gtk.MessageType.ERROR, message_format=message_label)
    error_dialog.set_icon_from_file(images.logo_favicon_path)
    error_dialog.set_title("Error")
    error_dialog.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
    error_dialog.set_modal(True)
    if on_signal and callback:
        error_dialog.connect(on_signal, callback)
    else:
        error_dialog.connect("response", default_error_callback)

    error_dialog.run()


def default_error_callback(dialog, response_id):
    """
    Default callback called when there is no callback provided to
    :meth:`build_error_dialog`.
    """
    if (response_id == Gtk.ResponseType.CLOSE
            or response_id == Gtk.ResponseType.DELETE_EVENT):
        dialog.destroy()
