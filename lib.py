#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import codecs
import datetime
import decimal
import locale
import math
from operator import itemgetter
import os
import pprint
import pylab
import random
import re
import sys
import time
import wx

# only import my_globals from local modules
import my_globals as mg
import my_exceptions
import core_stats

def get_normal_ys(vals, bins):
    """
    Get np array of y values for normal distribution curve with given values 
        and bins.
    """
    mu = core_stats.mean(vals)
    sigma = core_stats.stdev(vals)
    norm_ys = pylab.normpdf(bins, mu, sigma)
    return norm_ys

def quote_val(raw_val, unsafe_internal_quote, safe_internal_quote, 
              use_double_quotes=True):
    """
    Might be a string or a datetime but can't be a number
    """
    try:
        val = raw_val.isoformat()
    except AttributeError, e:
        try: # escape internal double quotes
            val = raw_val.replace(unsafe_internal_quote, safe_internal_quote)
        except AttributeError, e:
            raise Exception(u"Inappropriate attempt to quote non-string value."
                            u"\nCaused by error: %s" % lib.ue(e))
    if use_double_quotes:
        newval = u"\"%s\"" % val
    else:
        newval = u"\'%s\'" % val
    return newval

def get_p(p, dp):
    if p < 0.001:
        p_str = u"< 0.001"
    else:
        p_format = u"%%.%sf" % dp
        p_str = p_format % round(p, dp)
    return p_str

def get_exec_ready_text(text):
    """
    test -- often the result of f.read()
    exec can't handle some Windows scripts e.g. print("Hello world")\r\n
    you can see
    """
    debug = False
    if debug: print(repr(text)) # look for terminating \r\n on Windows sometimes
    return text.replace(u"\r", u"")

def dates_1900_to_datetime(days_since_1900):
    DATETIME_ZERO = datetime.datetime(1899, 12, 30, 0, 0, 0)
    days = float(days_since_1900)
    mydatetime = DATETIME_ZERO + datetime.timedelta(days)
    return mydatetime

def dates_1900_to_datetime_str(days_since_1900):
    dt = dates_1900_to_datetime(days_since_1900)
    if dt.microsecond > 500000: # add a second if microsecs adds more than half
        dt += datetime.timedelta(seconds=1)
    datetime_str = dt.isoformat(" ").split(".")[0] # truncate microsecs
    return datetime_str

def get_unique_db_name_key(db_names, db_name):
    "Might have different paths but same name."
    if db_name in db_names:
        db_name_key = db_name + u"_" + unicode(db_names.count(db_name))
    else:
        db_name_key = db_name
    db_names.append(db_name)
    return db_name_key

def sort_value_labels(sort_order, val_freq_label_lst):
    """
    In-place sort value labels list according to sort option selected.
    http://www.python.org/dev/peps/pep-0265/
    """
    if sort_order == mg.SORT_INCREASING:
        val_freq_label_lst.sort(key=itemgetter(1))
    elif sort_order == mg.SORT_DECREASING:
        val_freq_label_lst.sort(key=itemgetter(1), reverse=True)
    elif sort_order == mg.SORT_LABEL:
        val_freq_label_lst.sort(key=itemgetter(2))

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
    text = css[css_dojo_start_idx + len(mg.DOJO_STYLE_START): css_dojo_end_idx]
    css_dojo = get_exec_ready_text(text)
    css_dojo_dic = {}
    try:
        exec css_dojo in css_dojo_dic
    except SyntaxError, e:
        wx.MessageBox(\
            _(u"Syntax error in dojo settings in css file \"%(css_fil)s\"."
              u"\n\nDetails: %(css_dojo)s %(err)s") % {"css_fil": css_fil,
              u"css_dojo": css_dojo, u"err": lib.ue(e)})
        raise
    except Exception, e:
        wx.MessageBox(\
            _(u"Error processing css dojo file \"%(css_fil)s\"."
              u"\n\nDetails: %(err)s") % {u"css_fil": css_fil,
              u"err": lib.ue(e)})
        raise
    return (css_dojo_dic[u"outer_bg"], 
            css_dojo_dic[u"inner_bg"], 
            css_dojo_dic[u"axis_label_font_colour"], 
            css_dojo_dic[u"major_gridline_colour"], 
            css_dojo_dic[u"gridline_width"], 
            css_dojo_dic[u"stroke_width"], 
            css_dojo_dic[u"tooltip_border_colour"], 
            css_dojo_dic[u"colour_mappings"],
            css_dojo_dic[u"connector_style"],
            )

def get_bins(min_val, max_val):
    """
    Goal - set nice bin widths so "nice" value e.g. 0.2, 0.5, 1 (or
        200, 500, 1000 or 0.002, 0.005, 0.01) and not too many or too few
        bins.
    Start with a bin width which splits the data into the optimal number 
        of bins.  Normalise it, adjust upwards to nice size, and 
        denormalise.  Check number of bins resulting.
    OK?  If room to double number of bins, halve size of normalised bin
        width, and try to adjust upwards to a nice size.  This time,
        however, there is the option of 2 as an interval size (so we have
        2, 5, or 10.  Denormalise and recalculate the number of bins.
    Now reset lower and upper limits if appropriate.  Make lower limit a 
        multiple of the bin_width and make upper limit n_bins*bin_width higher.
        Add another bin if not covering max value.
    n_bins -- need an integer ready for core_stats.histogram
    """
    debug = False
    # init
    if min_val > max_val:
        if debug: print("Had to swap %s and %s ..." % (min_val, max_val))
        min_val, max_val = max_val, min_val
        if debug: print("... to %s and %s" % (min_val, max_val))
    data_range = max_val - min_val
    if data_range == 0:
        data_range = 1
    target_n_bins = 20
    min_n_bins = 10
    target_bin_width = 5 # half order of magnitude (10s are order of mag)
    init_bin_width = data_range/(target_n_bins*1.0)
    # normalise init_bin_width to val between 1 and 10
    norm_bin_width = init_bin_width
    while norm_bin_width <= 1:
        norm_bin_width *= 10
    while norm_bin_width > 10:
        norm_bin_width /= 10.0
    if debug:
        print("init: %s, normed: %s" % (init_bin_width, norm_bin_width))
    # get denorm ratio so can convert norm_bin widths back to data bin widths
    denorm_ratio = init_bin_width/norm_bin_width
    # adjust upwards to either 5 or 10
    better_norm_bin_width = 5 if norm_bin_width <= 5 else 10
    # denormalise
    better_bin_width = better_norm_bin_width*denorm_ratio
    n_bins = int(math.ceil(data_range/better_bin_width))
    # possible to increase granularity?
    if n_bins < min_n_bins:
        # halve normalised bin width and try again but with an extra option of 2
        norm_bin_width /= 2.0
        if norm_bin_width <= 2:
            better_norm_bin_width = 2
        elif norm_bin_width <= 5:
            better_norm_bin_width = 5
        else:
            better_norm_bin_width = 10
        # denormalise
        better_bin_width = better_norm_bin_width*denorm_ratio
        n_bins = int(math.ceil(data_range/(better_bin_width*1.0)))
    lower_limit = min_val
    upper_limit = max_val
    # Adjust lower and upper limits if bin_width doesn't exactly fit.  If an
    # exact fit, leave alone on assumption the limits are meaningful e.g. if
    # 9.69 - 19.69 and 20 bins then leave limits alone.
    if better_bin_width*n_bins != data_range:
        if debug: print(data_range, better_bin_width*n_bins)
        # Set lower limit to a clean multiple of the bin_width e.g. 3*bin_width
        # or -6*bin_width. Identify existing multiple and set to integer below
        # (floor). Lower limit is now that lower integer times the bin_width.
        # NB the multiple is an integer but the lower limit might not be
        # e.g. if the bin_size is a fraction e.g. 0.002
        existing_multiple = lower_limit/(better_bin_width*1.0)
        lower_limit = math.floor(existing_multiple)*better_bin_width
        upper_limit = lower_limit + (n_bins*better_bin_width)
    if max_val > upper_limit:
        upper_limit += better_bin_width
        n_bins += 1
    if debug:
        print(("For %s to %s use an interval size of %s for a data range of %s "
               "to %s giving you %s bins") % (min_val, max_val, 
                                              better_bin_width, lower_limit, 
                                              upper_limit, n_bins))
    return n_bins, lower_limit, upper_limit

