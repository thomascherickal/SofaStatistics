## cd /home/g/projects/sofastats_proj/sofastatistics/ && nosetests3 test_misc.py
## cd /home/g/projects/sofastats_proj/sofastatistics/ && nosetests3 test_misc.py:test_get_path
import gettext
gettext.install(domain='sofastats', localedir='./locale')
from nose.tools import assert_equal #@UnresolvedImport
assert_equal.__self__.maxDiff = None # http://stackoverflow.com/questions/14493670/how-to-set-self-maxdiff-in-nose-to-get-full-diff-output
from nose.tools import assert_almost_equals, assert_not_equal, assert_raises, assert_true #@UnresolvedImport
from calendar import timegm
from datetime import datetime
import decimal
from pathlib import Path
import time

from .. import basic_lib as b
from .. import my_globals as mg
from .. import config_globals
from .. import lib
from ..charting import charting_output
from ..importing import csv_importer
from .. import filtselect
from .. import getdata
from ..importing import importer
from ..stats import indep2var
from .. import output
from .. import projects
from .. import recode
from ..tables import report_table
from ..tables import table_config
from ..dbe_plugins import dbe_sqlite

test_us_style = False
if test_us_style:
    config_globals.set_ok_date_formats_by_fmt(d_fmt=mg.MDY)
else:
    config_globals.set_ok_date_formats_by_fmt(d_fmt=mg.DMY)

config_globals.set_SCRIPT_PATH()
config_globals.import_dbe_plugins()

STD_TAGS_DIC = {
    'TBL_TITLE_START': mg.TBL_TITLE_START,
    'TBL_TITLE_END': mg.TBL_TITLE_END,
    'TBL_SUBTITLE_START': mg.TBL_SUBTITLE_START,
    'TBL_SUBTITLE_END': mg.TBL_SUBTITLE_END,
    'REPORT_TABLE_START': mg.REPORT_TABLE_START,
    'REPORT_TABLE_END': mg.REPORT_TABLE_END,
    'ITEM_TITLE_START': mg.ITEM_TITLE_START,
}

def test_get_epoch_secs_from_datetime_str():
    ONE_DAY = 60*60*24
    t1970 = datetime(1970, 1, 1, 0, 0, 0)
    t1843 = datetime(1843, 1, 1, 0, 0, 0)
    t2000 = datetime(2000, 1, 1, 0, 0, 0)
    t2100 = datetime(2100, 1, 1, 0, 0, 0)
    tests = [
        ('1970-01-01 00:00:00', timegm(time.strptime('1970-01-01 00:00:00', '%Y-%m-%d %H:%M:%S'))),
        ('1970-01-01 00:00:00', 0),
        ('1969-12-31 00:00:00', -ONE_DAY),
        ('1969-12-21 00:00:00', -ONE_DAY*11),
        ('1970-01-02 00:00:00', ONE_DAY),
        ('1971-01-01 00:00:00', timegm(time.strptime('1971-01-01 00:00:00', '%Y-%m-%d %H:%M:%S'))),
        ('1843-01-01 00:00:00', timegm(time.strptime('1843-01-01 00:00:00', '%Y-%m-%d %H:%M:%S'))),
        ('1843-01-01 00:00:00', (t1843-t1970).total_seconds()),  ## different approach but should get same answer
        ('2000-01-01 00:00:00', (t2000-t1970).total_seconds()),
        ('2100-01-01 00:00:00', (t2100-t1970).total_seconds()),
        ('1066-10-14 12:00:00', timegm(time.strptime('1066-10-14 12:00:00', '%Y-%m-%d %H:%M:%S'))),  ## Battle of Hastings ;-)
        ('1066', timegm(time.strptime('1066-01-01 00:00:00', '%Y-%m-%d %H:%M:%S'))),
        ('1066-10', timegm(time.strptime('1066-10-01 00:00:00', '%Y-%m-%d %H:%M:%S'))),
        ('1066.0', timegm(time.strptime('1066-01-01 00:00:00', '%Y-%m-%d %H:%M:%S'))),
    ]
    for inputs, expected_output in tests:
        actual_output = lib.DateLib.get_epoch_secs_from_datetime_str(inputs)
        assert_equal(actual_output, expected_output)

def test_get_escaped_dict_pre_write():
    tests = [
        ({'SQLite': 'sofa_db', 'PostgreSQL': None, 'MySQL': None},
"""{"MySQL": None,
    "PostgreSQL": None,
    "SQLite": "sofa_db"}"""),
        ({'SQLite': 'demo_tbl', 'PostgreSQL': None, 'MySQL': None},
"""{"MySQL": None,
    "PostgreSQL": None,
    "SQLite": "demo_tbl"}"""),
        ({'SQLite': {'sofa_db': {'database': '/home/g/Documents/sofastats/_internal/sofa_db'}}, 
            'MySQL': {'passwd': 'fakepassword', 'host': 'localhost', 'port': 3306, 'user': 'root'}},
"""{"MySQL": {"host": "localhost",
    "passwd": "fakepassword",
    "port": 3306,
    "user": "root"},
    "SQLite": {"sofa_db": {"database": "/home/g/Documents/sofastats/_internal/sofa_db"}}}"""),
    ]
    for myinput, expected_output in tests:
        actual_output = lib.get_escaped_dict_pre_write(myinput)
        assert_equal(actual_output, expected_output)

def test_get_unicode_from_file():
    """
    salvageable_codecs: codecs.BOM_UTF8, codecs.BOM_UTF32, codecs.BOM_UTF16_BE,
    codecs.BOM_UTF16, codecs.BOM_UTF32_BE
    """
#     some_css = \
#     """/*
# dojo_style_start
# outer_bg = 'white'
# inner_bg = '#f2f1f0' # '#e0d9d5'
# axis_label_font_colour = '#423126'
# major_gridline_colour = '#b8a49e'
# gridline_width = 1
# stroke_width = 3
# tooltip_border_colour = '#736354'
# colour_mappings = [
#     ('#e95f29', '#ef7d44'),
#     ('#f4cb3a', '#f7d858'),
#     ('#4495c3', '#62add2'),
#     ('#44953a', '#62ad58'),
#     ('#f43a3a', '#f75858'),
#     ]
# connector_style = 'defbrown'
# dojo_style_end
# */
#     body{
#         font-size: 12px;
#         font-family: Ubuntu, Helvetica, Arial, sans-serif;
#     }
#     h1, h2{
#         font-family: Ubuntu, Helvetica, Arial, sans-serif;
#         font-weight: bold;
#     }"""
#     some_settings = """\
# # Windows file paths _must_ have double not single backslashes
# # 'C:\\Users\\demo.txt' is GOOD
# # 'C:\Users\demo.txt' is BAD
# 
# proj_notes = 'Default project so users can get started without having to understand projects.  Read only.'
# 
# fil_var_dets = '/home/g/Documents/sofastats/vdts/general_var_dets.vdts'
# fil_css = '/home/g/Documents/sofastats/css/default.css'
# fil_report = '/home/g/Documents/sofastats/reports/default_report.htm'
# fil_script = '/home/g/Documents/sofastats/scripts/general_scripts.py'
# default_dbe = 'SQLite'
# 
# default_dbs = {'MySQL': None, 'SQLite': 'sofa_db'}
# 
# default_tbls = {'MySQL': None, 'SQLite': 'demo_tbl'}
# 
# con_dets = {'SQLite': {'sofa_db': {'database': '/home/g/Documents/sofastats/_internal/sofa_db'}}}"""
#     tests = [
#         (codecs.BOM_UTF8 + 'spam', 'spam'),  ## '\xef\xbb\xbf'
#         (codecs.BOM_UTF8 + some_css, str(some_css)),
#         (codecs.BOM_UTF8 + bytes(some_settings, encoding='utf-8'), str(some_settings)),
#     ]
#     tmp_fpath = 'delme.txt'
#     for raw, expected_unistr in tests:
#         try:
#             with open(tmp_fpath, 'wb') as f:
#                 f.write(raw)
#             assert_equal(b.get_unicode_from_file(fpath=tmp_fpath),
#                 expected_unistr)
#             print(repr(raw) + ' was good')
#         except Exception:
#             print(repr(raw) + ' was bad')
#             raise
#         finally:
#             os.remove(tmp_fpath)

def test_get_proj_content():
    """
    Trying to make a string which, if eval'd by Python, would equal the original
    """
    debug = False
    kwargs1 = {'proj_notes': '''He said "I ♥ unicode! - don't you?"''',
        'fil_var_dets': '/home/g/Documents/sofastats/vdts/general_var_dets.vdts',
        'fil_css': '/home/g/Documents/sofastats/css/default.css',
        'fil_report': '/home/g/Documents/sofastats/reports/default_report.htm',
        'fil_script': '/home/g/Documents/sofastats/scripts/general_scripts.py',
        'default_dbe': 'SQLite',
        'default_dbs': {'MySQL': None, 'SQLite': 'sofa_db'},
        'default_tbls': {'MySQL': None, 'SQLite': 'demo_tbl'},
        'con_dets': {'SQLite':
            {'sofa_db':
                {'database': '/home/g/Documents/sofastats/_internal/sofa_db'}
            }
        }
    }
    ## Escaping your escapings etc can mess with your head!
    output1 = (r"""# Windows file paths _must_ have double not single backslashes
# "C:\\Users\\demo.txt" is GOOD
# "C:\Users\demo.txt" is BAD

proj_notes = """
    + "'''"
    + r'He said \"I ♥ unicode! - don' + r"\'" + r't you?\"'
    + "'''"
    + """

fil_var_dets = "/home/g/Documents/sofastats/vdts/general_var_dets.vdts"
fil_css = "/home/g/Documents/sofastats/css/default.css"
fil_report = "/home/g/Documents/sofastats/reports/default_report.htm"
fil_script = "/home/g/Documents/sofastats/scripts/general_scripts.py"
default_dbe = "SQLite"

default_dbs = {"MySQL": None,
    "SQLite": "sofa_db"}

default_tbls = {"MySQL": None,
    "SQLite": "demo_tbl"}

con_dets = {"SQLite": {"sofa_db": {"database": "/home/g/Documents/sofastats/_internal/sofa_db"}}}""")
    if debug: print(output1)
    tests = [
        (kwargs1, output1),
    ]
    for kwargs, expected_output in tests:
        actual_output = projects.get_proj_content(**kwargs)
        if debug: print(actual_output)
        assert_equal(actual_output, expected_output)

def test_escape_pre_write():
    tests = [
        (r"C:\Users\Bert's HP Laptop\Documents\Infoneer\Software\Sofastats\locale",
        r"C:\\Users\\Bert\'s HP Laptop\\Documents\\Infoneer\\Software\\Sofastats\\locale"),
    ]
    for myinput, expected_output in tests:
        actual_output = lib.escape_pre_write(myinput)
        assert_equal(actual_output, expected_output)

