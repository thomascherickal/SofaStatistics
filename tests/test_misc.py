#! /usr/bin/env python
# -*- coding: utf-8 -*-

# cd into this folder
# http://somethingaboutorange.com/mrl/projects/nose/0.11.1/usage.html
# nosetests test_misc.py
# nosetests test_misc.py:test_get_path
import gettext
gettext.install('sofa', './locale', unicode=True)
from nose.tools import assert_equal
from nose.tools import assert_not_equal
from nose.tools import assert_raises
from nose.tools import assert_true
import decimal
import time

#from .output import _strip_html
import my_globals as mg
import config_globals
import lib
import config_dlg
import csv_importer
import filtselect
import getdata
import importer
import indep2var
import output
import recode
import report_table
import table_config
import dbe_plugins.dbe_sqlite as dbe_sqlite
import dbe_plugins.dbe_mysql as dbe_mysql
import dbe_plugins.dbe_postgresql as dbe_postgresql

def test_process_orig():
    fld = u"bar"
    tests = [((u"Spam TO Eggs", fld, mg.FLD_TYPE_STRING), 
              u"`bar` BETWEEN \"Spam\" AND \"Eggs\""),
             ((u"1 TO 3", fld, mg.FLD_TYPE_NUMERIC), 
              u"`bar` BETWEEN 1 AND 3"),
             ((u" ", fld, mg.FLD_TYPE_STRING), 
              u"`bar` = \" \""),
             ((u"1 TO MAX", fld, mg.FLD_TYPE_NUMERIC), 
              u"`bar` >= 1"),
             ((u"1 TO MAX", fld, mg.FLD_TYPE_STRING), 
              u"`bar` >= \"1\""),
             ((u"MIN TO MAX", fld, mg.FLD_TYPE_STRING), 
              u"`bar` IS NOT NULL"),
             ((u"MIN TO MAX", fld, mg.FLD_TYPE_DATE), 
              u"`bar` IS NOT NULL"),
             ((u"MIN TO 2010-06-22 00:00:00", fld, mg.FLD_TYPE_DATE), 
              u"`bar` <= \"2010-06-22 00:00:00\""),
             ((u"MINTO10776", fld, mg.FLD_TYPE_NUMERIC), 
              u"`bar` <= 10776"),
             ((u"1 to 6", fld, mg.FLD_TYPE_STRING), 
              u"`bar` = \"1 to 6\""),
             ((u"-1 TO 26", fld, mg.FLD_TYPE_NUMERIC), 
              u"`bar` BETWEEN -1 AND 26"),
             ((u" MISSING ", fld, mg.FLD_TYPE_NUMERIC), 
              u"`bar` IS NULL"),
            ]
    for test in tests:
        assert_equal(recode.process_orig(*test[0]), test[1])
    raises_tests = [(1, fld, mg.FLD_TYPE_STRING),
                    (u"TO 21", fld, mg.FLD_TYPE_STRING),
                    (u"Spam TO MIN", fld, mg.FLD_TYPE_STRING),
                    (u"MAX TO Spam", fld, mg.FLD_TYPE_STRING),
                    (u"spam", fld, mg.FLD_TYPE_NUMERIC),
                    (u" REMAINING ", fld, mg.FLD_TYPE_NUMERIC), 
                    ]
    for test in raises_tests:
        #http://www.ibm.com/developerworks/aix/library/au-python_test/index.html
        assert_raises(Exception, recode.process_orig, test)

