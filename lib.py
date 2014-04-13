#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import

import codecs
import datetime
import decimal
import locale
import math
from operator import itemgetter
import os
import random
import re
import time
import urllib

import wx

# only import my_globals from local modules
import basic_lib as b
import my_globals as mg
import my_exceptions

# so we only do expensive tasks once per module per session
PURCHASE_CHECKED_EXTS = [] # individual extensions may have different purchase statements

def get_gettext_setup_txt():
    """
    Must achieve same result for gettext as occurs in SofaApp.setup_i18n() in
    start.py.
    
    Need to explicitly set proper locale in scripts so they can run 
    independently of the GI.
    
    Doesn't need to be in start.py but safest to be next to where code it is
    meant to replicate.
    """
    bits = []
    bits.append(u"try:")
    bits.append(u"    mytrans = gettext.translation(u'sofastats', \"%s\"," % 
        mg.LANGDIR)
    bits.append(u"        languages=[u'%s',], fallback=True)" % mg.CANON_NAME)
    bits.append(u"    mytrans.install(unicode=True)")
    bits.append(u"except Exception, e:")
    bits.append(u"    raise Exception(u\"Problem installing translation. \"")
    bits.append(u"        u\"Original error: %s\" % e)")
    if mg.PLATFORM == mg.LINUX:
        bits.append(u"try:")
        bits.append(u"    os.environ['LANG'] = u'%s.UTF-8'" % mg.CANON_NAME)
        bits.append(u"except (ValueError, KeyError):")
        bits.append(u"    pass # OK if unable to set environment settings.")
    return "\n".join(bits)

def formatnum(num):
    try:
        formatted = "{:,}".format(num)
    except ValueError:
        formatted = num
    return formatted

def extract_img_path(content, use_as_url=False):
    """
    Extract image path from html.
    
    use_as_url -- is the path going to be used as a url (if not we need to 
    unquote it) so the image path we extract can be used by the os e.g. to 
    copy an image
    
    IMG_SRC_START -- u"<img src='"
    """
    debug = False
    idx_start = content.index(mg.IMG_SRC_START) + len(mg.IMG_SRC_START)
    if debug: print(u"\n\n\nextract_img_path\n%s" % content)
    content_after_start = content[idx_start:]
    idx_end = content_after_start.index(mg.IMG_SRC_END) + idx_start
    img_path = content[idx_start: idx_end]
    if debug: 
        print(u"idx_end: %s" % idx_end)
        print(u"img_path: %s" % img_path)
    if not use_as_url:
        img_path = urllib.unquote(img_path) # so a proper path and not %20 etc
        if debug: print(u"not use_as_url img_path:\n%s" % img_path)
    # strip off 'file:///' (or file:// as appropriate for os)
    if mg.PLATFORM == mg.WINDOWS and mg.FILE_URL_START_WIN in img_path:
        img_path = os.path.join(u"", img_path.split(mg.FILE_URL_START_WIN)[1])
    elif mg.FILE_URL_START_GEN in img_path:
        img_path = os.path.join(u"", img_path.split(mg.FILE_URL_START_GEN)[1])
    if debug: print(u"Final img_path:\n%s" % img_path)
    return img_path

def get_src_dst_preexisting_img(export_report, imgs_path, content):
    """
    export_report -- boolean (cf export output)
    imgs_path -- 
    e.g. export output: /home/g/Desktop/SOFA export Sep 30 09-34 AM
    e.g. export report: /home/g/Documents/sofastats/reports/test_exporting_exported_images
    content -- 
    e.g. export output: <img src='file:///home/g/Documents/sofastats/reports/sofa_use_only_report_images/_img_001.png'>
    e.g. export report: <img src='test_exporting_images/000.png'>
    want src to be /home/g/Documents/sofastats/reports/sofa_use_only_report_images/_img_001.png 
        (not file:///home ...)
    and dst to be
    e.g. export output: /home/g/Desktop/SOFA export Sep 30 09-34 AM/_img_001.png
    e.g. export report: /home/g/Documents/sofastats/reports/test_exporting_exported_images/000.png
    """
    debug = False
    img_path = extract_img_path(content, use_as_url=False)
    if debug: print(u"get_src_dst_preexisting_img\nimg_path:\n%s\n" % img_path)
    if export_report: # trim off trailing divider, then split and get first part
        src = os.path.join(os.path.split(imgs_path[:-1])[0], img_path)
    else:
        src = img_path # the run_report process leaves an abs version. How nice!
    if debug: print(u"src:\n%s\n" % src)
    img_name = os.path.split(img_path)[1]
    if debug: print(u"img_path:\n%s\n" % img_path)
    dst = os.path.join(imgs_path, img_name)
    if debug: print(u"dst:\n%s\n" % dst)
    return src, dst

