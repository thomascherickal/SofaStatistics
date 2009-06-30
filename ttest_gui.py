#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os

import wx

import my_globals
import gen_config
import getdata
import output_buttons
import projects
import util

SCRIPT_PATH = util.get_script_path()


class DlgTTestConfig(wx.Dialog, 
                     gen_config.GenConfig, output_buttons.OutputButtons):
    """
    GenConfig - provides reusable interface for data selection, setting labels 
        etc.  Sets values for db, default_tbl etc and responds to selections 
        etc.
    OutputButtons - provides standard buttons for output dialogs.
    """
    
    def __init__(self, title, dbe, conn_dets, default_dbs=None, 
                 default_tbls=None, fil_labels="", fil_css="", fil_report="", 
                 fil_script="", var_labels=None, var_notes=None, 
                 val_dics=None):
         
        wx.Dialog.__init__(self, parent=None, id=-1, title=title, 
                           pos=(200, 0), 
                           style=wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | \
                           wx.RESIZE_BORDER | wx.SYSTEM_MENU | \
                           wx.CAPTION | wx.CLOSE_BOX | \
                           wx.CLIP_CHILDREN)
        self.dbe = dbe
        self.conn_dets = conn_dets
        self.default_dbs = default_dbs
        self.default_tbls = default_tbls
        self.fil_labels = fil_labels
        self.fil_css = fil_css
        self.fil_report = fil_report
        self.fil_script = fil_script        
        self.var_labels, self.var_notes, self.val_dics = \
            projects.GetLabels(fil_labels)            
        self.open_html = []
        self.open_scripts = []
        self.col_no_vars_item = None # needed if no variable in columns
        # set up panel for frame
        self.panel = wx.Panel(self)
        #self.panel.SetBackgroundColour(wx.Colour(205, 217, 215))

        ib = wx.IconBundle()
        ib.AddIconFromFile(os.path.join(SCRIPT_PATH, "images","tinysofa.xpm"), 
                           wx.BITMAP_TYPE_XPM)   
        self.SetIcons(ib)
        self.GenConfigSetup()
        self.SetupOutputButtons()
        szrMain = wx.BoxSizer(wx.VERTICAL)
        bxDesc = wx.StaticBox(self.panel, -1, "Variables")
        szrDesc = wx.StaticBoxSizer(bxDesc, wx.VERTICAL)
        szrDescTop = wx.BoxSizer(wx.HORIZONTAL)
        lblPurpose = wx.StaticText(self.panel, -1,
            "Purpose:")
        lblPurpose.SetFont(self.LABEL_FONT)
        lblDesc1 = wx.StaticText(self.panel, -1,
            "Answers the question, do 2 groups have a different average?")
        szrDescTop.Add(lblPurpose, 0, wx.RIGHT, 10)
        szrDescTop.Add(lblDesc1, 0, wx.GROW)
        lblDesc2 = wx.StaticText(self.panel, -1,
            "For example, do PhD graduates earn more on average than " + \
            "Masters graduates?")
        lblDesc3 = wx.StaticText(self.panel, -1,
            "Or do parents of pre-schoolers get the same amount of " + \
            "sleep on average as parents of teenagers?")
        szrDesc.Add(szrDescTop, 1, wx.GROW)
        szrDesc.Add(lblDesc2, 1, wx.GROW)
        szrDesc.Add(lblDesc3, 1, wx.GROW)
        bxVars = wx.StaticBox(self.panel, -1, "Variables")
        szrVars = wx.StaticBoxSizer(bxVars, wx.HORIZONTAL)
        szrVarsLeft = wx.BoxSizer(wx.VERTICAL)
        szrVarsRight = wx.BoxSizer(wx.VERTICAL)
        szrVarsLeftTop = wx.BoxSizer(wx.HORIZONTAL)
        szrVarsRightTop = wx.BoxSizer(wx.HORIZONTAL)
        szrVarsLeftMid = wx.BoxSizer(wx.HORIZONTAL)
        choice_var_names = self.flds.keys()
        fld_choice_items = \
            getdata.getSortedChoiceItems(dic_labels=self.var_labels, 
                                         vals=choice_var_names)
        self.lblGroupBy = wx.StaticText(self.panel, -1, "Group By:")
        self.lblGroupBy.SetFont(self.LABEL_FONT)
        self.dropGroupBy = wx.Choice(self.panel, -1, choices=fld_choice_items)
        self.dropGroupBy.Bind(wx.EVT_CHOICE, self.OnGroupBySel)
        szrVarsLeftTop.Add(self.lblGroupBy, 0, wx.RIGHT, 5)
        szrVarsLeftTop.Add(self.dropGroupBy, 0, wx.GROW)
        self.lblGroupA = wx.StaticText(self.panel, -1, "Group A:")
        self.dropGroupA = wx.Choice(self.panel, -1, choices=[], size=(200, -1))
        self.dropGroupA.Bind(wx.EVT_CHOICE, self.OnGroupByASel)
        self.lblGroupB = wx.StaticText(self.panel, -1, "Group B:")
        self.dropGroupB = wx.Choice(self.panel, -1, choices=[], size=(200, -1))
        self.dropGroupB.Bind(wx.EVT_CHOICE, self.OnGroupByBSel)
        self.SetGroupDropdowns()
        szrVarsLeftMid.Add(self.lblGroupA, 0, wx.RIGHT, 5)
        szrVarsLeftMid.Add(self.dropGroupA, 0, wx.RIGHT, 5)
        szrVarsLeftMid.Add(self.lblGroupB, 0, wx.RIGHT, 5)
        szrVarsLeftMid.Add(self.dropGroupB, 0)
        szrVarsLeft.Add(szrVarsLeftTop, 1, wx.GROW)
        szrVarsLeft.Add(szrVarsLeftMid, 0, wx.GROW)
        self.lblAveraged = wx.StaticText(self.panel, -1, "Averaged:")
        self.lblAveraged.SetFont(self.LABEL_FONT)
        # only want the fields which are numeric
        numeric_var_names = [x for x in self.flds if \
                             self.flds[x][my_globals.FLD_BOLNUMERIC]]
        val_choice_items = \
            getdata.getSortedChoiceItems(dic_labels=self.var_labels,
                                         vals=numeric_var_names)
        self.dropAveraged = wx.Choice(self.panel, -1, choices=val_choice_items)
        self.dropAveraged.Bind(wx.EVT_CHOICE, self.OnAveragedSel)
        szrVarsRightTop.Add(self.lblAveraged, 0, wx.LEFT, 10)
        szrVarsRightTop.Add(self.dropAveraged, 0, wx.LEFT, 5)
        szrVarsRight.Add(szrVarsRightTop, 0)
        self.lblPhrase = wx.StaticText(self.panel, -1, "")
        self.UpdatePhrase()
        szrVarsLeft.Add(self.lblPhrase, 0, wx.GROW|wx.TOP|wx.BOTTOM, 10)        
        szrVars.Add(szrVarsLeft, 1, wx.LEFT, 5)
        szrVars.Add(szrVarsRight, 0)
        self.SetupGenConfigSizer()
        szrMid = wx.BoxSizer(wx.HORIZONTAL)
        szrMidLeft = wx.BoxSizer(wx.VERTICAL)
        bxMidLeftTop = wx.StaticBox(self.panel, -1, "Type of t-test")
        szrMidLeftTop = wx.StaticBoxSizer(bxMidLeftTop, wx.HORIZONTAL)
        radIndep = wx.RadioButton(self.panel, -1, "Independent", 
                                  style=wx.RB_GROUP)
        radPaired = wx.RadioButton(self.panel, -1, "Paired")
        self.btnIndepHelp = wx.Button(self.panel, wx.ID_HELP)
        self.btnIndepHelp.Bind(wx.EVT_BUTTON, self.OnIndepHelpButton)
        szrMidLeftTop.Add(radIndep, 0, wx.RIGHT, 10)
        szrMidLeftTop.Add(radPaired, 0, wx.RIGHT, 10)
        szrMidLeftTop.Add(self.btnIndepHelp, 0)
        szrMidLeftBottom = wx.BoxSizer(wx.HORIZONTAL)
        szrMidLeft.Add(szrMidLeftTop, 0, wx.ALL, 5)
        szrMidLeft.Add(szrMidLeftBottom, 0)
        szrMid.Add(szrMidLeft, 5, wx.GROW)
        szrMid.Add(self.szrButtons, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)   
        szrMain.Add(szrDesc, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(self.szrData, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(szrVars, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(szrMid, 2, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 5)   
        szrMain.Add(self.szrConfig, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)

        bxLevel = wx.StaticBox(self.panel, -1, "Output Level")
        szrLevel = wx.StaticBoxSizer(bxLevel, wx.HORIZONTAL)
        radFull = wx.RadioButton(self.panel, -1, "Full Explanation", 
                                 style=wx.RB_GROUP)
        radBrief = wx.RadioButton(self.panel, -1, "Brief Explanation")
        radResults = wx.RadioButton(self.panel, -1, "Results Only")
        szrLevel.Add(radFull, 0, wx.RIGHT, 10)
        szrLevel.Add(radBrief, 0, wx.RIGHT, 10)
        szrLevel.Add(radResults, 0, wx.RIGHT, 10)

        self.szrOutput.Add(szrLevel)
        
        szrMain.Add(self.szrOutput, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        self.panel.SetSizer(szrMain)
        szrMain.SetSizeHints(self)
        self.Fit()
    
    def OnGroupBySel(self, event):
        self.SetGroupDropdowns()
        self.UpdatePhrase()
        event.Skip()
    
    def OnGroupByASel(self, event):        
        self.UpdatePhrase()
        event.Skip()
        
    def OnGroupByBSel(self, event):        
        self.UpdatePhrase()
        event.Skip()
    
    def SetGroupDropdowns(self):
        """
        Gets unique values for selected variable.
        Sets choices for dropGroupA and B accordingly.
        """
        choice_text = self.dropGroupBy.GetStringSelection()
        if not choice_text:
            return
        var_name, var_label = getdata.extractChoiceDets(choice_text)
        quoter = getdata.get_quoter_func(self.dbe)
        SQL_get_sorted_vals = "SELECT %s FROM %s GROUP BY %s ORDER BY %s" % \
            (quoter(var_name), quoter(self.tbl_name), quoter(var_name), 
             quoter(var_name))
        self.cur.execute(SQL_get_sorted_vals)
        val_dic = self.val_dics.get(var_name, {})
        vars_with_labels = [getdata.getChoiceItem(val_dic, x[0]) for \
                            x in self.cur.fetchall()]
        self.dropGroupA.SetItems(vars_with_labels)
        self.dropGroupA.SetSelection(0)
        self.dropGroupB.SetItems(vars_with_labels)
        self.dropGroupB.SetSelection(0)
        
    def UpdatePhrase(self):
        """
        Update phrase based on GroupBy, Group A, Group B, and Averaged by field.
        """
        choice_gp_text = self.dropGroupBy.GetStringSelection()
        if not choice_gp_text:
            return
        _, label_gp = getdata.extractChoiceDets(choice_gp_text)
        choice_a_text = self.dropGroupA.GetStringSelection()
        if not choice_a_text:
            return
        _, label_a = getdata.extractChoiceDets(choice_a_text)
        choice_b_text = self.dropGroupB.GetStringSelection()
        if not choice_b_text:
            return
        _, label_b = getdata.extractChoiceDets(choice_b_text)
        choice_avg_text = self.dropAveraged.GetStringSelection()
        if not choice_avg_text:
            return
        _, label_avg = getdata.extractChoiceDets(choice_avg_text)
        self.lblPhrase.SetLabel("Does %s \"%s\" have" % (label_gp, label_a) + \
            " a different average %s than \"%s\"?" % (label_avg, label_b))
        
    def OnAveragedSel(self, event):        
        self.UpdatePhrase()
        event.Skip()
    
    def OnIndepHelpButton(self, event):
        wx.MessageBox("Is your data for each group recorded in different " + \
          "rows (independent) or together on same row (paired)?" + \
          "\n\nExample of Independent data: if looking at Male vs Female " + \
          "vocabulary we do not have both male and female scores in the " + \
          "same rows. Male and Female data is independent." + \
          "\n\nExample of Paired data: if looking at mental ability in the " + \
          "Morning vs the Evening we might have one row per person with " + \
          "both time periods in the same row. Morning and Evening data is " + \
          "paired.")
    
    def OnButtonRun(self, event):
        """
        Generate script to special location (INT_SCRIPT_PATH), 
            run script putting output in special location 
            (INT_REPORT_PATH) and into report file, and finally, 
            display html output.
        """
        run_ok = self.TestConfigOK()
        if run_ok:
            # hourglass cursor
            curs = wx.StockCursor(wx.CURSOR_WAIT)
            self.SetCursor(curs)
            script = self.getScript()
            strContent = output.RunReport(self.fil_report, self.fil_css, script, 
                            self.conn_dets, self.dbe, self.db, self.tbl_name)
            # Return to normal cursor
            curs = wx.StockCursor(wx.CURSOR_ARROW)
            self.SetCursor(curs)
            self.DisplayReport(strContent)
        else:
            wx.MessageBox("Missing %s data" % missing_dim)

    def DisplayReport(self, strContent):
        # display results
        dlg = showhtml.ShowHTML(parent=self, content=strContent, 
                                file_name=projects.INT_REPORT_FILE, 
                                title="Report", 
                                print_folder=projects.INTERNAL_FOLDER)
        dlg.ShowModal()
        dlg.Destroy()
    
    def TestConfigOK(self):
        """
        Are the appropriate selections made to enable an analysis to be run?
        """
        # group by and averaged variables cannot be the same
        if self.dropGroupBy.GetStringSelection() == \
                self.dropAveraged.GetStringSelection():
            wx.MessageBox("The Grouped By Variable and the Averaged " + \
                          "variable cannot be the same")
            return False
        # group A and B cannot be the same
        if self.dropGroupA.GetStringSelection() == \
                self.dropGroupB.GetStringSelection():
            wx.MessageBox("Group A and Group B must be different")
            return False
        return True
    
   # export script
    def OnButtonExport(self, event):
        """
        Export script if enough data to create table.
        """
        export_ok = self.TestConfigOK()
        if export_ok:
            self.ExportScript()
        event.Skip()
    
    def ExportScript(self):
        """
        Export script for table to file currently displayed.
        If the file doesn't exist, make one and add the preliminary code.
        If a file exists, but is empty, put the preliminary code in then
            the new exported script.
        If the file exists and is not empty, append the script on the end.
        """
        modules = ["my_globals", "core_stats", "getdata", "output", 
                   "stats_output"]
        script = self.getScript()
        if self.fil_script in self.open_scripts:
            # see if empty or not
            f = file(self.fil_script, "r+")
            lines = f.readlines()
            empty_fil = False if lines else True            
            if empty_fil:
                output.InsertPrelimCode(modules, f, self.fil_report, 
                                        self.fil_css)
            # insert exported script
            self.AppendExportedScript(f, script, self.conn_dets, self.dbe, 
                                      self.db, self.tbl_name)
        else:
            # add file name to list, create file, insert preliminary code, 
            # and insert exported script.
            self.open_scripts.append(self.fil_script)
            f = file(self.fil_script, "w")
            output.InsertPrelimCode(modules, f, self.fil_report, self.fil_css)
            self.AppendExportedScript(f, script, self.conn_dets, self.dbe, 
                                      self.db, self.tbl_name)
        f.close()

    def getScript(self, has_rows, has_cols):
        "Build script from inputs"
        script_lst = []
        
        
        return "\n".join(script_lst)

    def OnButtonHelp(self, event):
        wx.MessageBox("Under construction")
        event.Skip()
    
    def OnButtonClear(self, event):
        wx.MessageBox("Under construction")
        event.Skip()
    
    def OnClose(self, event):
        "Close app"
        try:
            self.conn.close()
        except Exception:
            pass
        finally:
            self.Destroy()
            event.Skip()
