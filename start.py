#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Start up launches the SOFA main form. Along the way it tries to detect errors
    and report on them to the user so that they can seek help. E.g. faulty
    version of Python being used to launch SOFA; or missing images needed by the 
    form.
Start up can also run test code to diagnose early problems.
Start up also checks to see if the current user of SOFA has their local SOFA 
    folder in place ready to use. If not, SOFA constructs one. First, it 
    creates the required folder and subfolders. Then it populates them by 
    copying across css, sofa_db, default proj, vdts, and report extras. 
    In the local folder the default project file is modified to point to the 
    user's file paths. A version file is made for future reference.
SOFA may also look to see if the local folder was created by an older version of 
    SOFA. There may be some special tasks to conduct e.g. updating css files.
If missing, a SOFA recovery folder is also made. If there is already a recovery 
    folder, but the existing local copy of SOFA was older than the installing 
    copy, the recovery folder will be wiped and overwritten with the latest 
    files.
When the form is shown for the first time on Windows versions, a warning is 
    given and com types are initialised.
"""

from __future__ import absolute_import

dev_debug = False # relates to errors etc once GUI application running.
# show_early_steps is about revealing any errors before the GUI even starts.
show_early_steps = True # same in setup
test_lang = False

import sys
import platform
# About letting other modules even be found and called
MAC_PATH = u"/Library/sofastats"
if platform.system() == "Darwin":
    sys.path.insert(0, MAC_PATH) # start is running from Apps folder

import setup # if any modules are going to fail, it will be in here
LOCAL_PATH_SETUP_NEEDED = setup.setup_folders()

import codecs
import datetime
import gettext
import glob
import os
import traceback
import wx

import sqlite3 as sqlite
"Import hyperlink"
try:
    from agw import hyperlink as hl
except ImportError: # if it's not there locally, try the wxPython lib.
    try:
        import wx.lib.agw.hyperlink as hl
    except ImportError:
        msg = (u"There seems to be a problem related to your wxPython "
               u"package. %s" % traceback.format_exc())
        if show_early_steps:
            print(msg)
            raw_input(setup.INIT_DEBUG_MSG)
        raise Exception(msg)

import my_globals as mg
import lib
import config_globals
import config_dlg
import getdata
import projects
import projselect
import quotes

REVERSE = False

def get_next_y_pos(start, height):
    "Facilitate regular y position of buttons"
    i = 0
    while True:
        yield start + (i*height)
        i += 1

class FeedbackDlg(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent=parent, title=_("Feedback"), 
                           style=wx.CAPTION|wx.SYSTEM_MENU, 
                           pos=(mg.HORIZ_OFFSET+100,300))
        self.parent = parent
        self.panel = wx.Panel(self)
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_btns = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=50)
        szr_btns.AddGrowableCol(0,1) # idx, propn
        btn_exit = wx.Button(self.panel, -1, _("Just Exit"))
        btn_exit.Bind(wx.EVT_BUTTON, self.on_btn_exit)
        btn_feedback = wx.Button(self.panel, -1, _("Give Quick Feedback"))
        btn_feedback.Bind(wx.EVT_BUTTON, self.on_btn_feedback)
        szr_btns.Add(btn_exit, 0)
        szr_btns.Add(btn_feedback, 0, wx.ALIGN_RIGHT)
        txt_invitation = wx.StaticText(self.panel, -1, 
            _(u"Did SOFA meet your needs? Please let us know by answering a "
              u"short survey."
              u"\n\nYou can answer later by clicking on the \"%s\" link"
              u"\ndown the bottom of the main form"
              u"\n\nAnd you are always welcome to email "
              u"grant@sofastatistics.com - "
              u"\nespecially to solve any problems.") % mg.FEEDBACK_LINK)
        self.szr_main.Add(txt_invitation, 1, wx.GROW|wx.ALL, 10)
        self.szr_main.Add(szr_btns, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(self.szr_main)
        self.szr_main.SetSizeHints(self)
        self.Layout()
        
    def on_btn_exit(self, event):
        self.Destroy()
        
    def on_btn_feedback(self, event):
        import webbrowser
        url = u"http://www.sofastatistics.com/feedback.htm"
        webbrowser.open_new_tab(url)
        self.Destroy()
        event.Skip()
        

class SofaApp(wx.App):

    def __init__(self):
        # if wanting to initialise the parent class it must be run in 
        # child __init__ and nowhere else.
        if dev_debug:
            redirect = False
            filename = None
        else:
            redirect = True
            filename = os.path.join(mg.INT_PATH, u'output.txt')
        wx.App.__init__(self, redirect=redirect, filename=filename)

    def OnInit(self):
        debug = False
        """
        If a language isn't installed on the OS then it won't even look for the
            locale subfolder.  GetLanguage() will return a 1 instead of the 
            langid. 
        """
        try:
            # http://wiki.wxpython.org/RecipesI18n
            langdir = os.path.join(mg.SCRIPT_PATH, u'locale')
            langid = mg.TEST_LANGID if test_lang else wx.LANGUAGE_DEFAULT
            # next line will only work if locale is installed on the computer
            # on Macs, must be after app starts ...
            # ... (http://programming.itags.org/python/2877/)
            mylocale = wx.Locale(langid) #, wx.LOCALE_LOAD_DEFAULT)
            if debug:
                print(u"langid: %s" % langid)
                print(u"Getlanguage: %s" % mylocale.GetLanguage())
                print(u"GetCanonicalName: %s" % mylocale.GetCanonicalName())
                print(u"GetSysName: %s" % mylocale.GetSysName())
                print(u"GetLocale: %s" % mylocale.GetLocale())
                print(u"GetName: %s" % mylocale.GetName())
            if mylocale.IsOk():
                canon_name = mylocale.GetCanonicalName()
            else:
                if mg.PLATFORM == mg.LINUX:
                    cli = (u"\n\nSee list of languages installed on your "
                           u"system by typing\n       locale -a\ninto a "
                           u"terminal and hitting the Enter key.")
                else:
                    cli = u""
                # Language locale problem - provide more useful message to go 
                # alongside system one.
                mg.DEFERRED_WARNING_MSGS.append(
                    u"LANGUAGE ERROR:\n\n"
                    u"SOFA couldn't set its locale to %(lang)s. Does your "
                    u"system have %(lang)s installed?%(cli)s"
                    u"\n\nPlease contact developer for advice - "
                    u"grant@sofastatistics.com" % {u"cli": cli,
                                    u"lang": mylocale.GetLanguageName(langid)})
                """
                Resetting mylocale makes frame flash and die if not clean first.
                http://www.java2s.com/Open-Source/Python/GUI/wxPython/...
                             ...wxPython-src-2.8.11.0/wxPython/demo/I18N.py.htm
                """
                assert sys.getrefcount(mylocale) <= 2
                del mylocale # otherwise C++ object persists too long & crashes
                mylocale = wx.Locale(wx.LANGUAGE_DEFAULT)
                canon_name = mylocale.GetCanonicalName()
            mytrans = gettext.translation(u"sofastats", langdir, 
                                    languages=[canon_name,], fallback=True)
            if debug: print(canon_name)
            mytrans.install(unicode=True) # must set explicitly here for mac
            if mg.PLATFORM == mg.LINUX:
                try:
                    # to get some language settings to display properly:
                    os.environ['LANG'] = u"%s.UTF-8" % canon_name
                except (ValueError, KeyError):
                    pass
            mg.MAX_WIDTH = wx.Display().GetGeometry()[2]
            mg.MAX_HEIGHT = wx.Display().GetGeometry()[3]
            mg.HORIZ_OFFSET = 0 if mg.MAX_WIDTH < 1224 else 200
            frame = StartFrame()
            frame.CentreOnScreen(wx.VERTICAL) # on dual monitor, 
                # wx.BOTH puts in screen 2 (in Ubuntu at least)!
            frame.Show()
            self.SetTopWindow(frame)
            return True
        except Exception, e:
            try:
                frame.Close()
            except NameError:
                pass
            # raise original exception having closed frame if possible
            raise Exception(lib.ue(e))
        

class StartFrame(wx.Frame):
    
    def __init__(self):
        debug = False
        # layout "constants"
        self.tight_layout = (mg.MAX_WIDTH <= 1024 or mg.MAX_HEIGHT <= 600)
        #self.tight_layout = True # for testing
        self.tight_height_drop = 24
        self.tight_width_drop = 57
        if not self.tight_layout:
            self.form_width = 1000
            self.form_height = 600
            self.blankwp_height = 250
            self.btn_drop = 40
        else:
            self.form_width = 1000-self.tight_width_drop
            self.form_height = 600-self.tight_height_drop
            self.blankwp_height = 250-self.tight_height_drop
            self.btn_drop = 37
        btn_width = 170
        self.btn_right = self.form_width - (btn_width + 18)
        self.top_top = 7
        self.btn_left = 5
        self.main_left = 200
        self.help_text_top = 288
        self.max_help_text_width = 330 # pixels
        self.help_text_width = 330
        self.help_img_top = 315
        self.main_sofa_logo_right = 555
        self.version_right = self.main_sofa_logo_right + 10
        if not self.tight_layout:
            self.help_img_left = 575
            self.chart_img_offset = -30
            self.import_img_offset = -40
            self.report_img_offset = 10
            self.stats_img_offset = 10
            self.proj_img_offset = -20
            self.help_img_offset = 0
            self.get_started_img_offset = 0
            self.prefs_img_offset = 35
            self.data_img_offset = -30
            self.form_pos_left = mg.HORIZ_OFFSET+5
        else:
            self.help_img_left = 575-self.tight_width_drop
            self.chart_img_offset = -10
            self.import_img_offset = -10
            self.report_img_offset = 30
            self.stats_img_offset = 30
            self.proj_img_offset = 30
            self.help_img_offset = 30
            self.get_started_img_offset = 0
            self.prefs_img_offset = 55
            self.data_img_offset = 45
            self.form_pos_left = mg.MAX_WIDTH-(self.form_width+10)
        # The earliest point at which error messages can be shown to the user 
        # in a GUI.  E.g. Can't find the folder this script is in.
        self.text_brown = (90, 74, 61)
        deferred_error_msg = u"\n\n".join(mg.DEFERRED_ERRORS)
        if deferred_error_msg:
            raise Exception(deferred_error_msg)
        # Gen set up
        wx.Frame.__init__(self, None, title=_("SOFA Start"), 
                  size=(self.form_width, self.form_height), 
                  pos=(self.form_pos_left,-1),
                  style=wx.CAPTION|wx.MINIMIZE_BOX|wx.CLOSE_BOX|wx.SYSTEM_MENU)
        # Windows doesn't include window decorations
        y_start = self.GetClientSize()[1] - self.GetSize()[1]
        self.SetClientSize(self.GetSize())
        global REVERSE
        REVERSE = lib.mustreverse()
        self.panel = wx.Panel(self, size=(self.form_width, self.form_height)) # win
        self.panel.SetBackgroundColour(wx.Colour(205, 217, 215))
        self.panel.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SHOW, self.on_show) # doesn't run on Mac
        self.Bind(wx.EVT_CLOSE, self.on_exit_click)
        self.active_proj = mg.DEFAULT_PROJ
        proj_dic = config_globals.get_settings_dic(subfolder=mg.PROJS_FOLDER, 
                                                   fil_name=self.active_proj)
        if not mg.DATA_DETS:
            try:
                # trying to actually connect to a database on start up
                mg.DATA_DETS = getdata.DataDets(proj_dic)
                if debug: print("Updated mg.DATA_DETS")
            except Exception, e:
                lib.safe_end_cursor()
                wx.MessageBox(_("Unable to connect to data as defined in " 
                                "project %s. Please check your settings.") % 
                                self.active_proj)
                raise # for debugging
                return
        config_dlg.add_icon(frame=self)
        # background image
        if not self.tight_layout:
            sofabg_img = u"sofastats_start_bg.gif"
            demo_chart_img = u"demo_chart.gif"
            proj_img = u"projects.gif"
            data_img = u"data.gif"
        else:
            sofabg_img = u"sofastats_start_bg_tight.gif"
            demo_chart_img = u"demo_chart_tight.gif"
            proj_img = u"projects_tight.gif"
            data_img = u"data_tight.gif"
        sofabg = os.path.join(mg.SCRIPT_PATH, u"images", sofabg_img)
        top_sofa = os.path.join(mg.SCRIPT_PATH, u"images", u"top_sofa.gif")
        demo_chart = os.path.join(mg.SCRIPT_PATH, u"images", demo_chart_img)
        proj = os.path.join(mg.SCRIPT_PATH, u"images", proj_img)
        data = os.path.join(mg.SCRIPT_PATH, u"images", data_img)
        if not os.path.exists(sofabg):
            raise Exception(u"Problem finding background button image.  "
                            u"Missing path: %s" % sofabg)
        try:
            self.bmp_sofabg = lib.get_bmp(src_img_path=sofabg, reverse=REVERSE)
        except Exception:
            raise Exception(u"Problem creating background button image from %s"
                            % sofabg)
        # stable images
        upgrade = os.path.join(mg.SCRIPT_PATH, u"images", u"upgrade.xpm")
        self.bmp_upgrade = lib.get_bmp(src_img_path=upgrade, 
                                       bmp_type=wx.BITMAP_TYPE_XPM, 
                                       reverse=REVERSE)
        quote_left = os.path.join(mg.SCRIPT_PATH, u"images", 
                                  u"speech_mark_large.xpm")
        self.bmp_quote_left = lib.get_bmp(src_img_path=quote_left, 
                                          bmp_type=wx.BITMAP_TYPE_XPM, 
                                          reverse=REVERSE)
        quote_right = os.path.join(mg.SCRIPT_PATH, u"images", 
                                  u"speech_mark_small.xpm")
        self.bmp_quote_right = lib.get_bmp(src_img_path=quote_right, 
                                           bmp_type=wx.BITMAP_TYPE_XPM, 
                                           reverse=REVERSE)
        self.bmp_top_sofa = lib.get_bmp(src_img_path=top_sofa) # ok if reversed
        # slice of image to be refreshed (where text and image will be)
        blankwp_rect = wx.Rect(self.main_left, self.help_text_top, 
                               self.help_img_left+35, self.blankwp_height)
        self.blank_wallpaper = self.bmp_sofabg.GetSubBitmap(blankwp_rect)
        blankps_rect = wx.Rect(self.main_left, 218, 610, 30)
        self.blank_proj_strip = self.bmp_sofabg.GetSubBitmap(blankps_rect)
        # buttons
        btn_font_sz = 14 if mg.PLATFORM == mg.MAC else 10
        g = get_next_y_pos(284, self.btn_drop)
        # get started
        get_started_btn_bmp = lib.get_blank_btn_bmp(xpm=u"blankhelpbutton.xpm")
        bmp_btn_get_started = lib.add_text_to_bitmap(get_started_btn_bmp,
                                         _("Get Started"), btn_font_sz, "white")
        if REVERSE: bmp_btn_get_started = lib.reverse_bmp(bmp_btn_get_started)
        self.btn_get_started = wx.BitmapButton(self.panel, -1, 
                                               bmp_btn_get_started, 
                                               pos=(self.btn_left, g.next()))
        self.btn_get_started.Bind(wx.EVT_BUTTON, self.on_get_started_click)
        self.btn_get_started.Bind(wx.EVT_ENTER_WINDOW, 
                                  self.on_get_started_enter)
        self.btn_get_started.SetDefault()
        # Data entry
        bmp_btn_data = lib.add_text_to_bitmap(lib.get_blank_btn_bmp(), 
                                     _("Enter/Edit Data"), btn_font_sz, "white")
        if REVERSE: bmp_btn_data = lib.reverse_bmp(bmp_btn_data)
        self.btn_data = wx.BitmapButton(self.panel, -1, bmp_btn_data, 
                                         pos=(self.btn_left, g.next()))
        self.btn_data.Bind(wx.EVT_BUTTON, self.on_data_click)
        self.btn_data.Bind(wx.EVT_ENTER_WINDOW, self.on_data_enter)
        # Import
        bmp_btn_import = lib.add_text_to_bitmap(lib.get_blank_btn_bmp(), 
                                         _("Import Data"), btn_font_sz, "white")
        if REVERSE: bmp_btn_import = lib.reverse_bmp(bmp_btn_import)
        self.btn_import = wx.BitmapButton(self.panel, -1, bmp_btn_import, 
                                          pos=(self.btn_left, g.next()))
        self.btn_import.Bind(wx.EVT_BUTTON, self.on_import_click)
        self.btn_import.Bind(wx.EVT_ENTER_WINDOW, self.on_import_enter)
        # Report tables
        bmp_btn_tables = lib.add_text_to_bitmap(lib.get_blank_btn_bmp(),
                                       _("Report Tables"), btn_font_sz, "white")
        if REVERSE: bmp_btn_tables = lib.reverse_bmp(bmp_btn_tables)
        self.btn_tables = wx.BitmapButton(self.panel, -1, bmp_btn_tables, 
                                          pos=(self.btn_left, g.next()))
        self.btn_tables.Bind(wx.EVT_BUTTON, self.on_tables_click)
        self.btn_tables.Bind(wx.EVT_ENTER_WINDOW, self.on_tables_enter)
        # Charts
        bmp_btn_charts = lib.add_text_to_bitmap(lib.get_blank_btn_bmp(), 
                                              _("Charts"), btn_font_sz, "white")
        if REVERSE: bmp_btn_charts = lib.reverse_bmp(bmp_btn_charts)
        self.btn_charts = wx.BitmapButton(self.panel, -1, bmp_btn_charts, 
                                          pos=(self.btn_left, g.next()))
        self.btn_charts.Bind(wx.EVT_BUTTON, self.on_charts_click)
        self.btn_charts.Bind(wx.EVT_ENTER_WINDOW, self.on_charts_enter)
        # Stats
        bmp_btn_stats = lib.add_text_to_bitmap(lib.get_blank_btn_bmp(),
                                          _("Statistics"), btn_font_sz, "white")
        if REVERSE: bmp_btn_stats = lib.reverse_bmp(bmp_btn_stats)
        self.btn_statistics = wx.BitmapButton(self.panel, -1, bmp_btn_stats, 
                                              pos=(self.btn_left, g.next()))
        self.btn_statistics.Bind(wx.EVT_BUTTON, self.on_stats_click)
        self.btn_statistics.Bind(wx.EVT_ENTER_WINDOW, self.on_stats_enter)
        # Right
        g = get_next_y_pos(284, self.btn_drop)
        # on-line help
        help_btn_bmp = lib.get_blank_btn_bmp(xpm=u"blankhelpbutton.xpm")
        bmp_btn_help = lib.add_text_to_bitmap(help_btn_bmp, 
                                         _("Online Help"), btn_font_sz, "white")
        if REVERSE: bmp_btn_help = lib.reverse_bmp(bmp_btn_help)
        self.btn_help = wx.BitmapButton(self.panel, -1, bmp_btn_help, 
                                        pos=(self.btn_right, g.next()))
        self.btn_help.Bind(wx.EVT_BUTTON, self.on_help_click)
        self.btn_help.Bind(wx.EVT_ENTER_WINDOW, self.on_help_enter)
        self.btn_help.SetDefault()
        # Proj
        bmp_btn_proj = lib.add_text_to_bitmap(lib.get_blank_btn_bmp(), 
                                      _("Select Project"), btn_font_sz, "white")
        if REVERSE: bmp_btn_proj = lib.reverse_bmp(bmp_btn_proj)
        self.btn_proj = wx.BitmapButton(self.panel, -1, bmp_btn_proj, 
                                        pos=(self.btn_right, g.next()))
        self.btn_proj.Bind(wx.EVT_BUTTON, self.on_proj_click)
        self.btn_proj.Bind(wx.EVT_ENTER_WINDOW, self.on_proj_enter)
        # Prefs
        bmp_btn_prefs = lib.add_text_to_bitmap(lib.get_blank_btn_bmp(), 
                                         _("Preferences"), btn_font_sz, "white")
        if REVERSE: bmp_btn_prefs = lib.reverse_bmp(bmp_btn_prefs)
        self.btn_prefs = wx.BitmapButton(self.panel, -1, bmp_btn_prefs, 
                                         pos=(self.btn_right, g.next()))
        self.btn_prefs.Bind(wx.EVT_BUTTON, self.on_prefs_click)
        self.btn_prefs.Bind(wx.EVT_ENTER_WINDOW, self.on_prefs_enter)
        # Exit  
        bmp_btn_exit = lib.add_text_to_bitmap(lib.get_blank_btn_bmp(), 
                                              _("Exit"), btn_font_sz, "white")
        if REVERSE: bmp_btn_exit = lib.reverse_bmp(bmp_btn_exit)
        self.btn_exit = wx.BitmapButton(self.panel, -1, bmp_btn_exit, 
                                        pos=(self.btn_right, g.next()))
        self.btn_exit.Bind(wx.EVT_BUTTON, self.on_exit_click)
        self.btn_exit.Bind(wx.EVT_ENTER_WINDOW, self.on_exit_enter)
        if mg.PLATFORM == mg.LINUX:
            hand = wx.StockCursor(wx.CURSOR_HAND)
            self.btn_help.SetCursor(hand)
            self.btn_proj.SetCursor(hand)
            self.btn_prefs.SetCursor(hand)
            self.btn_data.SetCursor(hand)
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
        if mg.PLATFORM == mg.MAC:
            self.help_font = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        elif mg.PLATFORM == mg.WINDOWS:
            self.help_font = wx.Font(10.5, wx.DEFAULT, wx.NORMAL, wx.BOLD)
        else:
            self.help_font = wx.Font(10.5, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        try:
            # help images
            help = os.path.join(mg.SCRIPT_PATH, u"images", u"help.gif")
            self.bmp_help = lib.get_bmp(src_img_path=help, reverse=REVERSE)
            get_started = os.path.join(mg.SCRIPT_PATH, u"images",
                                       u"step_by_step.gif")
            self.bmp_get_started = lib.get_bmp(src_img_path=get_started, 
                                               reverse=REVERSE)
            self.bmp_proj = lib.get_bmp(src_img_path=proj, reverse=REVERSE)
            prefs = os.path.join(mg.SCRIPT_PATH, u"images", u"prefs.gif")
            self.bmp_prefs = lib.get_bmp(src_img_path=prefs, reverse=REVERSE)
            self.bmp_data = lib.get_bmp(src_img_path=data, reverse=REVERSE)
            imprt = os.path.join(mg.SCRIPT_PATH, u"images", u"import.gif")
            self.bmp_import = lib.get_bmp(src_img_path=imprt, reverse=REVERSE)
            tabs = os.path.join(mg.SCRIPT_PATH, u"images", u"table.gif")
            self.bmp_tabs = lib.get_bmp(src_img_path=tabs, reverse=REVERSE)
            self.bmp_chart = lib.get_bmp(src_img_path=demo_chart, 
                                         reverse=REVERSE)
            stats = os.path.join(mg.SCRIPT_PATH, u"images", u"stats.gif")
            self.bmp_stats = lib.get_bmp(src_img_path=stats, reverse=REVERSE)
            exit = os.path.join(mg.SCRIPT_PATH, u"images", u"exit.gif")
            self.bmp_exit = lib.get_bmp(src_img_path=exit, reverse=REVERSE)
            agpl3 = os.path.join(mg.SCRIPT_PATH, u"images", u"agpl3.xpm")
            self.bmp_agpl3 = lib.get_bmp(src_img_path=agpl3, 
                                     bmp_type=wx.BITMAP_TYPE_XPM, 
                                     reverse=REVERSE)
        except Exception, e:
            raise Exception(u"Problem setting up help images."
                            u"\nCaused by error: %s" % lib.ue(e))
        # upgrade available?
        # get level of version checking
        try:
            prefs_dic = \
                config_globals.get_settings_dic(subfolder=mg.INT_FOLDER, 
                                                fil_name=mg.INT_PREFS_FILE)
            version_lev = prefs_dic[mg.PREFS_KEY].get(mg.VERSION_CHECK_KEY, 
                                                      mg.VERSION_CHECK_ALL)
        except Exception, e:
            version_lev = mg.VERSION_CHECK_ALL
        # get upgrade available status
        try:
            if version_lev == mg.VERSION_CHECK_NONE:
                raise Exception(u"No permission to check for new versions")
            else:
                if not dev_debug:
                    new_version = self.get_latest_version(version_lev)
                if debug: print(new_version)
            self.upgrade_available = \
                                lib.version_a_is_newer(version_a=new_version, 
                                                       version_b=mg.VERSION)
        except Exception, e:
            self.upgrade_available = False
        # home link
        home_link_hpos = self.version_right if REVERSE else self.main_left
        link_home = hl.HyperLinkCtrl(self.panel, -1, "www.sofastatistics.com", 
                                     pos=(home_link_hpos, self.top_top), 
                                     URL="http://www.sofastatistics.com")
        self.setup_link(link=link_home, link_colour=wx.Colour(255,255,255), 
                        bg_colour=wx.Colour(0, 0, 0))
        # help link
        link_help = hl.HyperLinkCtrl(self.panel, -1, 
                            _("Get help from community"), 
                            pos=(self.main_left, self.top_top + 200), 
                            URL="http://groups.google.com/group/sofastatistics")
        self.setup_link(link=link_help, link_colour=self.text_brown, 
                        bg_colour=wx.Colour(205, 217, 215))
        # upgrade link
        if self.upgrade_available:
            upgrade_link_hpos = self.main_left if REVERSE \
                                               else self.version_right+125
            link_upgrade = hl.HyperLinkCtrl(self.panel, -1, 
                            _(u"Upgrade to %s here") % new_version, 
                            pos=(upgrade_link_hpos, self.top_top), 
                            URL="http://www.sofastatistics.com/downloads.php")
            self.setup_link(link=link_upgrade, 
                            link_colour=wx.Colour(255,255,255), 
                            bg_colour=wx.Colour(0, 0, 0))
        # feedback link
        feedback_link_hpos = self.main_left if REVERSE\
                                            else self.main_sofa_logo_right
        link_feedback = hl.HyperLinkCtrl(self.panel, -1, mg.FEEDBACK_LINK, 
                        pos=(feedback_link_hpos, self.form_height-53), 
                        URL="http://www.sofastatistics.com/feedback.htm")
        self.setup_link(link=link_feedback, 
                        link_colour=wx.Colour(255,255,255), 
                        bg_colour=wx.Colour(116, 99, 84))
        if mg.DBE_PROBLEM:
            prob = os.path.join(mg.INT_PATH, u"database connection problem.txt")
            f = codecs.open(prob, "w", "utf8")
            f.write(u"\n\n".join(mg.DBE_PROBLEM))
            f.close()
        if mg.MUST_DEL_TMP:
            wx.MessageBox(_("Please click on \"Enter/Edit Data\" and delete"
                        " the table \"%s\"") % mg.TMP_TBL_NAME)
        # any warnings to display once screen visible?
        warning_div = u"\n\n" + u"-"*20 + u"\n\n"
        deferred_warning_msg = warning_div.join(mg.DEFERRED_WARNING_MSGS)
        if deferred_warning_msg:
            wx.CallAfter(self.on_deferred_warning_msg, deferred_warning_msg)
        else:
            wx.CallAfter(self.sofastats_connect)
        
    def on_deferred_warning_msg(self, deferred_warning_msg):
        wx.MessageBox(deferred_warning_msg)
        
    def sofastats_connect(self):
        """
        If first time, or file otherwise missing or damaged, create file with
            date set a short time in the future as signal to connect to the 
            sofastatistics.com "What's Happening" web page. Whenever a 
            connection is made, reset date to a longer period away.
        If file exists and date can be read, connect if time has passed and 
            reset date to a longer period away.
        """
        debug = False
        connect_now = False
        sofastats_connect_fil = os.path.join(mg.INT_PATH, 
                                             mg.SOFASTATS_CONNECT_FILE)
        wx.BeginBusyCursor()
        try:
            # read date from file if possible
            f = codecs.open(sofastats_connect_fil, "U", encoding="utf-8")
            connect_cont = lib.get_exec_ready_text(text=f.read())
            f.close()
            connect_cont = lib.clean_bom_utf8(connect_cont)
            connect_dic = {}
            # http://docs.python.org/reference/simple_stmts.html
            exec connect_cont in connect_dic
            # if date <= now, connect_now and update file
            connect_date = connect_dic[mg.SOFASTATS_CONNECT_VAR]
            now_str = unicode(datetime.datetime.today())
            expired_date = (connect_date <= now_str)
            if expired_date:
                connect_now = True
        except Exception, e: # if probs, create new file for few weeks away
            self.update_sofastats_connect_date(sofastats_connect_fil, 
                                         days2wait=mg.SOFASTATS_CONNECT_INITIAL)
        if connect_now:
            try:
                # check we can!
                import showhtml
                import urllib # http://docs.python.org/library/urllib.html
                file2read = mg.SOFASTATS_CONNECT_URL
                # so I can see which versions are still in use
                # without violating privacy etc
                url2open = u"http://www.sofastatistics.com/%s?version=%s" % \
                                                        (file2read, mg.VERSION)
                url_reply = urllib.urlopen(url2open)
                if debug: print("Checked sofastatistics.com connection: %s" 
                                % new_version)
                # seems OK so connect
                width_reduction=mg.MAX_WIDTH*0.25 if mg.MAX_WIDTH > 1000 \
                                                  else 200
                height_reduction=mg.MAX_HEIGHT*0.25 if mg.MAX_HEIGHT > 600 \
                                                    else 100
                dlg = showhtml.DlgHTML(parent=self, 
                       title=_("What's happening in SOFA Statistics"), 
                       url='http://www.sofastatistics.com/sofastats_connect.php',
                       width_reduction=mg.MAX_WIDTH*0.25, 
                       height_reduction=mg.MAX_HEIGHT*0.25)
                dlg.ShowModal()
                # set next contact date
                self.update_sofastats_connect_date(sofastats_connect_fil, 
                                         days2wait=mg.SOFASTATS_CONNECT_REGULAR)
            except Exception, e:
                if debug: print(u"Unable to connect to sofastatistics.com."
                                u"/nCaused by error: %s" % lib.ue(e))
                pass
        lib.safe_end_cursor()
    
    def update_sofastats_connect_date(self, sofastats_connect_fil, 
                                      days2wait=120):
        f = codecs.open(sofastats_connect_fil, "w", encoding="utf-8")
        next_check_date = (datetime.datetime.today() +
                        datetime.timedelta(days=days2wait)).strftime('%Y-%m-%d')
        f.write("%s = '%s'" % (mg.SOFASTATS_CONNECT_VAR, next_check_date))
        f.close()
    
    def get_latest_version(self, version_lev):
        """
        Is there a new version or a new major version?
        """
        import urllib # http://docs.python.org/library/urllib.html
        debug = False
        file2read = mg.SOFASTATS_MAJOR_VERSION_CHECK \
                    if version_lev == mg.VERSION_CHECK_MAJOR \
                    else mg.SOFASTATS_VERSION_CHECK
        url2open = u"http://www.sofastatistics.com/%s" % file2read
        try:
            url_reply = urllib.urlopen(url2open)
            new_version = u"%s" % url_reply.read().strip()
            if debug: print("Checked new version: %s" % new_version)
        except Exception, e:
            raise Exception(u"Unable to extract latest sofa version."
                            u"/nCaused by error: %s" % lib.ue(e))
        return new_version
    
    def setup_link(self, link, link_colour, bg_colour):
        link.SetColours(link=link_colour, visited=link_colour, 
                        rollover=link_colour)
        link.SetOwnBackgroundColour(bg_colour)
        link.SetOwnFont(wx.Font(12 if mg.PLATFORM == mg.MAC else 9, 
                                wx.SWISS, wx.NORMAL, wx.NORMAL))
        link.SetSize(wx.Size(250, 17))
        link.SetUnderlines(link=True, visited=True, rollover=False)
        link.SetLinkCursor(wx.CURSOR_HAND)
        link.EnableRollover(True)
        link.SetVisited(True)
        link.UpdateLink(True)
        
    def on_show(self, event):
        setup.init_com_types(self, self.panel) # fortunately, not needed on Mac
    
    def on_paint_err_msg(self, e):
        wx.MessageBox(u"Problem displaying start form. "
                      u"Please email the lead developer for help - "
                      u"grant@sofastatistics.com\n\nCaused by error: %s" % 
                      lib.ue(e))
    
    def on_paint(self, event):
        """
        Cannot use static bitmaps and static text to replace.  In windows
            doesn't show background wallpaper.
        NB painting like this sets things behind the controls.
        """
        try:
            panel_dc = wx.ClientDC(self.panel)
            panel_dc.DrawBitmap(self.bmp_sofabg, 0, 0, True)
            if self.upgrade_available:
                panel_dc.DrawBitmap(self.bmp_upgrade, self.version_right+95, 4, 
                                    True)
            orig_left_pos = 136
            orig_right_pos = 445
            left_pos = orig_right_pos if REVERSE else orig_left_pos
            right_pos = orig_left_pos if REVERSE else orig_right_pos
            panel_dc.DrawBitmap(self.bmp_quote_left, left_pos, 95, True)
            panel_dc.DrawBitmap(self.bmp_quote_right, right_pos, 163, True)
            panel_dc.DrawBitmap(self.bmp_top_sofa, self.main_sofa_logo_right, 
                                65, True)
            panel_dc.DrawBitmap(self.bmp_chart, 
                                self.help_img_left+self.chart_img_offset, 
                                self.help_img_top-20, True)
            panel_dc.SetTextForeground(wx.WHITE)
            panel_dc.SetFont(wx.Font(12 if mg.PLATFORM == mg.MAC else 9, 
                                     wx.SWISS, wx.NORMAL, wx.NORMAL))
            version_link_hpos = self.main_left if REVERSE \
                                               else self.version_right
            panel_dc.DrawLabel(_("Version %s") % mg.VERSION, 
                               wx.Rect(version_link_hpos, 
                                       self.top_top, 100, 20))
            font_sz = 28 if mg.PLATFORM == mg.MAC else 20
            main_text = _("Statistics Open For All")
            extra_width = 40 if mg.PLATFORM == mg.MAC else 60
            main_text_width = self.max_help_text_width + extra_width
            main_fs = lib.get_font_size_to_fit(main_text, main_text_width, 
                                               font_sz, min_font_sz=14)
            panel_dc.SetFont(wx.Font(main_fs, wx.SWISS, wx.NORMAL, wx.NORMAL))
            panel_dc.DrawLabel(main_text, wx.Rect(self.main_left, 80, 
                                                  main_text_width, 100))
            panel_dc.SetFont(wx.Font(14 if mg.PLATFORM == mg.MAC else 9, 
                                     wx.SWISS, wx.NORMAL, wx.NORMAL))
            panel_dc.SetTextForeground(self.text_brown)
            panel_dc.DrawLabel(_("SOFA - Statistics Open For All"
                                 "\nthe user-friendly, open-source statistics,"
                                 "\nanalysis & reporting package"), 
               wx.Rect(self.main_left, 115, 100, 100))
            panel_dc.SetFont(self.help_font)
            panel_dc.DrawLabel(lib.get_text_to_draw(self.txtWelcome, 
                                                    self.max_help_text_width), 
                        wx.Rect(self.main_left, self.help_text_top, 
                                self.help_text_width, 260))
            panel_dc.SetTextForeground(wx.WHITE)
            panel_dc.SetFont(wx.Font(12 if mg.PLATFORM == mg.MAC else 7, 
                                     wx.SWISS, wx.NORMAL, wx.NORMAL))
            copyright = u"\u00a9"
            panel_dc.DrawLabel(u"Released under open source AGPL3 licence\n%s "
                               "2009-2011 Paton-Simpson & Associates Ltd" %
                               copyright, 
                               wx.Rect(self.main_left, self.form_height-53, 
                                       100, 50))
            panel_dc.DrawBitmap(self.bmp_agpl3, self.main_left-115, 
                                self.form_height-58, True)
            # make default db if not already there
            def_db = os.path.join(mg.LOCAL_PATH, mg.INT_FOLDER, mg.SOFA_DB)
            con = sqlite.connect(def_db)
            con.close()
            panel_dc.DrawBitmap(self.blank_proj_strip, self.main_left, 218, 
                                False)
            panel_dc.SetTextForeground(wx.WHITE)
            panel_dc.SetFont(wx.Font(14 if mg.PLATFORM == mg.MAC else 11, 
                                     wx.SWISS, wx.NORMAL, wx.NORMAL))
            panel_dc.DrawLabel(_(u"Currently using \"%s\" project settings") % 
                                              self.active_proj[:-len(u".proj")],
                               wx.Rect(self.main_left, 247, 400, 30))
            event.Skip()
        except Exception, e:
            event.Skip()
            self.panel.Unbind(wx.EVT_PAINT)
            wx.CallAfter(self.on_paint_err_msg, e)
            self.Destroy()

    def draw_blank_wallpaper(self, panel_dc):
        panel_dc.DrawBitmap(self.blank_wallpaper, self.main_left, 
                            self.help_text_top, False)
        
    def set_proj(self, proj_text=""):
        "proj_text must NOT have .proj on the end"
        self.active_proj = u"%s.proj" % proj_text
        self.Refresh()

    def on_get_started_click(self, event):
        import webbrowser
        url = u"http://www.sofastatistics.com/wiki/doku.php" + \
              u"?id=help:getting_started"
        webbrowser.open_new_tab(url)
        event.Skip()

    def on_get_started_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_get_started, 
                            self.help_img_left+self.get_started_img_offset, 
                            self.help_img_top-25, True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt_get_started = _(u"Step-by-step examples with screen-shots "
                            u"to get you started.")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_get_started, 
                                                self.max_help_text_width), 
                    wx.Rect(self.main_left, self.help_text_top, 
                            self.help_text_width, 260))
        event.Skip()

    def on_help_click(self, event):
        import webbrowser
        url = u"http://www.sofastatistics.com/help.php"
        webbrowser.open_new_tab(url)
        event.Skip()

    def on_help_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_help, 
                            self.help_img_left+self.help_img_offset, 
                            self.help_img_top-25, True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt_help = _(u"Get help on-line, including screen shots and "
                     u"step-by-step instructions. Connect to the community. "
                     u"Get direct help from the developer.")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_help, 
                                                self.max_help_text_width), 
                    wx.Rect(self.main_left, self.help_text_top, 
                            self.help_text_width, 260))
        event.Skip()

    def on_proj_click(self, event):
        proj_fils = projects.get_projs() # should always be the default present
        # open proj selection form
        dlgProj = projselect.ProjSelectDlg(self, proj_fils, self.active_proj)
        dlgProj.ShowModal()
        event.Skip()

    def on_proj_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_proj, 
                            self.help_img_left+self.proj_img_offset, 
                            self.help_img_top-20, True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt_projs = _("Projects let SOFA know how to connect to your data, "
                      "what labels to use, your favourite styles etc. The "
                      "default project is OK to get you started.")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_projs, 
                                                self.max_help_text_width), 
                    wx.Rect(self.main_left, self.help_text_top, 
                            self.help_text_width, 260))
        event.Skip()
    
    def on_prefs_click(self, event):
        import prefs
        debug = False
        try:
            prefs_dic = \
                config_globals.get_settings_dic(subfolder=mg.INT_FOLDER, 
                                                fil_name=mg.INT_PREFS_FILE)
        except Exception:
            prefs_dic = {}
        if debug: print(prefs_dic)
        dlg = prefs.PrefsDlg(parent=self, prefs_dic_in=prefs_dic)
        dlg.ShowModal()
        event.Skip()
    
    def on_prefs_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_prefs, 
                            self.help_img_left+self.prefs_img_offset, 
                            self.help_img_top-10, True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt_pref = _("Set preferences e.g. format for entering dates")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_pref, 
                                                self.max_help_text_width), 
                    wx.Rect(self.main_left, self.help_text_top, 
                            self.help_text_width, 260))
        event.Skip()
        
    def on_data_click(self, event):
        # open proj selection form
        import dataselect
        proj_name = self.active_proj
        dlgData = dataselect.DataSelectDlg(self, proj_name)
        dlgData.ShowModal()
        event.Skip()
        
    def on_data_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_data, 
                            self.help_img_left+self.data_img_offset, 
                            self.help_img_top-25, True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt1 = _(u"Enter data into a fresh data table or select an existing "
                 u"table to edit or add data to.")
        txt2 = _(u"For tables in the SOFA database you can also:")
        txt3 = _(u"* rename data tables, ")
        txt4 = _(u"* add, delete or rename fields, ")
        txt5 = _(u"* change the data type of fields, ")
        txt6 = _(u"* recode values from one field into another")
        txt7 = _(u"e.g. age into age group")
        text2draw = (
             lib.get_text_to_draw(txt1, self.max_help_text_width) + u"\n\n" +
             lib.get_text_to_draw(txt2, self.max_help_text_width) + u"\n " +
             lib.get_text_to_draw(txt3, self.max_help_text_width) + u"\n " +
             lib.get_text_to_draw(txt4, self.max_help_text_width) + u"\n " +
             lib.get_text_to_draw(txt5, self.max_help_text_width) + u"\n " +
             lib.get_text_to_draw(txt6, self.max_help_text_width) + u"\n    " +
             lib.get_text_to_draw(txt7, self.max_help_text_width)
                     )
        panel_dc.DrawLabel(text2draw, 
                    wx.Rect(self.main_left, self.help_text_top, 
                            self.help_text_width, 260))
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
        panel_dc.DrawBitmap(self.bmp_import, 
                            self.help_img_left+self.import_img_offset, 
                            self.help_img_top-20, True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt_entry = _("Import data e.g. a csv file, or a spreadsheet (Excel, "
                      "Open Document, or Google Docs).")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_entry, 
                                                self.max_help_text_width), 
                    wx.Rect(self.main_left, self.help_text_top, 
                            self.help_text_width-10, 260))
        event.Skip()

    def on_tables_click(self, event):
        "Open make table gui with settings as per active_proj"
        wx.BeginBusyCursor()
        import report_table
        try:
            dlg = report_table.DlgMakeTable()
            lib.safe_end_cursor()
            dlg.ShowModal()
        except Exception, e:
            msg = _("Unable to open report table dialog."
                    "\nCaused by error: %s") % lib.ue(e)
            print(traceback.format_exc())
            wx.MessageBox(msg)
        finally:
            lib.safe_end_cursor()
            event.Skip()
        
    def on_tables_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_tabs, 
                            self.help_img_left+self.report_img_offset, 
                            self.help_img_top-10, True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt1 = _(u"Make report tables e.g. Age vs Gender") 
        txt2 = _(u"Can make simple Frequency Tables, Crosstabs, "
                u"Row Stats Tables (mean, median, standard deviation etc), "
                u"and simple lists of data.")
        txt2draw = (lib.get_text_to_draw(txt1, self.max_help_text_width) + 
                    u"\n\n" +
                    lib.get_text_to_draw(txt2, self.max_help_text_width))
        panel_dc.DrawLabel(txt2draw, wx.Rect(self.main_left, self.help_text_top, 
                                             self.help_text_width, 260))      
        event.Skip()
    
    def get_script(self, cont, script):
        cont.append(mg.JS_WRAPPER_L)
        cont.append(script)
        cont.append(mg.JS_WRAPPER_R)
    
    def on_charts_click(self, event):
        import charting_dlg
        wx.BeginBusyCursor()
        try:
            dlg = charting_dlg.DlgCharting(_("Make Chart"))
            lib.safe_end_cursor()
            dlg.ShowModal()
        except Exception, e:
            msg = _(u"Unable to connect to data as defined in project %s.  "
                    u"Please check your settings") % self.active_proj
            wx.MessageBox(msg)
            raise Exception(u"%s.\nCaused by errors:\n\n%s" % 
                            (msg, traceback.format_exc()))
        finally:
            lib.safe_end_cursor()
            event.Skip()
        
    def on_charts_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_chart, 
                            self.help_img_left+self.chart_img_offset, 
                            self.help_img_top-20, True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt_charts = _("Make attractive charts with dynamic visual effects "
                       "e.g. a bar chart of sales")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_charts, 
                                                self.max_help_text_width), 
                        wx.Rect(self.main_left, self.help_text_top, 
                                self.help_text_width, 260))
        event.Skip()
    
    def on_stats_click(self, event):
        # open statistics selection dialog
        wx.BeginBusyCursor()
        import stats_select
        try:
            dlg = stats_select.StatsSelectDlg(self.active_proj)
            lib.safe_end_cursor()
            dlg.ShowModal()
        except Exception, e:
            msg = _("Unable to connect to data as defined in project %s.  "
                    "Please check your settings.") % self.active_proj
            wx.MessageBox(msg)
            raise Exception(u"%s.\nCaused by error: %s" % (msg, 
                                                    traceback.format_exc()))
        finally:
            lib.safe_end_cursor()
            event.Skip()
        
    def on_stats_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_stats, 
                            self.help_img_left+self.stats_img_offset, 
                            self.help_img_top-25, True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt1 = _(u"Run statistical tests on your data - e.g. a Chi Square to "
                u"see if there is a relationship between age group and gender.")
        txt2 = _(u"SOFA focuses on the statistical tests most users need most "
                 u"of the time.")
        txt3 = u"QUOTE: %s (%s)" % quotes.get_quote()
        txt2draw = (
                    lib.get_text_to_draw(txt1, self.max_help_text_width) + 
                    u"\n\n" +
                    lib.get_text_to_draw(txt2, self.max_help_text_width) + 
                    u"\n\n" +
                    lib.get_text_to_draw(txt3, self.max_help_text_width)
                    )
        panel_dc.DrawLabel(txt2draw, wx.Rect(self.main_left, self.help_text_top, 
                                             self.help_text_width, 260))
        event.Skip()
    
    def on_exit_click(self, event):
        debug = False
        wx.BeginBusyCursor()
        # wipe any internal images
        int_img_pattern = os.path.join(mg.INT_PATH, u"*.png")
        if debug: print(int_img_pattern)
        for delme in glob.glob(int_img_pattern):
            if debug: print(delme)
            os.remove(delme)
        lib.safe_end_cursor()
        #LOCAL_PATH_SETUP_NEEDED = True # testing
        if LOCAL_PATH_SETUP_NEEDED: # if first use, pop up on way out
            dlg = FeedbackDlg(self)
            dlg.ShowModal()
        self.Destroy()
        sys.exit()
        
    def on_exit_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_exit, self.help_img_left, 
                            self.help_img_top-12, True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt_exit = _("Exit SOFA Statistics")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_exit, 
                                                self.max_help_text_width), 
                    wx.Rect(self.main_left, self.help_text_top, 
                            self.help_text_width, 260))
        event.Skip()

try:
    app = SofaApp()
    #inspect = True
    #if inspect:
    #    import wx.lib.inspection
    #    wx.lib.inspection.InspectionTool().Show()
    app.MainLoop()
except Exception, e:
    print(traceback.format_exc())
    app = setup.ErrMsgApp(e)
    app.MainLoop()
    del app