def test_get_init_settings_data():
    tests = [
        (## simplest case - numbers
          ({'var0': {}, 'var1': {1: 'Male', 2: 'Female'}},  ## val_dics - the dic for var1 is the bit to be sorted
          'var1', True),
          ([(1, 'Male'), (2, 'Female'),], None)
        ),
        (## simple case - text field, text keys are integers which sort same alphabetically and numerically
          ({'var0': {}, 'var1': {'1': 'Male', '2': 'Female'}},
          'var1', False),
          ([('1', 'Male'), ('2', 'Female'),], None)
        ),
        (## trickier case - text field, text keys are integers but sort differently alphabetically and numerically
          ({'var0': {}, 'var1': {'11': 'Male', '2': 'Female'}},
          'var1', False),
          ([('2', 'Female'), ('11', 'Male'), ], None)
        ),
        (## trickier case - text field, text keys are text and integers that sort differently alphabetically and numerically
          ({'var0': {},
            'var1': {'1b': 'Should appear after proper numbers',
                      '11': 'Male', '2': 'Female'}},
          'var1', False),
          ([('2', 'Female'), ('11', 'Male'),
            ('1b', 'Should appear after proper numbers'),], None)
        ),
        (## tricky case - numeric field but some text keys
          ({'var0': {}, 'var1': {1: 'Male', 2: 'Female',
            'wat?': 'Yeah - WAT?!'}},
          'var1', True),
          ([(1, 'Male'), (2, 'Female'),], projects.BROKEN_VDT_MSG)
        ),
    ]
    for ((val_dics, var_name, bolnumeric),
            (expected_init_settings_data, expected_msg)) in tests:
        actual_init_settings_data, actual_msg = projects.get_init_settings_data(
            val_dics, var_name, bolnumeric=bolnumeric)
        assert_equal(actual_init_settings_data, expected_init_settings_data)
        assert_equal(actual_msg, expected_msg)

def test_get_optimal_min_max():
    tests = [
    ("""Both negative, too far away for snapping to 0:
        -1, -0.5  gap=0.5, range=0.5, gap2range=1 > 0.6 so no snap up to 0,
        instead make max closer to 0 by least amount possible i.e.
        0.1*1 or 0.1*0.5 so -0.5 + 0.05 i.e. -0.45
        and min is made further negative by subtracting least of
        0.1*1 or 0.1*0.5 i.e. 0.05 i.e. -1.05 """,
        (-1, -0.5), (-1.05, -0.45)),
    ("""Both negative, close enough for snapping to 0:
        -100, -0.5  gap=0.5, range=99.5, gap2range < 0.6 so might as well
        include (snap up to) 0, and min is made further negative by subtracting
        least of 0.1*100 or 0.1*99.5 i.e. 9.95 i.e. -109.95 """, 
        (-100, -0.5), (-109.95, 0.0)),
    ("""Negative up to 0 exactly:
        -100, 0  gap=0, range=100, gap2range < 0.6 so might as well
        include (snap up to) 0, and min is made further negative by subtracting
        least of 0.1*100 or 0.1*100 i.e. 10 i.e. -110 """,
        (-100, 0), (-110.0, 0.0)),
    ("""Spanning axis:
        -100, 10  gap=0, range=100, max = 1.1*10 i.e. 11
        and min = 1.1*-100 i.e. -110""",
        (-100, 10), (-110.0, 11.0)),
    ("""Both positive, close enough for snapping to 0:
        10, 100  gap=10, range=90, min = 0 because so close relative to range,
        max = 100 + least of 0.1*100 or 0.1*90 so 9 so 109
        """,
        (10, 100), (0.0, 109.0)),
    ("""Both positive, too far away for snapping to 0:
        100, 110  gap=100, range=10, too far to snap to 0, so
        min = 100 - least of 0.1*100 or 0.1*10 i.e. 100 - 1 i.e. 99,
        max = 110 + least of 0.1*110 or 0.1*10 so 1 so 111
        """,
        (100, 110), (99, 111.0)),
    ("""Both the same and positive:
        100, 100  min = 0, max = 1.1*100 i.e. 110
        """,
        (100, 100), (0, 110)),
    ("""Both the same and negative:
        -100, -100  min = -100*1.1 i.e. -110, max = 0
        """,
        (-100, -100), (-110, 0)),
    ("""Both the same and 0:
        0, 0  min = -1, max = 1
        """,
        (0, 0), (-1, 1)),
    ]
    for unused, myinputs, myoutputs in tests:
        min_in, max_in = myinputs
        min_out, max_out = myoutputs
        min_calc, max_calc = charting_output._get_optimal_min_max(
            min_in, max_in)
        assert_almost_equals(min_out, min_calc)
        assert_almost_equals(max_out, max_calc)

def test_get_histo_dp():
    tests = [
        ((5, 0.5), 1),
        ((5.1, 0.5), 1),
        ((5.1, 0.05), 2),
        ((5, 0.05), 2),
        ((5, 0.01), 2),
        ((5, 0.00000000005), 7),  ## 7 is the maximum
        ((1, 0.5), 1),
        ((1.1, 0.5), 1),
        ((1.1, 0.05), 2),
        ((1, 0.05), 2),
        ((1, 0.01), 2),
        ((1, 0.00000000005), 7),  ## 7 is the maximum
        ((-1, 0.2), 1),
        ((0.01, 0.00001), 5),
    ]
    for (combined_start, bin_width), expected_dp in tests:
        actual_dp = charting_output.Histo._get_histo_dp(combined_start, bin_width)
        assert_equal(actual_dp, expected_dp)

def test_quote_val():
    """
    Need to handle input with double quotes around text e.g. he said 'Hi',
    single quotes e.g. in names, or words like he's, and double double quotes
    e.g. sometimes entered ''fred''
    """
    tests = []
    sqlite_tests = [
        ({'raw_val': 'spam',
          'sql_str_literal_quote': "'",
          'sql_esc_str_literal_quote': "''", },
         "'spam'"),  ## e.g. ends up in SQL as ... WHERE myvar = 'spam' ...
        ({'raw_val': 'spam',
          'sql_str_literal_quote': "'",
          'sql_esc_str_literal_quote': "''", },
         "'spam'"),  ## e.g. ends up in SQL as ... WHERE myvar = 'spam' ...
        ({'raw_val': """He said 'No' didn''t he""",
          'sql_str_literal_quote': "'",
          'sql_esc_str_literal_quote': "''", },
         "'He said ''No'' didn''''t he'"),  ## e.g. ends up in SQL as ... WHERE myvar = 'He said ''No'' didn''t he' ...
        ({'raw_val': """He said ''No'' didn't he""",
          'sql_str_literal_quote': "'",
          'sql_esc_str_literal_quote': "''", },
         "'He said ''''No'''' didn''t he'"),  ## e.g. ends up in SQL as ... WHERE myvar = 'He said ''''No'''' didn''t he' ...
        ({'raw_val': """If the error 'bad screen distance 640.0' would disappear !""",
          'sql_str_literal_quote': "'",
          'sql_esc_str_literal_quote': "''", },
         "'If the error ''bad screen distance 640.0'' would disappear !'"),  ## e.g. ends up in SQL as ... WHERE myvar = 'If the error ''bad screen distance 640.0'' would disappear !' ...
        ({'raw_val': """If the error 'bad screen distance 640.0' would disappear !""",
          'sql_str_literal_quote': "'",
          'sql_esc_str_literal_quote': "''", },
         "'If the error ''bad screen distance 640.0'' would disappear !'"),  ## e.g. ends up in SQL as ... WHERE myvar = 'If the error ''bad screen distance 640.0'' would disappear !' ...
    ]
    tests.extend(sqlite_tests)
    for inputs, expected_output in tests:
        actual_output = lib.DbLib.quote_val(**inputs)
        assert_equal(actual_output, expected_output)

def test_get_item_title():
    """
    title, indiv_title='', item_type=''
    """
    tests = [
        (
            ('This is a title much longer than the 35 characters I allow for '
            'the title component',
            'And I have a long individual chart title too',
            'Chart Type'),
            'Chart Type_This is a title much longer than th_And I have a lo'
        ),
        (
            ('This is a title much longer than the 35 characters I allow for'
             ' the title component',
             '',
             'Chart Type'),
             'Chart Type_This is a title much longer than the 35 characters'
        ),
        (
            ('This is a short title',
             'A really long subtitle that deserves to get some breathing space',
             'Chart Type'),
             'Chart Type_This is a short title_A really long subtitle that d'
        ),
        (
            ('This is a short title',
             'A really long subtitle that deserves to get some breathing space',
             ''),
             'This is a short title_A really long subtitle that d'
        ),
    ]
    for inputs, expected_output in tests:
        actual_output = output.get_item_title(*inputs)
        assert_equal(actual_output, expected_output)

