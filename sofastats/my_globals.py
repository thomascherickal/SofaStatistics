import os
from pathlib import Path
import platform
from subprocess import Popen, PIPE
import sys
import wx

"""
Nothing in here should be translated unless it is a label - preferably ending in 
_LBL. This is to ensure headless scripts work and there is no reliance outside 
of the GUI on settings only found when running in the GUI.
"""

## my_globals exists to reduce likelihood of circular imports.
## It doesn't do any local importing at all until the last line, where it
## imports config (used for initial config plus re-config).

debug = False

VERSION = '1.5.0'
ATTRIBUTION = 'sofastatistics.com'
CONTACT = 'grant@sofastatistics.com'
## http://docs.wxwidgets.org/2.9/language_8h.html
"""
LANGUAGE_GALICIAN, LANGUAGE_CROATIAN, LANGUAGE_RUSSIAN, LANGUAGE_HEBREW
LANGUAGE_BRETON, LANGUAGE_SPANISH, LANGUAGE_ENGLISH, LANGUAGE_SPANISH_ARGENTINA
"""
TEST_LANGID = wx.LANGUAGE_FRENCH
DOJO_DEBUG = False  ## so can use unminified javascript and tweak it
LOCALEDIR = './locale'  ## overridden in setup.py
LANGDIR = None  ## overridden in start.py 
CANON_NAME = None  ## overridden in start.py
MAIN_SCRIPT_START = '#sofa_main_script_start'
SCRIPT_END = '#sofa_script_end'
ADD2RPT = False
DROP_SELECT = _('Nothing selected')
ODS_GETTING_LARGE = 10_000_000
XLSX_GETTING_LARGE = 10_000_000
MAX_WIDTH = None  ## set later
MAX_HEIGHT = None
DEFAULT_LEVEL = None
HORIZ_OFFSET = 0
DEFAULT_STATS_DP = 3
DEFAULT_REPORT_DP = 1
REASON_NO_DETAILS = 'Reason no details in stats output'
WILCOXON_DIFF_DETS = 'Wilcoxon diff details'
WILCOXON_RANKING_DETS = (
    'Wilcoxon ranking details - diffs, abs diffs, counter, rankings')
WILCOXON_PLUS_RANKS = 'Wilcoxon plus ranks'
WILCOXON_MINUS_RANKS = 'Wilcoxon minus ranks'
WILCOXON_SUM_PLUS_RANKS = 'Wilcoxon sum of plus ranks'
WILCOXON_SUM_MINUS_RANKS = 'Wilcoxon sum of minus ranks'
WILCOXON_T = 'Wilcoxon T'
WILCOXON_N = 'Wilcoxon N'
MANN_WHITNEY_N_1 = 'Mann-Whitney N sample 1'
MANN_WHITNEY_N_2 = 'Mann-Whitney N sample 2'
MANN_WHITNEY_LABEL_1 = 'Mann-Whitney label 1'
MANN_WHITNEY_LABEL_2 = 'Mann-Whitney label 2'
MANN_WHITNEY_VAL_DETS = 'Mann-Whitney value details'
MANN_WHITNEY_RANKS_1 = 'Mann-Whitney ranks for sample 1'
MANN_WHITNEY_SUM_RANK_1 = 'Mann-Whitney sum ranks for sample 1'
MANN_WHITNEY_U_1 = 'Mann-Whitney U for sample 1'
MANN_WHITNEY_U_2 = 'Mann-Whitney U for sample 2'
MANN_WHITNEY_U = 'Mann-Whitney '
SPEARMANS_INIT_TBL = 'Spearmans initial table'
SPEARMANS_X_RANKED = 'Spearmans sample X sorted vals and ranks'
SPEARMANS_Y_RANKED = 'Spearmans sample Y sorted vals and ranks'
SPEARMANS_N = 'Spearmans N'
SPEARMANS_N_CUBED_MINUS_N = 'Spearmans N cubed minus N'
SPEARMANS_TOT_D_SQUARED = 'Spearmans total diff squared'
SPEARMANS_TOT_D_SQUARED_x_6 = 'Spearmans total diff squared times 6'
SPEARMANS_PRE_RHO = 'Spearmans pre-rho'
SPEARMANS_RHO = 'Spearmans rho'
CHI_GRAND_TOT = 'Chi Square grand total'
CHI_CELLS_DATA = 'Chi Square cells data'
CHI_OBSERVED = 'Chi Square observed'
CHI_ROW_N = 'Chi Square row n'
CHI_COL_N = 'Chi Square column n'
CHI_CELL_ROW_SUM = 'Chi Square cell row sum'  ## sum pertaining to row cell belongs to (shared with all other cells in row)
CHI_CELL_COL_SUM = 'Chi Square cell column sum'
CHI_ROW_SUMS = 'Chi Square row sums'
CHI_ROW_OBS = 'Chi Square row obs items'
CHI_COL_SUMS = 'Chi Square column sums'
CHI_COL_OBS = 'Chi Square column obs items'
CHI_EXPECTED = 'Chi Square expected'
CHI_MAX_OBS_EXP = 'Chi Square max of obs and exp'
CHI_MIN_OBS_EXP = 'Chi Square min of obs and exp'
CHI_DIFF = 'Chi Square diff'
CHI_DIFF_SQU = 'Chi Square diff squared'
CHI_PRE_CHI = 'Chi Square pre-Chi'
CHI_PRE_CHIS = 'Chi Square pre-Chis'  ## list of them
CHI_CHI_SQU = 'Chi Square actual Chi Squared value'
CHI_ROW_N_MINUS_1 = 'Chi Square row N - 1'
CHI_COL_N_MINUS_1 = 'Chi Square column N - 1'
CHI_DF = 'CHI Square degrees of freedom'
# core stats *********************************************************
STATS_DIC_LBL = 'label'
STATS_DIC_N = 'n'
STATS_DIC_MEDIAN = 'median'
STATS_DIC_MEAN = 'mean'
STATS_DIC_SD = 'sd'
STATS_DIC_MIN = 'min'
STATS_DIC_MAX = 'max'
STATS_DIC_CI = 'confidence_interval'
DF = _('Degrees of Freedom (df)')
P_EXPLAN_DIFF = ('If p is small, e.g. less than 0.01, or 0.001, you can assume '
    'the result is statistically significant i.e. there is a difference between'
    ' at least two groups. Note: a statistically significant difference may not'
    ' necessarily be of any practical significance.')
P_EXPLAN_REL = ('If p is small, e.g. less than 0.01, or 0.001, you can assume '
    'the result is statistically significant i.e. there is a relationship. '
    'Note: a statistically significant difference may not necessarily be of '
    'any practical significance.')
OBRIEN_EXPLAN = ('If the value is small, e.g. less than 0.01, or 0.001, you '
    'can assume there is a difference in variance.')
STD_DEV_EXPLAN = ('Standard Deviation measures the spread of values.')
NORMALITY_MEASURE_EXPLAN = ('This provides a single measure of normality. If p'
    ' is small, e.g. less than 0.01, or 0.001, you can assume the distribution'
    ' is not strictly normal. Note - it may be normal enough though.')
