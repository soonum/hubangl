#!/usr/bin/env python34
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

import logging
import pathlib

from gi.repository import Gst
from gi.repository import GLib

from core import iofetch
from core import ioelements
from core.gstelement import GstElement
from core.exceptions import (TeePatchingError,
                             AddingElementError,
                             NotAudioVideoSource,
                             ElementAlreadyAdded,
                             TransportElementNotFound)

CUR_ELEM = None  # DEBUG
NEW_ELEM = None  # DEBUG
CUR_BIN = None  # DEBUG
DEFAULT_IMAGE = (pathlib.Path(__file__).resolve().parents[2]
                 / "artwork"
                 / "HUBAngl_logo_PNG_256-256_px.png")
DEFAULT_IP = "127.0.0.1"
DEFAULT_MOUNT = "eggs"
DEFAULT_PATH = "/tmp/spam"
DEFAULT_PORT = 12345

AUDIO_VIDEO_STREAM = "audiovideo"
VIDEO_ONLY_STREAM = "video"
AUDIO_ONLY_STREAM = "audio"

# Time to wait in seconds before trying to reconnect to an Icecast server.
RECONNECT_INTERVAL = 5

logger = logging.getLogger("core.process")


class PlaceholderPipeline:
    """
    Pipeline used as a placeholder waiting for user to select a audio and/or
    a video source.
    """
    def __init__(self):
        self.pipeline = Gst.Pipeline()
        self.pipeline_elements = self._create_elements()
        self.is_playing = False

        self._build_pipeline(*self.pipeline_elements)

    def _build_pipeline(self, *elements):
        for element in elements:
            self.pipeline.add(element)

        previous_item = None
        for element in elements:
            if previous_item:
                previous_item.link(element)
            previous_item = element

    def _create_elements(self):
        self.video_source = Gst.ElementFactory.make(
            "videotestsrc", "video_source_placeholder")
        self.video_source.set_property("pattern", 1)  # snow pattern

        caps_string = ("video/x-raw,"
                       + "format=I420,"
                       + "width=1280,"  # TODO: adjust value
                       + "height=720,"  # TODO: adjust value
                       + "framerate=24/1")
        caps = Gst.caps_from_string(caps_string)
        self.capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
        self.capsfilter.set_property("caps", caps)

        self.text_overlay = Gst.ElementFactory.make(
            "textoverlay", "text_overlay_placeholder")
        message = "Choose audio and/or video sources"
        self.text_overlay.set_property("text", message)
        self.text_overlay.set_property("valignment", "position")
        self.text_overlay.set_property("ypos", 0.7)
        self.text_overlay.set_property("halignment", "center")
        self.text_overlay.set_property("font-desc", "Sans, 24")  # TODO: Find a right font and font-size

        self.image_overlay = Gst.ElementFactory.make(
            "gdkpixbufoverlay", "image_overlay_placeholder")
        self.image_overlay.set_property("location", DEFAULT_IMAGE)
        self.image_overlay.set_property("relative-x", 0.75)  # TODO: improve handling
        self.image_overlay.set_property("relative-y", 0.1)  # TODO: idem
        self.image_overlay.set_property("alpha", 0.7)

        self.video_convert = Gst.ElementFactory.make(
            "videoconvert", "video_convert_placeholder")
        self.screen_sink = Gst.ElementFactory.make(
            "xvimagesink", "screen_sink_placeholder")

        return (self.video_source, self.capsfilter, self.text_overlay,
                self.image_overlay, self.video_convert, self.screen_sink)

    def set_play_state(self):
        """
        Set pipeline instance to PLAYING state either to start.
        """
        self.pipeline.set_state(Gst.State.PLAYING)
        self.is_playing = True
        logger.debug("[placeholder pipeline] Switched to PLAY state")

    def set_stop_state(self):
        """
        Set pipeline instance to NULL state.
        """
        self.pipeline.set_state(Gst.State.NULL)
        self.is_playing = False
        logger.debug("[placeholder pipeline] Switched to STOP state")

    def is_playing_state(self):
        """
        Return ``True`` if pipeline instance is in playing state.
        """
        state = self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
        if self.pipeline.state_get_name(state[1]) == "PLAYING":
            return True
        else:
            return False


