#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import codecs
from datetime import datetime
import locale
import os
import pprint
import time
import wx

import my_globals as mg
import lib
import my_exceptions
import getdata
import config_dlg
import showhtml

# do not use os.linesep for anything going to be read and exec'd
# in Windows the \r\n makes it fail.

dd = getdata.get_dd()
cc = config_dlg.get_cc()

def get_default_css():
    """
    Get default CSS.  The "constants" are used so that we can 
        guarantee the class names we use later on are the same as
        used here.
    """
    default_css = u"""
        body{
            font-size: 12px;
        }
        h1, h2{
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
        }
        h1{
            font-size: 18px;
        }
        h2{
            font-size: 16px;
        }
        tr, td, th{
            margin: 0;
        }
        .%s{""" % mg.CSS_TBL_TITLE_CELL + u"""
            border: none;
            padding: 18px 0px 12px 0px;
            margin: 0;
        }
        .%s{""" % mg.CSS_TBL_TITLE + u"""
            padding: 0;
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 18px;
        }
        .%s{ """ % mg.CSS_TBL_SUBTITLE + u"""
            padding: 12px 0px 0px 0px;
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 14px;
        }
        th, .%s, .%s, .%s, .%s {""" % (mg.CSS_ROW_VAR, mg.CSS_ROW_VAL, 
                                mg.CSS_DATACELL, mg.CSS_FIRST_DATACELL) + u"""
            border: solid 1px #A1A1A1;
        }
        th{
            margin: 0;
            padding: 0px 6px;
        }
        td{
            padding: 2px 6px;
        }
        .%s{""" % mg.CSS_ROW_VAL + u"""
            margin: 0;
        }
        .%s, .%s{ """ % (mg.CSS_DATACELL, mg.CSS_FIRST_DATACELL) + u"""
            text-align: right;
            margin: 0;
        }
        .%s, .%s, .%s {""" % (mg.CSS_FIRST_COL_VAR, mg.CSS_FIRST_ROW_VAR, 
                              mg.CSS_SPACEHOLDER) + u"""
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 15px;
            color: white;
        }
        .%s, .%s { """ % (mg.CSS_FIRST_COL_VAR, mg.CSS_FIRST_ROW_VAR) + u"""
            background-color: #333435;
        }
        .%s {""" % mg.CSS_SPACEHOLDER + u"""
            background-color: #CCD9D7;
        }
        .%s{ """ % mg.CSS_FIRST_COL_VAR + u"""
            padding: 9px 6px;
            vertical-align: top;
        }
        .%s, .%s{""" % (mg.CSS_ROW_VAR, mg.CSS_COL_VAR) + u"""
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 15px;
            color: #000146;
            background-color: white;
        }
        .%s{""" % mg.CSS_COL_VAR + u"""
            padding: 6px 0px;            
        }            
        .%s{""" % mg.CSS_COL_VAL + u"""
            vertical-align: top;
        }
        tr.%s td{""" % mg.CSS_TOTAL_ROW + u"""
            font-weight: bold;
            border-top: solid 2px black;
            border-bottom: double 3px black;
        }
        .%s{""" % mg.CSS_PAGE_BREAK_BEFORE + u"""
            page-break-before: always;
            border-bottom: none; /*3px dotted #AFAFAF;*/
            width: auto;
            height: 18px;
        }
        th.%s{""" % mg.CSS_MEASURE + u"""
            background-color: white;
        }"""
    default_css += u"\n    td.%s{\n        text-align: left;\n        "  % \
        mg.CSS_LBL + \
        u"background-color: #F5F5F5;\n    }"
    default_css += u"\n    td.%s{\n        text-align: right;\n    }" % \
        mg.CSS_ALIGN_RIGHT
    return default_css
    
