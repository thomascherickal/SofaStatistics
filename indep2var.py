#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os

import wx
import wx.html

import my_globals
import full_html
import gen_config
import getdata
import output
import output_buttons
import projects
import util

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
    uvals = [util.any2unicode(x) for x in vals]
    idx_val_a = uvals.index(val_a.strip('"'))
    idx_val_b = uvals.index(val_b.strip('"'))
    return idx_val_a, idx_val_b


class DlgIndep2VarConfig(wx.Dialog, gen_config.GenConfig, 
                         output_buttons.OutputButtons):
    """
    GenConfig - provides reusable interface for data selection, setting labels 
        etc.  Sets values for db, default_tbl etc and responds to selections 
        etc.
    OutputButtons - provides standard buttons for output dialogs.
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
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
            projects.GetVarDets(fil_var_dets)
        variables_rc_msg = _("Right click variables to view/edit details")
        # set up panel for frame
        self.panel = wx.Panel(self)
        #self.panel.SetBackgroundColour(wx.Colour(205, 217, 215))
        ib = wx.IconBundle()
        ib.AddIconFromFile(os.path.join(my_globals.SCRIPT_PATH, u"images",
                                        u"tinysofa.xpm"), 
                           wx.BITMAP_TYPE_XPM)
        self.SetIcons(ib)
        self.GenConfigSetup(self.panel) # mixin
        self.SetupOutputButtons() # mixin
        szrMain = wx.BoxSizer(wx.VERTICAL)
        bxDesc = wx.StaticBox(self.panel, -1, _("Variables"))
        szrDesc = wx.StaticBoxSizer(bxDesc, wx.VERTICAL)
        szrDescTop = wx.BoxSizer(wx.HORIZONTAL)
        lblPurpose = wx.StaticText(self.panel, -1, _("Purpose:"))
        lblPurpose.SetFont(self.LABEL_FONT)
        eg1, eg2, eg3 = self.GetExamples()
        lblDesc1 = wx.StaticText(self.panel, -1, eg1)
        szrDescTop.Add(lblPurpose, 0, wx.RIGHT, 10)
        szrDescTop.Add(lblDesc1, 0, wx.GROW)
        lblDesc2 = wx.StaticText(self.panel, -1, eg2)
        lblDesc3 = wx.StaticText(self.panel, -1, eg3)
        szrDesc.Add(szrDescTop, 1, wx.GROW|wx.LEFT, 5)
        szrDesc.Add(lblDesc2, 1, wx.GROW|wx.LEFT, 5)
        szrDesc.Add(lblDesc3, 1, wx.GROW|wx.LEFT, 5)
        bxVars = wx.StaticBox(self.panel, -1, _("Variables"))
        if not util.in_windows(): # http://trac.wxwidgets.org/ticket/9859
            bxVars.SetToolTipString(variables_rc_msg)
        szrVars = wx.StaticBoxSizer(bxVars, wx.HORIZONTAL)
        szrVarsLeft = wx.BoxSizer(wx.VERTICAL)
        self.szrVarsRight = wx.BoxSizer(wx.VERTICAL)
        szrVarsLeftTop = wx.BoxSizer(wx.HORIZONTAL)
        szrVarsRightTop = wx.BoxSizer(wx.HORIZONTAL)
        szrVarsLeftMid = wx.BoxSizer(wx.HORIZONTAL)
        # group by
        self.lblGroupBy = wx.StaticText(self.panel, -1, _("Group By:"))
        self.lblGroupBy.SetFont(self.LABEL_FONT)
        self.dropGroupBy = wx.Choice(self.panel, -1, choices=[], size=(300, -1))
        self.dropGroupBy.Bind(wx.EVT_CHOICE, self.OnGroupBySel)
        self.dropGroupBy.Bind(wx.EVT_RIGHT_DOWN, self.OnRightClickGroupBy)
        self.dropGroupBy.SetToolTipString(variables_rc_msg)
        self.setup_group_by()
        self.lblchop_warning = wx.StaticText(self.panel, -1, "")
        szrVarsLeftTop.Add(self.lblGroupBy, 0, wx.RIGHT|wx.TOP, 5)
        szrVarsLeftTop.Add(self.dropGroupBy, 0, wx.GROW)
        szrVarsLeftTop.Add(self.lblchop_warning, 1, wx.TOP|wx.RIGHT, 5)
        # group by A
        self.lblGroupA = wx.StaticText(self.panel, -1, _("Group A:"))
        self.dropGroupA = wx.Choice(self.panel, -1, choices=[], size=(200, -1))
        self.dropGroupA.Bind(wx.EVT_CHOICE, self.OnGroupByASel)
        # group by B
        self.lblGroupB = wx.StaticText(self.panel, -1, _("Group B:"))
        self.dropGroupB = wx.Choice(self.panel, -1, choices=[], size=(200, -1))
        self.dropGroupB.Bind(wx.EVT_CHOICE, self.OnGroupByBSel)
        self.setup_group_dropdowns()
        szrVarsLeftMid.Add(self.lblGroupA, 0, wx.RIGHT|wx.TOP, 5)
        szrVarsLeftMid.Add(self.dropGroupA, 0, wx.RIGHT, 5)
        szrVarsLeftMid.Add(self.lblGroupB, 0, wx.RIGHT|wx.TOP, 5)
        szrVarsLeftMid.Add(self.dropGroupB, 0)
        szrVarsLeft.Add(szrVarsLeftTop, 1, wx.GROW)
        szrVarsLeft.Add(szrVarsLeftMid, 0, wx.GROW|wx.TOP, 5)
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
        szrVarsRightTop.Add(self.lblAveraged, 0, wx.LEFT|wx.TOP, 5)
        szrVarsRightTop.Add(self.dropAveraged, 0)
        self.szrVarsRight.Add(szrVarsRightTop, 0)
        self.lblPhrase = wx.StaticText(self.panel, -1, 
                                       _("Start making your selections"))
        szrVarsLeft.Add(self.lblPhrase, 0, wx.GROW|wx.TOP|wx.BOTTOM, 10)        
        szrVars.Add(szrVarsLeft, 1, wx.LEFT, 5)
        szrVars.Add(self.szrVarsRight, 0)
        self.SetupGenConfigSizer(self.panel) # mixin
        szrBottom = wx.BoxSizer(wx.HORIZONTAL)
        szrBottomLeft = wx.BoxSizer(wx.VERTICAL)
        self.html = wx.html.HtmlWindow(self.panel, size=(200, 250))
        html2show = _("<p>This panel is under construction - more support for"
                      " the user and data visualisations coming.</p>")
        self.html.SetPage(html2show)
        szrBottomLeft.Add(self.html, 1, wx.GROW|wx.BOTTOM, 5)
        szrBottomLeft.Add(self.szrConfigTop, 0, wx.GROW)
        szrBottomLeft.Add(self.szrConfigBottom, 0, wx.GROW)
        bxLevel = wx.StaticBox(self.panel, -1, _("Output Level"))
        szrLevel = wx.StaticBoxSizer(bxLevel, wx.HORIZONTAL)
        radFull = wx.RadioButton(self.panel, -1, _("Full Explanation"), 
                                 style=wx.RB_GROUP)
        radBrief = wx.RadioButton(self.panel, -1, _("Brief Explanation"))
        radResults = wx.RadioButton(self.panel, -1, _("Results Only"))
        radFull.Enable(False)
        radBrief.Enable(False)
        radResults.Enable(False)
        szrLevel.Add(radFull, 0, wx.RIGHT, 10)
        szrLevel.Add(radBrief, 0, wx.RIGHT, 10)
        szrLevel.Add(radResults, 0, wx.RIGHT, 10)
        szrBottomLeft.Add(szrLevel, 0)
        szrBottom.Add(szrBottomLeft, 1, wx.GROW)
        szrBottom.Add(self.szrBtns, 0, wx.GROW|wx.LEFT, 10)           
        szrMain.Add(szrDesc, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(self.szrData, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(szrVars, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(szrBottom, 2, wx.GROW|wx.ALL, 10)
        self.AddOtherVarOpts()
        self.panel.SetSizer(szrMain)
        szrMain.SetSizeHints(self)

    def AddOtherVarOpts(self):
        pass

    def OnRightClickGroupBy(self, event):
        var_gp, choice_item = self.get_group_by()
        var_name, var_label = getdata.extractChoiceDets(choice_item)
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                            self.flds, self.var_labels, self.var_notes, 
                            self.var_types, self.val_dics, self.fil_var_dets)
        if updated:
            self.refresh_vars()

    def OnRightClickAvg(self, event):
        var_avg, choice_item = self.get_avg()
        var_name, var_label = getdata.extractChoiceDets(choice_item)
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                            self.flds, self.var_labels, self.var_notes, 
                            self.var_types, self.val_dics, self.fil_var_dets)
        if updated:
            self.refresh_vars()
    
    def refresh_vars(self):
        var_gp, var_avg = self.get_vars()
        self.setup_group_by(var_gp)
        self.setup_avg(var_avg)
        self.UpdateDefaults()
        self.UpdatePhrase()
        
    def OnPaint(self, event):
        if self.show_chop_warning:
            wx.CallAfter(self.ShowChopWarning)
        event.Skip()

    def OnDatabaseSel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        """
        gen_config.GenConfig.OnDatabaseSel(self, event)
        # now update var dropdowns
        self.update_var_dets()
        self.setup_group_by()
        self.setup_avg()
        self.setup_group_dropdowns()
                
    def OnTableSel(self, event):
        "Reset key data details after table selection."       
        gen_config.GenConfig.OnTableSel(self, event)
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
        gen_config.GenConfig.OnVarDetsFileLostFocus(self, event)
        self.setup_group_by(var_gp)
        self.setup_avg(var_avg)
        self.setup_group_dropdowns(val_a, val_b)
        self.UpdateDefaults()
        self.UpdatePhrase()
        
    def OnButtonVarDetsPath(self, event):
        """
        Want to retain already selected item - even though label and even 
            position may have changed.
        """
        val_a, val_b = self.GetVals()
        var_gp, var_avg = self.get_vars()
        gen_config.GenConfig.OnButtonVarDetsPath(self, event)
        self.setup_group_by(var_gp)
        self.setup_avg(var_avg)
        self.setup_group_dropdowns(val_a, val_b)
        self.UpdateDefaults()
        self.UpdatePhrase()
    
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
        self.setup_group_dropdowns()
        self.UpdatePhrase()
        self.UpdateDefaults()
        event.Skip()
    
    def UpdateDefaults(self):
        my_globals.group_by_default = self.dropGroupBy.GetStringSelection()
        my_globals.group_avg_default = self.dropAveraged.GetStringSelection()
        my_globals.val_a_default = self.dropGroupA.GetStringSelection()
        my_globals.val_b_default = self.dropGroupB.GetStringSelection()
    
    def OnGroupByASel(self, event):        
        self.UpdatePhrase()
        self.UpdateDefaults()
        event.Skip()
        
    def OnGroupByBSel(self, event):        
        self.UpdatePhrase()
        self.UpdateDefaults()
        event.Skip()
    
    def setup_group_by(self, var_gp=None):
        var_names = projects.get_approp_var_names(self.flds)
        var_gp_by_choice_items, self.sorted_var_names_by = \
            getdata.get_sorted_choice_items(dic_labels=self.var_labels, 
                                            vals=var_names)
        self.dropGroupBy.SetItems(var_gp_by_choice_items)
        # set selection
        idx_gp = projects.GetIdxToSelect(var_gp_by_choice_items, var_gp, 
                                self.var_labels, my_globals.group_by_default)
        self.dropGroupBy.SetSelection(idx_gp)

    def setup_avg(self, var_avg=None):
        var_names = projects.get_approp_var_names(self.flds, self.var_types,
                                                  self.min_data_type)
        var_avg_choice_items, self.sorted_var_names_avg = \
            getdata.get_sorted_choice_items(dic_labels=self.var_labels,
                                            vals=var_names)
        self.dropAveraged.SetItems(var_avg_choice_items)
        # set selection
        idx_avg = projects.GetIdxToSelect(var_avg_choice_items, var_avg, 
                                          self.var_labels, 
                                          my_globals.group_avg_default)
        self.dropAveraged.SetSelection(idx_avg)
        
    def setup_group_dropdowns(self, val_a=None, val_b=None):
        """
        Gets unique values for selected variable.
        Sets choices for dropGroupA and B accordingly.
        """
        choice_text = self.dropGroupBy.GetStringSelection()
        if not choice_text:
            return
        var_name, var_label = getdata.extractChoiceDets(choice_text)
        quoter = getdata.get_obj_quoter_func(self.dbe)
        SQL_get_sorted_vals = u"SELECT %s FROM %s GROUP BY %s ORDER BY %s" % \
            (quoter(var_name), quoter(self.tbl), quoter(var_name), 
             quoter(var_name))
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
        vals_with_labels = [getdata.get_choice_item(val_dic, x) \
                            for x in self.vals]
        self.dropGroupA.SetItems(vals_with_labels)
        self.dropGroupB.SetItems(vals_with_labels)
        # set selections
        if val_a:
            item_new_version_a = getdata.get_choice_item(val_dic, val_a)
            idx_a = vals_with_labels.index(item_new_version_a)
        else: # use defaults if possible
            idx_a = 0
            if my_globals.val_a_default:
                try:
                    idx_a = vals_with_labels.index(my_globals.val_a_default)
                except ValueError:
                    pass
        self.dropGroupA.SetSelection(idx_a)
        if val_b:
            item_new_version_b = getdata.get_choice_item(val_dic, val_b)
            idx_b = vals_with_labels.index(item_new_version_b)
        else: # use defaults if possible
            idx_b = 0
            if my_globals.val_b_default:
                try:
                    idx_b = vals_with_labels.index(my_globals.val_b_default)
                except ValueError:
                    pass
        self.dropGroupB.SetSelection(idx_b)
    
    def get_drop_vals(self):
        """
        Get values from main drop downs.
        Returns var_gp, label_gp, val_a, label_a, 
            val_b, label_b, var_avg, label_avg.
        val_a and val_b are quoted if not numeric e.g. '"firefox"' so ready to 
            use in majority of cases.
        """
        choice_gp_text = self.dropGroupBy.GetStringSelection()
        var_gp, label_gp = getdata.extractChoiceDets(choice_gp_text)
        choice_a_text = self.dropGroupA.GetStringSelection()
        val_a, label_a = getdata.extractChoiceDets(choice_a_text)
        choice_b_text = self.dropGroupB.GetStringSelection()
        val_b, label_b = getdata.extractChoiceDets(choice_b_text)
        choice_avg_text = self.dropAveraged.GetStringSelection()
        var_avg, label_avg = getdata.extractChoiceDets(choice_avg_text)
        var_gp_numeric = self.flds[var_gp][my_globals.FLD_BOLNUMERIC]
        if not var_gp_numeric:
            val_a = u"\"%s\"" % val_a
            val_b = u"\"%s\"" % val_b
        return var_gp_numeric, var_gp, label_gp, val_a, label_a, \
            val_b, label_b, var_avg, label_avg
        
    def OnAveragedSel(self, event):        
        self.UpdatePhrase()
        self.UpdateDefaults()
        event.Skip()
    
    def OnButtonRun(self, event):
        """
        Generate script to special location (INT_SCRIPT_PATH), 
            run script putting output in special location 
            (INT_REPORT_PATH) and into report file, and finally, 
            display html output.
        """
        run_ok = self.TestConfigOK()
        if run_ok:
            wx.BeginBusyCursor()
            css_fils, css_idx = output.GetCssDets(self.fil_report, self.fil_css)
            script = self.getScript(css_idx)
            strContent = output.RunReport(OUTPUT_MODULES, self.fil_report, 
                self.chkAddToReport.IsChecked(), css_fils, script, 
                self.con_dets, self.dbe, self.db, self.tbl, self.default_dbs, 
                self.default_tbls)
            wx.EndBusyCursor()
            output.DisplayReport(self, strContent)
        event.Skip()
    
    def TestConfigOK(self):
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
            val_a, unused = \
                getdata.extractChoiceDets(self.dropGroupA.GetStringSelection())
            val_b, unused = \
                getdata.extractChoiceDets(self.dropGroupB.GetStringSelection())
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
        export_ok = self.TestConfigOK()
        if export_ok:
            css_fils, css_idx = output.GetCssDets(self.fil_report, self.fil_css)
            script = self.getScript(css_idx)
            output.ExportScript(script, self.fil_script, 
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
                output.AddClosingScriptCode(f)
                f.close()
        except Exception:
            pass
        finally:
            self.Destroy()
            event.Skip()