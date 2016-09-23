#!/usr/bin/env python3.4
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

#######################################################################
# TODO:
# - Fetch inputs/output selection (from GUI)
# - 
#######################################################################
import time # -->[TEST]<--

import gi
from gi.repository import Gst
from gi.repository import GstVideo

from gi.repository import Gtk

import iofetch

Gst.init() # -->[DEBUG]<--

# Dict keys: 
CUR_ELEM = 'cur_elem'
NEW_ELEM = 'new_elem'
CUR_BIN = 'cur_bin'
CLASS = iofetch.CLASS
GSTELEM = iofetch.GSTELEM
AUDIO_IN = 'audio_in'
AUDIO_OUT = 'audio_out'
VIDEO_IN = 'video_in'
VIDEO_OUT = 'video_out' 
index_audio = 1
index_video = 1

all_audio_src = iofetch.find_audio() # -->[DEBUG]<--
all_video_src = iofetch.find_usbcam() # -->[DEBUG]<--

##print('\n-+-+-+- AUDIO SRC in rgrprocess -+-+-+-\n', all_audio_src) # -->[DEBUG]<--
##print('\n-+-+-+- VIDEO SRC in rgrprocess -+-+-+-\n', all_video_src) # -->[DEBUG]<--

    
def choose_audiosrc_elem(device, devname, *pargs, **kargs):
    """
    Creates an audio input Gst element (with a unique Gst ID) if not existing.

    Updates device's dict by set setting value of 'gstelement' at audiosrc.
    """
    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Have to handle the case of change of input feed ()
    #
    # --> There is probably a better way to update the state of the input
    #
    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    global index_audio
    srctype = device[iofetch.TYPE]
    gstelem = device[GSTELEM]
    klass = device[CLASS]
    tag = AUDIO_IN + str(index_audio)
    if gstelem:
        print('Gstreamer source element already created.')
    else:
        if srctype == iofetch.TYPE_IN:
            audiosrc = Gst.ElementFactory.make('pulsesrc', tag)
            audiosrc.set_property('device', devname)
            index_audio += 1
            field = {GSTELEM : audiosrc}
            u_msg = ' '.join(['New Gstreamer element created :', klass, srctype])
            iofetch.update_deviceinfo(device, field, update_msg=u_msg)
            return audiosrc
        
def choose_videosrc_elem(device, devname, *pargs, **kargs):
    """
    Creates a video input Gst element (with a unique Gst ID) if not existing.

    Updates device's dict by set setting value of 'gstelement' at videosrc.
    """
    global index_video
    videosrc = None
    srctype = device[iofetch.TYPE]
    gstelem = device[GSTELEM]
    comm_type = device[iofetch.COMM]
    klass = device[CLASS]
    tag = VIDEO_IN + str(index_video)

    if gstelem:
        print('Gstreamer source element already created.')
    else:
        if comm_type == iofetch.COMM_USB:
            videosrc = Gst.ElementFactory.make('v4l2src', tag)
            videosrc.set_property('device', devname)
        elif comm_type == iofetch.COMM_IP:
            videosrc = Gst.ElementFactory.make('rtspsrc', tag)
            # Here devname is an IPv4 address
            videosrc.set_property('location', devname)
        index_video += 1
        field = {GSTELEM : videosrc}
        u_msg = ' '.join(['New Gstreamer element created :', klass, srctype])
        iofetch.update_deviceinfo(device, field, update_msg=u_msg)
        return videosrc
        
    
def create_inputs_elem(*pargs, **kargs):
    """
    Creates inputs Gst elements.
    Feeds used are based on user choices.

    In v1.0, only 1 video and/or 1 audio input(s)
    must be passed as postionnal argument.

    Return a tuple of Gst elements.
    """
    audiosrc = None
    videosrc = None
    
    for devices in pargs:
        for name in devices:
            if devices[name][iofetch.CLASS] == iofetch.CLASS_AUDIO:
                audiosrc = choose_audiosrc_elem(devices[name], name,)
                if audiosrc: # [DEBUG]
                    ##print('GST ELEMENT:', audiosrc) # [DEBUG]
                    ##print('DEVICE NAME:', name) # [DEBUG]
                    print('DEVICE INFO:', devices[name]) # [DEBUG]
                    ##print('DEVICE CLASS:', devices[name][iofetch.CLASS]) # [DEBUG]
            elif devices[name][iofetch.CLASS] == iofetch.CLASS_VIDEO:
                videosrc = choose_videosrc_elem(devices[name], name,)
                if videosrc: # [DEBUG]
                    ##print('GST ELEMENT:', videosrc) # [DEBUG]
                    ##print('DEVICE NAME:', name) # [DEBUG]
                    print('DEVICE INFO:', devices[name]) # [DEBUG]
                    ##print('DEVICE CLASS:', devices[name][iofetch.CLASS]) # [DEBUG]
##    return audiosrc, videosrc

#create_inputs_elem(all_audio_src,all_video_src)

def create_formats_elem(*pargs, **kargs):
    pass

    
def build_bin(*pargs, **kargs):
    pass

    
def connect_bin(*pargs, **kargs):
    pass

    
def update_pipeline(*pargs, **kargs):
    pass

