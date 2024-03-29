from .. import basic_lib as b
from .. import my_globals as mg
from .. import lib
from .. import my_exceptions
from .. import output
from . import dimtables
from . import rawtables

import wx


class DemoTable:
    """
    All demo tables, whether dim tables or raw tables, derive from this class.
    """

    def get_demo_html_if_ok(self, css_idx, *, dp):
        "Show demo table if sufficient data to do so"
        has_cols = lib.GuiLib.get_tree_ctrl_children(
            tree=self.coltree, item=self.colroot)
        if self.needs_rows:
            has_rows = lib.GuiLib.get_tree_ctrl_children(
                tree=self.rowtree, item=self.rowroot)
            is_ok = has_rows and has_cols
        else:
            is_ok = has_cols
        return self.get_demo_html(css_idx, dp=dp) if is_ok else ''

    def get_html(self, css_idx, *, dp):
        "Returns html"
        raise NotImplementedError('get_html must be defined by subclass')

    def get_body_html_rows(self, row_label_rows_lst,
            tree_row_labels, tree_col_labels, css_idx, *, dp):
        """
        Make table body rows based on contents of row_label_rows_lst:
        e.g. [["<tr>", "<td class='firstrowvar' rowspan='8'>Gender</td>" ...],
        ...]
        It already contains row label data - we need to add the data cells
        into the appropriate row list within row_label_rows_lst before
        concatenating and appending "</tr>".
        """
        try:
            col_term_nodes = tree_col_labels.get_terminal_nodes()
            row_term_nodes = tree_row_labels.get_terminal_nodes()
            col_filters_lst = [x.filts for x in col_term_nodes]
            col_filt_flds_lst = [x.filt_flds for x in col_term_nodes]
            col_tots_lst = [x.is_coltot for x in col_term_nodes]
            col_measures_lst = [x.measure for x in col_term_nodes]
            row_filters_lst = [x.filts for x in row_term_nodes]
            row_label_rows_lst = self.get_row_labels_row_lst(row_filters_lst,
                col_measures_lst, col_filters_lst,
                col_tots_lst, col_filt_flds_lst, row_label_rows_lst,
                col_term_nodes, css_idx, dp)
        except Exception as e:
            row_label_rows_lst = ['<td>Problem getting table output: '
                f'Orig error: {b.ue(e)}</td>']
        return row_label_rows_lst

    def get_row_labels_row_lst(self, row_filters_lst,
            col_measures_lst, col_filters_lst, col_tots_lst, col_filt_flds_lst,
            row_label_rows_lst, col_term_nodes, css_idx, dp):
        """
        Get list of row data. Each row in the list is represented by a row of
        strings to concatenate, one per data point.
        """
        CSS_FIRST_DATACELL = mg.CSS_SUFFIX_TEMPLATE % (
            mg.CSS_FIRST_DATACELL, css_idx)
        CSS_DATACELL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_DATACELL, css_idx)
        i = 0
        data_item_presn_lst = []
        for unused in row_filters_lst:
            first = True
            for (colmeasure, _colfilter, 
                _coltot, _colfiltfld) in zip(col_measures_lst, col_filters_lst,
                    col_tots_lst, col_filt_flds_lst):
                if first:
                    cellclass = CSS_FIRST_DATACELL
                    first = False
                else:
                    cellclass = CSS_DATACELL
                ## build data row list
                dp_tpl = f'%.{dp}f'
                raw_val = dp_tpl % lib.get_rand_val_of_type(
                    mg.FLDTYPE_NUMERIC_KEY)
                num2display = lib.OutputLib.get_num2display(num=raw_val,
                    output_type=mg.MEASURE_LBL2KEY[colmeasure],
                    inc_perc=self.show_perc)
                data_item_presn_lst.append(
                    f"<td class='{cellclass}'>{num2display}</td>")
                i = i + 1
        i = 0
        ## put the cell data (inc html) into the right places
        for row in row_label_rows_lst:
            for unused in col_term_nodes:
                row.append(data_item_presn_lst[i])
                i = i + 1
        return row_label_rows_lst

    def get_demo_html(self, css_idx, *, dp):
        """
        Get demo HTML for table.
        """
        debug = False
        cc = output.get_cc()
        ## sort titles out first
        if self.txt_titles.GetValue():
            self.titles = self.txt_titles.GetValue().split('\n')
        else:
            self.titles = []
        if self.txt_subtitles.GetValue():
            self.subtitles = self.txt_subtitles.GetValue().split('\n')
        else:
            self.subtitles = []
        if debug: print(cc[mg.CURRENT_CSS_PATH])
        html = []
        try:
            html.append(output.get_html_hdr(hdr_title=_('Report(s)'),
                css_fpaths=[cc[mg.CURRENT_CSS_PATH], ],
                new_js_n_charts=None, has_dojo=False,
                default_if_prob=True, grey=True, abs_pth=True))
            html.append("<table cellspacing='0'>\n")  ## IE6 no CSS borderspacing
            main_html = self.get_html(css_idx, dp=dp)
        except my_exceptions.MissingCss:
            raise
        except my_exceptions.TooFewValsForDisplay:
            raise
        except Exception as e:
            wx.MessageBox(_('Unable to make report. Error details: %s')
                % b.ue(e))
            raise
        html.append(main_html)
        html.append('\n</table>')
        html.append('\n</body>\n</html>')
        demo_html = ''.join(html)
        if debug: print(demo_html)
        return demo_html


