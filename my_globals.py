#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import platform
from subprocess import Popen, PIPE
import sys
import wx

# my_globals exists to reduce likelihood of circular imports.
# It doesn't do any local importing at all until the last line, where it imports
# config (used for initial config plus re-config).

debug = False

VERSION = u"1.2.1"
ATTRIBUTION = u"sofastatistics.com"
CONTACT = u"grant@sofastatistics.com"
# http://docs.wxwidgets.org/2.9/language_8h.html
"""
LANGUAGE_GALICIAN, LANGUAGE_CROATIAN, LANGUAGE_RUSSIAN, LANGUAGE_HEBREW
LANGUAGE_BRETON, LANGUAGE_SPANISH, LANGUAGE_ENGLISH, LANGUAGE_SPANISH_ARGENTINA
"""
TEST_LANGID = wx.LANGUAGE_CROATIAN
FEEDBACK_LINK = _(u"Give quick feedback on SOFA")
MAIN_SCRIPT_START = u"#sofa_main_script_start"
SCRIPT_END = u"#sofa_script_end"
ADD2RPT = False
PYTHON_ENCODING_DECLARATION = u"#! /usr/bin/env python" + os.linesep + \
    u"# -*- coding: utf-8 -*-" + os.linesep
DROP_SELECT = _("Nothing selected")
ODS_GETTING_LARGE = 10000000
MAX_WIDTH = None # set later
MAX_HEIGHT = None
DEFAULT_LEVEL = None
HORIZ_OFFSET = 0
# core stats *********************************************************
STATS_DIC_LBL = u"label"
STATS_DIC_N = u"n"
STATS_DIC_MEDIAN = u"median"
STATS_DIC_MEAN = u"mean"
STATS_DIC_SD = u"sd"
STATS_DIC_MIN = u"min"
STATS_DIC_MAX = u"max"
DF = _("Degrees of Freedom (df)")
P_EXPLAN_DIFF = (u"If p is small, "
            u"e.g. less than 0.01, or 0.001, you can assume the result is "
            u"statistically significant i.e. there is a difference.")
P_EXPLAN_REL = (u"If p is small, "
            u"e.g. less than 0.01, or 0.001, you can assume the result is "
            u"statistically significant i.e. there is a relationship.")
# stats output *******************************************************
OUTPUT_RESULTS_ONLY = u"Output results only"
# Making tables ******************************************************
# can use content of constant as a short label
FREQ = _("Freq")
ROWPCT = _("Row %")
COLPCT = _("Col %")
SUM = _("Sum")
MEAN = _("Mean")
MEDIAN = _("Median")
SUMM_N = u"N" # N used in Summary tables
STD_DEV = _("Std Dev")
MIN = _("Min")
MAX = _("Max")
RANGE = _("Range")
LOWER_QUARTILE = _("L. Quartile")
UPPER_QUARTILE = _("U. Quartile")
IQR = _(u"IQR") # Inter-Quartile Range
measures_long_lbl_dic = {FREQ: _("Frequency"), 
                         ROWPCT: _("Row %"),
                         COLPCT: _("Column %"),
                         SUM: _("Sum"), 
                         MEAN: _("Mean"),
                         MEDIAN: _("Median"), 
                         SUMM_N: "N",
                         STD_DEV: _("Standard Deviation"),
                         MIN: _("Minimum"),
                         MAX: _("Maximum"),
                         RANGE: _("Range"),
                         LOWER_QUARTILE: _("Lower Quartile"),
                         UPPER_QUARTILE: _("Upper Quartile"),
                         IQR: _("Inter-Quartile Range"),
                         }
HAS_TOTAL = _("Total") # doubles as display label
FREQS = 0 # indexes in tab type
CROSSTAB = 1
ROW_STATS = 2
DATA_LIST = 3
FREQS_LBL = _("Frequencies")
CROSSTAB_LBL = _("Crosstabs")
ROW_STATS_LBL = _("Row Stats")
DATA_LIST_LBL = _("Data List")
TAB_TYPE2LBL = {FREQS: FREQS_LBL, CROSSTAB: CROSSTAB_LBL, 
                ROW_STATS: ROW_STATS_LBL, DATA_LIST: DATA_LIST_LBL}
EMPTY_ROW_LBL = u""
COL_MEASURES_KEY = u"Col measures key"
ROWPCT_AN_OPTION_KEY = u"Rowpct an option? key"
MEASURES_HORIZ_KEY = u"measures_horiz_key"
VAR_SUMMARISED_KEY = u"var_summarised key"
DEFAULT_MEASURE_KEY = u"default_measure_key"
NEEDS_ROWS_KEY = u"needs_row_key"
QUICK_IF_BELOW_KEY = u"quick_live_below_key" # safe assumption that we can run 
    # live demo output if table has less than this records
