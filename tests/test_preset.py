# -*- coding: utf-8 -*-
#
# Copyright 2016 David García Goñi
#
# This file is part of Phatty.
#
# Phatty is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Phatty is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Phatty. If not, see <http://www.gnu.org/licenses/>.

import unittest
import os
from phatty import preset

PRESET_FILE_NAME = os.path.join(os.path.dirname(__file__), 'resources/preset.syx')
PRESET_NAME = 'MOOG STAGE II'
PRESET_NAME_NEW = 'FooBAr       '

class Test(unittest.TestCase):

    def test_get_name(self):
        with open(PRESET_FILE_NAME, 'rb') as input_file:
            p = bytearray(input_file.read())
            name = preset.get_preset_name(p)
            self.assertTrue(name == PRESET_NAME)

    def test_set_name(self):
        with open(PRESET_FILE_NAME, 'rb') as input_file:
            p = bytearray(input_file.read())
            preset.set_preset_name(p, PRESET_NAME_NEW)
            name = preset.get_preset_name(p)
            self.assertTrue(name == PRESET_NAME_NEW)

    def test_normalize_name(self):
        name = preset.normalize_name('asdf.')
        self.assertTrue(name == 'asdf?        ')

    def test_normalize_name2(self):
        name = preset.normalize_name('1234567890asdf')
        self.assertTrue(name == '1234567890asd')

    def test_set_preset_number(self):
        with open(PRESET_FILE_NAME, 'rb') as input_file:
            p = bytearray(input_file.read())
            preset.set_preset_number(p, 7)
            number = preset.get_preset_number(p)
            self.assertTrue(number == 7)
