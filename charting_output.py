#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Use English UK spelling e.g. colour and when writing JS use camelcase.
NB no html headers here - the script generates those beforehand and appends 
    this and then the html footer.
"""

import math
import pprint

import my_globals as mg
import lib
import my_exceptions
import charting_pylab
import core_stats
import getdata
import output

dd = getdata.get_dd()

def get_basic_dets(dbe, cur, tbl, tbl_filt, fld_gp, fld_gp_name, fld_gp_lbls, 
                   fld_measure, fld_measure_lbls, sort_opt):
    """
    Get frequencies for all non-missing values in variable plus labels.
    Return list of dics with CHART_CHART_BY_LABEL, CHART_MEASURE_DETS, 
        CHART_MAX_LABEL_LEN, and CHART_Y_VALS.
    CHART_CHART_BY_LABEL is something like All if no chart by variable.
    """
    debug = False
    objqtr = getdata.get_obj_quoter_func(dbe)
    unused, and_tbl_filt = lib.get_tbl_filts(tbl_filt)
    sql_dic = {u"fld_gp": objqtr(fld_gp), u"fld_measure": objqtr(fld_measure),
               u"and_tbl_filt": and_tbl_filt, u"tbl": objqtr(tbl)}
    if fld_gp:
        SQL_get_vals = (u"""SELECT %(fld_gp)s, %(fld_measure)s, COUNT(*) AS freq
            FROM %(tbl)s
            WHERE %(fld_measure)s IS NOT NULL %(and_tbl_filt)s
            GROUP BY %(fld_gp)s, %(fld_measure)s
            ORDER BY %(fld_gp)s, %(fld_measure)s""") % sql_dic
    else:
        SQL_get_vals = (u"""SELECT %(fld_measure)s, COUNT(*) AS freq
            FROM %(tbl)s
            WHERE %(fld_measure)s IS NOT NULL %(and_tbl_filt)s
            GROUP BY %(fld_measure)s
            ORDER BY %(fld_measure)s""") % sql_dic
    if debug: print(SQL_get_vals)
    cur.execute(SQL_get_vals)
    raw_results = cur.fetchall()
    if not raw_results:
        raise my_exceptions.TooFewValsForDisplay
    all_basic_dets = []
    if fld_gp:
        split_results = get_split_results(fld_gp_name, fld_gp_lbls, raw_results)
    else:
        split_results = [{mg.CHART_CHART_BY_LABEL: mg.CHART_CHART_BY_LABEL_ALL,
                          mg.CHART_VAL_FREQS: raw_results},]
    for indiv_result in split_results:
        indiv_label = indiv_result[mg.CHART_CHART_BY_LABEL]
        indiv_raw_results = indiv_result[mg.CHART_VAL_FREQS]
        indiv_basic_dets = get_indiv_basic_dets(indiv_label, indiv_raw_results, 
                                                fld_measure_lbls, sort_opt)
        all_basic_dets.append(indiv_basic_dets)
    return all_basic_dets

def get_split_results(fld_gp_name, fld_gp_lbls, raw_results):
    """
    e.g.
    fld_gp, fld_measure, freq
    1,1,100
    1,2,56
    2,1,6
    2,2,113
    --->
    []
    return dict for each lot of field groups:
    [{mg.CHART_CHART_BY_LABEL: , 
      mg.CHART_VAL_FREQS: [(fld_measure, freq), ...]}, 
      ...]
    """
    split_raw_results = []
    prev_fld_gp_val = None
    for fld_gp_val, fld_measure, freq in raw_results:
        first_gp = (prev_fld_gp_val == None)
        same_group = (fld_gp_val == prev_fld_gp_val)
        if not same_group:
            if not first_gp: # save prev dic across
                split_raw_results.append(fld_gp_dic)
            fld_gp_val_lbl = fld_gp_lbls.get(fld_gp_val, fld_gp_val)
            chart_by_lbl = u"%s: %s" % (fld_gp_name, fld_gp_val_lbl)
            fld_gp_dic = {}
            fld_gp_dic[mg.CHART_CHART_BY_LABEL] = chart_by_lbl
            val_freqs_lst = [(fld_measure, freq),]
            fld_gp_dic[mg.CHART_VAL_FREQS] = val_freqs_lst
            prev_fld_gp_val = fld_gp_val
        else:
            val_freqs_lst.append((fld_measure, freq))
        if len(split_raw_results) > mg.CHART_MAX_CHARTS_IN_SET:
            raise my_exceptions.TooManyChartsInSeries(fld_gp_name, 
                                           max_items=mg.CHART_MAX_CHARTS_IN_SET)
    # save prev dic across
    split_raw_results.append(fld_gp_dic)
    if len(split_raw_results) > mg.CHART_MAX_CHARTS_IN_SET:
        raise my_exceptions.TooManyChartsInSeries(fld_gp_name, 
                                       max_items=mg.CHART_MAX_CHARTS_IN_SET)
    return split_raw_results

def get_indiv_basic_dets(indiv_label, indiv_raw_results, measure_val_lbls, 
                         sort_opt):
    """
    Returns dict for indiv chart containing: CHART_CHART_BY_LABEL, 
        CHART_MEASURE_DETS, CHART_MAX_LABEL_LEN, CHART_Y_VALS
    """
    val_freq_label_lst = []
    for val, freq in indiv_raw_results:
        freq = int(freq)
        val_label = measure_val_lbls.get(val, unicode(val))
        val_freq_label_lst.append((val, freq, val_label))
    lib.sort_value_labels(sort_opt, val_freq_label_lst)
    measure_dets = []
    max_label_len = 0
    y_vals = []
    for val, freq, val_label in val_freq_label_lst:
        len_y_val = len(val_label)
        if len_y_val > max_label_len:
            max_label_len = len_y_val
        split_label = lib.get_labels_in_lines(orig_txt=val_label, max_width=17)
        measure_dets.append((val, val_label, split_label))
        y_vals.append(freq)
    return {mg.CHART_CHART_BY_LABEL: indiv_label,
            mg.CHART_MEASURE_DETS: measure_dets, 
            mg.CHART_MAX_LABEL_LEN: max_label_len, 
            mg.CHART_Y_VALS: y_vals}

def get_single_val_dets(dbe, cur, tbl, tbl_filt, 
                        fld_gp, fld_gp_name, fld_gp_lbls, 
                        fld_measure, fld_measure_lbls, sort_opt):
    """
    Simple bar charts and single line line charts.
    """
    return get_basic_dets(dbe, cur, tbl, tbl_filt, 
                          fld_gp, fld_gp_name, fld_gp_lbls, 
                          fld_measure, fld_measure_lbls, sort_opt)

def get_grouped_val_dets(chart_type, dbe, cur, tbl, tbl_filt,
                         fld_gp, fld_gp_lbls, fld_measure, fld_measure_lbls):
    """
    e.g. clustered bar charts and multiple line line charts.
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
    debug = False
    MAX_ITEMS = 150 if chart_type == mg.CLUSTERED_BARCHART else 300
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
    if not raw_data:
        raise my_exceptions.TooFewValsForDisplay
    series_data, oth_vals = reshape_sql_crosstab_data(raw_data)
    if len(series_data) > 30:
        raise my_exceptions.TooManySeriesInChart
    series_dets = []
    tot_items = 0
    for gp_val, freqs in series_data.items():
        tot_items += len(freqs)
        if tot_items > MAX_ITEMS:
            raise my_exceptions.TooManyValsInChartSeries(fld_measure, MAX_ITEMS)
        gp_val_label = fld_gp_lbls.get(gp_val, unicode(gp_val))
        series_dic = {u"label": gp_val_label, u"y_vals": freqs}
        series_dets.append(series_dic)
    xaxis_dets = []
    max_label_len = 0
    for val in oth_vals:
        val_label = fld_measure_lbls.get(val, unicode(val))
        len_y_val = len(val_label)
        if len_y_val > max_label_len:
            max_label_len = len_y_val
        split_label = lib.get_labels_in_lines(orig_txt=val_label, max_width=17)
        xaxis_dets.append((val, val_label, split_label))
    if debug: print(xaxis_dets)
    return xaxis_dets, max_label_len, series_dets