debug = False
RPT_CONFIG = {
    FREQS: {COL_MEASURES_KEY: [FREQ, COLPCT], 
            VAR_SUMMARISED_KEY: False,
            NEEDS_ROWS_KEY: True,
            ROWPCT_AN_OPTION_KEY: True,
            MEASURES_HORIZ_KEY: True,
            DEFAULT_MEASURE_KEY: FREQ,
            QUICK_IF_BELOW_KEY: 1000 if debug else 5000}, # 5000
    CROSSTAB: {COL_MEASURES_KEY: [FREQ, COLPCT], 
               VAR_SUMMARISED_KEY: False,
               NEEDS_ROWS_KEY: True,
               ROWPCT_AN_OPTION_KEY: True,
               MEASURES_HORIZ_KEY: True,
               DEFAULT_MEASURE_KEY: FREQ,
               QUICK_IF_BELOW_KEY: 1000 if debug else 4000}, # 4000
    ROW_STATS: {COL_MEASURES_KEY: [MEAN, MEDIAN, SUMM_N, MIN, MAX, RANGE,
                                   LOWER_QUARTILE, UPPER_QUARTILE, IQR, SUM],
               VAR_SUMMARISED_KEY: True,
               NEEDS_ROWS_KEY: False,
               ROWPCT_AN_OPTION_KEY: False, 
               MEASURES_HORIZ_KEY: False,
               DEFAULT_MEASURE_KEY: MEAN,
               QUICK_IF_BELOW_KEY: 1000 if debug else 2000}, # 2000
    DATA_LIST: {COL_MEASURES_KEY: [],
                VAR_SUMMARISED_KEY: False, 
                NEEDS_ROWS_KEY: False,
                ROWPCT_AN_OPTION_KEY: False,
                MEASURES_HORIZ_KEY: True,
                DEFAULT_MEASURE_KEY: None,
                QUICK_IF_BELOW_KEY: 750},
  }
MAX_VAL_LEN_IN_SQL_CLAUSE = 30
COL_CONFIG_ITEM_LBL = _("Column configuration")
# dimension trees
ROWDIM = _("row") #double as labels
COLDIM = _("column")
# actual options selected ...
SORT_VALUE = _(u"By Value") # double as labels
SORT_NONE = _(u"None")
SORT_LBL = _(u"By Label")
SORT_INCREASING = _(u"Increasing")
SORT_DECREASING = _(u"Decreasing")
SORT_NO_OPTS = []
STD_SORT_OPTS = [SORT_VALUE, SORT_LBL, SORT_INCREASING, SORT_DECREASING]
SORT_VAL_AND_LABEL_OPTS = [SORT_VALUE, SORT_LBL]
SHOW_FREQ = _(u"Frequency")
SHOW_PERC = _(u"Percent")
DATA_SHOW_OPTS = [SHOW_FREQ, SHOW_PERC]
# content of constant and constant (ready to include in exported script)
# e.g. "dimtables.%s" "ROWPCT"
script_export_measures_dic = {FREQ: u"FREQ", 
                              ROWPCT: u"ROWPCT",
                              COLPCT: u"COLPCT",
                              SUM: u"SUM", 
                              MEAN: u"MEAN",
                              MEDIAN: u"MEDIAN", 
                              SUMM_N: u"SUMM_N",
                              STD_DEV: u"STD_DEV",
                              MIN: u"MIN",
                              MAX: u"MAX",
                              RANGE: u"RANGE",
                              LOWER_QUARTILE: u"LOWER_QUARTILE",
                              UPPER_QUARTILE: u"UPPER_QUARTILE",
                              IQR: u"IQR",
                              }
# Used to make it easy to slice into html and replace titles and subtitles only.
# Changing the return values of get html functions to get html_pre_title, 
# html_title, html_post_title etc was deemed an even worse approach ;-)
"""
To make it easy to extract individual items out of reports, split by divider, 
    and in each chunk, the text after the item_title_start till the end is the 
    item title we use to name any images we extract from it.
"""
ITEM_TITLE_START = u"<!--ITEM_TITLE_START-->" # put item title immediately after this and before divider
OUTPUT_ITEM_DIVIDER = u"<!--SOFASTATS_ITEM_DIVIDER-->"  # put at end of every item
VISUAL_DIVIDER_BEFORE_THIS = u"<!--VISUAL_DIVIDER_BEFORE_THIS-->"
TBL_TITLE_START = u"<!--_title_start-->"
TBL_TITLE_END = u"<!--_title_end-->"
TBL_SUBTITLE_START = u"<!--_subtitle_start-->"
TBL_SUBTITLE_END = u"<!--_subtitle_end-->"
IMG_SRC_START = u"<img src='"
IMG_SRC_END = u"'>"
PERC_ENCODED_BACKSLASH = u"%5C"
PERC_ENCODED_COLON = u"%3A"
FILE_URL_START_GEN = u"file://"
FILE_URL_START_WIN = u"file:///"
BODY_BACKGROUND_COLOUR = u"#ffffff" # if not white, will have to trim PDFs twice - once with this colour, then with white
BODY_START = u"<body class=\"tundra\">"
DEFAULT_HDR = \
u"""<!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
'http://www.w3.org/TR/html4/loose.dtd'>
<html>
<head>
<meta http-equiv="P3P" content='CP="IDC DSP COR CURa ADMa OUR IND PHY ONL COM 
STA"'>
<meta http-equiv="content-type" content="text/html; charset=utf-8"/>
<title>%%(title)s</title>
%%(dojo_insert)s
<style type="text/css">
<!--
%%(css)s
-->
</style>
</head>
%s\n""" % BODY_START # tundra is for dojo
JS_N_CHARTS_STR = u"var n_charts = "
CSS_FILS_START_TAG = u"<!--css_fils"
N_CHARTS_TAG_START = u"//n_charts_start"
N_CHARTS_TAG_END = u"//n_charts_end"
DOJO_STYLE_START = u"dojo_style_start"
DOJO_STYLE_END = u"dojo_style_end"
# output
# NB never have a class which is the same as the start of another.
# Simple search and replace is worth keeping and requires uniqueness.
CSS_ALIGN_RIGHT = u"right"
CSS_LBL = u"lbl"
CSS_TBL_TITLE = u"tbltitle"
CSS_TBL_TITLE_CELL = u"tblcelltitle"
CSS_TBL_SUBTITLE = u"tblsubtitle"
CSS_FIRST_COL_VAR = u"firstcolvar"
CSS_FIRST_ROW_VAR = u"firstrowvar"
CSS_TOPLINE = u"topline"
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
CSS_FTNOTE = u"ftnote"
CSS_ELEMENTS = [CSS_ALIGN_RIGHT, CSS_LBL, CSS_TBL_TITLE, 
    CSS_TBL_TITLE_CELL, CSS_TBL_SUBTITLE, CSS_FIRST_COL_VAR, CSS_FIRST_ROW_VAR,
    CSS_TOPLINE, CSS_DATACELL, CSS_FIRST_DATACELL, CSS_SPACEHOLDER, CSS_ROW_VAL, 
    CSS_COL_VAL, CSS_ROW_VAR, CSS_COL_VAR, CSS_MEASURE, CSS_TOTAL_ROW, 
    CSS_PAGE_BREAK_BEFORE, CSS_TBL_HDR_FTNOTE]