class Pipeline:
    """
    Class handling all GStreamer elements for `standalone` mode. This is also
    base class for `monitoring` and `controlroom` modes
    """
    def __init__(self):
        self.pipeline = Gst.Pipeline()
        self.is_preview_state = False
        self.is_playing = False

        # Map fakesink to tee element
        self._output_tee_pool = {}

        self.speaker_volume = None

        self.audio_sources = self.create_audio_sources()
        self.video_sources = self.create_video_sources()
        self.speaker_sinks = self.get_speaker_sinks()
        #: GstElement used in the pipeline
        self.speaker_sink = None

        # Streaming sinks that has to be added and linked when pipeline is
        # switched to play state.
        self.stream_sink_branches = {"audio": {"tee": None, "branches": []},
                                     "video": {"tee": None, "branches": []},
                                     "audiovideo": {"tee": None, "branches": []}}
        # Idem for store sinks.
        self.store_sink_branches = {"audio": {"tee": None, "branches": []},
                                    "video": {"tee": None, "branches": []},
                                    "audiovideo": {"tee": None, "branches": []}}

        (self.audio_process_source,
         self.audio_process_branch1,
         self.audio_process_branch2,
         self.audio_process_branch3,
         self.audio_muxer_source) = self.create_audio_process()

        (self.video_process_source,
         self.video_process_branch1,
         self.video_process_branch2,
         self.video_process_branch3,
         self.video_muxer_source) = self.create_video_process()

        (self.av_process_branch1,
         self.av_process_branch2,
         self.av_process_branch3) = self.create_audiovideo_process(
             self.audio_muxer_source,
             self.video_muxer_source)

        self.build_pipeline(self.pipeline,
                            self.audio_process_source,
                            self.audio_process_branch1,
                            self.audio_process_branch2,
                            self.audio_process_branch3,
                            self.video_process_source,
                            self.video_process_branch1,
                            self.video_process_branch2,
                            self.video_process_branch3,
                            self.av_process_branch1,
                            self.av_process_branch2,
                            self.av_process_branch3,)

    def set_play_state(self):
        """
        Set pipeline instance to PLAYING state either to start
        or resuming broadcasting.
        """
        if self.is_preview_state:
            self.pipeline.set_state(Gst.State.NULL)
            self.is_preview_state = False

        if not self.is_playing:
            self.set_output_branches()
            self.pipeline.set_state(Gst.State.PLAYING)
            self.is_playing = True
            logger.debug("[main pipeline] Switched to PLAY state")

    def set_pause_state(self):
        """
        Set pipeline instance to PAUSED state.
        """
        self.pipeline.set_state(Gst.State.PAUSED)

    def set_null_state(self):
        """
        Set pipeline instance to NULL state.
        """
        self.pipeline.set_state(Gst.State.NULL)

    def set_stop_state(self):
        """
        Set pipeline instance to NULL state and end broadcasting, then
        the pipeline gets back to preview mode.
        """
        self.remove_output_branches()

        self.set_null_state()
        self.is_playing = False
        logger.debug("[main pipeline] Switched to STOP state")

        # Switch back to preview mode.
        self.pipeline.set_state(Gst.State.PLAYING)
        self.is_preview_state = True

    def close(self):
        """
        Set pipeline instance to NULL state and shut it down.
        """
        self.set_null_state()
        self.pipeline = None

    def set_preview_state(self, default_source_type_requested):
        """
        Set pipeline instance to PLAYING state allowing preview before
        starting to stream by setting a default source.

        :param default_source_type_requested: :class:`str` defining
            type of source to get

        .. note:: In this version it is mandatory to have a default
            audio source to have a working pipeline.
        """
        self._set_default_source(default_source_type_requested)
        self.pipeline.set_state(Gst.State.PLAYING)
        self.is_preview_state = True
        logger.debug("[main pipeline] Switched to PREVIEW state")

    def _set_default_source(self, source_type_requested):
        """
        Set a default source of the needed type.

        :param source_type_requested: type of source a default is
            requested as :class:`str`, it can be ``audio`` or ``video``
        """
        if source_type_requested == "audio":
            self._build_default_audio_source()
        elif source_type_requested == "video":
            self._build_default_video_source()
        else:
            raise ValueError

    def _build_default_video_source(self):
        """
        """
        default_video_source = ioelements.VideoInput(
            "default_video_source", None, None, default=True)
        self.set_input_source(default_video_source)
        self.set_text_overlay("No video source", "center", "center")

    def _build_default_audio_source(self):
        """
        """
        default_audio_source = ioelements.AudioInput(
            "default_audio_source", None, default=True)
        self.set_input_source(default_audio_source)

    def is_standingby(self):
        """
        Check if pipeline instance is in the right state to perform
        major change on a Gstreamer element.
        Major change mean ``device`` or ``location`` change.

        Return True if change(s) can be made on Gst element.
        """
        raise NotImplementedError

    def set_text_overlay(self, text, h_alignment, v_alignment):
        """
        Set text displayed over video stream.

        :param text: text to display as :class:`str`
        :param h_alignment: text horizontal alignment
        :param v_alignment: text vertical alignment

        .. note:: This version have does not support font-type, font-size
            and font-color changing yet.
        """
        self.text_overlay.set_property("text", text)
        self.text_overlay.set_property("halignment", h_alignment)
        self.text_overlay.set_property("valignment", v_alignment)

    def get_current_text(self):
        """
        Return the string currently displayed over video stream.
        """
        return self.text_overlay.get_property("text")

    def set_image_overlay(self, filepath=None, offset_x=None,
                          offset_y=None, alpha=None):
        """
        Set image displayed over video stream.

        :param filepath: filepath to an image/picture
        :param offset_x: image position on x axis in pixel
        :param offset_y: image position on y axis in pixel
        """
        if filepath:
            self.image_overlay.set_property("location", filepath)
        if offset_x:
            self.image_overlay.set_property("offset-x", offset_x)
        if offset_y:
            self.image_overlay.set_property("offset-y", offset_y)
        if alpha:
            self.image_overlay.set_property("alpha", alpha)

    def mute_audio_input(self, value):
        """
        Mute or unmute the audio input source based on ``value``.

        :param value: :class:`bool`
        """
        self.source_volume.set_property("mute", value)
        logger.info("Audio input is {}".format("muted" if value else "unmuted"))

    def get_speaker_sinks(self):
        """
        Get audio sinks device names.

        :return: :class:`dict` {description: device_name}
        """
        audio_sinks = {}
        audio_devices = iofetch.find_audio()
        for device in audio_devices:
            if audio_devices[device][iofetch.TYPE] == iofetch.TYPE_IN:
                continue
            if "Monitor" in audio_devices[device][iofetch.DESCRIP]:
                continue
            audio_sinks[audio_devices[device][iofetch.DESCRIP]] = device

        return audio_sinks

    def set_speaker_sink(self, device_name):
        """
        Change the device used for the speaker sink GstElement.
        """
        self.speaker_sink.set_property("device", device_name)

    def set_default_speaker_sink(self):
        """
        Set the speaker sink GstElement device to built-in speakers.
        """
        for key, value in self.speaker_sinks.items():
            if "Built-in Audio" in key:
                self.set_speaker_sink(value)
                logger.debug("[main pipeline] Default loudspeaker sink set to"
                             " {}".format(value))
                return

    def update_gstelement_properties(self, gstelement, **kargs):
        """
        Update properties of a :class:`~core.GstElement` if there is any
        change to make.

        :param gstelement: :class:`~core.GstElement`
        :param kargs: field to update with property key as :class:`str` and
            value of the right type
        """
        for property_key, value in kargs.items():
            gstelement.set_property(property_key, value)

    def get_connected_element(self, pad):
        """
        Gets element connected to 'pad' in order to handle
        easily an element unlinking.

        Returns Gst.Element if there's any, None otherwise.
        """
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #  FIXME: May not work on 'tee' element,
        #         has to be tested before releasing
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        element = None
        if pad:
            linkedpad = pad.get_peer()
            if linkedpad:
                element = linkedpad.get_parent()
            return element

    def swap_gstelement(self, current_element, requested_element):
        """
        Swap two :class:`~core.gstelement.Gstelement` dynamically
        without pausing/stopping pipeline.

        :param current_element: :class:`~core.gstelement.Gstelement`
            currently in the pipeline
        :param requested_element: :class:`~core.gstelement.Gstelement`
            to add and link in the pipeline
        """
        blockpad = current_element.get_static_pad("src")
        if not blockpad:
            # TODO: refactor this part of code
            # This is an endpoint sink element
            # Only its parent can have a blockpad
            pad = current_element.get_static_pad("sink")
            parent = self.get_connected_element(pad)
            blockpad = parent.get_static_pad("src")

        user_data = {"current_element": current_element,
                     "requested_element": requested_element,
                     "bin": self.pipeline}
        Gst.Pad.add_probe(
            blockpad, Gst.PadProbeType.BLOCK_DOWNSTREAM,
            self.pad_probe_cb, user_data)

    def pad_probe_cb(self, pad, info, user_data):
        """
        Callback for blocking data flow between 2 or 3 elements.
        """
        # Remove the probe first
        Gst.Pad.remove_probe(pad, info.id)

        # Install new probe for EOS
        current_element = user_data["current_element"]
        sourcepad = current_element.get_static_pad("src")
        if not sourcepad:
            # TODO: refactor this part of code
            # This is an endpoint sink element
            # Only its parent can have a blockpad
            pad = current_element.get_static_pad("sink")
            parent = self.get_connected_element(pad)
            sourcepad = parent.get_static_pad("src")
            parent_needed = True
        else:
            parent_needed = False
        Gst.Pad.add_probe(sourcepad, Gst.PadProbeType.EVENT_DOWNSTREAM,
                          self.event_probe_cb, user_data,)

        # Push EOS into the element, the probe will be fired when the
        # EOS leaves the element and it has thus drained all of its data
        # TODO: refactor the 4 lines followings
        if parent_needed:
            sinkpad = parent.get_static_pad("sink")
        else:
            sinkpad = Gst.Element.get_static_pad(current_element, "sink")

        if sinkpad:
            Gst.Pad.send_event(sinkpad, Gst.Event.new_eos())
        else:
            # In case of input change
            current_element.send_event(Gst.Event.new_eos())

        return Gst.PadProbeReturn.OK

    def event_probe_cb(self, pad, info, user_data):
        """
        Callback handling event and allowing element replacement.
        """
        current_element = user_data["current_element"]
        requested_element = user_data["requested_element"]
        current_bin = user_data["bin"]
        info_event = info.get_event()

        if (info_event is None) or (info_event.type != Gst.EventType.EOS):
            return Gst.PadProbeReturn.PASS

        Gst.Pad.remove_probe(pad, info.id)

        # Getting element context:
        element_after = self.get_connected_element(pad)  # In v1.0 "pad" is most likely a sourcepad
        if element_after != current_element:
            current_element = pad.get_parent()
        else:
            # current_element is an endpoint pipeline element
            element_after = None
        sinkpad = current_element.get_static_pad("sink")
        element_before = self.get_connected_element(sinkpad)

        # -------------------------------------
        # No need to change element's state to NULL before removing?
        # If so --> thread deadlock (has to be investigated and debugged)
        # ------------------------------------
        #    current_element.set_state(Gst.State.NULL)
        current_bin.remove(current_element)
        logger.debug("[main pipeline] GstElement dynamically removed from"
                     " pipeline: '{}'".format(current_element.name))
        self.add_elements(current_bin, (requested_element,))
        if element_before:
            element_before.link(requested_element.gstelement)  # (doesn't apply for input feed)
        if element_after:
            requested_element.gstelement.link(element_after)  # (doesn't apply for screensink, filesink)
        # Not sure about setting requested_element in PLAYING state
        # TODO: Maybe call set_play_state
        current_element = None
        requested_element.gstelement.set_state(Gst.State.PAUSED)
        requested_element.gstelement.set_state(Gst.State.PLAYING)

        return Gst.PadProbeReturn.DROP

    def is_from_streaming(self, message):
        """
        Check if a message emitted on the bus is from a stream sink element.

        :param message: GStreamer bus message

        :return: ``True`` if the message was emitted by a stream sink element,
            ``False`` otherwise
        """
        for _, sinks in self.stream_sink_branches.items():
            for branch in sinks["branches"]:
                if message.src == branch[-1].gstelement.gstelement:
                    return True

        return False

    def reconnect_streaming_branch(self, message):
        """
        Perform auto reconnect to the icecast server. It assumes that
        ``message`` was emitted from stream sink element.

        :param message: GStreamer bus message
        """
        for feed_type, sinks in self.stream_sink_branches.items():
            for branch in sinks["branches"]:
                if message.src == branch[-1].gstelement.gstelement:
                    pad = branch[0].gstelement.get_static_pad("sink")
                    tee_pad = pad.get_peer()
                    tee_pad.add_probe(Gst.PadProbeType.BLOCK_DOWNSTREAM,
                                      self._on_stream_down, {"branch": branch})
                    break

    def _on_stream_down(self, pad, info, user_data):
        Gst.Pad.remove_probe(pad, info.id)
        branch = user_data["branch"]
        sink_pad = branch[0].gstelement.get_static_pad("sink")
        pad.unlink(sink_pad)
        for element in branch:
            if isinstance(element, ioelements.OutputElement):
                element = element.gstelement
            element.gstelement.set_state(Gst.State.NULL)
        GLib.timeout_add_seconds(RECONNECT_INTERVAL, self._reconnect_stream, pad, branch)
        return Gst.PadProbeReturn.OK

    def _reconnect_stream(self, tee_pad, branch):
        tee_pad.add_probe(Gst.PadProbeType.BLOCK_DOWNSTREAM,
                          self._on_reconnect_stream,
                          {"branch": branch})

    def _on_reconnect_stream(self, pad, info, user_data):
        Gst.Pad.remove_probe(pad, info.id)
        branch = user_data["branch"]
        sink_pad = branch[0].gstelement.get_static_pad("sink")
        pad.link(sink_pad)
        for element in branch:
            if isinstance(element, ioelements.OutputElement):
                element = element.gstelement
            element.gstelement.set_state(Gst.State.PLAYING)
        return Gst.PadProbeReturn.OK

    def build_pipeline(self, pipeline, *branches):
        """
        Add and link GStreamer elements into ``pipeline``.
        """
        self.add_elements(pipeline, *branches)
        self.link_elements(*branches)

    def _exist_in_pipeline(self, element):
        """
        Check if Gstreamer element is in a pipeline.

        :param element: instance of :class:`GstElement`

        :return: ``True`` if ``element`` is in ``pipeline``
        """
        if self._get_gst_element(element):
            return True

    def _get_gst_element(self, element):
        """
        Fetching GStreamer element in a piepline.

        :param element: instance of :class:`~core.gstelement.GstElement`

        :return: Gstreamer element
        """
        return self.pipeline.get_by_name(element.name)

    def get_source_by_name(self, name):
        """
        Fetching GStreamer element source by its name.
        The first match will be returned.

        :param element: name attribute of
            :class:`~core.ioelement.Input`

        :return: Gstreamer element
        """
        for source_type in (self.audio_sources, self.video_sources):
            for source in source_type:
                if name == source.name:
                    return source

    def connect_tee(self,
                    tee_element,
                    input_element,
                    *output_elements):
        """
        Links input and outputs of a ``tee`` element.
        """
        input_element.link(tee_element)
        logger.debug("[main pipeline] '{}' linked to '{}'".format(
            input_element.name, tee_element.name))
        tee_element.related_input = input_element
        for output_element in output_elements:
            tee_element.link(output_element)
            tee_element.related_output.append(output_element)
            logger.debug("[main pipeline] '{}' linked to '{}'".format(
                tee_element.name, output_element.name))

        tee_element.set_connected()

    def remove_tee_output(self, tee, element_kind):
        """
        Remove all ``tee`` output elements based upon matching of
        ``element_kind``.

        :param tee: Gstreamer tee element as :class:`GstElement`
        :param element_kind: type of GStreamer element as :class:`str`
        """
        for item in tee.related_output:
            if (self._exist_in_pipeline(item)
                    and item.element_kind == element_kind):
                tee.gstelement.unlink(item.gstelement)
                self.pipeline.remove(item.gstelement)
                logger.debug("[main pipeline] '{}' unlinked and removed its"
                             " output '{}'".format(tee.name, item.name))

    def build_tee_connections(self, *branches):
        """
        Establish relation between a ``tee`` element and its related input and
        outputs. Then it perform the linking of the related elements by
        calling :func:`connect_tee`
        """
        tee_elements = []
        tee_input_elements = []
        tee_output_elements = []

        for branche in branches:
            for item in branche:
                if item.element_kind == "tee":
                    tee_elements.append(item)
                    continue
                # Note: item can have both input and ouput
                if item.related_tee_input:
                    tee_input_elements.append(item)
                if item.related_tee_output:
                    tee_output_elements.append(item)

        for tee in tee_elements:
            # Definig the tee input
            for element in tee_input_elements:
                if element.related_tee_input.name == tee.name:
                    _input_element = element
                    break

            _output_elements = []
            # Definig the tee output(s)
            for element in tee_output_elements:
                if element.related_tee_output.name == tee.name:
                    _output_elements.append(element)

            if tee.endpoint_tee and not _output_elements:
                fakesink = self._output_tee_pool[tee]
                _output_elements.append(fakesink)

            if not (_input_element and _output_elements):
                raise TeePatchingError

            self.connect_tee(tee, _input_element, *_output_elements)

    def make_fakesink(self, tee_element, pipeline):
        """
        Create ``fakesink`` GStreamer element as a placeholder for an endpoint
        ``tee`` element output. It can be replaced by a
        :class:`~ioelements.StreamElement` or a :class:`~ioelements.StoreElement`.

        It is used for linking all the process elements in the pipeline
        without failing.

        It set the relation between the ``fakesink`` and the endpoint ``tee``,
        so it can be connected thereafter.

        After element creation it adds it to ``pipeline``.

        :param tee_element: endpoint ``tee`` element
        :param pipeline: GStreamer ``pipeline`` element

        :return: ``fakesink`` GStramer element
        """
        fakesink_name = "fakesink_" + str(len(self._output_tee_pool))
        fakesink = GstElement("fakesink", fakesink_name, tee_output=True)
        fakesink.set_related_tee(tee_element)
        fakesink.set_property("sync", False)

        pipeline.add(fakesink.gstelement)

        return fakesink

    def add_elements(self, pipeline, *branches):
        """
        Add Gst elements to ``pipeline``
        """
        for branch in branches:
            for element in branch:
                if self._exist_in_pipeline(element):
                    raise ElementAlreadyAdded
                try:
                    if (isinstance(element, ioelements.InputElement)
                            or isinstance(element, ioelements.OutputElement)):
                        gstelement = element.gstelement.gstelement
                    else:
                        gstelement = element.gstelement
                    pipeline.add(gstelement)
                    logger.debug("[main pipeline] GstElement added to"
                                 " pipeline: '{}'".format(element.name))
                except:
                    raise AddingElementError

    def remove_elements(self, pipeline, *branches):
        """
        Remove Gst elements from ``pipeline``
        """
        for branch in branches:
            for element in branch:
                if self._exist_in_pipeline(element):
                    if (isinstance(element, ioelements.InputElement)
                            or isinstance(element, ioelements.OutputElement)):
                        gstelement = element.gstelement.gstelement
                    else:
                        gstelement = element.gstelement

                    pipeline.remove(gstelement)
                    logger.debug("[main pipeline] GstElement removed from"
                                 " pipeline: '{}'".format(element.name))

    def link_elements(self, *branches):
        """
        Link GStreamer elements in the pipeline.

        :param branches: branches to link

        :note: ``tee`` elements MUST be linked with their input/outputs before
            any other GStreamer elements. Otherwise it could fail to link
            ``tee`` sources because of ``caps`` incompatibility
        """
        self.build_tee_connections(*branches)
        previous_item = None

        for branch in branches:
            for item in branch:
                if item.element_kind == "tee":
                    previous_item = None
                    continue
                if item.parents:
                    for parent in item.parents:
                        parent.link(item)
                        previous_item = item
                        logger.debug("[main pipeline] '{}' linked to '{}'".format(
                            parent.name, item.name))

                if not previous_item:
                    previous_item = item
                    # Must exist before any linking attempt.
                    continue

                previous_item.link(item)
                logger.debug("[main pipeline] '{}' linked to '{}'".format(
                    previous_item.name, item.name))
                previous_item = item
            else:
                # End of branch
                previous_item = None

    def set_input_source(self, source_element):
        """
        Add a audio/video source input to the pipeline.

        :param source_element: audio/video input Gstreamer element to add
        """
        source_gstelement = source_element.gstelement
        if self._exist_in_pipeline(source_gstelement):
            raise ElementAlreadyAdded

        if isinstance(source_element, ioelements.AudioInput):
            index = 0
        elif isinstance(source_element, ioelements.VideoInput):
            index = 1
        else:
            raise NotAudioVideoSource

        branch = (self.audio_process_source, self.video_process_source)

        pad = branch[index][0].get_static_pad("sink")
        parent = self.get_connected_element(pad)
        if parent:
            # An audio/video source is already set
            self.swap_gstelement(parent, source_gstelement)
        else:
            self.add_elements(self.pipeline, (source_gstelement,))
            source_gstelement.link(branch[index][0])

        logger.info("{} input source set to '{}'".format(
            "Audio" if not index else "Video", source_element.name))

    def remove_input_sources(self):
        """
        Remove all input sources from the pipeline.
        """
        for sources in (self.audio_sources, self.video_sources):
            for element in sources:
                source_gstelement = element.gstelement
                if self._exist_in_pipeline(source_gstelement):
                    pad = source_gstelement.get_static_pad("src")
                    parent = self.get_connected_element(pad)
                    if parent:
                        source_gstelement.gstelement.unlink(parent)
                    self.pipeline.remove(source_gstelement.gstelement)

        logger.debug("[main pipeline] Removed all input sources")

    def set_output_branches(self):
        """
        Add a streaming/storing sink to the pipeline.
        """
        for sinks_dict in (self.store_sink_branches, self.stream_sink_branches):
            for _, sinks in sinks_dict.items():
                if sinks["branches"]:
                    self.remove_tee_output(sinks["tee"], "fakesink")

                for branch in sinks["branches"]:
                    self.add_elements(self.pipeline, branch)
                    # Link first branch element to its related tee
                    sinks["tee"].link(branch[0])
                    # Link all branch elements together
                    for i, element in enumerate(branch):
                        if i == 0:
                            continue
                        if isinstance(element, ioelements.OutputElement):
                            element = element.gstelement
                        branch[i - 1].link(element)

    def remove_output_branches(self):
        """
        Remove all output sinks from the GStreamer pipeline.
        """
        for sinks_dict in (self.stream_sink_branches, self.store_sink_branches):
            for _, sinks in sinks_dict.items():
                for branch in sinks["branches"]:
                    self.remove_elements(self.pipeline, branch)
                    for element in branch:
                        if isinstance(element, ioelements.OutputElement):
                            element = element.gstelement
                        element.gstelement.set_state(Gst.State.NULL)

        for tee, fakesink in self._output_tee_pool.items():
            if not self._exist_in_pipeline(fakesink):
                self.pipeline.add(fakesink.gstelement)
                tee.link(fakesink)

    def create_audio_sources(self):
        """
        Create all available audio inputs GStreamer elements.

        :return: :class:`tuple` of GStreamer elements
        """
        audio_sources = []
        audio_devices = iofetch.find_audio()
        for device in audio_devices:
            if audio_devices[device][iofetch.TYPE] == iofetch.TYPE_OUT:
                continue
            if "HDMI" in audio_devices[device][iofetch.DESCRIP]:
                continue

            _gstelement = ioelements.AudioInput(
                audio_devices[device][iofetch.DESCRIP], device)
            audio_sources.append(_gstelement)

        return tuple(audio_sources)

    def create_video_sources(self):
        """
        Create all available video inputs GStreamer elements.

        :return: :class:`tuple` of GStreamer elements

        .. warn:: Currently this function support only usb cameras fetching.
        """
        video_sources = []
        video_devices = iofetch.find_usbcam()

        if not video_devices:
            return None

        for device in video_devices:
            _gstelement = ioelements.VideoInput(
                video_devices[device][iofetch.DESCRIP],
                iofetch.COMM_USB, device)
            video_sources.append(_gstelement)

        return tuple(video_sources)

    def create_stream_branch(self, element_name, feed_type, ip, port, mount,
                             password=None):
        """
        Create a stream sink branch and add it to :attr:`stream_sink_branches`.

        :param element_name: name that is given to store object as :class:`str`
        :param feed_type: could be either ``audiovideo``, ``audio`` or
            ``video`` as :class:`str`
        :param ip: address of Icecast server as :class:`str`
        :param port: port as :class:`int` that Icecast server is listening on.
        :param mount: mountpoint as :class:`str` used on Icecast server
        :param password: password as :class:`str` that allows to add a
            mountpoint

        :return: :class:`~core.ioelements.StreamElement`
        """
        id = str(len(self.stream_sink_branches[feed_type]["branches"]))

        queue_name = "queue_" + feed_type + "_streamsink_" + id
        queue = GstElement("queue", queue_name, tee_output=True)
        queue.set_related_tee(self.stream_sink_branches[feed_type]["tee"])
        queue.set_property("flush-on-eos", True)
        queue.set_property("leaky", 2)

        sink_name = element_name + "_" + id
        sink = ioelements.StreamElement(sink_name, ip, port, mount, password)

        self._append_sink(self.stream_sink_branches, feed_type, (queue, sink))
        return sink

    def create_store_branch(self, feed_type, filepath, element_name):
        """
        Create a file sink branch and add it to :attr:`store_sink_branches`.

        :param element_name: name that is given to store object as :class:`str`
        :param feed_type: could be either ``audiovideo``, ``audio`` or
            ``video`` as :class:`str`
        :param filepath: full filepath as :class:`str`

        :return: :class:`~core.ioelements.StoreElement`
        """
        id = str(len(self.store_sink_branches[feed_type]["branches"]))

        queue_name = "queue_" + feed_type + "_filesink_" + id
        queue = GstElement("queue", queue_name, tee_output=True)
        queue.set_related_tee(self.store_sink_branches[feed_type]["tee"])

        sink_name = element_name + "_" + id
        sink = ioelements.StoreElement(sink_name, filepath)

        self._append_sink(self.store_sink_branches, feed_type, (queue, sink))
        return sink

    def _append_sink(self, sink_dict, feed_type, *elements):
        """
        Append ``elements`` in ``sink_dict`` depending on ``feed_type``.

        :param sink_dict: :class:`dict` containing sinks elements
        :param feed_type: could be either ``audiovideo``, ``audio`` or
            ``video`` as :class:`str`
        :param elements: elements to add
        """
        element_list = sink_dict.get(feed_type)
        for element in elements:
            element_list["branches"].append(element)

    def _set_output_tee(self, feed_type, tee_element):
        self.stream_sink_branches[feed_type]["tee"] = tee_element
        self.store_sink_branches[feed_type]["tee"] = tee_element
        self._output_tee_pool[tee_element] = self.make_fakesink(tee_element,
                                                                self.pipeline)

    def create_audio_process(self,):
        """
        Create Gst elements for audio processing.

        Linking structure:
        <from audio_source>---/volume/---/audiolevel/--->
        --->/tee_audio_source/
                 |---/queue/---/volume/---/speaker_sink/
                 |---/vorbis_encoder/--->
                  --->/tee_audio_process/
                           |---<to audiovideo processing (queue_muxer_audio)>
                           |---/queue/---/ogg_muxer/--->
                            --->/tee_output_audio/
                                     |---<to output branches>

        :return: a :class:`tuple` of branches

        :note: A ``tee`` element means the end of a branch. Then each output
            of this ``tee`` make a new branch that has to be returned.
        """
        # Tee:
        tee_audio_source = GstElement("tee", "tee_audio_source")
        tee_audio_process = GstElement("tee", "tee_audio_process")
        tee_output_audio = GstElement("tee", "tee_output_audio",
                                      endpoint_tee=True)
        self._set_output_tee("audio", tee_output_audio)
        # Queue:
        queue_muxer_av1 = GstElement(
            "queue", "queue_muxer_av1", tee_output=True)
        queue_muxer_av1.set_related_tee(tee_audio_process)
        queue_speakersink = GstElement(
            "queue", "queue_speakersink", tee_output=True)
        queue_speakersink.set_related_tee(tee_audio_source)
        # Volume:
        self.source_volume = GstElement("volume", "source_volume")
        self.speaker_volume = GstElement("volume", "speaker_volume")
        self.speaker_volume.set_property("mute", True)  # Muted by default
        # VU-meter:
        audiolevel = GstElement("level", "audiolevel", tee_input=True)
        audiolevel.set_related_tee(tee_audio_source)
        audiolevel.set_property("interval", 200000000)
        # Encoder:
        vorbis_encoder = GstElement("vorbisenc",
                                    "vorbis_encoder",
                                    tee_input=True,
                                    tee_output=True)
        vorbis_encoder.related_tee_input = tee_audio_process  # TODO: use a setter instead
        vorbis_encoder.related_tee_output = tee_audio_source  # TODO: idem
        # Muxer:
        ogg_muxer = GstElement("oggmux", "ogg_muxer", tee_input=True)
        ogg_muxer.set_related_tee(tee_output_audio)
        # Sink:
        self.speaker_sink = GstElement("pulsesink", "speaker_sink")
        self.set_default_speaker_sink()
        self.speaker_sink.set_property("sync", False)

        source_branch = (self.source_volume, audiolevel, tee_audio_source)
        output_branch_encoding = (vorbis_encoder, tee_audio_process)
        output_branch_muxing = (queue_muxer_av1, ogg_muxer, tee_output_audio)
        output_branch_loudspeakers = (
            queue_speakersink, self.speaker_volume, self.speaker_sink)

        return (source_branch,
                output_branch_encoding,
                output_branch_muxing,
                output_branch_loudspeakers,
                tee_audio_process)

    def create_video_process(self):
        """
        Create Gst elements for video processing.

        Linking structure:
        <from video_source>---/capsfilter/---/videoscale/--->
        --->/image_overlay/---/text_overlay/--->
        --->/tee_video_source/
                 |---/queue/---/mkv_muxer/---/tee_output_video/
                 |                                |---<to output branches>
                 |---/screen_sink/
                 |---/vp8_encoder/--->
                  ---><to audiovideo processing (queue_muxer_video)>

        :return: a :class:`tuple` of branches

        :note: A ``tee`` element means the end of a branch. Then each output
            of this ``tee`` make a new branch that has to be returned.
        """
        # Tee:
        tee_video_source = GstElement("tee", "tee_video_source")
        tee_output_video = GstElement("tee", "tee_output_video",
                                      endpoint_tee=True)
        self._set_output_tee("video", tee_output_video)
        # Queue:
        queue_muxer_av2 = GstElement(
            "queue", "queue_muxer_av2", tee_output=True)
        queue_muxer_av2.set_related_tee(tee_video_source)
        # Caps:
        caps_string = ("video/x-raw,"
                       + "format=I420,"
                       + "width=1280,"  # TODO: adjust value
                       + "height=720,"  # TODO: adjust value
                       + "framerate=24/1")
        caps = Gst.caps_from_string(caps_string)
        capsfilter = GstElement("capsfilter", "capsfilter")
        capsfilter.set_property("caps", caps)
        # Image overlay:
        self.image_overlay = GstElement("gdkpixbufoverlay", "image_overlay")
        #self.image_overlay.set_property("location", DEFAULT_IMAGE)
        self.image_overlay.set_property("offset-x", -6)
        self.image_overlay.set_property("offset-y", 6)
        # Text overlay:
        self.text_overlay = GstElement(
            "textoverlay", "text_overlay", tee_input=True)
        self.text_overlay.set_related_tee(tee_video_source)
        self.text_overlay.set_property("valignment", "top")
        self.text_overlay.set_property("halignment", "left")
        self.text_overlay.set_property("font-desc", "Sans, 24")  # DEV
        # Converter:
        videorate = GstElement("videorate", "videorate")
        # Encoder:
        vp8_encoder = GstElement("vp8enc", "vp8_encoder", tee_output=True)
        vp8_encoder.set_related_tee(tee_video_source)
        #vp8_encoder.set_property("min_quantizer", 5)
        #vp8_encoder.set_property("max_quantizer", 13)
        vp8_encoder.set_property("cpu-used", 8)
        vp8_encoder.set_property("deadline", 1)
        vp8_encoder.set_property("threads", 2)
        #vp8_encoder.set_property("sharpness", 7)
        vp8_encoder.set_property('keyframe-max-dist', 120)
        vp8_encoder.set_property('target-bitrate', 2000000)
        # Muxer:
        mkv_muxer = GstElement("matroskamux", "mkv_muxer", tee_input=True)
        mkv_muxer.set_related_tee(tee_output_video)
        # Sink:
        screen_sink = GstElement("xvimagesink", "screen_sink", tee_output=True)
        screen_sink.set_related_tee(tee_video_source)
        screen_sink.set_property("sync", False)

        source_branch = (videorate, capsfilter, self.image_overlay,
                         self.text_overlay, tee_video_source,)
        output_branch_encoding = (vp8_encoder,)
        output_branch_muxing = (queue_muxer_av2, mkv_muxer, tee_output_video)
        output_branch_screen = (screen_sink,)

        return (source_branch,
                output_branch_encoding,
                output_branch_muxing,
                output_branch_screen,
                vp8_encoder)

    def create_audiovideo_process(self,
                                  audio_muxer_source,
                                  video_muxer_source):
        """
        Create Gst elements for audio + video
        processing.

        Linking structure:
        <from audio processing>---/queue/---
                                            |---/webmux/--->
        <from video processing>---/queue/---
        --->/tee_output_audiovideo/
                 |---<to output branches>

        :param audio_muxer_source: :class:`~core.gstelement.GstElement`
            providing audio feed
        :param video_muxer_source: :class:`~core.gstelement.GstElement`
            providing video feed

        :return: a :class:`tuple` of branches

        :note: A ``tee`` element means the end of a branch. Then each output
            of this ``tee`` make a new branch that has to be returned.
        """
        # Tee:
        tee_output_audiovideo = GstElement("tee", "tee_output_audiovideo",
                                           endpoint_tee=True)
        self._set_output_tee("audiovideo", tee_output_audiovideo)
        # Queue:
        if audio_muxer_source.element_kind == "tee":
            queue_muxer_audio = GstElement(
                "queue", "queue_muxer_audio", tee_output=True)
            queue_muxer_audio.set_related_tee(audio_muxer_source)
        else:
            queue_muxer_audio = GstElement(
                "queue", "queue_muxer_audio", parents=(audio_muxer_source,))

        if video_muxer_source.element_kind == "tee":
            queue_muxer_video = GstElement(
                "queue", "queue_muxer_video", tee_output=True)
            queue_muxer_video.set_related_tee(video_muxer_source)
        else:
            queue_muxer_video = GstElement(
                "queue", "queue_muxer_video", parents=(video_muxer_source,))
        # Muxer:
        webm_muxer = GstElement("webmmux",
                                "webm_muxer",
                                tee_input=True,
                                parents=(queue_muxer_audio,
                                         queue_muxer_video))
        webm_muxer.set_related_tee(tee_output_audiovideo)
        webm_muxer.set_property("streamable", True)

        source_audio = (queue_muxer_audio,)
        source_video = (queue_muxer_video,)
        output_branch_muxing = (webm_muxer, tee_output_audiovideo)

        return (source_audio, source_video, output_branch_muxing)


