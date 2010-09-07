#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import

dev_debug = True
test_lang = False

"""
Start up launches the SOFA main form.  Along the way it tries to detect errors
    and report on them to the user so that they can seek help.  E.g. faulty
    version of Python being used to launch SOFA; or missing images needed by the 
    form.
Start up can also run test code to diagnose early problems.
Start up also checks to see if the current user of SOFA has their local SOFA 
    folder in place ready to use.  If not, SOFA constructs one. First, it 
    creates the required folder and subfolders.  Then it populates them by 
    copying across css, sofa_db, default proj, vdts, and report extras. 
    In the local folder the default project file is modified to point to the 
    user's file paths.  A version file is made for future reference.
SOFA may also look to see if the local folder was created by an older version of 
    SOFA.  There may be some special tasks to conduct e.g. updating css files.
If missing, a SOFA recovery folder is also made.  If there is already a recovery 
    folder, but the existing local copy of SOFA was older than the installing 
    copy, the recovery folder will be wiped and overwritten with the latest 
    files.
When the form is shown for the first time on Windows versions, a warning is 
    given and com types are initialised.
"""

import warnings
warnings.simplefilter('ignore', DeprecationWarning)
warnings.simplefilter('ignore', UserWarning)

import codecs
import gettext
import glob
import os
import platform
import shutil
import sqlite3 as sqlite
import sys
import traceback
MAC_PATH = u"/Library/sofa"
if platform.system() == "Darwin":
    sys.path.insert(0, MAC_PATH) # start is running from Apps folder
import wxversion
wxversion.select("2.8")
import wx
try:
    from agw import hyperlink as hl
except ImportError: # if it's not there locally, try the wxPython lib.
    try:
        import wx.lib.agw.hyperlink as hl
    except ImportError:
        raise Exception(u"There seems to be a problem related to your "
                        u"wxPython package.")
# All i18n except for wx-based (which MUST happen after wx.App init)
# http://wiki.wxpython.org/RecipesI18n
# Install gettext.  Now all strings enclosed in "_()" will automatically be
# translated.
gettext.install('sofa', './locale', unicode=True)
try:
    import my_globals as mg # has translated text
    import lib
    import config_globals
    import my_exceptions
except Exception, e:
    raise Exception(u"Problem with first round of local importing")

# Give the user something if the program fails at an early stage before anything
# appears on the screen.  Can only guarantee this from here onwards because I 
# need lib etc.
class MsgFrame(wx.Frame):
    def __init__(self, e, raw_error_msg):
        wx.Frame.__init__(self, None, title=_("SOFA Error"))
        error_msg = lib.ue(e)
        if not raw_error_msg:
            error_msg = (u"Something went wrong with running SOFA Statistics. "
                         u"Please email the lead developer for help - "
                         u"grant@sofastatistics.com\n\nCaused by error: " +
                         error_msg)
        wx.MessageBox(error_msg)
        self.Destroy()
        import sys
        sys.exit()
        

class MsgApp(wx.App):

    def __init__(self, e, raw_error_msg=False):
        self.e = e
        self.raw_error_msg = raw_error_msg
        wx.App.__init__(self, redirect=False, filename=None)

    def OnInit(self):
        msgframe = MsgFrame(self.e, self.raw_error_msg)
        msgframe.Show()
        self.SetTopWindow(msgframe)
        return True


def check_python_version():
    if not sys.version.startswith(u"2.6"):
        fixit_file = os.path.join(mg.USER_PATH, u"Desktop", 
                                  u"how to get SOFA working.txt")
        f = open(fixit_file, "w")
        msg = (u"\n" + u"*"*80 + 
               u"\nHOW TO GET SOFA STATISTICS WORKING AGAIN\n" 
               + u"*"*80 +
               u"\n\nIt looks like an incorrect version of Python is being "
               u"used to run SOFA Statistics. "
               u"Fortunately, this is easily fixed (assuming you installed "
               u"Python 2.6 as part of the SOFA installation)."
               u"\n\nYou need to click the SOFA icon once with the right mouse "
               u"button and select Properties.\n\nIn the Shortcut tab, there "
               u"is a text box called Target.\n\nChange it from "
               u"\"C:\\Program Files\\sofa\\start.pyw\"\nto\n"
               u"C:\\Python26\\pythonw.exe "
               u"\"C:\Program Files\\sofa\\start.pyw\" "
               u"and click the OK button down the bottom.\n\nIf Python 2.6 is "
               u"installed somewhere else, change the Target details "
               u"accordingly - e.g. to D:\Python26 etc"
               u"\n\nFor help, please contact grant@sofastatistics.com")
        f.write(msg)
        f.close()    
        msgapp = MsgApp(msg + "\n\n" + u"*"*80 +u"\n\nThis message has been "
                u"saved to a file on your Desktop for future reference", True)
        msgapp.MainLoop()
        del msgapp

