#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os

import wx

import gen_config
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
        ib = wx.IconBundle()
        ib.AddIconFromFile(os.path.join(SCRIPT_PATH, "images","tinysofa.xpm"), 
                           wx.BITMAP_TYPE_XPM)   
        self.SetIcons(ib)
        self.GenConfigSetup()
        self.SetupOutputButtons()
        szrMain = wx.BoxSizer(wx.VERTICAL)
        self.SetupGenConfigSizer()
        szrMain.Add(self.szrData, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(self.szrButtons, 5, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)      
        szrMain.Add(self.szrConfig, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szrMain.Add(self.szrOutput, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        self.panel.SetSizer(szrMain)
        szrMain.SetSizeHints(self)
        self.Fit()
        
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
