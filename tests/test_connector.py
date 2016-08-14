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
import phatty
import mido
from mido import Message
from mock import Mock
from mock import call
from phatty.connector import Connector

BAD_BANK_FILE_NAME = os.path.join(
    os.path.dirname(__file__), 'resources/preset.syx')
BANK_FILE_NAME = os.path.join(os.path.dirname(__file__), 'resources/bank.syx')
BULK_FILE_NAME = os.path.join(os.path.dirname(__file__), 'resources/bulk.syx')


class Test(unittest.TestCase):

    def setUp(self):
        self.connector = Connector()
        self.connector.port = Mock()

    def test_get_panel_as_preset(self):

        def return_value():
            return [i for i in range(0, 192)]

        self.connector.get_panel = Mock(side_effect=return_value)
        value = self.connector.get_panel_as_preset(37)
        self.connector.get_panel.assert_called_once()
        self.assertEqual(value[2], 0x5)
        self.assertEqual(value[4], 37)

    def test_get_panel(self):

        def return_value():
            return [i for i in range(0, 192)]

        self.connector.tx_message = Mock()
        self.connector.rx_message = Mock(side_effect=return_value)
        value = self.connector.get_panel()
        self.connector.tx_message.assert_called_once_with(
            phatty.connector.REQUEST_PANEL)
        self.connector.rx_message.assert_called_once()
        self.assertEqual(value, return_value())

    def test_get_preset(self):

        def return_value():
            return [i for i in range(0, 192)]

        self.connector.tx_message = Mock()
        self.connector.rx_message = Mock(side_effect=return_value)
        value = self.connector.get_preset(37)
        msg = []
        msg.extend(phatty.connector.REQUEST_PATCH)
        msg[phatty.connector.REQ_PATCH_BYTE] = 37
        self.connector.tx_message.assert_called_once_with(msg)
        self.connector.rx_message.assert_called_once()
        self.assertEqual(value, return_value())

    def test_set_preset(self):
        self.connector.port.send = Mock()
        self.connector.set_preset(37)
        msg = Message('program_change', channel=0, program=37)
        self.connector.port.send.assert_called_once_with(msg)

    def test_set_bulk(self):
        try:
            data = []
            data.extend(phatty.connector.BULK_START)
            data.extend([0] * (phatty.connector.BULK_SIZE -
                               len(phatty.connector.BULK_START)))
            self.connector.tx_message = Mock()
            self.connector.set_bulk(data)
            self.connector.tx_message.assert_called_once_with(data)
        except ValueError as e:
            self.assertTrue(False)

    def test_set_bulk_red(self):
        try:
            data = []
            data.extend(phatty.connector.BULK_START)
            data.extend([0] * (phatty.connector.RED_BULK_SIZE -
                               len(phatty.connector.BULK_START)))
            self.connector.tx_message = Mock()
            self.connector.set_bulk(data)
            self.connector.tx_message.assert_called_once_with(data)
        except ValueError as e:
            self.assertTrue(False)

    def test_set_bulk_fail(self):
        try:
            data = []
            self.connector.set_bulk(data)
            self.assertTrue(False)
        except ValueError as e:
            self.assertTrue(str(e) == phatty.connector.INVALID_BULK_FILE)

    def test_set_bank(self):
        try:
            data = []
            data.extend(phatty.connector.BANK_START)
            data.extend([0] * (phatty.connector.BANK_SIZE -
                               len(phatty.connector.BANK_START)))
            self.connector.tx_message = Mock()
            self.connector.set_bank(data)
            self.connector.tx_message.assert_called_once_with(data)
        except ValueError as e:
            self.assertTrue(False)

    def test_set_bank_red(self):
        try:
            data = []
            data.extend(phatty.connector.BANK_START)
            data.extend([0] * (phatty.connector.RED_BANK_SIZE -
                               len(phatty.connector.BANK_START)))
            self.connector.tx_message = Mock()
            self.connector.set_bank(data)
            self.connector.tx_message.assert_called_once_with(data)
        except ValueError as e:
            self.assertTrue(False)

    def test_set_bank_fail(self):
        try:
            data = []
            self.connector.set_bank(data)
            self.assertTrue(False)
        except ValueError as e:
            self.assertTrue(str(e) == phatty.connector.INVALID_BANK_FILE)

    def set_bank_from_file(self, filename):
        with open(filename, 'rb') as file:
            data = file.read()
            data = list(data[1:len(data) - 1])
            self.connector.set_bank = Mock()
            self.connector.set_bank_from_file(filename)
        self.connector.set_bank.assert_called_once_with(data)

    def test_set_bank_from_bank_file(self):
        self.set_bank_from_file(BANK_FILE_NAME)

    def test_set_bank_from_bulk_file(self):
        self.set_bank_from_file(BULK_FILE_NAME)

    def test_set_bank_from_bank_file_error(self):
        try:
            self.connector.set_bank = Mock(side_effect=ValueError)
            self.connector.set_bank_from_file(BAD_BANK_FILE_NAME)
            self.assertTrue(False)
        except ValueError:
            self.assertTrue(True)

    def test_save_bank_to_file(self):
        data = [1, 2, 3]
        filename = 'foo'
        messages = [Message('sysex', data=data)]
        mido.write_syx_file = Mock()
        self.connector.save_bank_to_file(filename, data)
        mido.write_syx_file.assert_called_once_with(filename, messages)

    def test_set_panel_name(self):
        name = 'ABCabc123'
        calls = []
        calls.append(call(
            Message('control_change', channel=0, control=119, value=0)))
        calls.append(call(
            Message('control_change', channel=0, control=66, value=19)))
        calls.append(call(
            Message('control_change', channel=0, control=66, value=15)))
        calls.append(call(
            Message('control_change', channel=0, control=66, value=13)))
        calls.append(call(
            Message('control_change', channel=0, control=66, value=1)))
        for c in name:
            calls.append(call(
                Message('control_change', channel=0, control=66, value=ord(c))))
        self.connector.port.send = Mock()
        self.connector.set_panel_name(name)
        self.connector.port.send.assert_has_calls(calls, any_order=False)

    def check_send_message(self, function, control, array):
        for i in range(0, len(array)):
            message = Message('control_change', channel=0,
                              control=control, value=array[i])
            self.connector.port.send = Mock()
            function(i)
            self.connector.port.send.assert_called_once_with(message)

    def test_set_lfo_midi_sync(self):
        self.check_send_message(
            self.connector.set_lfo_midi_sync, 102, phatty.connector.LFO_MIDI_SYNC_VALUES)

    def test_set_panel_filter_poles(self):
        self.check_send_message(
            self.connector.set_panel_filter_poles, 109, phatty.connector.FILTER_POLES_VALUES)

    def test_set_panel_vel_to_filter(self):
        self.check_send_message(
            self.connector.set_panel_vel_to_filter, 110, phatty.connector.VEL_TO_FILTER_VALUES)

    def test_set_panel_vel_to_amp(self):
        self.check_send_message(
            self.connector.set_panel_vel_to_amp, 92, phatty.connector.VEL_TO_AMP_VALUES)

    def test_set_panel_release(self):
        self.check_send_message(
            self.connector.set_panel_release, 88, phatty.connector.RELEASE_VALUES)

    def test_set_panel_scale(self):
        self.check_send_message(
            self.connector.set_panel_scale, 113, phatty.connector.SCALE_VALUES)

    def test_set_panel_pw_up_amount(self):
        self.check_send_message(
            self.connector.set_panel_pw_up_amount, 107, phatty.connector.PW_VALUES)

    def test_set_panel_pw_down_amount(self):
        self.check_send_message(
            self.connector.set_panel_pw_down_amount, 108, phatty.connector.PW_VALUES)

    def test_set_panel_legato(self):
        self.check_send_message(
            self.connector.set_panel_legato, 112, phatty.connector.LEGATO_VALUES)

    def test_set_panel_keyboard_priority(self):
        self.check_send_message(
            self.connector.set_panel_keyboard_priority, 111, phatty.connector.KEYBOARD_PRIORITY_VALUES)

    def test_set_panel_glide_on_legato(self):
        self.check_send_message(
            self.connector.set_panel_glide_on_legato, 94, phatty.connector.RELEASE_VALUES)

    def test_set_panel_mod_source_5(self):
        self.check_send_message(
            self.connector.set_panel_mod_source_5, 104, phatty.connector.MOD_SRC_5_VALUES)

    def test_set_panel_mod_source_6(self):
        self.check_send_message(
            self.connector.set_panel_mod_source_6, 105, phatty.connector.MOD_SRC_6_VALUES)

    def test_set_panel_mod_dest_2(self):
        self.check_send_message(
            self.connector.set_panel_mod_dest_2, 106, phatty.connector.MOD_DEST_2_VALUES)

    def test_set_panel_lfo_key_retrigger(self):
        self.check_send_message(
            self.connector.set_panel_lfo_key_retrigger, 93, phatty.connector.LFO_RETRIGGER_VALUES)

    def test_set_panel_arp_octaves(self):
        self.check_send_message(
            self.connector.set_panel_arp_pattern, 117, phatty.connector.ARP_PATTERN_VALUES)

    def test_set_panel_arp_mode(self):
        self.check_send_message(
            self.connector.set_panel_arp_mode, 118, phatty.connector.ARP_MODE_VALUES)

    def test_set_panel_arp_octaves(self):
        self.check_send_message(
            self.connector.set_panel_arp_octaves, 116, phatty.connector.ARP_OCTAVES_VALUES)

    def test_set_panel_arp_gate(self):
        self.check_send_message(
            self.connector.set_panel_arp_gate, 95, phatty.connector.ARP_GATE_VALUES)

    def test_set_panel_arp_clock_source(self):
        self.check_send_message(
            self.connector.set_panel_arp_clock_source, 114, phatty.connector.ARP_CLOCK_SOURCE_VALUES)

    def test_set_panel_arp_clock_division(self):
        self.check_send_message(
            self.connector.set_panel_arp_clock_division, 115, phatty.connector.ARP_CLOCK_DIVISION_VALUES)
