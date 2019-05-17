"""
Makes sure all modules are OK.

Shows any initial errors even if no GUI to display them.

Creates any user folders and files needed and carries out any initial 
configuration inside files e.g. paths.
"""
from pathlib import Path

## 1) importing, and anything required to enable importing e.g. sys.path changes

## show_early_steps is about revealing any errors before the GUI even starts.
show_early_steps = True
force_error = False
debug = False

INIT_DEBUG_MSG = ('Please note the messages above (e.g. with a screen-shot)'
    ' and press any key to close')
import warnings
if show_early_steps: print('Just imported warnings')
warnings.simplefilter('ignore', DeprecationWarning)
warnings.simplefilter('ignore', UserWarning)
import datetime #@UnusedImport
if show_early_steps: print('Just imported datetime')
import gettext
if show_early_steps: print('Just imported gettext')
import glob #@UnusedImport
if show_early_steps: print('Just imported glob')
import os
if show_early_steps: print('Just imported os')
import platform #@UnusedImport
if show_early_steps: print('Just imported platform')
import shutil
if show_early_steps: print('Just imported shutil')
import sqlite3 as sqlite #@UnusedImport
if show_early_steps: print('Just imported sqlite3')
import sys
if show_early_steps: print('Just imported sys')
import traceback
if show_early_steps: print('Just imported traceback')
import wx #@UnusedImport
if show_early_steps: print('Just imported wx')
import wx.html2
if show_early_steps: print('Just imported wx.html2')
## All i18n except for wx-based (which MUST happen after wx.App init)
## http://wiki.wxpython.org/RecipesI18n
## Install gettext.  Now all strings enclosed in '_()' will automatically be
## translated.
localedir = Path('./locale')  ## fall back
try:
    localedir = Path(os.path.join(os.path.dirname(__file__), 'locale'))
    if debug: print(__file__)
except NameError as e:
    for path in sys.path:
        if 'sofastats' in path.lower():  ## if user hasn't used sofastats, 
            ## use default
            localedir = Path(path) / 'locale'
            break
if show_early_steps:
    print('Just identified locale folder')
gettext.install(domain='sofastats', localedir=localedir)
if show_early_steps: print('Just installed gettext')
try:
    from . import basic_lib as b #@UnresolvedImport
except Exception as e:
    msg = (f'Problem importing basic_lib. {traceback.format_exc()}')
    if show_early_steps: 
        print(msg)
        input(INIT_DEBUG_MSG)  ## Not holding up any other way of getting msg
            ## to user. Unlike when a GUI msg possible later on. In those cases
            ## just let that step happen.
    raise Exception(msg)
try:
    from . import my_globals as mg  #@UnresolvedImport  ## has translated text
except Exception as e:
    msg = f'Problem with importing my_globals. {traceback.format_exc()}'
    if show_early_steps: 
        print(msg)
        input(INIT_DEBUG_MSG)
    raise Exception(msg)
mg.LOCALEDIR = localedir
try:
    from . import my_exceptions #@UnresolvedImport
    from . import config_globals  #@UnresolvedImport
    from . import lib #@UnresolvedImport
except Exception as e:
    msg = f'Problem with first round of local importing. {traceback.format_exc()}'
    if show_early_steps:
        print(msg)
        input(INIT_DEBUG_MSG)  ## not holding up any other way of getting msg
            ## to user. Unlike when a GUI msg possible later on. In those cases
            ## just let that step happen.
    raise Exception(msg)
try:
    config_globals.set_SCRIPT_PATH()
    config_globals.set_ok_date_formats()
    config_globals.set_DEFAULT_DETAILS()
    config_globals.import_dbe_plugins() ## as late as possible because uses
        ## local modules e.g. my_exceptions, lib
except Exception as e:
    msg = (f'Problem with configuring globals. {traceback.format_exc()}')
    if show_early_steps: 
        print(msg)
        input(INIT_DEBUG_MSG)
    raise Exception(msg)

