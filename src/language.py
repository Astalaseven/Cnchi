#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  language.py
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

from gi.repository import Gtk
import gettext
import locale
import os

# Useful vars for gettext (translations)
APP="cnchi"
DIR="po"

# Import functions
from config import installer_settings
import i18n

import logging
logging.basicConfig(filename=installer_settings["log_file"], level=logging.DEBUG)

_next_page = "check"
_prev_page = None

class Language(Gtk.Box):

    def __init__(self, params):

        self.title = params['title']
        self.ui_dir = params['ui_dir']
        self.forward_button = params['forward_button']
        self.backwards_button = params['backwards_button']

        super().__init__()

        self.ui = Gtk.Builder()
        self.ui.add_from_file(os.path.join(self.ui_dir, "language.ui"))
        self.ui.connect_signals(self)

        self.label_choose_language = self.ui.get_object("label_choose_language")
        self.treeview_language = self.ui.get_object("treeview_language")

        self.translate_ui()

        self.set_languages_list()

        super().add(self.ui.get_object("language"))

    def translate_ui(self):
        txt = _("Welcome to the Cinnarch Installer")
        txt = '<span weight="bold" size="large">%s</span>' % txt
        self.title.set_markup(txt)

        txt = _("Please choose your language:")
        txt = '<span weight="bold">%s</span>' % txt
        self.label_choose_language.set_markup(txt)

        label = self.ui.get_object("welcome_label")
        txt = _("Lorem ipsum dolor sit amet, consectetur adipiscing elit.\n" \
        "Integer elementum, leo vitae porta elementum, eros diam\n" \
        "pretium magna, in tincidunt magna velit at tellus. Praesent\n" \
        "a tortor nec risus blandit sodales. Mauris tristique semper\n" \
        "nunc, eget euismod sem vehicula ut. Nam pharetra justo et\n" \
        "lorem feugiat quis vestibulum arcu malesuada. Vivamus\n" \
        "tristique augue in nisi iaculis nec sollicitudin eros pharetra.\n" \
        "Duis id arcu magna, nec convallis mi. In tempor volutpat dictum.\n" \
        "Vestibulum eros lacus, pharetra vel ultricies quis, sagittis sed orci.\n" \
        "\n" \
        "The installation process may resize or erase partitions on your hard disk.\n" \
        "Be sure to take a full backup of any valuable data before running\n" \
        "this program.")
        label.set_markup(txt)

        txt = _("Welcome to Cinnarch!")
        print(txt)
        txt = "<span weight='bold' size='large'>%s</span>" % txt
        self.title.set_markup(txt)


    def set_languages_list(self):
        liststore_language = Gtk.ListStore(str)

        render = Gtk.CellRendererText()
        col_languages = Gtk.TreeViewColumn(_("Languages"), render, text=0)
        self.treeview_language.set_model(liststore_language)
        self.treeview_language.append_column(col_languages)

        current_language, sorted_choices, display_map = i18n.get_languages()

        for lang in sorted_choices:
            liststore_language.append([lang])

    def set_language(self, locale_code):
        if locale_code is None:
            locale_code, encoding = locale.getdefaultlocale()

        try:
            lang = gettext.translation (APP, DIR, [locale_code] )
            lang.install()
            self.translate_ui()
        except IOError:
            print("Can't find translation file for the %s language" % (locale_code))


    def on_treeview_language_cursor_changed(self, treeview):
        selected = treeview.get_selection()
        if selected:
            (ls, iter) = selected.get_selected()
            if iter:
                current_language, sorted_choices, display_map = i18n.get_languages()
                language = ls.get_value(iter, 0)
                language_code = display_map[language][1]
                self.set_language(language_code)

    def store_values(self):
        selected = self.treeview_language.get_selection()

        (ls, iter) = selected.get_selected()
        language = ls.get_value(iter,0)

        current_language, sorted_choices, display_map = i18n.get_languages()

        installer_settings["language_name"] = display_map[language][0]
        installer_settings["language_code"] = display_map[language][1]

        logging.debug("language_name is " + installer_settings["language_name"])
        logging.debug("language_code is " + installer_settings["language_code"])
        print("language_name is " + installer_settings["language_name"])
        print("language_code is " + installer_settings["language_code"])

    def prepare(self):
        self.translate_ui()
        self.show_all()

    def get_prev_page(self):
        return _prev_page

    def get_next_page(self):
        return _next_page