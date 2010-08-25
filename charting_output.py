#! /usr/bin/env python
# -*- coding: utf-8 -*-

# NB no html headers here - the script generates those beforehand and appends 
# this and then the html footer.

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

def barchart_output(titles, subtitles, var_label, xaxis_dets, y_values, css_idx, 
                    page_break_after):
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
    html = [] # std fill = #7193b8
    html.append(u"""
    <script type="text/javascript">
        makechart_renumber = function(){
            var var0 = new Array();
            var0["var_label"] = "%(var_label)s";
            var0["y_values"] = %(y_values)s;
            var0["style"] = {stroke: {color: "white"}, fill: "#2996e9"};
            var data_arr0 = new Array(var0);
            var xaxis_labels = %(xaxis_labels)s;
            var xgap = %(xgap)s;
            var xfontsize = %(xfontsize)s;
            makeBarChart("mychart_renumber", data_arr0, xaxis_labels, xgap, 
                         xfontsize);
        }
    </script>
    %(titles)s
    <div id="mychart_renumber" style="width: %(width)spx; height: 300px;"></div>
    <br>
    <div id="legend_mychart_renumber"></div>
    <br>
    """ % {u"titles": title_dets_html, u"var_label": var_label, 
           u"y_values": unicode(y_values), u"xaxis_labels": xaxis_labels,
           u"width": width, u"xgap": xgap, u"xfontsize": xfontsize})
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)