def test_extract_img_path():
    """
    Note - os-dependent re: file:/// vs file://
    """
    tests = [(("<IMG src='default_report_images/000.png'>"
        '%(ITEM_TITLE_START)s<!--Results of ANOVA test of average '
        'Post-di_Japan-->' % {'ITEM_TITLE_START': mg.ITEM_TITLE_START}, False),
              Path('default_report_images/000.png')),
        (("""
        <!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
'http://www.w3.org/TR/html4/loose.dtd'>
<html>
<head>
<meta http-equiv='P3P' content='CP='IDC DSP COR CURa ADMa OUR IND PHY ONL COM
STA''>
<meta http-equiv='content-type' content='text/html; charset=utf-8'/>
<title>Report(s)</title>

<link rel='stylesheet' type='text/css'
href='file:///home/g/Documents/sofastats/reports/sofastats_report_extras/tundra.css' />
<script src='file:///home/g/Documents/sofastats/reports/sofastats_report_extras/dojo.xd.js'></script>
<script src='file:///home/g/Documents/sofastats/reports/sofastats_report_extras/sofastatsdojo_minified.js'></script>
<script src='file:///home/g/Documents/sofastats/reports/sofastats_report_extras/sofastats_charts.js'></script>
<script type='text/javascript'>
get_ie_script = function(mysrc){
    var script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = mysrc;
    document.getElementsByTagName('head')[0].appendChild(script);
}
if(dojo.isIE){
    get_ie_script('file:///home/g/Documents/sofastats/reports/sofastats_report_extras/arc.xd.js');
    get_ie_script('file:///home/g/Documents/sofastats/reports/sofastats_report_extras/gradient.xd.js');
    get_ie_script('file:///home/g/Documents/sofastats/reports/sofastats_report_extras/vml.xd.js');
}
makeObjects = function(){

    for(var i=0;i<16;i++){
        try{
            window['makechartRenumber' + String('00'+i).slice(-2)]();
        } catch(exceptionObject) {
            var keepGoing = true;
        }
    }

};
dojo.addOnLoad(makeObjects);

var DEFAULT_SATURATION  = 100,
DEFAULT_LUMINOSITY1 = 75,
DEFAULT_LUMINOSITY2 = 50,

c = dojox.color,

cc = function(colour){
    return function(){ return colour; };
},

hl = function(colour){

    var a = new c.Color(colour),
        x = a.toHsl();
    if(x.s == 0){
        x.l = x.l < 50 ? 100 : 0;
    }else{
        x.s = DEFAULT_SATURATION;
        if(x.l < DEFAULT_LUMINOSITY2){
            x.l = DEFAULT_LUMINOSITY1;
        }else if(x.l > DEFAULT_LUMINOSITY1){
            x.l = DEFAULT_LUMINOSITY2;
        }else{
            x.l = x.l - DEFAULT_LUMINOSITY2 > DEFAULT_LUMINOSITY1 - x.l
                ? DEFAULT_LUMINOSITY2 : DEFAULT_LUMINOSITY1;
        }
    }
    return c.fromHsl(x);
}

getfainthex = function(hexcolour){
    var a = new c.Color(hexcolour)
    x = a.toHsl();
    x.s = x.s * 1.5;
    x.l = x.l * 1.25;
    return c.fromHsl(x);
}

makefaint = function(colour){
    var fainthex = getfainthex(colour.toHex());
    return new dojox.color.Color(fainthex);
}

var labelLineBreak = (dojo.isIE) ? '\n' : '<br>';

</script>

<style type='text/css'>
<!--
    .dojoxLegendNode {
        border: 1px solid #ccc;
        margin: 5px 10px 5px 10px;
        padding: 3px
    }
    .dojoxLegendText {
        vertical-align: text-top;
        padding-right: 10px
    }
    @media print {
        .screen-float-only{
        float: none;
        }
    }

    @media screen {
        .screen-float-only{
        float: left;
        }
    }
-->
</style>
<style type='text/css'>
<!--

body {
    background-color: #ffffff;
}
td, th {
    background-color: white;
}
/*
dojo_style_start
outer_bg = 'white'
inner_bg = '#f2f1f0' # '#e0d9d5'
axis_label_font_colour = '#423126'
major_gridline_colour = '#b8a49e'
gridline_width = 1
stroke_width = 3
tooltip_border_colour = '#736354'
colour_mappings = [
    ('#e95f29', '#ef7d44'),
    ('#f4cb3a', '#f7d858'),
    ('#4495c3', '#62add2'),
    ('#44953a', '#62ad58'),
    ('#f43a3a', '#f75858'),
]
connector_style = 'defbrown'
dojo_style_end
*/
    body{
        font-size: 12px;
        font-family: Ubuntu, Helvetica, Arial, sans-serif;
    }
    h1, h2{
        font-family: Ubuntu, Helvetica, Arial, sans-serif;
        font-weight: bold;
    }
    h1{
        font-size: 18px;
    }
    h2{
        font-size: 16px;
    }
    .gui-msg-medium, gui-msg-small{
        color: #29221c;
        font-family: arial;
    }
    .gui-msg-medium{
        font-size: 16px;
    }
    *html .gui-msg-medium{
        font-weight: bold;
        font-size: 18px;
    }
    .gui-msg-small{
        font-size: 13px;
        line-height: 150%;
    }
    .gui-note{
        background-color: #e95829;
        color: white;
        font-weight: bold;
        padding: 2px;
    }
    tr, td, th{
        margin: 0;
    }

    .tbltitle0, .tblsubtitle0{
        margin: 0;
        font-family: Ubuntu, Helvetica, Arial, sans-serif;
        font-weight: bold;
        font-size: 14px;
    }
    .tbltitle0{ /*spans*/
        padding: 0;
        font-size: 18px;
    }
    .tblsubtitle0{
        padding: 12px 0px 0px 0px;
        font-size: 14px;
    }
    .tblcelltitle0{ /*th*/
        text-align: left;
        border: none;
        padding: 0px 0px 12px 0px;
        margin: 0;
    }

    th, .rowvar0, .rowval0, .datacell0, .firstdatacell0 {
        border: solid 1px #A1A1A1;
    }
    th{
        margin: 0;
        padding: 0px 6px;
    }
    td{
        padding: 2px 6px;
        border: solid 1px #c0c0c0;
        font-size: 13px;
    }
    .rowval0{
        margin: 0;
    }
    .datacell0, .firstdatacell0{
        text-align: right;
        margin: 0;
    }
    .firstcolvar0, .firstrowvar0, .spaceholder0 {
        font-family: Ubuntu, Helvetica, Arial, sans-serif;
        font-weight: bold;
        font-size: 14px;
        color: white;
    }
    .firstcolvar0, .firstrowvar0{
        background-color: #333435;
    }
    .firstrowvar0{
        border-left: solid 1px #333435;
        border-bottom:  solid 1px #333435;
    }
    .topline0{
        border-top: 2px solid #c0c0c0;
    }
    .spaceholder0 {
        background-color: #CCD9D7;
    }
    .firstcolvar0{
        padding: 9px 6px;
        vertical-align: top;
    }
    .rowvar0, .colvar0{
        font-family: Ubuntu, Helvetica, Arial, sans-serif;
        font-weight: bold;
        font-size: 14px;
        color: #333435;
        background-color: white;
    }
    .colvar0{
        padding: 6px 0px;
    }
    .colval0, .measure0{
        font-size: 12px;
        vertical-align: top;
    }
    table {
        border-collapse: collapse;
    }
    tr.total-row0 td{
        font-weight: bold;
        border-top: solid 2px black;
        border-bottom: double 3px black;
    }
    .page-break-before0{
        page-break-before: always;
        border-bottom: none; /*3px dotted #AFAFAF;*/
        width: auto;
        height: 18px;
    }
    td.lbl0{
        text-align: left;
        background-color: #F5F5F5;
    }
    td.right0{
        text-align: right;
    }
    .ftnote-line{
        /* for hr http://www.w3schools.com/TAGS/att_hr_align.asp*/
        width: 300px;
        text-align: left; /* IE and Opera*/
        margin-left: 0; /* Firefox, Chrome, Safari */
    }
    .tbl-header-ftnote0{
        color: white;
    }
    .ftnote{
        color: black;
    }
    /* Tool tip connector arrows */
    .dijitTooltipBelow-defbrown {

        padding-top: 13px;
    }
    .dijitTooltipAbove-defbrown {

        padding-bottom: 13px;
    }
    .tundra .dijitTooltipBelow-defbrown .dijitTooltipConnector {

        top: 0px;
        left: 3px;
        background: url('file:///home/g/Documents/sofastats/reports/sofastats_report_extras/tooltipConnectorUp-defbrown.png') no-repeat top left !important;
        width:16px;
        height:14px;
    }
    .dj_ie .tundra .dijitTooltipBelow-defbrown .dijitTooltipConnector {

        background-image: url('file:///home/g/Documents/sofastats/reports/sofastats_report_extras/tooltipConnectorUp-defbrown.gif') !important;
    }
    .tundra .dijitTooltipAbove-defbrown .dijitTooltipConnector {

        bottom: 0px;
        left: 3px;
        background:url('file:///home/g/Documents/sofastats/reports/sofastats_report_extras/tooltipConnectorDown-defbrown.png') no-repeat top left !important;
        width:16px;
        height:14px;
    }
    .dj_ie .tundra .dijitTooltipAbove-defbrown .dijitTooltipConnector {
        background-image: url('file:///home/g/Documents/sofastats/reports/sofastats_report_extras/tooltipConnectorDown-defbrown.gif') !important;
    }
    .dj_ie6 .tundra .dijitTooltipAbove-defbrown .dijitTooltipConnector {
        bottom: -3px;
    }
    .tundra .dijitTooltipLeft-defbrown {
        padding-right: 14px;
    }
    .dj_ie6 .tundra .dijitTooltipLeft-defbrown {
        padding-left: 15px;
    }
    .tundra .dijitTooltipLeft-defbrown .dijitTooltipConnector {

        right: 0px;
        bottom: 3px;
        background:url('file:///home/g/Documents/sofastats/reports/sofastats_report_extras/tooltipConnectorRight-defbrown.png') no-repeat top left !important;
        width:16px;
        height:14px;
    }
    .dj_ie .tundra .dijitTooltipLeft-defbrown .dijitTooltipConnector {
        background-image: url('file:///home/g/Documents/sofastats/reports/sofastats_report_extras/tooltipConnectorRight-defbrown.gif') !important;
    }
    .tundra .dijitTooltipRight-defbrown {
        padding-left: 14px;
    }
    .tundra .dijitTooltipRight-defbrown .dijitTooltipConnector {

        left: 0px;
        bottom: 3px;
        background:url('file:///home/g/Documents/sofastats/reports/sofastats_report_extras/tooltipConnectorLeft-defbrown.png') no-repeat top left !important;
        width:16px;
        height:14px;
    }
    .dj_ie .tundra .dijitTooltipRight-defbrown .dijitTooltipConnector {
        background-image: url('file:///home/g/Documents/sofastats/reports/sofastats_report_extras/tooltipConnectorLeft-defbrown.gif') !important;
    }

-->
</style>
</head>
<body class='tundra'>
<table cellspacing='0'><thead><tr><th class='tblcelltitle0'>
<span class='tbltitle0'>
</span>
<span class='tblsubtitle0'>
</span>
</th></tr></thead></table><div class=screen-float-only style='margin-right: 10px;
        margin-top: 0; '>
<IMG src='file:///home/g/Documents/sofastats/reports/sofa_use_only_report_images/_img_001.png'></div>
        """, False),
        Path('/home/g/Documents/sofastats/reports/sofa_use_only_report_images/_img_001.png')),
    ]
    win_tests = []
    non_win_tests = [
        (
             ("<IMG src='file:///home/g/Documents/sofastats/reports"
              "/sofa_use_only_report_images/_img_001.png'>"
              f'{mg.ITEM_TITLE_START}'
              '<!--Results of ANOVA test of average Post-di_Japan-->', False), 
              Path('/home/g/Documents/sofastats/reports/sofa_use_only_report_images/_img_001.png')
        ),
    ]
    if mg.PLATFORM == mg.WINDOWS:
        tests.extend(win_tests)
    else:
        tests.extend(non_win_tests)
    for (content, use_as_url), expected_output in tests:
        actual_output = lib.OutputLib._extract_img_path(
            content, use_as_url=use_as_url)
        assert_equal(actual_output, expected_output)

