#! /usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import os

# This module mustn't import anything local.
# It is used immediately after my_globals is loaded and needs to complete any 
# config (of my_globals) before other local modules are loaded so they can be
# assumed to be safe to start.  Other modules need to be able to rely on the 
# correctness of what is in my_globals. 
import my_globals

def get_settings_dic(subfolder, fil_name):
    """
    Returns settings_dic with keys for each setting.
    """
    settings_path = os.path.join(my_globals.LOCAL_PATH, subfolder, fil_name)
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

def update_ok_date_formats_globals():
    try:
        prefs_dic = get_settings_dic(subfolder=my_globals.INTERNAL_FOLDER, 
                                     fil_name=my_globals.INT_PREFS_FILE)
    except Exception:
        return # if no settings, leave status quo
    if my_globals.DATE_FORMATS_IN_USE == my_globals.INT_DATE_ENTRY_FORMAT:
        extra_ok_date_formats = ["%d-%m-%y", "%d/%m/%y", "%d-%m-%Y", "%d/%m/%Y"]
        my_globals.OK_DATE_FORMAT_EXAMPLES = ["31/3/09", "2:30pm 31/3/2009"]
    else:
        # needed for US, Canada, the Philippines etc
        extra_ok_date_formats = ["%m-%d-%y", "%m/%d/%y", "%m-%d-%Y", "%m/%d/%Y"]
        my_globals.OK_DATE_FORMAT_EXAMPLES = ["3/31/09", "2:30pm 3/31/2009"]
    my_globals.OK_DATE_FORMATS =  extra_ok_date_formats + \
        my_globals.ALWAYS_OK_DATE_FORMATS