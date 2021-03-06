#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2007-2008 Donald N. Allingham
# Copyright (C) 2008      Gary Burton 
# Copyright (C) 2008      Robert Cheramy <robert@cheramy.net>
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
#

"""Provide the common export options for Exporters."""

#-------------------------------------------------------------------------
#
# python modules
#
#-------------------------------------------------------------------------

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from gen.ggettext import gettext as _
from gen.ggettext import ngettext
import config
from gen.display.name import displayer as name_displayer
from Filters import GenericFilter, Rules
from gui.utils import ProgressMeter
        
class Progress(object):
    """
    Mirros the same interface that the ExportAssistant uses in the
    selection, but this is for the preview selection.
    """
    def __init__(self):
        import gtk
        self.pm = ProgressMeter(_("Selecting Preview Data"), _('Selecting...'))
        self.progress_cnt = 0
        self.title = _("Selecting...")
        while gtk.events_pending():
            gtk.main_iteration()

    def reset(self, title):
        import gtk
        self.pm.set_header(title)
        self.title = title
        while gtk.events_pending():
            gtk.main_iteration()

    def set_total(self, count):
        import gtk
        self.pm.set_pass(self.title, total=count+1)
        while gtk.events_pending():
            gtk.main_iteration()

    def update(self, count):
        import gtk
        self.pm.step()
        while gtk.events_pending():
            gtk.main_iteration()

    def close(self):
        self.pm.step()
        self.pm.close()