def test_get_src_dst_preexisting_img():
    """
    imgs_path -- e.g. export output: /home/g/Desktop/SOFA export Sep 30 09-34 AM
    e.g. export report:  /home/g/Documents/sofastats/reports/test_exporting_exported_images
    content -- e.g. export output: <img src='file:///home/g/Documents/sofastats/reports/sofa_use_only_report_images/_img_001.png'>
    e.g. export report: <img src='test_exporting_images/000.png'>
    want src to be /home/g/Documents/sofastats/reports/sofa_use_only_report_images/_img_001.png 
        (not file:///home ...)
    and dst to be /home/g/Desktop/SOFA export Sep 30 09-34 AM/_img_001.png

    img_path
    /home/uwe/Dokumente/sofastats/reports/sofa_use_only_report_images/_img_001.png'>

    src
<p><a id='ft1'></a><sup>1</sup> If p is small, e.g. less than 0.01, or 0.001, you can assume the result is statistically significant i.e. there is a relationship. Note: a statistically significant difference may not necessarily be of any practical significance.</p>
<p><a id='ft2

    dest
/home/uwe/Dokumente/sofastats/reports/sofa_use_only_report_images/_img_001.png'>
<p><a id='ft1'></a><sup>1</sup> If p is small, e.g. less than 0.01, or 0.001, you can assume the result is statistically significant i.e. there is a relationship. Note: a statistically significant difference may not necessarily be of any practical significance.</p>
<p><a id='ft2 /home/uwe/Desktop/SOFA export Mai 11 12-42 /p>
<p><a id='ft2
    """
    inputs = 'inputs'
    outputs = 'outputs'
    tests = []
    win_tests = []
    non_win_tests = [  ##{inputs:  (export_report, imgs_path, content),
                       ## outputs: (src, dest)
     {inputs: (False, '/home/g/Desktop/SOFA export Sep 30 09-34 AM/', "<IMG src='file:///home/g/Documents/sofastats/reports/sofa_use_only_report_images/_img_001.png'>"), 
      outputs: ('/home/g/Documents/sofastats/reports/sofa_use_only_report_images/_img_001.png', '/home/g/Desktop/SOFA export Sep 30 09-34 AM/_img_001.png')},
     {inputs: (True, '/home/g/Documents/sofastats/reports/test_exporting_exported_images/', "<IMG src='test_exporting_images/000.png'>"), 
      outputs: ('/home/g/Documents/sofastats/reports/test_exporting_images/000.png', '/home/g/Documents/sofastats/reports/test_exporting_exported_images/000.png')},
     {inputs: (False, '/home/g/Desktop/SOFA export Sep 30 09-34 AM/', "<IMG src='/home/g/Documents/sofastats/reports/sofa_use_only_report_images/_img_001.png'>"), 
      outputs: ('/home/g/Documents/sofastats/reports/sofa_use_only_report_images/_img_001.png', '/home/g/Desktop/SOFA export Sep 30 09-34 AM/_img_001.png')},
     {inputs: (False, '/home/g/Desktop/SOFA export Sep 30 09-34 AM/', "<IMG src='/home/g/Documents/sofastats/reports/sofa_use_only_report_images/_img_001.png'>\n<p><a id='ft1'></a><sup>1</sup> If p is small, e.g. less than 0.01, or 0.001, you can assume the result is statistically significant i.e. there is a relationship. Note: a statistically significant difference may not necessarily be of any practical significance.</p>\n<p><a id='ft2'>"),
      outputs: ('/home/g/Documents/sofastats/reports/sofa_use_only_report_images/_img_001.png', '/home/g/Desktop/SOFA export Sep 30 09-34 AM/_img_001.png')},
    ]
    if mg.PLATFORM == mg.WINDOWS:
        tests.extend(win_tests)
    else:
        tests.extend(non_win_tests)
    for test in tests:
        export_report, imgs_path, content = test[inputs]
        expected_res = tuple(Path(x) for x in test[outputs])
        actual_res = lib.OutputLib.get_src_dst_preexisting_img(
            export_report, Path(imgs_path), content)
        print(actual_res)
        print(expected_res)
        assert_equal(actual_res, expected_res)

def test_get_prestructured_grouped_data():
    raw_data0 = [(1,1,1,56),
                 (1,1,2,103),
                 (1,1,3,72),
                 (1,1,4,40),
                 (1,2,1,13),
                 (1,2,2,59),
                 (1,2,3,200),
                 (1,2,4,0),]
    fldnames0 = ['fld1', 'fld2', 'fld3', 'fld4']
    chart_n = 533
    prestructure0 = [
        {charting_output.CHART_VAL_KEY: 1,
         charting_output.CHART_N_KEY: chart_n,
         charting_output.CHART_SERIES_KEY: [
             {charting_output.SERIES_KEY: 1, 
              charting_output.XY_KEY: [(1,56), (2,103), (3,72), (4,40)]
             },
             {charting_output.SERIES_KEY: 2, 
              charting_output.XY_KEY: [(1,13), (2,59), (3,200), (4,0)]
             },
            ]
        },
    ]
    tests = [
        (raw_data0, fldnames0, {1: chart_n}, prestructure0),
    ]
    for raw_data, fldnames, chart_ns, expected_output in tests:
        actual_output = charting_output.DataPrep.get_prestructured_grouped_data(
            raw_data, fldnames, chart_ns)
        assert_equal(actual_output, expected_output)

def test_get_blocks():
    tests = [
             ((range(1,44), 20), ## 1-43 in blocks of 20 please :-)
              [range(1, 21), range(21, 41), range(41, 44)]),
            ]
    for (input0, input1), expected_output in tests:
        actual_output = dbe_sqlite.get_blocks(input0, block_sz=input1)
        assert_equal(actual_output, expected_output)

def test_importer_get_val():
    """
    getting value ready to feed into SQLite.
    NB '.'s in numeric or date --> Nulls. In string can stay as was.
    Empty strings --> Nulls, even in string fields.
    get_val(feedback, raw_val, is_pytime, fld_type, ok_fldname,
            faulty2missing_fld_list, row_num, comma_dec_sep_ok=False)
    """    
    feedback = {mg.NULLED_DOTS_KEY: False}
    faulty2missing_fld_list = []  ## throwaway in this test
    row_num = 1
    tests = [((feedback, 1, False, mg.FLDTYPE_NUMERIC_KEY, 'myfld',
               faulty2missing_fld_list, row_num, False), 1),
             ((feedback, 1.1, False, mg.FLDTYPE_NUMERIC_KEY, 'myfld',
               faulty2missing_fld_list, row_num, False), 1.1),
             ((feedback, '1.1', False, mg.FLDTYPE_NUMERIC_KEY, 'myfld',
               faulty2missing_fld_list, row_num, False), '1.1'),
            ((feedback, '1,1', False, mg.FLDTYPE_NUMERIC_KEY, 'myfld',
              faulty2missing_fld_list, row_num, True), '1.1'),
            ((feedback, 'fred', False, mg.FLDTYPE_STRING_KEY, 'myfld',
              faulty2missing_fld_list, row_num, False), 'fred'),
            ((feedback, '.', False, mg.FLDTYPE_DATE_KEY, 'myfld',
              faulty2missing_fld_list, row_num, False), None),
            ((feedback, '.', False, mg.FLDTYPE_NUMERIC_KEY, 'myfld',
              faulty2missing_fld_list, row_num, False), None),
            ((feedback, '.', False, mg.FLDTYPE_STRING_KEY, 'myfld',
              faulty2missing_fld_list, row_num, False), '.'),
            ((feedback, '', False, mg.FLDTYPE_NUMERIC_KEY, 'myfld',
              faulty2missing_fld_list, row_num, False), None),
            ((feedback, '', False, mg.FLDTYPE_DATE_KEY, 'myfld',
              faulty2missing_fld_list, row_num, False), None),
            ((feedback, '', False, mg.FLDTYPE_STRING_KEY, 'myfld',
              faulty2missing_fld_list, row_num, False), None),
            ((feedback, "''", False, mg.FLDTYPE_DATE_KEY, 'myfld',
              faulty2missing_fld_list, row_num, False), None),
            ((feedback, "''", False, mg.FLDTYPE_DATE_KEY, 'myfld',
              faulty2missing_fld_list, row_num, False), None),
            ((feedback, '"', False, mg.FLDTYPE_STRING_KEY, 'myfld',  ## if already 
              faulty2missing_fld_list, row_num, False), '"'),
            ((feedback, '"', False, mg.FLDTYPE_STRING_KEY, 'myfld',
              faulty2missing_fld_list, row_num, False), '"'),
    ]
    if test_us_style:
        tests.extend([
             ((feedback, '6/12/2010 15:29:59', False, mg.FLDTYPE_DATE_KEY,
               'myfld', faulty2missing_fld_list, row_num, False),
               '2010-06-12 15:29:59'),])
    else:
        tests.extend([
             ((feedback, '6/12/2010 15:29:59', False, mg.FLDTYPE_DATE_KEY,
               'myfld', faulty2missing_fld_list, row_num, False),
               '2010-12-06 15:29:59'),])
    for inputs, expected_output in tests:
        actual_output = importer.get_val(
            *inputs[:-1], comma_dec_sep_ok=inputs[-1])
        assert_equal(actual_output, expected_output)

def test_get_overall_fld_type():
    """
    mg.VAL_NUMERIC, mg.VAL_DATE, mg.VAL_STRING, mg.VAL_EMPTY_STRING
    mg.FLDTYPE_NUMERIC, mg.FLDTYPE_DATE, mg.FLDTYPE_STRING
    """
    tests = [
        (set([mg.VAL_NUMERIC, mg.VAL_EMPTY_STRING]), mg.FLDTYPE_NUMERIC_KEY),
        (set([mg.VAL_NUMERIC]), mg.FLDTYPE_NUMERIC_KEY),
        (set([mg.VAL_DATE, mg.VAL_EMPTY_STRING]), mg.FLDTYPE_DATE_KEY),
        (set([mg.VAL_DATE]), mg.FLDTYPE_DATE_KEY),
        (set([mg.VAL_STRING, mg.VAL_EMPTY_STRING]), mg.FLDTYPE_STRING_KEY),
        (set([mg.VAL_STRING]), mg.FLDTYPE_STRING_KEY),
        (set([mg.VAL_STRING, mg.VAL_NUMERIC, mg.VAL_DATE, 
              mg.VAL_EMPTY_STRING]), mg.FLDTYPE_STRING_KEY),  ## fallback
        (set([mg.VAL_STRING, mg.VAL_NUMERIC, mg.VAL_DATE]),
         mg.FLDTYPE_STRING_KEY),  ## fallback
        (set([mg.VAL_NUMERIC, mg.VAL_DATE]), mg.FLDTYPE_STRING_KEY),
        (set([mg.VAL_NUMERIC, mg.VAL_DATE, mg.VAL_EMPTY_STRING]),
         mg.FLDTYPE_STRING_KEY),
    ]
    for test in tests:
        assert_equal(lib.get_overall_fldtype(type_set=test[0]), test[1])

def test_dates_1900_to_datetime_str():
    """
    The first test relies on proper sec rounding based on microsecs.
    The second test rounding up from 59 seconds.
    """
    tests = [('40413.7434259259', '2010-08-23 17:50:32'),
             ('40419.7458333333', '2010-08-29 17:54:00'),
             ('0', '1899-12-30 00:00:00'),
             ('-1', '1899-12-29 00:00:00'),
             ]
    for test in tests:
        assert_equal(lib.DateLib.dates_1900_to_datetime_str(
            days_since_1900=test[0]), test[1])

def test_version_a_is_newer():
    true_tests = [('9.8.2', '9.6.9'),
                  ('10.1.1', '9.1.1'),
                  ('00009.1.1', '9.0.1'),
                 ]
    for test in true_tests:
        assert_true(lib.version_a_is_newer(test[0], test[1]))