CSS_SUFFIX_TEMPLATE = u"%s%s"
# projects ******************************************************
EMPTY_PROJ_NAME = _("GIVE ME A NAME ...")
USE_SQLITE_UDFS = False # set to true if unable to open default database -
# probably because system failed to delete tmp table (which requires UDFs to 
# even open).  Delete it and restore this to False. 
SOFA_DB = u"sofa_db"
DEMO_TBL = u"demo_tbl"
PROJ_FIL_RPT = u"fil_report"
PROJ_FIL_CSS = u"fil_css"
PROJ_FIL_VDTS = u"fil_var_dets"
PROJ_FIL_SCRIPT = u"fil_script"

# no unicode keys for 2.6 bug http://bugs.python.org/issue2646
PROJ_CON_DETS = "con_dets"
PROJ_DEFAULT_DBS = "default_dbs"

PROJ_DBE = u"default_dbe"
PROJ_DEFAULT_TBLS = u"default_tbls"
DEFAULT_PROJ = u"default.proj"
DEFAULT_VDTS = u"general_var_dets.vdts"
DEFAULT_STYLE = u"default.css"
DEFAULT_SCRIPT = u"general_scripts.py"
DEFAULT_REPORT = u"default_report.htm"
PROJ_CUSTOMISED_FILE = u"proj_file_customised.txt"
TEST_SCRIPT_EARLIEST = u"sofa_test_earliest.py"
TEST_SCRIPT_POST_CONFIG = u"sofa_test_post_config.py"
VERSION_FILE = u"__version__.txt"
SOFASTATS_CONNECT_FILE = u"next_sofastats_connect.txt"
SOFASTATS_CONNECT_VAR = u"next_sofastats_connect_date"
SOFASTATS_CONNECT_URL = "able_to_connect.txt"
SOFASTATS_CONNECT_INITIAL = 14 # days
SOFASTATS_CONNECT_REGULAR = 56 # days
SOFASTATS_VERSION_CHECK = u"latest_sofastatistics_version.txt"
SOFASTATS_MAJOR_VERSION_CHECK = u"latest_major_sofastatistics_version.txt"
GOOGLE_DOWNLOAD_EXT = u"ods" # csv has trouble with empty cols e.g. 1,2\n3\n4,5
GOOGLE_DOWNLOAD = u"temporary_google_spreadsheet.%s" % GOOGLE_DOWNLOAD_EXT
LINUX = u"linux"
WINDOWS = u"windows"
MAC = u"mac"
platforms = {u"Linux": LINUX, u"Windows": WINDOWS, u"Darwin": MAC}
PLATFORM = platforms.get(platform.system())
INT_FOLDER = u"_internal"
local_encoding = sys.getfilesystemencoding()
HOME_PATH = unicode(os.path.expanduser("~"), local_encoding)
OLD_SOFASTATS_FOLDER = False
if PLATFORM == LINUX: # see https://bugs.launchpad.net/sofastatistics/+bug/952077
    try:
        USER_PATH = Popen(['xdg-user-dir', 'DOCUMENTS'], 
                          stdout=PIPE).communicate()[0].strip()
    except OSError:
        USER_PATH = ""
    USER_PATH = unicode(USER_PATH or os.path.expanduser('~'), local_encoding)
else:
    USER_PATH = HOME_PATH