def get_pie_chart_dets(dbe, cur, tbl, tbl_filt, 
                       fld_gp, fld_gp_name, fld_gp_lbls, 
                       fld_measure, fld_measure_lbls, sort_opt):
    """
    fld_gp -- chart by each value
    basic_pie_dets -- list of dicts, one for each indiv pie chart.  Each dict 
        contains: CHART_CHART_BY_LABEL, CHART_MEASURE_DETS, CHART_MAX_LABEL_LEN, 
        CHART_Y_VALS.
    """
    debug = False
    pie_chart_dets = []
    basic_pie_dets = get_basic_dets(dbe, cur, tbl, tbl_filt, 
                                    fld_gp, fld_gp_name, fld_gp_lbls, 
                                    fld_measure, fld_measure_lbls, sort_opt)
    for basic_pie_det in basic_pie_dets:
        if debug: print(basic_pie_det)
        indiv_pie_dets = {}
        chart_by_label = basic_pie_det[mg.CHART_CHART_BY_LABEL]
        label_dets = basic_pie_det[mg.CHART_MEASURE_DETS]
        max_label_len = basic_pie_det[mg.CHART_MAX_LABEL_LEN]
        slice_vals = basic_pie_det[mg.CHART_Y_VALS]
        if len(label_dets) != len(slice_vals):
            raise Exception(u"Mismatch in number of slice labels and slice "
                            u"values")
        if len(slice_vals) > 30:
            raise my_exceptions.TooManySlicesInPieChart
        tot_freq = sum(slice_vals)
        slice_dets = []
        for i, slice_val in enumerate(slice_vals):
            slice_dic = {u"y": slice_val, u"text": label_dets[i][2], 
                         u"tooltip": u"%s<br>%s (%s%%)" % 
                         (label_dets[i][1], slice_val, 
                          round((100.0*slice_val)/tot_freq,1))}
            slice_dets.append(slice_dic)
        indiv_pie_dets[mg.CHART_SLICE_DETS] = slice_dets
        indiv_pie_dets[mg.CHART_CHART_BY_LABEL] = chart_by_label
        # add other details later e.g. label for pie chart
        pie_chart_dets.append(indiv_pie_dets)
    return pie_chart_dets

def get_histo_dets(dbe, cur, tbl, tbl_filt, fld_gp, fld_gp_name, fld_gp_lbls, 
                   fld_measure):
    """
    Make separate db call each histogram.  Getting all values anyway and don't 
        want to store in memory.
    Return list of dicts - one for each histogram.  Each contains: 
        CHART_XAXIS_DETS, CHART_Y_VALS, CHART_MINVAL, CHART_MAXVAL, 
        CHART_BIN_LABELS.
    xaxis_dets -- [(1, u""), (2: u"", ...]
    y_vals -- [0.091, ...]
    bin_labels -- [u"1 to under 2", u"2 to under 3", ...]
    """
    debug = False
    objqtr = getdata.get_obj_quoter_func(dbe)
    unused, and_tbl_filt = lib.get_tbl_filts(tbl_filt)
    sql_dic = {u"fld_gp": objqtr(fld_gp), u"fld_measure": objqtr(fld_measure),
               u"and_tbl_filt": and_tbl_filt, u"tbl": objqtr(tbl)}
    if fld_gp:
        SQL_fld_gp_vals = u"""SELECT %(fld_gp)s 
            FROM %(tbl)s 
            WHERE %(fld_measure)s IS NOT NULL %(and_tbl_filt)s 
            GROUP BY %(fld_gp)s""" % sql_dic
        cur.execute(SQL_fld_gp_vals)
        fld_gp_vals = [x[0] for x in cur.fetchall()]
        if len(fld_gp_vals) > mg.CHART_MAX_CHARTS_IN_SET:
            raise my_exceptions.TooManyChartsInSeries(fld_gp_name, 
                                           max_items=mg.CHART_MAX_CHARTS_IN_SET)
    else:
        fld_gp_vals = [None,] # Got to have something to loop through ;-)
    histo_dets = []
    for fld_gp_val in fld_gp_vals:
        if fld_gp:
            filt = getdata.make_fld_val_clause(dbe, dd.flds, fld_name=fld_gp, 
                                               val=fld_gp_val)
            and_fld_gp_filt = u" and %s" % filt
            fld_gp_val_lbl = fld_gp_lbls.get(fld_gp_val, fld_gp_val)
            chart_by_label = u"%s: %s" % (fld_gp_name, fld_gp_val_lbl)
        else:
            and_fld_gp_filt = u""
            chart_by_label = mg.CHART_CHART_BY_LABEL_ALL
        sql_dic[u"and_fld_gp_filt"] = and_fld_gp_filt
        SQL_get_vals = u"""SELECT %(fld_measure)s 
            FROM %(tbl)s
            WHERE %(fld_measure)s IS NOT NULL
                %(and_tbl_filt)s %(and_fld_gp_filt)s
            ORDER BY %(fld_measure)s""" % sql_dic
        if debug: print(SQL_get_vals)
        cur.execute(SQL_get_vals)
        vals = [x[0] for x in cur.fetchall()]
        if len(vals) < mg.MIN_HISTO_VALS:
            raise my_exceptions.TooFewValsForDisplay(min_n= mg.MIN_HISTO_VALS)
        # use nicest bins practical
        n_bins, lower_limit, upper_limit = lib.get_bins(min(vals), max(vals))
        (y_vals, start, 
            bin_width, unused) = core_stats.histogram(vals, n_bins, 
                                                defaultreallimits=[lower_limit, 
                                                                   upper_limit])
        y_vals, start, bin_width = lib.fix_sawtoothing(vals, n_bins, y_vals, 
                                                       start, bin_width)
        minval = start
        # only show as many decimal points as needed
        dp = 0
        while True:
            if (round(start, dp) != round(start + bin_width, dp)) or dp > 6:
                break
            dp += 1
        bin_ranges = []
        for y_val in y_vals:
            bin_start = round(start, dp)
            bin_end = round(start + bin_width, dp)
            start = bin_end
            bin_ranges.append((bin_start, bin_end))
        bin_labels = [_(u"%(lower)s to < %(upper)s") % 
                            {u"lower": x[0], u"upper": x[1]} for x in bin_ranges]
        maxval = bin_end
        xaxis_dets = [(x+1, u"") for x in range(n_bins)]
        if debug: print(minval, maxval, xaxis_dets, y_vals, bin_labels)
        histo_dic = {mg.CHART_CHART_BY_LABEL: chart_by_label,
                     mg.CHART_XAXIS_DETS: xaxis_dets,
                     mg.CHART_Y_VALS: y_vals,
                     mg.CHART_MINVAL: minval,
                     mg.CHART_MAXVAL: maxval,
                     mg.CHART_BIN_LABELS: bin_labels}
        histo_dets.append(histo_dic)
    return histo_dets