def test_process_orig():
    fld = 'bar'
    tests = [(('Spam TO Eggs', fld, mg.FLDTYPE_STRING_KEY), 
              "`bar` BETWEEN 'Spam' AND 'Eggs'"),
             (('1 TO 3', fld, mg.FLDTYPE_NUMERIC_KEY), 
              '`bar` BETWEEN 1 AND 3'),
            ((' ', fld, mg.FLDTYPE_STRING_KEY), 
             "`bar` = ' '"),
             (('1 TO MAX', fld, mg.FLDTYPE_NUMERIC_KEY), 
              '`bar` >= 1'),
             (('1 TO MAX', fld, mg.FLDTYPE_STRING_KEY), 
              "`bar` >= '1'"),
             (('MIN TO MAX', fld, mg.FLDTYPE_STRING_KEY), 
              '`bar` IS NOT NULL'),
             (('MIN TO MAX', fld, mg.FLDTYPE_DATE_KEY), 
              '`bar` IS NOT NULL'),
             (('MIN TO 2010-06-22 00:00:00', fld, mg.FLDTYPE_DATE_KEY), 
              "`bar` <= '2010-06-22 00:00:00'"),
             (('MINTO10776', fld, mg.FLDTYPE_NUMERIC_KEY), 
              '`bar` <= 10776'),
             (('1 to 6', fld, mg.FLDTYPE_STRING_KEY), 
              "`bar` = '1 to 6'"),
             (('-1 TO 26', fld, mg.FLDTYPE_NUMERIC_KEY), 
              '`bar` BETWEEN -1 AND 26'),
             ((' MISSING ', fld, mg.FLDTYPE_NUMERIC_KEY), 
              '`bar` IS NULL'),
            ]
    for test in tests:
        assert_equal(recode.process_orig(*test[0]), test[1])
    raises_tests = [(1, fld, mg.FLDTYPE_STRING_KEY),
                    ('TO 21', fld, mg.FLDTYPE_STRING_KEY),
                    ('Spam TO MIN', fld, mg.FLDTYPE_STRING_KEY),
                    ('MAX TO Spam', fld, mg.FLDTYPE_STRING_KEY),
                    ('spam', fld, mg.FLDTYPE_NUMERIC_KEY),
                    (' REMAINING ', fld, mg.FLDTYPE_NUMERIC_KEY), 
                    ]
    for test in raises_tests:
        #http://www.ibm.com/developerworks/aix/library/au-python_test/index.html
        assert_raises(Exception, recode.process_orig, test)

def test_has_data_changed():
    """
    The original data is in the form of a list of tuples - the tuples are 
        field name and type.
    The final data is a list of dicts, with keys for:
        mg.TBL_FLDNAME, 
        mg.TBL_FLDNAME_ORIG,
        mg.TBL_FLDTYPE,
        mg.TBL_FLDTYPE_ORIG.
    Different if TBL_fldname != TBL_fldname_ORIG
    Different if TBL_fldtype != TBL_fldtype_ORIG
    Different if set of TBL_fldnames not same as set of field names. 
    NB Need first two checks in case names swapped.  Sets wouldn't change 
        but data would have changed.
    """
    string = mg.FLDTYPE_STRING_KEY
    num = mg.FLDTYPE_NUMERIC_KEY
    orig_data1 = [('sofa_id', num), ('var001', string), 
                  ('var002', string), ('var003', string)]
    final_data1 = [ {'fldname_orig': 'sofa_id', 'fldname': 'sofa_id', 
                        'fldtype': num, 'fldtype_orig': num}, 
                    {'fldname_orig': 'var001', 'fldname': 'var001', 
                        'fldtype': string, 'fldtype_orig': string}, 
                    {'fldname_orig': 'var002', 'fldname': 'var002', 
                        'fldtype': string, 'fldtype_orig': string}, 
                    {'fldname_orig': 'var003', 'fldname': 'var003', 
                        'fldtype': string, 'fldtype_orig': string}]
    # renamed a field
    final_data2 = [ {'fldname_orig': 'sofa_id', 'fldname': 'sofa_id2', 
                        'fldtype': num, 'fldtype_orig': num}, 
                    {'fldname_orig': 'var001', 'fldname': 'var001', 
                        'fldtype': string, 'fldtype_orig': string}, 
                    {'fldname_orig': 'var002', 'fldname': 'var002', 
                        'fldtype': string, 'fldtype_orig': string}, 
                    {'fldname_orig': 'var003', 'fldname': 'var003', 
                        'fldtype': string, 'fldtype_orig': string}]
    # deleted a field
    final_data3 = [ {'fldname_orig': 'sofa_id', 'fldname': 'sofa_id', 
                        'fldtype': num, 'fldtype_orig': num}, 
                    {'fldname_orig': 'var001', 'fldname': 'var001', 
                        'fldtype': string, 'fldtype_orig': string}, 
                    {'fldname_orig': 'var003', 'fldname': 'var003', 
                        'fldtype': string, 'fldtype_orig': string}]
    # changed fld type to Numeric
    final_data4 = [ {'fldname_orig': 'sofa_id', 'fldname': 'sofa_id', 
                        'fldtype': num, 'fldtype_orig': num}, 
                    {'fldname_orig': 'var001', 'fldname': 'var001', 
                        'fldtype': string, 'fldtype_orig': string}, 
                    {'fldname_orig': 'var002', 'fldname': 'var002', 
                        'fldtype': string, 'fldtype_orig': num}, 
                    {'fldname_orig': 'var003', 'fldname': 'var003', 
                        'fldtype': string, 'fldtype_orig': string}]
    # swapped but same final (still changed)
    final_data5 = [ {'fldname_orig': 'sofa_id', 'fldname': 'sofa_id', 
                        'fldtype': num, 'fldtype_orig': num}, 
                    {'fldname_orig': 'var001', 'fldname': 'var002', 
                        'fldtype': string, 'fldtype_orig': string}, 
                    {'fldname_orig': 'var002', 'fldname': 'var001', 
                        'fldtype': string, 'fldtype_orig': string}, 
                    {'fldname_orig': 'var003', 'fldname': 'var003', 
                        'fldtype': string, 'fldtype_orig': string}]
    # added a field
    final_data6 = [ {'fldname_orig': 'sofa_id', 'fldname': 'sofa_id', 
                        'fldtype': num, 'fldtype_orig': num},  
                    {'fldname_orig': None, 'fldname': 'spam', 
                        'fldtype': None, 'fldtype_orig': string},
                    {'fldname_orig': 'var001', 'fldname': 'var001', 
                        'fldtype': string, 'fldtype_orig': string}, 
                    {'fldname_orig': 'var002', 'fldname': 'var002', 
                        'fldtype': string, 'fldtype_orig': string}, 
                    {'fldname_orig': 'var003', 'fldname': 'var003', 
                        'fldtype': string, 'fldtype_orig': string}]
    tests = [((orig_data1, final_data1), False),
             ((orig_data1, final_data2), True),
             ((orig_data1, final_data3), True),
             ((orig_data1, final_data4), True),
             ((orig_data1, final_data5), True),
             ((orig_data1, final_data6), True),
            ]
    for test in tests:
        assert_equal(table_config.has_data_changed(*test[0]), test[1])

def test_get_avg_row_size():
    """
    Measures length of string of comma separated values.
    Only needs to be approximate as is used for progress bar.
    Expects to get a list of strings or a dict of strings.
    If a dict, the final item could be a list if there are more items in the
        original row than the dict reader expected.
    """
    # 26 = 12chars + 3 extra chars for 2 digit ones + 11 commas
    """
    ä is E4 in latin1, 00 E4 in unicode, C3 A4 in utf-8, and Ã¤ if mistakenly 
        decoded as latin1 from utf-8. http://www.jeppesn.dk/utf-8.html
    """
    tests = [([
               ['1','2','3','4','5','6','7','8','9','10','11','12',],
               ], 
              26),
             ([
               ['1','2','3','4','5','6','7','8','9','10','11','12',], 
               ['a',],
               ],
              13.5),
             ([
               [None,],
               ], 
              0),
             ([
               [None, None, None, None,],
               ], 
              3),
             ([
               [None, None, None, None,], # -> ',,,' i.e. 3 long
               ['\u0195\u0164',], # -> ä i.e. 2 bytes long in utf-8 but 1 in latin1
               ], 
              2.5),
             ([
               [None, None, None, None,], # -> ',,,' i.e. 3 long
               ['ä',], # -> 1 byte long in unicode and in latin1
               ], 
              2.0),
             ]
    for test in tests:
        assert_equal(csv_importer.CsvImporter._get_avg_row_size(
            test[0]), test[1])

def test_get_next_fldname():
    """
    Get next available variable name where names follow a template e.g. var001,
        var002 etc.If a gap, starts after last one.  Gaps are not filled.
    """
    tests = [(['var001',], 'var002'),
             (['var001', 'var003'], 'var004'),
             (['var001', 'Var003'], 'var002'),
             (['fld001', 'Identität', 'Identität002'], 'var001'),
             ]
    for test in tests:
        assert_equal(lib.get_next_fldname(test[0]), test[1])    

css_path_tests = [
    ('default', Path('/home/g/Documents/sofastats/css/default.css')),
    ('Identität', Path('/home/g/Documents/sofastats/css/Identität.css')),
]

def test_path2style():
    'Strip style out of full css path'
    for test in css_path_tests:
        assert_equal(lib.OutputLib.path2style(test[1]), test[0])

def test_style2path():
    'Get full path of css file from style name alone'
    for test in css_path_tests:
        assert_equal(lib.OutputLib.style2path(test[0]), test[1])

