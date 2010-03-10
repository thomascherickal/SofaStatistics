import os
import wx

import my_globals
import filtselect
import getdata
import output
import projects


# explanation level
def get_szrLevel(parent, panel):
    """
    Get self.szrLevel with radio widgets. 
    """
    parent.radLevel = wx.RadioBox(panel, -1, _("Output Level"), 
                                choices=my_globals.LEVELS, 
                                style=wx.RA_SPECIFY_COLS)
    parent.radLevel.SetStringSelection(my_globals.DEFAULT_LEVEL)
    parent.szrLevel = wx.BoxSizer(wx.HORIZONTAL)
    parent.szrLevel.Add(parent.radLevel, 0, wx.RIGHT, 10)
    return parent.szrLevel
    

class ConfigDlg(object):
    """
    The standard interface for choosing data, styles etc.
    Can get sizers ready to use complete with widgets, event methods, and even
        properties e.g. self.con, self.cur etc.
    Used mixin because of large number of properties set and needing to be 
        shared.  The downside is that not always clear where something got set
        when looking from the class that inherits from this mixin.
    """

    def get_gen_config_szrs(self, panel, readonly=False):
        """
        Returns self.szrData, self.szrConfigBottom (vars and css), 
            self.szrConfigTop (reports and scripts) complete
            with widgets and the following setup ready to use: self.con, 
            self.cur, self.dbs, self.tbls, self.flds, self.has_unique, 
            self.idxs, self.db, and self.tbl.
        Widgets include dropdowns for database and tables, and textboxes plus 
            Browse buttons for labels, style, output, and script.
        Each widget has a set of events ready to go as well.
        Assumes self has quite a few properties already set e.g. dbe, 
            default_dbs, fil_script etc.
        """
        self.szrData = self.get_szrData(panel)
        self.szrConfigBottom, self.szrConfigTop = \
            self.get_misc_config_szrs(panel, readonly)
        return self.szrData, self.szrConfigBottom, self.szrConfigTop
        
    def get_szrData(self, panel):
        """
        Returns self.szrData complete with widgets and the following setup ready 
            to use: self.con, self.cur, self.dbs, self.tbls, self.flds, 
            self.has_unique, self.idxs, self.db, and self.tbl.
        Widgets include dropdowns for database and tables.
        Each widget has a set of events ready to go as well.
        Assumes self has quite a few properties already set e.g. dbe, 
            default_dbs etc.
        """
        self.LABEL_FONT = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        # 1) Databases
        lblDatabases = wx.StaticText(panel, -1, _("Database:"))
        lblDatabases.SetFont(self.LABEL_FONT)
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
        self.dropTables.Bind(wx.EVT_CONTEXT_MENU, self.OnRightClickTables)
        self.dropTables.SetToolTipString(_("Right click to add/remove filter"))
        # 2) Tables
        lblTables = wx.StaticText(panel, -1, _("Table:"))
        lblTables.SetFont(self.LABEL_FONT)
        bxData = wx.StaticBox(panel, -1, _("Data Source"))
        self.szrData = wx.StaticBoxSizer(bxData, wx.HORIZONTAL)
        self.szrData.Add(lblDatabases, 0, wx.LEFT|wx.RIGHT, 5)
        self.szrData.Add(self.dropDatabases, 0, wx.RIGHT, 10)
        self.szrData.Add(lblTables, 0, wx.RIGHT, 5)
        self.szrData.Add(self.dropTables, 0)
        return self.szrData
              
    def get_misc_config_szrs(self, panel, readonly=False):
        """
        Returns self.szrConfigBottom (vars and css), self.szrConfigTop (reports 
            and scripts) complete with widgets.
        Widgets include textboxes plus Browse buttons for labels, style, output, 
            and script.
        Each widget has a set of events ready to go as well.
        Assumes self has quite a few properties already set e.g. fil_script etc.
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
        return self.szrConfigBottom, self.szrConfigTop

    def get_szrOutputBtns(self, panel, inc_clear=True):
        #main
        self.btnRun = wx.Button(panel, -1, _("Run"))
        self.btnRun.Bind(wx.EVT_BUTTON, self.OnButtonRun)
        self.btnRun.SetToolTipString(_("Run report and display results"))
        label_divider = " " if my_globals.IN_WINDOWS else "\n"
        self.chkAddToReport = wx.CheckBox(panel, -1, 
                                          _("Add to%sreport" % label_divider))
        self.chkAddToReport.SetValue(True)
        self.btnExport = wx.Button(panel, -1, _("Export"))
        self.btnExport.Bind(wx.EVT_BUTTON, self.OnButtonExport)
        self.btnExport.SetToolTipString(_("Export to script for reuse"))
        self.btnExpand = wx.Button(panel, -1, _("Expand"))
        self.btnExpand.Bind(wx.EVT_BUTTON, self.OnButtonExpand)
        self.btnExpand.SetToolTipString(_("Open report in own window"))
        self.btnExpand.Enable(False)
        self.btnHelp = wx.Button(panel, wx.ID_HELP)
        self.btnHelp.Bind(wx.EVT_BUTTON, self.OnButtonHelp)
        if inc_clear:
            self.btnClear = wx.Button(panel, -1, _("Clear"))
            self.btnClear.SetToolTipString(_("Clear settings"))
            self.btnClear.Bind(wx.EVT_BUTTON, self.OnButtonClear)
        self.btnClose = wx.Button(panel, wx.ID_CLOSE)
        self.btnClose.Bind(wx.EVT_BUTTON, self.OnClose)
        # add to sizer
        self.szrOutputButtons = wx.FlexGridSizer(rows=7, cols=1, hgap=5, vgap=5)
        self.szrOutputButtons.AddGrowableRow(5,2) # idx, propn
        # only relevant if surrounding sizer stretched vertically enough by its 
        # content.
        self.szrOutputButtons.Add(self.btnRun, 0)
        self.szrOutputButtons.Add(self.chkAddToReport)
        self.szrOutputButtons.Add(self.btnExpand, wx.ALIGN_TOP)
        self.szrOutputButtons.Add(self.btnExport, 0, wx.TOP, 8)
        self.szrOutputButtons.Add(self.btnHelp, 0)
        if inc_clear:
            self.szrOutputButtons.Add(self.btnClear, 0)
        self.szrOutputButtons.Add(self.btnClose, 1, wx.ALIGN_BOTTOM)
        return self.szrOutputButtons

    def reread_fil_var_dets(self):
        self.fil_var_dets = self.txtVarDetsFile.GetValue()
        
    def update_var_dets(self):
        "Update all variable details, including those already displayed"
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
            projects.get_var_dets(self.fil_var_dets)

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
            getdata.refresh_tbl_dets(self)

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
        event.Skip()
    
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
        event.Skip()
    
    # label config
    def OnVarDetsFileLostFocus(self, event):
        ""
        self.reread_fil_var_dets()
        self.update_var_dets()
        event.Skip()

    def OnButtonVarDetsPath(self, event):
        "Open dialog and takes the variable details file selected (if any)"
        dlgGetFile = wx.FileDialog(self, _("Choose a variable config file:"), 
            defaultDir=os.path.join(my_globals.LOCAL_PATH, u"vdts"), 
            defaultFile=u"", wildcard=_("Config files (*.vdts)|*.vdts"))
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            fil_var_dets = u"%s" % dlgGetFile.GetPath()
            self.txtVarDetsFile.SetValue(fil_var_dets)
            self.reread_fil_var_dets()
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
            self.update_css()
        dlgGetFile.Destroy()
    
    def update_css(self):
        "Update css, including for demo table"
        self.fil_css = self.txtCssFile.GetValue()
    
    def OnCssFileLostFocus(self, event):
        "Reset css file"
        self.update_css()
        event.Skip()
        
    # explanation level
    def get_szrLevel(self, panel):
        """
        Get self.szrLevel with radio widgets. 
        """
        szrLevel = get_szrLevel(self, panel)
        self.radLevel.Enable(False)
        return szrLevel
    
    def OnButtonExpand(self, event):
        output.display_report(self, self.str_content, self.url_load)
        event.Skip()

def add_icon(frame):
    ib = wx.IconBundle()
    icon_path = os.path.join(my_globals.SCRIPT_PATH, u"images", u"tinysofa.xpm")
    ib.AddIconFromFile(icon_path, wx.BITMAP_TYPE_XPM)
    frame.SetIcons(ib)