
import random

import tabreports
import getdata
import rawtables
import make_table
import util
import dimtables


num_data_seq = ("1.0", "1.5", "2.0", "2.5", "3.0", "3.5", "12.0", "35.0")
str_data_seq = ("Lorem", "ipsum", "dolor", "sit", "amet")
dtm_data_seq = ("1 Feb 2009", "23 Aug 1994", "16 Sep 2001", "7 Nov 1986")

class DemoTable(object):
    """
    All demo tables, whether dim tables or raw tables, derive from this class.
    """
    
    def getDemoHTMLIfOK(self):
        "Get HTML to display if enough data to display"
        assert 0, "getDemoHTMLIfOK must be defined by subclass"

    def getHTMLParts(self):
        "Returns (hdr_html, body_html)"
        assert 0, "getHTMLParts must be defined by subclass"

    def getDemoHTML(self):
        "Get demo HTML for table"
        # sort titles out first
        if self.txtTitles.GetValue():
            self.titles = ["%s" % x for x \
                      in self.txtTitles.GetValue().split("\n")]
        else:
            self.titles = []
        if self.txtSubtitles.GetValue():
            self.subtitles = ["%s" % x for x \
                         in self.txtSubtitles.GetValue().split("\n")]
        else:
            self.subtitles = []
        if self.titles:
            self.titles[0] += " (random demo data only)"        
        html = tabreports.getHtmlHdr(hdr_title="Report(s)", 
                                     fil_css=self.fil_css)
        html += "<table cellspacing='0'>\n" # IE6 doesn't support CSS borderspacing
        (hdr_html, body_html) = self.getHTMLParts()
        html += hdr_html
        html += body_html
        html += "\n</table>"
        html += "\n</body>\n</html>"
        #print html
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
        
    def getDemoHTMLIfOK(self):
        "Show demo table if sufficient data to do so"
        has_cols = util.getTreeCtrlChildren(tree=self.coltree, 
                                    parent=self.colRoot)
        return self.getDemoHTML() if has_cols else ""
      
    def getHTMLParts(self):
        """
        Returns (hdr_html, body_html).
        If value labels available, use these rather than random numbers.
        """
        col_names, col_labels = make_table.GetColDets(self.coltree, 
                                                      self.colRoot, 
                                                      self.var_labels)
        cols_n = len(col_names)        
        bolhas_totals_row = self.chkTotalsRow.IsChecked()
        bolfirst_col_as_label = self.chkFirstAsLabel.IsChecked()
        hdr_html = self.getHdrDets(col_labels)
        body_html = "\n<tbody>"        
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
            col_class_lsts[0] = [tabreports.CSS_LBL]
        for i, col_name in enumerate(col_names):
            if self.flds[col_name][getdata.FLD_BOLNUMERIC] \
                    and not col_val_dics[i]:
                col_class_lsts[i].append(tabreports.CSS_ALIGN_RIGHT)
        for i in range(4): # four rows enough for demo purposes
            row_tds = []
            # process cells within row
            for j in range(cols_n):
                # cell contents
                if col_val_dics[j]: # choose a random value label
                    random_key = random.choice(col_val_dics[j].keys())
                    row_val = col_val_dics[j][random_key]
                elif self.flds[col_names[j]][getdata.FLD_BOLNUMERIC]: # choose a random number
                    row_val = str(random.choice(num_data_seq))
                elif self.flds[col_names[j]][getdata.FLD_BOLDATETIME]: # choose a random date
                    row_val = str(random.choice(dtm_data_seq))
                else:
                    row_val = str(random.choice(str_data_seq))
                # cell format
                col_class_names = "\"" + " ".join(col_class_lsts[j]) + "\""
                col_classes = "class = %s" % col_class_names if col_class_names else ""
                row_tds.append("<td %s>%s</td>" % (col_classes, row_val))
            body_html += "\n<tr>" + "".join(row_tds) + "</td></tr>"
        if bolhas_totals_row:
            if bolfirst_col_as_label:
                tot_cell = "<td class='%s'>TOTAL</td>" % tabreports.CSS_LBL
                start_idx = 1
            else:
                tot_cell = ""
                start_idx = 0
            # get demo data
            demo_row_data_lst = []
            for i in range(start_idx, cols_n):
                # if has value dic OR not numeric (e.g. date or string), 
                # show empty cell as total
                if col_val_dics[i] or \
                    not self.flds[col_names[i]][getdata.FLD_BOLNUMERIC]: 
                    demo_row_data_lst.append("&nbsp;&nbsp;")
                else:
                    demo_row_data_lst.append(str(random.choice(num_data_seq)))
            # never a displayed total for strings (whether orig data or labels)
            joiner = "</td><td class=\"%s\">" % tabreports.CSS_ALIGN_RIGHT
            body_html += "\n<tr class='total-row'>" + \
                tot_cell + "<td class=\"%s\">"  % tabreports.CSS_ALIGN_RIGHT + \
                joiner.join(demo_row_data_lst) + "</td></tr>"
        body_html += "\n</tbody>"
        return (hdr_html, body_html)

    