def get_scatterplot_dets(dbe, cur, tbl, tbl_filt, fld_x_axis, fld_y_axis, 
                         fld_gp, fld_gp_name, fld_gp_lbls, unique=True):
    """
    unique -- unique x-y pairs only
    """
    debug = False
    obj_qtr = getdata.get_obj_quoter_func(dbe)
    unused, and_tbl_filt = lib.get_tbl_filts(tbl_filt)
    sql_dic = {u"fld_gp": obj_qtr(fld_gp),
               u"fld_x_axis": obj_qtr(fld_x_axis),
               u"fld_y_axis": obj_qtr(fld_y_axis),
               u"tbl": obj_qtr(tbl), u"and_tbl_filt": and_tbl_filt}
    if fld_gp:
        SQL_fld_gp_vals = u"""SELECT %(fld_gp)s 
            FROM %(tbl)s 
            WHERE %(fld_x_axis)s IS NOT NULL AND %(fld_y_axis)s IS NOT NULL  
            %(and_tbl_filt)s 
            GROUP BY %(fld_gp)s""" % sql_dic
        cur.execute(SQL_fld_gp_vals)
        fld_gp_vals = [x[0] for x in cur.fetchall()]
        if len(fld_gp_vals) > mg.CHART_MAX_CHARTS_IN_SET:
            raise my_exceptions.TooManyChartsInSeries(fld_gp_name, 
                                           max_items=mg.CHART_MAX_CHARTS_IN_SET)
        elif len(fld_gp_vals) == 0:
            raise my_exceptions.TooFewValsForDisplay
    else:
        fld_gp_vals = [None,] # Got to have something to loop through ;-)
    scatterplot_dets = []
    for fld_gp_val in fld_gp_vals:
        if fld_gp:
            filt = getdata.make_fld_val_clause(dbe, dd.flds, fld_name=fld_gp, 
                                               val=fld_gp_val)
            and_fld_gp_filt = u" and %s" % filt
            fld_gp_val_lbl = fld_gp_lbls.get(fld_gp_val, fld_gp_val)
            chart_by_label = u"%s: %s" % (fld_gp_name, fld_gp_val_lbl)
        else:
            and_fld_gp_filt = u""
            chart_by_label = mg.CHART_CHART_BY_LABEL_ALL
        sql_dic[u"and_fld_gp_filt"] = and_fld_gp_filt
        if unique:
            SQL_get_pairs = u"""SELECT %(fld_x_axis)s, %(fld_y_axis)s
                    FROM %(tbl)s
                    WHERE %(fld_x_axis)s IS NOT NULL
                    AND %(fld_y_axis)s IS NOT NULL 
                    %(and_fld_gp_filt)s
                    %(and_tbl_filt)s
                    GROUP BY %(fld_x_axis)s, %(fld_y_axis)s""" % sql_dic
        else:
            SQL_get_pairs = u"""SELECT %(fld_x_axis)s, %(fld_y_axis)s
                    FROM %(tbl)s
                    WHERE %(fld_x_axis)s IS NOT NULL
                    AND %(fld_y_axis)s IS NOT NULL 
                    %(and_fld_gp_filt)s
                    %(and_tbl_filt)s""" % sql_dic
        if debug: print(SQL_get_pairs)
        cur.execute(SQL_get_pairs)
        data_tups = cur.fetchall()
        if not fld_gp:
            if not data_tups:
                raise my_exceptions.TooFewValsForDisplay
        lst_x = [x[0] for x in data_tups]
        lst_y = [x[1] for x in data_tups]
        if debug: print(chart_by_label)
        scatterplot_dic = {mg.CHART_CHART_BY_LABEL: chart_by_label,
                           mg.LIST_X: lst_x, mg.LIST_Y: lst_y,
                           mg.DATA_TUPS: data_tups,}
        scatterplot_dets.append(scatterplot_dic)
    return scatterplot_dets

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
        freq = int(freq)
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

def get_barchart_sizings(xaxis_dets, series_dets):
    debug = False
    n_clusters = len(xaxis_dets)
    n_bars_in_cluster = len(series_dets)
    minor_ticks = u"false"
    if n_clusters <= 2:
        xfontsize = 10
        width = 500 # image width
        xgap = 40
    elif n_clusters <= 5:
        xfontsize = 10
        width = 600
        xgap = 20
    elif n_clusters <= 8:
        xfontsize = 9
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
        xfontsize = xfontsize if xfontsize <= 10 else 10
    left_axis_label_shift = 20 if width > 1200 else 0 # gets squeezed 
        # out otherwise
    if debug: print(width, xgap, xfontsize, minor_ticks, left_axis_label_shift)
    return width, xgap, xfontsize, minor_ticks, left_axis_label_shift

