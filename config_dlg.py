#! /usr/bin/env python
# -*- coding: utf-8 -*-

import locale
import os
import wx

import my_globals as mg
import config_globals
import lib
import getdata
import output
#import filtselect # prevent circular import (inherits from Dlg not loaded yet)
import webbrowser

def get_cc():
    debug = False
    if not mg.CURRENT_CONFIG:
        proj_dic = config_globals.get_settings_dic(subfolder=mg.PROJS_FOLDER, 
                                                   fil_name=mg.DEFAULT_PROJ)
        mg.CURRENT_CONFIG = {mg.CURRENT_REPORT_PATH: proj_dic[mg.PROJ_FIL_RPT],
                         mg.CURRENT_CSS_PATH: proj_dic[mg.PROJ_FIL_CSS],
                         mg.CURRENT_VDTS_PATH: proj_dic[mg.PROJ_FIL_VDTS],
                         mg.CURRENT_SCRIPT_PATH: proj_dic[mg.PROJ_FIL_SCRIPT]}
        if debug: print("Updated mg.CURRENT_CONFIG")
    return mg.CURRENT_CONFIG

# explanation level
def get_szr_level(parent, panel, horiz=True):
    """
    Get self.szr_level with radio widgets. 
    """
    hv_style = wx.RA_SPECIFY_COLS if horiz else wx.RA_SPECIFY_ROWS
    parent.rad_level = wx.RadioBox(panel, -1, _("Output Level"), 
                                   choices=mg.LEVELS, style=hv_style)
    parent.rad_level.SetStringSelection(mg.DEFAULT_LEVEL)
    parent.szr_level = wx.BoxSizer(wx.HORIZONTAL)
    parent.szr_level.Add(parent.rad_level, 0, wx.RIGHT, 10)
    parent.rad_level.Enable(False)
    return parent.szr_level

label_divider = " " if mg.PLATFORM == mg.WINDOWS else "\n"
add_to_report = _("Add to%sreport") % label_divider
run = _("Show Results") if mg.PLATFORM == mg.MAC else _("Show\nResults")


def style2path(style):
    "Get full path of css file from style name alone"
    return os.path.join(mg.CSS_PATH, u"%s.css" % style)

def path2style(path):
    "Strip style out of full css path"
    style = path[len(mg.CSS_PATH)+1:-len(u".css")] # +1 to miss trailing slash
    if style == u"":
        raise Exception("Problem stripping style out of path (%s)" % path)
    return style


