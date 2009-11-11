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
from .output import _strip_html
from .output import _strip_script
from .util import get_path_to_display
import my_globals
import projects
import util

def test_get_path_to_display():
    """
    Microsoft used the backslash \ as a path delimiter.  This is a problem 
        because it indicates an escape sequence in Python strings.
    Raw strings are not a solution to this because we need to handle unicode at
        least some of the time.
    BTW u'C:\Users\...' creates special problems because \u is a special escape 
        to allow unicode strings to be represented by their code point number.
    Anyway, we should handle any string or path thrown at us including both 
        unicode and byte strings, plus backslashes and escaped backslashes.
    """    
    tests = [(r"C:\abcd\defg\foo.txt", r"C:\abcd\defg\foo.txt"),
             ("C:\\abcd\\defg\\foo.txt", r"C:\abcd\defg\foo.txt"),
             (u"C:\\abcd\\defg\\foo.txt", 
                r"C:\abcd\defg\foo.txt".decode("utf-8")),
             (u"C:\\unicodebait\\defg\\foo.txt", 
                r"C:\unicodebait\defg\foo.txt".decode("utf-8")),
             (u"C:\\Identität\\defg\\foo.txt", 
                r"C:\Identität\defg\foo.txt".decode("utf-8")),
             ("/home/g/abcd/foo.txt", "/home/g/abcd/foo.txt"),
             (u"/home/René/abcd/foo.txt", u"/home/René/abcd/foo.txt"),
             (u"/home/Identität/abcd/foo.txt", u"/home/Identität/abcd/foo.txt"),
             (u"/home/François/abcd/foo.txt", u"/home/François/abcd/foo.txt"),
             ]
    for test in tests:
        assert_equal(get_path_to_display(test[0]), test[1])

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
    