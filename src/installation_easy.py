#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  installation_easy.py
#  
#  Copyright 2013 Cinnarch
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  

import xml.etree.ElementTree as etree

from gi.repository import Gtk

import sys
import os

from config import installer_settings

import misc

import parted

from show_message import show_error

_next_page = "timezone"
_prev_page = "installation_ask"

class InstallationEasy(Gtk.Box):

    def __init__(self, params):

        self.title = params['title']
        self.ui_dir = params['ui_dir']
        self.forward_button = params['forward_button']
        self.backwards_button = params['backwards_button']

        super().__init__()
        self.ui = Gtk.Builder()
        self.ui.add_from_file(os.path.join(self.ui_dir, "installation_easy.ui"))

        self.label = dict()
        self.label['info'] = self.ui.get_object("label_info")
        self.label['mount'] = self.ui.get_object("label_mount")
        self.label['device'] = self.ui.get_object("label_device")
        self.label['root'] = self.ui.get_object("label_root")
        self.label['swap'] = self.ui.get_object("label_swap")

        self.combobox = dict()
        self.combobox['root'] = self.ui.get_object("comboboxtext_root")
        self.combobox['swap'] = self.ui.get_object("comboboxtext_swap")

        for name in self.combobox:
            self.populate_combobox_with_devices(self.combobox[name])

        self.ui.connect_signals(self)

        super().add(self.ui.get_object("installation_easy"))

        self.device = {'root':"", 'swap':""}

    def translate_ui(self):
        txt = _("You must inform about these two mount points to install Cinnarch")
        txt = '<span size="large">%s</span>' % txt
        self.label['info'].set_markup(txt)

        txt = _("Mount point")
        txt = '<b>%s</b>' % txt
        self.label['mount'].set_markup(txt)

        txt = _("Device")
        txt = '<b>%s</b>' % txt
        self.label['device'].set_markup(txt)

        txt = _("Cinnarch easy installation mode")
        txt = "<span weight='bold' size='large'>%s</span>" % txt
        self.title.set_markup(txt)

        txt = _("Install now!")
        self.forward_button.set_label(txt)

    def on_comboboxtext_root_changed(self, combobox):
        self.combobox_changed(combobox, "root")

    def on_comboboxtext_swap_changed(self, combobox):
        self.combobox_changed(combobox, "swap")

    def combobox_changed(self, combobox, name):
        tree_iter = combobox.get_active_iter()
        
        d = {'root':'swap', 'swap':'root'}
        op = d[name]
        
        if tree_iter != None:
            self.device[name] = combobox.get_active_text()
            print(self.device[name])
            if self.device[op] != "":
                if self.device[op] == self.device[name]:
                    show_error(_("You can't select the same device for both mount points!"))
                    self.forward_button.set_sensitive(False)
                else:
                    self.forward_button.set_sensitive(True)

    def prepare(self):
        self.translate_ui()
        self.show_all()
        self.forward_button.set_sensitive(False)

    def store_values(self):
        self.start_installation()

    def get_prev_page(self):
        return _prev_page

    def get_next_page(self):
        return _next_page
    
    @misc.raise_privileges
    def populate_combobox_with_devices(self, combobox):
        device_list = parted.getAllDevices()

        combobox.remove_all()
        
        extended = 2
        
        for dev in device_list:
            if not dev.path.startswith("/dev/sr"):
                try:           
                    disk = parted.Disk(dev)
                    # create list of partitions for this device (p.e. /dev/sda)
                    partition_list = disk.partitions
                    
                    for p in partition_list:
                        if p.type != extended:
                            combobox.append_text(p.path)
                except Exception as e:
                    print(e)

    def start_installation(self):
        #self.install_progress.set_sensitive(True)
        print(script_path)

        root_device = self.combobox["root"].get_active_text()
        swap_device = self.combobox["swap"].get_active_text()

        self.thread = installation_thread.InstallationThread("easy", script_path)
        self.thread.set_devices(None, self.root_device, self.swap_device)
        self.thread.start()

        #self.forward_button.set_sensitive(True)

        # simulate button click
        #self.forward_button.emit("clicked")