def setup_link(link, link_colour, bg_colour):
    link.SetColours(link=link_colour, visited=link_colour, 
        rollover=link_colour)
    link.SetOwnBackgroundColour(bg_colour)
    link.SetOwnFont(wx.Font(12 if mg.PLATFORM == mg.MAC else 9, 
        wx.SWISS, wx.NORMAL, wx.NORMAL))
    link.SetSize(wx.Size(250, 17))
    link.SetUnderlines(link=True, visited=True, rollover=False)
    link.SetLinkCursor(wx.CURSOR_HAND)
    link.EnableRollover(True)
    link.SetVisited(True)
    link.UpdateLink(True)


class DlgHelp(wx.Dialog):
    def __init__(self, parent, title, guidance_lbl, activity_lbl, guidance, 
            help_pg):
        wx.Dialog.__init__(self, parent=parent, title=title, 
            style=wx.CAPTION|wx.CLOSE_BOX|wx.SYSTEM_MENU, 
            pos=(mg.HORIZ_OFFSET+100,100))
        self.panel = wx.Panel(self)
        self.help_pg = help_pg
        self.Bind(wx.EVT_CLOSE, self.on_close)
        bx_guidance = wx.StaticBox(self.panel, -1, guidance_lbl)
        szr_guidance = wx.StaticBoxSizer(bx_guidance, wx.VERTICAL)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        lbl_guidance = wx.StaticText(self.panel, -1, guidance)
        szr_guidance.Add(lbl_guidance, 1, wx.GROW|wx.ALL, 10)
        btn_online_help = wx.Button(self.panel, -1, _("Online Help"))
        btn_online_help.Bind(wx.EVT_BUTTON, self.on_online_help)
        btn_online_help.SetToolTipString(_(u"Get more help with %s "
                                           "online") % activity_lbl)
        btn_close = wx.Button(self.panel, wx.ID_CLOSE)
        btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        szr_btns = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=5)
        szr_btns.AddGrowableCol(1,2) # idx, propn
        szr_btns.Add(btn_online_help, 0)
        szr_btns.Add(btn_close, 0, wx.ALIGN_RIGHT)
        szr_main.Add(szr_guidance, 0, wx.GROW|wx.ALL, 10)
        szr_main.Add(szr_btns, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(szr_main)
        szr_main.SetSizeHints(self)
        self.Layout()
        
    def on_online_help(self, event):
        import webbrowser
        url = (u"http://www.sofastatistics.com/wiki/doku.php"
            u"?id=help:%s" % self.help_pg)
        webbrowser.open_new_tab(url)
        event.Skip()
        
    def on_close(self, event):
        self.Destroy()
        

def fix_eols(orig):
    """
    Prevent EOL errors by replacing any new lines with spaces.
    Prevents variable or value labels, for example, with line breaks.
    """
    try:
        fixed = orig.replace(u"\n", u" ")
    except AttributeError: # e.g. None
        fixed = orig
    return fixed

def get_num2display(num, output_type, inc_perc=True):
    if output_type == mg.FREQ_KEY:
        num2display = unicode(num)
    else:
        if inc_perc:
            num2display = u"%s%%" % round(num, 1)
        else:
            num2display = u"%s" % round(num, 1)
    return num2display

def current_lang_rtl():
    return wx.GetApp().GetLayoutDirection() == wx.Layout_RightToLeft

def mustreverse():
    "Other OSs may require it too but uncertain at this stage"
    #return True #testing
    return current_lang_rtl() and mg.PLATFORM == mg.WINDOWS

def quote_val(raw_val, sql_str_literal_quote, sql_esc_str_literal_quote, 
              pystr_use_double_quotes=True, charset2try=u"utf-8"):
    """
    Need to quote a value e.g. for inclusion in an SQL statement.
    
    raw_val -- might be a string or a datetime but can't be a number.
    
    sql_str_literal_quote -- e.g. ' for SQLite
    
    sql_esc_str_literal_quote -- e.g. '' for SQLite
    
    pystr_use_double_quotes -- Use double quotes for string declaration 
    e.g. myvar = "..." vs myvar = '...'. Best to use the opposite of the 
    literal quotes used by the database engine to minimise escaping.
    """
    debug = False
    try: # try to process as date first
        val = raw_val.isoformat()
        quoted_val = sql_str_literal_quote + val + sql_str_literal_quote
    except AttributeError: # now try as string
        """
        E.g. val is: Don't say "Hello" like that
        
        We need something ready for WHERE myval = 'Don''t say "Hello" like that'
        
        So our string declaration ready for insertion into the SQL will need to 
        be something like:
        
        mystr = u"'Don''t say \"Hello\" like that'"
        
        Tricky because two levels of escaping ;-). 
        
        1) Database engine dependent SQL escaping: The SQL statement itself has 
        its own escaping of internal quotes. So SQLite uses ' for quotes and '' 
        to escape them internally.
        
        2) Python escaping: We need to create a Python string, and do any 
        internal escaping relative to that such that the end result when 
        included in a longer string is correctly escaped SQL. When escaping the 
        final Python string declaration, must escape relative to that e.g. 
        myvar = "..."..." needs to be "...\"...". 
        
        3) variable declaration of quoted value
        The overall process is not super hard when clearly understood as having 
        two steps.
        """
        try: # 1) do sql escaping
            try: # try as if already unicode
                val = raw_val.replace(sql_str_literal_quote, 
                    sql_esc_str_literal_quote)
            except UnicodeDecodeError:
                if debug: print(repr(raw_val))
                val = unicode(raw_val, charset2try).replace(
                    sql_str_literal_quote, sql_esc_str_literal_quote)
        except AttributeError, e:
            raise Exception(u"Inappropriate attempt to quote non-string value."
                u"\nCaused by error: %s" % b.ue(e))
        if pystr_use_double_quotes:
            # 2) do Python escaping
            pystr_esc_val = val.replace(u'"', u'\"')
            # 3) variable declaration of quoted value
            quoted_val = u"%s%s%s" % (sql_str_literal_quote, pystr_esc_val,
                sql_str_literal_quote)
        else:
            pystr_esc_val = val.replace(u"'", u"\'")
            quoted_val = u'%s%s%s' % (sql_str_literal_quote, pystr_esc_val,
                sql_str_literal_quote)
    return quoted_val

def get_p(p, dp):
    if p < 0.001:
        p_str = u"< 0.001"
    else:
        p_format = u"%%.%sf" % dp
        p_str = p_format % round(p, dp)
    return p_str

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

def sort_value_lbls(sort_order, vals_etc_lst, idx_measure, idx_lbl):
    """
    In-place sort value labels list according to sort option selected.
    http://www.python.org/dev/peps/pep-0265/
    """
    if sort_order == mg.SORT_INCREASING_KEY:
        vals_etc_lst.sort(key=itemgetter(idx_measure))
    elif sort_order == mg.SORT_DECREASING_KEY:
        vals_etc_lst.sort(key=itemgetter(idx_measure), reverse=True)
    elif sort_order == mg.SORT_LBL_KEY:
        vals_etc_lst.sort(key=itemgetter(idx_lbl))

def get_sorted_vals(sort_order, vals, lbls):
    """
    Get sorted values according to values in supplied list or their labels 
    according to sort option selected.
    
    http://www.python.org/dev/peps/pep-0265/
    """
    if sort_order == mg.SORT_INCREASING_KEY:
        sorted_vals = sorted(vals)
    elif sort_order == mg.SORT_DECREASING_KEY:
        sorted_vals = sorted(vals)
        sorted_vals.sort(reverse=True)
    elif sort_order == mg.SORT_LBL_KEY:
        val_lbls = [(x, lbls.get(x, unicode(x))) for x in vals]
        val_lbls.sort(key=itemgetter(1))
        sorted_vals = [x[0] for x in val_lbls]
    else:
        sorted_vals = vals
    return sorted_vals

def extract_dojo_style(css_fil):
    try:
        f = codecs.open(css_fil, "r", "utf-8")
    except IOError, e:
        raise my_exceptions.MissingCss(css_fil)
    css = f.read()
    f.close()
    try:
        css_dojo_start_idx = css.index(mg.DOJO_STYLE_START)
        css_dojo_end_idx = css.index(mg.DOJO_STYLE_END)
    except ValueError, e:
        raise my_exceptions.MalformedCssDojo(css)
    text = css[css_dojo_start_idx + len(mg.DOJO_STYLE_START): css_dojo_end_idx]
    css_dojo = b.get_exec_ready_text(text)
    css_dojo_dic = {}
    try:
        exec css_dojo in css_dojo_dic
    except SyntaxError, e:
        wx.MessageBox(_(u"Syntax error in dojo settings in css file"
            u" \"%(css_fil)s\"."
            u"\n\nDetails: %(css_dojo)s %(err)s") % {"css_fil": css_fil,
            u"css_dojo": css_dojo, u"err": b.ue(e)})
        raise
    except Exception, e:
        wx.MessageBox(_(u"Error processing css dojo file \"%(css_fil)s\"."
            u"\n\nDetails: %(err)s") % {u"css_fil": css_fil, u"err": b.ue(e)})
        raise
    return (css_dojo_dic[u"outer_bg"], 
        css_dojo_dic[u"inner_bg"], # grid_bg
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
    200, 500, 1000 or 0.002, 0.005, 0.01) and not too many or too few bins.
    
    Start with a bin width which splits the data into the optimal number of 
    bins. Normalise it, adjust upwards to nice size, and denormalise. Check 
    number of bins resulting.
    
    OK? If room to double number of bins, halve size of normalised bin width, 
    and try to adjust upwards to a nice size. This time, however, there is the 
    option of 2 as an interval size (so we have 2, 5, or 10. Denormalise and 
    recalculate the number of bins.
    
    Now reset lower and upper limits if appropriate. Make lower limit a multiple 
    of the bin_width and make upper limit n_bins*bin_width higher.
    
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
            "to %s giving you %s bins") % (min_val, max_val, better_bin_width, 
            lower_limit, upper_limit, n_bins))
    return n_bins, lower_limit, upper_limit