KURT_EXPLAN = ('Kurtosis measures the peakedness or flatness of values. '
    ' Between -2 and 2 means kurtosis is unlikely to be a problem. Between -1 '
    'and 1 means kurtosis is quite unlikely to be a problem.')
SKEW_EXPLAN = ('Skew measures the lopsidedness of values. '
    ' Between -2 and 2 means skew is unlikely to be a problem. Between -1 '
    'and 1 means skew is quite unlikely to be a problem.')
CI_EXPLAN = ('There is a 95%% chance the population mean is within the '
    "confidence interval calculated for this sample. Don't forget, of course, "
    'that the population mean could lie well outside the interval bounds. Note'
    ' - many statisticians argue about the best wording for this conclusion.')
# NOTE - GUI consumes labels (so translated strings are needed); script consumes untranslated keys so scripts can run safely headless
# Making tables ******************************************************
FREQ_KEY = 'FREQ_KEY'
ROWPCT_KEY = 'ROWPCT_KEY'
COLPCT_KEY = 'COLPCT_KEY'
SUM_KEY = 'SUM_KEY'
MEAN_KEY = 'MEAN_KEY'
MEDIAN_KEY = 'MEDIAN_KEY'
MODE_KEY = 'MODE_KEY'
SUMM_N_KEY = 'SUMM_N_KEY'
STD_DEV_KEY = 'STD_DEV_KEY'
MIN_KEY = 'MIN_KEY'
MAX_KEY = 'MAX_KEY'
RANGE_KEY = 'RANGE_KEY'
LOWER_QUARTILE_KEY = 'LOWER_QUARTILE_KEY'
UPPER_QUARTILE_KEY = 'UPPER_QUARTILE_KEY'
IQR_KEY = 'IQR_KEY'  ## Inter-Quartile Range
FREQ_LBL = _('Freq')
ROWPCT_LBL = _('Row %')
COLPCT_LBL = _('Col %')
SUM_LBL = _('Sum')
MEAN_LBL = _('Mean')
MEDIAN_LBL = _('Median')
MODE_LBL = _('Mode')
SUMM_N_LBL = 'N'  ## N used in Summary tables
STD_DEV_LBL = _('Std Dev')
MIN_LBL = _('Min')
MAX_LBL = _('Max')
RANGE_LBL = _('Range')
LOWER_QUARTILE_LBL = _('L. Quartile')
UPPER_QUARTILE_LBL = _('U. Quartile')
IQR_LBL = _('IQR')  ## Inter-Quartile Range
NO_CALC_LBL = _("Can't calc")  ## keep as short as possible because appears in table cells

MEASURE_LBLS_SHORT2LONG = {
    FREQ_LBL: _('Frequency'), 
    ROWPCT_LBL: _('Row %'),
    COLPCT_LBL: _('Column %'),
    SUM_LBL: _('Sum'), 
    MEAN_LBL: _('Mean'),
    MEDIAN_LBL: _('Median'),
    MODE_LBL: _('Mode'),
    SUMM_N_LBL: 'N',
    STD_DEV_LBL: _('Standard Deviation'),
    MIN_LBL: _('Minimum'),
    MAX_LBL: _('Maximum'),
    RANGE_LBL: _('Range'),
    LOWER_QUARTILE_LBL: _('Lower Quartile'),
    UPPER_QUARTILE_LBL: _('Upper Quartile'),
    IQR_LBL: _('Inter-Quartile Range'),
}
HAS_TOTAL = _('Total')  ## doubles as display label
FREQS = 0  ## indexes in tab type
CROSSTAB = 1
ROW_STATS = 2
DATA_LIST = 3
FREQS_LBL = _('Frequencies')
CROSSTAB_LBL = _('Crosstabs')
ROW_STATS_LBL = _('Row Stats')
DATA_LIST_LBL = _('Data List')
TAB_TYPE2LBL = {FREQS: FREQS_LBL, CROSSTAB: CROSSTAB_LBL, 
                ROW_STATS: ROW_STATS_LBL, DATA_LIST: DATA_LIST_LBL}
SELECT_ALL_LBL = '  ' + _('Select All') + '  '  ## so wide enough when changed to deselect no matter what the translation
DESELECT_ALL_LBL = _('Deselect All')
MAX_MODES = 10
EMPTY_ROW_LBL = ''
COL_MEASURES_KEY = 'Col measures key'
ROWPCT_AN_OPTION_KEY = 'Rowpct an option? key'
MEASURES_HORIZ_KEY = 'measures_horiz_key'
VAR_SUMMARISED_KEY = 'var_summarised key'
DEFAULT_MEASURE_KEY = 'default_measure_key'
NEEDS_ROWS_KEY = 'needs_row_key'
QUICK_IF_BELOW_KEY = 'quick_live_below_key'  ## safe assumption that we can run
    ## live demo output if table has less than this records
RPT_CONFIG = {
    FREQS: {COL_MEASURES_KEY: [FREQ_LBL, COLPCT_LBL],
        VAR_SUMMARISED_KEY: False,
        NEEDS_ROWS_KEY: True,
        ROWPCT_AN_OPTION_KEY: True,
        MEASURES_HORIZ_KEY: True,
        DEFAULT_MEASURE_KEY: FREQ_LBL,
        QUICK_IF_BELOW_KEY: 1_000 if debug else 5_000},  ## 5000
    CROSSTAB: {COL_MEASURES_KEY: [FREQ_LBL, COLPCT_LBL],
        VAR_SUMMARISED_KEY: False,
        NEEDS_ROWS_KEY: True,
        ROWPCT_AN_OPTION_KEY: True,
        MEASURES_HORIZ_KEY: True,
        DEFAULT_MEASURE_KEY: FREQ_LBL,
        QUICK_IF_BELOW_KEY: 1_000 if debug else 4_000},  ## 4000
    ROW_STATS: {COL_MEASURES_KEY: [MEAN_LBL, STD_DEV_LBL, MEDIAN_LBL, MODE_LBL,
            SUMM_N_LBL, MIN_LBL, MAX_LBL, RANGE_LBL, LOWER_QUARTILE_LBL,
            UPPER_QUARTILE_LBL, IQR_LBL, SUM_LBL],
        VAR_SUMMARISED_KEY: True,
        NEEDS_ROWS_KEY: False,
        ROWPCT_AN_OPTION_KEY: False,
        MEASURES_HORIZ_KEY: False,
        DEFAULT_MEASURE_KEY: MEAN_LBL,
        QUICK_IF_BELOW_KEY: 1_000 if debug else 2_000},  ## 2000
    DATA_LIST: {COL_MEASURES_KEY: [],
        VAR_SUMMARISED_KEY: False,
        NEEDS_ROWS_KEY: False,
        ROWPCT_AN_OPTION_KEY: False,
        MEASURES_HORIZ_KEY: True,
        DEFAULT_MEASURE_KEY: None,
        QUICK_IF_BELOW_KEY: 750},
  }