check_python_version() # do as early as possible.  Game over if Python faulty.

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

def get_installed_version(local_path):
    """
    Useful for working out if current version newer than installed version. Or
        if installed version is too old to work with this (latest) version.
        Perhaps we can migrate the old proj file if we know its version.
    """
    version_path = os.path.join(local_path, mg.VERSION_FILE)
    if os.path.exists(version_path):
        f = open(version_path, "r")
        installed_version = f.read().strip()
        f.close()
    else:
        installed_version = None
    return installed_version

def make_local_subfolders(local_path, local_subfolders):
    """
    Create user home folder and required subfolders if not already done.
    """
    try:
        os.mkdir(local_path)
    except OSError, e:
        pass
    except Exception, e:
        raise Exception(u"Unable to make local SOFA path %s." % local_path +
                        u"\nCaused by error: %s" % lib.ue(e))
    for local_subfolder in local_subfolders: # create required subfolders
        try:
            os.mkdir(os.path.join(local_path, local_subfolder))
        except OSError, e:
            pass
        except Exception, e:
            raise Exception(u"Unable to make local subfolder %s." % 
                            local_subfolder +
                            u"\nCaused by error: %s" % lib.ue(e))
    print(u"Made local subfolders under %s" % local_path)

def run_test_code(script):
    """
    Look for file called sofa_test.py in internal folder.  If there, run it.
    """
    test_path = os.path.join(mg.INT_PATH, script)
    if not os.path.exists(test_path):
        return
    f = codecs.open(test_path, "r", "utf8")
    test_code = f.read()
    f.close()
    test_code = lib.clean_bom_utf8(test_code)
    test_dic = {}
    try:
        # http://docs.python.org/reference/simple_stmts.html
        exec test_code in test_dic
    except SyntaxError, e:
        raise Exception(_("Syntax error in test script \"%s\".  " % test_path +
                          "\nCaused by error: %s" % lib.ue(e)))
    except Exception, e:
        raise Exception(_("Error running test script \"%s\"." % test_path +
                          "\nCaused by errors:\n\n%s" % traceback.format_exc()))
    print(u"Ran test code %s" % script)

def populate_css_path(prog_path, local_path):
    styles = [mg.DEFAULT_STYLE, u"grey_spirals.css", u"lucid_spirals.css", 
              u"pebbles.css"]
    for style in styles:
        try:
            shutil.copy(os.path.join(prog_path, u"css", style), 
                        os.path.join(local_path, u"css", style))
        except Exception, e:
            raise Exception(u"Problem populating css path."
                            u"\nCaused by error: %s" % lib.ue(e))
    print(u"Populated css paths under %s" % local_path)

def populate_extras_path(prog_path, local_path):
    extras = [u"arc.xd.js", u"blank.gif", u"blank.htm", u"dojo.xd.js", 
              u"gradient.xd.js", u"grey_spirals.gif", u"lucid_spirals.gif", 
              u"pebbles.gif", u"sofa_charts.js", 
              u"sofalayer.js.uncompressed.js", u"tundra.css", u"vml.xd.js"]
    for extra in extras:
        try:
            shutil.copy(os.path.join(prog_path, mg.REPORTS_FOLDER, 
                                     mg.REPORT_EXTRAS_FOLDER, extra), 
                        os.path.join(local_path, mg.REPORTS_FOLDER, 
                                     mg.REPORT_EXTRAS_FOLDER, extra))
        except Exception, e:
            raise Exception(u"Problem populating report extras path."
                            u"\nCaused by error: %s" % lib.ue(e))
    print(u"Populated report extras path under %s" % local_path)