def test_has_data_changed():
    """
    The original data is in the form of a list of tuples - the tuples are 
        field name and type.
    The final data is a list of dicts, with keys for:
        mg.TBL_FLD_NAME, 
        mg.TBL_FLD_NAME_ORIG,
        mg.TBL_FLD_TYPE,
        mg.TBL_FLD_TYPE_ORIG.
    Different if TBL_FLD_NAME != TBL_FLD_NAME_ORIG
    Different if TBL_FLD_TYPE != TBL_FLD_TYPE_ORIG
    Different if set of TBL_FLD_NAMEs not same as set of field names. 
    NB Need first two checks in case names swapped.  Sets wouldn't change 
        but data would have changed.
    """
    string = mg.FLD_TYPE_STRING
    num = mg.FLD_TYPE_NUMERIC
    orig_data1 = [(u'sofa_id', num), (u'var001', string), 
                  (u'var002', string), (u'var003', string)]
    final_data1 = [ {'fld_name_orig': u'sofa_id', 'fld_name': u'sofa_id', 
                        'fld_type': num, 'fld_type_orig': num}, 
                    {'fld_name_orig': u'var001', 'fld_name': u'var001', 
                        'fld_type': string, 'fld_type_orig': string}, 
                    {'fld_name_orig': u'var002', 'fld_name': u'var002', 
                        'fld_type': string, 'fld_type_orig': string}, 
                    {'fld_name_orig': u'var003', 'fld_name': u'var003', 
                        'fld_type': string, 'fld_type_orig': string}]
    # renamed a field
    final_data2 = [ {'fld_name_orig': u'sofa_id', 'fld_name': u'sofa_id2', 
                        'fld_type': num, 'fld_type_orig': num}, 
                    {'fld_name_orig': u'var001', 'fld_name': u'var001', 
                        'fld_type': string, 'fld_type_orig': string}, 
                    {'fld_name_orig': u'var002', 'fld_name': u'var002', 
                        'fld_type': string, 'fld_type_orig': string}, 
                    {'fld_name_orig': u'var003', 'fld_name': u'var003', 
                        'fld_type': string, 'fld_type_orig': string}]
    # deleted a field
    final_data3 = [ {'fld_name_orig': u'sofa_id', 'fld_name': u'sofa_id', 
                        'fld_type': num, 'fld_type_orig': num}, 
                    {'fld_name_orig': u'var001', 'fld_name': u'var001', 
                        'fld_type': string, 'fld_type_orig': string}, 
                    {'fld_name_orig': u'var003', 'fld_name': u'var003', 
                        'fld_type': string, 'fld_type_orig': string}]
    # changed fld type to Numeric
    final_data4 = [ {'fld_name_orig': u'sofa_id', 'fld_name': u'sofa_id', 
                        'fld_type': num, 'fld_type_orig': num}, 
                    {'fld_name_orig': u'var001', 'fld_name': u'var001', 
                        'fld_type': string, 'fld_type_orig': string}, 
                    {'fld_name_orig': u'var002', 'fld_name': u'var002', 
                        'fld_type': string, 'fld_type_orig': num}, 
                    {'fld_name_orig': u'var003', 'fld_name': u'var003', 
                        'fld_type': string, 'fld_type_orig': string}]
    # swapped but same final (still changed)
    final_data5 = [ {'fld_name_orig': u'sofa_id', 'fld_name': u'sofa_id', 
                        'fld_type': num, 'fld_type_orig': num}, 
                    {'fld_name_orig': u'var001', 'fld_name': u'var002', 
                        'fld_type': string, 'fld_type_orig': string}, 
                    {'fld_name_orig': u'var002', 'fld_name': u'var001', 
                        'fld_type': string, 'fld_type_orig': string}, 
                    {'fld_name_orig': u'var003', 'fld_name': u'var003', 
                        'fld_type': string, 'fld_type_orig': string}]
    # added a field
    final_data6 = [ {'fld_name_orig': u'sofa_id', 'fld_name': u'sofa_id', 
                        'fld_type': num, 'fld_type_orig': num},  
                    {'fld_name_orig': None, 'fld_name': u'spam', 
                        'fld_type': None, 'fld_type_orig': string},
                    {'fld_name_orig': u'var001', 'fld_name': u'var001', 
                        'fld_type': string, 'fld_type_orig': string}, 
                    {'fld_name_orig': u'var002', 'fld_name': u'var002', 
                        'fld_type': string, 'fld_type_orig': string}, 
                    {'fld_name_orig': u'var003', 'fld_name': u'var003', 
                        'fld_type': string, 'fld_type_orig': string}]
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
               [None, None, None, None,], # -> ",,," i.e. 3 long
               [u"\u0195\u0164",], # -> ä i.e. 2 bytes long in utf-8 but 1 in latin1
               ], 
              2.5),
             ([
               [None, None, None, None,], # -> ",,," i.e. 3 long
               [u"ä",], # -> 1 byte long in unicode and in latin1
               ], 
              2.0),
             ]
    for test in tests:
        assert_equal(csv_importer.get_avg_row_size(test[0]), test[1])

