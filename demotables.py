from __future__ import print_function

import random

import my_globals
import lib
import dimtables
import output
import rawtables
import wx

num_data_seq = (u"1.0", u"1.5", u"2.0", u"2.5", u"3.0", u"3.5", u"12.0", 
                u"35.0")
str_data_seq = (u"Lorem", u"ipsum", u"dolor", u"sit", u"amet")
dtm_data_seq = (u"1 Feb 2009", u"23 Aug 1994", u"16 Sep 2001", u"7 Nov 1986")


class DemoTable(object):
    """
    All demo tables, whether dim tables or raw tables, derive from this class.
    """
    
    def get_demo_html_if_ok(self, css_idx):
        "Get HTML to display if enough data to display"
        assert 0, "get_demo_html_if_ok must be defined by subclass"

    def get_html_parts(self, css_idx):
        "Returns (hdr_html, body_html)"
        assert 0, "get_html_parts must be defined by subclass"

    def get_demo_html(self, css_idx):
        "Get demo HTML for table"
        debug = False
        # sort titles out first
        if self.txtTitles.GetValue():
            self.titles = [u"%s" % x for x \
                      in self.txtTitles.GetValue().split(u"\n")]
        else:
            self.titles = []
        if self.txtSubtitles.GetValue():
            self.subtitles = [u"%s" % x for x \
                         in self.txtSubtitles.GetValue().split(u"\n")]
        else:
            self.subtitles = []
        if debug: print(self.fil_css)
        try:
            html = output.get_html_hdr(hdr_title=_(u"Report(s)"), 
                                       css_fils=[self.fil_css])
        except Exception, e:
            wx.MessageBox(_("Unable to make report.  Error details: %s" % unicode(e)))
            raise Exception, unicode(e)
        html += u"<table cellspacing='0'>\n" # IE6 - no support CSS borderspacing
        (hdr_html, body_html) = self.get_html_parts(css_idx)
        html += hdr_html
        html += body_html
        html += u"\n</table>"
        html += u"\n</body>\n</html>"
        #print(html)
        return html

