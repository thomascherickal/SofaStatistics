"""
Use English UK spelling e.g. colour and when writing JS use camelcase.

NB no html headers here - the script generates those beforehand and appends this
and then the html footer.

For most charts we can use freq and AVG - something SQL does just fine using
GROUP BY. Accordingly, we can reuse get_gen_chart_output_dets in many cases.

In other cases, however, e.g. box plots, we need to analyse the values to get
results that SQL can't do well e.g. quartiles. In such cases we have to custom-
make the specific queries we need.

For grouped data we ensure there is a value for every required group even if it
is a zero. E.g. if we are looking at web browser by country and one country
doesn't have any records for a particular browser, we still return a result for
that intersection, albeit zero. Note - this also applies to time series line
charts with multiple series. It means that the shape of a line will sometimes
have dips to zero in it if different groups don't share all the same dates. This
is as it should be. If there is a desire to show a result without the "enforced"
zeros this can be done by applying a filter to the data and creating a standard,
single-line line chart (possibly with extra lines for trends or smoothed data).
"""

from operator import itemgetter
import pprint

import numpy as np
import wx

from .. import basic_lib as b
from .. import my_globals as mg
from .. import lib
from .. import my_exceptions
from .. import getdata
from .. import output
from . import charting_pylab
from ..stats import core_stats

AVG_CHAR_WIDTH_PXLS = 6.5
AVG_LINE_HEIGHT_PXLS = 12
TXT_WIDTH_WHEN_ROTATED = 4
DOJO_YTITLE_OFFSET_0 = 45
CHART_VAL_KEY = 'chart_val_key'
CHART_N_KEY = 'chart_n_key'
CHART_SERIES_KEY = 'chart_series_key'
SERIES_KEY = 'series_key'
XY_KEY = 'xy_key'
TRENDLINE_LBL = 'Trend line'
SMOOTHLINE_LBL = 'Smooth line'
## Field names I really hope no-one accidentally uses themselves ;-)
## Can't use underscores to start field names because MS Access (amongst others?) can't cope.
SOFA_CHARTS = 'internal_sofa_charts'
SOFA_SERIES = 'internal_sofa_series'
SOFA_CAT = 'internal_sofa_cat'
SOFA_VAL2SHOW = 'internal_sofa_val2show'
SOFA_VAL = 'internal_sofa_val'
SOFA_X = 'internal_sofa_x'
SOFA_Y = 'internal_sofa_y'

def charts_append_divider(html, titles, overall_title, indiv_title='',
        item_type=''):
    title = overall_title if not titles else titles[0]
    output.append_divider(html, title, indiv_title, item_type)

def get_gen_chart_output_dets(chart_type, dbe, cur, tbl, tbl_filt,
        var_role_dic, sort_opt, *, rotate=False, data_show=mg.SHOW_FREQ_KEY,
        major_ticks=False, time_series=False):
    """
    Note - variables must match values relevant to mg.CHART_CONFIG e.g.
    VAR_ROLE_CATEGORY i.e. var_role_cat, for checking to work (see usage of
    locals() below).

    Returns some overall details for the chart plus series details (only the one
    series in some cases).

    Note - not all charts have x-axis labels and thus the option of rotating
    them.
    """
    debug = False
    is_agg = (var_role_dic['agg'] is not None)
    ## validate fields supplied (or not)
    chart_subtype_key = mg.AGGREGATE_KEY if is_agg else mg.INDIV_VAL_KEY
    chart_config = mg.CHART_CONFIG[chart_type][chart_subtype_key]
    for var_dets in chart_config:  ## looping through available dropdowns for chart
        var_role = var_dets[mg.VAR_ROLE_KEY]
        allows_missing = var_dets[mg.EMPTY_VAL_OK]
        matching_input_var = locals()['var_role_dic'][var_role]
        role_missing = matching_input_var is None
        if role_missing and not allows_missing:
            raise Exception(
                f"The required field {var_role} is missing for "
                f"the {chart_type} chart type.")
    ## misc
    tbl_quoted = getdata.tblname_qtr(dbe, tbl)
    where_tbl_filt, and_tbl_filt = lib.FiltLib.get_tbl_filts(tbl_filt)
    xlblsdic = var_role_dic['cat_lbls']
    ## Get data as per setup
    ## overall data ready for restructuring and presentation
    SQL_raw_data, SQL_chart_ns = DataPrep.get_gen_chart_SQL(dbe, tbl_quoted,
        where_tbl_filt, and_tbl_filt, var_role_dic['agg'], var_role_dic['cat'],
        var_role_dic['series'], var_role_dic['charts'], data_show)
    if debug: print(SQL_raw_data)
    try:
        cur.execute(SQL_raw_data)
    except Exception as e:
        raise Exception(
            f"Unable to get raw data for chart. Orig error: {b.ue(e)}")
    raw_data = cur.fetchall()
    if debug: print(raw_data)
    if not raw_data:
        raise my_exceptions.TooFewValsForDisplay
    ## chart ns data
    if debug: print(SQL_chart_ns)
    try:
        cur.execute(SQL_chart_ns)
    except Exception as e:
        raise Exception(
            f"Unable to get charts data for chart. Orig error: {b.ue(e)}")
    chart_ns_data = cur.fetchall()
    if debug: print(chart_ns_data)
    if not chart_ns_data:
        raise Exception('Unable to make chart if not chart values')
    chart_ns = dict(x for x in chart_ns_data)
    ## restructure and return data
    chart_output_dets = DataPrep.structure_gen_data(chart_ns, chart_type,
        raw_data, xlblsdic, var_role_dic, sort_opt,
        rotate=rotate, data_show=data_show,
        major_ticks=major_ticks, time_series=time_series)
    if debug: print(chart_output_dets)
    return chart_output_dets

def setup_highlights(colour_mappings, single_colour,
        override_first_highlight=False):
    """
    colour_mappings -- must be #ffffff style. Names ignored for highlighting
    e.g. "red".    

    single_colour -- if single colour in chart (e.g. simple bar chart), only
    need one highlight defined so can break out of loop.

    override_first_highlight -- added so we can override the highlight when
    using the default style and multiple series. Ensures it will look good in a
    very important case even though not a general solution.
    """
    colour_cases_list = []
    for i, mappings in enumerate(colour_mappings):
        bg_colour, hl_colour = mappings
        if hl_colour == '':
            continue  ## let default highlighting occur
        if i == 0 and override_first_highlight:
            hl_colour = '#736354'
        colour_cases_list.append(f"""                case "{bg_colour}":
            hlColour = "{hl_colour}";
            break;""")
        if single_colour:
            break
    colour_cases = '\n'.join(colour_cases_list)
    colour_cases = colour_cases.lstrip()
    return colour_cases

def get_lbl_dets(xaxis_dets):
    ## can be a risk that a split label for the middle x value will overlap with x-axis label below
    lbl_dets = []
    for i, xaxis_det in enumerate(xaxis_dets, 1):
        val_lbl = xaxis_det[2]  ## the split variant of the label
        lbl_dets.append('{' + f'value: {i}, text: {val_lbl}' + '}')
    return lbl_dets

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

def get_series_colours_by_lbl(chart_output_dets, css_fpath):
    css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fpath)
    item_colours = output.colour_mappings_to_item_colours(
        css_dojo_dic['colour_mappings'])
    ## check every series in every chart to get full list
    series_colours_by_lbl = {}
    series_lbls = []
    for chart_dets in chart_output_dets[mg.CHARTS_CHART_DETS]:
        series_dets = chart_dets[mg.CHARTS_SERIES_DETS]
        for series_det in series_dets:
            series_lbl = series_det[mg.CHARTS_SERIES_LBL_IN_LEGEND]
            if series_lbl not in series_lbls:  ## can't use set because want to retain order
                series_lbls.append(series_det[mg.CHARTS_SERIES_LBL_IN_LEGEND])
    for i, series_lbl in enumerate(series_lbls):
        try:
            series_colours_by_lbl[series_lbl] = item_colours[i]
        except IndexError:
            raise Exception(
                "Unable to cope with need for that many different colours.")
    return series_colours_by_lbl

