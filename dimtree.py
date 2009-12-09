#! /usr/bin/env python
# -*- coding: utf-8 -*-

import pprint
import wx

import my_globals
import dimtables
import util
import make_table
import getdata
import projects

SORT_OPT_NONE = 0 #No sorting options
SORT_OPT_BY_LABEL = 1 #Only provide option of sorting by label
SORT_OPT_ALL = 2 #Option of sorting by labels and freqs


class DimTree(object):
    
    # dimension (rows/columns) trees
    """
    All methods which add items to the tree must at the same
    time attach an ItemConfig object as its PyData (using
    setInitialConfig().  This includes OnColConfig when 
    col_no_vars_item is added.
    """
    def OnRowItemActivated(self, event):
        "Activated row item in tree.  Show config dialog."
        self.ConfigRow()
    
    def OnColItemActivated(self, event):
        "Activated col item in tree.  Show config dialog."
        self.ConfigCol()
    
    def OnRowItemRightClick(self, event):
        ""
        self.ShowVarProperties(self.rowtree, event)

    def OnColItemRightClick(self, event):
        ""
        self.ShowVarProperties(self.coltree, event)
        
    def ShowVarProperties(self, tree, event):
        choice_item = tree.GetItemText(event.GetItem())
        var_name, var_label = getdata.extractChoiceDets(choice_item)
        updated = projects.SetVarProps(choice_item, var_name, var_label, 
                            self.flds, self.var_labels, self.var_notes, 
                            self.var_types, self.val_dics, self.fil_var_dets)
        if updated:
            # update var label in tree and update demo html
            tree.SetItemText(event.GetItem(), 
                    getdata.get_choice_item(self.var_labels, var_name))
            self.UpdateDemoDisplay()
    
    def OnRowAdd(self, event):
        "Add row var under root"
        self.TryAdding(tree=self.rowtree, root=self.rowRoot, 
                       dim=my_globals.ROWDIM, oth_dim=my_globals.COLDIM, 
                       oth_dim_tree=self.coltree, 
                       oth_dim_root=self.colRoot)
     
    def OnColAdd(self, event):
        "Add column var under root"
        self.TryAdding(tree=self.coltree, root=self.colRoot, 
                       dim=my_globals.COLDIM, oth_dim=my_globals.ROWDIM, 
                       oth_dim_tree=self.rowtree, 
                       oth_dim_root=self.rowRoot)
    
    def TryAdding(self, tree, root, dim, oth_dim, oth_dim_tree, 
                  oth_dim_root):
        "Try adding a variable"
        if self.tab_type == my_globals.ROW_SUMM and tree == self.rowtree:
            min_data_type = my_globals.VAR_TYPE_ORD
        else:
            min_data_type = my_globals.VAR_TYPE_CAT
        var_names = projects.GetAppropVarNames(min_data_type, self.var_types, 
                                               self.flds)
        choices, unused = getdata.get_sorted_choice_items(\
                                dic_labels=self.var_labels, vals=var_names)
        dlg = wx.MultiChoiceDialog(self, _("Select a variable"), _("Variables"), 
                                   choices=choices)
        if dlg.ShowModal() == wx.ID_OK:
            # only use in one dimension
            text_selected = [choices[x] for x in dlg.GetSelections()]
            for text in text_selected:
                used_in_oth_dim = self.UsedInOthDim(text, oth_dim_tree, 
                                                    oth_dim_root)
                if used_in_oth_dim:
                    msg = _("Variable '%(text)s' has already been "
                            "used in %(oth_dim)s dimension")
                    wx.MessageBox(msg % {"text": text, "oth_dim": oth_dim})
                    return
                # in raw tables, can only use once
                if self.tab_type == my_globals.RAW_DISPLAY:
                    used_in_this_dim = self.UsedInThisDim(text, tree, root)
                    if used_in_this_dim:
                        msg = _("Variable '%(text)s' cannot be used "
                                "more than once")
                        wx.MessageBox(msg % {"text": text})
                        return
            # they all passed the tests so proceed
            for text in text_selected:
                new_id = tree.AppendItem(root, text)
                var_name, unused = getdata.extractChoiceDets(text)
                self.setInitialConfig(tree, dim, new_id, var_name)
            if text_selected:
                tree.UnselectAll() # multiple
                tree.SelectItem(new_id)
                self.UpdateDemoDisplay()
    
    def setInitialConfig(self, tree, dim, new_id, var_name=None):
        """
        Set initial config for new item.
        Variable name not applicable when a column config item rather than
            a normal column variable.
        """
        item_conf = make_table.ItemConfig()
        if (self.tab_type == my_globals.COL_MEASURES \
                    and dim == my_globals.COLDIM):
            item_conf.measures_lst = \
                [make_table.get_default_measure(my_globals.COL_MEASURES)]
        elif (self.tab_type == my_globals.ROW_SUMM \
                    and dim == my_globals.ROWDIM):
            item_conf.measures_lst = \
                [make_table.get_default_measure(my_globals.ROW_SUMM)]
        if var_name:
            item_conf.bolnumeric = \
                self.flds[var_name][my_globals.FLD_BOLNUMERIC]
        else:
            item_conf.bolnumeric = False
        tree.SetItemPyData(new_id, item_conf)
        tree.SetItemText(new_id, item_conf.getSummary(), 1)
    
    def OnRowAddUnder(self, event):
        """
        Add row var under another row var (i.e. nest it).
        Remove measures from ancestors.
        """
        tree = self.rowtree
        root = self.rowRoot
        dim = my_globals.ROWDIM
        oth_dim = my_globals.COLDIM
        oth_dim_tree = self.coltree
        oth_dim_root = self.colRoot
        selected_ids = tree.GetSelections()
        if root not in selected_ids \
                and self.tab_type != my_globals.COL_MEASURES:
            msg = _("Rows can only be nested in column"
                    " measures tables")
            wx.MessageBox(msg)
            return
        if len(selected_ids) == 1:
            self.TryAddingUnder(tree, root, dim, oth_dim, selected_ids[0], 
                                oth_dim_tree, oth_dim_root)
        elif len(selected_ids) == 0:
            wx.MessageBox(_("Select a %s variable first") % dim)
            return
        else:
            wx.MessageBox(_("Can only add under a single selected item."))
            return
    
    def OnColAddUnder(self, event):
        """
        Add column var under another column var (i.e. nest it).
        Remove measures from ancestors.
        """
        tree = self.coltree
        root = self.colRoot
        dim = my_globals.COLDIM
        oth_dim = my_globals.ROWDIM
        oth_dim_tree = self.rowtree
        oth_dim_root = self.rowRoot
        selected_ids = tree.GetSelections()
        if len(selected_ids) == 1:
            self.TryAddingUnder(tree, root, dim, oth_dim, selected_ids[0], 
                                oth_dim_tree, oth_dim_root)
        elif len(selected_ids) == 0:
            wx.MessageBox(_("Select a %s variable first") % dim)
            return
        else:
            wx.MessageBox(_("Can only add under a single selected item."))
            return
        
    def TryAddingUnder(self, tree, root, dim, oth_dim, selected_id, 
                       oth_dim_tree, oth_dim_root):
        """
        Try to add var under selected var.
        Only do so if OK e.g. no duplicate text in either dim.
        """
        choice_var_names = self.flds.keys()
        choices = [getdata.get_choice_item(self.var_labels, x) \
                   for x in choice_var_names]
        choices.sort(key=lambda s: s.upper())
        dlg = wx.MultiChoiceDialog(self, _("Select a variable"), 
                                   _("Variables"), choices=choices)
        if dlg.ShowModal() == wx.ID_OK:
            text_selected = [choices[x] for x in dlg.GetSelections()]
            for text in text_selected:
                # a text label supplied cannot be in any ancestors
                ancestor_labels = []
                parent_text = tree.GetItemText(selected_id)
                ancestor_labels.append(parent_text)
                ancestors = util.getTreeAncestors(tree, selected_id)
                parent_ancestor_labels = [tree.GetItemText(x) for \
                                          x in ancestors]
                ancestor_labels += parent_ancestor_labels
                # text cannot be anywhere in other dim tree
                used_in_oth_dim = self.UsedInOthDim(text, oth_dim_tree, 
                                                    oth_dim_root)                
                if text in ancestor_labels:
                    msg = _("Variable %s cannot be an "
                            "ancestor of itself")
                    wx.MessageBox(msg % text)
                    return
                elif used_in_oth_dim:
                    msg = _("Variable %(text)s already used in "
                            "%(oth_dim)s dimension")
                    wx.MessageBox(msg % {"text": text, "oth_dim": oth_dim})
                    return
            # they all passed the test so proceed        
            for text in text_selected:
                new_id = tree.AppendItem(selected_id, text)
                var_name, unused = getdata.extractChoiceDets(text)
                self.setInitialConfig(tree, dim, new_id, var_name)
                # empty all measures from ancestors and ensure sorting 
                # is appropriate
                for ancestor in util.getTreeAncestors(tree, new_id):
                    item_conf = tree.GetItemPyData(ancestor)
                    if item_conf: #ignore root node
                        item_conf.measures_lst = []
                        if item_conf.sort_order in \
                            [my_globals.SORT_FREQ_ASC, 
                             my_globals.SORT_FREQ_DESC]:
                            item_conf.sort_order = my_globals.SORT_NONE
                        tree.SetItemText(ancestor, 
                                         item_conf.getSummary(), 1)                        
            if text_selected:
                tree.ExpandAll(root)
                tree.UnselectAll() # multiple
                tree.SelectItem(new_id)
                self.UpdateDemoDisplay()
    
    def UsedInOthDim(self, text, oth_dim_tree, oth_dim_root):
        "Is this variable used in the other dimension at all?"
        oth_dim_items = util.getTreeCtrlDescendants(oth_dim_tree, 
                                                    oth_dim_root)
        oth_dim_labels = [oth_dim_tree.GetItemText(x) for \
                                  x in oth_dim_items]
        return text in oth_dim_labels
    
    def UsedInThisDim(self, text, dim_tree, dim_root):
        "Is this variable already used in this dimension?"
        dim_items = util.getTreeCtrlDescendants(dim_tree, 
                                                dim_root)
        dim_labels = [dim_tree.GetItemText(x) for x in dim_items]
        return text in dim_labels
                
    def OnRowDelete(self, event):
        """
        Delete row var and all its children.
        If it has a parent, set its measures to the default list.
        If colmeasures is set, delete that too.
        """
        selected_ids = self.rowtree.GetSelections()
        if len(selected_ids) == 0:
            return
        first_selected_id = selected_ids[0]
        parent = self.rowtree.GetItemParent(first_selected_id)
        if parent:
            item_conf = self.rowtree.GetItemPyData(parent)
            if item_conf:
                item_conf.measures_lst = [self.demo_tab.default_measure]
        for selected_id in selected_ids:
            self.rowtree.DeleteChildren(selected_id)
        if self.rowRoot not in selected_ids:
            for selected_id in selected_ids:
                self.rowtree.Delete(selected_id)
        # if the rowtree is now empty, ensure 
        # colmeasures is wiped as well (and restore Add and Add Under 
        # buttons too ;-)
        if self.tab_type == my_globals.COL_MEASURES and \
                not util.ItemHasChildren(tree=self.rowtree,
                                     parent=self.rowRoot) and \
                self.col_no_vars_item:
            self.coltree.DeleteChildren(self.colRoot)
            self.btnColAdd.Enable()
            self.btnColAddUnder.Enable()
            self.col_no_vars_item = None #it will be reallocated
        self.UpdateDemoDisplay()
            
    def OnColDelete(self, event):
        "Delete col var and all its children"
        selected_ids = self.coltree.GetSelections()
        if len(selected_ids) == 0:
            return
        first_selected_id = selected_ids[0]
        parent = self.coltree.GetItemParent(first_selected_id)
        if parent:
            item_conf = self.coltree.GetItemPyData(parent)
            if item_conf:
                item_conf.measures_lst = [self.demo_tab.default_measure]
        for selected_id in selected_ids:
            self.coltree.DeleteChildren(selected_id)
        if self.colRoot not in selected_ids:
            for selected_id in selected_ids:
                self.coltree.Delete(selected_id)
            self.UpdateDemoDisplay()
        if self.col_no_vars_item in selected_ids:
            self.btnColAdd.Enable()
            self.btnColAddUnder.Enable()
            self.col_no_vars_item = None #it will be reallocated
            
    def OnRowConfig(self, event):
        "Configure row button clicked."
        self.ConfigRow()
    
    def ConfigRow(self):
        """
        Configure row item e.g. measures, total.
        If a Summary Table, rows are never nested i.e. always terminal.
        Rows have no sorting options if a row summary table.
        Terminal nodes can have either label or freq sorting and
            other nodes can only have label sorting.
        """
        if not util.ItemHasChildren(self.rowtree, self.rowRoot):
            return
        selected_ids = self.rowtree.GetSelections()
        first_selected_id = selected_ids[0] 
        # get results from appropriate dialog and store as data
        inc_measures = (self.tab_type == my_globals.ROW_SUMM)
        if self.tab_type == my_globals.ROW_SUMM:
            sort_opt_allowed = SORT_OPT_NONE
        elif not util.ItemHasChildren(tree=self.rowtree, 
                                      parent=first_selected_id):
            sort_opt_allowed = SORT_OPT_ALL
        else:
            sort_opt_allowed = SORT_OPT_BY_LABEL
        dlg = DlgRowConfig(parent=self, var_labels=self.var_labels,
                           node_ids=selected_ids, tree=self.rowtree, 
                           inc_measures=inc_measures,
                           sort_opt_allowed=sort_opt_allowed)
        dlg.ShowModal()
        self.UpdateDemoDisplay()
    
    def OnColConfig(self, event):
        "Configure column button clicked."
        self.ConfigCol()

    def ConfigCol(self):
        """
        Configure column item e.g. measures, total.
        Either with columns vars or without.  If without, only filtering 
            by row vars.  Total doesn't make sense in this context.
        
        """
        empty_coltree = not util.ItemHasChildren(tree=self.coltree, 
                                              parent=self.colRoot)
        # empty_tree = not self.coltree.ItemHasChildren(self.colRoot) #buggy if root hidden
        # i.e. if there is only the root there
        # no col vars - just set measures (without total)
        if empty_coltree and self.tab_type == my_globals.COL_MEASURES:
            empty_rowtree = not util.ItemHasChildren(tree=self.rowtree, 
                                                     parent=self.rowRoot)
            if empty_rowtree:
                return
            #add special node before getting config
            self.col_no_vars_item = \
                self.coltree.AppendItem(self.colRoot, 
                                        my_globals.COL_MEASURES_TREE_LBL)
            self.setInitialConfig(self.coltree, my_globals.COLDIM, 
                                  self.col_no_vars_item)
            self.demo_tab.col_no_vars_item = self.col_no_vars_item
            self.coltree.ExpandAll(self.colRoot)
            self.coltree.SelectItem(self.col_no_vars_item)
            self.btnColAdd.Disable()
            self.btnColAddUnder.Disable()
            self.getColConfig(node_ids=[self.col_no_vars_item], 
                                  has_col_vars=False)
            self.UpdateDemoDisplay()
        elif empty_coltree and self.tab_type == my_globals.ROW_SUMM:
            return
        else: # not an empty col_measures or row summ table
            selected_ids = self.coltree.GetSelections()
            # the ids must all have the same parental status
            # if one has children, they all must
            # if one has no children, none can
            config_ok = True
            if not empty_coltree:
                first_has_children = util.ItemHasChildren(tree=self.coltree,
                                                          parent=selected_ids[0])
                for selected_id in selected_ids[1:]:
                    if util.ItemHasChildren(tree=self.coltree,
                                    parent=selected_id) != first_has_children:
                        config_ok = False
                        break
            if config_ok:
                if self.col_no_vars_item in selected_ids:
                    self.getColConfig(node_ids=[self.col_no_vars_item], 
                                      has_col_vars=False)
                elif self.colRoot not in selected_ids:
                    self.getColConfig(node_ids=selected_ids, has_col_vars=True)
                self.UpdateDemoDisplay()
            else:
                msg = _("If configuring multiple items at once, they "
                     "must all have children or none can have children")
                wx.MessageBox(msg)
            
    def getColConfig(self, node_ids, has_col_vars):
        """
        Get results from appropriate dialog and store as data.
        Only ask for measures if a table with colmeasures and
            the node is terminal.
        If the column item is col_no_vars_item then no sorting options.
        If a row summary table, no sorting options.
        Terminal nodes can have either label or freq sorting and
            other nodes can only have label sorting.
        """
        # include measures if the selected items have no children
        # only need to test one because they are all requried to be the same
        has_children = True
        if not node_ids:
            has_children = False
        else:
            item, cookie = self.coltree.GetFirstChild(node_ids[0])
            has_children = True if item else False
        inc_measures = ((self.tab_type == my_globals.COL_MEASURES)
                        and not has_children)
        if self.col_no_vars_item in node_ids \
                or self.tab_type != my_globals.COL_MEASURES:
            sort_opt_allowed = SORT_OPT_NONE
        elif not util.ItemHasChildren(tree=self.coltree, 
                                      parent=node_ids[0]):
            sort_opt_allowed = SORT_OPT_ALL
        else:
            sort_opt_allowed = SORT_OPT_BY_LABEL
        dlg = DlgColConfig(parent=self, var_labels=self.var_labels,
                           node_ids=node_ids, tree=self.coltree, 
                           inc_measures=inc_measures, 
                           sort_opt_allowed=sort_opt_allowed, 
                           has_col_vars=has_col_vars)
        dlg.ShowModal()
       
    def setupDimTree(self, tree):
        "Setup Dim Tree and return root"
        tree.AddColumn(_("Variable"))
        tree.AddColumn(_("Config"))
        tree.SetMainColumn(0)
        tree.SetColumnWidth(0, 150)
        tree.SetColumnWidth(1, 500)
        #MinSize lets SetSizeHints make a more sensible guess for starting point
        tree.SetMinSize((70, 110))
        return tree.AddRoot("root")
    
    def EnableRowSel(self, enable=True):
        "Enable (or disable) all row selection objects"
        self.btnRowAdd.Enable(enable)
        self.btnRowAddUnder.Enable(enable)
        self.btnRowDel.Enable(enable)
        self.btnRowConf.Enable(enable)
        self.rowtree.Enable(enable)
        
    def enable_col_btns(self, enable=True):
        "Enable (or disable) col buttons"
        self.btnColAdd.Enable(enable)
        self.btnColAddUnder.Enable(enable)
        self.btnColDel.Enable(enable)
        self.btnColConf.Enable(enable) 
        
    