class DemoDimTable(dimtables.DimTable, DemoTable):
    "A demo table only - no real data inside"
    
    def __init__(self, txtTitles, txtSubtitles, colRoot, rowRoot, rowtree, 
                 coltree, col_no_vars_item, var_labels, val_dics, fil_css):
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
    
    def getHTMLParts(self):
        "Returns (hdr_html, body_html)"
        (row_label_rows_lst, tree_row_labels, row_label_cols_n) = \
            self.getRowDets()
        (tree_col_dets, hdr_html) = self.getHdrDets(row_label_cols_n)
        #print row_label_rows_lst #debug
        row_label_rows_lst = self.getBodyHtmlRows(row_label_rows_lst,
                                                  tree_row_labels, 
                                                  tree_col_dets)        
        body_html = "\n\n<tbody>"
        for row in row_label_rows_lst:
            # flatten row list
            body_html += "\n" + "".join(row) + "</tr>"
        body_html += "\n</tbody>"
        return (hdr_html, body_html)
    
    def getRowDets(self):
        """
        Return row_label_rows_lst - need combination of row and col filters
            to add the data cells to the table body rows.
        tree_row_labels - not needed here - only with display of 
            actual data
        row_label_cols_n - needed to set up header (need to span the 
            row labels).
        """
        tree_row_labels = dimtables.LabelNodeTree()
        for row_child_item in util.getTreeCtrlChildren(tree=self.rowtree, 
                                                    parent=self.rowRoot):
            self.addSubtreeToLabelTree(tree_dims_item=row_child_item, 
                              tree_labels_node=tree_row_labels.root_node, 
                              dim=dimtables.ROWDIM)
        return self.processRowTree(tree_row_labels)

    def addSubtreeToLabelTree(self, tree_dims_item, tree_labels_node, dim):
        """
        NB tree_dims_item is a wxPython TreeCtrl item.
        If the tree_dims_item is the special col_no_vars_item
          just add the measures underneath the label node.
        Otherwise, for each dim item, e.g. gender, add node to the 
          labels tree,
          then the first two values underneath (and total if relevant).
        If the variable node is terminal, then add the measures underneath 
        the new value label nodes.
        If not terminal, add a node for each var underneath 
          (e.g. Ethnicity and Age Gp) under each value node and 
          send through again.
        dim - dimtables.ROWDIM or dimtables.COLDIM
        """
        if dim == dimtables.COLDIM:
            item_conf = self.coltree.GetItemPyData(tree_dims_item)
        elif dim == dimtables.ROWDIM:
            item_conf = self.rowtree.GetItemPyData(tree_dims_item)        
        if item_conf == None:
            item_conf = make_table.ItemConfig()
        if tree_dims_item == self.col_no_vars_item:
            # add measures only
            if item_conf:
                measures = item_conf.measures_lst
            else:
                measures = [self.default_measure]
            for measure in measures:
                tree_labels_node.addChild(dimtables.LabelNode(label=measure, 
                                                        measure=measure))
        else:
            # add var e.g. gender then values below e.g. Male, Female
            var_name, var_label = getdata.extractVarDets(\
                self.coltree.GetItemText(tree_dims_item))
            #print var_name #debug
            var_label = self.var_labels.get(var_name, var_name.title())
            new_var_node = tree_labels_node.addChild(\
                                            dimtables.LabelNode(label=var_label))
            # terminal tree_dim_item (got any children)?
            item, cookie = self.coltree.GetFirstChild(tree_dims_item)
            is_terminal = not item #i.e. if there is only the root there
            if dim==dimtables.ROWDIM and self.has_row_measures:
                # add measure label nodes
                if item_conf:
                    measures = item_conf.measures_lst
                else:
                    measures = [self.default_measure]
                for measure in measures:
                    new_var_node.addChild(dimtables.LabelNode(\
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
                if item_conf.sort_order == dimtables.SORT_LABEL:
                    subitems_lst.sort()
                i=len(subitems_lst) + 1 # so first filler is Val 2 if first 
                # value already filled
                while len(subitems_lst) < 2:
                    subitems_lst.append("Value %s" % i)
                    i=i+1
                if item_conf.has_tot:
                    subitems_lst.append(make_table.HAS_TOTAL)
                for subitem in subitems_lst:
                    # make val node e.g. Male
                    subitem_node = dimtables.LabelNode(label=subitem)
                    new_var_node.addChild(subitem_node)                
                    if is_terminal and dim==dimtables.COLDIM and \
                        self.has_col_measures:
                        # add measure label nodes
                        measures = item_conf.measures_lst
                        if not measures:
                            measures = [self.default_measure]
                        for measure in measures:
                            subitem_node.addChild(dimtables.LabelNode(\
                                                label=measure,
                                                measure=measure))
                    else:
                        # for each child of tree_dims_item e.g. Eth and Age Gp
                        if dim == dimtables.COLDIM:
                            tree = self.coltree
                        elif dim == dimtables.ROWDIM:
                            tree = self.rowtree
                        child_items = util.getTreeCtrlChildren(tree=tree, 
                                                        parent=tree_dims_item)
                        #print util.getSubTreeItems(tree=tree, parent=tree_dims_item) #debug
                        for child_item in child_items:
                            self.addSubtreeToLabelTree(tree_dims_item=\
                                   child_item, tree_labels_node=subitem_node, 
                                   dim=dim)
    
    def addSubtreesToColLabelTree(self, tree_col_labels):
        """
        Add subtrees to column label tree.
        If coltree has no children, (not even the col no vars item)
        do not add one hee (unlike Live Tables).  It will be handled
        by the calling class e.g. by adding measures or raising an
        exception.
        """
        col_children = util.getTreeCtrlChildren(tree=self.coltree, 
                                                parent=self.colRoot)
        for col_child_item in col_children:
            self.addSubtreeToLabelTree(tree_dims_item=col_child_item, 
                          tree_labels_node=tree_col_labels.root_node, 
                          dim=dimtables.COLDIM)
        return tree_col_labels
    

class GenDemoTable(DemoDimTable):
    "A general demo table"
    
    has_row_measures = False
    has_row_vals = True
    has_col_measures = True
    default_measure = make_table.get_default_measure(make_table.COL_MEASURES)
    
    def __init__(self, txtTitles, txtSubtitles, colRoot, rowRoot, rowtree, 
                 coltree, col_no_vars_item, var_labels, val_dics, fil_css):
        DemoDimTable.__init__(self, txtTitles, txtSubtitles, colRoot, rowRoot, 
                           rowtree, coltree, col_no_vars_item, var_labels, 
                           val_dics, fil_css)
        
    def getDemoHTMLIfOK(self):
        "Show demo table if sufficient data to do so"
        has_rows = util.getTreeCtrlChildren(tree=self.rowtree, 
                                    parent=self.rowRoot)
        has_cols = util.getTreeCtrlChildren(tree=self.coltree, 
                                         parent=self.colRoot)
        if has_rows and has_cols:
            return self.getDemoHTML()
        else:
            return ""
    
    def getHdrDets(self, row_label_cols_n):
        """
        Return tree_col_labels and the table header HTML.
        For HTML provide everything from <thead> to </thead>.
        """
        tree_col_labels = dimtables.LabelNodeTree()
        tree_col_labels = self.addSubtreesToColLabelTree(tree_col_labels)
        if tree_col_labels.getDepth() == 1:
            raise Exception, "There must always be a column item " + \
                "even if only the col no vars item"
        return self.processHdrTree(tree_col_labels, row_label_cols_n)    

    def getBodyHtmlRows(self, row_label_rows_lst, tree_row_labels,
                        tree_col_labels):
        """
        Make table body rows based on contents of row_label_rows_lst:
        e.g. [["<tr>", "<td class='firstrowvar' rowspan='8'>Gender</td>" ...],
        ...]
        It already contains row label data - we need to add the data cells 
        into the appropriate row list within row_label_rows_lst before
        concatenating and appending "</tr>".
        """
        #print row_label_rows_lst #debug
        col_term_nodes = tree_col_labels.getTerminalNodes()
        row_term_nodes = tree_row_labels.getTerminalNodes()
        col_filters_lst = [x.filts for x in col_term_nodes]
        col_filt_flds_lst = [x.filt_flds for x in col_term_nodes]
        col_tots_lst = [x.is_coltot for x in col_term_nodes]
        col_measures_lst = [x.measure for x in col_term_nodes]
        row_filters_lst = [x.filts for x in row_term_nodes]
        row_filt_flds_lst = [x.filt_flds for x in row_term_nodes]
        data_cells_n = len(row_term_nodes) * len(col_term_nodes)
        #print "%s data cells in table" % data_cells_n
        row_label_rows_lst = self.getRowLabelsRowLst(row_filters_lst, 
            row_filt_flds_lst, col_measures_lst, col_filters_lst, 
            col_tots_lst, col_filt_flds_lst, row_label_rows_lst, 
            data_cells_n, col_term_nodes)
        return row_label_rows_lst
                
    def getRowLabelsRowLst(self, row_filters_lst, row_filt_flds_lst, 
                           col_measures_lst, col_filters_lst, 
                           col_tots_lst, col_filt_flds_lst, 
                           row_label_rows_lst, data_cells_n,
                           col_term_nodes):
        """
        Get list of row data.  Each row in the list is represented
        by a row of strings to concatenate, one per data point.
        """
        i=0
        data_item_presn_lst = []
        for (row_filter, row_filt_flds) in zip(row_filters_lst,
                                               row_filt_flds_lst):
            first = True
            for (colmeasure, col_filter, coltot, col_filt_flds) in \
                        zip(col_measures_lst, col_filters_lst, 
                            col_tots_lst, col_filt_flds_lst):
                if first:
                    cellclass = "firstdatacell"
                    first = False
                else:
                    cellclass = "datacell"
                #build data row list
                data_val = random.choice(num_data_seq)
                if colmeasure in [dimtables.ROWPCT, dimtables.COLPCT]:
                    val = "%s%%" % data_val
                else:
                    val = data_val
                data_item_presn_lst.append("<td class='%s'>%s</td>" % \
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
    default_measure = make_table.get_default_measure(make_table.ROW_SUMM)
    
    def __init__(self, txtTitles, txtSubtitles, colRoot, rowRoot, rowtree, 
                 coltree, col_no_vars_item, var_labels, val_dics, fil_css):
        DemoDimTable.__init__(self, txtTitles, txtSubtitles, colRoot, rowRoot, 
                           rowtree, coltree, col_no_vars_item, var_labels, 
                           val_dics, fil_css)

    def getDemoHTMLIfOK(self):
        "Show demo table if sufficient data to do so"
        has_rows = util.getTreeCtrlChildren(tree=self.rowtree, 
                                    parent=self.rowRoot)
        return self.getDemoHTML() if has_rows else ""
            
    def getHdrDets(self, row_label_cols_n):
        """
        Return tree_col_labels and the table header HTML.
        For HTML provide everything from <thead> to </thead>.
        If no column variables, make a special column node.
        """
        tree_col_labels = dimtables.LabelNodeTree()
        tree_col_labels = self.addSubtreesToColLabelTree(tree_col_labels)
        if tree_col_labels.getDepth() == 1:
            tree_col_labels.addChild(dimtables.LabelNode(label="Measures"))
        return self.processHdrTree(tree_col_labels, row_label_cols_n)

    def getBodyHtmlRows(self, row_label_rows_lst, tree_row_labels,
                        tree_col_labels):
        """
        Make table body rows based on contents of row_label_rows_lst:
        e.g. [["<tr>", "<td class='firstrowvar' rowspan='8'>Gender</td>" ...],
        ...]
        It already contains row label data - we need to add the data cells 
        into the appropriate row list within row_label_rows_lst before
        concatenating and appending "</tr>".
        """
        col_term_nodes = tree_col_labels.getTerminalNodes()
        row_term_nodes = tree_row_labels.getTerminalNodes()
        row_measures_lst = [x.measure for x in row_term_nodes]
        col_filters_lst = [x.filts for x in col_term_nodes] #can be [[],[],[], ...]
        row_filt_flds_lst = [x.filt_flds for x in row_term_nodes]
        col_filt_flds_lst = [x.filt_flds for x in col_term_nodes]
        col_tots_lst = [x.is_coltot for x in col_term_nodes]
        data_cells_n = len(row_term_nodes) * len(col_term_nodes)
        #print "%s data cells in table" % data_cells_n
        row_label_rows_lst = self.getRowLabelsRowLst(row_filt_flds_lst, 
                                row_measures_lst, col_filters_lst, 
                                row_label_rows_lst, col_term_nodes)
        return row_label_rows_lst
    
    def getRowLabelsRowLst(self, row_flds_lst,  
                           row_measures_lst, col_filters_lst, 
                           row_label_rows_lst, col_term_nodes):
        """
        Get list of row data.  Each row in the list is represented
        by a row of strings to concatenate, one per data point.
        Get data values one at a time (no batches unlike Gen Tables).
        """
        data_item_lst = []
        for (rowmeasure, row_fld_lst) in zip(row_measures_lst, 
                                             row_flds_lst):
            first = True
            for col_filter_lst in col_filters_lst:
                #styling
                if first:
                    cellclass = "firstdatacell"
                    first = False
                else:
                    cellclass = "datacell"
                data_val = random.choice(num_data_seq)
                if rowmeasure == dimtables.SUMM_N:
                    val = "N=%s" % data_val
                else:
                    val = data_val
                data_item_lst.append("<td class='%s'>%s</td>" % \
                                     (cellclass, val))
        i=0
        for row in row_label_rows_lst:
            for j in range(len(col_term_nodes)):
                row.append(data_item_lst[i])
                i=i+1
        return row_label_rows_lst