class Monitoring(Pipeline):
    """
    Class handling pipeline Gst elements for monitoring mode.
    """
    def __init__(self):
        self.pipeline = Gst.Pipeline()
        self.audio_sources = ()
        self.video_sources = ()

        (self.audio_process_source,
         self.audio_process_branch1,
         self.audio_stream_endpoint) = self.create_audio_process()
        (self.video_process_source,
         self.video_process_branch1,
         self.video_stream_endpoint) = self.create_video_process()
        self.transport_branch = self.create_transport_layer(
            self.audio_stream_endpoint, self.video_stream_endpoint)

        self.build_pipeline(self.pipeline,
                            self.audio_sources,  # DEBUG Needed to initiate `previous_item` during linking
                            self.audio_process_source,
                            self.audio_process_branch1,
                            #self.audio_process_branch2,  # DEBUG
                            self.video_process_source,
                            self.video_process_branch1,
                            self.transport_branch)

    def create_transport_layer(self, *parents):
        """
        Create Gst elements for transporting data over a
        netwwork to a controlroom app instance.

        Linking structure:
        <from audio_processing>---
                                  |---/funnel/---/tcpclientsink/---<to controlroom>
        <from video_processing>---

        :param parents: streams (audio and/or video) to send

        :return: a :class:`tuple` of :class:`~core.gstelement.GstElement`
        """
        funnel = GstElement("funnel", "", tee_output=True, parents=parents)
        #tcp_client_sink = GstElement("tcpclientsink", "tcp_client_sink")

        #return (funnel, tcp_client_sink)

        queue = GstElement("queue", "queue_leaky_test")  # DEBUG
        queue.set_property("leaky", 2)  # DEBUG
        return (funnel, queue)  # DEBUG

    def create_audio_process(self):
        """
        Create Gst elements for audio processing.

        Linking structure:
        <from audio_source>---/audiolevel/---/vorbis_encoder/--->
        --->/tee_audio_source/
                 |---<to transport_layer>
                 |---/queue/---/speaker_sink/

        :return: a :class:`tuple` of branches

        :note: A ``tee`` element means the end of a branch. Then each output
            of this ``tee`` make a new branch that has to be returned.
        """
        # Tee:
        tee_audio_source = GstElement("tee", "tee_audio_source")
        # Queue:
        queue_audio_filesink = GstElement("queue",
                                      "queue_audio_filesink",
                                      tee_output=True)
        queue_audio_filesink.set_related_tee(tee_audio_source)
        queue_audio_filesink.set_property("leaky", 2)  # DEBUG
        # VU-meter:
        audiolevel = GstElement("level", "audiolevel")
        audiolevel.set_property("interval", 200000000)
        # Encoder:
        vorbis_encoder = GstElement("vorbisenc",
                                    "vorbis_encoder",
                                    tee_input=True)
        vorbis_encoder.set_related_tee(tee_audio_source)
        # Sink:
        speaker_sink = GstElement("pulsesink", "speaker_sink", tee_output=True)
        speaker_sink.set_related_tee(tee_audio_source)
        speaker_sink.set_property("device", "/devices/pci0000:00/0000:00:1b.0/sound/card0")  #DEBUG