LOCAL_PATH = os.path.join(USER_PATH, u"sofastats")
RECOVERY_PATH = os.path.join(USER_PATH, u"sofastats_recovery")
REPORTS_FOLDER = u"reports"
PROJS_FOLDER = u"projs"
VDTS_FOLDER = u"vdts"
SCRIPTS_FOLDER = u"scripts"
CSS_FOLDER = u"css"
REPORTS_PATH = os.path.join(LOCAL_PATH, REPORTS_FOLDER)
REPORT_EXTRAS_FOLDER = u"sofastats_report_extras"
REPORT_EXTRAS_PATH = os.path.join(REPORTS_PATH, REPORT_EXTRAS_FOLDER)
SCRIPT_PATH = None # set in config_globals
DEFERRED_ERRORS = [] # show to user immediately a GUI is available
DEFERRED_WARNING_MSGS = [] # show to user once start screen visible
INT_PATH = os.path.join(LOCAL_PATH, INT_FOLDER)
REG_REC = u"registration_records"
REG_PATH = os.path.join(INT_PATH, REG_REC)
PURCHASE_REC = u"purchase_records"
PURCHASED_PATH = os.path.join(INT_PATH, PURCHASE_REC)
USERDETS = u"user_dets"
USERDETS_PATH = os.path.join(INT_PATH, USERDETS)
CONTROL = u"control"
CONTROL_PATH = os.path.join(INT_PATH, CONTROL)
INT_SCRIPT_PATH = os.path.join(INT_PATH, u"script.py")
INT_PREFS_FILE = u"prefs.txt"
INT_REPORT_FILE = u"sofa_use_only_report.htm"
INT_REPORT_PATH = os.path.join(REPORTS_PATH, INT_REPORT_FILE)
CSS_PATH = os.path.join(LOCAL_PATH, CSS_FOLDER)
DEFAULT_CSS_PATH = os.path.join(CSS_PATH, DEFAULT_STYLE)
CURRENT_CONFIG = None
CURRENT_REPORT_PATH = u"current_report_path"
CURRENT_CSS_PATH = u"current_css_path"
CURRENT_VDTS_PATH = u"current_vdts_path"
CURRENT_SCRIPT_PATH = u"current_script_path"
VDT_RET = u"vdt_ret"
SCRIPT_RET = u"script_ret"
VAR_TYPE_CAT = _("Nominal (names only)")
VAR_TYPE_ORD = _("Ordinal (rank only)")
VAR_TYPE_QUANT = _("Quantity (is an amount)")
VAR_TYPES = [VAR_TYPE_CAT, VAR_TYPE_ORD, VAR_TYPE_QUANT]
VAR_TYPE_TO_SHORT = {VAR_TYPE_CAT: _("nominal"), VAR_TYPE_ORD: _("ordinal"), 
                     VAR_TYPE_QUANT: _("quantity")}
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
READONLY_COLOUR = wx.Colour(221,231,229)
NULLED_DOTS = u"dots_converted to null"
CANCEL_IMPORT = u"cancel import"
CANCEL_EXPORT = u"cancel export"
MISSING_VAL_INDICATOR = u"."
RET_CHANGED_DESIGN = 30101966 # must be integer and not 5101 etc
# must be defined before dbe modules called - used in them
GTE_EQUALS = u"="
GTE_NOT_EQUALS = u"not =" # each dbe converts to appropriate SQL operators
GTE_GT = u">"
GTE_LT = u"<"
GTE_GTE = u">="
GTE_LTE = u"<="
GTES = [GTE_EQUALS, GTE_NOT_EQUALS, GTE_GT, GTE_LT, GTE_GTE, GTE_LTE]
DATADETS_OBJ = None # stores settings for the current database and has a cursor 
    # to that database and methods for changing the database. This really 
    # deserves to be a global for the application as it removed a massive amount 
    # of fragile passing around of the object. Ensures that once changed, 
    # everything is consistent across every report, analysis etc until changed 
    # again. Prevented a lots of minor bugs elegantly. A good global :-)
    # Easy enough to mock one for testing. Not used inside scripts which are to 
    # be run headless. Database details are taken from this object and fed into 
    # script which is then run.
DBE_CON = u"dbe_con" # connection resource
DBE_CUR = u"dbe_cur" # cursor resource (tuple-based)
DBE_DBS = u"dbe dbs" # names
DBE_DB = u"dbe_db"# name
DBE_TBLS = u"dbe_tbls" # names
DBE_TBL = u"dbe_tbl" # name
DBE_FLDS = u"dbe_flds" """ Must return dict of dicts called flds.
        The outer dict has fld names as keys and details for that field as the 
        inner dict. Each field dict has as keys the FLD_ variables listed in 
        my_globals e.g. FLD_BOLNUMERIC. Need enough to present fields in order, 
        validate data entry, and guide labelling and reporting (e.g. numeric 
        or categorical)."""
DBE_IDXS = u"dbe_idxs" # dicts - name, is_unique, flds
DBE_HAS_UNIQUE = u"dbe_has_unique" # boolean
# also used as labels in dropdowns
DBE_SQLITE = u"SQLite"
DBE_MYSQL = u"MySQL"
DBE_MS_ACCESS = u"MS Access"
DBE_MS_SQL = u"MS SQL Server"
DBE_PGSQL = u"PostgreSQL"
DBE_CUBRID = u"CUBRID"
MUST_DEL_TMP = False
DBE_PROBLEM = []
DBES = []
DBE_MODULES = {}
DBE_PLUGINS = [(DBE_SQLITE, u"dbe_sqlite"), 
               (DBE_MYSQL, u"dbe_mysql"), 
               (DBE_CUBRID, u"dbe_cubrid"), 
               (DBE_MS_ACCESS, u"dbe_ms_access"), 
               (DBE_MS_SQL, u"dbe_ms_sql"),
               (DBE_PGSQL, u"dbe_postgresql"),
               ]