MAX_CELLS_IN_REPORT_TABLE = 100_000 if debug else 5_000
MAX_VAL_LEN_IN_SQL_CLAUSE = 90
COL_CONFIG_ITEM_LBL = _('Column configuration')
## dimension trees
ROWDIM_KEY = 'ROWDIM_KEY'
COLDIM_KEY = 'COLDIM_KEY'
ROWDIM_LBL = _('row')
COLDIM_LBL = _('column')
DIM_KEY2LBL = {ROWDIM_KEY: ROWDIM_LBL, COLDIM_KEY: COLDIM_LBL}
## actual options selected ...
## never mix translated labels and SOFA arguments - creates major issues when not using GUI but scripts
SORT_VALUE_KEY = 'SORT_VALUE_KEY'
SORT_NONE_KEY = 'SORT_NONE_KEY'
SORT_LBL_KEY = 'SORT_LBL_KEY'
SORT_INCREASING_KEY = 'SORT_INCREASING_KEY'
SORT_DECREASING_KEY = 'SORT_DECREASING_KEY'
SORT_VALUE_LBL = _('By Value')
SORT_NONE_LBL = _('None')
SORT_LBL_LBL = _('By Label')
SORT_INCREASING_LBL = _('Increasing')
SORT_DECREASING_LBL = _('Decreasing')
SORT_NO_OPTS = []
STD_SORT_OPT_LBLS = [
    SORT_VALUE_LBL, SORT_LBL_LBL, SORT_INCREASING_LBL, SORT_DECREASING_LBL]
SORT_VAL_AND_LABEL_OPT_KEYS = [SORT_VALUE_KEY, SORT_LBL_KEY]
SORT_VAL_AND_LABEL_OPT_LBLS = [SORT_VALUE_LBL, SORT_LBL_LBL]
SORT_LBL2KEY = {
    SORT_VALUE_LBL: SORT_VALUE_KEY,
    SORT_NONE_LBL: SORT_NONE_KEY,
    SORT_LBL_LBL: SORT_LBL_KEY,
    SORT_INCREASING_LBL: SORT_INCREASING_KEY,
    SORT_DECREASING_LBL: SORT_DECREASING_KEY}  ## in the GUI we work with drop downs and indexes using labels - only use keys at last step when writing scripts

SHOW_FREQ_KEY = 'SHOW_FREQ_KEY'
SHOW_PERC_KEY = 'SHOW_PERC_KEY'
SHOW_AVG_KEY = 'SHOW_AVG_KEY'
SHOW_SUM_KEY = 'SHOW_SUM_KEY'
SHOW_FREQ_LBL = _('Count')
SHOW_PERC_LBL = _('Percent')
SHOW_AVG_LBL = _('Mean')
SHOW_SUM_LBL = _('Sum')
DATA_SHOW_OPT_LBLS = [SHOW_FREQ_LBL, SHOW_PERC_LBL, SHOW_AVG_LBL, SHOW_SUM_LBL]
DATA_SHOW_KEY2LBL = {
    SHOW_FREQ_KEY: SHOW_FREQ_LBL,
    SHOW_PERC_KEY: SHOW_PERC_LBL, 
    SHOW_AVG_KEY: SHOW_AVG_LBL,
    SHOW_SUM_KEY: SHOW_SUM_LBL}
DATA_SHOW_LBL2KEY = dict([(val, key) for key, val in DATA_SHOW_KEY2LBL.items()])
AGGREGATE_DATA_SHOW_OPT_KEYS = [SHOW_AVG_KEY, SHOW_SUM_KEY]
AGGREGATE_DATA_SHOW_OPT_LBLS = [SHOW_AVG_LBL, SHOW_SUM_LBL]

## content of constant and constant (ready to include in exported script)
## e.g. 'dimtables.%s' 'ROWPCT'
MEASURE_LBL2KEY = {
    FREQ_LBL: FREQ_KEY,
    ROWPCT_LBL: ROWPCT_KEY,
    COLPCT_LBL: COLPCT_KEY,
    SUM_LBL: SUM_KEY,
    MEAN_LBL: MEAN_KEY,
    MEDIAN_LBL: MEDIAN_KEY,
    MODE_LBL: MODE_KEY,
    SUMM_N_LBL: SUMM_N_KEY,
    STD_DEV_LBL: STD_DEV_KEY,
    MIN_LBL: MIN_KEY,
    MAX_LBL: MAX_KEY,
    RANGE_LBL: RANGE_KEY,
    LOWER_QUARTILE_LBL: LOWER_QUARTILE_KEY,
    UPPER_QUARTILE_LBL: UPPER_QUARTILE_KEY,
    IQR_LBL: IQR_KEY,
}
MEASURE_KEY2LBL = dict([(val, key) for key, val in MEASURE_LBL2KEY.items()])
GROUPING_PLACEHOLDER = 1
## Used to make it easy to slice into html and replace titles and subtitles only.
## Changing the return values of get html functions to get html_pre_title, 
## html_title, html_post_title etc was deemed an even worse approach ;-)
"""
To make it easy to extract individual items out of reports, split by divider,
and in each chunk, split by title divider. The text after the item_title_start
till the end is the item title we use to name any images we extract from the
first half of the chunk. E.g.

SOFASTATS_ITEM_DIVIDER-->
    <div class=screen-float-only style='margin-right: 10px;
    margin-top: 0; page-break-after: always;'>
        <p><b>Gender: Female</b></p>Japan: Slope: 0.195; Intercept: 58.308<br>
        Italy: Slope: 0.625; Intercept: 37.838<br>
        Germany: Slope: 0.398; Intercept: 47.824<br>
        <img src='default_report_images/076.png'>
    </div>
<!--ITEM_TITLE_START--><!--Scatterplot_Age vs Post-diet Weight By Country B_Gender: Female-->
<!--SOFASTATS_ITEM_DIVIDER-->
"""
ITEM_TITLE_START = '<!-- _ITEM_TITLE_START -->'  ## put item title immediately after this and before divider
OUTPUT_ITEM_DIVIDER = '<!-- _SOFASTATS_ITEM_DIVIDER -->'  ## put at end of every item
VISUAL_DIVIDER_BEFORE_THIS = '<!-- _VISUAL_DIVIDER_BEFORE_THIS -->'
REPORT_TABLE_START = '<!-- _REPORT_TABLE_START -->'
REPORT_TABLE_END = '<!--_REPORT_TABLE_END -->'
TBL_TITLE_START = '<!-- _TBL_TITLE_START -->'
TBL_TITLE_END = '<!-- _TBL_TITLE_END -->'
TBL_SUBTITLE_START = '<!-- _TBL_SUBTITLE_START -->'
TBL_SUBTITLE_END = '<!-- _TBL_SUBTITLE_END -->'
IMG_SRC_START = "<IMG src='"
IMG_SRC_END = "'>"
PERC_ENCODED_BACKSLASH = '%5C'
PERC_ENCODED_COLON = '%3A'
FILE_URL_START_GEN = 'file://'
FILE_URL_START_WIN = 'file:///'
BODY_BACKGROUND_COLOUR = '#ffffff'  ## if not white, will have to trim PDFs twice - once with this colour, then with white
BODY_START = '<body class="tundra">'
DEFAULT_HDR = """\
<!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
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
%s\n""" % BODY_START  ## tundra is for dojo
JS_N_CHARTS_STR = 'var n_charts = '
CSS_FILS_START_TAG = '<!--css_fils'
N_CHARTS_TAG_START = '//n_charts_start'
N_CHARTS_TAG_END = '//n_charts_end'
DOJO_STYLE_START = 'dojo_style_start'
DOJO_STYLE_END = 'dojo_style_end'
## output
## NB never have a class which is the same as the start of another.
## Simple search and replace is worth keeping and requires uniqueness.
CSS_ALIGN_RIGHT = 'right'
CSS_LBL = 'lbl'
CSS_TBL_TITLE = 'tbltitle'
CSS_TBL_TITLE_CELL = 'tblcelltitle'
CSS_TBL_SUBTITLE = 'tblsubtitle'
CSS_FIRST_COL_VAR = 'firstcolvar'
CSS_FIRST_ROW_VAR = 'firstrowvar'
CSS_SUBTABLE = 'subtable'
CSS_TOPLINE = 'topline'
CSS_DATACELL = 'datacell'
CSS_FIRST_DATACELL = 'firstdatacell'
CSS_SPACEHOLDER = 'spaceholder'
CSS_ROW_VAL = 'rowval'
CSS_COL_VAL = 'colval'
CSS_ROW_VAR = 'rowvar'
CSS_COL_VAR = 'colvar'
CSS_MEASURE = 'measure'
CSS_TOTAL_ROW = 'total-row'
CSS_PAGE_BREAK_BEFORE = 'page-break-before'
CSS_TBL_HDR_FTNOTE = 'tbl-header-ftnote'
CSS_FTNOTE = 'ftnote'
CSS_ELEMENTS = [CSS_ALIGN_RIGHT, CSS_LBL, CSS_TBL_TITLE,
    CSS_TBL_TITLE_CELL, CSS_TBL_SUBTITLE, CSS_FIRST_COL_VAR, CSS_FIRST_ROW_VAR,
    CSS_SUBTABLE, CSS_TOPLINE, CSS_DATACELL, CSS_FIRST_DATACELL,
    CSS_SPACEHOLDER, CSS_ROW_VAL, CSS_COL_VAL, CSS_ROW_VAR, CSS_COL_VAR,
    CSS_MEASURE, CSS_TOTAL_ROW, CSS_PAGE_BREAK_BEFORE, CSS_TBL_HDR_FTNOTE]