def version_a_is_newer(version_a, version_b):
    """
    Must be able to process both version details or error raised.
    """
    try:
        version_b_parts = version_b.split(u".")
        if len(version_b_parts) != 3: 
            raise Exception(u"Faulty Version B details")
        version_b_parts = [int(x) for x in version_b_parts]
    except Exception:
        raise Exception(u"Version B parts faulty")
    try:
        version_a_parts = version_a.split(u".")
        if len(version_a_parts) != 3:
            raise Exception(u"Faulty Version A details")
        version_a_parts = [int(x) for x in version_a_parts]
    except Exception:
        raise Exception(u"Version A parts faulty")
    if version_a_parts[0] > version_b_parts[0]:
        is_newer = True
    elif (version_a_parts[0] == version_b_parts[0]
            and version_a_parts[1] > version_b_parts[1]):
        is_newer = True
    elif (version_a_parts[0] == version_b_parts[0]
            and version_a_parts[1] == version_b_parts[1]
            and version_a_parts[2] > version_b_parts[2]):
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
    """
    comma_dec_sep_ok -- Some countries use commas as decimal separators.
    """
    if is_numeric(val, comma_dec_sep_ok): # anything SQLite can add 
            # _as a number_ into a numeric field
        val_type = mg.VAL_NUMERIC
    elif is_pytime(val): # COM on Windows
        val_type = mg.VAL_DATE
    else:
        usable_datetime = is_usable_datetime_str(val)
        if usable_datetime:
            val_type = mg.VAL_DATE
        elif val == "": # Note - some strings can't be coerced into u"" comparison
            val_type = mg.VAL_EMPTY_STRING
        else:
            val_type = mg.VAL_STRING
    return val_type    