class DemoRawTable(rawtables.RawTable, DemoTable):
    """
    Demo display raw table (uses demo data only for illustrative purposes)
    """
    
    def __init__(self, txtTitles, txtSubtitles, colRoot, coltree, 
                 flds, var_labels, val_dics, fil_css, chkTotalsRow, 
                 chkFirstAsLabel):
        self.txtTitles = txtTitles
        self.txtSubtitles = txtSubtitles
        self.colRoot = colRoot
        self.coltree = coltree
        self.flds = flds
        self.var_labels = var_labels
        self.val_dics = val_dics
        self.fil_css=fil_css
        self.chkTotalsRow = chkTotalsRow
        self.chkFirstAsLabel = chkFirstAsLabel
    
    def update_flds(self, flds):
        """
        Needed if table selected changes after the table type has been set to 
            raw.
        """
        self.flds = flds
    
    def get_demo_html_if_ok(self, css_idx):
        "Show demo table if sufficient data to do so"
        has_cols = lib.get_tree_ctrl_children(tree=self.coltree, 
                                              parent=self.colRoot)
        return self.get_demo_html(css_idx) if has_cols else ""
      
    def get_html_parts(self, css_idx):
        """
        Returns (hdr_html, body_html).
        If value labels available, use these rather than random numbers.
        """
        debug = False
        CSS_LBL = my_globals.CSS_SUFFIX_TEMPLATE % \
            (my_globals.CSS_LBL, css_idx)
        CSS_ALIGN_RIGHT = my_globals.CSS_SUFFIX_TEMPLATE % \
            (my_globals.CSS_ALIGN_RIGHT, css_idx)
        CSS_TOTAL_ROW = my_globals.CSS_SUFFIX_TEMPLATE % \
            (my_globals.CSS_TOTAL_ROW, css_idx)   
        col_names, col_labels = lib.get_col_dets(self.coltree, self.colRoot, 
                                                 self.var_labels)
        cols_n = len(col_names)        
        bolhas_totals_row = self.chkTotalsRow.IsChecked()
        bolfirst_col_as_label = self.chkFirstAsLabel.IsChecked()
        hdr_html = self.get_hdr_dets(col_labels, css_idx)
        body_html = u"\n<tbody>"        
        # pre-store val dics for each column where possible
        col_val_dics = []
        for col_name in col_names:
            if self.val_dics.get(col_name):
                col_val_dic = self.val_dics[col_name]
                col_val_dics.append(col_val_dic)
            else:
                col_val_dics.append(None)
        # pre-store css class(es) for each column
        col_class_lsts = [[] for x in col_names]
        if bolfirst_col_as_label:
            col_class_lsts[0] = [CSS_LBL]
        for i, col_name in enumerate(col_names):
            if debug: 
                print("%s" % self.flds[col_name])
                print("%s" % col_val_dics)
            bolnumeric = self.flds[col_name][my_globals.FLD_BOLNUMERIC]
            if bolnumeric and not col_val_dics[i]:
                col_class_lsts[i].append(CSS_ALIGN_RIGHT)
        for i in range(4): # four rows enough for demo purposes
            row_tds = []
            # process cells within row
            for j in range(cols_n):
                # cell contents
                if col_val_dics[j]: # choose a random value label
                    random_key = random.choice(col_val_dics[j].keys())
                    row_val = col_val_dics[j][random_key]
                elif self.flds[col_names[j]][my_globals.FLD_BOLNUMERIC]: # choose a random number
                    row_val = unicode(random.choice(num_data_seq))
                elif self.flds[col_names[j]][my_globals.FLD_BOLDATETIME]: # choose a random date
                    row_val = unicode(random.choice(dtm_data_seq))
                else:
                    row_val = unicode(random.choice(str_data_seq))
                # cell format
                col_class_names = u"\"" + u" ".join(col_class_lsts[j]) + u"\""
                col_classes = u"class = %s" % col_class_names \
                    if col_class_names else ""
                row_tds.append(u"<td %s>%s</td>" % (col_classes, row_val))
            body_html += u"\n<tr>" + u"".join(row_tds) + u"</td></tr>"
        if bolhas_totals_row:
            if bolfirst_col_as_label:
                tot_cell = u"<td class='%s'>" % CSS_LBL + _("TOTAL") + u"</td>"
                start_idx = 1
            else:
                tot_cell = u""
                start_idx = 0
            # get demo data
            demo_row_data_lst = []
            for i in range(start_idx, cols_n):
                # if has value dic OR not numeric (e.g. date or string), 
                # show empty cell as total
                if col_val_dics[i] or \
                    not self.flds[col_names[i]][my_globals.FLD_BOLNUMERIC]: 
                    demo_row_data_lst.append(u"&nbsp;&nbsp;")
                else:
                    data = unicode(random.choice(num_data_seq))
                    demo_row_data_lst.append(data)
            # never a displayed total for strings (whether orig data or labels)
            joiner = u"</td><td class=\"%s\">" % CSS_ALIGN_RIGHT
            body_html += u"\n<tr class='%s'>" % CSS_TOTAL_ROW + \
                tot_cell + u"<td class=\"%s\">"  % CSS_ALIGN_RIGHT + \
                joiner.join(demo_row_data_lst) + u"</td></tr>"
        body_html += u"\n</tbody>"
        return (hdr_html, body_html)

    
