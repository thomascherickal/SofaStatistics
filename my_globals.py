from __future__ import print_function
import os
import subprocess
import sys

# my_globals exists to reduce likelihood of circular imports.
# It does't do any local importing at all until the last line, where it imports
# config (used for initial config plus re-config).

debug = False

VERSION = u"0.9.6"

MAIN_SCRIPT_START = u"#sofa_main_script_start"
SCRIPT_END = u"#sofa_script_end"
PYTHON_ENCODING_DECLARATION = u"#! /usr/bin/env python" + os.linesep + \
    u"# -*- coding: utf-8 -*-" + os.linesep
DROP_SELECT = _("Select")
# core stats *********************************************************
STATS_DIC_LABEL = u"label"
STATS_DIC_N = u"n"
STATS_DIC_MEDIAN = u"median"
STATS_DIC_MEAN = u"mean"
STATS_DIC_SD = u"sd"
STATS_DIC_MIN = u"min"
STATS_DIC_MAX = u"max"
# stats output *******************************************************
OUTPUT_RESULTS_ONLY = u"Output results only"
# Making tables ******************************************************
HAS_TOTAL = _("Total") # doubles as display label
COL_MEASURES = 0 # indexes in tab type
ROW_SUMM = 1
RAW_DISPLAY = 2
COL_MEASURES_TREE_LBL = _("Column measures")
# dimension trees
ROWDIM = _("row") #double as labels
COLDIM = _("column")
# actual options selected ...
SORT_NONE = _("None") #double as labels
SORT_LABEL = _("By Label")
SORT_FREQ_ASC = _("By Freq (Asc)")
SORT_FREQ_DESC = _("By Freq (Desc)")
# can use content of constant as a short label
FREQ = _("Freq")
ROWPCT = _("Row %")
COLPCT = _("Col %")
SUM = _("Sum")
MEAN = _("Mean")
MEDIAN = _("Median")
SUMM_N = u"N" # N used in Summary tables
STD_DEV = _("Std Dev")
measures_long_label_dic = {FREQ: _("Frequency"), 
                           ROWPCT: _("Row %"),
                           COLPCT: _("Column %"),
                           SUM: _("Sum"), 
                           MEAN: _("Mean"),
                           MEDIAN: _("Median"), 
                           SUMM_N: "N",
                           STD_DEV: _("Standard Deviation")}
# content of constant and constant (ready to include in exported script)
# e.g. "dimtables.%s" "ROWPCT"
script_export_measures_dic = {FREQ: u"FREQ", 
                              ROWPCT: u"ROWPCT",
                              COLPCT: u"COLPCT",
                              SUM: u"SUM", 
                              MEAN: u"MEAN",
                              MEDIAN: u"MEDIAN", 
                              SUMM_N: u"SUMM_N",
                              STD_DEV: u"STD_DEV"}
# Used to make it easy to slice into html and replace titles and subtitles only.
# Changing the return values of get html functions to get html_pre_title, 
# html_title, html_post_title etc was deemed an even worse approach ;-)
TBL_TITLE_START = u"<!--_title_start-->"
TBL_TITLE_END = u"<!--_title_end-->"
TBL_SUBTITLE_START = u"<!--_subtitle_start-->"
TBL_SUBTITLE_END = u"<!--_subtitle_end-->"
def pct_1_dec(num):
    return "%s%%" % round(num,1)
def pct_2_dec(num):
    return "%s%%" % round(num,2)
data_format_dic = {FREQ: str, ROWPCT: pct_1_dec, COLPCT: pct_1_dec}
# output - NB never have a class which is the same as the start of another
# simple search and replace is worth keeping
CSS_ALIGN_RIGHT = u"right"
CSS_LBL = u"lbl"
CSS_TBL_TITLE = u"tbltitle"
CSS_TBL_TITLE_CELL = u"tblcelltitle"
CSS_TBL_SUBTITLE = u"tblsubtitle"
CSS_FIRST_COL_VAR = u"firstcolvar"
CSS_FIRST_ROW_VAR = u"firstrowvar"
CSS_DATACELL = u"datacell"
CSS_FIRST_DATACELL = u"firstdatacell"
CSS_SPACEHOLDER = u"spaceholder"
CSS_ROW_VAL = u"rowval"
CSS_COL_VAL = u"colval"
CSS_ROW_VAR = u"rowvar"
CSS_COL_VAR = u"colvar"
CSS_MEASURE = u"measure"
CSS_TOTAL_ROW = u"total-row"
CSS_PAGE_BREAK_BEFORE = u"page-break-before"
CSS_TBL_HDR_FTNOTE = u"tbl-header-ftnote"
CSS_ELEMENTS = [CSS_ALIGN_RIGHT, CSS_LBL, CSS_TBL_TITLE, 
    CSS_TBL_TITLE_CELL, CSS_TBL_SUBTITLE, CSS_FIRST_COL_VAR, CSS_FIRST_ROW_VAR, 
    CSS_DATACELL, CSS_FIRST_DATACELL, CSS_SPACEHOLDER, CSS_ROW_VAL, CSS_COL_VAL, 
    CSS_ROW_VAR, CSS_COL_VAR, CSS_MEASURE, CSS_TOTAL_ROW, CSS_PAGE_BREAK_BEFORE,
    CSS_TBL_HDR_FTNOTE]
