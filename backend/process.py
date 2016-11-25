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
# Copyright (c) 2016 David Testé

from gi.repository import Gst
from gi.repository import Gtk

import iofetch
import ioelements
from exceptions import (GstElementInitError,
                        GstElementNotTeeIO,
                        TeePatchingError,
                        LinkingElementError,
                        AddingElementError,
                        NotAudioVideoSource,
                        NotStoreStreamSink,
                        ElementAlreadyAdded)


CUR_ELEM = None  # DEBUG
NEW_ELEM = None  # DEBUG
CUR_BIN = None  # DEBUG


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
                 parents=()):
        self.element_kind = element_kind
        if not name:
            name = element_kind
        self.name = name
        self.parents = parents
        try:
            self.gstelement = Gst.ElementFactory.make(self.element_kind,
                                                      self.name)
        except:
            raise GstElementInitError

        self.tee_input = tee_input
        self.tee_output = tee_output
        self.related_tee = None

        # #############################################################
        if tee_input and tee_output:
            pass
            #
            # Put here the case when an element is both input AND output of a tee
            #
        if self.element_kind == "tee":
            self.connected = False
            self.endpoint_tee = endpoint_tee

    def set_property(self, *args):
        """
        Provide ``GstElement`` interface to GStreamer set_property() method.
        """
        self.gstelement.set_property(*args)

    def set_related_tee(self, tee_element):
        """
        Refer GStreamer ``tee`` element that ``self`` has to be
        connected.

        :param tee_element: GStreamer ``tee`` element
        """
        if self.tee_input or self.tee_output:
            self.related_tee = tee_element
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


