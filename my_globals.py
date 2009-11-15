from __future__ import print_function
import os
import util # safe to import - never refers to anything in other modules

# my_globals exists to reduce likelihood of circular imports.

debug = False

VERSION = "0.8.12"

SCRIPT_END = "#sofa_script_end"

PYTHON_ENCODING_DECLARATION = u"#! /usr/bin/env python" + os.linesep + \
    u"# -*- coding: utf-8 -*-" + os.linesep

# stats output ******************************************************
OUTPUT_RESULTS_ONLY = "Output results only"

# Making tables ******************************************************
HAS_TOTAL = "Total" #doubles as display label
COL_MEASURES = 0 #indexes in tab type
ROW_SUMM = 1
RAW_DISPLAY = 2
COL_MEASURES_TREE_LBL = "Column measures"
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
SUMM_N = "N" # N used in Summary tables
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
script_export_measures_dic = {FREQ: "FREQ", 
                              ROWPCT: "ROWPCT",
                              COLPCT: "COLPCT",
                              SUM: "SUM", 
                              MEAN: "MEAN",
                              MEDIAN: "MEDIAN", 
                              SUMM_N: "SUMM_N",
                              STD_DEV: "STD_DEV"}
def pct_1_dec(num):
    return "%s%%" % round(num,1)
def pct_2_dec(num):
    return "%s%%" % round(num,2)
data_format_dic = {FREQ: str, ROWPCT: pct_1_dec, COLPCT: pct_1_dec}
# output - NB never have a class which is the same as the start of another
# simple search and replace is worth keeping
CSS_ALIGN_RIGHT = "right"
CSS_LBL = "lbl"
CSS_TBL_TITLE = "tbltitle"
CSS_TBL_TITLE_CELL = "tblcelltitle"
CSS_SUBTITLE = "tblsubtitle"
CSS_FIRST_COL_VAR = "firstcolvar"
CSS_FIRST_ROW_VAR = "firstrowvar"
CSS_DATACELL = "datacell"
CSS_FIRST_DATACELL = "firstdatacell"
CSS_SPACEHOLDER = "spaceholder"
CSS_ROW_VAL = "rowval"
CSS_COL_VAL = "colval"
CSS_ROW_VAR = "rowvar"
CSS_COL_VAR = "colvar"
CSS_MEASURE = "measure"
CSS_TOTAL_ROW = "total-row"
CSS_PAGE_BREAK_BEFORE = "page-break-before"
CSS_ELEMENTS = [CSS_ALIGN_RIGHT, CSS_LBL, CSS_TBL_TITLE, 
                CSS_TBL_TITLE_CELL, CSS_SUBTITLE, CSS_FIRST_COL_VAR, 
                CSS_FIRST_ROW_VAR, CSS_DATACELL, CSS_FIRST_DATACELL, 
                CSS_SPACEHOLDER, CSS_ROW_VAL, CSS_COL_VAL, CSS_ROW_VAR, 
                CSS_COL_VAR, CSS_MEASURE, CSS_TOTAL_ROW, CSS_PAGE_BREAK_BEFORE]
CSS_SUFFIX_TEMPLATE = "%s%s"

# projects ******************************************************
EMPTY_PROJ_NAME = _("GIVE ME A NAME ...")
SOFA_DEFAULT_DB = "SOFA_Default_db"
SOFA_DEFAULT_TBL = "SOFA_Default_tbl"
SOFA_DEFAULT_PROJ = "SOFA_Default_Project.proj"
SOFA_DEFAULT_LBLS = "SOFA_Default_Var_Dets.vdts"
SOFA_DEFAULT_STYLE = "SOFA_Default_Style.css"
SOFA_DEFAULT_SCRIPT = "SOFA_Default_Exported_Table_Scripts.py"
SOFA_DEFAULT_REPORT = "SOFA_Default_New_Tables.htm"
INTERNAL_FOLDER = "_internal"
USER_PATH, LOCAL_PATH = util.get_user_paths()
SCRIPT_PATH = util.get_script_path()
# http://www.velocityreviews.com/forums/t336564-proper-use-of-file.html
INT_SCRIPT_PATH = unicode(os.path.join(LOCAL_PATH, INTERNAL_FOLDER, 
                                       "script.py"), "utf-8")
