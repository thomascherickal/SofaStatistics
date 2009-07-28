import os

import util # safe to import - never refers to anything in other modules

# my_globals exists to reduce likelihood of circular imports.

# stats output ******************************************************
OUTPUT_RESULTS_ONLY = "Output results only"

# Making tables ******************************************************
HAS_TOTAL = "Total" #doubles as display label
COL_MEASURES = 0 #indexes in tab type
ROW_SUMM = 1
RAW_DISPLAY = 2
COL_MEASURES_TREE_LBL = "Column measures"
# dimension trees
ROWDIM = "row" #double as labels
COLDIM = "column"
# actual options selected ...
SORT_NONE = "None" #double as labels
SORT_LABEL = "By Label"
SORT_FREQ_ASC = "By Freq (Asc)"
SORT_FREQ_DESC = "By Freq (Desc)"
# can use content of constant as a short label
FREQ = "Freq"
ROWPCT = "Row %"
COLPCT = "Col %"
SUM = "Sum"
MEAN = "Mean"
MEDIAN = "Median"
SUMM_N = "N" # N used in Summary tables
STD_DEV = "Std Dev"
measures_long_label_dic = {FREQ: "Frequency", 
                           ROWPCT: "Row %",
                           COLPCT: "Column %",
                           SUM: "Sum", 
                           MEAN: "Mean",
                           MEDIAN: "Median", 
                           SUMM_N: "N",
                           STD_DEV: "Standard Deviation"}
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

# output
CSS_ALIGN_RIGHT = "right"
CSS_LBL = "lbl"

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

# projects ******************************************************
EMPTY_PROJ_NAME = "GIVE ME A NAME ..."
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
INT_SCRIPT_PATH = os.path.join(LOCAL_PATH, INTERNAL_FOLDER, "script.py")
INT_REPORT_FILE = "report.htm"
INT_REPORT_PATH = os.path.join(LOCAL_PATH, INTERNAL_FOLDER, INT_REPORT_FILE)
VAR_TYPE_CAT = "Nominal (names only)"
VAR_TYPE_ORD = "Ordinal (rank only)"
VAR_TYPE_QUANT = "Quantity (is an amount)"
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