FLDNAME_START = u"var"
NEXT_FLDNAME_TEMPLATE = FLDNAME_START + u"%03i"
NEXT_VARIANT_FLDNAME_TEMPLATE = u"%s%03i"
# importer
VAL_NUMERIC = u"numeric value"
VAL_DATE = u"datetime value"
VAL_STRING = u"string value"
VAL_EMPTY_STRING = u"empty string value"
HAS_HEADER = 1966 # anything OK as long as no collision with wx.ID_CANCEL
NO_HEADER = 1967
# field type labels - must work as labels as well as consts
FLDTYPE_NUMERIC = _("Numeric")
FLDTYPE_STRING = _("Text")
FLDTYPE_DATE = _("Date")
GEN2SQLITE_DIC = {
    FLDTYPE_NUMERIC: {"sqlite_type": "REAL", 
            "check_clause": ("CHECK(typeof(%(fldname)s) = 'null' "
            "or is_numeric(%(fldname)s))")},
    FLDTYPE_STRING: {"sqlite_type": "TEXT",
            "check_clause": ""},
    FLDTYPE_DATE: {"sqlite_type": "DATETIME", # DATETIME not a native storage 
                #class but can still be discovered via PRAGMA table_info()
            "check_clause": ("CHECK(typeof(%(fldname)s) = 'null' "
            "or is_std_datetime_str(%(fldname)s))")},
    }
RET_NUMERIC = 2010 # anything OK as long as no collision with wx.ID_CANCEL
RET_DATE = 2011
RET_TEXT = 2012
# grids
NEW_IS_DIRTY = u"..."
NEW_IS_READY = u"*"
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
TBL_FLDNAME = u"fldname"
TBL_FLDNAME_ORIG = u"fldname_orig"
TBL_FLDTYPE = u"fldtype"
TBL_FLDTYPE_ORIG = u"fldtype_orig"
TMP_TBLNAME = u"sofa_tmp_tbl"
TMP_TBLNAME2 = u"sofa_tmp_tbl2"
STRICT_TMP_TBL = u"tmp_strict"
SOFA_ID = u"sofa_id"
# demo data
NUM_DATA_SEQ = (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 12.0, 35.0)
# http://statistics.gmu.edu/pages/famous.html and 
# http://www.bobabernethy.com/bios_stats.htm
STR_DATA_SEQ = (u"William&nbsp;Sealey&nbsp;Gosset", u"Karl&nbsp;Pearson", 
                u"Gertrude&nbsp;Mary&nbsp;Cox", u"Ronald&nbsp;A.&nbsp;Fisher", 
                u"Frank&nbsp;Yates", u"Kirstine&nbsp;Smith", u"John&nbsp;Tukey", 
                u"George&nbsp;E.P.&nbsp;Box", u"David&nbsp;R.&nbsp;Cox", 
                u"Jerome&nbsp;H.&nbsp;Friedman", u"Bradley&nbsp;Efron", 
                u"Florence&nbsp;Nightingale&nbsp;David", u"Dorian&nbsp;Shainin",
                u"E.J.&nbsp;Gumbel", u"Jerzy&nbsp;Neyman")
DTM_DATA_SEQ = (u"1&nbsp;Feb&nbsp;2009", u"23&nbsp;Aug&nbsp;1994", 
                u"16&nbsp;Sep&nbsp;2001", u"7&nbsp;Nov&nbsp;1986")
# filters
DBE_TBL_FILTS = {}
# Matplotlib
MPL_FACECOLOR = u"#e95f29"
MPL_EDGECOLOR = u"white"
MPL_BGCOLOR = u"#f2f1f0"
MPL_NORM_LINE_COLOR = u"#736354"
RPT_SUBFOLDER_SUFFIX = u"_images"
rpt_subfolder_prefix = os.path.splitext(INT_REPORT_FILE)[0]
# e.g. /home/g/Documents/sofastats/reports/sofastats_use_only
INT_IMG_PREFIX_PATH = os.path.join(REPORTS_PATH, rpt_subfolder_prefix)
# e.g. /home/g/Documents/sofastats/reports/sofastats_use_only_images/
INT_IMG_PATH = INT_IMG_PREFIX_PATH + RPT_SUBFOLDER_SUFFIX
INT_IMG_ROOT = os.path.join(INT_IMG_PATH, u"_img")
INT_COPY_IMGS_PATH = os.path.join(INT_PATH, u"delete_after_copy")
# date formats
MDY = u"month_day_year"
DMY = u"day_month_year"
YMD = u"year_month_day"
OK_TIME_FORMATS = ["%I%p", "%I:%M%p", "%H:%M", "%H:%M:%S"] # currently no spaces allowed e.g. 4 pm
OK_DATE_FORMATS = None
OK_DATE_FORMAT_EXAMPLES = None
# preferences
PREFS_KEY = u"Prefs"
DEFAULT_LEVEL_KEY = u"default explanation level"
LEVEL_FULL = _(u"Full Explanation")
LEVEL_BRIEF = _(u"Brief Explanation")
LEVEL_RESULTS_ONLY = _(u"Results Only")
LEVELS = (LEVEL_FULL, LEVEL_BRIEF, LEVEL_RESULTS_ONLY)
VERSION_CHECK_KEY = u"version checking level"
VERSION_CHECK_NONE = _(u"No checking")
VERSION_CHECK_MAJOR = _(u"Only report major upgrades")
VERSION_CHECK_ALL = _(u"Report any version upgrades")
VERSION_CHECK_OPTS = [VERSION_CHECK_NONE, VERSION_CHECK_MAJOR, 
                      VERSION_CHECK_ALL]