def get_html_hdr(hdr_title, css_fils, default_if_prob=False, grey=False, 
                 abs=False):
    """
    Get HTML header.
    Add suffixes to each of the main classes so can have multiple styles in a
        single HTML file.
    default_if_prob -- if True, will use the default css if the specified css 
        fails.  Otherwise will raise a css-specific exception (which will 
        probably be handled to give the user some feedback).
    grey -- make the text in the cells grey instead of black so it is more
        clearly an example rather than real data.
    abs -- absolute paths to background images in css.
    """
    debug = False
    if debug: print(css_fils[0])
    if css_fils:
        css_lst = []
        for i, css_fil in enumerate(css_fils):
            try:
                f = open(css_fil, "r")
            except IOError, e:
                if default_if_prob:
                    f = open(mg.DEFAULT_CSS_PATH, "r")
                else:
                    raise my_exceptions.MissingCssException
            css_txt = f.read()
            for css_class in mg.CSS_ELEMENTS:
                # suffix all report-relevant css entities so distinct
                old_class = mg.MISSING_VAL_INDICATOR + css_class
                new_class = mg.MISSING_VAL_INDICATOR + \
                    mg.CSS_SUFFIX_TEMPLATE % (css_class, i)
                if debug: print(old_class, new_class)
                css_txt = css_txt.replace(old_class, new_class)
            css_lst.append(css_txt)
            f.close()
        css = (os.linesep + os.linesep).join(css_lst)
        if grey: # appending it will override whatever else it is set to
            css += u"\ntd, th {\n    color: #5f5f5f;\n}"
    else:
        if debug: print("\n\nUsing default css")
        css = get_default_css()
    hdr = mg.DEFAULT_HDR % (hdr_title, css)
    if abs:
        hdr = lib.rel2abs_background(hdr)
    if debug: print(hdr)
    return hdr

def get_html_ftr():
    "Close HTML off cleanly"
    return u"</body></html>"

# The rest is GUI -> script oriented code

def get_css_dets():
    """
    Returns css_fils, css_idx.
    css_fils - list of full paths to css files.
    Knowing the current report and the current css what is the full list of css 
        files used by the report and what is the index for the current one in
        that list?
    Try reading from report file first.
    If not there (empty report or manually broken by user?) make and use a new
        one using cc[mg.CURRENT_CSS_PATH].
    """
    
    cc[mg.CURRENT_CSS_PATH]
    
    
    if not os.path.exists(cc[mg.CURRENT_CSS_PATH]):
        retval = wx.MessageBox(_("The CSS style file '%s' doesn't "
                            "exist.  Continue using the default style instead?"
                            % cc[mg.CURRENT_CSS_PATH]), _("Needs CSS Style"), 
                            style=wx.YES_NO|wx.ICON_QUESTION)
        if retval == wx.YES:
            cc[mg.CURRENT_CSS_PATH] = mg.DEFAULT_CSS_PATH
        else:
            raise my_exceptions.MissingCssException
    css_fils = None
    # read from report
    if os.path.exists(cc[mg.CURRENT_REPORT_PATH]):
        f = codecs.open(cc[mg.CURRENT_REPORT_PATH], "U", "utf-8")
        content = lib.clean_bom_utf8(f.read())
        f.close()
        if content:
            try:
                idx_start = content.index("<!--css_fils") + len("<!--")
                idx_end = content.index("-->")
                css_fils_str = content[idx_start: idx_end]
                css_dets_dic = {}
                exec css_fils_str in css_dets_dic
                css_fils = css_dets_dic[u"css_fils"]
            except Exception:
                pass
    if not css_fils:
        css_fils = [cc[mg.CURRENT_CSS_PATH]]
    else:
        if cc[mg.CURRENT_CSS_PATH] not in css_fils:
            css_fils.append(cc[mg.CURRENT_CSS_PATH])
    #mg.OUTPUT_CSS_DIC[cc[mg.CURRENT_REPORT_PATH]] = css_fils
    css_idx = css_fils.index(cc[mg.CURRENT_CSS_PATH])
    return css_fils, css_idx

def _strip_script(script):
    """
    Get script up till #sofa_script_end ...
    """
    try:
        end_idx = script.index(mg.SCRIPT_END)
        stripped = script[:end_idx]
    except ValueError:
        stripped = script
    return stripped