def get_linechart_sizings(xaxis_dets, max_label_len, series_dets):
    debug = False
    n_vals = len(xaxis_dets)
    n_lines = len(series_dets)
    if n_vals < 30:
        width = 800
        xfontsize = 10
    elif n_vals < 60:
        width = 1200
        xfontsize = 10
    elif n_vals < 100:
        width = 1600
        xfontsize = 9
    else:
        width = 2000
        xfontsize = 8
    minor_ticks = u"true" if n_vals > 8 else u"false"
    micro_ticks = u"true" if n_vals > 100 else u"false"
    if n_vals > 10:
        if max_label_len > 10:
            width += 2000
        elif max_label_len > 7:
            width += 1500
        elif max_label_len > 4:
            width += 1000
    if debug: print(width, xfontsize, minor_ticks, micro_ticks)
    return width, xfontsize, minor_ticks, micro_ticks

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
    """
    For titles and subtitles.
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
    return title_dets_html

def get_label_dets(xaxis_dets, series_dets):
    label_dets = []
    for i, xaxis_det in enumerate(xaxis_dets,1):
        val_label = xaxis_det[2]
        label_dets.append(u"{value: %s, text: %s}" % (i, val_label))
    return label_dets

def get_left_axis_shift(xaxis_dets):
    """
    Need to shift margin left if wide labels to keep y-axis title close enough 
        to y_axis labels.
    """
    debug = False
    left_axis_label_shift = 0
    try:
        label1_len = len(xaxis_dets[0][1])
        if label1_len > 5:
            left_axis_label_shift = label1_len*-1.3
    except Exception, e:
        pass
    if debug: print(left_axis_label_shift)
    return left_axis_label_shift

def is_multichart(chart_dets):
    if len(chart_dets) > 1:
        multichart = True
    elif len(chart_dets) == 1:
        # might be only one field group value - still needs indiv chart title
        multichart = (chart_dets[0][mg.CHART_CHART_BY_LABEL] !=
                      mg.CHART_CHART_BY_LABEL_ALL) 
    else:
        multichart = False
    return multichart

def barchart_output(titles, subtitles, x_title, barchart_dets, inc_perc, 
                    css_idx, css_fil, page_break_after):
    """
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    series_labels -- e.g. ["Age Group", ] if simple bar chart,
        e.g. ["Male", "Female"] if clustered bar chart.
    var_numeric -- needs to be quoted or not.
    xaxis_dets -- [(1, "Under 20"), (2, "20-29"), (3, "30-39"), (4, "40-64"),
                   (5, "65+")]
    css_idx -- css index so can apply appropriate css styles
    """
    debug = False
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                          css_idx)
    html = []
    title_dets_html = get_title_dets_html(titles, subtitles, css_idx)
    html.append(title_dets_html)
    multichart = is_multichart(barchart_dets)
    axis_label_drop = 30 if x_title else 10
    if multichart:
        axis_label_drop = axis_label_drop*0.8
    height = 310 + axis_label_drop # compensate for loss of bar display height
    inc_perc_js = u"true" if inc_perc else u"false"
    """
    For each series, set colour details.
    For the collection of series as a whole, set the highlight mapping from 
        each series colour.
    From dojox.charting.action2d.Highlight but with extraneous % removed
    """
    (outer_bg, grid_bg, axis_label_font_colour, major_gridline_colour, 
            gridline_width, stroke_width, tooltip_border_colour, 
            colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
    outer_bg = u"" if outer_bg == u"" \
        else u"chartconf[\"outerBg\"] = \"%s\";" % outer_bg
    for chart_idx, barchart_det in enumerate(barchart_dets):
        xaxis_dets = barchart_det[mg.CHART_XAXIS_DETS]
        series_dets = barchart_det[mg.CHART_SERIES_DETS]
        pagebreak = u"" if chart_idx % 2 == 0 else u"page-break-after: always;"
        indiv_bar_title = "<p><b>%s</b></p>" % \
                    barchart_det[mg.CHART_CHART_BY_LABEL] if multichart else u""
        label_dets = get_label_dets(xaxis_dets, series_dets)
        single_colour = (len(series_dets) == 1)
        override_first_highlight = (css_fil == mg.DEFAULT_CSS_PATH 
                                    and single_colour)
        colour_cases = setup_highlights(colour_mappings, single_colour, 
                                        override_first_highlight)
        xaxis_labels = u"[" + u",\n            ".join(label_dets) + u"]"
        (width, xgap, xfontsize, minor_ticks, 
              left_axis_label_shift) = get_barchart_sizings(xaxis_dets, 
                                                            series_dets)
        if multichart:
            width = width*0.8
            xgap = xgap*0.8
            xfontsize = xfontsize*0.8
            left_axis_label_shift = left_axis_label_shift + 20
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
    chartconf["xaxisLabels"] = %(xaxis_labels)s;
    chartconf["xgap"] = %(xgap)s;
    chartconf["xfontsize"] = %(xfontsize)s;
    chartconf["sofaHl"] = sofaHlRenumber%(chart_idx)s;
    chartconf["gridlineWidth"] = %(gridline_width)s;
    chartconf["gridBg"] = \"%(grid_bg)s\";
    chartconf["minorTicks"] = %(minor_ticks)s;
    chartconf["axisLabelFontColour"] = \"%(axis_label_font_colour)s\";
    chartconf["majorGridlineColour"] = \"%(major_gridline_colour)s\";
    chartconf["xTitle"] = \"%(x_title)s\";
    chartconf["axisLabelDrop"] = %(axis_label_drop)s;
    chartconf["leftAxisLabelShift"] = %(left_axis_label_shift)s;
    chartconf["yTitle"] = \"%(y_title)s\";
    chartconf["tooltipBorderColour"] = \"%(tooltip_border_colour)s\";
    chartconf["incPerc"] = %(inc_perc_js)s;
    chartconf["connectorStyle"] = \"%(connector_style)s\";
    %(outer_bg)s
    makeBarChart("mychartRenumber%(chart_idx)s", series, chartconf);
}
</script>

<div class="screen-float-only" style="margin-right: 10px; %(pagebreak)s">
%(indiv_bar_title)s
<div id="mychartRenumber%(chart_idx)s" 
    style="width: %(width)spx; height: %(height)spx;">
    </div>
<div id="legendMychartRenumber%(chart_idx)s">
    </div>
</div>
        """ % {u"colour_cases": colour_cases,
               u"series_js": series_js, u"xaxis_labels": xaxis_labels, 
               u"width": width, u"height": height, u"xgap": xgap, 
               u"xfontsize": xfontsize, u"indiv_bar_title": indiv_bar_title,
               u"axis_label_font_colour": axis_label_font_colour,
               u"major_gridline_colour": major_gridline_colour,
               u"gridline_width": gridline_width, 
               u"axis_label_drop": axis_label_drop,
               u"left_axis_label_shift": left_axis_label_shift,
               u"x_title": x_title, u"y_title": mg.Y_AXIS_FREQ_LABEL,
               u"tooltip_border_colour": tooltip_border_colour, 
               u"inc_perc_js": inc_perc_js, u"connector_style": connector_style, 
               u"outer_bg": outer_bg,  u"pagebreak": pagebreak,
               u"chart_idx": u"%02d" % chart_idx,
               u"grid_bg": grid_bg, u"minor_ticks": minor_ticks})
    """
    zero padding chart_idx so that when we search and replace, and go to replace 
        Renumber1 with Renumber15, we don't change Renumber16 to Renumber156 ;-)
    """
    html.append(u"""<div style="clear: both;">&nbsp;&nbsp;</div>""")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)