class DemoRawTable(rawtables.RawTable, DemoTable):
    """
    Demo display raw table. Reads actual data.
    """

    def __init__(self, txt_titles, txt_subtitles, colroot, coltree, var_labels, 
                 val_dics, add_total_row, first_col_as_label):
        """
        txt_titles -- actual GUI object - turned into text 
        """
        self.txt_titles = txt_titles
        self.txt_subtitles = txt_subtitles
        self.colroot = colroot
        self.coltree = coltree
        self.var_labels = var_labels
        self.val_dics = val_dics
        self.add_total_row = add_total_row
        self.first_col_as_label = first_col_as_label
        self.needs_rows = mg.RPT_CONFIG[mg.DATA_LIST][mg.NEEDS_ROWS_KEY]
   
    def get_html(self, css_idx, *, dp):
        """
        Returns demo_html.
        Always run off fresh data - guaranteed by using dd. Can't take db 
            settings when instantiated - may change after that.
        """
        dd = mg.DATADETS_OBJ
        unused, tbl_filt = lib.FiltLib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
        where_tbl_filt, unused = lib.FiltLib.get_tbl_filts(tbl_filt)
        (col_names, col_labels,
         col_sorting) = lib.GuiLib.get_col_dets(self.coltree, self.colroot,
                                                self.var_labels)
        demo_html = rawtables.get_html(self.titles, self.subtitles, dd.dbe,
            col_labels, col_names, col_sorting, dd.tbl, dd.flds, dd.cur,
            self.first_col_as_label, self.val_dics, self.add_total_row,
            where_tbl_filt, css_idx, page_break_after=False, display_n=4)
        return demo_html


