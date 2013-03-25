#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Use English UK spelling e.g. colour and when writing JS use camelcase.
NB no html headers here - the script generates those beforehand and appends 
    this and then the html footer.
For most charts we can use freq and AVG - something SQL does just fine using 
    GROUP BY. Accordingly, we can reuse get_gen_chart_output_dets in many cases. 
In other cases, however, e.g. box plots, we need to analyse the values to get 
    results that SQL can't do well e.g. quartiles. In such cases we have to 
    custom-make the specific queries we need.
"""

import numpy as np
from operator import itemgetter
import pprint

import my_globals as mg
import lib
import my_exceptions
import charting_pylab
import core_stats
import getdata
import output

AVG_CHAR_WIDTH_PXLS = 6.5
AVG_LINE_HEIGHT_PXLS = 12
TXT_WIDTH_WHEN_ROTATED = 4
DOJO_YTITLE_OFFSET_0 = 45
CHART_VAL_KEY = u"chart_val_key"
CHART_SERIES_KEY = u"chart_series_key"
SERIES_KEY = u"series_key"
XY_KEY = u"xy_key"
TRENDLINE_LBL = u"Trend line"
SMOOTHLINE_LBL = u"Smoothed data line"


def get_SQL_raw_data(dbe, tbl_quoted, where_tbl_filt, and_tbl_filt, 
                     var_role_agg, var_role_cat, var_role_series, 
                     var_role_charts, data_show):
    """
    Returns a list of row tuples.
    Each row tuple follows the same templates. Dummy values are used to fill 
        empty fields e.g. series and charts, so that the same structure can be 
        relied upon irrespective of input.
    Fields - charts, series, cat, vals (either the result of COUNT(), AVG() 
        or SUM()).
    E.g. data = [(1,1,1,56),
                 (1,1,2,103),
                 (1,1,3,72),
                 (1,2,1,13),
                 (1,2,2,0),
                 (1,2,3,200),]
    Note - don't use freq as my own field name as it may conflict with freq if 
        selected by user.

    Because it is much easier to understand using an example, imagine the 
        following is our raw data:
        
    charts   series   cat
    gender   country  agegroup
      1        1         1
      1        1         1
      1        1         2
      1        2         4
      1        2         3
      2        1         1
      2        2         5
      .        1         1  # will not be represented in chart because of 
          missing value for one of the grouping variables
      2        .         1  # also not used 
    
    Two things to note: 1) the rows with missing values in any of the grouping 
        variables are discarded as they cannot be plotted; 2) we are going to 
        have a lot of zero values to display.
    Imagine displaying those results as a clustered bar chart of frequencies:
    Chart 1 (Male)
    Three colours - Japan, Italy, Germany
    Five x-labels - Under 20, 20-29, 30-39, 40-64, 65+
    Working from left to right in the chart:
    1,1,1 has a freq of 2 so we will have a bar 2 high for Japan above the Under 20 label
    1,2,1 has no values so the display for Italy above the Under 20 label will be 0
    1,3,1 has no values so the display for Germany above the Under 20 label will be 0
    1,1,2 has a freq of 1 so there will be a bar 1 high for Japan above the 20-29 label
    etc
    NB we can't do a group by on all grouping variables at once because the 
        combinations with zero freqs (e.g. 1,2,1) would not be included. We have 
        to do it grouping variable by grouping variable and then do a cartesian
        join at the end to give us all combinations we need to plot (whether 
        with zeros or another value).
    Looking at an individual grouping variable, we want to include all non-null 
        values where there are no missing values in any of the other grouping 
        variables (or in the variable being averaged if a chart of averages).
    """
    debug = False
    objqtr = getdata.get_obj_quoter_func(dbe)
    cartesian_joiner = getdata.get_cartesian_joiner(dbe)
    if not var_role_cat:
        raise Exception(u"All general charts require a category variable to be "
                        u"identified")
    mycat = objqtr(var_role_cat)
    # Series and charts are optional so we need to autofill them with something 
    # which will keep them in the same group.
    myseries = 1 if not var_role_series else objqtr(var_role_series)
    mycharts = 1 if not var_role_charts else objqtr(var_role_charts)
    is_agg = (data_show in mg.AGGREGATE_DATA_SHOW_OPTS)
    agg_filt = (u" AND %s IS NOT NULL " % objqtr(var_role_agg) if is_agg
                else u" ") 
    sql_dic = {u"tbl": tbl_quoted,
               u"var_role_charts": mycharts,
               u"var_role_series": myseries,
               u"var_role_cat": mycat,
               u"var_role_agg": objqtr(var_role_agg),
               u"where_tbl_filt": where_tbl_filt,
               u"and_tbl_filt": and_tbl_filt,
               u"and_agg_filt": agg_filt}
    # 1) grouping variables
    SQL_charts = ("""SELECT %(var_role_charts)s 
    AS charts
    FROM %(tbl)s
    WHERE %(var_role_charts)s IS NOT NULL 
        AND %(var_role_series)s IS NOT NULL 
        AND %(var_role_cat)s IS NOT NULL
        %(and_tbl_filt)s
        %(and_agg_filt)s
    GROUP BY %(var_role_charts)s""" % sql_dic)
    if debug: print(SQL_charts)
    SQL_series = ("""SELECT %(var_role_series)s 
    AS series
    FROM %(tbl)s
    WHERE %(var_role_series)s IS NOT NULL 
        AND %(var_role_charts)s IS NOT NULL 
        AND %(var_role_cat)s IS NOT NULL
        %(and_tbl_filt)s
        %(and_agg_filt)s
    GROUP BY %(var_role_series)s""" % sql_dic)
    if debug: print(SQL_series)
    SQL_cat = ("""SELECT %(var_role_cat)s 
    AS cat
    FROM %(tbl)s
    WHERE %(var_role_cat)s IS NOT NULL 
        AND %(var_role_charts)s IS NOT NULL 
        AND %(var_role_series)s IS NOT NULL
        %(and_tbl_filt)s
        %(and_agg_filt)s
    GROUP BY %(var_role_cat)s""" % sql_dic)
    if debug: print(SQL_cat)
    SQL_group_by_vars = """SELECT * FROM (%s) AS qrycharts %s 
        (%s) AS qryseries %s
        (%s) AS qrycat""" % (SQL_charts, cartesian_joiner, SQL_series, 
                             cartesian_joiner, SQL_cat)
    if debug: print(u"SQL_group_by_vars:\n%s" % SQL_group_by_vars)
    # 2) Now get measures field with all grouping vars ready to join to full list
    if data_show not in mg.AGGREGATE_DATA_SHOW_OPTS:
        sql_dic[u"val2show"] = u" COUNT(*) "
    elif data_show == mg.SHOW_AVG:
        sql_dic[u"val2show"] = u" AVG(%(var_role_agg)s) " % sql_dic
    elif data_show == mg.SHOW_SUM:
        sql_dic[u"val2show"] = u" SUM(%(var_role_agg)s) " % sql_dic
    else:
        raise Exception("get_SQL_raw_data() not expecting a data_show of %s" % 
                        data_show)
    SQL_vals2show = u"""SELECT %(var_role_charts)s
    AS charts,
        %(var_role_series)s
    AS series,
        %(var_role_cat)s
    AS cat,
        %(val2show)s
    AS val2show
    FROM %(tbl)s
    %(where_tbl_filt)s
    GROUP BY %(var_role_charts)s, 
        %(var_role_series)s, 
        %(var_role_cat)s""" % sql_dic
    if debug: print(u"SQL_vals2show:\n%s" % SQL_vals2show)
    # 3) Put all group by vars on left side of join with measures by those 
    # grouping vars.
    sql_dic[u"SQL_group_by_vars"] = SQL_group_by_vars
    sql_dic[u"SQL_vals2show"] = SQL_vals2show
    SQL_get_raw_data = """SELECT qrygrouping_vars.charts, 
    qrygrouping_vars.series, 
    qrygrouping_vars.cat,
        CASE WHEN val2show IS NULL THEN 0 ELSE val2show END 
    AS val
    FROM (%(SQL_group_by_vars)s) AS qrygrouping_vars 
    LEFT JOIN (%(SQL_vals2show)s) AS qryvals2show
    ON qrygrouping_vars.charts = qryvals2show.charts
    AND qrygrouping_vars.series = qryvals2show.series
    AND qrygrouping_vars.cat = qryvals2show.cat
    ORDER BY qrygrouping_vars.charts, qrygrouping_vars.series, 
        qrygrouping_vars.cat""" % sql_dic    
    if debug: print(u"SQL_get_raw_data:\n%s" % SQL_get_raw_data)
    return SQL_get_raw_data

def get_sorted_y_dets(data_show, major_ticks, sort_opt, vals_etc_lst, dp):
    """
    Sort in place then iterate and build new lists with guaranteed 
        synchronisation.
    """
    idx_measure = 1
    idx_lbl = 2
    lib.sort_value_lbls(sort_opt, vals_etc_lst, idx_measure, idx_lbl)
    sorted_xaxis_dets = []
    sorted_y_vals = []
    sorted_tooltips = []
    measures = [x[idx_measure] for x in vals_etc_lst]
    tot_measures = sum(measures)
    for val, measure, lbl, lbl_split, barlbl in vals_etc_lst:
        sorted_xaxis_dets.append((val, lbl, lbl_split))
        if tot_measures == 0:
            perc = 0
        else:
            perc = 100*(measure/float(tot_measures))
        y_val = perc if data_show == mg.SHOW_PERC else measure
        sorted_y_vals.append(y_val)
        measure2show = int(measure) if dp == 0 else measure # so 12 is 12 not 12.0
        tooltip_dets = [barlbl,] if barlbl else []
        if major_ticks:
            tooltip_dets.append(u"x-val: %s" % val)
            tooltip_dets.append(u"y-val: %s" % measure2show)
        else:
            tooltip_dets.append(u"%s" % measure2show)
        if data_show not in mg.AGGREGATE_DATA_SHOW_OPTS: # OK to show percentage
            tooltip_dets.append(u"%s%%" % round(perc,1))
        tooltip = u"<br>".join(tooltip_dets)
        sorted_tooltips.append(tooltip)
    return sorted_xaxis_dets, sorted_y_vals, sorted_tooltips

def get_prestructured_grouped_data(raw_data, fldnames):
    """
    [(1,1,1,56),
     (1,1,2,103), 
     ...]
    becomes
    [{CHART_VAL_KEY: 1, 
      CHART_SERIES_KEY: [{SERIES_KEY: 1, 
                          XY_KEY: [(1,56), (2,103)]
                             },
                         {SERIES_KEY: 2, 
                          XY_KEY: [(1,23), (2,4), ...]
                             },
                        ], ... ]
    """
    CHART_VAL_KEY = u"chart_val_key"
    CHART_SERIES_KEY = u"chart_series_key"
    SERIES_KEY = u"series_key"
    XY_KEY = u"xy_key"
    prestructure = []
    prev_chart_val = None
    prev_series_val = None
    for raw_data_row in raw_data:
        for data_val, fldname in zip(raw_data_row, fldnames):
            try:
                len_val = len(data_val)
            except TypeError:
                continue
            if len_val > mg.MAX_VAL_LEN_IN_SQL_CLAUSE:
                raise my_exceptions.CategoryTooLong(fldname)
        chart_val, series_val, x_val, y_val = raw_data_row
        same_chart = (chart_val == prev_chart_val)
        if not same_chart:
            chart_dic = {CHART_VAL_KEY: chart_val,
                         CHART_SERIES_KEY: 
                            [{SERIES_KEY: series_val,
                              XY_KEY: [(x_val, y_val),]}
                            ]
                         }
            prestructure.append(chart_dic)
            prev_chart_val = chart_val
            prev_series_val = series_val
        else: # same chart
            same_chart_dic = prestructure[-1]
            # same series?
            same_series = (series_val == prev_series_val)
            # add to existing series or set up new one in existing chart
            if not same_series:
                # add new series to same (last) chart
                series2add = {SERIES_KEY: series_val,
                              XY_KEY: [(x_val, y_val),]}
                same_chart_dic[CHART_SERIES_KEY].append(series2add)
                prev_series_val = series_val
            else:
                # add xy tuple to same (last) series in same (last) chart
                same_series_dic = same_chart_dic[CHART_SERIES_KEY][-1]
                same_series_dic[XY_KEY].append((x_val, y_val))
    return prestructure

def get_overall_title(var_role_agg_name, var_role_cat_name, 
                      var_role_series_name, var_role_charts_name):
    title_bits = []
    if var_role_agg_name:
        title_bits.append(u"Avg %s" % var_role_agg_name)
    if var_role_cat_name:
        if var_role_agg_name:
            title_bits.append(u"By %s" % var_role_cat_name)
        else:
            title_bits.append(u"%s" % var_role_cat_name)
    if var_role_series_name:
        title_bits.append(u"By %s" % var_role_series_name)
    if var_role_charts_name:
        title_bits.append(u"By %s" % var_role_charts_name)
    return u" ".join(title_bits)

def get_overall_title_scatterplot(var_role_x_axis_name, var_role_y_axis_name, 
                                  var_role_series_name, var_role_charts_name):
    title_bits = []
    title_bits.append(u"%s vs %s" % (var_role_x_axis_name, 
                                     var_role_y_axis_name))
    if var_role_series_name:
        title_bits.append(u"By %s" % var_role_series_name)
    if var_role_charts_name:
        title_bits.append(u"By %s" % var_role_charts_name)
    return u" ".join(title_bits)

def charts_append_divider(html, titles, overall_title, indiv_title=u"", 
                          item_type=u""):
    title = overall_title if not titles else titles[0]
    output.append_divider(html, title, indiv_title, item_type)

def structure_gen_data(chart_type, raw_data, xlblsdic, 
                  var_role_agg, var_role_agg_name, var_role_agg_lbls,
                  var_role_cat, var_role_cat_name, var_role_cat_lbls,
                  var_role_series, var_role_series_name, var_role_series_lbls,
                  var_role_charts, var_role_charts_name, var_role_charts_lbls,
                  sort_opt, dp, rotate=False, data_show=mg.SHOW_FREQ, 
                  major_ticks=False):
    """
    Structure data for general charts (use different processes preparing data 
        for histograms, scatterplots etc).
    Take raw columns of data from SQL cursor and create required dict. Note - 
        source data must be sorted by all grouping variables.
    raw_data -- 4 cols (even if has 1 as dummy variable in charts and/or series
        cols): charts, series, cat, vals.
    e.g. raw_data = [(1,1,1,56), (1,1,2,103), (1,1,3,72), (1,1,4,40),
                     (1,2,1,13), (1,2,2,59), (1,2,3,200), (1,2,4,0),]
    Processes to intermediate step first e.g.
        prestructure = [{CHART_VAL_KEY: 1, 
                         CHART_SERIES_KEY: [
              {SERIES_KEY: 1, 
               XY_KEY: [(1,56), (2,103), (3,72), (4,40)] },
              {SERIES_KEY: 2, 
               XY_KEY: [(1,13), (2,59), (3,200), (4,0)] },
             ]}, ]
    Returns chart_output_dets:
    chart_output_dets = {
        mg.CHARTS_OVERALL_TITLE: Age Group vs Gender, # used to label output items
        mg.CHARTS_MAX_X_LBL_LEN: max_x_lbl_len, # used to set height of chart(s)
        mg.CHARTS_MAX_Y_LBL_LEN: max_y_lbl_len, # used to set left axis shift of chart(s)
        mg.CHARTS_MAX_LBL_LINES: max_lbl_lines, # used to set axis lbl drop
        mg.CHARTS_OVERALL_LEGEND_LBL: u"Age Group", # or None if only one series
        mg.CHARTS_CHART_DETS: chart_dets}
    chart_dets = [
        {mg.CHARTS_CHART_LBL: u"Gender: Male", # or None if only one chart
         mg.CHARTS_SERIES_DETS: series_dets},
        {mg.CHARTS_CHART_LBL: u"Gender: Female",
         mg.CHARTS_SERIES_DETS: series_dets}, ...
    ]
    series_dets = {mg.CHARTS_SERIES_LBL_IN_LEGEND: u"Italy", # or None if only one series
                   mg.CHARTS_XAXIS_DETS: [(val, lbl, lbl_split), (...), ...], 
                   mg.CHARTS_SERIES_Y_VALS: [46, 32, 28, 94], 
                   mg.CHARTS_SERIES_TOOLTIPS: [u"46<br>23%", u"32<br>16%", 
                                               u"28<br>14%", u"94<br>47%"]}
    """
    max_x_lbl_len = 0
    max_y_lbl_len = 0
    max_lbl_lines = 0
    fldnames = [var_role_charts_name, var_role_series_name, var_role_cat_name, 
                var_role_agg_name]
    prestructure = get_prestructured_grouped_data(raw_data, fldnames)
    chart_dets = []
    n_charts = len(prestructure)
    if n_charts > mg.MAX_CHARTS_IN_SET:
        raise my_exceptions.TooManyChartsInSeries(var_role_charts_name, 
                                                 max_items=mg.MAX_CHARTS_IN_SET)
    multichart = n_charts > 1
    if multichart:
        chart_fldname = var_role_charts_name
        chart_fldlbls = var_role_charts_lbls
    else: # clustered, line - can have multiple series without being multi-chart
        chart_fldname = None
        chart_fldlbls = {}
    for chart_dic in prestructure:
        series = chart_dic[CHART_SERIES_KEY]
        if len(series) > mg.MAX_CHART_SERIES:
            raise my_exceptions.TooManySeriesInChart(mg.MAX_CHART_SERIES)
        multiseries = (len(series) > 1)
        """
        chart_dic = {CHART_VAL_KEY: 1, 
                     CHART_SERIES_KEY: [
              {SERIES_KEY: 1, 
               XY_KEY: [(1,56), (2,103), (3,72), (4,40)] },
              {SERIES_KEY: 2, 
               XY_KEY: [(1,13), (2,59), (3,200), (4,0)] }, ]}
        to
        {mg.CHARTS_CHART_LBL: u"Gender: Male", # or a dummy title if only one chart because not displayed
         mg.CHARTS_SERIES_DETS: series_dets}
        """
        if multichart:
            chart_val = chart_dic[CHART_VAL_KEY]
            chart_lbl = u"%s: %s" % (chart_fldname, 
                              chart_fldlbls.get(chart_val, unicode(chart_val)))
        else:
            chart_lbl = None
        series_dets = []
        for series_dic in series:
            series_val = series_dic[SERIES_KEY]
            if multiseries:
                legend_lbl = var_role_series_lbls.get(series_val, 
                                                      unicode(series_val))
            else:
                legend_lbl = None
            # process xy vals
            xy_vals = series_dic[XY_KEY]
            vals_etc_lst = []
            for x_val, y_val in xy_vals:
                x_val_lbl = xlblsdic.get(x_val, unicode(x_val))
                (x_val_split_lbl,
                 actual_lbl_width,
                 n_lines) = lib.get_lbls_in_lines(orig_txt=x_val_lbl, 
                                        max_width=17, dojo=True, rotate=rotate)
                if actual_lbl_width > max_x_lbl_len:
                    max_x_lbl_len = actual_lbl_width
                y_lbl_width = len(str(round(y_val, dp)))
                if y_lbl_width > max_y_lbl_len:
                    max_y_lbl_len = y_lbl_width
                if n_lines > max_lbl_lines:
                    max_lbl_lines = n_lines
                if chart_type == mg.CLUSTERED_BARCHART:
                    barlbl = u"%s, %s" % (x_val_lbl, legend_lbl)
                else:
                    barlbl = None
                vals_etc_lst.append((x_val, round(y_val, dp), x_val_lbl, 
                                     x_val_split_lbl, barlbl))
            n_cats = len(vals_etc_lst)
            if chart_type == mg.CLUSTERED_BARCHART:
                if n_cats > mg.MAX_CLUSTERS:
                    raise my_exceptions.TooManyValsInChartSeries(var_role_cat, 
                                                                mg.MAX_CLUSTERS)
            elif chart_type == mg.PIE_CHART:
                if n_cats > mg.MAX_PIE_SLICES:
                    raise my_exceptions.TooManySlicesInPieChart
            else:
                if n_cats > mg.MAX_CATS_GEN:
                    raise my_exceptions.TooManyValsInChartSeries(var_role_cat, 
                                                                mg.MAX_CATS_GEN)
            (sorted_xaxis_dets, 
             sorted_y_vals, 
             sorted_tooltips) = get_sorted_y_dets(data_show, major_ticks, 
                                                  sort_opt, vals_etc_lst, dp)
            series_det = {mg.CHARTS_SERIES_LBL_IN_LEGEND: legend_lbl,
                          mg.CHARTS_XAXIS_DETS: sorted_xaxis_dets, 
                          mg.CHARTS_SERIES_Y_VALS: sorted_y_vals, 
                          mg.CHARTS_SERIES_TOOLTIPS: sorted_tooltips}
            series_dets.append(series_det)
        chart_det = {mg.CHARTS_CHART_LBL: chart_lbl,
                     mg.CHARTS_SERIES_DETS: series_dets}
        chart_dets.append(chart_det)
    overall_title = get_overall_title(var_role_agg_name, var_role_cat_name, 
                                     var_role_series_name, var_role_charts_name)
    chart_output_dets = {mg.CHARTS_OVERALL_TITLE: overall_title,
                         mg.CHARTS_MAX_X_LBL_LEN: max_x_lbl_len,
                         mg.CHARTS_MAX_Y_LBL_LEN: max_y_lbl_len,
                         mg.CHARTS_MAX_LBL_LINES: max_lbl_lines,
                         mg.CHARTS_OVERALL_LEGEND_LBL: var_role_series_name,
                         mg.CHARTS_CHART_DETS: chart_dets}
    return chart_output_dets

def get_gen_chart_output_dets(chart_type, dbe, cur, tbl, tbl_filt, 
                    var_role_agg, var_role_agg_name, var_role_agg_lbls, 
                    var_role_cat, var_role_cat_name, var_role_cat_lbls, 
                    var_role_series, var_role_series_name, var_role_series_lbls, 
                    var_role_charts, var_role_charts_name, var_role_charts_lbls, 
                    sort_opt, rotate=False, data_show=mg.SHOW_FREQ, 
                    major_ticks=False):
    """
    Note - variables must match values relevant to mg.CHART_CONFIG e.g. 
        VAR_ROLE_CATEGORY i.e. var_role_cat, for checking to work 
        (see usage of locals() below).
    Returns some overall details for the chart plus series details (only the
        one series in some cases).
    Note - not all charts have x-axis labels and thus the option of rotating 
        them.
    """
    debug = False
    is_agg = (var_role_agg is not None)
    # validate fields supplied (or not)
    chart_subtype_key = mg.AGGREGATE_KEY if is_agg else mg.INDIV_VAL_KEY
    chart_config = mg.CHART_CONFIG[chart_type][chart_subtype_key]
    for var_dets in chart_config: # looping through available dropdowns for chart
        var_role = var_dets[mg.VAR_ROLE_KEY]
        allows_missing = var_dets[mg.INC_SELECT_KEY]
        matching_input_var = locals()[var_role]
        role_missing = matching_input_var is None
        if role_missing and not allows_missing:
            raise Exception(u"The required field %s is missing for the %s "
                            u"chart type." % (var_role, chart_type))
    # misc
    tbl_quoted = getdata.tblname_qtr(dbe, tbl)
    where_tbl_filt, and_tbl_filt = lib.get_tbl_filts(tbl_filt)
    xlblsdic = var_role_cat_lbls
    # Get data as per setup
    SQL_raw_data = get_SQL_raw_data(dbe, tbl_quoted, where_tbl_filt, 
                                    and_tbl_filt, var_role_agg, var_role_cat, 
                                    var_role_series, var_role_charts, data_show)
    if debug: print(SQL_raw_data)
    try:
        cur.execute(SQL_raw_data)
    except Exception, e:
        raise Exception(u"Unable to get raw data for chart. Orig error: %s" % 
                        lib.ue(e))
    raw_data = cur.fetchall()
    if debug: print(raw_data)
    if not raw_data:
        raise my_exceptions.TooFewValsForDisplay
    # restructure and return data
    dp = 2 if data_show in mg.AGGREGATE_DATA_SHOW_OPTS else 0
    chart_output_dets = structure_gen_data(chart_type, raw_data, xlblsdic, 
                    var_role_agg, var_role_agg_name, var_role_agg_lbls,
                    var_role_cat, var_role_cat_name, var_role_cat_lbls,
                    var_role_series, var_role_series_name, var_role_series_lbls,
                    var_role_charts, var_role_charts_name, var_role_charts_lbls,
                    sort_opt, dp, rotate, data_show, major_ticks)
    if debug: print(chart_output_dets)
    return chart_output_dets

def get_boxplot_dets(dbe, cur, tbl, tbl_filt, var_role_desc, var_role_desc_name,
                    var_role_cat, var_role_cat_name, var_role_cat_lbls,
                    var_role_series, var_role_series_name, var_role_series_lbls,
                    sort_opt, rotate=False):
    """
    NB can't just use group by SQL to get results - need upper and lower 
        quartiles etc and we have to work on the raw values to achieve this. We
        have to do more work outside of SQL to get the values we need.
    xaxis_dets -- [(0, "", ""), (1, "Under 20", ...] NB blanks either end
    
    series_dets -- [{mg.CHART_SERIES_LBL: "Girls", 
        mg.CHART_BOXDETS: [{mg.CHART_BOXPLOT_DISPLAY: True, 
                                mg.CHART_BOXPLOT_LWHISKER: 1.7, 
                                mg.CHART_BOXPLOT_LBOX: 3.2, ...}, 
                           {mg.CHART_BOXPLOT_DISPLAY: True, etc}, ...]}, ...]
    NB supply a boxdet even for an empty box. Put marker that it should be 
        skipped in terms of output to js. mg.CHART_BOXPLOT_DISPLAY
    # list of subseries dicts each of which has a label and a list of dicts 
        (one per box).
    http://en.wikipedia.org/wiki/Box_plot: one of several options: the lowest 
        datum still within 1.5 IQR of the lower quartile, and the highest datum 
        still within 1.5 IQR of the upper quartile.
    Because of this variability, it is appropriate to describe the convention 
        being used for the whiskers and outliers in the caption for the plot.
    """
    debug = False
    dd = mg.DATADETS_OBJ
    objqtr = getdata.get_obj_quoter_func(dbe)
    where_tbl_filt, and_tbl_filt = lib.get_tbl_filts(tbl_filt)
    boxplot_width = 0.25
    chart_dets = []
    xaxis_dets = [] # (0, u"''", u"''")]
    max_x_lbl_len = 0
    max_lbl_lines = 0
    sql_dic = {u"var_role_cat": objqtr(var_role_cat), 
               u"var_role_series": objqtr(var_role_series), 
               u"var_role_desc": objqtr(var_role_desc),
               u"where_tbl_filt": where_tbl_filt, 
               u"and_tbl_filt": and_tbl_filt, 
               u"tbl": getdata.tblname_qtr(dbe, tbl)}
    # 1) Get all series vals appearing in any rows where all fields are 
    # non-missing.
    if var_role_series:
        SQL_series_vals = u"""SELECT %(var_role_series)s 
            FROM %(tbl)s 
            WHERE %(var_role_series)s IS NOT NULL
            AND %(var_role_cat)s IS NOT NULL 
            AND %(var_role_desc)s IS NOT NULL
            %(and_tbl_filt)s 
            GROUP BY %(var_role_series)s""" % sql_dic
        if debug: print(SQL_series_vals)
        cur.execute(SQL_series_vals)
        series_vals = [x[0] for x in cur.fetchall()]
        if debug: print(series_vals)
        if len(series_vals) > mg.MAX_SERIES_IN_BOXPLOT:
            max_items = mg.MAX_SERIES_IN_BOXPLOT
            raise my_exceptions.TooManySeriesInChart(max_items)
    else:
        series_vals = [None,] # Got to have something to loop through ;-)
    # 2) Get all cat vals needed for x-axis i.e. all those appearing in any rows 
    # where all fields are non-missing.
    if var_role_cat:
        and_series_filt = (u"" if not var_role_series 
                           else " AND %(var_role_series)s IS NOT NULL " % 
                           sql_dic)
        sql_dic[u"and_series_filt"] = and_series_filt
        SQL_cat_vals = """SELECT %(var_role_cat)s
            FROM %(tbl)s 
            WHERE %(var_role_cat)s IS NOT NULL
            AND %(var_role_desc)s IS NOT NULL
            %(and_series_filt)s
            %(and_tbl_filt)s 
            GROUP BY %(var_role_cat)s""" % sql_dic
        if debug: print(SQL_cat_vals)
        cur.execute(SQL_cat_vals)
        cat_vals = [x[0] for x in cur.fetchall()]
        # sort appropriately
        cat_vals_and_lbls = [(x, var_role_cat_lbls.get(x, x)) for x in cat_vals]
        if sort_opt == mg.SORT_LBL:
            cat_vals_and_lbls.sort(key=itemgetter(1))
        sorted_cat_vals = [x[0] for x in cat_vals_and_lbls]
        if debug: print(sorted_cat_vals)
        if len(sorted_cat_vals) > mg.MAX_BOXPLOTS_IN_SERIES:
            raise my_exceptions.TooManyBoxplotsInSeries(var_role_cat_name, 
                                            max_items=mg.MAX_BOXPLOTS_IN_SERIES)   
    else:
        sorted_cat_vals = [1,] # the first boxplot is always 1 on the x-axis
    ymin = None # init
    ymax = 0
    first_chart_by = True
    any_missing_boxes = False
    any_displayed_boxes = False
    for series_val in series_vals: # e.g. "Boys" and "Girls"
        if series_val is not None:
            legend_lbl = var_role_series_lbls.get(series_val, 
                                                  unicode(series_val))
            series_val_filt = getdata.make_fld_val_clause(dbe, dd.flds, 
                                                       fldname=var_role_series, 
                                                       val=series_val)
            and_series_val_filt = u" AND %s" % series_val_filt
        else:
            legend_lbl = None
            and_series_val_filt = u" "
        sql_dic[u"and_series_val_filt"] = and_series_val_filt
        # time to get the boxplot information for the series
        boxdet_series = []
        for i, cat_val in enumerate(sorted_cat_vals, 1): # e.g. "Mt Albert Grammar", 
                # "Epsom Girls Grammar", "Hebron Christian College", ...
            if var_role_cat:
                if first_chart_by: # build xaxis_dets once
                    x_val_lbl = var_role_cat_lbls.get(cat_val, unicode(cat_val))
                    (x_val_split_lbl, 
                     actual_lbl_width,
                     n_lines) = lib.get_lbls_in_lines(orig_txt=x_val_lbl, 
                                         max_width=17, dojo=True, rotate=rotate)
                    if actual_lbl_width > max_x_lbl_len:
                        max_x_lbl_len = actual_lbl_width
                    if n_lines > max_lbl_lines:
                        max_lbl_lines = n_lines
                    xaxis_dets.append((i, x_val_lbl, x_val_split_lbl))
                # Now see if any desc values for particular series_val and cat_val
                and_cat_val_filt = u" AND %s" % getdata.make_fld_val_clause(dbe, 
                                                  dd.flds, fldname=var_role_cat, 
                                                  val=cat_val)
            else:
                xaxis_dets.append((i, u"''", "''"))
                and_cat_val_filt = u""
            sql_dic[u"and_cat_val_filt"] = and_cat_val_filt
            SQL_vals2desc = """SELECT %(var_role_desc)s
            FROM %(tbl)s 
            WHERE %(var_role_desc)s IS NOT NULL
            %(and_cat_val_filt)s
            %(and_series_val_filt)s
            %(and_tbl_filt)s""" % sql_dic
            cur.execute(SQL_vals2desc)
            vals2desc = [x[0] for x in cur.fetchall()]
            enough_vals = (len(vals2desc) > mg.MIN_DISPLAY_VALS_FOR_BOXPLOT)
            enough_diff = False
            if enough_vals:
                median = round(np.median(vals2desc),2)
                lq, uq = core_stats.get_quartiles(vals2desc)
                lbox = round(lq, 2)
                ubox = round(uq, 2)
                # Round them because even if all vals the same e.g. 1.0 will differ
                # very slightly because of method used to calc quartiles using 
                # floating point.
                line_vals = set([round(lbox,5), round(median,5), round(ubox,5)])
                enough_diff = (len(line_vals) == 3)
                if debug: print("%s, %s %s %s %s" % (enough_vals, enough_diff, 
                                                     lbox, median, ubox))
            boxplot_display = enough_vals and enough_diff
            if not boxplot_display:
                any_missing_boxes = True
                box_dic = {mg.CHART_BOXPLOT_WIDTH: boxplot_width,
                           mg.CHART_BOXPLOT_DISPLAY: boxplot_display,
                           mg.CHART_BOXPLOT_LWHISKER: None,
                           mg.CHART_BOXPLOT_LBOX: None,
                           mg.CHART_BOXPLOT_MEDIAN: None,
                           mg.CHART_BOXPLOT_UBOX: None,
                           mg.CHART_BOXPLOT_UWHISKER: None,
                           mg.CHART_BOXPLOT_OUTLIERS: None}
            else:
                any_displayed_boxes = True
                iqr = ubox-lbox
                raw_lwhisker = lbox - (1.5*iqr)
                lwhisker = get_lwhisker(raw_lwhisker, lbox, vals2desc)
                min_measure = min(vals2desc)
                if ymin is None:
                    ymin = min_measure
                elif min_measure < ymin:
                    ymin = min_measure
                raw_uwhisker = ubox + (1.5*iqr)
                uwhisker = get_uwhisker(raw_uwhisker, ubox, vals2desc)
                max_measure = max(vals2desc)
                if max_measure > ymax:
                    ymax = max_measure
                outliers = [round(x, 2) for x in vals2desc 
                            if x < lwhisker or x > uwhisker]
                box_dic = {mg.CHART_BOXPLOT_WIDTH: boxplot_width,
                           mg.CHART_BOXPLOT_DISPLAY: boxplot_display,
                           mg.CHART_BOXPLOT_LWHISKER: round(lwhisker, 2),
                           mg.CHART_BOXPLOT_LBOX: round(lbox, 2),
                           mg.CHART_BOXPLOT_MEDIAN: round(median, 2),
                           mg.CHART_BOXPLOT_UBOX: round(ubox, 2),
                           mg.CHART_BOXPLOT_UWHISKER: round(uwhisker, 2),
                           mg.CHART_BOXPLOT_OUTLIERS: outliers}
            boxdet_series.append(box_dic)
        title_bits = []
        title_bits.append(var_role_desc_name)
        title_bits.append(u"By %s" % var_role_cat_name)
        if var_role_series_name:
            title_bits.append(u"By %s" % var_role_series_name)
        overall_title = u" ".join(title_bits)
        series_dic = {mg.CHART_SERIES_LBL: legend_lbl, 
                      mg.CHART_BOXDETS: boxdet_series}
        chart_dets.append(series_dic)
        first_chart_by = False
    if not any_displayed_boxes:
        raise my_exceptions.TooFewBoxplotsInSeries
    xmin = 0.5
    xmax = i+0.5
    ymin, ymax = get_optimal_min_max(ymin, ymax)
    #xaxis_dets.append((xmax, u"''", u"''"))
    if debug: print(xaxis_dets)
    return (xaxis_dets, xmin, xmax, ymin, ymax, max_x_lbl_len, max_lbl_lines,
            overall_title, chart_dets, any_missing_boxes)

def get_lwhisker(raw_lwhisker, lbox, measure_vals):
    """
    Make no lower than the minimum value within (inclusive) 1.5*iqr below lq.
    Must never go above lbox.
    """
    lwhisker = raw_lwhisker # init
    measure_vals.sort() # no side effects
    for val in measure_vals: # going upwards
        if val < raw_lwhisker:
            pass # keep going up
        elif val >= raw_lwhisker:
            lwhisker = val
            break
    if lwhisker > lbox:
        lwhisker = lbox
    return lwhisker

def get_uwhisker(raw_uwhisker, ubox, measure_vals):
    """
    Make sure no higher than the maximum value within (inclusive) 
        1.5*iqr above uq. Must never fall below ubox.
    """
    uwhisker = raw_uwhisker # init
    measure_vals.reverse() # no side effects
    for val in measure_vals: # going downwards
        if val > raw_uwhisker:
            pass # keep going down
        elif val <= raw_uwhisker:
            uwhisker = val
            break
    if uwhisker < ubox:
        uwhisker = ubox
    return uwhisker

def get_histo_dets(dbe, cur, tbl, tbl_filt, flds, var_role_bin, 
                   var_role_bin_name, var_role_charts, var_role_charts_name, 
                   var_role_charts_lbls):
    """
    Make separate db call each histogram. Getting all values anyway and don't 
        want to store in memory.
    Return list of dicts - one for each histogram. Each contains: 
        CHARTS_XAXIS_DETS, CHARTS_SERIES_Y_VALS, CHART_MINVAL, CHART_MAXVAL, 
        CHART_BIN_LBLS.
    xaxis_dets -- [(1, u""), (2: u"", ...]
    y_vals -- [0.091, ...]
    bin_labels -- [u"1 to under 2", u"2 to under 3", ...]
    """
    debug = False
    objqtr = getdata.get_obj_quoter_func(dbe)
    unused, and_tbl_filt = lib.get_tbl_filts(tbl_filt)
    sql_dic = {u"var_role_charts": objqtr(var_role_charts), 
               u"var_role_bin": objqtr(var_role_bin),
               u"and_tbl_filt": and_tbl_filt, 
               u"tbl": getdata.tblname_qtr(dbe, tbl)}
    if var_role_charts:
        SQL_fld_chart_by_vals = u"""SELECT %(var_role_charts)s 
            FROM %(tbl)s 
            WHERE %(var_role_bin)s IS NOT NULL %(and_tbl_filt)s 
            GROUP BY %(var_role_charts)s""" % sql_dic
        cur.execute(SQL_fld_chart_by_vals)
        fld_chart_by_vals = [x[0] for x in cur.fetchall()]
        if len(fld_chart_by_vals) > mg.MAX_CHARTS_IN_SET:
            raise my_exceptions.TooManyChartsInSeries(var_role_charts_name, 
                                                 max_items=mg.MAX_CHARTS_IN_SET)
    else:
        fld_chart_by_vals = [None,] # Got to have something to loop through ;-)
    """
    Set bins for all data at once. If only one histogram, then the perfect 
        result for that. If multiple histograms, then ensures consistent 
        bins to enable comparison.
    If multiple charts, we only handle saw-toothing for the overall data.
    """
    SQL_get_combined_vals = u"""SELECT %(var_role_bin)s 
    FROM %(tbl)s
    WHERE %(var_role_bin)s IS NOT NULL
        %(and_tbl_filt)s
    ORDER BY %(var_role_bin)s""" % sql_dic
    if debug: print(SQL_get_combined_vals)
    cur.execute(SQL_get_combined_vals)
    combined_vals = [x[0] for x in cur.fetchall()]
    # use nicest bins practical
    n_bins, lower_limit, upper_limit = lib.get_bins(min(combined_vals), 
                                                    max(combined_vals))
    (combined_y_vals, combined_start, 
     bin_width, unused) = core_stats.histogram(combined_vals, n_bins, 
                                            defaultreallimits=[lower_limit, 
                                                               upper_limit])
    (unused, combined_start, 
     bin_width) = lib.fix_sawtoothing(combined_vals, n_bins, combined_y_vals, 
                                      combined_start, bin_width)
    histo_dets = []
    for fld_chart_by_val in fld_chart_by_vals:
        if var_role_charts:
            filt = getdata.make_fld_val_clause(dbe, flds, 
                                               fldname=var_role_charts, 
                                               val=fld_chart_by_val)
            and_fld_chart_by_filt = u" and %s" % filt
            fld_chart_by_val_lbl = var_role_charts_lbls.get(fld_chart_by_val, 
                                                         fld_chart_by_val)
            # must get y-vals for each chart individually
            sql_dic[u"and_fld_chart_by_filt"] = and_fld_chart_by_filt
            SQL_get_vals = u"""SELECT %(var_role_bin)s 
                FROM %(tbl)s
                WHERE %(var_role_bin)s IS NOT NULL
                    %(and_tbl_filt)s %(and_fld_chart_by_filt)s
                ORDER BY %(var_role_bin)s""" % sql_dic
            if debug: print(SQL_get_vals)
            cur.execute(SQL_get_vals)
            vals = [x[0] for x in cur.fetchall()]
            if len(vals) < mg.MIN_HISTO_VALS:
                raise my_exceptions.TooFewValsForDisplay(min_n=mg.MIN_HISTO_VALS)
            defaultreallimits = [lower_limit, upper_limit]
            (y_vals, unused, unused, 
             unused) = core_stats.histogram(vals, n_bins, defaultreallimits)
            vals4norm = vals
            chart_by_lbl = u"%s: %s" % (var_role_charts_name, 
                                        fld_chart_by_val_lbl)
        else: # only one chart - combined values are the values we need
            y_vals = combined_y_vals
            vals4norm = combined_vals
            chart_by_lbl = None
        # not fixing saw-toothing 
        minval = combined_start
        # only show as many decimal points as needed
        dp = 0
        while True:
            if (round(combined_start, dp) 
                    != round(combined_start + bin_width, dp)) or dp > 6:
                break
            dp += 1
        bin_ranges = [] # needed for labels
        bins = [] # needed to get y vals for normal dist curve
        start = combined_start
        for unused in y_vals:
            bin_start = round(start, dp)
            bins.append(bin_start)
            bin_end = round(start + bin_width, dp)
            start = bin_end
            bin_ranges.append((bin_start, bin_end))
        bin_lbls = [_(u"%(lower)s to < %(upper)s") % 
                     {u"lower": x[0], u"upper": x[1]} for x in bin_ranges]
        bin_lbls[-1] = bin_lbls[-1].replace(u"<", u"<=")
        maxval = bin_end
        xaxis_dets = [(x+1, u"") for x in range(n_bins)]
        norm_ys = list(lib.get_normal_ys(vals4norm, np.array(bins)))
        sum_yval = sum(y_vals)
        sum_norm_ys = sum(norm_ys)
        norm_multiplier = sum_yval/(1.0*sum_norm_ys)
        norm_ys = [x*norm_multiplier for x in norm_ys]
        if debug: print(minval, maxval, xaxis_dets, y_vals, bin_lbls)
        title_bits = []
        title_bits.append(var_role_bin_name)
        if var_role_charts_name:
            title_bits.append(u"By %s" % var_role_charts_name)
        overall_title = u" ".join(title_bits)    
        histo_dic = {mg.CHARTS_CHART_LBL: chart_by_lbl,
                     mg.CHARTS_XAXIS_DETS: xaxis_dets,
                     mg.CHARTS_SERIES_Y_VALS: y_vals,
                     mg.CHART_NORMAL_Y_VALS: norm_ys,
                     mg.CHART_MINVAL: minval,
                     mg.CHART_MAXVAL: maxval,
                     mg.CHART_BIN_LBLS: bin_lbls}
        histo_dets.append(histo_dic)
    return overall_title, histo_dets

def get_scatterplot_dets(dbe, cur, tbl, tbl_filt, flds, 
                    var_role_x_axis, var_role_x_axis_name, 
                    var_role_y_axis, var_role_y_axis_name, 
                    var_role_series, var_role_series_name, var_role_series_lbls,
                    var_role_charts, var_role_charts_name, var_role_charts_lbls, 
                    unique=True):
    """
    unique -- unique x-y pairs only
    """
    debug = False
    objqtr = getdata.get_obj_quoter_func(dbe)
    where_tbl_filt, and_tbl_filt = lib.get_tbl_filts(tbl_filt)
    fld_x_axis = objqtr(var_role_x_axis)
    fld_y_axis = objqtr(var_role_y_axis)
    xy_filt_tpl = (u" %%s %s IS NOT NULL AND %s IS NOT NULL " % (fld_x_axis, 
                                                                 fld_y_axis))
    where_xy_filt = (xy_filt_tpl % u"WHERE")
    and_xy_filt = (xy_filt_tpl % u"AND")
    # Series and charts are optional so we need to autofill them with something 
    # which will keep them in the same group.
    myseries = 1 if not var_role_series else objqtr(var_role_series)
    mycharts = 1 if not var_role_charts else objqtr(var_role_charts)
    sql_dic = {u"tbl": getdata.tblname_qtr(dbe, tbl), 
               u"var_role_charts": mycharts,
               u"var_role_series": myseries,
               u"fld_x_axis": objqtr(var_role_x_axis),
               u"fld_y_axis": objqtr(var_role_y_axis),
               u"where_tbl_filt": where_tbl_filt,
               u"and_tbl_filt": and_tbl_filt,
               u"where_xy_filt": where_xy_filt,
               u"and_xy_filt": and_xy_filt,}
    # only want rows where all variables are not null
    SQL_get_xy_pairs = (u"""SELECT %(var_role_charts)s 
    AS charts,
        %(var_role_series)s 
    AS series,
        %(fld_x_axis)s
    AS x, 
        %(fld_y_axis)s
    AS y
    FROM %(tbl)s
    WHERE charts IS NOT NULL 
        AND series IS NOT NULL 
        %(and_xy_filt)s
        %(and_tbl_filt)s
    GROUP BY charts, series""" % sql_dic)
    if unique:
        SQL_get_xy_pairs += u", %(fld_x_axis)s, %(fld_y_axis)s" % sql_dic
    if debug: print(SQL_get_xy_pairs)
    cur.execute(SQL_get_xy_pairs)
    raw_data = cur.fetchall()
    if not raw_data:
        raise my_exceptions.TooFewValsForDisplay
    fldnames = [sql_dic[u"var_role_charts"], sql_dic[u"var_role_series"], 
                sql_dic[u"fld_x_axis"], sql_dic[u"fld_y_axis"]]
    prestructure = get_prestructured_grouped_data(raw_data, fldnames)
    chart_dets = []
    n_charts = len(prestructure)
    if n_charts > mg.MAX_CHARTS_IN_SET:
        raise my_exceptions.TooManyChartsInSeries(var_role_charts_name, 
                                                 max_items=mg.MAX_CHARTS_IN_SET)
    multichart = n_charts > 1
    if multichart:
        chart_fldname = var_role_charts_name
        chart_fldlbls = var_role_charts_lbls
    else: # can have multiple series but only one chart
        chart_fldname = None
        chart_fldlbls = {}
    for chart_dic in prestructure:
        series = chart_dic[CHART_SERIES_KEY]
        if len(series) > mg.MAX_SCATTERPLOT_SERIES:
            max_items = mg.MAX_SCATTERPLOT_SERIES
            raise my_exceptions.TooManySeriesInChart(max_items)
        multiseries = (len(series) > 1)
        if multichart:
            chart_val = chart_dic[CHART_VAL_KEY]
            chart_lbl = u"%s: %s" % (chart_fldname, 
                              chart_fldlbls.get(chart_val, unicode(chart_val)))
        else:
            chart_lbl = None
        series_dets = []
        for series_dic in series:
            series_val = series_dic[SERIES_KEY]
            if multiseries:
                legend_lbl = var_role_series_lbls.get(series_val, 
                                                      unicode(series_val))
            else:
                legend_lbl = None
            # process xy vals
            xy_vals = series_dic[XY_KEY]
            list_x = []
            list_y = []
            data_tups = [] # only for dojo
            for x_val, y_val in xy_vals:
                list_x.append(x_val)
                list_y.append(y_val)
                data_tups.append((x_val, y_val))
            series_det = {mg.CHARTS_SERIES_LBL_IN_LEGEND: legend_lbl,
                          mg.LIST_X: list_x, 
                          mg.LIST_Y: list_y,
                          mg.DATA_TUPS: data_tups}
            series_dets.append(series_det)
        chart_det = {mg.CHARTS_CHART_LBL: chart_lbl,
                     mg.CHARTS_SERIES_DETS: series_dets}
        chart_dets.append(chart_det)
    overall_title = get_overall_title_scatterplot(var_role_x_axis_name, 
                                    var_role_y_axis_name, var_role_series_name, 
                                    var_role_charts_name)
    scatterplot_dets = {mg.CHARTS_OVERALL_LEGEND_LBL: var_role_series_name,
                        mg.CHARTS_CHART_DETS: chart_dets}
    return overall_title, scatterplot_dets

def reshape_sql_crosstab_data(raw_data, dp=0):
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
    for current_gp, oth, measure in raw_data:
        if dp == 0:
            measure = int(measure)
        else:
            measure = round(measure, dp)
        if debug: print(current_gp, oth, measure)
        if current_gp == prev_gp: # still in same gp
            current_series.append(measure)
            if collect_oth:
                oth_vals.append(oth)
        else: # transition
            if current_series: # so not the first row
                series_data[prev_gp] = current_series
                collect_oth = False
            prev_gp = current_gp
            current_series = [measure,] # starting new collection of measures
            if collect_oth:
                oth_vals = [oth,] # starting collection of oths (only once)
    # left last row
    series_data[prev_gp] = current_series
    if debug:
        print(series_data)
        print(oth_vals)
    return series_data, oth_vals

def get_histo_sizings(var_lbl, n_bins, minval, maxval):
    debug = False
    MIN_PXLS_PER_BAR = 30
    MIN_CHART_WIDTH = 700
    PADDING_PXLS = 5
    AVG_CHAR_WIDTH_PXLS = 10.5 # need more for histograms
    max_lbl_width = max(len(str(round(x,0))) for x in [minval, maxval])
    if debug: print(u"max_lbl_width: %s" % max_lbl_width)
    min_bin_width = max(max_lbl_width*AVG_CHAR_WIDTH_PXLS, MIN_PXLS_PER_BAR)
    width_x_title = len(var_lbl)*AVG_CHAR_WIDTH_PXLS + PADDING_PXLS
    width = max([n_bins*min_bin_width, width_x_title, MIN_CHART_WIDTH])
    if debug: print(u"Width: %s" % width)
    return width

def get_barchart_sizings(x_title, n_clusters, n_bars_in_cluster, 
                         max_x_lbl_width):
    debug = False
    MIN_PXLS_PER_BAR = 30
    MIN_CLUSTER_WIDTH = 60
    MIN_CHART_WIDTH = 450
    PADDING_PXLS = 35
    min_width_per_cluster = (MIN_PXLS_PER_BAR*n_bars_in_cluster)
    width_per_cluster = (max([min_width_per_cluster, MIN_CLUSTER_WIDTH,
                           max_x_lbl_width*AVG_CHAR_WIDTH_PXLS]) + PADDING_PXLS)
    width_x_title = len(x_title)*AVG_CHAR_WIDTH_PXLS + PADDING_PXLS
    width = max([width_per_cluster*n_clusters, width_x_title, MIN_CHART_WIDTH])
    # If wide labels, may not display almost any if one is too wide. Widen to take account.
    if n_clusters <= 2:
        xgap = 20
    elif n_clusters <= 5:
        xgap = 10
    elif n_clusters <= 8:
        xgap = 8
    elif n_clusters <= 10:
        xgap = 6
    elif n_clusters <= 16:
        xgap = 5
    else:
        xgap = 4
    if n_clusters <= 5:
        xfontsize = 10
    elif n_clusters > 5:
        xfontsize = 9
    elif n_clusters > 10:
        xfontsize = 8
    init_margin_offset_l = 30 if width > 1200 else 18 # else gets squeezed out e.g. in percent
    minor_ticks = u"true" if n_clusters > 8 else u"false"
    if debug: print(width, xgap, xfontsize, minor_ticks, init_margin_offset_l)
    return width, xgap, xfontsize, minor_ticks, init_margin_offset_l

def get_linechart_sizings(major_ticks, x_title, xaxis_dets, max_lbl_width, 
                          series_dets):
    """
    major_ticks -- e.g. want to only see the main labels and won't need it to be 
        so wide.
    """
    debug = False
    n_cats = len(xaxis_dets)
    n_series = len(series_dets)
    MIN_PXLS_PER_CAT = 10
    MIN_CHART_WIDTH = 700 if n_series < 5 else 900 # when vertically squeezed good to have more horizontal room
    PADDING_PXLS = 10
    width_per_cat = (max([MIN_PXLS_PER_CAT, max_lbl_width*AVG_CHAR_WIDTH_PXLS]) 
                     + PADDING_PXLS)
    width_x_title = len(x_title)*AVG_CHAR_WIDTH_PXLS + PADDING_PXLS
    width = max([n_cats*width_per_cat, width_x_title, MIN_CHART_WIDTH])
    if major_ticks:
        width = max(width*0.4, MIN_CHART_WIDTH)
    if n_cats <= 5:
        xfontsize = 10
    elif n_cats > 5:
        xfontsize = 9
    elif n_cats > 10:
        xfontsize = 8
    minor_ticks = u"true" if n_cats > 8 and not major_ticks else u"false"
    micro_ticks = u"true" if n_cats > 100 else u"false"
    if debug: print(width, xfontsize, minor_ticks, micro_ticks)
    return width, xfontsize, minor_ticks, micro_ticks

def get_boxplot_sizings(x_title, xaxis_dets, max_lbl_width, series_dets):
    debug = False
    n_cats = len(xaxis_dets)
    n_series = len(series_dets)
    PADDING_PXLS = 50
    MIN_PXLS_PER_BOX = 30
    MIN_CHART_WIDTH = 200 if len(xaxis_dets) == 1 else 400 # only one box
    min_pxls_per_cat = MIN_PXLS_PER_BOX*n_series
    width_per_cat = (max([min_pxls_per_cat, max_lbl_width*AVG_CHAR_WIDTH_PXLS]) 
                     + PADDING_PXLS)
    width_x_title = len(x_title)*AVG_CHAR_WIDTH_PXLS + PADDING_PXLS
    width = max([width_per_cat*n_cats, width_x_title, MIN_CHART_WIDTH])
    minor_ticks = u"true" if n_cats > 10 else u"false"
    if n_cats <= 5:
        xfontsize = 10
    elif n_cats > 5:
        xfontsize = 9
    elif n_cats > 10:
        xfontsize = 8
    if debug: print(width, xfontsize)
    return width, xfontsize, minor_ticks

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

def get_lbl_dets(xaxis_dets):
    # can be a risk that a split label for the middle x value will overlap with x-axis label below
    lbl_dets = []
    for i, xaxis_det in enumerate(xaxis_dets, 1):
        val_lbl = xaxis_det[2] # the split variant of the label
        lbl_dets.append(u"{value: %s, text: %s}" % (i, val_lbl))
    return lbl_dets

def get_ytitle_offset(max_y_lbl_len, x_lbl_len, max_safe_x_lbl_len_pxls, 
                      rotate=False):
    """
    Need to shift y-axis title left if wide y-axis label or first x-axis label 
        is wide.
    """
    debug = False
    # 45 is a good total offset with label width of 20
    ytitle_offset = DOJO_YTITLE_OFFSET_0 - 20
    # x-axis adjustment
    if not rotate:
        try:
            if x_lbl_len*AVG_CHAR_WIDTH_PXLS > max_safe_x_lbl_len_pxls:
                ytitle_offset += (AVG_CHAR_WIDTH_PXLS*x_lbl_len
                                  -max_safe_x_lbl_len_pxls)/2.0 # half of label goes to the right
        except Exception:
            pass
    # y-axis adjustment
    try:
        max_width_y_labels = AVG_CHAR_WIDTH_PXLS*max_y_lbl_len
        if debug: print(u"max_width_y_labels: %s" % max_width_y_labels)
        ytitle_offset += max_width_y_labels
    except Exception:
        pass
    if debug: print(u"ytitle_offset: %s" % ytitle_offset)
    if ytitle_offset < DOJO_YTITLE_OFFSET_0:
        ytitle_offset = DOJO_YTITLE_OFFSET_0
    return ytitle_offset

def get_ymax(chart_output_dets):
    all_y_vals = []
    for chart_dets in chart_output_dets[mg.CHARTS_CHART_DETS]:
        for series_det in chart_dets[mg.CHARTS_SERIES_DETS]:
            all_y_vals += series_det[mg.CHARTS_SERIES_Y_VALS]
    max_all_y_vals = max(all_y_vals)
    ymax = max_all_y_vals*1.1
    return ymax

def get_axis_lbl_drop(multichart, rotate, max_lbl_lines):
    debug = False
    axis_lbl_drop = 10 if multichart else 15
    if not rotate:
        extra_lines = max_lbl_lines - 1
        axis_lbl_drop += AVG_LINE_HEIGHT_PXLS*extra_lines
    if debug: print(axis_lbl_drop)
    return axis_lbl_drop

def get_indiv_title(multichart, chart_det):
    if multichart:
        indiv_title = chart_det[mg.CHARTS_CHART_LBL]
        indiv_title_html = ("<p><b>%s</b></p>" % indiv_title)
    else:
        indiv_title = u""
        indiv_title_html = u""
    return indiv_title, indiv_title_html

def simple_barchart_output(titles, subtitles, x_title, y_title, 
                           chart_output_dets, rotate, show_borders, css_idx, 
                           css_fil, page_break_after):
    """
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    chart_output_dets -- see structure_gen_data()
    var_numeric -- needs to be quoted or not.
    xaxis_dets -- [(1, "Under 20"), (2, "20-29"), (3, "30-39"), (4, "40-64"),
                   (5, "65+")]
    css_idx -- css index so can apply appropriate css styles
    """
    debug = False
    axis_lbl_rotate = -90 if rotate else 0
    html = []
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    title_dets_html = output.get_title_dets_html(titles, subtitles, css_idx)
    html.append(title_dets_html)
    multichart = len(chart_output_dets[mg.CHARTS_CHART_DETS]) > 1
    max_x_lbl_len = chart_output_dets[mg.CHARTS_MAX_X_LBL_LEN]
    max_y_lbl_len = chart_output_dets[mg.CHARTS_MAX_Y_LBL_LEN]
    max_lbl_lines = chart_output_dets[mg.CHARTS_MAX_LBL_LINES]
    axis_lbl_drop = get_axis_lbl_drop(multichart, rotate, max_lbl_lines)
    height = 310
    if rotate:
        height += AVG_CHAR_WIDTH_PXLS*max_x_lbl_len
    height += axis_lbl_drop  # compensate for loss of bar display height
    """
    For each series, set colour details.
    For the collection of series as a whole, set the highlight mapping from 
        each series colour.
    From dojox.charting.action2d.Highlight but with extraneous % removed
    """
    (outer_bg, grid_bg, axis_lbl_font_colour, major_gridline_colour, 
            gridline_width, stroke_width, tooltip_border_colour, 
            colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
    item_colours = output.colour_mappings_to_item_colours(colour_mappings)
    fill = item_colours[0]
    outer_bg = (u"" if outer_bg == u""
                else u"chartconf[\"outerBg\"] = \"%s\";" % outer_bg)
    single_colour = True
    override_first_highlight = (css_fil == mg.DEFAULT_CSS_PATH 
                                and single_colour)
    colour_cases = setup_highlights(colour_mappings, single_colour, 
                                    override_first_highlight)
    n_bars_in_cluster = 1
    # always the same number, irrespective of order
    n_clusters = len(chart_output_dets[mg.CHARTS_CHART_DETS][0]\
                     [mg.CHARTS_SERIES_DETS][0][mg.CHARTS_XAXIS_DETS])
    max_x_lbl_width = TXT_WIDTH_WHEN_ROTATED if rotate else max_x_lbl_len
    (width, xgap, xfontsize, minor_ticks, 
     init_margin_offset_l) = get_barchart_sizings(x_title, n_clusters, 
                                                  n_bars_in_cluster,
                                                  max_x_lbl_width)
    chart_dets = chart_output_dets[mg.CHARTS_CHART_DETS]
    # following details are same across all charts so look at first
    chart0_series_dets = chart_dets[0][mg.CHARTS_SERIES_DETS]
    # only one series per chart by design
    series_det = chart0_series_dets[0]
    xaxis_dets = series_det[mg.CHARTS_XAXIS_DETS]
    idx_1st_xdets = 0
    idx_xlbl = 1
    x_lbl_len = len(xaxis_dets[idx_1st_xdets][idx_xlbl])
    max_safe_x_lbl_len_pxls = 180
    y_title_offset = get_ytitle_offset(max_y_lbl_len, x_lbl_len, 
                                       max_safe_x_lbl_len_pxls, rotate)
    ymax = get_ymax(chart_output_dets)
    if multichart:
        width = width*0.9
        xgap = xgap*0.8
        xfontsize = xfontsize*0.75
    margin_offset_l = (init_margin_offset_l + y_title_offset 
                       - DOJO_YTITLE_OFFSET_0)
    if rotate:
        margin_offset_l += 15
    width += margin_offset_l
    stroke_width = stroke_width if show_borders else 0
    # loop through charts
    for chart_idx, chart_det in enumerate(chart_dets):
        indiv_title, indiv_title_html = get_indiv_title(multichart, chart_det)
        # only one series per chart by design
        series_det = chart_det[mg.CHARTS_SERIES_DETS][0]
        xaxis_dets = series_det[mg.CHARTS_XAXIS_DETS]
        lbl_dets = get_lbl_dets(xaxis_dets)
        xaxis_lbls = u"[" + u",\n            ".join(lbl_dets) + u"]"
        pagebreak = (u"" if chart_idx % 2 == 0
                     else u"page-break-after: always;")
        # build js for the single series (only 1 ever per chart in simple bar charts)
        series_js_list = []
        series_names_list = []
        series_names_list.append(u"series0")
        series_js_list.append(u"var series0 = new Array();")
        series_js_list.append(u"series0[\"seriesLabel\"] = \"%s\";"
                                   % series_det[mg.CHARTS_SERIES_LBL_IN_LEGEND])
        series_js_list.append(u"series0[\"yVals\"] = %s;" % 
                                            series_det[mg.CHARTS_SERIES_Y_VALS])
        tooltips = (u"['" + "', '".join(series_det[mg.CHARTS_SERIES_TOOLTIPS]) 
                    + u"']")
        series_js_list.append(u"series0[\"options\"] = "
            u"{stroke: {color: \"white\", width: \"%spx\"}, fill: \"%s\", "
            u"yLbls: %s};" % (stroke_width, fill, tooltips))
        series_js_list.append(u"")
        series_js = u"\n    ".join(series_js_list)
        series_js += (u"\n    var series = new Array(%s);"
                      % u", ".join(series_names_list))
        series_js = series_js.lstrip()
        html.append(u"""
<script type="text/javascript">

var sofaHlRenumber%(chart_idx)s = function(colour){
    var hlColour;
    switch (colour.toHex()){
        %(colour_cases)s
        default:
            hlColour = hl(colour.toHex());
            break;
    }
    return new dojox.color.Color(hlColour);
}

makechartRenumber%(chart_idx)s = function(){
    %(series_js)s
    var chartconf = new Array();
    chartconf["xaxisLabels"] = %(xaxis_lbls)s;
    chartconf["xgap"] = %(xgap)s;
    chartconf["xfontsize"] = %(xfontsize)s;
    chartconf["sofaHl"] = sofaHlRenumber%(chart_idx)s;
    chartconf["gridlineWidth"] = %(gridline_width)s;
    chartconf["gridBg"] = \"%(grid_bg)s\";
    chartconf["minorTicks"] = %(minor_ticks)s;
    chartconf["axisLabelFontColour"] = \"%(axis_lbl_font_colour)s\";
    chartconf["majorGridlineColour"] = \"%(major_gridline_colour)s\";
    chartconf["xTitle"] = \"\";
    chartconf["axisLabelDrop"] = %(axis_lbl_drop)s;
    chartconf["axisLabelRotate"] = %(axis_lbl_rotate)s;
    chartconf["yTitleOffset"] = %(y_title_offset)s;
    chartconf["marginOffsetL"] = %(margin_offset_l)s;
    chartconf["xTitle"] = \"%(x_title)s\";
    chartconf["yTitle"] = \"%(y_title)s\";
    chartconf["tooltipBorderColour"] = \"%(tooltip_border_colour)s\";
    chartconf["connectorStyle"] = \"%(connector_style)s\";
    chartconf["ymax"] = %(ymax)s;
    %(outer_bg)s
    makeBarChart("mychartRenumber%(chart_idx)s", series, chartconf);
}
</script>

<div class="screen-float-only" style="margin-right: 10px; %(pagebreak)s">
%(indiv_title_html)s
<div id="mychartRenumber%(chart_idx)s" 
    style="width: %(width)spx; height: %(height)spx;">
    </div>
</div>""" % {u"colour_cases": colour_cases,
             u"series_js": series_js, u"xaxis_lbls": xaxis_lbls, 
             u"width": width, u"height": height, u"ymax": ymax, u"xgap": xgap, 
             u"xfontsize": xfontsize, u"indiv_title_html": indiv_title_html,
             u"axis_lbl_font_colour": axis_lbl_font_colour,
             u"major_gridline_colour": major_gridline_colour,
             u"gridline_width": gridline_width, u"axis_lbl_drop": axis_lbl_drop,
             u"axis_lbl_rotate": axis_lbl_rotate,
             u"y_title_offset": y_title_offset, 
             u"margin_offset_l": margin_offset_l,
             u"x_title": x_title, u"y_title": y_title, 
             u"tooltip_border_colour": tooltip_border_colour,
             u"connector_style": connector_style, 
             u"outer_bg": outer_bg,  u"pagebreak": pagebreak,
             u"chart_idx": u"%02d" % chart_idx,
             u"grid_bg": grid_bg, u"minor_ticks": minor_ticks})
        overall_title = chart_output_dets[mg.CHARTS_OVERALL_TITLE]
        charts_append_divider(html, titles, overall_title, indiv_title, 
                              u"Bar Chart")
    if debug: 
        print(u"y_title_offset: %s, margin_offset_l: %s" % (y_title_offset, 
                                                            margin_offset_l))
    """
    zero padding chart_idx so that when we search and replace, and go to 
        replace Renumber1 with Renumber15, we don't change Renumber16 to 
        Renumber156 ;-)
    """
    html.append(u"""<div style="clear: both;">&nbsp;&nbsp;</div>""")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)

def clustered_barchart_output(titles, subtitles, x_title, y_title, 
                              chart_output_dets, rotate, show_borders, css_idx, 
                              css_fil, page_break_after):
    """
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    chart_output_dets -- see structure_gen_data()
    var_numeric -- needs to be quoted or not.
    xaxis_dets -- [(1, "Under 20"), (2, "20-29"), (3, "30-39"), (4, "40-64"),
                   (5, "65+")]
    css_idx -- css index so can apply appropriate css styles
    """
    debug = False
    axis_lbl_rotate = -90 if rotate else 0
    html = []
    multichart = len(chart_output_dets[mg.CHARTS_CHART_DETS]) > 1
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    title_dets_html = output.get_title_dets_html(titles, subtitles, css_idx)
    html.append(title_dets_html)
    max_x_lbl_len = chart_output_dets[mg.CHARTS_MAX_X_LBL_LEN]
    max_y_lbl_len = chart_output_dets[mg.CHARTS_MAX_Y_LBL_LEN]
    max_lbl_lines = chart_output_dets[mg.CHARTS_MAX_LBL_LINES]
    axis_lbl_drop = get_axis_lbl_drop(multichart, rotate, max_lbl_lines)
    legend_lbl = chart_output_dets[mg.CHARTS_OVERALL_LEGEND_LBL]
    height = 310
    if rotate:
        height += AVG_CHAR_WIDTH_PXLS*max_x_lbl_len 
    height += axis_lbl_drop  # compensate for loss of bar display height
    """
    For each series, set colour details.
    For the collection of series as a whole, set the highlight mapping from 
        each series colour.
    From dojox.charting.action2d.Highlight but with extraneous % removed
    """
    (outer_bg, grid_bg, axis_lbl_font_colour, major_gridline_colour, 
            gridline_width, stroke_width, tooltip_border_colour, 
            colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
    outer_bg = (u"" if outer_bg == u""
                else u"chartconf[\"outerBg\"] = \"%s\";" % outer_bg)
    chart_dets = chart_output_dets[mg.CHARTS_CHART_DETS]
    # following details are same across all charts so look at first
    chart0_series_dets = chart_dets[0][mg.CHARTS_SERIES_DETS]
    n_bars_in_cluster = len(chart0_series_dets)
    n_clusters = len(chart0_series_dets[0][mg.CHARTS_XAXIS_DETS])
    max_lbl_width = TXT_WIDTH_WHEN_ROTATED if rotate else max_x_lbl_len
    (width, xgap, xfontsize, minor_ticks, 
     init_margin_offset_l) = get_barchart_sizings(x_title, n_clusters, 
                                               n_bars_in_cluster, max_lbl_width)
    series_det = chart0_series_dets[0]
    xaxis_dets = series_det[mg.CHARTS_XAXIS_DETS]
    idx_1st_xdets = 0
    idx_xlbl = 1
    x_lbl_len = len(xaxis_dets[idx_1st_xdets][idx_xlbl])
    max_safe_x_lbl_len_pxls = 180
    y_title_offset = get_ytitle_offset(max_y_lbl_len, x_lbl_len, 
                                       max_safe_x_lbl_len_pxls, rotate)
    ymax = get_ymax(chart_output_dets)
    margin_offset_l = (init_margin_offset_l + y_title_offset 
                       - DOJO_YTITLE_OFFSET_0)
    if rotate:
        margin_offset_l += 15
    if multichart:
        width = width*0.8
        xgap = xgap*0.8
        xfontsize = xfontsize*0.8
        margin_offset_l += 15
    width += margin_offset_l
    series_colours_by_lbl = get_series_colours_by_lbl(chart_output_dets, 
                                                      css_fil)
    stroke_width = stroke_width if show_borders else 0
    # loop through charts
    for chart_idx, chart_det in enumerate(chart_dets):
        series_dets = chart_det[mg.CHARTS_SERIES_DETS]
        if debug: print(series_dets)
        legend = u"""
        <p style="float: left; font-weight: bold; margin-right: 12px; 
                margin-top: 9px;">
            %s:
        </p>
        <div id="legendMychartRenumber%02d">
            </div>""" % (legend_lbl, chart_idx)
        indiv_title, indiv_title_html = get_indiv_title(multichart, chart_det)
        single_colour = False
        override_first_highlight = (css_fil == mg.DEFAULT_CSS_PATH 
                                    and single_colour)
        colour_cases = setup_highlights(colour_mappings, single_colour, 
                                        override_first_highlight)
        series_js_list = []
        series_names_list = []
        for series_idx, series_det in enumerate(series_dets):
            series_lbl = series_det[mg.CHARTS_SERIES_LBL_IN_LEGEND]
            xaxis_dets = series_det[mg.CHARTS_XAXIS_DETS]
            lbl_dets = get_lbl_dets(xaxis_dets)
            xaxis_lbls = u"[" + u",\n            ".join(lbl_dets) + u"]"
            series_names_list.append(u"series%s" % series_idx)
            series_js_list.append(u"var series%s = new Array();" % series_idx)
            series_js_list.append(u"series%s[\"seriesLabel\"] = \"%s\";"
                                                    % (series_idx, series_lbl))
            series_js_list.append(u"series%s[\"yVals\"] = %s;" 
                          % (series_idx, series_det[mg.CHARTS_SERIES_Y_VALS]))
            fill = series_colours_by_lbl[series_lbl]
            tooltips = (u"['" 
                        + "', '".join(series_det[mg.CHARTS_SERIES_TOOLTIPS]) 
                        + u"']")
            series_js_list.append(u"series%s[\"options\"] = "
                u"{stroke: {color: \"white\", width: \"%spx\"}, fill: \"%s\", "
                u"yLbls: %s};" % (series_idx, stroke_width, fill, tooltips))
            series_js_list.append(u"")
            series_js = u"\n    ".join(series_js_list)
            new_array = u", ".join(series_names_list)
            series_js += u"\n    var series = new Array(%s);" % new_array
            series_js = series_js.lstrip()
        html.append(u"""
<script type="text/javascript">

var sofaHlRenumber%(chart_idx)s = function(colour){
    var hlColour;
    switch (colour.toHex()){
        %(colour_cases)s
        default:
            hlColour = hl(colour.toHex());
            break;
    }
    return new dojox.color.Color(hlColour);
}

makechartRenumber%(chart_idx)s = function(){
    %(series_js)s
    var chartconf = new Array();
    chartconf["xaxisLabels"] = %(xaxis_lbls)s;
    chartconf["xgap"] = %(xgap)s;
    chartconf["xfontsize"] = %(xfontsize)s;
    chartconf["sofaHl"] = sofaHlRenumber%(chart_idx)s;
    chartconf["gridlineWidth"] = %(gridline_width)s;
    chartconf["gridBg"] = \"%(grid_bg)s\";
    chartconf["minorTicks"] = %(minor_ticks)s;
    chartconf["axisLabelFontColour"] = \"%(axis_lbl_font_colour)s\";
    chartconf["majorGridlineColour"] = \"%(major_gridline_colour)s\";
    chartconf["xTitle"] = \"%(x_title)s\";
    chartconf["axisLabelDrop"] = %(axis_lbl_drop)s;
    chartconf["axisLabelRotate"] = %(axis_lbl_rotate)s;
    chartconf["yTitleOffset"] = %(y_title_offset)s;
    chartconf["marginOffsetL"] = %(margin_offset_l)s;
    chartconf["yTitle"] = \"%(y_title)s\";
    chartconf["tooltipBorderColour"] = \"%(tooltip_border_colour)s\";
    chartconf["connectorStyle"] = \"%(connector_style)s\";
    chartconf["ymax"] = %(ymax)s;
    %(outer_bg)s
    makeBarChart("mychartRenumber%(chart_idx)s", series, chartconf);
}
</script>

<div class="screen-float-only" style="margin-right: 10px; ">
%(indiv_title_html)s
<div id="mychartRenumber%(chart_idx)s" 
    style="width: %(width)spx; height: %(height)spx;">
    </div>
%(legend)s
</div>""" % {u"colour_cases": colour_cases, u"legend": legend,
             u"series_js": series_js, u"xaxis_lbls": xaxis_lbls,
             u"indiv_title_html": indiv_title_html, 
             u"width": width, u"height": height, u"xgap": xgap, u"ymax": ymax,
             u"xfontsize": xfontsize,
             u"axis_lbl_font_colour": axis_lbl_font_colour,
             u"major_gridline_colour": major_gridline_colour,
             u"gridline_width": gridline_width, 
             u"axis_lbl_drop": axis_lbl_drop,
             u"axis_lbl_rotate": axis_lbl_rotate,
             u"y_title_offset": y_title_offset,
             u"margin_offset_l": margin_offset_l,
             u"x_title": x_title, u"y_title": y_title,
             u"tooltip_border_colour": tooltip_border_colour, 
             u"connector_style": connector_style, 
             u"outer_bg": outer_bg,
             u"grid_bg": grid_bg, u"minor_ticks": minor_ticks,
             u"chart_idx": u"%02d" % chart_idx,})
        overall_title = chart_output_dets[mg.CHARTS_OVERALL_TITLE]
        charts_append_divider(html, titles, overall_title, indiv_title, 
                              u"Clust Bar")
    if debug: 
        print(u"y_title_offset: %s, margin_offset_l: %s" % (y_title_offset, 
                                                            margin_offset_l))
    html.append(u"""<div style="clear: both;">&nbsp;&nbsp;</div>""")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)

def piechart_output(titles, subtitles, chart_output_dets, inc_val_dets, 
                    css_fil, css_idx, page_break_after):
    """
    chart_output_dets -- see structure_gen_data()
    """
    debug = False
    html = []
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    multichart = len(chart_output_dets[mg.CHARTS_CHART_DETS]) > 1
    title_dets_html = output.get_title_dets_html(titles, subtitles, css_idx)
    html.append(title_dets_html)
    width = 500 if mg.PLATFORM == mg.WINDOWS else 450
    if multichart:
        width = width*0.8
    height = 350 if multichart else 400
    radius = 120 if multichart else 140
    lbl_offset = -20 if multichart else -30
    (outer_bg, grid_bg, axis_lbl_font_colour, 
     unused, unused, unused, tooltip_border_colour, 
     colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
    outer_bg = (u"" if outer_bg == u""
                else u"""chartconf["outerBg"] = "%s";""" % outer_bg)
    colour_cases = setup_highlights(colour_mappings, single_colour=False, 
                                    override_first_highlight=False)
    item_colours = output.colour_mappings_to_item_colours(colour_mappings)
    cat_colours_by_lbl = get_cat_colours_by_lbl(chart_output_dets, item_colours)
    if debug: print(pprint.pformat(cat_colours_by_lbl))
    #slice_colours = item_colours[:30]
    lbl_font_colour = axis_lbl_font_colour
    chart_dets = chart_output_dets[mg.CHARTS_CHART_DETS]
    slice_fontsize = 14 if len(chart_dets) < 10 else 10
    if multichart:
        slice_fontsize = slice_fontsize*0.8
    # loop through charts
    for chart_idx, chart_det in enumerate(chart_dets):
        # only one series per chart by design
        series_det = chart_det[mg.CHARTS_SERIES_DETS][0]
        pagebreak = u"" if chart_idx % 2 == 0 else u"page-break-after: always;"
        slices_js_lst = []
        # build indiv slice details for this chart
        y_vals = series_det[mg.CHARTS_SERIES_Y_VALS]
        tot_y_vals = sum(y_vals)
        xy_dets = zip(series_det[mg.CHARTS_XAXIS_DETS], y_vals)
        colours_for_this_chart = []
        for ((unused, val_lbl, split_lbl), y_val) in xy_dets:
            # supplies ALL slices in combined set, even if 0.0 as "y" val.
            if y_val == 0: # no slice will be shown so leave it out
                continue
            colours_for_this_chart.append(cat_colours_by_lbl[val_lbl])
            tiplbl = val_lbl.replace(u"\n", u" ") # line breaks mean no display
            slice_pct = round((100.0*y_val)/tot_y_vals, 1)
            tooltip = u"%s<br>%s (%s%%)" % (tiplbl, int(y_val), slice_pct)
            val2show = u"\"%s\"" % tooltip if inc_val_dets else split_lbl
            if mg.PLATFORM == mg.WINDOWS:
                val2show = val2show.replace(u"<br>", u": ")
            slices_js_lst.append(u"{\"y\": %(y)s, \"text\": %(text)s, " 
                    u"\"tooltip\": \"%(tooltip)s\"}" % 
                    {u"y": y_val, u"text": val2show, u"tooltip": tooltip})
        if debug:
            print(cat_colours_by_lbl)
            print(colours_for_this_chart)
        slices_js = (u"slices = [" + (u",\n" + u" "*4*4).join(slices_js_lst) 
                     + u"\n];")
        indiv_title, indiv_title_html = get_indiv_title(multichart, chart_det)
        html.append(u"""
<script type="text/javascript">
makechartRenumber%(chart_idx)s = function(){
    var sofaHlRenumber%(chart_idx)s = function(colour){
        var hlColour;
        switch (colour.toHex()){
            %(colour_cases)s
            default:
                hlColour = hl(colour.toHex());
                break;
        }
        return new dojox.color.Color(hlColour);
    }            
    %(slices_js)s
    var chartconf = new Array();
    chartconf["sliceColours"] = %(slice_colours)s;
    chartconf["sliceFontsize"] = %(slice_fontsize)s;
    chartconf["sofaHl"] = sofaHlRenumber%(chart_idx)s;
    chartconf["labelFontColour"] = "%(lbl_font_colour)s";
    chartconf["tooltipBorderColour"] = "%(tooltip_border_colour)s";
    chartconf["connectorStyle"] = "%(connector_style)s";
    %(outer_bg)s
    chartconf["gridBg"] = "%(grid_bg)s";
    chartconf["radius"] = %(radius)s;
    chartconf["labelOffset"] = %(lbl_offset)s;
    makePieChart("mychartRenumber%(chart_idx)s", slices, chartconf);
}
</script>

<div class="screen-float-only" style="margin-right: 10px; %(pagebreak)s">
%(indiv_title_html)s
<div id="mychartRenumber%(chart_idx)s" 
    style="width: %(width)spx; height: %(height)spx;">
    </div>
</div>""" % {u"slice_colours": colours_for_this_chart, 
             u"colour_cases": colour_cases, 
             u"width": width, u"height": height, u"radius": radius,
             u"lbl_offset": lbl_offset, u"pagebreak": pagebreak,
             u"indiv_title_html": indiv_title_html,
             u"slices_js": slices_js, u"slice_fontsize": slice_fontsize, 
             u"lbl_font_colour": lbl_font_colour,
             u"tooltip_border_colour": tooltip_border_colour,
             u"connector_style": connector_style, u"outer_bg": outer_bg, 
             u"grid_bg": grid_bg, u"chart_idx": u"%02d" % chart_idx,
             })
        overall_title = chart_output_dets[mg.CHARTS_OVERALL_TITLE]
        charts_append_divider(html, titles, overall_title, indiv_title, 
                              u"Pie Chart")
    html.append(u"""<div style="clear: both;">&nbsp;&nbsp;</div>""")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)

def get_cat_colours_by_lbl(chart_output_dets, item_colours):
    # get all lbls in use across all series
    debug = False
    lbls_in_use = [] # order matters so we can give first cats the best colours in list (using themed one before DOJO fillers)
    for chart_dets in chart_output_dets[mg.CHARTS_CHART_DETS]:
        series_det = chart_dets[mg.CHARTS_SERIES_DETS][0] # only one series per chart
        y_vals = series_det[mg.CHARTS_SERIES_Y_VALS]
        xy_dets = zip(series_det[mg.CHARTS_XAXIS_DETS], y_vals)
        for ((unused, val_lbl, unused), y_val) in xy_dets:
            val_lbl_shown = y_val != 0
            if val_lbl_shown and val_lbl not in lbls_in_use:
                lbls_in_use.append(val_lbl)
    cat_colours_by_lbl = {}
    for lbl_in_use, colour2use in zip(lbls_in_use, item_colours):
        cat_colours_by_lbl[lbl_in_use] = colour2use
    if debug: print(cat_colours_by_lbl)
    return cat_colours_by_lbl

def get_series_colours_by_lbl(chart_output_dets, css_fil):
    unused, item_colours, unused = output.get_stats_chart_colours(css_fil)
    # check every series in every chart to get full list
    series_colours_by_lbl = {}
    series_lbls = []
    for chart_dets in chart_output_dets[mg.CHARTS_CHART_DETS]:
        series_dets = chart_dets[mg.CHARTS_SERIES_DETS]
        for series_det in series_dets:
            series_lbl = series_det[mg.CHARTS_SERIES_LBL_IN_LEGEND]
            if series_lbl not in series_lbls: # can't use set because want to retain order
                series_lbls.append(series_det[mg.CHARTS_SERIES_LBL_IN_LEGEND])
    for i, series_lbl in enumerate(series_lbls):
        series_colours_by_lbl[series_lbl] = item_colours[i]
    return series_colours_by_lbl

def get_trend_y_vals(y_vals):
    "Returns values to plot a straight line which fits the y_vals provided"
    debug = False
    sumy = sum(y_vals)
    if debug: print("sumy: %s" % sumy)
    n = len(y_vals)
    sumx = sum(range(1,n+1))
    if debug: print("sumx: %s" % sumx)
    sumxy = 0
    sumx2 = 0
    for x, y_val in enumerate(y_vals,1):
        sumxy += x*y_val
        sumx2 += x**2
    if debug: print("sumxy: %s" % sumxy)
    if debug: print("sumx2: %s" % sumx2)
    b_num = (n*sumxy)-(sumx*sumy)
    if debug: print("b_num: %s" % b_num)
    b_denom = (n*sumx2) - (sumx**2)
    if debug: print("b_denom: %s" % b_denom)
    b = b_num/(1.0*b_denom)
    a = (sumy - (sumx*b))/(1.0*n)
    trend_y_vals = []
    for x in range(1,n+1):
        trend_y_vals.append(a + b*x)
    return trend_y_vals

def get_smooth_y_vals(y_vals):
    "Returns values to plot a smoothed line which fits the y_vals provided"
    smooth_y_vals = []
    weight = 0.8
    val1 = None
    val2 = None
    val3 = None
    val4 = None
    for i, y_val in enumerate(y_vals, 1):
        if i > 3:
            val1 = val2 # slips down a notch
        if i > 2:
            val2 = val3
        if i > 1:
            val3 = val4
        val4 = y_val # pops in at the top
        vals = [val4, val3, val2, val1]
        numer = 0
        denom = 0
        for i, val in enumerate(vals,1):
            if val is not None:
                numer += val*(weight**i)
                denom += weight**i
        smooth_y_vals.append(numer/(1.0*denom))
    return smooth_y_vals

def linechart_output(titles, subtitles, x_title, y_title, chart_output_dets, 
                     rotate, major_ticks, inc_trend, inc_smooth, css_fil, 
                     css_idx, page_break_after):
    """
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    chart_output_dets -- see structure_gen_data()
    css_idx -- css index so can apply    
    """
    debug = False
    axis_lbl_rotate = -90 if rotate else 0
    html = []
    multichart = len(chart_output_dets[mg.CHARTS_CHART_DETS]) > 1
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    title_dets_html = output.get_title_dets_html(titles, subtitles, css_idx)
    html.append(title_dets_html)
    # following details are same across all charts so look at first
    chart_dets = chart_output_dets[mg.CHARTS_CHART_DETS]
    chart0_series_dets = chart_dets[0][mg.CHARTS_SERIES_DETS]
    n_series = len(chart0_series_dets)
    multiseries = n_series > 1
    xaxis_dets = chart0_series_dets[0][mg.CHARTS_XAXIS_DETS]
    max_x_lbl_len = chart_output_dets[mg.CHARTS_MAX_X_LBL_LEN]
    max_y_lbl_len = chart_output_dets[mg.CHARTS_MAX_Y_LBL_LEN]
    max_lbl_lines = chart_output_dets[mg.CHARTS_MAX_LBL_LINES]
    axis_lbl_drop = get_axis_lbl_drop(multichart, rotate, max_lbl_lines)
    legend_lbl = chart_output_dets[mg.CHARTS_OVERALL_LEGEND_LBL]
    height = 310
    if rotate:
        height += AVG_CHAR_WIDTH_PXLS*max_x_lbl_len 
    height += axis_lbl_drop  # compensate for loss of bar display height
    max_lbl_width = TXT_WIDTH_WHEN_ROTATED if rotate else max_x_lbl_len
    (width, xfontsize, 
     minor_ticks, micro_ticks) = get_linechart_sizings(major_ticks, x_title, 
                                                      xaxis_dets, max_lbl_width, 
                                                      chart0_series_dets)
    init_margin_offset_l = 25 if width > 1200 else 15 # gets squeezed
    idx_1st_xdets = 0
    idx_xlbl = 1
    x_lbl_len = len(xaxis_dets[idx_1st_xdets][idx_xlbl])
    max_safe_x_lbl_len_pxls = 90
    ymax = get_ymax(chart_output_dets)
    y_title_offset = get_ytitle_offset(max_y_lbl_len, x_lbl_len, 
                                       max_safe_x_lbl_len_pxls, rotate)
    if multichart:
        width = width*0.8
        xfontsize = xfontsize*0.8
        init_margin_offset_l += 10
    margin_offset_l = (init_margin_offset_l + y_title_offset 
                       - DOJO_YTITLE_OFFSET_0)
    """
    For each series, set colour details.
    For the collection of series as a whole, set the highlight mapping from 
        each series colour.
    From dojox.charting.action2d.Highlight but with extraneous % removed
    """
    (unused, unused, axis_lbl_font_colour, major_gridline_colour, 
            gridline_width, unused, tooltip_border_colour, 
            unused, connector_style) = lib.extract_dojo_style(css_fil)
    grid_bg, item_colours, unused = output.get_stats_chart_colours(css_fil)
    # Can't have white for line charts because always a white outer background
    axis_lbl_font_colour = (axis_lbl_font_colour
                            if axis_lbl_font_colour != u"white" else u"black")
    series_colours_by_lbl = get_series_colours_by_lbl(chart_output_dets, 
                                                      css_fil)
    # loop through charts
    for chart_idx, chart_det in enumerate(chart_dets):
        series_dets = chart_det[mg.CHARTS_SERIES_DETS]
        pagebreak = u"" if chart_idx % 2 == 0 else u"page-break-after: always;"
        if debug: print(series_dets)
        if multiseries:
            legend = u"""
        <p style="float: left; font-weight: bold; margin-right: 12px; 
                margin-top: 9px;">
            %s:
        </p>
        <div id="legendMychartRenumber%02d">
            </div>""" % (legend_lbl, chart_idx)
        else:
            legend = u"" 
        indiv_title, indiv_title_html = get_indiv_title(multichart, chart_det)
        """
        If only one series, and trendlines/smoothlines are selected, make 
            additional series for each as appropriate.
        """
        if not multiseries:
            series0 = series_dets[0]
            dummy_tooltips = [u"",]
            if inc_trend or inc_smooth:
                raw_y_vals = series0[mg.CHARTS_SERIES_Y_VALS]
            if inc_trend:
                trend_y_vals = get_trend_y_vals(raw_y_vals)
                # repeat most of it
                trend_series = {
                    mg.CHARTS_SERIES_LBL_IN_LEGEND: TRENDLINE_LBL, 
                    mg.CHARTS_XAXIS_DETS: series0[mg.CHARTS_XAXIS_DETS],
                    mg.CHARTS_SERIES_Y_VALS: trend_y_vals,
                    mg.CHARTS_SERIES_TOOLTIPS: dummy_tooltips}
                series_dets.append(trend_series)
                n_series = len(series_dets)
                series_colours_by_lbl[TRENDLINE_LBL] = item_colours[n_series]
            if inc_smooth:
                smooth_y_vals = get_smooth_y_vals(raw_y_vals)
                smooth_series = {
                     mg.CHARTS_SERIES_LBL_IN_LEGEND: SMOOTHLINE_LBL, 
                     mg.CHARTS_XAXIS_DETS: series0[mg.CHARTS_XAXIS_DETS],
                     mg.CHARTS_SERIES_Y_VALS: smooth_y_vals,
                     mg.CHARTS_SERIES_TOOLTIPS: dummy_tooltips}
                series_dets.append(smooth_series)
                n_series = len(series_dets)
                series_colours_by_lbl[SMOOTHLINE_LBL] = item_colours[n_series]
            if debug: pprint.pprint(series_dets)
        series_js_list = []
        series_names_list = []
        for series_idx, series_det in enumerate(series_dets):
            series_lbl = series_det[mg.CHARTS_SERIES_LBL_IN_LEGEND]
            xaxis_dets = series_det[mg.CHARTS_XAXIS_DETS]
            lbl_dets = get_lbl_dets(xaxis_dets)
            xaxis_lbls = u"[" + u",\n            ".join(lbl_dets) + u"]"
            series_names_list.append(u"series%s" % series_idx)
            series_js_list.append(u"var series%s = new Array();" % series_idx)
            series_js_list.append(u"series%s[\"seriesLabel\"] = \"%s\";"
                                                    % (series_idx, series_lbl))
            series_js_list.append(u"series%s[\"yVals\"] = %s;" % 
                              (series_idx, series_det[mg.CHARTS_SERIES_Y_VALS]))
            stroke = series_colours_by_lbl[series_lbl]
            # To set markers explicitly:
            # http://dojotoolkit.org/api/1.5/dojox/charting/Theme/Markers/CIRCLE
            # e.g. marker: dojox.charting.Theme.defaultMarkers.CIRCLE"
            if (series_idx == 1 and (inc_trend or inc_smooth)
                or series_idx == 2 and (inc_trend and inc_smooth)):
                # curved has tension and no markers
                # tension has no effect on already straight (trend) line
                plot_style = u", plot: 'curved'"
            else:
                plot_style = u""
            tooltips = (u"['" 
                + "', '".join(series_det[mg.CHARTS_SERIES_TOOLTIPS]) + u"']")
            series_js_list.append(u"series%s[\"options\"] = "
                u"{stroke: {color: '%s', width: '6px'}, yLbls: %s %s};"
                % (series_idx, stroke, tooltips, plot_style))
            series_js_list.append(u"")
        series_js = u"\n    ".join(series_js_list)
        series_js += (u"\n    var series = new Array(%s);" %
                      u", ".join(series_names_list))
        series_js = series_js.lstrip()
        html.append(u"""
    <script type="text/javascript">
    
    makechartRenumber%(chart_idx)s = function(){
        %(series_js)s
        var chartconf = new Array();
        chartconf["xaxisLabels"] = %(xaxis_lbls)s;
        chartconf["xfontsize"] = %(xfontsize)s;
        chartconf["gridlineWidth"] = %(gridline_width)s;
        chartconf["gridBg"] = "%(grid_bg)s";
        chartconf["minorTicks"] = %(minor_ticks)s;
        chartconf["microTicks"] = %(micro_ticks)s;
        chartconf["axisLabelFontColour"] = "%(axis_lbl_font_colour)s";
        chartconf["majorGridlineColour"] = "%(major_gridline_colour)s";
        chartconf["xTitle"] = "%(x_title)s";
        chartconf["axisLabelDrop"] = %(axis_lbl_drop)s;
        chartconf["axisLabelRotate"] = %(axis_lbl_rotate)s;
        chartconf["yTitleOffset"] = %(y_title_offset)s;
        chartconf["marginOffsetL"] = %(margin_offset_l)s;
        chartconf["yTitle"] = "%(y_title)s";
        chartconf["ymax"] = %(ymax)s;
        chartconf["tooltipBorderColour"] = "%(tooltip_border_colour)s";
        chartconf["connectorStyle"] = "%(connector_style)s";
        makeLineChart("mychartRenumber%(chart_idx)s", series, chartconf);
    }
    </script>
        
    <div class="screen-float-only" style="margin-right: 10px; %(pagebreak)s">
    %(indiv_title_html)s
    <div id="mychartRenumber%(chart_idx)s" style="width: %(width)spx; 
            height: %(height)spx;">
        </div>
    %(legend)s
    </div>""" % {u"legend": legend,
                 u"series_js": series_js, u"xaxis_lbls": xaxis_lbls, 
                 u"indiv_title_html": indiv_title_html, 
                 u"width": width, u"height": height, u"xfontsize": xfontsize, 
                 u"axis_lbl_font_colour": axis_lbl_font_colour,
                 u"major_gridline_colour": major_gridline_colour,
                 u"gridline_width": gridline_width, u"pagebreak": pagebreak,
                 u"axis_lbl_drop": axis_lbl_drop,
                 u"axis_lbl_rotate": axis_lbl_rotate, u"ymax": ymax,
                 u"y_title_offset": y_title_offset,
                 u"margin_offset_l": margin_offset_l,
                 u"x_title": x_title, u"y_title": y_title,
                 u"tooltip_border_colour": tooltip_border_colour,
                 u"connector_style": connector_style, 
                 u"grid_bg": grid_bg, 
                 u"minor_ticks": minor_ticks, u"micro_ticks": micro_ticks,
                 u"chart_idx": u"%02d" % chart_idx})
        overall_title = chart_output_dets[mg.CHARTS_OVERALL_TITLE]
        charts_append_divider(html, titles, overall_title, indiv_title, 
                              u"Line Chart")
    if debug: 
        print(u"y_title_offset: %s, margin_offset_l: %s" % (y_title_offset, 
                                                            margin_offset_l))
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)
    
def areachart_output(titles, subtitles, x_title, y_title, chart_output_dets, 
                     rotate, major_ticks, css_fil, css_idx, page_break_after):
    """
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    chart_output_dets -- see structure_gen_data()
    css_idx -- css index so can apply    
    """
    debug = False
    axis_lbl_rotate = -90 if rotate else 0
    html = []
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    title_dets_html = output.get_title_dets_html(titles, subtitles, css_idx)
    html.append(title_dets_html)
    multichart = len(chart_output_dets[mg.CHARTS_CHART_DETS]) > 1
    max_x_lbl_len = chart_output_dets[mg.CHARTS_MAX_X_LBL_LEN]
    max_y_lbl_len = chart_output_dets[mg.CHARTS_MAX_Y_LBL_LEN]
    max_lbl_lines = chart_output_dets[mg.CHARTS_MAX_LBL_LINES]
    axis_lbl_drop = get_axis_lbl_drop(multichart, rotate, max_lbl_lines)
    max_lbl_width = TXT_WIDTH_WHEN_ROTATED if rotate else max_x_lbl_len
    height = 310
    if rotate:
        height += AVG_CHAR_WIDTH_PXLS*max_x_lbl_len   
    # following details are same across all charts so look at first
    chart_dets = chart_output_dets[mg.CHARTS_CHART_DETS]
    chart0_series_dets = chart_dets[0][mg.CHARTS_SERIES_DETS]
    xaxis_dets = chart0_series_dets[0][mg.CHARTS_XAXIS_DETS]
    (width, xfontsize, minor_ticks, 
     micro_ticks) = get_linechart_sizings(major_ticks, x_title, xaxis_dets, 
                                          max_lbl_width, chart0_series_dets)
    init_margin_offset_l = 25 if width > 1200 else 15 # gets squeezed
    idx_1st_xdets = 0
    idx_xlbl = 1
    x_lbl_len = len(xaxis_dets[idx_1st_xdets][idx_xlbl])
    max_safe_x_lbl_len_pxls = 90
    y_title_offset = get_ytitle_offset(max_y_lbl_len, x_lbl_len, 
                                       max_safe_x_lbl_len_pxls, rotate)
    ymax = get_ymax(chart_output_dets)
    if multichart:
        width = width*0.8
        xfontsize = xfontsize*0.8
        init_margin_offset_l += 10
    margin_offset_l = (init_margin_offset_l + y_title_offset 
                       - DOJO_YTITLE_OFFSET_0)
    """
    For each series, set colour details.
    For the collection of series as a whole, set the highlight mapping from 
        each series colour.
    From dojox.charting.action2d.Highlight but with extraneous % removed
    """
    (unused, grid_bg, axis_lbl_font_colour, major_gridline_colour, 
     gridline_width, unused, tooltip_border_colour, 
     colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
    # Can't have white for line charts because always a white outer background
    axis_lbl_font_colour = (axis_lbl_font_colour
                            if axis_lbl_font_colour != u"white" else u"black")
    #unused = setup_highlights(colour_mappings, single_colour=False, 
    #                                override_first_highlight=True)
    try:
        stroke = colour_mappings[0][0]
        fill = colour_mappings[0][1]
    except IndexError:
        stroke = mg.DOJO_COLOURS[0]
    # loop through charts
    for chart_idx, chart_det in enumerate(chart_dets):
        indiv_title, indiv_title_html = get_indiv_title(multichart, chart_det)
        # only one series per chart by design
        series_det = chart_det[mg.CHARTS_SERIES_DETS][0]
        xaxis_dets = series_det[mg.CHARTS_XAXIS_DETS]
        lbl_dets = get_lbl_dets(xaxis_dets)
        xaxis_lbls = u"[" + u",\n            ".join(lbl_dets) + u"]"
        pagebreak = u"" if chart_idx % 2 == 0 else u"page-break-after: always;"
        series_js_list = []
        series_names_list = []
        series_names_list.append(u"series0")
        series_js_list.append(u"var series0 = new Array();")
        series_js_list.append(u"series0[\"seriesLabel\"] = \"%s\";"
                                   % series_det[mg.CHARTS_SERIES_LBL_IN_LEGEND])
        series_js_list.append(u"series0[\"yVals\"] = %s;" % 
                                            series_det[mg.CHARTS_SERIES_Y_VALS])
        tooltips = (u"['" + "', '".join(series_det[mg.CHARTS_SERIES_TOOLTIPS]) 
                    + u"']")
        series_js_list.append(u"series0[\"options\"] = "
            u"{stroke: {color: \"%s\", width: \"6px\"}, fill: \"%s\", "
            u"yLbls: %s};" % (stroke, fill, tooltips))
        series_js_list.append(u"")
        series_js = u"\n    ".join(series_js_list)
        series_js += (u"\n    var series = new Array(%s);" %
                      u", ".join(series_names_list))
        series_js = series_js.lstrip()
        html.append(u"""
<script type="text/javascript">
makechartRenumber%(chart_idx)s = function(){
    %(series_js)s
    var chartconf = new Array();
    chartconf["xaxisLabels"] = %(xaxis_lbls)s;
    chartconf["xfontsize"] = %(xfontsize)s;
    chartconf["gridlineWidth"] = %(gridline_width)s;
    chartconf["gridBg"] = "%(grid_bg)s";
    chartconf["minorTicks"] = %(minor_ticks)s;
    chartconf["microTicks"] = %(micro_ticks)s;
    chartconf["yTitleOffset"] = %(y_title_offset)s;
    chartconf["marginOffsetL"] = %(margin_offset_l)s;
    chartconf["axisLabelDrop"] = %(axis_lbl_drop)s;
    chartconf["axisLabelRotate"] = %(axis_lbl_rotate)s;
    chartconf["axisLabelFontColour"] = "%(axis_lbl_font_colour)s";
    chartconf["majorGridlineColour"] = "%(major_gridline_colour)s";
    chartconf["xTitle"] = "%(x_title)s";
    chartconf["yTitle"] = "%(y_title)s";
    chartconf["ymax"] = %(ymax)s;
    chartconf["tooltipBorderColour"] = "%(tooltip_border_colour)s";
    chartconf["connectorStyle"] = "%(connector_style)s";
    makeAreaChart("mychartRenumber%(chart_idx)s", series, chartconf);
}
</script>

<div style="float: left; margin-right: 10px; %(pagebreak)s">
%(indiv_title_html)s
<div id="mychartRenumber%(chart_idx)s" 
    style="width: %(width)spx; height: %(height)spx; %(pagebreak)s">
    </div>
</div>""" % {u"series_js": series_js, u"xaxis_lbls": xaxis_lbls, 
             u"indiv_title_html": indiv_title_html,
             u"width": width, u"height": height, u"xfontsize": xfontsize, 
             u"axis_lbl_font_colour": axis_lbl_font_colour,
             u"major_gridline_colour": major_gridline_colour,
             u"y_title_offset": y_title_offset,
             u"margin_offset_l": margin_offset_l,
             u"axis_lbl_drop": axis_lbl_drop,
             u"axis_lbl_rotate": axis_lbl_rotate, u"ymax": ymax,
             u"gridline_width": gridline_width, u"x_title": x_title, 
             u"y_title": y_title, u"pagebreak": pagebreak,
             u"tooltip_border_colour": tooltip_border_colour,
             u"connector_style": connector_style, 
             u"grid_bg": grid_bg, u"chart_idx": u"%02d" % chart_idx,
             u"minor_ticks": minor_ticks, u"micro_ticks": micro_ticks})
        overall_title = chart_output_dets[mg.CHARTS_OVERALL_TITLE]
        charts_append_divider(html, titles, overall_title, indiv_title, 
                              u"Area Chart")
    if debug: 
        print(u"y_title_offset: %s, margin_offset_l: %s" % (y_title_offset, 
                                                            margin_offset_l))
    html.append(u"""<div style="clear: both;">&nbsp;&nbsp;</div>""")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)

def histogram_output(titles, subtitles, var_lbl, overall_title, chart_dets, 
                     inc_normal, show_borders, css_fil, css_idx, 
                     page_break_after=False):
    """
    See http://trac.dojotoolkit.org/ticket/7926 - he had trouble doing this then
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    minval -- minimum values for x axis
    maxval -- maximum value for x axis
    xaxis_dets -- [(1, u""), (2, u""), ...] - 1-based idx
    y_vals -- list of values e.g. [12, 30, 100.5, -1, 40]
    bin_lbls -- [u"1 to under 2", u"2 to under 3", ...] for tooltips
    css_idx -- css index so can apply    
    """
    debug = False
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    multichart = (len(chart_dets) > 1)
    html = []
    title_dets_html = output.get_title_dets_html(titles, subtitles, css_idx)
    html.append(title_dets_html)
    height = 300 if multichart else 350
    (outer_bg, grid_bg, axis_lbl_font_colour, major_gridline_colour, 
            gridline_width, stroke_width, tooltip_border_colour, 
            colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
    outer_bg = (u"" if outer_bg == u""
                else u"chartconf[\"outerBg\"] = \"%s\";" % outer_bg)
    single_colour = True
    override_first_highlight = (css_fil == mg.DEFAULT_CSS_PATH 
                                and single_colour)
    colour_cases = setup_highlights(colour_mappings, single_colour, 
                                    override_first_highlight)
    item_colours = output.colour_mappings_to_item_colours(colour_mappings)
    fill = item_colours[0]
    js_inc_normal = u"true" if inc_normal else u"false"
    
    init_margin_offset_l = 25
    yvals = []
    for chart_det in chart_dets:
        yvals.extend(chart_det[mg.CHARTS_SERIES_Y_VALS])
    xaxis_dets = chart_dets[0][mg.CHARTS_XAXIS_DETS]   
    idx_1st_xdets = 0
    idx_xlbl = 1
    x_lbl_len = len(xaxis_dets[idx_1st_xdets][idx_xlbl])
    ymax = max(yvals)
    max_y_lbl_len = len(str(round(ymax,0)))
    max_safe_x_lbl_len_pxls = 180
    y_title_offset = get_ytitle_offset(max_y_lbl_len, x_lbl_len, 
                                       max_safe_x_lbl_len_pxls, rotate=False)    
    margin_offset_l = (init_margin_offset_l + y_title_offset 
                       - DOJO_YTITLE_OFFSET_0)
    normal_stroke_width = 2*stroke_width # normal stroke needed even if border strokes not
    stroke_width = stroke_width if show_borders else 0
    for chart_idx, chart_det in enumerate(chart_dets):
        minval = chart_det[mg.CHART_MINVAL]
        maxval = chart_det[mg.CHART_MAXVAL]
        xaxis_dets = chart_det[mg.CHARTS_XAXIS_DETS]
        y_vals = chart_det[mg.CHARTS_SERIES_Y_VALS]
        norm_ys = chart_det[mg.CHART_NORMAL_Y_VALS]
        bin_lbls = chart_det[mg.CHART_BIN_LBLS]
        pagebreak = u"" if chart_idx % 2 == 0 else u"page-break-after: always;"
        indiv_title, indiv_title_html = get_indiv_title(multichart, chart_det)
        idx_lbls = [u"{value: %s, text: \"%s\"}" % x for x in xaxis_dets]
        xaxis_lbls = (u"[" + u",\n            ".join(idx_lbls) + u"]")
        bin_labs = u"\"" + u"\", \"".join(bin_lbls) + u"\""
        n_bins = len(xaxis_dets)
        width = get_histo_sizings(var_lbl, n_bins, minval, maxval)
        xfontsize = 10 if len(xaxis_dets) <= 20 else 8
        if multichart:
            width = width*0.9 # vulnerable to x axis labels vanishing on minor ticks
            xfontsize = xfontsize*0.8
        html.append(u"""
<script type="text/javascript">

var sofaHlRenumber%(chart_idx)s = function(colour){
    var hlColour;
    switch (colour.toHex()){
        %(colour_cases)s
        default:
            hlColour = hl(colour.toHex());
            break;
    }
    return new dojox.color.Color(hlColour);
}    

makechartRenumber%(chart_idx)s = function(){
    var datadets = new Array();
    datadets["seriesLabel"] = "%(var_lbl)s";
    datadets["yVals"] = %(y_vals)s;
    datadets["normYs"] = %(norm_ys)s;
    datadets["binLabels"] = [%(bin_lbls)s];
    datadets["style"] = {stroke: {color: "white", 
        width: "%(stroke_width)spx"}, fill: "%(fill)s"};
    datadets["normStyle"] = {plot: "normal", 
        stroke: {color: "%(major_gridline_colour)s", 
        width: "%(normal_stroke_width)spx"}, fill: "%(fill)s"};
    
    var chartconf = new Array();
    chartconf["xaxisLabels"] = %(xaxis_lbls)s;
    chartconf["xfontsize"] = %(xfontsize)s;
    chartconf["sofaHl"] = sofaHlRenumber%(chart_idx)s;
    chartconf["tickColour"] = "%(tick_colour)s";
    chartconf["gridlineWidth"] = %(gridline_width)s;
    chartconf["gridBg"] = "%(grid_bg)s";
    chartconf["minorTicks"] = %(minor_ticks)s;
    chartconf["yTitleOffset"] = %(y_title_offset)s;
    chartconf["marginOffsetL"] = %(margin_offset_l)s;
    chartconf["axisLabelFontColour"] = "%(axis_lbl_font_colour)s";
    chartconf["majorGridlineColour"] = "%(major_gridline_colour)s";
    chartconf["yTitle"] = "%(y_title)s";
    chartconf["tooltipBorderColour"] = "%(tooltip_border_colour)s";
    chartconf["connectorStyle"] = "%(connector_style)s";
    chartconf["minVal"] = %(minval)s;
    chartconf["maxVal"] = %(maxval)s;
    chartconf["incNormal"] = %(js_inc_normal)s;
    %(outer_bg)s
    makeHistogram("mychartRenumber%(chart_idx)s", datadets, chartconf);
}
</script>

<div class="screen-float-only" style="margin-right: 10px; %(pagebreak)s">
%(indiv_title_html)s
<div id="mychartRenumber%(chart_idx)s" 
        style="width: %(width)spx; height: %(height)spx;">
    </div>
</div>
        """ % {u"indiv_title_html": indiv_title_html,
               u"stroke_width": stroke_width, 
               u"normal_stroke_width": normal_stroke_width, u"fill": fill,
               u"colour_cases": colour_cases,
               u"xaxis_lbls": xaxis_lbls, u"y_vals": u"%s" % y_vals,
               u"bin_lbls": bin_labs, u"minval": minval, u"maxval": maxval,
               u"width": width, u"height": height, u"xfontsize": xfontsize, 
               u"var_lbl": var_lbl,
               u"y_title_offset": y_title_offset,
               u"margin_offset_l": margin_offset_l,
               u"axis_lbl_font_colour": axis_lbl_font_colour,
               u"major_gridline_colour": major_gridline_colour,
               u"gridline_width": gridline_width, 
               u"y_title": mg.Y_AXIS_FREQ_LBL, u"pagebreak": pagebreak,
               u"tooltip_border_colour": tooltip_border_colour,
               u"connector_style": connector_style, u"outer_bg": outer_bg, 
               u"grid_bg": grid_bg, u"chart_idx": u"%02d" % chart_idx,
               u"minor_ticks": u"true",
               u"tick_colour": major_gridline_colour, 
               u"norm_ys": norm_ys, u"js_inc_normal": js_inc_normal})
        charts_append_divider(html, titles, overall_title, indiv_title, 
                              u"Histogram")
    if debug: 
        print(u"y_title_offset: %s, margin_offset_l: %s" % (y_title_offset, 
                                                            margin_offset_l))
    html.append(u"""<div style="clear: both;">&nbsp;&nbsp;</div>""")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)

def use_mpl_scatterplots(scatterplot_dets):
    """
    Don't want Dojo scatterplots with millions of values - the html would become 
        enormous and unwieldy for a start.
    And want one style of scatterplots for all plots in a chart series.
    """
    chart_dets = scatterplot_dets[mg.CHARTS_CHART_DETS]
    chart_data_tups = []
    for chart_det in chart_dets:
        series_dets = chart_det[mg.CHARTS_SERIES_DETS]
        for series_det in series_dets:
            chart_data_tups.extend(series_det[mg.DATA_TUPS])
    use_mpl = len(chart_data_tups) > mg.MAX_POINTS_DOJO_SCATTERPLOT
    return use_mpl
            
def make_mpl_scatterplot(multichart, html, indiv_chart_title, show_borders, 
                         legend, series_dets, series_colours_by_lbl, label_x, 
                         label_y, ymin, ymax, x_vs_y, add_to_report, 
                         report_name, css_fil, pagebreak):
    """
    min and max values are supplied for the y-axis because we want consistency 
        on that between charts. For the x-axis, whatever is best per chart is OK. 
    """
    (grid_bg, dot_colours, 
     line_colour) = output.get_stats_chart_colours(css_fil)
    if multichart:
        width_inches, height_inches = (6.0, 3.4)
    else:
        width_inches, height_inches = (7.5, 4.1)
    title_dets_html = u"" # handled prior to this step
    html.append(u"""<div class=screen-float-only style="margin-right: 10px; 
        margin-top: 0; %(pagebreak)s">""" % {u"pagebreak": pagebreak})
    html.append(indiv_chart_title)
    all_x = []
    for series_det in series_dets:
        all_x.extend(series_det[mg.LIST_X])
    xmin, xmax = get_optimal_min_max(min(all_x), max(all_x))
    charting_pylab.add_scatterplot(grid_bg, show_borders, line_colour, 
                            series_dets, label_x, label_y, x_vs_y, 
                            title_dets_html, add_to_report, report_name, html, 
                            width_inches, height_inches, xmin=xmin, xmax=xmax, 
                            ymin=ymin, ymax=ymax, dot_colour=dot_colours[0], 
                            series_colours_by_lbl=series_colours_by_lbl)
    html.append(u"</div>")

def get_optimal_min_max(axismin, axismax):
    """
    axismin -- the minimum y value exactly
    axismax -- the maximum y value exactly
    Generally, we want box plots to have y-axes starting from just below the 
        minimum point (e.g. lowest outlier). That is avoid the common case where 
        we have the y-axis start at 0, and all our values range tightly 
        together. In which case we will have a series of tiny boxplots up the 
        top and we won't be able to see the different parts of it e.g. LQ, 
        median etc.
    But sometimes the lowest point is not that far above 0, in which case we 
        should set it to 0. A 0-based axis is preferable unless the values are a 
        long way away. Going from 0.5-12 is silly. Might as well go from 0-12.
    3 scenarios:
    
    1) min and max are both +ve
    |   *
    |
    -------
    Snap min to 0 if gap small rel to range, otherwise make min y-axis just 
    below min point. Make max y-axis just above the max point. Make the 
    padding from 0 the lesser of 0.1 of axismin and 0.1 of valrange. The 
    outer padding can be the lesser of the axismax and 0.1 of valrange.
    
    2) min and max are -ve
    -------
    |   *
    |
    Snap max to 0 if gap small rel to range, otherwise make max y-axis just 
    above max point. Make min y-axis just below min point. Make the 
    padding the lesser of 0.1 of gap and 0.1 of valrange.
    
    3) min is -ve and max is +ve
    |   *
    -------
    |   *
    Make max 1.1*axismax. No harm if 0.
    Make min 1.1*axismin. No harm if 0.
    """
    debug = False
    if debug: print("Orig min max: %s %s" % (axismin, axismax))
    if axismin >= 0 and axismax >= 0: # both +ve
        """
        Snap min to 0 if gap small rel to range, otherwise make min y-axis just 
        below min point. Make max y-axis just above the max point. Make the 
        padding from 0 the lesser of 0.1 of axismin and 0.1 of valrange. The 
        outer padding can be the lesser of the axismax and 0.1 of valrange.
        """
        gap = axismin
        valrange = (axismax - axismin)
        try:
            gap2range = gap/(valrange*1.0)
            if gap2range < 0.6: # close enough to snap to 0
                axismin = 0
            else: # can't just be 0.9 min - e.g. looking at years from 2000-2010 would be 1800 upwards!
                axismin -= min(0.1*gap, 0.1*valrange) # gap is never 0 and is at least 0.6 of valrange
        except ZeroDivisionError:
            pass
        axismax += min(0.1*axismax, 0.1*valrange)
    elif axismin <= 0 and axismax <= 0: # both -ve
        """
        Snap max to 0 if gap small rel to range, otherwise make max y-axis just 
        above max point. Make min y-axis just below min point. Make the 
        padding the lesser of 0.1 of gap and 0.1 of valrange.
        """
        gap = abs(axismax)
        valrange = abs(axismax - axismin)
        try:
            gap2range = gap/(valrange*1.0)
            if gap2range < 0.6:
                axismax = 0
            else:
                axismax += min(0.1*gap, 0.1*valrange)
        except ZeroDivisionError:
            pass
        axismin -= min(0.1*axismin, 0.1*valrange)
    elif axismin <=0 and axismax >=0: # spanning y-axis (even if all 0s ;-))
        """
        Pad max with 0.1*axismax. No harm if 0.
        Pad min with 0.1*axismin. No harm if 0.
        """
        axismax = 1.1*axismax
        axismin = 1.1*axismin
    else:
        pass
    if debug: print("Final axismin: %s; Final axismax %s" % (axismin, axismax))
    return axismin, axismax

def make_dojo_scatterplot(chart_idx, multichart, html, indiv_chart_title, 
                          show_borders, legend, series_dets, 
                          series_colours_by_lbl, label_x, label_y, ymin, ymax, 
                          css_fil, pagebreak):
    """
    min and max values are supplied for the y-axis because we want consistency 
        on that between charts. For the x-axis, whatever is best per chart is OK. 
    series_dets = {mg.CHARTS_SERIES_LBL_IN_LEGEND: u"Italy", # or None if only one series
                   mg.LIST_X: [1,1,2,2,2,3,4,6,8,18, ...], 
                   mg.LIST_Y: [3,5,4,5,6,7,9,12,17,6, ...], 
                   mg.DATA_TUPS: [(1,3),(1,5), ...]}
    """
    debug = False
    if multichart:
        width, height = (630, 350)
    else:
        width, height = (700, 385)   
    xfontsize = 10
    all_x = []
    for series_det in series_dets:
        all_x.extend(series_det[mg.LIST_X])
    xmin, xmax = get_optimal_min_max(min(all_x), max(all_x))
    init_margin_offset_l = 20
    max_y_lbl_len = len(str(round(ymax,0)))
    x_lbl_len = len(str(round(xmin,0)))
    max_safe_x_lbl_len_pxls = 90
    y_title_offset = get_ytitle_offset(max_y_lbl_len, x_lbl_len, 
                                       max_safe_x_lbl_len_pxls, rotate=False) 
    margin_offset_l = (init_margin_offset_l + y_title_offset 
                       - DOJO_YTITLE_OFFSET_0)
    x_title = label_x
    axis_lbl_drop = 10
    y_title = label_y
    if debug: print(label_x, xmin, xmax, label_y, ymin, ymax)
    series_js_list = []
    series_names_list = []
    for series_idx, series_det in enumerate(series_dets):
        series_lbl = series_det[mg.CHARTS_SERIES_LBL_IN_LEGEND]
        series_names_list.append(u"series%s" % series_idx)
        series_js_list.append(u"var series%s = new Array();" % series_idx)
        series_js_list.append(u"series%s[\"seriesLabel\"] = \"%s\";"
                 % (series_idx, series_lbl))
        jsdata = []
        x_set = set()
        for x, y in series_det[mg.DATA_TUPS]:
            jsdata.append("{x: %s, y: %s}" % (x, y))
            x_set.add(x)
        few_unique_x_vals = (len(x_set) < 10)
        minor_ticks = u"false" if few_unique_x_vals else u"true"
        xy_pairs = "[" + ",\n".join(jsdata) + "]"
        series_js_list.append(u"series%s[\"xyPairs\"] = %s;" % (series_idx, 
                                                                xy_pairs))
        (outer_bg, grid_bg, axis_lbl_font_colour, major_gridline_colour, 
         gridline_width, stroke_width, tooltip_border_colour, 
         colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
        # Can't have white for scatterplots because always a white outer background
        axis_lbl_font_colour = (axis_lbl_font_colour
                              if axis_lbl_font_colour != u"white" else u"black")
        stroke_width = stroke_width if show_borders else 0
        outer_bg = (u"" if outer_bg == u""
                    else u"chartconf[\"outerBg\"] = \"%s\";" % outer_bg)
        single_colour = True
        override_first_highlight = (css_fil == mg.DEFAULT_CSS_PATH 
                                    and single_colour)
        colour_cases = setup_highlights(colour_mappings, single_colour, 
                                        override_first_highlight)
        fill = series_colours_by_lbl[series_lbl]
        series_js_list.append(u"series%(series_idx)s[\"style\"] = "
                u"{stroke: {color: \"white\","
                u"width: \"%(stroke_width)spx\"}, fill: \"%(fill)s\","
                u"marker: \"m-6,0 c0,-8 12,-8 12,0 m-12,0 c0,8 12,8 12,0\"};" % 
                    {u"series_idx": series_idx, u"stroke_width": stroke_width,
                     u"fill": fill})
        series_js_list.append(u"")
        series_js = u"\n    ".join(series_js_list)
        series_js += (u"\n    var series = new Array(%s);" %
                      u", ".join(series_names_list))
        series_js = series_js.lstrip()
    
    
    
    # marker - http://o.dojotoolkit.org/forum/dojox-dojox/dojox-support/...
    # ...newbie-need-svg-path-segment-string
    html.append(u"""
<script type="text/javascript">

var sofaHlRenumber%(chart_idx)s = function(colour){
    var hlColour;
    switch (colour.toHex()){
        %(colour_cases)s
        default:
            hlColour = hl(colour.toHex());
            break;
    }
    return new dojox.color.Color(hlColour);
}    

makechartRenumber%(chart_idx)s = function(){
    %(series_js)s
    var chartconf = new Array();
    chartconf["xmin"] = %(xmin)s;
    chartconf["ymin"] = %(ymin)s;
    chartconf["xmax"] = %(xmax)s;
    chartconf["ymax"] = %(ymax)s;
    chartconf["xfontsize"] = %(xfontsize)s;
    chartconf["sofaHl"] = sofaHlRenumber%(chart_idx)s;
    chartconf["tickColour"] = "%(tick_colour)s";
    chartconf["gridlineWidth"] = %(gridline_width)s;
    chartconf["gridBg"] = \"%(grid_bg)s\";
    chartconf["minorTicks"] = %(minor_ticks)s;
    chartconf["yTitleOffset"] = %(y_title_offset)s;
    chartconf["marginOffsetL"] = %(margin_offset_l)s;
    chartconf["axisLabelFontColour"] = "%(axis_lbl_font_colour)s";
    chartconf["majorGridlineColour"] = "%(major_gridline_colour)s";
    chartconf["xTitle"] = "%(x_title)s";
    chartconf["axisLabelDrop"] = %(axis_lbl_drop)s;
    chartconf["yTitle"] = "%(y_title)s";
    chartconf["ymax"] = %(ymax)s;
    chartconf["tooltipBorderColour"] = "%(tooltip_border_colour)s";
    chartconf["connectorStyle"] = "%(connector_style)s";
    %(outer_bg)s
    makeScatterplot("mychartRenumber%(chart_idx)s", series, chartconf);
}
</script>

<div class="screen-float-only" style="margin-right: 10px; %(pagebreak)s">
%(indiv_chart_title)s
<div id="mychartRenumber%(chart_idx)s" 
        style="width: %(width)spx; height: %(height)spx;">
    </div>
%(legend)s
</div>      
""" % {u"legend": legend, u"series_js": series_js,
       u"indiv_chart_title": indiv_chart_title, u"xy_pairs": xy_pairs,
       u"xmin": xmin, u"ymin": ymin, u"xmax": xmax, u"ymax": ymax,
       u"x_title": x_title, u"y_title": y_title,
       u"stroke_width": stroke_width, u"fill": fill,
       u"colour_cases": colour_cases, 
       u"width": width, u"height": height, u"xfontsize": xfontsize, 
       u"pagebreak": pagebreak,
       u"axis_lbl_font_colour": axis_lbl_font_colour,
       u"major_gridline_colour": major_gridline_colour,
       u"y_title_offset": y_title_offset,
       u"margin_offset_l": margin_offset_l,
       u"gridline_width": gridline_width, 
       u"axis_lbl_drop": axis_lbl_drop,
       u"tooltip_border_colour": tooltip_border_colour,
       u"connector_style": connector_style, u"outer_bg": outer_bg, 
       u"grid_bg": grid_bg, u"chart_idx": u"%02d" % chart_idx, 
       u"minor_ticks": minor_ticks, u"tick_colour": major_gridline_colour})
    if debug: 
        print(u"y_title_offset: %s, margin_offset_l: %s" % (y_title_offset, 
                                                            margin_offset_l))

def get_scatterplot_ymin_ymax(scatterplot_dets):
    all_y_vals = []
    chart_dets = scatterplot_dets[mg.CHARTS_CHART_DETS]
    for chart_det in chart_dets:
        series_dets = chart_det[mg.CHARTS_SERIES_DETS]
        for series_det in series_dets:
            all_y_vals += series_det[mg.LIST_Y]
    ymin, ymax = get_optimal_min_max(min(all_y_vals), max(all_y_vals))
    return ymin, ymax

def scatterplot_output(titles, subtitles, overall_title, scatterplot_dets, 
                       label_x, label_y, add_to_report, report_name, 
                       show_borders, css_fil, css_idx, page_break_after=False):
    """
    scatterplot_dets = {mg.CHARTS_OVERALL_LEGEND_LBL: u"Age Group", # or None if only one series
                        mg.CHARTS_CHART_DETS: chart_dets}
    chart_dets = [
        {mg.CHARTS_CHART_LBL: u"Gender: Male", # or None if only one chart
         mg.CHARTS_SERIES_DETS: series_dets},
        {mg.CHARTS_CHART_LBL: u"Gender: Female",
         mg.CHARTS_SERIES_DETS: series_dets}, ...
    ]
    series_dets = {mg.CHARTS_SERIES_LBL_IN_LEGEND: u"Italy", # or None if only one series
                   mg.LIST_X: [1,1,2,2,2,3,4,6,8,18, ...], 
                   mg.LIST_Y: [3,5,4,5,6,7,9,12,17,6, ...], 
                   mg.DATA_TUPS: [(1,3),(1,5), ...]}
    """
    debug = False
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    pagebreak = u"page-break-after: always;"
    title_dets_html = output.get_title_dets_html(titles, subtitles, css_idx)
    x_vs_y = '"%s"' % label_x + _(u" vs ") + '"%s"' % label_y
    chart_dets = scatterplot_dets[mg.CHARTS_CHART_DETS]
    chart0_series_dets = chart_dets[0][mg.CHARTS_SERIES_DETS]
    multiseries = len(chart0_series_dets) > 1
    html = []
    html.append(title_dets_html)
    multichart = (len(scatterplot_dets[mg.CHARTS_CHART_DETS]) > 1)
    use_mpl = use_mpl_scatterplots(scatterplot_dets)
    ymin, ymax = get_scatterplot_ymin_ymax(scatterplot_dets) # unlike x-axis we require this to be consistent across charts
    legend_lbl = scatterplot_dets[mg.CHARTS_OVERALL_LEGEND_LBL]
    series_colours_by_lbl = get_series_colours_by_lbl(scatterplot_dets, css_fil)
    # loop through charts
    for chart_idx, chart_det in enumerate(chart_dets):
        series_dets = chart_det[mg.CHARTS_SERIES_DETS]
        pagebreak = u"" if chart_idx % 2 == 0 else u"page-break-after: always;"
        if debug: print(series_dets)
        if multiseries:
            legend = u"""
        <p style="float: left; font-weight: bold; margin-right: 12px; 
                margin-top: 9px;">
            %s:
        </p>
        <div id="legendMychartRenumber%02d">
            </div>""" % (legend_lbl, chart_idx)
        else:
            legend = u"" 
        indiv_title, indiv_title_html = get_indiv_title(multichart, chart_det)
        if use_mpl:
            make_mpl_scatterplot(multichart, html, indiv_title_html, 
                                 show_borders, legend, series_dets, 
                                 series_colours_by_lbl, label_x, label_y, ymin, 
                                 ymax, x_vs_y, add_to_report, report_name, 
                                 css_fil, pagebreak)
        else:
            make_dojo_scatterplot(chart_idx, multichart, html, 
                                  indiv_title_html, show_borders, legend, 
                                  series_dets, series_colours_by_lbl, label_x, 
                                  label_y, ymin, ymax, css_fil, pagebreak)
        charts_append_divider(html, titles, overall_title, indiv_title, 
                              u"Scatterplot")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)

def boxplot_output(titles, subtitles, any_missing_boxes, x_title, y_title, 
                   var_role_series_name, xaxis_dets, max_x_lbl_len, 
                   max_lbl_lines, overall_title, chart_dets, xmin, xmax, ymin, 
                   ymax, rotate, css_fil, css_idx, page_break_after):
    """
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    xaxis_dets -- [(0, "", ""), (1, "Under 20", ...] NB blanks either end
    boxplot_dets -- [{mg.CHART_SERIES_LBL: "Girls", 
        mg.CHART_BOXDETS: [{mg.CHART_BOXPLOT_DISPLAY: True, 
                                mg.CHART_BOXPLOT_LWHISKER: 1.7, 
                                mg.CHART_BOXPLOT_LBOX: 3.2, ...}, 
                           {mg.CHART_BOXPLOT_DISPLAY: True, etc}, 
                                    ...]},
                          ...]
    NB supply a boxdet even for an empty box. Put marker that it should be 
        skipped in terms of output to js. mg.CHART_BOXPLOT_DISPLAY
    # list of subseries dicts each of which has a label and a list of dicts 
        (one per box).
    css_idx -- css index so can apply
    """
    debug = False
    axis_lbl_rotate = -90 if rotate else 0
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    title_dets_html = output.get_title_dets_html(titles, subtitles, css_idx)
    lbl_dets = get_lbl_dets(xaxis_dets)
    lbl_dets.insert(0, u"""{value: 0, text: ""}""")
    lbl_dets.append(u"""{value: %s, text: ""}""" % len(lbl_dets))
    xaxis_lbls = u"[" + u",\n            ".join(lbl_dets) + u"]"
    multichart = False # currently by design
    axis_lbl_drop = get_axis_lbl_drop(multichart, rotate, max_lbl_lines)
    height = 350
    if rotate:
        height += AVG_CHAR_WIDTH_PXLS*max_x_lbl_len 
    height += axis_lbl_drop
    max_lbl_width = TXT_WIDTH_WHEN_ROTATED if rotate else max_x_lbl_len
    (width, xfontsize,
        minor_ticks) = get_boxplot_sizings(x_title, xaxis_dets, max_lbl_width, 
                                           chart_dets)
    yfontsize = xfontsize
    if width > 1200:
        init_margin_offset_l = 25
    elif len(xaxis_dets) == 1:
        init_margin_offset_l = 35
    else:
        init_margin_offset_l = 25 # gets squeezed
    idx_1st_xdets = 0
    idx_xlbl = 1
    x_lbl_len = len(xaxis_dets[idx_1st_xdets][idx_xlbl])
    max_y_lbl_len = len(str(round(ymax,0)))
    max_safe_x_lbl_len_pxls = 180
    y_title_offset = get_ytitle_offset(max_y_lbl_len, x_lbl_len, 
                                       max_safe_x_lbl_len_pxls, rotate) 
    margin_offset_l = (init_margin_offset_l + y_title_offset 
                       - DOJO_YTITLE_OFFSET_0)  
    if rotate:
        margin_offset_l += 10  
    html = []
    if any_missing_boxes:
        html.append(u"<p>At least one box will not be displayed because it "
                    u"needed more than %s values or has inadequate "
                    u"variability.</p>" % mg.MIN_DISPLAY_VALS_FOR_BOXPLOT)
    """
    For each series, set colour details.
    For the collection of series as a whole, set the highlight mapping from 
        each series colour.
    From dojox.charting.action2d.Highlight but with extraneous % removed
    """
    (unused, grid_bg, axis_lbl_font_colour, major_gridline_colour, 
            gridline_width, unused, tooltip_border_colour, 
            colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
    # Can't have white for boxplots because always a white outer background
    outer_bg = u"white"
    axis_lbl_font_colour = (axis_lbl_font_colour
                            if axis_lbl_font_colour != u"white" else u"black")
    """
    Build js for every series.
    colour_mappings - take first of each pair to use as outline of box plots, 
        and use getfainthex() to get lighter colour for interior (so we can see
        the details of the median line) and an even lighter version for the 
        highlight. The css-defined highlight is good for bar charts etc where
        change is the key, not visibility of interior details.
    """
    if debug:
        print(chart_dets)
    pagebreak = u"page-break-after: always;"
    n_series = len(chart_dets)
    n_boxes = len(chart_dets[0][mg.CHART_BOXDETS])
    """
    For each box, we need to identify the centre. For this we need to know 
        the number of boxes, where the first one starts, and the horizontal 
        jump rightwards for each one (= the gap which is width + extra 
        breathing space).
    """
    if n_boxes == 0:
        raise Exception("Box count of 0")
    n_gaps = n_series - 1
    shrinkage = n_series*0.6
    gap = 0.4/shrinkage
    pre_series = []
    bar_width = mg.CHART_BOXPLOT_WIDTH/shrinkage
    pre_series.append(u"    var width = %s;" % bar_width)
    pre_series.append(u"    var seriesconf = new Array();")
    pre_series.append(u"    var seriesdummy = [];")
    pre_series_str = "\n".join(pre_series)
    
    offset_start = -((gap*n_gaps)/2.0) # if 1 box, offset = 0 i.e. middle
    offsets = [offset_start + (x*gap) for x in range(n_series)]
    series_js = []
    if var_role_series_name:
        legend = u"""
    <p style="float: left; font-weight: bold; margin-right: 12px; 
            margin-top: 9px;">
        %s:
    </p>
    <div id="legendMychartRenumber00">
        </div>""" % var_role_series_name
    else:
        legend = u"" 
    for series_idx, series_det in enumerate(chart_dets):
        """
        series_det -- [((lwhisker, lbox, median, ubox, uwhisker, outliers), 
                (lwhisker etc), ...),
               ...] # list of subseries tuples each of which has a tuple 
                      per box.
        We flatten out the series and do it across and back across for 
            each sub series.
        """
        series_js.append(u"    // series%s" % series_idx)
        try:
            stroke = colour_mappings[series_idx][0]
        except IndexError:
            stroke = mg.DOJO_COLOURS[series_idx]
        series_js.append(u"    var strokecol%s = \"%s\";" % (series_idx, 
                                                             stroke))
        series_js.append(u"    var fillcol%s = getfainthex(strokecol%s);" 
                         % (series_idx, series_idx))
        series_js.append(u"    seriesconf[%(series_idx)s] = {seriesLabel: "
             u"\"%(series_lbl)s\", "
             u"seriesStyle: {stroke: {color: strokecol%(series_idx)s, "
             u"width: \"1px\"}, fill: fillcol%(series_idx)s}};"
             % {u"series_idx": series_idx, 
                u"series_lbl": series_det[mg.CHART_SERIES_LBL]})
        series_js.append(u"    var series%(series_idx)s = [" 
                      % {u"series_idx": series_idx})
        offset = offsets[series_idx]
        box_js = [] 
        for boxdet_idx, boxdet in enumerate(series_det[mg.CHART_BOXDETS]):
            if not boxdet[mg.CHART_BOXPLOT_DISPLAY]:
                continue
            unique_name = u"%s%s" % (series_idx, boxdet_idx)
            box_js.append(u"""        {seriesLabel: "dummylabel%(unique_name)s", 
        boxDets: {stroke: strokecol%(series_idx)s, fill: fillcol%(series_idx)s, 
                  center: %(boxdets_idx)s + 1 + %(offset)s, width: width,
                  summary_data: {%(lwhisker)s: %(lwhisker_val)s, 
                                 %(lbox)s: %(lbox_val)s,  
                                 %(median)s: %(median_val)s, 
                                 %(ubox)s: %(ubox_val)s, 
                                 %(uwhisker)s: %(uwhisker_val)s, 
                                 %(outliers)s: %(outliers_val)s}
                 }
              }""" % {u"unique_name": unique_name, u"series_idx": series_idx,
                        u"boxdets_idx": boxdet_idx, u"offset": offset,
                        u"lwhisker": mg.CHART_BOXPLOT_LWHISKER, 
                        u"lwhisker_val": boxdet[mg.CHART_BOXPLOT_LWHISKER],
                        u"lbox": mg.CHART_BOXPLOT_LBOX, 
                        u"lbox_val": boxdet[mg.CHART_BOXPLOT_LBOX],
                        u"median": mg.CHART_BOXPLOT_MEDIAN, 
                        u"median_val": boxdet[mg.CHART_BOXPLOT_MEDIAN],
                        u"ubox": mg.CHART_BOXPLOT_UBOX, 
                        u"ubox_val": boxdet[mg.CHART_BOXPLOT_UBOX],
                        u"uwhisker": mg.CHART_BOXPLOT_UWHISKER, 
                        u"uwhisker_val": boxdet[mg.CHART_BOXPLOT_UWHISKER],
                        u"outliers": mg.CHART_BOXPLOT_OUTLIERS, 
                        u"outliers_val": boxdet[mg.CHART_BOXPLOT_OUTLIERS],
                        })
        series_js.append(u",\n".join(box_js))            
        series_js.append(u"        ];") # close series list
    series_lst = ["series%s" % x for x in range(len(chart_dets))]
    series_js.append(u"    var series = seriesdummy.concat(%s);" 
                     % ", ".join(series_lst))
    series_js_str = u"\n".join(series_js)
    html.append(u"""
<script type="text/javascript">

makechartRenumber00 = function(){
%(pre_series_str)s
%(series_js_str)s
    var chartconf = new Array();
    chartconf["makefaint"] = makefaint;
    chartconf["tooltipBorderColour"] = "%(tooltip_border_colour)s";
    chartconf["connectorStyle"] = "%(connector_style)s";
    chartconf["outerBg"] = "%(outer_bg)s";
    chartconf["gridBg"] = "%(grid_bg)s";
    chartconf["axisColour"] = "black";
    chartconf["axisLabelFontColour"] = "%(axis_lbl_font_colour)s";
    chartconf["innerChartBorderColour"] = "white";
    chartconf["outerChartBorderColour"] = "white";
    chartconf["majorGridlineColour"] = "%(major_gridline_colour)s";
    chartconf["tickColour"] = "black";
    chartconf["minorTicks"] = %(minor_ticks)s;
    chartconf["gridlineWidth"] = %(gridline_width)s;
    chartconf["xfontsize"] = %(xfontsize)s;
    chartconf["yfontsize"] = %(yfontsize)s;
    chartconf["xTitle"] = "%(x_title)s";
    chartconf["yTitle"] = "%(y_title)s";
    chartconf["xaxisLabels"] = %(xaxis_lbls)s;
    chartconf["axisLabelDrop"] = %(axis_lbl_drop)s;
    chartconf["axisLabelRotate"] = %(axis_lbl_rotate)s;
    chartconf["yTitleOffset"] = %(y_title_offset)s;
    chartconf["marginOffsetL"] = %(margin_offset_l)s;
    chartconf["xmin"] = %(xmin)s;
    chartconf["xmax"] = %(xmax)s;
    chartconf["ymin"] = %(ymin)s;
    chartconf["ymax"] = %(ymax)s;
    makeBoxAndWhisker("mychartRenumber00", series, seriesconf, chartconf);
}
</script>
%(titles)s
    
<div class="screen-float-only" style="margin-right: 10px; %(pagebreak)s">

<div id="mychartRenumber00" style="width: %(width)spx; 
        height: %(height)spx;">
    </div>
<div id="dummychartRenumber00" 
    style="float: right; width: 100px; height: 100px; visibility: hidden;">
    <!--needs width and height for IE 6 so must float to keep out of way-->
    </div>
%(legend)s
</div>
    """ % {u"titles": title_dets_html, u"legend": legend, 
           u"pre_series_str": pre_series_str,
           u"series_js_str": series_js_str, u"xaxis_lbls": xaxis_lbls, 
           u"width": width, u"height": height, 
           u"xfontsize": xfontsize, u"yfontsize": yfontsize, 
           u"xmin": xmin, u"xmax": xmax, u"ymin": ymin, u"ymax": ymax,
           u"x_title": x_title, u"y_title": y_title,
           u"axis_lbl_font_colour": axis_lbl_font_colour,
           u"major_gridline_colour": major_gridline_colour,
           u"gridline_width": gridline_width, u"pagebreak": pagebreak,
           u"axis_lbl_drop": axis_lbl_drop, u"minor_ticks": minor_ticks,
           u"y_title_offset": y_title_offset,
           u"margin_offset_l": margin_offset_l,
           u"axis_lbl_rotate": axis_lbl_rotate,
           u"tooltip_border_colour": tooltip_border_colour,
           u"connector_style": connector_style, 
           u"outer_bg": outer_bg, u"grid_bg": grid_bg})
    charts_append_divider(html, titles, overall_title, indiv_title=u"", 
                          item_type=u"Boxplot")
    if debug: 
        print(u"y_title_offset: %s, margin_offset_l: %s" % (y_title_offset, 
                                                            margin_offset_l))
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)
    