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
from .output import _strip_html
from .output import _strip_script
from .util import get_unicode
import my_globals
import dimtables
import projects
import util

# make_fld_val_clause(dbe, fld, val, bolnumeric, quote_val):
    
def test_make_fld_val_clause():
    
    tests = [(my_globals.DBE_SQLITE, "name", "fred", False, ), "name = 'fred'"),
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
             ]
    for test in tests:
        assert_equal(get_unicode(test[0]), test[1])
        assert_true(isinstance(get_unicode(test[0]), unicode))

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
             ]
    for test in tests:
        assert_equal(get_unicode(test[0]), test[1])
        assert_true(isinstance(get_unicode(test[0]), unicode))

def test_strip_html():
    tests = [("<body>Freddy</body>", "Freddy"), 
             ("<body>Freddy</body>Teddy</body>", "Freddy"),
             ("<body>Freddy", "Freddy"),
             ]
    for test in tests:
        assert_equal(_strip_html(test[0]), test[1])

def test_strip_script():
    tests = [("\nchunky chicken%s\nxzmxnzmxnz" % my_globals.SCRIPT_END, 
              "\nchunky chicken")]
    for test in tests:
        assert_equal(_strip_script(test[0]), test[1])
        
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
    conn_dets = proj_dic["conn_dets"]
    default_dbs = proj_dic["default_dbs"] \
        if proj_dic["default_dbs"] else {}
    default_tbls = proj_dic["default_tbls"] \
        if proj_dic["default_tbls"] else {}
    assert_equal(dbe, my_globals.DBE_SQLITE)
    assert_equal(default_dbs[my_globals.DBE_SQLITE], my_globals.SOFA_DEFAULT_DB)
    assert_equal(default_tbls[my_globals.DBE_SQLITE], 
                 my_globals.SOFA_DEFAULT_TBL)
    assert_equal(conn_dets[my_globals.DBE_SQLITE][my_globals.SOFA_DEFAULT_DB]\
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
    