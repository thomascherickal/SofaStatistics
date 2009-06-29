
import wx
import pprint
import sys
import os

import my_globals
import getdata
import projselect
import util

USER_PATH, LOCAL_PATH = util.get_user_paths()

# http://www.velocityreviews.com/forums/t336564-proper-use-of-file.html
EMPTY_PROJ_NAME = "GIVE ME A NAME ..."
SOFA_DEFAULT_DB = "SOFA_Default_db"
SOFA_DEFAULT_TBL = "SOFA_Default_tbl"
SOFA_DEFAULT_PROJ = "SOFA_Default_Project.proj"
SOFA_DEFAULT_LBLS = "SOFA_Default_Labels.lbls"
SOFA_DEFAULT_STYLE = "SOFA_Default_Style.css"
SOFA_DEFAULT_SCRIPT = "SOFA_Default_Exported_Table_Scripts.py"
SOFA_DEFAULT_REPORT = "SOFA_Default_New_Tables.htm"
INTERNAL_FOLDER = "_internal"
INT_SCRIPT_PATH = os.path.join(LOCAL_PATH, INTERNAL_FOLDER, "script.py")
INT_REPORT_FILE = "report.htm"
INT_REPORT_PATH = os.path.join(LOCAL_PATH, INTERNAL_FOLDER, INT_REPORT_FILE)

def GetProjs():
    "NB includes .proj at end"
    proj_fils = os.listdir(os.path.join(LOCAL_PATH, "projs"))
    proj_fils = [x for x in proj_fils if x.endswith(".proj")]
    proj_fils.sort()
    return proj_fils

def GetProjSettingsDic(proj_name):
    """
    Returns proj_dic with keys such as conn_dets, fil_labels etc.
    proj_name MUST include .proj on end
    """
    f = open(os.path.join(LOCAL_PATH, "projs", proj_name), "r")
    proj_dic = {}
    exec f in proj_dic # http://docs.python.org/reference/simple_stmts.html
    f.close()
    return proj_dic

def GetLabels(fil_labels):
    """
    Get variable and value labels from fil_labels file.
    Returns var_labels, var_notes, val_dics.
    """
    try:
        fil = file(fil_labels, "r")
    except IOError:
        var_labels = {}
        var_notes = {}
        val_dics = {}
        return var_labels, var_notes, val_dics
    labels = fil.read()
    fil.close()
    labels_dic = {}
    exec labels in labels_dic
    try:
        results = labels_dic["var_labels"], labels_dic["var_notes"], \
                      labels_dic["val_dics"]
    except Exception, e:
        raise Exception, "Three variables needed in " + \
            "'%s': var_labels, var_notes, and val_dics.  " + \
            "Please check file." % fil_labels
    return results


