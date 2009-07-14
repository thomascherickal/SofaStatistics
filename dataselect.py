
import wx
import sys
import pprint

import getdata
import projects
import table_edit


class DataSelectDlg(wx.Dialog):
    def __init__(self, parent, proj_name):
        """
        NB self.dbe etc are all set during getdata.setupDataDropdowns
            because it calls getDbDetsObj to get the bits it needs
            and gets all the rest at the same time.
        No point getting them again in a more explicit way.
        """
        title = "Data in \"%s\" Project" % proj_name
        wx.Dialog.__init__(self, parent=parent, title=title,
                           size=(500, 300), 
                           style=wx.CAPTION|wx.CLOSE_BOX|
                           wx.SYSTEM_MENU, pos=(300, 100))
        self.parent = parent
        self.panel = wx.Panel(self)
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        self.szrMain = wx.BoxSizer(wx.VERTICAL)
        lblChoose = wx.StaticText(self.panel, -1, 
                                  "Choose an existing data table ...")
        proj_dic = projects.GetProjSettingsDic(proj_name=proj_name)
        self.var_labels, self.var_notes, self.val_dics = \
            projects.GetLabels(proj_dic["fil_labels"])
        getdata.setupDataDropdowns(self, self.panel, proj_dic["default_dbe"], 
                             proj_dic["conn_dets"], proj_dic["default_dbs"], 
                             proj_dic["default_tbls"])
        self.dropDatabases.Bind(wx.EVT_CHOICE, self.OnDatabaseSel)
        self.dropTables.Bind(wx.EVT_CHOICE, self.OnTableSel)
        self.chkReadOnly = wx.CheckBox(self.panel, -1, "Read Only")
        self.chkReadOnly.SetValue(True)
        btnOpen = wx.Button(self.panel, wx.ID_OPEN)
        btnOpen.Bind(wx.EVT_BUTTON, self.OnOpen)
        szrExistingTop = wx.BoxSizer(wx.HORIZONTAL)
        lblDbs = wx.StaticText(self.panel, -1, "Databases:")
        lblDbs.SetFont(lblfont)
        szrExistingTop.Add(lblDbs, 0, wx.RIGHT, 5)
        szrExistingTop.Add(self.dropDatabases, 0)
        self.dropDatabases.Bind(wx.EVT_CHOICE, self.OnDatabaseSel)
        szrExistingBottom = wx.BoxSizer(wx.HORIZONTAL)
        lblTbls = wx.StaticText(self.panel, -1, "Data tables:")
        lblTbls.SetFont(lblfont)
        szrExistingBottom.Add(lblTbls, 0, wx.RIGHT, 5)
        szrExistingBottom.Add(self.dropTables, 1, wx.GROW|wx.RIGHT, 10)
        szrExistingBottom.Add(self.chkReadOnly, 0, wx.TOP|wx.LEFT, 5)
        szrExistingBottom.Add(btnOpen, 0)
        bxExisting = wx.StaticBox(self.panel, -1, "Existing data tables")
        szrExisting = wx.StaticBoxSizer(bxExisting, wx.VERTICAL)
        szrExisting.Add(szrExistingTop, 0, wx.GROW|wx.ALL, 10)
        szrExisting.Add(szrExistingBottom, 0, wx.GROW|wx.ALL, 10)
        bxNew = wx.StaticBox(self.panel, -1, "")
        szrNew = wx.StaticBoxSizer(bxNew, wx.HORIZONTAL)
        lblMakeNew = wx.StaticText(self.panel, -1, "... or make a new data table")
        btnMakeNew = wx.Button(self.panel, wx.ID_NEW)
        btnMakeNew.Bind(wx.EVT_BUTTON, self.OnNewClick)
        szrNew.Add(lblMakeNew, 1, wx.GROW|wx.ALL, 10)
        szrNew.Add(btnMakeNew, 0, wx.ALL, 10)
        self.lblFeedback = wx.StaticText(self.panel, -1, "")
        btnClose = wx.Button(self.panel, wx.ID_CLOSE)
        btnClose.Bind(wx.EVT_BUTTON, self.OnClose)
        self.szrButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.szrButtons.Add(self.lblFeedback, 1, wx.GROW|wx.ALL, 10)
        self.szrButtons.Add(btnClose, 0, wx.RIGHT)        
        self.szrMain.Add(lblChoose, 0, wx.ALL, 10)
        self.szrMain.Add(szrExisting, 1, wx.LEFT|wx.BOTTOM|wx.RIGHT|wx.GROW, 10)
        self.szrMain.Add(szrNew, 0, wx.GROW|wx.LEFT|wx.BOTTOM|wx.RIGHT, 10)
        self.szrMain.Add(self.szrButtons, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.Layout()

    def AddFeedback(self, feedback):
        self.lblFeedback.SetLabel(feedback)
        wx.Yield()
        
    def OnDatabaseSel(self, event):
        getdata.ResetDataAfterDbSel(self)
    
    def OnTableSel(self, event):
        getdata.ResetDataAfterTblSel(self)
    
    def OnOpen(self, event):
        ""
        if not self.has_unique:
            wx.MessageBox("Table \"%s\" cannot be opened because it " % \
              self.tbl_name + \
              "lacks a unique index") # needed for caching even if read only
        else:
            read_only = self.chkReadOnly.IsChecked()
            dlg = table_edit.TblEditor(self, self.dbe, self.conn, 
                                       self.cur, self.db, self.tbl_name, 
                                       self.flds, self.var_labels, self.idxs,
                                       read_only)
            dlg.ShowModal()
        event.Skip()
    
    def OnNewClick(self, event):
        wx.MessageBox("Not available yet in this version")
        event.Skip()
    
    def OnClose(self, event):
        self.Destroy()
        

if __name__ == "__main__":
    app = wx.PySimpleApp()
    myframe = DataSelectDlg(None, "MOH.proj")
    myframe.Show()
    app.MainLoop()
    