HUBAngl Uses Broadcaster Angle
==============================

Overiew
-------
HUBAngl is a streaming client software. It is made simple so that related knowledge is not mandatory.

HUBAngl can be use in three different modes:
	1. standalone (since v0.1)
	2. control-room (soon)
	3. monitoring (soon)

Standalone mode
~~~~~~~~~~~~~~~
Fetch audio and/or video streams, process it and then it can be sent to a remote Icecast streaming server and/or store on the disk.
The streams broadcasted and stored can be either audio only, video only and audio+video or even all of them at once.

Control-room mode
~~~~~~~~~~~~~~~~~
Fetch streams from multiple remote HUBAngl instance working in monitoring mode. This mode is performing all the heavy processing, because of that the computer must be highly capable to deal with the CPU load in case of many streams to process.
Just like the standalone mode, it can then send streams to a remote Icecast streaming serverand/or store on the disk.

Monitoring mode
~~~~~~~~~~~~~~~
Fetch audio and/or video streams and sends it to a remote HUBAngl instance working in control-room mode. Almost no audio/video processing is done is this mode.

.. warning:: This is version 0.1, it is released only for feedback and basic debug purpose.
	  In its current development state, HUBAngl is not fully functional. Some key components are missing as well as nice features.

You must have a GNU/Linux distribution and Python v3.4 or greater in order to launch it (tested only on Trisquel 7 & 8). It uses GTK 3.X for the graphical user interface and GStreamer 1.X for dealing with streams.

Launch HUBAngl
--------------

.. code:: bash

	  $ ./hubangl


Happy Broadcasting
