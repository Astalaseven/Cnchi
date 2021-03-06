#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  slides.py
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

from gi.repository import Gtk, WebKit, GLib
import config
import os

import queue
from multiprocessing import Queue, Lock

import show_message as show
import log
import subprocess
import misc

# when we reach this page we can't go neither backwards nor forwards
_next_page = None
_prev_page = None

class Slides(Gtk.Box):

    def __init__(self, params):
        self.title = params['title']
        self.ui_dir = params['ui_dir']
        self.forward_button = params['forward_button']
        self.backwards_button = params['backwards_button']
        self.exit_button = params['exit_button']
        self.callback_queue = params['callback_queue']
        self.settings = params['settings']

        super().__init__()

        builder = Gtk.Builder()

        builder.add_from_file(os.path.join(self.ui_dir, "slides.ui"))
        builder.connect_signals(self)

        self.progress_bar = builder.get_object("progressbar")
        self.info_label = builder.get_object("info_label")
        self.scrolled_window = builder.get_object("scrolledwindow")

        self.webview = WebKit.WebView()
        
        if self.settings == None:
            html_file = '/usr/share/cnchi/data/slides.html'
        else:
            html_file = os.path.join(self.settings.get("DATA_DIR"), 'slides.html')
        
        try:
            with open(html_file) as html_stream:
                html = html_stream.read(None)
                data = os.path.join(os.getcwd(), "data")
                self.webview.load_html_string(html, "file://" + data)
        except IOError:
            pass
        
        self.scrolled_window.add(self.webview)
        
        self.install_ok = _("Installation finished!\n" \
                            "Do you want to restart your system now?")

        #self.scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        
        #self.lock = Lock()

        super().add(builder.get_object("slides"))
        
    def translate_ui(self):
        txt = _("Installing Antergos...")
        txt = "<span weight='bold' size='large'>%s</span>" % txt
        self.title.set_markup(txt)

        if len(self.info_label.get_label()) <= 0:
            self.set_message(_("Please wait..."))
        
        self.install_ok = _("Installation finished!\n" \
                            "Do you want to restart your system now?")

    def prepare(self, direction):
        self.translate_ui()
        self.show_all()

        self.backwards_button.hide()
        self.forward_button.hide()
        self.exit_button.hide()

    def store_values(self):
        return False

    def get_prev_page(self):
        return _prev_page

    def get_next_page(self):
        return _next_page

    def refresh(self):
        while Gtk.events_pending():
            Gtk.main_iteration()

    def set_message(self, txt):
        txt = "<span color='darkred'>%s</span>" % txt
        self.info_label.set_markup(txt)

    def manage_events_from_cb_queue(self):
        '''
        try:
            event = self.callback_queue.get_nowait()
        except queue.Empty:
            event = ()
        '''
        event = self.get_newest_event()

        if len(event) > 0:
            if event[0] == "percent":
                self.progress_bar.set_fraction(event[1])
            elif event[0] == "finished":
                log.debug(event[1])
                self.set_message(self.install_ok)
                response = show.question(self.install_ok)
                if response == Gtk.ResponseType.YES:
                    self.reboot()
                else:
                    tmp_files = [".setup-running", ".km-running", "setup-pacman-running", "setup-mkinitcpio-running", ".tz-running", ".setup", "Cnchi.log"]
                    for t in tmp_files:
                        p = os.path.join("/tmp", t)
                        if os.path.exists(p):
                            # TODO: some of these tmp files are created with sudo privileges
                            # (this should be fixed) meanwhile, we need sudo privileges to remove them
                            with misc.raised_privileges():
                                os.remove(p)
                    Gtk.main_quit()
                        
                self.exit_button.show()
                return False
            elif event[0] == "error":
                show.fatal_error(event[1])
            else:
                #with self.lock:
                log.debug(event[1])
                self.set_message(event[1])
                # remove old messages from the event queue 
                #self.callback_queue.clear()
                
        return True

    # FIXME: pac.py generates too many events. Here we can only
    # get the newest one and delete all the old ones.
    '''
    # Delete all the old events and get the newest one
    def get_newest_event(self):
        event = ()
        queue_empty = False
        while queue_empty == False:
            try:
                event = self.callback_queue.get_nowait()
            except queue.Empty:
                queue_empty = True
        return event
    '''

    def get_newest_event(self):
        try:
            event = self.callback_queue.get_nowait()
        except queue.Empty:
            event = ()
        return event


    @misc.raise_privileges
    def reboot(self):
        os.system("sync")
        subprocess.call(["/sbin/reboot", "--reboot", "--force", "--no-wall"])

class TestWindow(Gtk.Window):
    def __init__(self, box):
        Gtk.Window.__init__(self, title='Cinnarch Installer Test')
        self.set_title(_('Cinnarch Installer'))
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        self.set_size_request(800, 500)
        self.ui = Gtk.Builder()
        self.ui.add_from_file("/usr/share/cnchi/ui/cnchi.ui")

        self.add(self.ui.get_object("main"))

        self.main_box = self.ui.get_object("main_box")
        
        self.main_box.add(box)

if __name__ == '__main__':
    import gettext
    import locale
    
    print("Testing slides screen")
    
    APP = "Cinnarch Test Window"
    DIR = "/usr/share/locale"
    
    # This allows to translate all py texts (not the glade ones)
    gettext.textdomain(APP)
    gettext.bindtextdomain(APP, DIR)

    locale_code, encoding = locale.getdefaultlocale()
    lang = gettext.translation (APP, DIR, [locale_code], None, True)
    lang.install()

    # With this we can use _("string") to translate
    gettext.install(APP, localedir=DIR, codeset=None, names=[locale_code])

    params = {}
    params['title'] = "TITLE"
    params['ui_dir'] = "/usr/share/cnchi/ui"
    params['forward_button'] = None
    params['backwards_button'] = None
    params['exit_button'] = None
    params['callback_queue'] = None
    params['settings'] = None
    
    slides = Slides(params)
    
    w = TestWindow(slides)
    
    w.show_all()
    
    Gtk.main()
