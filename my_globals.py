#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import platform
import sys
import wx

# my_globals exists to reduce likelihood of circular imports.
# It doesn't do any local importing at all until the last line, where it imports
# config (used for initial config plus re-config).

debug = False

VERSION = u"1.0.6"
ADVANCED = False
ATTRIBUTION = u"sofastatistics.com"
# LANGUAGE_GALICIAN, LANGUAGE_CROATIAN, LANGUAGE_RUSSIAN, LANGUAGE_HEBREW
# LANGUAGE_BRETON, LANGUAGE_SPANISH
TEST_LANGID = wx.LANGUAGE_CROATIAN
FEEDBACK_LINK = _(u"Give quick feedback on SOFA")
MAIN_SCRIPT_START = u"#sofa_main_script_start"
SCRIPT_END = u"#sofa_script_end"
PYTHON_ENCODING_DECLARATION = u"#! /usr/bin/env python" + os.linesep + \
    u"# -*- coding: utf-8 -*-" + os.linesep
DROP_SELECT = _("Nothing selected")
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
HAS_TOTAL = _("Total") # doubles as display label
FREQS_TBL = 0 # indexes in tab type
CROSSTAB = 1
ROW_SUMM = 2
RAW_DISPLAY = 3
COL_CONFIG_ITEM_LBL = _("Column configuration")
# dimension trees
ROWDIM = _("row") #double as labels
COLDIM = _("column")
# actual options selected ...
SORT_NONE = _(u"None") # double as labels
SORT_LBL = _(u"By Label")
SORT_INCREASING = _(u"Increasing")
SORT_DECREASING = _(u"Decreasing")
SORT_OPTS = [SORT_NONE, SORT_LBL, SORT_INCREASING, SORT_DECREASING]
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
                         }
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
                              }
# Used to make it easy to slice into html and replace titles and subtitles only.
# Changing the return values of get html functions to get html_pre_title, 
# html_title, html_post_title etc was deemed an even worse approach ;-)
TBL_TITLE_START = u"<!--_title_start-->"
TBL_TITLE_END = u"<!--_title_end-->"
TBL_SUBTITLE_START = u"<!--_subtitle_start-->"
TBL_SUBTITLE_END = u"<!--_subtitle_end-->"
def pct_1_dec(num):
    if debug: print(num)
    return "%s%%" % round(num,1)
def pct_2_dec(num):
    return "%s%%" % round(num,2)
data_format_dic = {FREQ: str, ROWPCT: pct_1_dec, COLPCT: pct_1_dec}
DEFAULT_HDR = \
u"""<!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
'http://www.w3.org/TR/html4/loose.dtd'>
<html>
<head>
<meta http-equiv="P3P" content='CP="IDC DSP COR CURa ADMa OUR IND PHY ONL COM 
STA"'>
<meta http-equiv="content-type" content="text/html; charset=utf-8"/>
<title>%(title)s</title>
%(dojo_insert)s
<style type="text/css">
<!--
%(css)s
-->
</style>
</head>
<body class="tundra">\n""" # tundra is for dojo
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
PROJ_FIL_VDTS = u"fil_var_dets"
PROJ_FIL_RPT = u"fil_report"
PROJ_FIL_SCRIPT = u"fil_script"
PROJ_FIL_CSS = u"fil_css"
PROJ_CON_DETS = u"con_dets"
PROJ_DBE = u"default_dbe"
PROJ_DEFAULT_DBS = u"default_dbs"
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
SOFASTATS_VERSION_CHECK = u"latest_sofastats_version.txt"
SOFASTATS_MAJOR_VERSION_CHECK = u"latest_major_sofastats_version.txt"
GOOGLE_DOWNLOAD_EXT = u"ods" # csv has trouble with empty cols e.g. 1,2\n3\n4,5
GOOGLE_DOWNLOAD = u"temporary_google_spreadsheet.%s" % GOOGLE_DOWNLOAD_EXT
INT_FOLDER = u"_internal"
local_encoding = sys.getfilesystemencoding()
USER_PATH = unicode(os.path.expanduser("~"), local_encoding)
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
INT_SCRIPT_PATH = os.path.join(INT_PATH, u"script.py")
INT_REPORT_FILE = u"report.htm"
INT_PREFS_FILE = u"prefs.txt"
INT_REPORT_PATH = os.path.join(INT_PATH, INT_REPORT_FILE)
CSS_PATH = os.path.join(LOCAL_PATH, CSS_FOLDER)
DEFAULT_CSS_PATH = os.path.join(CSS_PATH, DEFAULT_STYLE)
CURRENT_CONFIG = None
CURRENT_REPORT_PATH = u"current_report_path"
CURRENT_CSS_PATH = u"current_css_path"
CURRENT_VDTS_PATH = u"current_vdts_path"
CURRENT_SCRIPT_PATH = u"current_script_path"
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
DATA_DETS = None
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
LINUX = u"linux"
WINDOWS = u"windows"
MAC = u"mac"
platforms = {u"Linux": LINUX, u"Windows": WINDOWS, u"Darwin": MAC}
PLATFORM = platforms.get(platform.system())
MUST_DEL_TMP = False
DBE_PROBLEM = []
DBES = []
DBE_MODULES = {}
DBE_PLUGINS = [(DBE_SQLITE, u"dbe_sqlite"), 
               (DBE_MYSQL, u"dbe_mysql"), 
               (DBE_MS_ACCESS, u"dbe_ms_access"), 
               (DBE_MS_SQL, u"dbe_ms_sql"),
               (DBE_PGSQL, u"dbe_postgresql"),
               ]
