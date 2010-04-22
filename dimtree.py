#! /usr/bin/env python
# -*- coding: utf-8 -*-

import pprint
import wx

import my_globals as mg
import lib
import getdata
import dimtables
import projects

SORT_OPT_NONE = 0 # No sorting options
SORT_OPT_BY_LABEL = 1 # Only provide option of sorting by label
SORT_OPT_ALL = 2 # Option of sorting by labels and freqs

dd = getdata.get_dd()

"""
Dimtree (tree of dimensions i.e. rows and columns) handles the GUI configuration 
    of the report table.  All it does is collect the right information to pass 
    onto the script.  The same configuration could be hand typed into the script 
    by the user with the same effect.
The script utilises dimtables to actually generate the HTML. Firstly, the node
    information is turned into a label tree which is used to create the data 
    cells.
A label tree has nodes for each value under a variable e.g. the dimension might 
    be country vs agegroup but we still need to know if there is a label node 
    for a particular value e.g. '30-39' for the given (filtered) data.  Plus we 
    need to add label nodes for totals, row %s etc.   
"""


class DimTree(object):
    
    # dimension (rows/columns) trees
    """
    All methods which add items to the tree must at the same
    time attach an ItemConfig object as its PyData (using
    set_initial_config().  This includes on_col_config when 
    col_no_vars_item is added.
    """
    def on_row_item_activated(self, event):
        "Activated row item in tree.  Show config dialog."
        self.config_row()
    
    def on_col_item_activated(self, event):
        "Activated col item in tree.  Show config dialog."
        self.config_col()
    
    def on_row_item_rclick(self, event):
        self.show_var_properties(self.rowtree, event)

    def on_col_item_rclick(self, event):
        """
        If a normal variable column variable, open config dialog.
        """
        item = event.GetItem()
        if item != self.col_no_vars_item:
            self.show_var_properties(self.coltree, event)
        
    def show_var_properties(self, tree, event):
        item = event.GetItem() # NB GUI tree item, not our own Dim Node obj
        tree.SelectItem(item)
        item_conf = tree.GetItemPyData(item)
        var_name = item_conf.var_name
        var_label = lib.get_item_label(self.var_labels, var_name)
        choice_item = lib.get_choice_item(self.var_labels, var_name)
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                                         self.var_labels, self.var_notes, 
                                         self.var_types, self.val_dics)
        if updated:
            # update var label in tree and update demo html
            tree.SetItemText(event.GetItem(), 
                    lib.get_choice_item(self.var_labels, var_name))
            self.update_demo_display()
    
    def on_row_add(self, event):
        "Add row var under root"
        self.try_adding(tree=self.rowtree, root=self.rowroot, dim=mg.ROWDIM, 
                        oth_dim=mg.COLDIM, oth_dim_tree=self.coltree, 
                        oth_dim_root=self.colroot)
     
    def on_col_add(self, event):
        "Add column var under root"
        self.try_adding(tree=self.coltree, root=self.colroot, dim=mg.COLDIM, 
                        oth_dim=mg.ROWDIM, oth_dim_tree=self.rowtree, 
                        oth_dim_root=self.rowroot)
    
    def get_selected_idxs(self, sorted_choices):
        selected_idxs = None # init
        if self.tab_type in (mg.ROW_SUMM, mg.RAW_DISPLAY):
            dlg = wx.MultiChoiceDialog(self, _("Select a variable"), 
                                       _("Variables"), choices=sorted_choices)
            retval = dlg.ShowModal()
            if retval == wx.ID_OK:
                selected_idxs = dlg.GetSelections()
        else:
            retval = wx.GetSingleChoiceIndex(_("Select a variable"), 
                            _("Variables"), choices=sorted_choices, parent=self)
            if retval != -1:
                selected_idxs = [retval,]
        return selected_idxs
    
    def try_adding(self, tree, root, dim, oth_dim, oth_dim_tree, oth_dim_root):
        """
        Try adding a variable.
        NB while in the GUI, all we are doing is building a tree control.
        It is when we build a script that we build a dim node tree (a tree of 
            what our config tree looks like in the GUI) from it and then build a 
            label node tree (a tree of what we see in output) from that.
        """
        if self.tab_type == mg.ROW_SUMM and tree == self.rowtree:
            min_data_type = mg.VAR_TYPE_ORD
        else:
            min_data_type = mg.VAR_TYPE_CAT
        var_names = projects.get_approp_var_names(self.var_types, min_data_type)
        sorted_choices, sorted_vars = lib.get_sorted_choice_items(
                                    dic_labels=self.var_labels, vals=var_names)
        selected_idxs = self.get_selected_idxs(sorted_choices)
        if selected_idxs:
            # only use in one dimension
            for idx in selected_idxs:
                text = sorted_choices[idx]
                var_name = sorted_vars[idx]
                used_in_oth_dim = self.used_in_oth_dim(text, oth_dim_tree, 
                                                       oth_dim_root)
                if used_in_oth_dim:
                    msg = _("Variable '%(text)s' has already been used in "
                            "%(oth_dim)s dimension")
                    wx.MessageBox(msg % {"text": text, "oth_dim": oth_dim})
                    return
                # in raw tables, can only use once
                if self.tab_type == mg.RAW_DISPLAY:
                    used_in_this_dim = self.used_in_this_dim(text, tree, root)
                    if used_in_this_dim:
                        msg = _("Variable '%(text)s' cannot be used more than "
                                "once")
                        wx.MessageBox(msg % {"text": text})
                        return
            # they all passed the tests so proceed
            for idx in selected_idxs:
                text = sorted_choices[idx]
                new_id = tree.AppendItem(root, text)
                var_name = sorted_vars[idx]            
                self.set_initial_config(tree, dim, new_id, var_name,
                                        self.last_row_summ_measures)
            tree.UnselectAll() # multiple
            tree.SelectItem(new_id)
            if tree == self.rowtree:
                self.setup_row_btns()
            else:
                self.setup_col_btns()
            self.setup_action_btns()
            self.update_demo_display()
    
    def set_initial_config(self, tree, dim, new_id, var_name=None, 
                           last_row_summ_measures=None):
        """
        Set initial config for new item.
        Variable name not applicable when a column config item 
            (col_no_vars_item)rather than a normal column variable.
        """
        item_conf = lib.ItemConfig()
        if self.tab_type == mg.FREQS_TBL and dim == mg.COLDIM:
            item_conf.measures_lst = [lib.get_default_measure(mg.FREQS_TBL)]
        elif self.tab_type == mg.CROSSTAB and dim == mg.COLDIM:
            item_conf.measures_lst = [lib.get_default_measure(mg.CROSSTAB)]
        elif self.tab_type == mg.ROW_SUMM and dim == mg.ROWDIM:
            if last_row_summ_measures:
                item_conf.measures_lst = self.last_row_summ_measures[:]
            else:
                item_conf.measures_lst = [lib.get_default_measure(mg.ROW_SUMM)]
        if var_name:
            item_conf.var_name = var_name
            item_conf.bolnumeric = dd.flds[var_name][mg.FLD_BOLNUMERIC]
        else:
            item_conf.bolnumeric = False
        tree.SetItemPyData(new_id, item_conf)
        tree.SetItemText(new_id, item_conf.get_summary(), 1)
    
    def on_row_add_under(self, event):
        """
        Add row var under another row var (i.e. nest it).
        Remove measures from ancestors.
        """
        tree = self.rowtree
        root = self.rowroot
        dim = mg.ROWDIM
        oth_dim = mg.COLDIM
        oth_dim_tree = self.coltree
        oth_dim_root = self.colroot
        selected_ids = tree.GetSelections()
        if (root not in selected_ids 
                and self.tab_type not in (mg.FREQS_TBL, mg.CROSSTAB)):
            msg = _("Rows can only be nested in frequency or crosstab tables")
            wx.MessageBox(msg)
            return
        if len(selected_ids) == 1:
            self.try_adding_under(tree, root, dim, oth_dim, selected_ids[0], 
                                  oth_dim_tree, oth_dim_root)
        elif not selected_ids:
            wx.MessageBox(_("Select a row variable first"))
            return
        else:
            wx.MessageBox(_("Can only add under a single selected row "
                            "variable."))
            return
    
    def on_col_add_under(self, event):
        """
        Add column var under another column var (i.e. nest it).
        Remove measures from ancestors.
        """
        tree = self.coltree
        root = self.colroot
        dim = mg.COLDIM
        oth_dim = mg.ROWDIM
        oth_dim_tree = self.rowtree
        oth_dim_root = self.rowroot
        selected_ids = tree.GetSelections()
        if len(selected_ids) == 1:
            self.try_adding_under(tree, root, dim, oth_dim, selected_ids[0], 
                                  oth_dim_tree, oth_dim_root)
        elif not selected_ids:
            wx.MessageBox(_("Select a column variable first"))
            return
        else:
            wx.MessageBox(_("Can only add under a single selected column "
                            "variable."))
            return
        
    def try_adding_under(self, tree, root, dim, oth_dim, selected_id, 
                         oth_dim_tree, oth_dim_root):
        """
        Try to add var under selected var.
        Only do so if OK e.g. no duplicate text in either dim.
        """
        var_names = dd.flds.keys()
        sorted_choices, sorted_vars = lib.get_sorted_choice_items(
                                                    self.var_labels, var_names)
        selected_idxs = self.get_selected_idxs(sorted_choices)
        if selected_idxs:
            for idx in selected_idxs:
                text = sorted_choices[idx]
                var_name = sorted_vars[idx]
                # a text label supplied cannot be in any ancestors
                ancestor_labels = []
                parent_text = tree.GetItemText(selected_id)
                ancestor_labels.append(parent_text)
                ancestors = lib.get_tree_ancestors(tree, selected_id)
                parent_ancestor_labels = [tree.GetItemText(x) for
                                          x in ancestors]
                ancestor_labels += parent_ancestor_labels
                # text cannot be anywhere in other dim tree
                used_in_oth_dim = self.used_in_oth_dim(text, oth_dim_tree, 
                                                       oth_dim_root)                
                if text in ancestor_labels:
                    msg = _("Variable %s cannot be an ancestor of itself")
                    wx.MessageBox(msg % text)
                    return
                elif used_in_oth_dim:
                    msg = _("Variable %(text)s already used in "
                            "%(oth_dim)s dimension")
                    wx.MessageBox(msg % {"text": text, "oth_dim": oth_dim})
                    return
            # they all passed the test so proceed
            for idx in selected_idxs:
                text = sorted_choices[idx]
                new_id = tree.AppendItem(selected_id, text)
                var_name = sorted_vars[idx] 
                self.set_initial_config(tree, dim, new_id, var_name, 
                                        self.last_row_summ_measures)
                # empty all measures from ancestors and ensure sorting 
                # is appropriate
                for ancestor in lib.get_tree_ancestors(tree, new_id):
                    item_conf = tree.GetItemPyData(ancestor)
                    if item_conf: #ignore root node
                        item_conf.measures_lst = []
                        if item_conf.sort_order in [mg.SORT_FREQ_ASC, 
                                                    mg.SORT_FREQ_DESC]:
                            item_conf.sort_order = mg.SORT_NONE
                        tree.SetItemText(ancestor, 
                                         item_conf.get_summary(), 1)                        
            tree.ExpandAll(root)
            tree.UnselectAll() # multiple
            tree.SelectItem(new_id)
            self.update_demo_display()
    
    def used_in_oth_dim(self, text, oth_dim_tree, oth_dim_root):
        "Is this variable used in the other dimension at all?"
        oth_dim_items = lib.get_tree_ctrl_descendants(oth_dim_tree, 
                                                      oth_dim_root)
        oth_dim_labels = [oth_dim_tree.GetItemText(x) for \
                                  x in oth_dim_items]
        return text in oth_dim_labels
    
    def used_in_this_dim(self, text, dim_tree, dim_root):
        "Is this variable already used in this dimension?"
        dim_items = lib.get_tree_ctrl_descendants(dim_tree, dim_root)
        dim_labels = [dim_tree.GetItemText(x) for x in dim_items]
        return text in dim_labels
                
    def on_row_delete(self, event):
        """
        Delete row var and all its children.
        If it has a parent, set its measures to the default list.
        """
        selected_ids = self.rowtree.GetSelections()
        if not selected_ids:
            wx.MessageBox(_("No row variable selected to delete"))
            return
        first_selected_id = selected_ids[0]
        parent_id = self.rowtree.GetItemParent(first_selected_id)
        if parent_id:
            item_conf = self.rowtree.GetItemPyData(parent_id)
            if item_conf:
                item_conf.measures_lst = [self.demo_tab.default_measure]
            prev_sibling_id = self.coltree.GetPrevSibling(first_selected_id)
            next_sibling_id = self.coltree.GetNextSibling(first_selected_id)
            if prev_sibling_id.IsOk():
                self.rowtree.SelectItem(prev_sibling_id)
            elif next_sibling_id.IsOk():
                self.rowtree.SelectItem(next_sibling_id)
            else:
                self.rowtree.SelectItem(parent_id)
        for selected_id in selected_ids:
            self.rowtree.DeleteChildren(selected_id)
        if self.rowroot not in selected_ids:
            for selected_id in selected_ids:
                self.rowtree.Delete(selected_id)
        self.setup_row_btns()
        self.setup_action_btns()
        self.update_demo_display()
            
    def on_col_delete(self, event):
        """
        Delete col var and all its children.  Set selection to previous sibling
            (if any) or parent (if no siblings) or nowhere if not even a parent.
        """
        selected_ids = self.coltree.GetSelections()
        if not selected_ids:
            wx.MessageBox(_("No column variable selected to delete"))
            return
        first_selected_id = selected_ids[0]
        parent_id = self.coltree.GetItemParent(first_selected_id)
        if parent_id:
            item_conf = self.coltree.GetItemPyData(parent_id)
            if item_conf:
                item_conf.measures_lst = [self.demo_tab.default_measure]
            prev_sibling_id = self.coltree.GetPrevSibling(first_selected_id)
            if prev_sibling_id.IsOk():
                self.coltree.SelectItem(prev_sibling_id)
            else:
                self.coltree.SelectItem(parent_id)
        for selected_id in selected_ids:
            self.coltree.DeleteChildren(selected_id)
        if self.colroot not in selected_ids:
            for selected_id in selected_ids:
                self.coltree.Delete(selected_id)
            self.update_demo_display()
        if self.col_no_vars_item in selected_ids:
            self.btn_col_add.Enable()
            self.btn_col_add_under.Enable()
            self.col_no_vars_item = None # will be reallocated)
        self.setup_col_btns()
        self.setup_action_btns()
            
    def on_row_config(self, event):
        "Configure row button clicked."
        self.config_row()
    
    def config_row(self):
        """
        Configure row item e.g. measures, total.
        If a Summary Table, rows are never nested i.e. always terminal.
        Rows have no sorting options if a row summary table.
        Terminal nodes can have either label or freq sorting and
            other nodes can only have label sorting.
        """
        if not lib.item_has_children(self.rowtree, self.rowroot):
            return
        selected_ids = self.rowtree.GetSelections()
        if not selected_ids:
            wx.MessageBox(_("Please select a row variable and try again"))
            return
        first_selected_id = selected_ids[0] 
        # get results from appropriate dialog and store as data
        inc_measures = (self.tab_type == mg.ROW_SUMM)
        if self.tab_type == mg.ROW_SUMM:
            sort_opt_allowed = SORT_OPT_NONE
        elif not lib.item_has_children(tree=self.rowtree, 
                                       parent=first_selected_id):
            sort_opt_allowed = SORT_OPT_ALL
        else:
            sort_opt_allowed = SORT_OPT_BY_LABEL
        ret_measures = [] # will be updated internally
        dlg = DlgRowConfig(parent=self, var_labels=self.var_labels,
                           node_ids=selected_ids, tree=self.rowtree,
                           sort_opt_allowed=sort_opt_allowed,
                           inc_measures=inc_measures, ret_measures=ret_measures)
        if dlg.ShowModal() == wx.ID_OK:
            self.last_row_summ_measures = ret_measures
            self.update_demo_display()
    
    def on_col_config(self, event):
        "Configure column button clicked."
        self.config_col()

    def add_default_column_config(self):
        self.col_no_vars_item = self.coltree.AppendItem(self.colroot, 
                                                        mg.COL_CONFIG_ITEM_LBL)
        self.set_initial_config(self.coltree, mg.COLDIM, self.col_no_vars_item)
        self.demo_tab.col_no_vars_item = self.col_no_vars_item
        self.coltree.ExpandAll(self.colroot)
        self.coltree.SelectItem(self.col_no_vars_item)
        self.btn_col_add.Disable()
        self.btn_col_add_under.Disable()

    def config_col(self):
        """
        Configure selected column item e.g. measures, total.
        Either with columns variables or without.  If without, total doesn't 
            make sense.
        """
        # error 1
        # ItemHasChildren is buggy if root hidden i.e. if only the root there.
        empty_coltree = not lib.item_has_children(tree=self.coltree, 
                                                  parent=self.colroot)
        if empty_coltree:
            raise Exception, "Cannot configure a missing column item"
        # error 2
        selected_ids = self.coltree.GetSelections()
        if not selected_ids:
            wx.MessageBox(_("Please select a column variable and try again"))
            return
        # the ids must all have the same parental status.
        # if one has children, they all must.
        # if one has no children, none can.
        have_children_mismatch = False
        first_has_children = lib.item_has_children(tree=self.coltree,
                                                   parent=selected_ids[0])
        for selected_id in selected_ids[1:]:
            if lib.item_has_children(tree=self.coltree,
                            parent=selected_id) != first_has_children:
                have_children_mismatch = True
                break
        if have_children_mismatch:
            msg = _("If configuring multiple items at once, they must all have "
                    "children or none can have children")
            wx.MessageBox(msg)
            return
        # ok to open config dlg
        if self.col_no_vars_item in selected_ids:
            has_col_vars = False
        elif self.colroot not in selected_ids:
            has_col_vars = True
        else:
            raise Exception, ("Configuring a column but no col vars OR a col "
                              "config item")
        if self.get_col_config(node_ids=selected_ids, 
                               has_col_vars=has_col_vars) == wx.ID_OK:
            self.update_demo_display()
            
    def get_col_config(self, node_ids, has_col_vars):
        """
        Get results from appropriate dialog and store as data.
        Only ask for measures if a table with colmeasures and node is terminal.
        If the column item is col_no_vars_item then no sorting options.
        If a row summary table, no sorting options.
        Terminal nodes can have either label or freq sorting and
            other nodes can only have label sorting.
        Returns the show modal return value.
        """
        # include measures if the selected items have no children
        # only need to test one because they are all requried to be the same
        has_children = True
        if not node_ids:
            has_children = False
        else:
            item, cookie = self.coltree.GetFirstChild(node_ids[0])
            has_children = True if item else False
        inc_measures = self.tab_type == mg.FREQS_TBL or \
                       ((self.tab_type == mg.CROSSTAB) and not has_children)
        if self.col_no_vars_item in node_ids or self.tab_type not in \
                (mg.FREQS_TBL, mg.CROSSTAB):
            sort_opt_allowed = SORT_OPT_NONE
        elif not lib.item_has_children(tree=self.coltree, parent=node_ids[0]):
            sort_opt_allowed = SORT_OPT_ALL
        else:
            sort_opt_allowed = SORT_OPT_BY_LABEL
        dlg = DlgColConfig(parent=self, var_labels=self.var_labels,
                           node_ids=node_ids, tree=self.coltree, 
                           inc_measures=inc_measures, 
                           sort_opt_allowed=sort_opt_allowed, 
                           has_col_vars=has_col_vars)
        retval = dlg.ShowModal()
        return retval
       
    def setup_dim_tree(self, tree):
        "Setup Dim Tree and return root"
        tree.AddColumn(_("Variable"))
        tree.AddColumn(_("Config"))
        tree.SetMainColumn(0)
        tree.SetColumnWidth(0, 150)
        tree.SetColumnWidth(1, 500)
        #MinSize lets SetSizeHints make a more sensible guess for starting point
        tree.SetMinSize((70, 110))
        return tree.AddRoot("root")

    def setup_row_btns(self):
        """
        Enable or disable row buttons according to table type and presence or
            absence of row items.
        """
        has_rows = True if lib.get_tree_ctrl_children(tree=self.rowtree, 
                                                      item=self.rowroot) \
                                                      else False
        if self.tab_type in (mg.FREQS_TBL, mg.CROSSTAB, mg.ROW_SUMM):
            self.btn_row_add.Enable(True)
            self.btn_row_add_under.Enable(has_rows 
                                          and self.tab_type != mg.ROW_SUMM)
            self.btn_row_del.Enable(has_rows)
            self.btn_row_conf.Enable(has_rows)
        elif self.tab_type == mg.RAW_DISPLAY:
            self.btn_row_add.Enable(False)
            self.btn_row_add_under.Enable(False)
            self.btn_row_del.Enable(False)
            self.btn_row_conf.Enable(False)
        
    def setup_col_btns(self):
        """
        Enable or disable column buttons according to table type and presence or
            absence of column items.
        """
        has_cols = True if lib.get_tree_ctrl_children(tree=self.coltree, 
                                                      item=self.colroot) \
                                                      else False
        if self.tab_type == mg.FREQS_TBL:
            self.btn_col_add.Enable(False)
            self.btn_col_add_under.Enable(False)
            self.btn_col_del.Enable(False)
            self.btn_col_conf.Enable(True)
        elif self.tab_type == mg.CROSSTAB:
            self.btn_col_add.Enable(True)
            self.btn_col_add_under.Enable(True)
            self.btn_col_del.Enable(enable=has_cols)
            self.btn_col_conf.Enable(enable=has_cols)
        elif self.tab_type == mg.ROW_SUMM:
            self.btn_col_add.Enable(True)
            self.btn_col_add_under.Enable(True)
            self.btn_col_del.Enable(enable=has_cols)
            self.btn_col_conf.Enable(enable=has_cols)
        elif self.tab_type == mg.RAW_DISPLAY:
            self.btn_col_add.Enable(True)
            self.btn_col_add_under.Enable(False)
            self.btn_col_del.Enable(True)
            self.btn_col_conf.Enable(False)

    
