#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2005-2007  Donald N. Allingham
# Copyright (C) 2008       Brian G. Matherly
# Copyright (C) 2009       Benny Malengier
# Copyright (C) 2010       Nick Hall
# Copyright (C) 2010       Jakim Friant
# Copyright (C) 2012       Gary Burton
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

# $Id$

"""
Manages the main window and the pluggable views
"""

#-------------------------------------------------------------------------
#
# Standard python modules
#
#-------------------------------------------------------------------------
from __future__ import print_function
from collections import defaultdict
import os
import time
import datetime
from gen.ggettext import sgettext as _
from cStringIO import StringIO
from collections import defaultdict
import sys
import posixpath

#-------------------------------------------------------------------------
#
# set up logging
#
#-------------------------------------------------------------------------
import logging
LOG = logging.getLogger(".")

#-------------------------------------------------------------------------
#
# GNOME modules
#
#-------------------------------------------------------------------------
import gtk

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from cli.grampscli import CLIManager
from gui.plug import tool
from gen.plug import (START, END)
from gen.plug import REPORT
from gen.plug.report._constants import standalone_categories
from gui.plug import (PluginWindows, ReportPluginDialog, ToolPluginDialog)
from gui.plug.report import report
from gui.utils import AvailableUpdates
from gui.pluginmanager import GuiPluginManager
import Relationship
import DisplayState
import const
import constfunc
import config
import Errors
from QuestionDialog import (ErrorDialog, WarningDialog, QuestionDialog2,
                            InfoDialog)
from gui import widgets
import UndoHistory
import Utils
from gui.dbloader import DbLoader
import GrampsDisplay
from gui.widgets.progressdialog import ProgressMonitor, GtkProgressDialog
from gui.configure import GrampsPreferences
from gen.db.backup import backup
from gen.db.exceptions import DbException
from gui.aboutdialog import GrampsAboutDialog
from gui.navigator import Navigator
from gui.views.tags import Tags

#-------------------------------------------------------------------------
#
# Constants
#
#-------------------------------------------------------------------------
if constfunc.is_quartz():
    try:
        import gtkosx_application as QuartzApp
        _GTKOSXAPPLICATION = True
    except:
        _GTKOSXAPPLICATION = False
else:
    _GTKOSXAPPLICATION = False

_UNSUPPORTED = _("Unsupported")

UIDEFAULT = '''<ui>
<menubar name="MenuBar">
  <menu action="FileMenu">
    <menuitem action="Open"/>
    <menu action="OpenRecent">
    </menu>
    <separator/>
    <menuitem action="Import"/>
    <menuitem action="Export"/>
    <placeholder name="LocalExport"/>
    <menuitem action="Backup"/>
    <separator/>
    <menuitem action="Abandon"/>
    <menuitem action="Quit"/>
  </menu>
  <menu action="EditMenu">
    <menuitem action="Undo"/>
    <menuitem action="Redo"/>
    <menuitem action="UndoHistory"/>
    <separator/>
    <placeholder name="CommonEdit"/>
    <separator/>
    <placeholder name="TagMenu"/>
    <separator/>
    <menuitem action="ScratchPad"/>
    <separator/>
    <menuitem action="Preferences"/>
  </menu>
  <menu action="ViewMenu">
    <menuitem action="ConfigView"/>
    <menuitem action="Navigator"/>
    <menuitem action="Toolbar"/>
    <placeholder name="Bars"/>
    <menuitem action="Fullscreen"/>
    <separator/>
    <placeholder name="ViewsInCategory"/>
    <separator/>
  </menu>
  <menu action="GoMenu">
    <placeholder name="CommonGo"/>
    <placeholder name="CommonHistory"/>
  </menu>
  <menu action="BookMenu">
    <placeholder name="AddEditBook"/>
    <separator/>
    <placeholder name="GoToBook"/>
  </menu>
  <menu action="ReportsMenu">
  </menu>
  <menu action="ToolsMenu">
  </menu>
  <menu action="WindowsMenu">
    <placeholder name="WinMenu"/>
  </menu>
  <menu action="HelpMenu">
    <menuitem action="UserManual"/>
    <menuitem action="FAQ"/>
    <menuitem action="KeyBindings"/>
    <menuitem action="TipOfDay"/>
    <menuitem action="PluginStatus"/>
    <separator/>
    <menuitem action="HomePage"/>
    <menuitem action="MailingLists"/>
    <menuitem action="ReportBug"/>
    <menuitem action="ExtraPlugins"/>
    <separator/>
    <menuitem action="About"/>
  </menu>
</menubar>
<toolbar name="ToolBar">
  <placeholder name="CommonNavigation"/>
  <separator/>
  <toolitem action="ScratchPad"/>
  <toolitem action="Reports"/>
  <toolitem action="Tools"/>
  <separator/>
  <placeholder name="TagTool"/>
  <separator/>
  <placeholder name="CommonEdit"/>
  <separator/>
  <placeholder name="ViewsInCategory"/>
  <separator/>
  <toolitem action="ConfigView"/>
</toolbar>
<accelerator action="F2"/>
<accelerator action="F3"/>
<accelerator action="F4"/>
<accelerator action="F5"/>
<accelerator action="F6"/>
<accelerator action="F7"/>
<accelerator action="F8"/>
<accelerator action="F9"/>
<accelerator action="F11"/>
<accelerator action="F12"/>
<accelerator action="<CONTROL>1"/>
<accelerator action="<CONTROL>2"/>
<accelerator action="<CONTROL>3"/>
<accelerator action="<CONTROL>4"/>
<accelerator action="<CONTROL>5"/>
<accelerator action="<CONTROL>6"/>
<accelerator action="<CONTROL>7"/>
<accelerator action="<CONTROL>8"/>
<accelerator action="<CONTROL>9"/>
<accelerator action="<CONTROL>0"/>
<accelerator action="<CONTROL>BackSpace"/>
<accelerator action="<CONTROL>J"/>
<accelerator action="<CONTROL>N"/>
<accelerator action="<CONTROL>P"/>
</ui>
'''

WIKI_HELP_PAGE_FAQ = '%s_-_FAQ' % const.URL_MANUAL_PAGE
WIKI_HELP_PAGE_KEY = '%s_-_Keybindings' % const.URL_MANUAL_PAGE
WIKI_HELP_PAGE_MAN = '%s' % const.URL_MANUAL_PAGE

#-------------------------------------------------------------------------
#
# ViewManager
#
#-------------------------------------------------------------------------

