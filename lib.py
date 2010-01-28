#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import codecs
import datetime
import decimal
import os
import pprint
import re
import subprocess
import sys
import time
import wx

# only import my_globals from local modules
import my_globals

def split_lst(lst, slice_size):
    cut_a = 0
    cut_b = slice_size
    split_lst = []
    while True:
        slice = lst[cut_a: cut_b]
        split_lst.append(slice)
        cut_a += slice_size
        cut_b += slice_size
        if cut_b > len(lst):
            break
    return split_lst

def get_title_dets_html(titles, subtitles, CSS_TBL_TITLE, CSS_TBL_SUBTITLE):
    """
    Table title and subtitle html ready to put in a cell.
    Applies to dim tables and raw tables.
    Do not want block display - if title and/or subtitle are empty, want minimal
        display height.
    """
    titles_html = u"\n<span class='%s'>%s" % (CSS_TBL_TITLE, 
                                           my_globals.TBL_TITLE_START)
    titles_inner_html = get_titles_inner_html(titles_html, titles)
    titles_html += titles_inner_html
    titles_html += u"%s</span>" % my_globals.TBL_TITLE_END
    subtitles_html = u"\n<span class='%s'>%s" % (CSS_TBL_SUBTITLE, 
                                        my_globals.TBL_SUBTITLE_START)
    subtitles_inner_html = get_subtitles_inner_html(subtitles_html, 
                                                        subtitles)
    subtitles_html += subtitles_inner_html 
    subtitles_html += u"%s</span>" % my_globals.TBL_SUBTITLE_END
    joiner = u"<br>" if titles_inner_html and subtitles_inner_html else u""
    title_dets_html = titles_html + joiner + subtitles_html
    return title_dets_html

def get_titles_inner_html(titles_html, titles):
    """
    Just the bits within the tags, css etc.
    """
    return u"<br>".join(titles)

def get_subtitles_inner_html(subtitles_html, subtitles):
    """
    Just the bits within the tags, css etc.
    """
    return u"<br>".join(subtitles)

def get_text_to_draw(orig_txt, max_width):
    "Return text broken into new lines so wraps within pixel width"
    mem = wx.MemoryDC()
    # add words to it until its width is too long then put int split
    lines = []
    words = orig_txt.split()
    line_words = []
    for word in words:
        line_words.append(word)
        line_width = mem.GetTextExtent(" ".join(line_words))[0]
        if line_width > max_width:
            line_words.pop()
            lines.append(u" ".join(line_words))
            line_words = [word]
    lines.append(u" ".join(line_words))
    wrapped_txt = u"\n".join(lines)
    return wrapped_txt

def add_text_to_bitmap(bitmap, text, font, colour, left=9, top=3):
    """
    Add short text to bitmap with standard left margin.
    Can then use bitmap for a bitmap button.
    See http://wiki.wxpython.org/index.cgi/WorkingWithImages
    """
    mem = wx.MemoryDC()
    mem.SelectObject(bitmap)
    mem.SetFont(font)
    mem.SetTextForeground(colour)
    rect = wx.Rect(left, top, bitmap.GetWidth(), bitmap.GetHeight())
    mem.DrawLabel(text, rect)    
    mem.SelectObject(wx.NullBitmap)
    return bitmap

def get_tbl_filt(dbe, db, tbl):
    """
    Returns tbl_filt_label, tbl_filt
    """
    try:
        tbl_filt_label, tbl_filt = my_globals.DBE_TBL_FILTS[dbe][db][tbl]
    except KeyError:
        tbl_filt_label, tbl_filt = u"", u""
    return tbl_filt_label, tbl_filt

def get_tbl_filt_clause(dbe, db, tbl):
    tbl_filt_label, tbl_filt = get_tbl_filt(dbe, db, tbl)
    return 'tbl_filt = """ %s """' % tbl_filt