INT_REPORT_FILE = "report.htm"
INT_REPORT_PATH = unicode(os.path.join(LOCAL_PATH, INTERNAL_FOLDER, 
                                       INT_REPORT_FILE), "utf-8")
DEFAULT_CSS_PATH = unicode(os.path.join(LOCAL_PATH, "css", SOFA_DEFAULT_STYLE), 
                          "utf-8")
VAR_TYPE_CAT = _("Nominal (names only)")
VAR_TYPE_ORD = _("Ordinal (rank only)")
VAR_TYPE_QUANT = _("Quantity (is an amount)")
VAR_TYPES = [VAR_TYPE_CAT, VAR_TYPE_ORD, VAR_TYPE_QUANT]
VAR_IDX_CAT = 0
VAR_IDX_ORD = 1
VAR_IDX_QUANT = 2
# remember defaults in stats tests
group_by_default = None
group_avg_default = None
group_a_default = None
group_b_default = None
val_a_default = None
val_b_default = None
# getdata ******************************************************
# misc field dets
FLD_SEQ = "field sequence"
FLD_BOLNULLABLE = "field nullable"
FLD_DATA_ENTRY_OK = "data entry ok" # e.g. not autonumber, timestamp etc
FLD_COLUMN_DEFAULT = "field default"
# test
FLD_BOLTEXT = "field text"
FLD_TEXT_LENGTH = "field text length"
FLD_CHARSET = "field charset"
# numbers
FLD_BOLNUMERIC = "field numeric"
FLD_BOLAUTONUMBER = "field autonumber"
FLD_DECPTS = "field decpts"
FLD_NUM_WIDTH = "field numeric display width" # used for column display only
FLD_BOL_NUM_SIGNED = "field numeric signed"
FLD_NUM_MIN_VAL = "field numeric minimum value"
FLD_NUM_MAX_VAL = "field numeric maximum value"
# datetime
FLD_BOLDATETIME = "field datetime"
# indexes
IDX_NAME = "index name"
IDX_IS_UNIQUE = "index is unique"
IDX_FLDS = "index fields"
# also used as labels in dropdowns
DBE_SQLITE = "SQLite"
DBE_MYSQL = "MySQL"
DBE_MS_ACCESS = "MS Access"
DBE_MS_SQL = "MS SQL Server"
DBE_PGSQL = "PostgreSQL"

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

DBES = []
DBE_MODULES = {}
DBE_PLUGINS = [(DBE_SQLITE, "dbe_sqlite"), 
               (DBE_MYSQL, "dbe_mysql"), 
               (DBE_MS_ACCESS, "dbe_ms_access"), 
               (DBE_MS_SQL, "dbe_ms_sql"),
               (DBE_PGSQL, "dbe_postgresql"),
               ]
for dbe_plugin, dbe_mod_name in DBE_PLUGINS:
    for_win_yet_not_win = not util.in_windows() and \
        dbe_plugin in [DBE_MS_ACCESS, DBE_MS_SQL]
    dbe_plugin_mod = os.path.join(os.path.dirname(__file__), "dbe_plugins", 
                                   "%s.py" % dbe_mod_name)
    if os.path.exists(dbe_plugin_mod):
        if not for_win_yet_not_win: # i.e. OK to add module
            try:
                dbe_mod = import_dbe_plugin(dbe_plugin)
            except Exception, e:
                if debug: print("Problem adding dbe plugin %s" % dbe_plugin +
                    ". Orig err: %s" % e)
                continue # skip bad module
            DBES.append(dbe_plugin)
            DBE_MODULES[dbe_plugin] = dbe_mod
            
# table config labels
CONF_NUMERIC = _("Numeric")
CONF_STRING = _("String")
CONF_DATE = _("Date")
# grids
# move directions
MOVE_LEFT = "move left"
MOVE_RIGHT = "move right"
MOVE_UP = "move up"
MOVE_DOWN = "move down"
MOVE_UP_RIGHT = "move up right"
MOVE_UP_LEFT = "move up left"
MOVE_DOWN_RIGHT = "move down right"
MOVE_DOWN_LEFT = "move down left"
# cell move types
MOVING_IN_EXISTING = "moving in existing"
MOVING_IN_NEW = "moving in new"
LEAVING_EXISTING = "leaving existing"
LEAVING_NEW = "leaving new"