def saw_toothing(y_vals, period, start_idx=0):
    """
    Sawtoothing is where every nth bin has values, but the others have none.
    """
    period_vals = y_vals[start_idx::period]
    sum_period = sum(period_vals)
    sum_all = sum(y_vals)
    sum_non_period = sum_all - sum_period
    return sum_non_period == 0

def fix_sawtoothing(raw_data, n_bins, y_vals, start, bin_width):
    """
    Look for sawtoothing on commonly found periods (5 and 2).  If found, reduce
        bins until problem gone or too few bins to keep shrinking.
    """
    while n_bins > 5:
        if saw_toothing(y_vals, period=5):
            shrink_factor = 5.0
        elif saw_toothing(y_vals, period=2):
            shrink_factor = 2.0
        elif saw_toothing(y_vals, period=2, start_idx=1):
            shrink_factor = 2.0
        else:
            break
        n_bins = int(math.ceil(n_bins/shrink_factor))
        (y_vals, start, 
            bin_width, unused) = core_stats.histogram(raw_data, n_bins)
    return y_vals, start, bin_width

def version_a_is_newer(version_a, version_b):
    """
    Must be able to process both version details or error raised.
    """
    try:
        version_b_parts = version_b.split(u".")
        if len(version_b_parts) != 3: 
            raise Exception(u"Faulty Version B details")
        version_b_parts = [int(x) for x in version_b_parts]
    except Exception, e:
        raise Exception(u"Version B parts faulty")
    try:
        version_a_parts = version_a.split(u".")
        if len(version_a_parts) != 3:
            raise Exception(u"Faulty Version A details")
        version_a_parts = [int(x) for x in version_a_parts]
    except Exception, e:
        raise Exception(u"Version A parts faulty")
    if version_a_parts[0] > version_b_parts[0]:
        is_newer = True
    elif version_a_parts[0] == version_b_parts[0] \
        and version_a_parts[1] > version_b_parts[1]:
        is_newer = True
    elif version_a_parts[0] == version_b_parts[0] \
        and version_a_parts[1] == version_b_parts[1]\
        and version_a_parts[2] > version_b_parts[2]:
        is_newer = True
    else:
        is_newer = False
    return is_newer

def get_unicode_datestamp():
    debug = False
    now = datetime.datetime.now()
    try:
        raw_datestamp = now.strftime(u"%d/%m/%Y at %I:%M %p")
        # see http://groups.google.com/group/comp.lang.python/browse_thread/...
        # ...thread/a18a590eb5d12e5b
        datestamp = raw_datestamp.decode(locale.getpreferredencoding())
        if debug: print(repr(datestamp))
        u_datestamp = u"%s" % datestamp
    except Exception:
        try:
            raw_datestamp = now.strftime(u"%d/%m/%Y at %H:%M")
            datestamp = raw_datestamp.decode(locale.getpreferredencoding())
            if debug: print(repr(datestamp))
            u_datestamp = u"%s" % datestamp
        except Exception:
            try:
                raw_datestamp = now.strftime(u"%d/%m/%Y at %H:%M")
                datestamp = raw_datestamp.decode("utf8", "replace")
                if debug: print(repr(datestamp))
                u_datestamp = u"%s" % datestamp
            except Exception:
                u_datestamp = u"date-time unrecorded" # TODO -chardet?
    return u_datestamp

def ue(e):
    """
    Return unicode string version of error reason
    unicode(e) handles u"找不到指定的模块。" & u"I \u2665 unicode"
    str(e).decode("utf8", ...) handles "找不到指定的模块。"
    """
    debug = False
    try:
        unicode_e = unicode(e)
    except UnicodeDecodeError:
        try:
            unicode_e = str(e).decode(locale.getpreferredencoding())
        except UnicodeDecodeError:
            try:
                unicode_e = str(e).decode("utf8", "replace")
            except UnicodeDecodeError:
                unicode_e = u"Problem getting error reason"
    if debug: 
        print("unicode_e has type %s" % type(unicode_e))
        print(repr(u"unicode_e is %s" % unicode_e))
    return unicode_e

