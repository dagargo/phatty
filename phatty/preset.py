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
PARAMETER_VALUES = 0
PARAMETER_DATABYTE = 1
PARAMETER_BITMASK = 2
PARAMETER_BITSHIFT = 3
FILTER_POLES_PARAMETERS = [[0, 1, 2, 3], 0x2c, 0x18, 0x3]
MOD_SOURCE_5_PARAMETERS = [[0, 1], 0x2a, 0x8, 0x3]
MOD_SOURCE_6_PARAMETERS = [[0, 1], 0x2a, 0x4, 0x2]
LFO_RETRIGGER_PARAMETERS = [[0, 1, 2], 0xbc, 0x6, 0x1]
VEL_TO_FILTER_PARAMETERS_1 = [[int(i / 8) for i in range(0, 17)], 0x2a, 0x3, 0]
VEL_TO_FILTER_PARAMETERS_2 = [[i % 8 for i in range(0, 17)], 0x2b, 0x38, 3]
VEL_TO_AMP_PARAMETERS_1 = [[int(i / 8) for i in range(0, 16)], 0x4b, 0x1, 0]
VEL_TO_AMP_PARAMETERS_2 = [[i % 8 for i in range(0, 16)], 0x4c, 0x38, 3]
MOD_DEST_2_PARAMETERS = [[0, 1, 2, 3, 4], 0x4d, 0x38, 0x3]
RELEASE_PARAMETERS = [[0, 1], 0x4c, 0x4, 2]
PW_UP_PARAMETERS = [[i for i in range(0, 7)], 0x4b, 0xe, 1]
PW_DOWN_PARAMETERS = [[i for i in range(0, 7)], 0x4d, 0x7, 0]
SCALE_PARAMETERS_1 = [[int(i / 16) for i in range(0, 33)], 0xbd, 0x3, 0]
SCALE_PARAMETERS_2 = [[i % 16 for i in range(0, 33)], 0xbe, 0x3c, 2]
LEGATO_PARAMETERS_1 = [[0, 0, 1], 0x2b, 0x1, 0]
LEGATO_PARAMETERS_2 = [[0, 1, 0], 0x2c, 0x20, 5]
GLIDE_ON_LEGATO_PARAMETERS = [[0, 1], 0xbc, 0x1, 0]
KEYBOARD_PRIORITY_PARAMETERS = [[0, 1, 2, 3], 0x4c, 0x3, 0]
ARP_OCTAVES_PARAMETERS = [[3, 4, 5, 6, 0, 1, 2], 0x52, 0x1c, 2]
ARP_PATTERN_PARAMETERS_1 = [[0, 0, 1], 0x51, 0x1, 0]
ARP_PATTERN_PARAMETERS_2 = [[0, 1, 0], 0x52, 0x20, 5]
ARP_MODE_PARAMETERS = [[0, 1, 2], 0x51, 0x6, 1]
ARP_GATE_PARAMETERS = [[0, 1, 2, 3], 0xbb, 0xc, 2]
ARP_CLOCK_SOURCE_PARAMETERS = [[0, 1, 2], 0x50, 0x6, 1]
ARP_CLOCK_DIVISION_PARAMETERS = [[i for i in range(0, 23)], 0xb9, 0x1f, 0]


def get_char(preset, position):
    k = (3 * int(position / 2)) + 22
    if position % 2 == 0:
        index = ((preset[k] & 0x1) << 6) | (preset[k + 1] & 0x3f)
    else:
        index = ((preset[k + 2] & 0x3) << 4) | ((preset[k + 3] & 0x3c) >> 2)
    return ALPHABET[index]


def set_char(preset, c, position):
    index = ALPHABET.find(c)
    if index == -1:
        raise ValueError()
    # Code adapted from
    # https://gitlab.com/jp-ma/phatty-editor/blob/master/libphatty/phatty-fmt.x
    k = (3 * int(position / 2)) + 22
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


def get_name(preset):
    name = []
    for i in range(NAME_LEN):
        c = get_char(preset, i)
        name.append(c)
    return ''.join(name)


def set_name(preset, preset_name):
    normalized_name = normalize_name(preset_name)
    for i in range(NAME_LEN):
        set_char(preset, normalized_name[i], i)


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


def set_number(preset, number):
    preset[PRESET_NUMBER_BYTE] = number


def get_number(preset):
    return preset[PRESET_NUMBER_BYTE]


def set_preset_value(preset, parameters, value):
    values = parameters[PARAMETER_VALUES]
    value = values[value]
    databyte = parameters[PARAMETER_DATABYTE]
    bitmask = parameters[PARAMETER_BITMASK]
    bitshift = parameters[PARAMETER_BITSHIFT]
    preset[databyte] = (preset[databyte] & ~bitmask) | (
        (value << bitshift) & bitmask)


def get_preset_value(preset, parameters):
    values = parameters[PARAMETER_VALUES]
    databyte = parameters[PARAMETER_DATABYTE]
    bitmask = parameters[PARAMETER_BITMASK]
    bitshift = parameters[PARAMETER_BITSHIFT]
    return (preset[databyte] & bitmask) >> bitshift


def set_filter_poles(preset, value):
    set_preset_value(preset, FILTER_POLES_PARAMETERS, value)


def get_filter_poles(preset):
    return get_preset_value(preset, FILTER_POLES_PARAMETERS)