CSS_SUFFIX_TEMPLATE = '%s%s'
# projects ******************************************************
EMPTY_PROJ_NAME = _('GIVE ME A NAME ...')
USE_SQLITE_UDFS = False  ## set to true if unable to open default database -
## probably because system failed to delete tmp table (which requires UDFs to
## even open).  Delete it and restore this to False.
SOFA_DB = 'sofa_db'
DEMO_TBL = 'demo_tbl'
PROJ_FIL_RPT = 'fil_report'
PROJ_FIL_CSS = 'fil_css'
PROJ_FIL_VDTS = 'fil_var_dets'
PROJ_FIL_SCRIPT = 'fil_script'
PROJ_CON_DETS = 'con_dets'
PROJ_DEFAULT_DBS = 'default_dbs'
PROJ_EXT = '.proj'
PROJ_DBE = 'default_dbe'
PROJ_DEFAULT_TBLS = 'default_tbls'
DEFAULT_PROJ = 'default.proj'
OPEN_ON_START_KEY = 'open_on_start'
OPEN_ON_START = False
DEFAULT_VDTS = 'general_var_dets.vdts'
DEFAULT_STYLE = 'default.css'
DEFAULT_SCRIPT = 'general_scripts.py'
DEFAULT_REPORT = 'default_report.htm'
PROJ_CUSTOMISED_FILE = 'proj_file_customised.txt'
TEST_SCRIPT_EARLIEST = 'sofa_test_earliest.py'
TEST_SCRIPT_POST_CONFIG = 'sofa_test_post_config.py'
VERSION_FILE = '__version__.txt'
SOFASTATS_CONNECT_FILE = 'next_sofastats_connect.txt'
SOFASTATS_CONNECT_VAR = 'next_sofastats_connect_date'
SOFASTATS_CONNECT_URL = 'able_to_connect.txt'
SOFASTATS_CONNECT_INITIAL = 14  ## days
SOFASTATS_CONNECT_REGULAR = 56  ## days
SOFASTATS_VERSION_CHECK = 'latest_sofastatistics_version.txt'
SOFASTATS_MAJOR_VERSION_CHECK = 'latest_major_sofastatistics_version.txt'
GOOGLE_DOWNLOAD_EXT = 'ods'  ## csv has trouble with empty cols e.g. 1,2\n3\n4,5
GOOGLE_DOWNLOAD = f'temporary_google_spreadsheet.{GOOGLE_DOWNLOAD_EXT}'
LINUX = 'linux'
WINDOWS = 'windows'
MAC = 'mac'
platforms = {'Linux': LINUX, 'Windows': WINDOWS, 'Darwin': MAC}
PLATFORM = platforms.get(platform.system())
INT_FOLDER = '_internal'
local_encoding = sys.getfilesystemencoding()
HOME_PATH = Path(os.path.expanduser('~'))
OLD_SOFASTATS_FOLDER = False
if PLATFORM == LINUX:  ## see https://bugs.launchpad.net/sofastatistics/+bug/952077
    try:
        USER_PATH = Path(str(Popen(['xdg-user-dir', 'DOCUMENTS'],
            stdout=PIPE).communicate()[0], encoding='utf-8').strip())  ## get output i.e. [0]. err is 2nd.
    except OSError:
        USER_PATH = None
    USER_PATH = USER_PATH or HOME_PATH
else:
    USER_PATH = HOME_PATH
## USER_PATH = '/path/to/new/root/for/sofastats/and/sofastats_recovery/folders' # can override but make sure the new folder doesn't exist yet - let SOFA make and populate it. Only then override anything you want to override.
LOCAL_PATH = USER_PATH / 'sofastats'
RECOVERY_PATH = USER_PATH / 'sofastats_recovery'
REPORTS_FOLDER = Path('reports')
PROJS_FOLDER = Path('projs')
VDTS_FOLDER = Path('vdts')
SCRIPTS_FOLDER = Path('scripts')
CSS_FOLDER = Path('css')
REPORTS_PATH = LOCAL_PATH / REPORTS_FOLDER
if PLATFORM == WINDOWS:
    BASE_URL = f'file://{REPORTS_PATH}'
else:
    BASE_URL = f'file://{REPORTS_PATH}'
