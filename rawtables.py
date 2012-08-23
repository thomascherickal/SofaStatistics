
from collections import namedtuple

import my_globals as mg
import lib
import getdata
import output

"""
Don't use dd - this and any other modules we wish to run as a standalone script 
must have dbe, db etc explicitly fed in. If the script is built by the GUI, the
GUI reads dd values and feeds them into the script.
"""

def get_hdr_dets(titles, subtitles, col_labels, css_idx):
    """
    Set up titles, subtitles, and col labels into table header.
    """
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, 
                                                  css_idx)
    # col labels
    hdr_html = u"\n<tr>"
    for col_label in col_labels:
        hdr_html += u"<th class='%s'>%s</th>" % (CSS_FIRST_COL_VAR, col_label)
    hdr_html += u"</tr>\n</thead>"
    return hdr_html

def get_html(titles, subtitles, dbe, col_labels, col_names, col_sorting, tbl, 
             flds, cur, first_col_as_label, val_dics, add_total_row, 
             where_tbl_filt, css_idx, page_break_after=False, display_n=None):
    """
    Get HTML for table.
    SELECT statement lists values in same order as col names.
    When adding totals, will only do it if all values are numeric (Or None).
    Pulled out of object so can be used by both demo raw table (may need to 
        update database settings (cursor, db etc) after the demo object was 
        initiated e.g. user has changed data source after selecting raw tables)
        AND by live run (which always grabs the data it needs at the moment it
        is called (current by definition) and instantiates and gets html in one
        go.
    """
    debug = True
    verbose = True
    idx_and_data = namedtuple('idx_and_data', 'sort_idx, lbl_cols')  
    CSS_LBL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_LBL, css_idx)
    CSS_ALIGN_RIGHT = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_ALIGN_RIGHT, css_idx)
    CSS_TOTAL_ROW = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_TOTAL_ROW, css_idx)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % \
                                        (mg.CSS_PAGE_BREAK_BEFORE, css_idx)
    html = []
    title_dets_html = output.get_title_dets_html(titles, subtitles, css_idx,
                                                 istable=True)
    html.append(title_dets_html)
    html.append(u"\n\n<table cellspacing='0'>\n") # IE6 - no support CSS borderspacing
    hdr_html = get_hdr_dets(titles, subtitles, col_labels, css_idx)
    html.append(hdr_html)
    # build body
    body_html = [u"\n<tbody>",]
    # Prepare column level config
    # pre-store val dics for each column where possible
    cols_n = len(col_names)
    col_val_dics = []
    for col_name in col_names:
        if val_dics.get(col_name):
            col_val_dic = val_dics[col_name]
            col_val_dics.append(col_val_dic)
        else:
            col_val_dics.append(None)
    # pre-store css class(es) for each column
    col_class_lsts = [[] for x in col_names]
    if first_col_as_label:
        col_class_lsts[0] = [CSS_LBL]
    for i, col_name in enumerate(col_names):
        if flds[col_name][mg.FLD_BOLNUMERIC] and not col_val_dics[i]:
            col_class_lsts[i].append(CSS_ALIGN_RIGHT)
    if add_total_row:
        row_tots = [0 for x in col_names] # init
        row_tots_used = set() # some will never have anything added to them    
    # get data from SQL 
    objqtr = getdata.get_obj_quoter_func(dbe)
    colnames_clause = u", ".join([objqtr(x) for x in col_names])
    """
    Get data from SQL and apply labels. Collect totals along the way as is 
        currently the case.
    Sort by labels if appropriate. Then generate HTML row by row and cell by 
        cell.
    """
    SQL_get_data = u"""SELECT %s 
    FROM %s 
    %s""" % (colnames_clause, getdata.tblname_qtr(dbe, tbl), where_tbl_filt)
    if debug: print(SQL_get_data)
    cur.execute(SQL_get_data) # must be dd.cur
    # get labelled vals and a sorting index (list of labelled values)
    idx_and_data_rows = []
    row_idx = 0
    while True:
        if display_n:
            if row_idx >= display_n:
                break # got all we need
        row = cur.fetchone()
        if row is None:
            break # run out of rows
        row_idx+=1
        sorting_lbls = []
        labelled_cols = []
        for idx_col in range(cols_n):
            # process row data to display cell contents
            raw_val = row[idx_col]
            if col_val_dics[idx_col]: # has a label dict
                row_val = col_val_dics[idx_col].get(row[idx_col], row[idx_col]) # use if possible
            else:
                if row[idx_col] or row[idx_col] in (u"", 0):
                    row_val = row[idx_col]
                elif row[idx_col] is None:
                    row_val = u"-"
            labelled_cols.append(row_val)
            # include row_val in lbl list which the data will be sorted by
            if col_sorting[idx_col] == mg.SORT_LBL:
                sorting_lbls.append(row_val)
            else:
                sorting_lbls.append(raw_val) # no label
            # process totals
            if add_total_row:
                # Skip if first col as val and this is first col
                # Skip if prev was a Null ("-")
                # Add to running total if a number
                if ((first_col_as_label and idx_col == 0) 
                        or row_val == u"-"):
                    pass
                elif (lib.is_basic_num(row_val) 
                      and lib.is_basic_num(row_tots[idx_col])):
                    row_tots[idx_col] += row_val
                    row_tots_used.add(idx_col)
        idx_and_data_rows.append(idx_and_data(sorting_lbls, labelled_cols))
    if add_total_row:
        if debug: print("row_tots: %s" % row_tots)
    # sort labelled data if appropriate
    if debug and verbose:
        print(u"Unsorted\n\n%s" % idx_and_data_rows)
    if mg.SORT_LBL in col_sorting:
        
        idx_and_data_rows.sort(key=lambda s: s.sort_idx)
    if debug and verbose:
        print(u"Sorted\n\n%s" % idx_and_data_rows)
    # generate html
    for idx_and_data_row in idx_and_data_rows:
        labelled_cols = idx_and_data_row.lbl_cols
        row_tds = []
        for i, labelled_col in enumerate(labelled_cols):
            # cell format
            col_class_names = u"\"" + u" ".join(col_class_lsts[i]) + u"\""
            col_classes = (u"class = %s" % col_class_names
                           if col_class_names else u"")
            row_tds.append(u"<td %s>%s</td>" % (col_classes, labelled_col))
 
        body_html.append(u"<tr>" + u"".join(row_tds) + u"</td></tr>")
    if add_total_row:
        row_tot_vals = []
        for i in range(cols_n):
            val = (unicode(row_tots[i]) if i in row_tots_used
                   else u"&nbsp;&nbsp;")
            row_tot_vals.append(val)
        if first_col_as_label:
            tot_cell = u"<td class='%s'>" % CSS_LBL + _("TOTAL") + u"</td>"
            row_tot_vals.pop(0)
        else:
            tot_cell = u""
        # never a displayed total for strings (whether orig data or labels)
        joiner = u"</td><td class=\"%s\">" % CSS_ALIGN_RIGHT
        body_html.append(u"<tr class='%s'>" % CSS_TOTAL_ROW +
                        tot_cell + u"<td class=\"%s\">"  % CSS_ALIGN_RIGHT +
                        joiner.join(row_tot_vals) + u"</td></tr>")
    body_html.append(u"</tbody>")
    html.append(u"\n".join(body_html))
    html.append(u"\n</table>")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" %
                    CSS_PAGE_BREAK_BEFORE)
    title = (titles[0] if titles else mg.TAB_TYPE2LBL[mg.DATA_LIST])
    output.append_divider(html, title, indiv_title=u"")
    return u"\n".join(html)