def set_vel_to_filter(preset, value):
    set_preset_value(preset, VEL_TO_FILTER_PARAMETERS_1, value)
    set_preset_value(preset, VEL_TO_FILTER_PARAMETERS_2, value)


def get_vel_to_filter(preset):
    return ((get_preset_value(preset, VEL_TO_FILTER_PARAMETERS_1) & 0x3) << 3) | get_preset_value(preset, VEL_TO_FILTER_PARAMETERS_2)


def set_vel_to_amp(preset, value):
    set_preset_value(preset, VEL_TO_AMP_PARAMETERS_1, value)
    set_preset_value(preset, VEL_TO_AMP_PARAMETERS_2, value)


def get_vel_to_amp(preset):
    return ((get_preset_value(preset, VEL_TO_AMP_PARAMETERS_1) & 0x1) << 3) | get_preset_value(preset, VEL_TO_AMP_PARAMETERS_2)


def set_release(preset, value):
    set_preset_value(preset, RELEASE_PARAMETERS, value)


def get_release(preset):
    return get_preset_value(preset, RELEASE_PARAMETERS)


def set_scale(preset, value):
    set_preset_value(preset, SCALE_PARAMETERS_1, value)
    set_preset_value(preset, SCALE_PARAMETERS_2, value)


def get_scale(preset):
    return ((get_preset_value(preset, SCALE_PARAMETERS_1) & 0x3) << 4) | get_preset_value(preset, SCALE_PARAMETERS_2)


def set_pw_up_amount(preset, value):
    set_preset_value(preset, PW_UP_PARAMETERS, value)


def get_pw_up_amount(preset):
    return get_preset_value(preset, PW_UP_PARAMETERS)


def set_pw_down_amount(preset, value):
    set_preset_value(preset, PW_DOWN_PARAMETERS, value)


def get_pw_down_amount(preset):
    return get_preset_value(preset, PW_DOWN_PARAMETERS)


def set_legato(preset, value):
    set_preset_value(preset, LEGATO_PARAMETERS_1, value)
    set_preset_value(preset, LEGATO_PARAMETERS_2, value)


def get_legato(preset):
    return ((get_preset_value(preset, LEGATO_PARAMETERS_1) & 0x1) << 1) | get_preset_value(preset, LEGATO_PARAMETERS_2)


def set_keyboard_priority(preset, value):
    set_preset_value(preset, KEYBOARD_PRIORITY_PARAMETERS, value)


def get_keyboard_priority(preset):
    return get_preset_value(preset, KEYBOARD_PRIORITY_PARAMETERS)


def set_glide_on_legato(preset, value):
    set_preset_value(preset, GLIDE_ON_LEGATO_PARAMETERS, value)


def get_glide_on_legato(preset):
    return get_preset_value(preset, GLIDE_ON_LEGATO_PARAMETERS)


def set_mod_source_5(preset, value):
    set_preset_value(preset, MOD_SOURCE_5_PARAMETERS, value)


def get_mod_source_5(preset):
    return get_preset_value(preset, MOD_SOURCE_5_PARAMETERS)


def set_mod_source_6(preset, value):
    set_preset_value(preset, MOD_SOURCE_6_PARAMETERS, value)


def get_mod_source_6(preset):
    return get_preset_value(preset, MOD_SOURCE_6_PARAMETERS)


def set_lfo_key_retrigger(preset, value):
    set_preset_value(preset, LFO_RETRIGGER_PARAMETERS, value)


def get_lfo_key_retrigger(preset):
    return get_preset_value(preset, LFO_RETRIGGER_PARAMETERS)


def set_mod_dest_2(preset, value):
    set_preset_value(preset, MOD_DEST_2_PARAMETERS, value)


def get_mod_dest_2(preset):
    return get_preset_value(preset, MOD_DEST_2_PARAMETERS)


def set_arp_pattern(preset, value):
    set_preset_value(preset, ARP_PATTERN_PARAMETERS_1, value)
    set_preset_value(preset, ARP_PATTERN_PARAMETERS_2, value)


def get_arp_pattern(preset):
    return ((get_preset_value(preset, ARP_PATTERN_PARAMETERS_1) & 0x1) << 1) | get_preset_value(preset, ARP_PATTERN_PARAMETERS_2)


def set_arp_mode(preset, value):
    set_preset_value(preset, ARP_MODE_PARAMETERS, value)


def get_arp_mode(preset):
    return get_preset_value(preset, ARP_MODE_PARAMETERS)


def set_arp_octaves(preset, value):
    set_preset_value(preset, ARP_OCTAVES_PARAMETERS, value)


def get_arp_octaves(preset):
    return ARP_OCTAVES_PARAMETERS[PARAMETER_VALUES].index(get_preset_value(preset, ARP_OCTAVES_PARAMETERS))


def set_arp_gate(preset, value):
    set_preset_value(preset, ARP_GATE_PARAMETERS, value)


def get_arp_gate(preset):
    return get_preset_value(preset, ARP_GATE_PARAMETERS)


def set_arp_clock_source(preset, value):
    set_preset_value(preset, ARP_CLOCK_SOURCE_PARAMETERS, value)


def get_arp_clock_source(preset):
    return get_preset_value(preset, ARP_CLOCK_SOURCE_PARAMETERS)


def set_arp_clock_division(preset, value):
    set_preset_value(preset, ARP_CLOCK_DIVISION_PARAMETERS, value)


def get_arp_clock_division(preset):
    return get_preset_value(preset, ARP_CLOCK_DIVISION_PARAMETERS)