## Give the user something if the program fails at an early stage before
## anything appears on the screen. Can only guarantee this from here onwards
## because I need lib etc.
class ErrMsgFrame(wx.Frame):
    def __init__(self, e, raw_error_msg):
        """
        :param bool raw_error_msg: if not to be used as is (raw), wrap in Oops!
        etc, version number etc.
        """
        wx.Frame.__init__(self, None, title=_('SOFA Error'))
        error_msg = b.ue(e)
        mybreak = '\n' + '*'*30 + '\n'
        err_msg_fname = 'sofastats_error_details.txt'
        if not raw_error_msg:
            error_msg = (
                'Oops! Something went wrong running SOFA Statistics version '
                f'{mg.VERSION}.'
                '\n\nHelp is available at '
                'http://www.sofastatistics.com/userguide.php under '
                '"SOFA won\'t start - solutions". You can also email '
                f'lead developer {mg.CONTACT} for help (usually '
                'reasonably prompt).\n\nSOFA is about to make an error file '
                'on your desktop. Please include that file '
                f'("{err_msg_fname}") in your email.'
                f'\n{mybreak}\nCaused by error: {error_msg}')
        wx.MessageBox(error_msg)
        fpath = mg.HOME_PATH / 'Desktop' / err_msg_fname
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(error_msg)
            f.write(mybreak)
            f.write(traceback.format_exc())
        self.Destroy()
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
        wx.Frame.__init__(self, None, title=_('SOFA Message'))
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
    if (mg.PLATFORM == mg.LINUX and pyversion < '3.6'):
        fixit_file = mg.HOME_PATH / 'Desktop' / 'how to get SOFA working.txt'
        with open(fixit_file, 'w', encoding='utf-8') as f:
            div = '*'*80
            os_msg = """
    If you have multiple versions of Python available you will need to ensure
    that SOFA Statistics is launched with version 3.6+ explicitly defined.
    E.g. /usr/bin/python3.6 instead of python.
            """
            msg = (f"""
    {div}
    HOW TO GET SOFA STATISTICS WORKING AGAIN
    {div}

    It looks like an incorrect version of Python is being used to run
    SOFA Statistics.
    {os_msg}
    For help, please contact {mg.CONTACT}""")
            f.write(msg)
        msgapp = ErrMsgApp(msg + '\n\n' + div + '\n\nThis message has been '
            'saved to a file on your Desktop for future reference', True)
        msgapp.MainLoop()
        del msgapp

## Yes - once again an action in a module - but only called once and about the
## prerequisites for even running the program at all.
check_python_version()  ## do as early as possible. Game over if Python faulty.
if show_early_steps: print("Just checked python version")

def init_com_types(parent, panel):
    """
    If first time opened, and in Windows, warn user about delay setting up
    (comtypes).
    """
    COMTYPES_HANDLED = 'comtypes_handled.txt'
    comtypes_tag = mg.LOCAL_PATH / COMTYPES_HANDLED
    if (mg.PLATFORM == mg.WINDOWS and not os.path.exists(comtypes_tag)):
        ## init com types
        wx.MessageBox(_('Click OK to prepare for first use of SOFA '
            'Statistics.\n\nPreparation may take a moment ...'))
        parent.html = wx.html2.WebView.New(panel, -1, size=wx.Size(10, 10))
        lib.OutputLib.update_html_ctrl(parent.html, '')
        parent.html = None
        ## leave tag saying it is done
        with open(comtypes_tag, 'w', encoding='utf-8') as f:
            f.write('Comtypes handled successfully :-)')

def get_installed_version(local_path):
    """
    Useful for working out if current version newer than installed version. Or
    if installed version is too old to work with this (latest) version. Perhaps
    we can migrate the old proj file if we know its version.
    """
    version_path = local_path / mg.VERSION_FILE
    if os.path.exists(version_path):
        with open(version_path, 'r', encoding='utf-8') as f:
            installed_version = f.read().strip()
    else:
        installed_version = None
    return installed_version

def make_local_subfolders(local_path, local_subfolders):
    """
    Create user home folder and required subfolders if not already done.
    """
    try:
        local_path.mkdir(exist_ok=True)
        if show_early_steps: print('Made local folder successfully.')
    except Exception as e:
        raise Exception(f'Unable to make local SOFA path "{local_path}".'
            + f'\nCaused by error: {b.ue(e)}')
    for local_subfolder in local_subfolders:  ## create required subfolders
        try:
            (local_path / local_subfolder).mkdir(exist_ok=True)
            if show_early_steps: 
                print(f'Added {local_subfolder} successfully.')
        except Exception as e:
            raise Exception(
                f'Unable to make local subfolder "{local_subfolder}".'
                + f'\nCaused by error: {b.ue(e)}')
    print(f'Made local subfolders under "{local_path}"')

