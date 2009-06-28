#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os

import wx

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
        szrVarsLeftBottom = wx.BoxSizer(wx.HORIZONTAL)
        choice_var_names = self.flds.keys()
        fld_choice_items = [getdata.getVarItem(self.var_labels, x) \
                            for x in choice_var_names]
        fld_choice_items.sort(key=lambda s: s.upper())
        self.lblGroupBy = wx.StaticText(self.panel, -1, "Group By:")
        self.lblGroupBy.SetFont(self.LABEL_FONT)
        self.dropGroupBy = wx.Choice(self.panel, -1, choices=fld_choice_items)
        self.dropGroupBy.Bind(wx.EVT_CHOICE, self.OnGroupBySel)
        szrVarsLeftTop.Add(self.lblGroupBy, 0, wx.RIGHT, 5)
        szrVarsLeftTop.Add(self.dropGroupBy, 1, wx.GROW)
        self.lblGroupA = wx.StaticText(self.panel, -1, "Group A:")
        self.dropGroupA = wx.Choice(self.panel, -1, choices=[])
        self.lblGroupB = wx.StaticText(self.panel, -1, "Group B:")
        self.dropGroupB = wx.Choice(self.panel, -1, choices=[])
        szrVarsLeftBottom.Add(self.lblGroupA, 0, wx.RIGHT, 5)
        szrVarsLeftBottom.Add(self.dropGroupA, 0, wx.RIGHT, 5)
        szrVarsLeftBottom.Add(self.lblGroupB, 0, wx.RIGHT, 5)
        szrVarsLeftBottom.Add(self.dropGroupB, 0)
        szrVarsLeft.Add(szrVarsLeftTop, 1, wx.GROW)
        szrVarsLeft.Add(szrVarsLeftBottom, 0)
        self.lblAveraged = wx.StaticText(self.panel, -1, "Averaged:")
        self.lblAveraged.SetFont(self.LABEL_FONT)
        self.dropAveraged = wx.Choice(self.panel, -1, choices=fld_choice_items)
        self.dropAveraged.Bind(wx.EVT_CHOICE, self.OnAveragedSel)
        szrVarsRightTop.Add(self.lblAveraged, 0, wx.LEFT, 10)
        szrVarsRightTop.Add(self.dropAveraged, 0, wx.LEFT, 5)
        szrVarsRight.Add(szrVarsRightTop, 0)
        self.lblPhrase = wx.StaticText(self.panel, -1, "Does 'Male' have " + \
                                "a different average 'vocab' from 'Female'?")
        szrVarsRight.Add(self.lblPhrase, 0, wx.ALL, 10)
        #szrVarsRight.Add(szrVarsRightBottom, 0)
        szrVars.Add(szrVarsLeft, 0)
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
        pass
    
    def OnAveragedSel(self, event):
        pass
    
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
        pass
    
    def OnButtonExport(self, event):
        pass
    
    def OnButtonHelp(self, event):
        pass
    
    def OnButtonClear(self, event):
        pass
    
    def OnClose(self, event):
        "Close app"
        try:
            self.conn.close()
        except Exception:
            pass
        finally:
            self.Destroy()