def test_get_next_fld_name():
    """
    Get next available variable name where names follow a template e.g. var001,
        var002 etc.If a gap, starts after last one.  Gaps are not filled.
    """
    tests = [([u"var001",], u"var002"),
             ([u"var001", u"var003"], u"var004"),
             ([u"var001", u"Var003"], u"var002"),
             ([u"fld001", u"Identität", u"Identität002"], u"var001"),
             ]
    for test in tests:
        assert_equal(lib.get_next_fld_name(test[0]), test[1])    

css_path_tests = [(u"default", u"/home/g/sofa/css/default.css"),
                  (u"Identität", u"/home/g/sofa/css/Identität.css"),
                  ]

def test_path2style():
    "Strip style out of full css path"
    for test in css_path_tests:
        assert_equal(config_dlg.path2style(test[1]), test[0])

def test_style2path():
    "Get full path of css file from style name alone"
    for test in css_path_tests:
        assert_equal(config_dlg.style2path(test[0]), test[1])

def test_replace_titles_subtitles():
    """
    For testing, use minimal css to keep it compact enough to understand easily.
    """
    orig1 = u"""<p class='gui-msg-medium'>Example data - click 'Run' for actual 
        results<br>&nbsp;&nbsp;or keep configuring</p>

        <!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
        'http://www.w3.org/TR/html4/loose.dtd'>
        <html>
        <head>
        <meta http-equiv="P3P" content='CP="IDC DSP COR CURa ADMa OUR 
        IND PHY ONL COM STA"'>
        <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
        <title>Report(s)</title>
        <style type="text/css">
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
        <span class='tbltitle0'><!--_title_start--><!--_title_end--></span>
        <span class='tblsubtitle0'><!--_subtitle_start--><!--_subtitle_end--></span></th></tr>
        <tr><th class='spaceholder0' rowspan='1' colspan='2'>&nbsp;&nbsp;</th><th class='measure0'  >Freq</th></tr>
        </thead>
        
        <tbody>
        <tr><td class='firstrowvar0'  rowspan='2'  >Car</td><td class='rowval0'  >BMW</td><td class='firstdatacell0'>2.5</td></tr>
        <tr><td class='rowval0'  >PORSCHE</td><td class='firstdatacell0'>1.5</td></tr>
        </tbody>
        </table>
        </body>
        </html>"""
    titles1 = [u'T']
    subtitles1 = []
    output1 = u"""<p class='gui-msg-medium'>Example data - click 'Run' for actual 
        results<br>&nbsp;&nbsp;or keep configuring</p>

        <!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
        'http://www.w3.org/TR/html4/loose.dtd'>
        <html>
        <head>
        <meta http-equiv="P3P" content='CP="IDC DSP COR CURa ADMa OUR 
        IND PHY ONL COM STA"'>
        <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
        <title>Report(s)</title>
        <style type="text/css">
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
        <span class='tbltitle0'><!--_title_start-->T<!--_title_end--></span>
        <span class='tblsubtitle0'><!--_subtitle_start--><!--_subtitle_end--></span></th></tr>
        <tr><th class='spaceholder0' rowspan='1' colspan='2'>&nbsp;&nbsp;</th><th class='measure0'  >Freq</th></tr>
        </thead>
        
        <tbody>
        <tr><td class='firstrowvar0'  rowspan='2'  >Car</td><td class='rowval0'  >BMW</td><td class='firstdatacell0'>2.5</td></tr>
        <tr><td class='rowval0'  >PORSCHE</td><td class='firstdatacell0'>1.5</td></tr>
        </tbody>
        </table>
        </body>
        </html>"""
    orig2 = u"""<p class='gui-msg-medium'>Example data - click 'Run' for 
        actual results<br>&nbsp;&nbsp;or keep configuring</p>

        <!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
        'http://www.w3.org/TR/html4/loose.dtd'>
        <html>
        <head>
        <meta http-equiv="P3P" content='CP="IDC DSP COR CURa ADMa OUR 
        IND PHY ONL COM STA"'>
        <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
        <title>Report(s)</title>
        <style type="text/css">
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
        <span class='tbltitle0'><!--_title_start-->1<br>2<!--_title_end--></span>
        <span class='tblsubtitle0'><!--_subtitle_start--><br>3<br>4<br><!--_subtitle_end--></span></th></tr>
        <tr><th class='spaceholder0' rowspan='1' colspan='2'>&nbsp;&nbsp;</th><th class='measure0'  >Freq</th></tr>
        </thead>
        
        <tbody>
        <tr><td class='firstrowvar0'  rowspan='2'  >Car</td><td class='rowval0'  >BMW</td><td class='firstdatacell0'>2.5</td></tr>
        <tr><td class='rowval0'  >PORSCHE</td><td class='firstdatacell0'>1.5</td></tr>
        </tbody>
        </table>
        </body>
        </html>"""
    titles2 = [u'1', u'2']
    subtitles2 = [u'3', u'4', u'5']
    output2 = u"""<p class='gui-msg-medium'>Example data - click 'Run' for 
        actual results<br>&nbsp;&nbsp;or keep configuring</p>

        <!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
        'http://www.w3.org/TR/html4/loose.dtd'>
        <html>
        <head>
        <meta http-equiv="P3P" content='CP="IDC DSP COR CURa ADMa OUR 
        IND PHY ONL COM STA"'>
        <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
        <title>Report(s)</title>
        <style type="text/css">
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
        <span class='tbltitle0'><!--_title_start-->1<br>2<!--_title_end--></span>
        <span class='tblsubtitle0'><!--_subtitle_start--><br>3<br>4<br>5<!--_subtitle_end--></span></th></tr>
        <tr><th class='spaceholder0' rowspan='1' colspan='2'>&nbsp;&nbsp;</th><th class='measure0'  >Freq</th></tr>
        </thead>
        
        <tbody>
        <tr><td class='firstrowvar0'  rowspan='2'  >Car</td><td class='rowval0'  >BMW</td><td class='firstdatacell0'>2.5</td></tr>
        <tr><td class='rowval0'  >PORSCHE</td><td class='firstdatacell0'>1.5</td></tr>
        </tbody>
        </table>
        </body>
        </html>"""
    tests = [((orig1, titles1, subtitles1), output1),
             ((orig2, titles2, subtitles2), output2),
             ]
    for test in tests:
        assert_equal(report_table.replace_titles_subtitles(*test[0]), test[1])