cp1252 = {
    # from http://www.microsoft.com/typography/unicode/1252.htm
    u"\x80": u"\u20AC", # EURO SIGN
    u"\x82": u"\u201A", # SINGLE LOW-9 QUOTATION MARK
    u"\x83": u"\u0192", # LATIN SMALL LETTER F WITH HOOK
    u"\x84": u"\u201E", # DOUBLE LOW-9 QUOTATION MARK
    u"\x85": u"\u2026", # HORIZONTAL ELLIPSIS
    u"\x86": u"\u2020", # DAGGER
    u"\x87": u"\u2021", # DOUBLE DAGGER
    u"\x88": u"\u02C6", # MODIFIER LETTER CIRCUMFLEX ACCENT
    u"\x89": u"\u2030", # PER MILLE SIGN
    u"\x8A": u"\u0160", # LATIN CAPITAL LETTER S WITH CARON
    u"\x8B": u"\u2039", # SINGLE LEFT-POINTING ANGLE QUOTATION MARK
    u"\x8C": u"\u0152", # LATIN CAPITAL LIGATURE OE
    u"\x8E": u"\u017D", # LATIN CAPITAL LETTER Z WITH CARON
    u"\x91": u"\u2018", # LEFT SINGLE QUOTATION MARK
    u"\x92": u"\u2019", # RIGHT SINGLE QUOTATION MARK
    u"\x93": u"\u201C", # LEFT DOUBLE QUOTATION MARK
    u"\x94": u"\u201D", # RIGHT DOUBLE QUOTATION MARK
    u"\x95": u"\u2022", # BULLET
    u"\x96": u"\u2013", # EN DASH
    u"\x97": u"\u2014", # EM DASH
    u"\x98": u"\u02DC", # SMALL TILDE
    u"\x99": u"\u2122", # TRADE MARK SIGN
    u"\x9A": u"\u0161", # LATIN SMALL LETTER S WITH CARON
    u"\x9B": u"\u203A", # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
    u"\x9C": u"\u0153", # LATIN SMALL LIGATURE OE
    u"\x9E": u"\u017E", # LATIN SMALL LETTER Z WITH CARON
    u"\x9F": u"\u0178", # LATIN CAPITAL LETTER Y WITH DIAERESIS
    }

oth_ms_gremlins = {
    u"\xe2\x80\x9c": u"\u201C", # LEFT DOUBLE QUOTATION MARK,
    u"\xe2\x80\x9d": u"\u201D", # RIGHT DOUBLE QUOTATION MARK
    u"\xe2\x80\x93": u"\u2013", # EN DASH
    u"\xe2\x80\x94": u"\u2014", # EM DASH - guess as to key
    u"\xe2\x80\xa6": u"\u2026", # HORIZONTAL ELLIPSIS
    }

def fix_cp1252(m):
    s = m.group(0)
    return cp1252.get(s, s)

def fix_gremlins(m):
    s = m.group(0)
    return oth_ms_gremlins.get(s, s)

def handle_ms_data(data):
    if not isinstance(data, basestring):
        return data
    else:
        return ms2unicode(data)

def ms2unicode(text):
    """
    Inspiration from http://effbot.org/zone/unicode-gremlins.htm
        which maps cp1252 gremlins to real unicode characters.
    Main changes - now ensure the output is unicode even if cp1252 characters 
        not found in it.
    Also handles smart quotes etc (which are multibyte) and commonly used ;-).
    """
    import re # easier to transplant for testing if everything here
    debug = False
    if not isinstance(text, basestring):
        raise Exception(u"ms2unicode() requires strings as inputs.")
    if debug: print(repr(text))
    for gremlin in oth_ms_gremlins:  # turn to unicode any bytes which contain
            # cp1252 bytes.  E.g. so u"\xe2\x80\x93" doesn't become the
            # nonsense u"\xe2\u20AC\x93" as a result of our search and replace.
        if re.search(gremlin, text):
            if isinstance(text, str): # Make sure we have a unicode string for 
                # fixing up step.  If has those ms characters probably safe to 
                # decode using "iso-8859-1"
                text = text.decode("iso-8859-1")
            text = re.sub(gremlin, fix_gremlins, text)
    if re.search(u"[\x80-\x9f]", text):
        text = re.sub(u"[\x80-\x9f]", fix_cp1252, text)
    if isinstance(text, str): # no gremlins or cp1252 so no guarantees unicoded
        try:
            text = text.decode(locale.getpreferredencoding())
        except UnicodeDecodeError:
            text = text.decode("utf8", "replace")
    if debug: print(repr(text))
    return text

def str2unicode(raw):
    """
    If not a string, raise Exception.  Otherwise ...
    Convert byte strings to unicode.
    Convert any cp1252 text to unicode e.g. smart quotes.
    Return safe unicode string (pure unicode and no unescaped backslashes).
    """
    if not isinstance(raw, basestring): # isinstance includes descendants
        raise Exception(u"str2unicode() requires strings as inputs.")
    if type(raw) == str:
        try:
            safe = raw.decode(locale.getpreferredencoding())
        except UnicodeDecodeError:
            try:
                safe = raw.decode("utf-8")
            except Exception:
                try:
                    safe = ms2unicode(raw)
                except Exception:
                    safe = raw.decode("utf8", "replace") # final fallback
    else:
        try:
            safe = ms2unicode(raw)
        except Exception:
            safe = raw.decode("utf8", "replace") # final fallback
    return safe

def any2unicode(raw):
    """
    Get unicode string back from any input.
    If a number, avoids scientific notation if up to 16 places.
    """
    if is_basic_num(raw):
        # only work with repr if you have to
        # 0.3 -> 0.3 if print() but 0.29999999999999999 if repr() 
        strval = unicode(raw)
        if re.search(r"\d+e[+-]\d+", strval): # num(s) e +or- num(s)
            return unicode(repr(raw)) # 1000000000000.4 rather than 1e+12
        else:
            return unicode(raw)
    elif isinstance(raw, basestring): # isinstance includes descendants
        return str2unicode(raw)
    else:
        return unicode(raw)

def none2empty(val):
    if val is None:
        return u""
    else:
        return val

def get_val_type(val, comma_dec_sep_ok=False):
    if is_numeric(val, comma_dec_sep_ok): # anything SQLite can add 
            # _as a number_ into a numeric field
        val_type = mg.VAL_NUMERIC
    elif is_pytime(val): # COM on Windows
        val_type = mg.VAL_DATE
    else:
        usable_datetime = is_usable_datetime_str(val)
        if usable_datetime:
            val_type = mg.VAL_DATE
        elif val == u"":
            val_type = mg.VAL_EMPTY_STRING
        else:
            val_type = mg.VAL_STRING
    return val_type    

def update_type_set(type_set, val, comma_dec_sep_ok=False):
    """
    Some countries use commas as decimal separators.
    """
    val_type = get_val_type(val, comma_dec_sep_ok)
    type_set.add(val_type)

