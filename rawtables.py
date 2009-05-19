import os
import datetime

import util
import tabreports
import getdata

DEF_CSS = r"c:\projects\css\SOFA_Default_Style.css"


class RawTable(object):
    """
    Simple table which basically displays contents of source SQL.
    Can add totals row.
    Can have the first column formatted as labels
    """
    def __init__(self, titles, dbe, col_names, col_labels, flds, 
                 var_labels, val_dics, datasource, cur, subtitles=None, 
                 add_total_row=False, first_col_as_label=False):
        """
        Set up table details required to make output.
        dbe - only here so can use the same interface for all table types
        """
        self.titles = titles
        if subtitles:
            self.subtitles = subtitles
        else:
            self.subtitles = []
        self.col_names = col_names
        self.col_labels = col_labels
        self.flds = flds
        self.var_labels = var_labels
        self.val_dics = val_dics
        self.datasource = datasource
        self.cur = cur
        self.add_total_row = add_total_row
        self.first_col_as_label = first_col_as_label

    def hasColMeasures(self):
        return False

    def getHdrDets(self, col_labels):
        """
        Set up titles, subtitles, and col labels into table header.
        """
        # titles and subtitles
        titles_html = "\n<p class='tbltitle'>"
        for title in self.titles:
            titles_html += "%s<br>" % title
        titles_html += "</p>"
        if self.subtitles != [""]:
            subtitles_html = "\n<p class='tblsubtitle'>"
            for subtitle in self.subtitles:
                subtitles_html += "%s<br>" % subtitle
            subtitles_html += "</p>"
        else:
            subtitles_html = ""
        title_dets_html = titles_html + subtitles_html
        hdr_html = "\n<thead>\n<tr><th class='tbltitlecell' colspan='%s'>" % \
            len(col_labels) + \
            "%s</th></tr>" % title_dets_html
        # col labels
        hdr_html += "\n<tr>"
        for col_label in col_labels:
            hdr_html += "<th class='firstcolvar'>%s</th>" % col_label
        hdr_html += "</tr>\n</thead>"
        return hdr_html

    def getHTML(self, page_break_after=False):
        """
        Get HTML for table.
        SELECT statement lists values in same order
            as col names.
        When adding totals, will only do it if all values are numeric (Or None).
        """
        html = ""
        html += "<table cellspacing='0'>\n" # IE6 doesn't support CSS borderspacing
        hdr_html = self.getHdrDets(self.col_labels)
        body_html = "\n\n<tbody>"
        row_tots = [0 for x in self.col_names]
        if self.first_col_as_label:
            del row_tots[0] # ignore label col
        SQL_get_data = "SELECT %s FROM %s" % (", ".join(self.col_names), 
                                              self.datasource)
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
            col_class_lsts[0] = [tabreports.CSS_LBL]
        for i, col_name in enumerate(self.col_names):
            if self.flds[col_name][getdata.FLD_BOLNUMERIC] \
                    and not col_val_dics[i]:
                col_class_lsts[i].append(tabreports.CSS_ALIGN_RIGHT)
        if self.add_total_row:
            row_tots = [0 for x in self.col_names] # initialise
        for row in rows:
            row_tds = []
            for i in range(cols_n):
                # process row data to display
                # cell contents
                if col_val_dics[i]: # has a label dict
                    row_val = col_val_dics[i].get(row[i], "-") # label from dic
                else:
                    if row[i] or row[i] in ("", 0):
                        row_val = row[i]
                    elif row[i] == None:
                        row_val = "-"
                # cell format
                col_class_names = "\"" + ", ".join(col_class_lsts[i]) + "\""
                col_classes = "class = %s" % col_class_names if col_class_names else ""
                row_tds.append("<td %s>%s</td>" % (col_classes, row_val))
                # process totals
                if self.add_total_row:
                    # Skip if first col as val and this is first col
                    # Skip if prev was a Null ("-")
                    # Add to running total if a number (and prev was a number)
                    # If not adding, set to blank html cell string
                    if (self.first_col_as_label and i == 0) or \
                        row_val == "-":
                        pass
                    elif util.isNumeric(row_val) and \
                            util.isNumeric(row_tots[i]):
                        row_tots[i] += row_val
                    else:
                        row_tots[i] = "&nbsp;&nbsp;"
            html += "\n<tr>" + "".join(row_tds) + "</td></tr>"
        if self.add_total_row:
            row_tot_vals = [str(x) for x in row_tots]
            if self.first_col_as_label:
                tot_cell = "<td class='%s'>TOTAL</td>" % tabreports.CSS_LBL
                row_tot_vals.pop(0)
            else:
                tot_cell = ""
            # never a displayed total for strings (whether orig data or labels)
            joiner = "</td><td class=\"%s\">" % tabreports.CSS_ALIGN_RIGHT
            body_html += "\n<tr class='total-row'>" + \
                tot_cell + "<td class=\"%s\">"  % tabreports.CSS_ALIGN_RIGHT + \
                joiner.join(row_tot_vals) + "</td></tr>"
        body_html += "\n</tbody>"        
        html += hdr_html
        html += body_html
        html += "\n</table>"
        if page_break_after:
            html += "<br><hr><br><div class='page-break-before'></div>"
        return html   
