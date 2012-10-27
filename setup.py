"""
Makes sure all modules are OK.
Shows any initial errors even if no GUI to display them.
Creates any user folders and files needed and carries out any initial 
    configuration inside files e.g. paths.
"""

# 1) importing, and anything required to enable importing e.g. sys.path changes

from __future__ import absolute_import

# show_early_steps is about revealing any errors before the GUI even starts.
show_early_steps = True
force_error = False
debug = False

INIT_DEBUG_MSG = u"Please note the messages above (e.g. with a screen-shot)" + \
                 u" and press any key to close"
import warnings
if show_early_steps: print(u"Just imported warnings")
warnings.simplefilter('ignore', DeprecationWarning)
warnings.simplefilter('ignore', UserWarning)
import codecs
if show_early_steps: print(u"Just imported codecs")
import datetime
if show_early_steps: print(u"Just imported datetime")
import gettext
if show_early_steps: print(u"Just imported gettext")
import glob
if show_early_steps: print(u"Just imported glob")
import os
if show_early_steps: print(u"Just imported os")
import platform
if show_early_steps: print(u"Just imported platform")
import shutil
if show_early_steps: print(u"Just imported shutil")
import sqlite3 as sqlite
if show_early_steps: print(u"Just imported sqlite3")
import sys
if show_early_steps: print(u"Just imported sys")
import traceback
if show_early_steps: print(u"Just imported traceback")
# yes - an action in a module - but only called once and really about letting 
# other modules even be found and called
if not(hasattr(sys, 'frozen') and sys.frozen):
    try:
        import wxversion
        wxversion.select("2.8")
    except wxversion.AlreadyImportedError, e:
        pass
    except Exception, e:
        msg = u"There seems to be a problem with wxversion. %s" % \
            traceback.format_exc()
        if show_early_steps: 
            print(msg)
            raw_input(INIT_DEBUG_MSG)
        raise Exception(msg)
    if show_early_steps: print(u"Just ran wxversion")
import wx
if show_early_steps: print(u"Just imported wx")
# All i18n except for wx-based (which MUST happen after wx.App init)
# http://wiki.wxpython.org/RecipesI18n
# Install gettext.  Now all strings enclosed in "_()" will automatically be
# translated.
localedir = u"./locale" # fall back
try:
    localedir = os.path.join(os.path.dirname(__file__), u"locale")
    if debug: print(__file__)
except NameError, e:
    for path in sys.path:
        if u"sofastats" in path.lower(): # if user hasn't used sofastats, 
            # use default
            localedir = os.path.join(path, u"locale")
            break
if show_early_steps: 
    print(u"Just identified locale folder")
gettext.install(domain='sofastats', localedir=localedir, unicode=True)
if show_early_steps: print(u"Just installed gettext")
try:
    import my_globals as mg # has translated text
except Exception, e:
    msg = u"Problem with importing my_globals. %s" % \
                traceback.format_exc()
    if show_early_steps: 
        print(msg)
        raw_input(INIT_DEBUG_MSG)
    raise Exception(msg)
try:
    import lib
    import config_globals
    import my_exceptions
except Exception, e:
    msg = u"Problem with first round of local importing. %s" % \
                traceback.format_exc()
    if show_early_steps: 
        print(msg)
        raw_input(INIT_DEBUG_MSG) # not holding up any other way of getting msg 
            # to user.  Unlike when a GUI msg possible later on. In those cases
            # just let that step happen.
    raise Exception(msg)


# Give the user something if the program fails at an early stage before anything
# appears on the screen. Can only guarantee this from here onwards because I 
# need lib etc.
class ErrMsgFrame(wx.Frame):
    def __init__(self, e, raw_error_msg):
        """
        raw_error_msg -- boolean. If not to be used as is (raw), wrap in Oops! 
            etc, version number etc.
        """
        wx.Frame.__init__(self, None, title=_("SOFA Error"))
        error_msg = lib.ue(e)
        mybreak = u"\n" + u"*"*30 + u"\n"
        err_msg_fname = u"sofastats_error_details.txt"
        if not raw_error_msg:
            error_msg = (u"Oops! Something went wrong running SOFA Statistics "
                u"version %(version)s.\n\nHelp is available at "
                u"http://www.sofastatistics.com/userguide.php under "
                u"\"SOFA won't start - solutions\". You can also email "
                u"lead developer %(contact)s for help (usually "
                u"reasonably prompt).\n\nSOFA is about to make an error file "
                u"on your desktop. Please include that file "
                u"(\"%(err_msg_fname)s\") in your email."
                u"\n%(mybreak)s\nCaused by error: %(error_msg)s""" % 
                {"version": mg.VERSION, "err_msg_fname": err_msg_fname, 
                 "error_msg": error_msg, "mybreak": mybreak, 
                 u"contact": mg.CONTACT})
        wx.MessageBox(error_msg)
        f = codecs.open(os.path.join(mg.USER_PATH, u"Desktop", err_msg_fname), 
                        "w", "utf-8")
        f.write(error_msg)
        f.write(mybreak)
        f.write(traceback.format_exc())
        f.close()
        self.Destroy()
        import sys
        sys.exit()
        

