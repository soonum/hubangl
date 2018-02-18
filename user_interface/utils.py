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
        dialog.connect("response", default_error_callback)

    dialog.run()


def default_error_callback(dialog, response_id):
    """
    Default callback called when there is no callback provided to
    :meth:`build_error_dialog`.
    """
    if (response_id == Gtk.ResponseType.CLOSE
            or response_id == Gtk.ResponseType.DELETE_EVENT):
        dialog.destroy()
