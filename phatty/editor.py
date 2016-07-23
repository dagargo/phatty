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


# TODO: remove
import time

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

# TODO: delete class


class ConnectorMock(object):

    def __init__(self):
        self.sw_version = 'mock'

    def connect(self, device):
        True

    def disconnect(self):
        True

    def connected(self):
        return True

    def get_preset(self, i):
        time.sleep(0.05)
        return [0] * 191

    def tx_message(self, data):
        time.sleep(0.05)

    def set_preset(self, id):
        pass

    def set_bank_from_file(self, filename):
        raise ValueError()

    def get_bank(self):
        time.sleep(3)
        return [1, 2, 3]

    def get_bulk(self):
        return get_bank()

    def set_bank_from_file(self, filename):
        pass

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
        self.button.show()
        self.dialog.set_title(title)
        self.running = True
        self.progressbar.set_fraction(0)
        self.dialog.show()

    def show_pulse(self, title):
        self.label.set_text('')
        self.button.hide()
        self.dialog.set_title(title)
        self.progressbar.set_fraction(0)
        self.running = True
        self.dialog.show()

    def cancel(self):
        self.running = False

    def hide(self):
        self.dialog.hide()

    def set_status(self, msg, fraction):
        self.label.set_text(msg)
        self.progressbar.set_fraction(fraction)

    def pulse_progressbar(self):
        self.progressbar.pulse()
        if self.running:
            return True
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
        self.dialog.show()

    def save(self):
        active = self.devices.get_active()
        device = self.device_liststore[active][0]
        self.phatty.config[utils.DEVICE] = device
        self.phatty.config[utils.BULK_ON] = self.bulk_switch.get_active()
        self.phatty.config[utils.DOWNLOAD_AUTO] = self.auto_switch.get_active()
        logger.debug('Configuration: {:s}'.format(str(self.phatty.config)))
        utils.write_config(self.phatty.config)
        self.phatty.ui_reconnect()
        self.dialog.hide()


class Editor(object):
    """Phatty user interface"""

    def __init__(self):
        self.connector = connector.Connector()  # ConnectorMock()
        self.main_window = None
        self.sysex_presets = []
        self.config = utils.read_config()
        self.transferring = Lock()

    def init_ui(self):
        self.main_window = builder.get_object('main_window')
        self.main_window.connect(
            'delete-event', lambda widget, event: self.quit())
        self.main_window.set_position(Gtk.WindowPosition.CENTER)
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
        self.presets = builder.get_object('preset_liststore')
        self.preset_selection = builder.get_object('preset_selection')
        self.presets.connect("row-deleted", self.row_deleted)
        self.preset_selection.connect("changed", self.selection_changed)
        self.preset_name_renderer = builder.get_object(
            'preset_name_renderer')
        self.preset_name_renderer.connect("edited", self.text_edited)
        self.transfer_dialog = TransferDialog(self.main_window)
        self.settings_dialog = SettingsDialog(self)

        self.filter_syx = Gtk.FileFilter()
        self.filter_syx.set_name('MIDI sysex')
        self.filter_syx.add_pattern('*.' + preset.FILE_EXTENSION)
        self.filter_syx.add_pattern('*.' + preset.FILE_EXTENSION_EX)

        self.filter_any = Gtk.FileFilter()
        self.filter_any.set_name('Any files')
        self.filter_any.add_pattern('*')

        self.main_window.present()

    def selection_changed(self, selection):
        model, iter = selection.get_selected()
        if iter != None:
            logger.debug('Preset {:d} selected'.format(model[iter][0]))
            self.connector.set_preset(model[iter][0])

    def text_edited(self, widget, row, name):
        logger.debug('Changing preset name...')
        normalized_name = preset.normalize_name(name)
        self.presets[row][1] = normalized_name
        preset.set_preset_name(self.sysex_presets[int(row)], name)

    def row_deleted(self, tree_model, path):
        if not self.transferring.locked():
            logger.debug('Reordering...')
            new_sysex_presets = []
            for i in range(connector.MAX_PRESETS):
                sysex_preset = self.sysex_presets[self.presets[i][0]]
                preset.set_preset_number(sysex_preset, i)
                new_sysex_presets.append(sysex_preset)
                self.presets[i][0] = i
            self.sysex_presets = new_sysex_presets

    def connect(self):
        device = self.config[utils.DEVICE]
        self.connector.connect(device)
        if self.connector.connected():
            conn_msg = CONN_MSG.format(self.connector.sw_version)
            self.set_status_msg(conn_msg)
        else:
            self.set_status_msg('Not connected')

    def ui_reconnect(self):
        self.connect()
        self.set_ui()

    def set_ui(self):
        if self.connector.connected() and self.config[utils.DOWNLOAD_AUTO]:
            self.download_presets()
        self.download_button.set_sensitive(self.connector.connected())
        self.upload_button.set_sensitive(
            self.connector.connected() and len(self.sysex_presets) > 0)
        self.open_button.set_sensitive(self.connector.connected())
        self.save_button.set_sensitive(self.connector.connected())

    def download_presets(self):
        logger.debug('Starting download thread...')
        self.transfer_dialog.show('Downloading presets')
        self.transferring.acquire()
        self.presets.clear()
        self.sysex_presets.clear()
        self.thread = Thread(target=self.do_download)
        self.thread.start()

    def do_download(self):
        for i in range(connector.MAX_PRESETS):
            if not self.transfer_dialog.running:
                logger.debug('Cancelling download...')
                break
            msg = 'Downloading preset {:d}...'.format(i)
            logger.debug(msg)
            fraction = (i + 1) / connector.MAX_PRESETS
            GLib.idle_add(self.transfer_dialog.set_status, msg, fraction)
            p = self.connector.get_preset(i)
            preset_name = preset.get_preset_name(p)
            GLib.idle_add(self.add_preset, i, preset_name)
            self.sysex_presets.append(p)
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

    def upload_presets(self):
        logger.debug('Starting upload thread...')
        self.transfer_dialog.show("Uploading presets")
        self.transferring.acquire()
        self.thread = Thread(target=self.do_upload)
        self.thread.start()

    def do_upload(self):
        for i in range(connector.MAX_PRESETS):
            if not self.transfer_dialog.running:
                logger.debug('Cancelling upload...')
                break
            msg = 'Uploading preset {:d}...'.format(i)
            logger.debug(msg)
            fraction = (i + 1) / connector.MAX_PRESETS
            GLib.idle_add(self.transfer_dialog.set_status, msg, fraction)
            self.connector.tx_message(self.sysex_presets[i])
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
        except (IOError, ValueError) as e:
            self.cancel_and_hide_transfer()
            msg = ERROR_IN_BANK_TRANSFER.format(filename)
            desc = str(e)
            GLib.idle_add(self.show_error_dialog, msg, desc)

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
        except IOError as e:
            self.cancel_and_hide_transfer()
            msg = ERROR_IN_BANK_TRANSFER.format(filename)
            desc = str(e)
            GLib.idle_add(self.show_error_dialog, msg, desc)

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

    def show_about(self):
        self.about_dialog.run()
        self.about_dialog.hide()

    def quit(self):
        logger.debug('Quitting...')
        self.connector.disconnect()
        self.main_window.hide()
        Gtk.main_quit()
        return True

    def main(self):
        self.init_ui()
        self.connect()
        self.set_ui()
        Gtk.main()