class DemoDimTable(dimtables.DimTable, DemoTable):
    """
    A demo table only - no real data inside. Just uses labels from GUI (stored
    in tree structures) to fake up a table with no real numbers inside.

    The only connection with the database is when the variables are defined. And
    the trees get wiped every time a database or table change is made. So always
    fresh and running off selected data.
    """
    def __init__(self,
            txt_titles, txt_subtitles,
            tab_type, colroot, rowroot,
            rowtree, coltree,
            col_no_vars_item, var_labels, val_dics):
        self.debug = False
        self.txt_titles = txt_titles
        self.txt_subtitles = txt_subtitles
        self.tab_type = tab_type
        rpt_config = mg.RPT_CONFIG[self.tab_type]
        self.has_col_measures = len(rpt_config[mg.COL_MEASURES_KEY])
        self.needs_rows = rpt_config[mg.NEEDS_ROWS_KEY]
        self.var_summarised = rpt_config[mg.VAR_SUMMARISED_KEY]
        self.default_measure = rpt_config[mg.DEFAULT_MEASURE_KEY]
        self.colroot = colroot
        self.rowroot = rowroot
        self.rowtree = rowtree
        self.coltree = coltree
        self.col_no_vars_item = col_no_vars_item
        self.var_labels = var_labels
        self.val_dics = val_dics
        # show_perc not set here when instantiated as must be checked from UI 
        #    each time get_demo_html_if_ok() is called.

    def get_html(self, css_idx, *, dp):
        "Returns demo_html"
        debug = False
        html = []
        title_dets_html = output.get_title_dets_html(
            self.titles, self.subtitles, css_idx, istable=True)
        html.append(title_dets_html)
        (row_label_rows_lst, tree_row_labels, 
            row_label_cols_n) = self.get_row_dets(css_idx)
        html.append("\n\n<table cellspacing='0'>\n")  ## IE6 - no support CSS borderspacing
        (tree_col_dets, hdr_html) = self.get_hdr_dets(row_label_cols_n, css_idx)
        html.append(hdr_html)
        if debug: print(row_label_rows_lst)
        row_label_rows_lst = self.get_body_html_rows(row_label_rows_lst,
            tree_row_labels, tree_col_dets, css_idx, dp=dp)
        html.append('\n\n<tbody>')
        for row in row_label_rows_lst:  ## flatten row list
            html.append('\n' + ''.join(row) + '</tr>')
        html.append('\n</tbody>')
        demo_html = ''.join(html)
        return demo_html

    def get_hdr_dets(self, row_label_cols_n, css_idx):
        """
        Return tree_col_labels and the table header HTML.

        For HTML provide everything from <thead> to </thead>.
        """
        tree_col_labels = dimtables.LabelNodeTree()
        tree_col_labels = self.add_subtrees_to_col_label_tree(tree_col_labels)
        if tree_col_labels.get_depth() == 1:
            raise Exception('There must always be a column item even if only '
                'the col no vars item')
        hdr_dets = self.process_hdr_tree(
            tree_col_labels, row_label_cols_n, css_idx)
        return hdr_dets

    def get_row_dets(self, css_idx):
        """
        Return row_label_rows_lst - need combination of row and col filters
        to add the data cells to the table body rows.

        tree_row_labels - not needed here - only with display of actual data

        row_label_cols_n - needed to set up header (need to span the row labels)
        """
        tree_row_labels = dimtables.LabelNodeTree()
        for row_child_item in lib.GuiLib.get_tree_ctrl_children(
                tree=self.rowtree, item=self.rowroot):
            self.add_subtree_to_label_tree(
                tree_dims_item=row_child_item,
                tree_labels_node=tree_row_labels.root_node,
                dim=mg.ROWDIM_KEY)
        ## If no row variables, make a special row node.
        if tree_row_labels.get_depth() == 1:
            child = dimtables.LabelNode(label=mg.EMPTY_ROW_LBL)
            tree_row_labels.add_child(child)
        return self.process_row_tree(tree_row_labels, css_idx)

    def add_subtree_to_label_tree(self,
            tree_dims_item, tree_labels_node, dim):
        """
        Overview -- 1) if col_no_vars, just the measures; 2) if row summ, vars
        and then measures; 3) normal, vars then vals, (then vars then vals etc)
        then measures.

        Note - tree_dims_item is a wxPython TreeCtrl item.

        If the tree_dims_item is the special col_no_vars_item, we want the
        measures directly underneath the label node root. NB this is the GUI
        tree item, not the Dim Nodes item that gets built off it when the script
        is actually run.

        If the table is a Row Summ, we want the vars at the top and measures
        directly underneath.

        Otherwise, for each dim item, e.g. gender, add node to the labels tree,
        then the first two values underneath (and total if relevant).

        If the variable node is terminal, then add the measures underneath the
        new value label nodes.

        If not terminal, add a node for each var underneath (e.g. Ethnicity and
        Age Gp) under each value node and send through again.

        :param str dim: mg.ROWDIM_KEY or mg.COLDIM_KEY
        """
        debug = False
        if dim == mg.COLDIM_KEY:
            tree = self.coltree
            item_conf = tree.GetItemPyData(tree_dims_item)
        elif dim == mg.ROWDIM_KEY:
            tree = self.rowtree
            item_conf = tree.GetItemPyData(tree_dims_item)        
        if item_conf is None:
            default_sort = (mg.SORT_NONE_LBL if self.tab_type == mg.DATA_LIST
                else mg.SORT_VALUE_LBL)
            item_conf = lib.ItemConfig(sort_order=default_sort)
        ## 1) if col_no_vars, just the measures
        if tree_dims_item == self.col_no_vars_item:
            ## add measures only
            if item_conf:
                measures = item_conf.measures_lst
            else:
                measures = [self.default_measure]
            for measure in measures:
                tree_labels_node.add_child(dimtables.LabelNode(label=measure,
                                                               measure=measure))
            return
        ## Add var e.g. gender (and if not row summ, then values below e.g. Male, Female.
        var_name = item_conf.var_name
        if debug: print(var_name)
        var_label = self.var_labels.get(var_name, var_name.title())
        var_node2add = dimtables.LabelNode(label=var_label)
        new_var_node = tree_labels_node.add_child(var_node2add)
        if dim == mg.COLDIM_KEY and self.var_summarised:
            ## 2) if row summ, vars and then measures
            """
            Each variable is terminal and has measures. Add measures.
            """
            ## add measure label nodes
            measures = item_conf.measures_lst
            if not measures:
                measures = [self.default_measure]
            self.add_measures(new_var_node, measures)
        else:  ## 3) normal, vars then vals, (then vars then vals etc) then measures.
            ## terminal tree_dim_item (got any children)?
            item, unused = self.coltree.GetFirstChild(tree_dims_item)
            is_terminal = not item  ## i.e. if there is only the root there
            ## Can add values (as labels if available, as placeholders otherwise)
            ## and possibly a total
            labels_dic = self.val_dics.get(var_name, {})
            subitems_lst = []  ## build subitems list
            for (i, (unused, val_label)) in enumerate(labels_dic.items()):
                if i > 1:
                    break
                subitems_lst.append(val_label)
            if item_conf.sort_order == mg.SORT_LBL_LBL:
                subitems_lst.sort()
            i = len(subitems_lst) + 1  ## so first filler is Val 2 if first value already filled
            while len(subitems_lst) < 2:
                subitems_lst.append(f'Value {i}')
                i = i + 1
            if item_conf.has_tot:
                subitems_lst.append(mg.HAS_TOTAL)
            force_freq = True  ## TODO - get from GUI but better to KISS
            for j, subitem in enumerate(subitems_lst):
                is_coltot = (
                    item_conf.has_tot
                    and dim == mg.COLDIM_KEY
                    and j == len(subitems_lst)-1)
                ## make val node e.g. Male
                subitem_node = dimtables.LabelNode(label=subitem)
                new_var_node.add_child(subitem_node)   
                if (is_terminal
                        and dim == mg.COLDIM_KEY
                        and self.has_col_measures):
                    ## add measure label nodes
                    measures = item_conf.measures_lst
                    if not measures:
                        measures = [self.default_measure]
                    self.add_measures(
                        subitem_node, measures,
                        is_coltot=is_coltot, force_freq=force_freq)
                else:
                    ## for each child of tree_dims_item e.g. Eth and Age Gp
                    if dim == mg.COLDIM_KEY:
                        tree = self.coltree
                    elif dim == mg.ROWDIM_KEY:
                        tree = self.rowtree
                    child_items = lib.GuiLib.get_tree_ctrl_children(
                        tree=tree, item=tree_dims_item)
                    if debug:
                        print(lib.GuiLib.get_sub_tree_items(
                            tree=tree, parent=tree_dims_item))
                    for child_item in child_items:
                        self.add_subtree_to_label_tree(
                            tree_dims_item=child_item,
                            tree_labels_node=subitem_node, dim=dim)

    def add_measures(self, node, measures, *,
            is_coltot=False, force_freq=False):
        sep_measures = measures[:]
        if (force_freq
                and is_coltot
                and mg.ROWPCT_LBL in measures
                and mg.FREQ_LBL not in measures):
            sep_measures.append(mg.FREQ_LBL)
        for measure in sep_measures:
            node.add_child(dimtables.LabelNode(label=measure, measure=measure))

    def add_subtrees_to_col_label_tree(self, tree_labels):
        """
        Add subtrees to col label tree.

        If coltree has no children, (not even the no vars item) do not add one
        here (unlike Live Tables). It will be handled by the calling class
        e.g. by adding measures or raising an exception.
        """
        dim_children = lib.GuiLib.get_tree_ctrl_children(
            tree=self.coltree, item=self.colroot)
        for dim_child_item in dim_children:
            self.add_subtree_to_label_tree(
                tree_dims_item=dim_child_item,
                tree_labels_node=tree_labels.root_node, dim=mg.COLDIM_KEY)
        return tree_labels