CSS_SUFFIX_TEMPLATE = u"%s%s"
# projects ******************************************************
EMPTY_PROJ_NAME = _("GIVE ME A NAME ...")
SOFA_DEFAULT_DB = u"SOFA_Default_db"
SOFA_DEFAULT_TBL = u"SOFA_Default_tbl"
SOFA_DEFAULT_PROJ = u"SOFA_Default_Project.proj"
SOFA_DEFAULT_VDTS = u"SOFA_Default_Var_Dets.vdts"
SOFA_DEFAULT_STYLE = u"SOFA_Default_Style.css"
SOFA_DEFAULT_SCRIPT = u"SOFA_Default_Exported_Table_Scripts.py"
SOFA_DEFAULT_REPORT = u"SOFA_Default_New_Tables.htm"
SOFA_DEFAULT_PATHS = u"SOFA_Default_Paths.txt"
INTERNAL_FOLDER = u"_internal"
local_encoding = sys.getfilesystemencoding()
USER_PATH = unicode(os.path.expanduser("~"), local_encoding)
LOCAL_PATH = os.path.join(USER_PATH, u"sofa")
SCRIPT_PATH = sys.path[0] # NB won't work within an interpreter
# http://www.velocityreviews.com/forums/t336564-proper-use-of-file.html
INT_PATH = os.path.join(LOCAL_PATH, INTERNAL_FOLDER)
INT_SCRIPT_PATH = os.path.join(INT_PATH, u"script.py")
INT_REPORT_FILE = u"report.htm"
INT_PREFS_FILE = u"prefs.txt"
INT_REPORT_PATH = os.path.join(INT_PATH, INT_REPORT_FILE)
DEFAULT_CSS_PATH = os.path.join(LOCAL_PATH, u"css", SOFA_DEFAULT_STYLE)
VAR_TYPE_CAT = _("Nominal (names only)")
VAR_TYPE_ORD = _("Ordinal (rank only)")
VAR_TYPE_QUANT = _("Quantity (is an amount)")
VAR_TYPES = [VAR_TYPE_CAT, VAR_TYPE_ORD, VAR_TYPE_QUANT]
VAR_IDX_CAT = 0
VAR_IDX_ORD = 1
VAR_IDX_QUANT = 2
# getdata ******************************************************
# misc field dets
FLD_SEQ = u"field sequence"
FLD_BOLNULLABLE = u"field nullable"
FLD_DATA_ENTRY_OK = u"data entry ok" # e.g. not autonumber, timestamp etc
FLD_COLUMN_DEFAULT = u"field default"
# test
FLD_BOLTEXT = u"field text"
FLD_TEXT_LENGTH = u"field text length"
FLD_CHARSET = u"field charset"
# numbers
FLD_BOLNUMERIC = u"field numeric"
FLD_BOLAUTONUMBER = u"field autonumber"
FLD_DECPTS = u"field decpts"
FLD_NUM_WIDTH = u"field numeric display width" # used for column display only
FLD_BOL_NUM_SIGNED = u"field numeric signed"
FLD_NUM_MIN_VAL = u"field numeric minimum value"
FLD_NUM_MAX_VAL = u"field numeric maximum value"
# datetime
FLD_BOLDATETIME = u"field datetime"
# indexes
IDX_NAME = u"index name"
IDX_IS_UNIQUE = u"index is unique"
IDX_FLDS = u"index fields"
# misc data
MISSING_VAL_INDICATOR = u"."
# must be defined before dbe modules called - used in them
GTE_EQUALS = "="
GTE_NOT_EQUALS = "not =" # each dbe converts to appropriate SQL operators
GTE_GT = ">"
GTE_LT = "<"
GTE_GTE = ">="
GTE_LTE = "<="
GTES = [GTE_EQUALS, GTE_NOT_EQUALS, GTE_GT, GTE_LT, GTE_GTE, GTE_LTE]
# also used as labels in dropdowns
DBE_SQLITE = u"SQLite"
DBE_MYSQL = u"MySQL"
DBE_MS_ACCESS = u"MS Access"
DBE_MS_SQL = u"MS SQL Server"
DBE_PGSQL = u"PostgreSQL"
"""
Include database engine in system if in dbe_plugins folder and os-appropriate.
"""
def import_dbe_plugin(dbe_plugin):
    if dbe_plugin == DBE_SQLITE:
        import dbe_plugins.dbe_sqlite as dbe_sqlite
        mod = dbe_sqlite
    elif dbe_plugin == DBE_MYSQL:
        import dbe_plugins.dbe_mysql as dbe_mysql
        mod = dbe_mysql
    elif dbe_plugin == DBE_MS_ACCESS:
        import dbe_plugins.dbe_ms_access as dbe_ms_access
        mod = dbe_ms_access
    elif dbe_plugin == DBE_MS_SQL:
        import dbe_plugins.dbe_ms_sql as dbe_ms_sql
        mod = dbe_ms_sql
    elif dbe_plugin == DBE_PGSQL:
        import dbe_plugins.dbe_postgresql as dbe_postgresql
        mod = dbe_postgresql
    return mod