class DemoDimTable(dimtables.DimTable, DemoTable):
    "A demo table only - no real data inside"
    
    def __init__(self, txtTitles, txtSubtitles, colRoot, rowRoot, rowtree, 
                 coltree, col_no_vars_item, var_labels, val_dics, fil_css):
        self.debug = False
        self.txtTitles = txtTitles
        self.txtSubtitles = txtSubtitles
        self.colRoot = colRoot
        self.rowRoot = rowRoot
        self.rowtree = rowtree
        self.coltree = coltree
        self.col_no_vars_item = col_no_vars_item
        self.var_labels = var_labels
        self.val_dics = val_dics
        self.fil_css=fil_css
        if self.debug: print(self.fil_css)
    
    def get_html_parts(self, css_idx):
        "Returns (hdr_html, body_html)"
        (row_label_rows_lst, tree_row_labels, row_label_cols_n) = \
                                                    self.get_row_dets(css_idx)
        (tree_col_dets, hdr_html) = self.get_hdr_dets(row_label_cols_n, css_idx)
        #print(row_label_rows_lst) #debug
        row_label_rows_lst = self.get_body_html_rows(row_label_rows_lst,
                                                     tree_row_labels, 
                                                     tree_col_dets, css_idx)        
        body_html = u"\n\n<tbody>"
        for row in row_label_rows_lst:
            # flatten row list
            body_html += u"\n" + u"".join(row) + u"</tr>"
        body_html += u"\n</tbody>"
        return (hdr_html, body_html)
    
    def get_row_dets(self, css_idx):
        """
        Return row_label_rows_lst - need combination of row and col filters
            to add the data cells to the table body rows.
        tree_row_labels - not needed here - only with display of 
            actual data
        row_label_cols_n - needed to set up header (need to span the 
            row labels).
        """
        tree_row_labels = dimtables.LabelNodeTree()
        for row_child_item in lib.get_tree_ctrl_children(tree=self.rowtree, 
                                                         parent=self.rowRoot):
            self.add_subtree_to_label_tree(tree_dims_item=row_child_item, 
                              tree_labels_node=tree_row_labels.root_node, 
                              dim=my_globals.ROWDIM)
        return self.process_row_tree(tree_row_labels, css_idx)

    def add_subtree_to_label_tree(self, tree_dims_item, tree_labels_node, dim):
        """
        NB tree_dims_item is a wxPython TreeCtrl item.
        If the tree_dims_item is the special col_no_vars_item, just add the 
            measures underneath the label node.  NB this is the GUI tree item,
            not the Dim Nodes item that gets built off it when the script is
            actually run.
        Otherwise, for each dim item, e.g. gender, add node to the labels tree,
          then the first two values underneath (and total if relevant).
        If the variable node is terminal, then add the measures underneath 
        the new value label nodes.
        If not terminal, add a node for each var underneath 
          (e.g. Ethnicity and Age Gp) under each value node and 
          send through again.
        dim - my_globals.ROWDIM or my_globals.COLDIM
        """
        debug = False
        if dim == my_globals.COLDIM:
            tree = self.coltree
            item_conf = tree.GetItemPyData(tree_dims_item)
        elif dim == my_globals.ROWDIM:
            tree = self.rowtree
            item_conf = tree.GetItemPyData(tree_dims_item)        
        if item_conf is None:
            item_conf = lib.ItemConfig()
        if tree_dims_item == self.col_no_vars_item:
            # add measures only
            if item_conf:
                measures = item_conf.measures_lst
            else:
                measures = [self.default_measure]
            for measure in measures:
                tree_labels_node.add_child(dimtables.LabelNode(label=measure, 
                                                               measure=measure))
        else:
            # add var e.g. gender then values below e.g. Male, Female
            var_name = item_conf.var_name
            if debug: print(var_name)
            var_label = self.var_labels.get(var_name, var_name.title())
            new_var_node = tree_labels_node.add_child(
                                        dimtables.LabelNode(label=var_label))
            # terminal tree_dim_item (got any children)?
            item, cookie = self.coltree.GetFirstChild(tree_dims_item)
            is_terminal = not item #i.e. if there is only the root there
            if dim==my_globals.ROWDIM and self.has_row_measures:
                # add measure label nodes
                if item_conf:
                    measures = item_conf.measures_lst
                else:
                    measures = [self.default_measure]
                for measure in measures:
                    new_var_node.add_child(dimtables.LabelNode(\
                                           label=measure,
                                           measure=measure))
            else: # no row_measures 
                # add values (as labels if available, as placeholders 
                # otherwise) and possibly a total
                labels_dic = self.val_dics.get(var_name, {})
                subitems_lst = [] # build subitems list
                for (i, (key, val_label)) in enumerate(labels_dic.items()):
                    if i > 1:
                        break
                    subitems_lst.append(val_label)
                if item_conf.sort_order == my_globals.SORT_LABEL:
                    subitems_lst.sort()
                i=len(subitems_lst) + 1 # so first filler is Val 2 if first 
                # value already filled
                while len(subitems_lst) < 2:
                    subitems_lst.append(u"Value %s" % i)
                    i=i+1
                if item_conf.has_tot:
                    subitems_lst.append(my_globals.HAS_TOTAL)
                for subitem in subitems_lst:
                    # make val node e.g. Male
                    subitem_node = dimtables.LabelNode(label=subitem)
                    new_var_node.add_child(subitem_node)                
                    if is_terminal and dim==my_globals.COLDIM and \
                        self.has_col_measures:
                        # add measure label nodes
                        measures = item_conf.measures_lst
                        if not measures:
                            measures = [self.default_measure]
                        for measure in measures:
                            subitem_node.add_child(dimtables.LabelNode(\
                                                   label=measure,
                                                   measure=measure))
                    else:
                        # for each child of tree_dims_item e.g. Eth and Age Gp
                        if dim == my_globals.COLDIM:
                            tree = self.coltree
                        elif dim == my_globals.ROWDIM:
                            tree = self.rowtree
                        child_items = lib.get_tree_ctrl_children(tree=tree, 
                                                        parent=tree_dims_item)
                        if debug:
                            print(lib.get_sub_tree_items(tree=tree,
                                                         parent=tree_dims_item))
                        for child_item in child_items:
                            self.add_subtree_to_label_tree(tree_dims_item=\
                                   child_item, tree_labels_node=subitem_node, 
                                   dim=dim)
    
    def add_subtrees_to_col_label_tree(self, tree_col_labels):
        """
        Add subtrees to column label tree.
        If coltree has no children, (not even the col no vars item)
        do not add one hee (unlike Live Tables).  It will be handled
        by the calling class e.g. by adding measures or raising an
        exception.
        """
        col_children = lib.get_tree_ctrl_children(tree=self.coltree, 
                                                  parent=self.colRoot)
        for col_child_item in col_children:
            self.add_subtree_to_label_tree(tree_dims_item=col_child_item, 
                                  tree_labels_node=tree_col_labels.root_node, 
                                  dim=my_globals.COLDIM)
        return tree_col_labels
    