class ProjectDlg(wx.Dialog):
    def __init__(self, parent, read_only=False, fil_proj=None):
        wx.Dialog.__init__(self, parent=parent, title="Project Settings",
                           size=(1090, 580), 
                           style=wx.CAPTION|wx.CLOSE_BOX|
                           wx.SYSTEM_MENU, pos=(100, 100))
        y_start = self.GetClientSize()[1] - self.GetSize()[1]
        self.panel_top = wx.Panel(self, pos=(0,0))
        self.scroll_conn_dets = wx.PyScrolledWindow(self, pos=(10, 280 + y_start), 
                                                    size=(1070, 240),
                                                    style=wx.SUNKEN_BORDER)
        self.scroll_conn_dets.SetScrollbars(10, 10, -1, -1) # otherwise no scrollbars
        self.scroll_conn_dets.SetVirtualSize((1270, 460))
        self.panel_bottom = wx.Panel(self, pos=(0, 525 + y_start))
        self.parent = parent
        self.szrTop = wx.BoxSizer(wx.VERTICAL)
        self.szrConn_Dets = wx.BoxSizer(wx.VERTICAL)
        self.szrBottom = wx.BoxSizer(wx.VERTICAL)
        # get available settings
        self.read_only = read_only
        if fil_proj:
            self.new_proj = False
            self.GetProjSettings(fil_proj)
        else:
            self.new_proj = True
        try:
            self.proj_name
        except AttributeError:
            self.proj_name = EMPTY_PROJ_NAME
        try:
            self.proj_notes
        except AttributeError:
            self.proj_notes = ""
        try:
            self.fil_labels
        except AttributeError:
            # make empty labels file if necessary
            fil_default_lbls = os.path.join(LOCAL_PATH, "lbls", 
                                            SOFA_DEFAULT_LBLS)
            if not os.path.exists(fil_default_lbls):
                f = open(fil_default_lbls, "w")
                f.write("# add labels here")
                f.close()
            self.fil_labels = fil_default_lbls
        try:            
            self.fil_css
        except AttributeError:
            self.fil_css = os.path.join(LOCAL_PATH, "css", 
                                        SOFA_DEFAULT_STYLE)
        try:            
            self.fil_report
        except AttributeError:       
            self.fil_report = os.path.join(LOCAL_PATH, "reports", 
                                           SOFA_DEFAULT_REPORT)
        try:            
            self.fil_script
        except AttributeError: 
            self.fil_script = os.path.join(LOCAL_PATH, "scripts", 
                                           SOFA_DEFAULT_SCRIPT)
        try:
            self.default_dbe
        except AttributeError:
            self.default_dbe = os.path.join(my_globals.DBE_SQLITE)
        getdata.setConnDetDefaults(self)
        # misc
        lblfont = wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD)
        # Project Name
        szrName = wx.BoxSizer(wx.HORIZONTAL)
        lblName = wx.StaticText(self.panel_top, -1, "Project Name:")
        lblName.SetFont(lblfont)
        self.txtName = wx.TextCtrl(self.panel_top, -1, self.proj_name, 
                                   size=(200, -1))
        self.txtName.Enable(not self.read_only)
        szrName.Add(lblName, 0, wx.RIGHT, 10)
        szrName.Add(self.txtName)
        # project notes
        lblProjNotes = wx.StaticText(self.panel_top, -1, "Project Notes:")
        lblProjNotes.SetFont(lblfont)
        self.txtProjNotes = wx.TextCtrl(self.panel_top, -1, self.proj_notes,
                                        size=(540, 60), style=wx.TE_MULTILINE)
        self.txtProjNotes.Enable(not self.read_only)
        # Data config details
        lblLabelPath = wx.StaticText(self.panel_top, -1, "Labels:")
        lblLabelPath.SetFont(lblfont)
        self.txtLabelsFile = wx.TextCtrl(self.panel_top, -1, self.fil_labels, 
                                         size=(320,-1))
        self.txtLabelsFile.Enable(not self.read_only)
        btnLabelPath = wx.Button(self.panel_top, -1, "Browse ...")
        btnLabelPath.Bind(wx.EVT_BUTTON, self.OnButtonLabelPath)
        btnLabelPath.Enable(not self.read_only)
        # CSS style config details
        lblCssPath = wx.StaticText(self.panel_top, -1, "CSS:")
        lblCssPath.SetFont(lblfont)
        self.txtCssFile = wx.TextCtrl(self.panel_top, -1, self.fil_css, 
                                      size=(320,-1))
        self.txtCssFile.Enable(not self.read_only)
        btnCssPath = wx.Button(self.panel_top, -1, "Browse ...")
        btnCssPath.Bind(wx.EVT_BUTTON, self.OnButtonCssPath)
        btnCssPath.Enable(not self.read_only)
        # Output details
        # report
        lblReportPath = wx.StaticText(self.panel_top, -1, "Report:")
        lblReportPath.SetFont(lblfont)
        self.txtReportFile = wx.TextCtrl(self.panel_top, -1, self.fil_report, 
                                         size=(320,-1))
        self.txtReportFile.Enable(not self.read_only)
        btnReportPath = wx.Button(self.panel_top, -1, "Browse ...")
        btnReportPath.Bind(wx.EVT_BUTTON, self.OnButtonReportPath)
        btnReportPath.Enable(not self.read_only)
        # script
        lblScriptPath = wx.StaticText(self.panel_top, -1, "Script:")
        lblScriptPath.SetFont(lblfont)
        self.txtScriptFile = wx.TextCtrl(self.panel_top, -1, self.fil_script, 
                                   size=(320,-1))
        self.txtScriptFile.Enable(not self.read_only)
        btnScriptPath = wx.Button(self.panel_top, -1, "Browse ...")
        btnScriptPath.Bind(wx.EVT_BUTTON, self.OnButtonScriptPath)
        btnScriptPath.Enable(not self.read_only)
        # DATA CONNECTIONS
        lblDataConnDets = wx.StaticText(self.panel_top, -1, 
                                        "Data Connection Details:")
        # default dbe
        lblDefault_Dbe = wx.StaticText(self.scroll_conn_dets, -1, 
                                       "Default Database Engine:")
        lblDefault_Dbe.SetFont(lblfont)
        self.dropDefault_Dbe = wx.Choice(self.scroll_conn_dets, -1, 
                                         choices=getdata.DBES)
        sel_dbe_id = getdata.DBES.index(self.default_dbe)
        self.dropDefault_Dbe.SetSelection(sel_dbe_id)
        self.dropDefault_Dbe.Bind(wx.EVT_CHOICE, self.OnDbeChoice)
        self.dropDefault_Dbe.Enable(not self.read_only)
        # NOTES
        szrNotes = wx.BoxSizer(wx.HORIZONTAL)
        szrNotes.Add(lblProjNotes, 0, wx.RIGHT, 5)
        szrNotes.Add(self.txtProjNotes, 1, wx.GROW)
        #2 CONFIG
        szrConfig = wx.BoxSizer(wx.HORIZONTAL)
        #3 DATA CONFIG
        bxDataConfig = wx.StaticBox(self.panel_top, -1, "Data Config")
        szrDataConfig = wx.StaticBoxSizer(bxDataConfig, wx.HORIZONTAL)
        #3 DATA CONFIG INNER
        szrDataConfigInner = wx.BoxSizer(wx.HORIZONTAL)
        szrDataConfigInner.Add(lblLabelPath, 0, wx.LEFT|wx.RIGHT, 5)
        szrDataConfigInner.Add(self.txtLabelsFile, 1, wx.GROW|wx.RIGHT, 10)
        szrDataConfigInner.Add(btnLabelPath, 0)
        szrDataConfig.Add(szrDataConfigInner, 1)
        szrConfig.Add(szrDataConfig, 1, wx.RIGHT, 10)
        #3 CSS CONFIG
        bxCssConfig = wx.StaticBox(self.panel_top, -1, "Table Style")
        szrCssConfig = wx.StaticBoxSizer(bxCssConfig, wx.HORIZONTAL)
        #3 CSS CONFIG INNER
        szrCssConfigInner = wx.BoxSizer(wx.HORIZONTAL)
        szrCssConfigInner.Add(lblCssPath, 0, wx.LEFT|wx.RIGHT, 5)
        szrCssConfigInner.Add(self.txtCssFile, 1, wx.GROW|wx.RIGHT, 10)
        szrCssConfigInner.Add(btnCssPath, 0)
        szrCssConfig.Add(szrCssConfigInner, 1)
        szrConfig.Add(szrCssConfig, 1)
        #2 OUTPUT
        bxOutput = wx.StaticBox(self.panel_top, -1, "Output")
        szrOutput = wx.StaticBoxSizer(bxOutput, wx.HORIZONTAL)
        #3 OUTPUT INNER
        szrOutputInner = wx.BoxSizer(wx.HORIZONTAL)
        # report 
        szrOutputInner.Add(lblReportPath, 0, wx.LEFT|wx.RIGHT, 5)
        szrOutputInner.Add(self.txtReportFile, 1, wx.GROW|wx.RIGHT, 10)
        szrOutputInner.Add(btnReportPath, 0, wx.RIGHT, 10)
        # script
        szrOutputInner.Add(lblScriptPath, 0, wx.LEFT|wx.RIGHT, 5)
        szrOutputInner.Add(self.txtScriptFile, 1, wx.GROW|wx.RIGHT, 10)
        szrOutputInner.Add(btnScriptPath, 0)
        szrOutput.Add(szrOutputInner, 1)
        # default dbe
        szrDefault_Dbe = wx.BoxSizer(wx.HORIZONTAL)
        szrDefault_Dbe.Add(lblDefault_Dbe, 0, wx.LEFT|wx.RIGHT, 5)
        szrDefault_Dbe.Add(self.dropDefault_Dbe, 0)
        # Close
        self.SetupButtons()
        # sizers
        # TOP
        self.szrTop.Add(szrName, 0, wx.GROW|wx.ALL, 10)
        self.szrTop.Add(szrNotes, 1, wx.GROW|wx.ALL, 10)
        self.szrTop.Add(szrConfig, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        self.szrTop.Add(szrOutput, 0, wx.GROW|wx.ALL, 10)
        self.szrTop.Add(lblDataConnDets, 0, wx.LEFT|wx.RIGHT, 10)
        self.panel_top.SetSizer(self.szrTop)
        self.szrTop.SetSizeHints(self.panel_top)
        # CONN DETS
        self.szrConn_Dets.Add(szrDefault_Dbe, 0, wx.LEFT|wx.RIGHT|wx.TOP, 10)
        getdata.setDataConnGui(parent=self, read_only=self.read_only, 
                               scroll=self.scroll_conn_dets, 
                               szr=self.szrConn_Dets, lblfont=lblfont)
        self.scroll_conn_dets.SetSizer(self.szrConn_Dets)
        # NEVER SetSizeHints or else grows beyond size!!!!   
        self.szrConn_Dets.SetVirtualSizeHints(self.scroll_conn_dets)
        #self.scroll_conn_dets.FitInside() # no effect
        # BOTTOM        
        self.szrBottom.Add(self.szrButtons, 0, wx.ALL, 10)
        self.panel_bottom.SetSizer(self.szrBottom)
        self.szrBottom.SetSizeHints(self.panel_bottom)
        # FINAL
        self.Layout()
        self.sqlite_grid.grid.SetFocus()

    def GetProjSettings(self, fil_proj):
        f = open(os.path.join(LOCAL_PATH, "projs", fil_proj), "r")
        proj_dic = {}
        exec f in proj_dic
        f.close()
        self.proj_name = fil_proj[:-5]
        # Taking settings from proj file (via exec and proj_dic)
        #   and adding them to this frame ready for use.
        # Must always be stored, even if only ""
        self.proj_notes = proj_dic["proj_notes"]
        self.fil_labels = proj_dic["fil_labels"]
        self.fil_css = proj_dic["fil_css"]
        self.fil_report = proj_dic["fil_report"]
        self.fil_script = proj_dic["fil_script"]
        self.default_dbe = proj_dic["default_dbe"]
        getdata.getProjConnSettings(self, proj_dic)
        
    # report output
    def OnButtonReportPath(self, event):
        "Open dialog and takes the report file selected (if any)"
        dlgGetFile = wx.FileDialog(self, "Choose a report output file:", 
            defaultDir=os.path.join(LOCAL_PATH, "reports"), 
            defaultFile="", 
            wildcard="HTML files (*.htm)|*.htm|HTML files (*.html)|*.html")
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            self.fil_report = "%s" % dlgGetFile.GetPath()
            self.txtReportFile.SetValue(self.fil_report)
        dlgGetFile.Destroy()
        
    # script output
    def OnButtonScriptPath(self, event):
        "Open dialog and takes the script file selected (if any)"
        dlgGetFile = wx.FileDialog(self, "Choose a file to export scripts to:", 
            defaultDir=os.path.join(LOCAL_PATH, "scripts"), 
            defaultFile="", wildcard="Scripts (*.py)|*.py")
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            self.fil_script = "%s" % dlgGetFile.GetPath()
            self.txtScriptFile.SetValue(self.fil_script)
        dlgGetFile.Destroy()

    # label config
    def OnButtonLabelPath(self, event):
        "Open dialog and takes the labels file selected (if any)"
        dlgGetFile = wx.FileDialog(self, "Choose a label config file:", 
            defaultDir=os.path.join(LOCAL_PATH, "lbls"), 
            defaultFile="", wildcard="Config files (*.lbls)|*.lbls")
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            fil_labels = "%s" % dlgGetFile.GetPath()
            self.txtLabelsFile.SetValue(fil_labels)
        dlgGetFile.Destroy()

    # css table style
    def OnButtonCssPath(self, event):
        "Open dialog and takes the css file selected (if any)"
        dlgGetFile = wx.FileDialog(self, "Choose a css table style file:", 
            defaultDir=os.path.join(LOCAL_PATH, "css"), 
            defaultFile="", 
            wildcard="CSS files (*.css)|*.css")
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            fil_css = "%s" % dlgGetFile.GetPath()
            self.txtCssFile.SetValue(fil_css)
        dlgGetFile.Destroy()
    
    def UpdateCss(self):
        "Update css, including for demo table"
        self.fil_css = self.txtCssFile.GetValue()
        self.demo_tab.fil_css = self.fil_css
    
    def OnDbeChoice(self, event):
        sel_dbe_id = self.dropDefault_Dbe.GetSelection()
        self.default_dbe = getdata.DBES[sel_dbe_id]
        event.Skip()
    
    def SetupButtons(self):
        """
        Must have ID of wx.ID_... to trigger validators (no event binding 
            needed) and for std dialog button layout.
        NB can only add some buttons as part of standard sizer to be realised.
        Insert or Add others after the Realize() as required.
        See http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3605904
        and http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3605432
        """
        btnDelete = wx.Button(self.panel_bottom, wx.ID_DELETE)
        btnDelete.Bind(wx.EVT_BUTTON, self.OnDelete)
        btnCancel = wx.Button(self.panel_bottom, wx.ID_CANCEL) # 
        btnCancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        if self.read_only:
            btnDelete.Disable()
            btnCancel.Disable()
        btnOK = wx.Button(self.panel_bottom, wx.ID_OK)
        btnOK.Bind(wx.EVT_BUTTON, self.OnOK)
        self.szrButtons = wx.StdDialogButtonSizer()
        self.szrButtons.AddButton(btnCancel)
        self.szrButtons.AddButton(btnOK)
        self.szrButtons.Realize()
        self.szrButtons.Insert(0, btnDelete, 0)

    def OnDelete(self, event):
        proj_name = self.txtName.GetValue()
        if wx.MessageBox("Deleting a project cannot be undone.  " + \
                "Do you want to delete the \"%s\" project?" % \
                proj_name, 
                style=wx.YES|wx.NO|wx.ICON_EXCLAMATION|wx.NO_DEFAULT) == wx.NO:
            return
        try:
            fil_to_delete = os.path.join(LOCAL_PATH, "projs", 
                                   "%s.proj" % self.txtName.GetValue())
            #print fil_to_delete # debug
            os.remove(fil_to_delete)
        except Exception:
            pass
        self.Destroy()
        self.SetReturnCode(wx.ID_DELETE) # only for dialogs 
        # (MUST come after Destroy)

    def OnCancel(self, event):
        "Close returning us to wherever we came from"
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL) # only for dialogs 
        # (MUST come after Destroy)

    def getFileName(self, path):
        "Works on Windows paths as well"
        path = path.replace("\\", "/")
        return os.path.split(path)[1]
       
    def OnOK(self, event):
        # get the data (separated for easier debugging)
        if not self.read_only:
            proj_name = self.txtName.GetValue()
            if proj_name == EMPTY_PROJ_NAME:
                wx.MessageBox("Please provide a project name")
                self.txtName.SetFocus()
                return
            try:
                # only needed if returning to projselect form
                # so OK to fail otherwise
               self.parent.StoreProjName("%s.proj" % proj_name)
            except Exception:
                print "Failed to change to %s.proj" % proj_name
                pass
            proj_notes = self.txtProjNotes.GetValue()
            fil_labels = self.txtLabelsFile.GetValue()
            fil_css = self.txtCssFile.GetValue()
            fil_report = self.txtReportFile.GetValue()
            fil_script = self.txtScriptFile.GetValue()
            default_dbe = getdata.DBES[self.dropDefault_Dbe.GetSelection()]
            default_dbs = {}
            default_tbls = {}
            conn_dets = {}
            any_incomplete, any_conns, completed_dbes = \
                getdata.processConnDets(self, default_dbs, default_tbls, 
                                        conn_dets)
            if any_incomplete:
                return
            enough_completed = proj_name and any_conns
            if not enough_completed:
                wx.MessageBox("Not enough details completed to " + \
                              "save a project file")
                return
            default_dbe_lacks_conn = default_dbe not in completed_dbes
            if default_dbe_lacks_conn:
                wx.MessageBox("Connection details need to be completed " + \
                      "for the default database engine (%s) to save a " + \
                      "project file" % default_dbe)
                return
            # write the data
            fil_name = os.path.join(LOCAL_PATH, "projs", "%s.proj" % \
                                  proj_name)
            f = open(fil_name, "w")
            f.write("proj_notes = \"%s\"" % proj_notes)
            f.write("\nfil_labels = r\"%s\"" % fil_labels)
            f.write("\nfil_css = r\"%s\"" % fil_css)
            f.write("\nfil_report = r\"%s\"" % fil_report)
            f.write("\nfil_script = r\"%s\"" % fil_script)
            f.write("\ndefault_dbe = \"%s\"" % default_dbe)
            f.write("\n\ndefault_dbs = " + pprint.pformat(default_dbs))
            f.write("\n\ndefault_tbls = " + pprint.pformat(default_tbls))
            f.write("\n\nconn_dets = " + pprint.pformat(conn_dets))
            f.close()
            if self.new_proj:
                self.parent.parent.SetProj(proj_name)
        self.Destroy()
        self.SetReturnCode(wx.ID_OK) # only for dialogs 
        # (MUST come after Destroy)
        
