import os
import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import config_globals
from sofastats import lib
from sofastats import config_output
from sofastats import output
from sofastats import projects
from sofastats import projects_gui


class DlgProjSelect(wx.Dialog):
    def __init__(self, parent, projs, proj):
        wx.Dialog.__init__(self, parent=parent, title=_('Projects'),
            size=wx.DefaultSize, style=wx.RESIZE_BORDER|wx.CAPTION|
            wx.SYSTEM_MENU, pos=(mg.HORIZ_OFFSET+200,-1))
        self.parent = parent
        self.panel = wx.Panel(self)
        self.projs = projs
        config_output.add_icon(frame=self)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_main_inner = wx.BoxSizer(wx.VERTICAL)
        lbl_proj = wx.StaticText(self.panel, -1, _('Project:'))
        self.drop_projs = wx.Choice(self.panel, -1, choices=self.projs)
        idx_proj = self.projs.index(proj)
        self.drop_projs.SetSelection(idx_proj)
        self.store_proj_name(self.projs[idx_proj])
        self.drop_projs.Bind(wx.EVT_CHOICE, self.on_proj_select)
        self.btn_edit = wx.Button(self.panel, wx.ID_EDIT)
        self.btn_edit.Bind(wx.EVT_BUTTON, self.on_edit)
        btn_make_new = wx.Button(self.panel, wx.ID_NEW)
        btn_make_new.Bind(wx.EVT_BUTTON, self.on_new_click)
        szr_top = wx.BoxSizer(wx.HORIZONTAL)
        szr_top.Add(self.drop_projs, 1)
        szr_top.Add(self.btn_edit, 0, wx.LEFT|wx.RIGHT, 10)
        szr_top.Add(btn_make_new, 0)
        lbl_desc = wx.StaticText(self.panel, -1, _('Description:'))
        self.get_notes(fil_proj=self.projs[idx_proj])
        self.txt_proj_notes = wx.TextCtrl(self.panel, -1, self.proj_notes,
            style=wx.TE_MULTILINE|wx.TE_READONLY, size=(400,90))
        self.setup_btns()
        szr_main.Add(szr_main_inner, 1, wx.GROW|wx.ALL, 10)
        szr_main_inner.Add(lbl_proj, 0, wx.BOTTOM, 5)
        szr_main_inner.Add(szr_top, 0, wx.GROW|wx.BOTTOM, 10)
        szr_main_inner.Add(lbl_desc, 0, wx.BOTTOM, 5)
        szr_main_inner.Add(self.txt_proj_notes, 1, wx.GROW)
        szr_main_inner.Add(self.szr_btns, 0, wx.GROW|wx.TOP, 10)
        self.panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()

    def store_proj_name(self, proj_name):
        "NB must have .proj on end"
        debug = False
        if debug: print(proj_name)
        self.proj_name = proj_name

    def setup_btns(self):
        """
        Must have ID of wx.ID_... to trigger validators (no event binding
        needed) and for std dialog button layout.
        """
        btn_cancel = wx.Button(self.panel, wx.ID_CANCEL)
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        btn_ok = wx.Button(self.panel, wx.ID_OK)
        btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        btn_ok.SetDefault()
        self.szr_btns = wx.StdDialogButtonSizer()
        self.szr_btns.AddButton(btn_cancel)
        self.szr_btns.AddButton(btn_ok)
        self.szr_btns.Realize()

    def get_notes(self, fil_proj):
        proj_path = os.path.join(mg.LOCAL_PATH, mg.PROJS_FOLDER, fil_proj)
        proj_txt = b.get_unicode_from_file(fpath=proj_path)
        proj_cont = b.get_exec_ready_text(text=proj_txt)
        proj_dic = {}
        try:
            exec(proj_cont, proj_dic)
        except SyntaxError as e:
            wx.MessageBox(\
                _("Syntax error in project file \"%(fil_proj)s\"."
                "\n\nDetails: %s") % {'fil_proj': fil_proj, 'err': str(e)})
            raise
        except Exception as e:
            wx.MessageBox(\
                _("Error processing project file \"%(fil_proj)s\"."
                "\n\nDetails: %(err)s") % {'fil_proj': fil_proj, 'err': str(e)})
            raise
        ## must always be stored, even if only ''
        try:
            self.proj_notes = projects.get_proj_notes(fil_proj, proj_dic)
        except Exception as e:
            wx.MessageBox(_('Please check %s for errors. Use the default '
                'project file for reference.') % fil_proj)
            raise

    def on_proj_select(self, event):
        self.set_notes()
        event.Skip()

    def set_notes(self):
        proj_sel_id = self.drop_projs.GetSelection()
        self.get_notes(self.projs[proj_sel_id])
        self.txt_proj_notes.SetValue(self.proj_notes)

    def on_edit(self, _event):
        proj_sel_id = self.drop_projs.GetSelection()
        read_only = (self.projs[proj_sel_id] == mg.DEFAULT_PROJ)
        fil_proj = self.projs[self.drop_projs.GetSelection()]
        try:
            dlgProj = projects_gui.DlgProject(
                parent=self, fil_proj=fil_proj, readonly=read_only)
        except Exception as e:
            wx.MessageBox(f'Unable to open project dialog for {fil_proj}. '
                f'Orig error: {b.ue(e)}')
            return
        ## refresh projects list and display accordingly
        ret = dlgProj.ShowModal()
        if ret == wx.ID_DELETE:
            ## redo and pick 1st
            self.projs = projects.get_projs()
            self.drop_projs.SetItems(self.projs)
            self.drop_projs.SetSelection(0)
            self.set_notes()
        elif ret == wx.ID_OK:
            self.set_to_name_from_ok()

    def on_new_click(self, _event):
        dlg_proj = projects_gui.DlgProject(parent=self, read_only=False)
        ret = dlg_proj.ShowModal()
        if ret == wx.ID_OK:
            self.set_to_name_from_ok()

    def set_to_name_from_ok(self):
        ## redo choices and display record with new name
        self.projs = projects.get_projs()
        self.drop_projs.SetItems(self.projs)
        ## get index of new name
        ## NB proj name should have been set by projects
        proj_sel_id = self.projs.index(self.proj_name)
        self.drop_projs.SetSelection(proj_sel_id)  ## may have changed name
        self.set_notes()

    def on_cancel(self, _event):
        self.Destroy()

    def on_ok(self, _event):
        dd = mg.DATADETS_OBJ
        proj_sel_id = self.drop_projs.GetSelection()
        fil_proj = self.projs[proj_sel_id]
        proj_dic = config_globals.get_settings_dic(
            subfolder=mg.PROJS_FOLDER, fil_name=fil_proj)
        try:
            wx.BeginBusyCursor()
            dic2restore = dd.proj_dic
            dd.set_proj_dic(proj_dic, dic2restore)
            cc = output.get_cc()
            cc[mg.CURRENT_REPORT_PATH] = proj_dic[mg.PROJ_FIL_RPT]
            cc[mg.CURRENT_CSS_PATH] = proj_dic[mg.PROJ_FIL_CSS]
            cc[mg.CURRENT_VDTS_PATH] = proj_dic[mg.PROJ_FIL_VDTS]
            proj_name = projects.filname2projname(fil_proj)  ## might not be a sensible ...proj file
            self.parent.set_proj_lbl(proj_name)
        except Exception as e:
            lib.GuiLib.safe_end_cursor()
            wx.MessageBox(_('Unable to use the selected project file. Please '
                'check name of file and its contents using %(def_proj)s as '
                'example.\nCaused by error: %(err)s') % 
                {'def_proj': mg.DEFAULT_PROJ, 'err': b.ue(e)})
            return
        lib.GuiLib.safe_end_cursor()
        self.Destroy()