REPORT_EXTRAS_FOLDER = 'sofastats_report_extras'
REPORT_EXTRAS_PATH = REPORTS_PATH / REPORT_EXTRAS_FOLDER
SCRIPT_PATH = None  ## set in config_globals
DEFERRED_ERRORS = []  ## show to user immediately a GUI is available
DEFERRED_WARNING_MSGS = []  ## show to user once start screen visible
INT_PATH = LOCAL_PATH / INT_FOLDER
INT_SCRIPT_PATH = INT_PATH / 'script.py'
INT_PREFS_FILE = 'prefs.txt'
INT_REPORT_FILE = 'sofa_use_only_report.htm'
INT_REPORT_PATH = REPORTS_PATH / INT_REPORT_FILE
CSS_PATH = LOCAL_PATH / CSS_FOLDER
DEFAULT_CSS_PATH = CSS_PATH / DEFAULT_STYLE
CURRENT_CONFIG = None
CURRENT_REPORT_PATH = 'current_report_path'
CURRENT_CSS_PATH = 'current_css_path'
CURRENT_VDTS_PATH = 'current_vdts_path'
CURRENT_SCRIPT_PATH = 'current_script_path'
VDT_RET = 'vdt_ret'
SCRIPT_RET = 'script_ret'
VAR_TYPE_CAT_KEY = 'VAR_TYPE_CAT_KEY'
VAR_TYPE_ORD_KEY = 'VAR_TYPE_ORD_KEY'
VAR_TYPE_QUANT_KEY = 'VAR_TYPE_QUANT_KEY'
VAR_TYPE_CAT_LBL = _('Nominal (names only)')
VAR_TYPE_ORD_LBL = _('Ordinal (rank only)')
VAR_TYPE_QUANT_LBL = _('Quantity (is an amount)')
VAR_TYPE_KEYS = [VAR_TYPE_CAT_KEY, VAR_TYPE_ORD_KEY, VAR_TYPE_QUANT_KEY]
VAR_TYPE_LBLS = [VAR_TYPE_CAT_LBL, VAR_TYPE_ORD_LBL, VAR_TYPE_QUANT_LBL]
VAR_TYPE_LBL2KEY = {
    VAR_TYPE_CAT_LBL: VAR_TYPE_CAT_KEY,
    VAR_TYPE_ORD_LBL: VAR_TYPE_ORD_KEY,
    VAR_TYPE_QUANT_LBL: VAR_TYPE_QUANT_KEY,
}
VAR_TYPE_KEY2LBL = dict([(val, key) for key, val in VAR_TYPE_LBL2KEY.items()])
VAR_TYPE_KEY2_SHORT_LBL = {
    VAR_TYPE_CAT_KEY: _('nominal'),
    VAR_TYPE_ORD_KEY: _('ordinal'),
    VAR_TYPE_QUANT_KEY: _('quantity')}
VAR_IDX_CAT = 0
VAR_IDX_ORD = 1
VAR_IDX_QUANT = 2
## getdata ******************************************************
## misc field dets
FLD_SEQ = 'field sequence'
FLD_BOLNULLABLE = 'field nullable'
FLD_DATA_ENTRY_OK = 'data entry ok'  ## e.g. not autonumber, timestamp etc
FLD_COLUMN_DEFAULT = 'field default'
## test
FLD_BOLTEXT = 'field text'
FLD_TEXT_LENGTH = 'field text length'
FLD_CHARSET = 'field charset'
## numbers
FLD_BOLNUMERIC = 'field numeric'
FLD_BOLAUTONUMBER = 'field autonumber'
FLD_DECPTS = 'field decpts'
FLD_NUM_WIDTH = 'field numeric display width'  ## used for column display only
FLD_BOL_NUM_SIGNED = 'field numeric signed'
FLD_NUM_MIN_VAL = 'field numeric minimum value'
FLD_NUM_MAX_VAL = 'field numeric maximum value'
## datetime
FLD_BOLDATETIME = 'field datetime'
## indexes
IDX_NAME = 'index name'
IDX_IS_UNIQUE = 'index is unique'
IDX_FLDS = 'index fields'
## misc data
READ_ONLY_COLOUR = wx.Colour(221,231,229)
NULLED_DOTS_KEY = 'dots_converted to null'
CANCEL_IMPORT = 'cancel import'
CANCEL_EXPORT = 'cancel export'
MISSING_VAL_INDICATOR = '.'
RET_CHANGED_DESIGN = 30101966  ## must be integer and not 5101 etc
## must be defined before dbe modules called - used in them
GTE_EQUALS = '='
GTE_NOT_EQUALS = 'not ='  ## each dbe converts to appropriate SQL operators
GTE_GT = '>'
GTE_LT = '<'
GTE_GTE = '>='
GTE_LTE = '<='
GTES = [GTE_EQUALS, GTE_NOT_EQUALS, GTE_GT, GTE_LT, GTE_GTE, GTE_LTE]
DATADETS_OBJ = None  ## stores settings for the current database and has a
## cursor to that database and methods for changing the database. This really
## deserves to be a global for the application as it removed a massive amount of
## fragile passing around of the object. Ensures that once changed, everything
## is consistent across every report, analysis etc until changed again.
## Prevented a lots of minor bugs elegantly. A good global :-). Easy enough to
## mock one for testing. Not used inside scripts which are to be run headless.
## Database details are taken from this object and fed into script which is then
## run.
DBE_CON = 'dbe_con'  ## connection resource
DBE_CUR = 'dbe_cur'  ## cursor resource (tuple-based)
DBE_DBS = 'dbe dbs'  ## names
DBE_DB = 'dbe_db'  ## name
DBE_TBLS = 'dbe_tbls'  ## names
DBE_TBL = 'dbe_tbl'  ## name
DBE_FLDS = 'dbe_flds'
## Must return dict of dicts called flds. The outer dict has fld names as keys
## and details for that field as the inner dict. Each field dict has as keys the
## FLD_ variables listed in my_globals e.g. FLD_BOLNUMERIC. Need enough to
## present fields in order, validate data entry, and guide labelling and
## reporting (e.g. numeric or categorical).
DBE_IDXS = 'dbe_idxs'  ## dicts - name, is_unique, flds
DBE_HAS_UNIQUE = 'dbe_has_unique'  ## boolean
## also used as labels in dropdowns
DBE_SQLITE = 'SQLite'
DBE_MYSQL = 'MySQL'
DBE_MS_ACCESS = 'MS Access'
DBE_MS_SQL = 'MS SQL Server'
DBE_PGSQL = 'PostgreSQL'
DBE_CUBRID = 'CUBRID'
DBE_KEY2KEY_AS_STR = {  ## Too late to split into keys and labels - all over users' existing proj files
    DBE_SQLITE: 'DBE_SQLITE',
    DBE_MYSQL: 'DBE_MYSQL',
    DBE_MS_ACCESS: 'DBE_MS_ACCESS',
    DBE_MS_SQL: 'DBE_MS_SQL',
    DBE_PGSQL: 'DBE_PGSQL',
    DBE_CUBRID: 'DBE_CUBRID',
}
MUST_DEL_TMP = False
DBE_PROBLEM = []
DBES = []
DBE_MODULES = {}
DBE_PLUGINS = [
    (DBE_SQLITE, 'dbe_sqlite'),
    (DBE_MYSQL, 'dbe_mysql'),
    (DBE_CUBRID, 'dbe_cubrid'),
    (DBE_MS_ACCESS, 'dbe_ms_access'),
    (DBE_MS_SQL, 'dbe_ms_sql'),
    (DBE_PGSQL, 'dbe_postgresql'),
]
FLDNAME_START = 'var'
FLDNAME_ZFILL = 3
NEXT_FLDNAME_TEMPLATE = FLDNAME_START + '%%0%si' % FLDNAME_ZFILL
NEXT_VARIANT_FLDNAME_TEMPLATE = '%%s%%0%si' % FLDNAME_ZFILL
## importer
VAL_NUMERIC = 'numeric value'
VAL_DATE = 'datetime value'
VAL_STRING = 'string value'
VAL_EMPTY_STRING = 'empty string value'
HAS_HEADER = 1966  ## anything OK as long as no collision with wx.ID_CANCEL
NO_HEADER = 1967
## field type labels - must work as labels as well as consts
FLDTYPE_NUMERIC_KEY = 'FLDTYPE_NUMERIC'
FLDTYPE_STRING_KEY = 'FLDTYPE_STRING'
FLDTYPE_DATE_KEY = 'FLDTYPE_DATE'
FLDTYPE_NUMERIC_LBL = _('Numeric')
FLDTYPE_STRING_LBL = _('Text')
FLDTYPE_DATE_LBL = _('Date')
FLDTYPE_LBL2KEY = {
    FLDTYPE_NUMERIC_LBL: FLDTYPE_NUMERIC_KEY,
    FLDTYPE_STRING_LBL: FLDTYPE_STRING_KEY,
    FLDTYPE_DATE_LBL: FLDTYPE_DATE_KEY,
}
FLDTYPE_KEY2LBL = dict([(val, key) for key, val in FLDTYPE_LBL2KEY.items()])
GEN2SQLITE_DIC = {
    FLDTYPE_NUMERIC_KEY: {
        'sqlite_type': 'REAL', 
        'check_clause': (
            "CHECK(typeof(%(fldname)s) = 'null' OR is_numeric(%(fldname)s))")},
    FLDTYPE_STRING_KEY: {
        'sqlite_type': 'TEXT',
        'check_clause': ''},
    FLDTYPE_DATE_KEY: {
        'sqlite_type': 'DATETIME',  ## DATETIME not a native storage class but can still be discovered via PRAGMA table_info()
        'check_clause': (
            "CHECK(typeof(%(fldname)s) = 'null' "
            "OR is_std_datetime_str(%(fldname)s))")},
    }