def get_tbl_filts(tbl_filt):
    """
    Returns filters ready to use as WHERE and AND filters:
        where_filt, and_filt
    Filters must still work if empty strings (for performance when no filter 
        required).
    """
    if tbl_filt.strip() != "":
        where_tbl_filt = u" WHERE %s" % tbl_filt
        and_tbl_filt = u" AND %s" % tbl_filt
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

def is_numeric(val):
    """
    Is a value numeric?  This is operationalised to mean can a value be cast as 
        a float.  
    NB the string 5 is numeric.  Scientific notation is numeric. Complex numbers 
        are considered not numeric for general use.  
    The type may not be numeric but the "content" must be.
    http://www.rosettacode.org/wiki/IsNumeric#Python
    """
    if isPyTime(val):
        return False
    elif val is None:
        return False
    else:
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
    
def str2unicode(raw):
    """
    If not a string, just return value unchanged.  Otherwise ...
    Convert byte strings to unicode.
    Convert any cp1252 text to unicode e.g. smart quotes.
    Return safe unicode string (pure unicode and no unescaped backslashes).
    """
    if not isinstance(raw, basestring): # isinstance includes descendants
        return raw
    if type(raw) == str:
        try:
            safe = raw.decode("utf-8")
        except UnicodeDecodeError:
            safe = ms2utf8(raw)
    else:
        safe = ms2utf8(raw)
    return safe

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
            raise Exception, "Unable to convert value to Decimal.  " + \
                "Value was \"%s\"" % f
    try:
        n, d = f.as_integer_ratio()
    except Exception:
        raise Exception, "Unable to turn value \"%s\" into integer " % f + \
            "ratio for unknown reason."
    numerator, denominator = decimal.Decimal(n), decimal.Decimal(d)
    ctx = decimal.Context(prec=60)
    result = ctx.divide(numerator, denominator)
    while ctx.flags[decimal.Inexact]:
        ctx.flags[decimal.Inexact] = False
        ctx.prec *= 2
        result = ctx.divide(numerator, denominator)
    return result

# uncovered

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

def ms2utf8(text):
    if not isinstance(text, basestring):
        return text
    # http://effbot.org/zone/unicode-gremlins.htm
    # map cp1252 gremlins to real unicode characters
    # NB the resulting unicode characters may still be outside of ascii 
    if re.search(u"[\x80-\x9f]", text):
        def fixup(m):
            s = m.group(0)
            return cp1252.get(s, s)
        if isinstance(text, type("")):
            # make sure we have a unicode string
            text = unicode(text, "iso-8859-1")
        text = re.sub(u"[\x80-\x9f]", fixup, text)
    return text

def clean_bom_utf8(raw):
    if raw.startswith(unicode(codecs.BOM_UTF8, "utf-8")):
        raw = raw[len(unicode(codecs.BOM_UTF8, "utf-8")):]
    return raw

if my_globals.IN_WINDOWS:
    import pywintypes

def escape_win_path(path):
    "Useful when writing a path to a text file"
    return path.replace("\\", "\\\\")

def getFileName(path):
    "Works on Windows paths as well"
    path = path.replace("\\\\", "\\").replace("\\", "/")
    return os.path.split(path)[1]
    
def isInteger(val):
    #http://mail.python.org/pipermail/python-list/2006-February/368113.html
    return isinstance(val, (int, long))

def isString(val):
    # http://mail.python.org/pipermail/winnipeg/2007-August/000237.html
    return isinstance(val, basestring)

def isPyTime(val): 
    #http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/511451
    return type(val).__name__ == 'time'
    
def if_none(val, default):
    """
    Returns default if value is None - otherwise returns value.
    While there is a regression in pywin32 cannot compare pytime with anything
        see http://mail.python.org/pipermail/python-win32/2009-March/008920.html
    """
    if isPyTime(val):
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
        raise Exception, "Please pass valid start and " + \
            "end dates as per the required format e.g. 25-01-2007"    

