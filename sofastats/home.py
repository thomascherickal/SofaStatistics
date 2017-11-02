#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
SOFA Statistics is released under the AGPL3 and the copyright is held by
Paton-Simpson & Associates Ltd.

Launches the SOFA main form. Along the way it tries to detect errors and report
on them to the user so that they can seek help. E.g. faulty version of Python
being used to launch SOFA; or missing images needed by the form.

Can also run test code to diagnose early problems.

Also checks to see if the current user of SOFA has their local SOFA folder in
place ready to use. If not, SOFA constructs one. First, it creates the required
folder and subfolders. Then it populates them by copying across css, sofa_db,
default proj, vdts, and report extras.

In the local folder the default project file is modified to point to the user's
file paths. A version file is made for future reference.

SOFA may also look to see if the local folder was created by an older version of
SOFA. There may be some special tasks to conduct e.g. updating css files.

If missing, a SOFA recovery folder is also made. If there is already a recovery
folder, but the existing local copy of SOFA was older than the installing copy,
the recovery folder will be wiped and overwritten with the latest files.

When the form is shown for the first time on Windows versions, a warning is
given and com types are initialised.
"""

from __future__ import absolute_import

dev_debug = False # relates to errors etc once GUI application running.
# show_early_steps is about revealing any errors before the GUI even starts.
show_early_steps = True # same in setup and start
show_more_steps = True
test_lang = False
# look in output for dojo_debug

import sys
import platform

FEEDBACK_LINK = _(u"Give quick feedback on SOFA")

if platform.system() == u"Windows":
    # handle pyw issue - but allow py to output useful messages
    try: # http://bugs.python.org/issue1415#msg57459
        print(" "*10000) # large enough to force flush to file
    except IOError, e: # fails in pyw (i.e. running pythonw.exe)
        # IOError: [Errno 9] Bad file descriptor error when eventually tries to
        # flush content of all the writes to file.
        class NullWriter:
            def __init__(self):
                pass
            def write(self, data):
                pass
        sys.stdout = NullWriter()
from sofastats import setup_sofastats   #@UnresolvedImport # if any modules are going to fail, it will be when this imported
LOCAL_PATH_SETUP_NEEDED = setup_sofastats.setup_folders()
if show_early_steps: print(u"Completed setup_folders successfully.")
import codecs
import datetime
import gettext
import glob
import os
import traceback
import wx
if show_early_steps: print(u"Imported wx successfully.")
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
            raw_input(setup_sofastats.INIT_DEBUG_MSG)
        raise Exception(msg)
if show_early_steps: print(u"Imported hl successfully.")
from sofastats import basic_lib as b  #@UnresolvedImport
if show_early_steps: print(u"Imported basic_lib successfully.")
from sofastats import my_globals as mg  #@UnresolvedImport
if show_early_steps: print(u"Imported my_globals successfully.")
from sofastats import lib  #@UnresolvedImport
if show_early_steps: print(u"Imported lib successfully.")
from sofastats import my_exceptions   #@UnresolvedImport #@UnusedImport
if show_early_steps: print(u"Imported my_exceptions successfully.")
from sofastats import config_globals  #@UnresolvedImport
if show_early_steps: print(u"Imported config_globals successfully.")
from sofastats import config_output  #@UnresolvedImport
if show_early_steps: print(u"Imported config_output successfully.")
from sofastats import backup_sofa  #@UnresolvedImport
if show_early_steps: print(u"Imported backup_sofa successfully.")
from sofastats import getdata  #@UnresolvedImport
if show_early_steps: print(u"Imported getdata successfully.")
from sofastats import projects  #@UnresolvedImport
if show_early_steps: print(u"Imported projects successfully.")
from sofastats import projselect  #@UnresolvedImport
if show_early_steps: print(u"Imported projselect successfully.")
from sofastats import quotes  #@UnresolvedImport
if show_early_steps: print(u"Imported quotes successfully.")

REVERSE = False

t2d = lib.GuiLib.get_text_to_draw
t2b = lib.GuiLib.add_text_to_bitmap
get_bmp = lib.GuiLib.get_bmp
reverse_bmp = lib.GuiLib.reverse_bmp

def setup_lang_and_fonts():
    """
    Must be done after redirection has occurred in __init__ so printing output
    to redirected file can cope with unicode on Win and Mac!

    Must be done AFTER redirection has occurred or has no effect!
    """
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr, 'replace')
    config_globals.set_fonts()
    try:
        setup_i18n()
    except Exception, e:
        print(u"Error setting up internationalisation. Orig error: %s" % e)
        pass # OK if unable to get translation settings. English will do.

def lang_etc(fn):
    def new_on_init(*args, **kwargs):
        setup_lang_and_fonts()
        fn(*args, **kwargs)
        return True # OnInit must return boolean
    return new_on_init


class SofaApp(wx.App):

    def __init__(self):
        # if wanting to initialise the parent class it must be run in
        # child __init__ and nowhere else (not in OnInit for example).
        if dev_debug:
            redirect = False
            filename = None
        else:
            redirect = True
            filename = os.path.join(mg.INT_PATH, u'output.txt')
        wx.App.__init__(self, redirect=redirect, filename=filename)

    @lang_etc
    def OnInit(self):
        """
        Application needs a frame to open so do that after setting some global
        values for screen dimensions.

        Also responsible for setting translations etc so application
        internationalised.
        """
        from sofastats import db_grid  #@UnresolvedImport
        ## the data form assumes the parent will want its var_labels etc updated. We won't use the results so OK to feed in empty dicts.
        proj_dic = config_globals.get_settings_dic(
            subfolder=mg.PROJS_FOLDER, fil_name=mg.DEFAULT_PROJ)
        try:
            frame = StartFrame(proj_dic)
            # on dual monitor, wx.BOTH puts in screen 2 (in Ubuntu at least)!
            frame.CentreOnScreen(wx.VERTICAL)
            frame.Show()
            self.SetTopWindow(frame)
        except Exception, e: # frame will close by itself now
            raise Exception(u"Problem initialising application. "
                u"Original error: %s" % b.ue(e))
        if mg.EXPORT_IMAGES_DIAGNOSTIC:
            wx.MessageBox("Diagnostic mode for export output is on - be ready "
                "to take screen-shots.")
        mg.OPEN_ON_START = proj_dic.get(mg.OPEN_ON_START_KEY, False)
        if mg.OPEN_ON_START:
            readonly = getdata.get_readonly_settings().readonly
            db_grid.open_data_table(frame, var_labels={}, var_notes={},
                var_types={}, val_dics={}, readonly=readonly)


def store_screen_dims():
    mg.MAX_WIDTH = wx.Display().GetGeometry()[2]
    mg.MAX_HEIGHT = wx.Display().GetGeometry()[3]
    mg.HORIZ_OFFSET = 0 if mg.MAX_WIDTH < 1224 else 200

def setup_i18n():
    """
    Esp http://wiki.wxpython.org/Internationalization
    See also http://wiki.wxpython.org/RecipesI18n
    """
    mg.LANGDIR = os.path.join(mg.SCRIPT_PATH, u'locale')
    try:
        canon_name = get_canon_name(mg.LANGDIR)
        mg.CANON_NAME = canon_name
    except Exception, e:
        raise Exception(u"Unable to get canon name. Original error: %s"
            % b.ue(e))
    try:
        mytrans = gettext.translation(u"sofastats", mg.LANGDIR,
            languages=[canon_name,], fallback=True)
        mytrans.install(unicode=True) # must set explicitly here for Mac
    except Exception, e:
        raise Exception(u"Problem installing translation. "
            u"Original error: %s" % b.ue(e))
    if mg.PLATFORM == mg.LINUX:
        try: # to get some language settings to display properly:
            os.environ['LANG'] = u"%s.UTF-8" % canon_name
        except (ValueError, KeyError):
            pass # OK if unable to set environment settings.

def was_translation_supplied(langdir, langid):
    """
    See what is under the locale folder supplied by SOFA installation.
    """
    try:
        langids_supplied = get_langids_supported_by_sofa(langdir)
        supplied = (langid in langids_supplied)
    except Exception, e:
        supplied = False
    return supplied

def get_canon_name(langdir):
    """
    Try to get a canon_name that will work on this system.

    First try the language default. Will only work if SOFA has support for
    that language (and if language actually installed on system).

    If not possible, fall back to closest language supplied. And failing
    that, fall back to English.

    If fails in spite of translation being supplied, suggest options and
    message to pass for support.
    """
    debug = False
    langid, orig_langname = get_langid_and_name(langdir) # may fall back to English
    # Next line will only work if locale installed on computer. On Macs,
    # must be after app starts (http://programming.itags.org/python/2877/)
    mylocale = wx.Locale(langid) #, wx.LOCALE_LOAD_DEFAULT)
    if debug: print_locale_dets(mylocale, langid)
    if mylocale.IsOk():
        canon_name = mylocale.GetCanonicalName()
    else: # failed
        if show_early_steps: print(u"Trouble getting %s" % orig_langname)
        warn_about_canon_probs(mylocale, langid, orig_langname)
        # Resetting mylocale makes frame flash and die if not clean first.
        # http://www.java2s.com/Open-Source/Python/GUI/wxPython/wxPython-src-2.8.11.0/wxPython/demo/I18N.py.htm
        assert sys.getrefcount(mylocale) <= 2
        del mylocale # otherwise C++ object persists too long & crashes
        mylocale = wx.Locale(wx.LANGUAGE_ENGLISH)
        canon_name = mylocale.GetCanonicalName()
    if debug: print(canon_name)
    return canon_name

def get_langid_and_name(langdir):
    """
    Get the best langid possible.

    If some variant of English e.g. English (Australia) just use the main
    English version. There will probably never be lots of English
    translations.

    Otherwise, try the language default. Will only work if SOFA has support for
    that language (and if language actually installed on system).

    If not possible, fall back to closest language supplied. And failing that,
    fall back to English.

    If a failure because SOFA translation not provided, let user know they can
    ask for a translation or even help contribute to a translation.
    """
    orig_langid = (mg.TEST_LANGID if test_lang else wx.LANGUAGE_DEFAULT)
    orig_langinfo = wx.Locale.GetLanguageInfo(orig_langid)
    orig_canon_name = orig_langinfo.CanonicalName
    orig_langname = orig_langinfo.Description
    english = False
    if "_" in orig_canon_name:
        orig_root = orig_canon_name.split("_")[0]
        if orig_root == u"en":
            english = True
    if english:
        langid = wx.LANGUAGE_ENGLISH
    else:
        translation_supplied = was_translation_supplied(langdir, orig_langid)
        if translation_supplied:
            langid = orig_langid # try it - still might fail
        else:
            closest_langid_supplied = get_closest_langid_supplied(langdir,
                orig_langinfo)
            if closest_langid_supplied:
                langid = closest_langid_supplied
                langinfo_used = wx.Locale.GetLanguageInfo(langid)
                langname_used = langinfo_used.Description
            else:
                langid = wx.LANGUAGE_ENGLISH
                langname_used = "UK English"
            msg = (u"SOFA does not appear to have been translated into "
                u"%(orig_langname)s yet. SOFA will operate in "
                u"%(langname_used)s instead. If you are able to help "
                u"translate English into %(orig_langname)s please "
                u"contact %(contact)s." %
                {"orig_langname": orig_langname,
                "langname_used": langname_used,
                "contact": mg.CONTACT})
            print(msg)
    return langid, orig_langname

def warn_about_canon_probs(mylocale, langid, orig_langname):
    """
    If a language isn't installed on the OS then it won't even look for
    the locale subfolder. GetLanguage() will return 1 instead of the langid.
    See also http://code.google.com/p/bpbible/source/browse/trunk/gui/i18n.py?r=977#36
    """
    if mg.PLATFORM == mg.LINUX:
        cli = (u"\n\nSee list of languages installed on your system by "
            u"typing\n       locale -a\ninto a terminal and hitting the "
            u"Enter key.")
    else:
        cli = u""
    msg = (u"Because there was a problem providing a %(orig_langname)s "
        u"translation, SOFA will now operate in English instead. SOFA is"
        u" operating perfectly apart from the attempt to set the "
        u"translation.\n\nDoes your system have %(orig_langname)s "
        u"installed?%(cli)s\n\nThe developer may be able to supply extra "
        u"help: %(contact)s" % {"orig_langname": orig_langname,
        "cli": cli, "contact": mg.CONTACT})
    try:
        lang = mylocale.GetLanguage()
    except Exception, e:
        lang = u"Unable to get language."
    try:
        canon_name = mylocale.GetCanonicalName()
    except Exception, e:
        canon_name = u"Unable to get canonical name."
    try:
        sysname = mylocale.GetSysName()
    except Exception, e:
        sysname = u"Unable to get system name."
    try:
        getlocale = mylocale.GetLocale()
    except Exception, e:
        getlocale = u"Unable to get locale."
    try:
        localename = mylocale.GetName()
    except Exception, e:
        localename = u"Unable to get locale name."
    extra_diagnostics = (u"\n\nExtra details for developer:"
    u"\nGetLanguageName: %(GetLanguageName)s"
    u"\nlangid: %(langid)s"
    u"\nGetlanguage: %(Getlanguage)s"
    u"\nGetCanonicalName: %(GetCanonicalName)s"
    u"\nGetSysName: %(GetSysName)s"
    u"\nGetLocale: %(GetLocale)s"
    u"\nGetName: %(GetName)s" % {u"GetLanguageName": orig_langname,
    u"langid": langid, u"Getlanguage": lang,
    u"GetCanonicalName": canon_name, u"GetSysName": sysname,
    u"GetLocale": getlocale, u"GetName": localename})
    msg += extra_diagnostics
    prob = os.path.join(mg.INT_PATH, u"translation problem.txt")
    f = codecs.open(prob, "w", "utf8")
    f.write(msg)
    f.close()
    #mg.DEFERRED_WARNING_MSGS.append(msg)

def get_langids_supported_by_sofa(langdir):
    locale_pths = os.listdir(langdir)
    langids = []
    for locale_pth in locale_pths:
        try:
            langinfo = wx.Locale.FindLanguageInfo(locale_pth)
            langids.append(langinfo.Language)
        except Exception, e:
            pass # Don't prevent the user getting an English version of SOFA running because of this minor problem.
    return langids

def get_closest_langid_supplied(langdir, orig_langinfo):
    try:
        closest_langid_supplied = None # init
        orig_canon_name = orig_langinfo.CanonicalName
        if "_" in orig_canon_name:
            orig_root = orig_canon_name.split("_")[0]
            langids_supplied = get_langids_supported_by_sofa(langdir)
            for langid in langids_supplied:
                langinfo = wx.Locale.GetLanguageInfo(langid)
                canon_name = langinfo.CanonicalName
                if "_" in canon_name:
                    root = canon_name.split("_")[0]
                    if root == orig_root:
                        closest_langid_supplied = langid
                        break
    except Exception, e:
        closest_langid_supplied = None
    return closest_langid_supplied

def print_locale_dets(mylocale, langid):
    print(u"langid: %s" % langid)
    print(u"Getlanguage: %s" % mylocale.GetLanguage())
    print(u"GetCanonicalName: %s" % mylocale.GetCanonicalName())
    print(u"GetSysName: %s" % mylocale.GetSysName())
    print(u"GetLocale: %s" % mylocale.GetLocale())
    print(u"GetName: %s" % mylocale.GetName())

def get_next_y_pos(start, height):
    "Facilitate regular y position of buttons"
    i = 0
    while True:
        yield start + (i*height)
        i += 1


class StartFrame(wx.Frame):

    def __init__(self, proj_dic):
        # earliest point error msgs can be shown to user in a GUI.
        store_screen_dims()
        deferred_error_msg = u"\n\n".join(mg.DEFERRED_ERRORS)
        if deferred_error_msg:
            raise Exception(deferred_error_msg)
        self.set_layout_constants()
        self.text_brown = (90, 74, 61) # on_paint needs this etc
        wx.Frame.__init__(self, None, title=_("SOFA Start"),
            size=(self.form_width, self.form_height),
            pos=(self.form_pos_left,-1), style=wx.CAPTION|wx.MINIMIZE_BOX
            |wx.CLOSE_BOX|wx.SYSTEM_MENU)
        self.SetClientSize(self.GetSize())
        global REVERSE
        REVERSE = lib.mustreverse()
        self.panel = wx.Panel(self, size=(self.form_width, self.form_height)) # win
        self.panel.SetBackgroundColour(wx.Colour(205, 217, 215))
        self.panel.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SHOW, self.on_show) # doesn't run on Mac
        self.Bind(wx.EVT_CLOSE, self.on_exit_click)
        self.active_proj = mg.DEFAULT_PROJ
        print(u"Run on %s" % datetime.datetime.today().isoformat(" ")
            .split(".")[0] + " " + 20*(u"*"))
        try:
            # trying to actually connect to a database on start up
            mg.DATADETS_OBJ = getdata.DataDets(proj_dic)
            if show_early_steps: print(u"Initialised mg.DATADETS_OBJ")
        except Exception, e:
            lib.GuiLib.safe_end_cursor()
            wx.MessageBox(_("Unable to connect to data as defined in "
                "project %s. Please check your settings.") % self.active_proj)
            raise # for debugging
        try:
            config_output.add_icon(frame=self)
            if show_more_steps: print(u"Added icon to frame")
        except Exception, e:
            lib.GuiLib.safe_end_cursor()
            wx.MessageBox(u"Problem adding icon to frame")
            raise # for debugging
        try:
            self.make_sized_imgs()
            if show_more_steps: print(u"Made sized images")
        except Exception, e:
            lib.GuiLib.safe_end_cursor()
            wx.MessageBox(u"Problem making sized images")
            raise # for debugging
        try:
            self.setup_stable_imgs()
            if show_more_steps: print(u"Set up stable images")
        except Exception, e:
            lib.GuiLib.safe_end_cursor()
            wx.MessageBox(u"Problem making sized images")
            raise # for debugging
        try:
            self.setup_buttons()
            if show_more_steps: print(u"Set up buttons")
        except Exception, e:
            lib.GuiLib.safe_end_cursor()
            wx.MessageBox(u"Problem setting up buttons")
            raise # for debug
        # text
        # NB cannot have transparent background properly in Windows if using
        # a static ctrl
        # http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3045245
        if mg.PLATFORM == mg.MAC:
            self.help_font = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        elif mg.PLATFORM == mg.WINDOWS:
            self.help_font = wx.Font(10.5, wx.DEFAULT, wx.NORMAL, wx.BOLD)
        else:
            self.help_font = wx.Font(10.5, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        try:
            self.set_help_imgs()
            if show_more_steps: print(u"Set up help images")
        except Exception, e:
            lib.GuiLib.safe_end_cursor()
            raise Exception(u"Problem setting up help images."
                u"\nCaused by error: %s" % b.ue(e))
        # upgrade available?
        if show_more_steps: print(u"Got version level")
        new_version = self.get_new_version()
        if show_more_steps: print(u"Got new version (if possible)")
        self.set_upgrade_availability(new_version)
        if show_more_steps: print(u"Identified if upgrade available")
        try:
            self.setup_links(new_version)
            if show_more_steps: print(u"Set up links")
        except Exception, e:
            lib.GuiLib.safe_end_cursor()
            wx.MessageBox(u"Problem setting up links")
            raise # for debugging
            return
        # database check
        if mg.DBE_PROBLEM:
            prob = os.path.join(mg.INT_PATH, u"database connection problem.txt")
            f = codecs.open(prob, "w", "utf8")
            f.write(u"\n\n".join(mg.DBE_PROBLEM))
            f.close()
        if show_more_steps: print(u"Passed check for database problems")
        if mg.MUST_DEL_TMP:
            wx.MessageBox(_(u"Please click on \"Enter/Edit Data\" and delete"
                u" either of these tables if present - \"%(tbl1)s\" and "
                u"\"%(tbl2)s\"") % {u"tbl1": mg.TMP_TBLNAME,
                u"tbl2": mg.TMP_TBLNAME2})
        if show_more_steps: print(u"Passed check for having to delete database")
        #try:
        #    wx.CallAfter(lib.check_crack, show_more_steps) # won't stop form load if fails
        #except Exception:
        #    pass
        # any warnings to display once screen visible?
        warning_div = u"\n\n" + u"-"*20 + u"\n\n"
        deferred_warning_msg = warning_div.join(mg.DEFERRED_WARNING_MSGS)
        if show_more_steps: print(u"Assembled warning message")
        if deferred_warning_msg:
            if show_more_steps: print(u"Has deferred warning message")
            wx.CallAfter(self.on_deferred_warning_msg, deferred_warning_msg)
            if show_more_steps: print(u"Set warning message to CallAfter")

    def get_new_version(self):
        """
        Return empty string if no new version or checking prevented.
        """
        debug = False
        new_version = u""
        try:
            new_version = self.get_latest_version()
        except Exception, e:
            pass
        if debug: print(new_version)
        return new_version

    def set_upgrade_availability(self, new_version):
        """
        new_version will be empty string or a version number e.g. 1.2.3
        Upgrade unavailable if nothing newer or if checking prevented or a
            connection not made.
        """
        try:
            self.upgrade_available = lib.version_a_is_newer(
                version_a=new_version, version_b=mg.VERSION)
        except Exception, e:
            self.upgrade_available = False

    def set_layout_constants(self):
        # layout "constants"
        self.tight_layout = (mg.MAX_WIDTH <= 1024 or mg.MAX_HEIGHT <= 600)
        #self.tight_layout = True # for testing
        #wx.MessageBox("Change tight_layout back")
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
            self.help_img_offset = 0
            self.get_started_img_offset = 0
            self.proj_img_offset = -20
            self.prefs_img_offset = 35
            self.backup_img_offset = 35
            self.data_img_offset = -30
            self.form_pos_left = mg.HORIZ_OFFSET+5
        else:
            self.help_img_left = 575-self.tight_width_drop
            self.chart_img_offset = -10
            self.import_img_offset = -10
            self.report_img_offset = 30
            self.stats_img_offset = 30
            self.help_img_offset = 30
            self.get_started_img_offset = 0
            self.proj_img_offset = 30
            self.prefs_img_offset = 55
            self.backup_img_offset = 55
            self.data_img_offset = 45
            self.form_pos_left = mg.MAX_WIDTH-(self.form_width+10)

    def make_sized_imgs(self):
        """
        Set images according to size constraints (tight_layout).
        """
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
        self.top_sofa = os.path.join(mg.SCRIPT_PATH, u"images", u"top_sofa.gif")
        self.demo_chart_sized = os.path.join(mg.SCRIPT_PATH, u"images",
                                             demo_chart_img)
        self.proj_sized = os.path.join(mg.SCRIPT_PATH, u"images", proj_img)
        self.data_sized = os.path.join(mg.SCRIPT_PATH, u"images", data_img)
        if not os.path.exists(sofabg):
            raise Exception(u"Problem finding background button image.  "
                u"Missing path: %s" % sofabg)
        try:
            self.bmp_sofabg = get_bmp(src_img_path=sofabg, reverse=REVERSE)
        except Exception:
            raise Exception(u"Problem creating background button image from %s"
                % sofabg)

    def set_help_imgs(self):
        # help images
        help_img = os.path.join(mg.SCRIPT_PATH, u"images", u"help.gif")
        self.bmp_help = get_bmp(src_img_path=help_img, reverse=REVERSE)
        get_started = os.path.join(mg.SCRIPT_PATH, u"images",
            u"step_by_step.gif")
        self.bmp_get_started = get_bmp(src_img_path=get_started,
            reverse=REVERSE)
        self.bmp_data = get_bmp(src_img_path=self.data_sized, reverse=REVERSE)
        imprt = os.path.join(mg.SCRIPT_PATH, u"images", u"import.gif")
        self.bmp_import = get_bmp(src_img_path=imprt, reverse=REVERSE)
        tabs = os.path.join(mg.SCRIPT_PATH, u"images", u"table.gif")
        self.bmp_tabs = get_bmp(src_img_path=tabs, reverse=REVERSE)
        self.bmp_chart = get_bmp(src_img_path=self.demo_chart_sized,
            reverse=REVERSE)
        stats = os.path.join(mg.SCRIPT_PATH, u"images", u"stats.gif")
        self.bmp_stats = get_bmp(src_img_path=stats, reverse=REVERSE)
        self.bmp_proj = get_bmp(src_img_path=self.proj_sized, reverse=REVERSE)
        prefs = os.path.join(mg.SCRIPT_PATH, u"images", u"prefs.gif")
        self.bmp_prefs = get_bmp(src_img_path=prefs, reverse=REVERSE)
        backup = os.path.join(mg.SCRIPT_PATH, u"images", u"backup.gif")
        self.bmp_backup = get_bmp(src_img_path=backup, reverse=REVERSE)
        exit_img = os.path.join(mg.SCRIPT_PATH, u"images", u"exit.gif")
        self.bmp_exit = get_bmp(src_img_path=exit_img, reverse=REVERSE)
        agpl3 = os.path.join(mg.SCRIPT_PATH, u"images", u"agpl3.xpm")
        self.bmp_agpl3 = get_bmp(src_img_path=agpl3,
            bmp_type=wx.BITMAP_TYPE_XPM, reverse=REVERSE)

    def setup_stable_imgs(self):
        upgrade = os.path.join(mg.SCRIPT_PATH, u"images", u"upgrade.xpm")
        self.bmp_upgrade = get_bmp(src_img_path=upgrade,
            bmp_type=wx.BITMAP_TYPE_XPM, reverse=REVERSE)
        quote_left = os.path.join(mg.SCRIPT_PATH, u"images",
            u"speech_mark_large.xpm")
        self.bmp_quote_left = get_bmp(src_img_path=quote_left,
            bmp_type=wx.BITMAP_TYPE_XPM, reverse=REVERSE)
        quote_right = os.path.join(mg.SCRIPT_PATH, u"images",
            u"speech_mark_small.xpm")
        self.bmp_quote_right = get_bmp(src_img_path=quote_right,
            bmp_type=wx.BITMAP_TYPE_XPM, reverse=REVERSE)
        self.bmp_top_sofa = get_bmp(src_img_path=self.top_sofa) # ok if reversed
        # slice of image to be refreshed (where text and image will be)
        blankwp_rect = wx.Rect(self.main_left, self.help_text_top,
            self.help_img_left+35, self.blankwp_height)
        self.blank_wallpaper = self.bmp_sofabg.GetSubBitmap(blankwp_rect)
        blankps_rect = wx.Rect(self.main_left, 218, 610, 30)
        self.blank_proj_strip = self.bmp_sofabg.GetSubBitmap(blankps_rect)

    def setup_buttons(self):
        btn_font_sz = 14 if mg.PLATFORM == mg.MAC else 10
        g = get_next_y_pos(284, self.btn_drop)
        # get started
        get_started_btn_bmp = lib.GuiLib.get_blank_btn_bmp(
            xpm=u"blankhelpbutton.xpm")
        bmp_btn_get_started = t2b(get_started_btn_bmp, _("Get Started"),
            btn_font_sz, "white")
        if REVERSE: bmp_btn_get_started = reverse_bmp(bmp_btn_get_started)
        self.btn_get_started = wx.BitmapButton(self.panel, -1,
            bmp_btn_get_started, pos=(self.btn_left, g.next()))
        self.btn_get_started.Bind(wx.EVT_BUTTON, self.on_get_started_click)
        self.btn_get_started.Bind(wx.EVT_ENTER_WINDOW,
            self.on_get_started_enter)
        self.btn_get_started.SetDefault()
        # Data entry
        bmp_btn_data = t2b(lib.GuiLib.get_blank_btn_bmp(), _("Enter/Edit Data"),
            btn_font_sz, "white")
        if REVERSE: bmp_btn_data = reverse_bmp(bmp_btn_data)
        self.btn_data = wx.BitmapButton(self.panel, -1, bmp_btn_data,
            pos=(self.btn_left, g.next()))
        self.btn_data.Bind(wx.EVT_BUTTON, self.on_data_click)
        self.btn_data.Bind(wx.EVT_ENTER_WINDOW, self.on_data_enter)
        # Import
        bmp_btn_import = t2b(lib.GuiLib.get_blank_btn_bmp(),
            _("Import Data"), btn_font_sz, "white")
        if REVERSE: bmp_btn_import = reverse_bmp(bmp_btn_import)
        self.btn_import = wx.BitmapButton(self.panel, -1, bmp_btn_import,
            pos=(self.btn_left, g.next()))
        self.btn_import.Bind(wx.EVT_BUTTON, self.on_import_click)
        self.btn_import.Bind(wx.EVT_ENTER_WINDOW, self.on_import_enter)
        # Report tables
        bmp_btn_tables = t2b(lib.GuiLib.get_blank_btn_bmp(),
            _("Report Tables"), btn_font_sz, "white")
        if REVERSE: bmp_btn_tables = reverse_bmp(bmp_btn_tables)
        self.btn_tables = wx.BitmapButton(self.panel, -1, bmp_btn_tables,
            pos=(self.btn_left, g.next()))
        self.btn_tables.Bind(wx.EVT_BUTTON, self.on_tables_click)
        self.btn_tables.Bind(wx.EVT_ENTER_WINDOW, self.on_tables_enter)
        # Charts
        bmp_btn_charts = t2b(lib.GuiLib.get_blank_btn_bmp(),
            _("Charts"), btn_font_sz, "white")
        if REVERSE: bmp_btn_charts = reverse_bmp(bmp_btn_charts)
        self.btn_charts = wx.BitmapButton(self.panel, -1, bmp_btn_charts,
            pos=(self.btn_left, g.next()))
        self.btn_charts.Bind(wx.EVT_BUTTON, self.on_charts_click)
        self.btn_charts.Bind(wx.EVT_ENTER_WINDOW, self.on_charts_enter)
        # Stats
        bmp_btn_stats = t2b(lib.GuiLib.get_blank_btn_bmp(),
            _("Statistics"), btn_font_sz, "white")
        if REVERSE: bmp_btn_stats = reverse_bmp(bmp_btn_stats)
        self.btn_statistics = wx.BitmapButton(self.panel, -1, bmp_btn_stats,
            pos=(self.btn_left, g.next()))
        self.btn_statistics.Bind(wx.EVT_BUTTON, self.on_stats_click)
        self.btn_statistics.Bind(wx.EVT_ENTER_WINDOW, self.on_stats_enter)
        # Right
        g = get_next_y_pos(284, self.btn_drop)
        # on-line help
        help_btn_bmp = lib.GuiLib.get_blank_btn_bmp(xpm=u"blankhelpbutton.xpm")
        bmp_btn_help = t2b(help_btn_bmp,
            _("Online Help"), btn_font_sz, "white")
        if REVERSE: bmp_btn_help = reverse_bmp(bmp_btn_help)
        self.btn_help = wx.BitmapButton(self.panel, -1, bmp_btn_help,
            pos=(self.btn_right, g.next()))
        self.btn_help.Bind(wx.EVT_BUTTON, self.on_help_click)
        self.btn_help.Bind(wx.EVT_ENTER_WINDOW, self.on_help_enter)
        self.btn_help.SetDefault()
        # Proj
        self.sel_proj_lbl = _("Select Project")
        bmp_btn_proj = t2b(lib.GuiLib.get_blank_btn_bmp(),
            self.sel_proj_lbl, btn_font_sz, "white")
        if REVERSE: bmp_btn_proj = reverse_bmp(bmp_btn_proj)
        self.btn_proj = wx.BitmapButton(self.panel, -1, bmp_btn_proj,
            pos=(self.btn_right, g.next()))
        self.btn_proj.Bind(wx.EVT_BUTTON, self.on_proj_click)
        self.btn_proj.Bind(wx.EVT_ENTER_WINDOW, self.on_proj_enter)
        # Prefs
        bmp_btn_prefs = t2b(lib.GuiLib.get_blank_btn_bmp(),
            _("Preferences"), btn_font_sz, "white")
        if REVERSE: bmp_btn_prefs = reverse_bmp(bmp_btn_prefs)
        self.btn_prefs = wx.BitmapButton(self.panel, -1, bmp_btn_prefs,
            pos=(self.btn_right, g.next()))
        self.btn_prefs.Bind(wx.EVT_BUTTON, self.on_prefs_click)
        self.btn_prefs.Bind(wx.EVT_ENTER_WINDOW, self.on_prefs_enter)
        # Backup
        bmp_btn_backup = t2b(lib.GuiLib.get_blank_btn_bmp(),
            _("Run Backup"), btn_font_sz, "white")
        if REVERSE: bmp_btn_backup = reverse_bmp(bmp_btn_backup)
        self.btn_backup = wx.BitmapButton(self.panel, -1, bmp_btn_backup,
            pos=(self.btn_right, g.next()))
        self.btn_backup.Bind(wx.EVT_BUTTON, self.on_backup_click)
        self.btn_backup.Bind(wx.EVT_ENTER_WINDOW, self.on_backup_enter)
        # Exit
        bmp_btn_exit = t2b(lib.GuiLib.get_blank_btn_bmp(),
            _("Exit"), btn_font_sz, "white")
        if REVERSE: bmp_btn_exit = reverse_bmp(bmp_btn_exit)
        self.btn_exit = wx.BitmapButton(self.panel, -1, bmp_btn_exit,
            pos=(self.btn_right, g.next()))
        self.btn_exit.Bind(wx.EVT_BUTTON, self.on_exit_click)
        self.btn_exit.Bind(wx.EVT_ENTER_WINDOW, self.on_exit_enter)
        if mg.PLATFORM == mg.LINUX:
            hand = wx.StockCursor(wx.CURSOR_HAND)
            self.btn_get_started.SetCursor(hand)
            self.btn_data.SetCursor(hand)
            self.btn_import.SetCursor(hand)
            self.btn_tables.SetCursor(hand)
            self.btn_charts.SetCursor(hand)
            self.btn_statistics.SetCursor(hand)
            self.btn_help.SetCursor(hand)
            self.btn_proj.SetCursor(hand)
            self.btn_prefs.SetCursor(hand)
            self.btn_backup.SetCursor(hand)
            self.btn_exit.SetCursor(hand)

    def setup_links(self, new_version):
        """
        new_version -- might be an empty string but, if so, there should be no
        upgrade available so no link displayed anyway.
        """
        # home link
        home_link_hpos = self.version_right if REVERSE else self.main_left
        link_home = hl.HyperLinkCtrl(self.panel, -1, "www.sofastatistics.com",
            pos=(home_link_hpos, self.top_top),
            URL="http://www.sofastatistics.com")
        lib.GuiLib.setup_link(link=link_home,
            link_colour=wx.Colour(255,255,255), bg_colour=wx.Colour(0, 0, 0))
        # help link
        link_help = hl.HyperLinkCtrl(self.panel, -1,
            _("Get help from community"),
            pos=(self.main_left, self.top_top + 200),
            URL="http://groups.google.com/group/sofastatistics")
        lib.GuiLib.setup_link(link=link_help, link_colour=self.text_brown,
            bg_colour=wx.Colour(205, 217, 215))
        # upgrade link
        if self.upgrade_available:
            upgrade_link_hpos = (self.main_left if REVERSE
                else self.version_right+125)
            link_upgrade = hl.HyperLinkCtrl(self.panel, -1,
                _(u"Upgrade to %s here") % new_version,
                pos=(upgrade_link_hpos, self.top_top),
                URL="http://www.sofastatistics.com/downloads.php")
            lib.GuiLib.setup_link(link=link_upgrade,
                link_colour=wx.Colour(255,255,255),
                bg_colour=wx.Colour(0, 0, 0))
        # feedback link
        feedback_link_hpos = (self.main_left if REVERSE
            else self.main_sofa_logo_right)
        link_feedback = hl.HyperLinkCtrl(self.panel, -1, mg.FEEDBACK_LINK,
            pos=(feedback_link_hpos, self.form_height-53),
            URL="http://www.sofastatistics.com/feedback.htm")
        lib.GuiLib.setup_link(link=link_feedback,
            link_colour=wx.Colour(255,255,255),
            bg_colour=wx.Colour(116, 99, 84))

    def on_deferred_warning_msg(self, deferred_warning_msg):
        wx.MessageBox(deferred_warning_msg)

    def update_sofastats_connect_date(self, sofastats_connect_fil,
            days2wait=30):
        f = codecs.open(sofastats_connect_fil, "w", encoding="utf-8")
        next_check_date = (datetime.datetime.today() +
            datetime.timedelta(days=days2wait)).strftime('%Y-%m-%d')
        f.write("%s = '%s'" % (mg.SOFASTATS_CONNECT_VAR, next_check_date))
        f.close()

    def get_latest_version(self):
        """
        Is there a new version?
        """
        import requests #@UnresolvedImport
        debug = False
        url2open = (u"http://www.sofastatistics.com/%s" %
            mg.SOFASTATS_VERSION_CHECK)
        try:
            url_reply = requests.get(url2open, timeout=4) # timeout affects time waiting for server. If can't get to server at all, dies instantly which is good.
            new_version = u"%s" % url_reply.read().strip()
            url_reply.close()
            if debug: print("Checked new version: %s" % new_version)
        except Exception, e:
            msg = (u"Unable to extract latest sofa version."
                u"\nCaused by error: %s" % b.ue(e))
            if debug: print(msg)
            raise Exception(msg)
        return new_version

    def on_show(self, event):
        setup_sofastats.init_com_types(self, self.panel) # fortunately, not needed on Mac

    def on_paint_err_msg(self, e):
        wx.MessageBox(u"Problem displaying start form. Please email the lead "
            u"developer for help - %s\n\nCaused by error: %s" % (mg.CONTACT,
            b.ue(e)))

    def on_paint(self, event):
        """
        Cannot use static bitmaps and static text to replace. In windows doesn't
        show background wallpaper.

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
                self.help_img_left+self.chart_img_offset, self.help_img_top-20,
                True)
            panel_dc.SetTextForeground(wx.WHITE)
            panel_dc.SetFont(wx.Font(12 if mg.PLATFORM == mg.MAC else 9,
                wx.SWISS, wx.NORMAL, wx.NORMAL))
            version_link_hpos = (self.main_left if REVERSE
                else self.version_right)
            panel_dc.DrawLabel(_("Version %s") % mg.VERSION,
                wx.Rect(version_link_hpos, self.top_top, 100, 20))
            font_sz = 28 if mg.PLATFORM == mg.MAC else 20
            main_text = _("Statistics Open For All")
            extra_width = 40 if mg.PLATFORM == mg.MAC else 60
            main_text_width = self.max_help_text_width + extra_width
            main_fs = lib.GuiLib.get_font_size_to_fit(main_text,
                main_text_width, font_sz, min_font_sz=14)
            panel_dc.SetFont(wx.Font(main_fs, wx.SWISS, wx.NORMAL, wx.NORMAL))
            panel_dc.DrawLabel(main_text, wx.Rect(self.main_left, 80,
                main_text_width, 100))
            panel_dc.SetFont(wx.Font(14 if mg.PLATFORM == mg.MAC else 9,
                wx.SWISS, wx.NORMAL, wx.NORMAL))
            panel_dc.SetTextForeground(self.text_brown)
            panel_dc.DrawLabel(_("SOFA - Statistics Open For All"
                "\nthe user-friendly, open-source statistics,"
                "\nanalysis & reporting package"), wx.Rect(self.main_left, 115,
                100, 100))
            panel_dc.SetFont(self.help_font)
            txt1 = _(u"Welcome to SOFA Statistics. Hovering the mouse "
                u"over the buttons lets you see what you can do.")
            txt2 = _(u"Note - SOFA is great at working with raw data. For data "
                u"that is already summarised you need to use other tools.")
            txt2draw = (t2d(txt1, self.max_help_text_width) +
                u"\n\n" + t2d(txt2, self.max_help_text_width))
            panel_dc.DrawLabel(txt2draw, wx.Rect(self.main_left,
                self.help_text_top, self.help_text_width, 260))
            panel_dc.SetTextForeground(wx.WHITE)
            panel_dc.SetFont(wx.Font(12 if mg.PLATFORM == mg.MAC else 8,
                wx.SWISS, wx.NORMAL, wx.NORMAL))
            panel_dc.DrawLabel(u"Fully open source and\nreleased under the "
                u"AGPL3 licence",
                wx.Rect(self.main_left, self.form_height-53, 100, 50))
            panel_dc.DrawBitmap(self.bmp_agpl3, self.main_left-115,
                self.form_height-58, True)
            # make default db if not already there
            def_db = os.path.join(mg.LOCAL_PATH, mg.INT_FOLDER, mg.SOFA_DB)
            con = sqlite.connect(def_db) #@UndefinedVariable
            con.close()
            panel_dc.DrawBitmap(self.blank_proj_strip, self.main_left, 218,
                False)
            panel_dc.SetTextForeground(wx.WHITE)
            panel_dc.SetFont(wx.Font(14 if mg.PLATFORM == mg.MAC else 11,
                wx.SWISS, wx.NORMAL, wx.NORMAL))
            active_projname = projects.filname2projname(self.active_proj)
            panel_dc.DrawLabel(_(u"Currently using \"%s\" project settings") %
                active_projname, wx.Rect(self.main_left, 247, 400, 30))
            event.Skip()
        except Exception, e:
            event.Skip()
            self.panel.Unbind(wx.EVT_PAINT)
            wx.CallAfter(self.on_paint_err_msg, e)
            self.Destroy()

    def draw_blank_wallpaper(self, panel_dc):
        panel_dc.DrawBitmap(self.blank_wallpaper, self.main_left,
            self.help_text_top, False)

    def set_proj_lbl(self, proj_text=""):
        if proj_text.endswith(mg.PROJ_EXT):
            raise Exception(u"proj_text must NOT have %s on the end" %
                mg.PROJ_EXT)
        debug = False
        self.active_proj = u"%s%s" % (proj_text, mg.PROJ_EXT)
        self.Refresh()
        if debug: print(u"Setting proj_text to %s" % proj_text)

    def on_get_started_click(self, event):
        import webbrowser
        url = (u"http://www.sofastatistics.com/wiki/doku.php"
            u"?id=help:getting_started")
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
        txt_get_started = _(u"Step-by-step examples with screen-shots to get "
            u"you started.")
        text2draw = t2d(txt_get_started, self.max_help_text_width)
        myrect = wx.Rect(self.main_left, self.help_text_top,
            self.help_text_width, 260)
        panel_dc.DrawLabel(text2draw, myrect)
        event.Skip()

    def on_data_click(self, event):
        from sofastats import dataselect  #@UnresolvedImport
        proj_name = self.active_proj
        dlgData = dataselect.DlgDataSelect(self, proj_name)
        dlgData.ShowModal()
        event.Skip()

    def on_data_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_data,
            self.help_img_left+self.data_img_offset, self.help_img_top-25, True)
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
            t2d(txt1, self.max_help_text_width) + u"\n\n" +
            t2d(txt2, self.max_help_text_width) + u"\n " +
            t2d(txt3, self.max_help_text_width) + u"\n " +
            t2d(txt4, self.max_help_text_width) + u"\n " +
            t2d(txt5, self.max_help_text_width) + u"\n " +
            t2d(txt6, self.max_help_text_width) + u"\n    " +
            t2d(txt7, self.max_help_text_width)
        )
        panel_dc.DrawLabel(text2draw, wx.Rect(self.main_left,
            self.help_text_top, self.help_text_width, 260))
        event.Skip()

    def on_import_click(self, event):
        from sofastats import importer_gui  #@UnresolvedImport
        dlg = importer_gui.DlgImportFileSelect(self)
        dlg.ShowModal()
        event.Skip()

    def on_import_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_import,
            self.help_img_left+self.import_img_offset, self.help_img_top-20,
            True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt_entry = (_(u"Import data e.g. a csv file, or a spreadsheet (Excel, "
            u"Open Document, or Google Docs). To connect to databases, click on"
            u" %s and configure connection settings instead.") %
            self.sel_proj_lbl)
        panel_dc.DrawLabel(t2d(txt_entry, self.max_help_text_width),
            wx.Rect(self.main_left, self.help_text_top,
                self.help_text_width-10, 260))
        event.Skip()

    def on_tables_click(self, event):
        "Open make table gui with settings as per active_proj"
        wx.BeginBusyCursor()
        from sofastats import report_table  #@UnresolvedImport
        try:
            dlg = report_table.DlgMakeTable()
            lib.GuiLib.safe_end_cursor()
            dlg.ShowModal()
        except Exception, e:
            msg = _("Unable to open report table dialog."
                "\nCaused by error: %s") % b.ue(e)
            print(traceback.format_exc())
            wx.MessageBox(msg)
        finally:
            lib.GuiLib.safe_end_cursor()
            event.Skip()

    def on_tables_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_tabs,
            self.help_img_left+self.report_img_offset, self.help_img_top-10,
            True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt1 = _(u"Make report tables e.g. Age vs Gender")
        txt2 = _(u"Can make simple Frequency Tables, Crosstabs, Row Stats "
            u"Tables (mean, median, standard deviation etc), and simple lists "
            u"of data.")
        txt2draw = (t2d(txt1, self.max_help_text_width) + u"\n\n"
            + t2d(txt2, self.max_help_text_width))
        panel_dc.DrawLabel(txt2draw, wx.Rect(self.main_left, self.help_text_top,
            self.help_text_width, 260))
        event.Skip()

    def get_script(self, cont, script):
        cont.append(mg.JS_WRAPPER_L)
        cont.append(script)
        cont.append(mg.JS_WRAPPER_R)

    def on_charts_click(self, event):
        from sofastats import charting_dlg  #@UnresolvedImport
        wx.BeginBusyCursor()
        try:
            dlg = charting_dlg.DlgCharting(_("Make Chart"))
            lib.GuiLib.safe_end_cursor()
            dlg.ShowModal()
        except Exception, e:
            msg = _(u"Unable to connect to data as defined in project %s.  "
                u"Please check your settings") % self.active_proj
            wx.MessageBox(msg)
            raise Exception(u"%s.\nCaused by errors:\n\n%s" %
                (msg, traceback.format_exc()))
        finally:
            lib.GuiLib.safe_end_cursor()
            event.Skip()

    def on_charts_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_chart,
            self.help_img_left+self.chart_img_offset, self.help_img_top-20,
            True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt_charts = _("Make attractive charts with dynamic visual effects "
            "e.g. a bar chart of sales")
        panel_dc.DrawLabel(t2d(txt_charts, self.max_help_text_width),
            wx.Rect(self.main_left, self.help_text_top, self.help_text_width,
                260))
        event.Skip()

    def on_stats_click(self, event):
        # open statistics selection dialog
        wx.BeginBusyCursor()
        from sofastats import stats_select  #@UnresolvedImport
        try:
            dlg = stats_select.DlgStatsSelect(self.active_proj)
            lib.GuiLib.safe_end_cursor()
            dlg.ShowModal()
        except Exception, e:
            msg = _("Unable to connect to data as defined in project %s.  "
                "Please check your settings.") % self.active_proj
            wx.MessageBox(msg)
            raise Exception(u"%s.\nCaused by error: %s" % (msg,
                traceback.format_exc()))
        finally:
            lib.GuiLib.safe_end_cursor()
            event.Skip()

    def on_stats_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_stats,
            self.help_img_left+self.stats_img_offset, self.help_img_top-25,
            True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt1 = _(u"Run statistical tests on your data - e.g. a Chi Square to "
            u"see if there is a relationship between age group and gender.")
        txt2 = _(u"SOFA focuses on the statistical tests most users need most "
            u"of the time.")
        txt3 = u"QUOTE: %s (%s)" % quotes.get_quote()
        txt2draw = (
            t2d(txt1, self.max_help_text_width) +
            u"\n\n" +
            t2d(txt2, self.max_help_text_width) +
            u"\n\n" +
            t2d(txt3, self.max_help_text_width)
            )
        panel_dc.DrawLabel(txt2draw, wx.Rect(self.main_left, self.help_text_top,
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
            self.help_img_left+self.help_img_offset, self.help_img_top-25, True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt_help = _(u"Get help on-line, including screen shots and "
            u"step-by-step instructions. Connect to the community. Get direct "
            u"help from the developer.")
        panel_dc.DrawLabel(t2d(txt_help, self.max_help_text_width),
            wx.Rect(self.main_left, self.help_text_top, self.help_text_width,
                260))
        event.Skip()

    def on_proj_click(self, event):
        proj_fils = projects.get_projs() # should always be the default present
        # open proj selection form
        dlgProj = projselect.DlgProjSelect(self, proj_fils, self.active_proj)
        dlgProj.ShowModal()
        if not projects.valid_proj(mg.PROJS_FOLDER, self.active_proj):
            wx.MessageBox(u"Unable to use '%s' project. Using default instead."
                % projects.filname2projname(self.active_proj))
            self.set_proj_lbl(projects.filname2projname(mg.DEFAULT_PROJ))
        event.Skip()

    def on_proj_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_proj,
            self.help_img_left+self.proj_img_offset, self.help_img_top-20, True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt_projs = _("Projects let SOFA know how to connect to your data, "
            "what labels to use, your favourite styles etc. The default "
            "project is OK to get you started.")
        panel_dc.DrawLabel(t2d(txt_projs, self.max_help_text_width),
            wx.Rect(self.main_left, self.help_text_top, self.help_text_width,
                260))
        event.Skip()

    def on_prefs_click(self, event):
        from sofastats import prefs  #@UnresolvedImport
        debug = False
        try:
            prefs_dic = config_globals.get_settings_dic(
                subfolder=mg.INT_FOLDER, fil_name=mg.INT_PREFS_FILE)
        except Exception:
            prefs_dic = {}
        if debug: print(prefs_dic)
        dlg = prefs.DlgPrefs(parent=self, prefs_dic_in=prefs_dic)
        dlg.ShowModal()
        event.Skip()

    def on_prefs_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_prefs,
            self.help_img_left+self.prefs_img_offset, self.help_img_top-10,
            True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt_pref = _("Set preferences")
        panel_dc.DrawLabel(t2d(txt_pref, self.max_help_text_width),
            wx.Rect(self.main_left, self.help_text_top, self.help_text_width,
                260))
        event.Skip()

    def on_backup_click(self, event):
        wx.BeginBusyCursor()
        try:
            msg = backup_sofa.run_backup()
        except Exception, e:
            msg = u"Unable to make backup.\n\nOrig error: %s" % e
        lib.GuiLib.safe_end_cursor()
        wx.MessageBox(msg)
        event.Skip()

    def on_backup_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_backup,
            self.help_img_left+self.backup_img_offset, self.help_img_top-10,
            True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt_backup = _(u"Backup your data, reports, and variable and project "
            u"details")
        panel_dc.DrawLabel(t2d(txt_backup, self.max_help_text_width),
            wx.Rect(self.main_left, self.help_text_top, self.help_text_width,
                260))
        event.Skip()

    def on_exit_click(self, event):
        debug = False
        wx.BeginBusyCursor()
        # wipe any internal images
        int_img_pattern = os.path.join(mg.INT_IMG_PATH, u"*.png")
        if debug: print(int_img_pattern)
        for delme in glob.glob(int_img_pattern):
            if debug: print(delme)
            os.remove(delme)
        lib.GuiLib.safe_end_cursor()
        self.Destroy()

    def on_exit_enter(self, event):
        panel_dc = wx.ClientDC(self.panel)
        self.draw_blank_wallpaper(panel_dc)
        panel_dc.DrawBitmap(self.bmp_exit, self.help_img_left,
            self.help_img_top-12, True)
        panel_dc.SetTextForeground(self.text_brown)
        panel_dc.SetFont(self.help_font)
        txt_exit = _("Exit SOFA Statistics")
        panel_dc.DrawLabel(t2d(txt_exit, self.max_help_text_width),
            wx.Rect(self.main_left, self.help_text_top, self.help_text_width,
                260))
        event.Skip()