class DlgConfig(wx.Dialog):
    
    def __init__(self, parent, var_labels, node_ids, tree, title, size, 
                 allow_tot, sort_opt_allowed, row=True):
        """
        Parent class for all dialogs collecting configuration details 
            for rows and cols.
        node_ids - list, even if only one item selected.
        """
        wx.Dialog.__init__(self, parent, id=-1, title=title, size=size)
        self.tree = tree
        self.allow_tot = allow_tot
        self.sort_opt_allowed = sort_opt_allowed
        self.node_ids = node_ids
        first_node_id = node_ids[0]
        # base item configuration on first one selected
        item_conf = self.tree.GetItemPyData(first_node_id)
        chk_size = (150, 20)
        szr_main = wx.BoxSizer(wx.VERTICAL)
        var_lbl = tree.GetItemText(first_node_id)
        lbl_var = wx.StaticText(self, -1, var_lbl)
        szr_main.Add(lbl_var, 0, wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT, 10)
        if self.allow_tot:
            box_misc = wx.StaticBox(self, -1, _("Misc"))
            szr_misc = wx.StaticBoxSizer(box_misc, wx.VERTICAL)
            self.chk_total = wx.CheckBox(self, -1, mg.HAS_TOTAL, 
                                         size=chk_size)
            if item_conf.has_tot:
                self.chk_total.SetValue(True)
            szr_misc.Add(self.chk_total, 0, wx.LEFT, 5)
            szr_main.Add(szr_misc, 0, wx.GROW|wx.ALL, 10)
        if self.sort_opt_allowed != SORT_OPT_NONE:
            self.rad_sort_opts = wx.RadioBox(self, -1, _("Sort order"),
                               choices=[mg.SORT_NONE, mg.SORT_LABEL,
                                        mg.SORT_FREQ_ASC, mg.SORT_FREQ_DESC],
                               size=(400,50))
            # set selection according to existing item_conf
            if item_conf.sort_order == mg.SORT_NONE:
                self.rad_sort_opts.SetSelection(0)
            elif item_conf.sort_order == mg.SORT_LABEL:
                self.rad_sort_opts.SetSelection(1)
            elif item_conf.sort_order == mg.SORT_FREQ_ASC:
                self.rad_sort_opts.SetSelection(2)
            elif item_conf.sort_order == mg.SORT_FREQ_DESC:
                self.rad_sort_opts.SetSelection(3)
            if self.sort_opt_allowed == SORT_OPT_BY_LABEL:
                # disable freq options
                self.rad_sort_opts.EnableItem(2, False)
                self.rad_sort_opts.EnableItem(3, False)
            szr_main.Add(self.rad_sort_opts, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        self.measure_chks_dic = {}
        if self.measures:
            box_measures = wx.StaticBox(self, -1, _("Measures"))
            direction = wx.VERTICAL if row else wx.HORIZONTAL
            szr_measures = wx.StaticBoxSizer(box_measures, direction)
            for measure, label in self.measures:
                chk = wx.CheckBox(self, -1, label, 
                            size=chk_size)
                if measure in item_conf.measures_lst:
                    chk.SetValue(True)
                self.measure_chks_dic[measure] = chk
                szr_measures.Add(chk, 1, wx.ALL, 5)
            szr_main.Add(szr_measures, 1, wx.GROW|wx.ALL, 10)
        btn_cancel = wx.Button(self, wx.ID_CANCEL)
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)            
        btn_ok = wx.Button(self, wx.ID_OK) # must have ID of wx.ID_OK 
        # to trigger validators (no event binding needed) and 
        # for std dialog button layout
        btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        btn_ok.SetDefault()
        # using the approach which will follow the platform convention 
        # for standard buttons
        szr_btns = wx.StdDialogButtonSizer()
        szr_btns.AddButton(btn_cancel)
        szr_btns.AddButton(btn_ok)
        szr_btns.Realize()
        szr_main.Add(szr_btns, 0, wx.GROW|wx.ALL, 10)
        szr_main.SetSizeHints(self)
        self.SetSizer(szr_main)
        self.Fit()
             
    def on_ok(self, event):
        """
        Store selection details into item conf object
        """
        # measures
        measures_lst = []
        any_measures = False
        for measure, label in self.measures:
            ticked = self.measure_chks_dic[measure].GetValue()
            if ticked:
                any_measures = True
                measures_lst.append(measure)
        if self.measures and not any_measures:
            wx.MessageBox(_("Please select at least one measure"))
            return
        # Store measures ready to be used as default when adding next row summ 
        #     var.
        try:
            self.ret_measures
            while True: # empty list but keep var pointing to it
                try:
                    del self.ret_measures[0]
                except IndexError:
                    break
            self.ret_measures.extend(measures_lst)
        except AttributeError:
            pass
        # tot
        has_tot = self.allow_tot and self.chk_total.GetValue()
        # sort order
        if self.sort_opt_allowed == SORT_OPT_NONE:
            sort_order = mg.SORT_NONE
        else:
            sort_opt_selection = self.rad_sort_opts.GetSelection()
            if sort_opt_selection == 0:
                sort_order = mg.SORT_NONE
            if sort_opt_selection == 1:
                sort_order = mg.SORT_LABEL
            if sort_opt_selection == 2:
                sort_order = mg.SORT_FREQ_ASC
            if sort_opt_selection == 3:
                sort_order = mg.SORT_FREQ_DESC
        for node_id in self.node_ids:
            existing_data = self.tree.GetItemPyData(node_id)
            var_name = existing_data.var_name
            bolnumeric = existing_data.bolnumeric
            item_conf = lib.ItemConfig(var_name, measures_lst, has_tot, 
                                       sort_order, bolnumeric)
            self.tree.SetItemPyData(node_id, item_conf)        
            self.tree.SetItemText(node_id, item_conf.get_summary(), 1)
        self.Destroy()
        self.SetReturnCode(wx.ID_OK) # or nothing happens!  
        # Prebuilt dialogs presumably do this internally.
    
    def on_cancel(self, event):
        "Cancel adding new package"
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)
    
    
class DlgRowConfig(DlgConfig):
    
    def __init__(self, parent, var_labels, node_ids, tree, sort_opt_allowed,
                 inc_measures, ret_measures):
        "ret_measures -- pass back list of measures ticked"
        self.ret_measures = ret_measures
        title = _("Configure Row Item")
        if inc_measures:
            self.measures = [
                        (mg.MEAN, mg.measures_long_label_dic[mg.MEAN]), 
                        (mg.MEDIAN, mg.measures_long_label_dic[mg.MEDIAN]), 
                        (mg.SUMM_N, mg.measures_long_label_dic[mg.SUMM_N]), 
                        (mg.STD_DEV, mg.measures_long_label_dic[mg.STD_DEV]),
                        (mg.SUM, mg.measures_long_label_dic[mg.SUM]),
                        ]
        else:
            self.measures = []
        size = wx.DefaultSize
        DlgConfig.__init__(self, parent, var_labels, node_ids, tree, 
                           title, size, allow_tot=not inc_measures,
                           sort_opt_allowed=sort_opt_allowed, row=True)
        

class DlgColConfig(DlgConfig):
    
    def __init__(self, parent, var_labels, node_ids, tree, inc_measures, 
                 sort_opt_allowed, has_col_vars=True):
        title = _("Configure Column Item")
        if inc_measures:
            self.measures = [
                (mg.FREQ, mg.measures_long_label_dic[mg.FREQ]), 
                (mg.COLPCT, mg.measures_long_label_dic[mg.COLPCT])
                ]
            if has_col_vars:
                self.measures.append((mg.ROWPCT, 
                                      mg.measures_long_label_dic[mg.ROWPCT]))
        else:
            self.measures = []
        size = wx.DefaultSize
        DlgConfig.__init__(self, parent, var_labels, node_ids, tree, 
                           title, size, allow_tot=has_col_vars, 
                           sort_opt_allowed=sort_opt_allowed, row=False)
        