def mysql2textdate(mysql_date, output_format):
    """
    Takes MySQL date e.g. 2008-01-25 and returns date string according to 
        format.  NB must be valid format for strftime.
    """
    year = int(mysql_date[:4])
    month = int(mysql_date[5:7])
    day = int(mysql_date[-2:])
    mydate = (year, month, day, 0, 0, 0, 0, 0, 0)
    return time.strftime(output_format, mydate)

def is_date_part(datetime_str):
    """
    Assumes date will have - or / or . and time will not.
    If a mishmash will fail bad_date later.
    """
    return "-" in datetime_str or "/" in datetime_str or "." in datetime_str

def is_time_part(datetime_str):
    """
    Assumes time will have : (or am/pm) and date will not.
    If a mishmash will fail bad_time later.
    """
    return ":" in datetime_str or "am" in datetime_str.lower() \
        or "pm" in datetime_str.lower()

def IsYear(datetime_str):
    is_year = False
    try:
        year = int(datetime_str)
        is_year = (1 <= year < 10000) 
    except Exception:
        pass
    return is_year

def datetime_split(datetime_str):
    """
    Split date and time (if both)
    Return date part, time part, order (True unless order 
        time then date).
    Return None for any missing components.
    Must be only one space in string (if any) - between date and time
        (or time and date).
    boldate_then_time -- only False if time then date with both present.
    """
    if " " in datetime_str:
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
    elif IsYear(datetime_str):
        return (datetime_str, None, True)
    else: # only one part
        boldate_then_time = True
        if is_date_part(datetime_str):
            return (datetime_str, None, boldate_then_time)
        elif is_time_part(datetime_str):
            return (None, datetime_str, boldate_then_time)
        else:
            return (None, None, boldate_then_time)

def get_dets_of_usable_datetime_str(raw_datetime_str):
    """
    Returns (date_part, date_format, time_part, time_format, boldate_then_time) 
        if a usable datetime.  NB usable doesn't mean valid as such.  E.g. we 
        may need to add a date to the time to make it valid.
    Returns None if not usable.
    These parts can be used to make a valid time object ready for conversion 
        into a standard string for data entry.
    """
    debug = False
    if not isString(raw_datetime_str):
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
        # see CellInvalid for message about correct datetime entry formats
        bad_date = True
        for ok_date_format in my_globals.OK_DATE_FORMATS:
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
        ok_time_formats = ["%I%p", "%I:%M%p", "%H:%M", "%H:%M:%S"]
        for ok_time_format in my_globals.OK_TIME_FORMATS:
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

def is_usable_datetime_str(raw_datetime_str):
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
    return get_dets_of_usable_datetime_str(raw_datetime_str) is not None
    
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
    datetime_dets = get_dets_of_usable_datetime_str(raw_datetime_str)
    if datetime_dets is None:
        raise Exception, ("Need a usable datetime string to return a standard "
                          "datetime string.")
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
            raise Exception, ("Supposedly a usable datetime str but no usable "
                              "parts")
        if debug: print(time_obj)
        std_datetime_str = time_obj_to_datetime_str(time_obj)
        return std_datetime_str

def time_obj_to_datetime_str(time_obj):
    "Takes time_obj and returns standard datetime string"
    datetime_str = "%4d-%02d-%02d %02d:%02d:%02d" % (time_obj[:6])
    return datetime_str

# data
def get_choice_item(item_labels, item_val):
    val_label = any2unicode(item_val)
    return u"%s (%s)" % (item_labels.get(item_val, val_label.title()), 
                         val_label)

def get_sorted_choice_items(dic_labels, vals):
    """
    Sorted by label, not name.
    dic_labels - could be for either variables of values.
    vals - either variables or values.
    Returns choice_items_sorted, orig_items_sorted.
    http://www.python.org/doc/faq/programming/#i-want-to-do-a-complicated- ...
        ... sort-can-you-do-a-schwartzian-transform-in-python
    """
    sorted_vals = vals
    sorted_vals.sort(key=lambda s: get_choice_item(dic_labels, s).upper())
    choice_items = [get_choice_item(dic_labels, x) for x in sorted_vals]
    return choice_items, sorted_vals

