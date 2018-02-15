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
# Copyright (c) 2016-2017 David Testé

"""
audio_displays
--------------

Provide audio visualization tools.
"""

import math


class AudioLevelDisplay(object):
    """
    Display a Level-Meter.

    :param drawing_area: :class:`Gtk.DrawingArea`
    """
    def __init__(self, drawing_area):
        self.drawing_area = self._prepare_drawingarea(drawing_area)

        self.level_rms = []
        self.level_peak = []
        self.level_decay = []

        self._decay_marker_width = 2
        # Margin between channels
        self._margin = 2

    def _prepare_drawingarea(self, drawing_area):
        drawing_area.set_size_request(24, -1)
        drawing_area.connect('draw', self.on_draw)
        return drawing_area

    def _normalize_db(self, db_value):
        """
        Normalize ``db_value`` following a decimal log scale.

        :param db_value: decibel value

        :return: normalized dB value
        """
        # -60db -> 1.00 (very quiet)
        # -30db -> 0.75
        # -15db -> 0.50
        #  -5db -> 0.25
        #  -0db -> 0.00 (very loud)
        logscale = 1 - math.log10(-0.15 * db_value + 1)
        return logscale

    def _get_channel_width(self, width, channels):
        """
        Get channel width in pixel.

        :param width: allocated width of :attr:`drawing_area`
        :param channels: total available audio channels as :class:`int`

        :return: channel width as :class:`int`
        """
        margins_width = self._margin * (channels - 1)
        return int((width - margins_width) / channels)

    def _get_brightness_value(self, y_position, channel):
        """
        Get the brightness of a pixel to draw.

        :param y_position: vertical position of the pixel
        :param channel: channel to draw on as :class:`int`

        :return: pixel brightness
        """
        # Default is dark
        brightness = 0.25
        if int(y_position - self.decay_px[channel]) in range(
                0, self._decay_marker_width):
            # Decay marker, extra bright
            brightness = 1.5
        elif y_position < self.rms_px[channel]:
            # RMS bar, full bright
            brightness = 1
        elif y_position < self.peak_px[channel]:
            # Peak bar, a little darker
            brightness = 0.75

        return brightness

    def _set_line_color(self, cairo_context, color, brightness):
        """
        Set the color for the audio level line to draw.

        :param cario_context: cairo context to draw to
        :param color: pixel color
        :param brightness: pixel brightness
        """
        cairo_context.set_source_rgb(color * brightness,
                                     (1 - color) * brightness * 0.75,
                                     0)

    def _draw_margin_line(self, cairo_context, x_position, y_position, width,
                          height):
        """
        Draw a black line for the margin.

        :param cario_context: cairo context to draw to
        :param x_position: horizontal position of the pixel
        :param y_position: vertical position of the pixel
        :param width: channel width
        :param height: channel height
        """
        cairo_context.set_source_rgb(0, 0, 0)
        cairo_context.move_to(x_position + width, height - y_position)
        cairo_context.line_to(x_position + width + self._margin,
                              height - y_position)
        cairo_context.stroke()

    def _draw_level_line(self, cairo_context, x_position, y_position, width,
                         height):
        """
        Draw a line for the audio level.

        :param cario_context: cairo context to draw to
        :param x_position: horizontal position of the pixel
        :param y_position: vertical position of the pixel
        :param width: channel width
        :param height: channel height
        """
        # Set the line-width > 1, to get a nice overlap
        cairo_context.set_line_width(2)

        cairo_context.move_to(x_position, height - y_position)
        cairo_context.line_to(x_position + width, height - y_position)
        cairo_context.stroke()

    def on_draw(self, widget, cairo_context):
        """
        Callback for rendering ``widget``.

        :param widget: :class:`Gtk.Widget` which received the signal
        :param cairo_context: cairo context to draw to

        :return: ``True`` to stop other handlers from being invoked for the
            event. ``False`` to propagate the event further.
        """
        channels = len(self.level_rms)
        if channels == 0:
            return False

        width = self.drawing_area.get_allocated_width()
        height = self.drawing_area.get_allocated_height()
        channel_width = self._get_channel_width(width, channels)

        self.rms_px = [self._normalize_db(db) * height
                       for db in self.level_rms]
        self.peak_px = [self._normalize_db(db) * height
                        for db in self.level_peak]
        self.decay_px = [self._normalize_db(db) * height
                         for db in self.level_decay]

        # Iterate over all pixels
        for y in range(0, height):
            # calculate our place in the color-gradient, clamp to 0…1
            # 0 -> green, 0.5 -> yellow, 1 -> red
            color = ((y / height) - 0.6) / 0.42

            for channel in range(0, channels):
                # start-coordinate for this channel
                x = (channel * channel_width) + (channel * self._margin)

                self._set_line_color(cairo_context, color,
                                     self._get_brightness_value(y, channel))
                self._draw_level_line(cairo_context, x, y, channel_width,
                                      height)
                self._draw_margin_line(cairo_context, x, y, channel_width,
                                       height)

        return True

    def on_level(self, rms, peak, decay):
        """
        :param rms: an iterable representing RMS dB values
        :param peak: an iterable representing peak dB values
        :param decay: an iterable representing decay dB values
        """
        self.level_rms = rms
        self.level_peak = peak
        self.level_decay = decay
        self.drawing_area.queue_draw()