class ErrMsgApp(wx.App):

    def __init__(self, e, raw_error_msg=False):
        self.e = e
        self.raw_error_msg = raw_error_msg
        wx.App.__init__(self, redirect=False, filename=None)

    def OnInit(self):
        msgframe = ErrMsgFrame(self.e, self.raw_error_msg)
        msgframe.Show()
        self.SetTopWindow(msgframe)
        return True


class MsgFrame(wx.Frame):
    def __init__(self, msg):
        wx.Frame.__init__(self, None, title=_("SOFA Message"))
        wx.MessageBox(msg)
        self.Destroy()
        

class MsgApp(wx.App):

    def __init__(self, msg):
        self.msg = msg
        wx.App.__init__(self, redirect=False, filename=None)

    def OnInit(self):
        msgframe = MsgFrame(self.msg)
        msgframe.Show()
        self.SetTopWindow(msgframe)
        return True
    

def check_python_version():
    debug = False
    pyversion = sys.version[:3]
    if debug: pyversion = None
    # Linux installer doesn't have hard-wired site-packages so 2.6 or 2.7 should 
    # work. Other installers have site-packages baked into the exe for their python version
    if (mg.PLATFORM == mg.LINUX and pyversion not in(u"2.6", u"2.7")):
        fixit_file = os.path.join(mg.USER_PATH, u"Desktop", 
                                  u"how to get SOFA working.txt")
        f = codecs.open(fixit_file, "w", "utf-8")
        div = u"*"*80
        os_msg = u"""
If you have multiple versions of Python available you will need to ensure that
SOFA Statistics is launched with version 2.6 or 2.7 explicitly defined.
E.g. /usr/bin/python2.6 instead of python.
        """
        msg_dic = {u"div": div, u"os_msg": os_msg, u"contact": mg.CONTACT}
        msg = (u"""
%(div)s
HOW TO GET SOFA STATISTICS WORKING AGAIN 
%(div)s

It looks like an incorrect version of Python is being used to run SOFA Statistics.
%(os_msg)s
For help, please contact %(contact)s""") % msg_dic
        f.write(msg)
        f.close()    
        msgapp = ErrMsgApp(msg + u"\n\n" + div + u"\n\nThis message has been "
                u"saved to a file on your Desktop for future reference", True)
        msgapp.MainLoop()
        del msgapp

# yes - once again an action in a module - but only called once and about the
# prerequisites for even running the program at all. 
check_python_version() # do as early as possible.  Game over if Python faulty.
if show_early_steps: print(u"Just checked python version")

def init_com_types(parent, panel):
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
        h = full_html.FullHTML(panel, parent, size=(10,10))
        try:
            h.pizza_magic() # must happen after Show
        except Exception:
            pass
        h.show_html(u"")
        h = None
        # leave tag saying it is done
        f = codecs.open(comtypes_tag, "w", "utf-8")
        f.write(u"Comtypes handled successfully :-)")
        f.close()

def get_installed_version_local_path():
    return get_installed_version(local_path=mg.LOCAL_PATH)

def get_installed_version(local_path):
    """
    Useful for working out if current version newer than installed version. Or
        if installed version is too old to work with this (latest) version.
        Perhaps we can migrate the old proj file if we know its version.
    """
    version_path = os.path.join(local_path, mg.VERSION_FILE)
    if os.path.exists(version_path):
        f = codecs.open(version_path, "r", "utf-8")
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
        if show_early_steps: print(u"Made local folder successfully.")
    except Exception, e:
        raise Exception(u"Unable to make local SOFA path \"%s\"." % local_path +
                        u"\nCaused by error: %s" % lib.ue(e))
    for local_subfolder in local_subfolders: # create required subfolders
        try:
            os.mkdir(os.path.join(local_path, local_subfolder))
            if show_early_steps: print(u"Added %s successfully." % 
                                       local_subfolder)
        except Exception, e:
            raise Exception(u"Unable to make local subfolder \"%s\"." % 
                            local_subfolder +
                            u"\nCaused by error: %s" % lib.ue(e))
    print(u"Made local subfolders under \"%s\"" % local_path)