class RawTable(object):
    """
    Simple table which basically displays contents of source SQL.
    Can add totals row.
    Can have the first column formatted as labels
    """
    def __init__(self, titles, subtitles, dbe, col_names, col_labels, 
                 col_sorting, flds, var_labels, val_dics, tbl, tbl_filt, cur, 
                 add_total_row=False, first_col_as_label=False):
        """
        Set up table details required to make mg.
        dbe - needed for quoting entities and values
        Need it in __init__ rather than get_html because that needs to follow 
            same API as demo dim tables.
        """
        debug = False
        self.titles = titles
        self.subtitles = subtitles
        self.dbe = dbe
        self.col_names = col_names
        self.col_labels = col_labels
        self.col_sorting = col_sorting
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

    def has_col_measures(self):
        return False
    
    def get_html(self, css_idx, page_break_after=False, display_n=None):
        """
        Get HTML for table.
        SELECT statement lists values in same order as col names.
        When adding totals, will only do it if all values are numeric (Or None).
        When running actual report, OK to use db settings as at time of 
            instantiation (so can use self without self having to be kept 
            up-to-date). Always up-to-date because only ever instantiated when 
            immediately run.
        """
        return get_html(self.titles, self.subtitles, self.dbe, self.col_labels, 
                        self.col_names, self.col_sorting, self.tbl, self.flds, 
                        self.cur, self.first_col_as_label, self.val_dics,
                        self.add_total_row, self.where_tbl_filt, css_idx, 
                        page_break_after, display_n)