#-------------------------------------------------------------------------
#
# WriterOptionBox
#
#-------------------------------------------------------------------------
class WriterOptionBox(object):
    """
    Create a VBox with the option widgets and define methods to retrieve
    the options.
     
    """
    def __init__(self, person, dbstate, uistate):
        self.person = person
        self.dbstate = dbstate
        self.uistate = uistate
        self.preview_dbase = None
        self.preview_button = None
        self.preview_proxy_button = {}
        self.proxy_options_showing = False
        self.proxy_dbase = {}
        self.private = 0
        self.restrict_num = 0
        self.reference_num = 0
        self.cfilter = None
        self.nfilter = None
        self.restrict_option = None
        self.private_check = None
        self.filter_obj = None
        self.filter_note = None
        self.reference_filter = None
        self.initialized_show_options = False
        self.set_config(config)
        # The following are special properties. Create them to force the
        # export wizard to not ask for a file, and to override the 
        # confirmation message:
        #self.no_fileselect = True
        #self.confirm_text = "You made it, kid!"

    def set_config(self, config):
        """
        Set the config used for these proxies. Allows WriterOptionBox
        to be used by reports, etc. The default is to use Gramps's
        system config.
        """
        self.config = config

    def mark_dirty(self, widget=None):
        self.preview_dbase = None
        if self.preview_button:
            self.preview_button.set_sensitive(1)
        for proxy_name in self.preview_proxy_button:
            if proxy_name != "unfiltered":
                self.preview_proxy_button[proxy_name].set_sensitive(0)
        self.parse_options()

    def get_option_box(self):
        """Build up a gtk.Table that contains the standard options."""
        import gtk
        import pango
        widget = gtk.VBox()
        
        full_database_row = gtk.HBox()
        full_database_row.pack_start(gtk.Label(_("Unfiltered Family Tree:")), False)
        people_count = len(self.dbstate.db.get_person_handles())
        button = gtk.Button(ngettext("%d Person", "%d People", people_count) % 
                            people_count)
        button.set_tooltip_text(_("Click to see preview of unfiltered data"))
        button.set_size_request(107, -1)
        button.connect("clicked", self.show_preview_data)
        button.proxy_name = "unfiltered"
        self.preview_proxy_button["unfiltered"] = button
        self.spacer = gtk.HBox()
        full_database_row.pack_end(self.spacer, False)
        full_database_row.pack_end(button, False)

        widget.pack_start(full_database_row, False)
        
        self.private_check = gtk.CheckButton(
            _('_Do not include records marked private'))
        self.private_check.connect("clicked", self.mark_dirty)
        self.private_check.set_active(self.get_proxy_value("privacy"))

        self.proxy_widget = {}
        self.vbox_n = []
        self.up_n = []
        self.down_n = []
        row = 0
        for proxy_name in self.get_proxy_names():
            frame = self.build_frame(proxy_name, row)
            widget.pack_start(frame, False)
            row += 1

        hbox = gtk.HBox()
        self.advanced_button = gtk.Button(_("Change order"))
        self.advanced_button.set_size_request(150, -1)
        self.proxy_options_showing = False
        self.advanced_button.connect("clicked", self.show_options)
        hbox.pack_end(self.advanced_button, False)
        self.preview_button = gtk.Button(_("Calculate Previews"))
        self.preview_button.connect("clicked", self.preview)
        hbox.pack_end(self.preview_button, False)
        widget.pack_start(hbox, False)

        cell = gtk.CellRendererText()
        cell.set_property('ellipsize', pango.ELLIPSIZE_END)
        self.filter_obj.pack_start(cell, True)
        self.filter_obj.add_attribute(cell, 'text', 0)
        self.filter_obj.set_model(self.build_model("person"))
        self.filter_obj.set_active(self.get_proxy_value("person"))

        cell = gtk.CellRendererText()
        cell.set_property('ellipsize', pango.ELLIPSIZE_END)
        self.restrict_option.pack_start(cell, True)
        self.restrict_option.add_attribute(cell, 'text', 0)
        self.restrict_option.set_model(self.build_model("living"))
        self.restrict_option.set_active(self.get_proxy_value("living"))

        cell = gtk.CellRendererText()
        cell.set_property('ellipsize', pango.ELLIPSIZE_END)
        self.reference_filter.pack_start(cell, True)
        self.reference_filter.add_attribute(cell, 'text', 0)
        self.reference_filter.set_model(self.build_model("reference"))
        self.reference_filter.set_active(self.get_proxy_value("reference"))

        notes_cell = gtk.CellRendererText()
        notes_cell.set_property('ellipsize', pango.ELLIPSIZE_END)
        self.filter_note.pack_start(notes_cell, True)
        self.filter_note.add_attribute(notes_cell, 'text', 0)
        self.filter_note.set_model(self.build_model("note"))
        self.filter_note.set_active(self.get_proxy_value("note"))

        self.filter_note.connect("changed", self.mark_dirty)
        self.filter_obj.connect("changed", self.mark_dirty)
        self.restrict_option.connect("changed", self.mark_dirty)
        self.reference_filter.connect("changed", self.mark_dirty)
        return widget

    def show_preview_data(self, widget):
        from DbState import DbState
        from QuickReports import run_quick_report_by_name
        if widget.proxy_name == "unfiltered":
            dbstate = self.dbstate
        else:
            dbstate = DbState()
            dbstate.db = self.proxy_dbase[widget.proxy_name]
            dbstate.open = True
        run_quick_report_by_name(dbstate,
                                 self.uistate, 
                                 'filterbyname', 
                                 'all')

    def preview(self, widget):
        """
        Calculate previews to see the selected data.
        """
        self.parse_options()
        pm = Progress()
        self.preview_dbase = self.get_filtered_database(self.dbstate.db, pm, preview=True)
        pm.close()
        self.preview_button.set_sensitive(0)

    def build_frame(self, proxy_name, row):
        """
        Build a frame for a proxy option. proxy_name is a string.
        """
        # Make a box and put the option in it:
        import gtk
        import gui.widgets
        button = gtk.Button(ngettext("%d Person", "%d People", 0) % 0)
        button.set_size_request(107, -1)
        button.connect("clicked", self.show_preview_data)
        button.proxy_name = proxy_name
        if proxy_name == "person":
            # Frame Person:
            self.filter_obj = gtk.ComboBox()
            label = gtk.Label(_('_Person Filter') + ": ")
            label.set_alignment(0, 0.5)
            label.set_size_request(150, -1)
            label.set_use_underline(True)
            label.set_mnemonic_widget(self.filter_obj)
            box = gtk.HBox()
            box.pack_start(label, False)
            box.pack_start(self.filter_obj)
            box.pack_start(
                gui.widgets.SimpleButton(gtk.STOCK_EDIT, 
                   lambda obj: self.edit_filter('Person', self.filter_obj)),
                False)
            button.set_tooltip_text(_("Click to see preview after person filter"))
        elif proxy_name == "note":
            # Frame Note:
            # Objects for choosing a Note filter:
            self.filter_note = gtk.ComboBox()
            label_note = gtk.Label(_('_Note Filter') + ": ")
            label_note.set_alignment(0, 0.5)
            label_note.set_size_request(150, -1)
            label_note.set_use_underline(True)
            label_note.set_mnemonic_widget(self.filter_note)
            box = gtk.HBox()
            box.pack_start(label_note, False)
            box.pack_start(self.filter_note)
            box.pack_start(
                gui.widgets.SimpleButton(gtk.STOCK_EDIT, 
                   lambda obj: self.edit_filter('Note', self.filter_note)),
                False)
            button.set_tooltip_text(_("Click to see preview after note filter"))
        elif proxy_name == "privacy":
            # Frame 3:
            label = gtk.Label(_("Privacy Filter") + ":")
            label.set_alignment(0, 0.5)
            label.set_size_request(150, -1)
            box = gtk.HBox()
            box.pack_start(label, False)
            box.add(self.private_check)
            button.set_tooltip_text(_("Click to see preview after privacy filter"))
        elif proxy_name == "living":
            # Frame 4:
            label = gtk.Label(_("Living Filter") + ":")
            label.set_alignment(0, 0.5)
            label.set_size_request(150, -1)
            box = gtk.HBox()
            box.pack_start(label, False)
            self.restrict_option = gtk.ComboBox()
            box.add(self.restrict_option)
            button.set_tooltip_text(_("Click to see preview after living filter"))
        elif proxy_name == "reference":
            # Frame 5:
            self.reference_filter = gtk.ComboBox()
            label = gtk.Label(_('Reference Filter') + ": ")
            label.set_alignment(0, 0.5)
            label.set_size_request(150, -1)
            box = gtk.HBox()
            box.pack_start(label, False)
            box.pack_start(self.reference_filter)
            button.set_tooltip_text(_("Click to see preview after reference filter"))
        else:
            raise AttributeError("Unknown proxy '%s'" % proxy_name)

        frame = gtk.Frame()
        hbox = gtk.HBox()
        frame.add(hbox)
        vbox = gtk.HBox()
        self.vbox_n.append(vbox)
        up = gtk.Button()
        up.connect("clicked", self.swap)
        if row == 0:
            up.set_sensitive(0) # can't go up
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_GO_UP,
                             gtk.ICON_SIZE_MENU)
        up.set_image(image)
        up.row = row - 1
        self.up_n.append(up)
        down = gtk.Button()
        down.connect("clicked", self.swap)
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_GO_DOWN,
                             gtk.ICON_SIZE_MENU)
        down.set_image(image)
        down.row = row
        if row == 4:
            down.set_sensitive(0) # can't go down
        self.down_n.append(down)
        self.preview_proxy_button[proxy_name] = button
        self.preview_proxy_button[proxy_name].set_sensitive(0)
        box.pack_end(button, False)
        hbox.pack_start(box)
        hbox.pack_end(vbox, False)
        self.proxy_widget[proxy_name] = box
        return frame

    def show_options(self, widget=None):
        """
        Show or hide the option arrows. Needs to add them if first
        time due to the fact that Gramps tends to use show_all rather
        than show.
        """
        import gtk
        if self.proxy_options_showing:
            self.advanced_button.set_label(_("Change order"))
            self.spacer_up.hide()
            self.spacer_down.hide()
            for n in range(5):
                self.up_n[n].hide()
                self.down_n[n].hide()
        else:
            self.advanced_button.set_label(_("Hide order"))
            if not self.initialized_show_options:
                self.initialized_show_options = True
                # This is necessary because someone used show_all up top
                # Now, we can't add something that we want hidden
                for n in range(5):
                    self.vbox_n[n].pack_start(self.up_n[n])
                    self.vbox_n[n].pack_end(self.down_n[n])
                # some spacer buttons:
                up = gtk.Button()
                up.set_sensitive(0) 
                image = gtk.Image()
                image.set_from_stock(gtk.STOCK_GO_UP,
                                     gtk.ICON_SIZE_MENU)
                up.set_image(image)
                self.spacer.pack_start(up, False)
                down = gtk.Button()
                down.set_sensitive(0) 
                image = gtk.Image()
                image.set_from_stock(gtk.STOCK_GO_DOWN,
                                     gtk.ICON_SIZE_MENU)
                down.set_image(image)
                self.spacer.pack_end(down, False)
                self.spacer_up = up
                self.spacer_down = down
            self.spacer_up.show()
            self.spacer_down.show()
            for n in range(5):
                self.up_n[n].show()
                self.down_n[n].show()
            
        self.proxy_options_showing = not self.proxy_options_showing

    def swap(self, widget):
        """
        Swap the order of two proxies. 
        """
        row1 = widget.row
        row2 = widget.row + 1
        proxy1 = self.config.get('export.proxy-order')[row1][0]
        proxy2 = self.config.get('export.proxy-order')[row2][0]
        widget1 = self.proxy_widget[proxy1]
        widget2 = self.proxy_widget[proxy2]
        parent1 = widget1.get_parent()
        parent2 = widget2.get_parent()
        widget1.reparent(parent2)
        widget2.reparent(parent1)
        self.swap_proxy_order(row1, row2)
        self.mark_dirty(widget)

    def __define_person_filters(self):
        """Add person filters if the active person is defined."""

        name = name_displayer.display(self.person)
        gramps_id = self.person.get_gramps_id()

        des = GenericFilter()
        # feature request 2356: avoid genitive form
        des.set_name(_("Descendants of %s") % name)
        des.add_rule(Rules.Person.IsDescendantOf([gramps_id, 1]))
        
        df = GenericFilter()
        # feature request 2356: avoid genitive form
        df.set_name(_("Descendant Families of %s") % name)
        df.add_rule(Rules.Person.IsDescendantFamilyOf([gramps_id, 1]))
        
        ans = GenericFilter()
        # feature request 2356: avoid genitive form
        ans.set_name(_("Ancestors of %s") % name)
        ans.add_rule(Rules.Person.IsAncestorOf([gramps_id, 1]))
        
        com = GenericFilter()
        com.set_name(_("People with common ancestor with %s") % name)
        com.add_rule(Rules.Person.HasCommonAncestorWith([gramps_id]))

        return [des, df, ans, com]

    def get_proxy_value(self, proxy_name):
        return [value for (name, value) in 
                self.config.get('export.proxy-order') if name == proxy_name][0]

    def set_proxy_value(self, proxy_name, proxy_value):
        [name_value for name_value in 
         self.config.get('export.proxy-order') if name_value[0] == proxy_name][0][1] = int(proxy_value)

    def get_proxy_names(self):
        return [name for (name, value) in self.config.get('export.proxy-order')]

    def swap_proxy_order(self, row1, row2):
        po = self.config.get('export.proxy-order')
        po[row1], po[row2] = po[row2], po[row1]

    def parse_options(self):
        """
        Extract the common values from the GTK widgets. 
        
        After this function is called, the following variables are defined:

           private  = privacy requested
           restrict = restrict information on living peoplel
           cfitler  = return the GenericFilter selected
           nfilter  = return the NoteFilter selected
           reference = restrict referenced/orphaned records

        """
        if self.private_check:
            self.private = self.private_check.get_active()
            self.set_proxy_value("privacy", self.private)

        if self.filter_obj:
            model = self.filter_obj.get_model()
            node = self.filter_obj.get_active_iter()
            if node:
                self.cfilter = model[node][1]
            self.set_proxy_value("person", self.filter_obj.get_active())

        if self.restrict_option:
            model = self.restrict_option.get_model()
            node = self.restrict_option.get_active_iter()
            if node:
                self.restrict_num = model[node][1]
            self.set_proxy_value("living", self.restrict_option.get_active())
        
        if self.filter_note:
            model = self.filter_note.get_model()
            node = self.filter_note.get_active_iter()
            if node:
                self.nfilter = model[node][1]
            self.set_proxy_value("note", self.filter_note.get_active())

        if self.reference_filter:
            model = self.reference_filter.get_model()
            node = self.reference_filter.get_active_iter()
            if node:
                self.reference_num = model[node][1]
            self.set_proxy_value("reference", self.reference_filter.get_active())

    def get_filtered_database(self, dbase, progress=None, preview=False):
        """
        dbase - the database
        progress - instance that has:
           .reset() method
           .set_total() method
           .update() method
           .progress_cnt integer representing N of total done
        """
        # Increment the progress count for each filter type chosen
        if self.private and progress:
            progress.progress_cnt += 1

        if self.restrict_num > 0 and progress:
            progress.progress_cnt += 1

        if (self.cfilter != None and (not self.cfilter.is_empty())) and progress:
            progress.progress_cnt += 1

        if (self.nfilter != None and (not self.nfilter.is_empty())) and progress:
            progress.progress_cnt += 1

        if self.reference_num > 0 and progress:
            progress.progress_cnt += 1

        if progress:
            progress.set_total(progress.progress_cnt)
            progress.progress_cnt = 0

        if self.preview_dbase:
            if progress:
                progress.progress_cnt += 5
            return self.preview_dbase

        self.proxy_dbase.clear()
        for proxy_name in self.get_proxy_names():
            dbase = self.apply_proxy(proxy_name, dbase, progress)
            if preview:
                self.proxy_dbase[proxy_name] = dbase
                self.preview_proxy_button[proxy_name].set_sensitive(1)
                people_count = len(dbase.get_person_handles())
                self.preview_proxy_button[proxy_name].set_label(
                    ngettext("%d Person", "%d People", people_count) %
                    people_count)
        return dbase

    def apply_proxy(self, proxy_name, dbase, progress=None):
        """
        Apply the named proxy to the dbase, and return.
        proxy_name is one of 
           ["person", "note", "privacy", "living", "reference"]
        """
        # If the private flag is set, apply the PrivateProxyDb
        import gen.proxy
        if proxy_name == "privacy":
            if self.private:
                if progress:
                    progress.reset(_("Filtering private data"))
                    progress.progress_cnt += 1
                    progress.update(progress.progress_cnt)
                dbase = gen.proxy.PrivateProxyDb(dbase)

        # If the restrict flag is set, apply the LivingProxyDb
        elif proxy_name == "living":
            if self.restrict_num > 0:
                if progress:
                    progress.reset(_("Filtering living persons"))
                    progress.progress_cnt += 1
                    progress.update(progress.progress_cnt)
                mode = [None, # include living
                        gen.proxy.LivingProxyDb.MODE_INCLUDE_LAST_NAME_ONLY,
                        gen.proxy.LivingProxyDb.MODE_EXCLUDE_ALL,
                        ][self.restrict_num]
                dbase = gen.proxy.LivingProxyDb(
                            dbase, 
                            mode) # 

        # If the filter returned by cfilter is not empty, apply the 
        # FilterProxyDb (Person Filter)
        elif proxy_name == "person":
            if self.cfilter != None and not self.cfilter.is_empty():
                if progress:
                    progress.reset(_("Applying selected person filter"))
                    progress.progress_cnt += 1
                    progress.update(progress.progress_cnt)
                dbase = gen.proxy.FilterProxyDb(
                    dbase, self.cfilter)

        # Apply the Note Filter
        elif proxy_name == "note":
            if self.nfilter != None and not self.nfilter.is_empty():
                if progress:
                    progress.reset(_("Applying selected note filter"))
                    progress.progress_cnt += 1
                    progress.update(progress.progress_cnt)
                dbase = gen.proxy.FilterProxyDb(
                    dbase, note_filter=self.nfilter)

        # Apply the ReferencedBySelection
        elif proxy_name == "reference":
            if progress:
                progress.reset(_("Filtering referenced records"))
                progress.progress_cnt += 1
                progress.update(progress.progress_cnt)
            if self.reference_num == 0:
                pass
            elif self.reference_num == 1:
                dbase = gen.proxy.ReferencedBySelectionProxyDb(dbase, 
                                                               all_people=True)
        else:
            raise AttributeError("no such proxy '%s'" % proxy_name)

        return dbase

    def edit_filter(self, namespace, filter_obj):
        """
        Callback which invokes the EditFilter dialog. Will create new
        filter if called if none is selected.
        """
        from gui.filtereditor import EditFilter
        from Filters import FilterList, GenericFilterFactory
        import const
        the_filter = None
        filterdb = FilterList(const.CUSTOM_FILTERS)
        filterdb.load()
        if filter_obj.get_active() != 0:
            model = filter_obj.get_model()
            node = filter_obj.get_active_iter()
            if node:
                sel_filter = model.get_value(node, 1)
                # the_filter needs to be a particular object for editor
                for filt in filterdb.get_filters(namespace):
                    if filt.get_name() == sel_filter.get_name():
                        the_filter = filt
        else:
            the_filter = GenericFilterFactory(namespace)()
        if the_filter:
            EditFilter(namespace, self.dbstate, self.uistate, [],
                       the_filter, filterdb,
                       lambda : self.edit_filter_save(filterdb, namespace))
        else: # can't edit this filter
            from QuestionDialog import ErrorDialog
            ErrorDialog(_("Cannot edit a system filter"), 
                        _("Please select a different filter to edit"))

    def edit_filter_save(self, filterdb, namespace):
        """
        If a filter changed, save them all. Reloads, and also calls callback.
        """
        from Filters import CustomFilters
        from Filters import reload_custom_filters
        filterdb.save()
        reload_custom_filters()
        if namespace == "Person":
            model = self.build_model("person")
            widget = self.filter_obj
        elif namespace == "Note":
            model = self.build_model("note")
            widget = self.filter_note
        widget.set_model(model)
        widget.set_active(0)

    def build_model(self, namespace):
        """
        Build a model for the combo box selector.
        """
        import gtk
        import gobject
        from Filters import CustomFilters
        if namespace == "person":
            # Populate the Person Filter
            entire_db = GenericFilter()
            entire_db.set_name(_("Include all selected people"))
            the_filters = [entire_db]

            if self.person:
                the_filters += self.__define_person_filters()

            the_filters.extend(CustomFilters.get_filters('Person'))

            model = gtk.ListStore(gobject.TYPE_STRING, object)
            for item in the_filters:
                model.append(row=[item.get_name(), item])
        elif namespace == "note":
            # Populate the Notes Filter
            entire_db = GenericFilter()
            entire_db.set_name(_("Include all selected notes"))
            notes_filters = [entire_db]
            notes_filters.extend(CustomFilters.get_filters('Note'))
            model = gtk.ListStore(gobject.TYPE_STRING, object)
            for item in notes_filters:
                model.append(row=[item.get_name(), item])

        elif namespace == "living":
            model = gtk.ListStore(gobject.TYPE_STRING, int)
            row = 0
            for item in [
                _('Include all selected people'),
                _('Replace given names of living people'),
                _('Do not include living people')]:
                model.append(row=[item, row])
                row += 1

        elif namespace == "reference":
            model = gtk.ListStore(gobject.TYPE_STRING, int)
            row = 0
            for item in [
                _('Include all selected records'),
                _('Do not include records not linked to a selected person'),]:
                model.append(row=[item, row])
                row += 1

        return model
