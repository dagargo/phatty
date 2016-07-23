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

"""Phatty preset utils"""

ALPHABET = ' ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz!#$%&()*?@'
NAME_LEN = 13
PRESET_NUMBER_BYTE = 4
FILE_EXTENSION = 'syx'
FILE_EXTENSION_EX = 'sysex'


def get_preset_char(preset, position):
    k = (3 * int(position / 2)) + 22
    if position % 2 == 0:
        index = ((preset[k] & 0x1) << 6) | (preset[k + 1] & 0x3f)
    else:
        index = ((preset[k + 2] & 0x3) << 4) | ((preset[k + 3] & 0x3c) >> 2)
    return ALPHABET[index]


def set_preset_char(preset, c, position):
    index = ALPHABET.find(c)
    if index == -1:
        raise ValueError()
    k = (3 * int(position / 2)) + 22
    # TODO: review comment
    # Code adapted from
    # https://gitlab.com/jp-ma/phatty-editor/blob/master/libphatty/phatty-fmt.x
    if position % 2 == 0:
        preset[k] &= ~0x1
        preset[k] |= (index >> 6) & 0x01
        preset[k + 1] &= ~0x3f
        preset[k + 1] |= index & 0x3f
    else:
        preset[k + 2] &= ~0x3
        preset[k + 2] |= (index >> 4) & 0x7
        preset[k + 3] &= ~0x3c
        preset[k + 3] |= (index & 0xf) << 2


def get_preset_name(preset):
    name = []
    for i in range(NAME_LEN):
        c = get_preset_char(preset, i)
        name.append(c)
    return ''.join(name)


def set_preset_name(preset, preset_name):
    normalized_name = normalize_name(preset_name)
    for i in range(NAME_LEN):
        set_preset_char(preset, normalized_name[i], i)


def normalize_name(name):
    input = list(name)
    output = []
    l = len(name)
    l = l if l <= NAME_LEN else NAME_LEN
    for i in range(l):
        c = name[i]
        index = ALPHABET.find(c)
        if index == -1:
            output.append('?')
        else:
            output.append(c)
    if l <= NAME_LEN:
        for i in range(NAME_LEN - len(name)):
            output.append(' ')
    return ''.join(output)


def set_preset_number(preset, number):
    preset[PRESET_NUMBER_BYTE] = number


def get_preset_number(preset):
    return preset[PRESET_NUMBER_BYTE]
