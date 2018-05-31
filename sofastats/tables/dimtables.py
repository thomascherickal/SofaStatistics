import math
import numpy

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats import my_exceptions
from sofastats.stats import core_stats
from sofastats import getdata
from sofastats import output
from sofastats import tree

"""
Don't use dd - this and any other modules we wish to run as a standalone script 
must have dbe, db etc explicitly fed in. If the script is built by the GUI, the
GUI reads dd values and feeds them into the script.
"""

"""
Not to be confused with the dimtree which controls what is shown in the GUI tree 
    control.
Dimension node trees are things like:
    row node = gender
    col nodes = age group > ethnicity
These are what the GUI builds when we configure the table.
Label node trees are what we need to actually display the results.
    E.g. col label nodes
    Age Group 
    1,    2,    3,    5  (4 might be missing if the value hasn't been used)
    Freq, Freq, Freq, Freq
The program runs through the label nodes to actually construct the HTML we will
    be displaying.
The step of determining which cells are actually needed (e.g. will there be a
    value 4 for Age Group) involves running SQL with the appropriate filter.
    Filters are additive as we move towards the end of tree e.g. If we are 
    looking under gender = 1 and eth = 3 what are the value labels we will need
    for nation, for instance?
If there is a global filter to be applied it must be applied everywhere the data
    is queried.
We may also need a TOTAl column or row.
If we have reached the end of the line, we then need to have a cell for each 
    measure e.g. we may need a frequency, a col and a row %.
"""

NOTNULL = u" %s IS NOT NULL " # NOT ISNULL() is not universally supported
# don't use dd - this needs to be runnable as a standalone script - everything 
# has to be explicit


class DimNodeTree(tree.NodeTree):
    """
    A specialist tree for storing dimension nodes.
    Sets the root node up as a DimNode.
    """    
    def __init__(self, measures=None):
        self.root_node = DimNode(label=u"Root", measures=measures)
        self.root_node.level = 0

    def add_child(self, child_node):
        "Update filt_flds to cover all fields in ancestral line"
        #super(tree.NodeTree, self).add_child(child_node)
        tree.NodeTree.add_child(self, child_node)
        child_node.filt_flds = [child_node.fld] # may be None


class LabelNodeTree(tree.NodeTree):
    """
    A specialist tree for storing label nodes.
    Sets the root node up as a LabelNode.
    """    
    def __init__(self):
        self.root_node = LabelNode(label=u"Root")
        self.root_node.level = 0
    
    def get_overall_title(self):
        parts = []
        for child in self.root_node.children: # only want first level
            if child.measure is None and child.label != mg.EMPTY_ROW_LBL:
                parts.append(child.label)
        overall_title = u" And ".join(parts)
        return overall_title

        
class DimNode(tree.Node):
    """
    A specialist node for recording table dimension (row or column)
    data.
    fld is optional for use in columns because sometimes we just want measures
        there e.g. freq, or summary measures such as mean, median etc.
    label - will use fld if no label supplied (and fld available) - e.g.
        fld=gender, fld.title() = Gender.
    labels - a dictionary of labels e.g. {"1": "Male", "2": "Female"}
    measures - e.g. FREQ_KEY
    has_tot - boolean
    sort_order -- mg.SORT_VALUE_KEY etc
    bolnumeric - so can set up filters correctly e.g. gender = "1" or 
        gender = 1 as appropriate
    """
    def __init__(self, fld=None, label="", labels=None, measures=None, 
            has_tot=False, sort_order=mg.SORT_VALUE_KEY, bolnumeric=False):
        self.fld = fld
        self.filt_flds = [] # only built when added as child to another DimNode
        if not label and fld is not None:
            self.label = fld.title()
        else:
            self.label = label
        if not labels:
            self.labels = {}
        else:
            self.labels = labels
        if not measures:
            self.measures = []
        else:
            self.measures = measures
        self.has_tot = has_tot
        self.sort_order = sort_order
        self.bolnumeric = bolnumeric
        tree.Node.__init__(self, dets_dic=None, label=self.label)

    def add_child(self, child_node):
        "Update filt_flds to cover all fields in ancestral line"
        #super(tree.Node, self).add_child(child_node)
        tree.Node.add_child(self, child_node)
        child_node.filt_flds = self.filt_flds + [child_node.fld]

class LabelNode(tree.Node):
    """
    A specialist node for recording table label data for a given dimension 
    (row or column).
    label - the most important data of all - what to display for this node
    filts - a list of all the filter clauses inherited from the ancestral 
        line e.g. gender=1, eth=3
    measure - if this is a terminal node, a single measure must be 
        specified e.g. FREQ
    is_coltot - used for calculations of data values
    """
    
    def __init__(self, label=u"", filts=None, measure=None, is_coltot=False):
        """
        filt_flds is only filled if this is a terminal node.  
        It is filled when the label nodes tree is being built from the dim node 
            tree node (which is where we get it from).
        """
        self.filt_flds = [] 
        if not filts:
            self.filts = []
        else:
            self.filts = filts
        self.measure = measure
        self.is_coltot = is_coltot
        #super(tree.Node, self).__init__(dets_dic=None, label=self.label)
        tree.Node.__init__(self, dets_dic=None, label=label)

    def __str__(self):
        return (self.level*2*u" " + u"Level: " + str(self.level) +
            u"; Label: " + self.label +
            u"; Measure: " + (self.measure if self.measure else u"None") +
            u"; Col Total?: " + (u"Yes" if self.is_coltot else u"No") +
            u"; Child labels: " + u", ".join([x.label for x in self.children]))


