#! /usr/bin/env python
# -*- coding: utf-8 -*-

import locale
import os
import wx

import basic_lib as b
import my_globals as mg
import my_exceptions
import lib
try:
    import export_output as export
except ImportError, e:
    print(u"Problem with export_output. Orig error: %s" % b.ue(e))
import db_grid
import getdata
import output
import showhtml
#import projects
import traceback
#import filtselect # prevent circular import (inherits from Dlg not loaded yet)
import webbrowser

"Import hyperlink"
try:
    from agw import hyperlink as hl
except ImportError: # if it's not there locally, try the wxPython lib.
    try:
        import wx.lib.agw.hyperlink as hl
    except ImportError:
        msg = (u"There seems to be a problem related to your wxPython "
            u"package. %s" % traceback.format_exc())
        raise Exception(msg)

debug = False
PRETEND_IS_MAC = debug
IS_MAC = ((mg.PLATFORM != mg.MAC) if PRETEND_IS_MAC 
    else (mg.PLATFORM == mg.MAC))

label_divider = " " if mg.PLATFORM == mg.WINDOWS else "\n"
ADD2_RPT_LBL = _("Also add%sto report") % label_divider
RUN_LBL = _("Show Results")
NO_OUTPUT_YET_MSG = (_(u"No output yet. Click \"%(run)s\" (with "
    u"\"%(add2rpt_lbl)s\" ticked) to add output to this report.") % 
    {u"run": RUN_LBL, u"add2rpt_lbl": ADD2_RPT_LBL}).replace(u"\n", u" ")
ADD_EXPECTED_SUBFOLDER_MSG = _(u"You need to add the "
    u"\"%(report_extras_folder)s\" subfolder into the \"%(rpt_root)s\" folder "
    u"so your charts and themes can display properly.\n\nCopy the "
    u"\"%(report_extras_folder)s\" folder from \"%(reports_path)s\".")


class DlgGetTest(wx.Dialog):
    
    def __init__(self, title, label):
        wx.Dialog.__init__(self, parent=None, id=-1, title=title, 
            pos=(mg.HORIZ_OFFSET+200, 300))
        #, style=wx.CLOSE_BOX|wx.SYSTEM_MENU|wx.CAPTION|
        #                   wx.CLIP_CHILDREN)
        szr = wx.BoxSizer(wx.VERTICAL)
        lbl_msg1 = wx.StaticText(self, -1, u"%s extension under "
            u"construction. Free test version" % label)
        lbl_msg2 = wx.StaticText(self, -1, u"available for a limited time from "
            u"%s" % mg.CONTACT)
        subject = output.percent_encode("Please send free %s extension" % label)
        link_home = hl.HyperLinkCtrl(self, -1, "Email Grant for test extension", 
            URL=u"mailto:grant@sofastatistics.com?subject=%s" % subject)
        lib.setup_link(link=link_home, link_colour="black", 
            bg_colour=wx.NullColour)
        btn_ok = wx.Button(self, wx.ID_OK) # autobound to close event by id
        szr.Add(lbl_msg1, 0, wx.TOP|wx.LEFT|wx.RIGHT, 10)
        szr.Add(lbl_msg2, 0, wx.LEFT|wx.RIGHT, 10)
        szr.Add(link_home, 0, wx.ALL, 10)
        szr.Add(btn_ok, 0, wx.ALL, 10)
        self.SetSizer(szr)
        szr.SetSizeHints(self)
        szr.Layout()

def style2path(style):
    "Get full path of css file from style name alone"
    return os.path.join(mg.CSS_PATH, u"%s.css" % style)

def path2style(path):
    "Strip style out of full css path"
    debug = False
    if debug: print(u"path: %s" % path)
    style = path[len(mg.CSS_PATH)+1:-len(u".css")] # +1 to miss trailing slash
    if style == u"":
        raise Exception("Problem stripping style out of path (%s)" % path)
    return style
    

