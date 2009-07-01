#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os

import wx

import my_globals
import gen_config
import getdata
import output
import output_buttons
import projects

OUTPUT_MODULES = ["my_globals", "core_stats", "getdata", "output", 
                  "stats_output"]


class DlgConfig(wx.Dialog, gen_config.GenConfig, output_buttons.OutputButtons):
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
        # set up panel for frame
        self.panel = wx.Panel(self)
        #self.panel.SetBackgroundColour(wx.Colour(205, 217, 215))
        ib = wx.IconBundle()
        ib.AddIconFromFile(os.path.join(my_globals.SCRIPT_PATH, "images",
                                        "tinysofa.xpm"), 
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
            "Answers the question, are the elements of paired sets of data" + \
                " different from each other?")
        szrDescTop.Add(lblPurpose, 0, wx.RIGHT, 10)
        szrDescTop.Add(lblDesc1, 0, wx.GROW)
        lblDesc2 = wx.StaticText(self.panel, -1,
            "For example, do people have a higher average weight after a " + \
                "diet compared with before?")
        lblDesc3 = wx.StaticText(self.panel, -1,
            "Or does average performance in IQ tests vary between morning " + \
                "and mid afternoon?")
        szrDesc.Add(szrDescTop, 1, wx.GROW|wx.LEFT, 5)
        szrDesc.Add(lblDesc2, 1, wx.GROW|wx.LEFT, 5)
        szrDesc.Add(lblDesc3, 1, wx.GROW|wx.LEFT, 5)
        bxVars = wx.StaticBox(self.panel, -1, "Variables")
        szrVars = wx.StaticBoxSizer(bxVars, wx.VERTICAL)
        szrVarsTop = wx.BoxSizer(wx.HORIZONTAL)
        szrVarsBottom = wx.BoxSizer(wx.HORIZONTAL)
        choice_var_names = self.flds.keys()
        fld_choice_items = \
            getdata.getSortedChoiceItems(dic_labels=self.var_labels, 
                                         vals=choice_var_names)
        self.lblGroupA = wx.StaticText(self.panel, -1, "Group A:")
        self.lblGroupA.SetFont(self.LABEL_FONT)
        self.dropGroupA = wx.Choice(self.panel, -1, choices=fld_choice_items)
        self.dropGroupA.Bind(wx.EVT_CHOICE, self.OnGroupSel)
        szrVarsTop.Add(self.lblGroupA, 0, wx.RIGHT, 5)
        szrVarsTop.Add(self.dropGroupA, 0, wx.GROW)
        self.lblGroupB = wx.StaticText(self.panel, -1, "Group B:")
        self.dropGroupB = wx.Choice(self.panel, -1, choices=fld_choice_items, 
                                    size=(200, -1))
        self.dropGroupB.Bind(wx.EVT_CHOICE, self.OnGroupSel)
        szrVarsTop.Add(self.lblGroupB, 0, wx.RIGHT, 5)
        szrVarsTop.Add(self.dropGroupB, 0, wx.GROW)
        self.lblPhrase = wx.StaticText(self.panel, -1, "")
        self.UpdatePhrase()
        szrVarsBottom.Add(self.lblPhrase, 0, wx.GROW|wx.TOP|wx.BOTTOM, 10)
        szrVars.Add(szrVarsTop, 1, wx.LEFT, 5)
        szrVars.Add(szrVarsBottom, 0, wx.LEFT, 5)
        self.SetupGenConfigSizer()
        szrMid = wx.BoxSizer(wx.HORIZONTAL)
        szrMidLeft = wx.BoxSizer(wx.VERTICAL)
        szrMidLeftBottom = wx.BoxSizer(wx.HORIZONTAL)
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
        radFull.Enable(False)
        radBrief.Enable(False)
        radResults.Enable(False)
        szrLevel.Add(radFull, 0, wx.RIGHT, 10)
        szrLevel.Add(radBrief, 0, wx.RIGHT, 10)
        szrLevel.Add(radResults, 0, wx.RIGHT, 10)
        self.szrOutput.Add(szrLevel)        
        szrMain.Add(self.szrOutput, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        self.panel.SetSizer(szrMain)
        szrMain.SetSizeHints(self)
        self.Fit()
    
    def OnGroupSel(self, event):
        self.UpdatePhrase()
        event.Skip()
        
    def GetDropVals(self):
        """
        Get values from main drop downs.
        Returns var_a, label_a, var_b, label_b.
        """
        choice_a_text = self.dropGroupA.GetStringSelection()
        if not choice_a_text:
            return
        var_a, label_a = getdata.extractChoiceDets(choice_a_text)
        choice_b_text = self.dropGroupB.GetStringSelection()
        if not choice_b_text:
            return
        var_b, label_b = getdata.extractChoiceDets(choice_b_text)
        return var_a, label_a, var_b, label_b
    
    def UpdatePhrase(self):
        """
        Update phrase based on GroupBy, Group A, Group B, and Averaged by field.
        """
        var_a, label_a, var_b, label_b = self.GetDropVals()
        self.lblPhrase.SetLabel("Is \"%s\" different from " % label_a + \
            "\"%s\"?" % label_b)
            
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
            strContent = output.RunReport(OUTPUT_MODULES, self.fil_report, 
                self.fil_css, script, self.conn_dets, self.dbe, self.db, 
                self.tbl_name)
            # Return to normal cursor
            curs = wx.StockCursor(wx.CURSOR_ARROW)
            self.SetCursor(curs)
            output.DisplayReport(self, strContent)
        event.Skip()
    
    def TestConfigOK(self):
        """
        Are the appropriate selections made to enable an analysis to be run?
        """
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
            output.AppendExportedScript(f, script, self.conn_dets, self.dbe, 
                                        self.db, self.tbl_name)
        else:
            # add file name to list, create file, insert preliminary code, 
            # and insert exported script.
            self.open_scripts.append(self.fil_script)
            f = file(self.fil_script, "w")
            output.InsertPrelimCode(modules, f, self.fil_report, self.fil_css)
            output.AppendExportedScript(f, script, self.conn_dets, self.dbe, 
                                        self.db, self.tbl_name)
        f.close()

    def getScript(self):
        "Build script from inputs"
        script_lst = []
        var_gp, label_gp, val_a, label_a, val_b, label_b, var_avg, \
            label_avg = self.GetDropVals()
        strGet_Sample = "sample_%s = core_stats.get_list(" + \
            "dbe=\"%s\", " % self.dbe + \
            "cur=cur, tbl=\"%s\",\n    " % self.tbl_name + \
            "fld_measure=\"%s\", " % var_avg + \
            "fld_filter=\"%s\", " % var_gp + \
            "filter_val=%s)"
        script_lst.append(strGet_Sample % ("a", val_a))
        script_lst.append(strGet_Sample % ("b", val_b))
        script_lst.append("label_a = \"%s\"" % label_a)
        script_lst.append("label_b = \"%s\"" % label_b)
        script_lst.append("label_avg = \"%s\"" % label_avg)
        script_lst.append("t, p, dic_a, dic_b = " + \
            "core_stats.ttest_ind(sample_a, sample_b, label_a, label_b)")
        script_lst.append("ttest_output = stats_output.ttest_output(" + \
            "t, p, label_avg, dic_a, dic_b,\n    indep=True, " + \
            "level=my_globals.OUTPUT_RESULTS_ONLY, page_break_after=False)")
        script_lst.append("fil.write(ttest_output)")
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