def get_overall_fldtype(type_set):
    """
    type_set may contain empty_str as well as actual types.  Useful to remove
    empty str and see what is left.
    
    STRING is the fallback.
    """
    debug = False
    main_type_set = type_set.copy()
    main_type_set.discard(mg.VAL_EMPTY_STRING)
    if main_type_set == set([mg.VAL_NUMERIC]):
        fldtype = mg.FLDTYPE_NUMERIC_KEY
    elif main_type_set == set([mg.VAL_DATE]):
        fldtype = mg.FLDTYPE_DATE_KEY
    elif (main_type_set == set([mg.VAL_STRING]) 
            or type_set == set([mg.VAL_EMPTY_STRING])):
        fldtype = mg.FLDTYPE_STRING_KEY
    else:
        if len(main_type_set) > 1:
            if debug: print(main_type_set)
        fldtype = mg.FLDTYPE_STRING_KEY   
    return fldtype

def update_local_display(html_ctrl, str_content, wrap_text=False):
    str_content = u"<p>%s</p>" % str_content if wrap_text else str_content 
    html_ctrl.show_html(str_content, url_load=True) # allow footnotes

def get_min_content_size(szr_lst, vertical=True):
    """
    For a list of sizers return min content size overall. NB excludes padding 
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
    size. Also handles need to "jitter" in Windows.
    
    Doesn't use the standard approach of szr.SetSizeHints(self) and 
    panel.Layout(). Setting size hints will shrink it using Fit().
    
    window -- e.g. the dialog itself or a frame.
    
    szr_lst -- all the szrs in the main szr (can be a grid instead of a szr)
    
    width_init -- starting width. If None use the minimum worked out.
    
    height_init -- starting height. If None use the minimum worked out.
    
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
            u"\nCaused by error: %s" % b.ue(e))
    return new_str

def get_invalid_var_dets_msg(fil_var_dets):
    debug = False
    try:
        f = codecs.open(fil_var_dets, "U", encoding="utf-8")
        var_dets_txt = b.get_exec_ready_text(text=f.read())
        f.close()
        var_dets = b.clean_boms(var_dets_txt)
        var_dets_dic = {}
        exec var_dets in var_dets_dic
        if debug: wx.MessageBox(u"%s got a clean bill of health from "
            u"get_invalid_var_dets_msg()!" % fil_var_dets)
        return None
    except Exception, e:
        return b.ue(e)

def get_var_dets(fil_var_dets):
    """
    Get variable details from fil_var_dets file.
    
    Returns var_labels, var_notes, var_types, val_dics.
    
    If any errors, return empty dicts and let user continue. Perhaps a corrupted 
    vdts file. Not a reason to bring the whole show down. At least make it easy 
    for them to fix the variable details/change the project settings etc. 
    """
    empty_var_dets = ({},{},{},{})
    try:
        f = codecs.open(fil_var_dets, "U", encoding="utf-8")
    except IOError:
        return empty_var_dets
    var_dets_txt = b.get_exec_ready_text(text=f.read())
    f.close()
    var_dets = b.clean_boms(var_dets_txt)
    var_dets_dic = {}
    results = empty_var_dets # init
    try: # http://docs.python.org/reference/simple_stmts.html
        exec var_dets in var_dets_dic
        try: # puts out results in form which should work irrespective of surrounding encoding of script. E.g. labels={u'1': u'R\xe9parateurs de lampe \xe0 p\xe9trole',
            orig_var_types = var_dets_dic["var_types"]
            var_types = {}
            for key, orig_type in orig_var_types.items():
                # if type not in new list, get from old list
                if orig_type in mg.VAR_TYPE_KEYS:
                    new_type = orig_type
                else:
                    new_type = mg.VAR_TYPE_LBL2KEY.get(orig_type, 
                        mg.VAR_TYPE_CAT_KEY)
                var_types[key] = new_type
            results = (var_dets_dic["var_labels"], var_dets_dic["var_notes"],
                var_types, var_dets_dic["val_dics"])
        except Exception, e:
            wx.MessageBox(u"Four variables needed in \"%s\": var_labels, "
                u"var_notes, var_types, and val_dics. "
                u"Please check file. Orig error: %s" % (fil_var_dets, b.ue(e)))
    except SyntaxError, e:
        wx.MessageBox(
            _(u"Syntax error in variable details file \"%(fil_var_dets)s\"."
            u"\n\nDetails: %(err)s") % {u"fil_var_dets": fil_var_dets, 
            u"err": unicode(e)})
    except Exception, e:
        wx.MessageBox(
            _(u"Error processing variable details file \"%(fil_var_dets)s\"."
            u"\n\nDetails: %(err)s") % {u"fil_var_dets": fil_var_dets, 
            u"err": unicode(e)})
    return results

def get_rand_val_of_type(lbl_type_key):
    if lbl_type_key == mg.FLDTYPE_NUMERIC_KEY:
        vals_of_type = mg.NUM_DATA_SEQ
    elif lbl_type_key == mg.FLDTYPE_STRING_KEY:
        vals_of_type = mg.STR_DATA_SEQ
    elif lbl_type_key == mg.FLDTYPE_DATE_KEY:
        vals_of_type = mg.DTM_DATA_SEQ
    else:
        raise Exception(u"Unknown lbl_type_key in get_rand_val_of_type")
    return random.choice(vals_of_type)

def safe_end_cursor():
    "Problems in Windows if no matching beginning cursor."
    try:
        if wx.IsBusy():
            wx.EndBusyCursor()
    except Exception:
        pass # might be called outside of gui e.g. headless importing

def get_n_fldnames(n):
    fldnames = []
    for i in range(n):
        fldname = mg.NEXT_FLDNAME_TEMPLATE % (i+1,)
        fldnames.append(fldname)
    return fldnames

def get_unique_fldnames(existing_fldnames):
    """
    If some field names are blank e.g. empty columns in a csv file, autofill
    with safe names (numbered to be unique). Create numbered versions of 
    duplicates to ensure they are also unique.
    """
    fldnames = []
    prev_fldnames_and_counters = {}
    for i, name in enumerate(existing_fldnames, 1):
        name = name.replace("\n", "_")
        if name == u"":
            newname = mg.NEXT_FLDNAME_TEMPLATE % (i+1,)
        else:
            if existing_fldnames.count(name) > 1:
                if name not in prev_fldnames_and_counters:
                    prev_fldnames_and_counters[name] = 1
                else:
                    prev_fldnames_and_counters[name] += 1
                # make unique using next number
                newname = mg.NEXT_VARIANT_FLDNAME_TEMPLATE % (name, 
                    prev_fldnames_and_counters[name])
            else:
                newname = name
        fldnames.append(newname)
    return fldnames

def get_next_fldname(existing_fldnames):
    """
    Get next available variable name where names follow a template e.g. var001,
    var002 etc.If a gap, starts after last one. Gaps are not filled.
    """
    nums_used = []
    for fldname in existing_fldnames:
        if not fldname.startswith(mg.FLDNAME_START):
            continue
        try:
            num_used = int(fldname[-len(mg.FLDNAME_START):])
        except ValueError:
            continue
        nums_used.append(num_used)
    free_num = max(nums_used) + 1 if nums_used else 1
    next_fldname = mg.NEXT_FLDNAME_TEMPLATE % free_num
    return next_fldname

def get_lbls_in_lines(orig_txt, max_width, dojo=False, rotate=False):
    """
    Returns quoted text. Will not be further quoted.
    
    Will be "%s" % wrapped txt not "\"%s\"" % wrapped_txt
    
    actual_lbl_width -- may be broken into lines if not rotated. If rotated, we
    need sum of each line (no line breaks possible at present).
    """
    debug = False
    lines = []
    try:
        words = orig_txt.split()
    except Exception:
        raise Exception("Tried to split a non-text label. "
            "Is the script not supplying text labels?")
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
    n_lines = len(lines)
    if dojo:
        if n_lines == 1:
            raw_lbl = lines[0].strip()
            wrapped_txt = u"\"" + raw_lbl + u"\""
            actual_lbl_width = len(raw_lbl)
        else:
            if rotate: # displays <br> for some reason so can't use it
                # no current way identified for line breaks when rotated
                # see - http://grokbase.com/t/dojo/dojo-interest/09cat4bkvg/...
                #...dojox-charting-line-break-in-axis-labels-ie
                wrapped_txt = (u"\"" 
                    + u"\" + \" \" + \"".join(x.strip() for x in lines) + u"\"")
                actual_lbl_width = sum(len(x)+1 for x in lines) - 1
            else:
                wrapped_txt = (u"\""
                    + u"\" + labelLineBreak + \"".join(lines) + u"\"")
                actual_lbl_width = max_width # they are centred in max_width
    else:
        if n_lines == 1:
            raw_lbl = lines[0].strip()
            wrapped_txt = raw_lbl
            actual_lbl_width = len(raw_lbl)
        else:
            wrapped_txt = u"\n".join(lines)
            actual_lbl_width = max_width # they are centred in max_width
    if debug: print(wrapped_txt)
    return wrapped_txt, actual_lbl_width, n_lines

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

def get_blank_btn_bmp(xpm=u"blankbutton.xpm"):
    blank_btn_path = os.path.join(mg.SCRIPT_PATH, u"images", xpm)
    if not os.path.exists(blank_btn_path):
        raise Exception(u"Problem finding background button image.  "
            u"Missing path: %s" % blank_btn_path)
    try:
        blank_btn_bmp = wx.Image(blank_btn_path, 
            wx.BITMAP_TYPE_XPM).ConvertToBitmap()
    except Exception:
        raise Exception(u"Problem creating background button image from %s"
            % blank_btn_path)
    return blank_btn_bmp

def get_bmp(src_img_path, bmp_type=wx.BITMAP_TYPE_GIF, reverse=False):
    """
    Makes image with path details, mirrors if required, then converts to a 
    bitmap and returns it.
    """
    img = wx.Image(src_img_path, bmp_type)
    if reverse:
        img = img.Mirror()
    bmp = img.ConvertToBitmap()
    return bmp

def reverse_bmp(bmp):
    img = wx.ImageFromBitmap(bmp).Mirror()
    bmp = img.ConvertToBitmap()
    return bmp

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
        except AttributeError:
            pass # Only needed to succeed if a string. Presumably wasn't so OK.
        try:
            unused = float(val)
        except (ValueError, TypeError):
            return False
        else:
            return True

def is_basic_num(val):
    """
    Is a value of a basic numeric type - i.e. integer, long, float? NB complex 
    or Decimal values are not considered basic numbers.
    
    NB a string containing a numeric value is not a number type even though it
    will pass is_numeric().
    """
    numtyped = type(val) in [int, long, float]
    return numtyped

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
            raise Exception(u"Unable to convert value to Decimal.  "
                + u"Value was \"%s\"" % f)
    try:
        n, d = f.as_integer_ratio()
    except Exception:
        raise Exception(u"Unable to turn value \"%s\" into integer " % f
            + u"ratio for unknown reason.")
    numerator, denominator = decimal.Decimal(n), decimal.Decimal(d)
    ctx = decimal.Context(prec=60)
    result = ctx.divide(numerator, denominator)
    while ctx.flags[decimal.Inexact]:
        ctx.flags[decimal.Inexact] = False
        ctx.prec *= 2
        result = ctx.divide(numerator, denominator)
    return result

# uncovered

def get_unicode_repr(item):
    if isinstance(item, unicode):
        return u'u"%s"' % unicode(item).replace('"', '""')
    elif isinstance(item, str):
        return u'"%s"' % unicode(item).replace('"', '""')
    elif item is None:
        return u"None"
    else:
        return u"%s" % unicode(item).replace('"', '""')

def dic2unicode(mydic, indent=1):
    """
    Needed because pprint.pformat() can't cope with strings like 'João Rosário'.
    
    Pity so will have to wait till Python 3 version to handle more elegantly.
    
    Goal is to make files that Python can run.
    
    Note -- recursive so can cope with nested dictionaries.
    """
    try:
        keyvals = sorted(mydic.items())
    except Exception: # not a dict, just a value
        return get_unicode_repr(mydic)
    ustr = u"{"
    rows = []
    for key, val in keyvals:
        keystr = get_unicode_repr(key) + u": "
        rows.append(keystr + dic2unicode(val, indent + len(u"{" + keystr)))
    joiner = u",\n%s" % (indent*u" ",)
    ustr += (joiner.join(rows))
    ustr += u"}"
    return ustr


if mg.PLATFORM == mg.WINDOWS:
    exec u"import pywintypes"

def escape_pre_write(txt):
    "Useful when writing a path to a text file etc"
    return txt.replace("\\", "\\\\").replace('"', '\"').replace("'", "\'")

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
        datetime_str = "%s-%s-%s %s:%s:%s" % (pytime.year, 
          unicode(pytime.month).zfill(2), unicode(pytime.day).zfill(2),
          unicode(pytime.hour).zfill(2),  unicode(pytime.minute).zfill(2),
          unicode(pytime.second).zfill(2))
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
        format. NB must be valid format for strftime.
    TODO - make safe for weird encoding issues.  See get_unicode_datestamp().
    """
    year = int(mysql_date[:4])
    month = int(mysql_date[5:7])
    day = int(mysql_date[-2:])
    mydate = (year, month, day, 0, 0, 0, 0, 0, 0)
    return time.strftime(output_format, mydate)

