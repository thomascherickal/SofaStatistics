#! /usr/bin/env python
# -*- coding: utf-8 -*-

dev_debug = True
test_lang = False

import warnings
warnings.simplefilter('ignore', DeprecationWarning)
warnings.simplefilter('ignore', UserWarning)

import codecs
import gettext
import glob
import os
import platform
import shutil
from pysqlite2 import dbapi2 as sqlite
import sys
import wxversion
wxversion.select("2.8")
import wx
try:
    from agw import hyperlink as hl
except ImportError: # if it's not there locally, try the wxPython lib.
    try:
        import wx.lib.agw.hyperlink as hl
    except ImportError:
        raise Exception, ("There seems to be a problem related to your "
                          "wxpython package.")

# All i18n except for wx-based (which MUST happen after wx.App init)
# http://wiki.wxpython.org/RecipesI18n
# Install gettext.  Now all strings enclosed in "_()" will automatically be
# translated.
gettext.install('sofa', './locale', unicode=True)
import my_globals as mg # has translated text
import lib
import config_globals
import config_dlg
# importing delayed until needed where possible for startup performance
# import dataselect
import full_html
import getdata
# import importer
# import report_table
import projects
import projselect
import quotes
# import stats_select

COPYRIGHT = u"\u00a9"
SCREEN_WIDTH = 1000
TEXT_BROWN = (90, 74, 61)
TOP_TOP = 9
BTN_LEFT= 5
BTN_WIDTH = 170
BTN_RIGHT = SCREEN_WIDTH - (BTN_WIDTH + 18)
BTN_DROP = 40
MAIN_LEFT = 200
HELP_TEXT_TOP = 288
MAX_HELP_TEXT_WIDTH = 330 # pixels
HELP_TEXT_WIDTH = 330
HELP_IMG_LEFT = 575
HELP_IMG_TOP = 315
MAIN_RIGHT = 650
SCRIPT_PATH = mg.SCRIPT_PATH
LOCAL_PATH = mg.LOCAL_PATH

def get_blank_btn_bmp():
    return wx.Image(os.path.join(SCRIPT_PATH, u"images", u"blankbutton.xpm"), 
                    wx.BITMAP_TYPE_XPM).ConvertToBitmap()

def get_next_y_pos(start, height):
    "Facilitate regular y position of buttons"
    i = 0
    while True:
        yield start + (i*height)
        i += 1

def install_local():
    """
    Install local set of files in user home dir if necessary.
    Modify default project settings to point to local (user) SOFA  directory.
    """
    prog_path = os.path.dirname(__file__)
    default_proj = os.path.join(LOCAL_PATH, u"projs", mg.SOFA_DEFAULT_PROJ)
    paths = [u"css", mg.INTERNAL_FOLDER, u"vdts", u"projs", u"reports", 
             u"scripts"]
    if not os.path.exists(LOCAL_PATH):
            # In Windows these steps are completed by the installer - but only
            # for the first user.
            # create required folders
            for path in paths:
                os.makedirs(os.path.join(LOCAL_PATH, path))
            # copy across default proj, vdts, css
            shutil.copy(os.path.join(prog_path, u"css", u"alt_style.css"), 
                        os.path.join(LOCAL_PATH, u"css", u"alt_style.css"))
            shutil.copy(os.path.join(prog_path, u"css", mg.SOFA_DEFAULT_STYLE), 
                        os.path.join(LOCAL_PATH, u"css", mg.SOFA_DEFAULT_STYLE))
            shutil.copy(os.path.join(prog_path, mg.INTERNAL_FOLDER, 
                                     mg.SOFA_DEFAULT_DB), 
                        os.path.join(LOCAL_PATH, mg.INTERNAL_FOLDER, 
                                     mg.SOFA_DEFAULT_DB))
            shutil.copy(os.path.join(prog_path, u"vdts", mg.SOFA_DEFAULT_VDTS), 
                        os.path.join(LOCAL_PATH, u"vdts", mg.SOFA_DEFAULT_VDTS))
            shutil.copy(os.path.join(prog_path, u"projs", mg.SOFA_DEFAULT_PROJ), 
                        default_proj)
    PROJ_CUSTOMISED_FILE = u"proj_file_customised.txt"
    if not os.path.exists(os.path.join(LOCAL_PATH, PROJ_CUSTOMISED_FILE)):
        # change home username
        f = codecs.open(default_proj, "r", "utf-8")
        proj_str = f.read() # provided by me - no BOM or non-ascii 
        f.close()
        for path in paths:
            new_str = lib.escape_pre_write(os.path.join(LOCAL_PATH, path, u""))
            proj_str = proj_str.replace(u"/home/g/sofa/%s/" % path, new_str)
        # add MS Access and SQL Server into mix if Windows
        if mg.IN_WINDOWS:
            proj_str = proj_str.replace(u"default_dbs = {",
                                        u"default_dbs = {'%s': None, " % \
                                            mg.DBE_MS_ACCESS)
            proj_str = proj_str.replace(u"default_tbls = {",
                                        u"default_tbls = {'%s': None, " % \
                                            mg.DBE_MS_ACCESS)
            proj_str = proj_str.replace(u"default_dbs = {",
                                        u"default_dbs = {'%s': None, " % \
                                            mg.DBE_MS_SQL)
            proj_str = proj_str.replace(u"default_tbls = {",
                                        u"default_tbls = {'%s': None, " % \
                                            mg.DBE_MS_SQL)
        f = codecs.open(default_proj, "w", "utf-8")
        f.write(proj_str)
        f.close()
        # create file as tag we have done the changes to the proj file
        f = file(os.path.join(LOCAL_PATH, PROJ_CUSTOMISED_FILE), "w")
        f.write(u"Local project file customised successfully :-)")
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
            filename = os.path.join(mg.LOCAL_PATH, mg.INTERNAL_FOLDER, 
                                    u'output.txt')
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
        mg.MAX_HEIGHT = wx.Display().GetGeometry()[3]
        return True