def test_rel2abs_links():
    """
    Make all images work of absolute rather than relative paths.  Will run OK
        when displayed internally in GUI.
    Make normal images absolute: turn my_report_name/001.png to e.g. 
        /home/g/sofa/reports/my_report_name/001.png so that the html can be 
        written to, and read from, anywhere (and still show the images!) in the
        temporary GUI displays.
    Make background images absolute: turn ../images/tile.gif to 
        /home/g/sofa/images/tile.gif.
    """
    tests = [
        ("<h1>Hi there!</h1><img src='my report name/my_img.png'", 
        "<h1>Hi there!</h1><img src='/home/g/sofa/reports/my report name/" + \
            "my_img.png'"),
        (u"<h1>Hi there!</h1><img src=\"Identität/my_img.png\"", 
        u"<h1>Hi there!</h1><img src=\"/home/g/sofa/reports/Identität/" + \
            u"my_img.png\""),
        ]
    for test in tests:
        assert_equal(lib.rel2abs_links(test[0]), test[1])
        
test_us_style = False
if test_us_style:
    mg.OK_DATE_FORMATS, mg.OK_DATE_FORMAT_EXAMPLES = \
        mg.get_date_fmt_lists(d_fmt=mg.MDY)

def test_is_usable_datetime_str():
    tests = [("June 2009", False),
             ("1901", True),
             ("1876", True),
             ("1666-09-02", True),
             ("1666/09/02", False), # wrong order if using slashes
             ("31.3.1988", True),
             ]
    if test_us_style:
        tests.extend([
             ("31/3/88", False),
             ("3/31/88", True),
             ])
    else:
        tests.extend([
             ("31/3/88", True),
             ("3/31/88", False),
             ])    
    for test in tests:
        assert_equal(lib.is_usable_datetime_str(test[0]), test[1])