def is_date_part(datetime_str):
    """
    Assumes date will have - or / or . or , or space and time will not.
    If a mishmash will fail bad_date later.
    """
    return (u"-" in datetime_str
        or u"/" in datetime_str 
        or u"." in datetime_str 
        or u"," in datetime_str
        or u" " in datetime_str)

def is_time_part(datetime_str):
    """
    Assumes time will have : (or am/pm) and date will not.
    If a mishmash will fail bad_time later.
    """
    return (":" in datetime_str or "am" in datetime_str.lower()
        or "pm" in datetime_str.lower())

def is_year(datetime_str):
    try:
        year = int(datetime_str)
        dt_is_year = (1 <= year < 10000) 
    except Exception:
        dt_is_year = False
    return dt_is_year

def get_datetime_parts(datetime_str):
    """
    Return potential date and time parts separately if possible.
    Split in the ways that ensure any legitimate datetime strings are split 
    properly.
    
    E.g. 2009 (or 4pm) returned as a list of 1 item []
    E.g. 2011-04-14T23:33:05 returned as [u"2011-04-14", u"23:33:052"]
     (Google docs spreadsheets use 2011-04-14T23:33:05).
    E.g. 1 Feb, 2009 4pm returned as [u"1 Feb, 2009", u"4pm"]
    E.g. 1 Feb 2009 returned as [u"1 Feb 2009"]
    E.g. 1 Feb 2009 4pm returned as [u"1 Feb 2009", u"4pm"]
    E.g. 21/12/2009 4pm returned as [u"21/12/2009", u"4pm"]

    Not sure which way round they are yet or no need to guarantee that the parts 
    are even valid as either dates or times.

    Copes with spaces in times by removing them e.g. 4 pm -> 4pm

    Returns parts_lst.
    """
    datetime_str = datetime_str.replace(u" pm", u"pm")
    datetime_str = datetime_str.replace(u" am", u"am")
    datetime_str = datetime_str.replace(u" PM", u"PM")
    datetime_str = datetime_str.replace(u" AM", u"AM")
    if datetime_str.count(u"T") == 1:
        parts_lst = datetime_str.split(u"T") # e.g. [u"2011-04-14", u"23:33:052"]
    elif u" " in datetime_str and datetime_str.strip() != u"": # split by last one unless ... last one fails time test
        # So we handle 1 Feb 2009 and 1 Feb 2009 4pm and 2011/03/23 4pm correctly
        # and 4pm 2011/03/23.
        # Assumed no spaces in times (as cleaned up to this point e.g. 4 pm -> 4pm).
        # So if a valid time, will either be first or last item or not at all. 
        last_bit_passes_time_test = is_time_part(datetime_str.split()[-1])
        first_bit_passes_time_test = is_time_part(datetime_str.split()[0])
        if not first_bit_passes_time_test and not last_bit_passes_time_test: # this is our best shot - still might fail
            parts_lst = [datetime_str]
        else: # Has to be split to potentially be valid. Split by last space 
            # (or first space if potentially starts with time).
            # Safe because we have removed spaces within times.
            bits = datetime_str.split(u" ") # e.g. [u"1 Feb 2009", u"4pm"]
            if first_bit_passes_time_test:
                first = bits[0]
                last = u" ".join([x for x in bits[1:]]) # at least one bit
            else:
                first = u" ".join([x for x in bits[:-1]]) # at least one bit
                last = bits[-1]
            parts_lst = [first, last]
    else:
        parts_lst = [datetime_str,]
    return parts_lst