class DimTable(object):

    """
    Functionality that applies to both demo and live tables
    """
    def process_hdr_tree(self, tree_col_labels, row_label_cols_n, css_idx):
        """
        Set up col labels into table header.
        """
        debug = False
        CSS_SPACEHOLDER = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_SPACEHOLDER, css_idx)        
        if debug: print(tree_col_labels)
        # includes root so -1, includes title/subtitle row so +1 (share row)
        col_label_rows_n = tree_col_labels.get_depth()
        col_label_rows_lst = [[u"<tr>"] for unused in range(col_label_rows_n)]
        # start off with spaceholder heading cell
        col_label_rows_lst[1].append(u"<th class='%s' rowspan='%s' " %
                            (CSS_SPACEHOLDER, tree_col_labels.get_depth() - 1) +
                            u"colspan='%s'>&nbsp;&nbsp;</th>" %
                            row_label_cols_n)
        col_label_rows_lst = self.col_label_row_bldr(
            node=tree_col_labels.root_node,
            col_label_rows_lst=col_label_rows_lst, 
            col_label_rows_n=col_label_rows_n, 
            row_offset=0, css_idx=css_idx)
        hdr_html = u"\n<thead>"
        for row in col_label_rows_lst:
            # flatten row list
            hdr_html += u"\n" + u"".join(row) + u"</tr>"
        hdr_html += u"\n</thead>"
        if debug: print(tree_col_labels)
        return (tree_col_labels, hdr_html)
      
    def process_row_tree(self, tree_row_labels, css_idx):
        "Turn row label tree into labels"
        debug = False
        if debug: print(tree_row_labels)
        row_label_cols_n = tree_row_labels.get_depth() - 1 # exclude root node
        try:
            row_label_rows_n = len(tree_row_labels.get_terminal_nodes())
        except my_exceptions.NoNodes:
            raise my_exceptions.TooFewValsForDisplay
        row_label_rows_lst = [[u"<tr>"] for unused in range(row_label_rows_n)]
        row_offset_dic = {}
        for i in range(row_label_cols_n):
            row_offset_dic[i]=0
        row_label_rows_lst = self.row_label_row_bldr(
            node=tree_row_labels.root_node,
            row_label_rows_lst=row_label_rows_lst,
            row_label_cols_n=row_label_cols_n,
            row_offset_dic=row_offset_dic, col_offset=0, 
            css_idx=css_idx)
        return (row_label_rows_lst, tree_row_labels, row_label_cols_n)       

    def row_label_row_bldr(self, node, row_label_rows_lst, row_label_cols_n,
            row_offset_dic, col_offset, css_idx):
        """
        Adds cells to the row label rows list as it goes through all nodes.
        NB nodes are not processed level by level but from from parent to child.

        Which row do we add a cell to? It depends entirely on the row offset for
        the level concerned. (NB colspanning doesn't affect the which row a cell
        goes in, or in which order it appears in the row.) So we need a
        row_offset_dic with a key for each level and a value which represents
        the offset (which is updated as we pass through siblings).  If a cell
        for level X needs to span Y rows we add Y to the value for
        row_offset_dic[X].

        As for colspanning, we need to know how many cols have been filled
        already, and how many cols there are to come to the right.

        If there is a gap, colspan the cell to cover it, and increase the
        col_offset being passed down the subtree.

        node - the node we are adding a cell to the table based upon.
        row_label_rows_lst - one row per row in row label section 
        row_label_cols_n - number of cols in row label section        
        row_offset_dic - keeps track of row position for sibling cells
            according to how much its previous siblings have spanned.
            Zero-based index with as many items as the depth of tree 
            (including root).  Index 0 is never used.
        col_offset - amount of colspanning which has occurred prior
            to the cell.  Need to know so terminal nodes all appear
            at same rightwards position regardless of subtree depth.
        Format cells according to whether variable or value.  Even level
            = value, odd level = variable.
        """
        debug = False
        CSS_SUBTABLE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_SUBTABLE, css_idx)
        CSS_FIRST_ROW_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_ROW_VAR, 
            css_idx)
        CSS_TOPLINE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_TOPLINE, css_idx)
        CSS_ROW_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_ROW_VAR, css_idx)
        CSS_ROW_VAL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_ROW_VAL, css_idx)
        if debug: print(node)
        level = node.level
        if level > 0: # skip adding cells for root node itself
            row_offset = level - 1 # e.g. first row level is 0
            row_idx = row_offset_dic[row_offset]
            rowspan_n = len(node.get_terminal_nodes())
            row_offset_dic[row_offset] = row_idx + rowspan_n # for next sibling
            # cell dimensions
            if rowspan_n > 1:
                rowspan = u" rowspan='%s' " % rowspan_n
            else:
                rowspan = u"" 
            cols_filled = level + col_offset
            cols_to_fill = row_label_cols_n - cols_filled
            cols_to_right = node.get_depth() - 1 # exclude self
            gap = cols_to_fill - cols_to_right            
            col_offset += gap
            if gap > 0:
                colspan = u" colspan='%s' " % (1 + gap, )
            else:
                colspan = u""
            # styling
            classes = []
            #classes.append("cols_to_right: {}; cols_filled: {}; row_idx: {}"
            #    .format(cols_to_right, cols_filled, row_idx))
            if cols_to_right % 2 > 0: # odd
                if cols_filled == 1: # first from left
                    classes.append(CSS_FIRST_ROW_VAR)
                    if row_idx > 0: # not first from top
                        classes.append(CSS_TOPLINE) # separate from row above
                        ## already has u"<tr>" as first item
                        row_label_rows_lst[row_idx][0] = (u"<tr class='%s'>"
                            % CSS_SUBTABLE)
                else:
                    classes.append(CSS_ROW_VAR)
            else:
                classes.append(CSS_ROW_VAL)
            cellclass=u"class='%s'" % u" ".join(classes)
            row_label_rows_lst[row_idx].append(u"<td %s %s %s>%s</td>"
                % (cellclass, rowspan, colspan, node.label))
            if debug: print(node.label)
        for child in node.children:
            row_label_rows_lst = self.row_label_row_bldr(
                child, row_label_rows_lst, row_label_cols_n, row_offset_dic,
                col_offset, css_idx)
        # Finish level, set all child levels to start with this one's final 
        # offset.  Otherwise Gender, Gender->Asst a problem (whereas 
        # Gender->Asst, Gender is fine).
        if level > 0: # don't do this on the root
            for i in range(row_offset + 1, row_label_cols_n):
                row_offset_dic[i] = row_offset_dic[row_offset]
        return row_label_rows_lst
    
    def col_label_row_bldr(self, node, col_label_rows_lst, col_label_rows_n, 
                           row_offset, css_idx):
        """
        Adds cells to the column label rows list as it goes through all nodes.
        Add cells to the correct row which means that the first cell
            in a subtree which is shorter than the maximum for the table
            must have an increased rowspan + pass on a row offset to all its
            children.
        node -- the node we are adding a cell to the table based upon.
        col_label_rows_lst -- one row per row in column label header        
        col_label_rows_n -- number of rows in column label header        
        row_offset -- number of rows downwards to be put so terminal nodes
            all appear at same level regardless of subtree depth.
        Add cell for node.
        Any gap between rows in table header below (which we are filling)
            and depth of nodes below (with which we fill the table header)?
        If so, increase rowspan of this cell + increase row offset by 
            appropriate amount so that the subsequent cells are added
            to the correct col label row.
        Format cells according to whether variable or value.  
        For General Tables, odd number of levels below = value, even = variable.
        For Summary Tables, vv.
        """
        CSS_COL_VAL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_COL_VAL, css_idx)
        CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, 
                                                      css_idx)
        CSS_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_COL_VAR, css_idx)
        CSS_MEASURE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_MEASURE, css_idx)
        rows_filled = node.level + 1 + row_offset
        rows_to_fill = col_label_rows_n - rows_filled
        rows_below = node.get_depth() - 1 # exclude self
        gap = rows_to_fill - rows_below
        # styling for this node according to level in hierarchy
        if self.has_col_measures:
            if self.var_summarised:
                # top row coloured, rest not
                if rows_below == 0:
                    cellclass=u"class='%s'" % CSS_MEASURE
                elif rows_below == 1:
                    cellclass=u"class='%s'" % CSS_FIRST_COL_VAR
            else:
                if rows_below == 0:
                    cellclass=u"class='%s'" % CSS_MEASURE
                elif rows_below % 2 > 0: # odd
                    cellclass=u"class='%s'" % CSS_COL_VAL
                else:
                    if rows_filled == 2:
                        cellclass=u"class='%s'" % CSS_FIRST_COL_VAR
                    else:
                        cellclass=u"class='%s'" % CSS_COL_VAR
        else:
            if rows_below % 2 == 0: # even
                cellclass=u"class='%s'" % CSS_COL_VAL
            else:
                if rows_filled == 2:
                    cellclass=u"class='%s'" % CSS_FIRST_COL_VAR
                else:
                    cellclass=u"class='%s'" % CSS_COL_VAR
        # cell dimensions
        if gap > 0:
            rowspan = u" rowspan='%s' " % (1 + gap,)
        else:
            rowspan = u""
        colspan_n = len(node.get_terminal_nodes())
        if colspan_n > 1:
            colspan = u" colspan='%s' " % colspan_n
        else:
            colspan = u""
        if node.level > 0: # skip root (we use that row for the title
            col_label_rows_lst[rows_filled - 1].append(\
                u"<th %s %s %s>%s</th>" % (cellclass, rowspan, colspan, 
                                           node.label))
        row_offset += gap
        for child in node.children:
            col_label_rows_lst = self.col_label_row_bldr(child, 
                                          col_label_rows_lst, col_label_rows_n, 
                                          row_offset, css_idx)
        return col_label_rows_lst
    
    
