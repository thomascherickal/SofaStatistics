import os
import wx

import my_globals as mg
import lib
import getdata
# import filtselect # prevent circular import
import output
import showhtml
import webbrowser

dd = getdata.get_dd()

# explanation level
def get_szr_level(parent, panel):
    """
    Get self.szr_level with radio widgets. 
    """
    parent.rad_level = wx.RadioBox(panel, -1, _("Output Level"), 
                                   choices=mg.LEVELS, style=wx.RA_SPECIFY_COLS)
    parent.rad_level.SetStringSelection(mg.DEFAULT_LEVEL)
    parent.szr_level = wx.BoxSizer(wx.HORIZONTAL)
    parent.szr_level.Add(parent.rad_level, 0, wx.RIGHT, 10)
    return parent.szr_level

label_divider = " " if mg.IN_WINDOWS else "\n"
add_to_report = _("Add to%sreport" % label_divider)
run = _("Run")


class ConfigDlg(object):
    """
    The standard interface for choosing data, styles etc.
    Can get sizers ready to use complete with widgets, event methods, and even
        properties e.g. dd.con, dd.cur etc.
    Used mixin because of large number of properties set and needing to be 
        shared.  The downside is that not always clear where something got set
        when looking from the class that inherits from this mixin.
    """

    def get_gen_config_szrs(self, panel, readonly=False):
        """
        Returns self.szr_data, self.szr_config_bottom (vars and css), 
            self.szr_config_top (reports and scripts) complete
            with widgets.  mg.DATA_DETS as dd is set up ready to use.
        Widgets include dropdowns for database and tables, and textboxes plus 
            Browse buttons for labels, style, output, and script.
        Each widget has a set of events ready to go as well.
        Assumes self has quite a few properties already set e.g. fil_script etc.
        """
        self.szr_data = self.get_szr_data(panel)
        self.szr_config_bottom, self.szr_config_top = \
                                    self.get_misc_config_szrs(panel, readonly)
        return self.szr_data, self.szr_config_bottom, self.szr_config_top
        
    def get_szr_data(self, panel):
        """
        Returns self.szr_data complete with widgets. dd is updated.
        Widgets include dropdowns for database and tables.
        Each widget has a set of events ready to go as well.
        Assumes self has quite a few properties already set.
        """
        self.LABEL_FONT = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        # 1) Databases
        lbl_databases = wx.StaticText(panel, -1, _("Database:"))
        lbl_databases.SetFont(self.LABEL_FONT)
        # get various db settings
        # set up self.drop_dbs and self.drop_tbls
        self.drop_dbs, self.drop_tbls = getdata.get_data_dropdowns(self, panel, 
                                                                dd.default_dbs)
        # not wanted in all cases when dropdowns used e.g. data select
        self.drop_tbls.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_tables)
        self.drop_tbls.SetToolTipString(_("Right click to add/remove filter"))
        # 2) Tables
        lbl_tables = wx.StaticText(panel, -1, _("Table:"))
        lbl_tables.SetFont(self.LABEL_FONT)
        bx_data = wx.StaticBox(panel, -1, _("Data Source"))
        self.szr_data = wx.StaticBoxSizer(bx_data, wx.HORIZONTAL)
        self.szr_data.Add(lbl_databases, 0, wx.LEFT|wx.RIGHT, 5)
        self.szr_data.Add(self.drop_dbs, 0, wx.RIGHT, 10)
        self.szr_data.Add(lbl_tables, 0, wx.RIGHT, 5)
        self.szr_data.Add(self.drop_tbls, 0)
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
        self.txt_var_dets_file = wx.TextCtrl(panel, -1, self.fil_var_dets, 
                                             size=(200,-1))
        self.txt_var_dets_file.Bind(wx.EVT_KILL_FOCUS, 
                                    self.on_var_dets_file_lost_focus)
        self.txt_var_dets_file.Enable(not readonly)
        browse = _("Browse")
        self.btn_var_dets_path = wx.Button(panel, -1, browse)
        self.btn_var_dets_path.Bind(wx.EVT_BUTTON, self.on_btn_var_dets_path)
        self.btn_var_dets_path.Enable(not readonly)
        self.btn_var_dets_path.SetToolTipString(_("Select an existing variable "
                                                  "config file"))
        # CSS style config details
        self.txt_css_file = wx.TextCtrl(panel, -1, self.fil_css, 
                                        size=(200,-1))
        self.txt_css_file.Bind(wx.EVT_KILL_FOCUS, self.on_css_file_lost_focus)
        self.txt_css_file.Enable(not readonly)
        self.btn_css_path = wx.Button(panel, -1, browse)
        self.btn_css_path.Bind(wx.EVT_BUTTON, self.on_btn_css_path)
        self.btn_css_path.Enable(not readonly)
        self.btn_css_path.SetToolTipString(_("Select an existing css style "
                                             "file"))
        # Output details
        # report
        self.txt_report_file = wx.TextCtrl(panel, -1, self.fil_report, 
                                           size=(300,-1))
        self.txt_report_file.Bind(wx.EVT_KILL_FOCUS, 
                                self.on_report_file_lost_focus)
        self.txt_report_file.Enable(not readonly)
        self.btn_report_path = wx.Button(panel, -1, browse)
        self.btn_report_path.Bind(wx.EVT_BUTTON, self.on_btn_report_path)
        self.btn_report_path.Enable(not readonly)
        self.btn_report_path.SetToolTipString(_("Select or create an HTML "
                                                "output file"))
        self.btn_view = wx.Button(panel, -1, _("View"))
        self.btn_view.Bind(wx.EVT_BUTTON, self.on_btn_view)
        self.btn_view.Enable(not readonly)
        self.btn_view.SetToolTipString(_("View selected HTML output file in "
                                         "your default browser"))
        # script
        self.txt_script_file = wx.TextCtrl(panel, -1, self.fil_script, 
                                           size=(200,-1))
        self.txt_script_file.Bind(wx.EVT_KILL_FOCUS, 
                                  self.on_script_file_lost_focus)
        self.txt_script_file.Enable(not readonly)
        self.btn_script_path = wx.Button(panel, -1, browse)
        self.btn_script_path.Bind(wx.EVT_BUTTON, self.on_btn_script_path)
        self.btn_script_path.Enable(not readonly)   
        self.btn_script_path.SetToolTipString(_("Select or create a Python "
                                                "script file"))
        self.szr_config_top = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_config_bottom = wx.BoxSizer(wx.HORIZONTAL)
        # Report
        bx_report_config = wx.StaticBox(panel, -1, _("Send output to ..."))
        szr_report_config = wx.StaticBoxSizer(bx_report_config, wx.HORIZONTAL)
        szr_report_config.Add(self.txt_report_file, 1, wx.GROW)
        szr_report_config.Add(self.btn_report_path, 0, wx.LEFT|wx.RIGHT, 5)
        szr_report_config.Add(self.btn_view, 0, wx.LEFT|wx.RIGHT, 5)
        self.szr_config_top.Add(szr_report_config, 2, wx.RIGHT, 10)
        # Css
        bx_css_config = wx.StaticBox(panel, -1, _("Style output using ..."))
        szr_css_config = wx.StaticBoxSizer(bx_css_config, wx.HORIZONTAL)
        szr_css_config.Add(self.txt_css_file, 1, wx.GROW)
        szr_css_config.Add(self.btn_css_path, 0, wx.LEFT|wx.RIGHT, 5)
        self.szr_config_top.Add(szr_css_config, 1)
        # Variables
        bx_var_config = wx.StaticBox(panel, -1, _("Variable config from ..."))
        szr_var_config = wx.StaticBoxSizer(bx_var_config, wx.HORIZONTAL)
        szr_var_config.Add(self.txt_var_dets_file, 1, wx.GROW)
        szr_var_config.Add(self.btn_var_dets_path, 0, wx.LEFT|wx.RIGHT, 5)
        self.szr_config_bottom.Add(szr_var_config, 1, wx.RIGHT, 10)
        # Script
        bx_script_config = wx.StaticBox(panel, -1, _("Export here to reuse"))
        szr_script_config = wx.StaticBoxSizer(bx_script_config, wx.HORIZONTAL)
        szr_script_config.Add(self.txt_script_file, 1, wx.GROW)
        szr_script_config.Add(self.btn_script_path, 0, wx.LEFT|wx.RIGHT, 5)
        self.szr_config_bottom.Add(szr_script_config, 1)
        return self.szr_config_bottom, self.szr_config_top

    def get_szr_output_btns(self, panel, inc_clear=True):
        #main
        self.btn_run = wx.Button(panel, -1, run)
        self.btn_run.Bind(wx.EVT_BUTTON, self.on_btn_run)
        self.btn_run.SetToolTipString(_("Run report and display results"))
        self.chk_add_to_report = wx.CheckBox(panel, -1, add_to_report)
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
        self.szr_output_btns = wx.FlexGridSizer(rows=7, cols=1, hgap=5, vgap=5)
        self.szr_output_btns.AddGrowableRow(5,2) # idx, propn
        # only relevant if surrounding sizer stretched vertically enough by its 
        # content.
        self.szr_output_btns.Add(self.btn_run, 0)
        self.szr_output_btns.Add(self.chk_add_to_report)
        self.szr_output_btns.Add(self.btn_expand, wx.ALIGN_TOP)
        self.szr_output_btns.Add(self.btn_export, 0, wx.TOP, 8)
        self.szr_output_btns.Add(self.btn_help, 0)
        if inc_clear:
            self.szr_output_btns.Add(self.btn_clear, 0)
        self.szr_output_btns.Add(self.btn_close, 1, wx.ALIGN_BOTTOM)
        return self.szr_output_btns

    def reread_fil_var_dets(self):
        self.fil_var_dets = self.txt_var_dets_file.GetValue()
        
    def update_var_dets(self):
        "Update all variable details, including those already displayed"
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
                                            lib.get_var_dets(self.fil_var_dets)

    # database/ tables (and views)
    def on_database_sel(self, event):
        """
        Copes if have to back out of selection because cannot access required
            details e.g. MS SQL Server model database.
        """
        getdata.refresh_db_dets(self)
        
    def on_table_sel(self, event):
        "Reset key data details after table selection."       
        getdata.refresh_tbl_dets(self)

    def filt_select(self):
        import filtselect
        dlg = filtselect.FiltSelectDlg(self, self.var_labels, self.var_notes, 
                            self.var_types, self.val_dics, self.fil_var_dets)
        dlg.ShowModal()
        self.refresh_vars()

    def on_rclick_tables(self, event):
        "Allow addition or removal of data filter"
        self.filt_select()
        getdata.setup_drop_tbls(self.drop_tbls)
        #event.Skip() - don't use or will appear twice in Windows!
    # report output
    def on_btn_report_path(self, event):
        "Open dialog and takes the report file selected (if any)"
        dlg_get_file = wx.FileDialog(self, 
            _("Choose or create a report output file:"), 
            defaultDir=mg.REPORTS_PATH, defaultFile=u"", 
            wildcard=_("HTML files (*.htm)|*.htm|HTML files (*.html)|*.html"),
            style=wx.SAVE)
            #MUST have a parent to enforce modal in Windows
        if dlg_get_file.ShowModal() == wx.ID_OK:
            self.fil_report = u"%s" % dlg_get_file.GetPath()
            self.txt_report_file.SetValue(self.fil_report)
        dlg_get_file.Destroy()

    def on_btn_view(self, event):
        """
        Open report in user's default web browser.
        """
        debug = False
        if not os.path.exists(path=self.fil_report):
            wx.MessageBox(_("No output yet. Click \"%s\" (with \"%s\" ticked) "
                    "to add output to this report.") % (run, add_to_report))
        else:
            if mg.IN_WINDOWS:
                url = u"file:///%s" % self.fil_report
            else:
                url = u"file://%s" % self.fil_report
            if debug: print(url)            
            webbrowser.open_new_tab(url)
        event.Skip()

    def on_report_file_lost_focus(self, event):
        "Reset report output file"
        self.fil_report = self.txt_report_file.GetValue()
        event.Skip()
    
    # script output
    def on_btn_script_path(self, event):
        "Open dialog and takes the script file selected (if any)"
        dlg_get_file = wx.FileDialog(self, 
            _("Choose or create a file to export scripts to:"), 
            defaultDir=os.path.join(mg.LOCAL_PATH, "scripts"), 
            defaultFile="", wildcard=_("Scripts (*.py)|*.py"),
            style=wx.SAVE)
            #MUST have a parent to enforce modal in Windows
        if dlg_get_file.ShowModal() == wx.ID_OK:
            self.fil_script = u"%s" % dlg_get_file.GetPath()
            self.txt_script_file.SetValue(self.fil_script)
        dlg_get_file.Destroy()

    def on_script_file_lost_focus(self, event):
        "Reset script file"
        self.fil_script = self.txt_script_file.GetValue()
        event.Skip()
    
    # label config
    def on_var_dets_file_lost_focus(self, event):
        self.reread_fil_var_dets()
        self.update_var_dets()
        event.Skip()

    def on_btn_var_dets_path(self, event):
        "Open dialog and takes the variable details file selected (if any)"
        dlg_get_file = wx.FileDialog(self, 
            _("Choose an existing variable config file:"), 
            defaultDir=os.path.join(mg.LOCAL_PATH, u"vdts"), 
            defaultFile=u"", wildcard=_("Config files (*.vdts)|*.vdts"))
            #MUST have a parent to enforce modal in Windows
        if dlg_get_file.ShowModal() == wx.ID_OK:
            fil_var_dets = u"%s" % dlg_get_file.GetPath()
            self.txt_var_dets_file.SetValue(fil_var_dets)
            self.reread_fil_var_dets()
            self.update_var_dets()
        dlg_get_file.Destroy()        

    # css table style
    def on_btn_css_path(self, event):
        "Open dialog and takes the css file selected (if any)"
        dlg_get_file = wx.FileDialog(self, 
            _("Choose an existing css table style file:"), 
            defaultDir=os.path.join(mg.LOCAL_PATH, "css"), 
            defaultFile=u"", 
            wildcard=_("CSS files (*.css)|*.css"))
            #MUST have a parent to enforce modal in Windows
        if dlg_get_file.ShowModal() == wx.ID_OK:
            fil_css = u"%s" % dlg_get_file.GetPath()
            self.txt_css_file.SetValue(fil_css)
            self.update_css()
        dlg_get_file.Destroy()
    
    def update_css(self):
        "Update css, including for demo table"
        self.fil_css = self.txt_css_file.GetValue()
    
    def on_css_file_lost_focus(self, event):
        "Reset css file"
        self.update_css()
        event.Skip()
        
    # explanation level
    def get_szr_level(self, panel):
        """
        Get self.szr_level with radio widgets. 
        """
        szr_level = get_szr_level(self, panel)
        self.rad_level.Enable(False)
        return szr_level
    
    def on_btn_expand(self, event):
        output.display_report(self, self.str_content, self.url_load)
        event.Skip()

def add_icon(frame):
    ib = wx.IconBundle()
    icon_path = os.path.join(mg.SCRIPT_PATH, u"images", u"tinysofa.xpm")
    ib.AddIconFromFile(icon_path, wx.BITMAP_TYPE_XPM)
    frame.SetIcons(ib)