RET_NUMERIC = 2010  ## anything OK as long as no collision with wx.ID_CANCEL
RET_DATE = 2011
RET_TEXT = 2012
## grids
NEW_IS_DIRTY = '...'
NEW_IS_READY = '*'
## move directions
MOVE_LEFT = 'move left'
MOVE_RIGHT = 'move right'
MOVE_UP = 'move up'
MOVE_DOWN = 'move down'
MOVE_UP_RIGHT = 'move up right'
MOVE_UP_LEFT = 'move up left'
MOVE_DOWN_RIGHT = 'move down right'
MOVE_DOWN_LEFT = 'move down left'
## cell move types
MOVING_IN_EXISTING = 'moving in existing'
MOVING_IN_NEW = 'moving in new'
LEAVING_EXISTING = 'leaving existing'
LEAVING_NEW = 'leaving new'
## table details
TBL_FLDNAME = 'fldname'
TBL_FLDNAME_ORIG = 'fldname_orig'
TBL_FLDTYPE = 'fldtype'
TBL_FLDTYPE_ORIG = 'fldtype_orig'
TMP_TBLNAME = 'sofa_tmp_tbl'
TMP_TBLNAME2 = 'sofa_tmp_tbl2'
STRICT_TMP_TBL = 'tmp_strict'
SOFA_ID = 'sofa_id'
WAS_SOFA_ID = f'was_{SOFA_ID}'
## demo data
NUM_DATA_SEQ = (
    1.514521, 1.235465, 2.0343, 2.588537, 3.006060, 3.502365, 12.1010101, 35.0990)
## http://statistics.gmu.edu/pages/famous.html and 
## http://www.bobabernethy.com/bios_stats.htm
STR_DATA_SEQ = (
    'William&nbsp;Sealey&nbsp;Gosset', 'Karl&nbsp;Pearson',
    'Gertrude&nbsp;Mary&nbsp;Cox', 'Ronald&nbsp;A.&nbsp;Fisher',
    'Frank&nbsp;Yates', 'Kirstine&nbsp;Smith', 'John&nbsp;Tukey',
    'George&nbsp;E.P.&nbsp;Box', 'David&nbsp;R.&nbsp;Cox',
    'Jerome&nbsp;H.&nbsp;Friedman', 'Bradley&nbsp;Efron', 
    'Florence&nbsp;Nightingale&nbsp;David', 'Dorian&nbsp;Shainin',
    'E.J.&nbsp;Gumbel', 'Jerzy&nbsp;Neyman')
DTM_DATA_SEQ = (
    '1&nbsp;Feb&nbsp;2009',
    '23&nbsp;Aug&nbsp;1994', 
    '16&nbsp;Sep&nbsp;2001',
    '7&nbsp;Nov&nbsp;1986',
)
## filters
DBE_TBL_FILTS = {}
## Matplotlib
MPL_FACECOLOR = '#e95f29'
MPL_EDGECOLOR = 'white'
MPL_BGCOLOR = '#f2f1f0'
MPL_NORM_LINE_COLOR = '#736354'
RPT_SUBFOLDER_SUFFIX = '_images'
rpt_subfolder_prefix = Path(INT_REPORT_FILE).stem  ## e.g. /home/g/Documents/sofastats/reports/sofastats_use_only
INT_IMG_PREFIX_PATH = REPORTS_PATH / rpt_subfolder_prefix  ## e.g. /home/g/Documents/sofastats/reports/sofastats_use_only_images/
INT_IMG_PATH = REPORTS_PATH / f'{rpt_subfolder_prefix}{RPT_SUBFOLDER_SUFFIX}'
INT_IMG_ROOT = REPORTS_PATH / f'{rpt_subfolder_prefix}{RPT_SUBFOLDER_SUFFIX}_img'
INT_COPY_IMGS_PATH = INT_PATH / 'delete_after_copy'
## date formats
MDY = 'month_day_year'
DMY = 'day_month_year'
YMD = 'year_month_day'
OK_TIME_FORMATS = ['%I%p', '%I:%M%p', '%H:%M', '%H:%M:%S']  ## currently no spaces allowed e.g. 4 pm
OK_DATE_FORMATS = None
OK_DATE_FORMAT_EXAMPLES = None
## preferences
PREFS_KEY = 'Prefs'
PREFS_DEFAULT_DETAILS_KEY = 'OUTPUT_DETAILS'
DEFAULT_DETAILS = False  ## gets reset by prefs being read during config_globals.set_DEFAULT_DETAILS()
## Charts
CHART_VALUES_LBL = _('Values')
CHART_DESCRIBED_LBL = _('Described')

CHART_BY = _('By')
CHARTS_CHART_BY_LBL = _('Charts By')
CHART_SERIES_BY_LBL = _('Series By')
CHART_AVERAGED_LBL = _('Averaged')
CHART_SUMMED_LBL = _('Summed')
CHART_DATETIMES_LBL = _('Dates/\nTimes')
DATA_SHOW2_LBL_KEY = {
    SHOW_AVG_LBL: CHART_AVERAGED_LBL,
    SHOW_SUM_LBL: CHART_SUMMED_LBL}
