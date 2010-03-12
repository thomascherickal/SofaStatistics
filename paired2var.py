#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os

import wx
import wx.html

import my_globals
import lib
import config_dlg
import full_html
import output
import projects

OUTPUT_MODULES = ["my_globals", "core_stats", "getdata", "output", 
                  "stats_output"]


class DlgPaired2VarConfig(wx.Dialog, config_dlg.ConfigDlg):
    """
    ConfigDlg - provides reusable interface for data selection, setting labels, 
        exporting scripts buttons etc.  Sets values for db, default_tbl etc and 
        responds to selections etc.
    """
    
    def __init__(self, title, dbe, con_dets, default_dbs=None, 
                 default_tbls=None, fil_var_dets="", fil_css="", fil_report="", 
                 fil_script=""):
         
        wx.Dialog.__init__(self, parent=None, id=-1, title=title, 
                           pos=(200, 0), 
                           style=wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | \
                           wx.RESIZE_BORDER | wx.SYSTEM_MENU | \
                           wx.CAPTION | wx.CLOSE_BOX | \
                           wx.CLIP_CHILDREN)
        self.dbe = dbe
        self.con_dets = con_dets
        self.default_dbs = default_dbs
        self.default_tbls = default_tbls
        self.fil_var_dets = fil_var_dets
        self.fil_css = fil_css
        self.fil_report = fil_report
        self.fil_script = fil_script
        self.url_load = True # btnExpand
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
            projects.get_var_dets(fil_var_dets)
        variables_rc_msg = _("Right click variables to view/edit details")
        # set up panel for frame
        self.panel = wx.Panel(self)
        #self.panel.SetBackgroundColour(wx.Colour(205, 217, 215))
        config_dlg.add_icon(frame=self)
        self.szrData, self.szrConfigBottom, self.szrConfigTop = \
            self.get_gen_config_szrs(self.panel) # mixin
        self.szrOutputButtons = self.get_szrOutputBtns(self.panel,
                                                       inc_clear=False) # mixin
        szrMain = wx.BoxSizer(wx.VERTICAL)
        bxDesc = wx.StaticBox(self.panel, -1, _("Purpose"))
        szrDesc = wx.StaticBoxSizer(bxDesc, wx.VERTICAL)
        eg1, eg2, eg3 = self.get_examples()
        lblDesc1 = wx.StaticText(self.panel, -1, eg1)
        lblDesc2 = wx.StaticText(self.panel, -1, eg2)
        lblDesc3 = wx.StaticText(self.panel, -1, eg3)
        szrDesc.Add(lblDesc1, 1, wx.GROW|wx.LEFT, 5)
        szrDesc.Add(lblDesc2, 1, wx.GROW|wx.LEFT, 5)
        szrDesc.Add(lblDesc3, 1, wx.GROW|wx.LEFT, 5)
        bxVars = wx.StaticBox(self.panel, -1, _("Variables"))
        if not my_globals.IN_WINDOWS: # http://trac.wxwidgets.org/ticket/9859
            bxVars.SetToolTipString(variables_rc_msg)
        szrVars = wx.StaticBoxSizer(bxVars, wx.VERTICAL)
        #szrVars = wx.BoxSizer(wx.HORIZONTAL) # removes tooltip bug in gtk
        szrVarsTop = wx.BoxSizer(wx.HORIZONTAL)
        szrVarsBottom = wx.BoxSizer(wx.HORIZONTAL)
        szrVars.Add(szrVarsTop, 1, wx.LEFT, 5)
        szrVars.Add(szrVarsBottom, 0, wx.LEFT, 5)
        # group A
        self.lblGroupA = wx.StaticText(self.panel, -1, _("Group A:"))
        self.lblGroupA.SetFont(self.LABEL_FONT)
        self.dropGroupA = wx.Choice(self.panel, -1, choices=[], size=(300, -1))
        self.dropGroupA.Bind(wx.EVT_CHOICE, self.on_group_by_sel)
        self.dropGroupA.Bind(wx.EVT_CONTEXT_MENU, self.on_right_click_group_a)
        self.dropGroupA.SetToolTipString(variables_rc_msg)
        szrVarsTop.Add(self.lblGroupA, 0, wx.RIGHT, 5)
        szrVarsTop.Add(self.dropGroupA, 0, wx.GROW)
        # group B
        self.lblGroupB = wx.StaticText(self.panel, -1, _("Group B:"))
        self.lblGroupB.SetFont(self.LABEL_FONT)
        self.dropGroupB = wx.Choice(self.panel, -1, choices=[], size=(300, -1))
        self.dropGroupB.Bind(wx.EVT_CHOICE, self.on_group_by_sel)
        self.dropGroupB.Bind(wx.EVT_CONTEXT_MENU, self.on_right_click_group_b)
        self.dropGroupB.SetToolTipString(variables_rc_msg)
        self.setup_groups()
        szrVarsTop.Add(self.lblGroupB, 0, wx.LEFT|wx.RIGHT, 5)
        szrVarsTop.Add(self.dropGroupB, 0, wx.GROW)
        # phrase
        self.lblPhrase = wx.StaticText(self.panel, -1, 
                                       _("Start making your selections"))
        szrVarsBottom.Add(self.lblPhrase, 0, wx.GROW|wx.TOP|wx.BOTTOM, 10)
        szrBottom = wx.BoxSizer(wx.HORIZONTAL)
        szrBottomLeft = wx.BoxSizer(wx.VERTICAL)
        if my_globals.MAX_HEIGHT <= 620:
            myheight = 130
        elif my_globals.MAX_HEIGHT <= 820:
            myheight = ((my_globals.MAX_HEIGHT/1024.0)*350) - 20
        else:
            myheight = 350
        self.html = full_html.FullHTML(self.panel, size=(200, myheight))
        html2show = _("<p>Waiting for a report to be run.</p>")
        self.html.show_html(html2show)
        szrBottomLeft.Add(self.html, 1, wx.GROW|wx.LEFT|wx.BOTTOM, 5)
        szrBottomLeft.Add(self.szrConfigTop, 0, wx.GROW)
        szrBottomLeft.Add(self.szrConfigBottom, 0, wx.GROW)
        self.szrLevel = self.get_szrLevel(self.panel) # mixin
        szrBottomLeft.Add(self.szrLevel, 0)
        szrBottom.Add(szrBottomLeft, 1, wx.GROW)
        szrBottom.Add(self.szrOutputButtons, 0, wx.GROW|wx.LEFT, 10)
        szrMain.Add(szrDesc, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(self.szrData, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(szrVars, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(szrBottom, 2, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(szrMain)
        szrMain.SetSizeHints(self)

    def on_right_click_group_a(self, event):
        var_a, choice_item = self.get_var_a()
        var_label_a = lib.get_item_label(item_labels=self.var_labels, 
                                         item_val=var_a)
        updated = projects.set_var_props(choice_item, var_a, var_label_a, 
                            self.flds, self.var_labels, self.var_notes, 
                            self.var_types, self.val_dics, self.fil_var_dets)
        if updated:
            self.refresh_vars()

    def on_right_click_group_b(self, event):
        var_b, choice_item = self.get_var_b()
        var_label_b = lib.get_item_label(item_labels=self.var_labels, 
                                         item_val=var_b)
        updated = projects.set_var_props(choice_item, var_b, var_label_b, 
                            self.flds, self.var_labels, self.var_notes, 
                            self.var_types, self.val_dics, self.fil_var_dets)
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
        var_names = projects.get_approp_var_names(self.flds, self.var_types,
                                                  self.min_data_type)
        fld_choice_items, self.sorted_var_names = lib.get_sorted_choice_items(
                                dic_labels=self.var_labels, vals=var_names)
        return fld_choice_items
       
    def setup_group_a(self, fld_choice_items, var_a=None):        
        self.dropGroupA.SetItems(fld_choice_items)
        idx_a = projects.get_idx_to_select(fld_choice_items, var_a, 
                                           self.var_labels, 
                                           my_globals.GROUP_A_DEFAULT)
        self.dropGroupA.SetSelection(idx_a)            

    def setup_group_b(self, fld_choice_items, var_b=None):        
        self.dropGroupB.SetItems(fld_choice_items)
        idx_b = projects.get_idx_to_select(fld_choice_items, var_b, 
                                           self.var_labels, 
                                           my_globals.GROUP_B_DEFAULT)
        self.dropGroupB.SetSelection(idx_b)
        
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
        idx_a = self.dropGroupA.GetSelection()
        var_a = self.sorted_var_names[idx_a]
        var_a_item = self.dropGroupA.GetStringSelection()
        return var_a, var_a_item

    def get_var_b(self):
        idx_b = self.dropGroupB.GetSelection()
        var_b = self.sorted_var_names[idx_b]
        var_b_item = self.dropGroupB.GetStringSelection()
        return var_b, var_b_item
    
    def get_vars(self):
        """
        self.sorted_var_names is set when dropdowns are set 
            (and only changed when reset).
        """
        var_a, unused = self.get_var_a()
        var_b, unused = self.get_var_b()
        return var_a, var_b

    def on_var_dets_file_lost_focus(self, event):
        var_a, var_b = self.get_vars()
        config_dlg.ConfigDlg.on_var_dets_file_lost_focus(self, event)
        self.setup_groups(var_a, var_b)
        self.update_phrase()
        
    def on_btn_var_dets_path(self, event):
        var_a, var_b = self.get_vars()
        config_dlg.ConfigDlg.on_btn_var_dets_path(self, event)
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
        self.lblPhrase.SetLabel(_("Is \"%(a)s\" different from \"%(b)s\"?") %
                                {"a": label_a, "b": label_b})
    
    def update_defaults(self):
        my_globals.GROUP_A_DEFAULT = self.dropGroupA.GetStringSelection()
        my_globals.GROUP_B_DEFAULT = self.dropGroupB.GetStringSelection()
        
    def update_local_display(self, strContent):
        self.html.show_html(strContent, url_load=True) # allow footnotes

    def on_btn_run(self, event):
        """
        Generate script to special location (INT_SCRIPT_PATH), 
            run script putting output in special location 
            (INT_REPORT_PATH) and into report file, and finally, 
            display html output.
        """
        run_ok = self.test_config_ok()
        if run_ok:
            wx.BeginBusyCursor()
            add_to_report = self.chkAddToReport.IsChecked()
            css_fils, css_idx = output.get_css_dets(self.fil_report, 
                                                    self.fil_css)
            script = self.get_script(css_idx, add_to_report, self.fil_report)
            bolran_report, str_content = output.run_report(OUTPUT_MODULES, 
                    add_to_report, self.fil_report, css_fils, script, 
                    self.con_dets, self.dbe, self.db, self.tbl, 
                    self.default_dbs, self.default_tbls)
            wx.EndBusyCursor()
            self.update_local_display(str_content)
            self.str_content = str_content
            self.btnExpand.Enable(bolran_report)
        event.Skip()
    
    def test_config_ok(self):
        """
        Are the appropriate selections made to enable an analysis to be run?
        """
        # group A and B cannot be the same
        if self.dropGroupA.GetStringSelection() == \
                self.dropGroupB.GetStringSelection():
            wx.MessageBox(_("Group A and Group B must be different"))
            return False
        return True
    
   # export script
    def on_btn_export(self, event):
        """
        Export script for table to file currently displayed (if enough data).
        If the file doesn't exist, make one and add the preliminary code.
        If a file exists, but is empty, put the preliminary code in then
            the new exported script.
        If the file exists and is not empty, append the script on the end.
        """
        export_ok = self.test_config_ok()
        if export_ok:
            add_to_report = self.chkAddToReport.IsChecked()
            css_fils, css_idx = output.get_css_dets(self.fil_report, 
                                                    self.fil_css)
            script = self.get_script(css_idx, add_to_report, self.fil_report)
            output.export_script(script, self.fil_script, 
                                 self.fil_report, css_fils, self.con_dets, 
                                 self.dbe, self.db, self.tbl, self.default_dbs, 
                                 self.default_tbls)
        event.Skip()

    def on_btn_help(self, event):
        wx.MessageBox("Under construction")
        event.Skip()
    
    def on_btn_clear(self, event):
        wx.MessageBox("Under construction")
        event.Skip()
    
    def on_close(self, event):
        "Close app"
        try:
            self.con.close()
            # add end to each open script file and close.
            for fil_script in self.open_scripts:
                # add ending code to script
                f = file(fil_script, "a")
                output.add_end_script_code(f)
                f.close()
        except Exception:
            pass
        finally:
            my_globals.DBE_DEFAULT = self.dbe
            my_globals.DB_DEFAULTS[self.dbe] = self.db
            my_globals.TBL_DEFAULTS[self.dbe] = self.tbl
            self.Destroy()
            event.Skip()