class GenDemoTable(DemoDimTable):
    "A general demo table"
    
    has_row_measures = False
    has_row_vals = True
    has_col_measures = True
    default_measure = lib.get_default_measure(my_globals.COL_MEASURES)
    
    def __init__(self, txtTitles, txtSubtitles, colRoot, rowRoot, rowtree, 
                 coltree, col_no_vars_item, var_labels, val_dics, fil_css):
        DemoDimTable.__init__(self, txtTitles, txtSubtitles, colRoot, rowRoot, 
                           rowtree, coltree, col_no_vars_item, var_labels, 
                           val_dics, fil_css)
        
    def get_demo_html_if_ok(self, css_idx):
        "Show demo table if sufficient data to do so"
        has_rows = lib.get_tree_ctrl_children(tree=self.rowtree, 
                                              parent=self.rowRoot)
        has_cols = lib.get_tree_ctrl_children(tree=self.coltree, 
                                              parent=self.colRoot)
        if has_rows and has_cols:
            return self.get_demo_html(css_idx)
        else:
            return ""
    
    def get_hdr_dets(self, row_label_cols_n, css_idx):
        """
        Return tree_col_labels and the table header HTML.
        For HTML provide everything from <thead> to </thead>.
        """
        tree_col_labels = dimtables.LabelNodeTree()
        tree_col_labels = self.add_subtrees_to_col_label_tree(tree_col_labels)
        if tree_col_labels.get_depth() == 1:
            raise Exception, u"There must always be a column item " + \
                u"even if only the col no vars item"
        return self.process_hdr_tree(tree_col_labels, row_label_cols_n, css_idx)    

    def get_body_html_rows(self, row_label_rows_lst, tree_row_labels,
                           tree_col_labels, css_idx):
        """
        Make table body rows based on contents of row_label_rows_lst:
        e.g. [["<tr>", "<td class='firstrowvar' rowspan='8'>Gender</td>" ...],
        ...]
        It already contains row label data - we need to add the data cells 
        into the appropriate row list within row_label_rows_lst before
        concatenating and appending "</tr>".
        """
        #print(row_label_rows_lst) #debug
        col_term_nodes = tree_col_labels.get_terminal_nodes()
        row_term_nodes = tree_row_labels.get_terminal_nodes()
        col_filters_lst = [x.filts for x in col_term_nodes]
        col_filt_flds_lst = [x.filt_flds for x in col_term_nodes]
        col_tots_lst = [x.is_coltot for x in col_term_nodes]
        col_measures_lst = [x.measure for x in col_term_nodes]
        row_filters_lst = [x.filts for x in row_term_nodes]
        row_filt_flds_lst = [x.filt_flds for x in row_term_nodes]
        data_cells_n = len(row_term_nodes) * len(col_term_nodes)
        #print("%s data cells in table" % data_cells_n)
        row_label_rows_lst = self.get_row_labels_row_lst(row_filters_lst, 
            row_filt_flds_lst, col_measures_lst, col_filters_lst, 
            col_tots_lst, col_filt_flds_lst, row_label_rows_lst, 
            data_cells_n, col_term_nodes, css_idx)
        return row_label_rows_lst
                
    def get_row_labels_row_lst(self, row_filters_lst, row_filt_flds_lst, 
                               col_measures_lst, col_filters_lst, 
                               col_tots_lst, col_filt_flds_lst, 
                               row_label_rows_lst, data_cells_n,
                               col_term_nodes, css_idx):
        """
        Get list of row data.  Each row in the list is represented
        by a row of strings to concatenate, one per data point.
        """
        CSS_FIRST_DATACELL = my_globals.CSS_SUFFIX_TEMPLATE % \
            (my_globals.CSS_FIRST_DATACELL, css_idx)
        CSS_DATACELL = my_globals.CSS_SUFFIX_TEMPLATE % \
            (my_globals.CSS_DATACELL, css_idx)
        i=0
        data_item_presn_lst = []
        for (row_filter, row_filt_flds) in zip(row_filters_lst,
                                               row_filt_flds_lst):
            first = True
            for (colmeasure, col_filter, coltot, col_filt_flds) in \
                        zip(col_measures_lst, col_filters_lst, 
                            col_tots_lst, col_filt_flds_lst):
                if first:
                    cellclass = CSS_FIRST_DATACELL
                    first = False
                else:
                    cellclass = CSS_DATACELL
                #build data row list
                data_val = random.choice(num_data_seq)
                if colmeasure in [my_globals.ROWPCT, my_globals.COLPCT]:
                    val = u"%s%%" % data_val
                else:
                    val = data_val
                data_item_presn_lst.append(u"<td class='%s'>%s</td>" % \
                                           (cellclass, val))
                i=i+1
        i=0
        # put the cell data (inc html) into the right places
        for row in row_label_rows_lst:
            for j in range(len(col_term_nodes)):
                row.append(data_item_presn_lst[i])
                i=i+1
        return row_label_rows_lst
    
    
