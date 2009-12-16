from __future__ import print_function
import codecs
import os
import sys
import wx

import my_globals
import getdata
import projects
import util


class ProjSelectDlg(wx.Dialog):
    def __init__(self, parent, projs):
        wx.Dialog.__init__(self, parent=parent, title=_("Projects"),
                           size=wx.DefaultSize, 
                           style=wx.RESIZE_BORDER|wx.CAPTION|wx.CLOSE_BOX|
                           wx.SYSTEM_MENU, pos=(400, 100))
        self.parent = parent
        self.panel = wx.Panel(self)
        self.projs = projs
        # icon
        ib = wx.IconBundle()
        ib.AddIconFromFile(os.path.join(my_globals.SCRIPT_PATH, 
                                        "images", 
                                        "tinysofa.xpm"), 
                           wx.BITMAP_TYPE_XPM)
        self.SetIcons(ib)
        self.szrMain = wx.BoxSizer(wx.VERTICAL)
        lblChoose = wx.StaticText(self.panel, -1, 
                                  _("Choose an existing project ..."))
        self.dropProjs = wx.Choice(self.panel, -1, choices=self.projs)
        self.dropProjs.SetSelection(0)
        self.StoreProjName(self.projs[0])
        self.dropProjs.Bind(wx.EVT_CHOICE, self.OnProjSelect)
        self.btnEdit = wx.Button(self.panel, wx.ID_EDIT)
        self.btnEdit.Bind(wx.EVT_BUTTON, self.OnEdit)
        szrExistingTop = wx.BoxSizer(wx.HORIZONTAL)
        szrExistingTop.Add(self.dropProjs, 1, wx.GROW|wx.RIGHT, 10)
        szrExistingTop.Add(self.btnEdit, 0)
        self.GetNotes(fil_proj=self.projs[0])
        self.txtProjNotes = wx.TextCtrl(self.panel, -1, self.proj_notes,
                                        style=wx.TE_MULTILINE|wx.TE_READONLY, 
                                        size=(400, 90))
        bxExisting = wx.StaticBox(self.panel, -1, _("Existing Projects"))
        szrExisting = wx.StaticBoxSizer(bxExisting, wx.VERTICAL)
        
        szrExisting.Add(szrExistingTop, 0, wx.GROW|wx.ALL, 10)
        szrExisting.Add(self.txtProjNotes, 1, wx.GROW|wx.ALL, 10)
        bxNew = wx.StaticBox(self.panel, -1, "")
        szrNew = wx.StaticBoxSizer(bxNew, wx.HORIZONTAL)
        lblMakeNew = wx.StaticText(self.panel, -1, 
                                   _("... or make a new project"))
        btnMakeNew = wx.Button(self.panel, wx.ID_NEW)
        btnMakeNew.Bind(wx.EVT_BUTTON, self.OnNewClick)
        szrNew.Add(lblMakeNew, 1, wx.GROW|wx.ALL, 10)
        szrNew.Add(btnMakeNew, 0, wx.ALL, 10)
        self.SetupButtons()
        self.szrMain.Add(lblChoose, 0, wx.ALL, 10)
        self.szrMain.Add(szrExisting, 1, wx.LEFT|wx.BOTTOM|wx.RIGHT|wx.GROW, 10)
        self.szrMain.Add(szrNew, 0, wx.GROW|wx.LEFT|wx.BOTTOM|wx.RIGHT, 10)
        self.szrMain.Add(self.szrButtons, 0, wx.GROW|wx.ALL|wx.ALIGN_RIGHT, 25)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.Layout()
    
    def StoreProjName(self, proj_name):
        "NB must have .proj on end"
        #print(proj_name) # debug
        self.proj_name = proj_name
    
    def SetupButtons(self):
        """
        Must have ID of wx.ID_... to trigger validators (no event binding 
            needed) and for std dialog button layout.
        """
        btnCancel = wx.Button(self.panel, wx.ID_CANCEL) # 
        btnCancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        btnOK = wx.Button(self.panel, wx.ID_OK)
        btnOK.Bind(wx.EVT_BUTTON, self.OnOK)
        btnOK.SetDefault()
        self.szrButtons = wx.StdDialogButtonSizer()
        self.szrButtons.AddButton(btnCancel)
        self.szrButtons.AddButton(btnOK)
        self.szrButtons.Realize()
    
    def GetNotes(self, fil_proj):
        proj_path = os.path.join(my_globals.LOCAL_PATH, "projs", fil_proj)
        f = codecs.open(proj_path, "U", encoding="utf-8")
        proj_cont = util.clean_bom_utf8(f.read())
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
        self.proj_notes = projects.GetProjNotes(fil_proj, proj_dic)
    
    def OnProjSelect(self, event):
        proj_sel_id = self.dropProjs.GetSelection()
        self.SetNotes(proj_sel_id)
        event.Skip()
    
    def SetNotes(self, proj_sel_id):
        proj_sel_id = self.dropProjs.GetSelection()
        self.GetNotes(self.projs[proj_sel_id])
        self.txtProjNotes.SetValue(self.proj_notes)
        
    def OnEdit(self,event):
        proj_sel_id = self.dropProjs.GetSelection()
        readonly = (self.projs[proj_sel_id] == my_globals.SOFA_DEFAULT_PROJ)
        dlgProj = projects.ProjectDlg(parent=self, readonly=readonly,
                          fil_proj=self.projs[self.dropProjs.GetSelection()])
        # refresh projects list and display accordingly
        ret_val = dlgProj.ShowModal()
        if ret_val == wx.ID_DELETE:
            # redo and pick 1st
            self.projs = projects.GetProjs()
            self.dropProjs.SetItems(self.projs)
            self.dropProjs.SetSelection(0)
            self.SetNotes(0)
        elif ret_val == wx.ID_OK:
            self.SetToNameFromOK()
          
    def OnNewClick(self, event):
        dlgProj = projects.ProjectDlg(parent=self, readonly=False)
        ret_val = dlgProj.ShowModal()
        if ret_val == wx.ID_OK:
            self.SetToNameFromOK()

    def SetToNameFromOK(self):
        # redo choices and display record with new name
        self.projs = projects.GetProjs()
        self.dropProjs.SetItems(self.projs)
        # get index of new name
        # NB proj name should have been set by projects
        proj_sel_id = self.projs.index(self.proj_name)
        self.dropProjs.SetSelection(proj_sel_id) # may have changed name
        self.SetNotes(proj_sel_id)

    def OnCancel(self, event):
        self.Destroy()
    
    def OnOK(self, event):
        proj_sel_id = self.dropProjs.GetSelection()
        fil_proj = self.projs[proj_sel_id]
        try:
            proj_name = fil_proj[:-5]
            self.parent.SetProj(proj_name)
        except Exception:
            pass
        self.Destroy()
