# -*- coding: utf-8 -*-
#
# Copyright 2017 David García Goñi
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

PRESET_FILE_NAME = os.path.join(
    os.path.dirname(__file__), 'resources/preset.syx')
PRESET_NAME = 'MOOG STAGE II'
PRESET_NAME_NEW = 'FooBAr       '


class Test(unittest.TestCase):

    def test_get_name(self):
        with open(PRESET_FILE_NAME, 'rb') as input_file:
            p = bytearray(input_file.read())
            name = preset.get_name(p)
            self.assertTrue(name == PRESET_NAME)

    def test_set_name(self):
        with open(PRESET_FILE_NAME, 'rb') as input_file:
            p = bytearray(input_file.read())
            preset.set_name(p, PRESET_NAME_NEW)
            name = preset.get_name(p)
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
            preset.set_number(p, 7)
            number = preset.get_number(p)
            self.assertTrue(number == 7)

    def check_getter_and_setter(self, getter, setter, parameters):
        values = parameters[preset.PARAMETER_VALUES]
        databyte = parameters[preset.PARAMETER_DATABYTE]
        bitmask = parameters[preset.PARAMETER_BITMASK]
        with open(PRESET_FILE_NAME, 'rb') as input_file:
            p = bytearray(input_file.read())
            for i in range(0, len(values)):
                data_before = p[databyte]
                setter(p, i)
                value = getter(p)
                data_after = p[databyte]
                self.assertTrue(values[i] == value)
                self.assertTrue(data_before & ~bitmask ==
                                data_after & ~bitmask)

    def test_set_filter_poles(self):
        self.check_getter_and_setter(
            preset.get_filter_poles, preset.set_filter_poles, preset.FILTER_POLES_PARAMETERS)

    def test_set_vel_to_filter(self):

        def get_vel_to_filter_1(p):
            return (preset.get_vel_to_filter(p) & 0x18) >> 3

        def get_vel_to_filter_2(p):
            return preset.get_vel_to_filter(p) & 0x7

        self.check_getter_and_setter(
            get_vel_to_filter_1, preset.set_vel_to_filter, preset.VEL_TO_FILTER_PARAMETERS_1)
        self.check_getter_and_setter(
            get_vel_to_filter_2, preset.set_vel_to_filter, preset.VEL_TO_FILTER_PARAMETERS_2)

    def test_set_vel_to_amp(self):

        def get_vel_to_amp_1(p):
            return (preset.get_vel_to_amp(p) & 0x8) >> 3

        def get_vel_to_amp_2(p):
            return preset.get_vel_to_amp(p) & 0x7

        self.check_getter_and_setter(
            get_vel_to_amp_1, preset.set_vel_to_amp, preset.VEL_TO_AMP_PARAMETERS_1)
        self.check_getter_and_setter(
            get_vel_to_amp_2, preset.set_vel_to_amp, preset.VEL_TO_AMP_PARAMETERS_2)

    def test_set_release(self):
        self.check_getter_and_setter(
            preset.get_release, preset.set_release, preset.RELEASE_PARAMETERS)

    def test_set_scale(self):

        def get_scale_1(p):
            return (preset.get_scale(p) & 0x30) >> 4

        def get_scale_2(p):
            return preset.get_scale(p) & 0xf

        self.check_getter_and_setter(
            get_scale_1, preset.set_scale, preset.SCALE_PARAMETERS_1)
        self.check_getter_and_setter(
            get_scale_2, preset.set_scale, preset.SCALE_PARAMETERS_2)

    def test_set_pw_up_amount(self):
        self.check_getter_and_setter(
            preset.get_pw_up_amount, preset.set_pw_up_amount, preset.PW_UP_PARAMETERS)

    def test_set_pw_down_amount(self):
        self.check_getter_and_setter(
            preset.get_pw_down_amount, preset.set_pw_down_amount, preset.PW_DOWN_PARAMETERS)

    def test_set_legato(self):

        def get_legato_1(p):
            return (preset.get_legato(p) & 0x2) >> 1

        def get_legato_2(p):
            return preset.get_legato(p) & 0x1

        self.check_getter_and_setter(
            get_legato_1, preset.set_legato, preset.LEGATO_PARAMETERS_1)
        self.check_getter_and_setter(
            get_legato_2, preset.set_legato, preset.LEGATO_PARAMETERS_2)

    def test_set_keyboard_priority(self):
        self.check_getter_and_setter(
            preset.get_keyboard_priority, preset.set_keyboard_priority, preset.KEYBOARD_PRIORITY_PARAMETERS)

    def test_set_glide_on_legato(self):
        self.check_getter_and_setter(
            preset.get_glide_on_legato, preset.set_glide_on_legato, preset.GLIDE_ON_LEGATO_PARAMETERS)

    def test_set_mod_source_5(self):
        self.check_getter_and_setter(
            preset.get_mod_source_5, preset.set_mod_source_5, preset.MOD_SOURCE_5_PARAMETERS)

    def test_set_mod_source_6(self):
        self.check_getter_and_setter(
            preset.get_mod_source_6, preset.set_mod_source_6, preset.MOD_SOURCE_6_PARAMETERS)

    def test_set_mod_dest_2(self):
        self.check_getter_and_setter(
            preset.get_mod_dest_2, preset.set_mod_dest_2, preset.MOD_DEST_2_PARAMETERS)

    def test_set_lfo_retrigger(self):
        self.check_getter_and_setter(
            preset.get_lfo_key_retrigger, preset.set_lfo_key_retrigger, preset.LFO_RETRIGGER_PARAMETERS)

    def test_set_arp_pattern(self):

        def get_arp_pattern_1(p):
            return (preset.get_arp_pattern(p) & 0x2) >> 1

        def get_arp_pattern_2(p):
            return preset.get_arp_pattern(p) & 0x1

        self.check_getter_and_setter(
            get_arp_pattern_1, preset.set_arp_pattern, preset.ARP_PATTERN_PARAMETERS_1)
        self.check_getter_and_setter(
            get_arp_pattern_2, preset.set_arp_pattern, preset.ARP_PATTERN_PARAMETERS_2)

    def test_set_arp_mode(self):
        self.check_getter_and_setter(
            preset.get_arp_mode, preset.set_arp_mode, preset.ARP_MODE_PARAMETERS)

    def test_set_arp_octaves(self):

        def get_arp_octaves(p):
            return preset.ARP_OCTAVES_PARAMETERS[preset.PARAMETER_VALUES][preset.get_arp_octaves(p)]

        self.check_getter_and_setter(
            get_arp_octaves, preset.set_arp_octaves, preset.ARP_OCTAVES_PARAMETERS)

    def test_set_arp_gate(self):
        self.check_getter_and_setter(
            preset.get_arp_gate, preset.set_arp_gate, preset.ARP_GATE_PARAMETERS)

    def test_set_arp_clock_division(self):
        self.check_getter_and_setter(
            preset.get_arp_clock_division, preset.set_arp_clock_division, preset.ARP_CLOCK_DIVISION_PARAMETERS)