class LiveTable(DimTable):
    """
    A Table with the ability to nest rows and columns, add totals to any 
    node, have multiple measures per terminal node e.g. freq, rowpct, 
    and colpct, etc etc.
    """
    
    def __init__(self, titles, subtitles, tab_type, dbe, tbl, tbl_filt, cur, 
                 flds, tree_rows, tree_cols, show_perc=True):
        """
        cur - must return tuples, not dictionaries
        """
        self.debug = False
        self.prepared = False
        self.prep_css_idx = None
        self.titles = titles
        self.subtitles = subtitles
        self.tab_type = tab_type
        rpt_config = mg.RPT_CONFIG[self.tab_type]
        self.default_measure = rpt_config[mg.DEFAULT_MEASURE_KEY]
        self.dbe = dbe
        self.tbl = tbl
        self.tbl_filt = tbl_filt
        self.where_tbl_filt, self.and_tbl_filt = lib.FiltLib.get_tbl_filts(
            tbl_filt)
        (self.if_clause, unused, unused, 
         self.quote_obj, unused, 
         self.placeholder, self.get_summable, 
         self.gte_not_equals, 
         unused) = getdata.get_dbe_syntax_elements(self.dbe)
        self.cur = cur
        self.flds = flds
        self.tree_rows = tree_rows
        self.tree_cols = tree_cols
        self.show_perc = show_perc
    
    def get_data_cell_n(self, tree_col_labels, tree_row_labels):
        col_term_nodes = tree_col_labels.get_terminal_nodes()
        row_term_nodes = tree_row_labels.get_terminal_nodes()
        data_cell_n = len(row_term_nodes) * len(col_term_nodes)
        return data_cell_n
    
    def prep_table(self, css_idx):
        """
        Prepare table setup information in advance of generation of final html.
        Useful if need to know total rows and cols to work out cells so can see 
            if too many (and abort).
        Required if using get_cell_n_ok().
        """
        (self.row_label_rows_lst, self.tree_row_labels, 
                row_label_cols_n) = self.get_row_dets(css_idx)
        (self.tree_col_labels, 
                self.hdr_html) = self.get_hdr_dets(row_label_cols_n, css_idx)
        self.prep_css_idx = css_idx
        self.prepared = True
    
    def get_cell_n_ok(self, max_cells=5000):
        """
        Returns False if too many cells to proceed (according to max_cells).
        Used to determine whether to proceed with table or not.
        """
        try:
            data_cell_n = self.get_data_cell_n(self.tree_col_labels, 
                                               self.tree_row_labels)
        except AttributeError:
            raise Exception(u"Must run prep_table() before get_cell_n_ok().")
        return max_cells >= data_cell_n
    
    def get_html(self, css_idx, dp, page_break_after=False):
        """
        Get HTML for table.
        """
        html = []
        title_dets_html = output.get_title_dets_html(self.titles,
            self.subtitles, css_idx, istable=True)
        html.append(title_dets_html)
        html.append(u"%s<table cellspacing='0'>\n" % mg.REPORT_TABLE_START) # IE6 no support CSS borderspacing
        if not (self.prepared and self.prep_css_idx == css_idx):
            # need to get fresh - otherwise, can skip this step. Did it in prep.
            (self.row_label_rows_lst, 
             self.tree_row_labels, 
             row_label_cols_n) = self.get_row_dets(css_idx)
            (self.tree_col_labels, 
             self.hdr_html) = self.get_hdr_dets(row_label_cols_n, css_idx)
        row_label_rows_lst = self.get_body_html_rows(self.row_label_rows_lst,
            self.tree_row_labels, self.tree_col_labels, css_idx, dp)
        body_html = u"\n\n<tbody>"
        for row in row_label_rows_lst:
            # flatten row list
            body_html += u"\n" + u"".join(row) + u"</tr>"
        body_html += u"\n</tbody>"
        html.append(self.hdr_html)
        html.append(body_html)
        html.append(u"\n</table>")
        try:
            if self.warnings:
                html.append(u"<p><b>%s</b><p>" % _(u"Warnings"))
                html.extend(self.warnings)
        except AttributeError:
            pass
        html.append(u"%s" % mg.REPORT_TABLE_END)
        parts = []
        overall_row_title = self.tree_row_labels.get_overall_title()
        overall_col_title = self.tree_col_labels.get_overall_title()
        if self.tab_type in [mg.FREQS, mg.CROSSTAB]:
            if overall_row_title:
                parts.append(overall_row_title)
            if overall_col_title:
                parts.append(overall_col_title)
            overall_title = u" By ".join(parts)
        elif self.tab_type == mg.ROW_STATS:
            if overall_col_title:
                parts.append(overall_col_title)
            if overall_row_title:
                parts.append(overall_row_title)
            overall_title = u" Stats By ".join(parts)
        title = (self.titles[0] if self.titles else overall_title)
        output.append_divider(html, title, indiv_title=u"", 
            item_type=mg.TAB_TYPE2LBL[self.tab_type])
        return u"\n".join(html)

    def get_hdr_dets(self, row_label_cols_n, css_idx):
        """
        Return tree_col_labels and the table header HTML.
        For HTML provide everything from <thead> to </thead>.
        If no column variables, make a special column node.
        """
        tree_col_labels = LabelNodeTree()
        tree_col_labels = self.add_subtrees_to_col_label_tree(tree_col_labels)
        if tree_col_labels.get_depth() == 1:
            raise Exception(u"There must always be a column item even if only "
                            u"the col no vars item")
        return self.process_hdr_tree(tree_col_labels, row_label_cols_n, css_idx)
        
    def get_body_html_rows(self, row_label_rows_lst, tree_row_labels,
                           tree_col_labels, css_idx, dp):
        """
        Make table body rows based on contents of row_label_rows_lst:
        e.g. [["<tr>", "<td class='firstrowvar' rowspan='8'>Gender</td>" ...],
        ...]
        It already contains row label data - we need to add the data cells 
        into the appropriate row list within row_label_rows_lst before
        concatenating and appending "</tr>".
        """
        debug = False
        try:
            col_term_nodes = tree_col_labels.get_terminal_nodes()
            row_term_nodes = tree_row_labels.get_terminal_nodes()
            col_filters_lst = [x.filts for x in col_term_nodes]
            col_filt_flds_lst = [x.filt_flds for x in col_term_nodes]
            col_tots_lst = [x.is_coltot for x in col_term_nodes]
            col_measures_lst = [x.measure for x in col_term_nodes]
            row_filters_lst = [x.filts for x in row_term_nodes]
            if debug: 
                print(row_filters_lst)
                print(col_term_nodes)
            row_filt_flds_lst = [x.filt_flds for x in row_term_nodes]
            data_cells_n = len(row_term_nodes) * len(col_term_nodes)
            if self.debug or debug:
                print(u"%s data cells in table" % data_cells_n)
            row_label_rows_lst = self.get_row_labels_row_lst(row_filters_lst, 
                row_filt_flds_lst, col_measures_lst, col_filters_lst,
                col_tots_lst, col_filt_flds_lst, row_label_rows_lst,
                data_cells_n, col_term_nodes, css_idx, dp)
        except Exception as e:
            row_label_rows_lst = [u"<td>Problem getting table output: "
                u"Orig error: %s</td>" % b.ue(e)]
        return row_label_rows_lst
    
    def get_row_dets(self, css_idx):
        """
        Return row_label_rows_lst - need combination of row and col filters
            to add the data cells to the table body rows.
        tree_row_labels - we collect row filters from this.
        row_label_cols_n - needed to set up header (need to span the 
            row labels).
        """
        tree_row_labels = LabelNodeTree()
        for child in self.tree_rows.root_node.children:
            self.add_subtree_to_label_tree(tree_dims_node=child,
                tree_labels_node=tree_row_labels.root_node,
                dim=mg.ROWDIM_KEY, oth_dim_root=self.tree_cols.root_node)
        if tree_row_labels.get_depth() == 1 and self.row_var_optional:
            tree_row_labels.add_child(LabelNode(label=mg.EMPTY_ROW_LBL))
        return self.process_row_tree(tree_row_labels, css_idx)
    
    def add_subtrees_to_col_label_tree(self, tree_col_labels):
        """
        Add subtrees to column label tree.
        If coltree has no children, must add a subtree underneath.
        """
        debug = False
        if debug: print(self.tree_cols)
        if self.tree_cols.root_node.children:
            for child in self.tree_cols.root_node.children:
                self.add_subtree_to_label_tree(tree_dims_node=child, 
                                    tree_labels_node=tree_col_labels.root_node,
                                    dim=mg.COLDIM_KEY, 
                                    oth_dim_root=self.tree_rows.root_node)
        else:
            self.add_subtree_to_label_tree(
                                    tree_dims_node=self.tree_cols.root_node, 
                                    tree_labels_node=tree_col_labels.root_node,
                                    dim=mg.COLDIM_KEY, 
                                    oth_dim_root=self.tree_rows.root_node)
        return tree_col_labels
          
    def add_subtree_to_label_tree(self, tree_dims_node, tree_labels_node, 
                                     dim, oth_dim_root):
        """
        Based on information from the variable dim node, add a subtree
        to the node supplied from the labels tree (if appropriate).
        dim node: fld, label, labels, measures, has_tot, sort_order, bolnumeric.
        label node: label, filts, measure, is_coltot.
        """
        debug = False
        has_fld = tree_dims_node.fld # None or a string        
        filt_flds = tree_dims_node.filt_flds
        if dim == mg.ROWDIM_KEY:
            if not has_fld:
                raise Exception(u"All row nodes must have a variable field "
                                u"specified")
            self.add_subtree_if_vals(tree_dims_node, tree_labels_node, 
                                     oth_dim_root, dim, filt_flds)
        elif dim == mg.COLDIM_KEY:
            if has_fld:
                if self.var_summarised:
                    if debug: print(tree_dims_node)
                    var_label = tree_dims_node.label
                    var_node2add = LabelNode(label=var_label)
                    new_var_node = tree_labels_node.add_child(var_node2add)
                    # add measure label nodes under var
                    self.add_measures(new_var_node, tree_dims_node.measures, 
                        is_coltot=False, filt_flds=filt_flds, filts=[])
                else:
                    self.add_subtree_if_vals(tree_dims_node, tree_labels_node, 
                                             oth_dim_root, dim, filt_flds)
            else:
                if self.has_col_measures:
                    self.add_col_measures_subtree_if_no_fld(tree_dims_node, 
                                                            tree_labels_node)                
    
    def get_vals_filt_clause(self, tree_dims_node, tree_labels_node, 
                             oth_dim_root):
        """
        To display a cell, we must know that there will be at least one 
            descendant cell to show underneath it. We do this by filtering the 
            raw data by the appropriate row and column filters.  If any records 
            remain, we can show the cell. As to showing the values beneath the 
            variable, we should work from the same filtered dataset. For the 
            cell, we only look at variable subtrees under the cell and all 
            variable subtrees under the root of the other dimension.        
        E.g. cols:
                          gender
           eth                            agegp
                                nation            religion
                                region
                                
        and rows:
                year                    year
                month
       
        Should we show gender? E.g.
        SELECT gender
        FROM datasource
        WHERE NOT ISNULL(gender)
            AND ( 
            (NOT ISNULL(agegp) AND NOT ISNULL(nation) AND NOT ISNULL(region))
                OR
            (NOT ISNULL(agegp) AND NOT ISNULL(religion))
            )
            AND (
            (NOT ISNULL(year) AND NOT ISNULL(month)) 
                OR
            (NOT ISNULL(year))
            )
        GROUP BY gender                
        1) parent filters must all be true (none in example above)
        2) self field cannot be null
        3) for each subtree, no fields in subtree can be null
        4) In the other dimension, for each subtree, 
        none of the fields can have a Null value.
        """
        # 1) e.g. []
        if tree_labels_node.filts:
            parent_filts = u" AND ".join(tree_labels_node.filts)
        else:
            parent_filts = u""
        # 2) e.g. " NOT ISNULL(gender) "
        self_filt = NOTNULL % self.quote_obj(tree_dims_node.fld)
        # 3) Identify fields already filtered in 1) or 2) already
        #we will remove them from field lists of subtree term nodes
        flds_done = len(tree_dims_node.filt_flds)
        #get subtree term node field lists (with already done fields sliced out)
        #e.g. gender>eth, gender>agegp>nation>region, agegp>religion
        # becomes [[eth],[agegp,nation,region],[agegp,religion]]
        subtree_term_nodes = []
        for child in tree_dims_node.children:            
            subtree_term_nodes += child.get_terminal_nodes()
        if subtree_term_nodes:
            subtree_filt_fld_lsts = [x.filt_flds[flds_done:] for x
                                     in subtree_term_nodes]
            dim_clause = self.tree_fld_lsts_to_clause(
                                    tree_fld_lsts=subtree_filt_fld_lsts)
        else:
            dim_clause = ""
        # 4) get all subtree term node field lists (no slicing this time)
        #  e.g. year>month, year becomes [[year,month],[year]]
        oth_subtree_term_nodes = []
        for child in oth_dim_root.children:
            oth_subtree_term_nodes += child.get_terminal_nodes()
        if oth_subtree_term_nodes:
            # NB the other dimension could be fieldless e.g. we are a row dim 
            # and the oth dim has col measures and no field set
            oth_subtree_filt_fld_lsts = [x.filt_flds for x
                                         in oth_subtree_term_nodes
                                         if x.filt_flds != [None]]
            oth_dim_clause = self.tree_fld_lsts_to_clause(
                                    tree_fld_lsts=oth_subtree_filt_fld_lsts)
        else:
            oth_dim_clause = u""
        # assemble
        main_clauses = []
        for clause in [parent_filts, self_filt, dim_clause, 
                       oth_dim_clause]:
            if clause:
                main_clauses.append(clause)
        final_filt_clause = u" AND ".join(main_clauses)
        return final_filt_clause

    def get_vals_sql(self, fld, tree_dims_node, tree_labels_node, oth_dim_root):
        """
        Return vals and freqs for a given field with a given set of filtering.
        """
        debug = False
        final_filt_clause = self.get_vals_filt_clause(tree_dims_node, 
                                                tree_labels_node, oth_dim_root)
        SQL_get_vals = (u"SELECT %(fld)s, COUNT(*) "
                        u"FROM %(tbl)s "
                        u"WHERE %(filt_clause)s %(and_tbl_flt)s "
                        u"GROUP BY %(fld)s") % {"fld": self.quote_obj(fld), 
                               "tbl": getdata.tblname_qtr(self.dbe, self.tbl), 
                               "filt_clause": final_filt_clause,
                               "and_tbl_flt": self.and_tbl_filt}
        if debug: print(SQL_get_vals)
        return SQL_get_vals
            
    def get_sorted_val_freq_label_lst(self, all_vals, tree_dims_node):
        """
        Get vals, their freq (across all the other dimension), and their label.
        [(val, freq, val_label), ...] sorted appropriately.

        Need to handle lists of strings, integers, floats etc. If all the floats
        are integers then don't round them even if to 0dp - converts to floats.
        """
        debug = False
        val_freq_label_lst = []
        xs_maybe_used_as_lbls = set([val for val, val_freq in all_vals])
        dp = lib.OutputLib.get_best_dp(xs_maybe_used_as_lbls)
        for (x_val, val_freq) in all_vals:
            xval4lbl = lib.OutputLib.get_best_x_lbl(x_val, dp)    
            default_val_label = lib.UniLib.any2unicode(xval4lbl)
            val_label = tree_dims_node.labels.get(x_val, default_val_label)
            val_tup = (x_val, val_freq, val_label)
            if debug: print(val_tup)
            val_freq_label_lst.append(val_tup)
        lib.sort_value_lbls(tree_dims_node.sort_order, val_freq_label_lst, 
            idx_measure=1, idx_lbl=2)
        # A total cell should be added, or not, after this stage.
        return val_freq_label_lst

    def add_subtree_if_vals(self, tree_dims_node, tree_labels_node, 
                            oth_dim_root, dim, filt_flds):
        """
        If the variable node has values to display (i.e. must have a field, not 
            be a summary table row, and must find values in data), the subtree 
            will have two initial levels:
            1) a node for the variable itself (storing labels in its dets_dic),
            2) a set of values nodes - one for each value plus one for the 
            total (if appropriate).
        Then we need to follow the subtree down a level below each 
            of the values nodes (assuming the tree_dims_node has any children).       
        To display a cell, we must know that there will be at least one
            descendant cell to show underneath it.              
        We do this by filtering the raw data by the appropriate row and column 
            filters.  If any records remain, we can show the cell.
        """
        TOT = u"_tot_"
        debug = False
        if debug:
            print("running add_subtree_if_vals") 
            print(tree_dims_node)
        fld = tree_dims_node.fld
        SQL_get_vals = self.get_vals_sql(fld, tree_dims_node, tree_labels_node, 
                                         oth_dim_root)
        if debug: print(SQL_get_vals)
        self.cur.execute(SQL_get_vals)
        all_vals = self.cur.fetchall()
        # some of these values might not be broken text
        
        if debug: print(all_vals)
        if not all_vals:
            return # do not add subtree - no values
        # add level 1 to data tree - the var
        node_lev1 = tree_labels_node.add_child(LabelNode(
                                                    label=tree_dims_node.label))
        val_freq_label_lst = self.get_sorted_val_freq_label_lst(all_vals,
                                                                tree_dims_node)
        force_freq = True # could get from GUI (must be exposed to scripting)
            # but better to KISS
        if tree_dims_node.has_tot:
            val_freq_label_lst.append((TOT, 0, u"TOTAL"))
        terminal_var = not tree_dims_node.children
        if terminal_var:
            var_measures = tree_dims_node.measures
            if not var_measures: # they unticked everything!
                var_measures = [mg.FREQ_KEY]
        for val, unused, val_label in val_freq_label_lst:
            # e.g. male, female
            # add level 2 to the data tree - the value nodes (plus total?); 
            # pass on and extend filtering from higher level in data tree
            val_node_filts = tree_labels_node.filts[:]
            is_tot = (val == TOT)
            if is_tot:
                val_node_filts.append(NOTNULL % self.quote_obj(fld))
            else:
                clause = getdata.make_fld_val_clause(self.dbe, self.flds, fld, 
                                                     val, mg.GTE_EQUALS)
                if debug: print(clause)
                val_node_filts.append(clause)
            is_coltot=(is_tot and dim == mg.COLDIM_KEY)
            val_node = node_lev1.add_child(LabelNode(label=val_label,
                                                     filts=val_node_filts))
            # if node has children, send through again to add further subtree
            if terminal_var: # a terminal node - add measures
                # only gen and sum table cols can have measures
                if dim == mg.COLDIM_KEY and self.has_col_measures:
                    self.add_measures(label_node=val_node, 
                                    measures=var_measures, is_coltot=is_coltot, 
                                    filt_flds=filt_flds, filts=val_node_filts,
                                    force_freq=force_freq) 
                else:
                    val_node.filt_flds = filt_flds
            else:
                for child in tree_dims_node.children:
                    self.add_subtree_to_label_tree(tree_dims_node=child, 
                                           tree_labels_node=val_node, dim=dim, 
                                           oth_dim_root=oth_dim_root)
    
    def add_col_measures_subtree_if_no_fld(self, tree_dims_node, 
                                           tree_labels_node):
        """
        Add subtree in case where no field.
        First check that it is OK to add.
        """
        if tree_dims_node.level > 1:
            raise Exception(u"If the col field has not been set, a node "
                            u"without a field specified must be immediately "
                            u"under the root node")
        self.add_measures(label_node=tree_labels_node, 
                          measures=tree_dims_node.measures, 
                          is_coltot=False, filt_flds=[], filts=[])

    def add_measures(self, label_node, measures, is_coltot, filt_flds, 
                     filts, force_freq=False):
        """
        Add measure label nodes under label node.
        
        If a column total with rowpct, and frequencies not selected, force it in 
        anyway. Shouldn't have pcts without a sense of total N.
        """
        debug = False
        if debug: print("is_coltot: %s; measures: %s" % (is_coltot, measures))
        sep_measures = measures[:]
        if (force_freq and is_coltot and mg.ROWPCT_KEY in measures
                and mg.FREQ_KEY not in measures):
            sep_measures.append(mg.FREQ_KEY)
        for measure in sep_measures:
            label = mg.MEASURE_KEY2LBL[measure]
            measure_node = LabelNode(label, filts, measure, is_coltot)
            measure_node.filt_flds = filt_flds
            label_node.add_child(measure_node)
    
    def tree_fld_lsts_to_clause(self, tree_fld_lsts):
        """
        [[eth],[agegp,nation,region],[agegp,religion]]
        becomes
        "((NOT ISNULL(eth)) 
            OR (NOT ISNULL(agegp) AND NOT ISNULL(nation) AND NOT ISNULL(region)) 
            OR (NOT ISNULL(agegp) AND NOT ISNULL(religion)))"
        """
        if not tree_fld_lsts:
            return None
        else:
            subtree_clauses_lst = [] #each subtree needs a parenthesised clause
            #e.g. "( NOT ISNULL(agegp) AND NOT ISNULL(religion) )"
            for subtree_lst in tree_fld_lsts:
                subtree_clauses = [NOTNULL % self.quote_obj(fld) for fld
                                   in subtree_lst]
                #e.g. " NOT ISNULL(agegp) ", " NOT ISNULL(religion) "
                #use AND within subtrees because every field must be filled
                subtree_clauses_lst.append(u"(" +
                                           u" AND ".join(subtree_clauses) +
                                           u")")
            #join subtree clauses with OR because a value in any is enough to
            #  retain label 
            clause = u"(" + u" OR ".join(subtree_clauses_lst) + u")"
            #e.g. see method documentation at top
            return clause

        
