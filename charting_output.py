#! /usr/bin/env python
# -*- coding: utf-8 -*-

# NB no html headers here - the script generates those beforehand and appends 
# this and then the html footer.

import pprint

import my_globals as mg
import lib
import my_exceptions
import output

def bar_chart_output(css_idx, titles, subtitles, label, values, x_axis_dets):
    """
    css_idx -- css index so can apply
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    label -- e.g. Germany
    values -- list of values e.g. [12, 30, 100.5, -1, 40]
    x_axis_dets -- [{value: 1, text: "Under 20"},
        {value: 2, text: "20-29"},
        {value: 3, text: "30-39"},
        {value: 4, text: "40-64"},
        {value: 5, text: "65+"}]
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
    return u"""
    <script type="text/javascript">
    makecharts0 = function(){
    var var0 = new Array();
    var0["label"] = "%(label)s";
    var0["values"] = %(values)s;
    var0["style"] = {stroke: {color: "black"}, fill: "#7193b8"};
    var data_arr0 = new Array(var0);
    var xaxis = {labels: %(x_axis)s};
    makeBarChart("mychart0", data_arr0, xaxis);
    </script>
    %(titles)s
    <div id="mychart0" style="width: 800px; height: 300px;"></div>
    <div id="legend_mychart0"></div>
    <br>
    """ % {u"titles": title_dets_html, u"label": label, 
           u"values": unicode(values), u"x_axis": pprint.pformat(x_axis_dets)}