def run_test_code(script):
    """
    Look for file called TEST_SCRIPT_EARLIEST or TEST_SCRIPT_POST_CONFIG in 
        internal folder.  If there, run it.
    """
    test_path = os.path.join(mg.INT_PATH, script)
    if not os.path.exists(test_path):
        return
    f = codecs.open(test_path, "r", "utf-8")
    test_code = lib.get_exec_ready_text(text=f.read())
    f.close()
    test_code = lib.clean_boms(test_code)
    test_dic = {}
    try:
        # http://docs.python.org/reference/simple_stmts.html
        exec test_code in test_dic
    except SyntaxError, e:
        raise Exception(_(u"Syntax error in test script \"%(test_path)s\"."
                          u"\nCaused by error: %(err)s") % 
                          {u"test_path": test_path, u"err": lib.ue(e)})
    except Exception, e:
        raise Exception(_(u"Error running test script \"%(test_path)s\"."
                          u"\nCaused by errors:\n\n%(err)s") %
                          {u"test_path": test_path, 
                           u"err": traceback.format_exc()})
    print(u"Ran test code %s" % script)

def populate_css_path(prog_path, local_path):
    """
    If something is wrong identifying script path, here is where it will fail 
        first.
    """
    styles = [mg.DEFAULT_STYLE, u"grey spirals.css", u"lucid spirals.css", 
              u"pebbles.css"]
    for style in styles:
        try:
            shutil.copy(os.path.join(prog_path, mg.CSS_FOLDER, style), 
                        os.path.join(local_path, mg.CSS_FOLDER, style))
            if show_early_steps: print(u"Just copied %s" % style)
        except Exception, e: # more diagnostic info to explain why it failed
            raise Exception(u"Problem populating css path."
                            u"\nCaused by error: %s" % lib.ue(e) +
                            u"\nprog_path: %s" % prog_path +
                            u"\nlocal_path: %s" % local_path +
                            u"\nFile location details: %s" % sys.path)
    print(u"Populated css paths under %s" % local_path)

