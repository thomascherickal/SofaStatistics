#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os

import wx
import wx.html

import my_globals
import lib
import config_dlg
import full_html
import getdata
import output
import projects

OUTPUT_MODULES = ["my_globals", "core_stats", "getdata", "output", 
                  "stats_output"]

def get_range_idxs(vals, val_a, val_b):
    """
    Get range indexes for two values from list of strings.
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
    
    def __init__(self, title, dbe, con_dets, default_dbs=None,
                 default_tbls=None, fil_var_dets="", fil_css="", fil_report="", 
                 fil_script="", takes_range=False):
         
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
        self.takes_range = takes_range
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
        szrVarsTop = wx.BoxSizer(wx.HORIZONTAL)
        szrVarsBottom = wx.BoxSizer(wx.HORIZONTAL)
        self.szrVarsTopLeft = wx.BoxSizer(wx.VERTICAL)
        szrVarsTopRight = wx.BoxSizer(wx.VERTICAL)
        szrVarsTopLeftTop = wx.BoxSizer(wx.HORIZONTAL)
        szrVarsTopRightTop = wx.BoxSizer(wx.HORIZONTAL)
        szrVarsTopRightBottom = wx.BoxSizer(wx.HORIZONTAL)
        # var averaged
        self.lblAveraged = wx.StaticText(self.panel, -1, u"%s:" % self.averaged)
        self.lblAveraged.SetFont(self.LABEL_FONT)
        # only want the fields which are numeric
        self.dropAveraged = wx.Choice(self.panel, -1, choices=[], 
                                      size=(300, -1))
        self.dropAveraged.Bind(wx.EVT_CHOICE, self.OnAveragedSel)
        self.dropAveraged.Bind(wx.EVT_RIGHT_DOWN, self.OnRightClickAvg)
        self.dropAveraged.SetToolTipString(variables_rc_msg)
        self.setup_avg()
        szrVarsTopLeftTop.Add(self.lblAveraged, 0, wx.TOP, 5)
        szrVarsTopLeftTop.Add(self.dropAveraged, 0, wx.RIGHT|wx.TOP, 5)
        self.szrVarsTopLeft.Add(szrVarsTopLeftTop, 0)
        # group by
        self.lblGroupBy = wx.StaticText(self.panel, -1, _("Group By:"))
        self.lblGroupBy.SetFont(self.LABEL_FONT)
        self.dropGroupBy = wx.Choice(self.panel, -1, choices=[], size=(300, -1))
        self.dropGroupBy.Bind(wx.EVT_CHOICE, self.OnGroupBySel)
        self.dropGroupBy.Bind(wx.EVT_RIGHT_DOWN, self.OnRightClickGroupBy)
        self.dropGroupBy.SetToolTipString(variables_rc_msg)
        self.setup_group_by()
        self.lblchop_warning = wx.StaticText(self.panel, -1, "")
        szrVarsTopRightTop.Add(self.lblGroupBy, 0, wx.RIGHT|wx.TOP, 5)
        szrVarsTopRightTop.Add(self.dropGroupBy, 0, wx.GROW)
        szrVarsTopRightTop.Add(self.lblchop_warning, 1, wx.TOP|wx.RIGHT, 5)
        # group by A
        self.lblGroupA = wx.StaticText(self.panel, -1, _("Group A:"))
        self.dropGroupA = wx.Choice(self.panel, -1, choices=[], size=(200, -1))
        self.dropGroupA.Bind(wx.EVT_CHOICE, self.OnGroupByASel)
        # group by B
        self.lblGroupB = wx.StaticText(self.panel, -1, _("Group B:"))
        self.dropGroupB = wx.Choice(self.panel, -1, choices=[], size=(200, -1))
        self.dropGroupB.Bind(wx.EVT_CHOICE, self.OnGroupByBSel)
        self.setup_group_dropdowns()
        szrVarsTopRightBottom.Add(self.lblGroupA, 0, wx.RIGHT|wx.TOP, 5)
        szrVarsTopRightBottom.Add(self.dropGroupA, 0, wx.RIGHT, 5)
        szrVarsTopRightBottom.Add(self.lblGroupB, 0, wx.RIGHT|wx.TOP, 5)
        szrVarsTopRightBottom.Add(self.dropGroupB, 0)
        szrVarsTopRight.Add(szrVarsTopRightTop, 1, wx.GROW)
        szrVarsTopRight.Add(szrVarsTopRightBottom, 0, wx.GROW|wx.TOP, 5)
        szrVarsTop.Add(self.szrVarsTopLeft, 0)
        lnVert = wx.StaticLine(self.panel, style=wx.LI_VERTICAL) 
        szrVarsTop.Add(lnVert, 0, wx.GROW|wx.LEFT|wx.RIGHT, 5)
        szrVarsTop.Add(szrVarsTopRight, 0)
        # comment
        self.lblPhrase = wx.StaticText(self.panel, -1, 
                                       _("Start making your selections"))
        szrVarsBottom.Add(self.lblPhrase, 0, wx.GROW|wx.TOP|wx.BOTTOM, 5)
        
        szrVars.Add(szrVarsTop, 0)      
        szrVars.Add(szrVarsBottom, 0, wx.GROW)
        
        
        
        szrBottom = wx.BoxSizer(wx.HORIZONTAL)
        szrBottomLeft = wx.BoxSizer(wx.VERTICAL)
        self.html = full_html.FullHTML(self.panel, size=(200, 250))
        html2show = _("<p>Waiting for a report to be run.</p>")
        self.html.show_html(html2show)
        szrBottomLeft.Add(self.html, 1, wx.GROW|wx.BOTTOM, 5)
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
        self.add_other_var_opts()
        self.panel.SetSizer(szrMain)
        szrMain.SetSizeHints(self)

    def add_other_var_opts(self):
        pass

    def OnRightClickTables(self, event):
        """
        Extend to pass on filter changes to group by val options a and b.
        """
        config_dlg.ConfigDlg.OnRightClickTables(self, event)
        self.refresh_vals()
        event.Skip()

    def OnRightClickGroupBy(self, event):
        var_gp, choice_item = self.get_group_by()
        var_name, var_label = lib.extract_var_choice_dets(choice_item)
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                            self.flds, self.var_labels, self.var_notes, 
                            self.var_types, self.val_dics, self.fil_var_dets)
        if updated:
            self.refresh_vars()

    def OnRightClickAvg(self, event):
        var_avg, choice_item = self.get_avg()
        var_name, var_label = lib.extract_var_choice_dets(choice_item)
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                            self.flds, self.var_labels, self.var_notes, 
                            self.var_types, self.val_dics, self.fil_var_dets)
        if updated:
            self.refresh_vars()
    
    def refresh_vars(self):
        var_gp, var_avg = self.get_vars()
        self.setup_group_by(var_gp)
        self.setup_avg(var_avg)
        self.update_defaults()
        self.update_phrase()
        
    def OnPaint(self, event):
        if self.show_chop_warning:
            wx.CallAfter(self.ShowChopWarning)
        event.Skip()

    def OnDatabaseSel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        """
        config_dlg.ConfigDlg.OnDatabaseSel(self, event)
        # now update var dropdowns
        self.update_var_dets()
        self.setup_group_by()
        self.setup_avg()
        self.setup_group_dropdowns()
                
    def OnTableSel(self, event):
        "Reset key data details after table selection."       
        config_dlg.ConfigDlg.OnTableSel(self, event)
        # now update var dropdowns
        self.update_var_dets()
        self.setup_group_by()
        self.setup_avg()
        self.setup_group_dropdowns()
    
    def OnVarDetsFileLostFocus(self, event):
        """
        Want to retain already selected item - even though label and even 
            position may have changed.
        """
        val_a, val_b = self.GetVals()
        var_gp, var_avg = self.get_vars()
        config_dlg.ConfigDlg.OnVarDetsFileLostFocus(self, event)
        self.setup_group_by(var_gp)
        self.setup_avg(var_avg)
        self.setup_group_dropdowns(val_a, val_b)
        self.update_defaults()
        self.update_phrase()
        
    def OnButtonVarDetsPath(self, event):
        """
        Want to retain already selected item - even though label and even 
            position may have changed.
        """
        val_a, val_b = self.GetVals()
        var_gp, var_avg = self.get_vars()
        config_dlg.ConfigDlg.OnButtonVarDetsPath(self, event)
        self.setup_group_by(var_gp)
        self.setup_avg(var_avg)
        self.setup_group_dropdowns(val_a, val_b)
        self.update_defaults()
        self.update_phrase()
    
    def get_group_by(self):
        idx_by = self.dropGroupBy.GetSelection()
        var_gp = self.sorted_var_names_by[idx_by]
        var_gp_item = self.dropGroupBy.GetStringSelection()
        return var_gp, var_gp_item
    
    def get_avg(self):
        idx_avg = self.dropAveraged.GetSelection()
        var_avg = self.sorted_var_names_avg[idx_avg]
        var_avg_item = self.dropAveraged.GetStringSelection()
        return var_avg, var_avg_item
    
    def get_vars(self):
        """
        self.sorted_var_names_by and self.sorted_var_names_avg are set when 
            dropdowns are set (and only changed when reset).
        """
        var_gp, unused = self.get_group_by()
        var_avg, unused = self.get_avg()
        return var_gp, var_avg
    
    def GetVals(self):
        """
        self.vals is set when dropdowns are set (and only changed when reset).
        """
        idx_a = self.dropGroupA.GetSelection()
        val_a = self.vals[idx_a]
        idx_b = self.dropGroupB.GetSelection()
        val_b = self.vals[idx_b]
        return val_a, val_b
    
    def OnGroupBySel(self, event):
        self.refresh_vals()
        event.Skip()
        
    def refresh_vals(self):
        self.setup_group_dropdowns()
        self.update_phrase()
        self.update_defaults()
    
    def update_defaults(self):
        my_globals.GROUP_BY_DEFAULT = self.dropGroupBy.GetStringSelection()
        my_globals.GROUP_AVG_DEFAULT = self.dropAveraged.GetStringSelection()
        my_globals.VAL_A_DEFAULT = self.dropGroupA.GetStringSelection()
        my_globals.VAL_B_DEFAULT = self.dropGroupB.GetStringSelection()
    
    def OnGroupByASel(self, event):        
        self.update_phrase()
        self.update_defaults()
        event.Skip()
        
    def OnGroupByBSel(self, event):        
        self.update_phrase()
        self.update_defaults()
        event.Skip()
    
    def setup_group_by(self, var_gp=None):
        var_names = projects.get_approp_var_names(self.flds)
        var_gp_by_choice_items, self.sorted_var_names_by = \
            lib.get_sorted_choice_items(dic_labels=self.var_labels, 
                                        vals=var_names)
        self.dropGroupBy.SetItems(var_gp_by_choice_items)
        # set selection
        idx_gp = projects.get_idx_to_select(var_gp_by_choice_items, var_gp, 
                                self.var_labels, my_globals.GROUP_BY_DEFAULT)
        self.dropGroupBy.SetSelection(idx_gp)

    def setup_avg(self, var_avg=None):
        var_names = projects.get_approp_var_names(self.flds, self.var_types,
                                                  self.min_data_type)
        var_avg_choice_items, self.sorted_var_names_avg = \
            lib.get_sorted_choice_items(dic_labels=self.var_labels,
                                        vals=var_names)
        self.dropAveraged.SetItems(var_avg_choice_items)
        # set selection
        idx_avg = projects.get_idx_to_select(var_avg_choice_items, var_avg, 
                                             self.var_labels, 
                                             my_globals.GROUP_AVG_DEFAULT)
        self.dropAveraged.SetSelection(idx_avg)
        
    def setup_group_dropdowns(self, val_a=None, val_b=None):
        """
        Gets unique values for selected variable.
        Sets choices for dropGroupA and B accordingly.
        """
        debug = False
        choice_text = self.dropGroupBy.GetStringSelection()
        if not choice_text:
            return
        var_name, var_label = lib.extract_var_choice_dets(choice_text)
        quoter = getdata.get_obj_quoter_func(self.dbe)
        unused, tbl_filt = lib.get_tbl_filt(self.dbe, self.db, self.tbl)
        where_filt, unused = lib.get_tbl_filts(tbl_filt)
        SQL_get_sorted_vals = u"""SELECT %(var_name)s 
            FROM %(tbl)s 
            %(where_filt)s
            GROUP BY %(var_name)s 
            ORDER BY %(var_name)s""" % {"var_name": quoter(var_name), 
                                        "tbl": quoter(self.tbl),
                                        "where_filt": where_filt}
        if debug: print(SQL_get_sorted_vals)
        self.cur.execute(SQL_get_sorted_vals)
        val_dic = self.val_dics.get(var_name, {})
        # cope if variable has massive spread of values
        all_vals = self.cur.fetchall()
        if len(all_vals) > 20:
            self.lblchop_warning.SetLabel(_("(1st 20 unique values)"))
            all_vals = all_vals[:20]
        else:
            self.lblchop_warning.SetLabel(u"")
        self.vals = [x[0] for x in all_vals]
        vals_with_labels = [lib.get_choice_item(val_dic, x) for x in self.vals]
        self.dropGroupA.SetItems(vals_with_labels)
        self.dropGroupB.SetItems(vals_with_labels)
        # set selections
        if val_a:
            item_new_version_a = lib.get_choice_item(val_dic, val_a)
            idx_a = vals_with_labels.index(item_new_version_a)
        else: # use defaults if possible
            idx_a = 0
            if my_globals.VAL_A_DEFAULT:
                try:
                    idx_a = vals_with_labels.index(my_globals.VAL_A_DEFAULT)
                except ValueError:
                    pass
        self.dropGroupA.SetSelection(idx_a)
        if val_b:
            item_new_version_b = lib.get_choice_item(val_dic, val_b)
            idx_b = vals_with_labels.index(item_new_version_b)
        else: # use defaults if possible
            idx_b = 0
            if my_globals.VAL_B_DEFAULT:
                try:
                    idx_b = vals_with_labels.index(my_globals.VAL_B_DEFAULT)
                except ValueError:
                    pass
        self.dropGroupB.SetSelection(idx_b)
    
    def get_drop_vals(self):
        """
        Get values from main drop downs.
        Returns var_gp, label_gp, val_a, label_a, val_b, label_b, var_avg, 
            label_avg.
        """
        choice_gp_text = self.dropGroupBy.GetStringSelection()
        var_gp, label_gp = lib.extract_var_choice_dets(choice_gp_text)
        choice_a_text = self.dropGroupA.GetStringSelection()
        val_a, label_a = lib.extract_var_choice_dets(choice_a_text)
        choice_b_text = self.dropGroupB.GetStringSelection()
        val_b, label_b = lib.extract_var_choice_dets(choice_b_text)
        choice_avg_text = self.dropAveraged.GetStringSelection()
        var_avg, label_avg = lib.extract_var_choice_dets(choice_avg_text)
        var_gp_numeric = self.flds[var_gp][my_globals.FLD_BOLNUMERIC]
        return var_gp_numeric, var_gp, label_gp, val_a, label_a, \
            val_b, label_b, var_avg, label_avg
        
    def OnAveragedSel(self, event):        
        self.update_phrase()
        self.update_defaults()
        event.Skip()
    
    def update_local_display(self, strContent):
        self.html.show_html(strContent, url_load=True) # allow footnotes
    
    def OnButtonRun(self, event):
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
        # group by and averaged variables cannot be the same
        if self.dropGroupBy.GetStringSelection() == \
                self.dropAveraged.GetStringSelection():
            wx.MessageBox(_("The Grouped By Variable and the %s variable "
                            "cannot be the same") % self.averaged)
            return False
        # group A and B cannot be the same
        if self.dropGroupA.GetStringSelection() == \
                self.dropGroupB.GetStringSelection():
            wx.MessageBox(_("Group A and Group B must be different"))
            return False
        if self.takes_range:
            var_gp_numeric, var_gp, unused, unused, unused, unused, unused, \
                unused, unused = self.get_drop_vals()
            # group a must be lower than group b
            val_a, unused = lib.extract_var_choice_dets(
                                        self.dropGroupA.GetStringSelection())
            val_b, unused = lib.extract_var_choice_dets(
                                        self.dropGroupB.GetStringSelection())
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
    def OnButtonExport(self, event):
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

    def OnButtonHelp(self, event):
        wx.MessageBox(u"Under construction")
        event.Skip()
    
    def OnButtonClear(self, event):
        wx.MessageBox(u"Under construction")
        event.Skip()
    
    def OnClose(self, event):
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