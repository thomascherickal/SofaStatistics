#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os

import wx
import wx.html

import my_globals
import gen_config
import getdata
import output
import output_buttons
import projects

OUTPUT_MODULES = ["my_globals", "core_stats", "getdata", "output", 
                  "stats_output"]


class DlgPaired2VarConfig(wx.Dialog, gen_config.GenConfig, 
                          output_buttons.OutputButtons):
    """
    GenConfig - provides reusable interface for data selection, setting labels 
        etc.  Sets values for db, default_tbl etc and responds to selections 
        etc.
    OutputButtons - provides standard buttons for output dialogs.
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
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
            projects.GetVarDets(fil_var_dets)
        # set up panel for frame
        self.panel = wx.Panel(self)
        #self.panel.SetBackgroundColour(wx.Colour(205, 217, 215))
        ib = wx.IconBundle()
        ib.AddIconFromFile(os.path.join(my_globals.SCRIPT_PATH, "images",
                                        "tinysofa.xpm"), 
                           wx.BITMAP_TYPE_XPM)   
        self.SetIcons(ib)
        self.GenConfigSetup(self.panel) # mixin
        self.SetupOutputButtons() # mixin
        szrMain = wx.BoxSizer(wx.VERTICAL)
        bxDesc = wx.StaticBox(self.panel, -1, _("Variables"))
        szrDesc = wx.StaticBoxSizer(bxDesc, wx.VERTICAL)
        szrDescTop = wx.BoxSizer(wx.HORIZONTAL)
        lblPurpose = wx.StaticText(self.panel, -1,
            "Purpose:")
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
        szrVars = wx.StaticBoxSizer(bxVars, wx.VERTICAL)
        szrVarsTop = wx.BoxSizer(wx.HORIZONTAL)
        szrVarsBottom = wx.BoxSizer(wx.HORIZONTAL)
        # group A
        self.lblGroupA = wx.StaticText(self.panel, -1, _("Group A:"))
        self.lblGroupA.SetFont(self.LABEL_FONT)
        self.dropGroupA = wx.Choice(self.panel, -1, choices=[], size=(300, -1))
        self.dropGroupA.Bind(wx.EVT_CHOICE, self.OnGroupSel)
        self.dropGroupA.Bind(wx.EVT_RIGHT_DOWN, self.OnRightClickGroupA)
        self.dropGroupA.SetToolTipString(_("Right click variables to view/edit "
                                           "details"))
        szrVarsTop.Add(self.lblGroupA, 0, wx.RIGHT, 5)
        szrVarsTop.Add(self.dropGroupA, 0, wx.GROW)
        # group B
        self.lblGroupB = wx.StaticText(self.panel, -1, _("Group B:"))
        self.dropGroupB = wx.Choice(self.panel, -1, choices=[], size=(300, -1))
        self.dropGroupB.Bind(wx.EVT_CHOICE, self.OnGroupSel)
        self.dropGroupB.Bind(wx.EVT_RIGHT_DOWN, self.OnRightClickGroupB)
        self.dropGroupB.SetToolTipString(_("Right click variables to view/edit "
                                           "details"))
        self.setup_groups()
        szrVarsTop.Add(self.lblGroupB, 0, wx.RIGHT, 5)
        szrVarsTop.Add(self.dropGroupB, 0, wx.GROW)
        # phrase
        self.lblPhrase = wx.StaticText(self.panel, -1, 
                                       _("Start making your selections"))
        szrVarsBottom.Add(self.lblPhrase, 0, wx.GROW|wx.TOP|wx.BOTTOM, 10)
        szrVars.Add(szrVarsTop, 1, wx.LEFT, 5)
        szrVars.Add(szrVarsBottom, 0, wx.LEFT, 5)
        self.SetupGenConfigSizer(self.panel) # mixin
        szrBottom = wx.BoxSizer(wx.HORIZONTAL)
        szrBottomLeft = wx.BoxSizer(wx.VERTICAL)
        self.html = wx.html.HtmlWindow(self.panel, size=(200, 250))
        html2show = _("<p>This panel is under construction - more support for"
                      " the user and data visualisations coming.</p>")
        self.html.SetPage(html2show)
        szrBottomLeft.Add(self.html, 1, wx.GROW|wx.LEFT|wx.BOTTOM, 5)
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
        self.panel.SetSizer(szrMain)
        szrMain.SetSizeHints(self)

    def OnRightClickGroupA(self, event):
        var_a, choice_item = self.get_var_a()
        var_name, var_label = getdata.extractChoiceDets(choice_item)
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                            self.flds, self.var_labels, self.var_notes, 
                            self.var_types, self.val_dics, self.fil_var_dets)
        if updated:
            self.refresh_vars()

    def OnRightClickGroupB(self, event):
        var_b, choice_item = self.get_var_b()
        var_name, var_label = getdata.extractChoiceDets(choice_item)
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                            self.flds, self.var_labels, self.var_notes, 
                            self.var_types, self.val_dics, self.fil_var_dets)
        if updated:
            self.refresh_vars()

    def refresh_vars(self):
        var_a, var_b = self.get_vars()
        fld_choice_items = self.get_group_choices()
        self.setup_group_a(fld_choice_items, var_a)
        self.setup_group_b(fld_choice_items, var_b)
        self.UpdateDefaults()
        self.UpdatePhrase()
        
    def get_group_choices(self):
        """
        Get group choice items.
        Also stores var names, and var names sorted by their labels (for later 
            reference).
        """
        var_names = projects.get_approp_var_names(self.flds, self.var_types,
                                                  self.min_data_type)
        fld_choice_items, self.sorted_var_names = \
            getdata.get_sorted_choice_items(dic_labels=self.var_labels, 
                                            vals=var_names)
        return fld_choice_items
       
    def setup_group_a(self, fld_choice_items, var_a=None):        
        self.dropGroupA.SetItems(fld_choice_items)
        idx_a = projects.GetIdxToSelect(fld_choice_items, var_a, 
                                        self.var_labels, 
                                        my_globals.group_a_default)
        self.dropGroupA.SetSelection(idx_a)            

    def setup_group_b(self, fld_choice_items, var_b=None):        
        self.dropGroupB.SetItems(fld_choice_items)
        idx_b = projects.GetIdxToSelect(fld_choice_items, var_b, 
                                        self.var_labels, 
                                        my_globals.group_b_default)
        self.dropGroupB.SetSelection(idx_b)
        
    def setup_groups(self, var_a=None, var_b=None):
        fld_choice_items = self.get_group_choices()
        self.setup_group_a(fld_choice_items, var_a)
        self.setup_group_b(fld_choice_items, var_b)
    
    def OnDatabaseSel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        """
        gen_config.GenConfig.OnDatabaseSel(self, event)
        self.update_var_dets()
        self.setup_groups()
                
    def OnTableSel(self, event):
        "Reset key data details after table selection."       
        gen_config.GenConfig.OnTableSel(self, event)
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

    def OnVarDetsFileLostFocus(self, event):
        var_a, var_b = self.get_vars()
        gen_config.GenConfig.OnVarDetsFileLostFocus(self, event)
        self.setup_groups(var_a, var_b)
        self.UpdatePhrase()
        
    def OnButtonVarDetsPath(self, event):
        var_a, var_b = self.get_vars()
        gen_config.GenConfig.OnButtonVarDetsPath(self, event)
        self.setup_groups(var_a, var_b)
        self.UpdatePhrase()
        
    def OnGroupSel(self, event):
        self.UpdatePhrase()
        self.UpdateDefaults()
        event.Skip()
        
    def get_drop_vals(self):
        """
        Get values from main drop downs.
        Returns var_a, label_a, var_b, label_b.
        """
        choice_a_text = self.dropGroupA.GetStringSelection()
        var_a, label_a = getdata.extractChoiceDets(choice_a_text)
        choice_b_text = self.dropGroupB.GetStringSelection()
        var_b, label_b = getdata.extractChoiceDets(choice_b_text)
        return var_a, label_a, var_b, label_b
    
    def UpdatePhrase(self):
        """
        Update phrase based on Group A and Group B.
        """
        var_a, label_a, var_b, label_b = self.get_drop_vals()
        self.lblPhrase.SetLabel(_("Is \"%(a)s\" different from \"%(b)s\"?") % \
                                {"a": label_a, "b": label_b})
    
    def UpdateDefaults(self):
        my_globals.group_a_default = self.dropGroupA.GetStringSelection()
        my_globals.group_b_default = self.dropGroupB.GetStringSelection()
    
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
        # group A and B cannot be the same
        if self.dropGroupA.GetStringSelection() == \
                self.dropGroupB.GetStringSelection():
            wx.MessageBox(_("Group A and Group B must be different"))
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
        wx.MessageBox("Under construction")
        event.Skip()
    
    def OnButtonClear(self, event):
        wx.MessageBox("Under construction")
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