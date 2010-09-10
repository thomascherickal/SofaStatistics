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

def get_basic_dets(dbe, cur, tbl, tbl_filt, fld_measure, measure_val_labels):
    """
    Get frequencies for all non-missing values in variable plus labels.
    """
    debug = False
    obj_quoter = getdata.get_obj_quoter_func(dbe)
    unused, and_tbl_filt = lib.get_tbl_filts(tbl_filt)
    SQL_get_vals = u"SELECT %s, COUNT(*) AS freq " % obj_quoter(fld_measure) + \
        u"FROM %s " % obj_quoter(tbl) + \
        u"WHERE %s IS NOT NULL %s" % (obj_quoter(fld_measure), and_tbl_filt) + \
        u" GROUP BY %s" % obj_quoter(fld_measure)
    if debug: print(SQL_get_vals)
    cur.execute(SQL_get_vals)
    measure_dets = []
    y_vals = []
    for val, freq in cur.fetchall():
        measure_dets.append((val, measure_val_labels.get(val, unicode(val))))
        y_vals.append(freq)
    return measure_dets, y_vals
    
def get_simple_barchart_dets(dbe, cur, tbl, tbl_filt, fld_measure, 
                             xaxis_val_labels):
    return get_basic_dets(dbe, cur, tbl, tbl_filt, fld_measure, 
                          xaxis_val_labels)

def get_pie_chart_dets(dbe, cur, tbl, tbl_filt, fld_measure, 
                       slice_val_labels):
    label_dets, slice_vals = get_basic_dets(dbe, cur, tbl, tbl_filt, 
                                            fld_measure, slice_val_labels)
    if len(label_dets) != len(slice_vals):
        raise Exception(u"Mismatch in number of slice labels and slice values")
    if len(slice_vals) > 30:
        raise Exception(u"More than 30 slices in Pie Chart. Too many.")
    tot_freq = sum(slice_vals)
    slice_dets = []
    for i, slice_val in enumerate(slice_vals):
        slice_dic = {u"y": slice_val, u"text": label_dets[i][1], 
                     u"tooltip": u"%s<br>%s (%s%%)" % 
                     (label_dets[i][1], slice_val, 
                      round((100.0*slice_val)/tot_freq,1))}
        slice_dets.append(slice_dic)
    return slice_dets

def reshape_sql_crosstab_data(raw_data):
    """
    Must be sorted by group by then measures
    e.g. raw_data = [(1,1,56),
                     (1,2,103),
                     (1,3,72),
                     (1,4,40),
                     (2,1,13),
                     (2,2,59),
                     (2,3,200),
                     (2,4,0),]
    from that we want
    1: [56,103,72,40] # separate data by series
    2: [13,59,200,0]
    and
    1,2,3,4 # vals for axis labelling
    """
    debug = False
    series_data = {}
    prev_gp = None # init
    current_series = None
    oth_vals = None
    collect_oth = True
    for current_gp, oth, freq in raw_data:
        if debug: print(current_gp, oth, freq)
        if current_gp == prev_gp: # still in same gp
            current_series.append(freq)
            if collect_oth:
                oth_vals.append(oth)
        else: # transition
            if current_series: # so not the first row
                series_data[prev_gp] = current_series
                collect_oth = False
            prev_gp = current_gp
            current_series = [freq,] # starting new collection of freqs
            if collect_oth:
                oth_vals = [oth,] # starting collection of oths (only once)
    # left last row
    series_data[prev_gp] = current_series
    if debug:
        print(series_data)
        print(oth_vals)
    return series_data, oth_vals

