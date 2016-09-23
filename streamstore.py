#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-

# This file is part of ABYSS.
# ABYSS Broadcast Your Streaming Successfully 
#
# ABYSS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ABYSS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ABYSS.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (c) 2016 David Testé

"""
streamstore module provides classes to manage outputs of a feed.
It gets configuration information from the top level GUI by modifying
streaming dict and storing dict.

rgrprocess module accesses classes attributes so as to update pipeline.
"""

from gi.repository import Gst


# Dict keys:
AUDIO = 'audio'
VIDEO = 'video'
AUDIOVIDEO = 'audiovideo'
FORMAT = 'format'
LOCATION = 'location'
GSTELEM = 'gstelement'
SELECTED = 'selected'
# Default values:
FORMAT_AUDIO = None # HAS TO BE MODIFIED WHEN DEFAULT FORMAT IS KNOWN
FORMAT_VIDEO = None # HAS TO BE MODIFIED WHEN DEFAULT FORMAT IS KNOWN
FORMAT_AUDIOVIDEO = None # HAS TO BE MODIFIED WHEN DEFAULT FORMAT IS KNOWN
LOCATIONINIT = None
GSTINIT = None
SELECTEDINIT = False


class Streamfeed():
    def __init__(self):
        streaminfo = {AUDIO : {SELECTED : SELECTEDINIT,
                               FORMAT : FORMAT_AUDIO,
                               GSTELEM : GSTINIT},
                      VIDEO : {SELECTED : SELECTEDINIT,
                               FORMAT : FORMAT_VIDEO,
                               GSTELEM : GSTINIT},
                      AUDIOVIDEO : {SELECTED : SELECTEDINIT,
                                    FORMAT : FORMAT_AUDIOVIDEO,
                                    GSTELEM : GSTINIT},
                      LOCATION : LOCATIONINIT,}

    def get_stream_elem(self):
        return streaminfo

    def set_stream_elem(self, feedtype, newformat, *pargs, **kargs):
        """Used mainly to modify FORMAT value by dict update."""
        streaminfo.update()
        update_gstelem()
        pass


class Storefeed():
    def __init__(self):
        storeinfo = {AUDIO : {SELECTED : SELECTEDINIT,
                              FORMAT : FORMAT_AUDIO,
                              GSTELEM : GSTINIT},
                     VIDEO : {SELECTED : SELECTEDINIT,
                              FORMAT : FORMAT_VIDEO,
                              GSTELEM : GSTINIT},
                     AUDIOVIDEO : {SELECTED : SELECTEDINIT,
                                   FORMAT : FORMAT_AUDIOVIDEO,
                                   GSTELEM : GSTINIT},
                     LOCATION : LOCATIONINIT,}

    def get_store_elem(self):
        return storeinfo

    def set_store_elem(self, feedtype, newformat, *pargs, **kargs):
        """Used mainly to modify FORMAT value."""
        update_gstelem()
        pass

        
def update_gstelem():
    """Updates GSTELEM value by creating/removing a Gst element. """
    pass