class ViewManager(CLIManager):
    """
    Overview
    ========

    The ViewManager is the session manager of the program.
    Specifically, it manages the main window of the program. It is closely tied
    into the gtk.UIManager to control all menus and actions.

    The ViewManager controls the various Views within the GRAMPS programs.
    Views are organised in categories. The categories can be accessed via
    a sidebar. Within a category, the different views are accesible via the
    toolbar of view menu.

    A View is a particular way of looking a information in the GRAMPS main
    window. Each view is separate from the others, and has no knowledge of
    the others.

    Examples of current views include:

    - Person View
    - Relationship View
    - Family View
    - Source View

    The View Manager does not have to know the number of views, the type of
    views, or any other details about the views. It simply provides the
    method of containing each view, and has methods for creating, deleting and
    switching between the views.

    """

    def __init__(self, dbstate, view_category_order):
        """
        The viewmanager is initialised with a dbstate on which GRAMPS is
        working, and a fixed view_category_order, which is the order in which
        the view categories are accessible in the sidebar.
        """
        CLIManager.__init__(self, dbstate, False)
        if _GTKOSXAPPLICATION:
            self.macapp = QuartzApp.Application()

        self.view_category_order = view_category_order

        #set pluginmanager to GUI one
        self._pmgr = GuiPluginManager.get_instance()
        self.merge_ids = []
        self.toolactions = None
        self.tool_menu_ui_id = None
        self.reportactions = None
        self.report_menu_ui_id = None

        self.active_page = None
        self.pages = []
        self.page_lookup = {}
        self.views = None
        self.current_views = [] # The current view in each category
        self.view_changing = False

        self.show_navigator = config.get('interface.view')
        self.show_toolbar = config.get('interface.toolbar-on')
        self.fullscreen = config.get('interface.fullscreen')

        self.__build_main_window()
        self.__connect_signals()
        if _GTKOSXAPPLICATION:
            self.macapp.ready()

        self.do_reg_plugins(self.dbstate, self.uistate)
        #plugins loaded now set relationship class
        self.rel_class = Relationship.get_relationship_calculator()
        self.uistate.set_relationship_class()
        # Need to call after plugins have been registered
        self.uistate.connect('update-available', self.process_updates)
        self.check_for_updates()

    def check_for_updates(self):
        """
        Check for add-on updates.
        """
        howoften = config.get("behavior.check-for-updates")
        update = False
        if howoften != 0: # update never if zero
            y,m,d = list(map(int,
                  config.get("behavior.last-check-for-updates").split("/")))
            days = (datetime.date.today() - datetime.date(y, m, d)).days
            if howoften == 1 and days >= 30: # once a month
                update = True
            elif howoften == 2 and days >= 7: # once a week
                update = True
            elif howoften == 3 and days >= 1: # once a day
                update = True
            elif howoften == 4: # always
                update = True

        if update:
            AvailableUpdates(self.uistate).start()

    def process_updates(self, addon_update_list):
        """
        Called when add-on updates are available.
        """
        try:
            PluginWindows.UpdateAddons(self.uistate, [], addon_update_list)
        except WindowActiveError:
            pass

        self.do_reg_plugins(self.dbstate, self.uistate)

    def _errordialog(self, title, errormessage):
        """
        Show the error.
        In the GUI, the error is shown, and a return happens
        """
        ErrorDialog(title, errormessage)
        return 1

    def __build_main_window(self):
        """
        Builds the GTK interface
        """
        width = config.get('interface.width')
        height = config.get('interface.height')

        self.window = gtk.Window()
        self.window.set_icon_from_file(const.ICON)
        self.window.set_default_size(width, height)

        vbox = gtk.VBox()
        self.window.add(vbox)
        hpane = gtk.HPaned()
        self.ebox = gtk.EventBox()

        self.navigator = Navigator(self)
        self.ebox.add(self.navigator.get_top())
        hpane.add1(self.ebox)
        hpane.show()

        self.notebook = gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.set_show_tabs(False)
        self.notebook.show()
        self.__init_lists()
        self.__build_ui_manager()

        hpane.add2(self.notebook)
        self.menubar = self.uimanager.get_widget('/MenuBar')
        self.toolbar = self.uimanager.get_widget('/ToolBar')
        self.__attach_menubar(vbox)
        vbox.pack_start(self.toolbar, False)
        vbox.add(hpane)
        vbox.pack_end(self.__setup_statusbar(), False)
        vbox.show()

        self.progress_monitor = ProgressMonitor(
            GtkProgressDialog, ("", self.window))

        self.uistate = DisplayState.DisplayState(
            self.window, self.statusbar, self.progress, self.warnbtn,
            self.uimanager, self.progress_monitor, self)

        # Create history objects
        for nav_type in ('Person', 'Family', 'Event', 'Place', 'Source',
                         'Citation', 'Repository', 'Note', 'Media'):
            self.uistate.register(self.dbstate, nav_type, 0)

        self.dbstate.connect('database-changed', self.uistate.db_changed)

        self.tags = Tags(self.uistate, self.dbstate)

        self.sidebar_menu = self.uimanager.get_widget(
            '/MenuBar/ViewMenu/Sidebar/')

        # handle OPEN button, insert it into the toolbar. Unfortunately,
        # UIManager has no built in support for and Open Recent button

        openbtn = self.__build_open_button()
        self.uistate.set_open_widget(openbtn)
        self.toolbar.insert(openbtn, 0)

        self.recent_manager = DisplayState.RecentDocsMenu(
            self.uistate, self.dbstate, self._read_recent_file)
        self.recent_manager.build()

        self.db_loader = DbLoader(self.dbstate, self.uistate)

        self.__setup_navigator()

        if self.show_toolbar:
            self.toolbar.show()
        else:
            self.toolbar.hide()

        if self.fullscreen:
            self.window.fullscreen()

        # Showing the main window is deferred so that
        # ArgHandler can work without it always shown
        # But we need to realize it here to have gtk.gdk.window handy
        self.window.realize()

    def __load_sidebar_plugins(self):
        """
        Load the sidebar plugins.
        """
        for pdata in self._pmgr.get_reg_sidebars():
            module = self._pmgr.load_plugin(pdata)
            if not module:
                print("Error loading sidebar '%s': skipping content"
                      % pdata.name)
                continue

            sidebar_class = getattr(module, pdata.sidebarclass)
            sidebar_page = sidebar_class(self.dbstate, self.uistate)
            self.navigator.add(pdata.menu_label, sidebar_page, pdata.order)

    def __setup_statusbar(self):
        """
        Create the statusbar that sits at the bottom of the window
        """
        self.progress = gtk.ProgressBar()
        self.progress.set_size_request(100, -1)
        self.progress.hide()

        self.statusbar = widgets.Statusbar()
        self.statusbar.show()

        self.warnbtn = widgets.WarnButton()

        hbox2 = gtk.HBox()
        hbox2.set_spacing(4)
        hbox2.set_border_width(2)
        hbox2.pack_start(self.progress, False)
        hbox2.pack_start(self.warnbtn, False)
        hbox2.pack_end(self.statusbar, True)
        hbox2.show()
        return hbox2

    def __setup_navigator(self):
        """
        If we have enabled te sidebar, show it, and turn off the tabs. If
        disabled, hide the sidebar and turn on the tabs.
        """
        if self.show_navigator:
            self.ebox.show()
        else:
            self.ebox.hide()

    def __build_open_button(self):
        """
        Build the OPEN button. Since GTK's UIManager does not have support for
        the Open Recent button, we must build in on our own.
        """
        openbtn = gtk.MenuToolButton('gramps-db')
        openbtn.connect('clicked', self.__open_activate)
        openbtn.set_sensitive(False)
        openbtn.set_tooltip_text(_("Connect to a recent database"))
        openbtn.show()
        return openbtn

    def __connect_signals(self):
        """
        Connects the signals needed
        """
        self.window.connect('delete-event', self.quit)
        self.notebook.connect('switch-page', self.view_changed)
        if _GTKOSXAPPLICATION:
            self.macapp.connect('NSApplicationWillTerminate', self.quit)

    def __init_lists(self):
        """
        Initialize the actions lists for the UIManager
        """
        self._file_action_list = [
            ('FileMenu', None, _('_Family Trees')),
            ('Open', 'gramps-db', _('_Manage Family Trees...'), "<control>o",
             _("Manage databases"), self.__open_activate),
            ('OpenRecent', None, _('Open _Recent'), None,
             _("Open an existing database")),
            ('Quit', gtk.STOCK_QUIT, _('_Quit'), "<control>q", None,
             self.quit),
            ('ViewMenu', None, _('_View')),
            ('EditMenu', None, _('_Edit')),
            ('Preferences', gtk.STOCK_PREFERENCES, _('_Preferences...'), None,
             None, self.preferences_activate),
            ('HelpMenu', None, _('_Help')),
            ('HomePage', None, _('Gramps _Home Page'), None, None,
             home_page_activate),
            ('MailingLists', None, _('Gramps _Mailing Lists'), None, None,
             mailing_lists_activate),
            ('ReportBug', None, _('_Report a Bug'), None, None,
             report_bug_activate),
            ('ExtraPlugins', None, _('_Extra Reports/Tools'), None, None,
             extra_plugins_activate),
            ('About', gtk.STOCK_ABOUT, _('_About'), None, None,
             self.display_about_box),
            ('PluginStatus', None, _('_Plugin Manager'), None, None,
             self.__plugin_status),
            ('FAQ', None, _('_FAQ'), None, None, faq_activate),
            ('KeyBindings', None, _('_Key Bindings'), None, None, key_bindings),
            ('UserManual', gtk.STOCK_HELP, _('_User Manual'), 'F1', None,
             manual_activate),
            ('TipOfDay', None, _('Tip of the Day'), None, None,
             self.tip_of_day_activate),
            ]

        self._readonly_action_list = [
            ('Export', 'gramps-export', _('_Export...'), "<control>e", None,
             self.export_data),
            ('Backup', None, _("Make Backup..."), None,
             _("Make a Gramps XML backup of the database"), self.quick_backup),
            ('Abandon', gtk.STOCK_REVERT_TO_SAVED,
             _('_Abandon Changes and Quit'), None, None, self.abort),
            ('Reports', 'gramps-reports', _('_Reports'), None,
             _("Open the reports dialog"), self.reports_clicked),
            ('GoMenu', None, _('_Go')),
            ('ReportsMenu', None, _('_Reports')),
            ('WindowsMenu', None, _('_Windows')),
            ('F2', None, 'F2', "F2", None, self.__keypress),
            ('F3', None, 'F3', "F3", None, self.__keypress),
            ('F4', None, 'F4', "F4", None, self.__keypress),
            ('F5', None, 'F5', "F5", None, self.__keypress),
            ('F6', None, 'F6', "F6", None, self.__keypress),
            ('F7', None, 'F7', "F7", None, self.__keypress),
            ('F8', None, 'F9', "F8", None, self.__keypress),
            ('F9', None, 'F9', "F9", None, self.__keypress),
            ('F11', None, 'F11', "F11", None, self.__keypress),
            ('<CONTROL>1', None, '<CONTROL>1', "<CONTROL>1", None, self.__gocat),
            ('<CONTROL>2', None, '<CONTROL>2', "<CONTROL>2", None, self.__gocat),
            ('<CONTROL>3', None, '<CONTROL>3', "<CONTROL>3", None, self.__gocat),
            ('<CONTROL>4', None, '<CONTROL>4', "<CONTROL>4", None, self.__gocat),
            ('<CONTROL>5', None, '<CONTROL>5', "<CONTROL>5", None, self.__gocat),
            ('<CONTROL>6', None, '<CONTROL>6', "<CONTROL>6", None, self.__gocat),
            ('<CONTROL>7', None, '<CONTROL>7', "<CONTROL>7", None, self.__gocat),
            ('<CONTROL>8', None, '<CONTROL>8', "<CONTROL>8", None, self.__gocat),
            ('<CONTROL>9', None, '<CONTROL>9', "<CONTROL>9", None, self.__gocat),
            ('<CONTROL>0', None, '<CONTROL>0', "<CONTROL>0", None, self.__gocat),
            # NOTE: CTRL+ALT+NUMBER is set in src/plugins/sidebar/cat...py
            ('<CONTROL>BackSpace', None, '<CONTROL>BackSpace',
             "<CONTROL>BackSpace", None, self.__keypress),
            ('<CONTROL>Delete', None, '<CONTROL>Delete',
             "<CONTROL>Delete", None, self.__keypress),
            ('<CONTROL>Insert', None, '<CONTROL>Insert',
             "<CONTROL>Insert", None, self.__keypress),
            ('F12', None, 'F12', "F12", None, self.__keypress),
            ('<CONTROL>J', None, '<CONTROL>J',
             "<CONTROL>J", None, self.__keypress),
            ('<CONTROL>N', None, '<CONTROL>N', "<CONTROL>N", None,
             self.__next_view),
            ('<CONTROL>P', None, '<CONTROL>P', "<CONTROL>P", None,
             self.__prev_view),
            ]

        self._action_action_list = [
            ('ScratchPad', gtk.STOCK_PASTE, _('Clip_board'), "<control>b",
             _("Open the Clipboard dialog"), self.scratchpad),
            ('Import', 'gramps-import', _('_Import...'), "<control>i", None,
             self.import_data),
            ('Tools', 'gramps-tools', _('_Tools'), None,
             _("Open the tools dialog"), self.tools_clicked),
            ('BookMenu', None, _('_Bookmarks')),
            ('ToolsMenu', None, _('_Tools')),
            ('ConfigView', 'gramps-config', _('_Configure View...'),
             '<shift><control>c', _('Configure the active view'),
             self.config_view),
            ]

        self._file_toggle_action_list = [
            ('Navigator', None, _('_Navigator'), "<control>m", None,
             self.navigator_toggle, self.show_navigator ),
            ('Toolbar', None, _('_Toolbar'), None, None, self.toolbar_toggle,
             self.show_toolbar ),
            ('Fullscreen', None, _('F_ull Screen'), "F11", None,
             self.fullscreen_toggle, self.fullscreen),
            ]

        self._undo_action_list = [
            ('Undo', gtk.STOCK_UNDO, _('_Undo'), '<control>z', None,
             self.undo),
            ]

        self._redo_action_list = [
            ('Redo', gtk.STOCK_REDO, _('_Redo'), '<shift><control>z', None,
             self.redo),
            ]

        self._undo_history_action_list = [
            ('UndoHistory', 'gramps-undo-history',
             _('Undo History...'), "<control>H", None, self.undo_history),
            ]

    def __keypress(self, action):
        """
        Callback that is called on a keypress. It works by extracting the
        name of the associated action, and passes that to the active page
        (current view) so that it can take the associated action.
        """
        name = action.get_name()
        try:
            self.active_page.call_function(name)
        except Exception:
            self.uistate.push_message(self.dbstate,
                                      _("Key %s is not bound") % name)

    def __gocat(self, action):
        """
        Callback that is called on ctrl+number press. It moves to the 
        requested category like __next_view/__prev_view. 0 is 10
        """
        cat = int(action.get_name()[-1])
        if cat == 0:
            cat = 10
        cat -= 1
        if cat >= len(self.current_views):
            #this view is not present
            return False
        self.goto_page(cat, None)

    def __next_view(self, action):
        """
        Callback that is called when the next category action is selected.
        It selects the next category as the active category. If we reach the end, 
        we wrap around to the first.
        """
        curpage = self.notebook.get_current_page()
        #find cat and view of the current page
        for key in self.page_lookup:
            if self.page_lookup[key] == curpage:
                cat_num, view_num = key
                break
        #now go to next category
        if cat_num >= len(self.current_views)-1:
            self.goto_page(0, None)
        else:
            self.goto_page(cat_num+1, None)

    def __prev_view(self, action):
        """
        Callback that is called when the previous category action is selected.
        It selects the previous category as the active category. If we reach the
        beginning of the list, we wrap around to the last.
        """
        curpage = self.notebook.get_current_page()
        #find cat and view of the current page
        for key in self.page_lookup:
            if self.page_lookup[key] == curpage:
                cat_num, view_num = key
                break
        #now go to next category
        if cat_num > 0:
            self.goto_page(cat_num-1, None)
        else:
            self.goto_page(len(self.current_views)-1, None)

    def init_interface(self):
        """
        Initialize the interface.
        """
        self.views = get_available_views()
        defaults = views_to_show(self.views,
                                 config.get('preferences.use-last-view'))
        self.current_views = defaults[2]

        self.__load_sidebar_plugins()

        self.goto_page(defaults[0], defaults[1])

        if not self.file_loaded:
            self.actiongroup.set_visible(False)
            self.readonlygroup.set_visible(False)
            self.undoactions.set_visible(False)
            self.redoactions.set_visible(False)
            self.undohistoryactions.set_visible(False)
        self.fileactions.set_sensitive(False)
        self.__build_tools_menu(self._pmgr.get_reg_tools())
        self.__build_report_menu(self._pmgr.get_reg_reports())
        self._pmgr.connect('plugins-reloaded',
                             self.__rebuild_report_and_tool_menus)
        self.fileactions.set_sensitive(True)
        self.uistate.widget.set_sensitive(True)
        config.connect("interface.statusbar", self.__statusbar_key_update)

    def __statusbar_key_update(self, client, cnxn_id, entry, data):
        """
        Callback function for statusbar key update
        """
        self.uistate.modify_statusbar(self.dbstate)

    def post_init_interface(self, show_manager=True):
        """
        Showing the main window is deferred so that
        ArgHandler can work without it always shown
        """
        self.window.show()
        if not self.dbstate.db.is_open() and show_manager:
            self.__open_activate(None)

    def do_load_plugins(self):
        """
        Loads the plugins at initialization time. The plugin status window is
        opened on an error if the user has requested.
        """
        # load plugins
        self.uistate.status_text(_('Loading plugins...'))
        error = CLIManager.do_load_plugins(self)

        #  get to see if we need to open the plugin status window
        if error and config.get('behavior.pop-plugin-status'):
            self.__plugin_status()

        self.uistate.push_message(self.dbstate, _('Ready'))

    def do_reg_plugins(self, dbstate, uistate):
        """
        Register the plugins at initialization time. The plugin status window
        is opened on an error if the user has requested.
        """
        # registering plugins
        self.uistate.status_text(_('Registering plugins...'))
        error = CLIManager.do_reg_plugins(self, dbstate, uistate)

        #  get to see if we need to open the plugin status window
        if error and config.get('behavior.pop-plugin-status'):
            self.__plugin_status()

        self.uistate.push_message(self.dbstate, _('Ready'))

    def quit(self, *obj):
        """
        Closes out the program, backing up data
        """
        # mark interface insenstitive to prevent unexpected events
        self.uistate.set_sensitive(False)

        # backup data, and close the database
        self.__backup()
        self.dbstate.db.close()

        # have each page save anything, if they need to:
        self.__delete_pages()

        # save the current window size
        (width, height) = self.window.get_size()
        config.set('interface.width', width)
        config.set('interface.height', height)
        config.save()
        gtk.main_quit()

    def __backup(self):
        """
        Backup the current file as a backup file.
        """
        if self.dbstate.db.has_changed:
            self.uistate.set_busy_cursor(1)
            self.uistate.progress.show()
            self.uistate.push_message(self.dbstate, _("Autobackup..."))
            try:
                backup(self.dbstate.db)
            except DbException, msg:
                ErrorDialog(_("Error saving backup data"), msg)
            self.uistate.set_busy_cursor(0)
            self.uistate.progress.hide()

    def abort(self, obj=None):
        """
        Abandon changes and quit.
        """
        if self.dbstate.db.abort_possible:

            dialog = QuestionDialog2(
                _("Abort changes?"),
                _("Aborting changes will return the database to the state "
                  "it was before you started this editing session."),
                _("Abort changes"),
                _("Cancel"))

            if dialog.run():
                self.dbstate.db.disable_signals()
                while self.dbstate.db.undo():
                    pass
                self.quit()
        else:
            WarningDialog(
                _("Cannot abandon session's changes"),
                _('Changes cannot be completely abandoned because the '
                  'number of changes made in the session exceeded the '
                  'limit.'))

    def __init_action_group(self, name, actions, sensitive=True, toggles=None):
        """
        Initialize an action group for the UIManager
        """
        new_group = gtk.ActionGroup(name)
        new_group.add_actions(actions)
        if toggles:
            new_group.add_toggle_actions(toggles)
        new_group.set_sensitive(sensitive)
        self.uimanager.insert_action_group(new_group, 1)
        return new_group

    def __build_ui_manager(self):
        """
        Builds the UIManager, and the associated action groups
        """
        self.uimanager = gtk.UIManager()

        accelgroup = self.uimanager.get_accel_group()

        self.actiongroup = self.__init_action_group(
            'MainWindow', self._action_action_list)
        self.readonlygroup = self.__init_action_group(
            'AllMainWindow', self._readonly_action_list)
        self.undohistoryactions = self.__init_action_group(
            'UndoHistory', self._undo_history_action_list)
        self.fileactions = self.__init_action_group(
            'FileWindow', self._file_action_list,
            toggles=self._file_toggle_action_list)
        self.undoactions = self.__init_action_group(
            'Undo', self._undo_action_list, sensitive=False)
        self.redoactions = self.__init_action_group(
            'Redo', self._redo_action_list, sensitive=False)
        self.window.add_accel_group(accelgroup)

        self.uimanager.add_ui_from_string(UIDEFAULT)
        self.uimanager.ensure_update()

    def __attach_menubar(self, vbox):
        vbox.pack_start(self.menubar, False, True, 0)
        if _GTKOSXAPPLICATION:
            menubar = self.uimanager.get_widget("/MenuBar")
            menubar.hide()
            quit_item = self.uimanager.get_widget("/MenuBar/FileMenu/Quit")
            about_item = self.uimanager.get_widget("/MenuBar/HelpMenu/About")
            prefs_item = self.uimanager.get_widget("/MenuBar/EditMenu/Preferences")
            self.macapp.set_menu_bar(menubar)
            self.macapp.insert_app_menu_item(about_item, 0)
            self.macapp.insert_app_menu_item(prefs_item, 1)

    def preferences_activate(self, obj):
        """
        Open the preferences dialog.
        """
        try:
            GrampsPreferences(self.uistate, self.dbstate)
        except Errors.WindowActiveError:
            return

    def tip_of_day_activate(self, obj):
        """
        Display Tip of the day
        """
        import TipOfDay
        TipOfDay.TipOfDay(self.uistate)

    def __plugin_status(self, obj=None):
        """
        Display plugin status dialog
        """
        try:
            PluginWindows.PluginStatus(self.dbstate, self.uistate, [])
        except Errors.WindowActiveError:
            pass

    def navigator_toggle(self, obj):
        """
        Set the sidebar based on the value of the toggle button. Save the
        results in the configuration settings
        """
        if obj.get_active():
            self.ebox.show()
            config.set('interface.view', True)
            self.show_navigator = True
        else:
            self.ebox.hide()
            config.set('interface.view', False)
            self.show_navigator = False
        config.save()

    def toolbar_toggle(self, obj):
        """
        Set the toolbar based on the value of the toggle button. Save the
        results in the configuration settings
        """
        if obj.get_active():
            self.toolbar.show()
            config.set('interface.toolbar-on', True)
        else:
            self.toolbar.hide()
            config.set('interface.toolbar-on', False)
        config.save()

    def fullscreen_toggle(self, obj):
        """
        Set the main Granps window fullscreen based on the value of the
        toggle button. Save the setting in the config file.
        """
        if obj.get_active():
            self.window.fullscreen()
            config.set('interface.fullscreen', True)
        else:
            self.window.unfullscreen()
            config.set('interface.fullscreen', False)
        config.save()

    def get_views(self):
        """
        Return the view definitions.
        """
        return self.views

    def goto_page(self, cat_num, view_num):
        """
        Create the page if it doesn't exist and make it the current page.
        """
        if view_num is None:
            view_num = self.current_views[cat_num]
        else:
            self.current_views[cat_num] = view_num

        page_num = self.page_lookup.get((cat_num, view_num))
        if page_num is None:
            page_def = self.views[cat_num][view_num]
            page_num = self.notebook.get_n_pages()
            self.page_lookup[(cat_num, view_num)] = page_num
            self.__create_page(page_def[0], page_def[1])

        self.notebook.set_current_page(page_num)
        return self.pages[page_num]

    def get_category(self, cat_name):
        """
        Return the category number from the given category name.
        """
        for cat_num, cat_views in enumerate(self.views):
            if cat_name == cat_views[0][0].category[1]:
                return cat_num
        return None

    def __create_dummy_page(self, pdata, error):
        from gui.views.pageview import DummyPage
        return DummyPage(pdata.name, pdata, self.dbstate, self.uistate,
                    _("View failed to load. Check error output."), error)
    
    def __create_page(self, pdata, page_def):
        """
        Create a new page and set it as the current page.
        """
        try:
            page = page_def(pdata, self.dbstate, self.uistate)
        except:
            import traceback
            LOG.warn("View '%s' failed to load." % pdata.id)
            traceback.print_exc()
            page = self.__create_dummy_page(pdata, traceback.format_exc())

        try:
            page_display = page.get_display()
        except:
            import traceback
            print("ERROR: '%s' failed to create view" % pdata.name)
            traceback.print_exc()
            page = self.__create_dummy_page(pdata, traceback.format_exc())
            page_display = page.get_display()

        page.define_actions()
        page.post()

        self.pages.append(page)

        # create icon/label for notebook tab (useful for debugging)
        hbox = gtk.HBox()
        image = gtk.Image()
        image.set_from_stock(page.get_stock(), gtk.ICON_SIZE_MENU)
        hbox.pack_start(image, False)
        hbox.add(gtk.Label(pdata.name))
        hbox.show_all()
        page_num = self.notebook.append_page(page.get_display(), hbox)
        return page

    def view_changed(self, notebook, page, page_num):
        """
        Called when the notebook page is changed.
        """
        if self.view_changing:
            return
        self.view_changing = True

        cat_num = view_num = None
        for key in self.page_lookup:
            if self.page_lookup[key] == page_num:
                cat_num, view_num = key
                break

        # Save last view in configuration
        view_id = self.views[cat_num][view_num][0].id
        config.set('preferences.last-view', view_id)
        last_views = config.get('preferences.last-views')
        if len(last_views) != len(self.views):
            # If the number of categories has changed then reset the defaults
            last_views = [''] * len(self.views)
        last_views[cat_num] = view_id
        config.set('preferences.last-views', last_views)
        config.save()

        self.navigator.view_changed(cat_num, view_num)
        self.__change_page(page_num)
        self.view_changing = False

    def __change_page(self, page_num):
        """
        Perform necessary actions when a page is changed.
        """
        if not self.dbstate.open:
            return

        self.__disconnect_previous_page()

        self.active_page = self.pages[page_num]
        self.active_page.set_active()
        self.__connect_active_page(page_num)

        self.uimanager.ensure_update()
        if _GTKOSXAPPLICATION:
            self.macapp.sync_menubar()

        while gtk.events_pending():
            gtk.main_iteration()

        self.active_page.change_page()

    def __delete_pages(self):
        """
        Calls on_delete() for each view
        """
        for page in self.pages:
            page.on_delete()

    def __disconnect_previous_page(self):
        """
        Disconnects the previous page, removing the old action groups
        and removes the old UI components.
        """
        map(self.uimanager.remove_ui, self.merge_ids)

        if self.active_page:
            self.active_page.set_inactive()
            groups = self.active_page.get_actions()
            for grp in groups:
                if grp in self.uimanager.get_action_groups():
                    self.uimanager.remove_action_group(grp)

    def __connect_active_page(self, page_num):
        """
        Inserts the action groups associated with the current page
        into the UIManager
        """
        for grp in self.active_page.get_actions():
            self.uimanager.insert_action_group(grp, 1)

        uidef = self.active_page.ui_definition()
        self.merge_ids = [self.uimanager.add_ui_from_string(uidef)]

        for uidef in self.active_page.additional_ui_definitions():
            mergeid = self.uimanager.add_ui_from_string(uidef)
            self.merge_ids.append(mergeid)

        configaction = self.actiongroup.get_action('ConfigView')
        if self.active_page.can_configure():
            configaction.set_sensitive(True)
        else:
            configaction.set_sensitive(False)

    def import_data(self, obj):
        """
        Imports a file
        """
        if self.dbstate.db.is_open():
            self.db_loader.import_file()
            infotxt = self.db_loader.import_info_text()
            if infotxt:
                InfoDialog(_('Import Statistics'), infotxt, self.window)
            self.__post_load()

    def __open_activate(self, obj):
        """
        Called when the Open button is clicked, opens the DbManager
        """
        from dbman import DbManager
        dialog = DbManager(self.dbstate, self.window)
        value = dialog.run()
        if value:
            (filename, title) = value
            filename = filename.encode(sys.getfilesystemencoding())
            self.db_loader.read_file(filename)
            self._post_load_newdb(filename, 'x-directory/normal', title)

    def __post_load(self):
        """
        This method is for the common UI post_load, both new files
        and added data like imports.
        """
        self.dbstate.db.undo_callback = self.__change_undo_label
        self.dbstate.db.redo_callback = self.__change_redo_label
        self.__change_undo_label(None)
        self.__change_redo_label(None)
        self.dbstate.db.undo_history_callback = self.undo_history_update
        self.undo_history_close()

        self.uistate.window.window.set_cursor(None)

    def _post_load_newdb(self, filename, filetype, title=None):
        """
        The method called after load of a new database.
        Inherit CLI method to add GUI part
        """
        self._post_load_newdb_nongui(filename, title)
        self._post_load_newdb_gui(filename, filetype, title)

    def _post_load_newdb_gui(self, filename, filetype, title=None):
        """
        Called after a new database is loaded to do GUI stuff
        """
        # GUI related post load db stuff
        # Update window title
        if filename[-1] == os.path.sep:
            filename = filename[:-1]
        name = os.path.basename(filename)
        if title:
            name = title

        if self.dbstate.db.readonly:
            msg =  "%s (%s) - Gramps" % (name, _('Read Only'))
            self.uistate.window.set_title(msg)
            self.actiongroup.set_sensitive(False)
        else:
            msg = "%s - Gramps" % name
            self.uistate.window.set_title(msg)
            self.actiongroup.set_sensitive(True)

        self.__change_page(self.notebook.get_current_page())
        self.actiongroup.set_visible(True)
        self.readonlygroup.set_visible(True)
        self.undoactions.set_visible(True)
        self.redoactions.set_visible(True)
        self.undohistoryactions.set_visible(True)

        self.recent_manager.build()

        # Call common __post_load method for GUI update after a change
        self.__post_load()

    def __change_undo_label(self, label):
        """
        Change the UNDO label
        """
        self.uimanager.remove_action_group(self.undoactions)
        self.undoactions = gtk.ActionGroup('Undo')
        if label:
            self.undoactions.add_actions([
                ('Undo', gtk.STOCK_UNDO, label, '<control>z', None, self.undo)])
        else:
            self.undoactions.add_actions([
                ('Undo', gtk.STOCK_UNDO, _('_Undo'),
                 '<control>z', None, self.undo)])
            self.undoactions.set_sensitive(False)
        self.uimanager.insert_action_group(self.undoactions, 1)

    def __change_redo_label(self, label):
        """
        Change the REDO label
        """
        self.uimanager.remove_action_group(self.redoactions)
        self.redoactions = gtk.ActionGroup('Redo')
        if label:
            self.redoactions.add_actions([
                ('Redo', gtk.STOCK_REDO, label, '<shift><control>z',
                 None, self.redo)])
        else:
            self.redoactions.add_actions([
                ('Redo', gtk.STOCK_UNDO, _('_Redo'),
                 '<shift><control>z', None, self.redo)])
            self.redoactions.set_sensitive(False)
        self.uimanager.insert_action_group(self.redoactions, 1)

    def undo_history_update(self):
        """
        This function is called to update both the state of
        the Undo History menu item (enable/disable) and
        the contents of the Undo History window.
        """
        try:
            # Try updating undo history window if it exists
            self.undo_history_window.update()
        except AttributeError:
            # Let it go: history window does not exist
            return

    def undo_history_close(self):
        """
        Closes the undo history
        """
        try:
            # Try closing undo history window if it exists
            if self.undo_history_window.opened:
                self.undo_history_window.close()
        except AttributeError:
            # Let it go: history window does not exist
            return

    def quick_backup(self, obj):
        """
        Make a quick XML back with or without media.
        """
        from QuestionDialog import QuestionDialog2
        window = gtk.Dialog(_("Gramps XML Backup"),
                            self.uistate.window,
                            gtk.DIALOG_DESTROY_WITH_PARENT, None)
        window.set_size_request(400, -1)
        ok_button = window.add_button(gtk.STOCK_OK,
                                      gtk.RESPONSE_APPLY)
        close_button = window.add_button(gtk.STOCK_CLOSE,
                                         gtk.RESPONSE_CLOSE)
        vbox = window.get_content_area()
        hbox = gtk.HBox()
        label = gtk.Label(_("Path:"))
        label.set_justify(gtk.JUSTIFY_LEFT)
        label.set_size_request(90, -1)
        label.set_alignment(0, .5)
        hbox.pack_start(label, False)
        path_entry = gtk.Entry()
        text = config.get('paths.quick-backup-directory')
        path_entry.set_text(text)
        hbox.pack_start(path_entry, True)
        file_entry = gtk.Entry()
        button = gtk.Button()
        button.connect("clicked",
                       lambda widget: self.select_backup_path(widget, path_entry))
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_OPEN, gtk.ICON_SIZE_BUTTON)
        image.show()
        button.add(image)
        hbox.pack_end(button, False)
        vbox.pack_start(hbox, False)
        hbox = gtk.HBox()
        label = gtk.Label(_("File:"))
        label.set_justify(gtk.JUSTIFY_LEFT)
        label.set_size_request(90, -1)
        label.set_alignment(0, .5)
        hbox.pack_start(label, False)
        struct_time = time.localtime()
        file_entry.set_text(config.get('paths.quick-backup-filename') %
                            {"filename": self.dbstate.db.get_dbname(),
                             "year": struct_time.tm_year,
                             "month": struct_time.tm_mon,
                             "day": struct_time.tm_mday,
                             "hour": struct_time.tm_hour,
                             "minutes": struct_time.tm_min,
                             "seconds": struct_time.tm_sec,
                             "extension": "gpkg",
                             })
        hbox.pack_end(file_entry, True)
        vbox.pack_start(hbox, False)
        hbox = gtk.HBox()
        bytes = 0
        mbytes = "0"
        for media in self.dbstate.db.iter_media_objects():
            fullname = Utils.media_path_full(self.dbstate.db, media.get_path())
            try:
                bytes += posixpath.getsize(fullname)
                length = len(str(bytes))
                if bytes <= 999999:
                    mbytes = "< 1"
                else:
                    mbytes = str(bytes)[:(length-6)]
            except OSError:
                pass
        label = gtk.Label(_("Media:"))
        label.set_justify(gtk.JUSTIFY_LEFT)
        label.set_size_request(90, -1)
        label.set_alignment(0, .5)
        hbox.pack_start(label, False)
        include = gtk.RadioButton(None, "%s (%s %s)" % (_("Include"),
                                                        mbytes, _("Megabyte|MB")))
        exclude = gtk.RadioButton(include, _("Exclude"))
        include.connect("toggled", lambda widget: self.media_toggle(widget, file_entry))
        hbox.pack_start(include, True)
        hbox.pack_end(exclude, True)
        vbox.pack_start(hbox, False)
        window.show_all()
        d = window.run()
        window.hide()
        if d == gtk.RESPONSE_APPLY:
            # if file exists, ask if overwrite; else abort
            basefile = file_entry.get_text()
            basefile = basefile.replace("/", r"-")
            filename = os.path.join(path_entry.get_text(), basefile)
            filename = filename.encode(sys.getfilesystemencoding())
            if os.path.exists(filename):
                sfilename = Utils.get_unicode_path_from_env_var(filename)
                question = QuestionDialog2(
                    _("Backup file already exists! Overwrite?"),
                    _("The file '%s' exists.") % sfilename,
                    _("Proceed and overwrite"),
                    _("Cancel the backup"))
                yes_no = question.run()
                if not yes_no:
                    return
            self.uistate.set_busy_cursor(1)
            self.pulse_progressbar(0)
            self.uistate.progress.show()
            self.uistate.push_message(self.dbstate, _("Making backup..."))
            if include.get_active():
                from ExportPkg import PackageWriter
                writer = PackageWriter(self.dbstate.db, filename,
                       msg_callback=lambda m1, m2: ErrorDialog(m1, m2),
                       callback=self.pulse_progressbar)
                writer.export()
            else:
                from ExportXml import XmlWriter
                writer = XmlWriter(self.dbstate.db,
                       msg_callback=lambda m1, m2: ErrorDialog(m1, m2),
                       callback=self.pulse_progressbar,
                       strip_photos=0, compress=1)
                writer.write(filename)
            self.uistate.set_busy_cursor(0)
            self.uistate.progress.hide()
            filename = Utils.get_unicode_path_from_env_var(filename)
            self.uistate.push_message(self.dbstate, _("Backup saved to '%s'") % filename)
            config.set('paths.quick-backup-directory', path_entry.get_text())
        else:
            self.uistate.push_message(self.dbstate, _("Backup aborted"))
        window.destroy()

    def pulse_progressbar(self, value, text=None):
        self.progress.set_fraction(min(value/100.0, 1.0))
        if text:
            self.progress.set_text("%s: %d%%" % (text, value))
        else:
            self.progress.set_text("%d%%" % value)
        while gtk.events_pending():
            gtk.main_iteration()

    def select_backup_path(self, widget, path_entry):
        """
        Choose a backup folder. Make sure there is one highlighted in
        right pane, otherwise FileChooserDialog will hang.
        """
        f = gtk.FileChooserDialog(
            _("Select backup directory"),
            action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
            buttons=(gtk.STOCK_CANCEL,
                     gtk.RESPONSE_CANCEL,
                     gtk.STOCK_APPLY,
                     gtk.RESPONSE_OK))
        mpath = path_entry.get_text()
        if not mpath:
            mpath = const.HOME_DIR
        f.set_current_folder(os.path.dirname(mpath))
        f.set_filename(os.path.join(mpath, "."))
        status = f.run()
        if status == gtk.RESPONSE_OK:
            filename = f.get_filename()
            if filename:
                val = Utils.get_unicode_path_from_file_chooser(filename)
                if val:
                    path_entry.set_text(val)
        f.destroy()
        return True

    def media_toggle(self, widget, file_entry):
        """
        Toggles media include values in the quick backup dialog.
        """
        include = widget.get_active()
        extension = "gpkg" if include else "gramps"
        filename = file_entry.get_text()
        if "." in filename:
            base, ext = filename.rsplit(".", 1)
            file_entry.set_text("%s.%s" % (base, extension))
        else:
            file_entry.set_text("%s.%s" % (filename, extension))

    def reports_clicked(self, obj):
        """
        Displays the Reports dialog
        """
        try:
            ReportPluginDialog(self.dbstate, self.uistate, [])
        except Errors.WindowActiveError:
            return

    def tools_clicked(self, obj):
        """
        Displays the Tools dialog
        """
        try:
            ToolPluginDialog(self.dbstate, self.uistate, [])
        except Errors.WindowActiveError:
            return

    def scratchpad(self, obj):
        """
        Displays the Clipboard (was scratchpad)
        """
        import ScratchPad
        try:
            ScratchPad.ScratchPadWindow(self.dbstate, self.uistate)
        except Errors.WindowActiveError:
            return

    def config_view(self, obj):
        """
        Displays the configuration dialog for the active view
        """
        self.active_page.configure()

    def undo(self, obj):
        """
        Calls the undo function on the database
        """
        self.uistate.set_busy_cursor(1)
        self.dbstate.db.undo()
        self.uistate.set_busy_cursor(0)

    def redo(self, obj):
        """
        Calls the redo function on the database
        """
        self.uistate.set_busy_cursor(1)
        self.dbstate.db.redo()
        self.uistate.set_busy_cursor(0)

    def undo_history(self, obj):
        """
        Displays the Undo history window
        """
        try:
            self.undo_history_window = UndoHistory.UndoHistory(self.dbstate,
                                                               self.uistate)
        except Errors.WindowActiveError:
            return

    def export_data(self, obj):
        """
        Calls the ExportAssistant to export data
        """
        if self.dbstate.db.db_is_open:
            import ExportAssistant
            try:
                ExportAssistant.ExportAssistant(self.dbstate, self.uistate)
            except Errors.WindowActiveError:
                return

    def __rebuild_report_and_tool_menus(self):
        """
        Callback that rebuilds the tools and reports menu
        """
        self.__build_tools_menu(self._pmgr.get_reg_tools())
        self.__build_report_menu(self._pmgr.get_reg_reports())
        self.uistate.set_relationship_class()

    def __build_tools_menu(self, tool_menu_list):
        """
        Builds a new tools menu
        """
        if self.toolactions:
            self.uistate.uimanager.remove_action_group(self.toolactions)
            self.uistate.uimanager.remove_ui(self.tool_menu_ui_id)
        self.toolactions = gtk.ActionGroup('ToolWindow')
        (uidef, actions) = self.build_plugin_menu(
            'ToolsMenu', tool_menu_list, tool.tool_categories,
            make_plugin_callback)
        self.toolactions.add_actions(actions)
        self.tool_menu_ui_id = self.uistate.uimanager.add_ui_from_string(uidef)
        self.uimanager.insert_action_group(self.toolactions, 1)
        self.uistate.uimanager.ensure_update()

    def __build_report_menu(self, report_menu_list):
        """
        Builds a new reports menu
        """
        if self.reportactions:
            self.uistate.uimanager.remove_action_group(self.reportactions)
            self.uistate.uimanager.remove_ui(self.report_menu_ui_id)
        self.reportactions = gtk.ActionGroup('ReportWindow')
        (uidef, actions) = self.build_plugin_menu(
            'ReportsMenu', report_menu_list, standalone_categories,
            make_plugin_callback)
        self.reportactions.add_actions(actions)
        self.report_menu_ui_id = self.uistate.uimanager.add_ui_from_string(uidef)
        self.uimanager.insert_action_group(self.reportactions, 1)
        self.uistate.uimanager.ensure_update()

    def build_plugin_menu(self, text, item_list, categories, func):
        """
        Builds a new XML description for a menu based on the list of plugindata
        """
        actions = []
        ofile = StringIO()
        ofile.write('<ui><menubar name="MenuBar"><menu action="%s">' % text)

        menu = gtk.Menu()
        menu.show()

        hash_data = defaultdict(list)
        for pdata in item_list:
            if not pdata.supported:
                category = _UNSUPPORTED
            else:
                category = categories[pdata.category]
            hash_data[category].append(pdata)

        # Sort categories, skipping the unsupported
        catlist = sorted(item for item in hash_data
                   if item != _UNSUPPORTED)

        for key in catlist:
            new_key = key.replace(' ', '-')
            ofile.write('<menu action="%s">' % new_key)
            actions.append((new_key, None, key))
            pdatas = hash_data[key]
            pdatas.sort(by_menu_name)
            for pdata in pdatas:
                new_key = pdata.id.replace(' ', '-')
                menu_name = ("%s...") % pdata.name
                ofile.write('<menuitem action="%s"/>' % new_key)
                actions.append((new_key, None, menu_name, None, None,
                                func(pdata, self.dbstate, self.uistate)))
            ofile.write('</menu>')

        # If there are any unsupported items we add separator
        # and the unsupported category at the end of the menu
        if _UNSUPPORTED in hash_data:
            ofile.write('<separator/>')
            ofile.write('<menu action="%s">' % _UNSUPPORTED)
            actions.append((_UNSUPPORTED, None, _UNSUPPORTED))
            pdatas = hash_data[_UNSUPPORTED]
            pdatas.sort(by_menu_name)
            for pdata in pdatas:
                new_key = pdata.id.replace(' ', '-')
                menu_name = ("%s...") % pdata.name
                ofile.write('<menuitem action="%s"/>' % new_key)
                actions.append((new_key, None, menu_name, None, None,
                                func(pdata, self.dbstate, self.uistate)))
            ofile.write('</menu>')

        ofile.write('</menu></menubar></ui>')
        return (ofile.getvalue(), actions)

    def display_about_box(self, obj):
        """Display the About box."""
        about = GrampsAboutDialog(self.uistate.window)
        about.run()
        about.destroy()

