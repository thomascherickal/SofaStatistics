#! /usr/bin/env python
# -*- coding: utf-8 -*-

import warnings
warnings.simplefilter('ignore', DeprecationWarning)

import os
import shutil
from pysqlite2 import dbapi2 as sqlite
import sys
import wx

import dataselect
import full_html
import getdata
import make_table_gui
import projects
import projselect
import util

VERSION = "0.7.3"

COPYRIGHT = "\xa9" if util.in_windows() else "©"
MAX_HELP_TEXT_WIDTH = 350 # pixels
TEXT_BROWN = (90, 74, 61)
MAIN_LEFT = 170
SCRIPT_PATH = util.get_script_path()
USER_PATH, LOCAL_PATH = util.get_user_paths()

def TextOnBitmap(bitmap, text, font, colour):
    """
    Add short text to bitmap with standard left margin.
    Can then use bitmap for a bitmap button.
    See http://wiki.wxpython.org/index.cgi/WorkingWithImages
    """
    mem = wx.MemoryDC()
    mem.SelectObject(bitmap)
    mem.SetFont(font)
    mem.SetTextForeground(colour)
    mem.DrawText(text, 9, 3)
    mem.SelectObject(wx.NullBitmap)
    return bitmap

def GetTextToDraw(orig_txt, max_width):
    "Return text broken into new lines so wraps within pixel width"
    mem = wx.MemoryDC()
    # add words to it until its width is tooNeed Dun long then put int split
    lines = []
    words = orig_txt.split()
    line_words = []
    for word in words:
        line_words.append(word)
        line_width = mem.GetTextExtent(" ".join(line_words))[0]
        if line_width > max_width:
            line_words.pop()
            lines.append(" ".join(line_words))
            line_words = [word]
    lines.append(" ".join(line_words))
    wrapped_txt = "\n".join(lines)
    return wrapped_txt

def GetBlankButtonBitmap():
    return wx.Image(os.path.join(SCRIPT_PATH, "images", "blankbutton.xpm"), 
                    wx.BITMAP_TYPE_XPM).ConvertToBitmap()

def GetNextYPos(start, height):
    "Facilitate regular y position of buttons"
    i = 0
    while True:
        yield start + (i*height)
        i += 1

def InstallLocal():
    """
    Install local set of files in user home dir if necessary (not on Windows).
    Modify default project settings to point to local (user) SOFA  directory.
    """
    sofa_prog_path = os.path.join(util.get_prog_path(), "sofa")
    default_proj = os.path.join(LOCAL_PATH, "projs",  
                                "SOFA_Default_Project.proj")
    paths = ["css", projects.INTERNAL_FOLDER, "lbls", "projs", "reports", 
             "scripts"]
    if not os.path.exists(LOCAL_PATH):
            # in Windows these steps are all completed by the installer
            # create required folders
            for path in paths:
                os.makedirs(os.path.join(LOCAL_PATH, path))
            # copy across default proj, lbls, css
            shutil.copy(os.path.join(sofa_prog_path, "css", "alt_style.css"), 
                        os.path.join(LOCAL_PATH, "css", "alt_style.css"))
            shutil.copy(os.path.join(sofa_prog_path, "css", 
                                     "SOFA_Default_Style.css"), 
                        os.path.join(LOCAL_PATH, "css", 
                                     "SOFA_Default_Style.css"))
            shutil.copy(os.path.join(sofa_prog_path, projects.INTERNAL_FOLDER, 
                                     "SOFA_Default_db"), 
                        os.path.join(LOCAL_PATH, projects.INTERNAL_FOLDER, 
                                     "SOFA_Default_db"))
            shutil.copy(os.path.join(sofa_prog_path, "lbls", 
                                     "SOFA_Default_Labels.lbls"), 
                        os.path.join(LOCAL_PATH, "lbls", 
                                     "SOFA_Default_Labels.lbls"))
            shutil.copy(os.path.join(sofa_prog_path, "projs", 
                                     "SOFA_Default_Project.proj"), 
                        default_proj)
    PROJ_CUSTOMISED_FILE = "proj_file_customised.txt"
    if not os.path.exists(os.path.join(LOCAL_PATH, PROJ_CUSTOMISED_FILE)):
        # change home username
        f = file(default_proj, "r")
        proj_str = f.read()
        f.close()
        for path in paths:
            proj_str = proj_str.replace("/home/g/sofa/%s/" % path, 
                                        os.path.join(LOCAL_PATH, path, ""))
        # add MS Access into mix if Windows
        if util.in_windows():
            proj_str = proj_str.replace("default_dbs = {",
                                        "default_dbs = {'%s': None, " % \
                                            getdata.DBE_MS_ACCESS)
            proj_str = proj_str.replace("default_tbls = {",
                                        "default_tbls = {'%s': None, " % \
                                            getdata.DBE_MS_ACCESS)
        f = file(default_proj, "w")
        f.write(proj_str)
        f.close()
        # create file as tag we have done the changes to the proj file
        f = file(os.path.join(LOCAL_PATH, PROJ_CUSTOMISED_FILE), "w")
        f.write("Local project file customised successfully :-)")
        f.close()


