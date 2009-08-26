import os
import wx

import my_globals
import getdata
import projects

LOCAL_PATH = my_globals.LOCAL_PATH


class GenConfig(object):
    "The standard interface for choosing data, styles etc"
    
    def GenConfigSetup(self):
        """
        Sets up dropdowns for database and tables, and textboxes plus Browse
            buttons for labels, style, output, and script.
        """
        self.LABEL_FONT = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        # Data details
        # Databases
        self.lblDatabases = wx.StaticText(self.panel, -1, "Database:")
        self.lblDatabases.SetFont(self.LABEL_FONT)
        # get various db settings
        dbdetsobj = getdata.getDbDetsObj(self.dbe, self.default_dbs, 
                                         self.default_tbls, self.conn_dets)
        (self.conn, self.cur, self.dbs, self.tbls, self.flds, self.has_unique,  
                self.idxs) = dbdetsobj.getDbDets()
        # set up self.dropDatabases and self.dropTables
        self.db = dbdetsobj.db
        self.tbl = dbdetsobj.tbl
        getdata.setupDataDropdowns(self, self.panel, self.dbe, self.default_dbs, 
                                   self.default_tbls, self.conn_dets, 
                                   self.dbs, self.db, self.tbls, self.tbl)
        self.dropDatabases.Bind(wx.EVT_CHOICE, self.OnDatabaseSel)
        # Tables
        self.lblTables = wx.StaticText(self.panel, -1, "Table:")
        self.lblTables.SetFont(self.LABEL_FONT)
        self.dropTables.Bind(wx.EVT_CHOICE, self.OnTableSel)
        # Data config details
        self.txtVarDetsFile = wx.TextCtrl(self.panel, -1, self.fil_var_dets, 
                                         size=(250,-1))
        self.txtVarDetsFile.Bind(wx.EVT_KILL_FOCUS, self.OnVarDetsFileLostFocus)
        self.btnVarDetsPath = wx.Button(self.panel, -1, "Browse")
        self.btnVarDetsPath.Bind(wx.EVT_BUTTON, self.OnButtonVarDetsPath)
        # CSS style config details
        self.txtCssFile = wx.TextCtrl(self.panel, -1, self.fil_css, 
                                      size=(250,-1))
        self.txtCssFile.Bind(wx.EVT_KILL_FOCUS, self.OnCssFileLostFocus)
        self.btnCssPath = wx.Button(self.panel, -1, "Browse")
        self.btnCssPath.Bind(wx.EVT_BUTTON, self.OnButtonCssPath)
        # Output details
        # report
        self.txtReportFile = wx.TextCtrl(self.panel, -1, self.fil_report, 
                                         size=(250,-1))
        self.txtReportFile.Bind(wx.EVT_KILL_FOCUS, self.OnReportFileLostFocus)
        self.btnReportPath = wx.Button(self.panel, -1, "Browse")
        self.btnReportPath.Bind(wx.EVT_BUTTON, self.OnButtonReportPath)
        # script
        self.txtScriptFile = wx.TextCtrl(self.panel, -1, self.fil_script, 
                                   size=(250,-1))
        self.txtScriptFile.Bind(wx.EVT_KILL_FOCUS, self.OnScriptFileLostFocus)
        self.btnScriptPath = wx.Button(self.panel, -1, "Browse")
        self.btnScriptPath.Bind(wx.EVT_BUTTON, self.OnButtonScriptPath)

    def SetupGenConfigSizer(self):
        bxData = wx.StaticBox(self.panel, -1, "Data Source")
        self.szrData = wx.StaticBoxSizer(bxData, wx.HORIZONTAL)
        self.szrConfigTop = wx.BoxSizer(wx.HORIZONTAL)
        self.szrConfigBottom = wx.BoxSizer(wx.HORIZONTAL)
        #1 MAIN
        #2 DATA
        self.szrData.Add(self.lblDatabases, 0, wx.LEFT|wx.RIGHT, 5)
        self.szrData.Add(self.dropDatabases, 0, wx.RIGHT, 10)
        self.szrData.Add(self.lblTables, 0, wx.RIGHT, 5)
        self.szrData.Add(self.dropTables, 0)
        #2 CONFIG TOP
        #3 VARIABLE CONFIG
        bxVarConfig = wx.StaticBox(self.panel, -1, "Variable Config")
        szrVarConfig = wx.StaticBoxSizer(bxVarConfig, wx.HORIZONTAL)
        szrVarConfig.Add(self.txtVarDetsFile, 1, wx.GROW)
        szrVarConfig.Add(self.btnVarDetsPath, 0, wx.LEFT|wx.RIGHT, 5)
        self.szrConfigTop.Add(szrVarConfig, 1, wx.RIGHT, 10)
        #3 CSS CONFIG
        bxCssConfig = wx.StaticBox(self.panel, -1, "Table Style")
        szrCssConfig = wx.StaticBoxSizer(bxCssConfig, wx.HORIZONTAL)
        szrCssConfig.Add(self.txtCssFile, 1, wx.GROW)
        szrCssConfig.Add(self.btnCssPath, 0, wx.LEFT|wx.RIGHT, 5)
        self.szrConfigTop.Add(szrCssConfig, 1)
        #3 CONFIG BOTTOM
        #3 REPORT
        bxReportConfig = wx.StaticBox(self.panel, -1, "Output Report")
        szrReportConfig = wx.StaticBoxSizer(bxReportConfig, wx.HORIZONTAL)
        szrReportConfig.Add(self.txtReportFile, 1, wx.GROW)
        szrReportConfig.Add(self.btnReportPath, 0, wx.LEFT|wx.RIGHT, 5)
        self.szrConfigBottom.Add(szrReportConfig, 1, wx.RIGHT, 10)
        #3 SCRIPT
        bxScriptConfig = wx.StaticBox(self.panel, -1, "Automation Script")
        szrScriptConfig = wx.StaticBoxSizer(bxScriptConfig, wx.HORIZONTAL)
        szrScriptConfig.Add(self.txtScriptFile, 1, wx.GROW)
        szrScriptConfig.Add(self.btnScriptPath, 0, wx.LEFT|wx.RIGHT, 5)
        self.szrConfigBottom.Add(szrScriptConfig, 1)

    def UpdateVarDets(self):
        "Update all variable details, including those already displayed"
        self.fil_var_dets = self.txtVarDetsFile.GetValue()
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
            projects.GetVarDets(self.fil_var_dets)

    # database/ tables (and views)
    def OnDatabaseSel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        """
        (self.dbe, self.db, self.cur, self.tbls, self.tbl, self.flds, 
                self.has_unique, self.idxs) = getdata.RefreshDbDets(self)
        self.dropTables.SetItems(self.tbls)
        tbls_lc = [x.lower() for x in self.tbls]
        self.dropTables.SetSelection(tbls_lc.index(self.tbl.lower()))
        
    def OnTableSel(self, event):
        "Reset key data details after table selection."       
        self.tbl, self.flds, self.has_unique, self.idxs = \
            getdata.RefreshTblDets(self)

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

    def OnScriptFileLostFocus(self, event):
        "Reset script file"
        self.fil_script = self.txtScriptFile.GetValue()
    
    # label config
    def OnVarDetsFileLostFocus(self, event):
        ""
        self.UpdateVarDets()

    def OnButtonVarDetsPath(self, event):
        "Open dialog and takes the variable details file selected (if any)"
        dlgGetFile = wx.FileDialog(self, "Choose a variable config file:", 
            defaultDir=os.path.join(LOCAL_PATH, "vdts"), 
            defaultFile="", wildcard="Config files (*.vdts)|*.vdts")
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            fil_var_dets = "%s" % dlgGetFile.GetPath()
            self.txtVarDetsFile.SetValue(fil_var_dets)
            self.UpdateVarDets()
        dlgGetFile.Destroy()        

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
    
    def OnCssFileLostFocus(self, event):
        "Reset css file"
        self.UpdateCss()