#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  desktop.py
#  
#  Copyright 2013 Antergos
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
#  Antergos Team:
#   Alex Filgueira (faidoc) <alexfilgueira.antergos.com>
#   Raúl Granados (pollitux) <raulgranados.antergos.com>
#   Gustau Castells (karasu) <karasu.antergos.com>
#   Kirill Omelchenko (omelcheck) <omelchek.antergos.com>
#   Marc Miralles (arcnexus) <arcnexus.antergos.com>
#   Alex Skinner (skinner) <skinner.antergos.com>

from gi.repository import Gtk, GLib
import config
import os

_next_page = "installation_ask"
_prev_page = "check"

class DesktopAsk(Gtk.Box):

    def __init__(self, params):
        self.title = params['title']
        self.ui_dir = params['ui_dir']
        self.forward_button = params['forward_button']
        self.backwards_button = params['backwards_button']
        self.settings = params['settings']

        super().__init__()

        self.ui = Gtk.Builder()
        self.ui.add_from_file(os.path.join(self.ui_dir, "desktop.ui"))

        self.desktops_dir = os.path.join(self.settings.get("DATA_DIR"), "desktops/")

        self.desktop_info = self.ui.get_object("desktop_info")
        self.treeview_desktop = self.ui.get_object("treeview_desktop")

        self.ui.connect_signals(self)

        self.desktop_choice = 'gnome'
        
        self.enabled_desktops = self.settings.get("desktops")
               
        self.desktops = {
         "gnome" : "Gnome",
         "cinnamon" : "Cinnamon",
         "xfce" : "Xfce",
         "lxde" : "Lxde",
         "openbox" : "Openbox",
         "enlightenment" : "Enlightenment (e17)",
         "kde" : "KDE",
         "razor" : "Razor-qt",
         "nox" : "Without X" }

        self.set_desktop_list()

        super().add(self.ui.get_object("desktop"))

    def translate_ui(self, desktop):
        image = self.ui.get_object("image_desktop")     
        label = self.ui.get_object("desktop_info")

        if desktop == 'gnome':
            txt = _("Gnome 3 is an easy and elegant way to use your " \
            "computer. It is designed to put you in control " \
            "and bring freedom to everybody. GNOME 3 is developed " \
            "by the GNOME community.")
            txt = "<span weight='bold'>GNOME</span>\n" + txt

        elif desktop == 'cinnamon':
            txt = _("Cinnamon it's a fork of GNOME Shell, initially " \
            "developed by (and for) Linux Mint. It attempts to " \
            "provide a more traditional user environment based " \
            "on the desktop metaphor, like GNOME 2")
            txt = "<span weight='bold'>CINNAMON</span>\n" + txt

        elif desktop == 'xfce':
            txt = _("Xfce is a lightweight desktop environment " \
            "for UNIX-like operating systems. It aims to " \
            "be fast and low on system resources, while " \
            "still being visually appealing and user friendly.")
            txt = "<span weight='bold'>XFCE</span>\n" + txt

        elif desktop == 'lxde':
            txt = _("Extremely fast-performing and energy-saving desktop " \
            "environment. It comes with a beautiful interface, " \
            "multi-language support, standard keyboard short cuts " \
            "and additional features like tabbed file browsing.")
            txt = "<span weight='bold'>LXDE</span>\n" + txt

        elif desktop == 'openbox':
            txt = _("Openbox is a highly configurable, next generation " \
            "window manager with extensive standards support." \
            "The *box visual style is well known for its " \
            "minimalistic appearance.")
            txt = "<span weight='bold'>OPENBOX</span>\n" + txt

        elif desktop == 'enlightenment':
            txt = _("Enlightenment is not just a window manager for Linux/X11 " \
            "and others, but also a whole suite of libraries to help " \
            "you create beautiful user interfaces with much less work")
            txt = "<span weight='bold'>ENLIGHTMENT</span>\n" + txt

        elif desktop == 'kde':
            txt = _("The KDE Community is an international technology " \
            "team dedicated to creating a free and user-friendly " \
            "computing experience, offering an advanced graphical " \
            "desktop and a wide variety of applications.")
            txt = "<span weight='bold'>KDE</span>\n" + txt

        elif desktop == 'razor':
            txt = _("Razor-qt is an advanced, easy-to-use, and fast desktop " \
            "environment based on Qt technologies. It has been " \
            "tailored for users who value simplicity, speed, and " \
            "an intuitive interface.")
            txt = "<span weight='bold'>RAZOR-QT</span>\n" + txt
            
        elif desktop == 'nox':
            txt = _("Don't install any desktop.")
            txt = "<span weight='bold'>NoX</span>\n" + txt
            
        label.set_markup(txt)

        image.set_from_file(self.desktops_dir + desktop + ".png")

        txt = _("Select your desktop")
        txt = "<span weight='bold' size='large'>%s</span>" % txt
        self.title.set_markup(txt)
            
    def prepare(self, direction):
        self.translate_ui(self.desktop_choice)
        self.show_all()

    def set_desktop_list(self):
        render = Gtk.CellRendererText()
        col_desktops = Gtk.TreeViewColumn(_("Desktops"), render, text=0)
        liststore_desktop = Gtk.ListStore(str)
        self.treeview_desktop.append_column(col_desktops)
        self.treeview_desktop.set_model(liststore_desktop)

        names = []
        for d in self.enabled_desktops:
            names.append(self.desktops[d])
        
        names.sort()
        
        for n in names:
            liststore_desktop.append([n])
                
        self.select_default_row(self.treeview_desktop, 'Gnome')

    def set_desktop(self, desktop):
        for k in self.desktops.keys():
            if self.desktops[k] == desktop:
                self.desktop_choice = k
                self.translate_ui(self.desktop_choice)
                return
                
    def on_treeview_desktop_cursor_changed(self, treeview):
        selected = treeview.get_selection()
        if selected:
            (ls, iter) = selected.get_selected()
            if iter:
                desktop = ls.get_value(iter, 0)
                self.set_desktop(desktop)
        
    def store_values(self):
        self.settings.set('desktop', self.desktop_choice)
        print(self.desktop_choice)
        return True

    def select_default_row(self, treeview, desktop):   
        model = treeview.get_model()
        iterator = model.iter_children(None)
        while iterator is not None:
            if model.get_value(iterator, 0) == desktop:
                path = model.get_path(iterator)
                treeview.get_selection().select_path(path)
                GLib.idle_add(self.scroll_to_cell, treeview, path)
                break
            iterator = model.iter_next(iterator)

    def scroll_to_cell(self, treeview, path):
        treeview.scroll_to_cell(path)
        return False

    def get_prev_page(self):
        return _prev_page

    def get_next_page(self):
        return _next_page