def get_connected_elem(pad):
    """
    Gets element connected to 'pad' in order to handle easily an element unlinking.
    
    Returns Gst.Element if there's any, None otherwise.
    """
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#  NOTE : May not work on 'tee' element, has to be tested before releasing
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    element = None
    if pad:
        linkedpad = pad.get_peer()
        if linkedpad:
            element = linkedpad.get_parent()
    return element 

def event_probe_cb(pad, info, user_data):
    """
    Callback handling event and allowing element replacement.
    """
    cur_elem = user_data[CUR_ELEM]
    new_elem = user_data[NEW_ELEM]
    cur_bin = user_data[CUR_BIN]
    info_pad = info
    info_event = info_pad.get_event()
    
    if (info_event is None) or (info_event.type != Gst.EventType.EOS):
#        print('[DEBUG] IN CONDTIONNAL STATEMENT')
        return Gst.PadProbeReturn.PASS
#    else: print('[DEBUG] EVENT IS EOS')

    Gst.Pad.remove_probe(pad, info_pad.id)
#    print('[DEBUG] PAD REMOVED')

    # Getting element context:
    elem_after = get_connected_elem(pad) # In v1.0 'pad' is most likely a srcpad:
    cur_elem = pad.get_parent()
    sinkpad = cur_elem.get_static_pad('sink')
    elem_before = get_connected_elem(sinkpad)

    #-------------------------------------
    # No need to change element's state to NULL before removing?
    # If so --> thread deadlock (has to be investigated and debugged)
    # ------------------------------------
#    cur_elem.set_state(Gst.State.NULL)
    print('[DEBUG] DONE SO FAR 1')
    cur_bin.remove(cur_elem)
    cur_bin.add(new_elem)
    if elem_before: elem_before.link(new_elem) # (doesn't apply for input feed)
    if elem_after: new_elem.link(elem_after) # (doesn't apply for screensink, filesink)
    new_elem.set_state(Gst.State.PLAYING)

    return Gst.PadProbeReturn.DROP
    
def pad_probe_cb(pad, info, user_data):
    """ Callback for blocking data flow between 2 or 3 elements"""

    BLOCK_PRB = Gst.PadProbeType.BLOCK
    EVENT_DOWNSTREAM_PRB = Gst.PadProbeType.EVENT_DOWNSTREAM
    
    #Gst_DEBUG_OBJECT(pad, 'pad is blocked now')

    # Remove the probe first
    Gst.Pad.remove_probe(pad, info.id)

    # Install new probe for EOS
#    cur_elem = user_data[0] # -->[DEBUG]<--
    cur_elem = user_data[CUR_ELEM]
    srcpad = Gst.Element.get_static_pad(cur_elem, 'src')
    Gst.Pad.add_probe(srcpad,
                      BLOCK_PRB or EVENT_DOWNSTREAM_PRB,
                      event_probe_cb,
                      user_data,)
                      #None)

    # Push EOS into the element, the probe will be fired when the
    # EOS leaves the element and it has thus drained all of its data
    sinkpad = Gst.Element.get_static_pad(cur_elem, 'sink')
    if sinkpad:
        Gst.Pad.send_event(sinkpad, Gst.Event.new_eos())
    else:
        cur_elem.send_event(Gst.Event.new_eos()) # In case of input change
    
    return Gst.PadProbeReturn.OK

def compare_formats(*pargs, **kargs):
    """
    Performs formats comparison between streaming and storing configurations.
    """
    pass


# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#  *** TEST BIN ***
# -----------------------------------------------------------------
class Testapp():

    def __init__(self):
        self.win = Gtk.Window()
        self.win.connect("delete_event",
                         lambda w,e: Gtk.main_quit())
        self.win.show_all()
        
    rproc = Gst.Pipeline()
    #rproc = Gst.ElementFactory.make('bin', 'process_bin')
    #rproc.set_state(Gst.State.NULL)
    
    testsrc = Gst.ElementFactory.make('videotestsrc', 'videosrc_1')
    rproc.add(testsrc)

    testsrc2 = Gst.ElementFactory.make('v4l2src', 'videosrc_2')
    testsrc2.set_property('device', '/dev/video0')

    videoconv = Gst.ElementFactory.make('videoconvert', 'conv')
    rproc.add(videoconv)
    testsrc.link(videoconv)

    screen = Gst.ElementFactory.make('xvimagesink', 'screensink')
    rproc.add(screen)
    videoconv.link(screen)

    rproc.set_state(Gst.State.PLAYING)

    time.sleep(1) # -->[DEBUG]<--
    print ('SLEEP FINISHED') # -->[DEBUG]<--
    #--------------------------------------------------------------------
    # HAS TO BE IMPLEMENTED PROPERLY
    #-------------------------------
    blockpad = testsrc.get_static_pad('src')
    user_data = {CUR_ELEM : testsrc, NEW_ELEM : testsrc2, CUR_BIN : rproc}
    #--------------------------------------------------------------------
    Gst.Pad.add_probe(blockpad,
                      Gst.PadProbeType.BLOCK_DOWNSTREAM,
                      pad_probe_cb,
                      user_data,)
    

Testapp()
Gtk.main()