class Pipeline:
    """
    Class handling all GStreamer elements in a single bin.
    """
    def __init__(self,):
        self.pipeline = Gst.Pipeline()
        self.fakesink_counter = 0

        (self.audio_process_source,
         self.audio_process_branch1,
         self.audio_process_branch2,
         self.audio_muxer_source) = self.create_audio_process()
        print("AUDIO INIT...\tDONE")  # DEBUG

        (self.video_process_source,
         self.video_process_branch1,
         self.video_process_branch2,
         self.video_process_branch3,
         self.video_muxer_source) = self.create_video_process()
        print("VIDEO INIT...\tDONE")  # DEBUG

        (self.av_process_branch1,
         self.av_process_branch2,
         self.av_process_branch3) = self.create_audiovideo_process(
             self.audio_muxer_source,
             self.video_muxer_source)
        print("AV INIT...\tDONE")  # DEBUG

        self.audio_sources = ()
        self.video_sources = ()
        self.stream_sinks = ()
        self.store_sinks = ()

        self.build_pipeline(self.pipeline,
                            self.audio_sources,  # DEBUG use ??
                            self.video_sources,  # DEBUG use ??
                            self.audio_process_source,
                            self.audio_process_branch1,
                            self.audio_process_branch2,
                            self.video_process_source,
                            self.video_process_branch1,
                            self.video_process_branch2,
                            self.video_process_branch3,
                            self.av_process_branch1,
                            self.av_process_branch2,
                            self.av_process_branch3,  # FAIL
                            self.stream_sinks,  # DEBUG use ??
                            self.store_sinks)  # DEBUG use ??
        print("BUILDING...\tDONE")  # DEBUG

    def set_play_state(self):
        """
        Set pipeline instance to PLAYING state either to start
        or resuming broadcasting.
        """
        self.pipeline.set_state(Gst.State.PLAYING)

    def set_stop_state(self):
        """
        Set pipeline instance to NULL state and end broadcasting.
        """
        self.pipeline.set_state(Gst.State.NULL)

    def is_standingby(self):
        """
        Check if pipeline instance is in the right state to perform
        major change on a Gstreamer element.
        Major change mean ``device`` or ``location`` change.

        Return True if change(s) can be made on Gst element.
        """

    def update_gstelement(self, gstelement, update_type, update_value):
        assert self.is_standingby()

        if not (isinstance(ioelements.InputElement)
                or isinstance(ioelements.OutputElement)):
            return

        possible_update = ["device",
                           "location",
                           "path",
                           "ip",
                           "port",
                           "mount",
                           "password"]
        if update_type in possible_update:
            gstelement.change_settings(update_type, update_value)
        self.set_play_state()

    def get_blockpad(self, gstelement, pad_type="src"):
        return gstelement.get_static_pad(pad_type)

    def add_probe(pad, user_data, pad_probe_type=None):
        if not pad_probe_type:
            pad_probe_type = Gst.PadProbType.BLOCK_DOWNSTREAM
        return Gst.Pad.add_probe(pad,
                                 pad_probe_type,
                                 # self.pad_probe_cb,
                                 user_data)

    def get_connected_element(self, pad):
        """
        Gets element connected to 'pad' in order to handle
        easily an element unlinking.

        Returns Gst.Element if there's any, None otherwise.
        """
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #  NOTE : May not work on 'tee' element,
        #         has to be tested before releasing
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        element = None
        if pad:
            linkedpad = pad.get_peer()
            if linkedpad:
                element = linkedpad.get_parent()
            return element

    def event_probe_cb(self, pad, info, user_data):
        """
        Callback handling event and allowing element replacement.
        """
        current_element = user_data[CUR_ELEM]
        new_element = user_data[NEW_ELEM]
        current_bin = user_data[CUR_BIN]
        info_pad = info
        info_event = info_pad.get_event()

        if (info_event is None) or (info_event.type != Gst.EventType.EOS):
            return Gst.PadProbeReturn.PASS

        Gst.Pad.remove_probe(pad, info_pad.id)

        # Getting element context:
        element_after = self.get_connected_element(pad)  # In v1.0 "pad" is most likely a srcpad
        current_element = pad.get_parent()
        sinkpad = current_element.get_static_pad("sink")
        element_before = self.get_connected_element(sinkpad)

        # -------------------------------------
        # No need to change element's state to NULL before removing?
        # If so --> thread deadlock (has to be investigated and debugged)
        # ------------------------------------
        #    current_element.set_state(Gst.State.NULL)
        print("[DEBUG] DONE SO FAR 1")  # [DEBUG]
        current_bin.remove(current_element)
        current_bin.add(new_element)
        if element_before:
            element_before.link(new_element)  # (doesn't apply for input feed)
        if element_after:
            new_element.link(element_after)  # (doesn't apply for screensink, filesink)

        # Not sure about setting new_element in PLAYING state
        # Maybe call set_play_state
        new_element.set_state(Gst.State.PLAYING)

        return Gst.PadProbeReturn.DROP

    def pad_probe_cb(self, pad, info, user_data):
        """
        Callback for blocking data flow between 2 or 3 elements.
        """
        BLOCK_PRB = Gst.PadProbeType.BLOCK
        EVENT_DOWNSTREAM_PRB = Gst.PadProbeType.EVENT_DOWNSTREAM

        # Remove the probe first
        Gst.Pad.remove_probe(pad, info.id)

        # Install new probe for EOS
        current_element = user_data[CUR_ELEM]
        srcpad = Gst.Element.get_static_pad(current_element, "src")
        Gst.Pad.add_probe(srcpad,
                          BLOCK_PRB or EVENT_DOWNSTREAM_PRB,
                          self.event_probe_cb,
                          user_data,)

        # Push EOS into the element, the probe will be fired when the
        # EOS leaves the element and it has thus drained all of its data
        sinkpad = Gst.Element.get_static_pad(current_element, "sink")
        if sinkpad:
            Gst.Pad.send_event(sinkpad, Gst.Event.new_eos())
        else:
            # In case of input change
            current_element.send_event(Gst.Event.new_eos())

        return Gst.PadProbeReturn.OK

    def build_pipeline(self, pipeline, *branches):
        """
        Add and link GStreamer elements into ``pipeline``
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

        :param element: instance of :class:`GstElement`

        :return: Gstreamer element
        """
        return self.pipeline.get_by_name(element.name)

    def connect_tee(self,
                    tee_element,
                    input_element,
                    *output_elements):
        """
        Links input and outputs of a ``tee`` element.
        """
        input_element.link(tee_element)
        for output_element in output_elements:
            tee_element.link(output_element)

        tee_element.set_connected()

    def build_tee_connections(self, *branches):
        """
        Establish relation between a ``tee`` element and its related input and
        outputs. Then it perform the linking of the related elements by
        calling :func:`connect_tee`
        """
        tee_elements = []
        tee_input_elements = []
        tee_output_elements = []
        previous_item = None

        for branche in branches:
            for item in branche:
                if item.element_kind == "tee":
                    tee_elements.append(item)
                    continue
                if item.related_tee:
                    if item.tee_input:
                        tee_input_elements.append(item)
                    elif item.tee_output:
                        tee_output_elements.append(item)

        for tee in tee_elements:
            self.print_gst("TEE", 0, tee)  # DEBUG
            # Definig the tee input
            for element in tee_input_elements:
                if element.related_tee.name == tee.name:
                    _input_element = element
                    self.print_gst("\tINPUT elem", 2, _input_element)  # DEBUG
                    break

            _output_elements = []
            # Definig the tee output(s)
            for element in tee_output_elements:
                if element.related_tee.name == tee.name:
                    _output_elements.append(element)

            if tee.endpoint_tee and not _output_elements:
                fakesink = self.make_fakesink(tee, self.pipeline)
                _output_elements.append(fakesink)

            self.print_gst("\tOUTPUT elem", 2, *_output_elements)  # DEBUG

            if not (_input_element and _output_elements):
                raise TeePatchingError

            self.connect_tee(tee, _input_element, *_output_elements)

    def make_queue(self, tee_element):
        """
        Create ``queue`` GStreamer element used for ###########################################################################################################################################################################################################################

        :param tee_element: endpoint ``tee`` element

        :return: ``queue`` GStramer element
        """
        queue_name = "queue" + str(self.fakesink_counter)
        return queue
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
        fakesink_name = "fakesink" + str(self.fakesink_counter)
        self.fakesink_counter += 1
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
            if not branch:
                continue
            for element in branch:
                if self._exist_in_pipeline(element):
                    raise ElementAlreadyAdded
                try:
                    pipeline.add(element.gstelement)
                    print("Element added -->", element.name)
                except:
                    raise AddingElementError

    def link_elements(self, *branches):
        """
        Link GStreamer elements in the pipeline.

        :param *branches:

        :note: ``tee`` elements MUST be linked with their input/outputs before
            any other GStreamer elements. Otherwise it could fail to link
            ``tee`` sources because of ``caps`` incompatibility
        """
        self.build_tee_connections(*branches)

        for branche in branches:
            for item in branche:
                if item.element_kind == "tee":
                    previous_item = None
                    continue
                if item.parents:
                    for parent in item.parents:
                        parent.link(item)
                    continue
                if not previous_item:
                    previous_item = item
                    # Must exist before any linking attempt.
                    continue

                previous_item.link(item)
                previous_item = item
            else:
                # End of branch
                previous_item = None

    def print_gst(self, msg, indent, *elements):
        """
        Debugging function.
        Print the name of each element.
        """
        indent_str = "\t" * indent
        print(msg)
        for element in elements:
            print(indent_str, "\_", element.name)

    def set_input_source(self, source_element):
        """
        Add a audio/video source input to the pipeline.

        :param source_element: audio/video input Gstreamer element to add
        """
        source_gstelement = source_element.gstelement

        if self._exist_in_pipeline(source_gstelement):
            raise ElementAlreadyAdded

        if isinstance(source_element, ioelements.AudioInput):
            self.add_elements(self.pipeline, (source_gstelement,))
            source_gstelement.link(self.audio_process_source[0])
        elif isinstance(source_element, ioelements.VideoInput):
            self.add_elements(self.pipeline, (source_gstelement,))
            source_gstelement.link(self.video_process_source[0])
        else:
            raise NotAudioVideoSource

    def set_output_sink(self, sink_element):
        """
        Add a streaming/storing sink to the pipeline.

        :param sink_element: stream/store Gstreamer element to add
        """
        sink_gstelement = sink_element.gstelement

        if self._exist_in_pipeline(sink_gstelement):
            raise ElementAlreadyAdded

        if isinstance(sink_element, ioelements.StoreElement):
            # 1- Créer un élément de queue associé :
            # SPAM
            # 2- Setter le tee relatif à l'élément :
            # EGGS
            # 3- Ajouter les élements dans le pipeline :
            self.add_elements(self.pipeline, (sink_gstelement,))
            # Trouver un moyen de linker les éléments par rapport à la branche
            # Audio ? Video ? Audio-Video ? (passer l'élement à raccorder
            # en argument?) :
            sink_gstelement.link(self.SPAMEGGSHAM)
        elif isinstance(sink_element, ioelements.StreamElement):
            pass
        else:
            NotStoreStreamSink

    def create_audio_process(self,):
        """
        Create, add and link Gst elements for audio processing.

        Linking structure:
        <from audio_source>---/audiolevel/---/vorbis_encoder/--->
        --->/tee_audio_source/
                 |---/queue/---/ogg_muxer/---/tee_output_audio/
                 |                                |---<to output_elements>
                 |---/queue/---/speaker_sink/
                 |---<to audiovideo processing (queue_muxer_av1)>

        :return: a :class:`tuple` of branches

        :note: A ``tee`` element means the end of a branch. Then each output
            of this ``tee`` make a new branch that has to be returned.
        """
        # Tee :
        tee_audio_source = GstElement("tee", "tee_audio_source")
        tee_output_audio = GstElement("tee",
                                      "tee_output_audio",
                                      endpoint_tee=True)
        # Queue :
        queue_muxer_a = GstElement("queue", "queue_muxer_a", tee_output=True)
        queue_muxer_a.set_related_tee(tee_audio_source)
        queue_audio_sink = GstElement("queue",
                                      "queue_audio_sink",
                                      tee_output=True)
        queue_audio_sink.set_related_tee(tee_audio_source)
        # Plugin :
        audiolevel = GstElement("level", "audiolevel")
        audiolevel.set_property("interval", 200000000)
        # Encoder :
        vorbis_encoder = GstElement("vorbisenc",
                                    "vorbis_encoder",
                                    tee_input=True)
        vorbis_encoder.set_related_tee(tee_audio_source)
        # Muxer :
        ogg_muxer = GstElement("oggmux", "ogg_muxer", tee_input=True)
        ogg_muxer.set_related_tee(tee_output_audio)
        # Sink :
        speaker_sink = GstElement("pulsesink", "speaker_sink", tee_output=True)
        speaker_sink.set_related_tee(tee_audio_source)
        speaker_sink.set_property("device", "/devices/pci0000:00/0000:00:1b.0/sound/card0")  #DEBUG