def piechart_output(titles, subtitles, pie_chart_dets, css_fil, css_idx, 
                    page_break_after):
    debug = False
    if debug: print(pie_chart_dets)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    multichart = is_multichart(pie_chart_dets)
    html = []
    title_dets_html = get_title_dets_html(titles, subtitles, css_idx)
    html.append(title_dets_html)
    width = 500 if mg.PLATFORM == mg.WINDOWS else 450
    if multichart:
        width = width*0.8
    height = 350 if multichart else 400
    radius = 120 if multichart else 140
    label_offset = -20 if multichart else -30
    (outer_bg, inner_bg, axis_label_font_colour, 
         major_gridline_colour, gridline_width, stroke_width, 
         tooltip_border_colour, 
         colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
    outer_bg = u"" if outer_bg == u"" \
        else u"""chartconf["outerBg"] = "%s";""" % outer_bg
    colour_cases = setup_highlights(colour_mappings, single_colour=False, 
                                    override_first_highlight=False)
    colours = [str(x[0]) for x in colour_mappings]
    colours.extend(mg.DOJO_COLOURS)
    slice_colours = colours[:30]
    label_font_colour = axis_label_font_colour
    for chart_idx, pie_chart_det in enumerate(pie_chart_dets):
        pagebreak = u"" if chart_idx % 2 == 0 else u"page-break-after: always;"
        slices_js_list = []
        slice_dets = pie_chart_det[mg.CHART_SLICE_DETS]
        slice_fontsize = 14 if len(slice_dets) < 10 else 10
        if multichart:
            slice_fontsize = slice_fontsize*0.8
        for slice_det in slice_dets:
            slices_js_list.append(u"{\"y\": %(y)s, \"text\": %(text)s, " 
                    u"\"tooltip\": \"%(tooltip)s\"}" % {u"y": slice_det[u"y"], 
                    u"text": slice_det[u"text"], 
                    u"tooltip": slice_det[u"tooltip"]})
        slices_js = u"slices = [" + (u",\n" + u" "*4*4).join(slices_js_list) + \
                    u"\n];"
        indiv_pie_title = "<p><b>%s</b></p>" % \
                   pie_chart_det[mg.CHART_CHART_BY_LABEL] if multichart else u""
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
    chartconf["labelFontColour"] = "%(label_font_colour)s";
    chartconf["tooltipBorderColour"] = "%(tooltip_border_colour)s";
    chartconf["connectorStyle"] = "%(connector_style)s";
    %(outer_bg)s
    chartconf["innerBg"] = "%(inner_bg)s";
    chartconf["radius"] = %(radius)s;
    chartconf["labelOffset"] = %(label_offset)s;
    makePieChart("mychartRenumber%(chart_idx)s", slices, chartconf);
}
</script>

<div class="screen-float-only" style="margin-right: 10px; %(pagebreak)s">
%(indiv_pie_title)s
<div id="mychartRenumber%(chart_idx)s" 
    style="width: %(width)spx; height: %(height)spx;">
    </div>
</div>
        """ % {u"slice_colours": slice_colours, u"colour_cases": colour_cases, 
               u"width": width, u"height": height, u"radius": radius,
               u"label_offset": label_offset, u"pagebreak": pagebreak,
               u"indiv_pie_title": indiv_pie_title,
               u"slices_js": slices_js, u"slice_fontsize": slice_fontsize, 
               u"label_font_colour": label_font_colour,
               u"tooltip_border_colour": tooltip_border_colour,
               u"connector_style": connector_style, u"outer_bg": outer_bg, 
               u"inner_bg": inner_bg, u"chart_idx": u"%02d" % chart_idx,
               })
    html.append(u"""<div style="clear: both;">&nbsp;&nbsp;</div>""")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)
    
def linechart_output(titles, subtitles, x_title, xaxis_dets, max_label_len, 
                     series_dets, inc_perc, css_fil, css_idx, 
                     page_break_after):
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
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    title_dets_html = get_title_dets_html(titles, subtitles, css_idx)
    # For multiple, don't split label if mid tick (clash with x axis label)
    label_dets = get_label_dets(xaxis_dets, series_dets)
    xaxis_labels = u"[" + u",\n            ".join(label_dets) + u"]"
    axis_label_drop = 30 if x_title else -10
    height = 310 + axis_label_drop # compensate for loss of bar display height                           
    (width, xfontsize, 
     minor_ticks, micro_ticks) = get_linechart_sizings(xaxis_dets, 
                                                     max_label_len, series_dets)
    left_axis_label_shift = 20 if width > 1200 else 10 # gets squeezed 
    inc_perc_js = u"true" if inc_perc else u"false"
    html = []
    """
    For each series, set colour details.
    For the collection of series as a whole, set the highlight mapping from 
        each series colour.
    From dojox.charting.action2d.Highlight but with extraneous % removed
    """
    (outer_bg, grid_bg, axis_label_font_colour, major_gridline_colour, 
            gridline_width, stroke_width, tooltip_border_colour, 
            colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
    # Can't have white for line charts because always a white outer background
    axis_label_font_colour = axis_label_font_colour \
                            if axis_label_font_colour != u"white" else u"black"
    # build js for every series
    series_js_list = []
    series_names_list = []
    if debug: print(series_dets)
    pagebreak = u"page-break-after: always;"
    for i, series_det in enumerate(series_dets):
        series_names_list.append(u"series%s" % i)
        series_js_list.append(u"var series%s = new Array();" % i)
        series_js_list.append(u"            series%s[\"seriesLabel\"] = \"%s\";"
                              % (i, series_det[u"label"]))
        series_js_list.append(u"            series%s[\"yVals\"] = %s;" % 
                              (i, series_det[u"y_vals"]))
        try:
            stroke = colour_mappings[i][0]
        except IndexError, e:
            stroke = mg.DOJO_COLOURS[i]
        series_js_list.append(u"            series%s[\"style\"] = "
            u"{stroke: {color: \"%s\", width: \"6px\"}};" % (i, stroke))
        series_js_list.append(u"")
    series_js = u"\n            ".join(series_js_list)
    series_js += u"\n            var series = new Array(%s);" % \
                                                u", ".join(series_names_list)
    series_js = series_js.lstrip()
    html.append(u"""
<script type="text/javascript">

makechartRenumber00 = function(){
    %(series_js)s
    var chartconf = new Array();
    chartconf["xaxisLabels"] = %(xaxis_labels)s;
    chartconf["xfontsize"] = %(xfontsize)s;
    chartconf["gridlineWidth"] = %(gridline_width)s;
    chartconf["gridBg"] = "%(grid_bg)s";
    chartconf["minorTicks"] = %(minor_ticks)s;
    chartconf["microTicks"] = %(micro_ticks)s;
    chartconf["axisLabelFontColour"] = "%(axis_label_font_colour)s";
    chartconf["majorGridlineColour"] = "%(major_gridline_colour)s";
    chartconf["xTitle"] = "%(x_title)s";
    chartconf["axisLabelDrop"] = %(axis_label_drop)s;
    chartconf["leftAxisLabelShift"] = %(left_axis_label_shift)s;
    chartconf["yTitle"] = "%(y_title)s";
    chartconf["tooltipBorderColour"] = "%(tooltip_border_colour)s";
    chartconf["incPerc"] = %(inc_perc_js)s;
    chartconf["connectorStyle"] = "%(connector_style)s";
    makeLineChart("mychartRenumber00", series, chartconf);
}
</script>
%(titles)s
    