def get_overall_fld_type(type_set):
    """
    type_set may contain empty_str as well as actual types.  Useful to remove
        empty str and see what is left.
    STRING is the fallback.
    """
    debug = False
    main_type_set = type_set.copy()
    main_type_set.discard(mg.VAL_EMPTY_STRING)
    if main_type_set == set([mg.VAL_NUMERIC]):
        fld_type = mg.FLD_TYPE_NUMERIC
    elif main_type_set == set([mg.VAL_DATE]):
        fld_type = mg.FLD_TYPE_DATE
    elif (main_type_set == set([mg.VAL_STRING]) 
            or type_set == set([mg.VAL_EMPTY_STRING])):
        fld_type = mg.FLD_TYPE_STRING
    else:
        if len(main_type_set) > 1:
            if debug: print(main_type_set)
        fld_type = mg.FLD_TYPE_STRING    
    return fld_type

def update_local_display(html_ctrl, str_content, wrap_text=False):
    str_content = u"<p>%s</p>" % str_content if wrap_text else str_content 
    html_ctrl.show_html(str_content, url_load=True) # allow footnotes

def get_min_content_size(szr_lst, vertical=True):
    """
    For a list of sizers return min content size overall.  NB excludes padding 
        (border).
    Returns x, y.
    vertical -- whether parent sizer of szr_lst is vertical.
    """
    debug = False
    x = 0
    y = 0
    for szr in szr_lst:
        szr_x, szr_y = szr.GetMinSize()
        if debug: print("szr_x: %s; szr_y: %s" % (szr_x, szr_y))
        if vertical:
            x = max([szr_x, x])
            y += szr_y
        else:
            x += szr_x
            y = max([szr_y, y])
    return x, y

def set_size(window, szr_lst, width_init=None, height_init=None, 
             horiz_padding=10):
    """
    Provide ability to display a larger initial size yet set an explicit minimum
        size.  Also handles need to "jitter" in Windows.
    Doesn't use the standard approach of szr.SetSizeHints(self) and 
        panel.Layout().  Setting size hints will shrink it using Fit().
    window -- e.g. the dialog itself or a frame.
    szr_lst -- all the szrs in the main szr (can be a grid instead of a szr)
    width_init -- starting width.  If None use the minimum worked out.
    height_init -- starting height.  If None use the minimum worked out.
    NB no need to set size=() in __init__ of window. 
    """
    width_cont_min, height_cont_min = get_min_content_size(szr_lst)
    width_min = width_cont_min + 2*horiz_padding # left and right
    height_correction = 200 if mg.PLATFORM == mg.MAC else 100
    height_min = height_cont_min + height_correction
    width_init = width_init if width_init else width_min
    height_init = height_init if height_init else height_min
    if mg.PLATFORM == mg.WINDOWS: # jitter to display inner controls
        window.SetSize((width_init+1, height_init+1))
    window.SetSize((width_init, height_init))
    window.SetMinSize((width_min,height_min))

def esc_str_input(raw):
    """
    Escapes input ready to go into a string using %.
    So "variable %Y has fields %s" % fields will fail because variables with 
        name %Y will confuse the string formatting operation.  %%Y will be fine.
    """
    try:
        new_str = raw.replace("%", "%%")
    except Exception, e:
        raise Exception(u"Unable to escape str input."
                        u"\nCaused by error: %s" % ue(e))
    return new_str

def get_var_dets(fil_var_dets):
    """
    Get variable details from fil_var_dets file.
    Returns var_labels, var_notes, var_types, val_dics.
    """
    try:
        f = codecs.open(fil_var_dets, "U", encoding="utf-8")
    except IOError:
        var_labels = {}
        var_notes = {}
        var_types = {}
        val_dics = {}
        return var_labels, var_notes, var_types, val_dics
    var_dets_txt = get_exec_ready_text(text=f.read())
    f.close()
    var_dets = clean_bom_utf8(var_dets_txt)
    var_dets_dic = {}
    try:
        # http://docs.python.org/reference/simple_stmts.html
        exec var_dets in var_dets_dic
    except SyntaxError, e:
        wx.MessageBox(\
            _(u"Syntax error in variable details file \"%(fil_var_dets)s\"."
              u"\n\nDetails: %(err)s") % {u"fil_var_dets": fil_var_dets, 
                                          u"err": unicode(e)})
        raise
    except Exception, e:
        wx.MessageBox(\
            _(u"Error processing variable details file \"%(fil_var_dets)s\"."
              u"\n\nDetails: %(err)s") % {u"fil_var_dets": fil_var_dets, 
                                          u"err": unicode(e)})
        raise
    try:
        results = var_dets_dic["var_labels"], var_dets_dic["var_notes"], \
                      var_dets_dic["var_types"], var_dets_dic["val_dics"]
    except Exception, e:
        raise Exception(u"Three variables needed in " +
                    u"'%s': var_labels, var_notes, var_types, and val_dics. " +
                    u"Please check file." % fil_var_dets)
    return results

def get_rand_val_of_type(type):
    if type == mg.FLD_TYPE_NUMERIC:
        vals_of_type = mg.NUM_DATA_SEQ
    elif type == mg.FLD_TYPE_STRING:
        vals_of_type = mg.STR_DATA_SEQ
    elif type == mg.FLD_TYPE_DATE:
        vals_of_type = mg.DTM_DATA_SEQ
    else:
        raise Exception(u"Unknown type in get_rand_val_of_type")
    return random.choice(vals_of_type)

def safe_end_cursor():
    "Problems in Windows if no matching beginning cursor."
    if wx.IsBusy():
        wx.EndBusyCursor()

def get_n_fld_names(n):
    fldnames = []
    for i in range(n):
        fldname = mg.NEXT_FLD_NAME_TEMPLATE % (i+1,)
        fldnames.append(fldname)
    return fldnames

def get_next_fld_name(existing_var_names):
    """
    Get next available variable name where names follow a template e.g. var001,
        var002 etc.If a gap, starts after last one.  Gaps are not filled.
    """
    nums_used = []
    for var_name in existing_var_names:
        if not var_name.startswith(mg.FLD_NAME_START):
            continue
        try:
            num_used = int(var_name[-len(mg.FLD_NAME_START):])
        except ValueError:
            continue
        nums_used.append(num_used)
    free_num = max(nums_used) + 1 if nums_used else 1
    next_fld_name = mg.NEXT_FLD_NAME_TEMPLATE % free_num
    return next_fld_name