def key_bindings(obj):
    """
    Display key bindings
    """
    GrampsDisplay.help(webpage=WIKI_HELP_PAGE_KEY)

def manual_activate(obj):
    """
    Display the GRAMPS manual
    """
    GrampsDisplay.help(webpage=WIKI_HELP_PAGE_MAN)

def report_bug_activate(obj):
    """
    Display the bug tracker web site
    """
    GrampsDisplay.url(const.URL_BUGTRACKER)

def home_page_activate(obj):
    """
    Display the GRAMPS home page
    """
    GrampsDisplay.url(const.URL_HOMEPAGE)

def mailing_lists_activate(obj):
    """
    Display the mailing list web page
    """
    GrampsDisplay.url(const.URL_MAILINGLIST)

def extra_plugins_activate(obj):
    """
    Display the wiki page with extra plugins
    """
    GrampsDisplay.url(const.URL_WIKISTRING+const.WIKI_EXTRAPLUGINS)

def faq_activate(obj):
    """
    Display FAQ
    """
    GrampsDisplay.help(webpage=WIKI_HELP_PAGE_FAQ)

def by_menu_name(first, second):
    """
    Sorts menu item lists
    """
    return cmp(first.name, second.name)

def run_plugin(pdata, dbstate, uistate):
    """
    run a plugin based on it's PluginData:
      1/ load plugin.
      2/ the report is run
    """
    pmgr = GuiPluginManager.get_instance()
    mod = pmgr.load_plugin(pdata)
    if not mod:
        #import of plugin failed
        ErrorDialog(
            _('Failed Loading Plugin'),
            _('The plugin %(name)s did not load and reported an error.\n\n'
              '%(error_msg)s\n\n'
              'If you are unable to fix the fault yourself then you can '
              'submit a bug at http://bugs.gramps-project.org or contact '
              'the plugin author (%(firstauthoremail)s).\n\n'
              'If you do not want Gramps to try and load this plugin again, '
              'you can hide it by using the Plugin Manager on the '
              'Help menu.') % {
                'name': pdata.name,
                'firstauthoremail': pdata.authors_email[0] if
                        pdata.authors_email else '...',
                'error_msg': pmgr.get_fail_list()[-1][1][1]})
        return

    if pdata.ptype == REPORT:
        report(dbstate, uistate, uistate.get_active('Person'),
               getattr(mod, pdata.reportclass),
               getattr(mod, pdata.optionclass),
               pdata.name, pdata.id,
               pdata.category, pdata.require_active,
               )
    else:
        tool.gui_tool(dbstate, uistate,
                      getattr(mod, pdata.toolclass),
                      getattr(mod, pdata.optionclass),
                      pdata.name, pdata.id, pdata.category,
                      dbstate.db.request_rebuild)

