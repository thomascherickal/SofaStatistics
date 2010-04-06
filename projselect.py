from __future__ import print_function
import codecs
import os
import sys
import wx

import my_globals as mg
import config_globals
import lib
import getdata
import config_dlg
import projects

dd = getdata.get_dd()


class ProjSelectDlg(wx.Dialog):
    def __init__(self, parent, projs, proj):
        wx.Dialog.__init__(self, parent=parent, title=_("Projects"),
                           size=wx.DefaultSize, 
                           style=wx.RESIZE_BORDER|wx.CAPTION|wx.CLOSE_BOX|
                           wx.SYSTEM_MENU, pos=(400,100))
        self.parent = parent
        self.panel = wx.Panel(self)
        self.projs = projs
        config_dlg.add_icon(frame=self)
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        lblChoose = wx.StaticText(self.panel, -1, 
                                  _("Choose an existing project ..."))
        self.drop_projs = wx.Choice(self.panel, -1, choices=self.projs)
        idx_proj = self.projs.index(proj)
        self.drop_projs.SetSelection(idx_proj)
        self.store_proj_name(self.projs[idx_proj])
        self.drop_projs.Bind(wx.EVT_CHOICE, self.on_proj_select)
        self.btn_edit = wx.Button(self.panel, wx.ID_EDIT)
        self.btn_edit.Bind(wx.EVT_BUTTON, self.on_edit)
        szr_existing_top = wx.BoxSizer(wx.HORIZONTAL)
        szr_existing_top.Add(self.drop_projs, 1, wx.GROW|wx.RIGHT, 10)
        szr_existing_top.Add(self.btn_edit, 0)
        self.get_notes(fil_proj=self.projs[idx_proj])
        self.txt_proj_notes = wx.TextCtrl(self.panel, -1, self.proj_notes,
                                          style=wx.TE_MULTILINE|wx.TE_READONLY, 
                                          size=(400,90))
        bx_existing = wx.StaticBox(self.panel, -1, _("Existing Projects"))
        szr_existing = wx.StaticBoxSizer(bx_existing, wx.VERTICAL)
        szr_existing.Add(szr_existing_top, 0, wx.GROW|wx.ALL, 10)
        szr_existing.Add(self.txt_proj_notes, 1, wx.GROW|wx.ALL, 10)
        bx_new = wx.StaticBox(self.panel, -1, "")
        szr_new = wx.StaticBoxSizer(bx_new, wx.HORIZONTAL)
        lbl_make_new = wx.StaticText(self.panel, -1, 
                                   _("... or make a new project"))
        btn_make_new = wx.Button(self.panel, wx.ID_NEW)
        btn_make_new.Bind(wx.EVT_BUTTON, self.on_new_click)
        szr_new.Add(lbl_make_new, 1, wx.GROW|wx.ALL, 10)
        szr_new.Add(btn_make_new, 0, wx.ALL, 10)
        self.setup_btns()
        self.szr_main.Add(lblChoose, 0, wx.ALL, 10)
        self.szr_main.Add(szr_existing, 1, wx.LEFT|wx.BOTTOM|wx.RIGHT|wx.GROW, 
                          10)
        self.szr_main.Add(szr_new, 0, wx.GROW|wx.LEFT|wx.BOTTOM|wx.RIGHT, 10)
        self.szr_main.Add(self.szr_btns, 0, wx.GROW|wx.ALL, 25)
        self.panel.SetSizer(self.szr_main)
        self.szr_main.SetSizeHints(self)
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
        btn_cancel = wx.Button(self.panel, wx.ID_CANCEL) # 
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        btn_ok = wx.Button(self.panel, wx.ID_OK)
        btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        btn_ok.SetDefault()
        self.szr_btns = wx.StdDialogButtonSizer()
        self.szr_btns.AddButton(btn_cancel)
        self.szr_btns.AddButton(btn_ok)
        self.szr_btns.Realize()
    
    def get_notes(self, fil_proj):
        proj_path = os.path.join(mg.LOCAL_PATH, "projs", fil_proj)
        f = codecs.open(proj_path, "U", encoding="utf-8")
        proj_cont = lib.clean_bom_utf8(f.read())
        f.close()
        proj_dic = {}
        try:
            exec proj_cont in proj_dic
        except SyntaxError, e:
            wx.MessageBox(\
                _("Syntax error in project file \"%s\"." % fil_proj + \
                          os.linesep + os.linesep + "Details: %s" % unicode(e)))
            raise Exception, unicode(e)
        except Exception, e:
            wx.MessageBox(\
                _("Error processing project file \"%s\"." % fil_proj + \
                          os.linesep + os.linesep + "Details: %s" % unicode(e)))
            raise Exception, unicode(e)
        # must always be stored, even if only ""
        try:
            self.proj_notes = projects.get_proj_notes(fil_proj, proj_dic)
        except Exception, e:
            wx.MessageBox(_("Please check %s for errors. Use the default "
                            "project file for reference.") % fil_proj)
            raise Exception, e
    
    def on_proj_select(self, event):
        proj_sel_id = self.drop_projs.GetSelection()
        self.set_notes(proj_sel_id)
        event.Skip()
    
    def set_notes(self, proj_sel_id):
        proj_sel_id = self.drop_projs.GetSelection()
        self.get_notes(self.projs[proj_sel_id])
        self.txt_proj_notes.SetValue(self.proj_notes)
        
    def on_edit(self,event):
        proj_sel_id = self.drop_projs.GetSelection()
        readonly = (self.projs[proj_sel_id] == mg.SOFA_DEFAULT_PROJ)
        dlgProj = projects.ProjectDlg(parent=self, readonly=readonly,
                          fil_proj=self.projs[self.drop_projs.GetSelection()])
        # refresh projects list and display accordingly
        retval = dlgProj.ShowModal()
        if retval == wx.ID_DELETE:
            # redo and pick 1st
            self.projs = projects.get_projs()
            self.drop_projs.SetItems(self.projs)
            self.drop_projs.SetSelection(0)
            self.set_notes(0)
        elif retval == wx.ID_OK:
            self.set_to_name_from_ok()
          
    def on_new_click(self, event):
        dlg_proj = projects.ProjectDlg(parent=self, readonly=False)
        retval = dlg_proj.ShowModal()
        if retval == wx.ID_OK:
            self.set_to_name_from_ok()

    def set_to_name_from_ok(self):
        # redo choices and display record with new name
        self.projs = projects.get_projs()
        self.drop_projs.SetItems(self.projs)
        # get index of new name
        # NB proj name should have been set by projects
        proj_sel_id = self.projs.index(self.proj_name)
        self.drop_projs.SetSelection(proj_sel_id) # may have changed name
        self.set_notes(proj_sel_id)

    def on_cancel(self, event):
        self.Destroy()
    
    def on_ok(self, event):
        proj_sel_id = self.drop_projs.GetSelection()
        fil_proj = self.projs[proj_sel_id]
        proj_dic = config_globals.get_settings_dic(subfolder=u"projs", 
                                                   fil_name=fil_proj)
        dd.set_proj_dic(proj_dic)
        try:
            proj_name = fil_proj[:-5] # might not be a sensible ...proj file
            self.parent.set_proj(proj_name)
        except Exception:
            pass
        self.Destroy()