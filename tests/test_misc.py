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

#from .output import _strip_html
import my_globals
import dimtables
import importer
import output
import projects
import util
import dbe_plugins.dbe_sqlite as dbe_sqlite
import dbe_plugins.dbe_mysql as dbe_mysql
import dbe_plugins.dbe_postgresql as dbe_postgresql

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
        assert_equal(util.n2d(test[0]), test[1])

def test_is_basic_num(): # about type
    tests = [(5, True),
             ("5", False),
             (1.2, True),
             (decimal.Decimal("1"), False),
             ((1 + 2j), False),
             ("spam", False),
             ]
    for test in tests:
        assert_equal(util.is_basic_num(test[0]), test[1])

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
        assert_equal(util.is_numeric(test[0]), test[1])

def test_make_fld_val_clause():
    quote_vals = {my_globals.DBE_SQLITE: dbe_sqlite.quote_val,
                  my_globals.DBE_MYSQL: dbe_mysql.quote_val,
                  my_globals.DBE_PGSQL: dbe_postgresql.quote_val,
                  }
    # make_fld_val_clause(dbe, fld, val, bolnumeric, quote_val):
    tests = [((my_globals.DBE_SQLITE, "var", "fred", False, 
         quote_vals[my_globals.DBE_SQLITE]), "var = \"fred\""),
       ((my_globals.DBE_SQLITE, "var", 5, True, 
         quote_vals[my_globals.DBE_SQLITE]), "var = 5"),
       ((my_globals.DBE_SQLITE, "var", "spam", True, # numeric type but string
         quote_vals[my_globals.DBE_SQLITE]), "var = \"spam\""),
       ((my_globals.DBE_MYSQL, "var", "fred", False, 
         quote_vals[my_globals.DBE_MYSQL]), "var = \"fred\""),
       ((my_globals.DBE_MYSQL, "var", 5, True, 
         quote_vals[my_globals.DBE_MYSQL]), "var = 5"),
       ((my_globals.DBE_PGSQL, "var", "fred", False, 
         quote_vals[my_globals.DBE_PGSQL]), "var = 'fred'"),
       ((my_globals.DBE_PGSQL, "var", 5, True, 
         quote_vals[my_globals.DBE_PGSQL]), "var = 5"),
        ]
    for test in tests:
        assert_equal(dimtables.make_fld_val_clause(*test[0]), test[1])

def test_get_unicode():
    tests = [(r"C:\abcd\defg\foo.txt", u"C:\\abcd\\defg\\foo.txt"),
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
        assert_equal(util.get_unicode(test[0]), test[1])
        assert_true(isinstance(util.get_unicode(test[0]), unicode))

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
    proj_dic = projects.GetProjSettingsDic(\
                proj_name=my_globals.SOFA_DEFAULT_PROJ)
    var_labels, var_notes, var_types, val_dics = \
        projects.GetVarDets(proj_dic["fil_var_dets"])
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
    proj_dic = projects.GetProjSettingsDic(\
                proj_name=my_globals.SOFA_DEFAULT_PROJ)
    var_labels, var_notes, var_types, val_dics = \
        projects.GetVarDets(proj_dic["fil_var_dets"])
    assert_not_equal(var_labels.get('Name'), None)
    assert_not_equal(var_notes.get('age'), None)
    assert_equal(var_types['browser'][:11], "Categorical")
    assert_equal(val_dics['country'][1], "Japan")
    