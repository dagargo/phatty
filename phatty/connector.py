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

"""Phatty connector"""

import mido
from mido import Message
import logging
import time

logger = logging.getLogger(__name__)

INIT_MSG = [0x7E, 0x7F, 6, 1]
PHATTY_MSG_WO_VERSION = [0x7e, 0x7f, 6, 2, 4, 0, 5, 0, 1]
REQUEST_PATCH = [4, 5, 6, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
REQUEST_BANK = [4, 5, 6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
REQUEST_BULK = [4, 5, 6, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
BANK_START = [4, 5, 1, 3]
BANK_START_I = [4, 5, 1, 3, 0]
BANK_START_II = [4, 5, 1, 3, 1]
BANK_START_WHITE = [4, 5, 1, 3, 2]
BULK_START = [4, 5, 3, 1]
BULK_START_II = [4, 5, 3, 1, 1]
REQ_PATCH_BYTE = 4
MAX_PRESETS = 100
RED_BANK_SIZE = 17142
BANK_SIZE = RED_BANK_SIZE + 202
RED_BULK_SIZE = RED_BANK_SIZE + 133
BULK_SIZE = RED_BULK_SIZE + 202
INVALID_BANK_FILE = 'Invalid bank file'
INVALID_BULK_FILE = 'Invalid bulk file'
HANDSHAKE_MSG = 'Handshake ok. Version {:s}.'
LPII_DEVICE_NAME = 'Little Phatty SE II 20:0'
MAX_DATA = 25
MSG_LEN = 64
SLEEP_TIME = 0.02

mido.set_backend('mido.backends.rtmidi')
logger.debug('Mido backend: {:s}'.format(str(mido.backend)))


class Connector(object):
    """Phatty connector"""

    def __init__(self):
        logger.debug('Initializing...')
        self.port = None

    def connected(self):
        return self.port != None

    def disconnect(self):
        """Disconnect from the Phatty."""
        if self.port:
            logger.debug('Disconnecing...')
            self.port.close()
            self.port = None

    def send(self, message):
        if message.type == 'sysex':
            data = message.bytes()
            for d in [data[i:i + MSG_LEN] for i in range(0, len(data), MSG_LEN)]:
                logger.debug('Sending message {:s}...'.format(
                    self.get_hex_data(d)))
                self.port.output._rt.send_message(d)
                time.sleep(SLEEP_TIME)
        else:
            self.port.output._rt.send_message(message.bytes())

    def connect(self, device):
        """Connect to the Phatty."""
        logger.debug('Connecting...')
        try:
            self.port = mido.open_ioport(device)
            self.port._send = self.send
            logger.debug('Handshaking...')
            self.tx_message(INIT_MSG)
            response = self.rx_message()
            if response[0:9] == PHATTY_MSG_WO_VERSION:
                self.sw_version = '.'.join([str(i) for i in response[9:13]])
                logger.debug(HANDSHAKE_MSG.format(self.sw_version))
            else:
                logger.debug('Bad handshake. Disconnecting...')
                self.disconnect()
        except IOError as e:
            logger.error('IOError while connecting')

    def get_preset(self, num):
        msg = []
        msg.extend(REQUEST_PATCH)
        msg[REQ_PATCH_BYTE] = num
        self.tx_message(msg)
        return self.rx_message()

    def tx_message(self, data):
        msg = Message('sysex', data=data)
        logger.debug('Sending message {:s}...'.format(self.get_hex_data(data)))
        self.port.send(msg)

    def rx_message(self):
        data_array = []
        msg = self.port.receive()
        while msg.type != 'sysex':
            msg = self.port.receive()
        data = msg.data
        logger.debug('Receiving message {:s}...'.format(
            self.get_hex_data(data)))
        data_array.extend(data)
        return data_array

    def get_hex_data(self, data):
        if len(data) > MAX_DATA:
            data = data[0:MAX_DATA]
        s = ', '.join([hex(i) for i in data])
        if len(data) > MAX_DATA:
            s += '[...]'
        return s

    def set_preset(self, id):
        msg = Message('program_change', channel=0, program=id)
        logger.debug('Sending program change {:d}...'.format(id))
        self.port.send(msg)

    def get_bank(self):
        self.tx_message(REQUEST_BANK)
        return self.rx_message()

    def get_bulk(self):
        self.tx_message(REQUEST_BULK)
        return self.rx_message()

    def set_bank(self, data):
        logger.debug('Sending bank...')
        if (len(data) == RED_BANK_SIZE or len(data) == BANK_SIZE) and data[0:4] == BANK_START:
            self.tx_message(data)
        else:
            raise ValueError(INVALID_BANK_FILE)

    def set_bulk(self, data):
        logger.debug('Sending bulk ...')
        if (len(data) == RED_BULK_SIZE or len(data) == BULK_SIZE) and data[0:4] == BULK_START:
            self.tx_message(data)
        else:
            raise ValueError(INVALID_BULK_FILE)

    def set_bank_from_file(self, filename):
        data = mido.read_syx_file(filename)[0].bytes()
        logger.debug('Read data size is {:d}B: "{:s}"...'.format(
            len(data), self.get_hex_data(data)))
        data = list(data[1:len(data) - 1])
        try:
            self.set_bank(data)
        except ValueError as e:
            self.set_bulk(data)

    def save_bank_to_file(self, filename, data):
        messages = [Message('sysex', data=data)]
        mido.write_syx_file(filename, messages)