def make_plugin_callback(pdata, dbstate, uistate):
    """
    Makes a callback for a report/tool menu item
    """
    return lambda x: run_plugin(pdata, dbstate, uistate)

def get_available_views():
    """
    Query the views and determine what views to show and in which order

    :Returns: a list of lists containing tuples (view_id, viewclass)
    """
    pmgr = GuiPluginManager.get_instance()
    view_list = pmgr.get_reg_views()
    viewstoshow = defaultdict(list)
    for pdata in view_list:
        mod = pmgr.load_plugin(pdata)
        if not mod or not hasattr(mod, pdata.viewclass):
            #import of plugin failed
            ErrorDialog(
                _('Failed Loading View'),
                _('The view %(name)s did not load and reported an error.\n\n'
                  '%(error_msg)s\n\n'
                  'If you are unable to fix the fault yourself then you can '
                  'submit a bug at http://bugs.gramps-project.org or contact '
                  'the view author (%(firstauthoremail)s).\n\n'
                  'If you do not want Gramps to try and load this view again, '
                  'you can hide it by using the Plugin Manager on the '
                  'Help menu.') % {
                    'name': pdata.name,
                    'firstauthoremail': pdata.authors_email[0] if
                            pdata.authors_email else '...',
                    'error_msg': pmgr.get_fail_list()[-1][1][1]})
            continue
        viewclass = getattr(mod, pdata.viewclass)

        # pdata.category is (string, trans-string):
        if pdata.order == START:
            viewstoshow[pdata.category[0]].insert(0, (pdata, viewclass) )
        else:
            viewstoshow[pdata.category[0]].append( (pdata, viewclass) )

    # First, get those in order defined, if exists:
    resultorder = [viewstoshow[cat]
                    for cat in config.get("interface.view-categories")
                        if cat in viewstoshow]

    # Next, get the rest in some order:
    resultorder.extend(viewstoshow[cat]
        for cat in sorted(viewstoshow.keys())
            if viewstoshow[cat] not in resultorder)
    return resultorder

def views_to_show(views, use_last=True):
    """
    Determine based on preference setting which views should be shown
    """
    current_cat = 0
    current_cat_view = 0
    default_cat_views = [0] * len(views)
    if use_last:
        current_page_id = config.get('preferences.last-view')
        default_page_ids = config.get('preferences.last-views')
        found = False
        for indexcat, cat_views in enumerate(views):
            cat_view = 0
            for pdata, page_def in cat_views:
                if not found:
                    if pdata.id == current_page_id:
                        current_cat = indexcat
                        current_cat_view = cat_view
                        default_cat_views[indexcat] = cat_view
                        found = True
                        break
                if pdata.id in default_page_ids:
                    default_cat_views[indexcat] = cat_view
                cat_view += 1
        if not found:
            current_cat = 0
            current_cat_view = 0
    return current_cat, current_cat_view, default_cat_views
