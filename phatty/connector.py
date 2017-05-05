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

"""Phatty connector"""

import mido
from mido import Message
import logging
import time
import math

logger = logging.getLogger(__name__)

INIT_MSG = [0x7E, 0x7F, 6, 1]
PHATTY_MSG_WO_VERSION = [0x7e, 0x7f, 6, 2, 4, 0, 5, 0, 1]
REQUEST_PANEL = [4, 5, 6, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
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
MAX_DATA = 25
RECEIVE_RETRIES = 50
RETRY_SLEEP_TIME = 0.1
MSG_LEN = 64
SLEEP_TIME = 0.125
FILTER_POLES_VALUES = [32 * i for i in range(0, 4)]
MOD_SRC_5_VALUES = [0, 64]
MOD_SRC_6_VALUES = [0, 64]
LFO_RETRIGGER_VALUES = [0, 43, 86]
VEL_TO_FILTER_VALUES = [0, 12, 19, 26, 33, 40,
                        47, 54, 61, 68, 75, 82, 89, 96, 103, 110, 117]
VEL_TO_AMP_VALUES = [8 * i for i in range(0, 16)]
MOD_DEST_2_VALUES = [0, 25, 50, 75, 100]
LFO_MIDI_SYNC_VALUES = [0, 64]
RELEASE_VALUES = [0, 64]
PW_VALUES = [16 * i for i in range(0, 7)]
SCALE_VALUES = [i for i in range(0, 33)]
LEGATO_VALUES = [0, 43, 86]
GLIDE_ON_LEGATO_VALUES = [0, 64]
KEYBOARD_PRIORITY_VALUES = [32 * i for i in range(0, 4)]
ARP_PATTERN_VALUES = [0, 43, 86]
ARP_MODE_VALUES = [0, 43, 86]
ARP_OCTAVES_VALUES = [0, 19, 38, 57, 71, 90, 109]
ARP_GATE_VALUES = [32 * i for i in range(0, 4)]
ARP_CLOCK_SOURCE_VALUES = [0, 43, 86]
ARP_CLOCK_DIVISION_VALUES = [i * 6 for i in range(0, 22)]
ARP_CLOCK_DIVISION_VALUES.extend([127])

mido.set_backend('mido.backends.rtmidi')
logger.debug('Mido backend: {:s}'.format(str(mido.backend)))


def create_controller(control, value):
    return Message('control_change', channel=0, control=control, value=value)


def get_ports():
    return mido.get_ioport_names()


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
            try:
                self.port.close()
            except IOError:
                logger.error('IOError while disconnecting')
            self.port = None

    # We are overriding the send function in mido ports.py.
    # The reason is that the ALSA sequencer has a buffer smaller than the
    # bank or bulk size.
    def send(self, msg):
        """Send a message on the port.
        A copy of the message will be sent, so you can safely modify
        the original message without any unexpected consequences.
        """
        if not self.port.is_output:
            raise ValueError('Not an output port')
        elif not isinstance(msg, Message):
            raise TypeError('argument to send() must be a Message')
        elif self.port.closed:
            raise ValueError('send() called on closed port')

        with self.port._lock:
            if msg.type == 'sysex':
                t = msg.copy().bytes()
                while len(t) > MSG_LEN:
                    h = t[:MSG_LEN]
                    t = t[MSG_LEN:]
                    self.port.output._rt.send_message(h)
                    time.sleep(SLEEP_TIME)
                self.port.output._rt.send_message(t)
            else:
                self.port.output._rt.send_message(msg.bytes())

    def connect(self, device, callback):
        """Connect to the Phatty."""
        logger.debug('Connecting to {:s}...'.format(device))
        try:
            self.port = mido.open_ioport(device)
            self.callback = callback
            self.port.send = self.send
            logger.debug('Handshaking...')
            self.tx_message(INIT_MSG)
            response = self.rx_message()
            self.port.callback = self.process_message
            if response[0:9] == PHATTY_MSG_WO_VERSION:
                self.sw_version = '.'.join([str(i) for i in response[9:13]])
                logger.debug(HANDSHAKE_MSG.format(self.sw_version))
            else:
                logger.debug('Bad handshake. Disconnecting...')
                self.disconnect()
        except IOError as e:
            logger.error('IOError while connecting: "{:s}"'.format(str(e)))
            self.disconnect()

    def process_message(self, message):
        logger.debug('Processing message...')
        self.callback(message)

    def get_panel_as_preset(self, preset):
        msg = self.get_panel()
        msg[2] = 0x5
        msg[4] = preset
        return msg

    def get_panel(self):
        self.port.callback = None
        self.tx_message(REQUEST_PANEL)
        m = self.rx_message()
        self.port.callback = self.process_message
        return m

    def get_preset(self, num):
        self.port.callback = None
        msg = []
        msg.extend(REQUEST_PATCH)
        msg[REQ_PATCH_BYTE] = num
        self.tx_message(msg)
        m = self.rx_message()
        self.port.callback = self.process_message
        return m

    def set_preset(self, id):
        msg = Message('program_change', channel=0, program=id)
        logger.debug('Sending program change {:d}...'.format(id))
        self.port.send(msg)

    def tx_message(self, data):
        msg = Message('sysex', data=data)
        logger.debug('Sending message {:s}...'.format(self.get_hex_data(data)))
        try:
            self.port.send(msg)
        except IOError:
            self.disconnect()
            raise ConnectorError()

    def rx_message(self):
        try:
            for i in range(0, RECEIVE_RETRIES):
                for msg in self.port.iter_pending():
                    if msg.type == 'sysex':
                        logger.debug('Receiving message {:s}...'.format(
                            self.get_hex_data(msg.data)))
                        data_array = []
                        data_array.extend(msg.data)
                        return data_array
                    else:
                        self.callback(msg)
                time.sleep(RETRY_SLEEP_TIME)
        except IOError:
            self.disconnect()
            raise ConnectorError()
        self.disconnect()
        raise ConnectorError()

    def get_hex_data(self, data):
        if len(data) > MAX_DATA:
            data = data[0:MAX_DATA]
        s = ', '.join([hex(i) for i in data])
        if len(data) > MAX_DATA:
            s += '[...]'
        return s

    def get_bank(self):
        self.port.callback = None
        self.tx_message(REQUEST_BANK)
        m = self.rx_message()
        self.port.callback = self.process_message
        return m

    def get_bulk(self):
        self.port.callback = None
        self.tx_message(REQUEST_BULK)
        m = self.rx_message()
        self.port.callback = self.process_message
        return m

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

    def set_panel_name(self, name):
        logger.debug('Setting preset name to {:s}...'.format(name))
        messages = []
        messages.append(
            Message('control_change', channel=0, control=119, value=0))
        messages.append(
            Message('control_change', channel=0, control=66, value=19))
        messages.append(
            Message('control_change', channel=0, control=66, value=15))
        messages.append(
            Message('control_change', channel=0, control=66, value=13))
        messages.append(
            Message('control_change', channel=0, control=66, value=1))
        for c in name:
            messages.append(
                Message('control_change', channel=0, control=66, value=ord(c)))
        for message in messages:
            self.port.send(message)

    # Global
    def set_lfo_midi_sync(self, value):
        msg = create_controller(102, LFO_MIDI_SYNC_VALUES[value])
        self.port.send(msg)

    # Filter and amp
    def set_panel_filter_poles(self, value):
        msg = create_controller(109, FILTER_POLES_VALUES[value])
        self.port.send(msg)

    def set_panel_vel_to_filter(self, value):
        msg = create_controller(110, VEL_TO_FILTER_VALUES[value])
        self.port.send(msg)

    def set_panel_vel_to_amp(self, value):
        msg = create_controller(92, VEL_TO_AMP_VALUES[value])
        self.port.send(msg)

    def set_panel_release(self, value):
        msg = create_controller(88, RELEASE_VALUES[value])
        self.port.send(msg)

    # Keyboard and controls
    def set_panel_scale(self, value):
        msg = create_controller(113, SCALE_VALUES[value])
        self.port.send(msg)

    def set_panel_pw_up_amount(self, value):
        msg = create_controller(107, PW_VALUES[value])
        self.port.send(msg)

    def set_panel_pw_down_amount(self, value):
        msg = create_controller(108, PW_VALUES[value])
        self.port.send(msg)

    def set_panel_legato(self, value):
        msg = create_controller(112, LEGATO_VALUES[value])
        self.port.send(msg)

    def set_panel_keyboard_priority(self, value):
        msg = create_controller(111, KEYBOARD_PRIORITY_VALUES[value])
        self.port.send(msg)

    def set_panel_glide_on_legato(self, value):
        msg = create_controller(94, GLIDE_ON_LEGATO_VALUES[value])
        self.port.send(msg)

    # Modulation
    def set_panel_mod_source_5(self, value):
        msg = create_controller(104, MOD_SRC_5_VALUES[value])
        self.port.send(msg)

    def set_panel_mod_source_6(self, value):
        msg = create_controller(105, MOD_SRC_6_VALUES[value])
        self.port.send(msg)

    def set_panel_mod_dest_2(self, value):
        msg = create_controller(106, MOD_DEST_2_VALUES[value])
        self.port.send(msg)

    def set_panel_lfo_key_retrigger(self, value):
        msg = create_controller(93, LFO_RETRIGGER_VALUES[value])
        self.port.send(msg)

    # Arpeggiator
    def set_panel_arp_pattern(self, value):
        msg = create_controller(117, ARP_PATTERN_VALUES[value])
        self.port.send(msg)

    def set_panel_arp_mode(self, value):
        msg = create_controller(118, ARP_MODE_VALUES[value])
        self.port.send(msg)

    def set_panel_arp_octaves(self, value):
        msg = create_controller(116, ARP_OCTAVES_VALUES[value])
        self.port.send(msg)

    def set_panel_arp_gate(self, value):
        msg = create_controller(95, ARP_GATE_VALUES[value])
        self.port.send(msg)

    def set_panel_arp_clock_source(self, value):
        msg = create_controller(114, ARP_CLOCK_SOURCE_VALUES[value])
        self.port.send(msg)

    def set_panel_arp_clock_division(self, value):
        msg = create_controller(115, ARP_CLOCK_DIVISION_VALUES[value])
        self.port.send(msg)


class ConnectorError(IOError):
    """Raise when there is a Connector error"""

    def __init__(self):
        super(ConnectorError, self).__init__('Connection error')
