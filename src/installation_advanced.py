#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  installation_advanced.py
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
#  Cinnarch Team:
#   Alex Filgueira (faidoc) <alexfilgueira.cinnarch.com>
#   Raúl Granados (pollitux) <raulgranados.cinnarch.com>
#   Gustau Castells (karasu) <karasu.cinnarch.com>
#   Kirill Omelchenko (omelcheck) <omelchek.cinnarch.com>
#   Marc Miralles (arcnexus) <arcnexus.cinnarch.com>
#   Alex Skinner (skinner) <skinner.cinnarch.com>

import xml.etree.ElementTree as etree

from gi.repository import Gtk

import subprocess

import gettext

import sys
import os

import misc

# Insert the src/parted directory at the front of the path.
base_dir = os.path.dirname(__file__) or '.'
parted_dir = os.path.join(base_dir, 'parted')
sys.path.insert(0, parted_dir)
# import Alex modules
import partition_module as pm
import fs_module as fs
import used_space
# Useful vars for gettext (translations)
APP="cnchi"
DIR="po"

# This allows to translate all py texts (not the glade ones)
gettext.textdomain(APP)
gettext.bindtextdomain(APP, DIR)

# With this we can use _("string") to translate
_ = gettext.gettext

import installation_thread

from config import installer_settings

from show_message import show_error, show_warning

_next_page = "timezone"
_prev_page = "installation_ask"

# Set this to true to avoid doing any changes on partitions
_debug = True

