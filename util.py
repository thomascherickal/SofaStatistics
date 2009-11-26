#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import codecs
import datetime
import decimal
import os
import pprint
import re
import sys
import time
import wx

# must be kept safe to import - must never refer to anything in other modules

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

def get_unicode(raw):
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

def clean_bom_utf8(raw):
    if raw.startswith(unicode(codecs.BOM_UTF8, "utf-8")):
        raw = raw[len(unicode(codecs.BOM_UTF8, "utf-8")):]
    return raw

def f2d(f):
    """
    Convert a floating point number to a Decimal with no loss of information
    http://docs.python.org/library/decimal.html
    """
    if not isinstance(f, float):
        f = float(f)
    try:
        n, d = f.as_integer_ratio()
    except Exception:
        raise Exception, "Unable to turn value %s into integer ration " % f + \
            "for unknown reason."
    numerator, denominator = decimal.Decimal(n), decimal.Decimal(d)
    ctx = decimal.Context(prec=60)
    result = ctx.divide(numerator, denominator)
    while ctx.flags[decimal.Inexact]:
        ctx.flags[decimal.Inexact] = False
        ctx.prec *= 2
        result = ctx.divide(numerator, denominator)
    return result

def in_windows():
    try:
        in_windows = os.environ['OS'].lower().startswith("windows")
    except Exception:
        in_windows = False
    return in_windows

if in_windows():
    import pywintypes

def get_user_paths():
    if in_windows():
        user_path = unicode(os.environ['USERPROFILE'], "utf-8")
    else:
        user_path = unicode(os.environ['HOME'], "utf-8")
    local_path = os.path.join(user_path, u"sofa")
    return user_path, local_path

def get_script_path():
    """
    NB won't work within an interpreter
    """
    return sys.path[0]

def get_local_path():
    return "%s/sofa" % os.getenv('HOME')

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

def isNumeric(val):
    "http://www.rosettacode.org/wiki/IsNumeric#Python"
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

def timeobj_to_datetime_str(timeobj):
    "Takes timeobj and returns standard datetime string"
    datetime_str = "%4d-%02d-%02d %02d:%02d:%02d" % (timeobj[:6])
    return datetime_str

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
    Assumes date will have - or / and time will not.
    If a mishmash will fail ok_date later.
    """
    return "-" in datetime_str or "/" in datetime_str

def is_time_part(datetime_str):
    """
    Assumes time will have : (or am/pm) and date will not.
    If a mishmash will fail ok_time later.
    """
    return ":" in datetime_str or "am" in datetime_str.lower() \
        or "pm" in datetime_str.lower()

def IsYear(datetime_str):
    is_year = False
    try:
        year = int(datetime_str)
        is_year = (1900 <= year < 10000) 
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
    """
    if " " in datetime_str:
        date_then_time = True
        datetime_split = datetime_str.split(" ")
        if len(datetime_split) != 2:
            return (None, None, True)
        if is_date_part(datetime_split[0]) \
                and is_time_part(datetime_split[1]):
            return (datetime_split[0], datetime_split[1], True)
        elif is_date_part(datetime_split[1]) \
                and is_time_part(datetime_split[0]):
            return (datetime_split[1], datetime_split[0], False)
        else:
            return (None, None, date_then_time)
    elif IsYear(datetime_str):
        return (datetime_str, None, True)
    else: # only one part
        date_then_time = True
        if is_date_part(datetime_str):
            return (datetime_str, None, date_then_time)
        elif is_time_part(datetime_str):
            return (None, datetime_str, date_then_time)
        else:
            return (None, None, date_then_time)

def valid_datetime_str(val):
    """
    Is the datetime string in a valid format?
    Returns tuple of Boolean and either a time object if True 
        or None if False. e.g. boldatetime, time_obj
    Used for checking user-entered datetimes.
    Doesn't cover all possibilities - just what is needed for typical data 
        entry.
    If only a time, use today's date.
    If only a date, use midnight as time e.g. MySQL 00:00:00
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
    debug = False
    if not isString(val):
        if debug: print("%s is not a valid datetime string" % val)
        return (False, None)
    # evaluate date and/or time components against allowable formats
    date_part, time_part, date_time_order = datetime_split(val)
    if date_part is None and time_part is None:
        return False, None
    # gather information on all parts
    if date_part:
        ok_date = False
        ok_date_format = None
        ok_date_formats = ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y"]
        for ok_date_format in ok_date_formats:
            try:
                t = time.strptime(date_part, ok_date_format)
                ok_date = True
                break
            except:
                pass
    if time_part:
        ok_time = False
        ok_time_format = None
        ok_time_formats = ["%I%p", "%I:%M%p", "%H:%M", "%H:%M:%S"]
        for ok_time_format in ok_time_formats:
            try:
                t = time.strptime(time_part, ok_time_format)
                ok_time = True
                break
            except:
                pass
    # determine what type of valid datetime then make time object    
    if date_part is not None and time_part is not None and ok_date and ok_time:
        if date_time_order: # date then time            
            t = time.strptime("%s %s" % (date_part, time_part), 
                              "%s %s" % (ok_date_format, ok_time_format))
        else: # time then date
            t = time.strptime("%s %s" % (time_part, date_part),
                              "%s %s" % (ok_time_format, ok_date_format))
    elif date_part is not None and time_part is None and ok_date:
        # date only (add time of 00:00:00)
        t = time.strptime("%s 00:00:00" % date_part, 
                          "%s %%H:%%M:%%S" % ok_date_format)
    elif date_part is None and time_part is not None and ok_time:
        # time only (assume today's date)
        today = time.localtime()
        t = time.strptime("%s-%s-%s %s" % (today[0], today[1], today[2], 
                                           time_part), 
                          "%%Y-%%m-%%d %s" % ok_time_format)
    else:
        return False, None
    if debug: print(t)
    return True, t
    
def getTreeCtrlChildren(tree, parent):
    "Get children of TreeCtrl item"
    children = []
    item, cookie = tree.GetFirstChild(parent) #p.471 wxPython
    while item:
        children.append(item)
        item, cookie = tree.GetNextChild(parent, cookie)
    return children

def ItemHasChildren(tree, parent):
    """
    tree.ItemHasChildren(item_id) doesn't work if root is hidden.
    E.g. self.tree = wx.gizmos.TreeListCtrl(self, -1, 
                      style=wx.TR_FULL_ROW_HIGHLIGHT | \
                      wx.TR_HIDE_ROOT)
    wxTreeCtrl::ItemHasChildren
    bool ItemHasChildren(const wxTreeItemId& item) const
    Returns TRUE if the item has children.
    """
    item, cookie = tree.GetFirstChild(parent)
    return True if item else False

def getTreeCtrlDescendants(tree, parent, descendants=None):
    """
    Get all descendants (descendent is an alternative spelling 
    in English grrr).
    """
    if descendants is None:
        descendants = []
    children = getTreeCtrlChildren(tree, parent)
    for child in children:
        descendants.append(child)
        getTreeCtrlDescendants(tree, child, descendants)
    return descendants

def getSubTreeItems(tree, parent):
    "Return string representing subtree"
    descendants = getTreeCtrlDescendants(tree, parent)
    descendant_labels = [tree.GetItemText(x) for x in descendants]
    return ", ".join(descendant_labels)

def getTreeAncestors(tree, child):
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
        