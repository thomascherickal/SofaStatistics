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
import my_globals
import config_globals
import lib
import filtselect
import getdata
import importer
import indep2var
import output
import projects
import dbe_plugins.dbe_sqlite as dbe_sqlite
import dbe_plugins.dbe_mysql as dbe_mysql
import dbe_plugins.dbe_postgresql as dbe_postgresql

test_us_style = False
if test_us_style:
    my_globals.OK_DATE_FORMATS, my_globals.OK_DATE_FORMAT_EXAMPLES = \
        my_globals.get_date_fmt_lists(d_fmt=my_globals.MM_DD_YY)

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
    flds = {"numvar": {my_globals.FLD_BOLNUMERIC: True, 
                       my_globals.FLD_BOLDATETIME: False},
            "strvar": {my_globals.FLD_BOLNUMERIC: False, 
                       my_globals.FLD_BOLDATETIME: False},
            "datevar": {my_globals.FLD_BOLNUMERIC: False, 
                        my_globals.FLD_BOLDATETIME: True},
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
    equal_tests = [([u"spam", u"eggs", u"knights who say ni", u"Παντελής 2"], 
                    [u"spam", u"eggs", u"knights_who_say_ni", u"Παντελής_2"]),
                    ]
    for test in equal_tests:
        assert_equal(importer.process_fld_names(test[0]), test[1])
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
    tests = [(1, my_globals.FLD_TYPE_NUMERIC),
             (2, my_globals.FLD_TYPE_NUMERIC),
             (3, my_globals.FLD_TYPE_NUMERIC),
             (4, my_globals.FLD_TYPE_NUMERIC),
             (5, my_globals.FLD_TYPE_NUMERIC),
             (6, my_globals.FLD_TYPE_STRING),
             (7, my_globals.FLD_TYPE_DATE),
             (8, my_globals.FLD_TYPE_NUMERIC), # 2009 on own is a number
             (9, my_globals.FLD_TYPE_NUMERIC), # empty + numeric = numeric
             (10, my_globals.FLD_TYPE_STRING),
             (11, my_globals.FLD_TYPE_STRING), # empty + string (2009-01 is not 
                # number or datetime) = string
             ]
    for test in tests:
        assert_equal(importer.assess_sample_fld(sample_data, test[0]), test[1])

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
    flds = {"numvar": {my_globals.FLD_BOLNUMERIC: True, 
                       my_globals.FLD_BOLDATETIME: False},
            "strvar": {my_globals.FLD_BOLNUMERIC: False, 
                       my_globals.FLD_BOLDATETIME: False}}
    # make_fld_val_clause(dbe, flds, fld_name, val, gte)
    tests = [((my_globals.DBE_SQLITE, flds, "strvar", "fred"), 
            u"`strvar` = \"fred\""),
       ((my_globals.DBE_SQLITE, flds, "numvar", 5), 
            u"`numvar` = 5"),# num type but string
       ((my_globals.DBE_SQLITE, flds, "numvar", "spam"), 
            u"`numvar` = \"spam\""),
       ((my_globals.DBE_SQLITE, flds, "numvar", None), 
            u"`numvar` IS NULL"),
       ((my_globals.DBE_MYSQL, flds, "strvar", "fred"), 
            u"`strvar` = \"fred\""),
       ((my_globals.DBE_MYSQL, flds, "numvar", 5), 
            u"`numvar` = 5"),
       ((my_globals.DBE_MYSQL, flds, "numvar", None), 
            u"`numvar` IS NULL"),
       ((my_globals.DBE_PGSQL, flds, "strvar", "fred"), 
            u"\"strvar\" = 'fred'"),
       ((my_globals.DBE_PGSQL, flds, "numvar", 5), 
            u"\"numvar\" = 5"),
       ((my_globals.DBE_SQLITE, flds, "strvar", "fred", 
            my_globals.GTE_NOT_EQUALS), 
            u"`strvar` != \"fred\""),
       ((my_globals.DBE_SQLITE, flds, "numvar", 5, 
            my_globals.GTE_NOT_EQUALS), 
            u"`numvar` != 5"),# num type but string
       ((my_globals.DBE_SQLITE, flds, "numvar", "spam", 
            my_globals.GTE_NOT_EQUALS), 
            u"`numvar` != \"spam\""),
       ((my_globals.DBE_SQLITE, flds, "numvar", None, 
            my_globals.GTE_NOT_EQUALS), 
            u"`numvar` IS NOT NULL"),
       ((my_globals.DBE_MYSQL, flds, "strvar", "fred", 
            my_globals.GTE_NOT_EQUALS), 
            u"`strvar` != \"fred\""),
       ((my_globals.DBE_MYSQL, flds, "numvar", 5, 
            my_globals.GTE_NOT_EQUALS), 
            u"`numvar` != 5"),
       ((my_globals.DBE_MYSQL, flds, "numvar", None, 
            my_globals.GTE_NOT_EQUALS), 
            u"`numvar` IS NOT NULL"),
       ((my_globals.DBE_PGSQL, flds, "strvar", "fred", 
            my_globals.GTE_NOT_EQUALS), 
            u"\"strvar\" != 'fred'"),
       ((my_globals.DBE_PGSQL, flds, "numvar", 5, 
            my_globals.GTE_NOT_EQUALS), 
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
    tests = [("\nchunky chicken%s\nxzmxnzmxnz" % my_globals.SCRIPT_END, 
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
                                       fil_name=my_globals.SOFA_DEFAULT_PROJ)
    var_labels, var_notes, var_types, val_dics = \
        projects.get_var_dets(proj_dic["fil_var_dets"])
    fil_var_dets = proj_dic["fil_var_dets"]
    dbe = proj_dic["default_dbe"]
    con_dets = proj_dic["con_dets"]
    default_dbs = proj_dic["default_dbs"] \
        if proj_dic["default_dbs"] else {}
    default_tbls = proj_dic["default_tbls"] \
        if proj_dic["default_tbls"] else {}
    assert_equal(dbe, my_globals.DBE_SQLITE)
    assert_equal(default_dbs[my_globals.DBE_SQLITE], my_globals.SOFA_DEFAULT_DB)
    assert_equal(default_tbls[my_globals.DBE_SQLITE], 
                 my_globals.SOFA_DEFAULT_TBL)
    assert_equal(con_dets[my_globals.DBE_SQLITE][my_globals.SOFA_DEFAULT_DB]\
                 ['database'].split("/")[-1], my_globals.SOFA_DEFAULT_DB)    
    
def test_get_var_dets():
    """
    OK if fails because user deliberately changed settings
    if they are smart enough to do that they should be smart enough to change 
    this test too ;-)
    """
    proj_dic = config_globals.get_settings_dic(subfolder=u"projs", 
                                       fil_name=my_globals.SOFA_DEFAULT_PROJ)
    var_labels, var_notes, var_types, val_dics = \
        projects.get_var_dets(proj_dic["fil_var_dets"])
    assert_not_equal(var_labels.get('Name'), None)
    assert_not_equal(var_notes.get('age'), None)
    assert_equal(var_types['browser'], my_globals.VAR_TYPE_CAT)
    assert_equal(val_dics['country'][1], "Japan")
    