class ExtraOutputConfigDlg(wx.Dialog):
    def __init__(self, parent, readonly):
        debug = False
        cc = get_cc()
        wx.Dialog.__init__(self, parent=parent, 
                           title=_("Extra output settings"), 
                           style=wx.CAPTION|wx.SYSTEM_MENU, 
                           pos=(mg.HORIZ_OFFSET+100,100))
        self.parent = parent
        self.panel = wx.Panel(self)
        bx_var_config = wx.StaticBox(self.panel, -1, 
                                     _("Variable config from ... "))    
        self.txt_var_dets_file = wx.TextCtrl(self.panel, -1, 
                                        cc[mg.CURRENT_VDTS_PATH], size=(500,-1))
        self.txt_var_dets_file.Enable(not readonly)
        # Data config details
        browse = _("Browse")
        self.btn_var_dets_path = wx.Button(self.panel, -1, browse)
        self.btn_var_dets_path.Bind(wx.EVT_BUTTON, self.on_btn_var_dets_path)
        self.btn_var_dets_path.Enable(not readonly)
        self.btn_var_dets_path.SetToolTipString(_("Select an existing variable "
                                                  "config file"))
        if mg.ADVANCED: # add bx before controls in it
            bx_script_config = wx.StaticBox(self.panel, -1, 
                                            _("Export script here to reuse "))
            # script
            self.txt_script_file = wx.TextCtrl(self.panel, -1, 
                                          cc[mg.CURRENT_SCRIPT_PATH], 
                                          size=(500,-1))
            self.txt_script_file.Enable(False)
            self.btn_script_path = wx.Button(self.panel, -1, browse)
            self.btn_script_path.Bind(wx.EVT_BUTTON, self.on_btn_script_path)
            self.btn_script_path.Enable(False)   
            self.btn_script_path.SetToolTipString(_("Select or create a Python "
                                                    "script file"))
        szr_main = wx.BoxSizer(wx.VERTICAL)
        # Variables
        szr_var_config = wx.StaticBoxSizer(bx_var_config, wx.HORIZONTAL)
        szr_var_config.Add(self.txt_var_dets_file, 1, wx.GROW)
        szr_var_config.Add(self.btn_var_dets_path, 0, wx.LEFT|wx.RIGHT, 5)
        if mg.ADVANCED:
            # Script
            szr_script_config = wx.StaticBoxSizer(bx_script_config, 
                                                  wx.HORIZONTAL)
            szr_script_config.Add(self.txt_script_file, 1, wx.GROW)
            szr_script_config.Add(self.btn_script_path, 0, wx.LEFT|wx.RIGHT, 5)
        self.setup_btns()
        szr_main.Add(szr_var_config, 0, wx.GROW|wx.ALL, 10)
        if mg.ADVANCED:
            szr_main.Add(szr_script_config, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_btns_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        szr_btns_wrapper.Add(self.szr_btns, 1, wx.GROW|wx.ALL, 10)
        szr_main.Add(szr_btns_wrapper, 0, wx.GROW|wx.RIGHT, 10)
        self.panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()
        self.txt_var_dets_file.SetFocus()

    def setup_btns(self):
        """
        Must have ID of wx.ID_... to trigger validators (no event binding 
            needed) and for std dialog button layout.
        NB can only add some buttons as part of standard sizer to be realised.
        Insert or Add others after the Realize() as required.
        See http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3605904
        and http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3605432
        """
        btn_cancel = wx.Button(self.panel, wx.ID_CANCEL) # 
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        btn_ok = wx.Button(self.panel, wx.ID_OK, _("Apply"))
        btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        self.szr_btns = wx.StdDialogButtonSizer()
        # assemble
        self.szr_btns.AddButton(btn_cancel)
        self.szr_btns.AddButton(btn_ok)
        self.szr_btns.Realize()
        btn_ok.SetDefault()

    def on_cancel(self, event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL) # only for dialogs 
        # (MUST come after Destroy)

    def on_ok(self, event):
        debug = False
        cc = get_cc()
        cc[mg.CURRENT_VDTS_PATH] = self.txt_var_dets_file.GetValue()
        if mg.ADVANCED:
            cc[mg.CURRENT_SCRIPT_PATH] = self.txt_script_file.GetValue()
        self.parent.update_var_dets()
        self.Destroy()
        self.SetReturnCode(wx.ID_OK) # or nothing happens!  
        # Prebuilt dialogs must do this internally.

    def on_btn_var_dets_path(self, event):
        "Open dialog and takes the variable details file selected (if any)"
        dlg_get_file = wx.FileDialog(self, 
            _("Choose an existing variable config file:"), 
            defaultDir=os.path.join(mg.LOCAL_PATH, mg.VDTS_FOLDER), 
            defaultFile=u"", wildcard=_("Config files (*.vdts)|*.vdts"))
            # MUST have a parent to enforce modal in Windows
        if dlg_get_file.ShowModal() == wx.ID_OK:
            self.txt_var_dets_file.SetValue(dlg_get_file.GetPath())
        dlg_get_file.Destroy()
    
    def on_btn_script_path(self, event):
        "Open dialog and takes the script file selected (if any)"
        dlg_get_file = wx.FileDialog(self, 
            _("Choose or create a file to export scripts to:"), 
            defaultDir=os.path.join(mg.LOCAL_PATH, mg.SCRIPTS_FOLDER), 
            defaultFile="", wildcard=_("Scripts (*.py)|*.py"),
            style=wx.SAVE)
            # MUST have a parent to enforce modal in Windows
        if dlg_get_file.ShowModal() == wx.ID_OK:
            self.txt_script_file.SetValue(dlg_get_file.GetPath())
        dlg_get_file.Destroy()
                   

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
        Returns self.szr_data, self.szr_config (reports and css) complete with 
            widgets.  mg.DATA_DETS as dd is set up ready to use.
        Widgets include dropdowns for database and tables, and textboxes plus 
            Browse buttons for output and style.
        Each widget has a set of events ready to go as well.
        """
        self.szr_data = self.get_szr_data(panel)
        self.szr_config = self.get_config_szr(panel, readonly)
        return self.szr_data, self.szr_config
        
    def get_szr_data(self, panel):
        """
        Returns self.szr_data complete with widgets. dd is updated.
        Widgets include dropdowns for database and tables.
        Each widget has a set of events ready to go as well.
        Assumes self has quite a few properties already set.
        """
        bx_data = wx.StaticBox(panel, -1, _("Data Source"))
        self.LABEL_FONT = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        # 1) Databases
        lbl_databases = wx.StaticText(panel, -1, _("Database:"))
        lbl_databases.SetFont(self.LABEL_FONT)
        # get various db settings
        # set up self.drop_dbs and self.drop_tbls
        dd = getdata.get_dd()
        (self.drop_dbs, 
         self.drop_tbls) = getdata.get_data_dropdowns(self, panel, 
                                                      dd.default_dbs)
        # 2) Tables
        # not wanted in all cases when dropdowns used e.g. data select
        self.drop_tbls.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_tables)
        self.drop_tbls.SetToolTipString(_("Right click to add/remove filter"))
        lbl_tables = wx.StaticText(panel, -1, _("Table:"))
        lbl_tables.SetFont(self.LABEL_FONT)
        # 3) Readonly
        self.chk_readonly = wx.CheckBox(panel, -1, _("Read Only"))
        self.chk_readonly.SetValue(True)
        getdata.readonly_enablement(self.chk_readonly)
        # 4) Open
        self.btn_open = wx.Button(panel, wx.ID_OPEN)
        self.btn_open.Bind(wx.EVT_BUTTON, self.on_open)
        # 5) Filtering
        btn_filter = wx.Button(panel, -1, _("Filter"))
        btn_filter.Bind(wx.EVT_BUTTON, self.on_btn_filter)
        self.szr_data = wx.StaticBoxSizer(bx_data, wx.HORIZONTAL)
        self.szr_data.Add(lbl_databases, 0, wx.LEFT|wx.RIGHT, 5)
        self.szr_data.Add(self.drop_dbs, 0, wx.RIGHT, 10)
        self.szr_data.Add(lbl_tables, 0, wx.RIGHT, 5)
        self.szr_data.Add(self.drop_tbls, 0, wx.RIGHT, 10)
        self.szr_data.Add(self.chk_readonly, 0, wx.RIGHT, 10)
        self.szr_data.Add(self.btn_open, 0, wx.RIGHT, 10)
        self.szr_data.Add(btn_filter, 0)
        return self.szr_data
              
    def get_config_szr(self, panel, readonly=False):
        """
        Returns self.szr_config (reports and css) complete with widgets.
        Widgets include textboxes plus Browse buttons for output and style.
        Each widget has a set of events ready to go as well.
        """
        debug = False
        cc = get_cc()
        self.readonly = readonly
        browse = _("Browse")
        bx_report_config = wx.StaticBox(panel, -1, 
                                        _("Send output to report ... "))
        bx_css_config = wx.StaticBox(panel, -1, _("Style output using ... "))
        self.szr_config = wx.BoxSizer(wx.HORIZONTAL)
        # Style config details
        if debug: print(os.listdir(mg.CSS_PATH))
        style_choices = [x[:-len(".css")] for x in os.listdir(mg.CSS_PATH) 
                         if x.endswith(u".css")]
        style_choices.sort()
        self.drop_style = wx.Choice(panel, -1, choices=style_choices)
        idx_fil_css = style_choices.index(path2style(cc[mg.CURRENT_CSS_PATH]))
        self.drop_style.SetSelection(idx_fil_css)
        self.drop_style.Bind(wx.EVT_CHOICE, self.on_drop_style)
        self.drop_style.Enable(not self.readonly)
        self.drop_style.SetToolTipString(_("Select an existing css style file"))
        # Output details
        # report
        self.txt_report_file = wx.TextCtrl(panel, -1, 
                                    cc[mg.CURRENT_REPORT_PATH], size=(300,-1))
        self.txt_report_file.Bind(wx.EVT_KILL_FOCUS, 
                                self.on_report_file_lost_focus)
        self.txt_report_file.Enable(not self.readonly)
        self.btn_report_path = wx.Button(panel, -1, browse)
        self.btn_report_path.Bind(wx.EVT_BUTTON, self.on_btn_report_path)
        self.btn_report_path.Enable(not self.readonly)
        self.btn_report_path.SetToolTipString(_("Select or create an HTML "
                                                "output file"))
        self.btn_view = wx.Button(panel, -1, _("View"))
        self.btn_view.Bind(wx.EVT_BUTTON, self.on_btn_view)
        self.btn_view.Enable(not self.readonly)
        self.btn_view.SetToolTipString(_("View selected HTML output file in "
                                         "your default browser"))
        btn_config = wx.Button(panel, -1, _("Config"))
        btn_config.Bind(wx.EVT_BUTTON, self.on_btn_config)
        btn_config.Enable(not self.readonly)
        btn_config.SetToolTipString(_("Configure variable details file and "
                                      "script file"))
        # Report
        szr_report_config = wx.StaticBoxSizer(bx_report_config, wx.HORIZONTAL)
        szr_report_config.Add(self.txt_report_file, 1, wx.GROW)
        szr_report_config.Add(self.btn_report_path, 0, wx.LEFT|wx.RIGHT, 5)
        szr_report_config.Add(self.btn_view, 0, wx.LEFT|wx.RIGHT, 5)
        self.szr_config.Add(szr_report_config, 3, wx.RIGHT, 5)
        # Style
        szr_style_config = wx.StaticBoxSizer(bx_css_config, wx.HORIZONTAL)
        szr_style_config.Add(self.drop_style, 1, wx.GROW)
        self.szr_config.Add(szr_style_config, 1, wx.RIGHT, 5)
        config_down_by = 27 if mg.PLATFORM == mg.MAC else 17
        self.szr_config.Add(btn_config, 0, wx.TOP, config_down_by)
        return self.szr_config
    
    def update_var_dets(self):
        "Update all variable details, including those already displayed"
        cc = get_cc()
        (self.var_labels, self.var_notes, self.var_types, 
                     self.val_dics) = lib.get_var_dets(cc[mg.CURRENT_VDTS_PATH])
    
    def on_btn_config(self, event):
        dlg = ExtraOutputConfigDlg(parent=self, readonly=self.readonly)
        ret = dlg.ShowModal()
        dlg.Destroy()
        return ret

    def get_titles(self):
        """
        Get titles list and subtitles list from GUI.
        """
        debug = False
        raw_titles = self.txt_titles.GetValue()
        if raw_titles:
            titles = [u"%s" % x for x in raw_titles.split(u"\n")]
        else:
            titles = []
        raw_subtitles = self.txt_subtitles.GetValue()
        if raw_subtitles:
            subtitles = [u"%s" % x for x in raw_subtitles.split(u"\n")]
        else:
            subtitles = []
        if debug: print("%s %s" % (titles, subtitles))
        return titles, subtitles
    
    def too_long(self):
        dd = getdata.get_dd()
        # check not a massive table
        too_long = False
        # count records in table
        unused, tbl_filt = lib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
        where_tbl_filt, unused = lib.get_tbl_filts(tbl_filt)
        SQL_get_count = u"SELECT COUNT(*) FROM %s %s" % \
                          (getdata.tblname_qtr(dd.dbe, dd.tbl), where_tbl_filt)
        dd.cur.execute(SQL_get_count)
        rows_n = dd.cur.fetchone()[0]
        if rows_n > 250000:
            strn = locale.format('%d', rows_n, True)
            if wx.MessageBox(_("The underlying data table has %s rows. "
                               "Do you wish to run this analysis?") % strn, 
                               caption=_("LARGE DATA TABLE"), 
                               style=wx.YES_NO) == wx.NO:
                too_long = True
        return too_long

    def get_szr_output_btns(self, panel, inc_clear=True):
        # main
        self.btn_run = wx.Button(panel, -1, run)
        self.btn_run.Bind(wx.EVT_BUTTON, self.on_btn_run)
        self.btn_run.SetToolTipString(_("Run report and display results"))
        self.chk_add_to_report = wx.CheckBox(panel, -1, add_to_report)
        self.chk_add_to_report.SetValue(True)
        if mg.ADVANCED:
            self.btn_script = wx.Button(panel, -1, _("To Script"))
            self.btn_script.Bind(wx.EVT_BUTTON, self.on_btn_script)
            self.btn_script.SetToolTipString(_("Export to script for reuse"))
            self.btn_script.Enable(False)
        self.btn_expand = wx.Button(panel, -1, _("Expand"))
        self.btn_expand.Bind(wx.EVT_BUTTON, self.on_btn_expand)
        self.btn_expand.SetToolTipString(_("Open report in own window"))
        self.btn_expand.Enable(False)
        if inc_clear:
            self.btn_clear = wx.Button(panel, -1, _("Clear"))
            self.btn_clear.SetToolTipString(_("Clear settings"))
            self.btn_clear.Bind(wx.EVT_BUTTON, self.on_btn_clear)
        self.btn_close = wx.Button(panel, wx.ID_CLOSE)
        self.btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        # add to sizer
        self.szr_output_btns = wx.FlexGridSizer(rows=7, cols=1, hgap=5, vgap=5)
        self.szr_output_btns.AddGrowableRow(3,2) # idx, propn
        self.szr_output_btns.AddGrowableCol(0,1) # idx, propn
        # only relevant if surrounding sizer stretched vertically enough by its 
        # content.
        self.szr_output_btns.Add(self.btn_run, 1, wx.ALIGN_RIGHT)
        self.szr_output_btns.Add(self.chk_add_to_report, 1, wx.ALIGN_RIGHT)
        self.szr_output_btns.Add(self.btn_expand, 1, 
                                 wx.ALIGN_RIGHT|wx.ALIGN_TOP)
        if mg.ADVANCED:
            self.szr_output_btns.Add(self.btn_script, 1, 
                                     wx.ALIGN_RIGHT|wx.TOP, 8)
        if inc_clear:
            self.szr_output_btns.Add(self.btn_clear, 1, wx.ALIGN_RIGHT)
        close_up_by = 13 if mg.PLATFORM == mg.MAC else 5
        self.szr_output_btns.Add(self.btn_close, 1, 
                                 wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM|wx.BOTTOM, 
                                 close_up_by)
        return self.szr_output_btns

    # database/ tables (and views)
    def on_database_sel(self, event):
        """
        Copes if have to back out of selection because cannot access required
            details e.g. MS SQL Server model database.
        """
        getdata.refresh_db_dets(self)
        getdata.readonly_enablement(self.chk_readonly)
        
    def on_table_sel(self, event):
        "Reset key data details after table selection."       
        getdata.refresh_tbl_dets(self)
        getdata.readonly_enablement(self.chk_readonly)

    def filters(self):
        import filtselect # by now, DLG will be available to inherit from
        dlg = filtselect.FiltSelectDlg(self, self.var_labels, self.var_notes, 
                                       self.var_types, self.val_dics)
        dlg.ShowModal()
        self.refresh_vars()
        getdata.setup_drop_tbls(self.drop_tbls)
        lib.safe_end_cursor()

    def on_rclick_tables(self, event):
        "Allow addition or removal of data filter"
        self.filters()
        # event.Skip() - don't use or will appear twice in Windows!

    def on_btn_filter(self, event):
        self.filters()
        
    def on_open(self, event):
        getdata.open_database(self, event)
        
    # report output
    def on_btn_report_path(self, event):
        "Open dialog and takes the report file selected (if any)"
        cc = get_cc()
        dlg_get_file = wx.FileDialog(self, 
            _("Choose or create a report output file:"), 
            defaultDir=mg.REPORTS_PATH, defaultFile=u"", 
            wildcard=_("HTML files (*.htm)|*.htm|HTML files (*.html)|*.html"),
            style=wx.SAVE)
            # MUST have a parent to enforce modal in Windows
        if dlg_get_file.ShowModal() == wx.ID_OK:
            new_rpt_pth = u"%s" % dlg_get_file.GetPath()
            new_rpt = os.path.split(new_rpt_pth)[1]
            cc[mg.CURRENT_REPORT_PATH] = new_rpt_pth
            self.txt_report_file.SetValue(new_rpt_pth)
            wx.MessageBox(_(u"Please note that any SOFA Charts you add "
                u"to \"%(new_rpt)s\" won't display unless the "
                u"\"%(report_extras_folder)s\" subfolder is in the same folder "
                u"as you open \"%(new_rpt)s\" from.") % 
                {u"report_extras_folder": mg.REPORT_EXTRAS_FOLDER, 
                 u"new_rpt": new_rpt})
        dlg_get_file.Destroy()

    def on_btn_run(self, event, OUTPUT_MODULES, get_script_args, 
                   new_has_dojo=False):
        debug = False
        cc = get_cc()
        if self.too_long():
            return
        wx.BeginBusyCursor()
        add_to_report = self.chk_add_to_report.IsChecked()
        if debug: print(cc[mg.CURRENT_CSS_PATH])
        try:
            css_fils, css_idx = output.get_css_dets()
        except my_exceptions.MissingCssException, e:
            lib.update_local_display(self.html, _("Please check the CSS "
                                    "file exists or set another. "
                                    "Caused by error: %s") % lib.ue(e), 
                                    wrap_text=True)
            lib.safe_end_cursor()
            event.Skip()
            return
        try:
            script = self.get_script(css_idx, *get_script_args)
        except Exception, e:
            raise Exception("Problem getting script. Orig error: %s" % 
                            lib.ue(e))
        bolran_report, str_content = output.run_report(OUTPUT_MODULES, 
                                                       add_to_report, css_fils, 
                                                       new_has_dojo, script)
        if debug: print(str_content)
        lib.update_local_display(self.html, str_content)
        self.str_content = str_content
        self.btn_expand.Enable(bolran_report)
        lib.safe_end_cursor()
        event.Skip()
        
    def on_btn_view(self, event):
        """
        Open report in user's default web browser.
        """
        debug = False
        cc = get_cc()
        if not os.path.exists(path=cc[mg.CURRENT_REPORT_PATH]):
            try:
                self.can_run_report
            except AttributeError:
                self.can_run_report = True
            if self.can_run_report:
                msg = _("No output yet. Click \"%(run)s\" (with "
                        "\"%(add_to_report)s\" ticked) to add output to this "
                        "report.") % {u"run": run, 
                                      u"add_to_report": add_to_report}
            else:
                msg = _("The output file has not been created yet.  Nothing to "
                        "view")
            wx.MessageBox(msg)
        else:
            if mg.PLATFORM == mg.WINDOWS:
                url = u"file:///%s" % cc[mg.CURRENT_REPORT_PATH]
            else:
                url = u"file://%s" % cc[mg.CURRENT_REPORT_PATH]
            if debug: print(url)            
            webbrowser.open_new_tab(url)
        event.Skip()

    def on_report_file_lost_focus(self, event):
        "Reset report output file"
        cc = get_cc()
        cc[mg.CURRENT_REPORT_PATH] = self.txt_report_file.GetValue()
        event.Skip()
    
    # table style
    def on_drop_style(self, event):
        "Change style"
        self.update_css()
    
    def update_css(self):
        "Update css, including for demo table"
        cc = get_cc()
        cc[mg.CURRENT_CSS_PATH] = \
            style2path(self.drop_style.GetStringSelection())
        
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
    