class GenTable(LiveTable):
    "A general table (not a summary table)"

    has_col_measures = True
    var_summarised = False
    row_var_optional = False
    
    def get_data_sql(self, SQL_table_select_clauses_lst):
        """
        Get SQL for data values e.g. percentages, frequencies etc.
        """
        debug = False
        SQL_select_results = (u"SELECT " +
                 u", ".join(SQL_table_select_clauses_lst) +
                 u" FROM %s" % getdata.tblname_qtr(self.dbe, self.tbl) +
                 self.where_tbl_filt)
        if debug: print(SQL_select_results)
        return SQL_select_results
    
    def get_dim_filts_4_oth_dim_tot_lst(self, dim_filter, dim_filt_flds):
        """
        The value of a cell depends on two things: 1) the type of measure e.g. 
            freq, and 2) the filters which apply to it.
        If a cell is in the col branch Gender=1 and AgeGp=3 then, except for a 
            TOTAL col, the values we use will come from all records in the 
            dataset which have Gender=1 and AgeGp=3. For the TOTAL, however, we
            will use all values where Gender=1 and AgeGp is not missing.  This
            method supplies the filter we use for totals.
        """
        if not dim_filt_flds:
            return []
        last_dim_filter = NOTNULL % self.quote_obj(dim_filt_flds[-1])
        # Replace final dim filter with a simple requirement that it is 
        # non-missing.
        tot4dim_filt_lst = dim_filter[:]
        tot4dim_filt_lst[-1] = last_dim_filter
        return tot4dim_filt_lst
    
    def get_row_labels_row_lst(self, row_filters_lst, row_filt_flds_lst, 
            col_measures_lst, col_filters_lst, col_tots_lst, col_filt_flds_lst, 
            row_label_rows_lst, data_cells_n, col_term_nodes, css_idx, dp):
        """
        Get list of row data. Each row in the list is represented by a row of
        strings to concatenate, one per data point.

        Build lists of data item HTML (data_item_presn_lst) and data item values
        (results) ready to combine.

        data_item_presn_lst is a list of tuples with left and right HTML
        wrappers for data ("<td class='%s'>" % cellclass, "</td>").

        As each data point is processed, a tuple is added to the list.

        results is built once per batch of data points for database efficiency
        reasons. Each call returns multiple values.
        """
        debug = False
        CSS_FIRST_DATACELL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_DATACELL,
            css_idx)
        CSS_DATACELL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_DATACELL, css_idx)
        i=0
        data_item_presn_lst = []
        results = []
        SQL_table_select_clauses_lst = []
        max_select_vars = 1 if debug else 50 # same speed from 30-100 but
            # twice as slow if much smaller or larger.
        for (row_filter, 
             row_filt_flds) in zip(row_filters_lst, row_filt_flds_lst):
            row_filts_tot4col_lst = self.get_dim_filts_4_oth_dim_tot_lst(
                row_filter, row_filt_flds)
            first = True # styling
            col_zipped = zip(col_measures_lst, col_filters_lst, col_tots_lst, 
                col_filt_flds_lst)
            for (colmeasure, col_filter, coltot, col_filt_flds) in col_zipped:
                col_filts_tot4row_lst = self.get_dim_filts_4_oth_dim_tot_lst(
                    col_filter, col_filt_flds)    
                # styling
                if first:
                    cellclass = CSS_FIRST_DATACELL
                    first = False
                else:
                    cellclass = CSS_DATACELL
                # build data row list
                data_item_presn_lst.append((u"<td class='%s'>" % cellclass, 
                    mg.MEASURE_KEY2LBL[colmeasure], u"</td>"))
                # build SQL clauses for next SQL query
                clause = self.get_func_clause(measure=colmeasure,
                    row_filters_lst=row_filter, 
                    col_filts_tot4row_lst=col_filts_tot4row_lst,
                    col_filters_lst=col_filter, 
                    row_filts_tot4col_lst=row_filts_tot4col_lst,
                    is_coltot=coltot)
                SQL_table_select_clauses_lst.append(clause)
                # process SQL queries when number of clauses reaches threshold
                if (len(SQL_table_select_clauses_lst) == max_select_vars
                        or i == data_cells_n - 1):
                    SQL_select_results = self.get_data_sql(
                        SQL_table_select_clauses_lst)
                    if debug: print(SQL_select_results)
                    self.cur.execute(SQL_select_results)
                    is_freq = (colmeasure == mg.FREQ_KEY)
                    results.extend(self.cur.fetchone())
                    SQL_table_select_clauses_lst = []
                i=i+1
                if debug:
                    print(results)
        i=0
        # using the data item HTML tuples and the results data, 
        # build the body row html
        for row in row_label_rows_lst:
            for unused in col_term_nodes:
                output_type = mg.MEASURE_LBL2KEY[data_item_presn_lst[i][1]]
                dp_tpl = u"%.{}f".format(dp)
                val = results[i]
                is_freq = (output_type == mg.FREQ_KEY)
                num2use = val if is_freq else dp_tpl % val  ## show integers for freqs (that's what the process in get_func_clause will have done by SUMming 1 and 0s. We don't alter that.
                num2display = lib.OutputLib.get_num2display(num=num2use,
                    output_type=output_type, inc_perc=self.show_perc)
                row.append(data_item_presn_lst[i][0]
                    + num2display + data_item_presn_lst[i][2])
                i=i+1
        return row_label_rows_lst
    
    def get_func_clause(self, measure, row_filters_lst, col_filts_tot4row_lst,
            col_filters_lst, row_filts_tot4col_lst, is_coltot):
        """
        Each terminal branch of a row or column tree has the filtering from all
        ancestors e.g. If Gender > AgeGp in row, the filtering to apply might be
        Gender=1 and AgeGp=3.  For the total for AgeGp we would have Gender=1
        and AgeGp not missing.

        measure -- e.g. FREQ_KEY
        row_filters_lst -- data in the original dataset will be counted if it
            meets the filter criteria.  ) if not meeting criteria, 1 if it does.
        col_filts_tot4row_lst -- as above but the final col is only required to
            be non-missing.  Used to calculate total for row i.e. across the
            cols e.g. for gender=1 and AgeGp=3 but all non-missing Nations.
        col_filters_lst -- as for rows.
        row_filts_tot4col_lst -- as for rows.
        is_coltot -- boolean

        NB avoid perils of integer division (SQLite, MS SQL Server etc) 5/2 = 2!
        """
        debug = False
        # To get freq, evaluate matching values to 1 (otherwise 0) then sum
        # With most dbs, boolean returns 1 for True and 0 for False
        # FREQ - all row and col filters apply
        sum4freq = self.get_summable(u" AND ".join(row_filters_lst
            + col_filters_lst))
        freq = u"SUM(%s)" % sum4freq
        # TOTAL FOR ROW - i.e. total across final cols
        # all row filts and col filts for row tot apply
        tot4row_summable = self.get_summable(u" AND ".join(row_filters_lst
             + col_filts_tot4row_lst))
        tot4row = u"SUM(%s)" % tot4row_summable
        # TOTAL FOR COL - i.e. total across final rows
        # all col filts and row tot filts apply
        tot4col_summable = self.get_summable(u" AND ".join(row_filts_tot4col_lst
            + col_filters_lst))
        tot4col = u"SUM(%s)" % tot4col_summable
        # TOTAL FOR ALL - i.e. total across final rows and cols
        sum4allsummable = self.get_summable(u" AND ".join(row_filts_tot4col_lst
            + col_filts_tot4row_lst))
        tot4all = u"SUM(%s)" % sum4allsummable
        if debug:
            print("Freq: %s" % freq)
            print("Total for row: %s" % tot4row)
            print("Total for col: %s" % tot4col)
            print("Total for all: %s" % tot4all)
        # NB measures are off the terminal columns
        if measure == mg.FREQ_KEY:
            func_clause = freq if not is_coltot else tot4row
        elif measure == mg.COLPCT_KEY:
            if not is_coltot:
                num = freq
                den = tot4col
            else:
                num = tot4row
                den = tot4all
            perc = u"100.0*(%s)/(%s)" % (num, den) # not integer div
            template = self.if_clause % (NOTNULL % perc, perc, 0)
            if debug: print(template)
            func_clause = template
        elif measure == mg.ROWPCT_KEY:
            if not is_coltot:
                perc = u"100.0*(%s)/(%s)" % (freq, tot4row) # not integer div
                template = self.if_clause % (NOTNULL % perc, perc, 0)
                if debug: 
                    print(freq, tot4row)
                    print(perc)
                func_clause = template
            else:
                func_clause = u"100"
        else:
            raise Exception(u"Measure %s not available" % measure)
        if debug: print(func_clause)
        return func_clause
        
                    