def run_test_code(script):
    """
    Look for file called TEST_SCRIPT_EARLIEST or TEST_SCRIPT_POST_CONFIG in
    internal folder. If there, run it.
    """
    test_path = mg.INT_PATH / script
    if not os.path.exists(test_path):
        return
    test_code = b.get_bom_free_contents(fpath=test_path)
    test_code = b.get_exec_ready_text(text=test_code)
    test_dic = {}
    try:
        ## http://docs.python.org/reference/simple_stmts.html
        exec(test_code, test_dic)
    except SyntaxError as e:
        raise Exception(_("Syntax error in test script \"%(test_path)s\"."
            "\nCaused by error: %(err)s") % {'test_path': test_path,
            'err': b.ue(e)})
    except Exception as e:
        raise Exception(_("Error running test script \"%(test_path)s\"."
            "\nCaused by errors:\n\n%(err)s") % {'test_path': test_path,
            'err': traceback.format_exc()})
    print(f'Ran test code {script}')

def populate_css_path(prog_path, local_path):
    """
    If something is wrong identifying script path, here is where it will fail
    first.
    """
    styles = [mg.DEFAULT_STYLE, 'grey spirals.css', 'lucid spirals.css', 
        'monochrome.css', 'pebbles.css', 'prestige (print).css',
        'prestige (screen).css', 'sky.css', ]
    for style in styles:
        try:
            src_style = prog_path / mg.CSS_FOLDER / style
            dest_style = local_path / mg.CSS_FOLDER / style
            shutil.copy(src_style, dest_style)
            if show_early_steps: print(f'Just copied {style}')
        except Exception as e:  ## more diagnostic info to explain why it failed
            raise Exception('Problem populating css path using shutil.copy().'
                f'\nCaused by error: {b.ue(e)}'
                f'\nsrc_style: {src_style}'
                f'\ndest_style: {dest_style}'
                f'\nFile location details: {sys.path}')
    print(f'Populated css paths under {local_path}')

def populate_extras_path(prog_path, local_path):
    extras = ['arc.xd.js', 'blank.gif', 'blank.htm', 'dojo.xd.js',
        'gradient.xd.js', 'grey_spirals.gif', 'lucid_spirals.gif',
        'pebbles.gif', 'popupMenuBg.gif', 'prestige_spirals.gif',
        'sky.jpg', 'sofastats_charts.js', 'sofastatsdojo_minified.js',
        'tooltipConnectorDown-defbrown.gif',
        'tooltipConnectorDown-defbrown.png',
        'tooltipConnectorDown.gif',
        'tooltipConnectorDown-greypurp.gif',
        'tooltipConnectorDown-greypurp.png',
        'tooltipConnectorDown-paleblue.gif',
        'tooltipConnectorDown-paleblue.png',
        'tooltipConnectorDown-paleorange.gif',
        'tooltipConnectorDown-paleorange.png',
        'tooltipConnectorDown.png',
        'tooltipConnectorLeft-defbrown.gif',
        'tooltipConnectorLeft-defbrown.png',
        'tooltipConnectorLeft.gif',
        'tooltipConnectorLeft-greypurp.gif',
        'tooltipConnectorLeft-greypurp.png',
        'tooltipConnectorLeft-paleblue.gif',
        'tooltipConnectorLeft-paleblue.png',
        'tooltipConnectorLeft-paleorange.gif',
        'tooltipConnectorLeft-paleorange.png',
        'tooltipConnectorLeft.png',
        'tooltipConnectorRight-defbrown.gif',
        'tooltipConnectorRight-defbrown.png',
        'tooltipConnectorRight.gif',
        'tooltipConnectorRight-greypurp.gif',
        'tooltipConnectorRight-greypurp.png',
        'tooltipConnectorRight-paleblue.gif',
        'tooltipConnectorRight-paleblue.png',
        'tooltipConnectorRight-paleorange.gif',
        'tooltipConnectorRight-paleorange.png',
        'tooltipConnectorRight.png',
        'tooltipConnectorUp-defbrown.gif',
        'tooltipConnectorUp-defbrown.png',
        'tooltipConnectorUp.gif',
        'tooltipConnectorUp-greypurp.gif',
        'tooltipConnectorUp-greypurp.png',
        'tooltipConnectorUp-paleblue.gif',
        'tooltipConnectorUp-paleblue.png',
        'tooltipConnectorUp-paleorange.gif',
        'tooltipConnectorUp-paleorange.png',
        'tooltipConnectorUp.png',
        'tundra.css', 'vml.xd.js']
    for extra in extras:
        try:
            shutil.copy(
                prog_path / mg.REPORTS_FOLDER / mg.REPORT_EXTRAS_FOLDER / extra,
                local_path / mg.REPORTS_FOLDER / mg.REPORT_EXTRAS_FOLDER / extra
            )
            if show_early_steps: print(f'Just copied {extra}')
        except Exception as e:
            raise Exception('Problem populating report extras path.'
                f'\nCaused by error: {b.ue(e)}')
    print(f'Populated report extras path under {local_path}')

