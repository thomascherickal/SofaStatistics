#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os

import wx
import wx.html

import my_globals as mg
import lib
import my_exceptions
import getdata
import config_dlg
import full_html
import output
import projects

OUTPUT_MODULES = ["my_globals as mg", "core_stats", "getdata", "output", 
                  "stats_output"]

dd = getdata.get_dd()

def get_range_idxs(vals, val_a, val_b):
    """
    Get range indexes for two values from list of values.
    NB the two values are strings as displayed in dropdowns even if the 
        underlying data is not.
    E.g. u'1' and u'5' in [1, 2, 3, 4, 5]
    or u'"Chrome"' and u'"Safari"' in [u'Chrome', u'Firefox', ...]
    or u'1000000000000.2' etc in ['1000000000000.2', '1000000000000.3', ...].
    val_a and val_b are deliberately wrapped in double quotes if strings by 
        all valid inputs to this function.
    """
    debug = False
    if debug:
        print(vals)
        print(type(val_a).__name__, val_a)
        print(type(val_b).__name__, val_b)
    uvals = [lib.any2unicode(x) for x in vals]
    idx_val_a = uvals.index(val_a.strip('"'))
    idx_val_b = uvals.index(val_b.strip('"'))
    return idx_val_a, idx_val_b


class DlgIndep2VarConfig(wx.Dialog, config_dlg.ConfigDlg):
    """
    ConfigDlg - provides reusable interface for data selection, setting labels, 
        exporting scripts buttons etc.  Sets values for db, default_tbl etc and 
        responds to selections etc.
    """
    inc_gp_by_select = False
    
    def __init__(self, title, fil_var_dets=u"", fil_css=u"", fil_report=u"", 
                 fil_script=u"", takes_range=False):
         
        wx.Dialog.__init__(self, parent=None, id=-1, title=title, 
                           pos=(200, 0), 
                           style=wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | \
                           wx.RESIZE_BORDER | wx.SYSTEM_MENU | \
                           wx.CAPTION | wx.CLOSE_BOX | \
                           wx.CLIP_CHILDREN)
        self.fil_var_dets = fil_var_dets
        self.fil_css = fil_css
        self.fil_report = fil_report
        self.fil_script = fil_script
        self.takes_range = takes_range
        self.url_load = True # btn_expand
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
                                                lib.get_var_dets(fil_var_dets)
        variables_rc_msg = _("Right click variables to view/edit details")
        # set up panel for frame
        self.panel = wx.Panel(self)
        #self.panel.SetBackgroundColour(wx.Colour(205, 217, 215))
        config_dlg.add_icon(frame=self)
        self.szr_data, self.szr_config_bottom, self.szr_config_top = \
                                    self.get_gen_config_szrs(self.panel) # mixin
        self.szr_output_btns = self.get_szr_output_btns(self.panel, 
                                                        inc_clear=False) # mixin
        szr_main = wx.BoxSizer(wx.VERTICAL)
        bx_desc = wx.StaticBox(self.panel, -1, _("Purpose"))
        szr_desc = wx.StaticBoxSizer(bx_desc, wx.VERTICAL)
        eg1, eg2, eg3 = self.get_examples()
        lbl_desc1 = wx.StaticText(self.panel, -1, eg1)
        lbl_desc2 = wx.StaticText(self.panel, -1, eg2)
        lbl_desc3 = wx.StaticText(self.panel, -1, eg3)
        szr_desc.Add(lbl_desc1, 1, wx.GROW|wx.LEFT, 5)
        szr_desc.Add(lbl_desc2, 1, wx.GROW|wx.LEFT, 5)
        szr_desc.Add(lbl_desc3, 1, wx.GROW|wx.LEFT, 5)
        bx_vars = wx.StaticBox(self.panel, -1, _("Variables"))
        if not mg.IN_WINDOWS: # http://trac.wxwidgets.org/ticket/9859
            bx_vars.SetToolTipString(variables_rc_msg)
        szr_vars = wx.StaticBoxSizer(bx_vars, wx.VERTICAL)
        szr_vars_top = wx.BoxSizer(wx.HORIZONTAL)
        szr_vars_bottom = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_vars_top_left = wx.BoxSizer(wx.VERTICAL)
        szr_vars_top_right = wx.BoxSizer(wx.VERTICAL)
        szr_vars_top_left_top = wx.BoxSizer(wx.HORIZONTAL)
        szr_vars_top_right_top = wx.BoxSizer(wx.HORIZONTAL)
        szr_vars_top_right_bottom = wx.BoxSizer(wx.HORIZONTAL)
        # var averaged
        self.lbl_avg = wx.StaticText(self.panel, -1, u"%s:" % self.averaged)
        self.lbl_avg.SetFont(self.LABEL_FONT)
        # only want the fields which are numeric
        self.drop_avg = wx.Choice(self.panel, -1, choices=[], size=(300,-1))
        self.drop_avg.Bind(wx.EVT_CHOICE, self.on_averaged_sel)
        self.drop_avg.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_vars)
        self.drop_avg.SetToolTipString(variables_rc_msg)
        self.sorted_var_names_avg = []
        self.setup_var(self.drop_avg, mg.VAR_AVG_DEFAULT, 
                       self.sorted_var_names_avg)
        szr_vars_top_left_top.Add(self.lbl_avg, 0, wx.TOP|wx.RIGHT, 5)
        szr_vars_top_left_top.Add(self.drop_avg, 0, wx.RIGHT|wx.TOP, 5)
        self.szr_vars_top_left.Add(szr_vars_top_left_top, 0)
        # group by
        self.lbl_group_by = wx.StaticText(self.panel, -1, _("Group By:"))
        self.lbl_group_by.SetFont(self.LABEL_FONT)
        self.drop_group_by = wx.Choice(self.panel, -1, choices=[], 
                                       size=(300,-1))
        self.drop_group_by.Bind(wx.EVT_CHOICE, self.on_group_by_sel)
        self.drop_group_by.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_group_by)
        self.drop_group_by.SetToolTipString(variables_rc_msg)
        self.gp_vals_sorted = [] # same order in dropdowns
        self.gp_choice_items_sorted = [] # refreshed as required and in 
            # order of labels, not raw values
        self.sorted_var_names_by = [] # var names sorted by labels i.e. same as 
            # dropdown.  Refreshed as needed so always usable.
        self.setup_group_by()
        self.lbl_chop_warning = wx.StaticText(self.panel, -1, "")
        szr_vars_top_right_top.Add(self.lbl_group_by, 0, wx.RIGHT|wx.TOP, 5)
        szr_vars_top_right_top.Add(self.drop_group_by, 0, wx.GROW)
        szr_vars_top_right_top.Add(self.lbl_chop_warning, 1, wx.TOP|wx.RIGHT, 5)
        # group by A
        self.lbl_group_a = wx.StaticText(self.panel, -1, _("Group A:"))
        self.drop_group_a = wx.Choice(self.panel, -1, choices=[], size=(200,-1))
        self.drop_group_a.Bind(wx.EVT_CHOICE, self.on_group_by_a_sel)
        # group by B
        self.lbl_group_b = wx.StaticText(self.panel, -1, _("Group B:"))
        self.drop_group_b = wx.Choice(self.panel, -1, choices=[], size=(200,-1))
        self.drop_group_b.Bind(wx.EVT_CHOICE, self.on_group_by_b_sel)
        self.setup_group_dropdowns()
        szr_vars_top_right_bottom.Add(self.lbl_group_a, 0, wx.RIGHT|wx.TOP, 5)
        szr_vars_top_right_bottom.Add(self.drop_group_a, 0, wx.RIGHT, 5)
        szr_vars_top_right_bottom.Add(self.lbl_group_b, 0, wx.RIGHT|wx.TOP, 5)
        szr_vars_top_right_bottom.Add(self.drop_group_b, 0)
        szr_vars_top_right.Add(szr_vars_top_right_top, 1, wx.GROW)
        szr_vars_top_right.Add(szr_vars_top_right_bottom, 0, wx.GROW|wx.TOP, 5)
        szr_vars_top.Add(self.szr_vars_top_left, 0)
        ln_vert = wx.StaticLine(self.panel, style=wx.LI_VERTICAL) 
        szr_vars_top.Add(ln_vert, 0, wx.GROW|wx.LEFT|wx.RIGHT, 5)
        szr_vars_top.Add(szr_vars_top_right, 0)
        # comment
        self.lbl_phrase = wx.StaticText(self.panel, -1, 
                                        _("Start making your selections"))
        szr_vars_bottom.Add(self.lbl_phrase, 0, wx.GROW|wx.TOP|wx.BOTTOM, 5)
        
        szr_vars.Add(szr_vars_top, 0)      
        szr_vars.Add(szr_vars_bottom, 0, wx.GROW)
        szr_bottom = wx.BoxSizer(wx.HORIZONTAL)
        szr_bottom_left = wx.BoxSizer(wx.VERTICAL)
        if mg.MAX_HEIGHT <= 620:
            myheight = 130
        elif mg.MAX_HEIGHT <= 820:
            myheight = ((mg.MAX_HEIGHT/1024.0)*350) - 20
        else:
            myheight = 350
        self.html = full_html.FullHTML(self.panel, size=(200, myheight))
        html2show = _("<p>Waiting for a report to be run.</p>")
        self.html.show_html(html2show)
        szr_bottom_left.Add(self.html, 1, wx.GROW|wx.BOTTOM, 5)
        szr_bottom_left.Add(self.szr_config_top, 0, wx.GROW)
        szr_bottom_left.Add(self.szr_config_bottom, 0, wx.GROW)
        self.szr_level = self.get_szr_level(self.panel) # mixin
        szr_bottom_left.Add(self.szr_level, 0)
        szr_bottom.Add(szr_bottom_left, 1, wx.GROW)
        szr_bottom.Add(self.szr_output_btns, 0, wx.GROW|wx.LEFT, 10)    
        szr_main.Add(szr_desc, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szr_main.Add(self.szr_data, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szr_main.Add(szr_vars, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szr_main.Add(szr_bottom, 2, wx.GROW|wx.ALL, 10)
        self.add_other_var_opts()
        self.panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()

    def add_other_var_opts(self):
        pass

    def on_rclick_tables(self, event):
        """
        Extend to pass on filter changes to group by val options a and b.
        """
        config_dlg.ConfigDlg.on_rclick_tables(self, event)
        self.refresh_vals()
        # event.Skip() - don't use or will appear twice in Windows!

    def on_rclick_group_by(self, event):
        var_gp, choice_item = self.get_group_by()
        label_gp = lib.get_item_label(item_labels=self.var_labels, 
                                      item_val=var_gp)
        updated = projects.set_var_props(choice_item, var_gp, label_gp, 
                                self.var_labels, self.var_notes, self.var_types, 
                                self.val_dics, self.fil_var_dets)
        if updated:
            self.refresh_vars()

    def on_rclick_vars(self, event):
        var_name, choice_item = self.get_var_dets(self.drop_avg, 
                                                  self.sorted_var_names_avg)
        var_label = lib.get_item_label(item_labels=self.var_labels, 
                                       item_val=var_name)
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                                self.var_labels, self.var_notes, self.var_types, 
                                self.val_dics, self.fil_var_dets)
        if updated:
            self.refresh_vars()
    
    def refresh_vars(self):
        var_gp, var_avg = self.get_vars()
        self.setup_group_by(var_gp)
        self.setup_var(self.drop_avg, mg.VAR_AVG_DEFAULT, 
                       self.sorted_var_names_avg, var_avg)
        self.update_defaults()
        self.update_phrase()
        
    def on_paint(self, event):
        if self.show_chop_warning:
            wx.CallAfter(self.show_chop_warning)
        event.Skip()

    def on_database_sel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        """
        config_dlg.ConfigDlg.on_database_sel(self, event)
        # now update var dropdowns
        self.update_var_dets()
        self.setup_group_by()
        self.setup_var(self.drop_avg, mg.VAR_AVG_DEFAULT,
                       self.sorted_var_names_avg)
        self.setup_group_dropdowns()
                
    def on_table_sel(self, event):
        "Reset key data details after table selection."       
        config_dlg.ConfigDlg.on_table_sel(self, event)
        # now update var dropdowns
        self.update_var_dets()
        self.setup_group_by()
        self.setup_var(self.drop_avg, mg.VAR_AVG_DEFAULT,
                       self.sorted_var_names_avg)
        self.setup_group_dropdowns()
    
    def on_var_dets_file_lost_focus(self, event):
        """
        Want to retain already selected item - even though label and even 
            position may have changed.
        """
        val_a, val_b = self.get_vals()
        var_gp, var_avg = self.get_vars()
        config_dlg.ConfigDlg.on_var_dets_file_lost_focus(self, event)
        self.setup_group_by(var_gp)
        self.setup_var(self.drop_avg, mg.VAR_AVG_DEFAULT, 
                       self.sorted_var_names_avg, var_avg)
        self.setup_group_dropdowns(val_a, val_b)
        self.update_defaults()
        self.update_phrase()
        
    def on_btn_var_dets_path(self, event):
        """
        Want to retain already selected item - even though label and even 
            position may have changed.
        """
        val_a, val_b = self.get_vals()
        var_gp, var_avg = self.get_vars()
        config_dlg.ConfigDlg.on_btn_var_dets_path(self, event)
        self.setup_group_by(var_gp)
        self.setup_var(self.drop_avg, mg.VAR_AVG_DEFAULT, 
                       self.sorted_var_names_avg, var_avg)
        self.setup_group_dropdowns(val_a, val_b)
        self.update_defaults()
        self.update_phrase()
    
    def get_group_by(self):
        idx_by = self.drop_group_by.GetSelection()
        var_gp = self.sorted_var_names_by[idx_by]
        var_gp_item = self.drop_group_by.GetStringSelection()
        return var_gp, var_gp_item
    
    def get_var_dets(self, drop_var, sorted_var_names):
        idx_var = drop_var.GetSelection()
        var_name = sorted_var_names[idx_var]
        var_item = drop_var.GetStringSelection()
        return var_name, var_item
    
    def get_vars(self):
        """
        self.sorted_var_names_by and self.sorted_var_names_avg are set when 
            dropdowns are set (and only changed when reset).
        """
        var_gp, unused = self.get_group_by()
        var_avg, unused = self.get_var_dets(self.drop_avg, 
                                            self.sorted_var_names_avg)
        return var_gp, var_avg
    
    def get_vals(self):
        """
        self.gp_vals_sorted is set when dropdowns are set (and only changed when 
            reset).
        """
        idx_a = self.drop_group_a.GetSelection()
        if idx_a == -1:
            val_a = None
        else:
            val_a = self.gp_vals_sorted[idx_a]
        idx_b = self.drop_group_b.GetSelection()
        if idx_b == -1:
            val_b = None
        else:
            val_b = self.gp_vals_sorted[idx_b]
        return val_a, val_b
    
    def on_group_by_sel(self, event):
        self.refresh_vals()
        event.Skip()
        
    def refresh_vals(self):
        self.setup_group_dropdowns()
        self.update_phrase()
        self.update_defaults()
    
    def update_defaults(self):
        mg.GROUP_BY_DEFAULT = self.drop_group_by.GetStringSelection()
        mg.VAR_AVG_DEFAULT = self.drop_avg.GetStringSelection()
        mg.VAL_A_DEFAULT = self.drop_group_a.GetStringSelection()
        mg.VAL_B_DEFAULT = self.drop_group_b.GetStringSelection()
    
    def on_group_by_a_sel(self, event):        
        self.update_phrase()
        self.update_defaults()
        event.Skip()
        
    def on_group_by_b_sel(self, event):        
        self.update_phrase()
        self.update_defaults()
        event.Skip()
    
    def setup_group_by(self, var_gp=None):
        var_names = projects.get_approp_var_names()
        if self.inc_gp_by_select:
            var_names.insert(0, mg.DROP_SELECT)
        var_gp_by_choice_items, self.sorted_var_names_by = \
                        lib.get_sorted_choice_items(dic_labels=self.var_labels, 
                                        vals=var_names, 
                                        inc_drop_select=self.inc_gp_by_select)
        self.drop_group_by.SetItems(var_gp_by_choice_items)
        # set selection
        idx_gp = projects.get_idx_to_select(var_gp_by_choice_items, var_gp, 
                                           self.var_labels, mg.GROUP_BY_DEFAULT)
        self.drop_group_by.SetSelection(idx_gp)

    def setup_var(self, drop_var, default, sorted_var_names, var_name=None):
        var_names = projects.get_approp_var_names(self.var_types,
                                                  self.min_data_type)
        var_choice_items, sorted_vals = lib.get_sorted_choice_items(
                                                    dic_labels=self.var_labels,
                                                    vals=var_names)
        while True:
            try:
                del sorted_var_names[0]
            except IndexError:
                break
        sorted_var_names.extend(sorted_vals)
        drop_var.SetItems(var_choice_items)
        # set selection
        idx_var = projects.get_idx_to_select(var_choice_items, var_name, 
                                             self.var_labels, default)
        drop_var.SetSelection(idx_var)
        
    def setup_group_dropdowns(self, val_a=None, val_b=None):
        """
        Gets unique values for selected variable.
        Sets choices for drop_group_a and B accordingly.
        """
        debug = False
        var_gp, choice_item = self.get_group_by()
        if not choice_item or choice_item == mg.DROP_SELECT:
            self.lbl_group_a.Enable(False)
            self.drop_group_a.SetItems([])
            self.drop_group_a.Enable(False)
            self.lbl_group_b.Enable(False)
            self.drop_group_b.SetItems([])
            self.drop_group_b.Enable(False)
            return
        self.lbl_group_a.Enable(True)
        self.drop_group_a.Enable(True)
        self.lbl_group_b.Enable(True)
        self.drop_group_b.Enable(True)
        quoter = getdata.get_obj_quoter_func(dd.dbe)
        unused, tbl_filt = lib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
        where_filt, unused = lib.get_tbl_filts(tbl_filt)
        SQL_get_sorted_vals = u"""SELECT %(var_gp)s 
            FROM %(tbl)s 
            %(where_filt)s
            GROUP BY %(var_gp)s 
            ORDER BY %(var_gp)s """ % {"var_gp": quoter(var_gp), 
                                       "tbl": quoter(dd.tbl),
                                       "where_filt": where_filt}
        if debug: print(SQL_get_sorted_vals)
        dd.cur.execute(SQL_get_sorted_vals)
        val_dic = self.val_dics.get(var_gp, {})
        # cope if variable has massive spread of values
        all_vals = dd.cur.fetchall()
        if len(all_vals) > 20:
            self.lbl_chop_warning.SetLabel(_("(1st 20 unique values)"))
            all_vals = all_vals[:20]
        else:
            self.lbl_chop_warning.SetLabel(u"")
        self.gp_vals_sorted = [x[0] for x in all_vals]
        self.gp_choice_items_sorted = [lib.get_choice_item(val_dic, x) 
                                 for x in self.gp_vals_sorted]
        self.drop_group_a.SetItems(self.gp_choice_items_sorted)
        self.drop_group_b.SetItems(self.gp_choice_items_sorted)
        # set selections
        if val_a:
            item_new_version_a = lib.get_choice_item(val_dic, val_a)
            idx_a = self.gp_choice_items_sorted.index(item_new_version_a)
        else: # use defaults if possible
            idx_a = 0
            if mg.VAL_A_DEFAULT:
                try:
                    idx_a = self.gp_choice_items_sorted.index(mg.VAL_A_DEFAULT)
                except ValueError:
                    pass
        self.drop_group_a.SetSelection(idx_a)
        if val_b:
            item_new_version_b = lib.get_choice_item(val_dic, val_b)
            idx_b = self.gp_choice_items_sorted.index(item_new_version_b)
        else: # use defaults if possible
            idx_b = 0
            if mg.VAL_B_DEFAULT:
                try:
                    idx_b = self.gp_choice_items_sorted.index(mg.VAL_B_DEFAULT)
                except ValueError:
                    pass
        self.drop_group_b.SetSelection(idx_b)
    
    def get_drop_vals(self):
        """
        Get values (in unicode form) from main drop downs.
        Returns var_gp_numeric, var_gp, label_gp, val_a, label_a, val_b, 
            label_b, var_avg, label_avg.
        """
        selection_idx_gp = self.drop_group_by.GetSelection()
        var_gp = self.sorted_var_names_by[selection_idx_gp]
        label_gp = lib.get_item_label(item_labels=self.var_labels, 
                                      item_val=var_gp)
        var_gp_numeric = dd.flds[var_gp][mg.FLD_BOLNUMERIC]
        # Now the a and b choices under the group
        val_dic = self.val_dics.get(var_gp, {})
        selection_idx_a = self.drop_group_a.GetSelection()
        val_a_raw = self.gp_vals_sorted[selection_idx_a]
        val_a = lib.any2unicode(val_a_raw)
        label_a = lib.get_item_label(item_labels=val_dic, 
                                     item_val=val_a_raw)
        selection_idx_b = self.drop_group_b.GetSelection()
        val_b_raw = self.gp_vals_sorted[selection_idx_b]
        val_b = lib.any2unicode(val_b_raw)
        label_b = lib.get_item_label(item_labels=val_dic, 
                                     item_val=val_b_raw)
        # the avg variable(s)
        selection_idx_avg = self.drop_avg.GetSelection()
        var_avg = self.sorted_var_names_avg[selection_idx_avg]
        label_avg = lib.get_item_label(item_labels=self.var_labels, 
                                       item_val=var_avg)
        return var_gp_numeric, var_gp, label_gp, val_a, label_a, \
            val_b, label_b, var_avg, label_avg
        
    def on_averaged_sel(self, event):        
        self.update_phrase()
        self.update_defaults()
        event.Skip()
    
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
            add_to_report = self.chk_add_to_report.IsChecked()
            try:
                css_fils, css_idx = output.get_css_dets(self.fil_report, 
                                                        self.fil_css)
            except my_exceptions.MissingCssException:
                self.update_local_display(_("Please check the CSS file exists "
                                            "or set another"))
                lib.safe_end_cursor()
                event.Skip()
                return
            script = self.get_script(css_idx, add_to_report, self.fil_report)
            bolran_report, str_content = output.run_report(OUTPUT_MODULES, 
                                                add_to_report, self.fil_report, 
                                                css_fils, script)
            lib.safe_end_cursor()
            self.update_local_display(str_content)
            self.str_content = str_content
            self.btn_expand.Enable(bolran_report)
        event.Skip()
    
    def test_config_ok(self):
        """
        Are the appropriate selections made to enable an analysis to be run?
        """
        # group by and averaged variables cannot be the same
        if self.drop_group_by.GetStringSelection() == \
                self.drop_avg.GetStringSelection():
            wx.MessageBox(_("The Grouped By Variable and the %s variable "
                            "cannot be the same") % self.averaged)
            return False
        # group A and B cannot be the same
        if self.drop_group_a.GetStringSelection() == \
                self.drop_group_b.GetStringSelection():
            wx.MessageBox(_("Group A and Group B must be different"))
            return False
        if self.takes_range:
            var_gp_numeric, var_gp, unused, unused, unused, unused, unused, \
                unused, unused = self.get_drop_vals()
            # group a must be lower than group b
            val_dic = self.val_dics.get(var_gp, {})
            selection_idx_a = self.drop_group_a.GetSelection()
            val_a = self.gp_vals_sorted[selection_idx_a]
            selection_idx_b = self.drop_group_b.GetSelection()
            val_b = self.gp_vals_sorted[selection_idx_b]
            if var_gp_numeric:
                # NB SQLite could have a string in a numeric field
                # could cause problems even if the string value is not one of 
                # the ones being tested as a range boundary here.
                try:
                    val_a = float(val_a)
                    val_b = float(val_b)
                except ValueError:
                    wx.MessageBox(u"Both values must be numeric.  "
                        u"Values selected were %s and %s" % (val_a, val_b))
                    return False
            if  val_a > val_b:
                wx.MessageBox(_("Group A must be lower than Group B"))
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
            add_to_report = self.chk_add_to_report.IsChecked()
            try:
                css_fils, css_idx = output.get_css_dets(self.fil_report, 
                                                        self.fil_css)
            except my_exceptions.MissingCssException:
                self.update_local_display(_("Please check the CSS file exists "
                                            "or set another"))
                event.Skip()
                return
            script = self.get_script(css_idx, add_to_report, self.fil_report)
            output.export_script(script, self.fil_script, self.fil_report, 
                                 css_fils)
        event.Skip()

    def on_btn_help(self, event):
        wx.MessageBox(u"Under construction")
        event.Skip()
    
    def on_btn_clear(self, event):
        wx.MessageBox(u"Under construction")
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
            pass
        finally:
            self.Destroy()
            event.Skip()