try:
    IN_WINDOWS = os.environ['OS'].lower().startswith("windows")
except Exception:
    IN_WINDOWS = False
DBES = []
DBE_MODULES = {}
DBE_PLUGINS = [(DBE_SQLITE, u"dbe_sqlite"), 
               (DBE_MYSQL, u"dbe_mysql"), 
               (DBE_MS_ACCESS, u"dbe_ms_access"), 
               (DBE_MS_SQL, u"dbe_ms_sql"),
               (DBE_PGSQL, u"dbe_postgresql"),
               ]
for dbe_plugin, dbe_mod_name in DBE_PLUGINS:
    for_win_yet_not_win = not IN_WINDOWS and \
        dbe_plugin in [DBE_MS_ACCESS, DBE_MS_SQL]
    dbe_plugin_mod = os.path.join(os.path.dirname(__file__), u"dbe_plugins", 
                                   u"%s.py" % dbe_mod_name)
    if os.path.exists(dbe_plugin_mod):
        if not for_win_yet_not_win: # i.e. OK to add module
            try:
                dbe_mod = import_dbe_plugin(dbe_plugin)
            except Exception, e:
                if debug: print(u"Problem adding dbe plugin %s" % dbe_plugin +
                    u". Orig err: %s" % e)
                continue # skip bad module
            DBES.append(dbe_plugin)
            DBE_MODULES[dbe_plugin] = dbe_mod
            
# field type labels - must work as labels as well as consts
FLD_TYPE_NUMERIC = _("Numeric")
FLD_TYPE_STRING = _("String")
FLD_TYPE_DATE = _("Date")
GEN2SQLITE_DIC = {
    FLD_TYPE_NUMERIC: {"sqlite_type": "REAL", 
            "check_clause": ("CHECK(typeof(%(fld_name)s) = 'null' "
            "or is_numeric(%(fld_name)s))")},
    FLD_TYPE_STRING: {"sqlite_type": "TEXT",
            "check_clause": ""},
    FLD_TYPE_DATE: {"sqlite_type": "DATETIME", # DATETIME not a native storage 
                #class but can still be discovered via PRAGMA table_info()
            "check_clause": ("CHECK(typeof(%(fld_name)s) = 'null' "
            "or is_std_datetime_str(%(fld_name)s))")},
    }