class InstallationAdvanced(Gtk.Box):

    def __init__(self, params):
        self.first_time = 0
        ## Store class parameters
        self.title = params['title']
        self.ui_dir = params['ui_dir']
        self.forward_button = params['forward_button']
        self.backwards_button = params['backwards_button']
        
        #stage_opts holds info about newly created partitions
        #format is tuple (label, mountpoint, fs(text), Format)
        #see its usage in listing, creating, and deleting partitions
        self.stage_opts = {}
        self.used_dic = {}
        ## Call base class
        super().__init__()

        ## Get UI items
        self.ui = Gtk.Builder()
        ui_file = os.path.join(self.ui_dir, "installation_advanced.ui")
        self.ui.add_from_file(ui_file)

        ## Connect UI signals
        self.ui.connect_signals(self)

        ## Load create and edit partition dialogs
        self.create_partition_dialog = self.ui.get_object('create_partition_dialog')
        self.edit_partition_dialog = self.ui.get_object('edit_partition_dialog')

        ## Initialize our create partition dialog filesystems' combo.
        use_combo = self.ui.get_object('partition_use_combo')
        use_combo.remove_all()
        for fs_name in sorted(fs._names):
            use_combo.append_text(fs_name)
        use_combo.set_wrap_width(2)

        ## Initialize our edit partition dialog filesystems' combo.
        use_combo = self.ui.get_object('partition_use_combo2')
        use_combo.remove_all()
        for fs_name in sorted(fs._names):
            use_combo.append_text(fs_name)
        use_combo.set_wrap_width(2)

        ## Initialize partition_types_combo
        combo = self.ui.get_object('partition_types_combo')
        combo.remove_all()
        combo.append_text("msdos (aka MBR)")
        combo.append_text("GUID Partition Table (GPT)")
        ## Automatically select first entry
        self.select_first_combobox_item(combo)

        ## Initialize our create and edit partition dialog mount points' combo.
        mount_combos = []
        mount_combos.append(self.ui.get_object('partition_mount_combo'))
        mount_combos.append(self.ui.get_object('partition_mount_combo2'))
        
        for combo in mount_combos:
            combo.remove_all()
            for mp in sorted(fs._common_mount_points):
                combo.append_text(mp)

        ## We will store our devices here
        self.disks = None

        self.grub_device_entry = self.ui.get_object('grub_device_entry')      
        self.grub_devices = dict()

        ## Initialise our partition list treeview
        self.partition_list = self.ui.get_object('partition_list_treeview')
        self.partition_list_store = None
        self.prepare_partition_list()

        ## Connect changing selection in the partition list treeview
        select = self.partition_list.get_selection()
        select.connect("changed", self.on_partition_list_treeview_selection_changed)

        ## Add ourselves to the parent class
        super().add(self.ui.get_object("installation_advanced"))


    ## Function to generate uid by partition object or path
    def gen_partition_uid(self, p=None, path=None):
        if path and not p:
            if "free" in path:
                return None
            for zz in self.all_partitions:
                for yy in zz:
                    if zz[yy].path == path:
                        p = zz[yy]
        try:
            dev = p.disk.device.path
        except:
            dev = 'thinking'
        ends = p.geometry.end
        starts = p.geometry.start
        uid = dev + str(starts) + str(ends)
        return uid
                        

    ## Activates/deactivates our buttons depending on which is selected in the
    ## partition treeview
    def check_buttons(self, selection):
        button_new = self.ui.get_object('partition_button_new')
        button_new.set_sensitive(False)

        button_delete = self.ui.get_object('partition_button_delete')
        button_delete.set_sensitive(False)

        button_edit = self.ui.get_object('partition_button_edit')
        button_edit.set_sensitive(False)
        
        button_new_label = self.ui.get_object('partition_button_new_label')
        button_new_label.set_sensitive(False)

        model, tree_iter = selection.get_selected()
        diskobj = None
        if tree_iter != None:
            path = model[tree_iter][0]
            if path == _("free space"):
                button_new.set_sensitive(True)
            else:
                disks = pm.get_devices()
                if not path in disks:
                    ## A partition is selected
                    for i in self.all_partitions:
                        if path in i:
                            diskobj = i[path].disk.device.path
                    if diskobj and model[tree_iter][1] == 'extended' and self.diskdic[diskobj]['has_logical']:
                        button_delete.set_sensitive(False)
                        button_edit.set_sensitive(False)
                    else:
                        button_delete.set_sensitive(True)    
                        button_edit.set_sensitive(True)
                else:
                    ## A drive (disk) is selected
                    button_new_label.set_sensitive(True)
                    

    ## Get all devices where we can put our Grub boot code
    ## Not using partitions (but we'll have to)
    def fill_grub_device_entry(self):       
        self.grub_device_entry.remove_all()
        self.grub_devices.clear()
        
        ## Just call get_devices once
        if self.disks == None:
            self.disks = pm.get_devices()

        for path in sorted(self.disks):
            disk = self.disks[path]
            if disk is not None:
                dev = disk.device
                ## avoid cdrom and any raid, lvm volumes or encryptfs
                if not dev.path.startswith("/dev/sr") and \
                   not dev.path.startswith("/dev/mapper"):
                    ## Hard drives measure themselves assuming kilo=1000, mega=1mil, etc
                    size_in_gigabytes = int((dev.length * dev.sectorSize) / 1000000000)
                    line = '{0} [{1} GB] ({2})'.format(dev.model, size_in_gigabytes, dev.path)
                    self.grub_device_entry.append_text(line)
                    self.grub_devices[line] = dev.path
        
        ## Automatically select first entry
        self.select_first_combobox_item(self.grub_device_entry)


    ## Automatically select first entry
    def select_first_combobox_item(self, combobox):
        tree_model = combobox.get_model()
        tree_iter = tree_model.get_iter_first()
        combobox.set_active_iter(tree_iter)


    ## Get new selected GRUB device
    def on_select_grub_drive_changed(self, widget):
        line = self.grub_device_entry.get_active_text()
        if line != None:
            self.grub_device = self.grub_devices[line]


    ## Create columns for our treeview
    def prepare_partition_list(self):
        
        render_text = Gtk.CellRendererText()
        
        render_toggle = Gtk.CellRendererToggle()
        render_toggle.connect("toggled", self.on_format_cell_toggled)
        
        col = Gtk.TreeViewColumn(_("Device"), render_text, text=0)
        self.partition_list.append_column(col)
        
        col = Gtk.TreeViewColumn(_("Type"), render_text, text=1)
        self.partition_list.append_column(col)
        
        col = Gtk.TreeViewColumn(_("Mount point"), render_text, text=2)
        self.partition_list.append_column(col)
        
        col = Gtk.TreeViewColumn(_("Label"), render_text, text=3)
        self.partition_list.append_column(col)
        
        col = Gtk.TreeViewColumn(_("Format?"), render_toggle, active=4, visible=5, sensitive=11)
        self.partition_list.append_column(col)
        
        col = Gtk.TreeViewColumn(_("Size"), render_text, text=6)
        self.partition_list.append_column(col)
        
        col = Gtk.TreeViewColumn(_("Used"), render_text, text=7)
        self.partition_list.append_column(col)   

        col = Gtk.TreeViewColumn(_("Flags"), render_text, text=9)
        self.partition_list.append_column(col)   


    ## Helper function to get a disk/partition size in human format
    def get_size(self, length, sectorSize):
        size = length * sectorSize
        size_txt = "%db" % size
        if size >= 1000000000:
            size /= 1000000000
            size_txt = "%dG" % size

        elif size >= 1000000:
            size /= 1000000
            size_txt = "%dM" % size
        
        elif size >= 1000:
            size /= 1000
            size_txt = "%dK" % size
            
        return size_txt


    ## Fill the partition list with all the data.
    def fill_partition_list(self):
        self.diskdic = {}
        self.all_partitions = []
        self.first_time += 1
        ## We will store our data model in 'partition_list_store'
        if self.partition_list_store != None:
            self.partition_list_store.clear()
        
        # Treeview columns:    
        # disc path or partition path or "free space",
        # fs_type
        # label
        # part_name
        # formatable_active
        # formatable_visible
        # size
        # used
        # partition_path
        # flags
        # formatable_selectable?
        self.partition_list_store = \
            Gtk.TreeStore(str, str, str, str, bool, bool, str, str, str, str, int, bool)
            
        ## Be sure to call get_devices once
        if self.disks == None:
            self.disks = pm.get_devices()
        self.diskdic['mounts'] = []
        ## Here we fill our model
        for disk_path in sorted(self.disks):
            if '/dev/mapper/arch_' in disk_path:
                continue
            
            self.diskdic[disk_path] = {}
            self.diskdic[disk_path]['has_logical'] = False
            self.diskdic[disk_path]['has_extended'] = False
            
            disk = self.disks[disk_path]
            
            if disk is None:
                # Maybe disk without a partition table?
                print(disk_path)
                row = [disk_path, "", "", "", False, False, "", "", "", "", 0, False]
                self.partition_list_store.append(None, row)
            else:
                dev = disk.device

                ## Get device size
                size_txt = self.get_size(dev.length, dev.sectorSize)
                
                row = [dev.path, "", "", "", False, False, size_txt, "", "", "", 0, False]
                disk_parent = self.partition_list_store.append(None, row)
                
                parent = disk_parent

                # Create a list of partitions for this device (/dev/sda for example)
                partitions = pm.get_partitions(disk)
                self.all_partitions.append(partitions)
                partition_list = pm.order_partitions(partitions)
                for partition_path in partition_list:
                    ## Get partition size
                    p = partitions[partition_path]
                    size_txt = self.get_size(p.geometry.length, dev.sectorSize)
                    fmt_enable = False
                    fmt_active = False
                    label = ""
                    fs_type = ""
                    mount_point = ""
                    used = ""
                    flags = ""
                    formatable = True

                    path = p.path
                    
                    ## Get file system
                    if p.fileSystem:
                        fs_type = p.fileSystem.type
                    else:
                        #kludge, btrfs not being detected...
                        if 'free' not in partition_path:
                            if self.gen_partition_uid(p=p) not in self.stage_opts:
                                if used_space.is_btrfs(p.path):
                                    fs_type = 'btrfs'
                            else:
                                fs_type = '?'
                        else:
                            fs_type = _("none")

                    ## Get mount point
                    if pm.check_mounted(p) and not "swap" in fs_type:
                        mount_point = self.get_mount_point(p.path)

                    if p.type == pm.PARTITION_EXTENDED:
                        ## Show 'extended' in file system type column
                        fs_type = _("extended")
                        formatable = False
                        self.diskdic[disk_path]['has_extended'] = True
                    elif p.type == pm.PARTITION_LOGICAL:
                        formatable = True
                        self.diskdic[disk_path]['has_logical'] = True
                    if p.type in (pm.PARTITION_FREESPACE,
                                  pm.PARTITION_FREESPACE_EXTENDED):
                        ## Show 'free space' instead of /dev/sda-1    
                        path = _("free space")
                        formatable = False
                    else:
                        
                        ## Get partition flags
                        flags = pm.get_flags(p)
                    if self.gen_partition_uid(p=p) in self.stage_opts:
                        (label, mount_point, fs_type, fmt_active) = self.stage_opts[self.gen_partition_uid(p=p)]           
                        fmt_enable = False
                    else:
                        fmt_enable = True
                        if 'free' not in path:
                            if self.first_time < 2:
                                if mount_point:
                                    used = pm.get_used_space(p)
                                else:
                                    used = self.get_size(used_space.get_used_space(partition_path, fs_type) * p.geometry.length, dev.sectorSize)
                                self.used_dic[(disk_path, p.geometry.start)] = used
                            else:
                                if (disk_path, p.geometry.start) in self.used_dic:
                                    used = self.used_dic[(disk_path, p.geometry.start)]
                                else:
                                    used = '0b'
                            info = fs.get_info(partition_path)
                            if 'LABEL' in info:
                                label = info['LABEL']
            
                    if mount_point:
                        self.diskdic['mounts'].append(mount_point)
            
                    row = [path, fs_type, mount_point, label, fmt_active, \
                           formatable, size_txt, used, partition_path, \
                           "", p.type, fmt_enable]
            
                    if p.type in (pm.PARTITION_LOGICAL,
                                  pm.PARTITION_FREESPACE_EXTENDED):
                        parent = myparent
                    else:
                        parent = disk_parent
                    tree_iter = self.partition_list_store.append(parent, row)

                    if p.type == pm.PARTITION_EXTENDED:
                        ## If we're an extended partition, all the logical
                        ## partitions that follow will be shown as children
                        ## of this one
                        myparent = tree_iter

        # assign our new model to our treeview
        self.partition_list.set_model(self.partition_list_store)
        self.partition_list.expand_all()
        
        # check if correct mount points are already defined, so we
        # can proceed with installation
        self.check_mount_points()
        

    ## Mark a partition to be formatted
    def on_format_cell_toggled(self, widget, path):
        print("on_format_cell_toggled")
        selected_path = Gtk.TreePath(path)
        self.partition_list_store[path][4] = not self.partition_list_store[path][4]
        print(self.partition_list_store[path][4])


    ## The user wants to edit a partition
    def on_partition_list_edit_activate(self, button):
        selection = self.partition_list.get_selection()
        
        if not selection:
            return
            
        model, tree_iter = selection.get_selected()

        if tree_iter == None:
            return
            
        print ("You selected %s" % model[tree_iter][0])

        ## Get necessary row data
        row = model[tree_iter]

        fs = row[1]
        mount_point = row[2]
        label = row[3]
        partition_path = row[8]
        print(partition_path) 
        # set fs in dialog combobox
        use_combo = self.ui.get_object('partition_use_combo2')
        use_combo_model = use_combo.get_model()
        use_combo_iter = use_combo_model.get_iter_first()

        while use_combo_iter != None:
            use_combo_row = use_combo_model[use_combo_iter]
            if use_combo_row[0] in fs:
                use_combo.set_active_iter(use_combo_iter)
                use_combo_iter = None
            else:
                use_combo_iter = use_combo_model.iter_next(use_combo_iter)

        # set mount point in dialog combobox
        mount_combo_entry = self.ui.get_object('combobox-entry2')
        mount_combo_entry.set_text(mount_point)
        
        # set label entry
        label_entry = self.ui.get_object('partition_label_entry2')
        label_entry.set_text(label)

        # Be sure to just call get_devices once
        if self.disks == None:
            self.disks = pm.get_devices()

        # Get disk_path and disk
        disk_path = self.get_disk_path_from_selection(model, tree_iter)    
        disk = self.disks[disk_path]

        # show edit partition dialog
        response = self.edit_partition_dialog.run()
        
        if response == Gtk.ResponseType.OK:
            mylabel = label_entry.get_text()
            mymount = mount_combo_entry.get_text().strip()
            if mymount in self.diskdic['mounts'] and mymount != mount_point:
                print(_('Cannot use same mount twice...'))
                show_warning(_('Cannot use same mount twice...'))
            else:
                if mount_point:
                    self.diskdic['mounts'].remove(mount_point)               
                myfmt = use_combo.get_active_text()
                if self.gen_partition_uid(path=partition_path) in self.stage_opts:
                    fmtop = True
                else:
                    fmtop = False
                self.stage_opts[self.gen_partition_uid(path=partition_path)] = (mylabel, mymount, myfmt, fmtop)
            
        self.edit_partition_dialog.hide()

        ## Update the partition list treeview
        self.fill_partition_list()


    ## This returns the disk path where the selected partition is in
    def get_disk_path_from_selection(self, model, tree_iter):
        if tree_iter != None and model != None:
            row = model[tree_iter]
            partition_path = row[8]
            
            ## Get partition type from the user selection
            part_type = row[10]
            
            # Get our parent drive
            parent_iter = model.iter_parent(tree_iter)

            if part_type == pm.PARTITION_LOGICAL:
                ## If we are a logical partition, our drive won't be our father
                ## but our grandpa (we have to skip the extended partition we're in)
                parent_iter = model.iter_parent(parent_iter)

            return model[parent_iter][0]
        else:
            return None


    ## Delete partition
    def on_partition_list_delete_activate(self, button):
        selection = self.partition_list.get_selection()
        
        if not selection:
            return
            
        model, tree_iter = selection.get_selected()

        if tree_iter == None:
            return

        ## Get row data
        row = model[tree_iter]
        mount_point = row[2]
        size_available = row[6]
        partition_path = row[8]
        if mount_point in self.diskdic['mounts']:
            self.diskdic['mounts'].remove(mount_point)
        if self.gen_partition_uid(path=partition_path) in self.stage_opts:
            del(self.stage_opts[self.gen_partition_uid(path=partition_path)])
        
        disk_path = self.get_disk_path_from_selection(model, tree_iter)

        print ("You will delete from disk [%s] partition [%s]" % (disk_path, partition_path))

        # Be sure to just call get_devices once
        if self.disks == None:
            self.disks = pm.get_devices()

        disk = self.disks[disk_path]

        partitions = pm.get_partitions(disk)
        
        part = partitions[partition_path]
        if (disk.device.path, part.geometry.start) in self.used_dic:
            del self.used_dic[(disk.device.path, part.geometry.start)]
        ## Before delete the partition, check if it's already mounted
        if pm.check_mounted(part):
            ## We unmount the partition. Should we ask first?
            subp = subprocess.Popen(['umount', part.path], stdout=subprocess.PIPE)

        ## Is it worth to show some warning message here?
        pm.delete_partition(disk, part)
        
        ## Update the partition list treeview
        self.fill_partition_list()
        

    def get_mount_point(self, partition_path):
        fsname = ''
        fstype = ''
        writable = ''
        with open('/proc/mounts') as fp:
            for line in fp:
                line = line.split()
                if line[0] == partition_path:
                    fsname = line[1]
                    fstype = line[2]
                    writable = line[3].split(',')[0]
        return fsname


    ## Add a new partition
    def on_partition_list_new_activate(self, button):
        selection = self.partition_list.get_selection()
        
        if not selection:
            return
            
        model, tree_iter = selection.get_selected()

        if tree_iter == None:
            return
            
        print ("You selected %s" % model[tree_iter][0])

        ## Get necessary row data
        row = model[tree_iter]

        ## Get partition type from the user selection
        part_type = row[10]

        ## Check that the user has selected a free space row.
        if part_type not in (pm.PARTITION_FREESPACE,
                             pm.PARTITION_FREESPACE_EXTENDED):
            return

        size_available = row[6]
        partition_path = row[8]

        # Get our parent drive
        parent_iter = model.iter_parent(tree_iter)
        
        parent_part_type = model[parent_iter][10]

        if parent_part_type == pm.PARTITION_EXTENDED:
            ## We're creating a partition inside an already created extended
            ## partition. Our drive won't be our father but our grandpa
            ## (we have to skip the extended partition we're in)
            parent_iter = model.iter_parent(parent_iter)
            isbase = False
        else:
            isbase = True
            
        disk_path = model[parent_iter][0]

        # Be sure to just call get_devices once
        if self.disks == None:
            self.disks = pm.get_devices()
                
        disk = self.disks[disk_path]
        dev = disk.device
            
        partitions = pm.get_partitions(disk)
        p = partitions[partition_path]
        
        #added extended, moving extended details up here

        # Get the objects from the dialog
        extended = disk.getExtendedPartition()
        supports_extended = disk.supportsFeature(pm.DISK_EXTENDED)
        primary_radio = self.ui.get_object('partition_create_type_primary')
        logical_radio = self.ui.get_object('partition_create_type_logical')
        extended_radio = self.ui.get_object('partition_create_type_extended')

        primary_radio.set_active(True)
        logical_radio.set_active(False)
        extended_radio.set_active(False)
        
        logical_radio.set_visible(True)
        primary_radio.set_visible(True)
        extended_radio.set_visible(True)

        if not supports_extended:
            extended_radio.set_visible(False)
        
        if isbase and extended:
            logical_radio.set_visible(False)
            extended_radio.set_visible(False)
        elif isbase and not extended:
            logical_radio.set_visible(False)
        elif not isbase:
            logical_radio.set_active(True)
            primary_radio.set_visible(False)
            extended_radio.set_visible(False)

        ## Get how many primary partitions are already created on disk
        primary_count = disk.primaryPartitionCount
        if primary_count >= disk.maxPrimaryPartitionCount:
            ## No room left for another primary partition
            primary_radio.set_sensitive(False)
        
        beginning_radio = self.ui.get_object('partition_create_place_beginning')
        end_radio = self.ui.get_object('partition_create_place_end')
        beginning_radio.set_active(True)
        end_radio.set_active(False)

        # Prepare size spin
        # +1 as not to leave unusably small space behind
        max_size_mb = int((p.geometry.length * dev.sectorSize) / 1000000) + 1
            
        size_spin = self.ui.get_object('partition_size_spinbutton')
        size_spin.set_digits(0)
        # value, lower, upper, step_incr, page_incr, page_size
        adjustment = Gtk.Adjustment(max_size_mb, 1, max_size_mb, 1, 10, 0)
        size_spin.set_adjustment(adjustment)
        size_spin.set_value(max_size_mb)
          
        # label
        label_entry = self.ui.get_object('partition_label_entry')
        label_entry.set_text("")

        #use
        use_combo = self.ui.get_object('partition_use_combo')
        use_combo.set_active(3) 

        # mount combo entry
        mount_combo_entry = self.ui.get_object('combobox-entry')
        mount_combo_entry.set_text("")

        # finally, show the create partition dialog

        response = self.create_partition_dialog.run()
        if response == Gtk.ResponseType.OK:
            mylabel = label_entry.get_text()
            mymount = mount_combo_entry.get_text().strip()
            if mymount in self.diskdic['mounts']:
                print(_('Cannot use same mount twice...'))
                show_warning(_('Cannot use same mount twice...'))
            else:
                if mymount:         
                    self.diskdic['mounts'].append(mymount)       
                myfmt = use_combo.get_active_text()
                # Get selected size
                size = int(size_spin.get_value())
                print("size : %d" % size)

                beg_var = beginning_radio.get_active()

                start_sector = p.geometry.start
                end_sector = p.geometry.end
                print(start_sector, end_sector, size, beg_var)              
                geometry = pm.geom_builder(disk, start_sector, 
                                           end_sector, size, beg_var)

                # user wants to create an extended, logical or primary partition
                if primary_radio.get_active():
                    print("Creating primary partition")
                    pm.create_partition(disk, pm.PARTITION_PRIMARY, geometry)
                elif extended_radio.get_active():
                    print("Creating extended partition")
                    pm.create_partition(disk, pm.PARTITION_EXTENDED, geometry)
                elif logical_radio.get_active():
                    logical_count = len(list(disk.getLogicalPartitions()))
                    max_logicals = disk.getMaxLogicalPartitions()        
                    if logical_count < max_logicals:
                        print("Creating logical partition")
                        # which geometry should we use here?
                        pm.create_partition(disk, pm.PARTITION_LOGICAL, geometry)
                
                # Store stage partition info in self.stage_opts
                old_parts = []
                for y in self.all_partitions:
                    for z in y:
                        old_parts.append(z)
                partitions = pm.get_partitions(disk)
                for e in partitions:
                    if e not in old_parts:
                        self.stage_opts[self.gen_partition_uid(p=partitions[e])] = (mylabel, mymount, myfmt, True)
                ## Update partition list treeview
                self.fill_partition_list()

        self.create_partition_dialog.hide()
        

    def on_partition_list_undo_activate(self, button):
        #print("on_partition_list_undo_activate")
        ## To undo user changes, we simply reload all devices        
        self.disks = pm.get_devices()

        ## Also undo stage partitions' options
        self.stage_opts = {}
        
        self.fill_partition_list()
    		

    ## Selection changed, call check_buttons to update them
    def on_partition_list_treeview_selection_changed(self, selection):
        self.check_buttons(selection)


    ## Called when clicked on the partition list treeview
    ## Inherited from Ubiquity. Not doing anything here (return false to not stop the chain of events)
    def on_partition_list_treeview_button_press_event(self, widget, event):
        #print("on_partition_list_treeview_button_press_event")
        #print(event.type)
        return False


    ## Called when a key is pressed when the partition list treeview has focus
    ## Inherited from Ubiquity. Not doing anything here (return false to not stop the chain of events)
    def on_partition_list_treeview_key_press_event(self, widget, event):
        #print("on_partition_list_treeview_key_press_event")
        return False


    ## Inherited from Ubiquity. Not doing anything here (return false to not stop the chain of events)
    def on_partition_list_treeview_row_activated(self, path, column, user_data):
        print("on_partition_list_treeview_row_activated")
        return False


    ## Inherited from Ubiquity. Not doing anything here (return false to not stop the chain of events)
    def on_partition_list_treeview_popup_menu(self, widget):
        print("on_partition_list_treeview_popup_menu")
        return False


    ## As the installer language can change anytime the user changes it, we have
    ## to "retranslate" all our widgets calling this function
    def translate_ui(self):
        txt = _("Advanced installation mode")
        txt = "<span weight='bold' size='large'>%s</span>" % txt
        self.title.set_markup(txt)
        
        txt = _("Device for boot loader installation:")
        txt = "<span weight='bold' size='small'>%s</span>" % txt
        label = self.ui.get_object('grub_device_label')
        label.set_markup(txt)
        
        txt = _("TODO: Here goes a warning message")
        txt = "<span weight='bold'>%s</span>" % txt
        label = self.ui.get_object('part_advanced_warning_message')
        label.set_markup(txt)
        
        txt = _("New partition table")
        button = self.ui.get_object('partition_button_new_label')
        button.set_label(txt)
        
        #txt = _("Revert")
        #button = self.ui.get_object('partition_button_undo')
        #button.set_label(txt)
        
        txt = _("Change...")
        button = self.ui.get_object('partition_button_edit')
        button.set_label(txt)

        ## Translate dialog "Create partition"
        txt = _("Size:")
        label = self.ui.get_object('partition_size_label')
        label.set_markup(txt)
        
        txt = _("Type:")
        label = self.ui.get_object('partition_create_type_label')
        label.set_markup(txt)
        
        txt = _("Primary")
        button = self.ui.get_object('partition_create_type_primary')
        button.set_label(txt)
               
        txt = _("Logical")
        button = self.ui.get_object('partition_create_type_logical')
        button.set_label(txt)
        
        txt = _("Extended")
        button = self.ui.get_object('partition_create_type_extended')
        button.set_label(txt)
 
        txt = _("Beginning of this space")
        button = self.ui.get_object('partition_create_place_beginning')
        button.set_label(txt)
        
        txt = _("End of this space")
        button = self.ui.get_object('partition_create_place_end')
        button.set_label(txt)
        
        txt = _("Use as:")
        label = self.ui.get_object('partition_use_label')
        label.set_markup(txt)
        
        txt = _("Mount point:")
        label = self.ui.get_object('partition_mount_label')
        label.set_markup(txt)

        txt = _("Label (optional):")
        label = self.ui.get_object('partition_label_label')
        label.set_markup(txt)
        
        txt = _("Encryption options...")
        button = self.ui.get_object('partition_encryption_settings')
        button.set_label(txt)
        
        ## Translate dialog "Edit partition"
        txt = _("Use as:")
        label = self.ui.get_object('partition_use_label2')
        label.set_markup(txt)
        
        txt = _("Mount point:")
        label = self.ui.get_object('partition_mount_label2')
        label.set_markup(txt)

        txt = _("Label (optional):")
        label = self.ui.get_object('partition_label_label2')
        label.set_markup(txt)
        
        ## Create disk partition table dialog
        txt = _("Partition table type:")
        label = self.ui.get_object('partition_type_label')
        label.set_markup(txt)

        dialog = self.ui.get_object("create_table_dialog")    
        dialog.set_title(_("Create partition table"))

        ## Change "Next" button text
        txt = _("Install now!")
        self.forward_button.set_label(txt)

        #self.ui.get_object('cancelbutton')
        #self.ui.get_object('partition_dialog_okbutton')
        

    ## Prepare our dialog to show/hide/activate/deactivate what's necessary
    def prepare(self):
        self.fill_grub_device_entry()

        self.fill_partition_list() 

        self.translate_ui()
        self.show_all()

        label = self.ui.get_object('part_advanced_recalculating_label')
        label.hide()
        
        spinner = self.ui.get_object('part_advanced_recalculating_spinner')
        spinner.hide()
        
        button = self.ui.get_object('partition_button_lvm')
        button.hide()
        
        image = self.ui.get_object('part_advanced_warning_image')
        image.hide()
        
        label = self.ui.get_object('part_advanced_warning_message')
        label.hide()      

        button = self.ui.get_object('partition_button_new')
        button.set_sensitive(False)

        button = self.ui.get_object('partition_button_delete')
        button.set_sensitive(False)

        button = self.ui.get_object('partition_button_edit')
        button.set_sensitive(False)
        
        button = self.ui.get_object('partition_button_new_label')
        button.set_sensitive(False)

        button = self.ui.get_object('partition_button_undo')
        button.set_sensitive(True)


    ## Create a new partition table
    def on_partition_list_new_label_activate(self, button):
        print("on_partition_list_new_label_activate : new partition table")
        
        ## TODO: We should check first if there's any mounted partition (including swap)'
        
        selection = self.partition_list.get_selection()
        
        if not selection:
            return
            
        model, tree_iter = selection.get_selected()

        if tree_iter == None:
            return
            
        path = model[tree_iter][0]

        # Be sure to just call get_devices once
        if self.disks == None:
            self.disks = pm.get_devices()

        disk_sel = self.disks[path]
        
        dialog = self.ui.get_object("create_table_dialog")
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            combo = self.ui.get_object('partition_types_combo')
            line = combo.get_active_text()
            if line:
                ## by default, use msdos type
                ptype = 'msdos'

                if "GPT" in line:
                    ptype = 'gpt'

                print("Creating a new partition table of type %s for disk %s" % (ptype, path))
                
                if _debug:
                    print("Debug option is on, not doing any real changes")
                else:
                    new_disk = pm.make_new_disk(path, ptype)
                    self.disks[path] = new_disk
                
                self.fill_grub_device_entry()
                self.fill_partition_list()

        dialog.hide()
        

    def check_mount_points(self):
        ## at least root (/) partition must be defined

        check_ok = False

        for disk_path in self.diskdic:
            mounts = self.diskdic['mounts']
            if "/" in mounts:
                check_ok = True

        for part_path in self.stage_opts:
            (lbl, mnt, fs, fmt) = self.stage_opts[part_path]
            if mnt == "/":
                check_ok = True

        self.forward_button.set_sensitive(check_ok)

    ## The user clicks "Install now!"
    def store_values(self):
        
        ## Create staged partitions 
        if self.disks != None:
            for disk_path in self.disks:
                disk = self.disks[disk_path]
                if _debug:
                    print("Debug option is on, not doing any real changes")
                else:
                    pm.finalize_changes(disk)
                    print("Saving changes done in %s" % disk_path)

                ## Now that partitions are created, set fs and label
                partitions = pm.get_partitions(disk)
                for partition_path in partitions:
                    ## Get label, mount point and filesystem of staged partitions
                    uid = self.gen_partition_uid(path=partition_path)
                    if uid in self.stage_opts:
                        (lbl, mnt, fs, fmt) = self.stage_opts[uid]
                        print("Creating fs of type %s in %s with label %s" % (fs, partition_path, lbl))
                        if _debug:
                            print("Debug option is on, not doing any real changes")
                        else:
                            (error, msg) = fs.create_fs(partitions[partition_path], fs, lbl)
                            print(msg)
                    elif _debug:
                        print("Partition %s not found in stage_opts" % partition_path)

        ## TODO : Format old partitions if required by user
        
        self.start_installation()

    
    ## Tell which one is our previous page (in our case installation_ask)
    def get_prev_page(self):
        return _prev_page

    
    ## Tell which one is our next page
    def get_next_page(self):
        return _next_page


    ## Start installation process
    def start_installation(self):
        ## should we add already mounted partitions to the list of
        ## partitions we will mount in the new system?
        
        mount_devices = {}
        
        for disk_path in self.disks:
            disk = self.disks[disk_path]
            partitions = pm.get_partitions(disk)
            self.all_partitions.append(partitions)
            partition_list = pm.order_partitions(partitions)
            for partition_path in partition_list:
                p = partitions[partition_path]
                uid = self.gen_partition_uid(p=p)
                if uid in self.stage_opts:
                    (label, mount_point, fs_type, fmt_active) = self.stage_opts[uid]
                    mount_devices[mount_point] = partition_path
                elif pm.check_mounted(p):
                    mount_point = self.get_mount_point(p.path)
                    mount_devices[mount_point] = partition_path
                    # TODO: also add swap
        
        self.thread = installation_thread.InstallationThread("advanced", mount_devices)
        #self.thread.start()
