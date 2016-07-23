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
from phatty.connector import Connector

BAD_BANK_FILE_NAME = os.path.join(
    os.path.dirname(__file__), 'resources/preset.syx')
BANK_FILE_NAME = os.path.join(os.path.dirname(__file__), 'resources/bank.syx')
BULK_FILE_NAME = os.path.join(os.path.dirname(__file__), 'resources/bulk.syx')


class Test(unittest.TestCase):

    def setUp(self):
        self.connector = Connector()

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

    def test_set_bank_from_bank_file(self):
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
