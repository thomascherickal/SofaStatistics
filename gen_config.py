import os
import wx

import getdata
import util

LOCAL_PATH = util.get_local_path()


class GenConfig(object):
    "The standard interface for choosing data, styles etc"
    
    def GenConfigSetup(self):
        """
        Sets up dropdowns for database and tables, and textboxes plus Browse
            buttons for labels, style, output, and script.
        """
        # Data details
        # Databases
        self.lblDatabases = wx.StaticText(self.panel, -1, "Database:")
        self.lblDatabases.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, 
                                               wx.BOLD))
        # set up self.dropDatabases and self.dropTables
        getdata.setupDataDropdowns(self, self.panel, self.dbe, self.conn_dets, 
                                   self.default_dbs, self.default_tbls)
        self.dropDatabases.Bind(wx.EVT_CHOICE, self.OnDatabaseSel)
        # Tables
        self.lblTables = wx.StaticText(self.panel, -1, "Table:")
        self.lblTables.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.dropTables.Bind(wx.EVT_CHOICE, self.OnTableSel)
        # Data config details
        self.lblLabelPath = wx.StaticText(self.panel, -1, "Labels:")
        self.lblLabelPath.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txtLabelsFile = wx.TextCtrl(self.panel, -1, self.fil_labels, 
                                         size=(250,-1))
        self.txtLabelsFile.Bind(wx.EVT_KILL_FOCUS, self.OnLabelFileLostFocus)
        self.btnLabelPath = wx.Button(self.panel, -1, "Browse ...")
        self.btnLabelPath.Bind(wx.EVT_BUTTON, self.OnButtonLabelPath)
        #self.btnLabelPath.Bind(wx.EVT_ENTER_WINDOW, self.LabelPathEnterWindow)
        #self.btnLabelPath.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        # CSS style config details
        self.lblCssPath = wx.StaticText(self.panel, -1, "Style:")
        self.lblCssPath.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txtCssFile = wx.TextCtrl(self.panel, -1, self.fil_css, 
                                      size=(250,-1))
        self.txtCssFile.Bind(wx.EVT_KILL_FOCUS, self.OnCssFileLostFocus)
        self.btnCssPath = wx.Button(self.panel, -1, "Browse ...")
        self.btnCssPath.Bind(wx.EVT_BUTTON, self.OnButtonCssPath)
        #self.btnCssPath.Bind(wx.EVT_ENTER_WINDOW, self.CssPathEnterWindow)
        #self.btnCssPath.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        # Output details
        # report 
        self.lblReportPath = wx.StaticText(self.panel, -1, "Report:")
        self.lblReportPath.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, 
                                                wx.BOLD))
        self.txtReportFile = wx.TextCtrl(self.panel, -1, self.fil_report, 
                                         size=(250,-1))
        self.txtReportFile.Bind(wx.EVT_KILL_FOCUS, self.OnReportFileLostFocus)
        self.btnReportPath = wx.Button(self.panel, -1, "Browse ...")
        self.btnReportPath.Bind(wx.EVT_BUTTON, self.OnButtonReportPath)
        #btnReportPath.Bind(wx.EVT_ENTER_WINDOW, self.ReportPathEnterWindow)
        #btnReportPath.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)
        # script
        self.lblScriptPath = wx.StaticText(self.panel, -1, "Script:")
        self.lblScriptPath.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txtScriptFile = wx.TextCtrl(self.panel, -1, self.fil_script, 
                                   size=(250,-1))
        self.txtScriptFile.Bind(wx.EVT_KILL_FOCUS, self.OnScriptFileLostFocus)
        self.btnScriptPath = wx.Button(self.panel, -1, "Browse ...")
        self.btnScriptPath.Bind(wx.EVT_BUTTON, self.OnButtonScriptPath)
        #self.btnScriptPath.Bind(wx.EVT_ENTER_WINDOW, self.ScriptPathEnterWindow)
        #self.btnScriptPath.Bind(wx.EVT_LEAVE_WINDOW, self.BlankStatusBar)

    def SetupGenConfigSizer(self):
        bxData = wx.StaticBox(self.panel, -1, "Data Source")
        self.szrData = wx.StaticBoxSizer(bxData, wx.HORIZONTAL)
        self.szrConfig = wx.BoxSizer(wx.HORIZONTAL)
        bxOutput = wx.StaticBox(self.panel, -1, "Output")
        self.szrOutput = wx.StaticBoxSizer(bxOutput, wx.HORIZONTAL)
        #1 MAIN
        #2 DATA
        #3 DATA INNER
        szrDataInner = wx.BoxSizer(wx.HORIZONTAL)
        szrDataInner.Add(self.lblDatabases, 0, wx.LEFT|wx.RIGHT, 5)
        szrDataInner.Add(self.dropDatabases, 0, wx.RIGHT, 10)
        szrDataInner.Add(self.lblTables, 0, wx.RIGHT, 5)
        szrDataInner.Add(self.dropTables, 0)
        self.szrData.Add(szrDataInner)
        #2 CONFIG
        #3 DATA CONFIG
        bxDataConfig = wx.StaticBox(self.panel, -1, "Data Config")
        szrDataConfig = wx.StaticBoxSizer(bxDataConfig, wx.HORIZONTAL)
        #3 DATA CONFIG INNER
        szrDataConfigInner = wx.BoxSizer(wx.HORIZONTAL)
        szrDataConfigInner.Add(self.lblLabelPath, 0, wx.LEFT|wx.RIGHT, 5)
        szrDataConfigInner.Add(self.txtLabelsFile, 1, wx.GROW|wx.RIGHT, 10)
        szrDataConfigInner.Add(self.btnLabelPath, 0)
        szrDataConfig.Add(szrDataConfigInner, 1)
        self.szrConfig.Add(szrDataConfig, 1, wx.RIGHT, 10)
        #3 CSS CONFIG
        bxCssConfig = wx.StaticBox(self.panel, -1, "Table Style")
        szrCssConfig = wx.StaticBoxSizer(bxCssConfig, wx.HORIZONTAL)
        #3 CSS CONFIG INNER
        szrCssConfigInner = wx.BoxSizer(wx.HORIZONTAL)
        szrCssConfigInner.Add(self.lblCssPath, 0, wx.LEFT|wx.RIGHT, 5)
        szrCssConfigInner.Add(self.txtCssFile, 1, wx.GROW|wx.RIGHT, 10)
        szrCssConfigInner.Add(self.btnCssPath, 0)
        szrCssConfig.Add(szrCssConfigInner, 1)
        self.szrConfig.Add(szrCssConfig, 1)
        #2 OUTPUT
        #3 OUTPUT INNER
        szrOutputInner = wx.BoxSizer(wx.HORIZONTAL)
        # report 
        szrOutputInner.Add(self.lblReportPath, 0, wx.LEFT|wx.RIGHT, 5)
        szrOutputInner.Add(self.txtReportFile, 1, wx.GROW|wx.RIGHT, 10)
        szrOutputInner.Add(self.btnReportPath, 0, wx.RIGHT, 10)
        # script
        szrOutputInner.Add(self.lblScriptPath, 0, wx.LEFT|wx.RIGHT, 5)
        szrOutputInner.Add(self.txtScriptFile, 1, wx.GROW|wx.RIGHT, 10)
        szrOutputInner.Add(self.btnScriptPath, 0)
        self.szrOutput.Add(szrOutputInner, 1)

    # database/ tables (and views)
    def OnDatabaseSel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        """
        getdata.ResetDataAfterDbSel(self)
                
    def OnTableSel(self, event):
        "Reset table, fields, has_unique, and idxs."       
        getdata.ResetDataAfterTblSel(self)

    # report output
    def OnButtonReportPath(self, event):
        "Open dialog and takes the report file selected (if any)"
        dlgGetFile = wx.FileDialog(self, "Choose a report output file:", 
            defaultDir=os.path.join(LOCAL_PATH, "reports"), 
            defaultFile="", 
            wildcard="HTML files (*.htm)|*.htm|HTML files (*.html)|*.html")
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            self.fil_report = "%s" % dlgGetFile.GetPath()
            self.txtReportFile.SetValue(self.fil_report)
        dlgGetFile.Destroy()
        
    #def ReportPathEnterWindow(self, event):
    #    "Hover over Report Path Browse button"
    #    self.statusbar.SetStatusText("Select html file for reporting ...")
    
    def OnReportFileLostFocus(self, event):
        "Reset report output file"
        self.fil_report = self.txtReportFile.GetValue()
    
    # script output
    def OnButtonScriptPath(self, event):
        "Open dialog and takes the script file selected (if any)"
        dlgGetFile = wx.FileDialog(self, "Choose a file to export scripts to:", 
            defaultDir=os.path.join(LOCAL_PATH, "scripts"), 
            defaultFile="", wildcard="Scripts (*.py)|*.py")
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            self.fil_script = "%s" % dlgGetFile.GetPath()
            self.txtScriptFile.SetValue(self.fil_script)
        dlgGetFile.Destroy()
    
    #def ScriptPathEnterWindow(self, event):
    #    "Hover over Script Path Browse button"
    #    self.statusbar.SetStatusText("Select output script file ...")

    def OnScriptFileLostFocus(self, event):
        "Reset script file"
        self.fil_script = self.txtScriptFile.GetValue()
    
    # label config
    def OnLabelFileLostFocus(self, event):
        ""
        self.UpdateLabels()

    def OnButtonLabelPath(self, event):
        "Open dialog and takes the labels file selected (if any)"
        dlgGetFile = wx.FileDialog(self, "Choose a label config file:", 
            defaultDir=os.path.join(LOCAL_PATH, "lbls"), 
            defaultFile="", wildcard="Config files (*.lbls)|*.lbls")
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            fil_labels = "%s" % dlgGetFile.GetPath()
            self.txtLabelsFile.SetValue(fil_labels)
            self.UpdateLabels()
        dlgGetFile.Destroy()
        

    #def LabelPathEnterWindow(self, event):
    #    "Hover over Label Path Browse button"
    #    self.statusbar.SetStatusText("Select source of variable " + \
    #                                 "and value labels ...")
        
    # css table style
    def OnButtonCssPath(self, event):
        "Open dialog and takes the css file selected (if any)"
        dlgGetFile = wx.FileDialog(self, "Choose a css table style file:", 
            defaultDir=os.path.join(LOCAL_PATH, "css"), 
            defaultFile="", 
            wildcard="CSS files (*.css)|*.css")
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            fil_css = "%s" % dlgGetFile.GetPath()
            self.txtCssFile.SetValue(fil_css)
            self.UpdateCss()
        dlgGetFile.Destroy()
    
    def UpdateCss(self):
        "Update css, including for demo table"
        self.fil_css = self.txtCssFile.GetValue()
        self.demo_tab.fil_css = self.fil_css
        self.UpdateDemoDisplay()
        
    #def CssPathEnterWindow(self, event):
    #    "Hover over Css Path Browse button"
    #    self.statusbar.SetStatusText("Select css table style file for " + \
    #                                 "reporting ...")
    
    def OnCssFileLostFocus(self, event):
        "Reset css file"
        self.UpdateCss()