def get_labels_in_lines(orig_txt, max_width, dojo=False):
    """
    Returns quoted text. Will not be further quoted.
    Will be "%s" % wrapped txt not "\"%s\"" % wrapped_txt
    """
    debug = False
    lines = []
    words = orig_txt.split()
    line_words = []
    for word in words:
        line_words.append(word)
        line_width = len(u" ".join(line_words))
        if line_width > max_width:
            line_words.pop()
            lines.append(u" ".join(line_words))
            line_words = [word]
    lines.append(u" ".join(line_words))
    lines = [x.center(max_width) for x in lines]
    if debug: 
        print(line_words)
        print(lines)
    if dojo:
        if len(lines) == 1:
            wrapped_txt = u"\"" + lines[0].strip() + u"\""
        else:
            wrapped_txt = u"\"" + u"\" + labelLineBreak + \"".join(lines) + \
                                                                        u"\""
    else:
        if len(lines) == 1:
            wrapped_txt = lines[0].strip()
        else:
            wrapped_txt = u"\n".join(lines)
    if debug: print(wrapped_txt)
    return wrapped_txt

def get_text_to_draw(orig_txt, max_width):
    "Return text broken into new lines so wraps within pixel width"
    mem = wx.MemoryDC()
    mem.SelectObject(wx.EmptyBitmap(100,100)) # mac fails without this
    # add words to it until its width is too long then put into split
    lines = []
    words = orig_txt.split()
    line_words = []
    for word in words:
        line_words.append(word)
        line_width = mem.GetTextExtent(u" ".join(line_words))[0]
        if line_width > max_width:
            line_words.pop()
            lines.append(u" ".join(line_words))
            line_words = [word]
    lines.append(u" ".join(line_words))
    wrapped_txt = u"\n".join(lines)
    mem.SelectObject(wx.NullBitmap)
    return wrapped_txt

def get_font_size_to_fit(text, max_width, font_sz, min_font_sz):
    "Shrink font until it fits or is min size"
    mem = wx.MemoryDC()
    mem.SelectObject(wx.EmptyBitmap(max_width,100)) # mac fails without this
    while font_sz > min_font_sz:
        font = wx.Font(font_sz, wx.SWISS, wx.NORMAL, wx.BOLD)
        mem.SetFont(font)
        text_width = mem.GetTextExtent(text)[0]
        if text_width < max_width:
            break
        else:
            font_sz -= 1
    return font_sz

def add_text_to_bitmap(bitmap, text, btn_font_sz, colour, left=9, top=3):
    """
    Add short text to bitmap with standard left margin.
    Can then use bitmap for a bitmap button.
    See http://wiki.wxpython.org/index.cgi/WorkingWithImages
    """
    width = bitmap.GetWidth()
    height = bitmap.GetHeight()
    rect = wx.Rect(left, top, width, height)
    mem = wx.MemoryDC()
    mem.SelectObject(bitmap)
    mem.SetTextForeground(colour)
    while btn_font_sz > 7:
        font = wx.Font(btn_font_sz, wx.SWISS, wx.NORMAL, wx.BOLD)
        mem.SetFont(font)
        max_text_width = width - (2*left)
        text_width = mem.GetTextExtent(text)[0]
        if text_width < max_text_width: 
            break
        else:
            btn_font_sz -= 1
    mem.DrawLabel(text, rect)
    mem.SelectObject(wx.NullBitmap)
    return bitmap

def get_tbl_filt(dbe, db, tbl):
    """
    Returns tbl_filt_label, tbl_filt.
    Do not build tbl_file = clause yourself using this - use get_tbl_filt_clause
        instead so quoting works.
    """
    try:
        tbl_filt_label, tbl_filt = mg.DBE_TBL_FILTS[dbe][db][tbl]
    except KeyError:
        tbl_filt_label, tbl_filt = u"", u""
    return tbl_filt_label, tbl_filt

def get_tbl_filt_clause(dbe, db, tbl):
    unused, tbl_filt = get_tbl_filt(dbe, db, tbl)
    return u'tbl_filt = u""" %s """' % tbl_filt

def get_tbl_filts(tbl_filt):
    """
    Returns filters ready to use as WHERE and AND filters:
        where_filt, and_filt
    Filters must still work if empty strings (for performance when no filter 
        required).
    """
    if tbl_filt.strip() != "":
        where_tbl_filt = u""" WHERE %s""" % tbl_filt
        and_tbl_filt = u""" AND %s""" % tbl_filt
    else:
        where_tbl_filt = u""
        and_tbl_filt = u""
    return where_tbl_filt, and_tbl_filt

def get_filt_msg(tbl_filt_label, tbl_filt):
    """
    Return filter message.
    """
    if tbl_filt.strip() != "":
        if tbl_filt_label.strip() != "":
            filt_msg = _("Data filtered by \"%(label)s\": %(filt)s") % \
                {"label": tbl_filt_label, "filt": tbl_filt.strip()}
        else:
            filt_msg = _("Data filtered by: ") + tbl_filt.strip()
    else:
        filt_msg = _("All data in table included - no filtering")
    return filt_msg

def is_numeric(val, comma_dec_sep_ok=False):
    """
    Is a value numeric?  This is operationalised to mean can a value be cast as 
        a float.  
    NB the string 5 is numeric.  Scientific notation is numeric. Complex numbers 
        are considered not numeric for general use.  
    The type may not be numeric (e.g. might be the string '5') but the "content" 
        must be.
    http://www.rosettacode.org/wiki/IsNumeric#Python
    """
    if is_pytime(val):
        return False
    elif val is None:
        return False
    else:
        try:
            if comma_dec_sep_ok:
                val = val.replace(u",", u".")
        except AttributeError, e:
            pass
        try:
            i = float(val)
        except (ValueError, TypeError):
            return False
        else:
            return True

def is_basic_num(val):
    """
    Is a value of a basic numeric type - i.e. integer, long, float?  NB complex 
        or Decimal values are not considered basic numbers.
    NB a string containing a numeric value is not a number type even though it
        will pass is_numeric().
    """
    return type(val) in [int, long, float]

def n2d(f):
    """
    Convert a floating point number to a Decimal with no loss of information
    http://docs.python.org/library/decimal.html with added error trapping and
        handling of non-floats.
    """
    if not isinstance(f, float):
        try:
            f = float(f)
        except (ValueError, TypeError):
            raise Exception(u"Unable to convert value to Decimal.  " +
                            u"Value was \"%s\"" % f)
    try:
        n, d = f.as_integer_ratio()
    except Exception:
        raise Exception(u"Unable to turn value \"%s\" into integer " % f +
                        u"ratio for unknown reason.")
    numerator, denominator = decimal.Decimal(n), decimal.Decimal(d)
    ctx = decimal.Context(prec=60)
    result = ctx.divide(numerator, denominator)
    while ctx.flags[decimal.Inexact]:
        ctx.flags[decimal.Inexact] = False
        ctx.prec *= 2
        result = ctx.divide(numerator, denominator)
    return result

