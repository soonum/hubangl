HUBAngl Uses Broadcaster Angle
==============================

Overiew
-------
HUBAngl is a streaming client software. It is made simple so that related knowledge is not mandatory.

How it works
~~~~~~~~~~~~
It fetches audio and/or video input streams, process them and then can be sent to a remote Icecast streaming server and/or store on the disk.
The streams that are broadcasted and stored can be either audio only, video only and audio+video or even all of them at once.

.. warning:: This is version 0.3, it is released only for feedback and basic debug purpose.
	  In its current development state, HUBAngl is not fully functional. Some key components are missing as well as nice features.

You must have a GNU/Linux distribution and Python v3.4 or greater in order to launch it (tested only on Trisquel 7 & 8). It uses GTK 3.X for the graphical user interface and GStreamer 1.X for dealing with streams.

Launch HUBAngl
--------------

.. code:: bash

	  $ ./src/hubangl

Loading a session configuration from a file is also possible.

.. code:: bash

	  $ ./src/hubangl -l <path_to_session_filename>.huba

.. warning:: Be very careful when saving a session to a file. Passwords to connect to Icecast servers are stored in **plain text**.

By default logging output will be printed to stdout, to avoid that use the option ``--quiet`` (or ``-q``). Log output can also be redirected in a file.

.. code:: bash

          $ ./src/hubangl -o <log_filename>

Happy Broadcasting