class SofaApp(wx.App):

    dev_debug = False

    def __init__(self):        
        # if wanting to initialise the parent class it must be run in child __init__ and nowhere else
        if self.dev_debug:
            redirect = False
            filename = None
        else:
            redirect = True
            _, local_path = util.get_user_paths()
            filename = os.path.join(local_path, projects.INTERNAL_FOLDER, 
                                    'output.txt')
        wx.App.__init__(self, redirect=redirect, filename=filename) 

    def OnInit(self):
        frame = StartFrame()
        frame.CentreOnScreen()
        frame.Show()
        self.SetTopWindow(frame)
        return True


class StartFrame(wx.Frame):
    
    def __init__(self):
        wx.Frame.__init__(self, None, title="SOFA Start", size=(800, 542),
              style=wx.CAPTION|wx.CLOSE_BOX|wx.MINIMIZE_BOX|wx.SYSTEM_MENU,
              pos=(100, 100))
        y_start = self.GetClientSize()[1] - self.GetSize()[1]
        self.SetClientSize(self.GetSize()) # Windows doesn't include window decorations
        self.panel = wx.Panel(self)
        self.InitComTypes(self.panel)
        self.panel.Bind(wx.EVT_PAINT, self.OnPaint)        
        # icon
        ib = wx.IconBundle()
        ib.AddIconFromFile(os.path.join(SCRIPT_PATH, 
                                        "images", 
                                        "tinysofa.xpm"), 
                           wx.BITMAP_TYPE_XPM)
        self.SetIcons(ib)        
        # background image
        img_sofa = wx.Image(os.path.join(SCRIPT_PATH, "images", "sofa2.xpm"), 
                            wx.BITMAP_TYPE_XPM)
        self.bmp_sofa = wx.BitmapFromImage(img_sofa)
        # slice of image to be refreshed (where text and image will be)
        self.blank_wallpaper = self.bmp_sofa.GetSubBitmap(wx.Rect(MAIN_LEFT, 248, 
                                                                  630, 250))
        self.blank_proj_strip = self.bmp_sofa.GetSubBitmap(wx.Rect(MAIN_LEFT, 218, 
                                                                   490, 30))
        # buttons
        font_buttons = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD)
        g = GetNextYPos(245, 34)
        btn_x_pos = 5
        bmp_btn_proj = TextOnBitmap(GetBlankButtonBitmap(), "Select project", 
                                    font_buttons, "white")
        self.btnProj = wx.BitmapButton(self.panel, -1, bmp_btn_proj, 
                                       pos=(btn_x_pos, g.next()))
        self.btnProj.Bind(wx.EVT_BUTTON, self.OnProjClick)
        self.btnProj.Bind(wx.EVT_ENTER_WINDOW, self.OnProjEnter)
        self.btnProj.SetDefault()
        bmp_btn_enter = TextOnBitmap(GetBlankButtonBitmap(), "Enter/Edit Data", 
                                     font_buttons, "white")
        self.btnEnter = wx.BitmapButton(self.panel, -1, bmp_btn_enter, 
                                        pos=(btn_x_pos, g.next()))
        self.btnEnter.Bind(wx.EVT_BUTTON, self.OnEnterClick)
        self.btnEnter.Bind(wx.EVT_ENTER_WINDOW, self.OnEnterEnter)       
        bmp_btn_import = TextOnBitmap(GetBlankButtonBitmap(), "Import Data", 
                                      font_buttons, "white")
        self.btnImport = wx.BitmapButton(self.panel, -1, bmp_btn_import, 
                                         pos=(btn_x_pos, g.next()))
        self.btnImport.Bind(wx.EVT_BUTTON, self.OnImportClick)
        self.btnImport.Bind(wx.EVT_ENTER_WINDOW, self.OnImportEnter)
        bmp_btn_tables = TextOnBitmap(GetBlankButtonBitmap(), "Make Tables", 
                                      font_buttons, "white")
        self.btnTables = wx.BitmapButton(self.panel, -1, bmp_btn_tables, 
                                         pos=(btn_x_pos, g.next()))
        self.btnTables.Bind(wx.EVT_BUTTON, self.OnTablesClick)
        self.btnTables.Bind(wx.EVT_ENTER_WINDOW, self.OnTablesEnter)       
        bmp_btn_charts = TextOnBitmap(GetBlankButtonBitmap(), "View Charts", 
                                      font_buttons, "white")
        self.btnCharts = wx.BitmapButton(self.panel, -1, bmp_btn_charts, 
                                         pos=(btn_x_pos, g.next()))
        self.btnCharts.Bind(wx.EVT_BUTTON, self.OnChartsClick)
        self.btnCharts.Bind(wx.EVT_ENTER_WINDOW, self.OnChartsEnter)
        bmp_btn_stats = TextOnBitmap(GetBlankButtonBitmap(), "Statistics", 
                                     font_buttons, "white")
        self.btnStatistics = wx.BitmapButton(self.panel, -1, bmp_btn_stats, 
                                             pos=(btn_x_pos, g.next()))
        self.btnStatistics.Bind(wx.EVT_BUTTON, self.OnStatsClick)
        self.btnStatistics.Bind(wx.EVT_ENTER_WINDOW, self.OnStatsEnter)
        bmp_btn_exit = TextOnBitmap(GetBlankButtonBitmap(), "Exit", 
                                    font_buttons, "white")
        self.btnExit = wx.BitmapButton(self.panel, -1, bmp_btn_exit, 
                                       pos=(btn_x_pos, g.next()))
        self.btnExit.Bind(wx.EVT_BUTTON, self.OnExitClick)
        self.btnExit.Bind(wx.EVT_ENTER_WINDOW, self.OnExitEnter)
        # text
        # NB cannot have transparent background properly in Windows if using
        # a static ctrl http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3045245
        self.txtWelcome = "Welcome to SOFA.  Hover the mouse over the " + \
            "buttons on the left to see what you can do."
        # help images
        img_proj = wx.Image(os.path.join(SCRIPT_PATH, "images", "briefcase.xpm"), 
                            wx.BITMAP_TYPE_XPM)
        self.bmp_proj = wx.BitmapFromImage(img_proj)
        img_import = wx.Image(os.path.join(SCRIPT_PATH, "images", "briefcase.xpm"), 
                              wx.BITMAP_TYPE_XPM)
        self.bmp_import = wx.BitmapFromImage(img_import)
        img_tabs = wx.Image(os.path.join(SCRIPT_PATH, "images", "table.xpm"), 
                            wx.BITMAP_TYPE_XPM)
        self.bmp_tabs = wx.BitmapFromImage(img_tabs)
        img_chart = wx.Image(os.path.join(SCRIPT_PATH, "images", "demo_chart.xpm"), 
                              wx.BITMAP_TYPE_XPM)
        self.bmp_chart = wx.BitmapFromImage(img_chart)
        img_stats = wx.Image(os.path.join(SCRIPT_PATH, "images", "stats.xpm"), 
                            wx.BITMAP_TYPE_XPM)
        self.bmp_stats = wx.BitmapFromImage(img_stats)
        img_psal = wx.Image(os.path.join(SCRIPT_PATH, "images", "psal_logo.xpm"), 
                         wx.BITMAP_TYPE_XPM)
        self.bmp_psal = wx.BitmapFromImage(img_psal)
        self.HELP_TEXT_FONT = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL)
        self.active_proj = projects.SOFA_DEFAULT_PROJ
    
    def InitComTypes(self, panel):
        """
        If first time opened, and in Windows, warn user about delay setting 
            up (comtypes).
        """
        COMTYPES_HANDLED = "comtypes_handled.txt"
        if util.in_windows() and not os.path.exists(os.path.join(LOCAL_PATH, 
                                                            COMTYPES_HANDLED)):
            wx.MessageBox("Click OK to prepare for first use of SOFA Statistics.\n\n" + \
                          "Preparation may take a moment ...")
            h = full_html.FullHTML(panel, (10, 10))
            h.ShowHTML("")
            h = None
        if not os.path.exists(os.path.join(LOCAL_PATH, COMTYPES_HANDLED)):
            # create file as tag we have done the changes to the proj file
            f = file(os.path.join(LOCAL_PATH, COMTYPES_HANDLED), "w")
            f.write("Comtypes handled successfully :-)")
            f.close()
    
    def OnPaint(self, event):
        """
        Cannot use static bitmaps and static text to replace.  In windows
            doesn't show background wallpaper.
        NB painting like this sets things behind the controls.
        """
        panel_dc = wx.PaintDC(self.panel)
        panel_dc.DrawBitmap(self.bmp_sofa, 0, 0, True)
        panel_dc.DrawBitmap(self.bmp_chart, 540, 260, True)
        panel_dc.SetTextForeground(wx.WHITE)
        panel_dc.SetFont(wx.Font(8, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel("Version %s" % VERSION, 
                           wx.Rect(MAIN_LEFT, 6, 100, 20))   
        panel_dc.SetFont(wx.Font(16, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel("Statistics Open For All", 
                           wx.Rect(MAIN_LEFT, 70, 100, 100))
        panel_dc.SetFont(wx.Font(9, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.SetTextForeground(TEXT_BROWN)
        panel_dc.DrawLabel("SOFA - Statistics Open For All" + \
           "\nthe user-friendly, open-source statistics,\nanalysis & reporting package", 
           wx.Rect(MAIN_LEFT, 105, 100, 100))
        panel_dc.DrawLabel(GetTextToDraw(self.txtWelcome, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, 248, 540, 260))
        panel_dc.SetTextForeground(wx.WHITE)
        panel_dc.SetFont(wx.Font(7, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel("SOFA\nPaton-Simpson & Associates Ltd\nAuckland, New Zealand", 
                           wx.Rect(MAIN_LEFT, 497, 100, 50))
        panel_dc.DrawLabel("%s 2009 Paton-Simpson & Associates Ltd" % COPYRIGHT, 
                           wx.Rect(500, 522, 100, 50))
        panel_dc.DrawBitmap(self.bmp_psal, 125, 492, True)
        # make default db if not already there
        connSqlite = sqlite.connect(os.path.join(LOCAL_PATH, 
                                                 projects.INTERNAL_FOLDER, 
                                                 projects.SOFA_DEFAULT_DB))
        connSqlite.close()
        panel_dc.DrawBitmap(self.blank_proj_strip, MAIN_LEFT, 218, False)
        panel_dc.SetTextForeground(wx.WHITE)
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel("Currently using \"%s\" Project settings" % 
                               self.active_proj[:-5],
                           wx.Rect(MAIN_LEFT, 218, 400, 30))
        event.Skip()
    
    def SetProj(self, proj_text=""):
        "proj_text must NOT have .proj on the end"
        self.active_proj = "%s.proj" % proj_text
        self.Refresh()
        
    def OnProjClick(self, event):
        proj_fils = projects.GetProjs() # should always be the default present
        # open proj selection form
        dlgProj = projselect.ProjSelectDlg(self, proj_fils)
        dlgProj.ShowModal()
        dlgProj.Destroy()
        event.Skip()

    def DrawBlankWallpaper(self, panel_dc):
        panel_dc.DrawBitmap(self.blank_wallpaper, MAIN_LEFT, 248, False)

    def OnProjEnter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.DrawBlankWallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_proj, 570, 280, True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_projs = "Projects are a way of storing all related reports, " + \
            "data files, and configuration info in one place.  The " + \
            "default project will be OK to get you started."
        panel_dc.DrawLabel(GetTextToDraw(txt_projs, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, 248, 540, 260))
        event.Skip()
    
    def OnEnterClick(self, event):
        # open proj selection form
        proj_name = self.active_proj
        dlgData = dataselect.DataSelectDlg(self, proj_name)
        dlgData.ShowModal()
        dlgData.Destroy()
        event.Skip()
        
    def OnEnterEnter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.DrawBlankWallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_chart, 540, 260, True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_entry = "Enter data into a fresh dataset or select an existing " + \
            "one to edit or add data to."
        panel_dc.DrawLabel(GetTextToDraw(txt_entry, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, 248, 540, 260))
        event.Skip()

    def OnImportClick(self, event):
        # open import data dialog
        pass
        event.Skip()
        
    def OnImportEnter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.DrawBlankWallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_import, 540, 260, True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_entry = "Import data e.g. a spreadsheets, csv file, or SPSS."
        panel_dc.DrawLabel(GetTextToDraw(txt_entry, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, 248, 540, 260))
        event.Skip()
        
    def OnTablesClick(self, event):
        "Open make table gui with settings as per active_proj"
        proj_dic = projects.GetProjSettingsDic(proj_name=self.active_proj)
        dlg = make_table_gui.DlgMakeTable("Make Table", 
            proj_dic["default_dbe"], proj_dic["conn_dets"], 
            proj_dic["default_dbs"], proj_dic["default_tbls"], 
            proj_dic["fil_labels"], proj_dic["fil_css"], 
            proj_dic["fil_report"], proj_dic["fil_script"])
        dlg.ShowModal()
        event.Skip()
        
    def OnTablesEnter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.DrawBlankWallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_tabs, 530, 255, True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_tabs = "Make tables e.g. Age vs Gender"
        panel_dc.DrawLabel(GetTextToDraw(txt_tabs, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, 248, 540, 260))
        event.Skip()
    
    def OnChartsClick(self, event):
        wx.MessageBox("Not available yet in version %s" % VERSION)
        event.Skip()
        
    def OnChartsEnter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.DrawBlankWallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_chart, 540, 260, True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_charts = "Make attractive charts e.g. a pie chart of regions"
        panel_dc.DrawLabel(GetTextToDraw(txt_charts, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, 248, 540, 260))
        event.Skip()
    
    def OnStatsClick(self, event):        
        wx.MessageBox("Not available yet in version %s" % VERSION)
        event.Skip()
        
    def OnStatsEnter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.DrawBlankWallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_stats, 500, 260, True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_stats1 = "Run statistical tests on your data e.g. a Chi Square " + \
            "to see if there is a relationship between age and gender."
        panel_dc.DrawLabel(GetTextToDraw(txt_stats1, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, 248, 540, 260))
        txt_stats2 = "SOFA focuses on the stats tests most users need most " + \
            "of the time."
        panel_dc.DrawLabel(GetTextToDraw(txt_stats2, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, 290, 540, 320))
        event.Skip()
    
    def OnExitClick(self, event):
        self.Destroy()
        sys.exit()
        
    def OnExitEnter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.DrawBlankWallpaper(panel_dc)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_exit = "Exit SOFA"
        panel_dc.DrawLabel(GetTextToDraw(txt_exit, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, 248, 540, 260))
        event.Skip()

InstallLocal()
app = SofaApp()
try:
    app.MainLoop()
finally:
    del app