def test_get_std_datetime_str():
    ymd = "%4d-%02d-%02d" % time.localtime()[:3]
    tests = [("2pm", "%s 14:00:00" % ymd),
             ("14:30", "%s 14:30:00" % ymd),
             ("2009-01-31", "2009-01-31 00:00:00"),
             ("11am 2009-01-31", "2009-01-31 11:00:00"),
             ("2009-01-31 3:30pm", "2009-01-31 15:30:00"),
             ("12.2.2001 2:35pm", "2001-02-12 14:35:00"),
             ("12.2.01 2:35pm", "2001-02-12 14:35:00"),
             ]
    if test_us_style:
        tests.extend([
             ("09/02/1666 00:12:16", "1666-09-02 00:12:16"), #http://en.wikipedia.org/wiki/Great_Fire_of_London
             ("3/31/88", "1988-03-31 00:00:00"),
             ])
    else:
        tests.extend([
             ("02/09/1666 00:12:16", "1666-09-02 00:12:16"), #http://en.wikipedia.org/wiki/Great_Fire_of_London
             ("31/3/88", "1988-03-31 00:00:00"),
             ])    
    for test in tests:
        assert_equal(lib.get_std_datetime_str(test[0]), test[1])
        
def test_get_dets_of_usable_datetime_str():
    # date_part, date_format, time_part, time_format, boldate_then_time
    tests = [("2009", ("2009", "%Y", None, None, True)),
             ("2009-01-31", ("2009-01-31", "%Y-%m-%d", None, None, True)),
             ("2pm", (None, None, "2pm", "%I%p", True)),
             ("2:30pm", (None, None, "2:30pm", "%I:%M%p", True)),
             ("14:30", (None, None, "14:30", "%H:%M", True)),
             ("14:30:00", (None, None, "14:30:00", "%H:%M:%S", True)),
             ("2009-01-31 14:03:00", ("2009-01-31", "%Y-%m-%d", "14:03:00", 
                                      "%H:%M:%S", True)),
             ("14:03:00 2009-01-31", ("2009-01-31", "%Y-%m-%d", "14:03:00", 
                                      "%H:%M:%S", False)),
             ("1am 2009-01-31", ("2009-01-31", "%Y-%m-%d", "1am", "%I%p", 
                                 False)),
             ("31.3.1988", ("31.3.1988", "%d.%m.%Y", None, None, True)),
             ("31.3.1988 2:45am", ("31.3.1988", "%d.%m.%Y", "2:45am", "%I:%M%p", 
                            True)),
             ("31.3.88 2:45am", ("31.3.88", "%d.%m.%y", "2:45am", "%I:%M%p", 
                            True)),
             ]
    if test_us_style:
        tests.extend([
             ("01/31/2009", ("01/31/2009", "%m/%d/%Y", None, None, True)),
             ("1/31/2009", ("1/31/2009", "%m/%d/%Y", None, None, True)),
             ("01/31/09", ("01/31/09", "%m/%d/%y", None, None, True)),
             ("1/31/09", ("1/31/09", "%m/%d/%y", None, None, True)),
             ])
    else:
        tests.extend([
             ("31/01/2009", ("31/01/2009", "%d/%m/%Y", None, None, True)),
             ("31/1/2009", ("31/1/2009", "%d/%m/%Y", None, None, True)),
             ("31/01/09", ("31/01/09", "%d/%m/%y", None, None, True)),
             ("31/1/09", ("31/1/09", "%d/%m/%y", None, None, True)),
             ])  
    for test in tests:
        assert_equal(lib.get_dets_of_usable_datetime_str(test[0]), test[1])

def test_get_val():
    "Must be useful for making WHERE clauses"
    flds = {"numvar": {mg.FLD_BOLNUMERIC: True, 
                       mg.FLD_BOLDATETIME: False},
            "strvar": {mg.FLD_BOLNUMERIC: False, 
                       mg.FLD_BOLDATETIME: False},
            "datevar": {mg.FLD_BOLNUMERIC: False, 
                        mg.FLD_BOLDATETIME: True},
            }
    tests = [(("12", flds, "numvar"), 12),
             (("", flds, "numvar"), None),
             (("NuLL", flds, "numvar"), None),
             (("NULL", flds, "strvar"), None),
             (("", flds, "strvar"), ""),
             (("12", flds, "strvar"), "12"),
             (("", flds, "datevar"), None),
             (("nuLL", flds, "datevar"), None),
             (("2009-01-31", flds, "datevar"), "2009-01-31 00:00:00"),
             (("2009", flds, "datevar"), "2009-01-01 00:00:00"),
             ]
    for test in tests:
        assert_equal(filtselect.get_val(*test[0]), test[1])

