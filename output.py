#! /usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
import os
import pprint
import time

import my_globals
import getdata
import showhtml
import util

def GetDefaultCss():
    """
    Get default CSS.  The "constants" are used so that we can 
        guarantee the class names we use later on are the same as
        used here.
    """
    default_css = """
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
        tr.rowsetstart th, tr.rowsetstart td{
            border-top: solid black 2px;
        }
        tr, td, th{
            margin: 0;
        }
        .tbltitlecell{
            border: none;
            padding: 18px 0px 12px 0px;
            margin: 0;
        }
        .tbltitle{
            padding: 0;
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 18px;
        }
        .tblsubtitle{
            padding: 12px 0px 0px 0px;
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 14px;
        }
        th, .rowvar, .rowval, .datacell, .firstdatacell {
            border: solid 1px #A1A1A1;
        }
        th{
            margin: 0;
            padding: 0px 6px;
        }
        td{
            padding: 2px 6px;
        }
        .rowval{
            margin: 0;
        }
        .datacell, .firstdatacell{
            text-align: right;
            margin: 0;
        }
        .firstcolvar, .firstrowvar, .spaceholder {
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 15px;
            color: white;
        }
        .firstcolvar, .firstrowvar {
            background-color: #333435;
        }
        .spaceholder {
            background-color: #CCD9D7;
        }
        .firstcolvar{
            padding: 9px 6px;
            vertical-align: top;
        }
        .rowvar, .colvar{
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 15px;
            color: #000146;
            background-color: white;
        }
        .colvar{
            padding: 6px 0px;            
        }            
        .colval{
            vertical-align: top;
        }
        .measure, .firstmeasure{
            vertical-align: top;
            font-size: 11px;
            font-weight: normal;
        }
        tr.total-row td{
            font-weight: bold;
            border-top: solid 2px black;
            border-bottom: double 3px black;
        }
        .page-break-before{
            page-break-before: always;
            border-bottom: none; /*3px dotted #AFAFAF;*/
            width: auto;
            height: 18px;
        }"""
    default_css += "\n    td.%s{\n        text-align: left;\n        "  % \
        my_globals.CSS_LBL + \
        "background-color: #F5F5F5;\n    }"
    default_css += "\n    td.%s{\n        text-align: right;\n    }" % \
        my_globals.CSS_ALIGN_RIGHT
    return default_css

default_hdr = """
            <!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
            'http://www.w3.org/TR/html4/loose.dtd'>
            <html>
            <head>
            <meta http-equiv="P3P" content='CP="IDC DSP COR CURa ADMa OUR 
            IND PHY ONL COM STA"'>
            <title>%s</title>
            <style type="text/css">
            <!--
            %s
            -->
            </style>
            </head>
            <body>\n"""
    
def getHtmlHdr(hdr_title, fil_css=None):
    """Get HTML header"""
    if fil_css:
        f = file(fil_css, "r")
        css = f.read()
        f.close()
    else:
        css = GetDefaultCss()
    hdr = default_hdr % (hdr_title, css)
    return hdr

def getHtmlFtr():
    "Close HTML off cleanly"
    return "</body></html>"

def RunReport(modules, fil_report, fil_css, inner_script, conn_dets, dbe, db, 
              tbl_name, default_dbs, default_tbls):
    """
    Runs report and returns HTML representation of it.
    """
    # generate script
    f = file(my_globals.INT_SCRIPT_PATH, "w")
    InsertPrelimCode(modules, f, my_globals.INT_REPORT_PATH, fil_css)
    AppendExportedScript(f, inner_script, conn_dets, dbe, db, tbl_name,
                         default_dbs, default_tbls)
    AddClosingScriptCode(f)
    f.close()
    # run script
    f = file(my_globals.INT_SCRIPT_PATH, "r")
    script = f.read()
    f.close()
    try:
        exec(script)
    except Exception, e:
        strContent = "<h1>Ooops!</h1>\n<p>Unable to run report.  " + \
            "Error encountered.  Original error message: %s</p>" % e
        return strContent
    f = file(my_globals.INT_REPORT_PATH, "r")
    strContent = f.read()
    f.close()
    # append into html file
    SaveToReport(fil_report, fil_css, strContent)
    strContent = "<p>Output also saved to '%s'</p>" % \
        fil_report + strContent
    return strContent

def InsertPrelimCode(modules, fil, fil_report, fil_css):
    """
    Insert preliminary code at top of file.
    fil - open file handle ready for writing.
    NB files always start from scratch per make tables session.
    """         
    fil.write("#! /usr/bin/env python")
    fil.write("\n# -*- coding: utf-8 -*-\n")
    fil.write("\nimport sys")
    fil.write("\nsys.path.append('%s')" % my_globals.SCRIPT_PATH)
    for module in modules:
        fil.write("\nimport %s" % module)
    fil.write("\n\nfil = file(r\"%s\", \"w\")" % fil_report)
    fil.write("\nfil.write(output.getHtmlHdr(\"Report(s)\", " + \
              "fil_css=r\"%s\"))" % fil_css)
    
def AppendExportedScript(fil, inner_script, conn_dets, dbe, db, tbl_name, 
                         default_dbs, default_tbls):
    """
    Append exported script onto file.
    fil - open file handle ready for writing
    """
    datestamp = datetime.now().strftime("Script " + \
                                    "exported %d/%m/%Y at %I:%M %p")
    # Fresh connection for each in case it changes in between tables
    getdata.setDbInConnDets(dbe, conn_dets, db)
    conn_dets_str = pprint.pformat(conn_dets)
    fil.write("\nconn_dets = %s" % conn_dets_str)
    default_dbs_str = pprint.pformat(default_dbs)
    fil.write("\ndefault_dbs = %s" % default_dbs_str)
    default_tbls_str = pprint.pformat(default_tbls)
    fil.write("\ndefault_tbls = %s" % default_tbls_str)
    fil.write("\nconn, cur, dbs, tbls, flds, has_unique, idxs = \\" + \
        "\n    getdata.getDbDetsObj(\"%s\", " % dbe + \
        "default_dbs, default_tbls, conn_dets=conn_dets," + \
        "\n    db=\"%s\", tbl=\"%s\")" % (db, tbl_name) + \
        ".getDbDets()")
    fil.write("\n\n#%s\n#%s\n" % ("-"*50, datestamp))
    fil.write(inner_script)
    fil.write("\nconn.close()")

def SaveToReport(fil_report, fil_css, content):
    """
    If report exists, append content stripped of every thing up till 
        and including body tag.
    If not, create file, insert header, then stripped content.
    """
    body = "<body>"
    start_idx = content.find(body) + len(body)
    content = content[start_idx:]
    if os.path.exists(fil_report):
        f = file(fil_report, "a")
    else:
        f = file(fil_report, "w")
        hdr_title = time.strftime("SOFA Statistics Report %Y-%m-%d_%H:%M:%S")
        f.write(getHtmlHdr(hdr_title, fil_css))
    f.write(content)
    f.close()

def AddClosingScriptCode(f):
    "Add ending code to script.  Nb leaves open file."
    f.write("\n\n#" + "-"*50 + "\n")
    f.write("\nfil.write(output.getHtmlFtr())")
    f.write("\nfil.close()")

def DisplayReport(parent, strContent):
    # display results
    dlg = showhtml.ShowHTML(parent=parent, content=strContent, 
                            file_name=my_globals.INT_REPORT_FILE, 
                            title="Report", 
                            print_folder=my_globals.INTERNAL_FOLDER)
    dlg.ShowModal()
    dlg.Destroy()