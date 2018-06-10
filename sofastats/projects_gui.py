import os
import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats import getdata
from sofastats import config_ui
from sofastats import output
from sofastats import projects


class DlgProject(wx.Dialog, config_ui.ConfigUI):
    def __init__(self, parent, fil_proj=None, *, read_only=False):
        config_ui.ConfigUI.__init__(self, autoupdate=False)
        self.can_run_report = False
        if mg.MAX_WIDTH <= 1024:
            mywidth = 976
        else:
            mywidth = 1024
        if mg.MAX_HEIGHT <= 620:
            myheight = 576
        elif mg.MAX_HEIGHT <= 870:
            myheight = mg.MAX_HEIGHT - 70
        else:
            myheight = 800
        wx.Dialog.__init__(self, parent=parent, title=_('Project Settings'),
            size=(mywidth, myheight), style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX
            |wx.RESIZE_BORDER|wx.SYSTEM_MENU|wx.CAPTION|wx.TAB_TRAVERSAL) 
        ## wx.CLIP_CHILDREN causes problems in Windows
        self.szr = wx.BoxSizer(wx.VERTICAL)
        self.panel_top = wx.Panel(self)
        self.panel_top.SetBackgroundColour(wx.Colour(205, 217, 215))
        self.scroll_con_dets = wx.ScrolledWindow(self, size=(900, 350),  ## need for Windows
            style=wx.SUNKEN_BORDER|wx.TAB_TRAVERSAL)
        self.scroll_con_dets.SetScrollRate(10,10)  ## gives it the scroll bars
        self.panel_config = wx.Panel(self)
        self.panel_config.SetBackgroundColour(wx.Colour(205, 217, 215))
        self.panel_bottom = wx.Panel(self)
        self.panel_bottom.SetBackgroundColour(wx.Colour(115, 99, 84))
        self.parent = parent
        self.szr_con_dets = wx.BoxSizer(wx.VERTICAL)
        self.szr_config_outer = wx.BoxSizer(wx.VERTICAL)
        self.szr_bottom = wx.BoxSizer(wx.VERTICAL)
        ## get available settings
        self.read_only = read_only
        self.new = (fil_proj is None)
        self.set_defaults(fil_proj)
        self.set_extra_dets(vdt_file=self.fil_var_dets, 
            script_file=self.script_file)  ## so opens proj settings
        getdata.set_con_det_defaults(self)
        ## misc
        lblfont = wx.Font(9, wx.SWISS, wx.NORMAL, wx.BOLD)
        ## Project Name and notes
        lbl_empty = wx.StaticText(self.panel_top, -1, '')
        lbl_name = wx.StaticText(self.panel_top, -1, _('Project Name:'))
        lbl_name.SetFont(lblfont)
        self.txt_name = wx.TextCtrl(
            self.panel_top, -1, self.proj_name, size=(200, -1))
        self.txt_name.Enable(not self.read_only)
        lbl_proj_notes = wx.StaticText(self.panel_top, -1, _('Notes:'))
        lbl_proj_notes.SetFont(lblfont)
        self.txt_proj_notes = wx.TextCtrl(
            self.panel_top, -1, self.proj_notes, style=wx.TE_MULTILINE)
        self.txt_proj_notes.Enable(not self.read_only)
        szr_desc = wx.BoxSizer(wx.HORIZONTAL)
        szr_desc_left = wx.BoxSizer(wx.VERTICAL)
        szr_desc_mid = wx.BoxSizer(wx.VERTICAL)
        szr_desc_right = wx.BoxSizer(wx.VERTICAL)
        self.btn_help = wx.Button(self.panel_top, wx.ID_HELP)
        self.btn_help.Bind(wx.EVT_BUTTON, self.on_btn_help)
        szr_desc_left.Add(lbl_empty, 0, wx.RIGHT, 10)
        szr_desc_left.Add(self.btn_help, 0, wx.RIGHT, 10)
        szr_desc_mid.Add(lbl_name, 0)
        szr_desc_mid.Add(self.txt_name, 0, wx.RIGHT, 10)
        szr_desc_right.Add(lbl_proj_notes, 0)
        szr_desc_right.Add(self.txt_proj_notes, 1, wx.GROW)
        szr_desc.Add(szr_desc_left, 0)
        szr_desc.Add(szr_desc_mid)
        szr_desc.Add(szr_desc_right, 1, wx.GROW)
        ## DATA CONNECTIONS
        lbl_data_con_dets = wx.StaticText(self.panel_top, -1,
            _("How to connect to my data:"))
        lbl_data_con_dets.SetFont(lblfont)
        ## default dbe
        lbl_default_dbe = wx.StaticText(self.scroll_con_dets, -1,
            _("Default Database Engine:"))
        lbl_default_dbe.SetFont(lblfont)
        self.drop_default_dbe = wx.Choice(self.scroll_con_dets, -1,
            choices=mg.DBES)
        sel_dbe_id = mg.DBES.index(self.default_dbe)
        self.drop_default_dbe.SetSelection(sel_dbe_id)
        self.drop_default_dbe.Bind(wx.EVT_CHOICE, self.on_dbe_choice)
        self.drop_default_dbe.Enable(not self.read_only)
        lbl_scroll_down = wx.StaticText(self.scroll_con_dets, -1,
            _("(scroll down for details of all your database engines)"))
        ## default dbe
        szr_default_dbe = wx.BoxSizer(wx.HORIZONTAL)
        szr_default_dbe.Add(lbl_default_dbe, 0, wx.LEFT|wx.RIGHT, 5)
        szr_default_dbe.Add(self.drop_default_dbe, 0)
        szr_default_dbe.Add(lbl_scroll_down, 0, wx.LEFT, 10)
        ## Close
        self.setup_btns()
        ## sizers
        ## TOP
        self.szr_top = wx.BoxSizer(wx.VERTICAL)
        self.szr_top.Add(szr_desc, 1, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        self.szr_top.Add(lbl_data_con_dets, 0, wx.GROW|wx.LEFT|wx.BOTTOM, 10)
        self.panel_top.SetSizer(self.szr_top)
        self.szr_top.SetSizeHints(self.panel_top)
        ## CON DETS
        self.szr_con_dets.Add(szr_default_dbe, 0, wx.LEFT|wx.RIGHT|wx.TOP, 10)
        getdata.set_data_con_gui(parent=self,
            scroll=self.scroll_con_dets, szr=self.szr_con_dets, lblfont=lblfont,
            read_only=self.read_only)
        self.scroll_con_dets.SetSizer(self.szr_con_dets)
        ## NEVER SetSizeHints or else grows beyond size!!!!
        self.szr_con_dets.SetVirtualSizeHints(self.scroll_con_dets)
        ## CONFIG
        ## mixin supplying self.szr_output_config
        self.szr_output_config = self.get_szr_output_config(self.panel_config, 
            report_file=self.fil_report,
            show_run_btn=False, show_add_btn=False, show_view_btn=False,
            show_export_options=False, read_only=self.read_only)
        btn_var_config = self.get_btn_var_config(self.panel_config)
        self.style_selector = self.get_style_selector(
            self.panel_config, as_list=False, css_file=self.fil_css)
        self.szr_output_config.Add(btn_var_config, 0, wx.LEFT|wx.RIGHT, 5)  ## normally part of data but we need it here so
        self.szr_output_config.Add(self.style_selector, 0, wx.LEFT|wx.RIGHT, 5)  ## normally part of output szr but need it here
        self.szr_config_outer.Add(self.szr_output_config, 0, wx.GROW|wx.ALL, 10)
        self.panel_config.SetSizer(self.szr_config_outer)
        self.szr_config_outer.SetSizeHints(self.panel_config)
        ## BOTTOM
        self.szr_bottom.Add(self.szr_btns, 0, wx.GROW|wx.ALL|wx.ALIGN_RIGHT, 10)
        self.panel_bottom.SetSizer(self.szr_bottom)
        self.szr_bottom.SetSizeHints(self.panel_bottom)
        ## FINAL # NB any ratio changes must work in multiple OSs
        self.szr.Add(self.panel_top, 0, wx.GROW)
        self.szr.Add(self.scroll_con_dets, 3,
            wx.GROW|wx.LEFT|wx.BOTTOM|wx.RIGHT, 10)
        self.szr.Add(self.panel_config, 0, wx.GROW)
        self.szr.Add(self.panel_bottom, 0, wx.GROW)
        self.SetAutoLayout(True)
        self.SetSizer(self.szr)
        self.SetMinSize((930,550))
        self.Layout()
        self.sqlite_grid.grid.SetFocus()
        self.txt_name.SetFocus()

    def set_defaults(self, fil_proj):
        """
        If a proj file, grabs default settings from there and stores as
        attributes of dialog via get_proj_settings().
        """
        if fil_proj:
            self.new_proj = False
            self.get_proj_settings(fil_proj)
        else:
            ## prepopulate with default settings
            self.get_proj_settings(fil_proj=mg.DEFAULT_PROJ)
            self.proj_name = mg.EMPTY_PROJ_NAME
            self.proj_notes = _("The internal sofa_db is added by default. It "
                "is needed to allow you to add new tables to SOFA Statistics")
            self.new_proj = True
        try:
            self.proj_name
        except AttributeError:
            self.proj_name = mg.EMPTY_PROJ_NAME
        try:
            self.proj_notes
        except AttributeError:
            self.proj_notes = ''
        try:
            self.fil_var_dets
        except AttributeError:
            ## make empty labels file if necessary
            fil_default_var_dets = os.path.join(mg.LOCAL_PATH, mg.VDTS_FOLDER, 
                mg.DEFAULT_VDTS)
            if not os.path.exists(fil_default_var_dets):
                with open(fil_default_var_dets, 'w', encoding='utf-8') as f:
                    f.write("# add variable details here")
            self.fil_var_dets = fil_default_var_dets
        try:            
            self.fil_css
        except AttributeError:
            self.fil_css = os.path.join(
                mg.LOCAL_PATH, mg.CSS_FOLDER, mg.DEFAULT_STYLE)
        try:            
            self.fil_report
        except AttributeError:
            self.fil_report = os.path.join(mg.REPORTS_PATH, mg.DEFAULT_REPORT)
        try:            
            self.fil_script
        except AttributeError:
            self.fil_script = os.path.join(mg.LOCAL_PATH, mg.SCRIPTS_FOLDER, 
                mg.DEFAULT_SCRIPT)
        try:
            self.default_dbe
        except AttributeError:
            self.default_dbe = os.path.join(mg.DBE_SQLITE)

    def get_proj_settings(self, fil_proj):
        """
        NB get any paths in form ready to display
        """
        proj_path = os.path.join(mg.LOCAL_PATH, mg.PROJS_FOLDER, fil_proj)
        proj_txt = b.get_unicode_from_file(fpath=proj_path)
        proj_cont = b.get_exec_ready_text(text=proj_txt)
        proj_dic = {}
        try:
            exec(proj_cont, proj_dic)
        except SyntaxError as e:
            wx.MessageBox(
                _("Syntax error in project file \"%(fil_proj)s\"."
                "\n\nDetails: %(err)s") % {u"fil_proj": fil_proj,
                "err": b.ue(e)})
            raise
        except Exception as e:
            wx.MessageBox(
                _("Error processing project file \"%(fil_proj)s\"."
                "\n\nDetails: %(err)s") % {u"fil_proj": fil_proj,
                "err": b.ue(e)})
            raise
        try:
            self.proj_name = projects.filname2projname(fil_proj)
        except Exception as e:
            wx.MessageBox(_("Please check %(fil_proj)s for errors. "
                "Use %(def_proj)s for reference.") % {u"fil_proj": fil_proj,
                "def_proj": mg.DEFAULT_PROJ})
            raise
        ## Taking settings from proj file (via exec and proj_dic)
        ##   and adding them to this frame ready for use.
        ## Must always be stored, even if only ""
        try:
            self.proj_notes = projects.get_proj_notes(fil_proj, proj_dic)
            self.fil_var_dets = proj_dic[mg.PROJ_FIL_VDTS]
            self.fil_css = proj_dic[mg.PROJ_FIL_CSS]
            self.fil_report = proj_dic[mg.PROJ_FIL_RPT]
            self.fil_script = proj_dic[mg.PROJ_FIL_SCRIPT]
            self.default_dbe = proj_dic[mg.PROJ_DBE]
            getdata.get_proj_con_settings(self, proj_dic)
        except KeyError as e:
            wx.MessageBox(_("Please check %(fil_proj)s for errors. "
                "Use %(def_proj)s for reference.") % {"fil_proj": fil_proj,
                "def_proj": mg.DEFAULT_PROJ})
            raise Exception(u"Key error reading from proj_dic."
                "\nCaused by error: %s" % b.ue(e))
        except Exception as e:
            wx.MessageBox(_("Please check %(fil_proj)s for errors. "
                "Use %(def_proj)s for reference.") % {"fil_proj": fil_proj,
                "def_proj": mg.DEFAULT_PROJ})
            raise

    def on_dbe_choice(self, event):
        sel_dbe_id = self.drop_default_dbe.GetSelection()
        self.default_dbe = mg.DBES[sel_dbe_id]
        event.Skip()

    def setup_btns(self):
        """
        Must have ID of wx.ID_... to trigger validators (no event binding
        needed) and for std dialog button layout.

        NB can only add some buttons as part of standard sizer to be realised.

        Insert or Add others after the Realize() as required.

        See http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3605904
        and http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3605432
        """
        if self.read_only:
            btn_ok = wx.Button(self.panel_bottom, wx.ID_OK)
        else:
            if not self.new:
                btn_delete = wx.Button(self.panel_bottom, wx.ID_DELETE)
                btn_delete.Bind(wx.EVT_BUTTON, self.on_delete)
            btn_cancel = wx.Button(self.panel_bottom, wx.ID_CANCEL)
            btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
            btn_ok = wx.Button(self.panel_bottom, wx.ID_OK, _('Update'))
        btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        self.szr_btns = wx.StdDialogButtonSizer()
        if not self.read_only:
            self.szr_btns.AddButton(btn_cancel)
        self.szr_btns.AddButton(btn_ok)
        self.szr_btns.Realize()
        if not self.read_only and not self.new:
            self.szr_btns.Insert(0, btn_delete, 0)

    def on_btn_var_config(self, event):
        ret_dic = config_ui.ConfigUI.on_btn_var_config(self, event)
        if ret_dic:
            self.vdt_file = ret_dic[mg.VDT_RET]
        else:  ## cancelled presumably
            cc = output.get_cc()
            self.vdt_file = cc[mg.CURRENT_VDTS_PATH] 
        self.set_extra_dets(vdt_file=self.vdt_file, 
            script_file=self.script_file)  ## so opens proj settings with these same settings even if not saved yet.

    def on_btn_help(self, event):
        """
        Export script if enough data to create table.
        """
        import webbrowser
        url = (u"http://www.sofastatistics.com/wiki/doku.php"
            u"?id=help:projects")
        webbrowser.open_new_tab(url)
        event.Skip()

    def on_delete(self, _event):
        proj_name = self.txt_name.GetValue()
        if wx.MessageBox(_("Deleting a project cannot be undone. Do you want "
            "to delete the \"%s\" project?") % proj_name, style=wx.YES|wx.NO|
            wx.ICON_EXCLAMATION|wx.NO_DEFAULT) == wx.NO:
            return
        try:
            fil_to_delete = os.path.join(mg.LOCAL_PATH, mg.PROJS_FOLDER, 
                f"{self.txt_name.GetValue()}{mg.PROJ_EXT}")
            os.remove(fil_to_delete)
        except Exception:
            raise Exception("Unable to delete selected project.")
        self.Destroy()
        self.SetReturnCode(wx.ID_DELETE)  ## only for dialogs (MUST come after Destroy)

    def on_cancel(self, _event):
        "Close returning us to wherever we came from"
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)  ## only for dialogs (MUST come after Destroy)

    def on_ok(self, _event):
        """
        If not read-only, writes settings to proj file.
        Name, notes and report are all taken from the text in the text boxes.
        """
        ## get the data (separated for easier debugging)
        proj_name = self.txt_name.GetValue()
        if self.read_only:
            self.parent.store_proj_name(f"{proj_name}{mg.PROJ_EXT}")
        else:
            if proj_name == mg.EMPTY_PROJ_NAME:
                wx.MessageBox(_("Please provide a project name"))
                self.txt_name.SetFocus()
                return
            elif proj_name == projects.filname2projname(mg.DEFAULT_PROJ):
                wx.MessageBox(_("You cannot use the default project name"))
                self.txt_name.SetFocus()
                return
            try:
                self.parent.store_proj_name(f"{proj_name}{mg.PROJ_EXT}")
            except Exception:
                print(f"Failed to change to {proj_name}{mg.PROJ_EXT}")
                pass  ## Only needed if returning to projselect form so OK to fail otherwise.
            fil_name = os.path.join(mg.LOCAL_PATH, mg.PROJS_FOLDER,
                f"{proj_name}{mg.PROJ_EXT}")
            proj_notes = self.txt_proj_notes.GetValue()
            fil_var_dets = self.vdt_file
            fil_script = self.script_file if self.script_file else ''
            style = self.style_selector.GetStringSelection()
            fil_css = lib.OutputLib.style2path(style)
            fil_report = self.txt_report_file.GetValue()
            default_dbe = mg.DBES[self.drop_default_dbe.GetSelection()]
            default_dbs = {}
            default_tbls = {}
            con_dets = {}
            (any_incomplete, any_cons,
             completed_dbes) = getdata.process_con_dets(self, default_dbs,
                                                        default_tbls, con_dets)
            if any_incomplete:
                return
            enough_completed = proj_name and any_cons
            if not enough_completed:
                wx.MessageBox(
                    _("Not enough details completed to save a project file"))
                return
            default_dbe_lacks_con = default_dbe not in completed_dbes
            if default_dbe_lacks_con:
                wx.MessageBox(_("Connection details need to be completed "
                    "for the default database engine (%s) to save a project"
                    " file.") % default_dbe)
                return
            proj_content = projects.get_proj_content(proj_notes, fil_var_dets,
                fil_css, fil_report, fil_script, default_dbe, default_dbs,
                default_tbls, con_dets)
            ## write the data
            if (self.new
                and (os.path.exists(fil_name)
                and wx.MessageBox(_("A project file of this name already exists"
                    ". Do you wish to override it?"),
                    caption=_("PROJECT ALREADY EXISTS"),
                    style=wx.YES_NO) == wx.NO)):
                return
            ## In Windows, MySQL.proj and mysql.proj are the same in the file
            ## system - if already a file with same name, delete it first
            ## otherwise will write to mysql.proj when saving MySQL.proj.
            ## And MySQL won't appear in list on return to projselect.
            if mg.PLATFORM == mg.WINDOWS and os.path.exists(fil_name):
                os.remove(fil_name)
            try:
                f = open(fil_name, 'w', encoding='utf-8')
            except OSError as e:
                wx.MessageBox(_("Unable to save project file. Please check "
                    "\"%(fil_name)s\" is a valid file name."
                    "\n\nCaused by error: %(err)s") % {"fil_name": fil_name,
                    "err": b.ue(e)})
                return
            f.write(proj_content)
            f.close()
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)  ## only for dialogs
        ## (MUST come after Destroy)