FLD_NAME_START = u"var"
NEXT_FLD_NAME_TEMPLATE = FLD_NAME_START + u"%03i"
# importer
VAL_NUMERIC = u"numeric value"
VAL_DATE = u"datetime value"
VAL_STRING = u"string value"
VAL_EMPTY_STRING = u"empty string value"
HAS_HEADER = 1966 # anything OK as long as no collision with wx.ID_CANCEL
NO_HEADER = 1967
# field type labels - must work as labels as well as consts
FLD_TYPE_NUMERIC = _("Numeric")
FLD_TYPE_STRING = _("Text")
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
TBL_FLD_NAME = u"fld_name"
TBL_FLD_NAME_ORIG = u"fld_name_orig"
TBL_FLD_TYPE = u"fld_type"
TBL_FLD_TYPE_ORIG = u"fld_type_orig"
TMP_TBL_NAME = u"sofa_tmp_tbl"
TMP_TBL_NAME2 = u"sofa_tmp_tbl2"
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
INT_IMG_ROOT = os.path.join(INT_PATH, u"_img")
# date formats
MDY = u"month_day_year"
DMY = u"day_month_year"
YMD = u"year_month_day"
OK_TIME_FORMATS = ["%I%p", "%I:%M%p", "%H:%M", "%H:%M:%S"]
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
CHART_CHART_BY = _("Charts By")
CHART_SERIES_BY = _("Series By")
CHART_AVERAGED = _("Averaged")
Y_AXIS_FREQ_LBL = _("Frequency")
# charts
FLD_MEASURE = u"fld_measure"
FLD_GROUP_BY = u"fld_gp_by"
FLD_GROUP_BY_NAME = u"fld_gp_by_name"
FLD_GROUP_BY_LBLS = u"fld_gp_by_lbls"
FLD_CHART_BY = u"fld_chart_by"
FLD_CHART_BY_NAME = u"fld_chart_by_name"
FLD_CHART_BY_LBLS = u"fld_chart_by_lbls"
SIMPLE_BARCHART = u"Simple Bar Chart"
CLUSTERED_BARCHART = u"Clustered Bar Chart"
PIE_CHART = u"Pie Chart"
LINE_CHART = u"Line Chart"
AREA_CHART = u"Area Chart"
HISTOGRAM = u"Histogram"
SCATTERPLOT = u"Scatterplot"
BOXPLOT = u"Box and Whisker Plot"
OPTIONAL_ONE_VAR_CHART_TYPES = [SIMPLE_BARCHART, PIE_CHART, LINE_CHART, 
                                AREA_CHART, HISTOGRAM, BOXPLOT]
