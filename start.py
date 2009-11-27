#! /usr/bin/env python
# -*- coding: utf-8 -*-

dev_debug = False
test_lang = False

import warnings
warnings.simplefilter('ignore', DeprecationWarning)

import wx
import gettext
import os
import platform
import shutil
from pysqlite2 import dbapi2 as sqlite
import sys

# All i18n except for wx-based (which MUST happen after wx.App init)
# http://wiki.wxpython.org/RecipesI18n
# Install gettext.  Now all strings enclosed in "_()" will automatically be
# translated.
gettext.install('sofa', './locale', unicode=True)
import my_globals # has translated text
import dataselect
import full_html
import getdata
import importer
import make_table_gui
import projects
import projselect
import quotes
import stats_select
import util

COPYRIGHT = u"\u00a9"
MAX_HELP_TEXT_WIDTH = 400 # pixels
TEXT_BROWN = (90, 74, 61)
MAIN_LEFT = 200
HELP_TEXT_TOP = 288
HELP_TEXT_WIDTH = 570
HELP_IMG_LEFT = 640
HELP_IMG_TOP = 315
SCRIPT_PATH = my_globals.SCRIPT_PATH
LOCAL_PATH = my_globals.LOCAL_PATH

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
    # add words to it until its width is too long then put int split
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
    Install local set of files in user home dir if necessary.
    Modify default project settings to point to local (user) SOFA  directory.
    """
    prog_path = os.path.dirname(__file__)
    default_proj = os.path.join(LOCAL_PATH, u"projs", 
                                my_globals.SOFA_DEFAULT_PROJ)
    paths = [u"css", my_globals.INTERNAL_FOLDER, u"vdts", u"projs", u"reports", 
             u"scripts"]
    if not os.path.exists(LOCAL_PATH):
            # In Windows these steps are completed by the installer - but only
            # for the first user.
            # create required folders
            for path in paths:
                os.makedirs(os.path.join(LOCAL_PATH, path))
            # copy across default proj, vdts, css
            shutil.copy(os.path.join(prog_path, "css", "alt_style.css"), 
                        os.path.join(LOCAL_PATH, "css", "alt_style.css"))
            shutil.copy(os.path.join(prog_path, u"css", 
                                     my_globals.SOFA_DEFAULT_STYLE), 
                        os.path.join(LOCAL_PATH, u"css", 
                                     my_globals.SOFA_DEFAULT_STYLE))
            shutil.copy(os.path.join(prog_path, my_globals.INTERNAL_FOLDER, 
                                     my_globals.SOFA_DEFAULT_DB), 
                        os.path.join(LOCAL_PATH, my_globals.INTERNAL_FOLDER, 
                                     my_globals.SOFA_DEFAULT_DB))
            shutil.copy(os.path.join(prog_path, u"vdts", 
                                     my_globals.SOFA_DEFAULT_VDTS), 
                        os.path.join(LOCAL_PATH, u"vdts", 
                                     my_globals.SOFA_DEFAULT_VDTS))
            shutil.copy(os.path.join(prog_path, u"projs", 
                                     my_globals.SOFA_DEFAULT_PROJ), 
                        default_proj)
    PROJ_CUSTOMISED_FILE = "proj_file_customised.txt"
    if not os.path.exists(os.path.join(LOCAL_PATH, PROJ_CUSTOMISED_FILE)):
        # change home username
        f = file(default_proj, "r")
        proj_str = f.read() # provided by me - no BOM on non-ascii 
        f.close()
        for path in paths:
            new_str = util.escape_win_path(os.path.join(LOCAL_PATH, path, ""))
            proj_str = proj_str.replace("/home/g/sofa/%s/" % path, new_str)
        # add MS Access and SQL Server into mix if Windows
        if util.in_windows():
            proj_str = proj_str.replace("default_dbs = {",
                                        "default_dbs = {'%s': None, " % \
                                            my_globals.DBE_MS_ACCESS)
            proj_str = proj_str.replace("default_tbls = {",
                                        "default_tbls = {'%s': None, " % \
                                            my_globals.DBE_MS_ACCESS)
            proj_str = proj_str.replace("default_dbs = {",
                                        "default_dbs = {'%s': None, " % \
                                            my_globals.DBE_MS_SQL)
            proj_str = proj_str.replace("default_tbls = {",
                                        "default_tbls = {'%s': None, " % \
                                            my_globals.DBE_MS_SQL)
        f = file(default_proj, "w")
        f.write(proj_str)
        f.close()
        # create file as tag we have done the changes to the proj file
        f = file(os.path.join(LOCAL_PATH, PROJ_CUSTOMISED_FILE), "w")
        f.write("Local project file customised successfully :-)")
        f.close()


class SofaApp(wx.App):

    def __init__(self):
        # if wanting to initialise the parent class it must be run in 
        # child __init__ and nowhere else.
        if dev_debug:
            redirect = False
            filename = None
        else:
            redirect = True
            unused, local_path = util.get_user_paths()
            filename = os.path.join(local_path, my_globals.INTERNAL_FOLDER, 
                                    'output.txt')
        wx.App.__init__(self, redirect=redirect, filename=filename)

    def OnInit(self):
        # http://wiki.wxpython.org/RecipesI18n
        path = sys.path[0].decode(sys.getfilesystemencoding())
        langdir = os.path.join(path,u'locale')
        langid = wx.LANGUAGE_GALICIAN if test_lang else wx.LANGUAGE_DEFAULT
        # the next line will only work if the locale is installed on the computer
        mylocale = wx.Locale(langid) #, wx.LOCALE_LOAD_DEFAULT)
        canon_name = mylocale.GetCanonicalName() # e.g. en_NZ, gl_ES etc
        # want main title to be right size but some languages too long for that
        self.main_font_size = 20 if canon_name.startswith('en_') else 16
        mytrans = gettext.translation('sofa', langdir, languages=[canon_name], 
                                      fallback = True)
        mytrans.install()
        if platform.system() == 'Linux':
            try:
                # to get some language settings to display properly:
                os.environ['LANG'] = u"%s.UTF-8" % canon_name
            except (ValueError, KeyError):
                pass
        frame = StartFrame(self.main_font_size)
        frame.CentreOnScreen(wx.VERTICAL) # on dual monitor, 
            # wx.BOTH puts in screen 2 (in Ubuntu at least)!
        frame.Show()
        self.SetTopWindow(frame)
        return True


class StartFrame(wx.Frame):
    
    def __init__(self, main_font_size):
        self.main_font_size = main_font_size
        # Gen set up
        wx.Frame.__init__(self, None, title=_("SOFA Start"), size=(900, 600),
              style=wx.CAPTION|wx.CLOSE_BOX|wx.MINIMIZE_BOX|wx.SYSTEM_MENU)
        # Windows doesn't include window decorations
        y_start = self.GetClientSize()[1] - self.GetSize()[1]
        self.SetClientSize(self.GetSize())
        self.panel = wx.Panel(self)
        self.InitComTypes(self.panel)
        self.panel.Bind(wx.EVT_PAINT, self.OnPaint)
        # icon
        ib = wx.IconBundle()
        tinysofa = os.path.join(SCRIPT_PATH, u"images", u"tinysofa.xpm")
        ib.AddIconFromFile(tinysofa, wx.BITMAP_TYPE_XPM)
        self.SetIcons(ib)
        # background image
        img_sofa = wx.Image(os.path.join(SCRIPT_PATH, "images", "sofa2.xpm"), 
                            wx.BITMAP_TYPE_XPM)
        self.bmp_sofa = wx.BitmapFromImage(img_sofa)
        # slice of image to be refreshed (where text and image will be)
        self.blank_wallpaper = \
            self.bmp_sofa.GetSubBitmap(wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, 
                                               HELP_IMG_LEFT+60, 250))
        self.blank_proj_strip = self.bmp_sofa.GetSubBitmap(wx.Rect(MAIN_LEFT, 
                                                                218, 490, 30))
        # buttons
        font_buttons = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD)
        g = GetNextYPos(284, 34)
        btn_x_pos = 5
        bmp_btn_proj = TextOnBitmap(GetBlankButtonBitmap(), 
                                    _("Select Project"), 
                                    font_buttons, "white")
        self.btnProj = wx.BitmapButton(self.panel, -1, bmp_btn_proj, 
                                       pos=(btn_x_pos, g.next()))
        self.btnProj.Bind(wx.EVT_BUTTON, self.OnProjClick)
        self.btnProj.Bind(wx.EVT_ENTER_WINDOW, self.OnProjEnter)
        self.btnProj.SetDefault()
        bmp_btn_enter = TextOnBitmap(GetBlankButtonBitmap(), 
                                     _("Enter/Edit Data"), 
                                     font_buttons, "white")
        self.btnEnter = wx.BitmapButton(self.panel, -1, bmp_btn_enter, 
                                        pos=(btn_x_pos, g.next()))
        self.btnEnter.Bind(wx.EVT_BUTTON, self.OnEnterClick)
        self.btnEnter.Bind(wx.EVT_ENTER_WINDOW, self.OnEnterEnter)       
        bmp_btn_import = TextOnBitmap(GetBlankButtonBitmap(), 
                                      _("Import Data"), 
                                      font_buttons, "white")
        self.btnImport = wx.BitmapButton(self.panel, -1, bmp_btn_import, 
                                         pos=(btn_x_pos, g.next()))
        self.btnImport.Bind(wx.EVT_BUTTON, self.OnImportClick)
        self.btnImport.Bind(wx.EVT_ENTER_WINDOW, self.OnImportEnter)
        bmp_btn_tables = TextOnBitmap(GetBlankButtonBitmap(),
                                      _("Report Tables"), 
                                      font_buttons, "white")
        self.btnTables = wx.BitmapButton(self.panel, -1, bmp_btn_tables, 
                                         pos=(btn_x_pos, g.next()))
        self.btnTables.Bind(wx.EVT_BUTTON, self.OnTablesClick)
        self.btnTables.Bind(wx.EVT_ENTER_WINDOW, self.OnTablesEnter)
        bmp_btn_charts = TextOnBitmap(GetBlankButtonBitmap(), 
                                      _("Charts"), 
                                      font_buttons, "white")
        self.btnCharts = wx.BitmapButton(self.panel, -1, bmp_btn_charts, 
                                         pos=(btn_x_pos, g.next()))
        self.btnCharts.Bind(wx.EVT_BUTTON, self.OnChartsClick)
        self.btnCharts.Bind(wx.EVT_ENTER_WINDOW, self.OnChartsEnter)
        bmp_btn_stats = TextOnBitmap(GetBlankButtonBitmap(),
                                     _("Statistics"), 
                                     font_buttons, "white")
        self.btnStatistics = wx.BitmapButton(self.panel, -1, bmp_btn_stats, 
                                             pos=(btn_x_pos, g.next()))
        self.btnStatistics.Bind(wx.EVT_BUTTON, self.OnStatsClick)
        self.btnStatistics.Bind(wx.EVT_ENTER_WINDOW, self.OnStatsEnter)
        bmp_btn_exit = TextOnBitmap(GetBlankButtonBitmap(), 
                                    _("Exit"), 
                                    font_buttons, "white")
        self.btnExit = wx.BitmapButton(self.panel, -1, bmp_btn_exit, 
                                       pos=(btn_x_pos, g.next()))
        self.btnExit.Bind(wx.EVT_BUTTON, self.OnExitClick)
        self.btnExit.Bind(wx.EVT_ENTER_WINDOW, self.OnExitEnter)
        # text
        # NB cannot have transparent background properly in Windows if using
        # a static ctrl 
        # http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3045245
        self.txtWelcome = _("Welcome to SOFA.  Hover the mouse over the "
            "buttons on the left to see what you can do.")
        # help images
        img_proj = wx.Image(os.path.join(SCRIPT_PATH, u"images", 
                                         u"briefcase.xpm"), wx.BITMAP_TYPE_XPM)
        self.bmp_proj = wx.BitmapFromImage(img_proj)
        img_data = wx.Image(os.path.join(SCRIPT_PATH, u"images", u"data.xpm"), 
                            wx.BITMAP_TYPE_XPM)
        self.bmp_data = wx.BitmapFromImage(img_data)
        img_import = wx.Image(os.path.join(SCRIPT_PATH, u"images", u"import.xpm"), 
                              wx.BITMAP_TYPE_XPM)
        self.bmp_import = wx.BitmapFromImage(img_import)
        img_tabs = wx.Image(os.path.join(SCRIPT_PATH, u"images", u"table.xpm"), 
                            wx.BITMAP_TYPE_XPM)
        self.bmp_tabs = wx.BitmapFromImage(img_tabs)
        chart = os.path.join(SCRIPT_PATH, u"images", u"demo_chart.xpm")
        img_chart = wx.Image(chart, wx.BITMAP_TYPE_XPM)
        self.bmp_chart = wx.BitmapFromImage(img_chart)
        img_stats = wx.Image(os.path.join(SCRIPT_PATH, u"images", u"stats.xpm"), 
                            wx.BITMAP_TYPE_XPM)
        self.bmp_stats = wx.BitmapFromImage(img_stats)
        psal = os.path.join(SCRIPT_PATH, u"images", u"psal_logo.xpm")
        img_psal = wx.Image(psal, wx.BITMAP_TYPE_XPM)
        self.bmp_psal = wx.BitmapFromImage(img_psal)
        self.HELP_TEXT_FONT = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL)
        self.active_proj = my_globals.SOFA_DEFAULT_PROJ
    
    def InitComTypes(self, panel):
        """
        If first time opened, and in Windows, warn user about delay setting 
            up (comtypes).
        """
        COMTYPES_HANDLED = u"comtypes_handled.txt"
        if util.in_windows() and not os.path.exists(os.path.join(LOCAL_PATH, 
                                                            COMTYPES_HANDLED)):
            wx.MessageBox(_("Click OK to prepare for first use of SOFA "
                          "Statistics.\n\nPreparation may take a moment ..."))
            h = full_html.FullHTML(panel, (10, 10))
            h.ShowHTML("")
            h = None
        if not os.path.exists(os.path.join(LOCAL_PATH, COMTYPES_HANDLED)):
            # create file as tag we have done the changes to the proj file
            f = file(os.path.join(LOCAL_PATH, COMTYPES_HANDLED), "w")
            f.write(u"Comtypes handled successfully :-)")
            f.close()
    
    def OnPaint(self, event):
        """
        Cannot use static bitmaps and static text to replace.  In windows
            doesn't show background wallpaper.
        NB painting like this sets things behind the controls.
        """
        panel_dc = wx.PaintDC(self.panel)
        panel_dc.DrawBitmap(self.bmp_sofa, 0, 0, True)
        panel_dc.DrawBitmap(self.bmp_import, HELP_IMG_LEFT-30, HELP_IMG_TOP-20, 
                            True)
        panel_dc.SetTextForeground(wx.WHITE)
        panel_dc.SetFont(wx.Font(8, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel(_("Version %s") % my_globals.VERSION, 
                           wx.Rect(MAIN_LEFT, 9, 100, 20))   
        panel_dc.SetFont(wx.Font(self.main_font_size, wx.SWISS, wx.NORMAL, 
                                 wx.NORMAL))
        panel_dc.DrawLabel(_("Statistics Open For All"), 
                           wx.Rect(MAIN_LEFT, 80, 100, 100))
        panel_dc.SetFont(wx.Font(9, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.SetTextForeground(TEXT_BROWN)
        panel_dc.DrawLabel(_("SOFA - Statistics Open For All"
           "\nthe user-friendly, open-source statistics,\nanalysis & "
           "reporting package"), 
           wx.Rect(MAIN_LEFT, 115, 100, 100))
        panel_dc.DrawLabel(GetTextToDraw(self.txtWelcome, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 
                                   260))
        panel_dc.SetTextForeground(wx.WHITE)
        panel_dc.SetFont(wx.Font(7, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel("SOFA\nPaton-Simpson & Associates Ltd" + \
                           "\nAuckland, New Zealand", 
                           wx.Rect(MAIN_LEFT, 547, 100, 50))
        panel_dc.DrawLabel("%s 2009 Paton-Simpson & Associates Ltd" % COPYRIGHT, 
                           wx.Rect(600, 560, 100, 50))
        panel_dc.DrawBitmap(self.bmp_psal, 155, 542, True)
        # make default db if not already there
        connSqlite = sqlite.connect(os.path.join(LOCAL_PATH, 
                                                 my_globals.INTERNAL_FOLDER, 
                                                 my_globals.SOFA_DEFAULT_DB))
        connSqlite.close()
        panel_dc.DrawBitmap(self.blank_proj_strip, MAIN_LEFT, 218, False)
        panel_dc.SetTextForeground(wx.WHITE)
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel(_("Currently using ") +
                           "\"%s\"" % self.active_proj[:-5] + 
                           _(" Project settings"),
                           wx.Rect(MAIN_LEFT, 247, 400, 30))
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
        panel_dc.DrawBitmap(self.blank_wallpaper, MAIN_LEFT, HELP_TEXT_TOP, 
                            False)

    def OnProjEnter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.DrawBlankWallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_proj, HELP_IMG_LEFT, HELP_IMG_TOP, True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_projs = _("Projects are a way of storing all related reports, "
            "data files, and configuration info in one place.  The "
            "default project will be OK to get you started.")
        panel_dc.DrawLabel(GetTextToDraw(txt_projs, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 
                                   260))
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
        panel_dc.DrawBitmap(self.bmp_data, HELP_IMG_LEFT-30, HELP_IMG_TOP-20, 
                            True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_entry = _("Enter data into a fresh dataset or select an existing "
            "one to edit or add data to.")
        panel_dc.DrawLabel(GetTextToDraw(txt_entry, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 
                                   260))
        event.Skip()

    def OnImportClick(self, event):
        # open import data dialog
        dlg = importer.ImportFileSelectDlg(self)
        dlg.ShowModal()
        event.Skip()
        
    def OnImportEnter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.DrawBlankWallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_import, HELP_IMG_LEFT-40, HELP_IMG_TOP, 
                            True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_entry = _("Import data e.g. an Excel spreadsheet or a csv file.")
        panel_dc.DrawLabel(GetTextToDraw(txt_entry, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH-10, 
                                   260))
        event.Skip()
        
    def OnTablesClick(self, event):
        "Open make table gui with settings as per active_proj"
        proj_name = self.active_proj
        proj_dic = projects.GetProjSettingsDic(proj_name)
        try:
            dlg = make_table_gui.DlgMakeTable( 
                proj_dic["default_dbe"], proj_dic["conn_dets"], 
                proj_dic["default_dbs"], proj_dic["default_tbls"], 
                proj_dic["fil_var_dets"], proj_dic["fil_css"], 
                proj_dic["fil_report"], proj_dic["fil_script"])
        except Exception, e:
            wx.MessageBox(_("Unable to connect to data as defined in " 
                "project %s.  Please check your settings." % proj_name))
            raise Exception, unicode(e)
            return
        dlg.ShowModal()
        event.Skip()
        
    def OnTablesEnter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.DrawBlankWallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_tabs, HELP_IMG_LEFT-40, HELP_IMG_TOP-25, 
                            True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_tabs1 = _("Make report tables e.g. Age vs Gender")
        panel_dc.DrawLabel(GetTextToDraw(txt_tabs1, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 
                                   260))       
        txt_tabs2 = _("Can make simple Frequency Tables, "
            "Summary Tables (mean, median, N, standard deviation, sum), "
            "and simple tabular reports of data as found in data source "
            "(with labels and optional totals).")
        panel_dc.DrawLabel(GetTextToDraw(txt_tabs2, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, HELP_TEXT_TOP+30, HELP_TEXT_WIDTH, 
                                   260))
        event.Skip()
    
    def OnChartsClick(self, event):
        wx.MessageBox(_("Not available yet in version ") + 
                      unicode(my_globals.VERSION))
        event.Skip()
        
    def OnChartsEnter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.DrawBlankWallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_chart, HELP_IMG_LEFT-30, HELP_IMG_TOP-20, 
                            True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_charts = _("Make attractive charts e.g. a pie chart of regions")
        panel_dc.DrawLabel(GetTextToDraw(txt_charts, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 
                                   260))
        event.Skip()
    
    def OnStatsClick(self, event):  
        # open statistics selection dialog
        proj_name = self.active_proj
        proj_dic = projects.GetProjSettingsDic(proj_name)
        dlg = stats_select.StatsSelectDlg(proj_name, 
            proj_dic["default_dbe"], proj_dic["conn_dets"], 
            proj_dic["default_dbs"], proj_dic["default_tbls"], 
            proj_dic["fil_var_dets"], proj_dic["fil_css"], 
            proj_dic["fil_report"], proj_dic["fil_script"])
        dlg.ShowModal()
        event.Skip()
        
    def OnStatsEnter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.DrawBlankWallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_stats, HELP_IMG_LEFT-30, HELP_IMG_TOP-20, 
                            True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_stats1 = _("Run statistical tests on your data - e.g. a "
            "Chi Square to see if there is a relationship between "
            "age group and gender.")
        panel_dc.DrawLabel(GetTextToDraw(txt_stats1, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 
                                   260))
        txt_stats2 = _("SOFA focuses on the statistical tests most users "
            "need most of the time.")
        panel_dc.DrawLabel(GetTextToDraw(txt_stats2, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, HELP_TEXT_TOP + 76, 
                                   HELP_TEXT_WIDTH, 320))
        txt_stats3 = "QUOTE:"
        panel_dc.DrawLabel(GetTextToDraw(txt_stats3, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, HELP_TEXT_TOP + 121, 
                                   HELP_TEXT_WIDTH, 320))
        txt_stats4 = "%s (%s)" % quotes.get_quote()
        panel_dc.DrawLabel(GetTextToDraw(txt_stats4, MAX_HELP_TEXT_WIDTH - 20), 
                           wx.Rect(MAIN_LEFT + 10, HELP_TEXT_TOP + 141, 
                                   HELP_TEXT_WIDTH-10, 320))
        event.Skip()
    
    def OnExitClick(self, event):
        self.Destroy()
        sys.exit()
        
    def OnExitEnter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.DrawBlankWallpaper(panel_dc)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_exit = _("Exit SOFA Statistics")
        panel_dc.DrawLabel(GetTextToDraw(txt_exit, MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 
                                   260))
        event.Skip()

InstallLocal()
app = SofaApp()
try:
    app.MainLoop()
finally:
    del app