#        speaker_sink.set_property("device", "alsa_output.pci-0000_00_1b.0.analog-stereo")  # DEBUG
        speaker_sink.set_property("sync", False)

        source_branch = (audiolevel, vorbis_encoder, tee_audio_source)
        output_branch1 = (queue_muxer_a, ogg_muxer, tee_output_audio)
        #output_branch2 = (queue_audio_sink, speaker_sink)  # DEBUG (see below)
        output_branch2 = ()  # DEBUG

        return (source_branch,
                output_branch1,
                output_branch2,
                tee_audio_source)

    def create_video_process(self,):
        """
        Create, add and link Gst elements for video processing.

        Linking structure:
        <from video_source>---/caps_filter/--->
        --->/tee_video_source/
                 |---/queue/---/mkv_muxer/---/tee_output_video/
                 |                                |---<to output_elements>
                 |---/screen_sink/
                 |---/vp8_encoder/---<to audiovideo processing (queue_muxer_av2)>

        :return: a :class:`tuple` of branches

        :note: A ``tee`` element means the end of a branch. Then each output
            of this ``tee`` make a new branch that has to be returned.
        """
        # Tee :
        tee_video_source = GstElement("tee", "tee_video_source")
        tee_output_video = GstElement("tee",
                                      "tee_output_video",
                                      endpoint_tee=True)
        # Queue :
        queue_muxer_v = GstElement("queue", "queue_muxer_v", tee_output=True)
        queue_muxer_v.set_related_tee(tee_video_source)
        # Caps :
        caps_string = "video/x-raw," + "width=(int)640," + "height=(int)360"
        caps = Gst.caps_from_string(caps_string)
        capsfilter = GstElement("capsfilter", "capsfilter", tee_input=True)
        capsfilter.set_related_tee(tee_video_source)
        capsfilter.set_property("caps", caps)
        # Scaling:
        video_scale = GstElement("videoscale", "video_scale")
        videoconvert = GstElement("videoconvert", "videoconvert")  # DEBUG
        # Encoder :
        vp8_encoder = GstElement("vp8enc", "vp8_encoder", tee_output=True)
        vp8_encoder.set_related_tee(tee_video_source)
        vp8_encoder.set_property("min_quantizer", 1)
        vp8_encoder.set_property("max_quantizer", 13)
        vp8_encoder.set_property("cpu-used", 5)
        vp8_encoder.set_property("deadline", 1)
        vp8_encoder.set_property("threads", 2)
        vp8_encoder.set_property("sharpness", 7)
        # Muxer :
        mkv_muxer = GstElement("matroskamux", "mkv_muxer", tee_input=True)
        mkv_muxer.set_related_tee(tee_output_video)
        # Sink :
        screen_sink = GstElement("xvimagesink", "screen_sink", tee_output=True)
        screen_sink.set_related_tee(tee_video_source)
        screen_sink.set_property("sync", False)

        source_branch = (video_scale, capsfilter, tee_video_source,)