def extract_var_choice_dets(choice_text):
    """
    Extract name, label from item
    e.g. return "gender" and "Gender" from "Gender (gender)".
    Returns as string (even if original was a number etc).
    If not in this format, e.g. special col measures label, handle differently.
    """
    try:
        start_idx = choice_text.index("(") + 1
        end_idx = choice_text.index(")")
        item_val = choice_text[start_idx:end_idx]
        item_label = choice_text[:start_idx - 2]
    except Exception:
        item_val = choice_text
        item_label = choice_text        
    return item_val, item_label

# report tables
def get_default_measure(tab_type):
    """
    Get default measure appropriate for table type
    NB raw tables don't have measures
    """
    if tab_type == my_globals.COL_MEASURES: 
        return my_globals.FREQ
    elif tab_type == my_globals.ROW_SUMM:
        return my_globals.MEAN
    else:
        raise Exception, u"Only dimension tables have measures"

def get_col_dets(coltree, colRoot, var_labels):
    """
    Get names and labels of columns actually selected in GUI column tree.
    Returns col_names, col_labels.
    """
    full_col_labels = get_sub_tree_items(coltree, colRoot)
    split_col_tree_labels = full_col_labels.split(", ")        
    col_names = [extract_var_choice_dets(x)[0] for x in split_col_tree_labels]
    col_labels = [var_labels.get(x, x.title()) for x in col_names]
    return col_names, col_labels


class ItemConfig(object):
    """
    Item config storage and retrieval.
    Has: measures, has_tot, sort order, bolnumeric
    """
    
    def __init__(self, measures_lst=None, has_tot=False, 
                 sort_order=my_globals.SORT_NONE, bolnumeric=False):
        if measures_lst:
            self.measures_lst = measures_lst
        else:
            self.measures_lst = []
        self.has_tot = has_tot
        self.sort_order = sort_order
        self.bolnumeric = bolnumeric
    
    def hasData(self):
        "Has the item got any extra config e.g. measures, a total?"
        return self.measures_lst or self.has_tot or \
            self.sort_order != my_globals.SORT_NONE
    
    def getSummary(self, verbose=False):
        "String summary of data"
        str_parts = []
        total_part = _("Has TOTAL") if self.has_tot else None
        if total_part:
            str_parts.append(total_part)
        if self.sort_order == my_globals.SORT_NONE:
            sort_order_part = None
        elif self.sort_order == my_globals.SORT_LABEL:
            sort_order_part = _("Sort by Label")
        elif self.sort_order == my_globals.SORT_FREQ_ASC:
            sort_order_part = _("Sort by Freq (Asc)")
        elif self.sort_order == my_globals.SORT_FREQ_DESC:
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

def get_tree_ctrl_children(tree, parent):
    "Get children of TreeCtrl item"
    children = []
    item, cookie = tree.GetFirstChild(parent) #p.471 wxPython
    while item:
        children.append(item)
        item, cookie = tree.GetNextChild(parent, cookie)
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
    item, cookie = tree.GetFirstChild(parent)
    return True if item else False

def get_tree_ctrl_descendants(tree, parent, descendants=None):
    """
    Get all descendants (descendent is an alternative spelling 
    in English grrr).
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
    while item:
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
        self.__label = super(StaticWrapText, self).GetLabel()
        # listen for sizing events
        self.Bind(wx.EVT_SIZE, self.OnSize)

    def SetLabel(self, newLabel):
        """Store the new label and recalculate the wrapped version."""
        self.__label = newLabel
        self.__wrap()

    def GetLabel(self):
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
        super(StaticWrapText, self).SetLabel("\n".join(lines))
        # refresh the widget
        self.Refresh()
        
    def OnSize(self, event):
        # dispatch to the wrap method which will 
        # determine if any changes are needed
        self.__wrap()