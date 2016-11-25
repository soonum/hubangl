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


class Error(Exception):
    """
    Base class handling base exceptions.
    """
    default_message = None

    def __init__(self, message=None, *pargs, **kwargs):
        if not message:
            message = self.default_message
            super().__init__(message, *pargs, **kwargs)


class GstElementInitError(Error):
    """
    Error raised when a GStreamer elements failed
    to initialized.
    """
    default_message = "GStreamer element init failed"


class GstElementNotTeeIO(Error):
    """
    Error raised when a GStreamer elements is not
    initialized as ``tee`` input/output.
    """
    default_message = "GStreamer was not initialized as a ``tee`` input/output"


class TeePatchingError(Error):
    """
    Error raised when an ``tee`` element has not at least one input and one
    output referenced elements.
    """
    default_message = "Input/output reference is missing for tee element"


class AddingElementError(Error):
    """
    Error raised when adding Gstreamer elements failed.
    """
    default_message = "Failed during adding elements into the pipeline"


class ElementAlreadyAdded(Error):
    """
    Error raised when a GStreamer element is already added into a pipeline.
    """
    default_message = "GStreamer already added into the pipeline"


class LinkingElementError(Error):
    """
    Error raised when linking Gstreamer elements failed.
    """
    default_message = "Failed during linking elements in the pipeline"


class NotAudioVideoSource(Error):
    """
    Error raised when GStreamer element is neither an audio or a video input
    source.
    """
    default_message = "GStreamer element is neither audio or video input source"


class NotStoreStreamSink(Error):
    """
    Error raised when GStreamer element is neither a store or a stream sink.
    """
    default_message = "GStreamer element is neither store or stream sink"


class DeviceMissing(Error):
    """
    Error raised when a device (as input) is missing.
    """
    default_message = "Device is missing"


class LocationMissing(Error):
    """
    Error raised when a location (as input) is missing.
    """
    default_message = "Location is missing"


class LocationNotValid(Error):
    """
    Error raised when a location (as custom path) is not valid.
    """
    default_message = "Location is not valid"


class StreamInfoIncomplete(Error):
    """
    Error raised when mandatory inputs for streaming
    Gst element are not filled.
    """
    default_message = "Streaming information incomplete"