def get_clustered_barchart_dets(dbe, cur, tbl, tbl_filt, fld_measure, fld_gp, 
                                xaxis_val_labels, group_by_val_labels):
    """
    Get labels and frequencies for each series, plus labels for x axis.
    Only include values for either fld_gp or fld_measure if at least one 
        non-null value in the other dimension.  If a whole series is zero, then 
        it won't show.  If there is any value in other dim will show that val 
        and zeroes for rest.
    If too many bars, provide warning.
    Result of a cartesian join on left side of a join to ensure all items in
        crosstab are present.
    SQL returns something like (grouped by fld_gp, fld_measure, with zero freqs 
        as needed):
    data = [(1,1,56),
            (1,2,103),
            (1,3,72),
            (1,4,40),
            (2,1,13),
            (2,2,59),
            (2,3,200),
            (2,4,0),]
    series_dets -- [{"label": "Male", "y_vals": [56,103,72,40],
                    {"label": "Female", "y_vals": [13,59,200,0],}
    xaxis_dets -- [(1, "North"), (2, "South"), (3, "East"), (4, "West"),]
    """
    debug = True
    obj_quoter = getdata.get_obj_quoter_func(dbe)
    where_tbl_filt, and_tbl_filt = lib.get_tbl_filts(tbl_filt)
    SQL_get_measure_vals = u"""SELECT %(fld_measure)s
        FROM %(tbl)s
        WHERE %(fld_gp)s IS NOT NULL AND %(fld_measure)s IS NOT NULL
            %(and_tbl_filt)s
        GROUP BY %(fld_measure)s"""
    SQL_get_gp_by_vals = u"""SELECT %(fld_gp)s
        FROM %(tbl)s
        WHERE %(fld_measure)s IS NOT NULL AND %(fld_gp)s IS NOT NULL
            %(and_tbl_filt)s
        GROUP BY %(fld_gp)s"""
    SQL_cartesian_join = """SELECT * FROM (%s) AS qrygp INNER JOIN 
        (%s) AS qrymeasure""" % (SQL_get_measure_vals, SQL_get_gp_by_vals)
    SQL_group_by = u"""SELECT %(fld_gp)s, %(fld_measure)s,
            COUNT(*) AS freq
        FROM %(tbl)s
        %(where_tbl_filt)s
        GROUP BY %(fld_gp)s, %(fld_measure)s"""
    sql_dic = {u"tbl": obj_quoter(tbl), 
               u"fld_measure": obj_quoter(fld_measure),
               u"fld_gp": obj_quoter(fld_gp),
               u"and_tbl_filt": and_tbl_filt,
               u"where_tbl_filt": where_tbl_filt}
    SQL_cartesian_join = SQL_cartesian_join % sql_dic
    SQL_group_by = SQL_group_by % sql_dic
    sql_dic[u"qrycart"] = SQL_cartesian_join
    sql_dic[u"qrygrouped"] = SQL_group_by
    SQL_get_raw_data = """SELECT %(fld_gp)s, %(fld_measure)s,
            CASE WHEN freq IS NULL THEN 0 ELSE freq END AS N
        FROM (%(qrycart)s) AS qrycart LEFT JOIN (%(qrygrouped)s) AS qrygrouped
        USING(%(fld_gp)s, %(fld_measure)s)
        ORDER BY %(fld_gp)s, %(fld_measure)s""" % sql_dic
    if debug: print(SQL_get_raw_data)
    cur.execute(SQL_get_raw_data)
    raw_data = cur.fetchall()
    if debug: print(raw_data)
    series_data, oth_vals = reshape_sql_crosstab_data(raw_data)
    series_dets = []
    for gp_val, freqs in series_data.items():
        gp_val_label = group_by_val_labels.get(gp_val, unicode(gp_val))
        series_dic = {u"label": gp_val_label, u"y_vals": freqs}
        series_dets.append(series_dic)
    xaxis_dets = []
    for val in oth_vals:
        xaxis_dets.append((val, xaxis_val_labels.get(val, unicode(val))))
    if debug: print(xaxis_dets)
    return xaxis_dets, series_dets

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
    return (css_dojo_dic[u"outer_bg"], 
            css_dojo_dic[u"inner_bg"], 
            css_dojo_dic[u"axis_label_font_colour"], 
            css_dojo_dic[u"major_gridline_colour"], 
            css_dojo_dic[u"gridline_width"], 
            css_dojo_dic[u"stroke_width"], 
            css_dojo_dic[u"tooltip_border_colour"], 
            css_dojo_dic[u"colour_mappings"])

def get_barchart_sizings(xaxis_dets, series_dets):
    debug = False
    n_clusters = len(xaxis_dets)
    n_bars_in_cluster = len(series_dets)
    minor_ticks = u"false"
    if n_clusters <= 2:
        xfontsize = 11
        width = 500 # image width
        xgap = 40
    elif n_clusters <= 5:
        xfontsize = 10
        width = 600
        xgap = 20
    elif n_clusters <= 8:
        xfontsize = 10
        width = 800
        xgap = 9
    elif n_clusters <= 10:
        minor_ticks = u"true"
        xfontsize = 7
        width = 1000
        xgap = 6
    elif n_clusters <= 16:
        minor_ticks = u"true"
        xfontsize = 7
        width = 1200
        xgap = 5
    else:
        minor_ticks = u"true"
        xfontsize = 6
        width = 1400
        xgap = 4
    if n_bars_in_cluster > 1:
        width = width*(1 + n_bars_in_cluster/10.0)
        xgap = xgap/(1 + n_bars_in_cluster/10.0)
        if n_bars_in_cluster < 4:
            xfontsize_mult = 1.2
        else:
            xfontsize_mult = 1.3
        xfontsize = xfontsize*xfontsize_mult
    if debug: print(width)
    return width, xgap, xfontsize, minor_ticks

