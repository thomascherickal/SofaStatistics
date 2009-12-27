import os
import datetime

import my_globals
import lib
import getdata


class RawTable(object):
    """
    Simple table which basically displays contents of source SQL.
    Can add totals row.
    Can have the first column formatted as labels
    """
    def __init__(self, titles, subtitles, dbe, col_names, col_labels, flds, 
                 var_labels, val_dics, tbl, tbl_filt, cur, 
                 add_total_row=False, first_col_as_label=False):
        """
        Set up table details required to make my_globals.
        dbe - only here so can use the same interface for all table types
        """
        debug = False
        self.titles = titles
        self.subtitles = subtitles
        self.col_names = col_names
        self.col_labels = col_labels
        self.flds = flds
        self.var_labels = var_labels
        self.val_dics = val_dics
        self.tbl = tbl
        self.where_tbl_filt, unused = lib.get_tbl_filts(tbl_filt)
        if debug: 
            print(tbl_filt)
            print(self.where_tbl_filt)
        self.cur = cur
        self.add_total_row = add_total_row
        self.first_col_as_label = first_col_as_label

    def hasColMeasures(self):
        return False

    def getHdrDets(self, col_labels, css_idx):
        """
        Set up titles, subtitles, and col labels into table header.
        """
        CSS_TBL_TITLE = my_globals.CSS_SUFFIX_TEMPLATE % \
            (my_globals.CSS_TBL_TITLE, css_idx)
        CSS_SUBTITLE = my_globals.CSS_SUFFIX_TEMPLATE % \
            (my_globals.CSS_SUBTITLE, css_idx)
        CSS_TBL_TITLE_CELL = my_globals.CSS_SUFFIX_TEMPLATE % \
            (my_globals.CSS_TBL_TITLE_CELL, css_idx)
        CSS_FIRST_COL_VAR = my_globals.CSS_SUFFIX_TEMPLATE % \
            (my_globals.CSS_FIRST_COL_VAR, css_idx)
        # titles and subtitles
        titles_html = u"\n<p class='%s'>" % CSS_TBL_TITLE
        for title in self.titles:
            titles_html += u"%s<br>" % title
        titles_html += u"</p>"
        if self.subtitles != [u""]:
            subtitles_html = u"\n<p class='%s'>" % CSS_SUBTITLE
            for subtitle in self.subtitles:
                subtitles_html += u"%s<br>" % subtitle
            subtitles_html += u"</p>"
        else:
            subtitles_html = u""
        title_dets_html = titles_html + subtitles_html
        hdr_html = u"\n<thead>\n<tr><th " + \
            u"class='%s'" % CSS_TBL_TITLE_CELL + \
            u" colspan='%s'>" % len(col_labels) + \
            u"%s</th></tr>" % title_dets_html
        # col labels
        hdr_html += u"\n<tr>"
        for col_label in col_labels:
            hdr_html += u"<th class='%s'>%s</th>" % (CSS_FIRST_COL_VAR, 
                                                     col_label)
        hdr_html += u"</tr>\n</thead>"
        return hdr_html

    def getHTML(self, css_idx, page_break_after=False):
        """
        Get HTML for table.
        SELECT statement lists values in same order
            as col names.
        When adding totals, will only do it if all values are numeric (Or None).
        """
        debug = False
        CSS_LBL = my_globals.CSS_SUFFIX_TEMPLATE % \
            (my_globals.CSS_LBL, css_idx)
        CSS_ALIGN_RIGHT = my_globals.CSS_SUFFIX_TEMPLATE % \
            (my_globals.CSS_ALIGN_RIGHT, css_idx)
        CSS_TOTAL_ROW = my_globals.CSS_SUFFIX_TEMPLATE % \
            (my_globals.CSS_TOTAL_ROW, css_idx)
        CSS_PAGE_BREAK_BEFORE = my_globals.CSS_SUFFIX_TEMPLATE % \
            (my_globals.CSS_PAGE_BREAK_BEFORE, css_idx)
        html = u""
        html += u"\n\n<table cellspacing='0'>\n" # IE6 - no support CSS borderspacing
        hdr_html = self.getHdrDets(self.col_labels, css_idx)
        html += hdr_html
        # build body
        body_html = u"\n\n<tbody>"
        row_tots = [0 for x in self.col_names]
        if self.first_col_as_label:
            del row_tots[0] # ignore label col
        SQL_get_data = u"SELECT %s FROM %s %s" % (u", ".join(self.col_names), 
                                                  self.tbl, self.where_tbl_filt)
        if debug: print(SQL_get_data)
        self.cur.execute(SQL_get_data)
        rows = self.cur.fetchall()
        cols_n = len(self.col_names)
        # pre-store val dics for each column where possible
        col_val_dics = []
        for col_name in self.col_names:
            if self.val_dics.get(col_name):
                col_val_dic = self.val_dics[col_name]
                col_val_dics.append(col_val_dic)
            else:
                col_val_dics.append(None)
        # pre-store css class(es) for each column
        col_class_lsts = [[] for x in self.col_names]
        if self.first_col_as_label:
            col_class_lsts[0] = [CSS_LBL]
        for i, col_name in enumerate(self.col_names):
            if self.flds[col_name][my_globals.FLD_BOLNUMERIC] \
                    and not col_val_dics[i]:
                col_class_lsts[i].append(CSS_ALIGN_RIGHT)
        if self.add_total_row:
            row_tots = [0 for x in self.col_names] # initialise
            row_tots_used = set() # some will never have anything added to them
        for row in rows:
            row_tds = []
            for i in range(cols_n):
                # process row data to display
                # cell contents
                if col_val_dics[i]: # has a label dict
                    row_val = col_val_dics[i].get(row[i], u"-") # label from dic
                else:
                    if row[i] or row[i] in (u"", 0):
                        row_val = row[i]
                    elif row[i] is None:
                        row_val = u"-"
                # cell format
                col_class_names = u"\"" + u" ".join(col_class_lsts[i]) + u"\""
                col_classes = u"class = %s" % col_class_names \
                    if col_class_names else u""
                row_tds.append(u"<td %s>%s</td>" % (col_classes, row_val))
                # process totals
                if self.add_total_row:
                    # Skip if first col as val and this is first col
                    # Skip if prev was a Null ("-")
                    # Add to running total if a number
                    if (self.first_col_as_label and i == 0) or \
                        row_val == u"-":
                        pass
                    elif lib.is_basic_num(row_val) and \
                            lib.is_basic_num(row_tots[i]):
                        row_tots[i] += row_val
                        row_tots_used.add(i)
            body_html += u"\n<tr>" + u"".join(row_tds) + u"</td></tr>"
        if self.add_total_row:
            row_tot_vals = []
            for i in range(cols_n):
                val = unicode(row_tots[i]) if i in row_tots_used \
                    else u"&nbsp;&nbsp;"
                row_tot_vals.append(val)
            if self.first_col_as_label:
                tot_cell = u"<td class='%s'>" % CSS_LBL + _("TOTAL") + u"</td>"
                row_tot_vals.pop(0)
            else:
                tot_cell = u""
            # never a displayed total for strings (whether orig data or labels)
            joiner = u"</td><td class=\"%s\">" % CSS_ALIGN_RIGHT
            body_html += u"\n<tr class='%s'>" % CSS_TOTAL_ROW + \
                tot_cell + u"<td class=\"%s\">"  % CSS_ALIGN_RIGHT + \
                joiner.join(row_tot_vals) + u"</td></tr>"
        body_html += u"\n</tbody>"
        html += body_html
        html += u"\n</table>"
        if page_break_after:
            html += u"<br><hr><br><div class='%s'></div>" % \
                CSS_PAGE_BREAK_BEFORE
        return html   
