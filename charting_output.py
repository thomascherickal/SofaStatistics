#! /usr/bin/env python
# -*- coding: utf-8 -*-

# NB no html headers here - the script generates those beforehand and appends 
# this and then the html footer.

import pprint

import my_globals as mg
import lib
import my_exceptions
import output

def barchart_output(titles, subtitles, label, values, x_axis_dets, css_idx, 
                    page_break_after):
    """
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    label -- e.g. Germany
    values -- list of values e.g. [12, 30, 100.5, -1, 40]
    x_axis_dets -- [(1, "Under 20"), (2, "20-29"), (3, "30-39"), (4, "40-64"),
                    (5, "65+")]
    css_idx -- css index so can apply
    """
    (CSS_TBL_TITLE, CSS_TBL_SUBTITLE, 
                            CSS_TBL_TITLE_CELL) = output.get_title_css(css_idx)
    title_dets_html_lst = []
    if titles:
        title_dets_html_lst.append(u"<p class='%s'>" % CSS_TBL_TITLE + 
                                   u"\n<br>".join(titles) + u"</p>")
    if subtitles:
        title_dets_html_lst.append(u"<p class='%s'>" % CSS_TBL_SUBTITLE + 
                                   u"\n<br>".join(subtitles) + u"</p>")
    title_dets_html = u"\n".join(title_dets_html_lst)
    x_axis = u"[" + u",\n            ".join([u"{value: %s, text: \"%s\"}" % 
                                    (x[0], x[1]) for x in x_axis_dets]) + u"]"
    html = []
    html.append(u"""
    <script type="text/javascript">
        makechart_renumber = function(){
            var var0 = new Array();
            var0["label"] = "%(label)s";
            var0["values"] = %(values)s;
            var0["style"] = {stroke: {color: "black"}, fill: "#7193b8"};
            var data_arr0 = new Array(var0);
            var xaxis = {labels: %(x_axis)s};
            makeBarChart("mychart_renumber", data_arr0, xaxis);
        }
    </script>
    %(titles)s
    <div id="mychart_renumber" style="width: 800px; height: 300px;"></div><br>
    <div id="legend_mychart_renumber"></div>
    <br>
    """ % {u"titles": title_dets_html, u"label": label, 
           u"values": unicode(values), u"x_axis": x_axis})
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)