def setup_highlights(colour_mappings, single_colour, 
                     override_first_highlight=False):
    """
    If single colour in chart, only need one highlight defined.
    If default style and multiple series, redefine highlight for first. 
        Basically a hack so the default chart has a highlight which looks good in   
    """
    colour_cases_list = []
    for i, mappings in enumerate(colour_mappings):
        bg_colour, hl_colour = mappings
        if hl_colour == u"":
            continue # let default highlighting occur
        if i == 0 and override_first_highlight:
            hl_colour = u"#736354"
        colour_cases_list.append(u"""                case \"%s\":
                    hlColour = \"%s\";
                    break;""" % (bg_colour, hl_colour))
        if single_colour:
            break
    colour_cases = u"\n".join(colour_cases_list)
    colour_cases = colour_cases.lstrip()
    return colour_cases

def get_title_dets_html(titles, subtitles, css_idx):
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
    return title_dets_html

def piechart_output(titles, subtitles, slice_dets, css_idx, css_fil, 
                    page_break_after):
    debug = False
    title_dets_html = get_title_dets_html(titles, subtitles, css_idx)
    (outer_bg, inner_bg, axis_label_font_colour, major_gridline_colour, 
            gridline_width, stroke_width, tooltip_border_colour, 
            colour_mappings) = extract_dojo_style(css_fil)
    outer_bg = u"" if outer_bg == u"" \
        else u"chartconf[\"outerBg\"] = \"%s\";" % outer_bg
    colour_cases = setup_highlights(colour_mappings, single_colour=False, 
                                    override_first_highlight=False)
    colours = [str(x[0]) for x in colour_mappings]
    colours.extend(mg.DOJO_COLOURS)
    slice_colours = colours[:30]
    slices_js_list = []
    for slice_det in slice_dets:
        slices_js_list.append(u"{\"y\": %(y)s, \"text\": \"%(text)s\", " 
                              u"\"tooltip\": \"%(tooltip)s\"}" % 
                              {u"y": slice_det[u"y"], 
                                   u"text": slice_det[u"text"],
                                   u"tooltip": slice_det[u"tooltip"]})
    slices_js = u"slices = [" + u",\n                ".join(slices_js_list) + \
                    u"\n];"
    slice_fontsize = 14 if len(slice_dets) < 10 else 10
    label_font_colour = axis_label_font_colour
    html = []
    html.append(u"""
    <script type="text/javascript">

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
            %(slices_js)s
            var chartconf = new Array();
            chartconf["sliceColours"] = %(slice_colours)s;
            chartconf["sliceFontsize"] = %(slice_fontsize)s;
            chartconf["sofaHl"] = sofaHl;
            chartconf["labelFontColour"] = \"%(label_font_colour)s\";
            chartconf["tooltipBorderColour"] = \"%(tooltip_border_colour)s\";
            %(outer_bg)s
            chartconf["innerBg"] = \"%(inner_bg)s\";
            makePieChart("mychartRenumber", slices, chartconf);
        }
    </script>
    %(titles)s
    <div id="mychartRenumber" 
        style="width: %(width)spx; height: %(height)spx;"></div>
    <br>
    """ % {u"slice_colours": slice_colours, u"colour_cases": colour_cases, 
           u"titles": title_dets_html, u"width": 400, u"height": 400,
           u"slices_js": slices_js, u"slice_fontsize": slice_fontsize, 
           u"label_font_colour": label_font_colour,
           u"tooltip_border_colour": tooltip_border_colour,
           u"outer_bg": outer_bg, u"inner_bg": inner_bg,
           })
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)
    