def populate_local_paths(prog_path, local_path, default_proj):
    """
    Install local set of files in user home dir if necessary.
    """
    # copy across css, sofa_db, default proj, vdts, and report extras 
    populate_css_path(prog_path, local_path)
    shutil.copy(os.path.join(prog_path, mg.INT_FOLDER, mg.SOFA_DB), 
                os.path.join(local_path, mg.INT_FOLDER, mg.SOFA_DB))
    shutil.copy(os.path.join(prog_path, u"projs", mg.DEFAULT_PROJ), 
                default_proj)
    shutil.copy(os.path.join(prog_path, u"vdts", mg.DEFAULT_VDTS), 
                os.path.join(local_path, u"vdts", mg.DEFAULT_VDTS))
    populate_extras_path(prog_path, local_path)
    print(u"Populated local paths under %s" % local_path)

def config_local_proj(local_path, default_proj, settings_subfolders):
    """
    Modify default project settings to point to local (user) SOFA directory.
    """
    # change home username
    f = codecs.open(default_proj, "r", "utf-8")
    proj_str = f.read() # provided by me - no BOM or non-ascii 
    f.close()
    for path in settings_subfolders:
        new_str = lib.escape_pre_write(os.path.join(mg.LOCAL_PATH, path, u""))
        proj_str = proj_str.replace(u"/home/g/sofa/%s/" % path, new_str)
    # add MS Access and SQL Server into mix if Windows
    if mg.PLATFORM == mg.WINDOWS:
        proj_str = proj_str.replace(u"default_dbs = {",
                            u"default_dbs = {'%s': None, " % mg.DBE_MS_ACCESS)
        proj_str = proj_str.replace(u"default_tbls = {",
                            u"default_tbls = {'%s': None, " % mg.DBE_MS_ACCESS)
        proj_str = proj_str.replace(u"default_dbs = {",
                            u"default_dbs = {'%s': None, " % mg.DBE_MS_SQL)
        proj_str = proj_str.replace(u"default_tbls = {",
                            u"default_tbls = {'%s': None, " % mg.DBE_MS_SQL)
    f = codecs.open(default_proj, "w", "utf-8")
    f.write(proj_str)
    f.close()
    # create file as tag we have done the changes to the proj file
    f = open(os.path.join(local_path, mg.PROJ_CUSTOMISED_FILE), "w")
    f.write(u"Local project file customised successfully :-)")
    f.close()
    print(u"Configured default project file for user")

def store_version(local_path):
    f = file(os.path.join(local_path, mg.VERSION_FILE), "w")
    f.write(mg.VERSION)
    f.close()
    print(u"Stored version as %s" % mg.VERSION)

def get_installer_version_status(local_path):
    try:
        installer_is_newer = lib.version_a_is_newer(version_a=mg.VERSION, 
                                    version_b=get_installed_version(local_path))
        installer_newer_status_known = True
    except Exception, e:
        installer_is_newer = None
        installer_newer_status_known = False
    return installer_is_newer, installer_newer_status_known

def freshen_recovery(local_subfolders):
    """
    Need a good upgrade process which leaves existing configuration intact if 
        possible but creates recovery folder which is guaranteed to work with 
        the version just installed.
    Always have two local folders - the main sofa folder and a sofa_recovery 
        folder.
    If the version of SOFA running is newer than the version in __version__.txt, 
        wipe the sofa_recovery folder, and make it afresh.  The home folder 
        should always contain a sofa-type folder which would allow the latest 
        installed version of SOFA to run.  If the ordinary sofa folder is faulty 
        in some way, can always wipe it and rename sofa_recovery to sofa and 
        open up successfully.
    The "sofa_recovery" folder should have a default project file which points 
        to the ordinary home "sofa" folder.  This will only work, of course, if 
        the folder is made operational by renaming it to "sofa".
    """
    installer_recovery_is_newer, installer_recovery_newer_status_known = \
                                get_installer_version_status(mg.RECOVERY_PATH)
    if (installer_recovery_is_newer or not installer_recovery_newer_status_known
            or not os.path.exists(mg.RECOVERY_PATH)):
        # make fresh recovery folder (over top of previous if necessary)
        try:
            shutil.rmtree(mg.RECOVERY_PATH)
        except OSError:
            pass
        make_local_subfolders(mg.RECOVERY_PATH, local_subfolders)
        default_proj = os.path.join(mg.RECOVERY_PATH, u"projs", mg.DEFAULT_PROJ)
        populate_local_paths(prog_path, mg.RECOVERY_PATH, default_proj)
        config_local_proj(mg.RECOVERY_PATH, default_proj, subfolders_in_proj)
        store_version(mg.RECOVERY_PATH)
    print(u"Freshened recovery")