class DlgVarConfig(wx.Dialog):
    """
    Shouldn't set variable details globally - it may not be appropriate to 
        autoupdate. Leave that for the parent dialog this returns to.
    """
    def __init__(self, parent, readonly, ret_dic, vdt_file=None):
        cc = output.get_cc()
        wx.Dialog.__init__(self, parent=parent, title=_(u"Select variable "
            u"details file with labels etc appropriate to your data"), 
            style=wx.CAPTION|wx.SYSTEM_MENU, pos=(mg.HORIZ_OFFSET+100,100))
        self.parent = parent
        self.panel = wx.Panel(self)
        self.ret_dic = ret_dic
        bx_var_config = wx.StaticBox(self.panel, -1, 
            _("Variable config from ... "))
        self.initial_vdt = (vdt_file if vdt_file else cc[mg.CURRENT_VDTS_PATH])
        self.txt_var_dets_file = wx.TextCtrl(self.panel, -1, self.initial_vdt, 
            size=(500,-1))
        self.txt_var_dets_file.Enable(not readonly)
        # Data config details
        browse = _("Browse")
        self.btn_var_dets_path = wx.Button(self.panel, -1, browse)
        self.btn_var_dets_path.Bind(wx.EVT_BUTTON, self.on_btn_var_dets_path)
        self.btn_var_dets_path.Enable(not readonly)
        self.btn_var_dets_path.SetToolTipString(_("Select an existing variable "
            "config file"))
        szr_main = wx.BoxSizer(wx.VERTICAL)
        # Variables
        szr_var_config = wx.StaticBoxSizer(bx_var_config, wx.HORIZONTAL)
        szr_var_config.Add(self.txt_var_dets_file, 1, wx.GROW)
        szr_var_config.Add(self.btn_var_dets_path, 0, wx.LEFT|wx.RIGHT, 5)
        self.setup_btns()
        szr_main.Add(szr_var_config, 0, wx.GROW|wx.ALL, 10)
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
        """
        If file doesn't exist, check if folder exists. If so, make file with 
            required vdt variables initialised. If not, advise user that folder 
            doesn't exist.
        If file exists, check it is a valid vdt file.
        Best to prevent storing an invalid vdt file in a project rather than 
            just catching once selected.
        Still have to handle it if corrupted after being set as part of a 
            project - just work with empty dicts for variable details until 
            overwritten as part of any update. Will effectively wipe a faulty 
            vdt except for the new item being added. Looks at everything stored 
            (nothing ;-) plus new item) and stores that.
        """
        entered_vdt_path = self.txt_var_dets_file.GetValue()
        file_exists = os.path.exists(entered_vdt_path)
        if file_exists: # exists but is it valid?
            invalid_msg = lib.get_invalid_var_dets_msg(entered_vdt_path)
            if not invalid_msg:
                self.ret_dic[mg.VDT_RET] = entered_vdt_path
            else:
                wx.MessageBox(_(u"Unable to use vdt file \"%(entered_vdt_path)s"
                    u"\" entered. Orig error: %(invalid_msg)s") % 
                    {u"entered_vdt_path": entered_vdt_path, 
                    u"invalid_msg": invalid_msg})
                self.ret_dic[mg.VDT_RET] = self.initial_vdt
        else:
            foldername, filename = os.path.split(entered_vdt_path)
            folder_exists = os.path.exists(foldername)
            if folder_exists:
                with open(entered_vdt_path, "w") as f:
                    f.write(u"var_labels={}\nvar_notes={}\nvar_types={}"
                        u"\nval_dics={}")
                    f.close()
                self.ret_dic[mg.VDT_RET] = entered_vdt_path
            else:
                wx.MessageBox(_(u"Unable to make vdt file \"%(filename)s\" - "
                    u"the \"%(foldername)s\" directory doesn't exist.") % 
                    {u"filename": filename, u"foldername": foldername})
                self.ret_dic[mg.VDT_RET] = self.initial_vdt
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
       

