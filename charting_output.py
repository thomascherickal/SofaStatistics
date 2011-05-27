#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Use English UK spelling e.g. colour and when writing JS use camelcase.
NB no html headers here - the script generates those beforehand and appends 
    this and then the html footer.
For most charts we can use freq and AVG - something SQL does just fine using 
    GROUP BY. Accordingly, we can reuse get_chart_dets in many cases. In other
    cases, however, e.g. box plots, we need to analyse the values to get results 
    that SQL can't do well e.g. quartiles. In such cases we have to custom-make 
    the specific queries we need.
"""

import math
import numpy as np
import pprint

import my_globals as mg
import lib
import my_exceptions
import charting_pylab
import core_stats
import getdata
import output

def get_SQL_raw_data(dbe, tbl_quoted, where_tbl_filt, and_tbl_filt, 
                     measure, fld_measure, fld_gp_by, fld_chart_by,
                     fld_group_series):
    objqtr = getdata.get_obj_quoter_func(dbe)
    sql_dic = {u"tbl": tbl_quoted, 
               u"fld_measure": objqtr(fld_measure),
               u"fld_group_series": objqtr(fld_group_series),
               mg.FLD_GROUP_BY: objqtr(fld_gp_by),
               mg.FLD_CHART_BY: objqtr(fld_chart_by), 
               u"and_tbl_filt": and_tbl_filt,
               u"where_tbl_filt": where_tbl_filt}
    if fld_group_series:
        # series fld, the x vals, and the y vals
        if measure == mg.CHART_FREQS:
            """
            Show zero values.            
            Only include values for either fld_group_series or fld_measure if 
                at least one non-null value in the other dimension. If a whole 
                series is zero, then it won't show. If there is any value in 
                other dim will show that val and zeroes for rest.
            SQL returns something like (grouped by fld_group_series, 
                fld_measure, N with zero freqs as needed):
            data = [(1,1,56),
                    (1,2,103),
                    (1,3,72),
                    (2,1,13),
                    (2,2,0),
                    (2,3,200),]
            """
            SQL_get_measure_vals = u"""SELECT %(fld_measure)s
                FROM %(tbl)s
                WHERE %(fld_group_series)s IS NOT NULL 
                    AND %(fld_measure)s IS NOT NULL
                    %(and_tbl_filt)s
                GROUP BY %(fld_measure)s"""
            SQL_get_group_vals = u"""SELECT %(fld_group_series)s
                FROM %(tbl)s
                WHERE %(fld_measure)s IS NOT NULL 
                    AND %(fld_group_series)s IS NOT NULL
                    %(and_tbl_filt)s
                GROUP BY %(fld_group_series)s"""
            SQL_cartesian_join = """SELECT * FROM (%s) AS qrymeasure INNER JOIN 
                (%s) AS qrygp""" % (SQL_get_measure_vals, SQL_get_group_vals)
            SQL_group_by = u"""SELECT %(fld_group_series)s, %(fld_measure)s,
                    COUNT(*) AS freq
                FROM %(tbl)s
                %(where_tbl_filt)s
                GROUP BY %(fld_group_series)s, %(fld_measure)s"""
            SQL_cartesian_join = SQL_cartesian_join % sql_dic
            SQL_group_by = SQL_group_by % sql_dic
            sql_dic[u"qrycart"] = SQL_cartesian_join
            sql_dic[u"qrygrouped"] = SQL_group_by
            SQL_get_raw_data = """SELECT %(fld_group_series)s, %(fld_measure)s,
                    CASE WHEN freq IS NULL THEN 0 ELSE freq END AS N
                FROM (%(qrycart)s) AS qrycart LEFT JOIN (%(qrygrouped)s) 
                    AS qrygrouped
                USING(%(fld_group_series)s, %(fld_measure)s)
                ORDER BY %(fld_group_series)s, %(fld_measure)s""" % sql_dic
        elif measure == mg.CHART_AVGS:
            """
            Must and will have measure, group_by, and chart_by 
                (the group series). Otherwise fld_group_series would be True.
            Only include values for either fld_chart_by or fld_gp_by if at 
                least one non-null value in the other dimension. If a whole 
                    series is zero, then it won't show. If there is any value 
                    in other dim will show that val and zeroes for rest.
            SQL returns something like (grouped by fld_chart_by, fld_gp_by, 
                averaged measure with zero avgs as needed):
            data = [(1,1,56),
                    (1,2,103),
                    (1,3,72),
                    (2,1,13),
                    (2,2,0),
                    (2,3,200),]
            """
            SQL_get_gp_by_vals = u"""SELECT %(fld_gp_by)s
                FROM %(tbl)s
                WHERE %(fld_chart_by)s IS NOT NULL AND %(fld_gp_by)s IS NOT NULL
                    %(and_tbl_filt)s
                GROUP BY %(fld_gp_by)s"""
            SQL_get_chart_by_vals = u"""SELECT %(fld_chart_by)s
                FROM %(tbl)s
                WHERE %(fld_gp_by)s IS NOT NULL AND %(fld_chart_by)s IS NOT NULL
                    %(and_tbl_filt)s
                GROUP BY %(fld_chart_by)s"""
            SQL_cartesian_join = """SELECT * FROM (%s) AS qryby INNER JOIN 
                (%s) AS qrygp""" % (SQL_get_gp_by_vals, SQL_get_chart_by_vals)
            SQL_group_by = u"""SELECT %(fld_chart_by)s, %(fld_gp_by)s,
                    AVG(%(fld_measure)s) AS measure
                FROM %(tbl)s
                %(where_tbl_filt)s
                GROUP BY %(fld_chart_by)s, %(fld_gp_by)s"""
            SQL_cartesian_join = SQL_cartesian_join % sql_dic
            SQL_group_by = SQL_group_by % sql_dic
            sql_dic[u"qrycart"] = SQL_cartesian_join
            sql_dic[u"qrygrouped"] = SQL_group_by
            SQL_get_raw_data = """SELECT %(fld_chart_by)s, %(fld_gp_by)s,
                    CASE WHEN measure IS NULL THEN 0 ELSE measure END AS val
                FROM (%(qrycart)s) AS qrycart LEFT JOIN (%(qrygrouped)s) 
                    AS qrygrouped
                USING(%(fld_chart_by)s, %(fld_gp_by)s)
                ORDER BY %(fld_chart_by)s, %(fld_gp_by)s""" % sql_dic
    else: # no series grouping
        # the x vals, and the y vals
        if measure == mg.CHART_FREQS:
            # group by measure field only, count non-missing vals
            SQL_get_raw_data = (u"""SELECT %(fld_measure)s, 
                    COUNT(*) AS measure
                FROM %(tbl)s
                WHERE %(fld_measure)s IS NOT NULL %(and_tbl_filt)s
                GROUP BY %(fld_measure)s
                ORDER BY %(fld_measure)s""") % sql_dic
        elif measure == mg.CHART_AVGS:
            # group by group by field, and get AVG of measure field
            SQL_get_raw_data = (u"""SELECT %(fld_gp_by)s,
                    AVG(%(fld_measure)s) AS measure
                FROM %(tbl)s
                WHERE %(fld_measure)s IS NOT NULL 
                    AND %(fld_gp_by)s IS NOT NULL 
                    %(and_tbl_filt)s
                GROUP BY %(fld_gp_by)s
                ORDER BY %(fld_gp_by)s""") % sql_dic           
    return SQL_get_raw_data

def get_sorted_xaxis_and_y_vals(sort_opt, vals_etc_lst):
    """
    Sort in place then iterate and build new lists with guaranteed 
        synchronisation.
    """
    lib.sort_value_lbls(sort_opt, vals_etc_lst, idx_measure=1, idx_lbl=2)
    sorted_xaxis_dets = []
    sorted_y_vals = []
    for val, measure, lbl, lbl_split in vals_etc_lst:
        sorted_xaxis_dets.append((val, lbl, lbl_split))
        sorted_y_vals.append(measure)
    return sorted_xaxis_dets, sorted_y_vals

def structure_data(chart_type, raw_data, max_items, xlblsdic, fld_gp_by, 
                   fld_chart_by, fld_chart_by_name, 
                   legend_fld_name, legend_fld_lbls,
                   chart_fld_name, chart_fld_lbls, sort_opt, dp):
    """
    Take raw columns of data from SQL cursor and create required dict.
    """
    n_cols = len(raw_data[0])
    multi_series = (n_cols > 2)
    if multi_series: # whether multichart or multiple series within a chart
        """
        Must be sorted by first two so groups and y_vals in order. Apply any 
            sorting before iterating through.
        e.g. raw_data = [(1,1,56),
                         (1,2,103),
                         (1,3,72),
                         (1,4,40),
                         (2,1,13),
                         (2,2,59),
                         (2,3,200),
                         (2,4,0),]
        """
        max_lbl_len = 0
        series_dets = []
        multichart = (fld_chart_by is not None 
                      and chart_type not in mg.NO_CHART_BY)
        first_group = True
        prev_group_val = None
        for group_val, x_val, y_val in raw_data:
            same_group = (group_val == prev_group_val)
            if not same_group:
                first_group = (prev_group_val is None)
                if not first_group: # save previous one
                    (sorted_xaxis_dets, 
                     sorted_y_vals) = get_sorted_xaxis_and_y_vals(sort_opt,
                                                                  vals_etc_lst)
                    series_dets.append({mg.CHART_LBL: chart_lbl,
                                        mg.CHART_LEGEND_LBL: legend_lbl, 
                                        mg.CHART_MULTICHART: multichart,
                                        mg.CHART_XAXIS_DETS: sorted_xaxis_dets,
                                        mg.CHART_Y_VALS: sorted_y_vals})
                vals_etc_lst = [] # reinit
                if multichart:
                    chart_lbl = u"%s: %s" % (chart_fld_name, 
                                             chart_fld_lbls.get(group_val, 
                                                            unicode(group_val)))
                    legend_lbl = legend_fld_name
                else:
                    chart_lbl = mg.CHART_LBL_SINGLE_CHART
                    legend_lbl = legend_fld_lbls.get(group_val, 
                                                     unicode(group_val))
                if len(series_dets) > mg.MAX_CHART_SERIES:
                    if fld_chart_by:
                        raise my_exceptions.TooManyChartsInSeries(
                                                    fld_chart_by_name,
                                                    mg.CHART_MAX_CHARTS_IN_SET)
                    else:
                        raise my_exceptions.TooManySeriesInChart(
                                                        mg.MAX_CHART_SERIES)
            # depending on sorting, may need one per chart.
            x_val_lbl = xlblsdic.get(x_val, unicode(x_val))
            x_val_split_lbl = lib.get_lbls_in_lines(orig_txt=x_val_lbl, 
                                                    max_width=17, dojo=True)
            if len(x_val_lbl) > max_lbl_len:
                max_lbl_len = len(x_val_lbl)
            vals_etc_lst.append((x_val, round(y_val, dp), x_val_lbl, 
                                 x_val_split_lbl))
            if len(vals_etc_lst) > max_items:
                raise my_exceptions.TooManyValsInChartSeries(fld_measure, 
                                                             max_items)
            if (chart_type == mg.PIE_CHART 
                    and len(vals_etc_lst) > mg.MAX_PIE_SLICES):
                raise my_exceptions.TooManySlicesInPieChart
            prev_group_val = group_val
        # save last one across
        (sorted_xaxis_dets, 
         sorted_y_vals) = get_sorted_xaxis_and_y_vals(sort_opt, vals_etc_lst)
        series_dets.append({mg.CHART_LBL: chart_lbl,
                            mg.CHART_LEGEND_LBL: legend_lbl,
                            mg.CHART_MULTICHART: multichart,
                            mg.CHART_XAXIS_DETS: sorted_xaxis_dets,
                            mg.CHART_Y_VALS: sorted_y_vals})
    else: # single series
        """
        Must be sorted by first column.
        e.g. raw_data = [(1,56),
                         (2,103),
                         (3,72),
                         (4,40),]
        """
        vals_etc_lst = []
        max_lbl_len = 0
        for x_val, y_val in raw_data:
            x_val_lbl = xlblsdic.get(x_val, unicode(x_val))
            x_val_split_lbl = lib.get_lbls_in_lines(orig_txt=x_val_lbl, 
                                                    max_width=17, dojo=True)
            if len(x_val_lbl) > max_lbl_len:
                max_lbl_len = len(x_val_lbl)
            vals_etc_lst.append((x_val, round(y_val, dp), x_val_lbl, 
                                 x_val_split_lbl))
            if len(vals_etc_lst) > max_items:
                raise my_exceptions.TooManyValsInChartSeries(fld_measure, 
                                                             max_items)
        chart_lbl = mg.CHART_LBL_SINGLE_CHART
        legend_lbl = legend_fld_name
        (sorted_xaxis_dets, 
         sorted_y_vals) = get_sorted_xaxis_and_y_vals(sort_opt, vals_etc_lst)
        series_dets = [{mg.CHART_LBL: chart_lbl,
                        mg.CHART_LEGEND_LBL: legend_lbl, 
                        mg.CHART_MULTICHART: False,
                        mg.CHART_XAXIS_DETS: sorted_xaxis_dets,
                        mg.CHART_Y_VALS: sorted_y_vals}]
    """
    Each series (possibly only one) has a chart lbl (possibly not used), a
        legend lbl, an xaxis_dets (may vary according to sorting used) 
        and y vals.
    """
    chart_dets = {mg.CHART_MAX_LBL_LEN: max_lbl_len,
                  mg.CHART_SERIES_DETS: series_dets}
    return chart_dets

def get_chart_dets(chart_type, dbe, cur, tbl, tbl_filt, 
                   fld_measure, fld_measure_name, fld_measure_lbls, 
                   fld_gp_by, fld_gp_by_name, fld_gp_by_lbls,
                   fld_chart_by, fld_chart_by_name, fld_chart_by_lbls, 
                   sort_opt, measure):
    """
    Returns some overall details for the chart plus series details (only the
        one series in some cases).
    Only at most one grouping variable - either group by (e.g. clustered bar 
        charts) or chart by (e.g. pie charts). May be neither.
    """
    debug = False
    # misc setup
    max_items = 150 if chart_type == mg.CLUSTERED_BARCHART else 300
    tbl_quoted = getdata.tblname_qtr(dbe, tbl)
    where_tbl_filt, and_tbl_filt = lib.get_tbl_filts(tbl_filt)
    xlblsdic = fld_measure_lbls if measure == mg.CHART_FREQS else fld_gp_by_lbls
    # validate fields supplied (or not)
    # check fld_gp_by and fld_chart_by are present as required
    if chart_type == mg.CLUSTERED_BARCHART:
        if fld_gp_by is None:
            raise Exception(u"%ss must have a field set to cluster by" 
                            % chart_type)
    if measure == mg.CHART_AVGS and fld_gp_by is None:
            raise Exception(u"%ss reporting averages must have a field "
                            u"set to group by" % chart_type)
    if (chart_type == mg.CLUSTERED_BARCHART and measure == mg.CHART_AVGS 
            and fld_chart_by is None):
        raise Exception(u"%ss must have a field set to cluster by if "
                        u"charting averages" 
                        % chart_type)
    # more setup and validation according to measure type and fields completed
    if measure == mg.CHART_FREQS:
        if not (fld_gp_by is None or fld_chart_by is None):
            raise Exception(u"SOFA doesn't have any charts reporting frequency "
                            u"with both the group by and chart by fields set.")
        dp = 0
        # set up legend and chart by names and labels
        # Either gp by or chart by
        if fld_gp_by is not None: # has BY
            fld_group_series = fld_gp_by
            legend_fld_name = fld_gp_by_name # e.g. Country
            legend_fld_lbls = fld_gp_by_lbls # e.g. {1: Japan, ...}
            chart_fld_name = mg.CHART_LBL_SINGLE_CHART
            chart_fld_lbls = {}
        elif fld_chart_by is not None: # CHARTS BY
            fld_group_series = fld_chart_by
            legend_fld_name = fld_measure_name # e.g. Country in orange box
            legend_fld_lbls = fld_measure_lbls
            chart_fld_name = fld_chart_by_name
            chart_fld_lbls = fld_chart_by_lbls
        else: # e.g. simple bar chart without a chart by selected
            fld_group_series = None
            legend_fld_name = fld_measure_name # e.g. Age Group in box
            legend_fld_lbls = {}
            chart_fld_name = mg.CHART_LBL_SINGLE_CHART # won't show
            chart_fld_lbls = {}
    elif measure == mg.CHART_AVGS:
        """
        May or may not have fld_chart_by set but must have fld_gp_by to enable 
            averaging of fld_measure.
        """
        dp = 2
        # in examples, age is measure, country is gp by, and gender is chart by
        if fld_chart_by is not None:
            fld_group_series = fld_chart_by
            """
            NB for line charts and clustered bar charts, not actually new 
                charts if chart_by.
            """
            if chart_type in mg.NO_CHART_BY:
                legend_fld_name = fld_chart_by_name # e.g. Age Group in orange box
                legend_fld_lbls = fld_chart_by_lbls
                chart_fld_name = mg.CHART_LBL_SINGLE_CHART
                chart_fld_lbls = {}
            else:
                legend_fld_name = fld_gp_by_name # e.g. Age Group in orange box
                legend_fld_lbls = {}
                chart_fld_name = fld_chart_by_name 
                chart_fld_lbls = fld_chart_by_lbls
        else:
            fld_group_series = None
            legend_fld_name = fld_gp_by_name # e.g. Country in orange box
            legend_fld_lbls = {}
            chart_fld_name = mg.CHART_LBL_SINGLE_CHART
            chart_fld_lbls = {}
    # Get data as per setup
    SQL_raw_data = get_SQL_raw_data(dbe, tbl_quoted, 
                                    where_tbl_filt, and_tbl_filt, 
                                    measure, fld_measure, 
                                    fld_gp_by, fld_chart_by, fld_group_series)
    if debug: print(SQL_raw_data)
    cur.execute(SQL_raw_data)
    raw_data = cur.fetchall()
    if debug: print(raw_data)
    if not raw_data:
        raise my_exceptions.TooFewValsForDisplay
    # restructure and return data
    chart_dets = structure_data(chart_type, raw_data, max_items, xlblsdic, 
                                fld_gp_by, 
                                fld_chart_by, fld_chart_by_name, 
                                legend_fld_name, legend_fld_lbls,
                                chart_fld_name, chart_fld_lbls, 
                                sort_opt, dp)
    return chart_dets

def get_boxplot_dets(dbe, cur, tbl, tbl_filt, fld_measure, fld_measure_name, 
                     fld_gp_by, fld_gp_by_name, fld_gp_by_lbls, 
                     fld_chart_by, fld_chart_by_name, fld_chart_by_lbls):
    """
    NB can't just use group by SQL to get results - need upper and lower 
        quartiles etc and we have to work on the raw values to achieve this. We
        have to do more work outside of SQL to get the values we need.
    chart_by is really series_by in the case of boxplots but it is easier to 
        use the term used throughout the rest of the code as the outer loop and
        gp_by as the inner loop.
    xaxis_dets -- [(0, "", ""), (1, "Under 20", ...] NB blanks either end
    series_dets -- [{mg.CHART_SERIES_LBL: "Girls", 
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
    """
    debug = False
    dd = getdata.get_dd()
    objqtr = getdata.get_obj_quoter_func(dbe)
    where_tbl_filt, and_tbl_filt = lib.get_tbl_filts(tbl_filt)
    boxplot_width = 0.25
    chart_dets = []
    # get all fld_chart_by_vals where an x_val but OK to be missing a measure 
        # (box will be missing in series)
    xaxis_dets = [] # (0, u"''", u"''")]
    max_lbl_len = 0
    sql_dic = {mg.FLD_CHART_BY: objqtr(fld_chart_by), 
               mg.FLD_GROUP_BY: objqtr(fld_gp_by), 
               u"fld_measure": objqtr(fld_measure),
               u"where_tbl_filt": where_tbl_filt, 
               u"and_tbl_filt": and_tbl_filt, 
               u"tbl": getdata.tblname_qtr(dbe, tbl)}
    if fld_chart_by: # must have gp_by as well but measure optional
        SQL_fld_chart_by_vals = u"""SELECT %(fld_chart_by)s 
            FROM %(tbl)s 
            WHERE %(fld_gp_by)s IS NOT NULL %(and_tbl_filt)s 
            GROUP BY %(fld_chart_by)s""" % sql_dic
        if debug: print(SQL_fld_chart_by_vals)
        cur.execute(SQL_fld_chart_by_vals)
        fld_chart_by_vals = [x[0] for x in cur.fetchall()]
        if len(fld_chart_by_vals) > mg.CHART_MAX_SERIES_IN_BOXPLOT:
            raise my_exceptions.TooManySeriesInChart( 
                                    max_items=mg.CHART_MAX_SERIES_IN_BOXPLOT)
    else:
        fld_chart_by_vals = [None,] # Got to have something to loop through ;-)
    ymin = 0 # init
    ymax = 0
    first_chart_by = True
    any_missing_boxes = False
    for fld_chart_by_val in fld_chart_by_vals: # e.g. "Boys" and "Girls"
        # set up series (chart by) filter and 
        if fld_chart_by:
            filt = getdata.make_fld_val_clause(dbe, dd.flds, 
                                               fld_name=fld_chart_by, 
                                               val=fld_chart_by_val)
            and_fld_chart_by_filt = u" AND %s" % filt
            if where_tbl_filt:
                comb_filt = u"%s AND %s" % (where_tbl_filt , filt)
            else:
                comb_filt = u"WHERE %s" % filt
            sql_dic[u"comb_filt"] = comb_filt
            SQL_gp_vals = u"""SELECT %(fld_gp_by)s 
                FROM %(tbl)s 
                %(comb_filt)s 
                GROUP BY %(fld_gp_by)s""" % sql_dic
            legend_lbl = fld_chart_by_lbls.get(fld_chart_by_val, 
                                               unicode(fld_chart_by_val))
        else:
            and_fld_chart_by_filt = u""
            SQL_gp_vals = u"""SELECT %(fld_gp_by)s 
                FROM %(tbl)s 
                %(where_tbl_filt)s 
                GROUP BY %(fld_gp_by)s""" % sql_dic
            legend_lbl = fld_gp_by_name
        sql_dic[u"and_fld_chart_by_filt"] = and_fld_chart_by_filt
        if debug: print(SQL_gp_vals)
        cur.execute(SQL_gp_vals)
        gp_by_vals = [x[0] for x in cur.fetchall()]
        if len(gp_by_vals) > mg.CHART_MAX_BOXPLOTS_IN_SERIES:
            raise my_exceptions.TooManyBoxplotsInSeries(fld_gp_by_name, 
                                max_items=mg.CHART_MAX_BOXPLOTS_IN_SERIES)            
        # time to get the boxplot information for the series
        boxdet_series = []
        for i, gp_val in enumerate(gp_by_vals, 1): # e.g. "Mt Albert Grammar", 
                # "Epsom Girls Grammar", "Hebron Christian College", ...
            if first_chart_by: # build xaxis_dets once
                x_val_lbl = fld_gp_by_lbls.get(gp_val, unicode(gp_val))
                x_val_split_lbl = lib.get_lbls_in_lines(orig_txt=x_val_lbl, 
                                                        max_width=17, dojo=True)
                if len(x_val_lbl) > max_lbl_len:
                    max_lbl_len = len(x_val_lbl)
                xaxis_dets.append((i, x_val_lbl, x_val_split_lbl))
            # Now see if any measure values with series_by_val and gp_val
            # Apply tbl_filt, series_by filt, and gp_by filt
            gp_by_filt = getdata.make_fld_val_clause(dbe, dd.flds, 
                                                     fld_name=fld_gp_by, 
                                                     val=gp_val)
            sql_dic[u"gp_by_filt"] = gp_by_filt
            SQL_measure_vals = u"""SELECT %(fld_measure)s
                FROM %(tbl)s
                WHERE %(gp_by_filt)s
                %(and_fld_chart_by_filt)s
                ORDER BY %(fld_measure)s""" % sql_dic
            cur.execute(SQL_measure_vals)
            measure_vals = [x[0] for x in cur.fetchall()]
            boxplot_display = (len(measure_vals) > 
                               mg.CHART_MIN_DISPLAY_VALS_FOR_BOXPLOT)
            if not boxplot_display:
                any_missing_boxes = True
            # This is bound to be really inefficient - optimise one day?
            lbox = core_stats.scoreatpercentile(measure_vals, percent=25.0)
            median = core_stats.scoreatpercentile(measure_vals, percent=50.0)
            ubox = core_stats.scoreatpercentile(measure_vals, percent=75.0)
            iqr = ubox-median
            raw_lwhisker = lbox - (1.5*iqr)
            # wrap up to next value
            for val in measure_vals:
                if val > raw_lwhisker:
                    lwhisker = val
                    break
            min_measure = min(measure_vals)
            if min_measure < ymin:
                ymin = min_measure            
            raw_uwhisker = ubox + (1.5*iqr)
            # wrap down to next value
            measure_vals.reverse()
            for val in measure_vals:
                if val < raw_uwhisker:
                    uwhisker = val
                    break
            max_measure = max(measure_vals)
            if max_measure > ymax:
                ymax = max_measure
            outliers = [round(x, 2) for x in measure_vals 
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
        series_dic = {mg.CHART_SERIES_LBL: legend_lbl, 
                      mg.CHART_BOXDETS: boxdet_series}
        chart_dets.append(series_dic)
        first_chart_by = False
    xmin = 0.5
    xmax = i+0.5
    ymax *=1.1
    xaxis_dets.append((xmax, u"''", u"''"))
    if debug: print(xaxis_dets)
    return (xaxis_dets, xmin, xmax, ymin, ymax, max_lbl_len, chart_dets, 
            any_missing_boxes)

def get_histo_dets(dbe, cur, tbl, tbl_filt, fld_measure,
                   fld_chart_by, fld_chart_by_name, fld_chart_by_lbls):
    """
    Make separate db call each histogram. Getting all values anyway and don't 
        want to store in memory.
    Return list of dicts - one for each histogram. Each contains: 
        CHART_XAXIS_DETS, CHART_Y_VALS, CHART_MINVAL, CHART_MAXVAL, 
        CHART_BIN_LBLS.
    xaxis_dets -- [(1, u""), (2: u"", ...]
    y_vals -- [0.091, ...]
    bin_labels -- [u"1 to under 2", u"2 to under 3", ...]
    """
    debug = False
    dd = getdata.get_dd()
    objqtr = getdata.get_obj_quoter_func(dbe)
    unused, and_tbl_filt = lib.get_tbl_filts(tbl_filt)
    sql_dic = {mg.FLD_CHART_BY: objqtr(fld_chart_by), 
               u"fld_measure": objqtr(fld_measure),
               u"and_tbl_filt": and_tbl_filt, 
               u"tbl": getdata.tblname_qtr(dbe, tbl)}
    if fld_chart_by:
        SQL_fld_chart_by_vals = u"""SELECT %(fld_chart_by)s 
            FROM %(tbl)s 
            WHERE %(fld_measure)s IS NOT NULL %(and_tbl_filt)s 
            GROUP BY %(fld_chart_by)s""" % sql_dic
        cur.execute(SQL_fld_chart_by_vals)
        fld_chart_by_vals = [x[0] for x in cur.fetchall()]
        if len(fld_chart_by_vals) > mg.CHART_MAX_CHARTS_IN_SET:
            raise my_exceptions.TooManyChartsInSeries(fld_chart_by_name, 
                                           max_items=mg.CHART_MAX_CHARTS_IN_SET)
    else:
        fld_chart_by_vals = [None,] # Got to have something to loop through ;-)
    histo_dets = []
    for fld_chart_by_val in fld_chart_by_vals:
        if fld_chart_by:
            filt = getdata.make_fld_val_clause(dbe, dd.flds, 
                                               fld_name=fld_chart_by, 
                                               val=fld_chart_by_val)
            and_fld_chart_by_filt = u" and %s" % filt
            fld_chart_by_val_lbl = fld_chart_by_lbls.get(fld_chart_by_val, 
                                                         fld_chart_by_val)
            chart_by_lbl = u"%s: %s" % (fld_chart_by_name, fld_chart_by_val_lbl)
        else:
            and_fld_chart_by_filt = u""
            chart_by_lbl = mg.CHART_LBL_SINGLE_CHART
        sql_dic[u"and_fld_chart_by_filt"] = and_fld_chart_by_filt
        SQL_get_vals = u"""SELECT %(fld_measure)s 
            FROM %(tbl)s
            WHERE %(fld_measure)s IS NOT NULL
                %(and_tbl_filt)s %(and_fld_chart_by_filt)s
            ORDER BY %(fld_measure)s""" % sql_dic
        if debug: print(SQL_get_vals)
        cur.execute(SQL_get_vals)
        vals = [x[0] for x in cur.fetchall()]
        if len(vals) < mg.MIN_HISTO_VALS:
            raise my_exceptions.TooFewValsForDisplay(min_n=mg.MIN_HISTO_VALS)
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
        bin_ranges = [] # needed for labels
        bins = [] # needed to get y vals for normal dist curve
        for y_val in y_vals:
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
        norm_ys = list(lib.get_normal_ys(vals, np.array(bins)))
        sum_yval = sum(y_vals)
        sum_norm_ys = sum(norm_ys)
        norm_multiplier = sum_yval/(1.0*sum_norm_ys)
        norm_ys = [x*norm_multiplier for x in norm_ys]
        if debug: print(minval, maxval, xaxis_dets, y_vals, bin_lbls)
        histo_dic = {mg.CHART_CHART_BY_LBL: chart_by_lbl,
                     mg.CHART_XAXIS_DETS: xaxis_dets,
                     mg.CHART_Y_VALS: y_vals,
                     mg.CHART_NORMAL_Y_VALS: norm_ys,
                     mg.CHART_MINVAL: minval,
                     mg.CHART_MAXVAL: maxval,
                     mg.CHART_BIN_LBLS: bin_lbls}
        histo_dets.append(histo_dic)
    return histo_dets

def get_scatterplot_dets(dbe, cur, tbl, tbl_filt, fld_x_axis, fld_y_axis, 
                         fld_chart_by, fld_chart_by_name, fld_chart_by_lbls, 
                         unique=True):
    """
    unique -- unique x-y pairs only
    """
    debug = False
    dd = getdata.get_dd()
    objqtr = getdata.get_obj_quoter_func(dbe)
    unused, and_tbl_filt = lib.get_tbl_filts(tbl_filt)
    sql_dic = {mg.FLD_CHART_BY: objqtr(fld_chart_by),
               u"fld_x_axis": objqtr(fld_x_axis),
               u"fld_y_axis": objqtr(fld_y_axis),
               u"tbl": getdata.tblname_qtr(dbe, tbl), 
               u"and_tbl_filt": and_tbl_filt}
    if fld_chart_by:
        SQL_fld_chart_by_vals = u"""SELECT %(fld_chart_by)s 
            FROM %(tbl)s 
            WHERE %(fld_x_axis)s IS NOT NULL AND %(fld_y_axis)s IS NOT NULL  
            %(and_tbl_filt)s 
            GROUP BY %(fld_chart_by)s""" % sql_dic
        cur.execute(SQL_fld_chart_by_vals)
        fld_chart_by_vals = [x[0] for x in cur.fetchall()]
        if len(fld_chart_by_vals) > mg.CHART_MAX_CHARTS_IN_SET:
            raise my_exceptions.TooManyChartsInSeries(fld_chart_by_name, 
                                           max_items=mg.CHART_MAX_CHARTS_IN_SET)
        elif len(fld_chart_by_vals) == 0:
            raise my_exceptions.TooFewValsForDisplay
    else:
        fld_chart_by_vals = [None,] # Got to have something to loop through ;-)
    scatterplot_dets = []
    for fld_chart_by_val in fld_chart_by_vals:
        if fld_chart_by:
            filt = getdata.make_fld_val_clause(dbe, dd.flds, 
                                               fld_name=fld_chart_by, 
                                               val=fld_chart_by_val)
            and_fld_chart_by_filt = u" and %s" % filt
            fld_chart_by_val_lbl = fld_chart_by_lbls.get(fld_chart_by_val, 
                                                         fld_chart_by_val)
            chart_by_lbl = u"%s: %s" % (fld_chart_by_name, fld_chart_by_val_lbl)
        else:
            and_fld_chart_by_filt = u""
            chart_by_lbl = mg.CHART_LBL_SINGLE_CHART
        sql_dic[u"and_fld_chart_by_filt"] = and_fld_chart_by_filt
        if unique:
            SQL_get_pairs = u"""SELECT %(fld_x_axis)s, %(fld_y_axis)s
                    FROM %(tbl)s
                    WHERE %(fld_x_axis)s IS NOT NULL
                    AND %(fld_y_axis)s IS NOT NULL 
                    %(and_fld_chart_by_filt)s
                    %(and_tbl_filt)s
                    GROUP BY %(fld_x_axis)s, %(fld_y_axis)s""" % sql_dic
        else:
            SQL_get_pairs = u"""SELECT %(fld_x_axis)s, %(fld_y_axis)s
                    FROM %(tbl)s
                    WHERE %(fld_x_axis)s IS NOT NULL
                    AND %(fld_y_axis)s IS NOT NULL 
                    %(and_fld_chart_by_filt)s
                    %(and_tbl_filt)s""" % sql_dic
        if debug: print(SQL_get_pairs)
        cur.execute(SQL_get_pairs)
        data_tups = cur.fetchall()
        if not fld_chart_by:
            if not data_tups:
                raise my_exceptions.TooFewValsForDisplay
        lst_x = [x[0] for x in data_tups]
        lst_y = [x[1] for x in data_tups]
        if debug: print(chart_by_lbl)
        scatterplot_dic = {mg.CHART_CHART_BY_LBL: chart_by_lbl,
                           mg.LIST_X: lst_x, mg.LIST_Y: lst_y,
                           mg.DATA_TUPS: data_tups,}
        scatterplot_dets.append(scatterplot_dic)
    return scatterplot_dets

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

def get_barchart_sizings(n_clusters, n_bars_in_cluster):
    debug = False
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
        width = 900
        xgap = 6
    elif n_clusters <= 16:
        minor_ticks = u"true"
        xfontsize = 7
        width = 1000
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
    left_axis_lbl_shift = 20 if width > 1200 else 10 # gets squeezed 
        # out otherwise
    if debug: print(width, xgap, xfontsize, minor_ticks, left_axis_lbl_shift)
    return width, xgap, xfontsize, minor_ticks, left_axis_lbl_shift

def get_linechart_sizings(xaxis_dets, max_lbl_len, series_dets):
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
        if max_lbl_len > 10:
            width += 2000
        elif max_lbl_len > 7:
            width += 1500
        elif max_lbl_len > 4:
            width += 1000
    if debug: print(width, xfontsize, minor_ticks, micro_ticks)
    return width, xfontsize, minor_ticks, micro_ticks

def get_boxplot_sizings(xaxis_dets, max_lbl_len, series_dets):
    debug = False
    minor_ticks = u"false"
    n_vals = len(xaxis_dets)
    n_series = len(series_dets)
    n_boxes = n_vals*n_series
    if n_vals < 6:
        width = 400
    elif n_vals < 10:
        width = 500
    elif n_vals < 13:
        minor_ticks = u"true"
        width = 700
    elif n_vals < 15:
        minor_ticks = u"true"
        width = 900
    else:
        minor_ticks = u"true"
        width = 1500
    if n_series > 2:
        width += (n_series*80)
    xfontsize = 11
    if n_vals > 5:
        xfontsize = 10
    elif n_vals > 10:
        xfontsize = 9
    if max_lbl_len > 14:
        width *= 1.5
        xfontsize *= 0.9
    if max_lbl_len > 10:
        width *= 1.3
        xfontsize *= 0.95
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

def get_lbl_dets(xaxis_dets):
    lbl_dets = []
    for i, xaxis_det in enumerate(xaxis_dets, 1):
        val_lbl = xaxis_det[2] # the split variant of the label
        lbl_dets.append(u"{value: %s, text: %s}" % (i, val_lbl))
    return lbl_dets

def get_left_axis_shift(xaxis_dets):
    """
    Need to shift margin left if wide labels to keep y-axis title close enough 
        to y_axis labels.
    """
    debug = False
    left_axis_lbl_shift = 0
    try:
        label1_len = len(xaxis_dets[0][1])
        if label1_len > 5:
            left_axis_lbl_shift = label1_len*-1.3
    except Exception, e:
        pass
    if debug: print(left_axis_lbl_shift)
    return left_axis_lbl_shift

def is_multichart(chart_dets):
    if len(chart_dets) > 1:
        multichart = True
    elif len(chart_dets) == 1:
        # might be only one field group value - still needs indiv chart title
        multichart = (chart_dets[0][mg.CHART_CHART_BY_LBL] !=
                      mg.CHART_LBL_SINGLE_CHART) 
    else:
        multichart = False
    return multichart

def simple_barchart_output(titles, subtitles, x_title, y_title, chart_dets, 
                           inc_perc, css_idx, css_fil, page_break_after):
    """
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    chart_dets --         
        
    If chart by, multiple xaxis_dets so we can have sort order by freq etc 
        which will vary by chart.
    Each series (possibly only one) has a chart lbl (possibly not used), a
        legend lbl, and y vals.
    chart_dets = {mg.CHART_MAX_LBL_LEN: ...,
                  mg.CHART_SERIES_DETS: see below}
                  series_dets = [{mg.CHART_LBL: ...,
                                  mg.CHART_LEGEND_LBL: ..., 
                                  mg.CHART_MULTICHART: ...,
                                  mg.CHART_XAXIS_DETS: ...,
                                  mg.CHART_Y_VALS: ...}]
    var_numeric -- needs to be quoted or not.
    xaxis_dets -- [(1, "Under 20"), (2, "20-29"), (3, "30-39"), (4, "40-64"),
                   (5, "65+")]
    css_idx -- css index so can apply appropriate css styles
    """
    debug = False
    html = []
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                          css_idx)
    title_dets_html = get_title_dets_html(titles, subtitles, css_idx)
    html.append(title_dets_html)
    multichart = chart_dets[mg.CHART_SERIES_DETS][0][mg.CHART_MULTICHART]
    axis_lbl_drop = 30 if x_title else 10
    if multichart:
        axis_lbl_drop = axis_lbl_drop*0.8
    height = 310 + axis_lbl_drop # compensate for loss of bar display height
    inc_perc_js = u"true" if inc_perc else u"false"
    """
    For each series, set colour details.
    For the collection of series as a whole, set the highlight mapping from 
        each series colour.
    From dojox.charting.action2d.Highlight but with extraneous % removed
    """
    (outer_bg, grid_bg, axis_lbl_font_colour, major_gridline_colour, 
            gridline_width, stroke_width, tooltip_border_colour, 
            colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
    try:
        fill = colour_mappings[0][0]
    except IndexError, e:
        fill = mg.DOJO_COLOURS[0]
    outer_bg = u"" if outer_bg == u"" \
        else u"chartconf[\"outerBg\"] = \"%s\";" % outer_bg
    single_colour = True
    override_first_highlight = (css_fil == mg.DEFAULT_CSS_PATH 
                                and single_colour)
    colour_cases = setup_highlights(colour_mappings, single_colour, 
                                    override_first_highlight)
    n_bars_in_cluster = 1
    # always the same number, irrespective of order
    n_clusters = len(chart_dets[mg.CHART_SERIES_DETS][0][mg.CHART_XAXIS_DETS])
    (width, xgap, xfontsize, minor_ticks, 
        left_axis_lbl_shift) = get_barchart_sizings(n_clusters, 
                                                      n_bars_in_cluster)
    if multichart:
        width = width*0.8
        xgap = xgap*0.8
        xfontsize = xfontsize*0.8
        left_axis_lbl_shift = left_axis_lbl_shift + 20
    for (chart_idx, 
         series_det) in enumerate(chart_dets[mg.CHART_SERIES_DETS]):
        xaxis_dets = series_det[mg.CHART_XAXIS_DETS]
        lbl_dets = get_lbl_dets(xaxis_dets)
        xaxis_lbls = u"[" + u",\n            ".join(lbl_dets) + u"]"
        pagebreak = u"" if chart_idx % 2 == 0 \
                        else u"page-break-after: always;"
        indiv_bar_title = "<p><b>%s</b></p>" % series_det[mg.CHART_LBL]
        # build js for every series
        series_js_list = []
        series_names_list = []
        if debug: print(series_dets)
        series_names_list.append(u"series%s" % chart_idx)
        series_js_list.append(u"var series%s = new Array();" % chart_idx)
        series_js_list.append(u"series%s[\"seriesLabel\"] = \"%s\";"
                             % (chart_idx, series_det[mg.CHART_LEGEND_LBL]))
        series_js_list.append(u"series%s[\"yVals\"] = %s;" % 
                              (chart_idx, series_det[mg.CHART_Y_VALS]))
        series_js_list.append(u"series%s[\"style\"] = "
            u"{stroke: {color: \"white\", width: \"%spx\"}, fill: \"%s\"};"
            % (chart_idx, stroke_width, fill))
        series_js_list.append(u"")
        series_js = u"\n    ".join(series_js_list)\
                        
        series_js += u"\nvar series = new Array(%s);" \
                     % u", ".join(series_names_list)
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
    chartconf["leftAxisLabelShift"] = %(left_axis_lbl_shift)s;
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
</div>""" % {u"colour_cases": colour_cases,
               u"series_js": series_js, u"xaxis_lbls": xaxis_lbls, 
               u"width": width, u"height": height, u"xgap": xgap, 
               u"xfontsize": xfontsize, u"indiv_bar_title": indiv_bar_title,
               u"axis_lbl_font_colour": axis_lbl_font_colour,
               u"major_gridline_colour": major_gridline_colour,
               u"gridline_width": gridline_width, 
               u"axis_lbl_drop": axis_lbl_drop,
               u"left_axis_lbl_shift": left_axis_lbl_shift,
               u"x_title": x_title, u"y_title": y_title,
               u"tooltip_border_colour": tooltip_border_colour, 
               u"inc_perc_js": inc_perc_js, 
               u"connector_style": connector_style, 
               u"outer_bg": outer_bg,  u"pagebreak": pagebreak,
               u"chart_idx": u"%02d" % chart_idx,
               u"grid_bg": grid_bg, u"minor_ticks": minor_ticks})
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

def clustered_barchart_output(titles, subtitles, x_title, y_title, chart_dets, 
                              inc_perc, css_idx, css_fil, page_break_after):
    """
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    chart_dets --         
        
    Even though one xaxis_dets per series, only one is needed for a clustered
        bar chart ad it will fit all series.
    Each series (possibly only one) has a chart lbl (possibly not used), a
        legend lbl, xaxis_dets, and y vals.
    chart_dets = {mg.CHART_MAX_LBL_LEN: ...,
                  mg.CHART_SERIES_DETS: see below}
                  series_dets = [{mg.CHART_LBL: ...,
                                  mg.CHART_LEGEND_LBL: ..., 
                                  mg.CHART_MULTICHART: ...,
                                  mg.CHART_XAXIS_DETS: ...,
                                  mg.CHART_Y_VALS: ...}]
    var_numeric -- needs to be quoted or not.
    xaxis_dets -- [(1, "Under 20"), (2, "20-29"), (3, "30-39"), (4, "40-64"),
                   (5, "65+")]
    css_idx -- css index so can apply appropriate css styles
    """
    debug = False
    html = []
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    title_dets_html = get_title_dets_html(titles, subtitles, css_idx)
    html.append(title_dets_html)
    multichart = False
    axis_lbl_drop = 30 if x_title else 10
    height = 310 + axis_lbl_drop # compensate for loss of bar display height
    inc_perc_js = u"true" if inc_perc else u"false"
    """
    For each series, set colour details.
    For the collection of series as a whole, set the highlight mapping from 
        each series colour.
    From dojox.charting.action2d.Highlight but with extraneous % removed
    """
    (outer_bg, grid_bg, axis_lbl_font_colour, major_gridline_colour, 
            gridline_width, stroke_width, tooltip_border_colour, 
            colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
    outer_bg = u"" if outer_bg == u"" \
        else u"chartconf[\"outerBg\"] = \"%s\";" % outer_bg
    xaxis_dets = chart_dets[mg.CHART_SERIES_DETS][0][mg.CHART_XAXIS_DETS]
    lbl_dets = get_lbl_dets(xaxis_dets)
    xaxis_lbls = u"[" + u",\n            ".join(lbl_dets) + u"]"
    series_dets = chart_dets[mg.CHART_SERIES_DETS]
    n_bars_in_cluster = len(series_dets)
    n_clusters = len(xaxis_dets)
    (width, xgap, xfontsize, minor_ticks, 
     left_axis_lbl_shift) = get_barchart_sizings(n_clusters, n_bars_in_cluster)
    single_colour = (len(series_dets) == 1)
    override_first_highlight = (css_fil == mg.DEFAULT_CSS_PATH 
                                and single_colour)
    colour_cases = setup_highlights(colour_mappings, single_colour, 
                                    override_first_highlight)
    series_js_list = []
    series_names_list = []
    if debug: print(series_dets)
    for i, series_det in enumerate(series_dets):
        series_names_list.append(u"series%s" % i)
        series_js_list.append(u"var series%s = new Array();" % i)
        series_js_list.append(u"series%s[\"seriesLabel\"] = \"%s\";"
                              % (i, series_det[mg.CHART_LEGEND_LBL]))
        series_js_list.append(u"series%s[\"yVals\"] = %s;" % 
                              (i, series_det[mg.CHART_Y_VALS]))
        try:
            fill = colour_mappings[i][0]
        except IndexError, e:
            fill = mg.DOJO_COLOURS[i]
        series_js_list.append(u"series%s[\"style\"] = "
            u"{stroke: {color: \"white\", width: \"%spx\"}, fill: \"%s\"};"
            % (i, stroke_width, fill))
        series_js_list.append(u"")
    series_js = u"\n    ".join(series_js_list)
    series_js += u"\n    var series = new Array(%s);" % \
                                            u", ".join(series_names_list)
    series_js = series_js.lstrip()
    html.append(u"""
<script type="text/javascript">

var sofaHlRenumber00 = function(colour){
    var hlColour;
    switch (colour.toHex()){
        %(colour_cases)s
        default:
            hlColour = hl(colour.toHex());
            break;
    }
    return new dojox.color.Color(hlColour);
}

makechartRenumber00 = function(){
    %(series_js)s
    var chartconf = new Array();
    chartconf["xaxisLabels"] = %(xaxis_lbls)s;
    chartconf["xgap"] = %(xgap)s;
    chartconf["xfontsize"] = %(xfontsize)s;
    chartconf["sofaHl"] = sofaHlRenumber00;
    chartconf["gridlineWidth"] = %(gridline_width)s;
    chartconf["gridBg"] = \"%(grid_bg)s\";
    chartconf["minorTicks"] = %(minor_ticks)s;
    chartconf["axisLabelFontColour"] = \"%(axis_lbl_font_colour)s\";
    chartconf["majorGridlineColour"] = \"%(major_gridline_colour)s\";
    chartconf["xTitle"] = \"%(x_title)s\";
    chartconf["axisLabelDrop"] = %(axis_lbl_drop)s;
    chartconf["leftAxisLabelShift"] = %(left_axis_lbl_shift)s;
    chartconf["yTitle"] = \"%(y_title)s\";
    chartconf["tooltipBorderColour"] = \"%(tooltip_border_colour)s\";
    chartconf["incPerc"] = %(inc_perc_js)s;
    chartconf["connectorStyle"] = \"%(connector_style)s\";
    %(outer_bg)s
    makeBarChart("mychartRenumber00", series, chartconf);
}
</script>

<div class="screen-float-only" style="margin-right: 10px; ">
<div id="mychartRenumber00" 
    style="width: %(width)spx; height: %(height)spx;">
    </div>
<div id="legendMychartRenumber00">
    </div>
</div>""" % {u"colour_cases": colour_cases,
             u"series_js": series_js, u"xaxis_lbls": xaxis_lbls, 
             u"width": width, u"height": height, u"xgap": xgap, 
             u"xfontsize": xfontsize,
             u"axis_lbl_font_colour": axis_lbl_font_colour,
             u"major_gridline_colour": major_gridline_colour,
             u"gridline_width": gridline_width, 
             u"axis_lbl_drop": axis_lbl_drop,
             u"left_axis_lbl_shift": left_axis_lbl_shift,
             u"x_title": x_title, u"y_title": y_title,
             u"tooltip_border_colour": tooltip_border_colour, 
             u"inc_perc_js": inc_perc_js, u"connector_style": connector_style, 
             u"outer_bg": outer_bg,
             u"grid_bg": grid_bg, u"minor_ticks": minor_ticks})
    html.append(u"""<div style="clear: both;">&nbsp;&nbsp;</div>""")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)

def piechart_output(titles, subtitles, chart_dets, css_fil, css_idx, 
                    page_break_after):
    """
    chart_dets --         
        
    Even though one xaxis_dets per series, only one is needed for a clustered
        bar chart ad it will fit all series.
    Each series (possibly only one) has a chart lbl (possibly not used), a
        legend lbl, xaxis_dets, and y vals.
    chart_dets = {mg.CHART_MAX_LBL_LEN: ...,
                  mg.CHART_SERIES_DETS: see below}
                  series_dets = [{mg.CHART_LBL: ...,
                                  mg.CHART_LEGEND_LBL: ..., 
                                  mg.CHART_MULTICHART: ...,
                                  mg.CHART_XAXIS_DETS: ...,
                                  mg.CHART_Y_VALS: ...}]
    """
    debug = False
    html = []
    if debug: print(pie_chart_dets)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    series_dets = chart_dets[mg.CHART_SERIES_DETS]
    multichart = series_dets[0][mg.CHART_MULTICHART]
    title_dets_html = get_title_dets_html(titles, subtitles, css_idx)
    html.append(title_dets_html)
    width = 500 if mg.PLATFORM == mg.WINDOWS else 450
    if multichart:
        width = width*0.8
    height = 350 if multichart else 400
    radius = 120 if multichart else 140
    lbl_offset = -20 if multichart else -30
    (outer_bg, grid_bg, axis_lbl_font_colour, 
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
    lbl_font_colour = axis_lbl_font_colour
    slice_fontsize = 14 if len(chart_dets) < 10 else 10
    if multichart:
        slice_fontsize = slice_fontsize*0.8
    # one series per chart
    for chart_idx, chart_det in enumerate(series_dets):
        pagebreak = u"" if chart_idx % 2 == 0 else u"page-break-after: always;"
        slices_js_lst = []
        # build indiv slice details for this chart
        y_vals = chart_det[mg.CHART_Y_VALS]
        tot_y_vals = sum(y_vals)
        xy_dets = zip(chart_det[mg.CHART_XAXIS_DETS], y_vals)
        for ((val, val_lbl, split_lbl), y_val) in xy_dets:
            tiplbl = val_lbl.replace(u"\n", u" ") # line breaks mean no display
            tooltip = u"%s<br>%s (%s%%)" % (tiplbl, int(y_val), 
                                            round((100.0*y_val)/tot_y_vals, 1))
            slices_js_lst.append(u"{\"y\": %(y)s, \"text\": %(text)s, " 
                    u"\"tooltip\": \"%(tooltip)s\"}" % 
                    {u"y": y_val, u"text": split_lbl, u"tooltip": tooltip})
        slices_js = u"slices = [" + (u",\n" + u" "*4*4).join(slices_js_lst) + \
                    u"\n];"
        indiv_pie_title = "<p><b>%s</b></p>" % chart_det[mg.CHART_LBL] \
                                                        if multichart else u""
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
%(indiv_pie_title)s
<div id="mychartRenumber%(chart_idx)s" 
    style="width: %(width)spx; height: %(height)spx;">
    </div>
</div>""" % {u"slice_colours": slice_colours, u"colour_cases": colour_cases, 
             u"width": width, u"height": height, u"radius": radius,
             u"lbl_offset": lbl_offset, u"pagebreak": pagebreak,
             u"indiv_pie_title": indiv_pie_title,
             u"slices_js": slices_js, u"slice_fontsize": slice_fontsize, 
             u"lbl_font_colour": lbl_font_colour,
             u"tooltip_border_colour": tooltip_border_colour,
             u"connector_style": connector_style, u"outer_bg": outer_bg, 
             u"grid_bg": grid_bg, u"chart_idx": u"%02d" % chart_idx,
             })
    html.append(u"""<div style="clear: both;">&nbsp;&nbsp;</div>""")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)


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

def linechart_output(titles, subtitles, x_title, y_title, chart_dets, 
                     inc_perc, inc_trend, inc_smooth, 
                     css_fil, css_idx, page_break_after):
    """
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    chart_dets --         
        
    Even though one xaxis_dets per series, only one is needed for a clustered
        bar chart ad it will fit all series.
    Each series (possibly only one) has a chart lbl (possibly not used), a
        legend lbl, xaxis_dets, and y vals.
    chart_dets = {mg.CHART_MAX_LBL_LEN: ...,
                  mg.CHART_SERIES_DETS: see below}
                  series_dets = [{mg.CHART_LBL: ...,
                                  mg.CHART_LEGEND_LBL: ..., 
                                  mg.CHART_MULTICHART: ...,
                                  mg.CHART_XAXIS_DETS: ...,
                                  mg.CHART_Y_VALS: ...}]
    css_idx -- css index so can apply    
    """
    debug = False
    html = []
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    title_dets_html = get_title_dets_html(titles, subtitles, css_idx)
    series_dets = chart_dets[mg.CHART_SERIES_DETS]
    if debug: 
        print(series_dets)
    # For multiple, don't split label if the mid tick (clash with x axis label)
    # NB one xaxis for all lines
    xaxis_dets = series_dets[0][mg.CHART_XAXIS_DETS]
    lbl_dets = get_lbl_dets(xaxis_dets)
    xaxis_lbls = u"[" + u",\n            ".join(lbl_dets) + u"]"
    axis_lbl_drop = 30 if x_title else -10
    height = 310 + axis_lbl_drop # compensate for loss of bar display height
    max_lbl_len = chart_dets[mg.CHART_MAX_LBL_LEN]                 
    (width, xfontsize, 
     minor_ticks, micro_ticks) = get_linechart_sizings(xaxis_dets, 
                                                       max_lbl_len, series_dets)
    left_axis_lbl_shift = 20 if width > 1200 else 10 # gets squeezed 
    inc_perc_js = u"true" if inc_perc else u"false"
    """
    For each series, set colour details.
    For the collection of series as a whole, set the highlight mapping from 
        each series colour.
    From dojox.charting.action2d.Highlight but with extraneous % removed
    """
    (outer_bg, grid_bg, axis_lbl_font_colour, major_gridline_colour, 
            gridline_width, stroke_width, tooltip_border_colour, 
            colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
    # Can't have white for line charts because always a white outer background
    axis_lbl_font_colour = axis_lbl_font_colour \
                            if axis_lbl_font_colour != u"white" else u"black"
    """
    Build js for every series.
    If only one series, and trendlines are selected, make an additional series
        for the trendline.
    """
    series_js_list = []
    series_names_list = []
    series0 = series_dets[0]
    if inc_trend or inc_smooth:
        raw_y_vals = series0[mg.CHART_Y_VALS]
    if inc_trend:
        trend_y_vals = get_trend_y_vals(raw_y_vals)
        # repeat most of it
        trend_series = {mg.CHART_LBL: u'Trend line',
                        mg.CHART_LEGEND_LBL: series0[mg.CHART_LEGEND_LBL], 
                        mg.CHART_MULTICHART: series0[mg.CHART_MULTICHART],
                        mg.CHART_XAXIS_DETS: series0[mg.CHART_XAXIS_DETS],
                        mg.CHART_Y_VALS: trend_y_vals}
        series_dets.append(trend_series)
    if inc_smooth:
        smooth_y_vals = get_smooth_y_vals(raw_y_vals)
        smooth_series = {mg.CHART_LBL: u'Smoothed data line',
                         mg.CHART_LEGEND_LBL: series0[mg.CHART_LEGEND_LBL], 
                         mg.CHART_MULTICHART: series0[mg.CHART_MULTICHART],
                         mg.CHART_XAXIS_DETS: series0[mg.CHART_XAXIS_DETS],
                         mg.CHART_Y_VALS: smooth_y_vals}
        series_dets.append(smooth_series)
    pagebreak = u"page-break-after: always;"
    for i, series_det in enumerate(series_dets):
        series_names_list.append(u"series%s" % i)
        series_js_list.append(u"var series%s = new Array();" % i)
        series_js_list.append(u"series%s[\"seriesLabel\"] = \"%s\";"
                              % (i, series_det[mg.CHART_LEGEND_LBL]))
        series_js_list.append(u"series%s[\"yVals\"] = %s;" % 
                              (i, series_det[mg.CHART_Y_VALS]))
        try:
            stroke = colour_mappings[i][0]
        except IndexError, e:
            stroke = mg.DOJO_COLOURS[i]
        # To set markers explicitly:
        # http://dojotoolkit.org/api/1.5/dojox/charting/Theme/Markers/CIRCLE
        # e.g. marker: dojox.charting.Theme.defaultMarkers.CIRCLE"
        if i == 1 and (inc_trend or inc_smooth) or \
                i == 2 and (inc_trend and inc_smooth):
            # curved has tension and no markers
            # tension has no effect on already straight (trend) line
            plot_style = u", plot: 'curved'"
        else:
            plot_style = u""
        series_js_list.append(u"series%s['style'] = "
            u"{stroke: {color: '%s', width: '6px'} %s };" % (i, stroke, 
                                                             plot_style))
        series_js_list.append(u"")
    series_js = u"\n    ".join(series_js_list)
    series_js += u"\n    var series = new Array(%s);" % \
                                                u", ".join(series_names_list)
    series_js = series_js.lstrip()
    html.append(u"""
<script type="text/javascript">

makechartRenumber00 = function(){
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
    chartconf["leftAxisLabelShift"] = %(left_axis_lbl_shift)s;
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
</div>""" % {u"titles": title_dets_html, 
             u"series_js": series_js, u"xaxis_lbls": xaxis_lbls, 
             u"width": width, u"height": height, u"xfontsize": xfontsize, 
             u"axis_lbl_font_colour": axis_lbl_font_colour,
             u"major_gridline_colour": major_gridline_colour,
             u"gridline_width": gridline_width, u"pagebreak": pagebreak,
             u"axis_lbl_drop": axis_lbl_drop,
             u"left_axis_lbl_shift": left_axis_lbl_shift,
             u"x_title": x_title, u"y_title": y_title,
             u"tooltip_border_colour": tooltip_border_colour,
             u"inc_perc_js": inc_perc_js, u"connector_style": connector_style, 
             u"grid_bg": grid_bg, 
             u"minor_ticks": minor_ticks, u"micro_ticks": micro_ticks})
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)
    
def areachart_output(titles, subtitles, x_title, y_title, chart_dets, inc_perc, 
                     css_fil, css_idx, page_break_after):
    """
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    chart_dets --         
        
    Even though one xaxis_dets per series, only one is needed for a clustered
        bar chart ad it will fit all series.
    Each series (possibly only one) has a chart lbl (possibly not used), a
        legend lbl, xaxis_dets, and y vals.
    chart_dets = {mg.CHART_MAX_LBL_LEN: ...,
                  mg.CHART_SERIES_DETS: see below}
                  series_dets = [{mg.CHART_LBL: ...,
                                  mg.CHART_LEGEND_LBL: ..., 
                                  mg.CHART_MULTICHART: ...,
                                  mg.CHART_XAXIS_DETS: ...,
                                  mg.CHART_Y_VALS: ...}]
    css_idx -- css index so can apply    
    """
    debug = False
    html = []
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    series_dets = chart_dets[mg.CHART_SERIES_DETS]
    if debug: print(series_dets)
    multichart = series_dets[0][mg.CHART_MULTICHART]
    # NB one xaxis for all lines
    xaxis_dets = series_dets[0][mg.CHART_XAXIS_DETS]
    lbl_dets = get_lbl_dets(xaxis_dets)
    xaxis_lbls = u"[" + u",\n            ".join(lbl_dets) + u"]"
    max_lbl_len = chart_dets[mg.CHART_MAX_LBL_LEN]
    (width, xfontsize, minor_ticks, 
                micro_ticks) = get_linechart_sizings(xaxis_dets, max_lbl_len, 
                                                     series_dets)
    left_axis_lbl_shift = 20 if width > 1200 else 0 # gets squeezed 
    if multichart:
        width = width*0.8
        xfontsize = xfontsize*0.8
        left_axis_lbl_shift = left_axis_lbl_shift + 20
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
    (outer_bg, grid_bg, axis_lbl_font_colour, major_gridline_colour, 
            gridline_width, stroke_width, tooltip_border_colour, 
            colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
    # Can't have white for line charts because always a white outer background
    axis_lbl_font_colour = axis_lbl_font_colour \
                            if axis_lbl_font_colour != u"white" else u"black"
    colour_cases = setup_highlights(colour_mappings, single_colour=False, 
                                    override_first_highlight=True)
    try:
        stroke = colour_mappings[0][0]
        fill = colour_mappings[0][1]
    except IndexError, e:
        stroke = mg.DOJO_COLOURS[0]
    # build js for every series
    series_js_list = []
    series_names_list = []
    for chart_idx, chart_det in enumerate(series_dets):
        pagebreak = u"" if chart_idx % 2 == 0 else u"page-break-after: always;"
        indiv_area_title = "<p><b>%s</b></p>" % \
                chart_det[mg.CHART_LBL] if multichart else u""
        series_names_list.append(u"series%s" % chart_idx)
        series_js_list.append(u"var series%s = new Array();" % chart_idx)
        series_js_list.append(u"series%s[\"seriesLabel\"] = \"%s\";"
                              % (chart_idx, chart_det[mg.CHART_LEGEND_LBL]))
        series_js_list.append(u"series%s[\"yVals\"] = %s;" % 
                              (chart_idx, chart_det[mg.CHART_Y_VALS]))
        series_js_list.append(u"series%s[\"style\"] = "
            u"{stroke: {color: \"%s\", width: \"6px\"}, fill: \"%s\"};" % 
            (chart_idx, stroke, fill))
        series_js_list.append(u"")
        series_js = u"\n    ".join(series_js_list)
        series_js += u"\n    var series = new Array(%s);" % \
                                                u", ".join(series_names_list)
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
    chartconf["leftAxisLabelShift"] = %(left_axis_lbl_shift)s;
    chartconf["axisLabelFontColour"] = "%(axis_lbl_font_colour)s";
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
</div>""" % {u"series_js": series_js, u"xaxis_lbls": xaxis_lbls, 
             u"indiv_area_title": indiv_area_title,
             u"width": width, u"height": height, u"xfontsize": xfontsize, 
             u"axis_lbl_font_colour": axis_lbl_font_colour,
             u"major_gridline_colour": major_gridline_colour,
             u"left_axis_lbl_shift": left_axis_lbl_shift,
             u"gridline_width": gridline_width, 
             u"y_title": y_title, u"pagebreak": pagebreak,
             u"tooltip_border_colour": tooltip_border_colour,
             u"inc_perc_js": inc_perc_js, u"connector_style": connector_style, 
             u"grid_bg": grid_bg, u"chart_idx": u"%02d" % chart_idx,
             u"minor_ticks": minor_ticks, u"micro_ticks": micro_ticks})
    html.append(u"""<div style="clear: both;">&nbsp;&nbsp;</div>""")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)

def histogram_output(titles, subtitles, var_lbl, histo_dets, inc_normal,
                     css_fil, css_idx, page_break_after=False):
    """
    See http://trac.dojotoolkit.org/ticket/7926 - he had trouble doing this then
    titles -- list of title lines correct styles
    subtitles -- list of subtitle lines
    minval -- minimum values for x axis
    maxval -- maximum value for x axis
    xaxis_dets -- [(1, u""), (2, u""), ...]
    y_vals -- list of values e.g. [12, 30, 100.5, -1, 40]
    bin_lbls -- [u"1 to under 2", u"2 to under 3", ...]
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
    (outer_bg, grid_bg, axis_lbl_font_colour, major_gridline_colour, 
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
    js_inc_normal = u"true" if inc_normal else u"false"
    for chart_idx, histo_det in enumerate(histo_dets):
        minval = histo_det[mg.CHART_MINVAL]
        maxval = histo_det[mg.CHART_MAXVAL]
        xaxis_dets = histo_det[mg.CHART_XAXIS_DETS]
        y_vals = histo_det[mg.CHART_Y_VALS]
        norm_ys = histo_det[mg.CHART_NORMAL_Y_VALS]
        bin_lbls = histo_det[mg.CHART_BIN_LBLS]
        pagebreak = u"" if chart_idx % 2 == 0 else u"page-break-after: always;"
        indiv_histo_title = "<p><b>%s</b></p>" % \
                histo_det[mg.CHART_CHART_BY_LBL] if multichart else u""        
        xaxis_lbls = u"[" + \
            u",\n            ".join([u"{value: %s, text: \"%s\"}" % (i, x[1]) 
                                    for i,x in enumerate(xaxis_dets,1)]) + u"]"
        bin_labs = u"\"" + u"\", \"".join(bin_lbls) + u"\""
        width = 700 if len(xaxis_dets) <= 20 else 900
        xfontsize = 10 if len(xaxis_dets) <= 20 else 8
        left_axis_lbl_shift = 10 
        if multichart:
            width = width*0.8
            xfontsize = xfontsize*0.8
            left_axis_lbl_shift += 20
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
    chartconf["leftAxisLabelShift"] = %(left_axis_lbl_shift)s;
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
%(indiv_histo_title)s
<div id="mychartRenumber%(chart_idx)s" 
        style="width: %(width)spx; height: %(height)spx;">
    </div>
</div>
        """ % {u"indiv_histo_title": indiv_histo_title,
               u"stroke_width": stroke_width, 
               u"normal_stroke_width": stroke_width*2, u"fill": fill,
               u"colour_cases": colour_cases,
               u"xaxis_lbls": xaxis_lbls, u"y_vals": u"%s" % y_vals,
               u"bin_lbls": bin_labs, u"minval": minval, u"maxval": maxval,
               u"width": width, u"height": height, u"xfontsize": xfontsize, 
               u"var_lbl": var_lbl,
               u"left_axis_lbl_shift": left_axis_lbl_shift,
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
    (grid_bg, 
         item_colours, line_colour) = output.get_stats_chart_colours(css_fil)
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
                          label_y, css_fil, pagebreak):
    debug = False
    if multichart:  
        width, height = (500, 300)
    else:
        width, height = (700, 350)
    left_axis_lbl_shift = 10
    xfontsize = 10
    xmax = max(list_x)
    x_title = label_x
    axis_lbl_drop = 10
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
    (outer_bg, grid_bg, axis_lbl_font_colour, major_gridline_colour, 
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
    chartconf["leftAxisLabelShift"] = %(left_axis_lbl_shift)s;
    chartconf["axisLabelFontColour"] = "%(axis_lbl_font_colour)s";
    chartconf["majorGridlineColour"] = "%(major_gridline_colour)s";
    chartconf["xTitle"] = "%(x_title)s";
    chartconf["axisLabelDrop"] = %(axis_lbl_drop)s;
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
       u"pagebreak": pagebreak,
       u"axis_lbl_font_colour": axis_lbl_font_colour,
       u"major_gridline_colour": major_gridline_colour,
       u"left_axis_lbl_shift": left_axis_lbl_shift,
       u"gridline_width": gridline_width, 
       u"axis_lbl_drop": axis_lbl_drop,
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
        chart_by_lbl = indiv_data[mg.CHART_CHART_BY_LBL]
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
                                  label_x, label_y, css_fil, pagebreak)
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % page_break_before)
    return u"".join(html)

def boxplot_output(titles, subtitles, any_missing_boxes, x_title, y_title, 
                   xaxis_dets, max_lbl_len, chart_dets, xmin, xmax, ymin, ymax, 
                   css_fil, css_idx, page_break_after):
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
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    title_dets_html = get_title_dets_html(titles, subtitles, css_idx)
    # For multiple, don't split label if the mid tick (clash with x axis label)
    lbl_dets = get_lbl_dets(xaxis_dets)
    lbl_dets.insert(0, u"""{value: 0, text: ""}""")
    lbl_dets.append(u"""{value: %s, text: ""}""" % len(lbl_dets))
    xaxis_lbls = u"[" + u",\n            ".join(lbl_dets) + u"]"
    axis_lbl_drop = 30 if x_title else -10
    height = 350 + axis_lbl_drop # compensate for loss of display height                           
    (width, xfontsize,
        minor_ticks) = get_boxplot_sizings(xaxis_dets, max_lbl_len, chart_dets)
    yfontsize = xfontsize
    left_axis_lbl_shift = 20 if width > 1200 else 10 # gets squeezed
    html = []
    if any_missing_boxes:
        html.append(u"<p>At least one box will not be displayed because it "
                    u"lacks at least %s values.</p>"
                    % mg.CHART_MIN_DISPLAY_VALS_FOR_BOXPLOT)
    """
    For each series, set colour details.
    For the collection of series as a whole, set the highlight mapping from 
        each series colour.
    From dojox.charting.action2d.Highlight but with extraneous % removed
    """
    (outer_bg, grid_bg, axis_lbl_font_colour, major_gridline_colour, 
            gridline_width, stroke_width, tooltip_border_colour, 
            colour_mappings, connector_style) = lib.extract_dojo_style(css_fil)
    # Can't have white for boxplots because always a white outer background
    outer_bg = u"white"
    axis_lbl_font_colour = axis_lbl_font_colour \
                            if axis_lbl_font_colour != u"white" else u"black"
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
    For each box, we need to identify the center. For this we need to know 
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
        except IndexError, e:
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
    chartconf["leftAxisLabelShift"] = %(left_axis_lbl_shift)s;
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
    style="width: 0px; height: 0px; visibility: hidden;">
    </div>
<div id="legendMychartRenumber00">
    </div>
</div>
    """ % {u"titles": title_dets_html, u"pre_series_str": pre_series_str,
           u"series_js_str": series_js_str, u"xaxis_lbls": xaxis_lbls, 
           u"width": width, u"height": height, 
           u"xfontsize": xfontsize, u"yfontsize": yfontsize, 
           u"xmin": xmin, u"xmax": xmax, u"ymin": ymin, u"ymax": ymax,
           u"x_title": x_title, u"y_title": y_title,
           u"axis_lbl_font_colour": axis_lbl_font_colour,
           u"major_gridline_colour": major_gridline_colour,
           u"gridline_width": gridline_width, u"pagebreak": pagebreak,
           u"axis_lbl_drop": axis_lbl_drop, u"minor_ticks": minor_ticks,
           u"left_axis_lbl_shift": left_axis_lbl_shift,
           u"tooltip_border_colour": tooltip_border_colour,
           u"connector_style": connector_style, 
           u"outer_bg": outer_bg, u"grid_bg": grid_bg})
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)
    