def export_script(script, css_fils):
    modules = ["my_globals as mg", "core_stats", "dimtables", "getdata", 
               "output", "rawtables", "stats_output"]
    if os.path.exists(cc[mg.CURRENT_SCRIPT_PATH]):
        f = codecs.open(cc[mg.CURRENT_SCRIPT_PATH], "U", "utf-8")
        existing_script = lib.clean_bom_utf8(f.read())             
        f.close()
    else:
        existing_script = None
    try:
        f = codecs.open(cc[mg.CURRENT_SCRIPT_PATH], "w", "utf-8")
    except IOError:
        wx.MessageBox(_("Problem making script file named \"%s\". Please try "
                        "another name.") % cc[mg.CURRENT_SCRIPT_PATH])
        return
    if existing_script:
        f.write(_strip_script(existing_script))
    else:
        insert_prelim_code(modules, f, cc[mg.CURRENT_REPORT_PATH], css_fils)
    tbl_filt_label, tbl_filt = lib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
    append_exported_script(f, script, tbl_filt_label, tbl_filt, 
                           inc_divider=True)
    add_end_script_code(f)
    f.close()
    wx.MessageBox(_("Script added to end of \"%s\" ready for reuse and "
                    "automation" % cc[mg.CURRENT_SCRIPT_PATH]))

def add_divider_code(f, tbl_filt_label, tbl_filt):
    """
    Adds divider code to a script file.
    """
    f.write(u"\nsource = output.get_source(u\"%s\", u\"%s\")" % (dd.db, dd.tbl))
    f.write(u"\ndivider = output.get_divider(source, "
            u" u\"\"\" %s \"\"\", u\"\"\" %s \"\"\")" % (tbl_filt_label, 
                                                         tbl_filt))
    f.write(u"\nfil.write(divider)\n")

def get_divider(source, tbl_filt_label, tbl_filt):
    """
    Get the HTML divider between content -includes source e.g. database, table 
        and time stamp; and a filter description.
    """    
    filt_msg = lib.get_filt_msg(tbl_filt_label, tbl_filt)
    return u"\n<br><br>\n<hr>\n%s\n<p>%s</p>" % (source, filt_msg)

def get_source(db, tbl_name):
    datestamp = datetime.now().strftime("on %d/%m/%Y at %I:%M %p")
    source = u"\n<p>From %s.%s %s</p>" % (db, tbl_name, datestamp)
    return source

def run_report(modules, add_to_report, css_fils, inner_script):
    """
    Runs report and returns bolran_report, and HTML representation of report 
        (or of the error) for GUI display.
    add_to_report -- also append result to current report.
    """
    debug = False
    # generate script
    f = codecs.open(mg.INT_SCRIPT_PATH, "w", "utf-8")
    if debug: print(css_fils)
    insert_prelim_code(modules, f, mg.INT_REPORT_PATH, css_fils)
    tbl_filt_label, tbl_filt = lib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
    append_exported_script(f, inner_script, tbl_filt_label, tbl_filt, 
                           inc_divider=False)
    add_end_script_code(f)
    f.close()
    # run script
    f = codecs.open(mg.INT_SCRIPT_PATH, "r", "utf-8")
    script = lib.clean_bom_utf8(f.read())    
    script = script[script.index(mg.MAIN_SCRIPT_START):]
    f.close()
    try:
        dummy_dic = {}
        exec script in dummy_dic
    except my_exceptions.ExcessReportTableCellsException, e:
        wx.MessageBox(unicode(e))
        return False, u""
    except my_exceptions.TooManyRowsInChiSquareException:
        wx.MessageBox(_("Please select a variable with fewer values for Group "
                        "A."))
        return False, u""
    except my_exceptions.TooManyColsInChiSquareException:
        wx.MessageBox(_("Please select a variable with fewer values for Group "
                        "B."))
        return False, u""
    except my_exceptions.TooFewRowsInChiSquareException:
        wx.MessageBox(_("Please select a variable with at least two values for "
                        "Group A."))
        return False, u""
    except my_exceptions.TooFewColsInChiSquareException:
        wx.MessageBox(_("Please select a variable with at least two values for "
                        "Group B."))
        return False, u""
    except my_exceptions.TooManyCellsInChiSquareException:
        wx.MessageBox(_("Please select variables which have fewer different "
                        "values. Too many values in contingency table."))
        return False, u""
    except my_exceptions.TooFewValsForDisplay:
        wx.MessageBox(_("Not enough data to display.  Please check variables "
                        "and any filtering."))
        return False, u""
    except Exception, e:
        err_content = _(u"<h1>Ooops!</h1>\n<p>Unable to run script to "
                        u"generate report. Error encountered: %s</p>") % \
                        lib.ue(e)
        if debug:
            raise
        return False, err_content
    f = codecs.open(mg.INT_REPORT_PATH, "U", "utf-8")
    raw_results = lib.clean_bom_utf8(f.read())
    f.close()
    source = get_source(dd.db, dd.tbl)
    filt_msg = lib.get_filt_msg(tbl_filt_label, tbl_filt)
    results_with_source = source + u"<p>%s</p>" % filt_msg + raw_results
    if add_to_report:
        # Append into html file.
        # Handles source and filter desc internally when making divider between 
        # output.
        save_to_report(css_fils, source, tbl_filt_label, tbl_filt, raw_results) 
        rel_display_content = (u"\n<p>Output also saved to '%s'</p>" %
                            lib.escape_pre_write(cc[mg.CURRENT_REPORT_PATH]) + 
                            results_with_source)
        # make relative links absolute so GUI viewers can display images
        gui_display_content = lib.rel2abs_background(
                                        lib.rel2abs_links(rel_display_content))
    else:
        gui_display_content = lib.rel2abs_background(results_with_source)
    if debug: print(gui_display_content)
    return True, gui_display_content