CHART_VALUES = _("Values")
CHART_DESCRIBED = _("Described")
CHART_BY = _("By")
CHARTS_CHART_BY = _("Charts By")
CHART_SERIES_BY = _("Series By")
CHART_AVERAGED = _("Averaged")
Y_AXIS_FREQ_LBL = _("Frequency")
Y_AXIS_PERC_LBL = _(u"Percentage")
X_AXIS = _(u"X-axis")
Y_AXIS = _(u"Y-axis")
# charts
FLD_MEASURE = u"fld_measure"
FLD_GROUP_BY = u"fld_gp_by"
FLD_GROUP_BY_NAME = u"fld_gp_by_name"
FLD_GROUP_BY_LBLS = u"fld_gp_by_lbls"
FLD_CHART_BY = u"fld_chart_by"
FLD_CHART_BY_NAME = u"fld_chart_by_name"
FLD_CHART_BY_LBLS = u"fld_chart_by_lbls"
# chart gui
SIMPLE_BARCHART = u"Simple Bar Chart"
CLUSTERED_BARCHART = u"Clustered Bar Chart"
PIE_CHART = u"Pie Chart"
LINE_CHART = u"Line Chart"
AREA_CHART = u"Area Chart"
HISTOGRAM = u"Histogram"
SCATTERPLOT = u"Scatterplot"
BOXPLOT = u"Box and Whisker Plot"
"""
For each chart type, we need config for avg (if available) and non-avg.
The config must list drop-down configs in order.
Each config will need: label, min_data_type, inc_select
"""
AVG_KEY = u"avg_key"
NON_AVG_KEY = u"non_avg_key"
LBL_KEY = u"lbl_key"
MIN_DATA_TYPE_KEY = u"min_data_type_key"
INC_SELECT_KEY = u"inc_select_key"
# what role is each dropdown controlling?
VAR_ROLE_KEY = u"var_role_key" # all keys must be usable as variable names
VAR_ROLE_AVG = u"var_role_avg" # the variable being averaged
VAR_ROLE_BIN = u"var_role_bin" # the variable being binned (histogram)
VAR_ROLE_DESC = u"var_role_desc" # the variable being described e.g. Boxplots
VAR_ROLE_CATEGORY = u"var_role_cat" # the var supplying the category - usually x-axis category values
VAR_ROLE_SERIES = u"var_role_series" # if multiple series within a single chart we will have multiple
VAR_ROLE_CHARTS = u"var_role_charts" # the var charts are split by
VAR_ROLE_X_AXIS = u"var_role_x_axis" # for scatterplots
VAR_ROLE_Y_AXIS = u"var_role_y_axis" # for scatterplots
CHART_CONFIG = {
    SIMPLE_BARCHART: {
        AVG_KEY: [
            {LBL_KEY: CHART_AVERAGED,
             MIN_DATA_TYPE_KEY: VAR_TYPE_QUANT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_AVG}, # dropdown 1
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY}, # dropdown 2
            {LBL_KEY: CHARTS_CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS}, # dropdown 3
            ],
        NON_AVG_KEY: [
            {LBL_KEY: CHART_VALUES,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY}, # dropdown 1
            {LBL_KEY: CHARTS_CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS}, # dropdown 2
            ],
    },
    CLUSTERED_BARCHART: {
        AVG_KEY: [
            {LBL_KEY: CHART_AVERAGED,
             MIN_DATA_TYPE_KEY: VAR_TYPE_QUANT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_AVG}, # dropdown 1
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY}, # dropdown 2
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_SERIES}, # dropdown 3
            {LBL_KEY: CHARTS_CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS}, # dropdown 4
            ],
        NON_AVG_KEY: [
            {LBL_KEY: CHART_VALUES,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY}, # dropdown 1
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_SERIES}, # dropdown 2
            {LBL_KEY: CHARTS_CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS}, # dropdown 3
            ],
    },
    PIE_CHART: {
        NON_AVG_KEY: [
            {LBL_KEY: CHART_VALUES,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY}, # dropdown 1
            {LBL_KEY: CHARTS_CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS}, # dropdown 2
            ],
    },
    LINE_CHART: {
        AVG_KEY: [
            {LBL_KEY: CHART_AVERAGED,
             MIN_DATA_TYPE_KEY: VAR_TYPE_QUANT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_AVG}, # dropdown 1
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY}, # dropdown 2
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: True,
             VAR_ROLE_KEY: VAR_ROLE_SERIES}, # dropdown 3
            {LBL_KEY: CHARTS_CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS}, # dropdown 4
            ],
        NON_AVG_KEY: [
            {LBL_KEY: CHART_VALUES,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY}, # dropdown 1
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: True,
             VAR_ROLE_KEY: VAR_ROLE_SERIES}, # dropdown 2
            {LBL_KEY: CHARTS_CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS}, # dropdown 3
            ],
    },
    AREA_CHART: {
        AVG_KEY: [
            {LBL_KEY: CHART_AVERAGED,
             MIN_DATA_TYPE_KEY: VAR_TYPE_QUANT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_AVG}, # dropdown 1
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY}, # dropdown 2
            {LBL_KEY: CHARTS_CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS}, # dropdown 3
            ],
        NON_AVG_KEY: [
            {LBL_KEY: CHART_VALUES,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY}, # dropdown 1
            {LBL_KEY: CHARTS_CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS}, # dropdown 2
            ],
    },
    HISTOGRAM: {
        NON_AVG_KEY: [
            {LBL_KEY: CHART_VALUES,
             MIN_DATA_TYPE_KEY: VAR_TYPE_QUANT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_BIN}, # dropdown 1
            {LBL_KEY: CHARTS_CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS}, # dropdown 2
            ],
    },
    SCATTERPLOT: {
        NON_AVG_KEY: [
            {LBL_KEY: X_AXIS,
             MIN_DATA_TYPE_KEY: VAR_TYPE_QUANT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_X_AXIS}, # dropdown 1
            {LBL_KEY: Y_AXIS,
             MIN_DATA_TYPE_KEY: VAR_TYPE_QUANT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_Y_AXIS}, # dropdown 2
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: True,
             VAR_ROLE_KEY: VAR_ROLE_SERIES}, # dropdown 3
            {LBL_KEY: CHARTS_CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS}, # dropdown 4
            ],
    },
    BOXPLOT: {
        NON_AVG_KEY: [
            {LBL_KEY: CHART_DESCRIBED,
             MIN_DATA_TYPE_KEY: VAR_TYPE_QUANT,
             INC_SELECT_KEY: False,
             VAR_ROLE_KEY: VAR_ROLE_DESC}, # dropdown 1
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: True,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY}, # dropdown 2
            {LBL_KEY: CHART_SERIES_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT,
             INC_SELECT_KEY: True,
             VAR_ROLE_KEY: VAR_ROLE_SERIES}, # dropdown 3
            ],
    },
}
# common format - all have categories, all use get_chart-dets() etc.
GEN_CHARTS = [SIMPLE_BARCHART, CLUSTERED_BARCHART, PIE_CHART, LINE_CHART, 
              AREA_CHART]