#        source_branch = (capsfilter, tee_video_source)  # DEBUG
        output_branch1 = (vp8_encoder,)
        output_branch2 = (queue_muxer_v, mkv_muxer, tee_output_video)
        output_branch3 = (screen_sink,)

        return (source_branch,
                output_branch1,
                output_branch2,
                output_branch3,
                vp8_encoder)

    def create_audiovideo_process(self,
                                  audio_muxer_source,
                                  video_muxer_source):
        """
        Create, add and link Gst elements for audio + video
        processing.

        Linking structure:
        <from audio processing>---/queue/---
                                            |---/webmux/--->
        <from video processing>---/queue/---
        --->/tee_output_audiovideo/
                 |---<to output_elements>

        :return: a :class:`tuple` of branches

        :note: A ``tee`` element means the end of a branch. Then each output
            of this ``tee`` make a new branch that has to be returned.
        """
        # Tee :
        tee_output_audiovideo = GstElement("tee",
                                           "tee_output_audiovideo",)
#                                           endpoint_tee=True)  # DEBUG
        # Queue :
        queue_muxer_av1 = GstElement("queue",
                                     "queue_muxer_av1",
                                     tee_output=True)
        queue_muxer_av1.set_related_tee(audio_muxer_source)
        queue_muxer_av2 = GstElement("queue",
                                     "queue_muxer_av2",
                                     tee_output=True)
        queue_muxer_av2.set_related_tee(video_muxer_source)
        queue_endpoint = GstElement("queue", "queue_endpoint", tee_output=True)  # DEBUG
        queue_endpoint.set_related_tee(tee_output_audiovideo)  # DEBUG 
        # Muxer :
        webm_muxer = GstElement("webmmux",
                                "webm_muxer",
                                tee_input=True,
                                parents=(queue_muxer_av1,
                                         queue_muxer_av2))
        webm_muxer.set_related_tee(tee_output_audiovideo)
        webm_muxer.set_property("streamable", True)

        branch1 = (queue_muxer_av1,)
        branch2 = (queue_muxer_av2,)
        branch3 = (webm_muxer, tee_output_audiovideo, queue_endpoint)  # DEBUG

        return (branch1, branch2, branch3)