def test_get_range_idxs():
    """
    val_a and val_b are deliberately wrapped in double quotes if strings by 
        all valid inputs to this function.
    """
    tests = [
        ([1, 2, 3, 4, 5], u"1", u"3", (0, 2)),
        ([u'Chrome', u'Firefox', u"Internet Explorer", u"Safari"],
            u'"Firefox"', u'"Internet Explorer"', (1, 2)),
        (['1000000000000.1', '1000000000000.2', '1000000000000.3', 
                '1000000000000.4', '1000000000000.5', '1000000000000.6'], 
            u'1000000000000.2', u'1000000000000.4', (1, 3)),
             ]
    for vals, val_a, val_b, idx_tup in tests:
        assert_equal(indep2var.get_range_idxs(vals, val_a, val_b), idx_tup)

def test_process_fld_names():
    "Spaces to underscores, only valid SQLite table and field names"
    equal_tests = [([u"spam", u"eggs.", u"knights who say ni", u"Παντελής 2"], 
                    [u"spam", u"eggs.", u"knights_who_say_ni", u"Παντελής_2"]),
                    ]
    for test in equal_tests:
        assert_equal(importer.process_fld_names(test[0]), test[1])
    # the two unladen swallows will become the same as space -> underscore
    raises_tests = [[u"unladen swallow", u"unladen_swallow", u"spam", u"eggs"],
                    [5, u"6"],
                    ]
    for test in raises_tests:
        #http://www.ibm.com/developerworks/aix/library/au-python_test/index.html
        assert_raises(Exception, importer.process_fld_names, test)

