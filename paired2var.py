#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os

import wx
import wx.html

import my_globals as mg
import lib
import my_exceptions
import config_dlg
import full_html
import output
import projects

OUTPUT_MODULES = ["my_globals as mg", "core_stats", "getdata", "output", 
                  "stats_output"]


class DlgPaired2VarConfig(wx.Dialog, config_dlg.ConfigDlg):
    """
    ConfigDlg - provides reusable interface for data selection, setting labels, 
        exporting scripts buttons etc.  Sets values for db, default_tbl etc and 
        responds to selections etc.
    """
    
    def __init__(self, title):
        cc = config_dlg.get_cc()
        wx.Dialog.__init__(self, parent=None, id=-1, title=title, 
                           pos=(mg.HORIZ_OFFSET,0), 
                           style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|\
                           wx.RESIZE_BORDER|wx.CLOSE_BOX|wx.SYSTEM_MENU|\
                           wx.CAPTION|wx.CLIP_CHILDREN)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.url_load = True # btn_expand
        self.html_msg = u""
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
                                    lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
        variables_rc_msg = _("Right click variables to view/edit details")
        # set up panel for frame
        self.panel = wx.Panel(self)
        bx_desc = wx.StaticBox(self.panel, -1, _("Purpose"))
        bx_vars = wx.StaticBox(self.panel, -1, _("Variables"))
        #self.panel.SetBackgroundColour(wx.Colour(205, 217, 215))
        config_dlg.add_icon(frame=self)
        # mixins
        self.szr_data, self.szr_config = self.get_gen_config_szrs(self.panel)
        self.szr_output_btns = self.get_szr_output_btns(self.panel,
                                                        inc_clear=False)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_top = wx.BoxSizer(wx.HORIZONTAL)
        szr_desc = wx.StaticBoxSizer(bx_desc, wx.VERTICAL)
        eg1, eg2, eg3 = self.get_examples()
        lbl_desc1 = wx.StaticText(self.panel, -1, eg1)
        lbl_desc2 = wx.StaticText(self.panel, -1, eg2)
        lbl_desc3 = wx.StaticText(self.panel, -1, eg3)
        szr_desc.Add(lbl_desc1, 1, wx.GROW|wx.LEFT, 5)
        szr_desc.Add(lbl_desc2, 1, wx.GROW|wx.LEFT, 5)
        szr_desc.Add(lbl_desc3, 1, wx.GROW|wx.LEFT, 5)
        self.btn_help = wx.Button(self.panel, wx.ID_HELP)
        self.btn_help.Bind(wx.EVT_BUTTON, self.on_btn_help)
        if mg.PLATFORM == mg.LINUX: # http://trac.wxwidgets.org/ticket/9859
            bx_vars.SetToolTipString(variables_rc_msg)
        szr_vars = wx.StaticBoxSizer(bx_vars, wx.VERTICAL)
        #szr_vars = wx.BoxSizer(wx.HORIZONTAL) # removes tooltip bug in gtk
        szr_vars_top = wx.BoxSizer(wx.HORIZONTAL)
        szr_vars_bottom = wx.BoxSizer(wx.HORIZONTAL)
        szr_vars.Add(szr_vars_top, 1, wx.LEFT, 5)
        szr_vars.Add(szr_vars_bottom, 0, wx.LEFT, 5)
        # group A
        self.lbl_group_a = wx.StaticText(self.panel, -1, _("Group A:"))
        self.lbl_group_a.SetFont(self.LABEL_FONT)
        self.drop_group_a = wx.Choice(self.panel, -1, choices=[], size=(300, -1))
        self.drop_group_a.Bind(wx.EVT_CHOICE, self.on_group_by_sel)
        self.drop_group_a.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_group_a)
        self.drop_group_a.SetToolTipString(variables_rc_msg)
        szr_vars_top.Add(self.lbl_group_a, 0, wx.RIGHT, 5)
        szr_vars_top.Add(self.drop_group_a, 0, wx.GROW)
        # group B
        self.lbl_group_b = wx.StaticText(self.panel, -1, _("Group B:"))
        self.lbl_group_b.SetFont(self.LABEL_FONT)
        self.drop_group_b = wx.Choice(self.panel, -1, choices=[], size=(300, -1))
        self.drop_group_b.Bind(wx.EVT_CHOICE, self.on_group_by_sel)
        self.drop_group_b.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_group_b)
        self.drop_group_b.SetToolTipString(variables_rc_msg)
        #self.setup_groups()
        szr_vars_top.Add(self.lbl_group_b, 0, wx.LEFT|wx.RIGHT, 5)
        szr_vars_top.Add(self.drop_group_b, 0, wx.GROW)
        # phrase
        self.lbl_phrase = wx.StaticText(self.panel, -1, 
                                       _("Start making your selections"))
        szr_vars_bottom.Add(self.lbl_phrase, 0, wx.GROW|wx.TOP|wx.BOTTOM, 10)
        szr_bottom = wx.BoxSizer(wx.HORIZONTAL)
        szr_bottom_left = wx.BoxSizer(wx.VERTICAL)
        if mg.MAX_HEIGHT <= 620:
            myheight = 130
        elif mg.MAX_HEIGHT <= 820:
            myheight = ((mg.MAX_HEIGHT/1024.0)*350) - 20
        else:
            myheight = 350
        if mg.PLATFORM == mg.MAC:
            myheight = myheight*0.3
        self.html = full_html.FullHTML(panel=self.panel, parent=self, 
                                       size=(200,myheight))
        if mg.PLATFORM == mg.MAC:
            self.html.Bind(wx.EVT_WINDOW_CREATE, self.on_show)
        else:
            self.Bind(wx.EVT_SHOW, self.on_show)
        szr_bottom_left.Add(self.html, 1, wx.GROW|wx.LEFT|wx.BOTTOM, 5)
        szr_bottom_left.Add(self.szr_config, 0, wx.GROW)
        #self.szr_level = self.get_szr_level(self.panel) # mixin
        #szr_bottom_left.Add(self.szr_level, 0)
        szr_bottom.Add(szr_bottom_left, 1, wx.GROW)
        szr_bottom.Add(self.szr_output_btns, 0, wx.GROW|wx.LEFT, 10)
        static_box_gap = 0 if mg.PLATFORM == mg.MAC else 10
        if static_box_gap:
            szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        help_down_by = 27 if mg.PLATFORM == mg.MAC else 17
        szr_top.Add(self.btn_help, 0, wx.TOP, help_down_by)
        szr_top.Add(szr_desc, 1, wx.LEFT, 5)
        szr_main.Add(szr_top, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        if static_box_gap:
            szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        szr_main.Add(self.szr_data, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        if static_box_gap:
            szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        szr_main.Add(szr_vars, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        if static_box_gap:
            szr_main.Add(wx.BoxSizer(wx.VERTICAL), 0, wx.TOP, static_box_gap)
        szr_main.Add(szr_bottom, 2, wx.GROW|wx.LEFT|wx.BOTTOM|wx.RIGHT, 10)
        self.panel.SetSizer(szr_main)
        szr_lst = [szr_top, self.szr_data, szr_vars, szr_bottom]
        lib.set_size(window=self, szr_lst=szr_lst)
        self.setup_groups()

    def on_show(self, event):
        try:
            self.html.pizza_magic() # must happen after Show
        except Exception, e:
            my_exceptions.DoNothingException() # need on Mac or exceptn survives
        finally: # any initial content
            self.html.show_html(self.html_msg)
            self.html_msg = u""

    def on_rclick_group_a(self, event):
        var_a, choice_item = self.get_var_a()
        var_label_a = lib.get_item_label(item_labels=self.var_labels, 
                                         item_val=var_a)
        updated = projects.set_var_props(choice_item, var_a, var_label_a, 
                                         self.var_labels, self.var_notes, 
                                         self.var_types, self.val_dics)
        if updated:
            self.refresh_vars()

    def on_rclick_group_b(self, event):
        var_b, choice_item = self.get_var_b()
        var_label_b = lib.get_item_label(item_labels=self.var_labels, 
                                         item_val=var_b)
        updated = projects.set_var_props(choice_item, var_b, var_label_b, 
                                         self.var_labels, self.var_notes, 
                                         self.var_types, self.val_dics)
        if updated:
            self.refresh_vars()

    def refresh_vars(self):
        var_a, var_b = self.get_vars()
        fld_choice_items = self.get_group_choices()
        self.setup_group_a(fld_choice_items, var_a)
        self.setup_group_b(fld_choice_items, var_b)
        self.update_defaults()
        self.update_phrase()
        
    def get_group_choices(self):
        """
        Get group choice items.
        Also stores var names, and var names sorted by their labels (for later 
            reference).
        """
        var_names = projects.get_approp_var_names(self.var_types,
                                                  self.min_data_type)
        if len(var_names) < 2:
            msg = (_(u"<p>There are not enough suitable variables available"
                    u" for this analysis. "
                    u"Only variables with a %s data type can be used in this "
                    u"analysis."
                    u"</p><p>This problem sometimes occurs when numeric data is"
                    u" accidentally imported from a spreadsheet as text. "
                    u"In such cases the solution is to format the data columns "
                    u"to a numeric format in the spreadsheet and re-import it."
                    u"</p>") % 
                    mg.VAR_TYPE_TO_SHORT.get(self.min_data_type, _("suitable")))
        else:
            msg = _("<p>Waiting for a report to be run.</p>")
        try:
            self.html.show_html(msg)
        except Exception, e: # no html ctrl yet so defer and display when ready
            self.html_msg = msg
        fld_choice_items, self.sorted_var_names = lib.get_sorted_choice_items(
                                dic_labels=self.var_labels, vals=var_names)
        return fld_choice_items
       
    def setup_group_a(self, fld_choice_items, var_a=None):        
        self.drop_group_a.SetItems(fld_choice_items)
        idx_a = projects.get_idx_to_select(fld_choice_items, var_a, 
                                           self.var_labels, mg.GROUP_A_DEFAULT)
        self.drop_group_a.SetSelection(idx_a)            

    def setup_group_b(self, fld_choice_items, var_b=None):        
        self.drop_group_b.SetItems(fld_choice_items)
        idx_b = projects.get_idx_to_select(fld_choice_items, var_b, 
                                           self.var_labels, mg.GROUP_B_DEFAULT)
        self.drop_group_b.SetSelection(idx_b)
        
    def setup_groups(self, var_a=None, var_b=None):
        fld_choice_items = self.get_group_choices()
        self.setup_group_a(fld_choice_items, var_a)
        self.setup_group_b(fld_choice_items, var_b)
    
    def on_database_sel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        """
        config_dlg.ConfigDlg.on_database_sel(self, event)
        self.update_var_dets()
        self.setup_groups()
                
    def on_table_sel(self, event):
        "Reset key data details after table selection."       
        config_dlg.ConfigDlg.on_table_sel(self, event)
        self.update_var_dets()
        self.setup_groups()

    def get_var_a(self):
        idx_a = self.drop_group_a.GetSelection()
        var_a = self.sorted_var_names[idx_a]
        var_a_item = self.drop_group_a.GetStringSelection()
        return var_a, var_a_item

    def get_var_b(self):
        idx_b = self.drop_group_b.GetSelection()
        var_b = self.sorted_var_names[idx_b]
        var_b_item = self.drop_group_b.GetStringSelection()
        return var_b, var_b_item
    
    def get_vars(self):
        """
        self.sorted_var_names is set when dropdowns are set 
            (and only changed when reset).
        """
        var_a, unused = self.get_var_a()
        var_b, unused = self.get_var_b()
        return var_a, var_b
        
    def on_btn_config(self, event):
        var_a, var_b = self.get_vars()
        config_dlg.ConfigDlg.on_btn_config(self, event)
        self.setup_groups(var_a, var_b)
        self.update_phrase()
        
    def on_group_by_sel(self, event):
        self.update_phrase()
        self.update_defaults()
        event.Skip()
        
    def get_drop_vals(self):
        """
        Get values from main drop downs.
        Returns var_a, label_a, var_b, label_b.
        """
        var_a, var_b = self.get_vars()
        label_a = lib.get_item_label(item_labels=self.var_labels, 
                                     item_val=var_a)
        label_b = lib.get_item_label(item_labels=self.var_labels, 
                                     item_val=var_b)
        return var_a, label_a, var_b, label_b
    
    def update_phrase(self):
        """
        Update phrase based on Group A and Group B.
        """
        var_a, label_a, var_b, label_b = self.get_drop_vals()
        self.lbl_phrase.SetLabel(_("Is \"%(a)s\" different from \"%(b)s\"?") %
                                {"a": label_a, "b": label_b})
    
    def update_defaults(self):
        mg.GROUP_A_DEFAULT = self.drop_group_a.GetStringSelection()
        mg.GROUP_B_DEFAULT = self.drop_group_b.GetStringSelection()

    def on_btn_run(self, event):
        """
        Generate script to special location (INT_SCRIPT_PATH), run script 
            putting output in special location (INT_REPORT_PATH) and into report 
            file, and finally, display html output.
        """
        cc = config_dlg.get_cc()
        run_ok = self.test_config_ok()
        add_to_report = self.chk_add_to_report.IsChecked()
        if run_ok:
            get_script_args=[cc[mg.CURRENT_CSS_PATH], add_to_report,
                             cc[mg.CURRENT_REPORT_PATH]]
            config_dlg.ConfigDlg.on_btn_run(self, event, OUTPUT_MODULES, 
                                            get_script_args)
    
    def test_config_ok(self):
        """
        Are the appropriate selections made to enable an analysis to be run?
        """
        # group A and B cannot be the same
        if self.drop_group_a.GetStringSelection() == \
                self.drop_group_b.GetStringSelection():
            wx.MessageBox(_("Group A and Group B must be different"))
            return False
        return True
    
   # export script
    def on_btn_script(self, event):
        """
        Export script for table to file currently displayed (if enough data).
        If the file doesn't exist, make one and add the preliminary code.
        If a file exists, but is empty, put the preliminary code in then
            the new exported script.
        If the file exists and is not empty, append the script on the end.
        """
        cc = config_dlg.get_cc()
        export_ok = self.test_config_ok()
        if export_ok:
            add_to_report = self.chk_add_to_report.IsChecked()
            try:
                css_fils, css_idx = output.get_css_dets()
            except my_exceptions.MissingCssException, e:
                lib.update_local_display(self.html, _("Please check the CSS "
                                        "file exists or set another. "
                                        "Caused by error: %s") % lib.ue(e), 
                                        wrap_text=True)
                lib.safe_end_cursor()
                event.Skip()
                return
            script = self.get_script(css_idx, add_to_report,
                                     cc[mg.CURRENT_REPORT_PATH])
            output.export_script(script, css_fils)
        event.Skip()

    def on_btn_help(self, event):
        wx.MessageBox("Under construction")
        event.Skip()
    
    def on_btn_clear(self, event):
        wx.MessageBox("Under construction")
        event.Skip()
    
    def on_close(self, event):
        "Close dialog"
        try:
            # add end to each open script file and close.
            for fil_script in self.open_scripts:
                # add ending code to script
                f = file(fil_script, "a")
                output.add_end_script_code(f)
                f.close()
        except Exception:
            my_exceptions.DoNothingException()
        finally:
            self.Destroy()
            event.Skip()