def populate_local_paths(prog_path, local_path, default_proj):
    """
    Install local set of files in user home dir if necessary.
    """
    ## copy across css, sofa_db, default proj, vdts, and report extras
    populate_css_path(prog_path, local_path)
    shutil.copy(
        prog_path / mg.INT_FOLDER / mg.SOFA_DB,
        local_path / mg.INT_FOLDER / mg.SOFA_DB)
    if show_early_steps: print(f'Just copied {mg.SOFA_DB}')
    shutil.copy(
        prog_path / mg.PROJS_FOLDER / mg.DEFAULT_PROJ,
        default_proj)
    if show_early_steps: print(f'Just copied {default_proj}')
    shutil.copy(
        prog_path / mg.VDTS_FOLDER / mg.DEFAULT_VDTS,
        local_path / mg.VDTS_FOLDER / mg.DEFAULT_VDTS)
    if show_early_steps: print(f'Just copied {mg.DEFAULT_VDTS}')
    populate_extras_path(prog_path, local_path)
    print(f'Populated local paths under {local_path}')

def config_local_proj(local_path, default_proj, settings_subfolders):
    """
    Modify default project settings to point to local (user) SOFA directory.

    NB user paths can have any characters in them e.g. an apostrophe in Tim's,
    so escaping is essential if the outer quotes are needed internally.

    Assume stored in double quotes.
    """
    ## change home username
    try:
        with open(default_proj, encoding='utf-8') as f:
            proj_str = f.read()  ## provided by me - no BOM or non-ascii
        if show_early_steps: print('Just read default project')
        for path in settings_subfolders:
            old_path = f'/home/g/Documents/sofastats/{path}/'
            new_path = lib.escape_pre_write(
                str(mg.LOCAL_PATH / f'{path}') + '/')  ## https://stackoverflow.com/questions/47572165/whats-the-best-way-to-add-a-trailing-slash-to-a-pathlib-directory
            proj_str = proj_str.replace(old_path, new_path)
            if show_early_steps:
                print(f"Just modified {old_path} to {new_path}")
        ## add MS Access and SQL Server into mix if Windows
        if mg.PLATFORM == mg.WINDOWS:
            proj_str = proj_str.replace("default_dbs = {",
                "default_dbs = {'%s': None, " % mg.DBE_MS_ACCESS)
            proj_str = proj_str.replace('default_tbls = {',
                "default_tbls = {'%s': None, " % mg.DBE_MS_ACCESS)
            if show_early_steps: print('Just updated %s' % mg.DBE_MS_ACCESS)
            proj_str = proj_str.replace('default_dbs = {',
                "default_dbs = {'%s': None, " % mg.DBE_MS_SQL)
            proj_str = proj_str.replace('default_tbls = {',
                "default_tbls = {'%s': None, " % mg.DBE_MS_SQL)
            if show_early_steps: print(f'Just updated {mg.DBE_MS_SQL}')
        with open(default_proj, 'w', encoding='utf-8') as f:
            f.write(proj_str)
        if show_early_steps: 
            print(f'Just wrote to default project {default_proj}')
        ## create file as tag we have done the changes to the proj file
        fpath = local_path / mg.PROJ_CUSTOMISED_FILE
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write('Local project file customised successfully :-)')
        print('Configured default project file for user')
    except Exception as e:
        raise Exception('Problem configuring default project settings. '
            'It may be best to delete your local sofastats folder '
            'e.g. C:\\Users\\username\\sofastats '
            'or C:\\Documents and Settings\\username\\sofastats'
            f'\nCaused by error: {b.ue(e)}')