<div class="screen-float-only" style="margin-right: 10px; %(pagebreak)s">

<div id="mychartRenumber00" style="width: %(width)spx; 
        height: %(height)spx;">
    </div>
<div id="legendMychartRenumber00">
    </div>
</div>
    """ % {u"titles": title_dets_html, 
           u"series_js": series_js, u"xaxis_labels": xaxis_labels, 
           u"width": width, u"height": height, u"xfontsize": xfontsize, 
           u"axis_label_font_colour": axis_label_font_colour,
           u"major_gridline_colour": major_gridline_colour,
           u"gridline_width": gridline_width, u"pagebreak": pagebreak,
           u"axis_label_drop": axis_label_drop,
           u"left_axis_label_shift": left_axis_label_shift,
           u"x_title": x_title, u"y_title": mg.Y_AXIS_FREQ_LABEL,
           u"tooltip_border_colour": tooltip_border_colour,
           u"inc_perc_js": inc_perc_js, u"connector_style": connector_style, 
           u"grid_bg": grid_bg, 
           u"minor_ticks": minor_ticks, u"micro_ticks": micro_ticks})
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)
    
def areachart_output(titles, subtitles, chart_dets, inc_perc, css_fil, css_idx, 
                     page_break_after):
    """
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    css_idx -- css index so can apply    
    """
    debug = False
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    multichart = is_multichart(chart_dets)
    html = []
    title_dets_html = get_title_dets_html(titles, subtitles, css_idx)
    html.append(title_dets_html)
    inc_perc_js = u"true" if inc_perc else u"false"
    height = 250 if multichart else 300
    """
    For each series, set colour details.
    For the collection of series as a whole, set the highlight mapping from 
        each series colour.
    From dojox.charting.action2d.Highlight but with extraneous % removed
    """
    (outer_bg, grid_bg, axis_label_font_colour, major_gridline_colour, 
            gridline_width, stroke_width, tooltip_border_colour, 
            colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
    # Can't have white for line charts because always a white outer background
    axis_label_font_colour = axis_label_font_colour \
                            if axis_label_font_colour != u"white" else u"black"
    colour_cases = setup_highlights(colour_mappings, single_colour=False, 
                                    override_first_highlight=True)    
    for chart_idx, areachart_det in enumerate(chart_dets):
        xaxis_dets = areachart_det[mg.CHART_XAXIS_DETS]
        series_dets = areachart_det[mg.CHART_SERIES_DETS]
        max_label_len = areachart_det[mg.CHART_MAX_LABEL_LEN]
        pagebreak = u"" if chart_idx % 2 == 0 else u"page-break-after: always;"
        indiv_area_title = "<p><b>%s</b></p>" % \
                areachart_det[mg.CHART_CHART_BY_LABEL] if multichart else u""
        xaxis_labels = u"[" + \
            u",\n            ".join([u"{value: %s, text: %s}" % (i, x[2]) 
                                    for i,x in enumerate(xaxis_dets,1)]) + u"]"
        (width, xfontsize, minor_ticks, 
                micro_ticks) = get_linechart_sizings(xaxis_dets, max_label_len, 
                                                     series_dets)
        left_axis_label_shift = 20 if width > 1200 else 0 # gets squeezed 
        if multichart:
            width = width*0.8
            xfontsize = xfontsize*0.8
            left_axis_label_shift = left_axis_label_shift + 20
        # build js for every series
        series_js_list = []
        series_names_list = []
        if debug: print(series_dets)
        for i, series_det in enumerate(series_dets):
            series_names_list.append(u"series%s" % i)
            series_js_list.append(u"var series%s = new Array();" % i)
            series_js_list.append(u"            "
                                  u"series%s[\"seriesLabel\"] = \"%s\";"
                                  % (i, series_det[u"label"]))
            series_js_list.append(u"            series%s[\"yVals\"] = %s;" % 
                                  (i, series_det[u"y_vals"]))
            try:
                stroke = colour_mappings[i][0]
                fill = colour_mappings[i][1]
            except IndexError, e:
                stroke = mg.DOJO_COLOURS[i]
            series_js_list.append(u"            series%s[\"style\"] = "
                u"{stroke: {color: \"%s\", width: \"6px\"}, fill: \"%s\"};" % 
                (i, stroke, fill))
            series_js_list.append(u"")
        series_js = u"\n            ".join(series_js_list)
        series_js += u"\n            var series = new Array(%s);" % \
                                                u", ".join(series_names_list)
        series_js = series_js.lstrip()
        html.append(u"""
<script type="text/javascript">
makechartRenumber%(chart_idx)s = function(){
    %(series_js)s
    var chartconf = new Array();
    chartconf["xaxisLabels"] = %(xaxis_labels)s;
    chartconf["xfontsize"] = %(xfontsize)s;
    chartconf["gridlineWidth"] = %(gridline_width)s;
    chartconf["gridBg"] = "%(grid_bg)s";
    chartconf["minorTicks"] = %(minor_ticks)s;
    chartconf["microTicks"] = %(micro_ticks)s;
    chartconf["leftAxisLabelShift"] = %(left_axis_label_shift)s;
    chartconf["axisLabelFontColour"] = "%(axis_label_font_colour)s";
    chartconf["majorGridlineColour"] = "%(major_gridline_colour)s";
    chartconf["yTitle"] = "%(y_title)s";
    chartconf["tooltipBorderColour"] = "%(tooltip_border_colour)s";
    chartconf["incPerc"] = %(inc_perc_js)s;
    chartconf["connectorStyle"] = "%(connector_style)s";
    makeAreaChart("mychartRenumber%(chart_idx)s", series, chartconf);
}
</script>

<div style="float: left; margin-right: 10px; %(pagebreak)s">
%(indiv_area_title)s
<div id="mychartRenumber%(chart_idx)s" 
    style="width: %(width)spx; height: %(height)spx; %(pagebreak)s">
    </div>
<div id="legendMychartRenumber%(chart_idx)s">
    </div>
