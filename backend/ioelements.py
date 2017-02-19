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

from backend import utils
from backend.gstelement import GstElement
from backend.exceptions import (GstElementInitError,
                                DeviceMissing,
                                LocationMissing,
                                LocationNotValid,
                                StreamInfoIncomplete)


class InputElement:
    """
    Class handling input element behavior.

    in_type could be "audio" or "video".
    """
    def __init__(self, description):
        self.description = description

    def detach_gstelement(self, pipeline_state):
        # Idem change_gstelement()
        # Put an assertion HERE to check pipeline state
        self.gstelement = None

    def change_property(self, property_name, property_value):
        self.gstelement.set_property(property_name, property_value)


class AudioInput(InputElement):
    def __init__(self, description, device_location, **kwargs):
        InputElement.__init__(self, description)
        self.device_location = device_location
        self.gstelement = self.create_gstelement(
            self.device_location, **kwargs)

    def create_gstelement(self, device, **kwargs):
        if kwargs.get("default", False):
            return self._create_default_audio_source()
        else:
            return self._create_audio_source(device, **kwargs)

    def _create_default_audio_source(self):
        _gstelement = GstElement("audiotestsrc", "default_audio_source")
        if not _gstelement:
            raise GstElementInitError
        _gstelement.set_property("volume", 0)  # muted source

        return _gstelement

    def _create_audio_source(self, device, **kwargs):
        if not device:
            raise DeviceMissing

        name = "microphone_" + device
        _gstelement = GstElement("pulsesrc", name, **kwargs)
        if not _gstelement:
            raise GstElementInitError
        _gstelement.set_property("device", device)

        return _gstelement


class VideoInput(InputElement):
    def __init__(self, description, communication, device_location, **kwargs):
        InputElement.__init__(self, description)
        self.communication = communication
        self.device_location = device_location
        self.gstelement = self.create_gstelement(
            self.device_location, **kwargs)

    def create_gstelement(self, device_location, **kwargs):
        if kwargs.get("default", False):
            return self._create_default_video_source()
        elif self.communication == "usb":
            return self._create_usbcam_input(device_location, **kwargs)
        elif (self.communication == "tcp"
              or self.communication == "udp"
              or self.communication == "http"
              or self.communication == "tls"):
            return self._create_rtsp_input(device_location, **kwargs)

    def _create_default_video_source(self):
        _gstelement = GstElement("videotestsrc", "default_video_source")
        if not _gstelement:
            raise GstElementInitError
        _gstelement.set_property("pattern", 2)

        return _gstelement

    def _create_usbcam_input(self, device, **kwargs):
        if not device:
            raise DeviceMissing
        name = "usb_camera_" + device
        _gstelement = GstElement("v4l2src", name, **kwargs)
        if not _gstelement:
            raise GstElementInitError
        _gstelement.set_property("device", device)

        return _gstelement

    def _create_rtsp_input(self, location, **kwargs):
        if not location:
            raise LocationMissing

        if utils.has_valid_ip(location) and utils.get_port(location) == 554:
            if "rtsp://" not in location:
                location = "rtsp://" + location
        else:
            raise LocationNotValid

        _gstelement = GstElement("rtspsrc", "ip_camera", **kwargs)
        if not _gstelement:
            raise GstElementInitError
        _gstelement.set_property("location", location)

        return _gstelement


class OutputElement:
    """
    Class handling output element behavior.

    out_type could be "stream" or "store".
    """
    def __init__(self, description):
        self.description = description

    def detach_gstelement(self, pipeline_state):
        # Idem change_gstelement()
        # Put an assertion HERE to check pipeline state
        self.gstelement = None

    def change_property(self, property_name, property_value):
        self.gstelement.set_property(property_name, property_value)


class StreamElement(OutputElement):
    def __init__(self, description, ip, port, mount,
                 password=None, **kwargs):
        OutputElement.__init__(self, description)
        self.ip = ip
        self.mount = mount
        self.port = port
        self.password = password
        self.gstelement = self.create_gstelement(
            self.ip, self.port, self.mount, self.password, **kwargs)

    def create_gstelement(self, ip, port, mount, password, **kwargs):
        """
        Create GStreamer streaming sink. It streams over an IceCast server.
        """
        if not (ip or port or mount):
            raise StreamInfoIncomplete

        _gstelement = GstElement("shout2send", self.description, **kwargs)
        if not _gstelement:
            raise GstElementInitError
        _gstelement.set_property("sync", False)
        _gstelement.set_property("ip", ip)
        _gstelement.set_property("port", port)
        _gstelement.set_property("mount", mount)
        if password:
            _gstelement.set_property("password", password)

        return _gstelement


class StoreElement(OutputElement):
    def __init__(self, description, path, **kwargs):
        OutputElement.__init__(self, description)
        self.path = path
        self.gstelement = self.create_gstelement(self.path, **kwargs)

    def create_gstelement(self, path, **kwargs):
        """
        Creates a GStreamer file sink.
        """
        if not path:
            raise ValueError

        _gstelement = GstElement("filesink", self.description, **kwargs)
        if not _gstelement:
            raise GstElementInitError
        _gstelement.set_property("location", path)
        _gstelement.set_property("sync", False)

        return _gstelement