# uncovered

def clean_bom_utf8(raw):
    if raw.startswith(unicode(codecs.BOM_UTF8, "utf-8")):
        raw = raw[len(unicode(codecs.BOM_UTF8, "utf-8")):]
    return raw

if mg.PLATFORM == mg.WINDOWS:
    import pywintypes

def escape_pre_write(txt):
    "Useful when writing a path to a text file etc"
    return txt.replace("\\", "\\\\")

def get_file_name(path):
    "Works on Windows paths as well"
    path = path.replace("\\\\", "\\").replace("\\", "/")
    return os.path.split(path)[1]

def is_integer(val):
    # http://mail.python.org/pipermail/python-list/2006-February/368113.html
    return isinstance(val, (int, long))

def is_string(val):
    # http://mail.python.org/pipermail/winnipeg/2007-August/000237.html
    return isinstance(val, basestring)

def is_pytime(val): 
    #http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/511451
    return type(val).__name__ == 'time'
    
def if_none(val, default):
    """
    Returns default if value is None - otherwise returns value.
    While there is a regression in pywin32 cannot compare pytime with anything
        see http://mail.python.org/pipermail/python-win32/2009-March/008920.html
    """
    if is_pytime(val):
        return val
    elif val is None:
        return default
    else:
        return val

def pytime_to_datetime_str(pytime):
    """
    A PyTime object is used primarily when exchanging date/time information 
        with COM objects or other win32 functions.
    http://docs.activestate.com/activepython/2.4/pywin32/PyTime.html
    See http://timgolden.me.uk/python/win32_how_do_i/use-a-pytime-value.html
    And http://code.activestate.com/recipes/511451/    
    """
    try:
        int_pytime = pywintypes.Time(int(pytime))
        datetime_str = "%s-%s-%s %s:%s:%s" % (int_pytime.year, 
                                          unicode(int_pytime.month).zfill(2),
                                          unicode(int_pytime.day).zfill(2),
                                          unicode(int_pytime.hour).zfill(2),
                                          unicode(int_pytime.minute).zfill(2),
                                          unicode(int_pytime.second).zfill(2))
    except ValueError:
        datetime_str = "NULL"
    return datetime_str

def flip_date(date):
    """Reorder MySQL date e.g. 2008-11-23 -> 23-11-2008"""
    return "%s-%s-%s" % (date[-2:], date[5:7], date[:4])

def date_range2mysql(entered_start_date, entered_end_date):
    """
    Takes date range in format "01-01-2008" for both start and end
        and returns start_date and end_date in mysql format.
    """
    #start date and end date must both be a valid date in that format
    try:
        #valid formats: http://docs.python.org/lib/module-time.html
        time.strptime(entered_start_date, "%d-%m-%Y")
        time.strptime(entered_end_date, "%d-%m-%Y")
        def DDMMYYYY2MySQL(value):
            #e.g. 26-04-2001 -> 2001-04-26 less flexible than using strptime and 
            # strftime together but much quicker
            return "%s-%s-%s" % (value[-4:], value[3:5], value[:2])
        start_date = DDMMYYYY2MySQL(entered_start_date)# MySQL-friendly dates
        end_date = DDMMYYYY2MySQL(entered_end_date)# MySQL-friendly dates
        return start_date, end_date     
    except:
        raise Exception(u"Please pass valid start and end dates as per the "
                        u"required format e.g. 25-01-2007")    

def mysql2textdate(mysql_date, output_format):
    """
    Takes MySQL date e.g. 2008-01-25 and returns date string according to 
        format.  NB must be valid format for strftime.
    TODO - make safe for weird encoding issues.  See get_unicode_datestamp().
    """
    year = int(mysql_date[:4])
    month = int(mysql_date[5:7])
    day = int(mysql_date[-2:])
    mydate = (year, month, day, 0, 0, 0, 0, 0, 0)
    return time.strftime(output_format, mydate)

def is_date_part(datetime_str):
    """
    Assumes date will have - or / or . or , and time will not.
    If a mishmash will fail bad_date later.
    """
    return ("-" in datetime_str or "/" in datetime_str or "." in datetime_str 
            or "," in datetime_str)

def is_time_part(datetime_str):
    """
    Assumes time will have : (or am/pm) and date will not.
    If a mishmash will fail bad_time later.
    """
    return ":" in datetime_str or "am" in datetime_str.lower() \
        or "pm" in datetime_str.lower()

def is_year(datetime_str):
    dt_is_year = False
    try:
        year = int(datetime_str)
        dt_is_year = (1 <= year < 10000) 
    except Exception:
        pass
    return dt_is_year

def datetime_split(datetime_str):
    """
    Split date and time (if both).
    A space can be treated as the splitter unless after a comma, in which case 
        it should be seen as an internal part of a date e.g. Feb 11, 2010.
    Return date part, time part, order (True unless order 
        time then date).
    Return None for any missing components.
    Must be only one space in string (if any) - between date and time
        (or time and date).
    boldate_then_time -- only False if time then date with both present.
    """
    if u" " in datetime_str and u", " not in datetime_str:
        boldate_then_time = True
        datetime_split = datetime_str.split(" ")
        if len(datetime_split) != 2:
            return (None, None, True)
        if is_date_part(datetime_split[0]) \
                and is_time_part(datetime_split[1]):
            return (datetime_split[0], datetime_split[1], True)
        elif is_date_part(datetime_split[1]) \
                and is_time_part(datetime_split[0]):
            boldate_then_time = False
            return (datetime_split[1], datetime_split[0], boldate_then_time)
        else:
            return (None, None, boldate_then_time)
    elif is_year(datetime_str):
        return (datetime_str, None, True)
    else: # only one part
        boldate_then_time = True
        if is_date_part(datetime_str):
            return (datetime_str, None, boldate_then_time)
        elif is_time_part(datetime_str):
            return (None, datetime_str, boldate_then_time)
        else:
            return (None, None, boldate_then_time)