# grids
# move directions
MOVE_LEFT = u"move left"
MOVE_RIGHT = u"move right"
MOVE_UP = u"move up"
MOVE_DOWN = u"move down"
MOVE_UP_RIGHT = u"move up right"
MOVE_UP_LEFT = u"move up left"
MOVE_DOWN_RIGHT = u"move down right"
MOVE_DOWN_LEFT = u"move down left"
# cell move types
MOVING_IN_EXISTING = u"moving in existing"
MOVING_IN_NEW = u"moving in new"
LEAVING_EXISTING = u"leaving existing"
LEAVING_NEW = u"leaving new"
# table details
TBL_FLD_NAME = "fld_name"
TBL_FLD_NAME_ORIG = "fld_name_orig"
TBL_FLD_TYPE = "fld_type"
TBL_FLD_TYPE_ORIG = "fld_type_orig"
TMP_TBL_NAME = "sofa_tmp_tbl"
SOFA_ID = "sofa_id"
# filters
DBE_TBL_FILTS = {}
# Matplotlib
FACECOLOR = "#f87526"
EDGECOLOR = "#8f8f8f"
NORM_LINE_COLOR = "#5a4a3d"
INT_IMG_ROOT = os.path.join(INT_PATH, u"_img")
# date formats
MDY = "month_day_year"
DMY = "day_month_year"
YMD = "year_month_day"
def get_date_fmt():
    """
    On Windows, get local datetime_format.
    With insights from code by Denis Barmenkov <barmenkov at bpc.ru>
        (see http://win32com.goermezer.de/content/view/210/291/) and registry
        details from http://windowsitpro.com/article/articleid/71636/...
        ...jsi-tip-0311---regional-settings-in-the-registry.html.
    On Linux and possibly OS-X, locale command works.
    Returns MDY, DMY, or YMD.
    """
    debug = False
    try:
        if IN_WINDOWS:
            # the following must have been specially installed
            import win32api
            import win32con
            rkey = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER, 
                                       'Control Panel\\International')
            raw_d_fmt = win32api.RegQueryValueEx(rkey, "iDate")[0]
            raw2const = {"0": MDY, "1": DMY, "2": YMD}
            win32api.RegCloseKey(rkey)
        else:
            cmd = 'locale -k LC_TIME'
            child = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, 
                                     stdout=subprocess.PIPE)
            locale_dets = child.stdout.read().strip().split()
            d_fmt_str = [x for x in locale_dets if x.startswith("d_fmt")][0]
            raw_d_fmt = d_fmt_str.split("=")[1].strip().strip('"')
            raw2const = {"%m/%d/%y": MDY, "%m/%d/%Y": MDY,
                         "%d/%m/%y": DMY, "%d/%m/%Y": DMY,
                         "%y/%m/%d": YMD, "%Y/%m/%d": YMD}
    except Exception, e:
        raise Exception, "Unable to get date format. %s" % e
    try:
        if debug: print("%s %s" % (raw2const, raw_d_fmt))
        d_fmt = raw2const[raw_d_fmt]
    except KeyError:
        print("Unexpected raw_d_fmt (%s) in get_date_fmt()" % raw_d_fmt)
        d_fmt = DMY
    return d_fmt
d_fmt = get_date_fmt()
def get_date_fmt_lists(d_fmt):
    if d_fmt == DMY:
        extra_ok_date_formats = ["%d-%m-%y", "%d-%m-%Y",
                                 "%d/%m/%y", "%d/%m/%Y",
                                 "%d.%m.%y", "%d.%m.%Y"] # European
        ok_date_format_examples = ["31/3/09", "2:30pm 31/3/2009"]
    elif d_fmt == MDY:
        # needed for US, Canada, the Philippines etc
        extra_ok_date_formats = ["%m-%d-%y", "%m/%d/%y", "%m-%d-%Y", "%m/%d/%Y"]
        ok_date_format_examples = ["3/31/09", "2:30pm 3/31/2009"]
    elif d_fmt == YMD:
        extra_ok_date_formats = []
        ok_date_format_examples = ["09/03/31", "2:30pm 09/03/31"]
    else:
        raise Exception, "Unexpected d_fmt value (%s) in get_date_fmt_lists()" \
            % d_fmt
    always_ok_date_formats = ["%Y-%m-%d", "%Y"]
    ok_date_formats =  extra_ok_date_formats + always_ok_date_formats
    return ok_date_formats, ok_date_format_examples
OK_DATE_FORMATS, OK_DATE_FORMAT_EXAMPLES = get_date_fmt_lists(d_fmt)
OK_TIME_FORMATS = ["%I%p", "%I:%M%p", "%H:%M", "%H:%M:%S"]
# preferences
PREFS_KEY = "Prefs"
DEFAULT_LEVEL_KEY = "default level key"
LEVEL_FULL = _("Full Explanation")
LEVEL_BRIEF = _("Brief Explanation")
LEVEL_RESULTS_ONLY = _("Results Only")
LEVELS = (LEVEL_FULL, LEVEL_BRIEF, LEVEL_RESULTS_ONLY)
# remember defaults //////////
# stats tests
GROUP_BY_DEFAULT = None
VAR_AVG_DEFAULT = None
VAR_1_DEFAULT = None
VAR_2_DEFAULT = None
GROUP_A_DEFAULT = None
GROUP_B_DEFAULT = None
VAL_A_DEFAULT = None
VAL_B_DEFAULT = None
# data last selected
DBE_DEFAULT = None
DB_DEFAULTS = {}
TBL_DEFAULTS = {}
JS_WRAPPER_L = u"\n\n<script type=\"text/javascript\">"
JS_WRAPPER_R = u"\n</script>"

# ////////////////////////////////////////////////////////////
import config_globals
config_globals.set_DEFAULT_LEVEL()