#! /usr/bin/env python
# -*- coding: utf-8 -*-

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