def get_dets_of_usable_datetime_str(raw_datetime_str, ok_date_formats, 
                                    ok_time_formats):
    """
    Returns (date_part, date_format, time_part, time_format, boldate_then_time) 
        if a usable datetime.  NB usable doesn't mean valid as such.  E.g. we 
        may need to add a date to the time to make it valid.
    Returns None if not usable.
    These parts can be used to make a valid time object ready for conversion 
        into a standard string for data entry.
    """
    debug = False
    if not is_string(raw_datetime_str):
        if debug: print("%s is not a valid datetime string" % raw_datetime_str)
        return None
    # evaluate date and/or time components against allowable formats
    date_part, time_part, boldate_then_time = datetime_split(raw_datetime_str)
    if date_part is None and time_part is None:
        if debug: print("Both date and time parts are empty.")
        return None
    # gather information on the parts we have (we have at least one)
    date_format = None
    if date_part:
        # see cell_invalid for message about correct datetime entry formats
        bad_date = True
        for ok_date_format in ok_date_formats:
            try:
                t = time.strptime(date_part, ok_date_format)
                date_format = ok_date_format
                bad_date = False
                break
            except:
                pass
        if bad_date:
            return None
    time_format = None
    if time_part:
        bad_time = True
        for ok_time_format in ok_time_formats:
            try:
                t = time.strptime(time_part, ok_time_format)
                time_format = ok_time_format
                bad_time = False
                break
            except:
                pass
        if bad_time:
            return None
    # have at least one part and no bad parts
    return (date_part, date_format, time_part, time_format, boldate_then_time)

def is_usable_datetime_str(raw_datetime_str, ok_date_formats=None, 
                           ok_time_formats=None):
    """
    Is the datetime string usable?  Used for checking user-entered datetimes.
    Doesn't cover all possibilities - just what is needed for typical data 
        entry.
    If only a time, can always use today's date later to prepare for SQL.
    If only a date, can use midnight as time e.g. MySQL 00:00:00
    Acceptable formats for date component are:
    2009, 2008-02-26, 1-1-2008, 01-01-2008, 01/01/2008, 1/1/2008.
    NB not American format - instead assumed to be day, month, year.
    TODO - handle better ;-)
    Acceptable formats for time are:
    2pm, 2:30pm, 14:30 , 14:30:00
    http://docs.python.org/library/datetime.html#module-datetime
    Should only be one space in string (if any) - between date and time
        (or time and date).
    """
    ok_date_formats
    return get_dets_of_usable_datetime_str(raw_datetime_str, 
                            ok_date_formats or mg.OK_DATE_FORMATS, 
                            ok_time_formats or mg.OK_TIME_FORMATS) is not None
    
def is_std_datetime_str(raw_datetime_str):
    """
    The only format accepted as valid for SQL is yyyy-mm-dd hh:mm:ss.
    NB lots of other formats may be usable, but this is the only one acceptable
        for direct entry into a database.
    http://www.cl.cam.ac.uk/~mgk25/iso-time.html
    """
    try:
        t = time.strptime(raw_datetime_str, "%Y-%m-%d %H:%M:%S")
        return True
    except Exception:
        return False

def get_std_datetime_str(raw_datetime_str):
    """
    Takes a string and checks if there is a usable datetime in there (even a
        time without a date is OK).
    If there is, creates a complete time_obj and then turns that into a standard
        datetime string.
    
    """
    debug = False
    datetime_dets = get_dets_of_usable_datetime_str(raw_datetime_str, 
                                                    mg.OK_DATE_FORMATS, 
                                                    mg.OK_TIME_FORMATS)
    if datetime_dets is None:
        raise Exception(u"Need a usable datetime string to return a standard "
                        u"datetime string.")
    else: 
        # usable (possibly requiring a date to be added to a time)
        # has at least one part (date/time) and anything it has is ok
        (date_part, date_format, time_part, time_format, boldate_then_time) = \
            datetime_dets
        # determine what type of valid datetime then make time object    
        if date_part is not None and time_part is not None:
            if boldate_then_time:           
                time_obj = time.strptime("%s %s" % (date_part, time_part), 
                                         "%s %s" % (date_format, time_format))
            else: # time then date
                time_obj = time.strptime("%s %s" % (time_part, date_part),
                                         "%s %s" % (time_format, date_format))
        elif date_part is not None and time_part is None:
            # date only (add time of 00:00:00)
            time_obj = time.strptime("%s 00:00:00" % date_part, 
                                     "%s %%H:%%M:%%S" % date_format)
        elif date_part is None and time_part is not None:
            # time only (assume today's date)
            today = time.localtime()
            time_obj = time.strptime("%s-%s-%s %s" % (today[0], today[1], 
                                                      today[2], time_part), 
                                     "%%Y-%%m-%%d %s" % time_format)
        else:
            raise Exception(u"Supposedly a usable datetime str but no usable "
                            u"parts")
        if debug: print(time_obj)
        std_datetime_str = time_obj_to_datetime_str(time_obj)
        return std_datetime_str

def time_obj_to_datetime_str(time_obj):
    "Takes time_obj and returns standard datetime string"
    datetime_str = "%4d-%02d-%02d %02d:%02d:%02d" % (time_obj[:6])
    return datetime_str

# data

def get_item_label(item_labels, item_val):
    """
    e.g. if lacking a label, turn agegrp into Agegrp
    e.g. if has a label, turn agegrp into Age Group
    """
    item_val_u = any2unicode(item_val)
    return item_labels.get(item_val, item_val_u.title())

def get_choice_item(item_labels, item_val):
    """
    e.g. "Age Group (agegrp)"
    """
    item_label = get_item_label(item_labels, item_val)
    return u"%s (%s)" % (item_label, any2unicode(item_val))

def get_sorted_choice_items(dic_labels, vals, inc_drop_select=False):
    """
    Sorted by label, not name.
    dic_labels - could be for either variables of values.
    vals - either variables or values.
    If DROP_SELECT in list, always appears first.
    Returns choice_items_sorted, orig_items_sorted.
    http://www.python.org/doc/faq/programming/#i-want-to-do-a-complicated- ...
        ... sort-can-you-do-a-schwartzian-transform-in-python
    """
    sorted_vals = vals
    sorted_vals.sort(key=lambda s: get_choice_item(dic_labels, s).upper())
    choice_items = [get_choice_item(dic_labels, x) for x in sorted_vals]
    if inc_drop_select:
        choice_items.insert(0, mg.DROP_SELECT)
        sorted_vals.insert(0, mg.DROP_SELECT)
    return choice_items, sorted_vals

def get_selected_choice_item(vars_lst, var_labels, idx):
    
    return choice_item

def get_selected_var_name(vars_lst, idx):
    
    return var_name

def get_selected_var_label(vars_lst, var_labels, idx):
    
    return var_label