def populate_extras_path(prog_path, local_path):
    extras = [u"arc.xd.js", u"blank.gif", u"blank.htm", u"dojo.xd.js", 
              u"gradient.xd.js", u"grey_spirals.gif", u"lucid_spirals.gif", 
              u"pebbles.gif", u"popupMenuBg.gif", u"sofastats_charts.js", 
              u"sofastatsdojo_minified.js", 
              u"tooltipConnectorDown-defbrown.gif",
              u"tooltipConnectorDown-defbrown.png",
              u"tooltipConnectorDown.gif",
              u"tooltipConnectorDown-greypurp.gif",
              u"tooltipConnectorDown-greypurp.png",
              u"tooltipConnectorDown-paleblue.gif",
              u"tooltipConnectorDown-paleblue.png",
              u"tooltipConnectorDown-paleorange.gif",
              u"tooltipConnectorDown-paleorange.png",
              u"tooltipConnectorDown.png",
              u"tooltipConnectorLeft-defbrown.gif",
              u"tooltipConnectorLeft-defbrown.png",
              u"tooltipConnectorLeft.gif",
              u"tooltipConnectorLeft-greypurp.gif",
              u"tooltipConnectorLeft-greypurp.png",
              u"tooltipConnectorLeft-paleblue.gif",
              u"tooltipConnectorLeft-paleblue.png",
              u"tooltipConnectorLeft-paleorange.gif",
              u"tooltipConnectorLeft-paleorange.png",
              u"tooltipConnectorLeft.png",
              u"tooltipConnectorRight-defbrown.gif",
              u"tooltipConnectorRight-defbrown.png",
              u"tooltipConnectorRight.gif",
              u"tooltipConnectorRight-greypurp.gif",
              u"tooltipConnectorRight-greypurp.png",
              u"tooltipConnectorRight-paleblue.gif",
              u"tooltipConnectorRight-paleblue.png",
              u"tooltipConnectorRight-paleorange.gif",
              u"tooltipConnectorRight-paleorange.png",
              u"tooltipConnectorRight.png",
              u"tooltipConnectorUp-defbrown.gif",
              u"tooltipConnectorUp-defbrown.png",
              u"tooltipConnectorUp.gif",
              u"tooltipConnectorUp-greypurp.gif",
              u"tooltipConnectorUp-greypurp.png",
              u"tooltipConnectorUp-paleblue.gif",
              u"tooltipConnectorUp-paleblue.png",
              u"tooltipConnectorUp-paleorange.gif",
              u"tooltipConnectorUp-paleorange.png",
              u"tooltipConnectorUp.png",
              u"tundra.css", u"vml.xd.js"]
    for extra in extras:
        try:
            shutil.copy(os.path.join(prog_path, mg.REPORTS_FOLDER, 
                                     mg.REPORT_EXTRAS_FOLDER, extra), 
                        os.path.join(local_path, mg.REPORTS_FOLDER, 
                                     mg.REPORT_EXTRAS_FOLDER, extra))
            if show_early_steps: print(u"Just copied %s" % extra)
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
    if show_early_steps: print(u"Just copied %s" % mg.SOFA_DB)
    shutil.copy(os.path.join(prog_path, mg.PROJS_FOLDER, mg.DEFAULT_PROJ), 
                default_proj)
    if show_early_steps: print(u"Just copied %s" % default_proj)
    shutil.copy(os.path.join(prog_path, mg.VDTS_FOLDER, mg.DEFAULT_VDTS), 
                os.path.join(local_path, mg.VDTS_FOLDER, mg.DEFAULT_VDTS))
    if show_early_steps: print(u"Just copied %s" % mg.DEFAULT_VDTS)
    populate_extras_path(prog_path, local_path)
    print(u"Populated local paths under %s" % local_path)

def config_local_proj(local_path, default_proj, settings_subfolders):
    """
    Modify default project settings to point to local (user) SOFA directory.
    NB user paths can have any characters in them e.g. an apostrophe in Tim's, 
        so escaping is essential if the outer quotes are needed internally. 
        Assume stored in double quotes.
    """
    # change home username
    try:
        f = codecs.open(default_proj, "r", "utf-8")
        proj_str = f.read() # provided by me - no BOM or non-ascii 
        f.close()
        if show_early_steps: print(u"Just read default project")
        for path in settings_subfolders:
            new_path = lib.escape_pre_write(os.path.join(mg.LOCAL_PATH, 
                                                         path, u""))
            new_path = new_path.replace('"', '""')
            proj_str = proj_str.replace(u"/home/g/Documents/sofastats/%s/" % 
                                        path, new_path)
            if show_early_steps: print(u"Just modified %s" % path)
        # add MS Access and SQL Server into mix if Windows
        if mg.PLATFORM == mg.WINDOWS:
            proj_str = proj_str.replace(u"default_dbs = {",
                            u"default_dbs = {'%s': None, " % mg.DBE_MS_ACCESS)
            proj_str = proj_str.replace(u"default_tbls = {",
                            u"default_tbls = {'%s': None, " % mg.DBE_MS_ACCESS)
            if show_early_steps: print(u"Just updated %s" % mg.DBE_MS_ACCESS)
            proj_str = proj_str.replace(u"default_dbs = {",
                            u"default_dbs = {'%s': None, " % mg.DBE_MS_SQL)
            proj_str = proj_str.replace(u"default_tbls = {",
                            u"default_tbls = {'%s': None, " % mg.DBE_MS_SQL)
            if show_early_steps: print(u"Just updated %s" % mg.DBE_MS_SQL)
        f = codecs.open(default_proj, "w", "utf-8")
        f.write(proj_str)
        f.close()
        if show_early_steps: print(u"Just wrote to default project %s" % 
                                   default_proj)
        # create file as tag we have done the changes to the proj file
        f = codecs.open(os.path.join(local_path, mg.PROJ_CUSTOMISED_FILE), "w", 
                        "utf-8")
        f.write(u"Local project file customised successfully :-)")
        f.close()
        print(u"Configured default project file for user")
    except Exception, e:
        raise Exception(u"Problem configuring default project settings. "
                        u"It may be best to delete your local sofastats folder "
                        u"e.g. C:\\Users\\username\\sofastats or C:\\Documents "
                        u"and Settings\\username\\sofastats"
                        u"\nCaused by error: %s" % lib.ue(e))