def test_replace_titles_subtitles():
    """
    For testing, use minimal css to keep it compact enough to understand easily.
    """
    orig1 = """<p class='gui-msg-medium'>Example data - click 'Run' for actual 
        results<br>&nbsp;&nbsp;or keep configuring</p>

        <!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
        'http://www.w3.org/TR/html4/loose.dtd'>
        <html>
        <head>
        <meta http-equiv='P3P' content='CP='IDC DSP COR CURa ADMa OUR 
        IND PHY ONL COM STA''>
        <meta http-equiv='content-type' content='text/html; charset=utf-8'/>
        <title>Report(s)</title>
        <style type='text/css'>
        <!--
        body{
            font-size: 12px;
        }
        -->
        </style>
        </head>
        <body>
        <table cellspacing='0'>
        
        <thead>
        <tr><th class='tblcelltitle0' colspan='3'>
        <span class='tbltitle0'>%(TBL_TITLE_START)s%(TBL_TITLE_END)s</span>
        <span class='tblsubtitle0'>%(TBL_SUBTITLE_START)s%(TBL_SUBTITLE_END)s</span></th></tr>
        <tr><th class='spaceholder0' rowspan='1' colspan='2'>&nbsp;&nbsp;</th><th class='measure0'  >Freq</th></tr>
        </thead>
        
        <tbody>
        <tr><td class='firstrowvar0'  rowspan='2'  >Car</td><td class='rowval0'  >BMW</td><td class='firstdatacell0'>2.5</td></tr>
        <tr><td class='rowval0'  >PORSCHE</td><td class='firstdatacell0'>1.5</td></tr>
        </tbody>
        </table>
        </body>
        </html>""" % STD_TAGS_DIC
    titles1 = ['T']
    subtitles1 = []
    output1 = """<p class='gui-msg-medium'>Example data - click 'Run' for actual 
        results<br>&nbsp;&nbsp;or keep configuring</p>

        <!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
        'http://www.w3.org/TR/html4/loose.dtd'>
        <html>
        <head>
        <meta http-equiv='P3P' content='CP='IDC DSP COR CURa ADMa OUR 
        IND PHY ONL COM STA''>
        <meta http-equiv='content-type' content='text/html; charset=utf-8'/>
        <title>Report(s)</title>
        <style type='text/css'>
        <!--
        body{
            font-size: 12px;
        }
        -->
        </style>
        </head>
        <body>
        <table cellspacing='0'>
        
        <thead>
        <tr><th class='tblcelltitle0' colspan='3'>
        <span class='tbltitle0'>%(TBL_TITLE_START)sT%(TBL_TITLE_END)s</span>
        <span class='tblsubtitle0'>%(TBL_SUBTITLE_START)s%(TBL_SUBTITLE_END)s</span></th></tr>
        <tr><th class='spaceholder0' rowspan='1' colspan='2'>&nbsp;&nbsp;</th><th class='measure0'  >Freq</th></tr>
        </thead>
        
        <tbody>
        <tr><td class='firstrowvar0'  rowspan='2'  >Car</td><td class='rowval0'  >BMW</td><td class='firstdatacell0'>2.5</td></tr>
        <tr><td class='rowval0'  >PORSCHE</td><td class='firstdatacell0'>1.5</td></tr>
        </tbody>
        </table>
        </body>
        </html>""" % STD_TAGS_DIC
    orig2 = """<p class='gui-msg-medium'>Example data - click 'Run' for 
        actual results<br>&nbsp;&nbsp;or keep configuring</p>

        <!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
        'http://www.w3.org/TR/html4/loose.dtd'>
        <html>
        <head>
        <meta http-equiv='P3P' content='CP='IDC DSP COR CURa ADMa OUR 
        IND PHY ONL COM STA''>
        <meta http-equiv='content-type' content='text/html; charset=utf-8'/>
        <title>Report(s)</title>
        <style type='text/css'>
        <!--
        body{
            font-size: 12px;
        }
        -->
        </style>
        </head>
        <body>
        <table cellspacing='0'>
        
        <thead>
        <tr><th class='tblcelltitle0' colspan='3'>
        <span class='tbltitle0'>%(TBL_TITLE_START)s1<br>2%(TBL_TITLE_END)s</span>
        <span class='tblsubtitle0'>%(TBL_SUBTITLE_START)s<br>3<br>4<br>%(TBL_SUBTITLE_END)s</span></th></tr>
        <tr><th class='spaceholder0' rowspan='1' colspan='2'>&nbsp;&nbsp;</th><th class='measure0'  >Freq</th></tr>
        </thead>
        
        <tbody>
        <tr><td class='firstrowvar0'  rowspan='2'  >Car</td><td class='rowval0'  >BMW</td><td class='firstdatacell0'>2.5</td></tr>
        <tr><td class='rowval0'  >PORSCHE</td><td class='firstdatacell0'>1.5</td></tr>
        </tbody>
        </table>
        </body>
        </html>""" % STD_TAGS_DIC
    titles2 = ['1', '2']
    subtitles2 = ['3', '4', '5']
    output2 = """<p class='gui-msg-medium'>Example data - click 'Run' for 
        actual results<br>&nbsp;&nbsp;or keep configuring</p>

        <!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
        'http://www.w3.org/TR/html4/loose.dtd'>
        <html>
        <head>
        <meta http-equiv='P3P' content='CP='IDC DSP COR CURa ADMa OUR 
        IND PHY ONL COM STA''>
        <meta http-equiv='content-type' content='text/html; charset=utf-8'/>
        <title>Report(s)</title>
        <style type='text/css'>
        <!--
        body{
            font-size: 12px;
        }
        -->
        </style>
        </head>
        <body>
        <table cellspacing='0'>
        
        <thead>
        <tr><th class='tblcelltitle0' colspan='3'>
        <span class='tbltitle0'>%(TBL_TITLE_START)s1<br>2%(TBL_TITLE_END)s</span>
        <span class='tblsubtitle0'>%(TBL_SUBTITLE_START)s<br>3<br>4<br>5%(TBL_SUBTITLE_END)s</span></th></tr>
        <tr><th class='spaceholder0' rowspan='1' colspan='2'>&nbsp;&nbsp;</th><th class='measure0'  >Freq</th></tr>
        </thead>
        
        <tbody>
        <tr><td class='firstrowvar0'  rowspan='2'  >Car</td><td class='rowval0'  >BMW</td><td class='firstdatacell0'>2.5</td></tr>
        <tr><td class='rowval0'  >PORSCHE</td><td class='firstdatacell0'>1.5</td></tr>
        </tbody>
        </table>
        </body>
        </html>""" % STD_TAGS_DIC
    tests = [((orig1, titles1, subtitles1), output1),
             ((orig2, titles2, subtitles2), output2),
             ]
    for test in tests:
        assert_equal(report_table.replace_titles_subtitles(*test[0]), test[1])

def test_extract_title_subtitle():
    tests = [
    ("""
<table cellspacing='0'><thead><tr><th class='tblcelltitle0'>
<span class='tbltitle0'>
%(TBL_TITLE_START)s
My really awesome title
%(TBL_TITLE_END)s
</span>
<br>
<span class='tblsubtitle0'>
%(TBL_SUBTITLE_START)s
My brilliant subtitle
%(TBL_SUBTITLE_END)s
</span>
</th></tr></thead></table>""" % STD_TAGS_DIC,
    ('My really awesome title', 'My brilliant subtitle')),
    ]
    for myinput, myoutput in tests:
        assert_equal(output.extract_title_subtitle(myinput), myoutput)

def test_extract_tbl_only():
    tests = [
        ("""<table cellspacing='0'><thead><tr><th class='tblcelltitle0'>
<span class='tbltitle0'>
%(TBL_TITLE_START)s
Country By Gender
%(TBL_TITLE_END)s
</span>
<br>
<span class='tblsubtitle0'>
%(TBL_SUBTITLE_START)s
Basic analysis only
%(TBL_SUBTITLE_END)s
</span>
</th></tr></thead></table>
%(REPORT_TABLE_START)s<table cellspacing='0'>

<thead>
<tr></tr>
<tr><th class='spaceholder0' rowspan='3' colspan='2'>&nbsp;&nbsp;</th><th class='firstcolvar0'   colspan='9' >Gender</th></tr>
<tr><th class='colval0'   colspan='3' >Male</th><th class='colval0'   colspan='3' >Female</th><th class='colval0'   colspan='3' >TOTAL</th></tr>
<tr><th class='measure0'  >Freq</th><th class='measure0'  >Col %%</th><th class='measure0'  >Row %%</th><th class='measure0'  >Freq</th><th class='measure0'  >Col %%</th><th class='measure0'  >Row %%</th><th class='measure0'  >Freq</th><th class='measure0'  >Col %%</th><th class='measure0'  >Row %%</th></tr>
</thead>

<tbody>
<tr><td class='firstrowvar0'  rowspan='3'  >Country</td><td class='rowval0'  >Japan</td><td class='firstdatacell0'>254</td><td class='datacell0'>33.0%%</td><td class='datacell0'>54.5%%</td><td class='datacell0'>212</td><td class='datacell0'>29.0%%</td><td class='datacell0'>45.5%%</td><td class='datacell0'>466</td><td class='datacell0'>31.1%%</td><td class='datacell0'>100.0%%</td></tr>
<tr><td class='rowval0'  >Italy</td><td class='firstdatacell0'>265</td><td class='datacell0'>34.5%%</td><td class='datacell0'>52.3%%</td><td class='datacell0'>242</td><td class='datacell0'>33.1%%</td><td class='datacell0'>47.7%%</td><td class='datacell0'>507</td><td class='datacell0'>33.8%%</td><td class='datacell0'>100.0%%</td></tr>
<tr><td class='rowval0'  >Germany</td><td class='firstdatacell0'>250</td><td class='datacell0'>32.5%%</td><td class='datacell0'>47.4%%</td><td class='datacell0'>277</td><td class='datacell0'>37.9%%</td><td class='datacell0'>52.6%%</td><td class='datacell0'>527</td><td class='datacell0'>35.1%%</td><td class='datacell0'>100.0%%</td></tr>
</tbody>

</table>%(REPORT_TABLE_END)s
%(ITEM_TITLE_START)s<!--Crosstabs_Country By Gender-->        
        """ % {'TBL_TITLE_START': mg.TBL_TITLE_START,
    'TBL_TITLE_END': mg.TBL_TITLE_END,
    'TBL_SUBTITLE_START': mg.TBL_SUBTITLE_START,
    'TBL_SUBTITLE_END': mg.TBL_SUBTITLE_END,
    'REPORT_TABLE_START': mg.REPORT_TABLE_START, 
    'REPORT_TABLE_END': mg.REPORT_TABLE_END, 
    'ITEM_TITLE_START': mg.ITEM_TITLE_START}, 
        """<h2>Country By Gender</h2>
<h2>Basic analysis only</h2>
<table cellspacing='0'>

<thead>
<tr></tr>
<tr><th class='spaceholder0' rowspan='3' colspan='2'>&nbsp;&nbsp;</th><th class='firstcolvar0'   colspan='9' >Gender</th></tr>
<tr><th class='colval0'   colspan='3' >Male</th><th class='colval0'   colspan='3' >Female</th><th class='colval0'   colspan='3' >TOTAL</th></tr>
<tr><th class='measure0'  >Freq</th><th class='measure0'  >Col %</th><th class='measure0'  >Row %</th><th class='measure0'  >Freq</th><th class='measure0'  >Col %</th><th class='measure0'  >Row %</th><th class='measure0'  >Freq</th><th class='measure0'  >Col %</th><th class='measure0'  >Row %</th></tr>
</thead>

<tbody>
<tr><td class='firstrowvar0'  rowspan='3'  >Country</td><td class='rowval0'  >Japan</td><td class='firstdatacell0'>254</td><td class='datacell0'>33.0%</td><td class='datacell0'>54.5%</td><td class='datacell0'>212</td><td class='datacell0'>29.0%</td><td class='datacell0'>45.5%</td><td class='datacell0'>466</td><td class='datacell0'>31.1%</td><td class='datacell0'>100.0%</td></tr>
<tr><td class='rowval0'  >Italy</td><td class='firstdatacell0'>265</td><td class='datacell0'>34.5%</td><td class='datacell0'>52.3%</td><td class='datacell0'>242</td><td class='datacell0'>33.1%</td><td class='datacell0'>47.7%</td><td class='datacell0'>507</td><td class='datacell0'>33.8%</td><td class='datacell0'>100.0%</td></tr>
<tr><td class='rowval0'  >Germany</td><td class='firstdatacell0'>250</td><td class='datacell0'>32.5%</td><td class='datacell0'>47.4%</td><td class='datacell0'>277</td><td class='datacell0'>37.9%</td><td class='datacell0'>52.6%</td><td class='datacell0'>527</td><td class='datacell0'>35.1%</td><td class='datacell0'>100.0%</td></tr>
</tbody>

</table>"""),
    ]
    for myinput, myoutput in tests:
        #print(output.extract_tbl_only(myinput))
        #print('\n'*4)
        #print(myoutput)
        assert_equal(output.extract_tbl_only(myinput), myoutput)