class SummTable(LiveTable):
    "A summary table - e.g. Median, Mean etc"
    
    has_col_measures = True
    var_summarised = True
    row_var_optional = True
    
    def __init__(self, titles, subtitles, tab_type, dbe, tbl, tbl_filt, cur, 
            flds, tree_rows, tree_cols, show_perc=True):
        LiveTable.__init__(self, titles, subtitles, tab_type, dbe, tbl, 
            tbl_filt, cur, flds, tree_rows, tree_cols, show_perc=True)
        self.warnings = []
    
    def get_row_labels_row_lst(self, row_filters_lst, row_filt_flds_lst, 
            col_measures_lst, col_filters_lst, col_tots_lst, col_filt_flds_lst, 
            row_label_rows_lst, data_cells_n, col_term_nodes, css_idx, dp):
        """
        Get list of row data. Each row in the list is represented by a row of 
        strings to concatenate, one per data point.
        
        Get data values one at a time (no batches unlike Gen Tables) and add to 
        html chunks.
        
        Example data if two col variables - mean, median, mean, median
        """
        CSS_FIRST_DATACELL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_DATACELL,
            css_idx)
        CSS_DATACELL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_DATACELL, css_idx)
        """
        col_measures_lst -- 
        """
        debug = False
        if debug: print(col_measures_lst)
        data_item_lst = []
        for row_filter, unused in zip(row_filters_lst, 
                row_filt_flds_lst):
            first = True # styling
            col_zipped = zip(col_measures_lst, col_filters_lst, 
                col_filt_flds_lst)
            for (colmeasure, unused, col_filt_flds) in col_zipped:
                col_fld = col_filt_flds[0]
                # styling
                if first:
                    cellclass = CSS_FIRST_DATACELL
                    first = False
                else:
                    cellclass = CSS_DATACELL
                data_val, msg = self.get_data_val(colmeasure, col_fld, 
                    row_filter, dp)
                if msg:
                    self.warnings.append(u"<p>%s</p>" % msg)
                data_item_lst.append(u"<td class='%s'>%s</td>" %
                    (cellclass, data_val))
        i=0
        for row in row_label_rows_lst:
            for unused in col_term_nodes:
                row.append(data_item_lst[i])
                i=i+1
        return row_label_rows_lst
    
    def _get_non_num_val(self, SQL_get_vals):
        """
        Returns first non-numeric value found (ignoring None).
        Otherwise, returns None.
        """
        debug = False
        self.cur.execute(SQL_get_vals)
        val = None
        while True:
            try:
                val = self.cur.fetchone()[0]
            except Exception:
                return None
            if debug: print(val)
            if val is not None and not lib.TypeLib.is_basic_num(val):
                break
        return val

    ## Only separated those out where handling NaN
    def _lq(self, data, SQL_get_vals, col_fld, dp2_tpl):
        msg = None
        try:
            lq, unused = core_stats.get_quartiles(data)
            if math.isnan(lq):
                data_val = mg.NO_CALC_LBL
            else:
                data_val = dp2_tpl % lq
        except Exception:
            bad_val = self._get_non_num_val(SQL_get_vals)
            if bad_val is not None:
                msg = (u"Unable to calculate lower quartile "
                    u"for %s. " % col_fld +
                    u"The field contains at least one non-numeric " +
                    u"value: \"%s\"" % bad_val)
            data_val = mg.NO_CALC_LBL
        return data_val, msg

    def _uq(self, data, SQL_get_vals, col_fld, dp2_tpl):
        msg = None
        try:
            unused, uq = core_stats.get_quartiles(data)
            if math.isnan(uq):
                data_val = mg.NO_CALC_LBL
            else:
                data_val = dp2_tpl % uq
        except Exception:
            bad_val = self._get_non_num_val(SQL_get_vals)
            if bad_val is not None:
                msg = (u"Unable to calculate upper quartile "
                    u"for %s. " % col_fld +
                    u"The field contains at least one non-numeric " +
                    u"value: \"%s\"" % bad_val)
            data_val = mg.NO_CALC_LBL
        return data_val, msg

    def _iq_range(self, data, SQL_get_vals, col_fld, dp2_tpl):
        msg = None
        try:
            lq, uq = core_stats.get_quartiles(data)
            if math.isnan(lq) or math.isnan(uq):
                data_val = mg.NO_CALC_LBL
            else:
                data_val = dp2_tpl % (uq-lq, )
        except Exception:
            bad_val = self._get_non_num_val(SQL_get_vals)
            if bad_val is not None:
                msg = (u"Unable to calculate Inter-Quartile Range "
                    u"for %s. " % col_fld +
                    u"The field contains at least one non-numeric " +
                    u"value: \"%s\"" % bad_val)
            data_val = mg.NO_CALC_LBL
        return data_val, msg

    def _std_dev(self, data, SQL_get_vals, col_fld, dp2_tpl):
        msg = None
        try:
            raw = numpy.std(data, ddof=1)  ## use ddof=1 for sample sd
            if math.isnan(raw):
                data_val = mg.NO_CALC_LBL
            else:
                data_val = dp2_tpl % raw
        except Exception:
            bad_val = self._get_non_num_val(SQL_get_vals)
            if bad_val is not None:
                msg = (u"Unable to calculate standard deviation for "
                    + u" %s. " % col_fld
                    + u"The field contains at least one non-numeric "
                    + u"value: \"%s\"" % bad_val)
            data_val = mg.NO_CALC_LBL
        return data_val, msg

    def get_data_val(self, measure, col_fld, row_filter_lst,
            dp=mg.DEFAULT_REPORT_DP):
        """
        measure -- e.g. MEAN
        col_fld -- the numeric field we are calculating the summary of. NB if
            SQLite, may be a numeric field with some non-numeric values in it.
        row_filter_lst - so we only look at values in the row.
        dp -- values rounded to required decimal points.
        """
        debug = False
        msg = None
        dp2_tpl = u"%.{0}f".format(dp)  ## shows that many decimal places even if zeros at end and rounds if necessary to fit
        row_filt_clause = u" AND ".join(row_filter_lst)
        if row_filt_clause:
            overall_filter = u" WHERE " + row_filt_clause + self.and_tbl_filt
        else: 
            overall_filter = self.where_tbl_filt
        # if using raw data (or finding bad data) must handle non-numeric values 
        # myself. Not using SQL to do aggregate calculations - only to get raw 
        # vals which are then processed by numpy or whatever.
        SQL_get_vals = ("""SELECT %(fld)s
        FROM %(tblname)s
        %(overall_filter)s
        %(and_or_where)s %(fld)s IS NOT NULL""" % 
            {u"fld": self.quote_obj(col_fld),
             u"tblname": getdata.tblname_qtr(self.dbe, self.tbl),
             u"overall_filter": overall_filter,
             u"and_or_where": u"AND" if overall_filter else u"WHERE"})
        sql_for_raw_only = [mg.MEDIAN_KEY, mg.MODE_KEY, mg.LOWER_QUARTILE_KEY, 
            mg.UPPER_QUARTILE_KEY, mg.IQR_KEY, mg.STD_DEV_KEY]
        if measure in sql_for_raw_only:
            self.cur.execute(SQL_get_vals)
            raw_vals = self.cur.fetchall() # sometimes returns REALS as strings
            if debug: print(raw_vals)
            # SQLite sometimes returns strings even if REAL
            data = [float(x[0]) for x in raw_vals]
            if debug: print(data)
        if measure == mg.MIN_KEY:
            SQL_get_min = (u"SELECT MIN(%s) " % self.quote_obj(col_fld)
                + u"FROM " + getdata.tblname_qtr(self.dbe, self.tbl) 
                + overall_filter)
            try:
                self.cur.execute(SQL_get_min)
                data_val = lib.formatnum(self.cur.fetchone()[0])
            except Exception:
                data_val = mg.NO_CALC_LBL
        elif measure == mg.MAX_KEY:
            SQL_get_max = (u"SELECT MAX(%s) " % self.quote_obj(col_fld)
                + u"FROM " + getdata.tblname_qtr(self.dbe, self.tbl) 
                + overall_filter)
            try:
                self.cur.execute(SQL_get_max)
                data_val = lib.formatnum(self.cur.fetchone()[0])
            except Exception:
                data_val = mg.NO_CALC_LBL
        elif measure == mg.RANGE_KEY:
            SQL_get_range = (u"SELECT (MAX(%(fld)s) - MIN(%(fld)s)) " %
                {u"fld": self.quote_obj(col_fld)} + u"FROM " 
                + getdata.tblname_qtr(self.dbe, self.tbl) + overall_filter)
            try:
                self.cur.execute(SQL_get_range)
                data_val = dp2_tpl % self.cur.fetchone()[0]
            except Exception:
                data_val = mg.NO_CALC_LBL
        elif measure == mg.SUM_KEY:
            SQL_get_sum = (u"SELECT SUM(%s) " % self.quote_obj(col_fld) +
                u"FROM " + getdata.tblname_qtr(self.dbe, self.tbl) 
                + overall_filter)
            try:
                self.cur.execute(SQL_get_sum)
                data_val = lib.formatnum(self.cur.fetchone()[0])
            except Exception:
                data_val = mg.NO_CALC_LBL
        elif measure == mg.MEAN_KEY:
            val2float = getdata.get_val2float_func(self.dbe)
            SQL_get_mean = u"""SELECT AVG(%s) 
                FROM %s %s""" % (val2float(self.quote_obj(col_fld)),
                getdata.tblname_qtr(self.dbe, self.tbl), overall_filter)
            try:
                self.cur.execute(SQL_get_mean)
                data_val = dp2_tpl % self.cur.fetchone()[0]
            except Exception:
                data_val = mg.NO_CALC_LBL
        elif measure == mg.MEDIAN_KEY:
            try:
                data_val = dp2_tpl % numpy.median(data)
            except Exception:
                bad_val = self._get_non_num_val(SQL_get_vals)
                if bad_val is not None:
                    msg = (u"Unable to calculate median for %s. " % col_fld
                        + u"The field contains at least one non-numeric "
                        + u"value: \"%s\"" % bad_val)
                data_val = mg.NO_CALC_LBL
        elif measure == mg.MODE_KEY:
            try:
                maxfreq, mode = core_stats.mode(data)
                n_modes = len(mode)
                if n_modes > mg.MAX_MODES:
                    data_val = u"Too many modes to display"
                else:
                    mode2show = u", ".join(str(x) for x in mode)
                    data_val = u"%s (N=%s)" % (mode2show,
                        lib.formatnum(maxfreq))
            except Exception:
                bad_val = self._get_non_num_val(SQL_get_vals)
                if bad_val is not None:
                    msg = (u"Unable to calculate mode for %s. " % col_fld
                        + u"The field contains at least one non-numeric "
                        + u"value: \"%s\"" % bad_val)
                data_val = mg.NO_CALC_LBL
        elif measure == mg.LOWER_QUARTILE_KEY:
            data_val, msg = self._lq(data, SQL_get_vals, col_fld, dp2_tpl)
        elif measure == mg.UPPER_QUARTILE_KEY:
            data_val, msg = self._uq(data, SQL_get_vals, col_fld, dp2_tpl)
        elif measure == mg.IQR_KEY:
            data_val, msg = self._iq_range(data, SQL_get_vals, col_fld, dp2_tpl)
        elif measure == mg.SUMM_N_KEY:
            SQL_get_n = u"SELECT COUNT(%s) " % self.quote_obj(col_fld) + \
                u"FROM %s %s" % (getdata.tblname_qtr(self.dbe, self.tbl), 
                    overall_filter)
            try:
                self.cur.execute(SQL_get_n)
                data_val = u"N=%s" % lib.formatnum(self.cur.fetchone()[0])
            except Exception:
                data_val = mg.NO_CALC_LBL
        elif measure == mg.STD_DEV_KEY:
            data_val, msg = self._std_dev(data, SQL_get_vals, col_fld,
                dp2_tpl)
        else:
            raise Exception(u"Measure not available")
        return data_val, msg
    