</div>
        """ % {u"series_js": series_js, u"xaxis_labels": xaxis_labels, 
               u"indiv_area_title": indiv_area_title,
               u"width": width, u"height": height, u"xfontsize": xfontsize, 
               u"axis_label_font_colour": axis_label_font_colour,
               u"major_gridline_colour": major_gridline_colour,
               u"left_axis_label_shift": left_axis_label_shift,
               u"gridline_width": gridline_width, 
               u"y_title": mg.Y_AXIS_FREQ_LABEL, u"pagebreak": pagebreak,
               u"tooltip_border_colour": tooltip_border_colour,
               u"inc_perc_js": inc_perc_js, u"connector_style": connector_style, 
               u"grid_bg": grid_bg, u"chart_idx": u"%02d" % chart_idx,
               u"minor_ticks": minor_ticks, u"micro_ticks": micro_ticks})
    html.append(u"""<div style="clear: both;">&nbsp;&nbsp;</div>""")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)

def histogram_output(titles, subtitles, var_label, histo_dets, css_fil, 
                     css_idx, page_break_after=False):
    """
    See http://trac.dojotoolkit.org/ticket/7926 - he had trouble doing this then
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    minval -- minimum values for x axis
    maxval -- maximum value for x axis
    xaxis_dets -- [(1, u""), (2, u""), ...]
    y_vals -- list of values e.g. [[12, 30, 100.5, -1, 40], ]
    bin_labels -- [u"1 to under 2", u"2 to under 3", ...]
    css_idx -- css index so can apply    
    """
    debug = False
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    multichart = is_multichart(histo_dets)
    html = []
    title_dets_html = get_title_dets_html(titles, subtitles, css_idx)
    html.append(title_dets_html)
    height = 300 if multichart else 350
    (outer_bg, grid_bg, axis_label_font_colour, major_gridline_colour, 
            gridline_width, stroke_width, tooltip_border_colour, 
            colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
    outer_bg = u"" if outer_bg == u"" \
        else u"chartconf[\"outerBg\"] = \"%s\";" % outer_bg
    single_colour = True
    override_first_highlight = (css_fil == mg.DEFAULT_CSS_PATH 
                                and single_colour)
    colour_cases = setup_highlights(colour_mappings, single_colour, 
                                    override_first_highlight)
    try:
        fill = colour_mappings[0][0]
    except IndexError, e:
        fill = mg.DOJO_COLOURS[0]
    for chart_idx, histo_det in enumerate(histo_dets):
        minval = histo_det[mg.CHART_MINVAL]
        maxval = histo_det[mg.CHART_MAXVAL]
        xaxis_dets = histo_det[mg.CHART_XAXIS_DETS]
        y_vals = histo_det[mg.CHART_Y_VALS]
        bin_labels = histo_det[mg.CHART_BIN_LABELS]
        pagebreak = u"" if chart_idx % 2 == 0 else u"page-break-after: always;"
        indiv_histo_title = "<p><b>%s</b></p>" % \
                histo_det[mg.CHART_CHART_BY_LABEL] if multichart else u""        
        xaxis_labels = u"[" + \
            u",\n            ".join([u"{value: %s, text: \"%s\"}" % (i, x[1]) 
                                    for i,x in enumerate(xaxis_dets,1)]) + u"]"
        bin_labs = u"\"" + u"\", \"".join(bin_labels) + u"\""
        width = 700
        xfontsize = 10
        left_axis_label_shift = 30 if width > 1200 else 10 # gets squeezed 
        if multichart:
            width = width*0.8
            xfontsize = xfontsize*0.8
            left_axis_label_shift += 20
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
    datadets["seriesLabel"] = "%(var_label)s";
    datadets["yVals"] = %(y_vals)s;
    datadets["binLabels"] = [%(bin_labels)s];
    datadets["style"] = {stroke: {color: "white", 
        width: "%(stroke_width)spx"}, fill: "%(fill)s"};
    
    var chartconf = new Array();
    chartconf["xaxisLabels"] = %(xaxis_labels)s;
    chartconf["xfontsize"] = %(xfontsize)s;
    chartconf["sofaHl"] = sofaHlRenumber%(chart_idx)s;
    chartconf["tickColour"] = "%(tick_colour)s";
    chartconf["gridlineWidth"] = %(gridline_width)s;
    chartconf["gridBg"] = "%(grid_bg)s";
    chartconf["minorTicks"] = %(minor_ticks)s;
    chartconf["leftAxisLabelShift"] = %(left_axis_label_shift)s;
    chartconf["axisLabelFontColour"] = "%(axis_label_font_colour)s";
    chartconf["majorGridlineColour"] = "%(major_gridline_colour)s";
    chartconf["yTitle"] = "%(y_title)s";
    chartconf["tooltipBorderColour"] = "%(tooltip_border_colour)s";
    chartconf["connectorStyle"] = "%(connector_style)s";
    chartconf["minVal"] = %(minval)s;
    chartconf["maxVal"] = %(maxval)s;
    %(outer_bg)s
    makeHistogram("mychartRenumber%(chart_idx)s", datadets, chartconf);
}
</script>

<div class="screen-float-only" style="margin-right: 10px; %(pagebreak)s">
%(indiv_histo_title)s
<div id="mychartRenumber%(chart_idx)s" 
        style="width: %(width)spx; height: %(height)spx;">
    </div>
</div>
        """ % {u"indiv_histo_title": indiv_histo_title,
               u"stroke_width": stroke_width, u"fill": fill,
               u"colour_cases": colour_cases,
               u"xaxis_labels": xaxis_labels, u"y_vals": u"%s" % y_vals,
               u"bin_labels": bin_labs, u"minval": minval, u"maxval": maxval,
               u"width": width, u"height": height, u"xfontsize": xfontsize, 
               u"var_label": var_label,
               u"left_axis_label_shift": left_axis_label_shift,
               u"axis_label_font_colour": axis_label_font_colour,
               u"major_gridline_colour": major_gridline_colour,
               u"gridline_width": gridline_width, 
               u"y_title": mg.Y_AXIS_FREQ_LABEL, u"pagebreak": pagebreak,
               u"tooltip_border_colour": tooltip_border_colour,
               u"connector_style": connector_style, u"outer_bg": outer_bg, 
               u"grid_bg": grid_bg, u"chart_idx": u"%02d" % chart_idx,
               u"minor_ticks": u"true",
               u"tick_colour": major_gridline_colour})
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
    use_mpl = False
    for indiv_data in scatterplot_dets:
        if len(indiv_data[mg.DATA_TUPS]) > mg.MAX_POINTS_DOJO_SCATTERPLOT:
            use_mpl = True
            break
    return use_mpl

def make_mpl_scatterplot(multichart, html, indiv_scatterplot_title, dot_borders, 
                         list_x, list_y, label_x, label_y, x_vs_y, 
                         add_to_report, report_name, css_fil, pagebreak):
    debug = False
    (grid_bg, item_colours, 
               line_colour) = output.get_stats_chart_colours(css_fil)
    colours = item_colours + mg.DOJO_COLOURS
    dot_colour = colours[0]
    if multichart:
        width_inches, height_inches = (6.0, 3.6)
    else:
        width_inches, height_inches = (7.5, 4.5)
    title_dets_html = u"" # handled prior to this step
    html.append(u"""<div class=screen-float-only style="margin-right: 10px; 
        %(pagebreak)s">""" % {u"pagebreak": pagebreak})
    html.append(indiv_scatterplot_title)
    charting_pylab.add_scatterplot(grid_bg, dot_colour, dot_borders, 
                                   line_colour, list_x, list_y, label_x, 
                                   label_y, x_vs_y, title_dets_html, 
                                   add_to_report, report_name, html, 
                                   width_inches, height_inches)
    html.append(u"</div>")

