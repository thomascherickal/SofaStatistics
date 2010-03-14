import os
import wx

import my_globals as mg
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
                                  choices=mg.LEVELS, style=wx.RA_SPECIFY_COLS)
    parent.radLevel.SetStringSelection(mg.DEFAULT_LEVEL)
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
        Returns self.szr_data, self.szr_config_bottom (vars and css), 
            self.szr_config_top (reports and scripts) complete
            with widgets and the following setup ready to use: self.con, 
            self.cur, self.dbs, self.tbls, self.flds, self.has_unique, 
            self.idxs, self.db, and self.tbl.
        Widgets include dropdowns for database and tables, and textboxes plus 
            Browse buttons for labels, style, output, and script.
        Each widget has a set of events ready to go as well.
        Assumes self has quite a few properties already set e.g. dbe, 
            default_dbs, fil_script etc.
        """
        self.szr_data = self.get_szr_data(panel)
        self.szr_config_bottom, self.szr_config_top = \
            self.get_misc_config_szrs(panel, readonly)
        return self.szr_data, self.szr_config_bottom, self.szr_config_top
        
    def get_szr_data(self, panel):
        """
        Returns self.szr_data complete with widgets and the following setup ready 
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
                self.idxs) = dbdetsobj.get_db_dets()
        # set up self.dropDatabases and self.dropTables
        self.db = dbdetsobj.db
        self.tbl = dbdetsobj.tbl
        self.dropDatabases, self.dropTables = \
            getdata.get_data_dropdowns(self, panel, self.dbe, self.default_dbs, 
                                       self.default_tbls, self.con_dets,
                                       self.dbs, self.db, self.tbls, self.tbl)
        # not wanted in all cases when dropdowns used e.g. data select
        self.dropTables.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_tables)
        self.dropTables.SetToolTipString(_("Right click to add/remove filter"))
        # 2) Tables
        lblTables = wx.StaticText(panel, -1, _("Table:"))
        lblTables.SetFont(self.LABEL_FONT)
        bxData = wx.StaticBox(panel, -1, _("Data Source"))
        self.szr_data = wx.StaticBoxSizer(bxData, wx.HORIZONTAL)
        self.szr_data.Add(lblDatabases, 0, wx.LEFT|wx.RIGHT, 5)
        self.szr_data.Add(self.dropDatabases, 0, wx.RIGHT, 10)
        self.szr_data.Add(lblTables, 0, wx.RIGHT, 5)
        self.szr_data.Add(self.dropTables, 0)
        return self.szr_data
              
    def get_misc_config_szrs(self, panel, readonly=False):
        """
        Returns self.szr_config_bottom (vars and css), self.szr_config_top 
            (reports and scripts) complete with widgets.
        Widgets include textboxes plus Browse buttons for labels, style, output, 
            and script.
        Each widget has a set of events ready to go as well.
        Assumes self has quite a few properties already set e.g. fil_script etc.
        """
        # Data config details
        self.txtVarDetsFile = wx.TextCtrl(panel, -1, self.fil_var_dets, 
                                         size=(250,-1))
        self.txtVarDetsFile.Bind(wx.EVT_KILL_FOCUS, 
                                 self.on_var_dets_file_lost_focus)
        self.txtVarDetsFile.Enable(not readonly)
        self.btn_var_dets_path = wx.Button(panel, -1, _("Browse"))
        self.btn_var_dets_path.Bind(wx.EVT_BUTTON, self.on_btn_var_dets_path)
        self.btn_var_dets_path.Enable(not readonly)
        # CSS style config details
        self.txtCssFile = wx.TextCtrl(panel, -1, self.fil_css, 
                                      size=(250,-1))
        self.txtCssFile.Bind(wx.EVT_KILL_FOCUS, self.on_css_file_lost_focus)
        self.txtCssFile.Enable(not readonly)
        self.btn_css_path = wx.Button(panel, -1, _("Browse"))
        self.btn_css_path.Bind(wx.EVT_BUTTON, self.on_btn_css_path)
        self.btn_css_path.Enable(not readonly)
        # Output details
        # report
        self.txtReportFile = wx.TextCtrl(panel, -1, self.fil_report, 
                                         size=(250,-1))
        self.txtReportFile.Bind(wx.EVT_KILL_FOCUS, 
                                self.on_report_file_lost_focus)
        self.txtReportFile.Enable(not readonly)
        self.btn_report_path = wx.Button(panel, -1, _("Browse"))
        self.btn_report_path.Bind(wx.EVT_BUTTON, self.on_btn_report_path)
        self.btn_report_path.Enable(not readonly)
        # script
        self.txtScriptFile = wx.TextCtrl(panel, -1, self.fil_script, 
                                         size=(250,-1))
        self.txtScriptFile.Bind(wx.EVT_KILL_FOCUS, 
                                self.on_script_file_lost_focus)
        self.txtScriptFile.Enable(not readonly)
        self.btn_script_path = wx.Button(panel, -1, _("Browse"))
        self.btn_script_path.Bind(wx.EVT_BUTTON, self.on_btn_script_path)
        self.btn_script_path.Enable(not readonly)        
          
        self.szr_config_top = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_config_bottom = wx.BoxSizer(wx.HORIZONTAL)
        # CONFIG TOP
        # Variables
        bxVarConfig = wx.StaticBox(panel, -1, _("Variable config from ..."))
        szrVarConfig = wx.StaticBoxSizer(bxVarConfig, wx.HORIZONTAL)
        szrVarConfig.Add(self.txtVarDetsFile, 1, wx.GROW)
        szrVarConfig.Add(self.btn_var_dets_path, 0, wx.LEFT|wx.RIGHT, 5)
        self.szr_config_top.Add(szrVarConfig, 1, wx.RIGHT, 10)
        # Css
        bxCssConfig = wx.StaticBox(panel, -1, _("Style output using ..."))
        szr_css_config = wx.StaticBoxSizer(bxCssConfig, wx.HORIZONTAL)
        szr_css_config.Add(self.txtCssFile, 1, wx.GROW)
        szr_css_config.Add(self.btn_css_path, 0, wx.LEFT|wx.RIGHT, 5)
        self.szr_config_top.Add(szr_css_config, 1)
        # CONFIG BOTTOM
        # Report
        bxReportConfig = wx.StaticBox(panel, -1, _("Send output to ..."))
        szrReportConfig = wx.StaticBoxSizer(bxReportConfig, wx.HORIZONTAL)
        szrReportConfig.Add(self.txtReportFile, 1, wx.GROW)
        szrReportConfig.Add(self.btn_report_path, 0, wx.LEFT|wx.RIGHT, 5)
        self.szr_config_bottom.Add(szrReportConfig, 1, wx.RIGHT, 10)
        # Script
        bxScriptConfig = wx.StaticBox(panel, -1, _("Export here to reuse"))
        szrScriptConfig = wx.StaticBoxSizer(bxScriptConfig, wx.HORIZONTAL)
        szrScriptConfig.Add(self.txtScriptFile, 1, wx.GROW)
        szrScriptConfig.Add(self.btn_script_path, 0, wx.LEFT|wx.RIGHT, 5)
        self.szr_config_bottom.Add(szrScriptConfig, 1)
        return self.szr_config_bottom, self.szr_config_top

    def get_szrOutputBtns(self, panel, inc_clear=True):
        #main
        self.btn_run = wx.Button(panel, -1, _("Run"))
        self.btn_run.Bind(wx.EVT_BUTTON, self.on_btn_run)
        self.btn_run.SetToolTipString(_("Run report and display results"))
        label_divider = " " if mg.IN_WINDOWS else "\n"
        self.chk_add_to_report = wx.CheckBox(panel, -1, 
                                          _("Add to%sreport" % label_divider))
        self.chk_add_to_report.SetValue(True)
        self.btn_export = wx.Button(panel, -1, _("Export"))
        self.btn_export.Bind(wx.EVT_BUTTON, self.on_btn_export)
        self.btn_export.SetToolTipString(_("Export to script for reuse"))
        self.btn_expand = wx.Button(panel, -1, _("Expand"))
        self.btn_expand.Bind(wx.EVT_BUTTON, self.on_btn_expand)
        self.btn_expand.SetToolTipString(_("Open report in own window"))
        self.btn_expand.Enable(False)
        self.btn_help = wx.Button(panel, wx.ID_HELP)
        self.btn_help.Bind(wx.EVT_BUTTON, self.on_btn_help)
        if inc_clear:
            self.btn_clear = wx.Button(panel, -1, _("Clear"))
            self.btn_clear.SetToolTipString(_("Clear settings"))
            self.btn_clear.Bind(wx.EVT_BUTTON, self.on_btn_clear)
        self.btn_close = wx.Button(panel, wx.ID_CLOSE)
        self.btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        # add to sizer
        self.szrOutputButtons = wx.FlexGridSizer(rows=7, cols=1, hgap=5, vgap=5)
        self.szrOutputButtons.AddGrowableRow(5,2) # idx, propn
        # only relevant if surrounding sizer stretched vertically enough by its 
        # content.
        self.szrOutputButtons.Add(self.btn_run, 0)
        self.szrOutputButtons.Add(self.chk_add_to_report)
        self.szrOutputButtons.Add(self.btn_expand, wx.ALIGN_TOP)
        self.szrOutputButtons.Add(self.btn_export, 0, wx.TOP, 8)
        self.szrOutputButtons.Add(self.btn_help, 0)
        if inc_clear:
            self.szrOutputButtons.Add(self.btn_clear, 0)
        self.szrOutputButtons.Add(self.btn_close, 1, wx.ALIGN_BOTTOM)
        return self.szrOutputButtons

    def reread_fil_var_dets(self):
        self.fil_var_dets = self.txtVarDetsFile.GetValue()
        
    def update_var_dets(self):
        "Update all variable details, including those already displayed"
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
            projects.get_var_dets(self.fil_var_dets)

    # database/ tables (and views)
    def on_database_sel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        """
        (self.dbe, self.db, self.con, self.cur, self.tbls, self.tbl, self.flds, 
                self.has_unique, self.idxs) = getdata.refresh_db_dets(self)
        self.dropTables.SetItems(self.tbls)
        tbls_lc = [x.lower() for x in self.tbls]
        self.dropTables.SetSelection(tbls_lc.index(self.tbl.lower()))
        
    def on_table_sel(self, event):
        "Reset key data details after table selection."       
        self.tbl, self.flds, self.has_unique, self.idxs = \
            getdata.refresh_tbl_dets(self)

    def filt_select(self):
        dlg = filtselect.FiltSelectDlg(self, self.dbe, self.con, self.cur, 
                self.db, self.tbl, self.flds, self.var_labels, self.var_notes, 
                self.var_types, self.val_dics, self.fil_var_dets)
        dlg.ShowModal()
        self.refresh_vars()

    def on_rclick_tables(self, event):
        "Allow addition or removal of data filter"
        self.filt_select()
        getdata.setup_drop_tbls(self.dropTables, self.dbe, self.db, self.tbls, 
                                self.tbl)
        event.Skip()

    # report output
    def on_btn_report_path(self, event):
        "Open dialog and takes the report file selected (if any)"
        dlgGetFile = wx.FileDialog(self, _("Choose a report output file:"), 
            defaultDir=os.path.join(mg.LOCAL_PATH, u"reports"), 
            defaultFile=u"", 
            wildcard=_("HTML files (*.htm)|*.htm|HTML files (*.html)|*.html"))
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            self.fil_report = u"%s" % dlgGetFile.GetPath()
            self.txtReportFile.SetValue(self.fil_report)
        dlgGetFile.Destroy()

    def on_report_file_lost_focus(self, event):
        "Reset report output file"
        self.fil_report = self.txtReportFile.GetValue()
        event.Skip()
    
    # script output
    def on_btn_script_path(self, event):
        "Open dialog and takes the script file selected (if any)"
        dlgGetFile = wx.FileDialog(self, 
            _("Choose a file to export scripts to:"), 
            defaultDir=os.path.join(mg.LOCAL_PATH, "scripts"), 
            defaultFile="", wildcard=_("Scripts (*.py)|*.py"))
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            self.fil_script = u"%s" % dlgGetFile.GetPath()
            self.txtScriptFile.SetValue(self.fil_script)
        dlgGetFile.Destroy()

    def on_script_file_lost_focus(self, event):
        "Reset script file"
        self.fil_script = self.txtScriptFile.GetValue()
        event.Skip()
    
    # label config
    def on_var_dets_file_lost_focus(self, event):
        ""
        self.reread_fil_var_dets()
        self.update_var_dets()
        event.Skip()

    def on_btn_var_dets_path(self, event):
        "Open dialog and takes the variable details file selected (if any)"
        dlgGetFile = wx.FileDialog(self, _("Choose a variable config file:"), 
            defaultDir=os.path.join(mg.LOCAL_PATH, u"vdts"), 
            defaultFile=u"", wildcard=_("Config files (*.vdts)|*.vdts"))
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            fil_var_dets = u"%s" % dlgGetFile.GetPath()
            self.txtVarDetsFile.SetValue(fil_var_dets)
            self.reread_fil_var_dets()
            self.update_var_dets()
        dlgGetFile.Destroy()        

    # css table style
    def on_btn_css_path(self, event):
        "Open dialog and takes the css file selected (if any)"
        dlgGetFile = wx.FileDialog(self, _("Choose a css table style file:"), 
            defaultDir=os.path.join(mg.LOCAL_PATH, "css"), 
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
    
    def on_css_file_lost_focus(self, event):
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
    
    def on_btn_expand(self, event):
        output.display_report(self, self.str_content, self.url_load)
        event.Skip()

def add_icon(frame):
    ib = wx.IconBundle()
    icon_path = os.path.join(mg.SCRIPT_PATH, u"images", u"tinysofa.xpm")
    ib.AddIconFromFile(icon_path, wx.BITMAP_TYPE_XPM)
    frame.SetIcons(ib)