CHART_TYPE_TO_MIN_DATA_TYPES = {SIMPLE_BARCHART: (VAR_TYPE_CAT, VAR_TYPE_CAT),
                               CLUSTERED_BARCHART: (VAR_TYPE_CAT, VAR_TYPE_CAT),
                               PIE_CHART: (VAR_TYPE_CAT, VAR_TYPE_CAT),
                               LINE_CHART: (VAR_TYPE_CAT, VAR_TYPE_CAT),
                               AREA_CHART: (VAR_TYPE_CAT, VAR_TYPE_CAT),
                               HISTOGRAM: (VAR_TYPE_QUANT, VAR_TYPE_CAT),
                               SCATTERPLOT: (VAR_TYPE_ORD, VAR_TYPE_ORD),
                               BOXPLOT: (VAR_TYPE_QUANT, VAR_TYPE_CAT),}
CHART_TYPE_TO_LBLS = {SIMPLE_BARCHART: (CHART_VALUES, CHART_CHART_BY, None),
                CLUSTERED_BARCHART: (CHART_VALUES, CHART_BY, CHART_CHART_BY),
                PIE_CHART: (CHART_VALUES, CHART_CHART_BY, None),
                LINE_CHART: (CHART_VALUES, CHART_BY, CHART_CHART_BY),
                AREA_CHART: (CHART_VALUES, CHART_CHART_BY, None),
                HISTOGRAM: (CHART_VALUES, CHART_CHART_BY, None),
                SCATTERPLOT: (_(u"X-axis"), _(u"Y-axis"), CHART_CHART_BY),
                BOXPLOT: (CHART_DESCRIBED, CHART_BY, CHART_SERIES_BY),
                }
THREE_VAR_CHART_TYPES = [SCATTERPLOT, BOXPLOT]
HAS_AVG_OPTION = [SIMPLE_BARCHART, CLUSTERED_BARCHART, LINE_CHART, AREA_CHART,]
NO_CHART_BY = [CLUSTERED_BARCHART, LINE_CHART, BOXPLOT, ]
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
CHART_MAX_CHARTS_IN_SET = 16
CHART_MAX_SERIES_IN_BOXPLOT = 8
CHART_MAX_BOXPLOTS_IN_SERIES = 20
CHART_CHART_BY_LBL = u"chart_by_lbl"
CHART_LBL = u"Chart lbl"
CHART_LEGEND_LBL = u"Legend lbl"
CHART_LBL_SINGLE_CHART = u"Single chart only"
CHART_VAL_MEASURES = u"chart_val_measures" # e.g. freqs or avgs
CHART_MEASURE_DETS = u"measure_dets"
CHART_MAX_LBL_LEN = u"max_lbl_len"
CHART_Y_VALS = u"y_vals"
CHART_NORMAL_Y_VALS = u"normal_y_vals"
CHART_SLICE_DETS = u"slice_dets"
CHART_XAXIS_DETS = u"xaxis_dets"
CHART_SERIES_DETS = u"series_dets"
CHART_SERIES_LBL = u"series_label"
CHART_MULTICHART = u"multichart"
CHART_BOXDETS = u"boxdets"
CHART_BOXPLOT_WIDTH = 0.25
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
MIN_HISTO_VALS = 5
MAX_POINTS_DOJO_SCATTERPLOT = 1000
SAMPLE_A = u"sample_a"
SAMPLE_B = u"sample_b"
LIST_X = u"list_x"
LIST_Y = u"list_y"
DATA_TUPS = u"data_tups"
CHART_FREQS = "chart_freqs"
CHART_AVGS = "chart_avgs"
# remember defaults //////////
# stats tests
GROUP_BY_DEFAULT = None
VAR_AVG_DEFAULT = None
VAR_1_DEFAULT = None
VAR_2_DEFAULT = None
VAR_3_DEFAULT = None
GROUP_A_DEFAULT = None
GROUP_B_DEFAULT = None
VAL_A_DEFAULT = None
VAL_B_DEFAULT = None
MAX_CHI_DIMS = 6
MIN_CHI_DIMS = 2
MAX_CHI_CELLS = 25
MAX_PIE_SLICES = 30
MAX_CHART_SERIES = 30
JS_WRAPPER_L = u"\n\n<script type=\"text/javascript\">"
JS_WRAPPER_R = u"\n</script>"

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
