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

"""Phatty user interface"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject
from gi.repository import GLib
from threading import Thread, Lock
import logging
import pkg_resources
from phatty import connector
from phatty import preset
from phatty import utils
import sys
import getopt
import mido

GLib.threads_init()

CONN_MSG = 'Connected (firmware version {:s})'
ERROR_IN_BANK_TRANSFER = 'Error in bank transfer {:s}'
ERROR_WHILE_SAVING_BANK = 'Error while saving bank to {:s}'
PKG_NAME = 'phatty'

glade_file = pkg_resources.resource_filename(__name__, 'resources/gui.glade')
version = pkg_resources.get_distribution(PKG_NAME).version


def print_help():
    print ('Usage: {:s} [-v]'.format(PKG_NAME))

log_level = logging.ERROR
try:
    opts, args = getopt.getopt(sys.argv[1:], "hv")
except getopt.GetoptError:
    print_help()
    sys.exit(1)
for opt, arg in opts:
    if opt == '-h':
        print_help()
        sys.exit()
    elif opt == '-v':
        log_level = logging.DEBUG

logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

utils.create_config()

logger.debug('Reading glade file...')
with open(glade_file, 'r') as file:
    try:
        glade_contents = file.read()
    except IOError as e:
        logger.error('Glade file could not be read. Exiting...')
        sys.exit(-1)

builder = Gtk.Builder()
builder.add_from_string(glade_contents)


class TransferDialog(object):

    def __init__(self, parent):
        self.dialog = builder.get_object('transfer_dialog')
        self.label = builder.get_object('transfer_label')
        self.progressbar = builder.get_object('progressbar')
        self.button = builder.get_object('transfer_cancel')
        self.dialog.set_transient_for(parent)
        self.dialog.connect('delete-event', lambda widget,
                            event: self.cancel() or True)
        self.button.connect('clicked', lambda widget: self.cancel())

    def show(self, title):
        self.dialog.set_title(title)
        self.running = True
        self.progressbar.set_fraction(0)
        self.dialog.show()

    def show_fraction(self, title):
        self.button.show()
        self.show(title)

    def show_pulse(self, title):
        self.label.set_text('')
        self.button.hide()
        self.pulsating = True
        self.show(title)

    def cancel(self):
        self.running = False
        self.pulsating = False

    def hide(self):
        self.dialog.hide()

    def set_status(self, msg, fraction):
        self.label.set_text(msg)
        self.progressbar.set_fraction(fraction)

    def pulse_progressbar(self):
        self.progressbar.pulse()
        if self.running:
            return self.pulsating
        else:
            return False


class SettingsDialog(object):

    def __init__(self, phatty):
        self.phatty = phatty
        self.dialog = builder.get_object('settings_dialog')
        self.accept = builder.get_object('settings_accept_button')
        self.cancel = builder.get_object('settings_cancel_button')
        self.devices = builder.get_object('device_combo')
        self.device_liststore = builder.get_object('device_liststore')
        self.bulk_switch = builder.get_object('bulk_switch')
        self.auto_switch = builder.get_object('auto_switch')
        # These are global parameters and hence are neither is stored in
        # presets nor its value can be recalled
        self.lfo_midi_sync = builder.get_object('lfo_midi_sync')
        self.lfo_midi_sync.connect('state-set', lambda widget, state: self.phatty.call_connector(
            self.phatty.connector.set_lfo_midi_sync,
            1 if state else 0))

        self.dialog.set_transient_for(phatty.main_window)
        self.dialog.connect('delete-event', lambda widget,
                            event: widget.hide() or True)
        self.cancel.connect('clicked', lambda widget: self.dialog.hide())
        self.accept.connect('clicked', lambda widget: self.save())

    def show(self):
        self.device_liststore.clear()
        i = 0
        for port in mido.get_output_names():
            logger.debug('Adding port {:s}...'.format(port))
            self.device_liststore.append([port])
            if self.phatty.config[utils.DEVICE] == port:
                logger.debug('Port {:s} is active'.format(port))
                self.devices.set_active(i)
            i += 1
        self.bulk_switch.set_active(self.phatty.config[utils.BULK_ON])
        self.auto_switch.set_active(self.phatty.config[utils.DOWNLOAD_AUTO])
        self.lfo_midi_sync.set_active(self.phatty.config[utils.LFO_MIDI_SYNC])
        self.dialog.show()

    def save(self):
        active = self.devices.get_active()
        device = self.device_liststore[active][0]
        self.phatty.config[utils.DEVICE] = device
        self.phatty.config[utils.BULK_ON] = self.bulk_switch.get_active()
        self.phatty.config[utils.DOWNLOAD_AUTO] = self.auto_switch.get_active()
        self.phatty.config[
            utils.LFO_MIDI_SYNC] = self.lfo_midi_sync.get_active()
        logger.debug('Configuration: {:s}'.format(str(self.phatty.config)))
        utils.write_config(self.phatty.config)
        self.phatty.ui_reconnect()
        self.dialog.hide()


class Editor(object):
    """Phatty user interface"""

    def __init__(self):
        self.connector = connector.Connector()
        self.main_window = None
        self.sysex_presets = []
        self.config = utils.read_config()
        self.transferring = Lock()

    def init_ui(self):
        self.main_window = builder.get_object('main_window')
        self.main_window.connect(
            'delete-event', lambda widget, event: self.quit())
        self.main_window.set_position(Gtk.WindowPosition.CENTER)
        self.main_container = builder.get_object('main_container')
        self.about_dialog = builder.get_object('about_dialog')
        self.about_dialog.set_position(Gtk.WindowPosition.CENTER)
        self.about_dialog.set_transient_for(self.main_window)
        self.about_dialog.set_version(version)
        self.connect_button = builder.get_object('connect_button')
        self.connect_button.connect(
            'clicked', lambda widget: self.ui_reconnect())
        self.download_button = builder.get_object('download_button')
        self.download_button.connect(
            'clicked', lambda widget: self.download_presets())
        self.upload_button = builder.get_object('upload_button')
        self.upload_button.connect(
            'clicked', lambda widget: self.upload_presets())
        self.upload_button.set_sensitive(False)
        self.about_button = builder.get_object('about_button')
        self.about_button.connect('clicked', lambda widget: self.show_about())
        self.settings_button = builder.get_object('settings_button')
        self.settings_button.connect(
            'clicked', lambda widget: self.settings_dialog.show())
        self.open_button = builder.get_object('open_button')
        self.open_button.connect(
            'clicked', lambda widget: self.open_bank_from_file())
        self.save_button = builder.get_object('save_button')
        self.save_button.connect(
            'clicked', lambda widget: self.save_bank_to_file())
        self.statusbar = builder.get_object('statusbar')
        self.context_id = self.statusbar.get_context_id(PKG_NAME)
        self.preset_list = builder.get_object('preset_list')
        self.presets = builder.get_object('preset_liststore')
        self.preset_selection = builder.get_object('preset_selection')
        self.presets.connect('row-deleted', self.row_deleted)
        self.preset_selection.connect('changed', self.selection_changed)
        self.preset_name_renderer = builder.get_object(
            'preset_name_renderer')
        self.preset_name_renderer.connect('edited', self.set_preset_name)
        self.transfer_dialog = TransferDialog(self.main_window)
        self.settings_dialog = SettingsDialog(self)

        # Filter and envelopes
        self.filter_poles = builder.get_object('filter_poles')
        self.filter_poles.connect('changed', lambda widget: self.call_connector(
            self.connector.set_panel_filter_poles,
            int(self.filter_poles.get_value() - 1)))
        self.vel_to_filter = builder.get_object('vel_to_filter')
        self.vel_to_filter.connect('value-changed', lambda widget: self.call_connector(
            self.connector.set_panel_vel_to_filter,
            int(self.vel_to_filter.get_value() + 8)))
        self.vel_to_amp = builder.get_object('vel_to_amp')
        self.vel_to_amp.connect('value-changed', lambda widget: self.call_connector(
            self.connector.set_panel_vel_to_amp,
            int(self.vel_to_amp.get_value())))
        self.release = builder.get_object('release')
        self.release.connect('state-set', lambda widget, state: self.call_connector(
            self.connector.set_panel_release,
            1 if state else 0))
        # Keyboard and controls
        self.scale = builder.get_object('scale')
        self.scale.connect('changed', lambda widget: self.call_connector(
            self.connector.set_panel_scale,
            self.scale.get_active()))
        self.pw_up_amount = builder.get_object('pw_up_amount')
        self.pw_up_amount.connect('changed', lambda widget: self.call_connector(
            self.connector.set_panel_pw_up_amount,
            self.pw_up_amount.get_active()))
        self.pw_down_amount = builder.get_object('pw_down_amount')
        self.pw_down_amount.connect('changed', lambda widget: self.call_connector(
            self.connector.set_panel_pw_down_amount,
            self.pw_down_amount.get_active()))
        self.legato = builder.get_object('legato')
        self.legato.connect('changed', lambda widget: self.call_connector(
            self.connector.set_panel_legato,
            self.legato.get_active()))
        self.keyboard_priority = builder.get_object('keyboard_priority')
        self.keyboard_priority.connect('changed', lambda widget: self.call_connector(
            self.connector.set_panel_keyboard_priority,
            self.keyboard_priority.get_active()))
        self.glide_on_legato = builder.get_object('glide_on_legato')
        self.glide_on_legato.connect('state-set', lambda widget, state: self.call_connector(
            self.connector.set_panel_glide_on_legato,
            1 if state else 0))
        # Modulation parameters
        self.mod_source_5 = builder.get_object('mod_source_5')
        self.mod_source_5.connect('changed', lambda widget: self.call_connector(
            self.connector.set_panel_mod_source_5,
            self.mod_source_5.get_active()))
        self.mod_source_6 = builder.get_object('mod_source_6')
        self.mod_source_6.connect('changed', lambda widget: self.call_connector(
            self.connector.set_panel_mod_source_6,
            self.mod_source_6.get_active()))
        self.mod_dest_2 = builder.get_object('mod_dest_2')
        self.mod_dest_2.connect('changed', lambda widget: self.call_connector(
            self.connector.set_panel_mod_dest_2,
            self.mod_dest_2.get_active()))
        self.lfo_key_retrigger = builder.get_object('lfo_key_retrigger')
        self.lfo_key_retrigger.connect('changed', lambda widget: self.call_connector(
            self.connector.set_panel_lfo_key_retrigger,
            self.lfo_key_retrigger.get_active()))
        # Arpeggiator
        self.arp_pattern = builder.get_object('arp_pattern')
        self.arp_pattern.connect('changed', lambda widget: self.call_connector(
            self.connector.set_panel_arp_pattern,
            self.arp_pattern.get_active()))
        self.arp_mode = builder.get_object('arp_mode')
        self.arp_mode.connect('changed', lambda widget: self.call_connector(
            self.connector.set_panel_arp_mode,
            self.arp_mode.get_active()))
        self.arp_octaves = builder.get_object('arp_octaves')
        self.arp_octaves.connect('changed', lambda widget: self.call_connector(
            self.connector.set_panel_arp_octaves,
            int(self.arp_octaves.get_value() + 3)))
        self.arp_gate = builder.get_object('arp_gate')
        self.arp_gate.connect('changed', lambda widget: self.call_connector(
            self.connector.set_panel_arp_gate,
            self.arp_gate.get_active()))
        self.arp_clock_source = builder.get_object('arp_clock_source')
        self.arp_clock_source.connect('changed', lambda widget: self.call_connector(
            self.connector.set_panel_arp_clock_source,
            self.arp_clock_source.get_active()))
        self.arp_clock_division = builder.get_object('arp_clock_division')
        self.arp_clock_division.connect('changed', lambda widget: self.call_connector(
            self.connector.set_panel_arp_clock_division,
            self.arp_clock_division.get_active()))

        # Preset buttons
        self.download_panel = builder.get_object('download_panel')
        self.download_panel.connect(
            'clicked', lambda widget: self.get_panel())
        self.download_preset = builder.get_object('download_preset')
        self.download_preset.connect(
            'clicked', lambda widget: self.get_preset())
        self.upload_preset = builder.get_object('upload_preset')
        self.upload_preset.connect('clicked', lambda widget: self.set_preset())

        self.filter_syx = Gtk.FileFilter()
        self.filter_syx.set_name('MIDI sysex')
        self.filter_syx.add_pattern('*.' + preset.FILE_EXTENSION)
        self.filter_syx.add_pattern('*.' + preset.FILE_EXTENSION_EX)

        self.filter_any = Gtk.FileFilter()
        self.filter_any.set_name('Any files')
        self.filter_any.add_pattern('*')

        self.main_window.present()

    def get_panel(self):
        model, iter = self.preset_selection.get_selected()
        active_preset = model[iter][0]
        try:
            panel = self.connector.get_panel_as_preset(active_preset)
            self.sysex_presets[active_preset] = panel
            self.presets[active_preset][1] = preset.get_name(panel)
            self.set_preset_attributes(active_preset)
        except ConnectorError as e:
            GLib.idle_add(self.show_error_dialog, str(e), None)
            self.ui_reconnect()

    def get_preset(self):
        model, iter = self.preset_selection.get_selected()
        active_preset = model[iter][0]
        try:
            p = self.connector.get_preset(active_preset)
            self.sysex_presets[active_preset] = p
            self.presets[active_preset][1] = preset.get_name(p)
            self.set_preset_attributes(active_preset)
        except ConnectorError as e:
            GLib.idle_add(self.show_error_dialog, str(e), None)
            self.ui_reconnect()

    def set_preset(self):
        model, iter = self.preset_selection.get_selected()
        active_preset = model[iter][0]
        try:
            self.connector.tx_message(self.sysex_presets[active_preset])
        except ConnectorError as e:
            GLib.idle_add(self.show_error_dialog, str(e), None)
            self.ui_reconnect()

    def set_preset_attributes(self, id):
        active_preset = self.sysex_presets[id]
        # Filter and amp
        filter_poles = preset.get_filter_poles(active_preset)
        self.filter_poles.set_value(filter_poles + 1)
        vel_to_filter = preset.get_vel_to_filter(active_preset) - 8
        self.vel_to_filter.set_value(vel_to_filter)
        vel_to_amp = preset.get_vel_to_amp(active_preset)
        self.vel_to_amp.set_value(vel_to_amp)
        release = preset.get_release(active_preset)
        self.release.set_active(True if release == 1 else False)
        # Keyboard and controls
        scale = preset.get_scale(active_preset)
        self.scale.set_active(scale)
        pw_up_amount = preset.get_pw_up_amount(active_preset)
        self.pw_up_amount.set_active(pw_up_amount)
        pw_down_amount = preset.get_pw_down_amount(active_preset)
        self.pw_down_amount.set_active(pw_down_amount)
        legato = preset.get_legato(active_preset)
        self.legato.set_active(legato)
        keyboard_priority = preset.get_keyboard_priority(active_preset)
        self.keyboard_priority.set_active(keyboard_priority)
        glide_on_legato = preset.get_glide_on_legato(active_preset)
        self.glide_on_legato.set_active(
            True if glide_on_legato == 1 else False)
        # Modulation
        mod_source_5 = preset.get_mod_source_5(active_preset)
        self.mod_source_5.set_active(mod_source_5)
        mod_source_6 = preset.get_mod_source_6(active_preset)
        self.mod_source_6.set_active(mod_source_6)
        mod_dest_2 = preset.get_mod_dest_2(active_preset)
        self.mod_dest_2.set_active(mod_dest_2)
        lfo_key_retrigger = preset.get_lfo_key_retrigger(active_preset)
        self.lfo_key_retrigger.set_active(lfo_key_retrigger)
        # Arpeggiator
        arp_pattern = preset.get_arp_pattern(active_preset)
        self.arp_pattern.set_active(arp_pattern)
        arp_mode = preset.get_arp_mode(active_preset)
        self.arp_mode.set_active(arp_mode)
        arp_octaves = preset.get_arp_octaves(active_preset)
        self.arp_octaves.set_value(arp_octaves - 3)
        arp_gate = preset.get_arp_gate(active_preset)
        self.arp_gate.set_active(arp_gate)
        arp_clock_source = preset.get_arp_clock_source(active_preset)
        self.arp_clock_source.set_active(arp_clock_source)
        arp_clock_division = preset.get_arp_clock_division(active_preset)
        self.arp_clock_division.set_active(arp_clock_division)

    def selection_changed(self, selection):
        model, iter = selection.get_selected()
        if iter != None:
            logger.debug('Preset {:d} selected'.format(model[iter][0]))
            try:
                self.connector.set_preset(model[iter][0])
                self.set_preset_attributes(model[iter][0])
            except ConnectorError as e:
                GLib.idle_add(self.show_error_dialog, str(e), None)
                self.ui_reconnect()

    def row_deleted(self, tree_model, path):
        if not self.transferring.locked():
            logger.debug('Reordering...')
            new_sysex_presets = []
            for i in range(connector.MAX_PRESETS):
                sysex_preset = self.sysex_presets[self.presets[i][0]]
                preset.set_number(sysex_preset, i)
                new_sysex_presets.append(sysex_preset)
                self.presets[i][0] = i
            self.sysex_presets = new_sysex_presets

    def set_preset_name(self, widget, row, name):
        logger.debug('Changing preset name...')
        active_preset = int(row)
        normalized_name = preset.normalize_name(name)
        self.presets[active_preset][1] = normalized_name
        preset.set_name(self.sysex_presets[active_preset], normalized_name)
        try:
            self.connector.set_panel_name(normalized_name)
        except ConnectorError as e:
            GLib.idle_add(self.show_error_dialog, str(e), None)
            self.ui_reconnect()

    def connect(self):
        device = self.config[utils.DEVICE]
        self.connector.connect(device)
        if self.connector.connected():
            conn_msg = CONN_MSG.format(self.connector.sw_version)
            self.set_status_msg(conn_msg)
        else:
            self.set_status_msg('Not connected')

    def ui_reconnect(self):
        if not self.connector.connected():
            self.connect()
            self.set_ui()

    def set_ui(self):
        if self.connector.connected() and self.config[utils.DOWNLOAD_AUTO]:
            self.download_presets()
        self.set_sensitivities()

    def set_sensitivities(self):
        for c in [self.open_button, self.save_button, self.download_button, self.settings_dialog.lfo_midi_sync]:
            c.set_sensitive(self.connector.connected())
        for c in [self.main_container, self.upload_button, self.download_panel, self.download_preset, self.upload_preset]:
            c.set_sensitive(self.connector.connected()
                            and len(self.sysex_presets) > 0)

    def download_presets(self):
        logger.debug('Starting download thread...')
        self.transfer_dialog.show_fraction('Downloading presets')
        self.transferring.acquire()
        self.presets.clear()
        self.sysex_presets.clear()
        self.thread = Thread(target=self.do_download)
        self.thread.start()

    def do_download(self):
        try:
            for i in range(connector.MAX_PRESETS):
                if not self.transfer_dialog.running:
                    logger.debug('Cancelling download...')
                    break
                msg = 'Downloading preset {:d}...'.format(i)
                logger.debug(msg)
                fraction = (i + 1) / connector.MAX_PRESETS
                GLib.idle_add(self.transfer_dialog.set_status, msg, fraction)
                p = self.connector.get_preset(i)
                preset_name = preset.get_name(p)
                GLib.idle_add(self.add_preset, i, preset_name)
                self.sysex_presets.append(p)
        except ConnectorError as e:
            GLib.idle_add(self.show_error_dialog, str(e), None)
            self.ui_reconnect()
        GLib.idle_add(self.end_download)

    def add_preset(self, number, name):
        self.presets.append([number, name])

    def end_download(self):
        if not self.transfer_dialog.running:
            self.presets.clear()
            self.sysex_presets.clear()
        self.thread.join()
        logger.debug('Thread finished')
        self.upload_button.set_sensitive(len(self.sysex_presets) > 0)
        self.transferring.release()
        self.transfer_dialog.hide()
        self.preset_list.set_cursor(0)
        self.set_sensitivities()

    def upload_presets(self):
        logger.debug('Starting upload thread...')
        self.transfer_dialog.show_fraction("Uploading presets")
        self.transferring.acquire()
        self.thread = Thread(target=self.do_upload)
        self.thread.start()

    def do_upload(self):
        try:
            for i in range(connector.MAX_PRESETS):
                if not self.transfer_dialog.running:
                    logger.debug('Cancelling upload...')
                    break
                msg = 'Uploading preset {:d}...'.format(i)
                logger.debug(msg)
                fraction = (i + 1) / connector.MAX_PRESETS
                GLib.idle_add(self.transfer_dialog.set_status, msg, fraction)
                self.connector.tx_message(self.sysex_presets[i])
        except ConnectorError as e:
            GLib.idle_add(self.show_error_dialog, str(e), None)
            self.ui_reconnect()
        GLib.idle_add(self.end_upload)

    def end_upload(self):
        self.thread.join()
        logger.debug('Thread finished')
        self.transferring.release()
        self.transfer_dialog.hide()

    def set_status_msg(self, msg):
        logger.info(msg)
        if self.main_window:
            self.statusbar.pop(self.context_id)
            self.statusbar.push(self.context_id, msg)

    def open_bank_from_file(self):
        dialog = Gtk.FileChooserDialog('Open', self.main_window,
                                       Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.add_filter(self.filter_syx)
        dialog.add_filter(self.filter_any)
        response = dialog.run()
        filename = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            self.transfer_dialog.show_pulse('Sending bank')
            GLib.timeout_add(50, self.transfer_dialog.pulse_progressbar)
            self.thread = Thread(
                target=self.set_bank_from_file, args=(filename,))
            self.thread.start()

    def set_bank_from_file(self, filename):
        try:
            self.connector.set_bank_from_file(filename)
            self.cancel_and_hide_transfer()
            GLib.idle_add(self.download_presets)
        except (ValueError) as e:
            self.cancel_and_hide_transfer()
            msg = ERROR_IN_BANK_TRANSFER.format(filename)
            desc = str(e)
            GLib.idle_add(self.show_error_dialog, msg, desc)
        except ConnectorError as e:
            self.cancel_and_hide_transfer()
            GLib.idle_add(self.show_error_dialog, str(e), None)
            self.ui_reconnect()

    def save_bank_to_file(self):
        title = 'Receiving ' + 'bulk' if self.config[utils.BULK_ON] else 'bank'
        self.transfer_dialog.show_pulse(title)
        GLib.timeout_add(50, self.transfer_dialog.pulse_progressbar)
        self.thread = Thread(target=self.get_bank_and_save)
        self.thread.start()

    def get_bank_and_save(self):
        try:
            if self.config[utils.BULK_ON]:
                data = self.connector.get_bulk()
                def_filename = 'bulk.' + preset.FILE_EXTENSION
            else:
                data = self.connector.get_bank()
                def_filename = 'bank.' + preset.FILE_EXTENSION
            self.cancel_and_hide_transfer()
            GLib.idle_add(self.ask_filename_and_save, def_filename, data)
        except ConnectorError as e:
            self.cancel_and_hide_transfer()
            GLib.idle_add(self.show_error_dialog, str(e), None)
            self.ui_reconnect()

    def ask_filename_and_save(self, def_filename, data):
        dialog = Gtk.FileChooserDialog('Save as', self.main_window,
                                       Gtk.FileChooserAction.SAVE,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
        Gtk.FileChooser.set_do_overwrite_confirmation(dialog, True)
        dialog.add_filter(self.filter_syx)
        dialog.add_filter(self.filter_any)
        dialog.set_current_name(def_filename)
        response = dialog.run()
        filename = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            try:
                self.connector.save_bank_to_file(filename, data)
            except IOError as e:
                msg = ERROR_WHILE_SAVING_BANK.format(filename)
                desc = str(e)
                GLib.idle_add(self.show_error_dialog, msg, desc)

    def cancel_and_hide_transfer(self):
        self.transfer_dialog.cancel()
        GLib.idle_add(self.transfer_dialog.hide)
        GLib.idle_add(self.thread.join)

    def show_error_dialog(self, msg, desc):
        dialog = Gtk.MessageDialog(self.main_window,
                                   flags=Gtk.DialogFlags.MODAL,
                                   type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.OK,
                                   message_format=msg)
        dialog.connect(
            'response', lambda widget, response: widget.destroy())
        dialog.format_secondary_text(desc)
        logger.error(desc)
        dialog.run()
        dialog.destroy()

    def call_connector(self, method, *args):
        logger.debug('Calling connector {:s}...'.format(str(method)))
        try:
            method(*args)
        except ConnectorError as e:
            GLib.idle_add(self.show_error_dialog, str(e), None)
            self.ui_reconnect()

    def show_about(self):
        self.about_dialog.run()
        self.about_dialog.hide()

    def quit(self):
        logger.debug('Quitting...')
        self.connector.disconnect()
        self.main_window.hide()
        Gtk.main_quit()

    def main(self):
        self.init_ui()
        self.connect()
        self.set_ui()
        Gtk.main()
