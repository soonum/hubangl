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
# Copyright (c) 2016-2019 David Testé

import collections
import concurrent.futures
import socket
import subprocess
import time


# Duration in seconds between to remote check wave.
REMOTE_CHECK_FREQUENCY = 5
# Duration after which we stop waiting for a reply from the server
REMOTE_PING_TIMEOUT = .5

Watchers = collections.namedtuple("Watchers", ["remote", "local"])
_watchers = ()
_executor = None


def setup():
    global _executor
    global _watchers
    _executor = concurrent.futures.ThreadPoolExecutor()
    _watchers = Watchers(RemoteWatcher(), LocalWatcher())

    for watcher in _watchers:
        watcher.start()


def shutdown():
    global _executor
    for watcher in _watchers:
        watcher.stop()

    _executor.shutdown()


def get_remote_watcher():
    """
    :return: current instance of :class:`~core.watch.RemoteWatcher`
    """
    return _watchers.remote if _watchers else None


def get_local_watcher():
    """
    :return: current instance of :class:`~core.watch.LocalWatcher`
    """
    return _watchers.local if _watchers else None


class RemoteWatcher:
    """
    Watch availability and health of remote elements such as streaming servers.
    """
    def __init__(self):
        self._watch_task = None
        self._shutting_down = False

        self._elements = {}  # Formatted as {address: RemoteElement}

    def start(self):
        """
        Start watching remote elements by checking on them at a fixed interval.
        """
        if self._watch_task:
            return

        self._watch_task = _executor.submit(self._check_availability)
        self._watch_task.add_done_callback(self._on_check_done)

    def stop(self):
        if self._shutting_down or not self._watch_task:
            return

        self._shutting_down = True
        self._watch_task.cancel()
        self._watch_task.done()
        self._watch_task = None

    def _check_availability(self):
        """
        This method is supposed to be run in an executor.
        """
        time.sleep(REMOTE_CHECK_FREQUENCY)
        for element in self._elements.values():
            element.ping()

    def _on_check_done(self, fut):
        if not self._shutting_down:
            self._watch_task = _executor.submit(self._check_availability)
            self._watch_task.add_done_callback(self._on_check_done)

    def add_watcher(self, address):
        """
        Add a watcher to the element represented by its ``address``.
        If a watcher has been previously set with ``address`` value, it won't
        create a new watcher.

        :param address: :class:`tuple` as ``(host, port)``

        :return: watched element
        """
        try:
            element = self._elements[address]
        except KeyError:
            element = self._elements[address] = RemoteElement(address)

        return element

    def remove_watcher(self, address):
        """
        Remove a watcher to the element represented by its ``address``.

        :param address: :class:`tuple` as ``(host, port)``

        :return: watched element or ``None`` if the element was not referenced
        """
        try:
            element = self._elements[address]
            del self._elements[address]
            return element
        except KeyError:
            pass


class LocalWatcher:
    """
    Watch availability of local resources such as free disk space.
    """
    # TODO: Need implementation
    def start(self):
        pass

    def stop(self):
        pass


class RemoteElement:
    """
    Represent a remote element that can be watched.

    :param address: :class:`tuple` as ``(host, port)``
    """
    def __init__(self, address):
        self._host = address[0]
        self._port = address[1]

        self._available = False
        self._unavailable_since = None
        # Can happend when a ping has failed and thus the availability of the
        # element cannot be garanteed.
        self._unknown_state = False
        self._host_running = False
        self._port_open = False
        # Latency in milliseconds measured during the last ping.
        self._latency = -1

        # nmap based ping command
        self._ping_command = ["nmap", "-p", str(self._port), self._host]

    @property
    def hostname(self):
        return socket.gethostbyaddr(self._host)[0]

    @property
    def port(self):
        return self._port

    @property
    def available(self):
        return self._available

    @property
    def unavailable_since(self):
        return self._unavailable_since

    @property
    def unknown_state(self):
        return self._unknown_state

    @property
    def host_running(self):
        return self._host_running

    @property
    def port_open(self):
        return self._port_open

    @property
    def latency(self):
        return self._latency

    def ping(self):
        """
        Ping the remote element and determine its availability.
        """
        try:
            proc = subprocess.run(self._ping_command,
                                  timeout=REMOTE_PING_TIMEOUT,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        except subprocess.TimeoutExpired:
            # TODO: Add logging like ->
            # logger.info("Server at {address:port} took more than {timeout} seconds to reply to ping")
            self._set_state(None, None, -1)
        else:
            result = self._parse_ping_result(proc.stdout, proc.stderr)
            self._set_state(*result)

    def _parse_ping_result(self, stdout, stderr):
        """
        Parse nmap command output.

        :param stdout: captured stdout from the ping subprocess
        :param stderr: captured stderr from the ping subprocess

        :return: three elements :class:`tuple`
        """
        if stderr:
            # TODO: Add logging like ->
            # logger.info("Unexepected error during ping %s" % stderr.decode())
            return None, None, -1

        host_running = False
        port_open = False
        latency = -1

        host_pattern = b"Host is up ("
        port_pattern = str(self._port).encode() + b"/"
        for line in stdout.split(b"\n"):
            if line.startswith(host_pattern):
                host_running = True
                latency = line.lstrip(host_pattern).rstrip(b"s latency).")
            elif line.startswith(port_pattern) and b"open" in line:
                port_open = True

        return host_running, port_open, float(latency) / 1000

    def _set_state(self, host_running, port_open, latency):
        """
        Determine if the element is available based on result of a ping.
        """
        if host_running is None or port_open is None:
            self._unknown_state = True
            return

        self._host_running = host_running
        self._port_open = port_open
        self._latency = latency

        if self._host_running and self._port_open:
            self._available = True
            self._unavailable_since = None
        else:
            self._available = False
            if not self._unavailable_since:
                self._unavailable_since = time.time()

    def get_state(self):
        """
        Retrieve the state of the element thus its availability.

        :return: :class:`dict` describing element's state
        """
        return {"available": self._available,
                "unavailable_since": self._unavailable_since,
                "unknown_state": self._unknown_state,
                "host_running": self._host_running,
                "port_open": self._port_open,
                "latency": self._latency}


class LocalElement:
    """
    Represent a local element that can be watched.
    """
    # TODO: need implementation