subfolders_in_proj = [u"css", mg.INT_FOLDER, u"projs", mg.REPORTS_FOLDER, 
                      u"scripts", u"vdts"]
oth_subfolders = [os.path.join(mg.REPORTS_FOLDER, mg.REPORT_EXTRAS_FOLDER)]
local_subfolders = subfolders_in_proj + oth_subfolders
if mg.PLATFORM == mg.MAC:
    prog_path = MAC_PATH
else:
    prog_path = os.path.dirname(__file__)
installer_is_newer, installer_newer_status_known = \
                                    get_installer_version_status(mg.LOCAL_PATH)
try:
    # 1) create local SOFA folder if missing. Otherwise, leave intact for now
    local_path_setup_needed = not os.path.exists(mg.LOCAL_PATH)
    if local_path_setup_needed:
        make_local_subfolders(mg.LOCAL_PATH, local_subfolders)
    run_test_code(mg.TEST_SCRIPT_EARLIEST)
    if local_path_setup_needed:
        # need mg but must run pre code calling dd
        default_proj = os.path.join(mg.LOCAL_PATH, u"projs", mg.DEFAULT_PROJ)
        populate_local_paths(prog_path, mg.LOCAL_PATH, default_proj)
        config_local_proj(mg.LOCAL_PATH, default_proj, subfolders_in_proj)
        store_version(mg.LOCAL_PATH)
    run_test_code(mg.TEST_SCRIPT_POST_CONFIG) # can now use dd and proj config
    # 2) Modify existing local SOFA folder if versions require it
    if not local_path_setup_needed: # any fresh one won't need modification
        try: # if already installed version is older than 0.9.16 ...
            installed_version = get_installed_version(mg.LOCAL_PATH)
            if installed_version is None or \
                    lib.version_a_is_newer(version_a=u"0.9.16",
                                           version_b=installed_version):
                # update css files - url(images...) -> url("images...")
                populate_css_path(prog_path, mg.LOCAL_PATH)
                # add new sofa_report_extras folder and populate it
                REPORT_EXTRAS_PATH = os.path.join(mg.LOCAL_PATH, 
                                                  mg.REPORTS_FOLDER, 
                                                  mg.REPORT_EXTRAS_FOLDER)
                try:
                    os.mkdir(REPORT_EXTRAS_PATH) # under reports
                except OSError, e:
                    pass # already there
                except Exception, e:
                    raise Exception(u"Unable to make report extras path %s." % 
                                    REPORT_EXTRAS_PATH +
                                    u"\nCaused by error: %s" % lib.ue(e))
                populate_extras_path(prog_path, mg.LOCAL_PATH)
                store_version(mg.LOCAL_PATH) # update it so only done once    
        except Exception, e:
            raise Exception(u"Problem modifying your local sofa folder. One "
                            u"option is to delete the %s folder and let SOFA "
                            u"make a fresh one." % mg.LOCAL_PATH)
    # 3) Make a fresh recovery folder if needed
    freshen_recovery(local_subfolders)
except Exception, e:
    msg = (u"Problem running initial setup.\nCaused by error: %s" % lib.ue(e))
    msgapp = MsgApp(msg)
    msgapp.MainLoop()
    del msgapp
try:
    import getdata # call before all modules relying on mg.DATA_DETS as dd
    import config_dlg # actually uses proj dict and connects to sofa_db
    import full_html
    import projects
    import projselect
    import quotes
except Exception, e:
    msg = (u"Problem with second round of local importing."
           u"\nCaused by error: %s" % lib.ue(e))
    msgapp = MsgApp(msg)
    msgapp.MainLoop()
    del msgapp

def get_blank_btn_bmp(xpm=u"blankbutton.xpm"):
    blank_btn_path = os.path.join(SCRIPT_PATH, u"images", xpm)
    if not os.path.exists(blank_btn_path):
        raise Exception(u"Problem finding background button image.  "
                        u"Missing path: %s" % blank_btn_path)
    try:
        blank_btn_bmp = wx.Image(blank_btn_path, 
                                 wx.BITMAP_TYPE_XPM).ConvertToBitmap()
    except Exception:
        raise Exception(u"Problem creating background button image from %s"
                        % blank_btn_path)
    return blank_btn_bmp

