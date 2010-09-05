#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Use English UK spelling e.g. colour and when writing JS use camelcase.
NB no html headers here - the script generates those beforehand and appends 
    this and then the html footer.
"""

import pprint

import my_globals as mg
import lib
import my_exceptions
import getdata
import output

def get_barchart_dets(dbe, cur, tbl, tbl_filt, fld_measure, val_labels):
    """
    Get frequencies for all values in variable plus labels.
    """
    debug = False
    obj_quoter = getdata.get_obj_quoter_func(dbe)
    where_tbl_filt, unused = lib.get_tbl_filts(tbl_filt)
    SQL_get_vals = u"SELECT %s, COUNT(*) AS freq " % obj_quoter(fld_measure) + \
        u"FROM %s " % obj_quoter(tbl) + \
        u" %s " % where_tbl_filt + \
        u"GROUP BY %s" % obj_quoter(fld_measure)
    if debug: print(SQL_get_vals)
    cur.execute(SQL_get_vals)
    xaxis_dets = []
    y_values = []
    for val, freq in cur.fetchall():
        xaxis_dets.append((val, val_labels.get(val, unicode(val))))
        y_values.append(freq)
    return xaxis_dets, y_values

def extract_dojo_style(css_fil):
    try:
        f = open(css_fil, "r")
    except IOError, e:
        raise my_exceptions.MissingCssException(css_fil)
    css = f.read()
    f.close()
    try:
        css_dojo_start_idx = css.index(mg.DOJO_STYLE_START)
        css_dojo_end_idx = css.index(mg.DOJO_STYLE_END)
    except ValueError, e:
        raise my_exceptions.MalformedCssDojoError(css)
    css_dojo = css[css_dojo_start_idx + len(mg.DOJO_STYLE_START):\
                   css_dojo_end_idx]
    css_dojo_dic = {}
    try:
        exec css_dojo in css_dojo_dic
    except SyntaxError, e:
        wx.MessageBox(\
            _("Syntax error in dojo settings in css file \"%s\"." % css_fil +
              "\n\nDetails: %s %s" % (css_dojo, lib.ue(e))))
        raise
    except Exception, e:
        wx.MessageBox(\
            _("Error processing css dojo file \"%s\"." % css_fil +
              "\n\nDetails: %s" % lib.ue(e)))
        raise
    return (css_dojo_dic[u"grid_bg"], css_dojo_dic[u"axis_label_font_colour"], 
            css_dojo_dic[u"major_gridline_colour"], 
            css_dojo_dic[u"gridline_width"], 
            css_dojo_dic[u"tooltip_border_colour"], 
            css_dojo_dic[u"colour_mappings"])

def barchart_output(titles, subtitles, var_label, xaxis_dets, y_values, css_idx, 
                    css_fil, page_break_after):
    """
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    var_label -- e.g. Age Group
    var_numeric -- needs to be quoted or not.
    y_values -- list of values e.g. [12, 30, 100.5, -1, 40]
    xaxis_dets -- [(1, "Under 20"), (2, "20-29"), (3, "30-39"), (4, "40-64"),
                   (5, "65+")]
    css_idx -- css index so can apply    
    """
    (CSS_TBL_TITLE, CSS_TBL_SUBTITLE, 
                            CSS_TBL_TITLE_CELL) = output.get_title_css(css_idx)
    title_dets_html_lst = []
    if titles:
        title_dets_html_lst.append(u"<p class='%s %s'>" % (CSS_TBL_TITLE, 
                                                           CSS_TBL_TITLE_CELL) + 
                                   u"\n<br>".join(titles) + u"</p>")
    if subtitles:
        title_dets_html_lst.append(u"<p class='%s %s'>" % (CSS_TBL_SUBTITLE, 
                                                           CSS_TBL_TITLE_CELL) + 
                                   u"\n<br>".join(subtitles) + u"</p>")
    title_dets_html = u"\n".join(title_dets_html_lst)
    xaxis_labels = u"[" + \
        u",\n            ".join([u"{value: %s, text: \"%s\"}" % (i, x[1]) 
                                    for i,x in enumerate(xaxis_dets,1)]) + u"]"
    items_n = len(xaxis_dets)
    if items_n <= 2:
        width = 500
        xgap = 40
        xfontsize = 11
    elif items_n <= 5:
        width = 600
        xgap = 20
        xfontsize = 10
    elif items_n <= 8:
        width = 800
        xgap = 9
        xfontsize = 10
    elif items_n <= 12:
        width = 1100
        xgap = 6
        xfontsize = 7
    else:
        width = 1400
        xgap = 4
        xfontsize = 6
    html = []
    """
    For each series, set colour details.
    For the collection of series as a whole, set the highlight mapping from 
        each series colour.
    From dojox.charting.action2d.Highlight but with extraneous % removed
    """
    (grid_bg, axis_label_font_colour, major_gridline_colour, 
            gridline_width, tooltip_border_colour, colour_mappings) = \
                                                     extract_dojo_style(css_fil)
    colour_cases_list = []
    for bg_colour, hl_colour in colour_mappings:
        colour_cases_list.append(u"""case \"%s\":
                    hlColour = \"%s\";
                    break;""" % (bg_colour, hl_colour))
    colour_cases = u"\n".join(colour_cases_list)
    html.append(u"""
    <script type="text/javascript">

        var DEFAULT_SATURATION  = 100,
        DEFAULT_LUMINOSITY1 = 75,
        DEFAULT_LUMINOSITY2 = 50,

        c = dojox.color,

        cc = function(colour){
            return function(){ return colour; };
        },

        hl = function(colour){

            var a = new c.Color(colour),
                x = a.toHsl();
            if(x.s == 0){
                x.l = x.l < 50 ? 100 : 0;
            }else{
                x.s = DEFAULT_SATURATION;
                if(x.l < DEFAULT_LUMINOSITY2){
                    x.l = DEFAULT_LUMINOSITY1;
                }else if(x.l > DEFAULT_LUMINOSITY1){
                    x.l = DEFAULT_LUMINOSITY2;
                }else{
                    x.l = x.l - DEFAULT_LUMINOSITY2 > DEFAULT_LUMINOSITY1 - x.l 
                        ? DEFAULT_LUMINOSITY2 : DEFAULT_LUMINOSITY1;
                }
            }
            return c.fromHsl(x);
        }
    
        sofaHl = function(colour){
            var hlColour;
            switch (colour.toHex()){
                %(colour_cases)s
                default:
                    hlColour = hl(colour.toHex());
                    break;
            }
            return new dojox.color.Color(hlColour);
        }    
    
        makechartRenumber = function(){
        
            var series0 = new Array();
            series0["varLabel"] = "%(var_label)s";
            series0["yVals"] = %(y_values)s;
            series0["style"] = {stroke: {color: "white"}, fill: "#2996e9"};
            
            var series = new Array(series0);
            var chartconf = new Array();
            chartconf["xaxisLabels"] = %(xaxis_labels)s;
            chartconf["xgap"] = %(xgap)s;
            chartconf["xfontsize"] = %(xfontsize)s;
            chartconf["sofaHl"] = sofaHl;
            chartconf["gridlineWidth"] = %(gridline_width)s;
            chartconf["gridBg"] = \"%(grid_bg)s\";
            chartconf["axisLabelFontColour"] = \"%(axis_label_font_colour)s\";
            chartconf["majorGridlineColour"] = \"%(major_gridline_colour)s\";
            chartconf["tooltipBorderColour"] = \"%(tooltip_border_colour)s\";
            makeBarChart("mychartRenumber", series, chartconf);
        }
    </script>
    %(titles)s
    <div id="mychartRenumber" style="width: %(width)spx; height: 300px;"></div>
    <br>
    <div id="legendMychartRenumber"></div>
    <br>
    """ % {u"colour_cases": colour_cases, u"titles": title_dets_html, 
           u"var_label": var_label, u"y_values": unicode(y_values), 
           u"xaxis_labels": xaxis_labels, u"width": width, u"xgap": xgap, 
           u"xfontsize": xfontsize, u"grid_bg": grid_bg,
           u"axis_label_font_colour": axis_label_font_colour,
           u"major_gridline_colour": major_gridline_colour,
           u"gridline_width": gridline_width, 
           u"tooltip_border_colour": tooltip_border_colour})
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)