class StartFrame(wx.Frame):
    
    def __init__(self, main_font_size):
        self.main_font_size = main_font_size
        # Gen set up
        wx.Frame.__init__(self, None, title=_("SOFA Start"), 
              size=(SCREEN_WIDTH, 600),
              style=wx.CAPTION|wx.CLOSE_BOX|wx.MINIMIZE_BOX|wx.SYSTEM_MENU)
        # Windows doesn't include window decorations
        y_start = self.GetClientSize()[1] - self.GetSize()[1]
        self.SetClientSize(self.GetSize())
        self.panel = wx.Panel(self, size=(SCREEN_WIDTH, 600)) # win
        self.panel.SetBackgroundColour(wx.Colour(205, 217, 215))
        self.panel.Bind(wx.EVT_PAINT, self.on_paint)
        self.init_com_types(self.panel)
        config_dlg.add_icon(frame=self)
        # background image
        sofa = os.path.join(SCRIPT_PATH, u"images", u"sofa2.xpm")
        self.bmp_sofa = wx.Image(sofa, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        # slice of image to be refreshed (where text and image will be)
        blankwp_rect = wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_IMG_LEFT+35, 250)
        self.blank_wallpaper = self.bmp_sofa.GetSubBitmap(blankwp_rect)
        blankps_rect = wx.Rect(MAIN_LEFT, 218, 610, 30)
        self.blank_proj_strip = self.bmp_sofa.GetSubBitmap(blankps_rect)
        # buttons
        font_buttons = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD)
        g = get_next_y_pos(284, BTN_DROP)
        # Proj
        bmp_btn_proj = lib.add_text_to_bitmap(get_blank_btn_bmp(), 
                        _("Select Project"), font_buttons, "white")
        self.btn_proj = wx.BitmapButton(self.panel, -1, bmp_btn_proj, 
                                        pos=(BTN_LEFT, g.next()))
        self.btn_proj.Bind(wx.EVT_BUTTON, self.on_proj_click)
        self.btn_proj.Bind(wx.EVT_ENTER_WINDOW, self.on_proj_enter)
        self.btn_proj.SetDefault()
        # Prefs
        bmp_btn_pref = lib.add_text_to_bitmap(get_blank_btn_bmp(), 
                       _("Preferences"), font_buttons, "white")
        self.btn_prefs = wx.BitmapButton(self.panel, -1, bmp_btn_pref, 
                                         pos=(BTN_LEFT, g.next()))
        self.btn_prefs.Bind(wx.EVT_BUTTON, self.on_prefs_click)
        self.btn_prefs.Bind(wx.EVT_ENTER_WINDOW, self.on_prefs_enter)
        # Data entry
        bmp_btn_enter = lib.add_text_to_bitmap(get_blank_btn_bmp(), 
                        _("Enter/Edit Data"), font_buttons, "white")
        self.btn_enter = wx.BitmapButton(self.panel, -1, bmp_btn_enter, 
                                         pos=(BTN_LEFT, g.next()))
        self.btn_enter.Bind(wx.EVT_BUTTON, self.on_enter_click)
        self.btn_enter.Bind(wx.EVT_ENTER_WINDOW, self.on_enter_enter)
        # Import
        bmp_btn_import = lib.add_text_to_bitmap(get_blank_btn_bmp(), 
                         _("Import Data"), font_buttons, "white")
        self.btn_import = wx.BitmapButton(self.panel, -1, bmp_btn_import, 
                                          pos=(BTN_LEFT, g.next()))
        self.btn_import.Bind(wx.EVT_BUTTON, self.on_import_click)
        self.btn_import.Bind(wx.EVT_ENTER_WINDOW, self.on_import_enter)
        # Right
        g = get_next_y_pos(284, BTN_DROP)
        # Report tables
        bmp_btn_tables = lib.add_text_to_bitmap(get_blank_btn_bmp(),
                         _("Report Tables"), font_buttons, "white")
        self.btn_tables = wx.BitmapButton(self.panel, -1, bmp_btn_tables, 
                                          pos=(BTN_RIGHT, g.next()))
        self.btn_tables.Bind(wx.EVT_BUTTON, self.on_tables_click)
        self.btn_tables.Bind(wx.EVT_ENTER_WINDOW, self.on_tables_enter)
        # Charts
        bmp_btn_charts = lib.add_text_to_bitmap(get_blank_btn_bmp(), 
                         _("Charts"), font_buttons, "white")
        self.btn_charts = wx.BitmapButton(self.panel, -1, bmp_btn_charts, 
                                          pos=(BTN_RIGHT, g.next()))
        self.btn_charts.Bind(wx.EVT_BUTTON, self.on_charts_click)
        self.btn_charts.Bind(wx.EVT_ENTER_WINDOW, self.on_charts_enter)
        # Stats
        bmp_btn_stats = lib.add_text_to_bitmap(get_blank_btn_bmp(),
                        _("Statistics"), font_buttons, "white")
        self.btn_statistics = wx.BitmapButton(self.panel, -1, bmp_btn_stats, 
                                              pos=(BTN_RIGHT, g.next()))
        self.btn_statistics.Bind(wx.EVT_BUTTON, self.on_stats_click)
        self.btn_statistics.Bind(wx.EVT_ENTER_WINDOW, self.on_stats_enter)
        # Exit  
        bmp_btn_exit = lib.add_text_to_bitmap(get_blank_btn_bmp(), 
                       _("Exit"), font_buttons, "white")
        self.btn_exit = wx.BitmapButton(self.panel, -1, bmp_btn_exit, 
                                        pos=(BTN_RIGHT, g.next()))
        self.btn_exit.Bind(wx.EVT_BUTTON, self.on_exit_click)
        self.btn_exit.Bind(wx.EVT_ENTER_WINDOW, self.on_exit_enter)
        if not mg.IN_WINDOWS:
            hand = wx.StockCursor(wx.CURSOR_HAND)
            self.btn_proj.SetCursor(hand)
            self.btn_prefs.SetCursor(hand)
            self.btn_enter.SetCursor(hand)
            self.btn_import.SetCursor(hand)
            self.btn_tables.SetCursor(hand)
            self.btn_charts.SetCursor(hand)
            self.btn_statistics.SetCursor(hand)
            self.btn_exit.SetCursor(hand)
        # text
        # NB cannot have transparent background properly in Windows if using
        # a static ctrl 
        # http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3045245
        self.txtWelcome = _("Welcome to SOFA Statistics.  Hovering the mouse "
                            "over the buttons lets you see what you can do.")
        # help images
        proj = os.path.join(SCRIPT_PATH, u"images", u"briefcase.xpm")
        self.bmp_proj = wx.Image(proj, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        prefs = os.path.join(SCRIPT_PATH, u"images", u"prefs.xpm")
        self.bmp_prefs = wx.Image(prefs, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        data = os.path.join(SCRIPT_PATH, u"images", u"data.xpm")
        self.bmp_data = wx.Image(data, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        imprt = os.path.join(SCRIPT_PATH, u"images", u"import.xpm")
        self.bmp_import = wx.Image(imprt, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        tabs = os.path.join(SCRIPT_PATH, u"images", u"table.xpm")
        self.bmp_tabs = wx.Image(tabs, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        chart = os.path.join(SCRIPT_PATH, u"images", u"demo_chart.xpm")
        self.bmp_chart = wx.Image(chart, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        stats = os.path.join(SCRIPT_PATH, u"images", u"stats.xpm")
        self.bmp_stats = wx.Image(stats, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        exit = os.path.join(SCRIPT_PATH, u"images", u"exit.xpm")
        self.bmp_exit = wx.Image(exit, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        psal = os.path.join(SCRIPT_PATH, u"images", u"psal_logo.xpm")
        self.bmp_psal = wx.Image(psal, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        self.HELP_TEXT_FONT = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL)
        self.active_proj = mg.SOFA_DEFAULT_PROJ
        link_home = hl.HyperLinkCtrl(self.panel, -1, "www.sofastatistics.com", 
                                     pos=(MAIN_LEFT, TOP_TOP), 
                                     URL="http://www.sofastatistics.com")
        link_home.SetColours(link=wx.Colour(255,255,255), 
                             visited=wx.Colour(255,255,255), 
                             rollover=wx.Colour(255,255,255))
        link_home.SetOwnBackgroundColour(wx.Colour(0, 0, 0))
        link_home.SetOwnFont(wx.Font(9, wx.SWISS, wx.NORMAL, wx.NORMAL))
        link_home.SetSize(wx.Size(200, 17))
        link_home.SetUnderlines(link=True, visited=True, rollover=False)
        link_home.SetLinkCursor(wx.CURSOR_HAND)
        link_home.EnableRollover(True)
        link_home.SetVisited(True)
        link_home.UpdateLink(True)
        link_help = hl.HyperLinkCtrl(self.panel, -1, _("Ask here for help"), 
                         pos=(MAIN_LEFT, TOP_TOP + 200), 
                         URL="http://groups.google.com/group/sofastatistics")
        link_help.SetColours(link=TEXT_BROWN, 
                             visited=TEXT_BROWN, 
                             rollover=TEXT_BROWN)
        link_help.SetOwnBackgroundColour(wx.Colour(205, 217, 215))
        link_help.SetOwnFont(wx.Font(9, wx.SWISS, wx.NORMAL, wx.NORMAL))
        link_help.SetSize(wx.Size(200, 17))
        link_help.SetUnderlines(link=True, visited=True, rollover=False)
        link_help.SetLinkCursor(wx.CURSOR_HAND)
        link_help.EnableRollover(True)
        link_help.SetVisited(True)
        link_help.UpdateLink(True)
        if mg.DBE_PROBLEM:
            f = open(os.path.join(mg.INT_PATH, 
                                  u"database connection problem.txt"), "w")
            f.write(u"\n\n".join(mg.DBE_PROBLEM))
            f.close()
    
    def init_com_types(self, panel):
        """
        If first time opened, and in Windows, warn user about delay setting 
            up (comtypes).
        """
        COMTYPES_HANDLED = u"comtypes_handled.txt"
        if mg.IN_WINDOWS and not os.path.exists(os.path.join(LOCAL_PATH, 
                                                             COMTYPES_HANDLED)):
            wx.MessageBox(_("Click OK to prepare for first use of SOFA "
                            "Statistics.\n\nPreparation may take a moment ..."))
            h = full_html.FullHTML(panel, (10, 10))
            h.show_html(u"")
            h = None
        if not os.path.exists(os.path.join(LOCAL_PATH, COMTYPES_HANDLED)):
            # create file as tag we have done the changes to the proj file
            f = file(os.path.join(LOCAL_PATH, COMTYPES_HANDLED), "w")
            f.write(u"Comtypes handled successfully :-)")
            f.close()
    
    def on_paint(self, event):
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
        panel_dc.DrawLabel(_("Version %s") % mg.VERSION, 
                           wx.Rect(MAIN_RIGHT, TOP_TOP, 100, 20))
        panel_dc.SetFont(wx.Font(self.main_font_size, wx.SWISS, wx.NORMAL, 
                                 wx.NORMAL))
        panel_dc.DrawLabel(_("Statistics Open For All"), 
                           wx.Rect(MAIN_LEFT, 80, 100, 100))
        panel_dc.SetFont(wx.Font(9, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.SetTextForeground(TEXT_BROWN)
        panel_dc.DrawLabel(_("SOFA - Statistics Open For All"
                             "\nthe user-friendly, open-source statistics,"
                             "\nanalysis & reporting package"), 
           wx.Rect(MAIN_LEFT, 115, 100, 100))
        panel_dc.DrawLabel(lib.get_text_to_draw(self.txtWelcome, 
                                                MAX_HELP_TEXT_WIDTH), 
                    wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 260))
        panel_dc.SetTextForeground(wx.WHITE)
        panel_dc.SetFont(wx.Font(7, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel(u"Released under open source AGPL3 licence\n%s "
                           "2009-2010 Paton-Simpson & Associates Ltd" % \
                           COPYRIGHT, 
                           wx.Rect(MAIN_LEFT, 547, 100, 50))
        panel_dc.DrawLabel(u"SOFA\nPaton-Simpson & Associates Ltd\n" + \
                           _("Analysis & reporting specialists"), 
                           wx.Rect(MAIN_RIGHT, 547, 100, 50))
        panel_dc.DrawBitmap(self.bmp_psal, MAIN_RIGHT-45, 542, True)
        # make default db if not already there
        def_db = os.path.join(LOCAL_PATH, mg.INTERNAL_FOLDER, 
                              mg.SOFA_DEFAULT_DB)
        con = sqlite.connect(def_db)
        con.close()
        panel_dc.DrawBitmap(self.blank_proj_strip, MAIN_LEFT, 218, False)
        panel_dc.SetTextForeground(wx.WHITE)
        panel_dc.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.NORMAL))
        panel_dc.DrawLabel(_("Currently using ") +
                           "\"%s\"" % self.active_proj[:-5] + 
                           _(" Project settings"),
                           wx.Rect(MAIN_LEFT, 247, 400, 30))
        event.Skip()

    def draw_blank_wallpaper(self, panel_dc):
        panel_dc.DrawBitmap(self.blank_wallpaper, MAIN_LEFT, HELP_TEXT_TOP, 
                            False)
        
    def set_proj(self, proj_text=""):
        "proj_text must NOT have .proj on the end"
        self.active_proj = u"%s.proj" % proj_text
        self.Refresh()
        
    def on_proj_click(self, event):
        proj_fils = projects.get_projs() # should always be the default present
        # open proj selection form
        dlgProj = projselect.ProjSelectDlg(self, proj_fils, self.active_proj)
        dlgProj.ShowModal()
        dlgProj.Destroy()
        event.Skip()

    def on_proj_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_proj, HELP_IMG_LEFT, HELP_IMG_TOP, True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_projs = _("Projects let SOFA know how to connect to your data, "
                      "what labels to use, your favourite styles etc. The "
                      "default project is OK to get you started.")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_projs, MAX_HELP_TEXT_WIDTH), 
                    wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 260))
        event.Skip()
    
    def on_prefs_click(self, event):
        import prefs
        debug = False
        try:
            prefs_dic = \
                config_globals.get_settings_dic(subfolder=mg.INTERNAL_FOLDER, 
                                                fil_name=mg.INT_PREFS_FILE)
        except Exception:
            prefs_dic = {}
        if debug: print(prefs_dic)
        dlg = prefs.PrefsDlg(parent=self, prefs_dic=prefs_dic)
        dlg.ShowModal()
        event.Skip()
    
    def on_prefs_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_prefs, HELP_IMG_LEFT+50, HELP_IMG_TOP-10, 
                            True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_pref = _("Set preferences e.g. format for entering dates")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_pref, MAX_HELP_TEXT_WIDTH), 
                    wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 260))
        
    def on_enter_click(self, event):
        # open proj selection form
        import dataselect
        proj_name = self.active_proj
        dlgData = dataselect.DataSelectDlg(self, proj_name)
        dlgData.ShowModal()
        dlgData.Destroy()
        event.Skip()
        
    def on_enter_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_data, HELP_IMG_LEFT-30, HELP_IMG_TOP-20, 
                            True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_entry = _("Enter data into a fresh dataset or select an existing "
                      "one to edit or add data to.")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_entry, MAX_HELP_TEXT_WIDTH), 
                    wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 260))
        event.Skip()

    def on_import_click(self, event):
        # open import data dialog
        import importer
        dlg = importer.ImportFileSelectDlg(self)
        dlg.ShowModal()
        event.Skip()
        
    def on_import_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_import, HELP_IMG_LEFT-40, HELP_IMG_TOP, 
                            True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_entry = _("Import data e.g. an Excel or Open Document Format "
                      "spreadsheet or a csv file.")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_entry, MAX_HELP_TEXT_WIDTH), 
                    wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH-10, 260))
        event.Skip()

    def get_dbe_and_default_dbs_tbls(self, proj_dic):
        """
        Which dbe? If a default, use that.  If not, use project default.
        Also grab the default_dbs and default_tbls as lists that can be 
            manipulated later.
        """
        if mg.DBE_DEFAULT:
            dbe = mg.DBE_DEFAULT
        else:
            dbe = proj_dic["default_dbe"]
        default_dbs = proj_dic["default_dbs"]
        default_tbls = proj_dic["default_tbls"]
        return dbe, default_dbs, default_tbls
    
    def on_tables_click(self, event):
        "Open make table gui with settings as per active_proj"
        wx.BeginBusyCursor()
        import report_table
        proj_name = self.active_proj
        proj_dic = config_globals.get_settings_dic(subfolder=u"projs", 
                                                   fil_name=proj_name)
        try:
            dbe, default_dbs, default_tbls = \
                                    self.get_dbe_and_default_dbs_tbls(proj_dic)
            getdata.refresh_default_dbs_tbls(dbe, default_dbs, default_tbls)
            dlg = report_table.DlgMakeTable(dbe, proj_dic["con_dets"], 
                                default_dbs, default_tbls, 
                                proj_dic["fil_var_dets"], proj_dic["fil_css"], 
                                proj_dic["fil_report"], proj_dic["fil_script"])
            lib.safe_end_cursor()
            dlg.ShowModal()
        except Exception, e:
            msg = _("Unable to connect to data as defined in project %s. "
                    "Please check your settings." % proj_name)
            wx.MessageBox(msg)
            raise Exception, u"%s. Orig error: %s" % (msg, e) 
        finally:
            lib.safe_end_cursor()
            event.Skip()
        
    def on_tables_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_tabs, HELP_IMG_LEFT-40, HELP_IMG_TOP-25, 
                            True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_tabs1 = _("Make report tables e.g. Age vs Gender")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_tabs1, MAX_HELP_TEXT_WIDTH), 
                        wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 260))       
        txt_tabs2 = _("Can make simple Frequency Tables, Crosstabs, "
                "Summary Tables (mean, median, etc), and simple lists of data.")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_tabs2, MAX_HELP_TEXT_WIDTH), 
                    wx.Rect(MAIN_LEFT, HELP_TEXT_TOP+30, HELP_TEXT_WIDTH, 260))
        event.Skip()
    
    def get_script(self, cont, script):
        cont.append(mg.JS_WRAPPER_L)
        cont.append(script)
        cont.append(mg.JS_WRAPPER_R)
    
    def on_charts_click(self, event):
        CHARTS_NO = 0
        CHARTS_PRELIM = 1
        CHARTS_JS = 2
        charts = CHARTS_PRELIM
        if charts == CHARTS_NO:
            wx.MessageBox(_("Not available yet in version ") + 
                          unicode(mg.VERSION))
        elif charts == CHARTS_PRELIM:
            wx.MessageBox("Demonstration only at this stage - still under "
                          "construction")
            wx.BeginBusyCursor()
            import charting_output
            proj_name = self.active_proj
            proj_dic = config_globals.get_settings_dic(subfolder=u"projs", 
                                                       fil_name=proj_name)
            try:
                dbe, default_dbs, default_tbls = \
                                    self.get_dbe_and_default_dbs_tbls(proj_dic)
                getdata.refresh_default_dbs_tbls(dbe, default_dbs, default_tbls)
                dlg = charting_output.DlgCharting(_("Make Chart"), dbe, 
                                proj_dic["con_dets"], default_dbs, default_tbls, 
                                proj_dic["fil_var_dets"], proj_dic["fil_css"], 
                                proj_dic["fil_report"], proj_dic["fil_script"])
                lib.safe_end_cursor()
                dlg.ShowModal()
            except Exception, e:
                msg = _("Unable to connect to data as defined in project %s.  "
                        "Please check your settings." % proj_name)
                wx.MessageBox(msg)
                raise Exception, u"%s.  Orig error: %s" % (msg, e) 
            finally:
                lib.safe_end_cursor()
                event.Skip()
        elif charts == CHARTS_JS:
            import output
            import charting_js as chart
            cont = []
            cont.append(u"""<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
                "http://www.w3.org/TR/html4/strict.dtd">
                <html lang="en">
                <head>
                <title>Dojo Test Chart</title>
                <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
                <style type="text/css">
                    @import "http://archive.dojotoolkit.org/nightly/dojotoolkit/dojo/resources/dojo.css";
                </style>
                <!-- required for Tooltip: a default dijit theme: -->
                <link rel="stylesheet" href="http://ajax.googleapis.com/ajax/libs/dojo/1.4.1/dijit/themes/tundra/tundra.css">
                <style>
                .dojoxLegendNode {border: 1px solid #ccc; margin: 5px 10px 5px 10px; padding: 3px}
                .dojoxLegendText {vertical-align: text-top; padding-right: 10px}
                </style>
                
                <script src="http://ajax.googleapis.com/ajax/libs/dojo/1.4.1/dojo/dojo.xd.js"></script>
                
                <script type="text/javascript">
                dojo.require("dojox.charting.Chart2D");
                dojo.require("dojox.charting.themes.PlotKit.blue");
                
                dojo.require("dojox.charting.action2d.Highlight");
                dojo.require("dojox.charting.action2d.Magnify");
                dojo.require("dojox.charting.action2d.MoveSlice");
                dojo.require("dojox.charting.action2d.Shake");
                dojo.require("dojox.charting.action2d.Tooltip");
                
                dojo.require("dojox.charting.widget.Legend");
                
                dojo.require("dojo.colors");
                dojo.require("dojo.fx.easing");
                                
                makeObjects = function(){
                    var dc = dojox.charting;
                    var mychart = new dc.Chart2D("mychart");
                    mychart.setTheme(dc.themes.PlotKit.blue);
                    mychart.addAxis("x", {labels: [{value: 1, text: "Under 20"},
                        {value: 2, text: "20-29"},
                        {value: 3, text: "30-39"},
                        {value: 4, text: "40-64"},
                        {value: 5, text: "65+"}]});
                    mychart.addAxis("y", {vertical: true});
                    mychart.addPlot("default", {type: "ClusteredColumns", gap: 10});
                    mychart.addPlot("grid", {type: "Grid"});
                    mychart.addSeries("Germany", [12, 30, 100.5, -1, 40], {stroke: {color: "black"}, fill: "#7193b8"});
                    mychart.addSeries("Italy", [20, 45, 57, 1, 37.5], {stroke: {color: "black"}, fill: "#b1b2b2"});
                    mychart.addSeries("Japan", [40, 37, 124, -2, 50], {stroke: {color: "black"}, fill: "#0a175e"});
                    var anim_a = new dc.action2d.Highlight(mychart, "default", {
                        duration: 450,
                        easing:   dojo.fx.easing.sineOut
                    });
                    var anim_b = new dc.action2d.Shake(mychart, "default");
                    var anim_c = new dc.action2d.Tooltip(mychart, "default");
                    mychart.render();
                    var legend = new dojox.charting.widget.Legend({chart: mychart}, "legend");
                };
                
                dojo.addOnLoad(makeObjects);
                                
                </script>
                </head>
                
                <body class="tundra">
                <h1>Clustered Bar Chart</h1>
                <!--<p><button onclick="makeObjects();">Go</button></p>-->
                <p>Hover over markers, bars, columns, slices, and so on.</p>
                
                <div id="mychart" style="width: 600px; height: 400px;"></div>
                
                <div id="legend"></div>
                
                </body>
                </html>""")
            strContent = u"".join(cont)
            f = codecs.open("/home/g/Desktop/test.htm", "w", "utf-8")
            f.write(strContent)
            f.close()
            output.display_report(self, strContent, url_load=True)
        event.Skip()
        
    def on_charts_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_chart, HELP_IMG_LEFT-30, HELP_IMG_TOP-20, 
                            True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_charts = _("Make attractive charts e.g. a pie chart of regions")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_charts, MAX_HELP_TEXT_WIDTH), 
                        wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 260))
        event.Skip()
    
    def on_stats_click(self, event):
        # open statistics selection dialog
        wx.BeginBusyCursor()
        import stats_select
        proj_name = self.active_proj
        proj_dic = config_globals.get_settings_dic(subfolder=u"projs", 
                                                   fil_name=proj_name)
        try:
            dbe, default_dbs, default_tbls = \
                                    self.get_dbe_and_default_dbs_tbls(proj_dic)
            getdata.refresh_default_dbs_tbls(dbe, default_dbs, default_tbls)
            dlg = stats_select.StatsSelectDlg(proj_name, 
                        dbe, proj_dic["con_dets"], default_dbs, default_tbls, 
                        proj_dic["fil_var_dets"], proj_dic["fil_css"], 
                        proj_dic["fil_report"], proj_dic["fil_script"])
            lib.safe_end_cursor()
            dlg.ShowModal()
        except Exception, e:
            msg = _("Unable to connect to data as defined in project %s.  "
                    "Please check your settings." % proj_name)
            wx.MessageBox(msg)
            raise Exception, u"%s.  Orig error: %s" % (msg, e)
        finally:
            lib.safe_end_cursor()
            event.Skip()
        
    def on_stats_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_stats, HELP_IMG_LEFT-30, HELP_IMG_TOP-20, 
                            True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_stats1 = _("Run statistical tests on your data - e.g. a "
                       "Chi Square to see if there is a relationship between "
                       "age group and gender.")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_stats1, 
                                                MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 
                                   260))
        txt_stats2 = _("SOFA focuses on the statistical tests most users "
                       "need most of the time.")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_stats2, 
                                                MAX_HELP_TEXT_WIDTH), 
                wx.Rect(MAIN_LEFT, HELP_TEXT_TOP + 61, HELP_TEXT_WIDTH, 320))
        txt_stats3 = u"QUOTE:"
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_stats3, 
                                                MAX_HELP_TEXT_WIDTH), 
                           wx.Rect(MAIN_LEFT, HELP_TEXT_TOP + 106, 
                                   HELP_TEXT_WIDTH, 320))
        txt_stats4 = u"%s (%s)" % quotes.get_quote()
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_stats4, 
                                                MAX_HELP_TEXT_WIDTH - 20), 
                           wx.Rect(MAIN_LEFT + 10, HELP_TEXT_TOP + 131, 
                                   HELP_TEXT_WIDTH-10, 320))
        event.Skip()
    
    def on_exit_click(self, event):
        debug = False
        wx.BeginBusyCursor()
        # wipe any internal images
        int_img_pattern = os.path.join(mg.INT_PATH, "*.png")
        if debug: print(int_img_pattern)
        for delme in glob.glob(int_img_pattern):
            if debug: print(delme)
            os.remove(delme)
        lib.safe_end_cursor()
        self.Destroy()
        sys.exit()
        
    def on_exit_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_exit, HELP_IMG_LEFT-30, HELP_IMG_TOP-50, 
                            True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_exit = _("Exit SOFA Statistics")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_exit, MAX_HELP_TEXT_WIDTH), 
                    wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 260))
        event.Skip()

install_local()
app = SofaApp()
try:
    app.MainLoop()
finally:
    del app