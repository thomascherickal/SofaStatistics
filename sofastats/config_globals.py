import os
from pathlib import Path
import subprocess
import wx

"""
Anything called here should rely as little as possible on modules other than
my_globals itself. The goal is to avoid circular importing.

This module is used immediately after my_globals is loaded and needs to complete
any config (of my_globals) before other local modules are loaded so they can be
assumed to be safe to start. Other modules need to be able to rely on the
correctness of what is in my_globals at the time they are called.
"""

from . import basic_lib as b
from . import my_globals as mg

def set_SCRIPT_PATH():
    """
    Using __file__ on start.py doesn't work (it will show where the interpreter
    is) but it will on an imported module in same path, even if running from an
    interpreter e.g. IDLE.
    http://stackoverflow.com/questions/247770/retrieving-python-module-path
    http://www.velocityreviews.com/forums/t336564-proper-use-of-file.html
    """
    rawpth = os.path.dirname(mg.__file__)
    mg.SCRIPT_PATH = Path(rawpth)
    if mg.SCRIPT_PATH == mg.LOCAL_PATH:
        raise Exception(_("Oops - it looks like you've installed SOFA to your "
            "user directory rather than a program directory. Please uninstall "
            "SOFA and reinstall to a different location."))

def import_dbe_plugin(dbe_plugin):
    """
    Include database engine in system if in dbe_plugins folder and
    os-appropriate.
    """
    try:
        if dbe_plugin == mg.DBE_SQLITE:
            from sofastats.dbe_plugins import dbe_sqlite
            mod = dbe_sqlite
        elif dbe_plugin == mg.DBE_MYSQL:
            from sofastats.dbe_plugins import dbe_mysql
            mod = dbe_mysql
        elif dbe_plugin == mg.DBE_CUBRID:
            from sofastats.dbe_plugins import dbe_cubrid
            mod = dbe_cubrid
        elif dbe_plugin == mg.DBE_MS_ACCESS:
            from sofastats.dbe_plugins import dbe_ms_access
            mod = dbe_ms_access
        elif dbe_plugin == mg.DBE_MS_SQL:
            from sofastats.dbe_plugins import dbe_ms_sql
            mod = dbe_ms_sql
        elif dbe_plugin == mg.DBE_PGSQL:
            from sofastats.dbe_plugins import dbe_postgresql
            mod = dbe_postgresql
        else:
            raise Exception('Unknown database engine plug-in type')
    except ImportError as e:
        raise Exception(
            f'Import error with "{dbe_plugin}". Caused by error: {b.ue(e)}')
    return mod

def import_dbe_plugins():
    """
    Tries to keep going even if a database module doesn't work etc. Of course,
    if SQLite isn't available we are doomed as that runs the default database.
    """
    for dbe_plugin, dbe_mod_name in mg.DBE_PLUGINS:
        wrong_os = (dbe_plugin in [mg.DBE_MS_ACCESS, mg.DBE_MS_SQL] 
            and mg.PLATFORM != mg.WINDOWS)
        dbe_plugin_mod = mg.SCRIPT_PATH / 'dbe_plugins' / f'{dbe_mod_name}.py'
        if os.path.exists(dbe_plugin_mod):
            if wrong_os:
                print(f"Not adding dbe plug-in '{dbe_plugin}'. Wrong OS")
            else:
                try:
                    dbe_mod = import_dbe_plugin(dbe_plugin)
                except Exception as e:
                    msg = (f"Not adding dbe plugin {dbe_plugin}."
                        f"\nReason: {b.ue(e)}")
                    print(msg)
                    mg.DBE_PROBLEM.append(msg)
                    continue  ## skip bad module
                else:
                    print(f"Successfully added dbe plug-in '{dbe_plugin}'")
                    mg.DBES.append(dbe_plugin)
                    mg.DBE_MODULES[dbe_plugin] = dbe_mod
        else:
            print(f"Couldn't find path: {dbe_plugin_mod}")

def get_date_fmt():
    """
    On Windows, get local datetime_format.

    With insights from code by Denis Barmenkov <barmenkov at bpc.ru>
    (see http://win32com.goermezer.de/content/view/210/291/) and registry
    details from http://windowsitpro.com/article/articleid/71636/jsi-tip-0311---regional-settings-in-the-registry.html

    On Linux and possibly OS-X, locale command works.

    :return: MDY, DMY, or YMD.
    :rtype: str
    """
    debug = False
    default_d_fmt = mg.DMY
    try:
        if mg.PLATFORM == mg.WINDOWS:
            try:  ## the following must have been specially installed
                import win32api
                import win32con
            except ImportError as e:
                raise Exception(_('Problem with Windows modules. Did all steps '
                    'in installation succeed? You may need to install again.'
                    '"\nError caused by: %s' % b.ue(e)))
            rkey = win32api.RegOpenKey(
                win32con.HKEY_CURRENT_USER, 'Control Panel\\International')
            raw_d_fmt = win32api.RegQueryValueEx(rkey, 'iDate')[0]
            raw2const = {'0': mg.MDY, '1': mg.DMY, '2': mg.YMD}
            win32api.RegCloseKey(rkey)
        else:
            cmd = 'locale -k LC_TIME'
            child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
            locale_dets = child.stdout.read().strip().split()
            d_fmt_str = [x for x in locale_dets if x.startswith(b"d_fmt")][0]
            raw_d_fmt = str(d_fmt_str.split(b"=")[1].strip().strip(b'"'),
                encoding='utf-8')
            raw2const = {
                '%m/%d/%y': mg.MDY, '%m/%d/%Y': mg.MDY, 
                '%m-%d-%y': mg.MDY, '%m-%d-%Y': mg.MDY,
                '%d/%m/%y': mg.DMY, '%d/%m/%Y': mg.DMY, 
                '%d-%m-%y': mg.DMY, '%d-%m-%Y': mg.DMY,
                '%y/%m/%d': mg.YMD, '%Y/%m/%d': mg.YMD, 
                '%y-%m-%d': mg.YMD, '%Y-%m-%d': mg.YMD}
        try:
            if debug: print('%s %s' % (raw2const, raw_d_fmt))
            d_fmt = raw2const[raw_d_fmt]
        except KeyError:
            print(f'Unexpected raw_d_fmt ({raw_d_fmt}) in get_date_fmt()')
            d_fmt = default_d_fmt
    except Exception as e:
        print(f'Unable to get date format.\nCaused by error: {b.ue(e)}')
        d_fmt = default_d_fmt
    return d_fmt

