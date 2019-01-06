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

import unittest

from gui import status_bar


class TestStatusBar(unittest.TestCase):
    def setUp(self):
        self.status_bar = status_bar.StatusBar()

    def test_hboxes_are_hidden_by_default(self):
        # tester que les boxes sont non montrables via get_no_show_all()
        pass

    def test_add_watched_element(self):
        # tester que la box est bien montrable via get_no_show_all()
        pass

    def test_remove_watched_element(self):
        pass


class TestWatchedElement(unittest.TestCase):
    def setUp(self):
        self.status_bar = status_bar.StatusBar()