def store_version(local_path):
    fpath = local_path / mg.VERSION_FILE
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(mg.VERSION)
    print(f'Stored version as {mg.VERSION}')

def get_installer_version_status(local_path):
    try:
        installer_is_newer = lib.version_a_is_newer(version_a=mg.VERSION,
            version_b=get_installed_version(local_path))
        installer_newer_status_known = True
    except Exception as e:
        installer_is_newer = None
        installer_newer_status_known = False
    return installer_is_newer, installer_newer_status_known

def archive_older_default_report():
    def_rpt_pth = mg.REPORTS_PATH / mg.DEFAULT_REPORT
    if os.path.exists(def_rpt_pth):
        try:
            new_filename = f'default_report_pre_{mg.VERSION}.htm'
            new_version = mg.REPORTS_PATH / new_filename
            os.rename(def_rpt_pth, new_version)
            if show_early_steps: 
                print(f'Just renamed {def_rpt_pth} to new version')
            mg.DEFERRED_WARNING_MSGS.append('EXISTING REPORT SAFEGUARDED:'
                f'\n\nAs part of the upgrade to version {mg.VERSION}, '
                f'SOFA has renamed "{mg.DEFAULT_REPORT}" to "{new_filename}" '
                '\nto ensure all new content added to the default report '
                'works with the latest chart display code.')
        except OSError as e:
            raise Exception('Unable to archive older default report.')

def freshen_recovery(prog_path, local_subfolders, subfolders_in_proj):
    """
    Need a good upgrade process which leaves existing configuration intact if
    possible but creates recovery folder which is guaranteed to work with the
    version just installed.

    Always have two local folders - the main sofastats folder and a
    sofastats_recovery folder.

    If the version of SOFA running is newer than the version in __version__.txt,
    wipe the sofastats_recovery folder, and make it afresh. The home folder
    should always contain a sofa-type folder which would allow the latest
    installed version of SOFA to run. If the ordinary sofastats folder is faulty
    in some way, can always wipe it and rename sofastats_recovery to sofastats
    and open up successfully.

    The "sofastats_recovery" folder should have a default project file which
    points to the ordinary home "sofastats" folder. This will only work, of
    course, if the folder is made operational by renaming it to "sofastats".
    """
    if force_error:
        raise Exception('Error added to make error message appear :-)')
    (installer_recovery_is_newer, 
     installer_recovery_newer_status_known) = \
        get_installer_version_status(mg.RECOVERY_PATH)
    if show_early_steps: print('Just identified installer recovery status')
    if (installer_recovery_is_newer or not installer_recovery_newer_status_known
            or not os.path.exists(mg.RECOVERY_PATH)):
        ## make fresh recovery folder (over top of previous if necessary)
        try:
            shutil.rmtree(mg.RECOVERY_PATH)
            if show_early_steps: print(f'Just deleted {mg.RECOVERY_PATH}')
        except OSError:
            pass  ## OK to fail removing recovery path if not there.
        make_local_subfolders(mg.RECOVERY_PATH, local_subfolders)
        default_proj = mg.RECOVERY_PATH / mg.PROJS_FOLDER / mg.DEFAULT_PROJ
        populate_local_paths(prog_path, mg.RECOVERY_PATH, default_proj)
        config_local_proj(mg.RECOVERY_PATH, default_proj, subfolders_in_proj)
        store_version(mg.RECOVERY_PATH)
        print('Freshened recovery')