def _get_optimal_min_max(axismin, axismax):
    """
    For boxplots and scatterplots.

    axismin -- the minimum y value exactly
    axismax -- the maximum y value exactly

    Generally, we want box and scatter plots to have y-axes starting from just
    below the minimum point (e.g. lowest outlier). That is avoid the common case
    where we have the y-axis start at 0, and all our values range tightly
    together. In which case, for boxplots, we will have a series of tiny
    boxplots up the top and we won't be able to see the different parts of it
    e.g. LQ, median etc. For scatter plots our data will be too tightly
    scrunched up to see any spread.

    But sometimes the lowest point is not that far above 0, in which case we
    should set it to 0. A 0-based axis is preferable unless the values are a
    long way away. Going from 0.5-12 is silly. Might as well go from 0-12.
    4 scenarios:

    1) min and max are both the same
    Just try to set the max differently to the min so there is a range on the
    axis to display. See implementation for more details.

    2) min and max are both +ve
    |   *
    |
    -------
    Snap min to 0 if gap small rel to range, otherwise make min y-axis just
    below min point. Make max y-axis just above the max point. Make the
    padding from 0 the lesser of 0.1 of axismin and 0.1 of valrange. The
    outer padding can be the lesser of the axismax and 0.1 of valrange.

    3) min and max are -ve
    -------
    |   *
    |
    Snap max to 0 if gap small rel to range, otherwise make max y-axis just
    above max point. Make min y-axis just below min point. Make the
    padding the lesser of 0.1 of gap and 0.1 of valrange.

    4) min is -ve and max is +ve
    |   *
    -------
    |   *
    Make max 1.1*axismax. No harm if 0.
    Make min 1.1*axismin. No harm if 0.
    """
    debug = False
    if debug: print(f"Orig min max: {axismin} {axismax}")
    if axismin == axismax:
        myvalue = axismin
        if myvalue < 0:
            axismin = 1.1*myvalue
            axismax = 0
        elif myvalue == 0:
            axismin = -1
            axismax = 1
        elif myvalue > 0:
            axismin = 0
            axismax = 1.1*myvalue
    elif axismin >= 0 and axismax >= 0:  ## both +ve
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
            if gap2range < 0.6:  ## close enough to snap to 0
                axismin = 0
            else:  ## can't just be 0.9 min - e.g. looking at years from 2000-2010 would be 1800 upwards!
                axismin -= min(0.1*gap, 0.1*valrange)  ## gap is never 0 and is at least 0.6 of valrange
        except ZeroDivisionError:
            pass
        axismax += min(0.1*axismax, 0.1*valrange)
    elif axismin <= 0 and axismax <= 0:  ## both -ve
        """
        Snap max to 0 if gap small rel to range, otherwise make max y-axis just
        above max point. Make min y-axis just below min point. Make the padding
        the lesser of 0.1 of gap and 0.1 of valrange.
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
        axismin -= min(0.1*abs(axismin), 0.1*valrange)  ## make even more negative, but by the least possible
    elif axismin <=0 and axismax >=0:  ## spanning y-axis (even if all 0s ;-))
        """
        Pad max with 0.1*axismax. No harm if 0.
        Pad min with 0.1*axismin. No harm if 0.
        """
        axismax = 1.1*axismax
        axismin = 1.1*axismin
    else:
        pass
    if debug: print(f"Final axismin: {axismin}; Final axismax {axismax}")
    return axismin, axismax


class DataPrep:

    @staticmethod
    def get_gen_chart_SQL(dbe, tbl_quoted, where_tbl_filt, and_tbl_filt,
            var_role_agg, var_role_cat, var_role_series, var_role_charts,
            data_show):
        """
        var_role_xxxx -- might be None.
    
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
        Note - don't use freq as my own field name as it may conflict with freq
        if selected by user.

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

        Two things to note: 1) the rows with missing values in any of the
        grouping variables are discarded as they cannot be plotted; 2) we are
        going to have a lot of zero values to display.

        Imagine displaying those results as a clustered bar chart of frequencies:

        Chart 1 (Male)
        Three colours - Japan, Italy, Germany
        Five x-labels - Under 20, 20-29, 30-39, 40-64, 65+
        Working from left to right in the chart:
        1,1,1 has a freq of 2 so we will have a bar 2 high for Japan above the
        Under 20 label

        1,2,1 has no values so the display for Italy above the Under 20 label
        will be 0

        1,3,1 has no values so the display for Germany above the Under 20 label
        will be 0

        1,1,2 has a freq of 1 so there will be a bar 1 high for Japan above the
        20-29 label etc

        NB we can't do a group by on all grouping variables at once because the
        combinations with zero freqs (e.g. 1,2,1) would not be included. We have
        to do it grouping variable by grouping variable and then do a cartesian
        join at the end to give us all combinations we need to plot (whether
        with zeros or another value).

        Looking at an individual grouping variable, we want to include all non-
        null values where there are no missing values in any of the other
        grouping variables (or in the variable being averaged if a chart of
        averages).
        """
        debug = False
        objqtr = getdata.get_obj_quoter_func(dbe)
        cartesian_joiner = getdata.get_cartesian_joiner(dbe)
        has_charts = bool(var_role_charts)
        has_series = bool(var_role_series)
        has_cat = bool(var_role_cat)
        if not has_cat:
            raise Exception('All general charts require a category variable '
                'to be identified')
        ## Get everything ready to use in queries by quoting and, if required,
        ## autofilling. tbl_quoted is already quoted and ready to go.
    
        ## Series and charts are optional so we need to autofill them with
        ## something which will keep them in the same group.
        var_role_charts = (objqtr(var_role_charts) if has_charts 
            else mg.GROUPING_PLACEHOLDER)
        var_role_series = (objqtr(var_role_series) if has_series 
            else mg.GROUPING_PLACEHOLDER)
        var_role_cat = objqtr(var_role_cat)
        var_role_agg = objqtr(var_role_agg)
        is_agg = (data_show in mg.AGGREGATE_DATA_SHOW_OPT_KEYS)
        agg_filt = f" AND {var_role_agg} IS NOT NULL " if is_agg else ' '
        sql_dic = {'tbl': tbl_quoted,
            'var_role_charts': var_role_charts,
            'var_role_series': var_role_series,
            'var_role_cat': var_role_cat,
            'var_role_agg': var_role_agg,
            'where_tbl_filt': where_tbl_filt,
            'and_tbl_filt': and_tbl_filt,
            'and_agg_filt': agg_filt,
            'sofa_charts': SOFA_CHARTS,
            'sofa_series': SOFA_SERIES,
            'sofa_cat': SOFA_CAT,
            'sofa_val': SOFA_VAL,
            'sofa_val2show': SOFA_VAL2SHOW,
        }
        ## 1) grouping variables
        ## Charts ***************************
        """
        SQL_charts_n -
        Just trying to get counts per chart. If only chart the chart value will
        be a dummy value of 1 or whatever mg.GROUPING_PLACEHOLDER is. And the
        same approach for series.

        But we only want to count records per chart where the data is actually
        going to be used. So must have category populated and any other filters
        in place e.g. the filter currently applied to this table and the filter
        on the aggregated variable if relevant (e.g. getting the mean age for a
        given category e.g. country. Then a simple aggregate query grouping by
        chart to get count.
        """
        ## Keeping SQL_chart_ns and SQL_charts near to each other - so similar in logic
        SQL_chart_ns = """SELECT
            {var_role_charts},
                COUNT({var_role_charts})
            AS chart_n
            FROM {tbl}
            WHERE {var_role_charts} IS NOT NULL
                AND {var_role_series} IS NOT NULL
                AND {var_role_cat} IS NOT NULL
                {and_tbl_filt}
                {and_agg_filt}
            GROUP BY {var_role_charts}""".format(**sql_dic)
        if debug: print(f'SQL_chart_ns:\n{SQL_chart_ns}')
        if has_charts:
            SQL_charts = """SELECT
                {var_role_charts}
            AS {sofa_charts}
            FROM {tbl}
            WHERE {var_role_charts} IS NOT NULL
                AND {var_role_series} IS NOT NULL
                AND {var_role_cat} IS NOT NULL
                {and_tbl_filt}
                {and_agg_filt}
            GROUP BY {var_role_charts}""".format(**sql_dic)
        else:
            if dbe == mg.DBE_MS_ACCESS:  ## one can't touch Access without getting a few warts ;-)
                SQL_charts = """SELECT TOP 1 1 AS {sofa_charts}
                    FROM {tbl}""".format(**sql_dic)
            else:
                SQL_charts = "SELECT 1 AS {sofa_charts}".format(**sql_dic)
        if debug: print(f'SQL_charts:\n{SQL_charts}')
        ## Series ***************************
        if has_series:
            SQL_series = """SELECT {var_role_series}
            AS {sofa_series}
            FROM {tbl}
            WHERE {var_role_series} IS NOT NULL
                AND {var_role_charts} IS NOT NULL
                AND {var_role_cat} IS NOT NULL
                {and_tbl_filt}
                {and_agg_filt}
            GROUP BY {var_role_series}""".format(**sql_dic)
        else:
            if dbe == mg.DBE_MS_ACCESS:
                SQL_series = ("SELECT TOP 1 1 AS %(sofa_series)s FROM %(tbl)s"
                    % sql_dic)
            else:
                SQL_series = "SELECT 1 AS {sofa_series}".format(**sql_dic)
        if debug: print(f'SQL_series:\n{SQL_series}')
        SQL_cat = """SELECT {var_role_cat}
        AS {sofa_cat}
        FROM {tbl}
        WHERE {var_role_cat} IS NOT NULL
            AND {var_role_charts} IS NOT NULL
            AND {var_role_series} IS NOT NULL
            {and_tbl_filt}
            {and_agg_filt}
        GROUP BY {var_role_cat}""".format(**sql_dic)
        if debug: print(f'SQL_cat:\n{SQL_cat}')
        SQL_group_by_vars = f"""SELECT * FROM ({SQL_charts}) AS qrycharts
            {cartesian_joiner} 
            ({SQL_series}) AS qryseries
            {cartesian_joiner}
            ({SQL_cat}) AS qrycat"""
        if debug: print(f'SQL_group_by_vars:\n{SQL_group_by_vars}')
        ## 2) Now get measures field with all grouping vars ready to join to full list
        if data_show not in mg.AGGREGATE_DATA_SHOW_OPT_KEYS:
            sql_dic['val2show'] = ' COUNT(*) '
        elif data_show == mg.SHOW_AVG_KEY:
            sql_dic['val2show'] = ' AVG({var_role_agg}) '.format(**sql_dic)
        elif data_show == mg.SHOW_SUM_KEY:
            sql_dic['val2show'] = ' SUM({var_role_agg}) '.format(**sql_dic)
        else:
            raise Exception(
                f'get_SQL_raw_data() not expecting a data_show of {data_show}')
        groupby_vars = []
        if has_charts: groupby_vars.append(var_role_charts)
        if has_series: groupby_vars.append(var_role_series)
        groupby_vars.append(var_role_cat)
        sql_dic['groupby_charts_series_cats'] = (
            ' GROUP BY ' + ', '.join(groupby_vars))
        SQL_vals2show = """SELECT {var_role_charts}
        AS {sofa_charts},
            {var_role_series}
        AS {sofa_series},
            {var_role_cat}
        AS {sofa_cat},
            {val2show}
        AS {sofa_val2show}
        FROM {tbl}
        {where_tbl_filt}
        {groupby_charts_series_cats}""".format(**sql_dic)
        if debug: print(f'SQL_vals2show:\n{SQL_vals2show}')
        ## 3) Put all group by vars on left side of join with measures by those
        ## grouping vars.
        sql_dic['SQL_group_by_vars'] = SQL_group_by_vars
        sql_dic['SQL_vals2show'] = SQL_vals2show
        sql_dic['get_val2show'] = (mg.DBE_MODULES[dbe].if_clause
            % (f'{SOFA_VAL2SHOW} IS NULL', '0', SOFA_VAL2SHOW))
        SQL_raw_data = """SELECT qrygrouping_vars.{sofa_charts},
        qrygrouping_vars.{sofa_series},
        qrygrouping_vars.{sofa_cat},
            {get_val2show}
        AS {sofa_val}
        FROM ({SQL_group_by_vars}) AS qrygrouping_vars
        LEFT JOIN ({SQL_vals2show}) AS qryvals2show
        ON qrygrouping_vars.{sofa_charts} = qryvals2show.{sofa_charts}
        AND qrygrouping_vars.{sofa_series} = qryvals2show.{sofa_series}
        AND qrygrouping_vars.{sofa_cat} = qryvals2show.{sofa_cat}
        ORDER BY qrygrouping_vars.{sofa_charts}, qrygrouping_vars.{sofa_series},
            qrygrouping_vars.{sofa_cat}""".format(**sql_dic)    
        if debug: print(f'SQL_raw_data:\n{SQL_raw_data}')
        return SQL_raw_data, SQL_chart_ns

    @staticmethod
    def get_sorted_y_dets(data_show, major_ticks, time_series, sort_opt,
            vals_etc_lst, dp, *, multiseries=False):
        """
        Sort in place then iterate and build new lists with guaranteed
        synchronisation.

        Tooltips can use rounded y-vals but actual y_vals must keep full
        precision.
        """
        if multiseries and sort_opt not in mg.SORT_VAL_AND_LABEL_OPT_KEYS:
            raise Exception("Sorting by anything other than val or lbl fails if"
                " a multiseries chart because sorting by increasing or "
                "decreasing is based on data for the category _across_ series "
                "e.g. total for the male gender category across all age group "
                "series whereas this function sorts within a series only.")
        idx_raw_measure = 1
        idx_lbl = 3
        lib.sort_value_lbls(sort_opt, vals_etc_lst, idx_raw_measure, idx_lbl)  ## sort by raw rather than rounded measure
        sorted_xaxis_dets = []
        sorted_y_vals = []
        sorted_tooltips = []
        measures = [x[idx_raw_measure] for x in vals_etc_lst]
        tot_measures = sum(measures)
        for (val, raw_measure, rounded_measure, lbl,
                lbl_split, itemlbl) in vals_etc_lst:
            sorted_xaxis_dets.append((val, lbl, lbl_split))
            if tot_measures == 0:
                perc = 0
            else:
                perc = 100*(raw_measure/float(tot_measures))
            y_val = perc if data_show == mg.SHOW_PERC_KEY else raw_measure
            sorted_y_vals.append(y_val)
            measure2show = int(rounded_measure) if dp == 0 else rounded_measure # so 12 is 12 not 12.0
            tooltip_dets = [itemlbl,] if itemlbl else []
            if major_ticks or time_series:
                tooltip_dets.append(f'x-val: {val}')
                tooltip_dets.append(f'y-val: {measure2show}')
            else:
                tooltip_dets.append('{:,}'.format(measure2show))
            if data_show not in mg.AGGREGATE_DATA_SHOW_OPT_KEYS:  ## OK to show percentage
                dp_tpl = f'%.{mg.DEFAULT_REPORT_DP}f%%'
                tooltip_dets.append(dp_tpl % perc)
            tooltip = '<br>'.join(tooltip_dets)
            sorted_tooltips.append(tooltip)
        return sorted_xaxis_dets, sorted_y_vals, sorted_tooltips

    @staticmethod
    def get_prestructured_grouped_data(raw_data, fldnames, chart_ns):
        """
        chart_ns -- usually summarised data so counting records per chart is
        simply a matter of summing a few y-vals. But with scatterplot data,
        which is a list of unique x-y combinations, we need this data supplied.
        And no, we can't just count records per chart because they may have been
        aggregated into unique x-y values so the n records could be considerably
        less than the actual number of records.

        [(1,1,1,56),  ## chart_val, series_val, x_val, y_val (N)
         (1,1,2,103), ## iterate through rows and consolidate by series & chart
         (1,2,1,23),
         (1,2,2,4),
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
        Need to iterate through and every time chart id changes start new
        collection of series under the new chart. And every time a series
        changes, start a new one.
        """
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
            if not same_chart:  ## initialise a fresh chart with a fresh series
                n_recs_to_add = chart_ns[chart_val]
                chart_dic = {CHART_VAL_KEY: chart_val,
                             CHART_N_KEY: n_recs_to_add,  ## add to as we go (SQL would have been better but the SQL is more than tricky enough already and very, very fast doing it here ayway)
                             CHART_SERIES_KEY:  ## may add more if we find more series for this chart
                                 [{SERIES_KEY: series_val,
                                   XY_KEY: [(x_val, y_val),]}
                                 ]
                             }
                prestructure.append(chart_dic)
                ## tracking only
                prev_chart_val = chart_val
                prev_series_val = series_val
            else:  ## same chart
                same_chart_dic = prestructure[-1]
                ## same series?
                same_series = (series_val == prev_series_val)
                ## add to existing series or set up new one in existing chart
                if not same_series:
                    ## add new series to same (last) chart
                    series2add = {
                        SERIES_KEY: series_val,
                        XY_KEY: [(x_val, y_val), ]}
                    same_chart_dic[CHART_SERIES_KEY].append(series2add)
                    prev_series_val = series_val
                else:
                    ## add xy tuple to same (last) series in same (last) chart
                    same_series_dic = same_chart_dic[CHART_SERIES_KEY][-1]
                    same_series_dic[XY_KEY].append((x_val, y_val))
        return prestructure

    @staticmethod
    def structure_gen_data(chart_ns, chart_type,
            raw_data, xlblsdic, var_role_dic, sort_opt, *,
            rotate=False, data_show=mg.SHOW_FREQ_KEY,
            major_ticks=False, time_series=False):
        """
        Structure data for general charts (use different processes preparing
        data for histograms, scatterplots etc).

        Take raw columns of data from SQL cursor and create required dict. Note
        - source data must be sorted by all grouping variables.

        raw_data -- 4 cols (even if has 1 as dummy variable in charts and/or
        series cols): charts, series, cat, vals.

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
            mg.CHARTS_OVERALL_LEGEND_LBL: "Age Group", # or None if only one series
            mg.CHARTS_CHART_DETS: chart_dets,
        }
        chart_dets = [
            {mg.CHARTS_CHART_N: 543,
             mg.CHARTS_CHART_LBL: "Gender: Male", # or None if only one chart
             mg.CHARTS_SERIES_DETS: series_dets},
            {mg.CHARTS_CHART_LBL: "Gender: Female",
             mg.CHARTS_SERIES_DETS: series_dets}, ...
        ]
        series_dets = {mg.CHARTS_SERIES_LBL_IN_LEGEND: "Italy", # or None if only one series
                       mg.CHARTS_XAXIS_DETS: [(val, lbl, lbl_split), (...), ...], 
                       mg.CHARTS_SERIES_Y_VALS: [46, 32, 28, 94], 
                       mg.CHARTS_SERIES_TOOLTIPS: ["46<br>23%", "32<br>16%", 
                                                   "28<br>14%", "94<br>47%"]}

        dp -- is the maximum dp for both x and y values displayed.
        """
        max_x_lbl_len = 0
        max_y_lbl_len = 0
        max_lbl_lines = 0
        fldnames = [var_role_dic['charts_name'], var_role_dic['series_name'],
            var_role_dic['cat_name'], var_role_dic['agg_name']]
        dp_y = 0 if data_show == mg.SHOW_FREQ_KEY else mg.DEFAULT_REPORT_DP  ## freq is always an integer so avoid showing decimals 
        prestructure = DataPrep.get_prestructured_grouped_data(
            raw_data, fldnames, chart_ns=chart_ns)
        chart_dets = []
        n_charts = len(prestructure)
        if n_charts > mg.MAX_CHARTS_IN_SET:
            if wx.MessageBox(_("This output will have %s charts and may not "
                        "display properly. Do you wish to make it anyway?")
                        % n_charts, 
                    caption=_('HIGH NUMBER OF CHARTS'),
                    style=wx.YES_NO) == wx.NO:
                raise my_exceptions.TooManyChartsInSeries(
                    var_role_dic['charts_name'],
                    max_items=mg.MAX_CHARTS_IN_SET)
        multichart = n_charts > 1
        if multichart:
            chart_fldname = var_role_dic['charts_name']
            chart_fldlbls = var_role_dic['charts_lbls']
        else:  ## clustered, line - can have multiple series without being multi-chart
            chart_fldname = None
            chart_fldlbls = {}
        allow_exceed_max_clusters = False
        allow_exceed_max_series = False
        xs_maybe_used_as_lbls = set()  ## because we will have repeated values when multiple charts etc and supplying repeat values will break our test of distinctiveness under rounding when setting dp
        for chart_dic in prestructure:
            for series_dic in chart_dic[CHART_SERIES_KEY]:
                for x_val, unused in series_dic[XY_KEY]:
                    xs_maybe_used_as_lbls.add(x_val)
        dp_x = lib.OutputLib.get_best_dp(xs_maybe_used_as_lbls)
        for chart_dic in prestructure:
            series = chart_dic[CHART_SERIES_KEY]
            n_series = len(series)
            if n_series > mg.MAX_CHART_SERIES and not allow_exceed_max_series:
                if wx.MessageBox(
                    _("This chart will have %s series and may not display "
                        "properly. Do you wish to make it anyway?") % n_series,
                        caption=_("HIGH NUMBER OF SERIES"),
                        style=wx.YES_NO) == wx.NO:
                    raise my_exceptions.TooManySeriesInChart(
                        mg.MAX_CHART_SERIES)
                else:
                    allow_exceed_max_series = True
            multiseries = (len(series) > 1)
            """
            chart_dic = {CHART_VAL_KEY: 1,
                         CHART_N_KEY: 493,
                         CHART_SERIES_KEY: [
                  {SERIES_KEY: 1,
                   XY_KEY: [(1,56), (2,103), (3,72), (4,40)] },
                  {SERIES_KEY: 2,
                   XY_KEY: [(1,13), (2,59), (3,200), (4,0)] }, ]}
            to
            {mg.CHARTS_CHART_LBL: "Gender: Male",  ## or a dummy title if only one chart because not displayed
             mg.CHARTS_SERIES_DETS: series_dets}
            """
            if multichart:
                chart_val = chart_dic[CHART_VAL_KEY]
                chart_fld_lbl = chart_fldlbls.get(chart_val, str(chart_val))
                chart_lbl = f"{chart_fldname}: {chart_fld_lbl}"
            else:
                chart_lbl = None
            series_dets = []
            for series_dic in series:
                series_val = series_dic[SERIES_KEY]
                if multiseries:
                    legend_lbl = var_role_dic['series_lbls'].get(
                        series_val, str(series_val))
                else:
                    legend_lbl = None
                ## process xy vals
                xy_vals = series_dic[XY_KEY]
                vals_etc_lst = []
                for x_val, y_val in xy_vals:
                    xval4lbl = lib.OutputLib.get_best_x_lbl(x_val, dp_x)
                    y_val_rounded = round(y_val, dp_y)
                    x_val_lbl = xlblsdic.get(x_val, str(xval4lbl))  ## original value for label matching, rounded for display if no label
                    (x_val_split_lbl, actual_lbl_width,
                     n_lines) = lib.OutputLib.get_lbls_in_lines(
                                        orig_txt=x_val_lbl,
                                        max_width=17, dojo=True, rotate=rotate)
                    if actual_lbl_width > max_x_lbl_len:
                        max_x_lbl_len = actual_lbl_width
                    rounding2use = dp_y if chart_type == mg.BOXPLOT else 0  ## only interested in width as potentially displayed on y-axis - which is always integers unless boxplot
                    y_lbl_width = len(str(round(y_val, rounding2use)))
                    if y_lbl_width > max_y_lbl_len:
                        max_y_lbl_len = y_lbl_width
                    if n_lines > max_lbl_lines:
                        max_lbl_lines = n_lines
                    if multiseries:  ##chart_type == mg.CLUSTERED_BARCHART:
                        itemlbl = f"{x_val_lbl}, {legend_lbl}"
                    else:
                        itemlbl = None
                    vals_etc_lst.append(
                        (x_val, y_val, y_val_rounded,
                         x_val_lbl, x_val_split_lbl, itemlbl))
                n_cats = len(vals_etc_lst)
                if chart_type == mg.CLUSTERED_BARCHART:
                    if n_cats > mg.MAX_CLUSTERS and not allow_exceed_max_clusters:
                        if wx.MessageBox(
                                _("This chart will have %(n_cats)s clusters by "
                                "%(var_role_cat)s and may not display properly."
                                " Do you wish to make it anyway?") % {
                                    "n_cats": n_cats,
                                    "var_role_cat": var_role_dic['cat']},
                                caption=_('HIGH NUMBER OF CLUSTERS'),
                                style=wx.YES_NO) == wx.NO:
                            raise my_exceptions.TooManyValsInChartSeries(
                                var_role_dic['cat'], mg.MAX_CLUSTERS)
                        else:
                            allow_exceed_max_clusters = True
                elif chart_type == mg.PIE_CHART:
                    if n_cats > mg.MAX_PIE_SLICES:
                        raise my_exceptions.TooManySlicesInPieChart
                else:
                    if n_cats > mg.MAX_CATS_GEN:
                        if multiseries:
                            msg = (
                                _("This chart will have %(n_cats)s "
                                "%(var_role_cat)s categories for "
                                "%(var_role_series_name)s \"%(series_lbl)s\" "
                                "and may not display properly. Do you wish to "
                                "make it anyway?") % {"n_cats": n_cats,
                                "var_role_cat": var_role_dic['cat'],
                                "var_role_series_name": var_role_dic['series_name'],
                                "series_lbl": legend_lbl})
                        else:
                            msg = (
                                _("This chart will have %(n_cats)s "
                                "%(var_role_cat)s categories and may not "
                                "display properly. Do you wish to make it "
                                "anyway?") % {
                                    "n_cats": n_cats,
                                    "var_role_cat": var_role_dic['cat']})
                        if wx.MessageBox(msg,
                            caption=_("HIGH NUMBER OF CATEGORIES"), 
                                style=wx.YES_NO) == wx.NO:
                            raise my_exceptions.TooManyValsInChartSeries(
                                var_role_dic['cat'], mg.MAX_CATS_GEN)
                (sorted_xaxis_dets, sorted_y_vals,
                    sorted_tooltips) = DataPrep.get_sorted_y_dets(
                        data_show, major_ticks, time_series, sort_opt,
                        vals_etc_lst, dp_y, multiseries=multiseries)
                series_det = {
                    mg.CHARTS_SERIES_LBL_IN_LEGEND: legend_lbl,
                    mg.CHARTS_XAXIS_DETS: sorted_xaxis_dets,
                    mg.CHARTS_SERIES_Y_VALS: sorted_y_vals,
                    mg.CHARTS_SERIES_TOOLTIPS: sorted_tooltips}
                series_dets.append(series_det)
            chart_det = {
                mg.CHARTS_CHART_LBL: chart_lbl,
                mg.CHARTS_CHART_N: chart_dic[CHART_N_KEY],
                mg.CHARTS_SERIES_DETS: series_dets}
            chart_dets.append(chart_det)
        overall_title = Titles.get_overall_title(
            var_role_dic['agg_name'],
            var_role_dic['cat_name'],
            var_role_dic['series_name'],
            var_role_dic['charts_name'])
        chart_output_dets = {
            mg.CHARTS_OVERALL_TITLE: overall_title,
            mg.CHARTS_MAX_X_LBL_LEN: max_x_lbl_len,
            mg.CHARTS_MAX_Y_LBL_LEN: max_y_lbl_len,
            mg.CHARTS_MAX_LBL_LINES: max_lbl_lines,
            mg.CHARTS_OVERALL_LEGEND_LBL: var_role_dic['series_name'],
            mg.CHARTS_CHART_DETS: chart_dets}
        return chart_output_dets


class Titles:
    
    @staticmethod
    def get_overall_title(var_role_agg_name, var_role_cat_name,
            var_role_series_name, var_role_charts_name):
        title_bits = []
        if var_role_agg_name:
            title_bits.append(f'Avg {var_role_agg_name}')
        if var_role_cat_name:
            if var_role_agg_name:
                title_bits.append(f'By {var_role_cat_name}')
            else:
                title_bits.append(f'{var_role_cat_name}')
        if var_role_series_name:
            title_bits.append(f'By {var_role_series_name}')
        if var_role_charts_name:
            title_bits.append(f'By {var_role_charts_name}')
        return ' '.join(title_bits)

    @staticmethod
    def get_ytitle_offset(max_y_lbl_len, x_lbl_len, max_safe_x_lbl_len_pxls, *,
            rotate=False):
        """
        Need to shift y-axis title left if wide y-axis label or first x-axis 
        label is wide.
        """
        debug = False
        ## 45 is a good total offset with label width of 20
        ytitle_offset = DOJO_YTITLE_OFFSET_0 - 20
        ## x-axis adjustment
        if not rotate:
            try:
                if x_lbl_len*AVG_CHAR_WIDTH_PXLS > max_safe_x_lbl_len_pxls:
                    lbl_shift = (AVG_CHAR_WIDTH_PXLS*x_lbl_len
                        - max_safe_x_lbl_len_pxls)/2.0  ## half of label goes to the right
                    ytitle_offset += lbl_shift
            except Exception:
                pass
        ## y-axis adjustment
        try:
            max_width_y_labels = AVG_CHAR_WIDTH_PXLS*max_y_lbl_len
            if debug: print(f"max_width_y_labels: {max_width_y_labels}")
            ytitle_offset += max_width_y_labels
        except Exception:
            pass
        if debug: print(f"ytitle_offset: {ytitle_offset}")
        if ytitle_offset < DOJO_YTITLE_OFFSET_0:
            ytitle_offset = DOJO_YTITLE_OFFSET_0
        return ytitle_offset

    @staticmethod
    def get_indiv_title(multichart, chart_det):
        if multichart:
            indiv_title = chart_det[mg.CHARTS_CHART_LBL]
            indiv_title_html = (f'<p><b>{indiv_title}</b></p>')
        else:
            indiv_title = ''
            indiv_title_html = ''
        return indiv_title, indiv_title_html


class BarChart:

    @staticmethod
    def _get_barchart_sizings(x_title, n_clusters, n_bars_in_cluster,
            max_x_lbl_width):
        """
        minor_ticks -- generally we don't want them as they result in lots of
        ticks between the groups in clustered bar charts each with a distracting
        and meaningless value e.g. if we have two groups 1 and 2 we don't want a
        tick for 0.8 and 0.9 etc. But if we don't have minor ticks when we have
        a massive number of clusters we get no ticks at all. Probably a dojo bug
        I am trying to work around.
        """
        debug = False
        MIN_PXLS_PER_BAR = 30
        MIN_CLUSTER_WIDTH = 60
        MIN_CHART_WIDTH = 450
        PADDING_PXLS = 35
        DOJO_MINOR_TICKS_NEEDED_FROM_N = 10  ## whatever works. Tested on cluster of Age vs Cars
        min_width_per_cluster = (MIN_PXLS_PER_BAR*n_bars_in_cluster)
        width_per_cluster = (max([min_width_per_cluster, MIN_CLUSTER_WIDTH,
            max_x_lbl_width*AVG_CHAR_WIDTH_PXLS]) + PADDING_PXLS)
        width_x_title = len(x_title)*AVG_CHAR_WIDTH_PXLS + PADDING_PXLS
        width = max([width_per_cluster*n_clusters, width_x_title,
            MIN_CHART_WIDTH])
        ## If wide labels, may not display almost any if one is too wide. Widen to take account.
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
        elif n_clusters > 10:
            xfontsize = 8
        else:
            xfontsize = 9
        init_margin_offset_l = 35 if width > 1200 else 25 # else gets squeezed out e.g. in percent
        minor_ticks = ('true' if n_clusters >= DOJO_MINOR_TICKS_NEEDED_FROM_N
            else 'false')
        if debug: print(width, xgap, xfontsize, minor_ticks,
            init_margin_offset_l)
        """
        dlg = wx.NumberEntryDialog(None, "Set Initial margin offset left",
            "Go on", "Set it!", 20, -100, 100)
        if dlg.ShowModal() == wx.ID_OK:
            init_margin_offset_l = dlg.GetValue()
        dlg.Destroy()
        """
        return width, xgap, xfontsize, minor_ticks, init_margin_offset_l

    @staticmethod
    def _add_dojo_html_js(html, chart_settings_dic):
        html.append("""
        <script type="text/javascript">

        var sofaHlRenumber{chart_idx} = function(colour){{
            var hlColour;
            switch (colour.toHex()){{
                {colour_cases}
                default:
                    hlColour = hl(colour.toHex());
                    break;
            }}
            return new dojox.color.Color(hlColour);
        }}

        makechartRenumber{chart_idx} = function(){{
            {series_js}
            var conf = new Array();
            conf["axis_font_colour"] = "{axis_font_colour}";
            conf["axis_lbl_drop"] = {axis_lbl_drop};
            conf["axis_lbl_rotate"] = {axis_lbl_rotate};
            conf["chart_bg"] = "{chart_bg}";
            conf["connector_style"] = "{connector_style}";
            conf["gridline_width"] = {gridline_width};
            conf["highlight"] = sofaHlRenumber{chart_idx};
            conf["major_gridline_colour"] = "{major_gridline_colour}";
            conf["margin_offset_l"] = {margin_offset_l};
            conf["minor_ticks"] = {minor_ticks};
            conf["n_chart"] = "{n_chart}";
            conf["plot_bg"] = "{plot_bg}";
            conf["plot_font_colour"] = "{plot_font_colour}";
            conf["plot_font_colour_filled"] = "{plot_font_colour_filled}";
            conf["tooltip_border_colour"] = "{tooltip_border_colour}";
            conf["xaxis_lbls"] = {xaxis_lbls};
            conf["xfontsize"] = {xfontsize};
            conf["xgap"] = {xgap};
            conf["x_title"] = "{x_title}";
            conf["ymax"] = {ymax};
            conf["y_title_offset"] = {y_title_offset};
            conf["y_title"] = "{y_title}";
            makeBarChart("mychartRenumber{chart_idx}", series, conf);
        }}
        </script>

        <div class="screen-float-only" style="margin-right: 10px; {pagebreak}">
        {indiv_title_html}
            <div id="mychartRenumber{chart_idx}"
                style="width: {width}px; height: {height}px;">
            </div>
        {legend}
        </div>""".format(**chart_settings_dic))

    @staticmethod
    def simple_barchart_output(
            titles, subtitles,
            x_title, y_title,
            chart_output_dets, css_idx, css_fpath, *,
            rotate, show_n, show_borders, page_break_after):
        """
        :param list titles: list of title lines correct styles
        :param list subtitles: list of subtitle lines
        :param dict chart_output_dets: see structure_gen_data()
         var_numeric -- needs to be quoted or not.
         xaxis_dets -- [(1, "Under 20"), (2, "20-29"), (3, "30-39"),
             (4, "40-64"), (5, "65+")]
        :param int css_idx: css index so can apply appropriate css styles
        """
        debug = False
        axis_lbl_rotate = -90 if rotate else 0
        html = []
        CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (
            mg.CSS_PAGE_BREAK_BEFORE, css_idx)
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
        height += axis_lbl_drop  ## compensate for loss of bar display height
        """
        For each series, set colour details.

        For the collection of series as a whole, set the highlight mapping from
        each series colour.

        From dojox.charting.action2d.Highlight but with extraneous % removed.
        """
        css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fpath)
        item_colours = output.colour_mappings_to_item_colours(
            css_dojo_dic['colour_mappings'])
        fill = item_colours[0]
        single_colour = True
        override_first_highlight = (
            css_fpath == mg.DEFAULT_CSS_PATH 
            and single_colour)
        colour_cases = setup_highlights(css_dojo_dic['colour_mappings'],
            single_colour, override_first_highlight)
        n_bars_in_cluster = 1
        ## always the same number, irrespective of order
        n_clusters = len(
            chart_output_dets\
                [mg.CHARTS_CHART_DETS][0]\
                [mg.CHARTS_SERIES_DETS][0]\
                [mg.CHARTS_XAXIS_DETS])
        max_x_lbl_width = TXT_WIDTH_WHEN_ROTATED if rotate else max_x_lbl_len
        (width, xgap, xfontsize, minor_ticks,
         init_margin_offset_l) = BarChart._get_barchart_sizings(
                x_title, n_clusters, n_bars_in_cluster, max_x_lbl_width)
        chart_dets = chart_output_dets[mg.CHARTS_CHART_DETS]
        ## following details are same across all charts so look at first
        chart0_series_dets = chart_dets[0][mg.CHARTS_SERIES_DETS]
        ## only one series per chart by design
        series_det = chart0_series_dets[0]
        xaxis_dets = series_det[mg.CHARTS_XAXIS_DETS]
        idx_1st_xdets = 0
        idx_xlbl = 1
        x_lbl_len = len(xaxis_dets[idx_1st_xdets][idx_xlbl])
        max_safe_x_lbl_len_pxls = 180
        y_title_offset = Titles.get_ytitle_offset(max_y_lbl_len, x_lbl_len, 
            max_safe_x_lbl_len_pxls, rotate=rotate)
        ymax = get_ymax(chart_output_dets)
        if multichart:
            width = width*0.9
            xgap = xgap*0.8
            xfontsize = xfontsize*0.75
        margin_offset_l = (
            init_margin_offset_l + y_title_offset - DOJO_YTITLE_OFFSET_0)
        if rotate:
            margin_offset_l += 15
        width += margin_offset_l
        stroke_width = css_dojo_dic['stroke_width'] if show_borders else 0
        ## loop through charts
        for chart_idx, chart_det in enumerate(chart_dets):
            indiv_title, indiv_title_html = Titles.get_indiv_title(
                multichart, chart_det)
            ## only one series per chart by design
            n_chart = ('N = ' + lib.formatnum(chart_det[mg.CHARTS_CHART_N])
                if show_n else '')
            series_det = chart_det[mg.CHARTS_SERIES_DETS][0]
            xaxis_dets = series_det[mg.CHARTS_XAXIS_DETS]
            lbl_dets = get_lbl_dets(xaxis_dets)
            xaxis_lbls = '[' + ',\n            '.join(lbl_dets) + ']'
            pagebreak = ('' if chart_idx % 2 == 0
                else 'page-break-after: always;')
            # build js for the single series (only 1 ever per chart in simple bar charts)
            series_js_list = []
            series_names_list = []
            series_names_list.append('series0')
            series_js_list.append('var series0 = new Array();')
            series_lbl = series_det[mg.CHARTS_SERIES_LBL_IN_LEGEND]
            series_js_list.append(f'series0["seriesLabel"] = "{series_lbl}";')
            series_y_vals = series_det[mg.CHARTS_SERIES_Y_VALS]
            series_js_list.append(f'series0["yVals"] = {series_y_vals};')
            tooltips = ("['"
                + "', '".join(series_det[mg.CHARTS_SERIES_TOOLTIPS]) + "']")
            series_js_list.append(
                'series0["options"] = {'
                    'stroke: {'
                        'color: "white", '
                        f'width: "{stroke_width}px"'
                    '}, '
                    f'fill: "{fill}", '
                    f'yLbls: {tooltips}'
                '};')
            series_js_list.append('')
            series_js = "\n    ".join(series_js_list)
            series_js += ("\n    var series = new Array(%s);"
                % ", ".join(series_names_list))
            series_js = series_js.lstrip()
            chart_settings_dic = {
                'axis_font_colour': css_dojo_dic['axis_font_colour'],
                'axis_lbl_drop': lib.if_none(axis_lbl_drop, 30),
                'axis_lbl_rotate': lib.if_none(axis_lbl_rotate, 0),
                'chart_bg': lib.if_none(css_dojo_dic['chart_bg'], 'null'),
                'chart_idx': '%02d' % chart_idx,
                'colour_cases': colour_cases,
                'connector_style': lib.if_none(css_dojo_dic['connector_style'], 'defbrown'),
                'gridline_width': lib.if_none(css_dojo_dic['gridline_width'], 3),
                'height': height,
                'indiv_title_html': indiv_title_html,
                'legend': '',  ## clustered bar charts use this 
                'major_gridline_colour': css_dojo_dic['major_gridline_colour'],
                'margin_offset_l': lib.if_none(margin_offset_l, 0),
                'minor_ticks': lib.if_none(minor_ticks, 'false'),
                'n_chart': lib.if_none(n_chart, "''"),
                'pagebreak': pagebreak,
                'plot_bg': css_dojo_dic['plot_bg'],
                'plot_font_colour': css_dojo_dic['plot_font_colour'],
                'plot_font_colour_filled': lib.if_none(css_dojo_dic['plot_font_colour_filled'], 'black'),
                'series_js': series_js,
                'tooltip_border_colour': lib.if_none(css_dojo_dic['tooltip_border_colour'], '#ada9a5'),
                'width': width,
                'x_title': lib.if_none(x_title, "''"),
                'xaxis_lbls': xaxis_lbls,
                'xfontsize': xfontsize,
                'xgap': xgap,
                'y_title': y_title,
                'y_title_offset': lib.if_none(y_title_offset, 0),
                'ymax': ymax,
            }
            BarChart._add_dojo_html_js(html, chart_settings_dic)
            overall_title = chart_output_dets[mg.CHARTS_OVERALL_TITLE]
            charts_append_divider(
                html, titles, overall_title, indiv_title, 'Bar Chart')
        if debug: 
            print(f'y_title_offset: {y_title_offset}, '
                f'margin_offset_l: {margin_offset_l}')
        """
        zero padding chart_idx so that when we search and replace, and go to
        replace Renumber1 with Renumber15, we don't change Renumber16 to
        Renumber156 ;-)
        """
        html.append('<div style="clear: both;">&nbsp;&nbsp;</div>')
        if page_break_after:
            html.append(
                f"<br><hr><br><div class='{CSS_PAGE_BREAK_BEFORE}'></div>")
        return "".join(html)

    @staticmethod
    def clustered_barchart_output(titles, subtitles, x_title, y_title, 
            chart_output_dets, css_idx, css_fpath, *,
            rotate, show_n, show_borders, page_break_after):
        """
        :param list titles: list of title lines correct styles
        :param list subtitles: list of subtitle lines
        :param dict chart_output_dets: see structure_gen_data()
         var_numeric -- needs to be quoted or not.
         xaxis_dets -- [(1, "Under 20"), (2, "20-29"), (3, "30-39"),
             (4, "40-64"), (5, "65+")]
        :param int css_idx: css index so can apply appropriate css styles
        """
        debug = False
        axis_lbl_rotate = -90 if rotate else 0
        html = []
        multichart = len(chart_output_dets[mg.CHARTS_CHART_DETS]) > 1
        CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (
            mg.CSS_PAGE_BREAK_BEFORE, css_idx)
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
        height += axis_lbl_drop  ## compensate for loss of bar display height
        """
        For each series, set colour details.

        For the collection of series as a whole, set the highlight mapping from
        each series colour.

        From dojox.charting.action2d.Highlight but with extraneous % removed
        """
        css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fpath)
        chart_dets = chart_output_dets[mg.CHARTS_CHART_DETS]
        ## following details are same across all charts so look at first
        chart0_series_dets = chart_dets[0][mg.CHARTS_SERIES_DETS]
        n_bars_in_cluster = len(chart0_series_dets)
        n_clusters = len(chart0_series_dets[0][mg.CHARTS_XAXIS_DETS])
        max_lbl_width = TXT_WIDTH_WHEN_ROTATED if rotate else max_x_lbl_len
        (width, xgap, xfontsize, minor_ticks,
         init_margin_offset_l) = BarChart._get_barchart_sizings(
                    x_title, n_clusters, n_bars_in_cluster, max_lbl_width)
        series_det = chart0_series_dets[0]
        xaxis_dets = series_det[mg.CHARTS_XAXIS_DETS]
        idx_1st_xdets = 0
        idx_xlbl = 1
        x_lbl_len = len(xaxis_dets[idx_1st_xdets][idx_xlbl])
        max_safe_x_lbl_len_pxls = 180
        y_title_offset = Titles.get_ytitle_offset(max_y_lbl_len, x_lbl_len,
            max_safe_x_lbl_len_pxls, rotate=rotate)
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
        series_colours_by_lbl = get_series_colours_by_lbl(
            chart_output_dets, css_fpath)
        stroke_width = css_dojo_dic['stroke_width'] if show_borders else 0
        ## loop through charts
        for chart_idx, chart_det in enumerate(chart_dets):
            n_chart = ('N = ' + lib.formatnum(chart_det[mg.CHARTS_CHART_N])
                if show_n else '')
            series_dets = chart_det[mg.CHARTS_SERIES_DETS]
            if debug: print(series_dets)
            legend = """
            <p style="float: left; font-weight: bold; margin-right: 12px; 
                    margin-top: 9px;">
                %s:
            </p>
            <div id="legendMychartRenumber%02d">
                </div>""" % (legend_lbl, chart_idx)
            indiv_title, indiv_title_html = Titles.get_indiv_title(
                multichart, chart_det)
            single_colour = False
            override_first_highlight = (
                (css_fpath == mg.DEFAULT_CSS_PATH)
                and single_colour)
            colour_cases = setup_highlights(css_dojo_dic['colour_mappings'],
                single_colour, override_first_highlight)
            series_js_list = []
            series_names_list = []
            for series_idx, series_det in enumerate(series_dets):
                series_lbl = series_det[mg.CHARTS_SERIES_LBL_IN_LEGEND]
                xaxis_dets = series_det[mg.CHARTS_XAXIS_DETS]
                lbl_dets = get_lbl_dets(xaxis_dets)
                xaxis_lbls = '[' + ',\n            '.join(lbl_dets) + ']'
                series_names_list.append(f'series{series_idx}')
                series_js_list.append(f'var series{series_idx} = new Array();')
                series_js_list.append(
                    f'series{series_idx}["seriesLabel"] = "{series_lbl}";')
                series_y_vals = series_det[mg.CHARTS_SERIES_Y_VALS]
                series_js_list.append(
                    f'series{series_idx}["yVals"] = {series_y_vals};')
                fill = series_colours_by_lbl[series_lbl]
                tooltips = ("['"
                    + "', '".join(series_det[mg.CHARTS_SERIES_TOOLTIPS])
                    + "']")
                series_js_list.append(
                f'series{series_idx}["options"] = {{'
                    'stroke: {'
                        'color: "white", '
                        f'width: "{stroke_width}px"'
                    '}, '
                    f'fill: "{fill}", '
                    f'yLbls: {tooltips}'
                '};')
                series_js_list.append('')
                series_js = '\n    '.join(series_js_list)
                new_array = ', '.join(series_names_list)
                series_js += f'\n    var series = new Array({new_array});'
                series_js = series_js.lstrip()
            chart_settings_dic = {
                'axis_font_colour': css_dojo_dic['axis_font_colour'],
                'axis_lbl_drop': lib.if_none(axis_lbl_drop, 30),
                'axis_lbl_rotate': lib.if_none(axis_lbl_rotate, 0),
                'chart_bg': lib.if_none(css_dojo_dic['chart_bg'], 'null'),
                'chart_idx': '%02d' % chart_idx,
                'colour_cases': colour_cases,
                'connector_style': lib.if_none(css_dojo_dic['connector_style'], 'defbrown'),
                'gridline_width': lib.if_none(css_dojo_dic['gridline_width'], 3),
                'height': height,
                'indiv_title_html': indiv_title_html,
                'legend': legend,  ## clustered bar charts use this 
                'major_gridline_colour': css_dojo_dic['major_gridline_colour'],
                'margin_offset_l': lib.if_none(margin_offset_l, 0),
                'minor_ticks':lib.if_none( minor_ticks, 'false'),
                'n_chart': lib.if_none(n_chart, "''"),
                'pagebreak': '',  ## not used with clustered bar charts
                'plot_bg': css_dojo_dic['plot_bg'],
                'plot_font_colour': css_dojo_dic['plot_font_colour'],
                'plot_font_colour_filled': lib.if_none(css_dojo_dic['plot_font_colour_filled'], 'black'),
                'series_js': series_js,
                'tooltip_border_colour': lib.if_none(css_dojo_dic['tooltip_border_colour'], '#ada9a5'),
                'width': width,
                'x_title': lib.if_none(x_title, "''"),
                "xaxis_lbls": xaxis_lbls,
                "xfontsize": xfontsize,
                "xgap": xgap,
                "y_title": y_title,
                "y_title_offset": lib.if_none(y_title_offset, 0),
                "ymax": ymax,
            }
            BarChart._add_dojo_html_js(html, chart_settings_dic)
            overall_title = chart_output_dets[mg.CHARTS_OVERALL_TITLE]
            charts_append_divider(
                html, titles, overall_title, indiv_title, 'Clust Bar')
        if debug: 
            print(f'y_title_offset: {y_title_offset}, '
                f'margin_offset_l: {margin_offset_l}')
        html.append('<div style="clear: both;">&nbsp;&nbsp;</div>')
        if page_break_after:
            html.append(
                f"<br><hr><br><div class='{CSS_PAGE_BREAK_BEFORE}'></div>")
        return "".join(html)


class BoxPlotDets:

    """
    Lots of shared state as different categories and series change the overall
    attributes of the chart e.g. max y axis. So using object rather than static
    methods.
    """

    def __init__(self, *, dbe, cur, tbl, tbl_filt, flds, var_role_dic,
            sort_opt, rotate, boxplot_opt):
        self.first_chart_by = True
        self.y_display_min = None
        self.y_display_max = 0
        self.xaxis_dets = []  ## (0, "''", "''")]
        self.max_x_lbl_len = 0
        self.max_lbl_lines = 0
        self.any_missing_boxes = False
        self.any_displayed_boxes = False
        self.n_chart = 0  ## Note -- only ever one boxplot chart (no matter how many series)
        self.dbe = dbe
        self.cur = cur
        self.tbl = tbl
        self.tbl_filt = tbl_filt
        self.flds = flds
        self.var_role_dic = var_role_dic
        self.sort_opt = sort_opt
        self.rotate = rotate
        self.boxplot_opt = boxplot_opt
        objqtr = getdata.get_obj_quoter_func(self.dbe)
        where_tbl_filt, and_tbl_filt = lib.FiltLib.get_tbl_filts(tbl_filt)
        self.sql_dic = {
            'var_role_cat': objqtr(var_role_dic['cat']),
            'var_role_series': objqtr(var_role_dic['series']),
            'var_role_desc': objqtr(var_role_dic['desc']),
            'where_tbl_filt': where_tbl_filt,
            'and_tbl_filt': and_tbl_filt,
            'tbl': getdata.tblname_qtr(self.dbe, self.tbl)}

    def _get_series_vals(self):
        debug = False
        if self.var_role_dic['series']:
            SQL_series_vals = """SELECT {var_role_series}
                FROM {tbl}
                WHERE {var_role_series} IS NOT NULL
                AND {var_role_cat} IS NOT NULL
                AND {var_role_desc} IS NOT NULL
                {and_tbl_filt}
                GROUP BY {var_role_series}""".format(**self.sql_dic)
            if debug: print(SQL_series_vals)
            self.cur.execute(SQL_series_vals)
            series_vals = [x[0] for x in self.cur.fetchall()]
            if debug: print(series_vals)
            n_boxplot_series = len(series_vals)
            if n_boxplot_series > mg.MAX_SERIES_IN_BOXPLOT:
                if wx.MessageBox(
                        _("This chart will have %(n_boxplot_series)s "
                        "%(var_role_cat)s series and may not display properly. "
                        "Do you wish to make it anyway?") % {
                            "n_boxplot_series": n_boxplot_series,
                            "var_role_cat": self.var_role_dic['cat']
                        },
                        caption=_('HIGH NUMBER OF SERIES'),
                        style=wx.YES_NO) == wx.NO:
                    raise my_exceptions.TooManySeriesInChart(
                        mg.MAX_SERIES_IN_BOXPLOT)
        else:
            series_vals = [None, ]  ## Got to have something to loop through ;-)
        return series_vals

    def _get_sorted_cat_vals(self):
        """
        Get category values (sorted if requested) with raw values and display
        values. Where categories are unlabeled numeric values the display value
        will honour the max display decimal place selected by the user. E.g. if
        the raw value is 1.1234 then the display value will be 1.1.
        """
        debug = False
        if self.var_role_dic['cat']: # might just be a single box e.g. a box for age overall
            and_series_filt = ('' if not self.var_role_dic['series']
                else " AND {var_role_series} IS NOT NULL ".format(**self.sql_dic))
            self.sql_dic['and_series_filt'] = and_series_filt
            SQL_cat_vals = """SELECT {var_role_cat}
                FROM {tbl}
                WHERE {var_role_cat} IS NOT NULL
                AND {var_role_desc} IS NOT NULL
                {and_series_filt}
                {and_tbl_filt}
                GROUP BY {var_role_cat}""".format(**self.sql_dic)
            if debug: print(SQL_cat_vals)
            try:
                self.cur.execute(SQL_cat_vals)
            except Exception:
                print(SQL_cat_vals)
                raise
            cat_vals = [x[0] for x in self.cur.fetchall()]
            ## sort appropriately
            cat_vals_and_lbls = [(x, self.var_role_dic['cat_lbls'].get(x, x))
                for x in cat_vals]
            if self.sort_opt == mg.SORT_LBL_KEY:
                cat_vals_and_lbls.sort(key=itemgetter(1))
            sorted_cat_raw_vals = [x[0] for x in cat_vals_and_lbls]
            sorted_cat_display_vals = lib.OutputLib.get_best_x_lbls(
                xs_maybe_used_as_lbls=sorted_cat_raw_vals)
            if debug: print(sorted_cat_display_vals)
            n_boxplots = len(sorted_cat_raw_vals)
            if n_boxplots > mg.MAX_BOXPLOTS_IN_SERIES:
                msg = _("This chart will have %(n_boxplots)s series by "
                    "%(var_role_cat)s and may not display properly. Do you wish"
                    " to make it anyway?") % {"n_boxplots": n_boxplots,
                    "var_role_cat": self.var_role_dic['cat']}
                if wx.MessageBox(msg, caption=_("HIGH NUMBER OF SERIES"),
                        style=wx.YES_NO) == wx.NO:
                    raise my_exceptions.TooManyBoxplotsInSeries(
                        self.var_role_dic['cat_name'],
                        max_items=mg.MAX_BOXPLOTS_IN_SERIES)
            sorted_cat_vals = list(
                zip(sorted_cat_raw_vals, sorted_cat_display_vals))
        else:
            sorted_cat_vals = [(1, 1), ]  ## the first boxplot is always 1 on the x-axis
        return sorted_cat_vals

    def _get_box_dets(self, i, *, raw_cat_val, display_cat_val, legend_lbl):
        """
        Get details for specific box for category e.g. Japan. Also get details
        for boxes as a whole e.g. max y display value.
        """
        debug = False
        boxplot_width = 0.25
        if self.var_role_dic['cat']:
            x_val_lbl = self.var_role_dic['cat_lbls'].get(
                raw_cat_val, str(display_cat_val))
            if self.first_chart_by:  ## build xaxis_dets once
                (x_val_split_lbl,
                 actual_lbl_width,
                 n_lines) = lib.OutputLib.get_lbls_in_lines(
                     orig_txt=x_val_lbl, max_width=17, dojo=True, rotate=self.rotate)
                if actual_lbl_width > self.max_x_lbl_len:
                    self.max_x_lbl_len = actual_lbl_width
                if n_lines > self.max_lbl_lines:
                    self.max_lbl_lines = n_lines
                self.xaxis_dets.append((i, x_val_lbl, x_val_split_lbl))
            ## Now see if any desc values for particular series_val and cat_val
            val_clause = getdata.make_fld_val_clause(
                self.dbe, self.flds, fldname=self.var_role_dic['cat'], val=raw_cat_val)
            and_cat_val_filt = f' AND {val_clause}'
        else:
            self.xaxis_dets.append((i, "''", "''"))
            and_cat_val_filt = ''
        self.sql_dic['and_cat_val_filt'] = and_cat_val_filt
        SQL_vals2desc = """SELECT {var_role_desc}
        FROM {tbl}
        WHERE {var_role_desc} IS NOT NULL
        {and_cat_val_filt}
        {and_series_val_filt}
        {and_tbl_filt}""".format(**self.sql_dic)
        self.cur.execute(SQL_vals2desc)
        vals2desc = [x[0] for x in self.cur.fetchall()]
        n_vals = len(vals2desc)
        has_vals = (n_vals > 0)
        if has_vals:
            median = np.median(vals2desc)
            lq, uq = core_stats.get_quartiles(vals2desc)
            lbox = lq
            ubox = uq
            if debug: print(f'{lbox} {median} {ubox}')
        boxplot_display = has_vals
        if not boxplot_display:
            self.any_missing_boxes = True
            box_dic = {mg.CHART_BOXPLOT_WIDTH: boxplot_width,
                mg.CHART_BOXPLOT_DISPLAY: boxplot_display,
                mg.CHART_BOXPLOT_LWHISKER: None,
                mg.CHART_BOXPLOT_LWHISKER_ROUNDED: None,
                mg.CHART_BOXPLOT_LBOX: None,
                mg.CHART_BOXPLOT_MEDIAN: None,
                mg.CHART_BOXPLOT_UBOX: None,
                mg.CHART_BOXPLOT_UWHISKER: None,
                mg.CHART_BOXPLOT_OUTLIERS: None,
                mg.CHART_BOXPLOT_INDIV_LBL: None}
        else:
            self.any_displayed_boxes = True
            min_measure = min(vals2desc)
            max_measure = max(vals2desc)
            ## whiskers
            if self.boxplot_opt == mg.CHART_BOXPLOT_MIN_MAX_WHISKERS:
                lwhisker = min_measure
                uwhisker = max_measure
            elif self.boxplot_opt in (mg.CHART_BOXPLOT_HIDE_OUTLIERS,
                    mg.CHART_BOXPLOT_1_POINT_5_IQR_OR_INSIDE):
                iqr = ubox - lbox
                raw_lwhisker = lbox - (1.5*iqr)
                lwhisker = BoxPlot._get_lwhisker(
                    raw_lwhisker, lbox, vals2desc)
                raw_uwhisker = ubox + (1.5*iqr)
                uwhisker = BoxPlot._get_uwhisker(
                    raw_uwhisker, ubox, vals2desc)
            ## outliers
            if self.boxplot_opt == mg.CHART_BOXPLOT_1_POINT_5_IQR_OR_INSIDE:
                outliers = [x for x in vals2desc
                    if x < lwhisker or x > uwhisker]
                outliers_rounded = [
                    round(x, mg.DEFAULT_REPORT_DP) for x in vals2desc
                    if x < lwhisker or x > uwhisker]
            else:
                outliers = []  ## hidden or inside whiskers
                outliers_rounded = []
            ## setting y-axis
            if self.boxplot_opt == mg.CHART_BOXPLOT_HIDE_OUTLIERS:
                min2display = lwhisker
                max2display = uwhisker
            else:
                min2display = min_measure
                max2display = max_measure
            if self.y_display_min is None:
                self.y_display_min = min2display
            elif min2display < self.y_display_min:
                self.y_display_min = min2display
            if max2display > self.y_display_max:
                self.y_display_max = max2display
            ## labels
            lblbits = []
            if self.var_role_dic['cat']:
                lblbits.append(x_val_lbl)
            if legend_lbl:
                lblbits.append(legend_lbl)
            ## assemble
            box_dic = {mg.CHART_BOXPLOT_WIDTH: boxplot_width,
                mg.CHART_BOXPLOT_DISPLAY: boxplot_display,
                mg.CHART_BOXPLOT_LWHISKER: lwhisker,
                mg.CHART_BOXPLOT_LWHISKER_ROUNDED: round(lwhisker,
                    mg.DEFAULT_REPORT_DP),
                mg.CHART_BOXPLOT_LBOX: lbox,
                mg.CHART_BOXPLOT_LBOX_ROUNDED: round(lbox,
                    mg.DEFAULT_REPORT_DP),
                mg.CHART_BOXPLOT_MEDIAN: median,
                mg.CHART_BOXPLOT_MEDIAN_ROUNDED: round(median,
                    mg.DEFAULT_REPORT_DP),
                mg.CHART_BOXPLOT_UBOX: ubox,
                mg.CHART_BOXPLOT_UBOX_ROUNDED: round(ubox,
                    mg.DEFAULT_REPORT_DP),
                mg.CHART_BOXPLOT_UWHISKER: uwhisker,
                mg.CHART_BOXPLOT_UWHISKER_ROUNDED: round(uwhisker,
                    mg.DEFAULT_REPORT_DP),
                mg.CHART_BOXPLOT_OUTLIERS: outliers,
                mg.CHART_BOXPLOT_OUTLIERS_ROUNDED: outliers_rounded,
                mg.CHART_BOXPLOT_INDIV_LBL: ', '.join(lblbits)}
        return {mg.BOX_DIC: box_dic, mg.BOX_N_VALS: n_vals}

    def _get_boxdet_series_dets(self, sorted_cat_vals, legend_lbl):
        boxdet_series = []
        for i, (raw_cat_val, display_cat_val) in enumerate(sorted_cat_vals, 1):  ## e.g. "Mt Albert Grammar", 
                ## "Epsom Girls Grammar", "Hebron Christian College", ...
            box_dets = self._get_box_dets(i,
                raw_cat_val=raw_cat_val, display_cat_val=display_cat_val,
                legend_lbl=legend_lbl)
            self.n_chart += box_dets[mg.BOX_N_VALS]
            boxdet_series.append(box_dets[mg.BOX_DIC])
        return boxdet_series

    def get_boxplot_dets(self):
        """
        Desc, Category, Series correspond to dropdown 1-3 respectively. E.g. if
        the averaged variable is age, the split within the series is gender, and
        the different series (each with own colour) is country, we have var desc
        = age, var cat = gender, and var series = country.

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

        http://en.wikipedia.org/wiki/Box_plot: the default,
        CHART_BOXPLOT_1_POINT_5_IQR_OR_INSIDE, is one of several options: the
        lowest datum still within 1.5 IQR of the lower quartile, and the highest
        datum still within 1.5 IQR of the upper quartile.
        """
        debug = False
        chart_dets = []
        ## 1) What are our series to display? If there is no data for an entire
        ## series, we want to leave it out. E.g. if country = Palau has no skiing
        ## data it won't appear as a series. So get all series vals appearing in
        ## any rows where all fields are non-missing. If a series even has one
        ## value, we show the series and a box plot for every category that has a
        ## value to be averaged, even if only one value (resulting in a single
        ## line rather than a box as such).
        series_vals = self._get_series_vals()
        ## 2) Get all cat vals needed for x-axis i.e. all those appearing in any
        ## rows where all fields are non-missing.
        sorted_cat_vals = self._get_sorted_cat_vals()
        for series_val in series_vals:  ## e.g. "Boys" and "Girls"
            if series_val is not None:
                legend_lbl = self.var_role_dic['series_lbls'].get(series_val,
                    str(series_val))
                series_val_filt = getdata.make_fld_val_clause(
                    self.dbe, self.flds,
                    fldname=self.var_role_dic['series'], val=series_val)
                and_series_val_filt = f' AND {series_val_filt}'
            else:
                legend_lbl = None
                and_series_val_filt = ' '
            self.sql_dic['and_series_val_filt'] = and_series_val_filt
            ## time to get the boxplot information for the series
            boxdet_series_dets = self._get_boxdet_series_dets(
                sorted_cat_vals, legend_lbl)
            title_bits = []
            title_bits.append(self.var_role_dic['desc_name'])
            cat_name = self.var_role_dic['cat_name']
            title_bits.append(f'By {cat_name}')
            if self.var_role_dic['series_name']:
                series_name = self.var_role_dic['series_name']
                title_bits.append(f'By {series_name}')
            overall_title = ' '.join(title_bits)
            series_dic = {
                mg.CHART_SERIES_LBL: legend_lbl,
                mg.CHART_BOXDETS: boxdet_series_dets}
            chart_dets.append(series_dic)
            self.first_chart_by = False
        if not self.any_displayed_boxes:
            raise my_exceptions.TooFewBoxplotsInSeries
        xmin = 0.5
        xmax = len(sorted_cat_vals) + 0.5
        y_display_min, y_display_max = _get_optimal_min_max(
            self.y_display_min, self.y_display_max)
        if debug: print(self.xaxis_dets)
        return (self.n_chart, self.xaxis_dets,
            xmin, xmax,
            y_display_min, y_display_max,
            self.max_x_lbl_len, self.max_lbl_lines,
            overall_title, chart_dets, self.any_missing_boxes)


class BoxPlot:

    @staticmethod
    def _add_dojo_html_js(html, chart_settings_dic):
        html.append("""
        <script type="text/javascript">

        makechartRenumber00 = function(){{
            {pre_series_str}
            {series_js_str}
            var conf = new Array();
            conf["axis_font_colour"] = "{axis_font_colour}";
            conf["axis_lbl_drop"] = {axis_lbl_drop};
            conf["axis_lbl_rotate"] = {axis_lbl_rotate};
            conf["chart_bg"] = "{chart_bg}";
            conf["connector_style"] = "{connector_style}";
            conf["gridline_width"] = {gridline_width};
            conf["highlight"] = {highlight};
            conf["major_gridline_colour"] = "{major_gridline_colour}";
            conf["margin_offset_l"] = {margin_offset_l};
            conf["minor_ticks"] = {minor_ticks};
            conf["n_chart"] = "{n_chart}";
            conf["plot_bg"] = "{plot_bg}";
            conf["plot_font_colour"] = "{plot_font_colour}";
            conf["plot_font_colour_filled"] = "{plot_font_colour_filled}";
            conf["tooltip_border_colour"] = "{tooltip_border_colour}";
            conf["xaxis_lbls"] = {xaxis_lbls};
            conf["xfontsize"] = {xfontsize};
            conf["xmax"] = {xmax};
            conf["xmin"] = {xmin};
            conf["x_title"] = "{x_title}";
            conf["yfontsize"] = {yfontsize};
            conf["ymax"] = {ymax};
            conf["ymin"] = {ymin};
            conf["y_title_offset"] = {y_title_offset};
            conf["y_title"] = "{y_title}";
            makeBoxAndWhisker("mychartRenumber00", series, seriesconf, conf);
        }}
        </script>
        {titles}

        <div class="screen-float-only" style="margin-right: 10px; {pagebreak}">

            <div id="mychartRenumber00" 
                style="width: {width}px; height: {height}px;">
            </div>
            <div id="dummychartRenumber00" 
                style="float: right; width: 100px; height: 100px; visibility: hidden;">
                <!--needs width and height for IE 6 so must float to keep out of way-->
            </div>
            {legend}
            <p>{display_dets}</p>
        </div>""".format(**chart_settings_dic))

    @staticmethod
    def get_boxplot_dets(
            dbe, cur, tbl, tbl_filt, flds, var_role_dic, sort_opt, *,
            rotate=False, boxplot_opt=mg.CHART_BOXPLOT_1_POINT_5_IQR_OR_INSIDE):
        """
        Desc, Category, Series correspond to dropdown 1-3 respectively. E.g. if
        the averaged variable is age, the split within the series is gender, and
        the different series (each with own colour) is country, we have var desc
        = age, var cat = gender, and var series = country.

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

        http://en.wikipedia.org/wiki/Box_plot: the default,
        CHART_BOXPLOT_1_POINT_5_IQR_OR_INSIDE, is one of several options: the
        lowest datum still within 1.5 IQR of the lower quartile, and the highest
        datum still within 1.5 IQR of the upper quartile.
        """
        boxplot_dets = BoxPlotDets(
            dbe=dbe, cur=cur, tbl=tbl, tbl_filt=tbl_filt, flds=flds,
            var_role_dic=var_role_dic,
            sort_opt=sort_opt, rotate=rotate, boxplot_opt=boxplot_opt)
        return boxplot_dets.get_boxplot_dets()

    @staticmethod
    def _get_lwhisker(raw_lwhisker, lbox, measure_vals):
        """
        Make no lower than the minimum value within (inclusive) 1.5*iqr below lq.
        Must never go above lbox.
        """
        lwhisker = raw_lwhisker  ## init
        measure_vals.sort()  ## no side effects
        for val in measure_vals:  ## going upwards
            if val < raw_lwhisker:
                pass  ## keep going up
            elif val >= raw_lwhisker:
                lwhisker = val
                break
        if lwhisker > lbox:
            lwhisker = lbox
        return lwhisker

    @staticmethod
    def _get_uwhisker(raw_uwhisker, ubox, measure_vals):
        """
        Make sure no higher than the maximum value within (inclusive)
        1.5*iqr above uq. Must never fall below ubox.
        """
        uwhisker = raw_uwhisker  ## init
        measure_vals.reverse()  ## no side effects
        for val in measure_vals:  ## going downwards
            if val > raw_uwhisker:
                pass  ## keep going down
            elif val <= raw_uwhisker:
                uwhisker = val
                break
        if uwhisker < ubox:
            uwhisker = ubox
        return uwhisker

    @staticmethod
    def _get_boxplot_sizings(x_title, xaxis_dets, max_lbl_width, series_dets):
        debug = False
        n_cats = len(xaxis_dets)
        n_series = len(series_dets)
        PADDING_PXLS = 50
        MIN_PXLS_PER_BOX = 30
        MIN_CHART_WIDTH = 200 if len(xaxis_dets) == 1 else 400 # only one box
        min_pxls_per_cat = MIN_PXLS_PER_BOX*n_series
        width_per_cat = (max([min_pxls_per_cat,
            max_lbl_width*AVG_CHAR_WIDTH_PXLS]) + PADDING_PXLS)
        width_x_title = len(x_title)*AVG_CHAR_WIDTH_PXLS + PADDING_PXLS
        width = max([width_per_cat*n_cats, width_x_title, MIN_CHART_WIDTH])
        minor_ticks = "true" if n_cats > 10 else "false"
        if n_cats <= 5:
            xfontsize = 10
        elif n_cats > 10:
            xfontsize = 8
        else:
            xfontsize = 9
        if debug: print(width, xfontsize)
        return width, xfontsize, minor_ticks

    @staticmethod
    def boxplot_output(
            titles, subtitles, x_title, y_title, overall_title,
            var_role_series_name, n_chart,
            xaxis_dets, max_x_lbl_len, max_lbl_lines,
            chart_dets, boxplot_opt,
            css_fpath, css_idx,
            xmin, xmax, ymin, ymax, *,
            any_missing_boxes, rotate, show_n, page_break_after):
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
        n_chart = f'N = {n_chart:,}' if show_n else ''
        display_dets = mg.CHART_BOXPLOT_OPTIONS2LABELS.get(boxplot_opt, "")
        axis_lbl_rotate = -90 if rotate else 0
        CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (
            mg.CSS_PAGE_BREAK_BEFORE, css_idx)
        title_dets_html = output.get_title_dets_html(titles, subtitles, css_idx)
        lbl_dets = get_lbl_dets(xaxis_dets)
        lbl_dets.insert(0, """{value: 0, text: ""}""")
        lbl_dets.append("""{value: %s, text: ""}""" % len(lbl_dets))
        xaxis_lbls = "[" + ",\n            ".join(lbl_dets) + "]"
        multichart = False # currently by design
        axis_lbl_drop = get_axis_lbl_drop(multichart, rotate, max_lbl_lines)
        height = 350
        if rotate:
            height += AVG_CHAR_WIDTH_PXLS*max_x_lbl_len 
        height += axis_lbl_drop
        max_lbl_width = TXT_WIDTH_WHEN_ROTATED if rotate else max_x_lbl_len
        (width, xfontsize,
            minor_ticks) = BoxPlot._get_boxplot_sizings(x_title, xaxis_dets,
                max_lbl_width, chart_dets)
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
        max_y_lbl_len = len(str(int(ymax)))
        max_safe_x_lbl_len_pxls = 180
        y_title_offset = Titles.get_ytitle_offset(max_y_lbl_len, x_lbl_len,
            max_safe_x_lbl_len_pxls, rotate=rotate) 
        margin_offset_l = (init_margin_offset_l + y_title_offset
            - DOJO_YTITLE_OFFSET_0)
        if rotate:
            margin_offset_l += 10
        html = []
        if any_missing_boxes:
            html.append("<p>At least one box will not be displayed because "
                "there was no data in that category and series</p>")
        """
        For each series, set colour details.

        For the collection of series as a whole, set the highlight mapping from 
        each series colour.

        From dojox.charting.action2d.Highlight but with extraneous % removed
        """
        css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fpath)
        """
        Build js for every series. colour_mappings - take first of each pair to
        use as outline of box plots, and use getfainthex() to get lighter colour
        for interior (so we can see the details of the median line) and an even
        lighter version for the highlight. The css-defined highlight is good for
        bar charts etc where change is the key, not visibility of interior
        details.
        """
        if debug:
            print(chart_dets)
        pagebreak = "page-break-after: always;"
        n_series = len(chart_dets)
        n_boxes = len(chart_dets[0][mg.CHART_BOXDETS])
        """
        For each box, we need to identify the centre. For this we need to know
        the number of boxes, where the first one starts, and the horizontal jump
        rightwards for each one (= the gap which is width + extra breathing
        space).
        """
        if n_boxes == 0:
            raise Exception("Box count of 0")
        n_gaps = n_series - 1
        shrinkage = n_series*0.6
        gap = 0.4/shrinkage
        pre_series = []
        bar_width = mg.CHART_BOXPLOT_WIDTH/shrinkage
        pre_series.append(f'    var width = {bar_width};')
        pre_series.append("    var seriesconf = new Array();")
        pre_series.append("    var seriesdummy = [];")
        pre_series_str = "\n".join(pre_series)
        offset_start = -((gap*n_gaps)/2.0) # if 1 box, offset = 0 i.e. middle
        offsets = [offset_start + (x*gap) for x in range(n_series)]
        series_js = []
        if var_role_series_name:
            legend = """
        <p style="float: left; font-weight: bold; margin-right: 12px; 
                margin-top: 9px;">
            %s:
        </p>
        <div id="legendMychartRenumber00">
            </div>""" % var_role_series_name
        else:
            legend = "" 
        for series_idx, series_det in enumerate(chart_dets):
            """
            series_det -- [((lwhisker, lbox, median, ubox, uwhisker, outliers), 
                    (lwhisker etc), ...),
                   ...] # list of subseries tuples each of which has a tuple 
                          per box.
            We flatten out the series and do it across and back across for 
                each sub series.
            """
            series_js.append("    // series%s" % series_idx)
            try:
                stroke = css_dojo_dic['colour_mappings'][series_idx][0]
            except IndexError:
                stroke = mg.DOJO_COLOURS[series_idx]
            series_js.append("    var strokecol%s = \"%s\";" % (series_idx, 
                stroke))
            series_js.append("    var fillcol%s = getfainthex(strokecol%s);" 
                % (series_idx, series_idx))
            series_js.append("    seriesconf[%(series_idx)s] = {seriesLabel: "
                "\"%(series_lbl)s\", "
                "seriesStyle: {stroke: {color: strokecol%(series_idx)s, "
                "width: \"1px\"}, fill: fillcol%(series_idx)s}};"
                % {"series_idx": series_idx, 
                "series_lbl": series_det[mg.CHART_SERIES_LBL]})
            series_js.append("    var series%(series_idx)s = [" 
                % {"series_idx": series_idx})
            offset = offsets[series_idx]
            box_js = [] 
            for boxdet_idx, boxdet in enumerate(series_det[mg.CHART_BOXDETS]):
                if not boxdet[mg.CHART_BOXPLOT_DISPLAY]:
                    continue
                unique_name = "%s%s" % (series_idx, boxdet_idx)
                box_js.append("""        {{seriesLabel: "dummylabel{unique_name}",
            boxDets: {{stroke: strokecol{series_idx}, fill: fillcol{series_idx},
                      center: {boxdets_idx} + 1 + {offset}, width: width,
                      summary_data: {{
                          {lwhisker}: {lwhisker_val}, {lwhisker_rounded}: {lwhisker_val_rounded},
                          {lbox}: {lbox_val}, {lbox_rounded}: {lbox_val_rounded},
                          {median}: {median_val}, {median_rounded}: {median_val_rounded},
                          {ubox}: {ubox_val}, {ubox_rounded}: {ubox_val_rounded},
                          {uwhisker}: {uwhisker_val}, {uwhisker_rounded}: {uwhisker_val_rounded},
                          {outliers}: {outliers_val}, {outliers_rounded}: {outliers_val_rounded}
                          }},
                      indiv_boxlbl: "{indiv_boxlbl}"
                    }}
                }}""".format(
                unique_name=unique_name,
                series_idx=series_idx,
                boxdets_idx=boxdet_idx,
                offset=offset,
                lwhisker=mg.CHART_BOXPLOT_LWHISKER, lwhisker_val=boxdet[mg.CHART_BOXPLOT_LWHISKER],
                lwhisker_rounded=mg.CHART_BOXPLOT_LWHISKER_ROUNDED, lwhisker_val_rounded=boxdet[mg.CHART_BOXPLOT_LWHISKER_ROUNDED],
                lbox=mg.CHART_BOXPLOT_LBOX, lbox_val=boxdet[mg.CHART_BOXPLOT_LBOX],
                lbox_rounded=mg.CHART_BOXPLOT_LBOX_ROUNDED, lbox_val_rounded=boxdet[mg.CHART_BOXPLOT_LBOX_ROUNDED],
                median=mg.CHART_BOXPLOT_MEDIAN, median_val=boxdet[mg.CHART_BOXPLOT_MEDIAN],
                median_rounded=mg.CHART_BOXPLOT_MEDIAN_ROUNDED, median_val_rounded=boxdet[mg.CHART_BOXPLOT_MEDIAN_ROUNDED],
                ubox=mg.CHART_BOXPLOT_UBOX, ubox_val=boxdet[mg.CHART_BOXPLOT_UBOX],
                ubox_rounded=mg.CHART_BOXPLOT_UBOX_ROUNDED, ubox_val_rounded=boxdet[mg.CHART_BOXPLOT_UBOX_ROUNDED],
                uwhisker=mg.CHART_BOXPLOT_UWHISKER, uwhisker_val=boxdet[mg.CHART_BOXPLOT_UWHISKER],
                uwhisker_rounded=mg.CHART_BOXPLOT_UWHISKER_ROUNDED, uwhisker_val_rounded=boxdet[mg.CHART_BOXPLOT_UWHISKER_ROUNDED],
                outliers=mg.CHART_BOXPLOT_OUTLIERS, outliers_val=boxdet[mg.CHART_BOXPLOT_OUTLIERS],
                outliers_rounded=mg.CHART_BOXPLOT_OUTLIERS_ROUNDED, outliers_val_rounded=boxdet[mg.CHART_BOXPLOT_OUTLIERS_ROUNDED],
                indiv_boxlbl=boxdet[mg.CHART_BOXPLOT_INDIV_LBL]
                ))
            series_js.append(",\n".join(box_js))            
            series_js.append("        ];") # close series list
        series_lst = ["series%s" % x for x in range(len(chart_dets))]
        series_js.append("    var series = seriesdummy.concat(%s);" 
            % ", ".join(series_lst))
        series_js_str = "\n".join(series_js)
        chart_settings_dic = {
            "axis_font_colour": css_dojo_dic['axis_font_colour'],
            "axis_lbl_drop": lib.if_none(axis_lbl_drop, 30),
            "axis_lbl_rotate": lib.if_none(axis_lbl_rotate, 0),
            "chart_bg": lib.if_none(css_dojo_dic['chart_bg'], "null"),
            "connector_style": lib.if_none(css_dojo_dic['connector_style'], "defbrown"),
            "display_dets": display_dets,
            "gridline_width": lib.if_none(css_dojo_dic['gridline_width'], 3),
            "height": height,
            "highlight": "makefaint",
            "legend": legend,
            "major_gridline_colour": css_dojo_dic['major_gridline_colour'],
            "margin_offset_l": lib.if_none(margin_offset_l, 0),
            "minor_ticks": lib.if_none(minor_ticks, "false"),
            "n_chart": n_chart,
            "pagebreak": pagebreak,
            "plot_bg": css_dojo_dic['plot_bg'],
            "plot_font_colour": css_dojo_dic['plot_font_colour'],
            "plot_font_colour_filled": lib.if_none(css_dojo_dic['plot_font_colour_filled'], "black"),
            "pre_series_str": pre_series_str,
            "series_js_str": series_js_str,
            "titles": title_dets_html,
            "tooltip_border_colour": lib.if_none(css_dojo_dic['tooltip_border_colour'], "#ada9a5"),
            "width": width,
            "x_title": lib.if_none(x_title, "''"),
            "xaxis_lbls": xaxis_lbls,
            "xfontsize": xfontsize,
            "xmax": xmax,
            "xmin": xmin,
            "y_title": lib.if_none(y_title, "''"),
            "y_title_offset": lib.if_none(y_title_offset, 0),
            "yfontsize": yfontsize,
            "ymax": ymax,
            "ymin": ymin,
        }
        BoxPlot._add_dojo_html_js(html, chart_settings_dic)
        charts_append_divider(html, titles, overall_title, indiv_title="",
            item_type="Boxplot")
        if debug: 
            print("y_title_offset: %s, margin_offset_l: %s" % (y_title_offset,
                margin_offset_l))
        if page_break_after:
            html.append("<br><hr><br><div class='%s'></div>"
                % CSS_PAGE_BREAK_BEFORE)
        return "".join(html)


class Histo:

    @staticmethod
    def _add_dojo_html_js(html, chart_settings_dic):
        html.append("""
        <script type="text/javascript">

        var sofaHlRenumber{chart_idx} = function(colour){{
            var hlColour;
            switch (colour.toHex()){{
                {colour_cases}
                default:
                    hlColour = hl(colour.toHex());
                    break;
            }}
            return new dojox.color.Color(hlColour);
        }}

        makechartRenumber{chart_idx} = function(){{
            var datadets = new Array();
            datadets["seriesLabel"] = "{var_lbl}";
            datadets["yVals"] = {y_vals};
            datadets["normYs"] = {norm_ys};
            datadets["binLabels"] = [{bin_lbls}];
            datadets["style"] = {{
                stroke: {{
                    color: "white", width: "{stroke_width}px"
                }},
                fill: "{fill}"
            }};
            datadets["normStyle"] = {{
                plot: "normal", 
                stroke: {{
                    color: "{normal_curve_colour}", 
                    width: "{normal_stroke_width}px"
                }},
                fill: "{fill}"
            }};
            var conf = new Array();
            conf["axis_font_colour"] = "{axis_font_colour}";
            conf["chart_bg"] = "{chart_bg}";
            conf["connector_style"] = "{connector_style}";
            conf["gridline_width"] = {gridline_width};
            conf["highlight"] = sofaHlRenumber{chart_idx};
            conf["inc_normal"] = {js_inc_normal};
            conf["major_gridline_colour"] = "{major_gridline_colour}";
            conf["margin_offset_l"] = {margin_offset_l};
            conf["maxval"] = {maxval};
            conf["minval"] = {minval};
            conf["minor_ticks"] = {minor_ticks};
            conf["n_chart"] = "{n_chart}";
            conf["normal_curve_colour"] = "{normal_curve_colour}";
            conf["plot_bg"] = "{plot_bg}";
            conf["plot_font_colour"] = "{plot_font_colour}";
            conf["plot_font_colour_filled"] = "{plot_font_colour_filled}";
            conf["tooltip_border_colour"] = "{tooltip_border_colour}";
            conf["xaxis_lbls"] = {xaxis_lbls};
            conf["xfontsize"] = {xfontsize};
            conf["y_title_offset"] = {y_title_offset};
            conf["y_title"] = "{y_title}";
            makeHistogram("mychartRenumber{chart_idx}", datadets, conf);
        }}
        </script>

        <div class="screen-float-only" style="margin-right: 10px; {pagebreak}">
        {indiv_title_html}
            <div id="mychartRenumber{chart_idx}" 
                style="width: {width}px; height: {height}px;">
            </div>
        </div>""".format(**chart_settings_dic))

    @staticmethod
    def _get_histo_dp(combined_start, bin_width):
        """
        Only show as many decimal points as needed.

        E.g. if starts at 1 and bin width is 1 then we only need 0 dp. If bin
        width is 0.5 then we need 1 dp. If bin width is 0.01 we need 2 dp.

        There are not enough dps if the bin_width, or the start value, are
        changed by rounding themselves to that dp.

        combined_start -- if multiple histograms (e.g. one per country) we want
        to share the same bins. So what is the start for all of them combined?
        """
        dp = 0
        while True:
            enough = (round(bin_width, dp) == bin_width 
                and round(combined_start, dp) == combined_start)
            if enough or dp > 6:
                break
            dp += 1
        return dp

    @staticmethod
    def _get_histo_sizings(var_lbl, n_bins, minval, maxval):
        debug = False
        MIN_PXLS_PER_BAR = 30
        MIN_CHART_WIDTH = 700
        PADDING_PXLS = 5
        AVG_CHAR_WIDTH_PXLS = 10.5 # need more for histograms
        max_lbl_width = max(len(str(round(x,0))) for x in [minval, maxval])
        if debug: print("max_lbl_width: %s" % max_lbl_width)
        min_bin_width = max(max_lbl_width*AVG_CHAR_WIDTH_PXLS, MIN_PXLS_PER_BAR)
        width_x_title = len(var_lbl)*AVG_CHAR_WIDTH_PXLS + PADDING_PXLS
        width = max([n_bins*min_bin_width, width_x_title, MIN_CHART_WIDTH])
        if debug: print("Width: %s" % width)
        return width

    @staticmethod
    def get_histo_dets(dbe, cur, tbl, tbl_filt, flds, var_role_dic, inc_normal):
        """
        Make separate db call each histogram. Getting all values anyway and
        don't want to store in memory.

        Return list of dicts - one for each histogram. Each contains:
            CHARTS_XAXIS_DETS, CHARTS_SERIES_Y_VALS, CHART_MINVAL, CHART_MAXVAL,
            CHART_BIN_LBLS.
        xaxis_dets -- [(1, ""), (2: "", ...]
        y_vals -- [0.091, ...]
        bin_labels -- ["1 to under 2", "2 to under 3", ...]
        """
        debug = False
        objqtr = getdata.get_obj_quoter_func(dbe)
        unused, and_tbl_filt = lib.FiltLib.get_tbl_filts(tbl_filt)
        sql_dic = {"var_role_charts": objqtr(var_role_dic['charts']),
           "var_role_bin": objqtr(var_role_dic['bin']),
           "and_tbl_filt": and_tbl_filt,
           "tbl": getdata.tblname_qtr(dbe, tbl)}
        if var_role_dic['charts']:
            SQL_fld_chart_by_vals = """SELECT %(var_role_charts)s
                FROM %(tbl)s
                WHERE %(var_role_bin)s IS NOT NULL %(and_tbl_filt)s
                GROUP BY %(var_role_charts)s""" % sql_dic
            cur.execute(SQL_fld_chart_by_vals)
            fld_chart_by_vals = [x[0] for x in cur.fetchall()]
            if len(fld_chart_by_vals) > mg.MAX_CHARTS_IN_SET:
                raise my_exceptions.TooManyChartsInSeries(
                    var_role_dic['charts_name'],
                    max_items=mg.MAX_CHARTS_IN_SET)
        else:
            fld_chart_by_vals = [None,] # Got to have something to loop through ;-)
        """
        Set bins for all data at once. If only one histogram, then the perfect
        result for that. If multiple histograms, then ensures consistent bins to
        enable comparison. If multiple charts, we only handle saw-toothing for
        the overall data.
        """
        SQL_get_combined_vals = """SELECT %(var_role_bin)s 
        FROM %(tbl)s
        WHERE %(var_role_bin)s IS NOT NULL
            %(and_tbl_filt)s
        ORDER BY %(var_role_bin)s""" % sql_dic
        if debug: print(SQL_get_combined_vals)
        cur.execute(SQL_get_combined_vals)
        combined_vals = [x[0] for x in cur.fetchall()]
        if not combined_vals:
            raise Exception("No data to make histogram with.")
        # use nicest bins practical
        ## start by getting bins as per default code
        n_bins, lower_limit, upper_limit = lib.get_bins(min(combined_vals), 
            max(combined_vals), n_distinct=len(set(combined_vals)))
        (combined_y_vals, combined_start, 
         bin_width, unused) = core_stats.histogram(combined_vals, n_bins, 
            defaultreallimits=[lower_limit, upper_limit])
        ## make any saw-toothing corrections necessary
        (fixed_combined_y_vals, combined_start, 
         bin_width) = core_stats.fix_sawtoothing(combined_vals, n_bins, 
             combined_y_vals, combined_start, bin_width)
        # put any temporary hack overrides for combined_start, bin_width below here**************
        #combined_start = 100 # or whatever the starting number for the bins should be
        #bin_width = 10 # or whatever the width of the bins should be
        histo_dets = []
        for fld_chart_by_val in fld_chart_by_vals:
            if var_role_dic['charts']:
                filt = getdata.make_fld_val_clause(dbe, flds, 
                    fldname=var_role_dic['charts'],
                    val=fld_chart_by_val)
                and_fld_chart_by_filt = " and %s" % filt
                fld_chart_by_val_lbl = var_role_dic['charts_lbls'].get(
                    fld_chart_by_val, fld_chart_by_val)
                # must get y-vals for each chart individually
                sql_dic["and_fld_chart_by_filt"] = and_fld_chart_by_filt
                SQL_get_vals = """SELECT %(var_role_bin)s 
                    FROM %(tbl)s
                    WHERE %(var_role_bin)s IS NOT NULL
                        %(and_tbl_filt)s %(and_fld_chart_by_filt)s
                    ORDER BY %(var_role_bin)s""" % sql_dic
                if debug: print(SQL_get_vals)
                cur.execute(SQL_get_vals)
                vals = [x[0] for x in cur.fetchall()]
                if len(vals) < mg.MIN_HISTO_VALS:
                    raise my_exceptions.TooFewValsForDisplay(
                        min_n=mg.MIN_HISTO_VALS)
                defaultreallimits = [lower_limit, upper_limit]
                (y_vals, unused, unused, 
                 unused) = core_stats.histogram(vals, n_bins, defaultreallimits)
                vals4norm = vals
                chart_by_lbl = "%s: %s" % (var_role_dic['charts_name'],
                    fld_chart_by_val_lbl)
            else: # only one chart - combined values are the values we need
                y_vals = fixed_combined_y_vals
                vals4norm = combined_vals
                chart_by_lbl = None
            # not fixing saw-toothing 
            minval = combined_start
            dp = Histo._get_histo_dp(combined_start, bin_width) # only show as many decimal points as needed
            bin_ranges = [] # needed for labels
            bins = [] # needed to get y vals for normal dist curve
            start = combined_start
            for unused in y_vals:
                bin_start = round(start, dp)
                bins.append(bin_start)
                bin_end = round(start + bin_width, dp)
                start = bin_end
                bin_ranges.append((bin_start, bin_end))
            bin_lbls = [_("%(lower)s to < %(upper)s") % 
                {"lower": x[0], "upper": x[1]} for x in bin_ranges]
            bin_lbls[-1] = bin_lbls[-1].replace('<', '<=')
            maxval = bin_end
            xaxis_dets = [(x+1, '') for x in range(n_bins)]
            sum_yval = sum(y_vals)
            if inc_normal: # some things are done in code above that aren't needed if not generating norm curve but easier to leave in
                norm_ys = list(core_stats.get_normal_ys(vals4norm,
                    np.array(bins)))
                sum_norm_ys = sum(norm_ys)
                norm_multiplier = sum_yval/(1.0*sum_norm_ys)
                norm_ys = [x*norm_multiplier for x in norm_ys]
            else:
                norm_ys = []
            if debug: print(minval, maxval, xaxis_dets, y_vals, bin_lbls)
            title_bits = []
            title_bits.append(var_role_dic['bin_name'])
            if var_role_dic['charts_name']:
                title_bits.append("By %s"
                    % var_role_dic['charts_name'])
            overall_title = " ".join(title_bits)    
            histo_dic = {
                mg.CHARTS_CHART_LBL: chart_by_lbl,
                mg.CHARTS_CHART_N: lib.formatnum(sum_yval),
                mg.CHARTS_XAXIS_DETS: xaxis_dets,
                mg.CHARTS_SERIES_Y_VALS: y_vals,
                mg.CHART_NORMAL_Y_VALS: norm_ys,
                mg.CHART_MINVAL: minval,
                mg.CHART_MAXVAL: maxval,
                mg.CHART_BIN_LBLS: bin_lbls}
            histo_dets.append(histo_dic)
        return overall_title, histo_dets

    @staticmethod
    def histogram_output(titles, subtitles, var_lbl, overall_title, chart_dets,
            css_fpath, css_idx, *,
            inc_normal, show_n, show_borders, page_break_after=False):
        """
        See http://trac.dojotoolkit.org/ticket/7926 - he had trouble doing this
        then.

        titles -- list of title lines correct styles
        subtitles -- list of subtitle lines
        minval -- minimum values for x axis
        maxval -- maximum value for x axis
        xaxis_dets -- [(1, ""), (2, ""), ...] - 1-based idx
        y_vals -- list of values e.g. [12, 30, 100.5, -1, 40]
        bin_lbls -- ["1 to under 2", "2 to under 3", ...] for tooltips
        css_idx -- css index so can apply    
        """
        debug = False
        CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (
            mg.CSS_PAGE_BREAK_BEFORE, css_idx)
        multichart = (len(chart_dets) > 1)
        html = []
        title_dets_html = output.get_title_dets_html(titles, subtitles, css_idx)
        html.append(title_dets_html)
        height = 300 if multichart else 350
        css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fpath)
        single_colour = True
        override_first_highlight = (
            (css_fpath == mg.DEFAULT_CSS_PATH)
            and single_colour)
        colour_cases = setup_highlights(css_dojo_dic['colour_mappings'],
            single_colour, override_first_highlight)
        item_colours = output.colour_mappings_to_item_colours(css_dojo_dic['colour_mappings'])
        fill = item_colours[0]
        js_inc_normal = "true" if inc_normal else "false"
        init_margin_offset_l = 25
        yvals = []
        for chart_det in chart_dets:
            yvals.extend(chart_det[mg.CHARTS_SERIES_Y_VALS])
        xaxis_dets = chart_dets[0][mg.CHARTS_XAXIS_DETS]
        idx_1st_xdets = 0
        idx_xlbl = 1
        x_lbl_len = len(xaxis_dets[idx_1st_xdets][idx_xlbl])
        ymax = max(yvals)
        max_y_lbl_len = len(str(int(ymax)))
        max_safe_x_lbl_len_pxls = 180
        y_title_offset = Titles.get_ytitle_offset(max_y_lbl_len, x_lbl_len,
            max_safe_x_lbl_len_pxls, rotate=False)    
        margin_offset_l = (init_margin_offset_l + y_title_offset 
            - DOJO_YTITLE_OFFSET_0)
        normal_stroke_width = 2*css_dojo_dic['stroke_width'] # normal stroke needed even if border strokes not
        stroke_width = css_dojo_dic['stroke_width'] if show_borders else 0
        for chart_idx, chart_det in enumerate(chart_dets):
            n_chart = ("N = " + lib.formatnum(chart_det[mg.CHARTS_CHART_N])
                if show_n else "")
            minval = chart_det[mg.CHART_MINVAL]
            maxval = chart_det[mg.CHART_MAXVAL]
            xaxis_dets = chart_det[mg.CHARTS_XAXIS_DETS]
            y_vals = chart_det[mg.CHARTS_SERIES_Y_VALS]
            norm_ys = chart_det[mg.CHART_NORMAL_Y_VALS]
            bin_labels = chart_det[mg.CHART_BIN_LBLS]
            pagebreak = ("" if chart_idx % 2 == 0
                else "page-break-after: always;")
            indiv_title, indiv_title_html = Titles.get_indiv_title(
                multichart, chart_det)
            idx_lbls = ["{value: %s, text: \"%s\"}" % x for x in xaxis_dets]
            xaxis_lbls = ("[" + ",\n            ".join(idx_lbls) + "]")
            bin_lbls = "\"" + "\", \"".join(bin_labels) + "\""
            n_bins = len(xaxis_dets)
            width = Histo._get_histo_sizings(var_lbl, n_bins, minval, maxval)
            xfontsize = 10 if len(xaxis_dets) <= 20 else 8
            if multichart:
                width = width*0.9 # vulnerable to x axis labels vanishing on minor ticks
                xfontsize = xfontsize*0.8
            chart_settings_dic = {
                "axis_font_colour": css_dojo_dic['axis_font_colour'],
                "bin_lbls": bin_lbls,
                "chart_bg": lib.if_none(css_dojo_dic['chart_bg'], "null"),
                "chart_idx": "%02d" % chart_idx,
                "colour_cases": colour_cases,
                "connector_style": lib.if_none(css_dojo_dic['connector_style'], "defbrown"),
                "fill": fill,
                "gridline_width": lib.if_none(css_dojo_dic['gridline_width'], 3),
                "height": height,
                "indiv_title_html": indiv_title_html,
                "js_inc_normal": js_inc_normal,
                "major_gridline_colour": lib.if_none(css_dojo_dic['major_gridline_colour'], "null"),
                "margin_offset_l": lib.if_none(margin_offset_l, 0),
                "maxval": maxval,
                "minor_ticks": "true",
                "minval": minval,
                "n_chart": n_chart,
                "norm_ys": norm_ys,
                "normal_curve_colour": lib.if_none(css_dojo_dic['normal_curve_colour'], "null"),
                "normal_stroke_width": normal_stroke_width,
                "pagebreak": pagebreak,
                "plot_bg": lib.if_none(css_dojo_dic['plot_bg'], "null"),
                "plot_font_colour": lib.if_none(css_dojo_dic['plot_font_colour'], "null"),
                "plot_font_colour_filled": lib.if_none(css_dojo_dic['plot_font_colour_filled'], "white"),
                "stroke_width": stroke_width,
                "tooltip_border_colour": lib.if_none(css_dojo_dic['tooltip_border_colour'], "#ada9a5"),
                "var_lbl": var_lbl,
                "width": width,
                "xaxis_lbls": xaxis_lbls,
                "y_title_offset": 0,
                "y_vals": "%s" % y_vals,
                "xfontsize": xfontsize,
                "y_title_offset": y_title_offset,
                "y_title": mg.Y_AXIS_FREQ_LBL,
            }
            Histo._add_dojo_html_js(html, chart_settings_dic)
            charts_append_divider(html, titles, overall_title, indiv_title,
                "Histogram")
        if debug:
            print("y_title_offset: %s, margin_offset_l: %s" % (y_title_offset,
                margin_offset_l))
        html.append("""<div style="clear: both;">&nbsp;&nbsp;</div>""")
        if page_break_after:
            html.append("<br><hr><br><div class='%s'></div>" %
                CSS_PAGE_BREAK_BEFORE)
        return "".join(html)


class ScatterPlot:

    @staticmethod
    def _add_dojo_html_js(html, chart_settings_dic):
        html.append("""
        <script type="text/javascript">

        var sofaHlRenumber{chart_idx} = function(colour){{
            var hlColour;
            switch (colour.toHex()){{
                {colour_cases}
                default:
                    hlColour = hl(colour.toHex());
                    break;
            }}
            return new dojox.color.Color(hlColour);
        }}

        makechartRenumber{chart_idx} = function(){{
            {series_js}
            var conf = new Array();
            conf["axis_font_colour"] = "{axis_font_colour}";
            conf["axis_lbl_drop"] = {axis_lbl_drop};
            conf["chart_bg"] = "{chart_bg}";
            conf["connector_style"] = "{connector_style}";
            conf["gridline_width"] = {gridline_width};
            conf["highlight"] = sofaHlRenumber{chart_idx};
            conf["inc_regression_js"] = {inc_regression_js};
            conf["major_gridline_colour"] = "{major_gridline_colour}";
            conf["margin_offset_l"] = {margin_offset_l};
            conf["minor_ticks"] = {minor_ticks};
            conf["n_chart"] = "{n_chart}";
            conf["plot_bg"] = "{plot_bg}";
            conf["plot_font_colour"] = "{plot_font_colour}";
            conf["plot_font_colour_filled"] = "{plot_font_colour_filled}";
            conf["tooltip_border_colour"] = "{tooltip_border_colour}";
            conf["xfontsize"] = {xfontsize};
            conf["xmax"] = {xmax};
            conf["xmin"] = {xmin};
            conf["x_title"] = "{x_title}";
            conf["ymax"] = {ymax};
            conf["ymin"] = {ymin};
            conf["y_title_offset"] = {y_title_offset};
            conf["y_title"] = "{y_title}";
            makeScatterplot("mychartRenumber{chart_idx}", series, conf);
        }}
        </script>

        <div class="screen-float-only" style="margin-right: 10px; {pagebreak}">
        {indiv_chart_title}
        {regression_msg}
        {indiv_chart_title}
            <div id="mychartRenumber{chart_idx}" 
                style="width: {width}px; height: {height}px;">
            </div>
        {legend}
        </div>""".format(**chart_settings_dic))

    @staticmethod
    def _get_chart_ns(cur, sql_dic):
        SQL_get_chart_ns = ("""SELECT
        %(var_role_charts)s,
            COUNT(%(var_role_charts)s)
        AS chart_n
        FROM %(tbl)s
        WHERE %(var_role_charts)s IS NOT NULL
            AND %(var_role_series)s IS NOT NULL
            %(and_xy_filt)s
            %(and_tbl_filt)s
        GROUP BY %(var_role_charts)s
        """ % sql_dic)
        cur.execute(SQL_get_chart_ns)
        chart_ns = dict(x for x in cur.fetchall())
        return chart_ns

    @staticmethod
    def _coords_lst2js_pairs(coords_lst):
        "Turn coordinates into a JavaScript-friendly version as a string"
        js_pairs_lst = ["{x: %s, y: %s}" % (x, y) for x, y in coords_lst]
        js_pairs = "[" + ",\n".join(js_pairs_lst) + "]"
        return js_pairs

    @staticmethod
    def _get_overall_title_scatterplot(var_role_dic):
        title_bits = []
        title_bits.append("%s vs %s" % (var_role_dic['x_axis_name'],
            var_role_dic['y_axis_name']))
        if var_role_dic['series_name']:
            title_bits.append("By %s" % var_role_dic['series_name'])
        if var_role_dic['charts_name']:
            title_bits.append("By %s" % var_role_dic['charts_name'])
        return " ".join(title_bits)

    @staticmethod
    def _make_dojo_scatterplot(chart_idx, multichart, html, indiv_chart_title,
            show_borders, legend, n_chart, series_dets, series_colours_by_lbl,
            label_x, label_y, ymin, ymax, css_fpath, pagebreak):
        """
        min and max values are supplied for the y-axis because we want
        consistency on that between charts. For the x-axis, whatever is best per
        chart is OK.

        series_dets = {mg.CHARTS_SERIES_LBL_IN_LEGEND: "Italy", # or None if only one series
            mg.LIST_X: [1,1,2,2,2,3,4,6,8,18, ...], 
            mg.LIST_Y: [3,5,4,5,6,7,9,12,17,6, ...],
            mg.INC_REGRESSION: True,
            mg.LINE_LST: [12,26], # or None
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
        xmin, xmax = _get_optimal_min_max(min(all_x), max(all_x))
        init_margin_offset_l = 25
        max_y_lbl_len = len(str(int(ymax)))
        x_lbl_len = len(str(int(xmin)))
        max_safe_x_lbl_len_pxls = 90
        y_title_offset = Titles.get_ytitle_offset(max_y_lbl_len, x_lbl_len,
            max_safe_x_lbl_len_pxls, rotate=False)
        margin_offset_l = (init_margin_offset_l + y_title_offset
            - DOJO_YTITLE_OFFSET_0)
        x_title = label_x
        axis_lbl_drop = 10
        y_title = label_y
        if debug: print(label_x, xmin, xmax, label_y, ymin, ymax)
        series_js_list = []
        series_names_list = []
        indiv_regression_msgs = []
        for series_idx, series_det in enumerate(series_dets):
            series_lbl = series_det[mg.CHARTS_SERIES_LBL_IN_LEGEND]
            list_x = series_det[mg.LIST_X]
            list_y = series_det[mg.LIST_Y]
            inc_regression = series_det[mg.INC_REGRESSION]
            line_lst = series_det[mg.LINE_LST]
            data_tups = series_det[mg.DATA_TUPS]
            series_names_list.append("series%s" % series_idx)
            series_js_list.append("var series%s = new Array();" % series_idx)
            series_js_list.append("series%s[\"seriesLabel\"] = \"%s\";"
                % (series_idx, series_lbl))
            js_pairs_points = ScatterPlot._coords_lst2js_pairs(data_tups)
            series_js_list.append("series%s[\"xyPairs\"] = %s;" % (series_idx,
                js_pairs_points))
            x_set = set([item[0] for item in data_tups])
            few_unique_x_vals = (len(x_set) < 4)
            minor_ticks = "false" if few_unique_x_vals else "true"
            css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fpath)
            stroke_width = css_dojo_dic['stroke_width'] if show_borders else 0
            single_colour = True
            override_first_highlight = (
                (css_fpath == mg.DEFAULT_CSS_PATH)
                and single_colour)
            colour_cases = setup_highlights(css_dojo_dic['colour_mappings'],
                single_colour, override_first_highlight)
            fill = series_colours_by_lbl[series_lbl]
            point_series_style = ("series%(series_idx)s[\"style\"] = "
                "{stroke: {color: \"white\","
                "width: \"%(stroke_width)spx\"}, fill: \"%(fill)s\","
                "marker: \"m-6,0 c0,-8 12,-8 12,0 m-12,0 c0,8 12,8 12,0\"};" %
                {"series_idx": series_idx, "stroke_width": stroke_width,
                 "fill": fill})
            series_js_list.append(point_series_style)
            inc_regression_js = "false"
            if inc_regression:
                inc_regression_js = "true"
                if line_lst is not None:
                    indiv_regression_msg = core_stats.get_indiv_regression_msg(
                        list_x, list_y, series_lbl)
                    indiv_regression_msgs.append(indiv_regression_msg)
                    y0, y1 = line_lst
                    line_coords = [(min(list_x), y0), (max(list_x), y1)]
                    js_pairs_line = ScatterPlot._coords_lst2js_pairs(
                        line_coords)
                    regression_lbl = ("%s " % series_lbl if series_lbl
                        else "Line") # must not be identical to label for points or Dojo ignores first series of same name ;-)
                    #regression_lbl = ("%s Line" % series_lbl if series_lbl else "Line")
                    series_js_list.append("""series%s["lineLabel"] = "%s";"""
                        % (series_idx, regression_lbl))
                    series_js_list.append("series%s[\"xyLinePairs\"] = %s;"
                        % (series_idx, js_pairs_line))
                    line_series_style = ("series%(series_idx)s[\"lineStyle\"] = "
                        "{plot: \"regression\", stroke: {color: \"%(fill)s\","
                        "width: \"5px\"}, fill: \"%(fill)s\"};" %
                        {"series_idx": series_idx, "fill": fill})
                    series_js_list.append(line_series_style)
                else:
                    indiv_regression_msgs.append(mg.REGRESSION_ERR)
            series_js_list.append("")
            series_js = "\n    ".join(series_js_list)
            series_js += ("\n    var series = new Array(%s);" %
                ", ".join(series_names_list))
            series_js = series_js.lstrip()
        regression_msg = ("<br>".join(x for x in indiv_regression_msgs if x)
            + "<br><br>")
        # marker - http://o.dojotoolkit.org/forum/dojox-dojox/dojox-support/...
        # ...newbie-need-svg-path-segment-string
        chart_settings_dic = {
            "axis_font_colour": css_dojo_dic['axis_font_colour'],
            "axis_lbl_drop": lib.if_none(axis_lbl_drop, 30),
            "chart_bg": lib.if_none(css_dojo_dic['chart_bg'], "null"),
            "chart_idx": "%02d" % chart_idx,
            "colour_cases": colour_cases,
            "connector_style": lib.if_none(css_dojo_dic['connector_style'], "defbrown"),
            "fill": fill,
            "gridline_width": lib.if_none(css_dojo_dic['gridline_width'], 3),
            "height": height,
            "inc_regression_js": inc_regression_js,
            "indiv_chart_title": indiv_chart_title,
            "legend": legend,
            "major_gridline_colour": css_dojo_dic['major_gridline_colour'],
            "margin_offset_l": lib.if_none(margin_offset_l, 0),
            "minor_ticks": lib.if_none(minor_ticks, "false"),
            "n_chart": lib.if_none(n_chart, "''"),
            "pagebreak": pagebreak,
            "plot_bg": lib.if_none(css_dojo_dic['plot_bg'], "null"),
            "plot_font_colour": css_dojo_dic['plot_font_colour'],
            "plot_font_colour_filled": lib.if_none(css_dojo_dic['plot_font_colour_filled'], "white"),
            "regression_msg": regression_msg,
            "series_js": series_js,
            "stroke_width": stroke_width,
            "tooltip_border_colour": lib.if_none(css_dojo_dic['tooltip_border_colour'], "#ada9a5"),
            "width": width,
            "x_title": lib.if_none(x_title, "''"),
            "xfontsize": xfontsize,
            "xmax": xmax,
            "xmin": xmin,
            "y_title": y_title,
            "ymax": ymax,
            "ymin": ymin,
            "y_title_offset": lib.if_none(y_title_offset, 0),
        }
        ScatterPlot._add_dojo_html_js(html, chart_settings_dic)
        if debug: 
            print("y_title_offset: %s, margin_offset_l: %s" % (y_title_offset,
                margin_offset_l))

    @staticmethod
    def _get_scatterplot_ymin_ymax(scatterplot_dets):
        all_y_vals = []
        chart_dets = scatterplot_dets[mg.CHARTS_CHART_DETS]
        for chart_det in chart_dets:
            series_dets = chart_det[mg.CHARTS_SERIES_DETS]
            for series_det in series_dets:
                all_y_vals += series_det[mg.LIST_Y]
        ymin, ymax = _get_optimal_min_max(min(all_y_vals), max(all_y_vals))
        return ymin, ymax

    @staticmethod
    def _use_mpl_scatterplots(scatterplot_dets):
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

    @staticmethod      
    def _make_mpl_scatterplot(multichart, html, indiv_chart_title, show_borders, 
            n_chart, series_dets, series_colours_by_lbl, label_x,
            label_y, ymin, ymax, x_vs_y, add_to_report, report_fpath, css_fpath,
            pagebreak):
        """
        min and max values are supplied for the y-axis because we want consistency 
        on that between charts. For the x-axis, whatever is best per chart is OK. 
        """
        css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fpath)
        item_colours = output.colour_mappings_to_item_colours(
            css_dojo_dic['colour_mappings'])
        if multichart:
            width_inches, height_inches = (6.0, 3.4)
        else:
            width_inches, height_inches = (7.5, 4.1)
        title_dets_html = "" # handled prior to this step
        html.append("""<div class=screen-float-only style="margin-right: 10px; 
            margin-top: 0; %(pagebreak)s">""" % {"pagebreak": pagebreak})
        html.append(indiv_chart_title)
        all_x = []
        indiv_regression_msgs = []
        for series_det in series_dets:
            series_lbl = series_det[mg.CHARTS_SERIES_LBL_IN_LEGEND]
            list_x = series_det[mg.LIST_X]
            list_y = series_det[mg.LIST_Y]
            inc_regression = series_det[mg.INC_REGRESSION]
            line_lst = series_det[mg.LINE_LST]
            if inc_regression:
                if line_lst is not None:
                    indiv_regression_msg = core_stats.get_indiv_regression_msg(
                        list_x, list_y, series_lbl)
                    indiv_regression_msgs.append(indiv_regression_msg)
                else:
                    indiv_regression_msgs.append(mg.REGRESSION_ERR)
            all_x.extend(series_det[mg.LIST_X])
        regression_msg = ("<br>".join(x for x in indiv_regression_msgs if x) 
            + "<br>")
        html.append(regression_msg)
        xmin, xmax = _get_optimal_min_max(min(all_x), max(all_x))
        charting_pylab.add_scatterplot(css_dojo_dic['plot_bg'], show_borders,
            css_dojo_dic['major_gridline_colour'], 
            css_dojo_dic['plot_font_colour_filled'], n_chart, series_dets,
            label_x, label_y, x_vs_y, title_dets_html, add_to_report,
            report_fpath, html, width_inches, height_inches, xmin=xmin,
            xmax=xmax, ymin=ymin, ymax=ymax, dot_colour=item_colours[0],
            series_colours_by_lbl=series_colours_by_lbl)
        html.append("</div>")

    @staticmethod
    def get_scatterplot_dets(dbe, cur, tbl, tbl_filt, var_role_dic, unique=True,
            inc_regression=False):
        """
        unique -- unique x-y pairs only (irrespective of how many records had
        same combination.
        """
        debug = False
        objqtr = getdata.get_obj_quoter_func(dbe)
        where_tbl_filt, and_tbl_filt = lib.FiltLib.get_tbl_filts(tbl_filt)
        fld_x_axis = objqtr(var_role_dic['x_axis'])
        fld_y_axis = objqtr(var_role_dic['y_axis'])
        xy_filt = "%s IS NOT NULL AND %s IS NOT NULL " % (fld_x_axis,
            fld_y_axis)
        where_xy_filt = " WHERE " + xy_filt
        and_xy_filt = " AND" + xy_filt
        sql_dic = {"tbl": getdata.tblname_qtr(dbe, tbl),
            "fld_x_axis": objqtr(var_role_dic['x_axis']),
            "fld_y_axis": objqtr(var_role_dic['y_axis']),
            "where_tbl_filt": where_tbl_filt,
            "and_tbl_filt": and_tbl_filt,
            "where_xy_filt": where_xy_filt,
            "and_xy_filt": and_xy_filt,
            "sofa_series": SOFA_SERIES,
            "sofa_charts": SOFA_CHARTS,
            "sofa_x": SOFA_X,
            "sofa_y": SOFA_Y,
        }
        # Series and charts are optional so we need to autofill them with
        # something which will keep them in the same group.
        if var_role_dic['charts']:
            sql_dic["var_role_charts"] = objqtr(var_role_dic['charts'])
        else:
            sql_dic["var_role_charts"] = mg.GROUPING_PLACEHOLDER
        if var_role_dic['series']:
            sql_dic["var_role_series"] = objqtr(var_role_dic['series'])
        else:
            sql_dic["var_role_series"] = mg.GROUPING_PLACEHOLDER
        # only want rows where all variables are not null (and don't name field x or y or series or bad confusion happens in SQLite!
        SQL_get_xy_pairs = ("""SELECT %(var_role_charts)s
        AS %(sofa_charts)s,
            %(var_role_series)s
        AS %(sofa_series)s,
            %(fld_x_axis)s
        AS %(sofa_x)s,
            %(fld_y_axis)s
        AS %(sofa_y)s
        FROM %(tbl)s
        WHERE %(var_role_charts)s IS NOT NULL
            AND %(var_role_series)s IS NOT NULL
            %(and_xy_filt)s
            %(and_tbl_filt)s
        """ % sql_dic)
        if unique:
            groupby_vars = []
            if var_role_dic['charts']:
                groupby_vars.append(objqtr(var_role_dic['charts']))
            if var_role_dic['series']:
                groupby_vars.append(objqtr(var_role_dic['series']))
            groupby_vars.append(sql_dic["fld_x_axis"])
            groupby_vars.append(sql_dic["fld_y_axis"])
            SQL_get_xy_pairs += (" GROUP BY " + ", ".join(groupby_vars))
        if debug: print(SQL_get_xy_pairs)
        cur.execute(SQL_get_xy_pairs)
        raw_data = cur.fetchall()
        if not raw_data:
            raise my_exceptions.TooFewValsForDisplay
        fldnames = [sql_dic["var_role_charts"], sql_dic["var_role_series"],
            sql_dic["fld_x_axis"], sql_dic["fld_y_axis"]]
        chart_ns = ScatterPlot._get_chart_ns(cur, sql_dic)
        prestructure = DataPrep.get_prestructured_grouped_data(
            raw_data, fldnames, chart_ns=chart_ns)
        chart_dets = []
        n_charts = len(prestructure)
        if n_charts > mg.MAX_CHARTS_IN_SET:
            raise my_exceptions.TooManyChartsInSeries(
                var_role_dic['charts_name'],
                max_items=mg.MAX_CHARTS_IN_SET)
        multichart = n_charts > 1
        if multichart:
            chart_fldname = var_role_dic['charts_name']
            chart_fldlbls = var_role_dic['charts_lbls']
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
                chart_lbl = "%s: %s" % (chart_fldname,
                    chart_fldlbls.get(chart_val, str(chart_val)))
            else:
                chart_lbl = None
            series_dets = []
            for series_dic in series:
                series_val = series_dic[SERIES_KEY]
                if multiseries:
                    legend_lbl = var_role_dic['series_lbls'].get(
                        series_val, str(series_val))
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
                line_lst = None
                if inc_regression:
                    try:
                        (unused, unused, unused, 
                         y0, y1) = core_stats.get_regression_dets(list_x, list_y)
                        line_lst = [y0, y1]
                    except Exception:
                        pass
                series_det = {mg.CHARTS_SERIES_LBL_IN_LEGEND: legend_lbl,
                    mg.LIST_X: list_x, mg.LIST_Y: list_y, 
                    mg.INC_REGRESSION: inc_regression, mg.LINE_LST: line_lst, 
                    mg.DATA_TUPS: data_tups}
                series_dets.append(series_det)
            chart_det = {
                mg.CHARTS_CHART_N: chart_dic[CHART_N_KEY],
                mg.CHARTS_CHART_LBL: chart_lbl,
                mg.CHARTS_SERIES_DETS: series_dets}
            chart_dets.append(chart_det)
        overall_title = ScatterPlot._get_overall_title_scatterplot(var_role_dic)
        scatterplot_dets = {
            mg.CHARTS_OVERALL_LEGEND_LBL: var_role_dic['series_name'],
            mg.CHARTS_CHART_DETS: chart_dets}
        return overall_title, scatterplot_dets

    @staticmethod
    def scatterplot_output(titles, subtitles, overall_title, label_x, label_y,
            scatterplot_dets, css_fpath, css_idx, report_fpath, *,
            add_to_report, show_n, show_borders, page_break_after=False):
        """
        scatterplot_dets = {
            mg.CHARTS_OVERALL_LEGEND_LBL: "Age Group", # or None if only one series
            mg.CHARTS_CHART_DETS: chart_dets}
        chart_dets = [
            {mg.CHARTS_CHART_LBL: "Gender: Male", # or None if only one chart
             mg.CHARTS_SERIES_DETS: series_dets},
            {mg.CHARTS_CHART_LBL: "Gender: Female",
             mg.CHARTS_SERIES_DETS: series_dets}, ...
        ]
        series_dets = {mg.CHARTS_SERIES_LBL_IN_LEGEND: "Italy", # or None if only one series
            mg.LIST_X: [1,1,2,2,2,3,4,6,8,18, ...], 
            mg.LIST_Y: [3,5,4,5,6,7,9,12,17,6, ...],
            mg.LINE_LST: [12,26], # or None
            mg.DATA_TUPS: [(1,3),(1,5), ...]}
        """
        debug = False
        CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
            css_idx)
        pagebreak = "page-break-after: always;"
        title_dets_html = output.get_title_dets_html(titles, subtitles, css_idx)
        x_vs_y = '"%s"' % label_x + _(" vs ") + '"%s"' % label_y
        chart_dets = scatterplot_dets[mg.CHARTS_CHART_DETS]
        html = []
        html.append(title_dets_html)
        multichart = (len(scatterplot_dets[mg.CHARTS_CHART_DETS]) > 1)
        use_mpl = ScatterPlot._use_mpl_scatterplots(scatterplot_dets)
        ymin, ymax = ScatterPlot._get_scatterplot_ymin_ymax(scatterplot_dets) # unlike x-axis we require this to be consistent across charts
        legend_lbl = scatterplot_dets[mg.CHARTS_OVERALL_LEGEND_LBL]
        series_colours_by_lbl = get_series_colours_by_lbl(
            scatterplot_dets, css_fpath)
        # loop through charts
        for chart_idx, chart_det in enumerate(chart_dets):
            n_chart = ("N = " + lib.formatnum(chart_det[mg.CHARTS_CHART_N])
                if show_n else "")
            series_dets = chart_det[mg.CHARTS_SERIES_DETS]
            pagebreak = ("" if chart_idx % 2 == 0
                else "page-break-after: always;")
            if debug: print(series_dets)
            multiseries = len(series_dets) > 1
            if multiseries:
                legend = """
            <p style="float: left; font-weight: bold; margin-right: 12px; 
                    margin-top: 9px;">
                %s:
            </p>
            <div id="legendMychartRenumber%02d">
                </div>""" % (legend_lbl, chart_idx)
            else:
                legend = "" 
            indiv_title, indiv_title_html = Titles.get_indiv_title(
                multichart, chart_det)
            if use_mpl:
                ScatterPlot._make_mpl_scatterplot(multichart, html,
                    indiv_title_html, show_borders, n_chart, series_dets,
                    series_colours_by_lbl, label_x, label_y, ymin, ymax, x_vs_y,
                    add_to_report, report_fpath, css_fpath, pagebreak)
            else:
                ScatterPlot._make_dojo_scatterplot(chart_idx, multichart, html,
                    indiv_title_html, show_borders, legend, n_chart,
                    series_dets, series_colours_by_lbl, label_x, label_y, ymin,
                    ymax, css_fpath, pagebreak)
            charts_append_divider(html, titles, overall_title, indiv_title,
                "Scatterplot")
        if page_break_after:
            html.append("<br><hr><br><div class='%s'></div>" %
                CSS_PAGE_BREAK_BEFORE)
        return "".join(html)