def datetime_split(datetime_str):
    """
    Split date and time (if both).
    
    Return date part, time part, order (True unless order time then date).
    
    Return None for any missing components.
    
    boldate_then_time -- only False if time then date with both present.
    """
    parts_lst = get_datetime_parts(datetime_str)
    if len(parts_lst) == 1:
        if is_year(datetime_str):
            return (datetime_str, None, True)
        else: # only one part
            boldate_then_time = True
            if is_date_part(datetime_str):
                return (datetime_str, None, boldate_then_time)
            elif is_time_part(datetime_str):
                return (None, datetime_str, boldate_then_time)
            else:
                return (None, None, boldate_then_time)
    elif len(parts_lst) == 2:
        boldate_then_time = True
        if (is_date_part(parts_lst[0]) and is_time_part(parts_lst[1])):
            return (parts_lst[0], parts_lst[1], True)
        elif (is_date_part(parts_lst[1]) and is_time_part(parts_lst[0])):
            boldate_then_time = False
            return (parts_lst[1], parts_lst[0], boldate_then_time)
        else:
            return (None, None, boldate_then_time)
    else:
        return (None, None, True)

def get_dets_of_usable_datetime_str(raw_datetime_str, ok_date_formats, 
        ok_time_formats):
    """
    Returns (date_part, date_format, time_part, time_format, boldate_then_time) 
    if a usable datetime. NB usable doesn't mean valid as such.  E.g. we may 
    need to add a date to the time to make it valid.
    
    Returns None if not usable.
    
    These parts can be used to make a valid time object ready for conversion 
    into a standard string for data entry.
    """
    debug = False
    if not is_string(raw_datetime_str):
        if debug: print("%s is not a valid datetime string" % raw_datetime_str)
        return None
    if raw_datetime_str.strip() == u"":
        if debug: print("Spaces or empty text are not valid datetime strings")
        return None
    try:
        unicode(raw_datetime_str)
    except Exception:
        return None # can't do anything further with something that can't be converted to unicode
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
                unused = time.strptime(date_part, ok_date_format)
                date_format = ok_date_format
                bad_date = False
                break
            except Exception:
                continue
        if bad_date:
            return None
    time_format = None
    if time_part:
        bad_time = True
        for ok_time_format in ok_time_formats:
            try:
                unused = time.strptime(time_part, ok_time_format)
                time_format = ok_time_format
                bad_time = False
                break
            except Exception:
                continue
        if bad_time:
            return None
    # have at least one part and no bad parts
    return (date_part, date_format, time_part, time_format, boldate_then_time)