def insert_prelim_code(modules, f, fil_report, css_fils):
    """
    Insert preliminary code at top of file.
    f - open file handle ready for writing.
    NB only one output file per script irrespective of selection as each script
        exported.
    """
    debug = False
    if debug: print(css_fils)
    # NB the coding declaration we are just adding must be removed before we
    # try to run the script as a unicode string
    # else "encoding declaration in Unicode string".
    f.write(mg.PYTHON_ENCODING_DECLARATION)
    f.write(u"\n" + mg.MAIN_SCRIPT_START)
    f.write(u"\nimport codecs")
    f.write(u"\nimport sys")
    f.write(u"\nimport gettext")
    f.write(u"\nimport numpy as np")
    f.write(u"\ngettext.install('sofa', './locale', unicode=False)")
    f.write(u"\nsys.path.append(u'%s')" % \
            lib.escape_pre_write(mg.SCRIPT_PATH))
    for module in modules:
        f.write(u"\nimport %s" % module)
    f.write(u"\nimport my_exceptions")
    f.write(u"""\n\nfil = codecs.open(u"%s",""" % \
                      lib.escape_pre_write(fil_report) + u""" "w", "utf-8")""")
    css_fils_str = pprint.pformat(css_fils)
    f.write(u"\ncss_fils=%s" % css_fils_str)
    f.write(u"\nfil.write(output.get_html_hdr(\"Report(s)\", css_fils, "
            u"default_if_prob=True))")
    f.write(u"\n\n# end of script 'header'" + u"\n" + u"\n")
    