class LineAreaChart:

    @staticmethod
    def _add_dojo_html_js(html, chart_settings_dic, area=False):
        chart_settings_dic['chart_type'] = 'Area' if area else 'Line'
        html.append("""
        <script type="text/javascript">
        makechartRenumber{chart_idx} = function(){{
            {series_js}
            var conf = new Array();
            conf["axis_font_colour"] = "{axis_font_colour}";
            conf["axis_lbl_drop"] = {axis_lbl_drop};
            conf["axis_lbl_rotate"] = {axis_lbl_rotate};
            conf["chart_bg"] = "{chart_bg}";
            conf["connector_style"] = "{connector_style}";
            conf["gridline_width"] = {gridline_width};
            conf["major_gridline_colour"] = "{major_gridline_colour}";
            conf["margin_offset_l"] = {margin_offset_l};
            conf["micro_ticks"] = {micro_ticks};
            conf["minor_ticks"] = {minor_ticks};
            conf["n_chart"] = "{n_chart}";
            conf["plot_bg"] = "{plot_bg}";
            conf["plot_font_colour"] = "{plot_font_colour}";
            conf["plot_font_colour_filled"] = "{plot_font_colour_filled}";
            conf["time_series"] = {time_series};
            conf["tooltip_border_colour"] = "{tooltip_border_colour}";
            conf["x_title"] = "{x_title}";
            conf["xaxis_lbls"] = {xaxis_lbls};
            conf["xfontsize"] = {xfontsize};
            conf["y_title_offset"] = {y_title_offset};
            conf["y_title"] = "{y_title}";
            conf["ymax"] = {ymax};
            make{chart_type}Chart("mychartRenumber{chart_idx}", series, conf);
        }}
        </script>

        <div style="float: left; margin-right: 10px; {pagebreak}">
        {indiv_title_html}
        <div id="mychartRenumber{chart_idx}" 
            style="width: {width}px; height: {height}px; {pagebreak}">
            </div>
        {legend}
        </div>""".format(**chart_settings_dic))

    @staticmethod
    def _get_line_area_chart_sizings(time_series, major_ticks, x_title,
            xaxis_dets, max_lbl_width, series_dets):
        """
        major_ticks -- e.g. want to only see the main labels and won't need it
        to be so wide.

        time_series -- can narrow a lot because standard-sized labels and
        usually not many.
        """
        debug = False
        n_cats = len(xaxis_dets)
        n_series = len(series_dets)
        MIN_PXLS_PER_CAT = 10
        MIN_CHART_WIDTH = 700 if n_series < 5 else 900 # when vertically squeezed good to have more horizontal room
        PADDING_PXLS = 20 if n_cats < 8 else 25
        if time_series:
            width_per_cat = MIN_PXLS_PER_CAT
        else:
            width_per_cat = (max([MIN_PXLS_PER_CAT,
                max_lbl_width*AVG_CHAR_WIDTH_PXLS]) + PADDING_PXLS)
        width_x_title = len(x_title)*AVG_CHAR_WIDTH_PXLS + PADDING_PXLS
        width = max([n_cats*width_per_cat, width_x_title, MIN_CHART_WIDTH])
        if major_ticks:
            width = max(width*0.4, MIN_CHART_WIDTH)
        if n_cats <= 5:
            xfontsize = 10
        elif n_cats > 10:
            xfontsize = 8
        else:
            xfontsize = 9
        minor_ticks = "true" if n_cats > 8 and not major_ticks else "false"
        micro_ticks = "true" if n_cats > 100 else "false"
        if debug: print(width, xfontsize, minor_ticks, micro_ticks)
        return width, xfontsize, minor_ticks, micro_ticks

    @staticmethod
    def _get_time_series_affected_dets(time_series, x_title, xaxis_dets,
            series_det, lbl_dets):
        if time_series:
            js_time_series = "true"
            xaxis_lbls = "[]"
            ## https://phillipsb1.wordpress.com/2010/07/25/date-and-time-based-charts/
            try:
                xs = []
                for val, unused, unused in xaxis_dets:
                    xs.append(lib.DateLib.get_epoch_secs_from_datetime_str(
                        str(val))*1000)
            except Exception:
                raise my_exceptions.InvalidTimeSeriesInput(fldname=x_title)
            ys = series_det[mg.CHARTS_SERIES_Y_VALS]
            assert len(xs) == len(ys)
            xys = zip(xs, ys)
            series_vals = [{'x': xy[0], 'y': xy[1]} for xy in xys]
        else:
            js_time_series = "false"
            xaxis_lbls = "[" + ",\n            ".join(lbl_dets) + "]"
            series_vals = series_det[mg.CHARTS_SERIES_Y_VALS]
        return js_time_series, xaxis_lbls, series_vals

    @staticmethod
    def _get_trend_y_vals(y_vals):
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
        for x in range(1, n+1):
            trend_y_vals.append(a + b*x)
        return trend_y_vals

    @staticmethod
    def _get_smooth_y_vals(y_vals):
        """
        Returns values to plot a smoothed line which fits the y_vals provided.
        """
        smooth_y_vals = []
        for i, y_val in enumerate(y_vals):
            if 1 < i < len(y_vals) - 2:
                smooth_y_vals.append(np.median(y_vals[i - 2 : i + 3]))
            elif i in (1, len(y_vals) - 2):
                smooth_y_vals.append(np.median(y_vals[i - 1: i + 2]))
            elif i == 0:
                smooth_y_vals.append((2 * y_val + y_vals[i + 1]) / 3)
            elif i == len(y_vals) - 1:
                smooth_y_vals.append((2 * y_val + y_vals[i - 1]) / 3)
        return smooth_y_vals

    @staticmethod
    def areachart_output(titles, subtitles, x_title, y_title, chart_output_dets,
            css_fpath, css_idx, *,
            time_series, rotate, show_n, major_ticks,
            hide_markers, page_break_after):
        """
        titles -- list of title lines correct styles
        subtitles -- list of subtitle lines
        chart_output_dets -- see structure_gen_data()
        css_idx -- css index so can apply    
        """
        debug = False
        if time_series and not rotate:
            major_ticks = False
        ## arbitrary plot names added with addPlot in my js file - each has different settings re: tension and markers
        plot_style = (", plot: 'unmarked'" if hide_markers
            else ", plot: 'default'")
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
         micro_ticks) = LineAreaChart._get_line_area_chart_sizings(time_series,
                                    major_ticks, x_title, xaxis_dets,
                                    max_lbl_width, chart0_series_dets)
        init_margin_offset_l = 25 if width > 1200 else 15 # gets squeezed
        if rotate:
            init_margin_offset_l += 5
        idx_1st_xdets = 0
        idx_xlbl = 1
        x_lbl_len = len(xaxis_dets[idx_1st_xdets][idx_xlbl])
        max_safe_x_lbl_len_pxls = 90
        y_title_offset = Titles.get_ytitle_offset(max_y_lbl_len, x_lbl_len, 
            max_safe_x_lbl_len_pxls, rotate=rotate)
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
        css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fpath)
        try:
            stroke = css_dojo_dic['colour_mappings'][0][0]
            fill = css_dojo_dic['colour_mappings'][0][1]
        except IndexError:
            stroke = mg.DOJO_COLOURS[0]
        # loop through charts
        for chart_idx, chart_det in enumerate(chart_dets):
            indiv_title, indiv_title_html = Titles.get_indiv_title(
                multichart, chart_det)
            # only one series per chart by design
            n_chart = ("N = " + lib.formatnum(chart_det[mg.CHARTS_CHART_N])
                if show_n else "")
            series_det = chart_det[mg.CHARTS_SERIES_DETS][0]
            xaxis_dets = series_det[mg.CHARTS_XAXIS_DETS]
            lbl_dets = get_lbl_dets(xaxis_dets)
            xaxis_lbls = "[" + ",\n            ".join(lbl_dets) + "]"
            pagebreak = "" if chart_idx % 2 == 0 else "page-break-after: always;"
            series_js_list = []
            series_names_list = []
            series_names_list.append("series0")
            series_js_list.append("var series0 = new Array();")
            series_js_list.append("series0[\"seriesLabel\"] = \"%s\";"
                % series_det[mg.CHARTS_SERIES_LBL_IN_LEGEND])
            ## times series
            (js_time_series, xaxis_lbls,
             series_vals) = LineAreaChart._get_time_series_affected_dets(
                 time_series, x_title, xaxis_dets, series_det, lbl_dets)
            ## more
            series_js_list.append("series0[\"seriesVals\"] = %s;"
                % series_vals)
            tooltips = ("['"
                + "', '".join(series_det[mg.CHARTS_SERIES_TOOLTIPS]) + "']")
            series_js_list.append("series0[\"options\"] = "
                "{stroke: {color: \"%s\", width: \"6px\"}, fill: \"%s\", "
                "yLbls: %s %s};" % (stroke, fill, tooltips, plot_style))
            series_js_list.append("")
            series_js = "\n    ".join(series_js_list)
            series_js += ("\n    var series = new Array(%s);"
                % ", ".join(series_names_list))
            series_js = series_js.lstrip()
            chart_settings_dic = {
                "axis_font_colour": css_dojo_dic['axis_font_colour'],
                "axis_lbl_drop": lib.if_none(axis_lbl_drop, 30),
                "axis_lbl_rotate": axis_lbl_rotate,
                "chart_bg": css_dojo_dic['chart_bg'],
                "chart_idx": "%02d" % chart_idx,
                "connector_style": lib.if_none(css_dojo_dic['connector_style'], "defbrown"),
                "gridline_width": lib.if_none(css_dojo_dic['gridline_width'], 3),
                "indiv_title_html": indiv_title_html,
                "legend": "",  ## not used in area charts - they can only show one series per chart
                "major_gridline_colour": css_dojo_dic['major_gridline_colour'],
                "margin_offset_l": lib.if_none(margin_offset_l, 0),
                "micro_ticks": micro_ticks,
                "minor_ticks": minor_ticks,
                "n_chart": n_chart,
                "pagebreak": pagebreak,
                "plot_bg": css_dojo_dic['plot_bg'],
                "plot_font_colour": css_dojo_dic['plot_font_colour'],
                "plot_font_colour_filled": lib.if_none(css_dojo_dic['plot_font_colour_filled'], "black"),
                "series_js": series_js,
                "time_series": lib.if_none(js_time_series, "false"),
                "tooltip_border_colour": lib.if_none(css_dojo_dic['tooltip_border_colour'], "#ada9a5"),
                "width": width, "height": height,
                "x_title": x_title,
                "xaxis_lbls": xaxis_lbls,
                "xfontsize": xfontsize,
                "y_title": y_title,
                "y_title_offset": lib.if_none(y_title_offset, 0),
                "ymax": ymax,
            }
            LineAreaChart._add_dojo_html_js(html, chart_settings_dic,
                area=True)
            overall_title = chart_output_dets[mg.CHARTS_OVERALL_TITLE]
            charts_append_divider(html, titles, overall_title, indiv_title,
                "Area Chart")
        if debug:
            print("y_title_offset: %s, margin_offset_l: %s" % (y_title_offset,
                margin_offset_l))
        html.append("""<div style="clear: both;">&nbsp;&nbsp;</div>""")
        if page_break_after:
            html.append("<br><hr><br><div class='%s'></div>" %
                CSS_PAGE_BREAK_BEFORE)
        return "".join(html)

    @staticmethod
    def linechart_output(titles, subtitles, x_title, y_title, chart_output_dets,
            css_fpath, css_idx, *,
            time_series, rotate, show_n, major_ticks, inc_trend, inc_smooth,
            hide_markers, page_break_after):
        """
        titles -- list of title lines correct styles
        subtitles -- list of subtitle lines
        chart_output_dets -- see structure_gen_data()
        css_idx -- css index so can apply    
        """
        debug = False
        if time_series and not rotate:
            major_ticks = False
        axis_lbl_rotate = -90 if rotate else 0
        html = []
        multichart = len(chart_output_dets[mg.CHARTS_CHART_DETS]) > 1
        CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (
            mg.CSS_PAGE_BREAK_BEFORE, css_idx)
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
         minor_ticks, micro_ticks) = LineAreaChart._get_line_area_chart_sizings(
                time_series, major_ticks, x_title, xaxis_dets, max_lbl_width,
                chart0_series_dets)
        init_margin_offset_l = 25 if width > 1200 else 15  ## gets squeezed
        if rotate:
            init_margin_offset_l += 4
        idx_1st_xdets = 0
        idx_xlbl = 1
        x_lbl_len = len(xaxis_dets[idx_1st_xdets][idx_xlbl])
        max_safe_x_lbl_len_pxls = 90
        ymax = get_ymax(chart_output_dets)
        y_title_offset = Titles.get_ytitle_offset(max_y_lbl_len, x_lbl_len,
            max_safe_x_lbl_len_pxls, rotate=rotate)
        if multichart:
            width = width*0.9
            xfontsize = xfontsize*0.9
            init_margin_offset_l += 10
        margin_offset_l = (init_margin_offset_l + y_title_offset 
            - DOJO_YTITLE_OFFSET_0)
        """
        For each series, set colour details.

        For the collection of series as a whole, set the highlight mapping from
        each series colour.

        From dojox.charting.action2d.Highlight but with extraneous % removed
        """
        css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fpath)
        item_colours = output.colour_mappings_to_item_colours(
            css_dojo_dic['colour_mappings'])
        series_colours_by_lbl = get_series_colours_by_lbl(
            chart_output_dets, css_fpath)
        # loop through charts
        for chart_idx, chart_det in enumerate(chart_dets):
            n_chart = ("N = " + lib.formatnum(chart_det[mg.CHARTS_CHART_N])
                if show_n else "")
            series_dets = chart_det[mg.CHARTS_SERIES_DETS]
            pagebreak = ("" if chart_idx % 2 == 0
                else "page-break-after: always;")
            if debug: print(series_dets)
            if legend_lbl is not None:
                legend_html = """
                <p style="float: left; font-weight: bold; margin-right: 12px;
                    margin-top: 9px;">
                %s:
                </p>""" % legend_lbl
            else:
                legend_html = ""
            legend_html += """
            <div id="legendMychartRenumber%02d">
                </div>""" % chart_idx
            indiv_title, indiv_title_html = Titles.get_indiv_title(
                multichart, chart_det)
            """
            If only one series, and trendlines/smoothlines are selected, make
            additional series for each as appropriate.
            """
            if multiseries:
                legend = legend_html
            else:
                series0 = series_dets[0]
                dummy_tooltips = ["",]
                if inc_trend or inc_smooth:
                    raw_y_vals = series0[mg.CHARTS_SERIES_Y_VALS]
                if inc_trend:
                    trend_y_vals = LineAreaChart._get_trend_y_vals(raw_y_vals)
                    if time_series:
                        ## we're using coordinates so can just have the end points (the non-time series approach is only linear when even x gaps between the y values)
                        trend_xaxis_dets = [series0[mg.CHARTS_XAXIS_DETS][0],
                            series0[mg.CHARTS_XAXIS_DETS][-1]]
                        trend_y_vals = [trend_y_vals[0], trend_y_vals[-1]]
                    else:
                        trend_xaxis_dets = series0[mg.CHARTS_XAXIS_DETS]
                    ## repeat most of it
                    trend_series = {
                        mg.CHARTS_SERIES_LBL_IN_LEGEND: TRENDLINE_LBL,
                        mg.CHARTS_XAXIS_DETS: trend_xaxis_dets,
                        mg.CHARTS_SERIES_Y_VALS: trend_y_vals,
                        mg.CHARTS_SERIES_TOOLTIPS: dummy_tooltips}
                    series_dets.insert(0, trend_series)
                    series_colours_by_lbl[TRENDLINE_LBL] = item_colours[1]
                if inc_smooth:
                    smooth_y_vals = LineAreaChart._get_smooth_y_vals(raw_y_vals)
                    smooth_series = {
                         mg.CHARTS_SERIES_LBL_IN_LEGEND: SMOOTHLINE_LBL,
                         mg.CHARTS_XAXIS_DETS: series0[mg.CHARTS_XAXIS_DETS],
                         mg.CHARTS_SERIES_Y_VALS: smooth_y_vals,
                         mg.CHARTS_SERIES_TOOLTIPS: dummy_tooltips}
                    series_dets.insert(0, smooth_series)
                    series_colours_by_lbl[SMOOTHLINE_LBL] = item_colours[2]
                if debug: pprint.pprint(series_dets)
                if inc_trend or inc_smooth:
                    ORIG_VAL_LABEL = "Original Values"
                    series0[mg.CHARTS_SERIES_LBL_IN_LEGEND] = ORIG_VAL_LABEL
                    series_colours_by_lbl[ORIG_VAL_LABEL] = item_colours[0]  ## currently mapped against original label of None
                    legend = legend_html
                else:
                    legend = ""
            series_js_list = []
            series_names_list = []
            for series_idx, series_det in enumerate(series_dets):
                series_lbl = series_det[mg.CHARTS_SERIES_LBL_IN_LEGEND]
                xaxis_dets = series_det[mg.CHARTS_XAXIS_DETS]
                lbl_dets = get_lbl_dets(xaxis_dets)
                ## times series
                (js_time_series, xaxis_lbls,
                    series_vals) = LineAreaChart._get_time_series_affected_dets(
                                        time_series, x_title, xaxis_dets,
                                        series_det, lbl_dets)
                ## more
                series_names_list.append("series%s" % series_idx)
                series_js_list.append("var series%s = new Array();"
                    % series_idx)
                series_js_list.append("series%s[\"seriesLabel\"] = \"%s\";"
                    % (series_idx, series_lbl))
                series_js_list.append("series%s[\"seriesVals\"] = %s;"
                    % (series_idx, series_vals))
                stroke = series_colours_by_lbl[series_lbl]
                # To set markers explicitly:
                # http://dojotoolkit.org/api/1.5/dojox/charting/Theme/Markers/CIRCLE
                # e.g. marker: dojox.charting.Theme.defaultMarkers.CIRCLE"
                # Note - trend line comes first in case just two points - don't want it to set the x-axis labels - leave that to the other lines
                ## arbitrary plot names added with addPlot in my js file - each has different settings re: tension and markers
                if multiseries:
                    if hide_markers:
                        plot_style = ", plot: 'unmarked'"
                    else:
                        plot_style = ", plot: 'default'"
                else:
                    if inc_trend and inc_smooth:
                        orig_idx = 2
                        trend_idx = 1
                        smooth_idx = 0
                    elif inc_trend:  ## only trend
                        orig_idx = 1
                        trend_idx = 0
                        smooth_idx = None
                    elif inc_smooth:  ## only smooth
                        orig_idx = 1
                        trend_idx = None
                        smooth_idx = 0
                    else:
                        orig_idx = 0
                        trend_idx = None
                        smooth_idx = None
                    if series_idx == orig_idx:
                        if hide_markers:
                            plot_style = ", plot: 'unmarked'"
                        else:
                            plot_style = ", plot: 'default'"
                    elif series_idx == trend_idx:
                        plot_style = ", plot: 'unmarked'"
                    elif series_idx == smooth_idx:
                        plot_style = ", plot: 'curved'"
                    else:
                        raise Exception("Unexpected series_idx: {}"
                            .format(series_idx))
                tooltips = ("['" 
                    + "', '".join(series_det[mg.CHARTS_SERIES_TOOLTIPS])
                    + "']")
                series_js_list.append("""series%s["options"] = """
                    "{stroke: {color: '%s', width: '6px'}, yLbls: %s %s};"
                    % (series_idx, stroke, tooltips, plot_style))
                series_js_list.append("")
            series_js = "\n    ".join(series_js_list)
            series_js += ("\n    var series = new Array(%s);"
                % ", ".join(series_names_list))
            series_js = series_js.lstrip()
            chart_settings_dic = {
                "axis_font_colour": css_dojo_dic['axis_font_colour'],
                "axis_lbl_drop": lib.if_none(axis_lbl_drop, 30),
                "axis_lbl_rotate": lib.if_none(axis_lbl_rotate, 0),
                "chart_bg": css_dojo_dic['chart_bg'],
                "chart_idx": "%02d" % chart_idx,
                "connector_style": lib.if_none(css_dojo_dic['connector_style'], "defbrown"),
                "gridline_width": lib.if_none(css_dojo_dic['gridline_width'], 3),
                "indiv_title_html": indiv_title_html,
                "legend": legend,
                "major_gridline_colour": css_dojo_dic['major_gridline_colour'],
                "margin_offset_l": lib.if_none(margin_offset_l, 0),
                "micro_ticks": lib.if_none(micro_ticks, "false"),
                "minor_ticks": lib.if_none(minor_ticks, "false"),
                "n_chart": n_chart,
                "pagebreak": pagebreak,
                "plot_bg": css_dojo_dic['plot_bg'],
                "plot_font_colour": css_dojo_dic['plot_font_colour'],
                "plot_font_colour_filled": lib.if_none(css_dojo_dic['plot_font_colour_filled'], "black"),
                "series_js": series_js,
                "time_series": lib.if_none(js_time_series, "false"),
                "tooltip_border_colour": lib.if_none(css_dojo_dic['tooltip_border_colour'], "#ada9a5"),
                "y_title_offset": lib.if_none(y_title_offset, 0),
                "x_title": x_title,
                "xaxis_lbls": xaxis_lbls,
                "xfontsize": xfontsize,
                "width": width,
                "height": height,
                "y_title": y_title,
                "ymax": ymax,
            }
            LineAreaChart._add_dojo_html_js(html, chart_settings_dic,
                area=False)
            overall_title = chart_output_dets[mg.CHARTS_OVERALL_TITLE]
            charts_append_divider(html, titles, overall_title, indiv_title,
                "Line Chart")
        if debug: 
            print("y_title_offset: %s, margin_offset_l: %s" % (y_title_offset,
                margin_offset_l))
        if page_break_after:
            html.append("<br><hr><br><div class='%s'></div>"
                % CSS_PAGE_BREAK_BEFORE)
        return "".join(html)