EXPECTED_VAR_ROLE_KEYS = [VAR_ROLE_AVG, VAR_ROLE_CATEGORY, VAR_ROLE_SERIES,
                          VAR_ROLE_CHARTS]
DOJO_COLOURS = ['indigo', 'gold', 'hotpink', 'firebrick', 'indianred', 
    'mistyrose', 'darkolivegreen', 'darkseagreen', 'slategrey', 'tomato', 
    'lightcoral', 'orangered', 'navajowhite', 'slategray', 'palegreen', 
    'darkslategrey', 'greenyellow', 'burlywood', 'seashell', 
    'mediumspringgreen', 'mediumorchid', 'papayawhip', 'blanchedalmond', 
    'chartreuse', 'dimgray', 'lemonchiffon', 'peachpuff', 'springgreen',
    'aquamarine', 'orange', 'lightsalmon', 'darkslategray', 'brown', 'ivory', 
    'dodgerblue', 'peru', 'lawngreen', 'chocolate', 'crimson', 'forestgreen', 
    'darkgrey', 'lightseagreen', 'cyan', 'mintcream', 'transparent', 
    'antiquewhite', 'skyblue', 'sienna', 'darkturquoise', 'goldenrod', 
    'darkgreen', 'floralwhite', 'darkviolet', 'darkgray', 'moccasin', 
    'saddlebrown', 'grey', 'darkslateblue', 'lightskyblue', 'lightpink', 
    'mediumvioletred', 'deeppink', 'limegreen', 'darkmagenta', 'palegoldenrod', 
    'plum', 'turquoise', 'lightgoldenrodyellow', 'darkgoldenrod', 'lavender', 
    'slateblue', 'yellowgreen', 'sandybrown', 'thistle', 'violet', 'magenta', 
    'dimgrey', 'tan', 'rosybrown', 'olivedrab', 'pink', 'lightblue', 
    'ghostwhite', 'honeydew', 'cornflowerblue', 'linen', 'darkblue', 
    'powderblue', 'seagreen', 'darkkhaki', 'snow', 'mediumblue', 'royalblue', 
    'lightcyan', 'mediumpurple', 'midnightblue', 'cornsilk', 'paleturquoise', 
    'bisque', 'darkcyan', 'khaki', 'wheat', 'darkorchid', 'deepskyblue', 
    'salmon', 'darkred', 'steelblue', 'palevioletred', 'lightslategray', 
    'aliceblue', 'lightslategrey', 'lightgreen', 'orchid', 'gainsboro', 
    'mediumseagreen', 'lightgray', 'mediumturquoise', 'cadetblue', 
    'lightyellow', 'lavenderblush', 'coral', 'lightgrey', 'whitesmoke', 
    'mediumslateblue', 'darkorange', 'mediumaquamarine', 'darksalmon', 'beige', 
    'blueviolet', 'azure', 'lightsteelblue', 'oldlace']