#        speaker_sink.set_property("device", "alsa_output.pci-0000_00_1b.0.analog-stereo")  # DEBUG
        speaker_sink.set_property("sync", False)

        filesink = GstElement("filesink", "file_sink_debug", tee_output=True)  # DEBUG
        filesink.set_related_tee(tee_audio_source)  # DEBUG
        filesink.set_property("location", "/tmp/test_audio_sink")  # DEBUG

        source_branch = (audiolevel, vorbis_encoder, tee_audio_source)
        #output_branch1 = (queue_audio_filesink, speaker_sink)  # DEBUG (see below)
        #output_branch1 = (queue_audio_filesink,)  # DEBUG
        #output_branch1 = (speaker_sink,)  # DEBUG (see below)
        output_branch1 = (filesink,)  # DEBUG (see below)

        return (source_branch, output_branch1, tee_audio_source)

    def create_video_process(self):
        """
        Create Gst elements for video processing.

        Linking structure:
        <from video_source>---/caps_filter/--->
        --->/tee_video_source/
                 |---<to transport_layer>
                 |---/screen_sink/

        :return: a :class:`tuple` of branches

        :note: A ``tee`` element means the end of a branch. Then each output
            of this ``tee`` make a new branch that has to be returned.
        """
        # Tee:
        tee_video_source = GstElement("tee", "tee_video_source")
        # Caps:
        caps_string = "video/x-raw," + "width=(int)1280," + "height=(int)720" + "framerate=(fraction)24/1"
        caps = Gst.caps_from_string(caps_string)
        capsfilter = GstElement("capsfilter", "capsfilter", tee_input=True)
        capsfilter.set_related_tee(tee_video_source)
        capsfilter.set_property("caps", caps)
        # Scaling:
        video_scale = GstElement("videoscale", "video_scale")
        # Sink:
        screen_sink = GstElement("xvimagesink", "screen_sink", tee_output=True)
        screen_sink.set_related_tee(tee_video_source)
        screen_sink.set_property("sync", False)

        source_branch = (video_scale, capsfilter, tee_video_source)
#        source_branch = (capsfilter, tee_video_source)  # DEBUG
        output_branch1 = (screen_sink,)

        return (source_branch, output_branch1, tee_video_source)

        def set_tcp_client_sink(self, host, port, **kargs):
            """
            Set needed values for tcpclientsink to send data to a tcpserversrc

            :param host: IP address as :class:`str` of controlroom server
            :param port: port number as :class:`int` the controlroom server is
                listening on
            """
            for element in self.transport_branch:
                if element.element_kind == "tcpclientsink":
                    tcp_client_sink = element
                    break
            else:
                raise TransportElementNotFound

            tcp_client_sink.set_property("host", host)
            tcp_client_sink.set_property("port", port)
            if kargs:
                for key, value in kargs:
                    tcp_client_sink.set_property(key, value)