class PieChart:

    @staticmethod
    def _add_dojo_html_js(html, chart_settings_dic):
        html.append("""
        <script type="text/javascript">
        makechartRenumber{chart_idx} = function(){{
            var sofaHlRenumber{chart_idx} = function(colour){{
                var hlColour;
                switch (colour.toHex()){{
                    {colour_cases}
                    default:
                        hlColour = hl(colour.toHex());
                        break;
                }}
                return new dojox.color.Color(hlColour);
            }}
            {slices_js}
            var conf = new Array();
            conf["connector_style"] = "{connector_style}";
            conf["highlight"] = sofaHlRenumber{chart_idx};
            conf["lbl_offset"] = {lbl_offset};
            conf["n_chart"] = "{n_chart}";
            conf["plot_bg_filled"] = "{plot_bg_filled}";
            conf["plot_font_colour_filled"] = "{plot_font_colour_filled}";
            conf["radius"] = {radius};
            conf["slice_colours"] = {slice_colours};
            conf["slice_fontsize"] = {slice_fontsize};
            conf["tooltip_border_colour"] = "{tooltip_border_colour}";
            makePieChart("mychartRenumber{chart_idx}", slices, conf);
        }}
        </script>

        <div class="screen-float-only" style="margin-right: 10px; {pagebreak}">
        {indiv_title_html}
        <div id="mychartRenumber{chart_idx}" 
            style="width: {width}px; height: {height}px;">
            </div>
        </div>
        """.format(**chart_settings_dic))

    @staticmethod
    def _get_cat_colours_by_lbl(chart_output_dets, item_colours):
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

    @staticmethod
    def piechart_output(titles, subtitles, chart_output_dets,
            css_fpath, css_idx,
            *, inc_count, inc_pct, show_n, page_break_after):
        """
        chart_output_dets -- see structure_gen_data()
        """
        debug = False
        html = []
        CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (
            mg.CSS_PAGE_BREAK_BEFORE, css_idx)
        multichart = len(chart_output_dets[mg.CHARTS_CHART_DETS]) > 1
        title_dets_html = output.get_title_dets_html(titles, subtitles, css_idx)
        html.append(title_dets_html)
        width = 500 if mg.PLATFORM == mg.WINDOWS else 450
        if multichart:
            width = width*0.8
        height = 370 if multichart else 420
        radius = 120 if multichart else 140
        lbl_offset = -20 if multichart else -30
        css_dojos_dic = lib.OutputLib.extract_dojo_style(css_fpath)
        colour_cases = setup_highlights(
            css_dojos_dic['colour_mappings'], single_colour=False, 
            override_first_highlight=False)
        item_colours = output.colour_mappings_to_item_colours(
            css_dojos_dic['colour_mappings'])
        cat_colours_by_lbl = PieChart._get_cat_colours_by_lbl(chart_output_dets,
            item_colours)
        if debug: print(pprint.pformat(cat_colours_by_lbl))
        #slice_colours = item_colours[:30]
        chart_dets = chart_output_dets[mg.CHARTS_CHART_DETS]
        slice_fontsize = 14 if len(chart_dets) < 10 else 10
        if multichart:
            slice_fontsize = slice_fontsize*0.8
        # loop through charts
        for chart_idx, chart_det in enumerate(chart_dets):
            # only one series per chart by design
            n_chart = ("N = " + lib.formatnum(chart_det[mg.CHARTS_CHART_N])
                if show_n else "")
            series_det = chart_det[mg.CHARTS_SERIES_DETS][0]
            pagebreak = ("" if chart_idx % 2 == 0
                else "page-break-after: always;")
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
                tiplbl = val_lbl.replace('\n', ' ')  ## line breaks mean no display
                slice_pct = round((100.0*y_val)/tot_y_vals,
                    mg.DEFAULT_REPORT_DP)
                if mg.DEFAULT_REPORT_DP == 0:
                    slice_pct = int(slice_pct)
                if inc_count or inc_pct:
                    raw_val2show = lib.OutputLib.get_count_pct_dets(inc_count,
                        inc_pct, lbl=tiplbl, count=y_val, pct=slice_pct)
                    val2show = u'"%s"' % raw_val2show
                else:
                    val2show = split_lbl
                if mg.PLATFORM == mg.WINDOWS:
                    val2show = val2show.replace('<br>', ': ')
                tooltip = lib.OutputLib.get_count_pct_dets(inc_count=True,
                    inc_pct=True, lbl=tiplbl, count=y_val, pct=slice_pct)
                slices_js_lst.append("{\"y\": %(y)s, \"text\": %(text)s, " 
                    "\"tooltip\": \"%(tooltip)s\"}" % {"y": y_val,
                    "text": val2show, "tooltip": tooltip})
            if debug:
                print(cat_colours_by_lbl)
                print(colours_for_this_chart)
            slices_js = ("slices = [" + (",\n" + " "*4*4).join(slices_js_lst)
                + "\n];")
            indiv_title, indiv_title_html = Titles.get_indiv_title(
                multichart, chart_det)
            chart_settings_dic = {
                "chart_idx": "%02d" % chart_idx,
                "colour_cases": colour_cases,
                "connector_style": lib.if_none(css_dojos_dic['connector_style'], "defbrown"),
                "height": height,
                "indiv_title_html": indiv_title_html,
                "lbl_offset": lib.if_none(lbl_offset, -30),
                "n_chart": n_chart,
                "pagebreak": pagebreak,
                "plot_bg_filled": lib.if_none(css_dojos_dic['plot_bg_filled'], ""),
                "plot_font_colour_filled": css_dojos_dic['plot_font_colour_filled'],
                "radius": lib.if_none(radius, 140),
                "slice_colours": colours_for_this_chart,
                "slice_fontsize": slice_fontsize,
                "slices_js": slices_js,
                "tooltip_border_colour": lib.if_none(css_dojos_dic['tooltip_border_colour'], "#ada9a5"),
                "width": width,
            }
            PieChart._add_dojo_html_js(html, chart_settings_dic)
            overall_title = chart_output_dets[mg.CHARTS_OVERALL_TITLE]
            charts_append_divider(html, titles, overall_title, indiv_title,
                "Pie Chart")
        html.append("""<div style="clear: both;">&nbsp;&nbsp;</div>""")
        if page_break_after:
            html.append("<br><hr><br><div class='%s'></div>" %
                CSS_PAGE_BREAK_BEFORE)
        return "".join(html)