def store_version(local_path):
    f = codecs.open(os.path.join(local_path, mg.VERSION_FILE), "w", "utf-8")
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

def archive_older_default_report():
    def_rpt_pth = os.path.join(mg.REPORTS_PATH, mg.DEFAULT_REPORT)
    if os.path.exists(def_rpt_pth):
        try:
            new_filename = u"default_report_pre_%s.htm" % mg.VERSION
            new_version = os.path.join(mg.REPORTS_PATH, new_filename)
            os.rename(def_rpt_pth, new_version)
            if show_early_steps: print(u"Just renamed %s to new version" % 
                                       def_rpt_pth)
            mg.DEFERRED_WARNING_MSGS.append("EXISTING REPORT SAFEGUARDED:"
                "\n\nAs part of the upgrade to version %s, "
                "SOFA has renamed \"%s\" to \"%s\" "
                "\nto ensure all new content added to the default report "
                "works with the latest chart display code." % 
                (mg.VERSION, mg.DEFAULT_REPORT, new_filename))
        except OSError, e:
            raise Exception("Unable to archive older default report.")
                    
def freshen_recovery(prog_path, local_subfolders, subfolders_in_proj):
    """
    Need a good upgrade process which leaves existing configuration intact if 
        possible but creates recovery folder which is guaranteed to work with 
        the version just installed.
    Always have two local folders - the main sofastats folder and a 
        sofastats_recovery folder.
    If the version of SOFA running is newer than the version in __version__.txt, 
        wipe the sofastats_recovery folder, and make it afresh.  The home folder 
        should always contain a sofa-type folder which would allow the latest 
        installed version of SOFA to run.  If the ordinary sofastats folder is 
        faulty in some way, can always wipe it and rename sofastats_recovery to 
        sofastats and open up successfully.
    The "sofastats_recovery" folder should have a default project file which 
        points to the ordinary home "sofastats" folder.  This will only work, of 
        course, if the folder is made operational by renaming it to "sofastats".
    """
    if force_error:
        raise Exception("Error added to make error message appear :-)")
    (installer_recovery_is_newer, 
     installer_recovery_newer_status_known) = \
                                  get_installer_version_status(mg.RECOVERY_PATH)
    if show_early_steps: print(u"Just identified installer recovery status")
    if (installer_recovery_is_newer or not installer_recovery_newer_status_known
            or not os.path.exists(mg.RECOVERY_PATH)):
        # make fresh recovery folder (over top of previous if necessary)
        try:
            shutil.rmtree(mg.RECOVERY_PATH)
            if show_early_steps: print(u"Just deleted %s" % mg.RECOVERY_PATH)
        except OSError:
            pass # OK to fail removing recovery path if not there.
        make_local_subfolders(mg.RECOVERY_PATH, local_subfolders)
        default_proj = os.path.join(mg.RECOVERY_PATH, mg.PROJS_FOLDER, 
                                    mg.DEFAULT_PROJ)
        populate_local_paths(prog_path, mg.RECOVERY_PATH, default_proj)
        config_local_proj(mg.RECOVERY_PATH, default_proj, subfolders_in_proj)
        store_version(mg.RECOVERY_PATH)
        print(u"Freshened recovery")