def append_exported_script(f, inner_script, tbl_filt_label, tbl_filt, 
                           inc_divider=False):
    """
    Append exported script onto existing script file.
    f - open file handle ready for writing
    """
    debug = False
    now = datetime.now()
    raw_datestamp = now.strftime(u"Script exported %d/%m/%Y at %I:%M %p")
    try:
        datestamp = raw_datestamp.decode(locale.getpreferredencoding())
    except Exception:
        raw_datestamp = now.strftime(u"Script exported %d/%m/%Y at %H:%M")
        try:
            datestamp = raw_datestamp.decode(locale.getpreferredencoding())
        except Exception:
            datestamp = u"" # not worth any more trouble at this stage
    # Fresh connection for each in case it changes in between tables
    f.write(u"#%s" % (u"-"*65))
    f.write(u"\n# %s" % datestamp)
    if inc_divider:
        add_divider_code(f, tbl_filt_label, tbl_filt)
    con_dets_str = pprint.pformat(dd.con_dets)
    f.write(u"\n" + u"con_dets = %s" % con_dets_str)
    default_dbs_str = pprint.pformat(dd.default_dbs)
    f.write(u"\n" + u"default_dbs = %s" % default_dbs_str)
    default_tbls_str = pprint.pformat(dd.default_tbls)
    f.write(u"\ndefault_tbls = %s" % default_tbls_str)
    f.write(u"\ndbe_resources = getdata.get_dbe_resources(dbe=\"%s\", " % 
            dd.dbe)
    f.write(u"\n    con_dets=con_dets, default_dbs=default_dbs, "
            u"default_tbls=default_tbls, ")
    f.write(u"\n    db=\"%s\", tbl=\"%s\")" % (dd.db, dd.tbl))
    f.write(u"\ncon = dbe_resources[mg.DBE_CON]")
    f.write(u"\ncur = dbe_resources[mg.DBE_CUR]")
    f.write(u"\ndbs = dbe_resources[mg.DBE_DBS]")
    f.write(u"\ndb = dbe_resources[mg.DBE_DB]")
    f.write(u"\ntbls = dbe_resources[mg.DBE_TBLS]")
    f.write(u"\ntbl = dbe_resources[mg.DBE_TBL]")
    f.write(u"\nflds = dbe_resources[mg.DBE_FLDS]")
    f.write(u"\nidxs = dbe_resources[mg.DBE_IDXS]")
    f.write(u"\nhas_unique = dbe_resources[mg.DBE_HAS_UNIQUE]")
    f.write(u"\n%s" % inner_script)
    # f.write(u"\ncon.close()") # closes the whole thing and not just for this 
    # script ;-)

def _strip_html(html):
    """
    Get html between the <body></body> tags.  The start tag must be present.
    """
    body_start = u"<body>"
    body_end = u"</body>"
    try:
        start_idx = html.index(body_start) + len(body_start)
    except ValueError:
        raise Exception(u"Unable to process malformed HTML.  "
                        u"Original HTML: %s" % html)
    try:
        end_idx = html.index(body_end)
        stripped = html[start_idx:end_idx]
    except ValueError:
        stripped = html[start_idx:]
    return stripped

def save_to_report(css_fils, source, tbl_filt_label, tbl_filt, new_html):
    """
    If report doesn't exist, make it.
    If it does exist, extract existing content and then create empty version.
    Add to empty file, new header, existing content, and new content.
    A new header is required each time because there may be new css included.
    New content is everything from "content" after the body tag.
    """
    new_no_hdr = _strip_html(new_html)
    if os.path.exists(cc[mg.CURRENT_REPORT_PATH]):
        f = codecs.open(cc[mg.CURRENT_REPORT_PATH], "U", "utf-8")
        existing_html = lib.clean_bom_utf8(f.read())
        existing_no_ends = _strip_html(existing_html)
        f.close()        
    else:
        existing_no_ends = None
    hdr_title = time.strftime(_("SOFA Statistics Report") + \
                              " %Y-%m-%d_%H:%M:%S")
    hdr = get_html_hdr(hdr_title, css_fils)
    f = codecs.open(cc[mg.CURRENT_REPORT_PATH], "w", "utf-8")
    css_fils_str = pprint.pformat(css_fils)
    f.write(u"<!--css_fils = %s-->\n\n" % css_fils_str)
    f.write(hdr)
    if existing_no_ends:
        f.write(existing_no_ends)
    f.write(get_divider(source, tbl_filt_label, tbl_filt))
    f.write(new_no_hdr)
    f.write(get_html_ftr())
    f.close()

def add_end_script_code(f):
    "Add ending code to script.  NB leaves open file."
    f.write(u"\n" + u"\n" + mg.SCRIPT_END + \
            u"-"*(65 - len(mg.SCRIPT_END)) + u"\n")
    f.write(u"\n" + u"fil.write(output.get_html_ftr())")
    f.write(u"\n" + u"fil.close()")

def display_report(parent, str_content, url_load=False):
    # display results
    wx.BeginBusyCursor()
    dlg = showhtml.DlgHTML(parent=parent, title=_("Report"), url=None, 
                           content=str_content, url_load=url_load)
    dlg.ShowModal()
    lib.safe_end_cursor() # again to be sure
    