def get_next_y_pos(start, height):
    "Facilitate regular y position of buttons"
    i = 0
    while True:
        yield start + (i*height)
        i += 1


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
        try:
            # http://wiki.wxpython.org/RecipesI18n
            path = sys.path[0].decode(sys.getfilesystemencoding())
            langdir = os.path.join(path,u'locale')
            langid = wx.LANGUAGE_GALICIAN if test_lang else wx.LANGUAGE_DEFAULT
            # next line will only work if locale is installed on the computer
            mylocale = wx.Locale(langid) #, wx.LOCALE_LOAD_DEFAULT)
            canon_name = mylocale.GetCanonicalName() # e.g. en_NZ, gl_ES etc
            # want main title to be right size but some langs too long for that
            self.main_font_size = 20 if canon_name.startswith('en_') else 16
            mytrans = gettext.translation(u"sofa", langdir, 
                                        languages=[canon_name], fallback = True)
            mytrans.install()
            if platform.system() == u"Linux":
                try:
                    # to get some language settings to display properly:
                    os.environ['LANG'] = u"%s.UTF-8" % canon_name
                except (ValueError, KeyError):
                    pass
            mg.MAX_WIDTH = wx.Display().GetGeometry()[2]
            mg.MAX_HEIGHT = wx.Display().GetGeometry()[3]
            mg.HORIZ_OFFSET = 0 if mg.MAX_WIDTH < 1224 else 200
            frame = StartFrame(self.main_font_size)
            frame.CentreOnScreen(wx.VERTICAL) # on dual monitor, 
                # wx.BOTH puts in screen 2 (in Ubuntu at least)!
            frame.Show()
            self.SetTopWindow(frame)
            return True
        except Exception, e:
            try:
                frame.Close()
            except Exception:
                pass
            raise