def setup_folders():
    """
    Create folders as required and set them up including changes to file e.g. 
        paths contained in them.
    """
    subfolders_in_proj = [mg.CSS_FOLDER, mg.INT_FOLDER, mg.PROJS_FOLDER, 
                          mg.REPORTS_FOLDER, mg.SCRIPTS_FOLDER, mg.VDTS_FOLDER]
    oth_subfolders = [os.path.join(mg.REPORTS_FOLDER, mg.REPORT_EXTRAS_FOLDER)]
    local_subfolders = subfolders_in_proj + oth_subfolders
    prog_path = mg.SCRIPT_PATH
    if show_early_steps: print(u"Just set prog_path")
    try:
        # 1) make local SOFA folder if missing. Otherwise, leave intact for now
        try:
            local_path_setup_needed = not os.path.exists(mg.LOCAL_PATH)
            if local_path_setup_needed:
                make_local_subfolders(mg.LOCAL_PATH, local_subfolders)
            run_test_code(mg.TEST_SCRIPT_EARLIEST)
            if local_path_setup_needed:
                # need mg but must run pre code calling dd
                default_proj = os.path.join(mg.LOCAL_PATH, mg.PROJS_FOLDER, 
                                            mg.DEFAULT_PROJ)
                populate_local_paths(prog_path, mg.LOCAL_PATH, default_proj)
                config_local_proj(mg.LOCAL_PATH, default_proj, 
                                  subfolders_in_proj)
                store_version(mg.LOCAL_PATH)
        except Exception, e:
            raise Exception(u"Unable to make local sofa folders in \"%s.\""
                            % mg.LOCAL_PATH +
                            u"\nCaused by error: %s" % lib.ue(e))
        run_test_code(mg.TEST_SCRIPT_POST_CONFIG) # can now use dd and proj config
        # 2) Modify existing local SOFA folder if version change require it
        existing_local = not local_path_setup_needed
        if existing_local:
            try: # e.g. if already installed version is older than 1.1.16 ...
                installed_version = get_installed_version(mg.LOCAL_PATH)
                if show_early_steps: print(u"Just got installed version")
                new_version = (installed_version is None 
                               or lib.version_a_is_newer(version_a=mg.VERSION,
                                                  version_b=installed_version))
                if new_version:
                    # update css files - url(images...) -> url("images...")
                    populate_css_path(prog_path, mg.LOCAL_PATH)
                    # ensure sofastats_report_extras folder and freshly populate it
                    REPORT_EXTRAS_PATH = os.path.join(mg.LOCAL_PATH, 
                                                      mg.REPORTS_FOLDER, 
                                                      mg.REPORT_EXTRAS_FOLDER)
                    try:
                        os.mkdir(REPORT_EXTRAS_PATH) # under reports
                        if show_early_steps: 
                            print(u"Just made %s" % REPORT_EXTRAS_PATH)
                    except OSError, e:
                        pass # Already there.
                    except Exception, e:
                        raise Exception(u"Unable to make report extras "
                                        u"path \"%s\"." % REPORT_EXTRAS_PATH +
                                        u"\nCaused by error: %s" % lib.ue(e))
                    populate_extras_path(prog_path, mg.LOCAL_PATH)
                    archive_older_default_report()
                    store_version(mg.LOCAL_PATH) # update it so only done once
            except Exception, e:
                raise Exception(u"Problem modifying your local sofastats "
                        u"folder. One option is to delete the \"%s\" folder and"
                        u" let SOFA make a fresh one.\nCaused by error: %s" %
                        (mg.LOCAL_PATH, lib.ue(e)))
        # 3) Make a fresh recovery folder if needed
        try:
            freshen_recovery(prog_path, local_subfolders, subfolders_in_proj)
        except Exception, e:
            raise Exception(u"Problem freshening your recovery folder \"%s\"."
                    u"\nCaused by error: %s" % (prog_path, lib.ue(e)))
        # 4) ensure the internal copy images path exists
        try:
            os.mkdir(mg.INT_COPY_IMGS_PATH)
        except OSError:
            pass # already there
    except Exception, e:
        if show_early_steps: print(u"Problem running initial setup - about to "
                                   u"make msg.")
        msg = (u"Problem running initial setup.\nCaused by error: %s" % 
               lib.ue(e))
        if show_early_steps: 
            print(msg)
            print(traceback.format_exc())
        msgapp = ErrMsgApp(msg)
        msgapp.MainLoop()
        del msgapp
    return local_path_setup_needed

# local importing
try:
    about = u"config_output"
    import config_output # actually uses proj dict and connects to sofa_db. Thus
        # can't rely on wx.msgboxes etc because wx.App not up yet
    about = u"full_html"
    import full_html
    about = u"getdata"
    import getdata
    about = u"projects"
    import projects
    about = u"projselect"
    import projselect
    about = u"quotes"
    import quotes
except my_exceptions.ComtypesException, e:
    msgapp = ErrMsgApp(lib.ue(e))
except my_exceptions.InconsistentFileDate, e:
    msgapp = ErrMsgApp(lib.ue(e))
except Exception, e:
    msg = (u"Problem with second round of local importing while "
           u"importing %s." % about +
           u"\nCaused by error: %s" % lib.ue(e) +
           u"\n\nMore details that may help developer:\n%s" % 
           traceback.format_exc())
    msgapp = ErrMsgApp(msg)
    # msgapp.MainLoop() # already sys.exit()
    # del msgapp