def barchart_output(titles, subtitles, xaxis_dets, series_dets, css_idx, 
                    css_fil, page_break_after):
    """
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    series_labels -- e.g. ["Age Group", ] if simple bar chart,
        e.g. ["Male", "Female"] if clustered bar chart.
    var_numeric -- needs to be quoted or not.
    y_vals -- list of values e.g. [[12, 30, 100.5, -1, 40], ]
    xaxis_dets -- [(1, "Under 20"), (2, "20-29"), (3, "30-39"), (4, "40-64"),
                   (5, "65+")]
    css_idx -- css index so can apply    
    """
    debug = False
    title_dets_html = get_title_dets_html(titles, subtitles, css_idx)
    xaxis_labels = u"[" + \
        u",\n            ".join([u"{value: %s, text: \"%s\"}" % (i, x[1]) 
                                    for i,x in enumerate(xaxis_dets,1)]) + u"]"
    width, xgap, xfontsize, minor_ticks = get_barchart_sizings(xaxis_dets, 
                                                               series_dets)
    html = []
    """
    For each series, set colour details.
    For the collection of series as a whole, set the highlight mapping from 
        each series colour.
    From dojox.charting.action2d.Highlight but with extraneous % removed
    """
    (outer_bg, grid_bg, axis_label_font_colour, major_gridline_colour, 
            gridline_width, stroke_width, tooltip_border_colour, 
            colour_mappings) = extract_dojo_style(css_fil)
    outer_bg = u"" if outer_bg == u"" \
        else u"chartconf[\"outerBg\"] = \"%s\";" % outer_bg
    single_colour = (len(series_dets) == 1)
    override_first_highlight = (css_fil == mg.DEFAULT_CSS_PATH 
                                and single_colour)
    colour_cases = setup_highlights(colour_mappings, single_colour, 
                                    override_first_highlight)
    # build js for every series
    series_js_list = []
    series_names_list = []
    if debug: print(series_dets)
    for i, series_det in enumerate(series_dets):
        series_names_list.append(u"series%s" % i)
        series_js_list.append(u"var series%s = new Array();" % i)
        series_js_list.append(u"            series%s[\"seriesLabel\"] = \"%s\";"
                              % (i, series_det[u"label"]))
        series_js_list.append(u"            series%s[\"yVals\"] = %s;" % 
                              (i, series_det[u"y_vals"]))
        try:
            fill = colour_mappings[i][0]
        except IndexError, e:
            fill = mg.DOJO_COLOURS[i]
        series_js_list.append(u"            series%s[\"style\"] = "
            u"{stroke: {color: \"white\", width: \"%spx\"}, fill: \"%s\"};"
            % (i, stroke_width, fill))
        series_js_list.append(u"")
    series_js = u"\n            ".join(series_js_list)
    series_js += u"\n            var series = new Array(%s);" % \
                                                u", ".join(series_names_list)
    series_js = series_js.lstrip()
    html.append(u"""
    <script type="text/javascript">

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
            %(series_js)s
            var chartconf = new Array();
            chartconf["xaxisLabels"] = %(xaxis_labels)s;
            chartconf["xgap"] = %(xgap)s;
            chartconf["xfontsize"] = %(xfontsize)s;
            chartconf["sofaHl"] = sofaHl;
            chartconf["gridlineWidth"] = %(gridline_width)s;
            chartconf["gridBg"] = \"%(grid_bg)s\";
            chartconf["minorTicks"] = %(minor_ticks)s;
            chartconf["axisLabelFontColour"] = \"%(axis_label_font_colour)s\";
            chartconf["majorGridlineColour"] = \"%(major_gridline_colour)s\";
            chartconf["tooltipBorderColour"] = \"%(tooltip_border_colour)s\";
            %(outer_bg)s
            makeBarChart("mychartRenumber", series, chartconf);
        }
    </script>
    %(titles)s
    <div id="mychartRenumber" style="width: %(width)spx; height: 300px;"></div>
    <br>
    <div id="legendMychartRenumber"></div>
    <br>
    """ % {u"colour_cases": colour_cases, u"titles": title_dets_html, 
           u"series_js": series_js, u"xaxis_labels": xaxis_labels, 
           u"width": width, u"xgap": xgap, u"xfontsize": xfontsize, 
           u"axis_label_font_colour": axis_label_font_colour,
           u"major_gridline_colour": major_gridline_colour,
           u"gridline_width": gridline_width, 
           u"tooltip_border_colour": tooltip_border_colour,
           u"outer_bg": outer_bg, u"grid_bg": grid_bg, 
           u"minor_ticks": minor_ticks})
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)