def setup_folders():
    """
    Create folders as required and set them up including changes to file
    e.g. paths contained in them.
    """
    subfolders_in_proj = [mg.CSS_FOLDER, mg.INT_FOLDER, mg.PROJS_FOLDER,
        mg.REPORTS_FOLDER, mg.SCRIPTS_FOLDER, mg.VDTS_FOLDER]
    oth_subfolders = [mg.REPORTS_FOLDER / mg.REPORT_EXTRAS_FOLDER, ]
    local_subfolders = subfolders_in_proj + oth_subfolders
    prog_path = mg.SCRIPT_PATH
    if show_early_steps: print('Just set prog_path')
    try:
        ## 1) make local SOFA folder if missing. Otherwise, leave intact for now
        try:
            local_path_setup_needed = not os.path.exists(mg.LOCAL_PATH)
            if local_path_setup_needed:
                make_local_subfolders(mg.LOCAL_PATH, local_subfolders)
            run_test_code(mg.TEST_SCRIPT_EARLIEST)
            if local_path_setup_needed:
                ## need mg but must run pre code calling dd
                default_proj = mg.LOCAL_PATH / mg.PROJS_FOLDER / mg.DEFAULT_PROJ
                populate_local_paths(prog_path, mg.LOCAL_PATH, default_proj)
                config_local_proj(
                    mg.LOCAL_PATH, default_proj, subfolders_in_proj)
                store_version(mg.LOCAL_PATH)
        except Exception as e:
            raise Exception(
                f'Unable to make local sofa folders in "{mg.LOCAL_PATH}."'
                + f'\nCaused by error: {b.ue(e)}')
        run_test_code(mg.TEST_SCRIPT_POST_CONFIG)  ## can now use dd and proj config
        ## 2) Modify existing local SOFA folder if version change require it
        existing_local = not local_path_setup_needed
        if existing_local:
            try:  ## e.g. if already installed version is older than 1.1.16 ...
                installed_version = get_installed_version(mg.LOCAL_PATH)
                if show_early_steps: print('Just got installed version')
                new_version = (installed_version is None 
                    or lib.version_a_is_newer(version_a=mg.VERSION,
                    version_b=installed_version))
                if new_version:
                    ## update css files - url(images...) -> url('images...')
                    populate_css_path(prog_path, mg.LOCAL_PATH)
                    ## ensure sofastats_report_extras folder and freshly populate it
                    REPORT_EXTRAS_PATH = (
                        mg.LOCAL_PATH / mg.REPORTS_FOLDER
                        / mg.REPORT_EXTRAS_FOLDER)
                    try:
                        REPORT_EXTRAS_PATH.mkdir(exist_ok=True)  ## under reports
                        if show_early_steps: 
                            print(f'Just made {REPORT_EXTRAS_PATH}')
                    except Exception as e:
                        raise Exception('Unable to make report extras '
                            f'path "{REPORT_EXTRAS_PATH}".'
                            + f'\nCaused by error: {b.ue(e)}')
                    populate_extras_path(prog_path, mg.LOCAL_PATH)
                    archive_older_default_report()
                    store_version(mg.LOCAL_PATH)  ## update it so only done once
            except Exception as e:
                raise Exception('Problem modifying your local sofastats folder.'
                    f' One option is to delete the "{mg.LOCAL_PATH}" folder and'
                    f' let SOFA make a fresh one.\nCaused by error: {b.ue(e)}')
        ## 3) Make a fresh recovery folder if needed
        try:
            freshen_recovery(prog_path, local_subfolders, subfolders_in_proj)
        except Exception as e:
            raise Exception(
                f'Problem freshening your recovery folder "{prog_path}".'
                f'\nCaused by error: {b.ue(e)}')
        ## 4) ensure the internal copy images path exists
        mg.INT_COPY_IMGS_PATH.mkdir(exist_ok=True)  #@UndefinedVariable
    except Exception as e:
        if show_early_steps: 
            print('Problem running initial setup - about to make msg.')
        msg = f'Problem running initial setup.\nCaused by error: {b.ue(e)}'
        if show_early_steps: 
            print(msg)
            print(traceback.format_exc())
        msgapp = ErrMsgApp(msg)
        msgapp.MainLoop()
        del msgapp
    return local_path_setup_needed

# local importing
try:
    about = 'config_output'
    from . import config_output  #@UnusedImport actually uses proj dict and connects to sofa_db. Thus
        ## can't rely on wx.msgboxes etc because wx.App not up yet
    about = 'getdata'
    from . import getdata #@UnusedImport
    about = 'projects'
    from . import projects #@UnusedImport
    about = 'projects_gui'
    from . import projects_gui #@UnusedImport
    about = 'projselect'
    from . import projselect #@UnusedImport
    about = 'quotes'
    from . import quotes #@UnusedImport
except my_exceptions.ComtypesException as e:
    msgapp = ErrMsgApp(b.ue(e))
except my_exceptions.InconsistentFileDate as e:
    msgapp = ErrMsgApp(b.ue(e))
except Exception as e:
    msg = (
        f'Problem with second round of local importing while importing {about}.'
        f'\nCaused by error: {b.ue(e)}'
        f'\n\nMore details that may help developer:\n{traceback.format_exc()}')
    msgapp = ErrMsgApp(msg)
    # msgapp.MainLoop() # already sys.exit()
    # del msgapp