def set_ok_date_formats():
    d_fmt = get_date_fmt()
    set_ok_date_formats_by_fmt(d_fmt)

def set_ok_date_formats_by_fmt(d_fmt):
    if d_fmt == mg.DMY:
        extra_ok_date_formats = [
            '%d-%m-%y', '%d-%m-%Y',
            '%d/%m/%y', '%d/%m/%Y',
            '%d.%m.%y', '%d.%m.%Y']  ## European
        ok_date_format_examples = ['31/3/09', '2:30pm 31/3/2009']
    elif d_fmt == mg.MDY:
        ## needed for US, Canada, the Philippines etc
        extra_ok_date_formats = [
            '%m-%d-%y', '%m/%d/%y', '%m.%d.%y', 
            '%m-%d-%Y', '%m/%d/%Y', '%m.%d.%Y']
        ok_date_format_examples = ['3/31/09', '2:30pm 3/31/2009']
    elif d_fmt == mg.YMD:
        extra_ok_date_formats = []
        ok_date_format_examples = ['09/03/31', '2:30pm 09/03/31']
    else:
        raise Exception('Unexpected d_fmt value (%s) in get_date_fmt_lists()'
                        % d_fmt)
    always_ok_date_formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%Y',  ## 2015
        '%Y.0',  ## 2015.0
        '%Y-%m',  ## 2015-08
        '%Y-%b',  ## 2015-Aug
        '%Y-%B',  ## 2015-August
        '%m-%Y',  ## 08-2015
        '%b-%Y',  ## Aug-2015
        '%B-%Y',  ## August-2015
        '%Y %b',  ## 2015 Aug
        '%Y %B',  ## 2015 August
        '%B %Y',  ## February 2010 
        '%b %Y',  ## Feb 2010
        '%B %d, %Y',  ## February 11, 2010 
        '%b %d, %Y',  ## Feb 11, 2010
        '%B %d %Y',  ## February 11 2010 
        '%b %d %Y',  ## Feb 11 2010
        '%d %B, %Y',  ## 11 February, 2010 
        '%d %b, %Y',  ## 11 Feb, 2010
        '%d %B %Y',  ## 11 February 2010 
        '%d %b %Y',  ## 11 Feb 2010
    ]
    ok_date_formats =  extra_ok_date_formats + always_ok_date_formats
    mg.OK_DATE_FORMATS = ok_date_formats
    mg.OK_DATE_FORMAT_EXAMPLES = ok_date_format_examples

def get_settings_dic(subfolder, fil_name):
    """
    Returns settings_dic with keys for each setting.
    Used for project dics, preferences dics etc.
    """
    settings_path = mg.LOCAL_PATH / subfolder / fil_name
    settings_cont = b.get_bom_free_contents(fpath=settings_path)
    settings_dic = {}
    try:
        exec(settings_cont, settings_dic)
    except SyntaxError as e:
        err_msg = _("Syntax error in settings file \"%(fil_name)s\"."
            "\n\nDetails: %(details)s") % {'fil_name': fil_name,  
            "details": b.ue(e)}
        try:
            wx.MessageBox(err_msg)  ## only works if wx.App up.
            raise
        except Exception as e:
            raise Exception(err_msg)
    except Exception as e:
        err_msg = _("Error processing settings file \"%(fil_name)s\"."
            "\n\nDetails: %(details)s") % {'fil_name': fil_name,
            "details": b.ue(e)}
        try:
            wx.MessageBox(err_msg)
            raise
        except Exception as e:
            raise Exception(err_msg)
    return settings_dic

def set_fonts():
    font_size = 11 if mg.PLATFORM == mg.MAC else 9
    mg.LABEL_FONT = wx.Font(font_size, wx.SWISS, wx.NORMAL, wx.BOLD)
    mg.BTN_FONT = wx.Font(font_size, wx.SWISS, wx.NORMAL, wx.NORMAL)
    mg.BTN_BOLD_FONT = wx.Font(font_size, wx.SWISS, wx.NORMAL, wx.BOLD)
    mg.GEN_FONT = wx.Font(font_size, wx.SWISS, wx.NORMAL, wx.NORMAL)

def set_DEFAULT_DETAILS(ignore_prefs=False):
    """
    Update mg.DEFAULT_DETAILS (if any prefs set).

    :param bool ignore_prefs: used if wanting to test different levels than in
     prefs doc from unit test.
    """
    if not ignore_prefs:
        try:
            prefs_dic = get_settings_dic(subfolder=mg.INT_FOLDER, 
                fil_name=mg.INT_PREFS_FILE)
            stored_lev = (prefs_dic.get(mg.PREFS_KEY, {})
                .get(mg.PREFS_DEFAULT_DETAILS_KEY))
            if stored_lev not in [True, False]:
                raise Exception(f'Invalid stored level: {b.ue(stored_lev)}')
            mg.DEFAULT_DETAILS = stored_lev
        except Exception:
            mg.DEFAULT_DETAILS = False
