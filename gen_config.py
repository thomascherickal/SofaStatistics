import os
import wx

import my_globals
import filtselect
import getdata
import projects


class GenConfig(object):
    "The standard interface for choosing data, styles etc"
    
    def GenConfigSetup(self, panel):
        """
        Sets up dropdowns for database and tables, and textboxes plus Browse
            buttons for labels, style, output, and script.
        Make the following available: self.con, self.cur, self.dbs, self.tbls, 
            self.flds, self.has_unique, self.idxs, self.db, and self.tbl.
        """
        self.LABEL_FONT = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        self.DataConfigSetup(panel)
        self.MiscConfigSetup(panel)
        
    def DataConfigSetup(self, panel):
        """
        Set up database details
        """
        # 1) Databases
        self.lblDatabases = wx.StaticText(panel, -1, _("Database:"))
        self.lblDatabases.SetFont(self.LABEL_FONT)
        # get various db settings
        dbdetsobj = getdata.get_db_dets_obj(self.dbe, self.default_dbs, 
                                            self.default_tbls, self.con_dets)
        (self.con, self.cur, self.dbs, self.tbls, self.flds, self.has_unique,  
                self.idxs) = dbdetsobj.getDbDets()
        # set up self.dropDatabases and self.dropTables
        self.db = dbdetsobj.db
        self.tbl = dbdetsobj.tbl
        self.dropDatabases, self.dropTables = \
            getdata.get_data_dropdowns(self, panel, self.dbe, self.default_dbs, 
                                       self.default_tbls, self.con_dets,
                                       self.dbs, self.db, self.tbls, self.tbl)
        # not wanted in all cases when dropdowns used e.g. data select
        self.dropTables.Bind(wx.EVT_RIGHT_DOWN, self.OnRightClickTables)
        self.dropTables.SetToolTipString(_("Right click to add/remove filter"))
        # 2) Tables
        self.lblTables = wx.StaticText(panel, -1, _("Table:"))
        self.lblTables.SetFont(self.LABEL_FONT)
        
    def MiscConfigSetup(self, panel, readonly=False):
        """
        Set up details of data labels, table styles, output, and scripts
        """
        # Data config details
        self.txtVarDetsFile = wx.TextCtrl(panel, -1, self.fil_var_dets, 
                                         size=(250,-1))
        self.txtVarDetsFile.Bind(wx.EVT_KILL_FOCUS, self.OnVarDetsFileLostFocus)
        self.txtVarDetsFile.Enable(not readonly)
        self.btnVarDetsPath = wx.Button(panel, -1, _("Browse"))
        self.btnVarDetsPath.Bind(wx.EVT_BUTTON, self.OnButtonVarDetsPath)
        self.btnVarDetsPath.Enable(not readonly)
        # CSS style config details
        self.txtCssFile = wx.TextCtrl(panel, -1, self.fil_css, 
                                      size=(250,-1))
        self.txtCssFile.Bind(wx.EVT_KILL_FOCUS, self.OnCssFileLostFocus)
        self.txtCssFile.Enable(not readonly)
        self.btnCssPath = wx.Button(panel, -1, _("Browse"))
        self.btnCssPath.Bind(wx.EVT_BUTTON, self.OnButtonCssPath)
        self.btnCssPath.Enable(not readonly)
        # Output details
        # report
        self.txtReportFile = wx.TextCtrl(panel, -1, self.fil_report, 
                                         size=(250,-1))
        self.txtReportFile.Bind(wx.EVT_KILL_FOCUS, self.OnReportFileLostFocus)
        self.txtReportFile.Enable(not readonly)
        self.btnReportPath = wx.Button(panel, -1, _("Browse"))
        self.btnReportPath.Bind(wx.EVT_BUTTON, self.OnButtonReportPath)
        self.btnReportPath.Enable(not readonly)
        # script
        self.txtScriptFile = wx.TextCtrl(panel, -1, self.fil_script, 
                                   size=(250,-1))
        self.txtScriptFile.Bind(wx.EVT_KILL_FOCUS, self.OnScriptFileLostFocus)
        self.txtScriptFile.Enable(not readonly)
        self.btnScriptPath = wx.Button(panel, -1, _("Browse"))
        self.btnScriptPath.Bind(wx.EVT_BUTTON, self.OnButtonScriptPath)
        self.btnScriptPath.Enable(not readonly)

    def SetupGenConfigSizer(self, panel):
        self.SetupDataConfigSizer(panel)
        self.SetupMiscConfigSizers(panel)
        
    def SetupDataConfigSizer(self, panel):
        "Add pre-defined widgets to self.szrData"
        bxData = wx.StaticBox(panel, -1, _("Data Source"))
        self.szrData = wx.StaticBoxSizer(bxData, wx.HORIZONTAL)
        self.szrData.Add(self.lblDatabases, 0, wx.LEFT|wx.RIGHT, 5)
        self.szrData.Add(self.dropDatabases, 0, wx.RIGHT, 10)
        self.szrData.Add(self.lblTables, 0, wx.RIGHT, 5)
        self.szrData.Add(self.dropTables, 0)
              
    def SetupMiscConfigSizers(self, panel):
        "Add pre-defined widgets to self.szrConfigTop and self.szrConfigBottom"     
        self.szrConfigTop = wx.BoxSizer(wx.HORIZONTAL)
        self.szrConfigBottom = wx.BoxSizer(wx.HORIZONTAL)
        # CONFIG TOP
        # Variables
        bxVarConfig = wx.StaticBox(panel, -1, _("Variable config from ..."))
        szrVarConfig = wx.StaticBoxSizer(bxVarConfig, wx.HORIZONTAL)
        szrVarConfig.Add(self.txtVarDetsFile, 1, wx.GROW)
        szrVarConfig.Add(self.btnVarDetsPath, 0, wx.LEFT|wx.RIGHT, 5)
        self.szrConfigTop.Add(szrVarConfig, 1, wx.RIGHT, 10)
        # Css
        bxCssConfig = wx.StaticBox(panel, -1, _("Style output using ..."))
        szrCssConfig = wx.StaticBoxSizer(bxCssConfig, wx.HORIZONTAL)
        szrCssConfig.Add(self.txtCssFile, 1, wx.GROW)
        szrCssConfig.Add(self.btnCssPath, 0, wx.LEFT|wx.RIGHT, 5)
        self.szrConfigTop.Add(szrCssConfig, 1)
        # CONFIG BOTTOM
        # Report
        bxReportConfig = wx.StaticBox(panel, -1, _("Send output to ..."))
        szrReportConfig = wx.StaticBoxSizer(bxReportConfig, wx.HORIZONTAL)
        szrReportConfig.Add(self.txtReportFile, 1, wx.GROW)
        szrReportConfig.Add(self.btnReportPath, 0, wx.LEFT|wx.RIGHT, 5)
        self.szrConfigBottom.Add(szrReportConfig, 1, wx.RIGHT, 10)
        # Script
        bxScriptConfig = wx.StaticBox(panel, -1, _("Export here to reuse"))
        szrScriptConfig = wx.StaticBoxSizer(bxScriptConfig, wx.HORIZONTAL)
        szrScriptConfig.Add(self.txtScriptFile, 1, wx.GROW)
        szrScriptConfig.Add(self.btnScriptPath, 0, wx.LEFT|wx.RIGHT, 5)
        self.szrConfigBottom.Add(szrScriptConfig, 1)

    def update_var_dets(self):
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
        (self.dbe, self.db, self.con, self.cur, self.tbls, self.tbl, self.flds, 
                self.has_unique, self.idxs) = getdata.refresh_db_dets(self)
        self.dropTables.SetItems(self.tbls)
        tbls_lc = [x.lower() for x in self.tbls]
        self.dropTables.SetSelection(tbls_lc.index(self.tbl.lower()))
        
    def OnTableSel(self, event):
        "Reset key data details after table selection."       
        self.tbl, self.flds, self.has_unique, self.idxs = \
            getdata.RefreshTblDets(self)

    def filt_select(self):
        dlg = filtselect.FiltSelectDlg(self, self.dbe, self.con, self.cur, 
                self.db, self.tbl, self.flds, self.var_labels, self.var_notes, 
                self.var_types, self.val_dics, self.fil_var_dets)
        dlg.ShowModal()
        self.refresh_vars()

    def OnRightClickTables(self, event):
        "Allow addition or removal of data filter"
        self.filt_select()
        getdata.setup_drop_tbls(self.dropTables, self.dbe, self.db, self.tbls, 
                                self.tbl)
        event.Skip()

    # report output
    def OnButtonReportPath(self, event):
        "Open dialog and takes the report file selected (if any)"
        dlgGetFile = wx.FileDialog(self, _("Choose a report output file:"), 
            defaultDir=os.path.join(my_globals.LOCAL_PATH, u"reports"), 
            defaultFile=u"", 
            wildcard=_("HTML files (*.htm)|*.htm|HTML files (*.html)|*.html"))
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            self.fil_report = u"%s" % dlgGetFile.GetPath()
            self.txtReportFile.SetValue(self.fil_report)
        dlgGetFile.Destroy()

    def OnReportFileLostFocus(self, event):
        "Reset report output file"
        self.fil_report = self.txtReportFile.GetValue()
    
    # script output
    def OnButtonScriptPath(self, event):
        "Open dialog and takes the script file selected (if any)"
        dlgGetFile = wx.FileDialog(self, 
            _("Choose a file to export scripts to:"), 
            defaultDir=os.path.join(my_globals.LOCAL_PATH, "scripts"), 
            defaultFile="", wildcard=_("Scripts (*.py)|*.py"))
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            self.fil_script = u"%s" % dlgGetFile.GetPath()
            self.txtScriptFile.SetValue(self.fil_script)
        dlgGetFile.Destroy()

    def OnScriptFileLostFocus(self, event):
        "Reset script file"
        self.fil_script = self.txtScriptFile.GetValue()
    
    # label config
    def OnVarDetsFileLostFocus(self, event):
        ""
        self.update_var_dets()

    def OnButtonVarDetsPath(self, event):
        "Open dialog and takes the variable details file selected (if any)"
        dlgGetFile = wx.FileDialog(self, _("Choose a variable config file:"), 
            defaultDir=os.path.join(my_globals.LOCAL_PATH, u"vdts"), 
            defaultFile=u"", wildcard=_("Config files (*.vdts)|*.vdts"))
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            fil_var_dets = u"%s" % dlgGetFile.GetPath()
            self.txtVarDetsFile.SetValue(fil_var_dets)
            self.update_var_dets()
        dlgGetFile.Destroy()        

    # css table style
    def OnButtonCssPath(self, event):
        "Open dialog and takes the css file selected (if any)"
        dlgGetFile = wx.FileDialog(self, _("Choose a css table style file:"), 
            defaultDir=os.path.join(my_globals.LOCAL_PATH, "css"), 
            defaultFile=u"", 
            wildcard=_("CSS files (*.css)|*.css"))
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            fil_css = u"%s" % dlgGetFile.GetPath()
            self.txtCssFile.SetValue(fil_css)
            self.UpdateCss()
        dlgGetFile.Destroy()
    
    def UpdateCss(self):
        "Update css, including for demo table"
        self.fil_css = self.txtCssFile.GetValue()
    
    def OnCssFileLostFocus(self, event):
        "Reset css file"
        self.UpdateCss()