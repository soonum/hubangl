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

from gi.repository import Gst

from backend.exceptions import (GstElementInitError,
                                GstElementNotTeeIO,
                                LinkingElementError,)


class GstElement:
    """
    Helper for creating GStreamer element.
    It allows to define a GStreamer element as a tee input/output.

    :param element_kind: GStreamer element identifier as :class:`str`
    :param name: name element instance as :class:`str`, value of
        ``element_kind`` if is empty
    :param tee_input: instance is a tee input, default ``False``
    :param tee_output: instance is a tee output, default ``False``
    :param endpoint_tee: instance is a tee used right before a
        :class:`~ioelements.StreamElement` and/or a
        :class:`~ioelements.StoreElement`
    :param parents: a :class:`tuple` of GStreamer parent elements
        (used for connecting multiple sources to a muxer)
    """
    def __init__(self, element_kind, name,
                 tee_input=False, tee_output=False, endpoint_tee=False,
                 parents=None):
        self.element_kind = element_kind
        if not name:
            name = element_kind
        self.name = name
        self.parents = parents or ()
        try:
            self.gstelement = Gst.ElementFactory.make(
                self.element_kind, self.name)
        except:
            raise GstElementInitError

        self.tee_input = tee_input
        self.tee_output = tee_output
        self.related_tee = None

        # TODO: improve that data handling
        self.related_tee_input = None
        self.related_tee_output = None
        if tee_input and tee_output:
            pass
            # TODO:
            # Put here the case when an element is both input AND output of a tee
           #
        if self.element_kind == "tee":
            self.connected = False
            self.endpoint_tee = endpoint_tee
            self.related_input = None
            self.related_output = []

    def set_property(self, *args):
        """
        Provide ``GstElement`` interface to GStreamer set_property() method.
        """
        self.gstelement.set_property(*args)

    def get_property(self, arg):
        """
        Provide ``GstElement`` interface to GStreamer get_property() method.
        """
        return self.gstelement.get_property(arg)

    def get_static_pad(self, *args):
        """
        Provide ``GstElement`` interface to GStreamer get_static_pad() method.
        """
        return self.gstelement.get_static_pad(*args)

    def set_related_tee(self, tee_element):
        """
        Refer GStreamer ``tee`` element that ``self`` has to be
        connected.

        :param tee_element: GStreamer ``tee`` element
        """
        if self.tee_input:
            self.related_tee_input = tee_element
        elif self.tee_output:
            self.related_tee_output = tee_element
        else:
            raise GstElementNotTeeIO

    def set_connected(self):
        """
        Change connection state of a tee element after linking.
        """
        if "tee" not in self.element_kind:
            return
        self.connected = True

    def link(self, element):
        """
        Provide ``GstElement`` interface to GStreamer link() method.
        """
        try:
            self.gstelement.link(element.gstelement)
        except:
            raise LinkingElementError