class DlgConfig(wx.Dialog):
    
    def __init__(self, parent, var_labels, node_ids, tree, title, size, 
                 allow_tot, sort_opt_allowed):
        """
        Parent class for all dialogs collecting configuration details 
            for rows and cols.
        node_ids - list, even if only one item selected.
        """
        wx.Dialog.__init__(self, parent, id=-1, title=title, 
                           size=size)
        self.tree = tree
        self.allow_tot = allow_tot
        self.sort_opt_allowed = sort_opt_allowed
        self.node_ids = node_ids
        first_node_id = node_ids[0]
        # base item configuration on first one selected
        item_conf = self.tree.GetItemPyData(first_node_id)
        chkSize = (150, 20)
        szrMain = wx.BoxSizer(wx.VERTICAL)
        lblVar = wx.StaticText(self, -1, tree.GetItemText(first_node_id))
        szrMain.Add(lblVar, 0, wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT, 10)
        if self.allow_tot:
            boxMisc = wx.StaticBox(self, -1, _("Misc"))
            szrMisc = wx.StaticBoxSizer(boxMisc, wx.VERTICAL)
            self.chkTotal = wx.CheckBox(self, -1, my_globals.HAS_TOTAL, 
                                        size=chkSize)
            if item_conf.has_tot:
                self.chkTotal.SetValue(True)
            szrMisc.Add(self.chkTotal, 0, wx.LEFT, 5)
            szrMain.Add(szrMisc, 0, wx.GROW|wx.ALL, 10)
        if self.sort_opt_allowed != SORT_OPT_NONE:
            self.radSortOpts = wx.RadioBox(self, -1, _("Sort order"),
                                       choices=[my_globals.SORT_NONE, 
                                                my_globals.SORT_LABEL,
                                                my_globals.SORT_FREQ_ASC,
                                                my_globals.SORT_FREQ_DESC],
                                       size=(400,50))
            # set selection according to existing item_conf
            if item_conf.sort_order == my_globals.SORT_NONE:
                self.radSortOpts.SetSelection(0)
            elif item_conf.sort_order == my_globals.SORT_LABEL:
                self.radSortOpts.SetSelection(1)
            elif item_conf.sort_order == my_globals.SORT_FREQ_ASC:
                self.radSortOpts.SetSelection(2)
            elif item_conf.sort_order == my_globals.SORT_FREQ_DESC:
                self.radSortOpts.SetSelection(3)
            if self.sort_opt_allowed == SORT_OPT_BY_LABEL:
                # disable freq options
                self.radSortOpts.EnableItem(2, False)
                self.radSortOpts.EnableItem(3, False)

            szrMain.Add(self.radSortOpts, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        self.measure_chks_dic = {}
        if self.measures:
            boxMeasures = wx.StaticBox(self, -1, _("Measures"))
            szrMeasures = wx.StaticBoxSizer(boxMeasures, wx.VERTICAL)
            for measure, label in self.measures:
                chk = wx.CheckBox(self, -1, label, 
                            size=chkSize)
                if measure in item_conf.measures_lst:
                    chk.SetValue(True)
                self.measure_chks_dic[measure] = chk
                szrMeasures.Add(chk, 1, wx.ALL, 5)
            szrMain.Add(szrMeasures, 1, wx.GROW|wx.ALL, 10)
        btnCancel = wx.Button(self, wx.ID_CANCEL)
        btnCancel.Bind(wx.EVT_BUTTON, self.OnCancel)            
        btnOK = wx.Button(self, wx.ID_OK) # must have ID of wx.ID_OK 
        # to trigger validators (no event binding needed) and 
        # for std dialog button layout
        btnOK.Bind(wx.EVT_BUTTON, self.OnOK)
        btnOK.SetDefault()
        # using the approach which will follow the platform convention 
        # for standard buttons
        szrButtons = wx.StdDialogButtonSizer()
        szrButtons.AddButton(btnCancel)
        szrButtons.AddButton(btnOK)
        szrButtons.Realize()
        szrMain.Add(szrButtons, 0, wx.ALL, 10)
        szrMain.SetSizeHints(self)
        self.SetSizer(szrMain)
        self.Fit()
             
    def OnOK(self, event):
        "Store selection details into item conf object"
        # measures
        measures_lst = []
        any_measures = False
        for measure, label in self.measures:
            ticked = self.measure_chks_dic[measure].GetValue()
            if ticked:
                any_measures = True
                measures_lst.append(measure)
        if not any_measures and self.min_measure:
            measures_lst.append(self.min_measure)
        # tot
        has_tot = self.allow_tot and self.chkTotal.GetValue()
        # sort order
        if self.sort_opt_allowed == SORT_OPT_NONE:
            sort_order = my_globals.SORT_NONE
        else:
            sort_opt_selection = self.radSortOpts.GetSelection()
            if sort_opt_selection == 0:
                sort_order = my_globals.SORT_NONE
            if sort_opt_selection == 1:
                sort_order = my_globals.SORT_LABEL
            if sort_opt_selection == 2:
                sort_order = my_globals.SORT_FREQ_ASC
            if sort_opt_selection == 3:
                sort_order = my_globals.SORT_FREQ_DESC
        for node_id in self.node_ids:
            bolnumeric = self.tree.GetItemPyData(node_id).bolnumeric
            item_conf = make_table.ItemConfig(measures_lst, has_tot, 
                                              sort_order, bolnumeric)
            self.tree.SetItemPyData(node_id, item_conf)        
            self.tree.SetItemText(node_id, item_conf.getSummary(), 1)
        self.Destroy()
        self.SetReturnCode(wx.ID_OK) # or nothing happens!  
        # Prebuilt dialogs must do this internally.
    
    def OnCancel(self, event):
        "Cancel adding new package"
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)
    
    
class DlgRowConfig(DlgConfig):
    
    def __init__(self, parent, var_labels, node_ids, tree, inc_measures, 
                 sort_opt_allowed):
        title = _("Configure Row Item")
        if inc_measures:
            self.measures = [
                (my_globals.MEAN, 
                    my_globals.measures_long_label_dic[my_globals.MEAN]), 
                (my_globals.MEDIAN, 
                    my_globals.measures_long_label_dic[my_globals.MEDIAN]), 
                (my_globals.SUMM_N, 
                    my_globals.measures_long_label_dic[my_globals.SUMM_N]), 
                (my_globals.STD_DEV, 
                    my_globals.measures_long_label_dic[my_globals.STD_DEV]),
                (my_globals.SUM, 
                    my_globals.measures_long_label_dic[my_globals.SUM]),
                ]
            self.min_measure = my_globals.MEAN
        else:
            self.measures = []
            self.min_measure = None
        size = wx.DefaultSize
        DlgConfig.__init__(self, parent, var_labels, node_ids, tree, 
                           title, size, allow_tot=not inc_measures,
                           sort_opt_allowed=sort_opt_allowed)
        
class DlgColConfig(DlgConfig):
    
    def __init__(self, parent, var_labels, node_ids, tree, inc_measures, 
                 sort_opt_allowed, has_col_vars=True):
        title = _("Configure Column Item")
        if inc_measures:
            self.measures = [
                (my_globals.FREQ, 
                    my_globals.measures_long_label_dic[my_globals.FREQ]), 
                (my_globals.ROWPCT, 
                    my_globals.measures_long_label_dic[my_globals.ROWPCT]),
                (my_globals.COLPCT, 
                    my_globals.measures_long_label_dic[my_globals.COLPCT])
                ]
            self.min_measure = my_globals.FREQ
        else:
            self.measures = []
            self.min_measure = None
        size = wx.DefaultSize
        DlgConfig.__init__(self, parent, var_labels, node_ids, tree, 
                           title, size, allow_tot=has_col_vars, 
                           sort_opt_allowed=sort_opt_allowed)