#print(get_dets_of_usable_datetime_str("4 am Feb 1 2011", mg.OK_DATE_FORMATS, 
#                                      mg.OK_TIME_FORMATS))

def is_usable_datetime_str(raw_datetime_str, ok_date_formats=None, 
                           ok_time_formats=None):
    """
    Is the datetime string usable? Used for checking user-entered datetimes.
    
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
        unused = time.strptime(raw_datetime_str, "%Y-%m-%d %H:%M:%S")
        return True
    except Exception:
        return False

def get_time_obj(raw_datetime_str):
    """
    Takes a string and checks if there is a usable datetime in there (even a
    time without a date is OK).

    If there is, creates a complete time_obj and returns it.
    """
    debug = False
    datetime_dets = get_dets_of_usable_datetime_str(raw_datetime_str, 
        mg.OK_DATE_FORMATS, mg.OK_TIME_FORMATS)
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
                today[2], time_part), "%%Y-%%m-%%d %s" % time_format)
        else:
            raise Exception(u"Supposedly a usable datetime str but no usable "
                u"parts")
        if debug: print(time_obj)
    return time_obj

def get_datetime_from_str(raw_datetime_str):
    """
    Takes a string and checks if there is a usable datetime in there (even a
    time without a date is OK).

    If there is, returns a standard datetime object.
    """
    time_obj = get_time_obj(raw_datetime_str)
    dt = datetime.datetime.fromtimestamp(time.mktime(time_obj))
    return dt
    
def get_std_datetime_str(raw_datetime_str):
    """
    Takes a string and checks if there is a usable datetime in there (even a
    time without a date is OK).

    If there is, returns a standard datetime string.
    """
    time_obj = get_time_obj(raw_datetime_str)
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
    return item_labels.get(item_val, item_val_u.title()) #.replace(u"\n", u" ") # leave as is

def get_choice_item(item_labels, item_val):
    """
    e.g. "Age Group (agegrp)"
    """
    item_label = get_item_label(item_labels, item_val)
    return u"%s (%s)" % (item_label, any2unicode(item_val)) #.replace(u"\n", u" "))

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

# report tables
def get_col_dets(coltree, colroot, var_labels):
    """
    Get names and labels of columns actually selected in GUI column tree plus 
    any sort order. Returns col_names, col_labels, col_sorting.
    """
    descendants = get_tree_ctrl_descendants(tree=coltree, parent=colroot)
    col_names = []
    col_sorting = []
    for descendant in descendants: # NB GUI tree items, not my Dim Node obj
        item_conf = coltree.GetItemPyData(descendant)
        col_names.append(item_conf.var_name)
        col_sorting.append(item_conf.sort_order)
    col_labels = [var_labels.get(x, x.title()) for x in col_names]
    return col_names, col_labels, col_sorting


class ItemConfig(object):
    """
    Item config storage and retrieval.
    
    Has: var_name, measures, has_tot, sort order, bolnumeric
    
    bolnumeric is only used for verbose summary reporting.
    
    Note - won't have a var name if it is the column config item.
    """
    
    def __init__(self, sort_order, var_name=None, measures_lst=None, 
            has_tot=False, bolnumeric=False):
        self.var_name = var_name
        if measures_lst:
            self.measures_lst = measures_lst
        else:
            self.measures_lst = []
        self.has_tot = has_tot
        self.sort_order = sort_order
        self.bolnumeric = bolnumeric
    
    def get_summary(self, verbose=False):
        """
        String summary of data (apart from variable name).
        """
        str_parts = []
        total_part = _("Has TOTAL") if self.has_tot else None
        if total_part:
            str_parts.append(total_part)
        # ordinary sorting by freq (may include rows and cols)
        order2lbl_dic = {mg.SORT_NONE_KEY: u"Not Sorted",
            mg.SORT_VALUE_KEY: u"Sort by Value", 
            mg.SORT_LBL_KEY: _("Sort by Label"),
            mg.SORT_INCREASING_KEY: _("Sort by Freq (Asc)"),
            mg.SORT_DECREASING_KEY: _("Sort by Freq (Desc)")}
        sort_order_part = order2lbl_dic.get(self.sort_order)        
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
    item, unused = tree.GetFirstChild(parent) # item is an id
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