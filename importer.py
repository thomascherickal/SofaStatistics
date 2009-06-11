import os
import util
import wx

import csv_importer
import getdata
import projects

SCRIPT_PATH = util.get_script_path()
FILE_CSV = "csv"
FILE_UNKNOWN = "unknown"
FLD_NUMERIC = "numeric field"
FLD_DATETIME = "datetime field"
FLD_STRING = "string field"
VAL_NUMERIC = "numeric value"
VAL_DATETIME = "datetime value"
VAL_STRING = "string value"
VAL_EMPTY_STRING = "empty string value"


class ImportFileSelectDlg(wx.Dialog):
    def __init__(self, parent):
        """
        Make selection based on file extension 
            and possibly inspection of sample of rows (e.g. csv dialect).
        """
        title = "Select file to import"
        wx.Dialog.__init__(self, parent=parent, title=title,
                           size=(500, 300), 
                           style=wx.CAPTION|wx.CLOSE_BOX|
                           wx.SYSTEM_MENU, pos=(300, 100))
        self.parent = parent
        self.panel = wx.Panel(self)
        # icon
        ib = wx.IconBundle()
        ib.AddIconFromFile(os.path.join(SCRIPT_PATH, "images", "tinysofa.xpm"), 
                           wx.BITMAP_TYPE_XPM)
        self.SetIcons(ib)
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        self.szrMain = wx.BoxSizer(wx.VERTICAL)
        # file path
        lblFilePath = wx.StaticText(self.panel, -1, "File:")
        lblFilePath.SetFont(lblfont)
        self.txtFile = wx.TextCtrl(self.panel, -1, "", size=(320,-1))
        self.txtFile.SetFocus()
        btnFilePath = wx.Button(self.panel, -1, "Browse ...")
        btnFilePath.Bind(wx.EVT_BUTTON, self.OnButtonFilePath)
        # internal SOFA name
        lblIntName = wx.StaticText(self.panel, -1, "SOFA Name:")
        lblIntName.SetFont(lblfont)
        self.txtIntName = wx.TextCtrl(self.panel, -1, "")
        #buttons
        btnCancel = wx.Button(self.panel, wx.ID_CANCEL)
        btnCancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        btnImport = wx.Button(self.panel, -1, "IMPORT")
        btnImport.Bind(wx.EVT_BUTTON, self.OnImport)
        # sizers
        self.szrFilePath = wx.BoxSizer(wx.HORIZONTAL)
        self.szrFilePath.Add(lblFilePath, 0, wx.LEFT, 10)
        self.szrFilePath.Add(self.txtFile, 1, wx.GROW|wx.LEFT|wx.RIGHT, 5)
        self.szrFilePath.Add(btnFilePath, 0, wx.RIGHT, 10)
        self.szrIntName = wx.BoxSizer(wx.HORIZONTAL)
        self.szrIntName.Add(lblIntName, 0, wx.RIGHT, 5)
        self.szrIntName.Add(self.txtIntName, 1)
        self.szrButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.szrButtons.Add(btnCancel, 0)
        self.szrButtons.Add(btnImport, 0, wx.GROW|wx.LEFT, 10)
        self.szrMain.Add(self.szrFilePath, 0, wx.GROW|wx.TOP, 20)
        self.szrMain.Add(self.szrIntName, 0, wx.GROW|wx.ALL, 10)
        self.szrMain.Add(self.szrButtons, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.Layout()

    def OnButtonFilePath(self, event):
        "Open dialog and takes the file selected (if any)"
        dlgGetFile = wx.FileDialog(self) #, message=..., wildcard=...
        #defaultDir="spreadsheets", defaultFile="", )
        #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            path = dlgGetFile.GetPath()
            self.txtFile.SetValue(path)
            filestart, _ = self.GetFilestartExt(path)
            self.txtIntName.SetValue(filestart)
        dlgGetFile.Destroy()
        self.txtIntName.SetFocus()
        event.Skip()
    
    def GetFilestartExt(self, path):
        _, filename = os.path.split(path)
        filestart, extension = os.path.splitext(filename)
        return filestart, extension
    
    def OnCancel(self, event):
        self.Destroy()
    
    def CheckTblName(self, file_path, tbl_name):
        """
        Returns final_tbl_name.
        Checks table name and gives user option of correcting it if problems.
        Raises exception if no suitable name selected.
        """
        final_tbl_name = tbl_name # unless overridden
        # check existing names
        proj_dic = projects.GetProjSettingsDic(projects.SOFA_DEFAULT_PROJ)
        dbdetsobj = getdata.getDbDetsObj(dbe=getdata.DBE_SQLITE, 
                                         conn_dets=proj_dic["conn_dets"])
        conn, cur, dbs, tbls, flds, has_unique, idxs = dbdetsobj.getDbDets()
        if tbl_name in tbls:
            msg = "A table named \"%s\" " % tbl_name + \
                  "already exists in the SOFA default database.\n\n" + \
                  "Do you want to replace it with the new data from " + \
                  "\"%s\"?" % file_path
            retCode = wx.MessageBox(msg, "TABLE ALREADY EXISTS",
                wx.YES_NO|wx.CANCEL|wx.ICON_QUESTION)
            if retCode == wx.CANCEL: # Not wx.ID_CANCEL
                raise Exception, "Had a name collision but cancelled out " + \
                    "of beginning to resolve it"
            elif retCode == wx.NO:
                # get new one
                dlg = wx.TextEntryDialog(None, "Please enter new name for table",
                                         "NEW TABLE NAME",
                                         style=wx.OK|wx.CANCEL)
                if dlg.ShowModal() == wx.ID_OK:
                    val_entered = dlg.GetValue()
                    if val_entered != "":
                        final_tbl_name = self.CheckTblName(file_path, 
                                                           val_entered)
                        tbl_name = val_entered
                    else:
                        raise Exception, "No table name entered when give chance"
                else:
                    raise Exception, "Had a name collision but cancelled " + \
                        "out of completing resolution of it"
        return final_tbl_name
    
    def OnImport(self, event):
        """
        Identify type of file by extension and open dialog if needed
            to get any additional choices e.g. separator used in 'csv'.
        """
        file_path = self.txtFile.GetValue()
        if not file_path:
            wx.MessageBox("Please select a file")
            return
        # identify file type
        _, extension = self.GetFilestartExt(file_path)
        if extension.lower() == ".csv":
            self.file_type = FILE_CSV
        else:
            wx.MessageBox("Files with the file name extension " + \
                              "'%s' are not supported" % extension)
            return
        tbl_name = self.txtIntName.GetValue()
        if not tbl_name:
            wx.MessageBox("Please select a name for the file")
            return
        try:
            final_tbl_name = self.CheckTblName(file_path, tbl_name)
        except Exception:
            wx.MessageBox("Please select a suitable table name and try again")
            return
        # import file
        if self.file_type == FILE_CSV:
            file_importer = csv_importer.FileImporter(file_path, 
                                                      final_tbl_name)
        if file_importer.GetParams():
            try:
                file_importer.ImportContent()
            except Exception, e:
                wx.MessageBox("Unable to import data\n\nError: %s" % e)
        event.Skip()
        

if __name__ == "__main__":
    app = wx.PySimpleApp()
    myframe = ImportFileSelectDlg(None)
    myframe.Show()
    app.MainLoop()
