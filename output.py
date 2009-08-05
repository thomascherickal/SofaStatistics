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
        tr, td, th{
            margin: 0;
        }
        .%s{""" % my_globals.CSS_TBL_TITLE_CELL + """
            border: none;
            padding: 18px 0px 12px 0px;
            margin: 0;
        }
        .%s{""" % my_globals.CSS_TBL_TITLE + """
            padding: 0;
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 18px;
        }
        .%s{ """ % my_globals.CSS_SUBTITLE + """
            padding: 12px 0px 0px 0px;
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 14px;
        }
        th, .%s, .%s, .%s, .%s {""" % (my_globals.CSS_ROW_VAR, 
                                my_globals.CSS_ROW_VAL, my_globals.CSS_DATACELL, 
                                my_globals.CSS_FIRST_DATACELL) + """
            border: solid 1px #A1A1A1;
        }
        th{
            margin: 0;
            padding: 0px 6px;
        }
        td{
            padding: 2px 6px;
        }
        .%s{""" % my_globals.CSS_ROW_VAL + """
            margin: 0;
        }
        .%s, .%s{ """ % (my_globals.CSS_DATACELL, 
                         my_globals.CSS_FIRST_DATACELL) + """
            text-align: right;
            margin: 0;
        }
        .%s, .%s, .%s {""" % (my_globals.CSS_FIRST_COL_VAR, 
                              my_globals.CSS_FIRST_ROW_VAR, 
                              my_globals.CSS_SPACEHOLDER) + """
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 15px;
            color: white;
        }
        .%s, .%s { """ % (my_globals.CSS_FIRST_COL_VAR, 
                          my_globals.CSS_FIRST_ROW_VAR) + """
            background-color: #333435;
        }
        .%s {""" % my_globals.CSS_SPACEHOLDER + """
            background-color: #CCD9D7;
        }
        .%s{ """ % my_globals.CSS_FIRST_COL_VAR + """
            padding: 9px 6px;
            vertical-align: top;
        }
        .%s, .%s{""" % (my_globals.CSS_ROW_VAR, my_globals.CSS_COL_VAR) + """
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            font-size: 15px;
            color: #000146;
            background-color: white;
        }
        .%s{""" % my_globals.CSS_COL_VAR + """
            padding: 6px 0px;            
        }            
        .%s{""" % my_globals.CSS_COL_VAL + """
            vertical-align: top;
        }
        tr.%s td{""" % my_globals.CSS_TOTAL_ROW + """
            font-weight: bold;
            border-top: solid 2px black;
            border-bottom: double 3px black;
        }
        .%s{""" % my_globals.CSS_PAGE_BREAK_BEFORE + """
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
    
def getHtmlHdr(hdr_title, css_fils):
    """
    Get HTML header.
    Add suffixes to each of the main classes so can have multiple styles in a
        single HTML file.
    """
    debug = False
    if css_fils:
        css_lst = []
        for i, css_fil in enumerate(css_fils):
            f = file(css_fil, "r")
            css_txt = f.read()
            for css_class in my_globals.CSS_ELEMENTS:
                # suffix all report-relevant css entities so distinct
                old_class = "." + css_class
                new_class = "." + \
                    my_globals.CSS_SUFFIX_TEMPLATE % (css_class, i)
                if debug: print old_class, new_class
                css_txt = css_txt.replace(old_class, new_class)
            css_lst.append(css_txt)
            f.close()
        css = "\n\n".join(css_lst)
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
    
    css_fils = my_globals.OUTPUT_CSS_DIC.get(fil_report)
    if not css_fils:
        my_globals.OUTPUT_CSS_DIC[fil_report] = [my_globals.DEFAULT_CSS_PATH]
    else:
        if fil_css not in css_fils:
            css_fils.append(fil_css)
    InsertPrelimCode(modules, f, my_globals.INT_REPORT_PATH, css_fils)
    
    
    
    
    
    
    
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
    SaveToReport(fil_report, css_fils, strContent)
    strContent = "<p>Output also saved to '%s'</p>" % \
        fil_report + strContent
    return strContent

def InsertPrelimCode(modules, fil, fil_report, css_fils):
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
              "css_fils=%s))" % css_fils)
    
def AppendExportedScript(fil, inner_script, conn_dets, dbe, db, tbl_name, 
                         default_dbs, default_tbls):
    """
    Append exported script onto file.
    fil - open file handle ready for writing
    """
    datestamp = datetime.now().strftime("Script " + \
                                    "exported %d/%m/%Y at %I:%M %p")
    # Fresh connection for each in case it changes in between tables
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

def SaveToReport(fil_report, css_fils, content):
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
        f.write(getHtmlHdr(hdr_title, css_fils))
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