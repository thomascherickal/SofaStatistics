#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import codecs
from datetime import datetime
import os
import pprint
import time

import my_globals
import getdata
import showhtml
import util

# do not use os.linesep for anything going to be read and exec'd
# in Windows the \r\n makes it fail.

def GetDefaultCss():
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
        .%s{""" % my_globals.CSS_TBL_TITLE_CELL + u"""
            border: none;
            padding: 18px 0px 12px 0px;
            margin: 0;
        }
        .%s{""" % my_globals.CSS_TBL_TITLE + u"""
            padding: 0;
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 18px;
        }
        .%s{ """ % my_globals.CSS_SUBTITLE + u"""
            padding: 12px 0px 0px 0px;
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 14px;
        }
        th, .%s, .%s, .%s, .%s {""" % (my_globals.CSS_ROW_VAR, 
                                my_globals.CSS_ROW_VAL, my_globals.CSS_DATACELL, 
                                my_globals.CSS_FIRST_DATACELL) + u"""
            border: solid 1px #A1A1A1;
        }
        th{
            margin: 0;
            padding: 0px 6px;
        }
        td{
            padding: 2px 6px;
        }
        .%s{""" % my_globals.CSS_ROW_VAL + u"""
            margin: 0;
        }
        .%s, .%s{ """ % (my_globals.CSS_DATACELL, 
                         my_globals.CSS_FIRST_DATACELL) + u"""
            text-align: right;
            margin: 0;
        }
        .%s, .%s, .%s {""" % (my_globals.CSS_FIRST_COL_VAR, 
                              my_globals.CSS_FIRST_ROW_VAR, 
                              my_globals.CSS_SPACEHOLDER) + u"""
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 15px;
            color: white;
        }
        .%s, .%s { """ % (my_globals.CSS_FIRST_COL_VAR, 
                          my_globals.CSS_FIRST_ROW_VAR) + u"""
            background-color: #333435;
        }
        .%s {""" % my_globals.CSS_SPACEHOLDER + u"""
            background-color: #CCD9D7;
        }
        .%s{ """ % my_globals.CSS_FIRST_COL_VAR + u"""
            padding: 9px 6px;
            vertical-align: top;
        }
        .%s, .%s{""" % (my_globals.CSS_ROW_VAR, my_globals.CSS_COL_VAR) + u"""
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 15px;
            color: #000146;
            background-color: white;
        }
        .%s{""" % my_globals.CSS_COL_VAR + u"""
            padding: 6px 0px;            
        }            
        .%s{""" % my_globals.CSS_COL_VAL + u"""
            vertical-align: top;
        }
        tr.%s td{""" % my_globals.CSS_TOTAL_ROW + u"""
            font-weight: bold;
            border-top: solid 2px black;
            border-bottom: double 3px black;
        }
        .%s{""" % my_globals.CSS_PAGE_BREAK_BEFORE + u"""
            page-break-before: always;
            border-bottom: none; /*3px dotted #AFAFAF;*/
            width: auto;
            height: 18px;
        }
        th.%s{""" % my_globals.CSS_MEASURE + u"""
            background-color: white;
        }"""
    default_css += u"\n    td.%s{\n        text-align: left;\n        "  % \
        my_globals.CSS_LBL + \
        u"background-color: #F5F5F5;\n    }"
    default_css += u"\n    td.%s{\n        text-align: right;\n    }" % \
        my_globals.CSS_ALIGN_RIGHT
    return default_css

default_hdr = u"""
            <!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
            'http://www.w3.org/TR/html4/loose.dtd'>
            <html>
            <head>
            <meta http-equiv="P3P" content='CP="IDC DSP COR CURa ADMa OUR 
            IND PHY ONL COM STA"; charset=utf-8'>
            <title>%s</title>
            <style type="text/css">
            <!--
            %s
            -->
            </style>
            </head>
            <body>\n"""
    
def getHtmlHdr(hdr_title, css_fils):
    """
    Get HTML header.
    Add suffixes to each of the main classes so can have multiple styles in a
        single HTML file.
    """
    debug = False
    if debug: print(css_fils[0])
    if css_fils:
        css_lst = []
        for i, css_fil in enumerate(css_fils):
            try:
                f = file(css_fil, "r")
            except IOError, e:
                raise Exception, _("The css file %s doesn't exist" % css_fil)
            css_txt = f.read()
            for css_class in my_globals.CSS_ELEMENTS:
                # suffix all report-relevant css entities so distinct
                old_class = u"." + css_class
                new_class = u"." + \
                    my_globals.CSS_SUFFIX_TEMPLATE % (css_class, i)
                if debug: print(old_class, new_class)
                css_txt = css_txt.replace(old_class, new_class)
            css_lst.append(css_txt)
            f.close()
        css = (os.linesep + os.linesep).join(css_lst)
    else:
        css = GetDefaultCss()
    hdr = default_hdr % (hdr_title, css)
    return hdr

def getHtmlFtr():
    "Close HTML off cleanly"
    return u"</body></html>"

# The rest is GUI -> script oriented code

def GetCssDets(fil_report, fil_css):
    """
    Returns css_fils, css_idx.
    css_fils - list of full paths to css files.
    Knowing the current report and the current css what is the full list of css 
        files used by the report and what is the index for the current one in
        that list?
    Try reading from report file first.
    If not there (empty report or manually broken by user?) make and use a new
        one using fil_css.
    """
    css_fils = None
    # read from report
    if os.path.exists(fil_report):
        f = codecs.open(fil_report, "U", "utf-8")
        content = util.clean_bom_utf8(f.read())
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
        css_fils = [fil_css]
    else:
        if fil_css not in css_fils:
            css_fils.append(fil_css)
    #my_globals.OUTPUT_CSS_DIC[fil_report] = css_fils
    css_idx = css_fils.index(fil_css)
    return css_fils, css_idx

def _strip_script(script):
    """
    Get script up till #sofa_script_end ...
    """
    try:
        end_idx = script.index(my_globals.SCRIPT_END)
        stripped = script[:end_idx]
    except ValueError:
        stripped = script
    return stripped

def ExportScript(script, fil_script, fil_report, css_fils, conn_dets, dbe, db, 
                 tbl, default_dbs, default_tbls):
    modules = ["my_globals", "core_stats", "dimtables", "getdata", "output", 
               "rawtables", "stats_output"]
    if os.path.exists(fil_script):
        f = codecs.open(fil_script, "U", "utf-8")
        existing_script = util.clean_bom_utf8(f.read())             
        f.close()
    else:
        existing_script = None
    f = codecs.open(fil_script, "w", "utf-8")
    if existing_script:
        f.write(_strip_script(existing_script))
    else:
        InsertPrelimCode(modules, f, fil_report, css_fils)
    AppendExportedScript(f, script, conn_dets, dbe, db, tbl, default_dbs, 
                         default_tbls, add_divider_code=True)
    AddClosingScriptCode(f)
    f.close()

def AddDividerCode(f, db, tbl):
    f.write(u"source = output.GetSource(\"%s\", \"%s\")" % (db, tbl))
    f.write(u"\n" + u"divider = output.GetDivider(source)")
    f.write(u"\n" + u"fil.write(divider)\n")

def GetSource(db, tbl_name):
    datestamp = datetime.now().strftime("on %d/%m/%Y at %I:%M %p")
    source = u"\n" + u"<p>From %s.%s %s</p>" % (db, tbl_name, datestamp)
    return source

def RunReport(modules, fil_report, add_to_report, css_fils, inner_script, 
              conn_dets, dbe, db, tbl_name, default_dbs, default_tbls):
    """
    Runs report and returns HTML representation of it.
    add_to_report - also append result to current report.
    """
    debug = False
    # generate script
    f = codecs.open(my_globals.INT_SCRIPT_PATH, "w", "utf-8")
    if debug: print(css_fils)
    InsertPrelimCode(modules, f, my_globals.INT_REPORT_PATH, css_fils)
    AppendExportedScript(f, inner_script, conn_dets, dbe, db, tbl_name,
                         default_dbs, default_tbls, add_divider_code=False)
    AddClosingScriptCode(f)
    f.close()
    # run script
    f = codecs.open(my_globals.INT_SCRIPT_PATH, "r", "utf-8")
    script = util.clean_bom_utf8(f.read())    
    script = script[script.index(my_globals.MAIN_SCRIPT_START):]
    f.close()
    try:
        dummy_dic = {}
        exec script in dummy_dic
    except Exception, e:
        strErrContent = _(u"<h1>Ooops!</h1>\n<p>Unable to run script " + \
                          u"to generate report.  "
            u"Error encountered.  Original error message: %s</p>") % e
        if debug:
            raise Exception, unicode(e)
        return strErrContent
    f = codecs.open(my_globals.INT_REPORT_PATH, "U", "utf-8")
    source = GetSource(db, tbl_name)
    strContent = util.clean_bom_utf8(f.read())
    f.close()
    # append into html file
    if add_to_report:
        SaveToReport(fil_report, css_fils, source, strContent)
        strContent = u"\n" + u"<p>Output also saved to '%s'</p>" % \
            util.escape_win_path(fil_report) + source + strContent
    return strContent

def InsertPrelimCode(modules, f, fil_report, css_fils):
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
    f.write(my_globals.PYTHON_ENCODING_DECLARATION)
    f.write(u"\n" + my_globals.MAIN_SCRIPT_START)
    f.write(u"\n" + u"import codecs")
    f.write(u"\n" + u"import sys")
    f.write(u"\n" + u"import gettext")
    f.write(u"\n" + u"gettext.install('sofa', './locale', unicode=False)")
    f.write(u"\n" + u"sys.path.append(u'%s')" % \
            util.escape_win_path(my_globals.SCRIPT_PATH))
    for module in modules:
        f.write(u"\n" + u"import %s" % module)
    f.write(u"\n" + u"\n" + u"""fil = codecs.open(u"%s",""" % \
              util.escape_win_path(fil_report) + u""" "w", "utf-8")""")
    css_fils_str = pprint.pformat(css_fils)
    f.write(u"\n" + u"css_fils=%s" % css_fils_str)
    f.write(u"\n" + u"fil.write(output.getHtmlHdr(\"Report(s)\", "
              u"css_fils))" + u"\n" + u"\n")
    f.write(u"# end of script 'header'" + u"\n" + u"\n")
    
def AppendExportedScript(f, inner_script, conn_dets, dbe, db, tbl_name, 
                         default_dbs, default_tbls, add_divider_code=False):
    """
    Append exported script onto existing script file.
    f - open file handle ready for writing
    """
    datestamp = datetime.now().strftime("Script exported %d/%m/%Y at %I:%M %p")
    # Fresh connection for each in case it changes in between tables
    f.write(u"#%s" % (u"-"*50))
    f.write(u"\n" + u"# %s" % datestamp)
    if add_divider_code:
        AddDividerCode(f, db, tbl_name)
    conn_dets_str = pprint.pformat(conn_dets)
    f.write(u"\n" + u"conn_dets = %s" % conn_dets_str)
    default_dbs_str = pprint.pformat(default_dbs)
    f.write(u"\n" + u"default_dbs = %s" % default_dbs_str)
    default_tbls_str = pprint.pformat(default_tbls)
    f.write(u"\n" + u"default_tbls = %s" % default_tbls_str)
    f.write(u"\n" + \
        u"conn, cur, dbs, tbls, flds, has_unique, idxs = \\" + \
        u"\n" + "    getdata.getDbDetsObj(\"%s\", " % dbe + \
        u"default_dbs, default_tbls, conn_dets=conn_dets," + \
        u"\n" + "    db=\"%s\", tbl=\"%s\")" % (db, tbl_name) + \
        u".getDbDets()")
    f.write(u"\n" + u"%s" % inner_script)
    f.write(u"\n" + u"conn.close()")

def _strip_html(html):
    """
    Get html between the <body></body> tags.  The start tag must be present.
    """
    body_start = u"<body>"
    body_end = u"</body>"
    try:
        start_idx = html.index(body_start) + len(body_start)
    except ValueError:
        raise Exception, (u"Unable to process malformed HTML.  "
                          u"Original HTML: %s" % html)
    try:
        end_idx = html.index(body_end)
        stripped = html[start_idx:end_idx]
    except ValueError:
        stripped = html[start_idx:]
    return stripped

def GetDivider(source):
    """
    Get the HTML divider between content -includes source e.g. database, table 
        and time stamp.
    """
    return u"\n" + u"<br><br>" + u"\n" + u"<hr>" + u"\n" + source

def SaveToReport(fil_report, css_fils, source, new_html):
    """
    If report doesn't exist, make it.
    If it does exist, extract existing content and then create empty version.
    Add to empty file, new header, existing content, and new content.
    A new header is required each time because there may be new css included.
    New content is everything from "content" after the body tag.
    """
    new_no_hdr = _strip_html(new_html)
    if os.path.exists(fil_report):
        f = codecs.open(fil_report, "U", "utf-8")
        existing_html = util.clean_bom_utf8(f.read())
        existing_no_ends = _strip_html(existing_html)
        f.close()        
    else:
        existing_no_ends = None
    hdr_title = time.strftime(_("SOFA Statistics Report") + \
                              " %Y-%m-%d_%H:%M:%S")
    hdr = getHtmlHdr(hdr_title, css_fils)
    f = codecs.open(fil_report, "w", "utf-8")
    css_fils_str = pprint.pformat(css_fils)
    f.write(u"<!--css_fils = %s-->\n\n" % css_fils_str)
    f.write(hdr)
    if existing_no_ends:
        f.write(existing_no_ends)
    f.write(GetDivider(source))
    f.write(new_no_hdr)
    f.write(getHtmlFtr())
    f.close()

def AddClosingScriptCode(f):
    "Add ending code to script.  Nb leaves open file."
    f.write(u"\n" + u"\n" + my_globals.SCRIPT_END + \
            u"-"*(50 - len(my_globals.SCRIPT_END)) + u"\n")
    f.write(u"\n" + u"fil.write(output.getHtmlFtr())")
    f.write(u"\n" + u"fil.close()")

def DisplayReport(parent, strContent):
    # display results
    dlg = showhtml.ShowHTML(parent=parent, content=strContent, 
                            file_name=my_globals.INT_REPORT_FILE, 
                            title=_("Report"), 
                            print_folder=my_globals.INTERNAL_FOLDER)
    dlg.ShowModal()
    dlg.Destroy()