class ConfigUI(object):
    """
    The standard interface for choosing data, styles etc.
    Can get sizers ready to use complete with widgets, event methods, and even
        properties e.g. dd.con, dd.cur etc.
    Used mixin because of large number of properties set and needing to be 
        shared. The downside is that not always clear where something got set
        when looking from the class that inherits from this mixin.
    """
    
    def __init__(self, autoupdate):
        """
        This interface is used in two cases - where we want changes to be 
            automatically shared across all subsequent operations e.g. selecting 
            a different style; and where we don't e.g. when modifying a project 
            file. In the latter case, we only want changes to become global when 
            a project is selected, not while configuring a project. We might 
            modify a project but not select it e.g. cancel on projselect stage. 
            Use self.autoupdate as determinant.
        """
        debug = False
        if debug: print("autoupdate got set")
        self.autoupdate = autoupdate
        # init
        self.vdt_file = None
        self.script_file = None
        self.rows_n = self.get_rows_n()
        self.export_output_enabled = False
        self.copy_output_enabled = False

    def get_gen_config_szrs(self, panel, readonly=False, hide_db=True):
        """
        Returns self.szr_data, self.szr_output_config (reports and css) complete 
            with widgets.  mg.DATADETS_OBJ as dd is set up ready to use.
        Widgets include dropdowns for database and tables, and textboxes plus 
            Browse buttons for output and style.
        Each widget has a set of events ready to go as well.
        """
        self.szr_data = self.get_szr_data(panel, readonly, hide_db)
        self.szr_output_config = self.get_szr_output_config(panel, readonly)
        return self.szr_data, self.szr_output_config
        
    def get_szr_data(self, panel, readonly=False, hide_db=True):
        """
        Returns self.szr_data complete with widgets. dd is updated.
        Widgets include dropdowns for database and tables.
        Each widget has a set of events ready to go as well.
        Assumes self has quite a few properties already set.
        """
        self.readonly = readonly
        try:
            self.drop_tbls_sel_evt
        except AttributeError:
            raise Exception(u"Must define self.drop_tbls_sel_evt first")
        bx_data = wx.StaticBox(panel, -1, _("Data Source"))
        # 1) Databases
        lbl_databases = wx.StaticText(panel, -1, _("Database:"))
        lbl_databases.SetFont(mg.LABEL_FONT)
        # get various db settings
        # set up self.drop_dbs and self.drop_tbls
        dd = mg.DATADETS_OBJ
        (self.drop_dbs, self.drop_tbls, 
         self.db_choice_items, 
         self.selected_dbe_db_idx) = getdata.get_data_dropdowns(self, panel, 
            dd.default_dbs)
        # 2) Tables
        # not wanted in all cases when dropdowns used e.g. data select
        self.drop_tbls.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_tables)
        self.drop_tbls.SetToolTipString(_("Right click to add/remove filter"))
        lbl_tables = wx.StaticText(panel, -1, _("Table:"))
        lbl_tables.SetFont(mg.LABEL_FONT)
        # 3) Readonly
        self.chk_readonly = wx.CheckBox(panel, -1, _("Read Only"))
        self.chk_readonly.SetFont(mg.GEN_FONT)
        self.chk_readonly.SetValue(True)
        getdata.readonly_enablement(self.chk_readonly)
        # 4) Open
        btn_size = (70,-1)
        self.btn_open = wx.Button(panel, wx.ID_OPEN, size=btn_size)
        self.btn_open.SetFont(mg.BTN_FONT)
        self.btn_open.Bind(wx.EVT_BUTTON, self.on_open)
        # 5) Filtering
        btn_filter = wx.Button(panel, -1, _("Filter"), size=btn_size)
        btn_filter.SetFont(mg.BTN_FONT)
        btn_filter.Bind(wx.EVT_BUTTON, self.on_btn_filter)
        btn_var_config = self.get_btn_var_config(panel) # also needed by projects but not as part of bundle
        self.szr_data = wx.StaticBoxSizer(bx_data, wx.HORIZONTAL)
        if not hide_db:
            self.szr_data.Add(lbl_databases, 0, wx.LEFT|wx.RIGHT, 5)
            self.szr_data.Add(self.drop_dbs, 0, wx.RIGHT, 10)
            self.szr_data.Add(lbl_tables, 0, wx.RIGHT, 5)
        else:
            lbl_databases.Hide()
            self.drop_dbs.Hide()
            self.szr_data.Add(lbl_tables, 0, wx.LEFT|wx.RIGHT, 5)
        self.szr_data.Add(self.drop_tbls, 0, wx.RIGHT, 10)
        self.szr_data.Add(self.chk_readonly, 0, wx.RIGHT, 10)
        self.szr_data.Add(self.btn_open, 0, wx.RIGHT, 10)
        self.szr_data.Add(btn_filter, 0, wx.RIGHT, 10)
        self.szr_data.Add(btn_var_config, 0)
        return self.szr_data

    def get_szr_output_config(self, panel, readonly=False, report_file=None,
            show_run_btn=True, show_add_btn=True, show_view_btn=True, 
            show_export_options=True):
        """
        Returns self.szr_output_config (reports and css) complete with widgets.
        Widgets include textboxes plus Browse buttons for output and style.
        Each widget has a set of events ready to go as well.
        Sets defaults to current stored values in global cc.
        report_file -- usually just want what is stored to global but when in 
            project dialog need to have option of taking from proj file.
        """
        self.panel_with_add2report = panel
        cc = output.get_cc()
        bx_report_config = wx.StaticBox(panel, -1, _("Output"))
        if show_run_btn:
            self.btn_run = wx.Button(panel, -1, RUN_LBL, size=(170,-1))
            self.btn_run.SetFont(mg.BTN_FONT)
            self.btn_run.Bind(wx.EVT_BUTTON, self.on_btn_run)
            self.btn_run.SetToolTipString(_("Run report and show results"))
        if show_add_btn:
            self.chk_add_to_report = wx.CheckBox(panel, -1, ADD2_RPT_LBL)
            self.chk_add_to_report.SetFont(mg.GEN_FONT)
            self.chk_add_to_report.SetValue(mg.ADD2RPT)
            self.chk_add_to_report.Bind(wx.EVT_CHECKBOX, 
                self.on_chk_add_to_report)
        self.readonly = readonly
        browse = _("Browse")
        if not report_file:
            report_file = cc[mg.CURRENT_REPORT_PATH]
        szr_html_report = wx.BoxSizer(wx.HORIZONTAL)
        szr_html_report_left = wx.BoxSizer(wx.VERTICAL)
        self.txt_report_file = wx.TextCtrl(panel, -1, report_file, 
            size=(300,-1))
        self.txt_report_file.SetFont(mg.GEN_FONT)
        self.txt_report_file.Bind(wx.EVT_KILL_FOCUS, 
            self.on_report_file_lost_focus)
        self.txt_report_file.Enable(not self.readonly)
        self.btn_report_path = wx.Button(panel, -1, browse)
        self.btn_report_path.SetFont(mg.BTN_FONT)
        self.btn_report_path.Bind(wx.EVT_BUTTON, self.on_btn_report_path)
        self.btn_report_path.Enable(not self.readonly)
        self.btn_report_path.SetToolTipString(_("Select or create an HTML "
            "output file"))
        if show_view_btn:
            self.btn_view = wx.Button(panel, -1, _("View Report"), size=(-1,25))
            self.btn_view.SetFont(mg.BTN_FONT)
            self.btn_view.Bind(wx.EVT_BUTTON, self.on_btn_view)
            self.btn_view.Enable(not self.readonly)
            self.btn_view.SetToolTipString(_("View selected HTML output file "
                "in your default browser"))
        szr_output_config = wx.StaticBoxSizer(bx_report_config, wx.HORIZONTAL)
        if show_run_btn:
            szr_output_config.Add(self.btn_run, 0, wx.GROW)
        if show_add_btn:
            szr_output_config.Add(self.chk_add_to_report, 0, 
                wx.LEFT|wx.RIGHT, 10)
        szr_html_report_left.Add(self.txt_report_file, 0, wx.GROW)
        if show_view_btn:
            szr_html_report_left.Add(self.btn_view, 0, wx.ALIGN_RIGHT)
        szr_html_report.Add(szr_html_report_left, 1)
        szr_html_report.Add(self.btn_report_path, 0, wx.LEFT|wx.RIGHT, 5)
        szr_output_config.Add(szr_html_report, 3)
        if show_export_options:
            export_choice_items = [
                _("Current Output"), 
                _("Copy current output ready to paste"),
                _("Entire Report"), 
            ]
            self.drop_export = wx.Choice(panel, -1, choices=export_choice_items)
            self.drop_export.Enable(not self.readonly)
            self.drop_export.SetToolTipString(_(u"Export report as PDF, images,"
                u" or to spreadsheet ready for reports, slideshows etc"))
            self.drop_export.SetSelection(0)
            lbl_export = wx.StaticText(panel, -1, _("Export:"))
            lbl_export.SetFont(mg.LABEL_FONT)
            vln = wx.StaticLine(panel, -1, style=wx.LI_VERTICAL)
            vln.SetSize((30,30))
            szr_export = wx.BoxSizer(wx.VERTICAL)
            szr_export_upper = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_export = wx.Button(panel, -1, _("Export"), size=(-1,25))
            self.btn_export.SetFont(mg.BTN_FONT)
            self.btn_export.Bind(wx.EVT_BUTTON, self.on_btn_export)
            self.btn_export.SetToolTipString(_("Export output as per selection"))
            szr_output_config.Add(vln, 0, wx.GROW)
            szr_export_upper.Add(lbl_export, 0, wx.TOP|wx.LEFT, 5)
            szr_export_upper.Add(self.drop_export, 0, wx.LEFT, 5)
            szr_export.Add(szr_export_upper, 0, wx.GROW)
            szr_export.Add(self.btn_export, 0, wx.ALIGN_RIGHT)
            szr_output_config.Add(szr_export, 0)
        return szr_output_config

    def get_szr_output_display(self, panel, inc_clear=True, idx_style=2):
        # main
        self.style_selector = self.get_style_selector(panel)
        self.btn_expand = wx.Button(panel, -1, _("Expand"))
        self.btn_expand.SetFont(mg.BTN_FONT)
        self.btn_expand.Bind(wx.EVT_BUTTON, self.on_btn_expand)
        self.btn_expand.SetToolTipString(_(u"Open displayed output in own "
            u"window"))
        self.btn_expand.Enable(False)
        if inc_clear:
            self.btn_clear = wx.Button(panel, -1, _("Clear"))
            self.btn_clear.SetFont(mg.BTN_FONT)
            self.btn_clear.SetToolTipString(_("Clear settings"))
            self.btn_clear.Bind(wx.EVT_BUTTON, self.on_btn_clear)
        self.btn_close = wx.Button(panel, wx.ID_CLOSE)
        self.btn_close.SetFont(mg.BTN_FONT)
        self.btn_close.Bind(wx.EVT_BUTTON, self.on_btn_close)
        # add to sizer
        szr_output_display = wx.FlexGridSizer(rows=4, cols=1, hgap=5, vgap=5)
        szr_output_display.AddGrowableRow(idx_style,2) # idx, propn
        szr_output_display.AddGrowableCol(0,1) # idx, propn
        # only relevant if surrounding sizer stretched vertically enough by its 
        # content.
        szr_output_display.Add(self.btn_expand, 0, wx.GROW|wx.ALIGN_RIGHT|
            wx.ALIGN_TOP)
        if inc_clear:
            szr_output_display.Add(self.btn_clear, 0, wx.GROW|wx.ALIGN_RIGHT)
        szr_output_display.Add(self.style_selector, 1, wx.GROW|wx.BOTTOM, 5)
        # close
        szr_output_display.Add(self.btn_close, 0, wx.GROW|wx.ALIGN_RIGHT)
        return szr_output_display

    def get_style_selector(self, panel, as_list=True, css_file=None):
        debug = False
        cc = output.get_cc()
        # style config details
        if debug: print(os.listdir(mg.CSS_PATH))
        style_choices = [x[:-len(".css")] for x in os.listdir(mg.CSS_PATH) 
            if x.endswith(u".css")]
        style_choices.sort()
        if as_list:
            style_selector = wx.ListBox(panel, -1, choices=style_choices, 
                size=(120,-1))
            style_selector.Bind(wx.EVT_LISTBOX, self.on_style_sel)
        else:
            style_selector = wx.Choice(panel, -1, choices=style_choices)
            style_selector.Bind(wx.EVT_CHOICE, self.on_style_sel)
        style_selector.SetFont(mg.GEN_FONT)
        style = (path2style(css_file) if css_file 
            else path2style(cc[mg.CURRENT_CSS_PATH]))
        idx_fil_css = style_choices.index(style)
        style_selector.SetSelection(idx_fil_css)
        style_selector.Enable(not self.readonly)
        style_selector.SetToolTipString(_("Select an existing css style file"))
        return style_selector
    
    def get_btn_var_config(self, panel):
        btn_var_config = wx.Button(panel, -1, _("Config Vars"))
        btn_var_config.SetFont(mg.BTN_FONT)
        btn_var_config.Bind(wx.EVT_BUTTON, self.on_btn_var_config)
        btn_var_config.Enable(not self.readonly)
        btn_var_config.SetToolTipString(_(u"Configure variable details e.g. "
            u"labels"))
        return btn_var_config
    
    def set_extra_dets(self, vdt_file, script_file):          
        self.vdt_file = vdt_file
        self.script_file = script_file
        
    def on_btn_var_config(self, event):
        """
        Return the settings selected
        """
        cc = output.get_cc()
        ret_dic = {}
        dlg = DlgVarConfig(self, self.readonly, ret_dic, self.vdt_file)
        ret = dlg.ShowModal()
        if ret == wx.ID_OK and self.autoupdate:
            cc[mg.CURRENT_VDTS_PATH] = ret_dic[mg.VDT_RET] # main place this gets set
            output.update_var_dets(dlg=self)
        dlg.Destroy()
        return ret_dic

    def on_chk_add_to_report(self, event):
        try:
            mg.ADD2RPT = self.chk_add_to_report.IsChecked()
        except Exception:
            pass

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
    
    def get_rows_n(self):
        debug = False
        dd = mg.DATADETS_OBJ
        # count records in table
        unused, tbl_filt = lib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
        where_tbl_filt, unused = lib.get_tbl_filts(tbl_filt)
        tblname = getdata.tblname_qtr(dd.dbe, dd.tbl)
        s = u"SELECT COUNT(*) FROM %s %s" % (tblname, where_tbl_filt)
        try:
            dd.cur.execute(s)
            rows_n = dd.cur.fetchone()[0]
        except Exception, e:
            if debug: print(u"Unable to count rows. Orig error: %s" % b.ue(e))
            rows_n = 0
        return rows_n
    
    def too_long(self):
        # check not a massive table
        too_long = False
        rows_n = self.get_rows_n()
        if rows_n > 250000:
            strn = locale.format('%d', rows_n, True)
            if wx.MessageBox(_("The underlying data table has %s rows. "
                    "Do you wish to run this analysis?") % strn,
                    caption=_("LARGE DATA TABLE"), style=wx.YES_NO) == wx.NO:
                too_long = True
        return too_long

    # database/ tables (and views)
    def on_database_sel(self, event):
        """
        Copes if have to back out of selection because cannot access required
            details e.g. MS SQL Server model database.
        Return False if no change made so no updating etc required.
        """
        debug = False
        if debug: print(u"on_database_sel called")
        if getdata.refresh_db_dets(self):
            getdata.readonly_enablement(self.chk_readonly)
            self.rows_n = self.get_rows_n()
            return True
        return False
        
    def on_table_sel(self, event):
        "Reset key data details after table selection."  
        debug = False
        if debug: print(u"on_table_sel called")     
        getdata.refresh_tbl_dets(self)
        getdata.readonly_enablement(self.chk_readonly)
        self.rows_n = self.get_rows_n()

    def filters(self):
        import filtselect # by now, DLG will be available to inherit from
        parent = self
        dlg = filtselect.DlgFiltSelect(parent, self.var_labels, self.var_notes, 
            self.var_types, self.val_dics)
        retval = dlg.ShowModal()
        if retval != wx.ID_CANCEL:
            self.refresh_vars()
            parent.drop_tbls = getdata.get_fresh_drop_tbls(parent, 
                parent.drop_tbls_szr, parent.drop_tbls_panel)
        lib.safe_end_cursor()

    def on_rclick_tables(self, event):
        "Allow addition or removal of data filter"
        self.filters()
        # event.Skip() - don't use or will appear twice in Windows!

    def on_btn_filter(self, event):
        self.filters()
        
    def on_open(self, event):
        db_grid.open_database(self, event)
    
    def has_expected_subfolder(self, rpt_root):
        # see if has js support etc in subfolder
        expected_subfolder = os.path.join(rpt_root, mg.REPORT_EXTRAS_FOLDER)
        return os.path.exists(expected_subfolder)
    
    # report output
    def on_btn_report_path(self, event):
        "Open dialog and takes the report file selected (if any)"
        cc = output.get_cc()
        dlg_get_file = wx.FileDialog(self, 
            _("Choose or create a report output file:"), 
            defaultDir=mg.REPORTS_PATH, defaultFile=u"", 
            wildcard=_(u"HTML files (*.htm)|*.htm|HTML files (*.html)|*.html"),
            style=wx.SAVE)
            # MUST have a parent to enforce modal in Windows
        if dlg_get_file.ShowModal() == wx.ID_OK:
            # not necessary that the report exists, only that its folder is already there
            new_rpt_pth = u"%s" % dlg_get_file.GetPath()
            new_rpt_root, new_rpt = os.path.split(new_rpt_pth) #@UnusedVariable
            if not os.path.exists(new_rpt_root): # they hand-wrote a faulty path?
                wx.MessageBox(_(u"Warning - the folder your report is in "
                    u"doesn't currently exist."))
                return
            if self.autoupdate:
                cc[mg.CURRENT_REPORT_PATH] = new_rpt_pth
            self.txt_report_file.SetValue(new_rpt_pth)
            give_warning = not self.has_expected_subfolder(new_rpt_root)
            if give_warning:
                wx.MessageBox(ADD_EXPECTED_SUBFOLDER_MSG % 
                    {u"report_extras_folder": mg.REPORT_EXTRAS_FOLDER,
                     u"rpt_root": new_rpt_root, 
                     u"reports_path": mg.REPORTS_PATH})
        dlg_get_file.Destroy()

    def on_btn_export(self, event):
        if mg.PLATFORM == mg.MAC:
            wx.MessageBox(u"Sorry - I haven't been able to get exporting to "
                u"work on Macs yet. Please contact %s if you would like details"
                u" or if you are a Python developer and can help." % mg.CONTACT)
            return
        idx_export_sel = self.drop_export.GetSelection()
        if idx_export_sel == 0:
            if self.export_output_enabled:
                self.on_sel_export_output(event)
            else:
                wx.MessageBox(u"Unable to export output")
        elif idx_export_sel == 1:
            if self.copy_output_enabled:
                self.on_sel_copy_output(event)
            else:
                wx.MessageBox(u"Unable to copy output")
        elif idx_export_sel == 2:
            self.on_sel_export_report(event)
        else:
            raise Exception(u"Unexpected export selection: {}".format(
                idx_export_sel))

    def on_sel_export_report(self, event):
        cc = output.get_cc()
        report_missing = not os.path.exists(path=cc[mg.CURRENT_REPORT_PATH])
        if report_missing:
            try:
                self.can_run_report # False for Project dialog - can't make a report so no point letting them know they can make one if they want to view something
            except AttributeError:
                self.can_run_report = True
            if self.can_run_report:
                msg = NO_OUTPUT_YET_MSG
            else:
                msg = _("The output file has not been created yet. Nothing to "
                    "export") # not in a position to make one
            wx.MessageBox(msg)
            return
        # check subfolder there
        rpt_root = os.path.split(cc[mg.CURRENT_REPORT_PATH])[0]
        if not self.has_expected_subfolder(rpt_root):
            wx.MessageBox(ADD_EXPECTED_SUBFOLDER_MSG % 
                {u"report_extras_folder": mg.REPORT_EXTRAS_FOLDER,
                u"rpt_root": rpt_root, u"reports_path": mg.REPORTS_PATH})
            return
        cc = output.get_cc()
        dlg = export.DlgExportOutput(title=u"Export Report", 
            report_path=cc[mg.CURRENT_REPORT_PATH], save2report_path=True)
        dlg.ShowModal()

        
    def on_sel_export_output(self, event):
        try:
            self.update_demo_display() # so mg.INT_REPORT_PATH includes the latest title
        except AttributeError:
            pass
        dlg = export.DlgExportOutput(title=u"Export Output", 
            report_path=mg.INT_REPORT_PATH, save2report_path=False)
        dlg.ShowModal()
    
    def on_sel_copy_output(self, event):
        wx.BeginBusyCursor()
        try:
            export.copy_output()
            lib.safe_end_cursor()
            """
            Copying to the clipboard does not actually copy anything, it just 
            posts a promise to provide the data later when when it is asked for. 
            http://wxpython-users.1045709.n5.nabble.com/...
            ...Going-crazy-with-copy-paste-problem-td2365276.html
            """
            wx.MessageBox(_(u"Finished. Note - don't close the %s form before "
                u"pasting the output or it won't work." % self.title), 
                caption=u"COPIED OUTPUT")
        except Exception, e:
            lib.safe_end_cursor()
            wx.MessageBox(u"Unable to copy output to clipboard. Orig error: %s" 
                % b.ue(e))
    
    def get_script_output(self, get_script_args, new_has_dojo, 
            allow_add2rpt=True):
        debug = False
        cc = output.get_cc()
        if debug: print(cc[mg.CURRENT_CSS_PATH])
        css_fils, css_idx = output.get_css_dets()
        try:
            script = self.get_script(css_idx, *get_script_args)
        except Exception, e:
            raise Exception("Problem getting script. Orig error: %s" % 
                b.ue(e))
        add_to_report = False if not allow_add2rpt else mg.ADD2RPT
        (bolran_report, 
         str_content) = output.run_report(self.output_modules, add_to_report, 
            css_fils, new_has_dojo, script)
        if debug: print(str_content)
        return bolran_report, str_content
    
    def run_report(self, get_script_args, new_has_dojo=False):
        if self.too_long():
            return
        wx.BeginBusyCursor()
        (bolran_report, 
         str_content) = self.get_script_output(get_script_args, new_has_dojo)
        lib.update_local_display(self.html, str_content)
        self.content2expand = str_content
        self.align_export_btns(bolran_report)
        lib.safe_end_cursor()

    def align_export_btns(self, enable_btns):
        self.btn_expand.Enable(enable_btns)
        self.export_output_enabled = enable_btns
        self.copy_output_enabled = enable_btns

    def on_btn_run(self, event, get_script_args, new_has_dojo=False):
        try:
            self.run_report(get_script_args, new_has_dojo)
        except my_exceptions.MissingCss, e:    
            lib.update_local_display(self.html, _("Please check the CSS file "
                "exists or set another. Caused by error: %s") % b.ue(e), 
                wrap_text=True)
            lib.safe_end_cursor()
        event.Skip()
        
    def on_btn_view(self, event):
        """
        Open report in user's default web browser.
        """
        debug = False
        cc = output.get_cc()
        report_missing = not os.path.exists(path=cc[mg.CURRENT_REPORT_PATH])
        if report_missing:
            try:
                self.can_run_report # False for Project dialog - can't make a report so no point letting them know they can make one if they want to view something
            except AttributeError:
                self.can_run_report = True
            if self.can_run_report:
                msg = NO_OUTPUT_YET_MSG
            else:
                msg = _("The output file has not been created yet. Nothing to "
                    "view") # not in a position to make one
            wx.MessageBox(msg)
        else:
            url = output.path2url(cc[mg.CURRENT_REPORT_PATH])
            if debug: print(url)            
            webbrowser.open_new_tab(url)
        event.Skip()

    def on_report_file_lost_focus(self, event):
        "Reset report output file"
        if self.autoupdate:
            cc = output.get_cc()
            cc[mg.CURRENT_REPORT_PATH] = self.txt_report_file.GetValue()
        event.Skip()
    
    # table style
    def on_style_sel(self, event):
        """
        Change style. Note - when a listbox, fires on exit from form too - but 
            no GetStringSelection possible at that point (returns empty string)
            even if there was a selection previously before the close was 
            initiated.
        """
        if self.style_selector.GetSelection() != wx.NOT_FOUND:
            self.update_css()
    
    def update_css(self):
        "Update css, including for demo table"
        debug = False
        if self.autoupdate:
            cc = output.get_cc()
            style = self.style_selector.GetStringSelection()
            if style == u"":
                return
            if debug: print(u"Selected style is: %s" % style)
            cc[mg.CURRENT_CSS_PATH] = style2path(style)
        
    # explanation level
    #def get_szr_level(self, panel):
    #    """
    #    Get self.szr_level with radio widgets. 
    #    """
    #    szr_level = get_szr_level(self, panel)
    #    self.rad_level.Enable(False)
    #    return szr_level
    
    def on_btn_expand(self, event):
        showhtml.display_report(self, self.content2expand, self.url_load)
        event.Skip()
            
    def on_btn_close(self, event):
        self.Destroy()
        event.Skip()
        event.Skip()

def add_icon(frame):
    """
    Probably best to add largest first: http://stackoverflow.com/questions/...
    ...525329/embedding-icon-in-exe-with-py2exe-visible-in-vista/6198910#6198910
    """
    ib = wx.IconBundle()
    for sz in [128, 64, 48, 32, 16]:
        icon_path = os.path.join(mg.SCRIPT_PATH, u"images", 
            u"sofastats_%s.xpm" % sz)
        ib.AddIconFromFile(icon_path, wx.BITMAP_TYPE_XPM)
    frame.SetIcons(ib)
    