class Monitoring(Pipeline):
    """
    Class handling pipeline Gst elements for monitoring mode.
    """
    def __init__(self):
        self.pipeline = Gst.Pipeline()

# --------------------------------------------------------------------
# HAS TO BE IMPLEMENTED PROPERLY
# -------------------------------
# blockpad = testsrc.get_static_pad("src")
# user_data = {CUR_ELEM : testsrc, NEW_ELEM : testsrc2, CUR_BIN : rproc}
# --------------------------------------------------------------------
# Gst.Pad.add_probe(blockpad,
#                  Gst.PadProbeType.BLOCK_DOWNSTREAM,
#                  pad_probe_cb,
#                  user_data)


def on_message(self, bus, message):
    t = message.type
    if t == Gst.MessageType.EOS:
        self.streampipe.set_state(Gst.State.NULL)
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print (ERROR, '%s' % err, debug)

if __name__ == "__main__":
    # basic unittest for debbuging Pipeline class
    Gst.init()

    # Microphone init
    audio_devices = iofetch.find_audio()
    for key in audio_devices:
        # Get the built-in microphone
        if audio_devices[key]["type"] == "input" and "hdmi" not in key:
            a_device = key
            break

    microphone = ioelements.AudioInput("Empty description", a_device)
    print("AUDIO INPUT SOURCE (", a_device, ") ... \t DONE", sep="")

    # Camera init
    usbcam_devices = iofetch.find_usbcam()
    #if len(usbcam_devices) > 1:
    for key in usbcam_devices:
        # Try not to get built-in usb cam
        if usbcam_devices[key]["description"] != "TOSHIBA Web Camera":
            v_device = key
            break
    else:
        v_device = key

    usbcam = ioelements.VideoInput("Empty description",
                                   "usb",
                                   v_device,)
    print("VIDEO INPUT SOURCE (", v_device, ") ... \t DONE", sep="")

    testpipeline = Pipeline()

    testpipeline.set_input_source(usbcam)
    testpipeline.set_input_source(microphone)
    print("SOURCES ADDED to pipeline ... \tDONE")

    bus = testpipeline.pipeline.get_bus()
    bus.add_signal_watch()
    bus.enable_sync_message_emission()
    # Used to get messages that GStreamer emits.
    bus.connect("message", on_message)

    testpipeline.set_play_state()

    class Testapp():
        def __init__(self,):
            self.win = Gtk.Window()
            self.win.connect("delete_event",
                             lambda w,e: Gtk.main_quit())
            self.win.show_all()

    Testapp()
    Gtk.main()