class SummDemoTable(DemoDimTable):
    "A summary demo table"

    has_row_measures = True
    has_row_vals = False
    has_col_measures = False
    default_measure = lib.get_default_measure(my_globals.ROW_SUMM)
    
    def __init__(self, txtTitles, txtSubtitles, colRoot, rowRoot, rowtree, 
                 coltree, col_no_vars_item, var_labels, val_dics, fil_css):
        DemoDimTable.__init__(self, txtTitles, txtSubtitles, colRoot, rowRoot, 
                           rowtree, coltree, col_no_vars_item, var_labels, 
                           val_dics, fil_css)

    def get_demo_html_if_ok(self, css_idx):
        "Show demo table if sufficient data to do so"
        has_rows = lib.get_tree_ctrl_children(tree=self.rowtree, 
                                              parent=self.rowRoot)
        return self.get_demo_html(css_idx) if has_rows else ""
            
    def get_hdr_dets(self, row_label_cols_n, css_idx):
        """
        Return tree_col_labels and the table header HTML.
        For HTML provide everything from <thead> to </thead>.
        If no column variables, make a special column node.
        """
        tree_col_labels = dimtables.LabelNodeTree()
        tree_col_labels = self.add_subtrees_to_col_label_tree(tree_col_labels)
        if tree_col_labels.get_depth() == 1:
            tree_col_labels.add_child(dimtables.LabelNode(label=u"Measures"))
        return self.process_hdr_tree(tree_col_labels, row_label_cols_n, css_idx)

    def get_body_html_rows(self, row_label_rows_lst, tree_row_labels,
                           tree_col_labels, css_idx):
        """
        Make table body rows based on contents of row_label_rows_lst:
        e.g. [["<tr>", "<td class='firstrowvar' rowspan='8'>Gender</td>" ...],
        ...]
        It already contains row label data - we need to add the data cells 
        into the appropriate row list within row_label_rows_lst before
        concatenating and appending "</tr>".
        """
        col_term_nodes = tree_col_labels.get_terminal_nodes()
        row_term_nodes = tree_row_labels.get_terminal_nodes()
        row_measures_lst = [x.measure for x in row_term_nodes]
        col_filters_lst = [x.filts for x in col_term_nodes] #can be [[],[],[], ...]
        row_filt_flds_lst = [x.filt_flds for x in row_term_nodes]
        col_filt_flds_lst = [x.filt_flds for x in col_term_nodes]
        col_tots_lst = [x.is_coltot for x in col_term_nodes]
        data_cells_n = len(row_term_nodes) * len(col_term_nodes)
        #print("%s data cells in table" % data_cells_n)
        row_label_rows_lst = self.get_row_labels_row_lst(row_filt_flds_lst, 
                                row_measures_lst, col_filters_lst, 
                                row_label_rows_lst, col_term_nodes, css_idx)
        return row_label_rows_lst
    
    def get_row_labels_row_lst(self, row_flds_lst,  
                               row_measures_lst, col_filters_lst, 
                               row_label_rows_lst, col_term_nodes, css_idx):
        """
        Get list of row data.  Each row in the list is represented
        by a row of strings to concatenate, one per data point.
        Get data values one at a time (no batches unlike Gen Tables).
        """
        CSS_FIRST_DATACELL = my_globals.CSS_SUFFIX_TEMPLATE % \
            (my_globals.CSS_FIRST_DATACELL, css_idx)
        CSS_DATACELL = my_globals.CSS_SUFFIX_TEMPLATE % \
            (my_globals.CSS_DATACELL, css_idx)
        data_item_lst = []
        for (rowmeasure, row_fld_lst) in zip(row_measures_lst, 
                                             row_flds_lst):
            first = True
            for col_filter_lst in col_filters_lst:
                #styling
                if first:
                    cellclass = CSS_FIRST_DATACELL
                    first = False
                else:
                    cellclass = CSS_DATACELL
                data_val = random.choice(num_data_seq)
                if rowmeasure == my_globals.SUMM_N:
                    val = u"N=%s" % data_val
                else:
                    val = data_val
                data_item_lst.append(u"<td class='%s'>%s</td>" % \
                                     (cellclass, val))
        i=0
        for row in row_label_rows_lst:
            for j in range(len(col_term_nodes)):
                row.append(data_item_lst[i])
                i=i+1
        return row_label_rows_lst