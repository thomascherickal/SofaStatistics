from __future__ import print_function

import random

import my_globals as mg
import lib
import my_exceptions
import config_dlg
import getdata
import dimtables
import output
import rawtables
import wx

dd = getdata.get_dd()
cc = config_dlg.get_cc()


class DemoTable(object):
    """
    All demo tables, whether dim tables or raw tables, derive from this class.
    """
    
    def get_demo_html_if_ok(self, css_idx):
        "Get HTML to display if enough data to display"
        assert 0, "get_demo_html_if_ok must be defined by subclass"

    def get_html(self, css_idx):
        "Returns html"
        assert 0, "get_html must be defined by subclass"

    def get_demo_html(self, css_idx):
        "Get demo HTML for table"
        debug = False
        # sort titles out first
        if self.txt_titles.GetValue():
            self.titles = [u"%s" % x for x \
                      in self.txt_titles.GetValue().split(u"\n")]
        else:
            self.titles = []
        if self.txt_subtitles.GetValue():
            self.subtitles = [u"%s" % x for x \
                         in self.txt_subtitles.GetValue().split(u"\n")]
        else:
            self.subtitles = []
        if debug: print(cc[mg.CURRENT_CSS_PATH])
        html = []
        try:
            html.append(output.get_html_hdr(hdr_title=_(u"Report(s)"), 
                                    css_fils=[cc[mg.CURRENT_CSS_PATH],], 
                                    default_if_prob=True, grey=True, abs=True))
            html.append(u"<table cellspacing='0'>\n") # IE6 no CSS borderspacing
            main_html = self.get_html(css_idx)
        except my_exceptions.MissingCssException:
            raise my_exceptions.MissingCssException # pass it on
        except my_exceptions.TooFewValsForDisplay:
            raise my_exceptions.TooFewValsForDisplay # pass it on
        except Exception, e:
            wx.MessageBox(_("Unable to make report.  Error details: %s" % 
                            lib.ue(e)))
            raise Exception, unicode(e)
        html.append(main_html)
        html.append(u"\n</table>")
        html.append(u"\n</body>\n</html>")
        demo_html = u"".join(html)
        if debug: print(demo_html)
        return demo_html

class DemoRawTable(rawtables.RawTable, DemoTable):
    """
    Demo display raw table (uses demo data only for illustrative purposes)
    """
    
    def __init__(self, txtTitles, txtSubtitles, colroot, coltree, var_labels, 
                 val_dics, chk_totals_row, chk_first_as_label):
        self.txt_titles = txtTitles
        self.txt_subtitles = txtSubtitles
        self.colroot = colroot
        self.coltree = coltree
        self.var_labels = var_labels
        self.val_dics = val_dics
        self.chk_totals_row = chk_totals_row
        self.chk_first_as_label = chk_first_as_label
        self.dbe = dd.dbe
        self.cur = dd.cur
        self.tbl = dd.tbl
        self.flds = dd.flds

    def update_db_dets(self, dbe, default_dbs, default_tbls, con_dets, cur, db, 
                       tbl,flds): 
        """
        Needed if table selected changes after the table type has been set to 
            raw.
        """
        self.dbe = dbe
        self.default_dbs = default_dbs
        self.default_tbls = default_tbls
        self.con_dets = con_dets
        self.db = db
        self.tbl = tbl
        self.flds = flds
    
    def get_demo_html_if_ok(self, css_idx):
        "Show demo table if sufficient data to do so"
        has_cols = lib.get_tree_ctrl_children(tree=self.coltree, 
                                              item=self.colroot)
        return self.get_demo_html(css_idx) if has_cols else ""
      
    def get_html(self, css_idx):
        """
        Returns demo_html.
        Update anything which might have changed first.
        Db details are updated anytime db or tbl changes.
        """
        self.add_total_row = self.chk_totals_row.IsChecked()
        self.first_col_as_label = self.chk_first_as_label.IsChecked()
        unused, tbl_filt = lib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
        self.where_tbl_filt, unused = lib.get_tbl_filts(tbl_filt)
        self.col_names, self.col_labels = lib.get_col_dets(self.coltree, 
                                                           self.colroot, 
                                                           self.var_labels)
        demo_html = rawtables.RawTable.get_html(self, css_idx, 
                                                page_break_after=False, 
                                                display_n=4)
        return demo_html

    