def test_assess_sample_fld():
    sample_data = [{1: "2", 
                   2: "2.0", 
                   3: 2, 
                   4: 2.0, 
                   5: "1.245e10",
                   6: "spam",
                   7: "2009-01-31",
                   8: "2009",
                   9: "",
                   10: "",
                   11: 5},
                   {1: "2", 
                   2: "2.0", 
                   3: 2, 
                   4: 2.0, 
                   5: "1.245e10",
                   6: "spam",
                   7: "2009-01-31",
                   8: "2009",
                   9: 5,
                   10: "",
                   11: "2009-01"}
                   ]
    # fld name, expected type
    tests = [(1, mg.FLD_TYPE_NUMERIC),
             (2, mg.FLD_TYPE_NUMERIC),
             (3, mg.FLD_TYPE_NUMERIC),
             (4, mg.FLD_TYPE_NUMERIC),
             (5, mg.FLD_TYPE_NUMERIC),
             (6, mg.FLD_TYPE_STRING),
             (7, mg.FLD_TYPE_DATE),
             (8, mg.FLD_TYPE_NUMERIC), # 2009 on own is a number
             (9, mg.FLD_TYPE_NUMERIC), # empty + numeric = numeric
             (10, mg.FLD_TYPE_STRING),
             (11, mg.FLD_TYPE_STRING), # empty + string (2009-01 is not 
                # number or datetime) = string
             ]
    has_header = False
    for test in tests:
        assert_equal(importer.assess_sample_fld(sample_data, has_header, 
                                                test[0], range(1,12), True), 
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
    tests = [(1, D("1")),
             (-1, D("-1")),
             ("34", D("34")),
             ("34.00", D("34")),
             (1.00000, D("1")),
             (1.002e3, D("1002")),
             ]
    for test in tests:
        assert_equal(lib.n2d(test[0]), test[1])

def test_is_basic_num(): # about type
    tests = [(5, True),
             ("5", False),
             (1.2, True),
             (decimal.Decimal("1"), False),
             ((1 + 2j), False),
             ("spam", False),
             ]
    for test in tests:
        assert_equal(lib.is_basic_num(test[0]), test[1])

def test_is_numeric(): # about content
    tests = [(5, True),
             (1.000003, True),
             (0.0000001, True),
             ("5", True),
             ("1e+10", True),
             ("e+10", False),
             ("spam", False),
             ("2010-01-01", False),
             (314j, False),
             (1 + 14j, False),
             ((1 + 14j), False),
             ]
    for test in tests:
        print(test)
        assert_equal(lib.is_numeric(test[0]), test[1])

def test_make_fld_val_clause():
    flds = {"numvar": {mg.FLD_BOLNUMERIC: True, 
                       mg.FLD_BOLDATETIME: False},
            "strvar": {mg.FLD_BOLNUMERIC: False, 
                       mg.FLD_BOLDATETIME: False}}
    # make_fld_val_clause(dbe, flds, fld_name, val, gte)
    tests = [((mg.DBE_SQLITE, flds, "strvar", "fred"), 
            u"`strvar` = \"fred\""),
       ((mg.DBE_SQLITE, flds, "numvar", 5), 
            u"`numvar` = 5"),# num type but string
       ((mg.DBE_SQLITE, flds, "numvar", "spam"), 
            u"`numvar` = \"spam\""),
       ((mg.DBE_SQLITE, flds, "numvar", None), 
            u"`numvar` IS NULL"),
       ((mg.DBE_MYSQL, flds, "strvar", "fred"), 
            u"`strvar` = \"fred\""),
       ((mg.DBE_MYSQL, flds, "numvar", 5), 
            u"`numvar` = 5"),
       ((mg.DBE_MYSQL, flds, "numvar", None), 
            u"`numvar` IS NULL"),
       ((mg.DBE_PGSQL, flds, "strvar", "fred"), 
            u"\"strvar\" = 'fred'"),
       ((mg.DBE_PGSQL, flds, "numvar", 5), 
            u"\"numvar\" = 5"),
       ((mg.DBE_SQLITE, flds, "strvar", "fred", 
            mg.GTE_NOT_EQUALS), 
            u"`strvar` != \"fred\""),
       ((mg.DBE_SQLITE, flds, "numvar", 5, 
            mg.GTE_NOT_EQUALS), 
            u"`numvar` != 5"),# num type but string
       ((mg.DBE_SQLITE, flds, "numvar", "spam", 
            mg.GTE_NOT_EQUALS), 
            u"`numvar` != \"spam\""),
       ((mg.DBE_SQLITE, flds, "numvar", None, 
            mg.GTE_NOT_EQUALS), 
            u"`numvar` IS NOT NULL"),
       ((mg.DBE_MYSQL, flds, "strvar", "fred", 
            mg.GTE_NOT_EQUALS), 
            u"`strvar` != \"fred\""),
       ((mg.DBE_MYSQL, flds, "numvar", 5, 
            mg.GTE_NOT_EQUALS), 
            u"`numvar` != 5"),
       ((mg.DBE_MYSQL, flds, "numvar", None, 
            mg.GTE_NOT_EQUALS), 
            u"`numvar` IS NOT NULL"),
       ((mg.DBE_PGSQL, flds, "strvar", "fred", 
            mg.GTE_NOT_EQUALS), 
            u"\"strvar\" != 'fred'"),
       ((mg.DBE_PGSQL, flds, "numvar", 5, 
            mg.GTE_NOT_EQUALS), 
            u"\"numvar\" != 5"),
        ]
    for test in tests:
        assert_equal(getdata.make_fld_val_clause(*test[0]), test[1])

def test_any2unicode():
    tests = [
     (1, u"1"),
     (0.3, u"0.3"),
     (10000000000.2, u"10000000000.2"),
     (1000000000000000.2, u"1000000000000000.2"), # fails if any longer
     (r"C:\abcd\defg\foo.txt", u"C:\\abcd\\defg\\foo.txt"),
     ("C:\\abcd\\defg\\foo.txt", u"C:\\abcd\\defg\\foo.txt"),
     (u"C:\\abcd\\defg\\foo.txt", u"C:\\abcd\\defg\\foo.txt"),
     (u"C:\\unicodebait\\foo.txt", u"C:\\unicodebait\\foo.txt"),
     (u"C:\\Identität\\foo.txt", u"C:\\Identität\\foo.txt"),
     (r"/home/g/abcd/foo.txt", u"/home/g/abcd/foo.txt"),
     ("/home/g/abcd/foo.txt", u"/home/g/abcd/foo.txt"),
     (u"/home/René/abcd/foo.txt", u"/home/René/abcd/foo.txt"),
     (u"/home/Identität/abcd/foo.txt", u"/home/Identität/abcd/foo.txt"),
     (u"/home/François/abcd/foo.txt", u"/home/François/abcd/foo.txt"),
     (u"\x93fred\x94", u"\u201Cfred\u201D"),
     (r"C:\Documents and Settings\Παντελής\sofa\_internal", 
      u'C:\\Documents and Settings\\\u03a0\u03b1\u03bd\u03c4\u03b5\u03bb\u03ae\u03c2\\sofa\\_internal')
             ]
    for test in tests:
        assert_equal(lib.any2unicode(test[0]), test[1])
        assert_true(isinstance(lib.any2unicode(test[0]), unicode))

def test_str2unicode():
    tests = [
     (r"C:\abcd\defg\foo.txt", u"C:\\abcd\\defg\\foo.txt"),
     ("C:\\abcd\\defg\\foo.txt", u"C:\\abcd\\defg\\foo.txt"),
     (u"C:\\abcd\\defg\\foo.txt", u"C:\\abcd\\defg\\foo.txt"),
     (u"C:\\unicodebait\\foo.txt", u"C:\\unicodebait\\foo.txt"),
     (u"C:\\Identität\\foo.txt", u"C:\\Identität\\foo.txt"),
     (r"/home/g/abcd/foo.txt", u"/home/g/abcd/foo.txt"),
     ("/home/g/abcd/foo.txt", u"/home/g/abcd/foo.txt"),
     (u"/home/René/abcd/foo.txt", u"/home/René/abcd/foo.txt"),
     (u"/home/Identität/abcd/foo.txt", u"/home/Identität/abcd/foo.txt"),
     (u"/home/François/abcd/foo.txt", u"/home/François/abcd/foo.txt"),
     (u"\x93fred\x94", u"\u201Cfred\u201D"),
     (r"C:\Documents and Settings\Παντελής\sofa\_internal", 
      u'C:\\Documents and Settings\\\u03a0\u03b1\u03bd\u03c4\u03b5\u03bb\u03ae\u03c2\\sofa\\_internal')
             ]
    for test in tests:
        assert_equal(lib.str2unicode(test[0]), test[1])
        assert_true(isinstance(lib.str2unicode(test[0]), unicode))

def test_strip_html():
    tests = [("<body>Freddy</body>", "Freddy"), 
             ("<body>Freddy</body>Teddy</body>", "Freddy"),
             ("<body>Freddy", "Freddy"),
             ]
    for test in tests:
        assert_equal(output._strip_html(test[0]), test[1])

def test_strip_script():
    tests = [("\nchunky chicken%s\nxzmxnzmxnz" % mg.SCRIPT_END, 
              "\nchunky chicken")]
    for test in tests:
        assert_equal(output._strip_script(test[0]), test[1])
        
def test_sofa_default_proj_settings():
    """
    OK if fails because user deliberately changed settings
    if they are smart enough to do that they should be smart enough to change 
    this test too ;-)
    """
    proj_dic = config_globals.get_settings_dic(subfolder=u"projs", 
                                       fil_name=mg.DEFAULT_PROJ)
    var_labels, var_notes, var_types, val_dics = \
                                    lib.get_var_dets(proj_dic["fil_var_dets"])
    fil_var_dets = proj_dic["fil_var_dets"]
    dbe = proj_dic["default_dbe"]
    con_dets = proj_dic["con_dets"]
    default_dbs = proj_dic["default_dbs"] \
        if proj_dic["default_dbs"] else {}
    default_tbls = proj_dic["default_tbls"] \
        if proj_dic["default_tbls"] else {}
    assert_equal(dbe, mg.DBE_SQLITE)
    assert_equal(default_dbs[mg.DBE_SQLITE], mg.SOFA_DB)
    assert_equal(default_tbls[mg.DBE_SQLITE], mg.DEMO_TBL)
    assert_equal(con_dets[mg.DBE_SQLITE][mg.SOFA_DB]['database'].split("/")[-1], 
                 mg.SOFA_DB)    
    
def test_get_var_dets():
    """
    OK if fails because user deliberately changed settings
    if they are smart enough to do that they should be smart enough to change 
    this test too ;-)
    """
    proj_dic = config_globals.get_settings_dic(subfolder=u"projs", 
                                               fil_name=mg.DEFAULT_PROJ)
    var_labels, var_notes, var_types, val_dics = \
                                    lib.get_var_dets(proj_dic["fil_var_dets"])
    assert_not_equal(var_labels.get('Name'), None)
    assert_not_equal(var_notes.get('age'), None)
    assert_equal(var_types['browser'], mg.VAR_TYPE_CAT)
    assert_equal(val_dics['country'][1], "Japan")
    