Y_AXIS_FREQ_LBL = _('Frequency')
Y_AXIS_PERC_LBL = _('Percentage')
X_AXIS_LBL = _('X-axis')
Y_AXIS_LBL = _('Y-axis')
## charts
FLD_MEASURE = 'fld_measure'
FLD_GROUP_BY = 'fld_gp_by'
FLD_GROUP_BY_NAME = 'fld_gp_by_name'
FLD_GROUP_BY_LBLS = 'fld_gp_by_lbls'
FLD_CHART_BY = 'fld_chart_by'
FLD_CHART_BY_NAME = 'fld_chart_by_name'
FLD_CHART_BY_LBLS = 'fld_chart_by_lbls'
## chart gui
MAX_DISPLAY_DP = 20
SIMPLE_BARCHART = 'Simple Bar Chart'
CLUSTERED_BARCHART = 'Clustered Bar Chart'
PIE_CHART = 'Pie Chart'
LINE_CHART = 'Line Chart'
AREA_CHART = 'Area Chart'
HISTOGRAM = 'Histogram'
SCATTERPLOT = 'Scatterplot'
BOXPLOT = 'Box and Whisker Plot'

BOX_DIC = 'box_dic'
BOX_N_VALS = 'box_n_vals'

"""
For each chart type, we need config for avg (if available) and non-avg.
The config must list drop-down configs in order.
Each config will need: label, min_data_type, inc_select
"""
AGGREGATE_KEY = 'aggregate_key'
INDIV_VAL_KEY = 'indiv_val_key'
LBL_KEY = 'lbl_key'
MIN_DATA_TYPE_KEY = 'min_data_type_key'
EMPTY_VAL_OK = 'empty_val_ok'
## what role is each dropdown controlling?
VAR_ROLE_KEY = 'key'  ## all keys must be usable as variable names
VAR_ROLE_AGG = 'agg'  ## the variable being aggregated
VAR_ROLE_BIN = 'bin'  ## the variable being binned (histogram)
VAR_ROLE_DESC = 'desc'  ## the variable being described e.g. Boxplots
VAR_ROLE_CATEGORY = 'cat'  ## the var supplying the category - usually x-axis category values
VAR_ROLE_SERIES = 'series'  ## if multiple series within a single chart we will have multiple
VAR_ROLE_CHARTS = 'charts'  ## the var charts are split by
VAR_ROLE_X_AXIS = 'x_axis'  ## for scatterplots
VAR_ROLE_Y_AXIS = 'y_axis'  ## for scatterplots
CHART_CONFIG = {
    SIMPLE_BARCHART: {
        AGGREGATE_KEY: [
            {LBL_KEY: DATA_SHOW2_LBL_KEY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_QUANT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_AGG},  ## dropdown 1
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY},  ## dropdown 2
            {LBL_KEY: CHARTS_CHART_BY_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS},  ## dropdown 3
            ],
        INDIV_VAL_KEY: [
            {LBL_KEY: CHART_VALUES_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY},  ## dropdown 1
            {LBL_KEY: CHARTS_CHART_BY_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS},  ## dropdown 2
            ],
    },
    CLUSTERED_BARCHART: {
        AGGREGATE_KEY: [
            {LBL_KEY: DATA_SHOW2_LBL_KEY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_QUANT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_AGG},  ## dropdown 1
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY},  ## dropdown 2
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_SERIES},  ## dropdown 3
            {LBL_KEY: CHARTS_CHART_BY_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS},  ## dropdown 4
            ],
        INDIV_VAL_KEY: [
            {LBL_KEY: CHART_VALUES_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY},  ## dropdown 1
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_SERIES},  ## dropdown 2
            {LBL_KEY: CHARTS_CHART_BY_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS},  ## dropdown 3
            ],
    },
    PIE_CHART: {
        INDIV_VAL_KEY: [
            {LBL_KEY: CHART_VALUES_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY},  ## dropdown 1
            {LBL_KEY: CHARTS_CHART_BY_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS},  ## dropdown 2
            ],
    },
    LINE_CHART: {
        AGGREGATE_KEY: [
            {LBL_KEY: DATA_SHOW2_LBL_KEY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_QUANT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_AGG},  ## dropdown 1
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY},  ## dropdown 2
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: True,
             VAR_ROLE_KEY: VAR_ROLE_SERIES},  ## dropdown 3
            {LBL_KEY: CHARTS_CHART_BY_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS},  ## dropdown 4
            ],
        INDIV_VAL_KEY: [
            {LBL_KEY: CHART_VALUES_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY},  ## dropdown 1
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: True,
             VAR_ROLE_KEY: VAR_ROLE_SERIES},  ## dropdown 2
            {LBL_KEY: CHARTS_CHART_BY_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS},  ## dropdown 3
            ],
    },
    AREA_CHART: {
        AGGREGATE_KEY: [
            {LBL_KEY: DATA_SHOW2_LBL_KEY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_QUANT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_AGG},  ## dropdown 1
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY},  ## dropdown 2
            {LBL_KEY: CHARTS_CHART_BY_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS},  ## dropdown 3
            ],
        INDIV_VAL_KEY: [
            {LBL_KEY: CHART_VALUES_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY},  ## dropdown 1
            {LBL_KEY: CHARTS_CHART_BY_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS},  ## dropdown 2
            ],
    },
    HISTOGRAM: {
        INDIV_VAL_KEY: [
            {LBL_KEY: CHART_VALUES_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_QUANT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_BIN},  ## dropdown 1
            {LBL_KEY: CHARTS_CHART_BY_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS},  ## dropdown 2
            ],
    },
    SCATTERPLOT: {
        INDIV_VAL_KEY: [
            {LBL_KEY: X_AXIS_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_QUANT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_X_AXIS},  ## dropdown 1
            {LBL_KEY: Y_AXIS_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_QUANT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_Y_AXIS},  ## dropdown 2
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: True,
             VAR_ROLE_KEY: VAR_ROLE_SERIES},  ## dropdown 3
            {LBL_KEY: CHARTS_CHART_BY_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: True,
             VAR_ROLE_KEY: VAR_ROLE_CHARTS},  ## dropdown 4
            ],
    },
    BOXPLOT: {
        INDIV_VAL_KEY: [
            {LBL_KEY: CHART_DESCRIBED_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_QUANT_KEY,
             EMPTY_VAL_OK: False,
             VAR_ROLE_KEY: VAR_ROLE_DESC},  ## dropdown 1
            {LBL_KEY: CHART_BY,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: True,
             VAR_ROLE_KEY: VAR_ROLE_CATEGORY},  ## dropdown 2
            {LBL_KEY: CHART_SERIES_BY_LBL,
             MIN_DATA_TYPE_KEY: VAR_TYPE_CAT_KEY,
             EMPTY_VAL_OK: True,
             VAR_ROLE_KEY: VAR_ROLE_SERIES},  ## dropdown 3
            ],
    },
}
## common format - all have categories, all use get_chart-dets() etc.
GEN_CHARTS = [
    SIMPLE_BARCHART, CLUSTERED_BARCHART, PIE_CHART, LINE_CHART, AREA_CHART]
CHARTS_WITH_YTITLE_OPTIONS = [
    SIMPLE_BARCHART, CLUSTERED_BARCHART, LINE_CHART, AREA_CHART]