class DemoDimTable(dimtables.DimTable, DemoTable):
    "A demo table only - no real data inside"
    
    def __init__(self, txtTitles, txtSubtitles, colroot, rowroot, rowtree, 
                 coltree, col_no_vars_item, var_labels, val_dics):
        self.debug = False
        self.txt_titles = txtTitles
        self.txt_subtitles = txtSubtitles
        self.colroot = colroot
        self.rowroot = rowroot
        self.rowtree = rowtree
        self.coltree = coltree
        self.col_no_vars_item = col_no_vars_item
        self.var_labels = var_labels
        self.val_dics = val_dics
    
    def get_html(self, css_idx):
        "Returns demo_html"
        debug = False
        html = []
        (row_label_rows_lst, tree_row_labels, row_label_cols_n) = \
                                                    self.get_row_dets(css_idx)
        (tree_col_dets, hdr_html) = self.get_hdr_dets(row_label_cols_n, css_idx)
        html.append(hdr_html)
        if debug: print(row_label_rows_lst)
        row_label_rows_lst = self.get_body_html_rows(row_label_rows_lst,
                                                     tree_row_labels, 
                                                     tree_col_dets, css_idx)        
        html.append(u"\n\n<tbody>")
        for row in row_label_rows_lst:
            # flatten row list
            html.append(u"\n" + u"".join(row) + u"</tr>")
        html.append(u"\n</tbody>")
        demo_html = u"".join(html)
        return demo_html
    
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
                                                         item=self.rowroot):
            self.add_subtree_to_label_tree(tree_dims_item=row_child_item, 
                              tree_labels_node=tree_row_labels.root_node, 
                              dim=mg.ROWDIM)
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
        dim - mg.ROWDIM or mg.COLDIM
        """
        debug = False
        if dim == mg.COLDIM:
            tree = self.coltree
            item_conf = tree.GetItemPyData(tree_dims_item)
        elif dim == mg.ROWDIM:
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
            if dim == mg.ROWDIM and self.has_row_measures:
                # add measure label nodes
                if item_conf:
                    measures = item_conf.measures_lst
                else:
                    measures = [self.default_measure]
                self.add_measures(new_var_node, measures)
            else: # not a row dim with measures ... so can add values
                # (as labels if available, as placeholders otherwise) and 
                # possibly a total
                labels_dic = self.val_dics.get(var_name, {})
                subitems_lst = [] # build subitems list
                for (i, (key, val_label)) in enumerate(labels_dic.items()):
                    if i > 1:
                        break
                    subitems_lst.append(val_label)
                if item_conf.sort_order == mg.SORT_LABEL:
                    subitems_lst.sort()
                i = len(subitems_lst) + 1 # so first filler is Val 2 if first 
                # value already filled
                while len(subitems_lst) < 2:
                    subitems_lst.append(u"Value %s" % i)
                    i = i+1
                if item_conf.has_tot:
                    subitems_lst.append(mg.HAS_TOTAL)
                force_freq = True # TODO - get from GUI but better to KISS
                for j, subitem in enumerate(subitems_lst):
                    is_coltot = (item_conf.has_tot and dim == mg.COLDIM
                                 and j == len(subitems_lst)-1)
                    # make val node e.g. Male
                    subitem_node = dimtables.LabelNode(label=subitem)
                    new_var_node.add_child(subitem_node)                
                    if is_terminal and dim == mg.COLDIM and \
                            self.has_col_measures:
                        # add measure label nodes
                        measures = item_conf.measures_lst
                        if not measures:
                            measures = [self.default_measure]
                        self.add_measures(subitem_node, measures, is_coltot, 
                                          force_freq)
                    else:
                        # for each child of tree_dims_item e.g. Eth and Age Gp
                        if dim == mg.COLDIM:
                            tree = self.coltree
                        elif dim == mg.ROWDIM:
                            tree = self.rowtree
                        child_items = lib.get_tree_ctrl_children(tree=tree, 
                                                            item=tree_dims_item)
                        if debug:
                            print(lib.get_sub_tree_items(tree=tree,
                                                         parent=tree_dims_item))
                        for child_item in child_items:
                            self.add_subtree_to_label_tree(tree_dims_item=\
                                   child_item, tree_labels_node=subitem_node, 
                                   dim=dim)
    
    def add_measures(self, node, measures, is_coltot=False, force_freq=False):
        sep_measures = measures[:]
        if force_freq and is_coltot and mg.ROWPCT in measures \
                and mg.FREQ not in measures:
            sep_measures.append(mg.FREQ)
        for measure in sep_measures:
            node.add_child(dimtables.LabelNode(label=measure, measure=measure))
    
    def add_subtrees_to_col_label_tree(self, tree_col_labels):
        """
        Add subtrees to column label tree.
        If coltree has no children, (not even the col no vars item)
        do not add one hee (unlike Live Tables).  It will be handled
        by the calling class e.g. by adding measures or raising an
        exception.
        """
        col_children = lib.get_tree_ctrl_children(tree=self.coltree, 
                                                  item=self.colroot)
        for col_child_item in col_children:
            self.add_subtree_to_label_tree(tree_dims_item=col_child_item, 
                                  tree_labels_node=tree_col_labels.root_node, 
                                  dim=mg.COLDIM)
        return tree_col_labels
    

class GenDemoTable(DemoDimTable):
    "A general demo table"
    
    has_row_measures = False
    has_row_vals = True
    has_col_measures = True
    default_measure = lib.get_default_measure(mg.FREQS_TBL)
    
    def __init__(self, txtTitles, txtSubtitles, colroot, rowroot, rowtree, 
                 coltree, col_no_vars_item, var_labels, val_dics):
        DemoDimTable.__init__(self, txtTitles, txtSubtitles, colroot, rowroot, 
                              rowtree, coltree, col_no_vars_item, var_labels, 
                              val_dics)
        
    def get_demo_html_if_ok(self, css_idx):
        "Show demo table if sufficient data to do so"
        has_rows = lib.get_tree_ctrl_children(tree=self.rowtree, 
                                              item=self.rowroot)
        has_cols = lib.get_tree_ctrl_children(tree=self.coltree, 
                                              item=self.colroot)
        if has_rows and has_cols:
            return self.get_demo_html(css_idx)
        else:
            return u""
    
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
        hdr_dets = self.process_hdr_tree(tree_col_labels, row_label_cols_n, 
                                         css_idx)
        return hdr_dets

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
        CSS_FIRST_DATACELL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_DATACELL, 
                                                       css_idx)
        CSS_DATACELL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_DATACELL, css_idx)
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
                # build data row list
                raw_val = lib.get_rand_val_of_type(mg.FLD_TYPE_NUMERIC)
                data_val = unicode(raw_val)  
                if colmeasure in [mg.ROWPCT, mg.COLPCT]:
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
    default_measure = lib.get_default_measure(mg.ROW_SUMM)
    
    def __init__(self, txtTitles, txtSubtitles, colroot, rowroot, rowtree, 
                 coltree, col_no_vars_item, var_labels, val_dics):
        DemoDimTable.__init__(self, txtTitles, txtSubtitles, colroot, rowroot, 
                              rowtree, coltree, col_no_vars_item, var_labels, 
                              val_dics)

    def get_demo_html_if_ok(self, css_idx):
        "Show demo table if sufficient data to do so"
        has_rows = lib.get_tree_ctrl_children(tree=self.rowtree,
                                              item=self.rowroot)
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
        hdr_dets = self.process_hdr_tree(tree_col_labels, row_label_cols_n, 
                                         css_idx)
        return hdr_dets

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
        CSS_FIRST_DATACELL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_DATACELL, 
                                                       css_idx)
        CSS_DATACELL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_DATACELL, css_idx)
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
                raw_val = lib.get_rand_val_of_type(mg.FLD_TYPE_NUMERIC)
                data_val = unicode(raw_val)  
                if rowmeasure == mg.SUMM_N:
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