# report tables
def get_default_measure(tab_type):
    """
    Get default measure appropriate for table type
    NB raw tables don't have measures
    """
    if tab_type in (mg.FREQS_TBL, mg.CROSSTAB): 
        return mg.FREQ
    elif tab_type == mg.ROW_SUMM:
        return mg.MEAN
    elif tab_type == mg.RAW_DISPLAY:
        raise Exception(u"Data Lists do not have measures")
    else:
        raise Exception(u"Unexpected table type in get_default_measure()")
        
def get_col_dets(coltree, colroot, var_labels):
    """
    Get names and labels of columns actually selected in GUI column tree.
    Returns col_names, col_labels.
    """
    descendants = get_tree_ctrl_descendants(tree=coltree, parent=colroot)
    col_names = []
    for descendant in descendants: # NB GUI tree items, not my Dim Node obj
        item_conf = coltree.GetItemPyData(descendant)
        col_names.append(item_conf.var_name)
    col_labels = [var_labels.get(x, x.title()) for x in col_names]
    return col_names, col_labels


class ItemConfig(object):
    """
    Item config storage and retrieval.
    Has: var_name, measures, has_tot, sort order, bolnumeric
    NB: won't have a var name if it is the column config item.
    """
    
    def __init__(self, var_name=None, measures_lst=None, has_tot=False, 
                 sort_order=mg.SORT_NONE, bolnumeric=False):
        self.var_name = var_name
        if measures_lst:
            self.measures_lst = measures_lst
        else:
            self.measures_lst = []
        self.has_tot = has_tot
        self.sort_order = sort_order
        self.bolnumeric = bolnumeric
    
    def has_data(self):
        """
        Has the item got any extra config e.g. measures, a total?
        Variable name doesn't count.
        """
        return self.measures_lst or self.has_tot or \
            self.sort_order != mg.SORT_NONE
    
    def get_summary(self, verbose=False):
        """
        String summary of data (apart from variable name).
        """
        str_parts = []
        total_part = _("Has TOTAL") if self.has_tot else None
        if total_part:
            str_parts.append(total_part)
        if self.sort_order == mg.SORT_NONE:
            sort_order_part = None
        elif self.sort_order == mg.SORT_LABEL:
            sort_order_part = _("Sort by Label")
        elif self.sort_order == mg.SORT_INCREASING:
            sort_order_part = _("Sort by Freq (Asc)")
        elif self.sort_order == mg.SORT_DECREASING:
            sort_order_part = _("Sort by Freq (Desc)")            
        if sort_order_part:
            str_parts.append(sort_order_part)
        if verbose:
            if self.bolnumeric:
                str_parts.append(_("Numeric"))
            else:
                str_parts.append(_("Not numeric"))
        measures = ", ".join(self.measures_lst)
        measures_part = _("Measures: %s") % measures if measures else None
        if measures_part:
            str_parts.append(measures_part)
        return u"; ".join(str_parts)

# All items are ids with methods e.g. IsOk().  The tree uses the ids to do 
# things.  Items don't get their siblings; the tree does knowing the item id.
def get_tree_ctrl_children(tree, item):
    """
    Get children of TreeCtrl item
    """
    children = []
    child, cookie = tree.GetFirstChild(item) # p.471 wxPython
    while child: # an id
        children.append(child)
        child, cookie = tree.GetNextChild(item, cookie)
    return children

def item_has_children(tree, parent):
    """
    tree.item_has_children(item_id) doesn't work if root is hidden.
    E.g. self.tree = wx.gizmos.TreeListCtrl(self, -1, 
                      style=wx.TR_FULL_ROW_HIGHLIGHT | \
                      wx.TR_HIDE_ROOT)
    wxTreeCtrl::ItemHasChildren
    bool ItemHasChildren(const wxTreeItemId& item) const
    Returns TRUE if the item has children.
    """
    item, cookie = tree.GetFirstChild(parent) # item is an id
    return True if item else False

def get_tree_ctrl_descendants(tree, parent, descendants=None):
    """
    Get all descendants (descendent is an alternative spelling in English grrr).
    """
    if descendants is None:
        descendants = []
    children = get_tree_ctrl_children(tree, parent)
    for child in children:
        descendants.append(child)
        get_tree_ctrl_descendants(tree, child, descendants)
    return descendants

def get_sub_tree_items(tree, parent):
    "Return string representing subtree"
    descendants = get_tree_ctrl_descendants(tree, parent)
    descendant_labels = [tree.GetItemText(x) for x in descendants]
    return ", ".join(descendant_labels)

def get_tree_ancestors(tree, child):
    "Get ancestors of TreeCtrl item"
    ancestors = []
    item = tree.GetItemParent(child)
    while item: # an id
        ancestors.append(item)
        item = tree.GetItemParent(item)
    return ancestors

    
class StaticWrapText(wx.StaticText):
    """
    A StaticText-like widget which implements word wrapping.
    http://yergler.net/projects/stext/stext_py.txt
    __id__ = "$Id: stext.py,v 1.1 2004/09/15 16:45:55 nyergler Exp $"
    __version__ = "$Revision: 1.1 $"
    __copyright__ = '(c) 2004, Nathan R. Yergler'
    __license__ = 'licensed under the GNU GPL2'
    """
    
    def __init__(self, *args, **kwargs):
        wx.StaticText.__init__(self, *args, **kwargs)
        # store the initial label
        self.__label = super(StaticWrapText, self).get_label()
        # listen for sizing events
        self.Bind(wx.EVT_SIZE, self.on_size)

    def set_label(self, newLabel):
        """Store the new label and recalculate the wrapped version."""
        self.__label = newLabel
        self.__wrap()

    def get_label(self):
        """Returns the label (unwrapped)."""
        return self.__label
    
    def __wrap(self):
        """Wraps the words in label."""
        words = self.__label.split()
        lines = []
        # get the maximum width (that of our parent)
        max_width = self.GetParent().GetVirtualSizeTuple()[0]        
        index = 0
        current = []
        for word in words:
            current.append(word)
            if self.GetTextExtent(" ".join(current))[0] > max_width:
                del current[-1]
                lines.append(" ".join(current))
                current = [word]
        # pick up the last line of text
        lines.append(" ".join(current))
        # set the actual label property to the wrapped version
        super(StaticWrapText, self).set_label("\n".join(lines))
        # refresh the widget
        self.Refresh()
        
    def on_size(self, event):
        # dispatch to the wrap method which will 
        # determine if any changes are needed
        self.__wrap()