def make_dojo_scatterplot(chart_idx, multichart, html, indiv_scatterplot_title, 
                          dot_borders, data_tups, list_x, list_y, label_x, 
                          label_y, x_vs_y, css_fil, pagebreak):
    debug = False
    if multichart:  
        width, height = (500, 300)
    else:
        width, height = (700, 350)
    left_axis_label_shift = 10
    xfontsize = 10
    xmax = max(list_x)
    x_title = label_x
    axis_label_drop = 10
    ymax = max(list_y)
    y_title = label_y
    if debug: print(label_x, xmax, label_y, ymax)
    jsdata = []
    x_set = set()
    for x, y in data_tups:
        jsdata.append("{x: %s, y: %s}" % (x, y))
        x_set.add(x)
    few_unique_x_vals = (len(x_set) < 10)
    minor_ticks = u"false" if few_unique_x_vals else u"true"
    xy_pairs = "[" + ",\n".join(jsdata) + "]"
    (outer_bg, grid_bg, axis_label_font_colour, major_gridline_colour, 
     gridline_width, stroke_width, tooltip_border_colour, 
     colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
    stroke_width = stroke_width if dot_borders else 0 
    outer_bg = u"" if outer_bg == u"" \
        else u"chartconf[\"outerBg\"] = \"%s\";" % outer_bg
    single_colour = True
    override_first_highlight = (css_fil == mg.DEFAULT_CSS_PATH 
                                and single_colour)
    colour_cases = setup_highlights(colour_mappings, single_colour, 
                                    override_first_highlight)
    try:
        fill = colour_mappings[0][0]
    except IndexError, e:
        fill = mg.DOJO_COLOURS[0]
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
    var datadets = new Array();
    datadets["xyPairs"] = %(xy_pairs)s;
    datadets["style"] = {stroke: {color: \"white\", 
        width: "%(stroke_width)spx"}, fill: "%(fill)s",
        marker: "m-6,0 c0,-8 12,-8 12,0 m-12,0 c0,8 12,8 12,0"};
    
    var chartconf = new Array();
    chartconf["xmax"] = %(xmax)s;
    chartconf["ymax"] = %(ymax)s;
    chartconf["xfontsize"] = %(xfontsize)s;
    chartconf["sofaHl"] = sofaHlRenumber%(chart_idx)s;
    chartconf["tickColour"] = "%(tick_colour)s";
    chartconf["gridlineWidth"] = %(gridline_width)s;
    chartconf["gridBg"] = \"%(grid_bg)s\";
    chartconf["minorTicks"] = %(minor_ticks)s;
    chartconf["leftAxisLabelShift"] = %(left_axis_label_shift)s;
    chartconf["axisLabelFontColour"] = "%(axis_label_font_colour)s";
    chartconf["majorGridlineColour"] = "%(major_gridline_colour)s";
    chartconf["xTitle"] = "%(x_title)s";
    chartconf["axisLabelDrop"] = %(axis_label_drop)s;
    chartconf["yTitle"] = "%(y_title)s";
    chartconf["tooltipBorderColour"] = "%(tooltip_border_colour)s";
    chartconf["connectorStyle"] = "%(connector_style)s";
    %(outer_bg)s
    makeScatterplot("mychartRenumber%(chart_idx)s", datadets, chartconf);
}
</script>

<div class="screen-float-only" style="margin-right: 10px; %(pagebreak)s">
%(indiv_scatterplot_title)s
<div id="mychartRenumber%(chart_idx)s" 
        style="width: %(width)spx; height: %(height)spx;">
    </div>
</div>      
""" % {u"indiv_scatterplot_title": indiv_scatterplot_title,
       u"xy_pairs": xy_pairs, u"xmax": xmax, u"ymax": ymax,
       u"x_title": x_title, u"y_title": y_title,
       u"stroke_width": stroke_width, u"fill": fill,
       u"colour_cases": colour_cases, 
       u"width": width, u"height": height, u"xfontsize": xfontsize, 
       u"series_label": x_vs_y, u"pagebreak": pagebreak,
       u"axis_label_font_colour": axis_label_font_colour,
       u"major_gridline_colour": major_gridline_colour,
       u"left_axis_label_shift": left_axis_label_shift,
       u"gridline_width": gridline_width, 
       u"axis_label_drop": axis_label_drop,
       u"tooltip_border_colour": tooltip_border_colour,
       u"connector_style": connector_style, u"outer_bg": outer_bg, 
       u"grid_bg": grid_bg, u"chart_idx": u"%02d" % chart_idx, 
       u"minor_ticks": minor_ticks, u"tick_colour": major_gridline_colour})

def scatterplot_output(titles, subtitles, scatterplot_dets, label_x, label_y, 
                       add_to_report, report_name, dot_borders, css_fil, 
                       css_idx, page_break_after=False):
    """
    scatter_data -- dict with keys SAMPLE_A, SAMPLE_B, DATA_TUPS
    """
    debug = False
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    pagebreak = u"page-break-after: always;"
    title_dets_html = get_title_dets_html(titles, subtitles, css_idx)
    x_vs_y = '"%s"' % label_x + _(" vs ") + '"%s"' % label_y
    html = []
    html.append(title_dets_html)
    multichart = (len(scatterplot_dets) > 1)
    use_mpl = use_mpl_scatterplots(scatterplot_dets)
    for chart_idx, indiv_data in enumerate(scatterplot_dets):
        chart_by_lbl = indiv_data[mg.CHART_CHART_BY_LABEL]
        data_tups = indiv_data[mg.DATA_TUPS]
        list_x = indiv_data[mg.LIST_X]
        list_y = indiv_data[mg.LIST_Y]
        indiv_scatterplot_title = "<p><b>%s</b></p>" % \
                                            chart_by_lbl if multichart else u""
        if use_mpl:
            make_mpl_scatterplot(multichart, html, indiv_scatterplot_title, 
                                 dot_borders, list_x, list_y, 
                                 label_x, label_y, x_vs_y, add_to_report, 
                                 report_name, css_fil, pagebreak)
        else:
            make_dojo_scatterplot(chart_idx, multichart, html, 
                                  indiv_scatterplot_title, 
                                  dot_borders, data_tups, list_x, list_y, 
                                  label_x, label_y, x_vs_y, css_fil, pagebreak)
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % page_break_before)
    return u"".join(html)
