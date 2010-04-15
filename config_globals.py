#! /usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import os
import wx

# This module mustn't import anything local.
# It is used immediately after my_globals is loaded and needs to complete any 
# config (of my_globals) before other local modules are loaded so they can be
# assumed to be safe to start.  Other modules need to be able to rely on the 
# correctness of what is in my_globals. 
import my_globals as mg

def get_settings_dic(subfolder, fil_name):
    """
    Returns settings_dic with keys for each setting.
    """
    settings_path = os.path.join(mg.LOCAL_PATH, subfolder, fil_name)
    try:
        f = codecs.open(settings_path, "U", encoding="utf-8")
    except IOError:
        raise Exception, "Unable to get settings from non-existent file %s" % \
            settings_path
    settings_cont = f.read()
    f.close()
    if settings_cont.startswith(unicode(codecs.BOM_UTF8, "utf-8")):
        settings_cont = settings_cont[len(unicode(codecs.BOM_UTF8, "utf-8")):]
    settings_dic = {}
    try:
        # http://docs.python.org/reference/simple_stmts.html
        exec settings_cont in settings_dic
    except SyntaxError, e:
        wx.MessageBox(\
            _("Syntax error in settings file \"%s\"." % fil_name + \
                      os.linesep + os.linesep + "Details: %s" % unicode(e)))
        raise Exception, unicode(e)
    except Exception, e:
        wx.MessageBox(\
            _("Error processing settings file \"%s\"." % fil_name + \
                      os.linesep + os.linesep + "Details: %s" % unicode(e)))
        raise Exception, unicode(e)
    return settings_dic

def set_DEFAULT_LEVEL(ignore_prefs=False):
    """
    Update mg.DEFAULT_LEVEL (if any prefs set).
    ignore_prefs -- used if wanting to test different levels than in prefs doc
        from unit test.
    """
    if not ignore_prefs:
        try:
            prefs_dic = get_settings_dic(subfolder=mg.INT_FOLDER, 
                                         fil_name=mg.INT_PREFS_FILE)
            stored_lev = \
                prefs_dic[mg.PREFS_KEY][mg.DEFAULT_LEVEL_KEY]
            if stored_lev not in mg.LEVELS:
                raise Exception, "Invalid stored level: %s" % stored_lev
            mg.DEFAULT_LEVEL = stored_lev
        except Exception:
            mg.DEFAULT_LEVEL = mg.LEVEL_BRIEF
            