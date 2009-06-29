# minimise likelihood of circular imports
# stats output
OUTPUT_RESULTS_ONLY = "Output results only"
# Making tables
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