LBL_LINE_BREAK_JS = """var labelLineBreak = (dojo.isIE) ? "\\n" : "<br>";"""
CHARTS_CHART_DETS = u"chart_dets"
CHARTS_CHART_LBL = u"Chart lbl" # Label for top of chart e.g. Gender: Male
CHARTS_OVERALL_TITLE = u"charts_overall_title" # e.g. Agegroup by Gender
CHARTS_OVERALL_LEGEND_LBL = u"Overall Legend Label" # One per chart
CHARTS_SERIES_LBL_IN_LEGEND = u"Series Label in Legend" # one per series in chart e.g. Male. Goes in legend on bottom
CHART_VAL_MEASURES = u"chart_val_measures" # e.g. freqs or avgs
CHART_MEASURE_DETS = u"measure_dets"
CHARTS_MAX_LBL_LEN = u"max_lbl_len" # all charts share same x labels - we need to know max for chart height is x labels rotated
CHARTS_MAX_LBL_LINES = u"max_lbl_lines"
CHARTS_SERIES_Y_VALS = u"y_vals"
CHARTS_SERIES_TOOLTIPS = u"tooltips"
CHART_NORMAL_Y_VALS = u"normal_y_vals"
CHART_SLICE_DETS = u"slice_dets"
CHARTS_XAXIS_DETS = u"xaxis_dets"
CHARTS_SERIES_DETS = u"series_dets"
CHART_SERIES_LBL = u"series_label"
CHART_MULTICHART = u"multichart"
CHART_BOXDETS = u"boxdets"
CHART_BOXPLOT_WIDTH = 0.15
CHART_BOXPLOT_DISPLAY = u"boxplot_display"
CHART_BOXPLOT_LWHISKER = u"lwhisker"
CHART_BOXPLOT_LBOX = u"lbox"
CHART_BOXPLOT_MEDIAN = u"median"
CHART_BOXPLOT_UBOX = u"ubox"
CHART_BOXPLOT_UWHISKER = u"uwhisker"
CHART_BOXPLOT_OUTLIERS = u"outliers"
CHART_MINVAL = u"minval"
CHART_MAXVAL = u"maxval"
CHART_BIN_LBLS = u"bin_labels"
SAMPLE_A = u"sample_a"
SAMPLE_B = u"sample_b"
LIST_X = u"list_x"
LIST_Y = u"list_y"
DATA_TUPS = u"data_tups"
CHART_FREQS = "chart_freqs"
CHART_AVGS = "chart_avgs"
# remember defaults //////////
# stats tests
STD_DROP_WIDTH = 180
GROUP_BY_DEFAULT = None
VAR_AVG_DEFAULT = None
VAR_1_DEFAULT = None
VAR_2_DEFAULT = None
VAR_3_DEFAULT = None
VAR_4_DEFAULT = None
GROUP_A_DEFAULT = None
GROUP_B_DEFAULT = None
VAL_A_DEFAULT = None
VAL_B_DEFAULT = None
MAX_CHI_DIMS = 6
MIN_CHI_DIMS = 2
MAX_CHI_CELLS = 25
MAX_PIE_SLICES = 30
MAX_CLUSTERS = 50
MAX_CATS_GEN = 100
MAX_CHART_SERIES = 30
MIN_HISTO_VALS = 5
MAX_POINTS_DOJO_SCATTERPLOT = 800 # 800 (use 5000 to demo dojo using demo_tbl)
MAX_SCATTERPLOT_SERIES = 5
MAX_CHARTS_IN_SET = 16
MAX_SERIES_IN_BOXPLOT = 8
MAX_BOXPLOTS_IN_SERIES = 20
MIN_DISPLAY_VALS_FOR_BOXPLOT = 12
JS_WRAPPER_L = u"\n\n<script type=\"text/javascript\">"
JS_WRAPPER_R = u"\n</script>"
REGISTERED = u"registered"
REGEXTS = u"regexts"
PURCHEXTS = u"purchexts"
LOCALPHRASE = u"WSGosset" # must be 8 long exactly
USERNAME = u"username"
DISPLAYNAME = u"displayname"
CONTROLVAR = u"control"

# ////////////////////////////////////////////////////////////
# leaving all this to the end is mainly about avoiding circular import problems
# also about keeping functions to the end so that my_globals is easier to grasp 
# at a glance (basically it just defined things - nothing is run until below)
import config_globals # can rely on everything at least having been defined in
    # my_globals (even as None) before it configures globals
config_globals.set_SCRIPT_PATH()
config_globals.set_ok_date_formats()
config_globals.set_DEFAULT_LEVEL()
config_globals.import_dbe_plugins() # as late as possible because uses local 
    # modules e.g. lib, my_exceptions
LABEL_FONT = None # will be set after wx.App started
BTN_FONT = None
GEN_FONT = None