EXPECTED_VAR_ROLE_KEYS = [
    VAR_ROLE_AGG, VAR_ROLE_CATEGORY, VAR_ROLE_SERIES, VAR_ROLE_CHARTS]
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
LBL_LINE_BREAK_JS = 'var labelLineBreak = (dojo.isIE) ? "\\n" : "<br>";'
CHARTS_CHART_DETS = 'chart_dets'
CHARTS_CHART_N = 'chart_n'
CHARTS_CHART_LBL = 'Chart lbl'  ## Label for top of chart e.g. Gender: Male
CHARTS_OVERALL_TITLE = 'charts_overall_title'  ## e.g. Agegroup by Gender
CHARTS_OVERALL_LEGEND_LBL = 'Overall Legend Label'  ## One per chart
CHARTS_SERIES_LBL_IN_LEGEND = 'Series Label in Legend'  ## one per series in chart e.g. Male. Goes in legend on bottom
CHART_VAL_MEASURES = 'chart_val_measures'  ## e.g. freqs or avgs
CHART_MEASURE_DETS = 'measure_dets'
CHARTS_MAX_X_LBL_LEN = 'max_x_lbl_len'  ## all charts share same x labels - we need to know max for chart height is x labels rotated
CHARTS_MAX_Y_LBL_LEN = 'max_y_lbl_len'
CHARTS_MAX_LBL_LINES = 'max_lbl_lines'
CHARTS_SERIES_Y_VALS = 'y_vals'
CHARTS_SERIES_TOOLTIPS = 'tooltips'
CHART_NORMAL_Y_VALS = 'normal_y_vals'
CHART_SLICE_DETS = 'slice_dets'
CHARTS_XAXIS_DETS = 'xaxis_dets'
CHARTS_SERIES_DETS = 'series_dets'
CHART_SERIES_LBL = 'series_label'
CHART_MULTICHART = 'multichart'
CHART_BOXDETS = 'boxdets'
CHART_BOXPLOT_WIDTH = 0.15
CHART_BOXPLOT_DISPLAY = 'boxplot_display'
CHART_BOXPLOT_LWHISKER = 'lwhisker'
CHART_BOXPLOT_LWHISKER_ROUNDED = 'lwhisker_rounded'
CHART_BOXPLOT_LBOX = 'lbox'
CHART_BOXPLOT_LBOX_ROUNDED = 'lbox_rounded'
CHART_BOXPLOT_MEDIAN = 'median'
CHART_BOXPLOT_MEDIAN_ROUNDED = 'median_rounded'
CHART_BOXPLOT_UBOX = 'ubox'
CHART_BOXPLOT_UBOX_ROUNDED = 'ubox_rounded'
CHART_BOXPLOT_UWHISKER = 'uwhisker'
CHART_BOXPLOT_UWHISKER_ROUNDED = 'uwhisker_rounded'
CHART_BOXPLOT_OUTLIERS = 'outliers'
CHART_BOXPLOT_OUTLIERS_ROUNDED = 'outliers_rounded'
CHART_BOXPLOT_INDIV_LBL = 'indiv_lbl'
CHART_BOXPLOT_MIN_MAX_WHISKERS = _('Whiskers are min and max')
CHART_BOXPLOT_1_POINT_5_IQR_OR_INSIDE = _('Whiskers 1.5 IQR max')
CHART_BOXPLOT_HIDE_OUTLIERS = _('Hide_outliers')
CHART_BOXPLOT_OPTIONS = [
    CHART_BOXPLOT_1_POINT_5_IQR_OR_INSIDE,
    CHART_BOXPLOT_HIDE_OUTLIERS,
    CHART_BOXPLOT_MIN_MAX_WHISKERS, ]
iqr_whisker_msg = _('Lower whiskers are 1.5 times the Inter-Quartile Range '
    'below the lower quartile, or the minimum value, whichever is closest to '
    'the middle. Upper whiskers are calculated using the same approach.')
CHART_BOXPLOT_OPTIONS2LABELS = {
    CHART_BOXPLOT_1_POINT_5_IQR_OR_INSIDE: _('Outliers displayed. ') + iqr_whisker_msg,
    CHART_BOXPLOT_HIDE_OUTLIERS: _('Outliers hidden. ') + iqr_whisker_msg,
    CHART_BOXPLOT_MIN_MAX_WHISKERS: _('Whiskers are at the minimum and maximum'
        ' values'), }
CHART_MINVAL = 'minval'
CHART_MAXVAL = 'maxval'
CHART_BIN_LBLS = 'bin_labels'
SAMPLE_A = 'sample_a'
SAMPLE_B = 'sample_b'
LIST_X = 'list_x'
LIST_Y = 'list_y'
LINE_LST = 'line_lst'
DATA_TUPS = 'data_tups'
CHART_FREQS = 'chart_freqs'
CHART_AVGS = 'chart_avgs'
INC_REGRESSION = 'include_regression'
REGRESSION_ERR = 'Unable to calculate regression line'
## remember defaults //////////
## stats tests
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
MIN_CHI_DIMS = 2
MAX_CHI_DIMS = 30  ## was 6
MAX_CHI_CELLS = 200  ## was 25
MAX_PIE_SLICES = 30
MAX_CLUSTERS = 150  ## was 50
MAX_CATS_GEN = 100
MAX_GROUPS4DROPDOWN = 20
MAX_CHART_SERIES = 30
MIN_HISTO_VALS = 5
MAX_RANKDATA_VALS = 100_000  ## can override in gui mode
MAX_POINTS_DOJO_SCATTERPLOT = 800  ## 800 (use 5000 to demo dojo using demo_tbl)
MAX_SCATTERPLOT_SERIES = 5
MAX_CHARTS_IN_SET = 16
MAX_SERIES_IN_BOXPLOT = 8
MAX_BOXPLOTS_IN_SERIES = 20
JS_WRAPPER_L = "\n\n<script type=\'text/javascript\'>"
JS_WRAPPER_R = '\n</script>'
REGISTERED = 'registered'
REGEXTS = 'regexts'
PURCHEXTS = 'purchexts'
LOCALPHRASE = 'WSGosset'  ## must be 8 long exactly
USERNAME = 'username'
DISPLAYNAME = 'displayname'
CONTROLVAR = 'control'
LABEL_FONT = None  ## will be set after wx.App started
BTN_FONT = None
BTN_BOLD_FONT = None
GEN_FONT = None
## exporting output
MAC_FRAMEWORK_PATH = os.path.join(
    os.path.split(os.path.dirname(__file__))[0], 'Frameworks')  ## where misc libraries will be (even if via soft link)
#print(MAC_FRAMEWORK_PATH)
OVERRIDE_FOLDER = None  ## override to send them somewhere specific
EXPORT_IMAGES_DIAGNOSTIC = False  ## override to get more feedback
EXPORT_IMG_GAUGE_STEPS = 100
EXPORT_DATA_GAUGE_STEPS = 100
IMPORT_GAUGE_STEPS = 50  ## i.e. total size of gauge

DRAFT_DPI = 72
SCREEN_DPI = 150
PRINT_DPI = 300
HIGH_QUAL_DPI = 600
TOP_DPI = 1_200

IMPORT_EXTENTIONS = {
    'csv': '.csv',
    'tsv': '.tsv',
    'tab': '.tab',
    'txt': '.txt',
    'xls': '.xls',
    'xlsx': '.xlsx',
    'ods': '.ods', }