def test_rel2abs_rpt_img_links():
    """
    Make all images work of absolute rather than relative paths. Will run OK
        when displayed internally in GUI.
    Make normal images absolute: turn my_report_name/001.png to e.g. 
        file:///home/g/sofastats/reports/my_report_name/001.png so that the html 
        can be written to, and read from, anywhere (and still show the images!) 
        in the temporary GUI displays.
    Make background images absolute: turn ../images/tile.gif to 
        file:///home/g/sofastats/images/tile.gif.
    """
    tests = [
        ("<h1>Hi there!</h1>%smy report name/my_img.png'" % mg.IMG_SRC_START, 
        '<h1>Hi there!</h1>%sfile:///home/g/Documents/sofastats/reports/'
            "my report name/my_img.png'" % mg.IMG_SRC_START),
    ]
    for test in tests:
        assert_equal(output.rel2abs_rpt_img_links(test[0]), test[1])

def test_is_usable_datetime_str():
    print(mg.OK_DATE_FORMATS)
    print(mg.OK_DATE_FORMAT_EXAMPLES)
    tests = [('June 2009', True),
             ('2009 June', True),
             ('2009 Jun', True),
             ('Feb 23, 2010', True),
             ('February 23, 2010', True),
             ('February 23 2010', True),
             ('1901', True),
             ('1876', True),
             ('1666-09-02', True),
             ('1666/09/02', True),
             ]
    if test_us_style:
        tests.extend([
             ('31/3/88', False),
             ('3/31/88', True),
             ('31.3.1988', False),
             ])
    else:
        tests.extend([
             ('31/3/88', True),
             ('3/31/88', False),
             ('31.3.1988', True),
             ])
    for test in tests:
        print(test[0], lib.DateLib.is_usable_datetime_str(test[0]), test[1])
        assert_equal(lib.DateLib.is_usable_datetime_str(test[0]), test[1])

def test_get_std_datetime_str():
    ymd = '%4d-%02d-%02d' % time.localtime()[:3]
    tests = [('2pm', '%s 14:00:00' % ymd),
             ('14:30', '%s 14:30:00' % ymd),
             ('2009-01-31', '2009-01-31 00:00:00'),
             ('11am 2009-01-31', '2009-01-31 11:00:00'),
             ('2009-01-31 3:30pm', '2009-01-31 15:30:00'),
             ('2009-01-31 3:30 pm', '2009-01-31 15:30:00'), # should turn 3:30 pm to 3:30pm
             ]
    if test_us_style:
        tests.extend([
             ('09/02/1666 00:12:16', '1666-09-02 00:12:16'), #http://en.wikipedia.org/wiki/Great_Fire_of_London
             ('3/31/88', '1988-03-31 00:00:00'),
             ('12.2.2001 2:35pm', '2001-12-02 14:35:00'),
             ('12.2.01 2:35pm', '2001-12-02 14:35:00'),
             ])
    else:
        tests.extend([
             ('02/09/1666 00:12:16', '1666-09-02 00:12:16'), #http://en.wikipedia.org/wiki/Great_Fire_of_London
             ('31/3/88', '1988-03-31 00:00:00'),
             ('12.2.2001 2:35pm', '2001-02-12 14:35:00'),
             ('12.2.01 2:35pm', '2001-02-12 14:35:00'),
             ])    
    for test in tests:
        assert_equal(lib.DateLib.get_std_datetime_str(test[0]), test[1])
        
def test_get_dets_of_usable_datetime_str():
    # date_part, date_format, time_part, time_format, boldate_then_time
    tests = [(5, None),
             (' ', None),
             ('   ', None),
             ('', None),
             ('2009', ('2009', '%Y', None, None, True)),
             ('2009-01-31', ('2009-01-31', '%Y-%m-%d', None, None, True)),
             ('2pm', (None, None, '2pm', '%I%p', True)),
             ('2:30pm', (None, None, '2:30pm', '%I:%M%p', True)),
             ('14:30', (None, None, '14:30', '%H:%M', True)),
             ('14:30:00', (None, None, '14:30:00', '%H:%M:%S', True)),
             ('2009-01-31 14:03:00', ('2009-01-31', '%Y-%m-%d', '14:03:00', 
                                      '%H:%M:%S', True)),
             ('14:03:00 2009-01-31', ('2009-01-31', '%Y-%m-%d', '14:03:00', 
                                      '%H:%M:%S', False)),
             ('1am 2009-01-31', ('2009-01-31', '%Y-%m-%d', '1am', '%I%p', 
                                 False)),
             ('Feb 1 2011', ('Feb 1 2011', '%b %d %Y', None, None, True)),
             ('Feb 1 2011 4 pm', ('Feb 1 2011', '%b %d %Y', '4pm', '%I%p', 
                                  True)),
             ('4 am Feb 1 2011', ('Feb 1 2011', '%b %d %Y', '4am', '%I%p', 
                                  False)),
             ('Feb 1, 2011 4 pm', ('Feb 1, 2011', '%b %d, %Y', '4pm', '%I%p', 
                                  True)),
             ('4 am Feb 1, 2011', ('Feb 1, 2011', '%b %d, %Y', '4am', '%I%p', 
                                  False)),
             ]
    if test_us_style:
        tests.extend([
             ('01/31/2009', ('01/31/2009', '%m/%d/%Y', None, None, True)),
             ('1/31/2009', ('1/31/2009', '%m/%d/%Y', None, None, True)),
             ('01/31/09', ('01/31/09', '%m/%d/%y', None, None, True)),
             ('1/31/09', ('1/31/09', '%m/%d/%y', None, None, True)),
             ('3.31.1988', ('3.31.1988', '%m.%d.%Y', None, None, True)),
             ('3.31.1988 2:45am', ('3.31.1988', '%m.%d.%Y', '2:45am', '%I:%M%p', 
                            True)),
             ('3.31.88 2:45am', ('3.31.88', '%m.%d.%y', '2:45am', '%I:%M%p', 
                            True)),
             ])
    else:
        tests.extend([
             ('31/01/2009', ('31/01/2009', '%d/%m/%Y', None, None, True)),
             ('31/1/2009', ('31/1/2009', '%d/%m/%Y', None, None, True)),
             ('31/01/09', ('31/01/09', '%d/%m/%y', None, None, True)),
             ('31/1/09', ('31/1/09', '%d/%m/%y', None, None, True)),
             ('31.3.1988', ('31.3.1988', '%d.%m.%Y', None, None, True)),
             ('31.3.1988 2:45am', ('31.3.1988', '%d.%m.%Y', '2:45am', '%I:%M%p', 
                            True)),
             ('31.3.88 2:45am', ('31.3.88', '%d.%m.%y', '2:45am', '%I:%M%p', 
                            True)),
             ])  
    for test in tests:
        assert_equal(lib.DateLib._get_dets_of_usable_datetime_str(test[0], 
                               mg.OK_DATE_FORMATS, mg.OK_TIME_FORMATS), test[1])

def test_get_val():
    'Must be useful for making WHERE clauses'
    flds = {'numvar': {mg.FLD_BOLNUMERIC: True, 
                       mg.FLD_BOLDATETIME: False},
            'strvar': {mg.FLD_BOLNUMERIC: False, 
                       mg.FLD_BOLDATETIME: False},
            'datevar': {mg.FLD_BOLNUMERIC: False, 
                        mg.FLD_BOLDATETIME: True},
            }
    tests = [(('12', flds, 'numvar'), 12),
             (('', flds, 'numvar'), None),
             (('NuLL', flds, 'numvar'), None),
             (('NULL', flds, 'strvar'), None),
             (('', flds, 'strvar'), ''),
             (('12', flds, 'strvar'), '12'),
             (('', flds, 'datevar'), None),
             (('nuLL', flds, 'datevar'), None),
             (('2009-01-31', flds, 'datevar'), '2009-01-31 00:00:00'),
             (('2009', flds, 'datevar'), '2009-01-01 00:00:00'),
             ]
    for test in tests:
        assert_equal(filtselect.get_val(*test[0]), test[1])

def test_get_range_idxs():
    tests = [
        ([1, 2, 3, 4, 5], '1', '3', (0, 2)),
        (['Chrome', 'Firefox', 'Internet Explorer', 'Safari'],
            'Firefox', 'Internet Explorer', (1, 2)),
        (['1000000000000.1', '1000000000000.2', '1000000000000.3', 
                '1000000000000.4', '1000000000000.5', '1000000000000.6'], 
            '1000000000000.2', '1000000000000.4', (1, 3)),
    ]
    for vals, val_a, val_b, idx_tup in tests:
        assert_equal(indep2var.get_range_idxs(vals, val_a, val_b), idx_tup)

def test_process_fldnames():
    """
    Only valid SQLite table and field names. Spaces, hyphens, and dots to 
    underscores. NB dots and hyphens seem to fail completely so we can't test
    their conversion.
    """
    equal_tests = [
        (['spam', 'eggs', 'knights who say ni', 'Παντελής 2'], 
            ['spam', 'eggs', 'knights_who_say_ni', 'Παντελής_2']),
        (['☀', '☁', '☂'], 
            ['☀', '☁', '☂']), # don't ask ;-)
        (['unladen swallow', 'unladen_swallow', 'spam', 'eggs'], 
         ['unladen_swallow001', 'unladen_swallow002', 'spam', 'eggs']),
        ]
    for raw_names, expected_names in equal_tests:
        actual_names = importer.process_fldnames(raw_names)
        assert_equal(actual_names, expected_names)
    raises_tests = [
        [5, '6'],
    ]
    for test in raises_tests:
        #http://www.ibm.com/developerworks/aix/library/au-python_test/index.html
        assert_raises(Exception, importer.process_fldnames, test)