class StartFrame(wx.Frame):
    
    def __init__(self, main_font_size):
        debug = False
        try:
            error_msg = mg.PATH_ERROR
        except Exception:
            error_msg = None
        if error_msg:
            raise Exception(error_msg)
        self.main_font_size = main_font_size
        # Gen set up
        wx.Frame.__init__(self, None, title=_("SOFA Start"), 
                          size=(SCREEN_WIDTH, 600), pos=(mg.HORIZ_OFFSET,-1),
                          style=wx.CAPTION|wx.MINIMIZE_BOX|wx.SYSTEM_MENU)
        # Windows doesn't include window decorations
        y_start = self.GetClientSize()[1] - self.GetSize()[1]
        self.SetClientSize(self.GetSize())
        self.panel = wx.Panel(self, size=(SCREEN_WIDTH, 600)) # win
        self.panel.SetBackgroundColour(wx.Colour(205, 217, 215))
        self.panel.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SHOW, self.on_show) # no Mac version needed - win only
        self.active_proj = mg.DEFAULT_PROJ
        proj_dic = config_globals.get_settings_dic(subfolder=u"projs", 
                                                   fil_name=self.active_proj)
        if not mg.DATA_DETS:
            try:
                mg.DATA_DETS = getdata.DataDets(proj_dic)
                if debug: print("Updated mg.DATA_DETS")
            except Exception, e:
                lib.safe_end_cursor()
                wx.MessageBox(_("Unable to connect to data as defined in " 
                                "project %s.  Please check your settings." % 
                                self.active_proj))
                raise # for debugging
                return
        config_dlg.add_icon(frame=self)
        # background image
        sofa = os.path.join(SCRIPT_PATH, u"images", u"sofa2.xpm")
        if not os.path.exists(sofa):
            raise Exception(u"Problem finding background button image.  "
                            u"Missing path: %s" % sofa)
        try:
            self.bmp_sofa = wx.Image(sofa, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        except Exception:
            raise Exception(u"Problem creating background button image from %s"
                            % sofa)
        # slice of image to be refreshed (where text and image will be)
        blankwp_rect = wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_IMG_LEFT+35, 250)
        self.blank_wallpaper = self.bmp_sofa.GetSubBitmap(blankwp_rect)
        blankps_rect = wx.Rect(MAIN_LEFT, 218, 610, 30)
        self.blank_proj_strip = self.bmp_sofa.GetSubBitmap(blankps_rect)
        # buttons
        font_buttons = wx.Font(14 if mg.PLATFORM == mg.MAC else 10, 
                               wx.SWISS, wx.NORMAL, wx.BOLD)
        g = get_next_y_pos(284, BTN_DROP)
        # on-line help
        bmp_btn_help = \
           lib.add_text_to_bitmap(get_blank_btn_bmp(xpm=u"blankhelpbutton.xpm"), 
                _("Online Help"), font_buttons, "white")
        self.btn_help = wx.BitmapButton(self.panel, -1, bmp_btn_help, 
                                        pos=(BTN_LEFT, g.next()))
        self.btn_help.Bind(wx.EVT_BUTTON, self.on_help_click)
        self.btn_help.Bind(wx.EVT_ENTER_WINDOW, self.on_help_enter)
        self.btn_help.SetDefault()
        # Proj
        bmp_btn_proj = lib.add_text_to_bitmap(get_blank_btn_bmp(), 
                        _("Select Project"), font_buttons, "white")
        self.btn_proj = wx.BitmapButton(self.panel, -1, bmp_btn_proj, 
                                        pos=(BTN_LEFT, g.next()))
        self.btn_proj.Bind(wx.EVT_BUTTON, self.on_proj_click)
        self.btn_proj.Bind(wx.EVT_ENTER_WINDOW, self.on_proj_enter)
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
        if mg.PLATFORM == mg.LINUX:
            hand = wx.StockCursor(wx.CURSOR_HAND)
            self.btn_help.SetCursor(hand)
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
        try:
            # help images
            help = os.path.join(SCRIPT_PATH, u"images", u"help.xpm")
            self.bmp_help = wx.Image(help, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
            proj = os.path.join(SCRIPT_PATH, u"images", u"briefcase.xpm")
            self.bmp_proj = wx.Image(proj, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
            prefs = os.path.join(SCRIPT_PATH, u"images", u"prefs.xpm")
            self.bmp_prefs = \
                           wx.Image(prefs, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
            data = os.path.join(SCRIPT_PATH, u"images", u"data.xpm")
            self.bmp_data = wx.Image(data, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
            imprt = os.path.join(SCRIPT_PATH, u"images", u"import.xpm")
            self.bmp_import = \
                           wx.Image(imprt, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
            tabs = os.path.join(SCRIPT_PATH, u"images", u"table.xpm")
            self.bmp_tabs = wx.Image(tabs, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
            chart = os.path.join(SCRIPT_PATH, u"images", u"demo_chart.xpm")
            self.bmp_chart = \
                           wx.Image(chart, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
            stats = os.path.join(SCRIPT_PATH, u"images", u"stats.xpm")
            self.bmp_stats = \
                           wx.Image(stats, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
            exit = os.path.join(SCRIPT_PATH, u"images", u"exit.xpm")
            self.bmp_exit = wx.Image(exit, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
            agpl3 = os.path.join(SCRIPT_PATH, u"images", u"agpl3.xpm")
            self.bmp_agpl3 = \
                           wx.Image(agpl3, wx.BITMAP_TYPE_XPM).ConvertToBitmap()
        except Exception, e:
            raise Exception(u"Problem setting up help images."
                            u"\nCaused by error: %s" % lib.ue(e))
        self.HELP_TEXT_FONT = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL)
        link_home = hl.HyperLinkCtrl(self.panel, -1, "www.sofastatistics.com", 
                                     pos=(MAIN_LEFT, TOP_TOP), 
                                     URL="http://www.sofastatistics.com")
        link_home.SetColours(link=wx.Colour(255,255,255), 
                             visited=wx.Colour(255,255,255), 
                             rollover=wx.Colour(255,255,255))
        link_home.SetOwnBackgroundColour(wx.Colour(0, 0, 0))
        link_home.SetOwnFont(wx.Font(12 if mg.PLATFORM == mg.MAC else 9, 
                                     wx.SWISS, wx.NORMAL, wx.NORMAL))
        link_home.SetSize(wx.Size(200, 17))
        link_home.SetUnderlines(link=True, visited=True, rollover=False)
        link_home.SetLinkCursor(wx.CURSOR_HAND)
        link_home.EnableRollover(True)
        link_home.SetVisited(True)
        link_home.UpdateLink(True)
        link_help = hl.HyperLinkCtrl(self.panel, -1, 
                            _("Get help from community"), 
                            pos=(MAIN_LEFT, TOP_TOP + 200), 
                            URL="http://groups.google.com/group/sofastatistics")
        link_help.SetColours(link=TEXT_BROWN, 
                             visited=TEXT_BROWN, 
                             rollover=TEXT_BROWN)
        link_help.SetOwnBackgroundColour(wx.Colour(205, 217, 215))
        link_help.SetOwnFont(wx.Font(12 if mg.PLATFORM == mg.MAC else 9, 
                                     wx.SWISS, wx.NORMAL, wx.NORMAL))
        link_help.SetSize(wx.Size(200, 17))
        link_help.SetUnderlines(link=True, visited=True, rollover=False)
        link_help.SetLinkCursor(wx.CURSOR_HAND)
        link_help.EnableRollover(True)
        link_help.SetVisited(True)
        link_help.UpdateLink(True)
        if mg.DBE_PROBLEM:
            prob = os.path.join(mg.INT_PATH, u"database connection problem.txt")
            f = codecs.open(prob, "w", "utf8")
            f.write(u"\n\n".join(mg.DBE_PROBLEM))
            f.close()
        if mg.MUST_DEL_TMP:
            wx.MessageBox(_("Please click on \"Enter/Edit Data\" and delete"
                        " the table \"%s\"") % mg.TMP_TBL_NAME)
    
    def on_show(self, event):
        self.init_com_types(self.panel)
    
    def init_com_types(self, panel):
        """
        If first time opened, and in Windows, warn user about delay setting 
            up (comtypes).
        """
        COMTYPES_HANDLED = u"comtypes_handled.txt"
        comtypes_tag = os.path.join(mg.LOCAL_PATH, COMTYPES_HANDLED)
        if (mg.PLATFORM == mg.WINDOWS and not os.path.exists(comtypes_tag)):
            # init com types
            wx.MessageBox(_("Click OK to prepare for first use of SOFA "
                            "Statistics.\n\nPreparation may take a moment ..."))
            h = full_html.FullHTML(panel=panel, parent=self, size=(10,10))
            try:
                h.pizza_magic() # must happen after Show
            except Exception:
                pass
            h.show_html(u"")
            h = None
            # leave tag saying it is done
            f = file(comtypes_tag, "w")
            f.write(u"Comtypes handled successfully :-)")
            f.close()
    
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
            panel_dc = wx.PaintDC(self.panel)
            panel_dc.DrawBitmap(self.bmp_sofa, 0, 0, True)
            panel_dc.DrawBitmap(self.bmp_import, HELP_IMG_LEFT-30, 
                                HELP_IMG_TOP-20, True)
            panel_dc.SetTextForeground(wx.WHITE)
            panel_dc.SetFont(wx.Font(12 if mg.PLATFORM == mg.MAC else 8, 
                                     wx.SWISS, wx.NORMAL, wx.NORMAL))
            panel_dc.DrawLabel(_("Version %s") % mg.VERSION, 
                               wx.Rect(MAIN_RIGHT, TOP_TOP, 100, 20))
            panel_dc.SetFont(wx.Font(self.main_font_size+5 if 
                                     mg.PLATFORM == mg.MAC 
                                     else self.main_font_size, 
                                     wx.SWISS, wx.NORMAL, wx.NORMAL))
            panel_dc.DrawLabel(_("Statistics Open For All"), 
                               wx.Rect(MAIN_LEFT, 80, 100, 100))
            panel_dc.SetFont(wx.Font(14 if mg.PLATFORM == mg.MAC else 9, 
                                     wx.SWISS, wx.NORMAL, wx.NORMAL))
            panel_dc.SetTextForeground(TEXT_BROWN)
            panel_dc.DrawLabel(_("SOFA - Statistics Open For All"
                                 "\nthe user-friendly, open-source statistics,"
                                 "\nanalysis & reporting package"), 
               wx.Rect(MAIN_LEFT, 115, 100, 100))
            panel_dc.DrawLabel(lib.get_text_to_draw(self.txtWelcome, 
                                                    MAX_HELP_TEXT_WIDTH), 
                        wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 260))
            panel_dc.SetTextForeground(wx.WHITE)
            panel_dc.SetFont(wx.Font(12 if mg.PLATFORM == mg.MAC else 7, 
                                     wx.SWISS, wx.NORMAL, wx.NORMAL))
            panel_dc.DrawLabel(u"Released under open source AGPL3 licence\n%s "
                               "2009-2010 Paton-Simpson & Associates Ltd" %
                               COPYRIGHT, 
                               wx.Rect(MAIN_LEFT, 547, 100, 50))
            panel_dc.DrawBitmap(self.bmp_agpl3, MAIN_LEFT-115, 542, True)
            # make default db if not already there
            def_db = os.path.join(mg.LOCAL_PATH, mg.INT_FOLDER, mg.SOFA_DB)
            con = sqlite.connect(def_db)
            con.close()
            panel_dc.DrawBitmap(self.blank_proj_strip, MAIN_LEFT, 218, False)
            panel_dc.SetTextForeground(wx.WHITE)
            panel_dc.SetFont(wx.Font(14 if mg.PLATFORM == mg.MAC else 11, 
                                     wx.SWISS, wx.NORMAL, wx.NORMAL))
            panel_dc.DrawLabel(_("Currently using \"%s\" project settings") % 
                                    self.active_proj[:-5],
                               wx.Rect(MAIN_LEFT, 247, 400, 30))
            event.Skip()
        except Exception, e:
            event.Skip()
            self.panel.Unbind(wx.EVT_PAINT)
            wx.CallAfter(self.on_paint_err_msg, e)
            self.Destroy()

    def draw_blank_wallpaper(self, panel_dc):
        panel_dc.DrawBitmap(self.blank_wallpaper, MAIN_LEFT, HELP_TEXT_TOP, 
                            False)
        
    def set_proj(self, proj_text=""):
        "proj_text must NOT have .proj on the end"
        self.active_proj = u"%s.proj" % proj_text
        self.Refresh()

    def on_help_click(self, event):
        import webbrowser
        url = u"http://www.sofastatistics.com/help.php"
        webbrowser.open_new_tab(url)
        event.Skip()

    def on_help_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_help, HELP_IMG_LEFT+50, HELP_IMG_TOP-25, 
                            True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_help = _("Get help on-line, including screen shots and step-by-step" 
                     " instructions. Regularly updated.")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_help, MAX_HELP_TEXT_WIDTH), 
                    wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 260))
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
                config_globals.get_settings_dic(subfolder=mg.INT_FOLDER, 
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
        txt_entry = _("Import data e.g. a csv file, or a spreadsheet (Excel, "
                      "Open Document, or Google Docs).")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_entry, MAX_HELP_TEXT_WIDTH), 
                    wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH-10, 260))
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
            msg = _("Unable to open report table dialog. Caused by error: %s" % 
                    lib.ue(e))
            wx.MessageBox(msg)
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
        import charting_dlg
        wx.BeginBusyCursor()
        try:
            dlg = charting_dlg.DlgCharting(_("Make Chart"))
            lib.safe_end_cursor()
            dlg.ShowModal()
        except Exception, e:
            msg = _("Unable to connect to data as defined in project %s.  "
                    "Please check your settings" % self.active_proj)
            wx.MessageBox(msg)
            raise Exception(u"%s.\nCaused by errors:\n\n%s" % 
                            (msg, traceback.format_exc()))
        finally:
            lib.safe_end_cursor()
            event.Skip()
        
    def on_charts_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_chart, HELP_IMG_LEFT-30, HELP_IMG_TOP-20, 
                            True)
        panel_dc.SetTextForeground(TEXT_BROWN)
        txt_charts = _("Make attractive charts with dynamic visual effects "
                       "e.g. a bar chart of sales")
        panel_dc.DrawLabel(lib.get_text_to_draw(txt_charts, MAX_HELP_TEXT_WIDTH), 
                        wx.Rect(MAIN_LEFT, HELP_TEXT_TOP, HELP_TEXT_WIDTH, 260))
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
                    "Please check your settings." % self.active_proj)
            wx.MessageBox(msg)
            raise Exception(u"%s.\nCaused by error: %s" % (msg, lib.ue(e)))
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

try:
    app = SofaApp()
    app.MainLoop()
except Exception, e:
    app = MsgApp(e)
    app.MainLoop()
    del app