def test_assess_sample_fld():
    """
    sample_data, has_header, ok_fldname, ok_fldnames, 
                      faulty2missing_fld_list, allow_none=True, 
                      comma_dec_sep_ok=False
    """
    sample_data = [
        {
            1: '2',
            2: '2.0',
            3: 2,
            4: 2.0,
            5: '1.245e10',
            6: 'spam',
            7: '2009-01-31',
            8: '2009',
            9: '',
            10: '',
            11: 5},
            {1: '2',
            2: '2.0',
            3: 2,
            4: 2.0,
            5: '1.245e10',
            6: 'spam',
            7: '2009-01-31',
            8: '2009',
            9: 5,
            10: '',
            11: '2009-01',
        }
    ]
    ## fld name, expected type
    tests = [(1, mg.FLDTYPE_NUMERIC_KEY),
             (2, mg.FLDTYPE_NUMERIC_KEY),
             (3, mg.FLDTYPE_NUMERIC_KEY),
             (4, mg.FLDTYPE_NUMERIC_KEY),
             (5, mg.FLDTYPE_NUMERIC_KEY),
             (6, mg.FLDTYPE_STRING_KEY),
             (7, mg.FLDTYPE_DATE_KEY),
             (8, mg.FLDTYPE_NUMERIC_KEY), # 2009 on own is a number
             (9, mg.FLDTYPE_NUMERIC_KEY), # empty + numeric = numeric
             (10, mg.FLDTYPE_STRING_KEY),
             (11, mg.FLDTYPE_STRING_KEY), # empty + string (2009-01 is not 
                # number or datetime) = string
             ]
    for test in tests:
        assert_equal(importer.assess_sample_fld(sample_data=sample_data, 
                has_header=False, ok_fldname=test[0], 
                ok_fldnames=range(1,12), faulty2missing_fld_list=[], 
                allow_none=True, comma_dec_sep_ok=False, headless=True), 
            test[1])

def test_n2d():
    """
    Hard to test except for cases where float is stored in binary exactly 
        because the code from http://docs.python.org/library/decimal.html is
        the gold standard for me.
    Still worth ensuring it works for simple cases to make sure nothing breaks 
        it.
    """
    D = decimal.Decimal
    tests = [(1, D('1')),
             (-1, D('-1')),
             ('34', D('34')),
             ('34.00', D('34')),
             (1.00000, D('1')),
             (1.002e3, D('1002')),
             ]
    for test in tests:
        assert_equal(lib.n2d(test[0]), test[1])

def test_is_basic_num(): # about type
    tests = [(5, True),
             ('5', False),
             (1.2, True),
             (decimal.Decimal('1'), False),
             ((1 + 2j), False),
             ('spam', False),
             ]
    for test in tests:
        assert_equal(lib.TypeLib.is_basic_num(test[0]), test[1])

def test_is_numeric(): # about content
    tests = [(5, False, True),
             (1.000003, False, True),
             (0.0000001, False, True),
             ('5', False, True),
             ('5.5', False, True),
             ('5,5', True, True),
             ('5,5', False, False), # comma not OK so should fail
             ('1e+10', False, True),
             ('e+10', False, False),
             ('spam', False, False),
             ('2010-01-01', False, False),
             (314j, False, False),
             (1 + 14j, False, False),
             ((1 + 14j), False, False),
             ('NaN', False, True),
             ]
    for test in tests:
        print(test)
        assert_equal(lib.TypeLib.is_numeric(test[0], comma_dec_sep_ok=test[1]),
            test[2])

def test_make_fld_val_clause():
    """
    dbe, flds, fldname, val, gte=mg.GTE_EQUALS
    """
    import copy
    orig_dd = copy.deepcopy(mg.DATADETS_OBJ)
    print(mg.DATADETS_OBJ)
    if mg.DATADETS_OBJ is None:
        class mockdd(object):
            pass
        mg.DATADETS_OBJ = mockdd
    NUMVAR = 'numvar'
    STRVAR = 'strvar'
    mg.DATADETS_OBJ.flds = {
        NUMVAR: {mg.FLD_CHARSET: 'utf-8'}, 
        STRVAR: {mg.FLD_CHARSET: 'utf-8'},
    }
    flds = {
        NUMVAR: {
            mg.FLD_BOLNUMERIC: True, 
            mg.FLD_BOLDATETIME: False,
            mg.FLD_CHARSET: 'utf-8',
        },
        STRVAR: {
            mg.FLD_BOLNUMERIC: False, 
            mg.FLD_BOLDATETIME: False,
            mg.FLD_CHARSET: 'utf-8',
        }
    }
    # make_fld_val_clause(dbe, flds, fldname, val, gte)
    tests = [
        ((mg.DBE_SQLITE, flds, STRVAR, 'fred'),
            f"`{STRVAR}` = 'fred'"),
        ((mg.DBE_SQLITE, flds, NUMVAR, 5),
            f'`{NUMVAR}` = 5'),  ## num type but string
        ((mg.DBE_SQLITE, flds, NUMVAR, 'spam'),
            f"`{NUMVAR}` = 'spam'"),
        ((mg.DBE_SQLITE, flds, NUMVAR, None),
            f'`{NUMVAR}` IS NULL'),
        ((mg.DBE_MYSQL, flds, STRVAR, 'fred'),
            f'`{STRVAR}` = "fred"'),
        ((mg.DBE_MYSQL, flds, NUMVAR, 5),
            f'`{NUMVAR}` = 5'),
        ((mg.DBE_MYSQL, flds, NUMVAR, None),
            f'`{NUMVAR}` IS NULL'),
        ((mg.DBE_PGSQL, flds, STRVAR, 'fred'),
            f"\"{STRVAR}\" = 'fred'"),
        ((mg.DBE_PGSQL, flds, NUMVAR, 5),
            f'"{NUMVAR}" = 5'),
        ((mg.DBE_SQLITE, flds, STRVAR, 'fred', mg.GTE_NOT_EQUALS),
            f"`{STRVAR}` != 'fred'"),
        ((mg.DBE_SQLITE, flds, NUMVAR, 5,
            mg.GTE_NOT_EQUALS),
            f'`{NUMVAR}` != 5'),# num type but string
        ((mg.DBE_SQLITE, flds, NUMVAR, 'spam', mg.GTE_NOT_EQUALS),
            f"`{NUMVAR}` != 'spam'"),
        ((mg.DBE_SQLITE, flds, NUMVAR, None, mg.GTE_NOT_EQUALS),
            f'`{NUMVAR}` IS NOT NULL'),
        ((mg.DBE_MYSQL, flds, STRVAR, 'fred', mg.GTE_NOT_EQUALS),
            f'`{STRVAR}` != "fred"'),
        ((mg.DBE_MYSQL, flds, NUMVAR, 5, mg.GTE_NOT_EQUALS),
            f'`{NUMVAR}` != 5'),
        ((mg.DBE_MYSQL, flds, NUMVAR, None, mg.GTE_NOT_EQUALS),
            f'`{NUMVAR}` IS NOT NULL'),
        ((mg.DBE_PGSQL, flds, STRVAR, 'fred', mg.GTE_NOT_EQUALS),
            f"\"{STRVAR}\" != 'fred'"),
        ((mg.DBE_PGSQL, flds, NUMVAR, 5, mg.GTE_NOT_EQUALS),
            f'"{NUMVAR}" != 5'),
        ]
    for inputs, expected_res in tests:
        actual_res = getdata.make_fld_val_clause(*inputs)
        assert_equal(actual_res, expected_res)
    mg.DATADETS_OBJ = orig_dd

def test_any2unicode():
    tests = [
     (1, '1'),
     (0.3, '0.3'),
     (10000000000.2, '10000000000.2'),
     (1000000000000000.2, '1000000000000000.2'), # fails if any longer
     (r'C:\abcd\defg\foo.txt', 'C:\\abcd\\defg\\foo.txt'),
     ('C:\\abcd\\defg\\foo.txt', 'C:\\abcd\\defg\\foo.txt'),
     ('C:\\abcd\\defg\\foo.txt', 'C:\\abcd\\defg\\foo.txt'),
     ('C:\\unicodebait\\foo.txt', 'C:\\unicodebait\\foo.txt'),
     ('C:\\Identität\\foo.txt', 'C:\\Identität\\foo.txt'),
     (r'/home/g/abcd/foo.txt', '/home/g/abcd/foo.txt'),
     ('/home/g/abcd/foo.txt', '/home/g/abcd/foo.txt'),
     ('/home/René/abcd/foo.txt', '/home/René/abcd/foo.txt'),
     ('/home/Identität/abcd/foo.txt', '/home/Identität/abcd/foo.txt'),
     ('/home/François/abcd/foo.txt', '/home/François/abcd/foo.txt'),
#      ('\x93fred\x94', '\u201Cfred\u201D'),
     (r'C:\Documents and Settings\Παντελής\sofastats\_internal', 
      'C:\\Documents and Settings\\\u03a0\u03b1\u03bd\u03c4\u03b5\u03bb\u03ae\u03c2\\sofastats\\_internal')
             ]
    for test in tests:
        assert_equal(lib.UniLib.any2unicode(test[0]), test[1])
        assert_true(isinstance(lib.UniLib.any2unicode(test[0]), str))

def test_extract_html_body():
    tests = [(f'{mg.BODY_START}Freddy</body>', 'Freddy'), 
             (f'{mg.BODY_START}Freddy</body>Teddy</body>', 'Freddy'),
             (f'{mg.BODY_START}Freddy', 'Freddy'),
             ]
    for html, expected_body in tests:
        actual_body = output.extract_html_body(html)
        assert_equal(actual_body, expected_body)

def test_strip_script():
    tests = [('\nchunky chicken%s\nxzmxnzmxnz' % mg.SCRIPT_END, 
              '\nchunky chicken')]
    for test in tests:
        assert_equal(output._strip_script(test[0]), test[1])
        
def test_sofa_default_proj_settings():
    """
    OK if fails because user deliberately changed settings
    if they are smart enough to do that they should be smart enough to change 
    this test too ;-)
    """
    proj_dic = config_globals.get_settings_dic(subfolder=mg.PROJS_FOLDER, 
                                               fil_name=mg.DEFAULT_PROJ)
    (unused, unused, 
     unused, unused) = lib.get_var_dets(proj_dic[mg.PROJ_FIL_VDTS])
    unused = proj_dic[mg.PROJ_FIL_VDTS]
    dbe = proj_dic[mg.PROJ_DBE]
    con_dets = proj_dic[mg.PROJ_CON_DETS]
    default_dbs = proj_dic[mg.PROJ_DEFAULT_DBS] \
        if proj_dic[mg.PROJ_DEFAULT_DBS] else {}
    default_tbls = proj_dic[mg.PROJ_DEFAULT_TBLS] \
        if proj_dic[mg.PROJ_DEFAULT_TBLS] else {}
    assert_equal(dbe, mg.DBE_SQLITE)
    assert_equal(default_dbs[mg.DBE_SQLITE], mg.SOFA_DB)
    assert_equal(default_tbls[mg.DBE_SQLITE], mg.DEMO_TBL)
    assert_equal(con_dets[mg.DBE_SQLITE][mg.SOFA_DB]['database'].split('/')[-1], 
                 mg.SOFA_DB)    
    
def test_get_var_dets():
    """
    OK if fails because user deliberately changed settings
    if they are smart enough to do that they should be smart enough to change 
    this test too ;-)
    """
    proj_dic = config_globals.get_settings_dic(subfolder=mg.PROJS_FOLDER, 
                                               fil_name=mg.DEFAULT_PROJ)
    (var_labels, var_notes, 
     var_types, val_dics) = lib.get_var_dets(proj_dic[mg.PROJ_FIL_VDTS])
    assert_not_equal(var_labels.get('Name'), None)
    assert_not_equal(var_notes.get('age'), None)
    assert_equal(var_types['browser'], mg.VAR_TYPE_CAT_KEY)
    assert_equal(val_dics['country'][1], 'Japan')
    