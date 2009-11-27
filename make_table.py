from __future__ import print_function
import os
import pprint
import random
import sys
import wx

import my_globals
import demotables
import dimtables
import getdata
import output
import projects
import rawtables
import util

OUTPUT_MODULES = ["my_globals", "dimtables", "rawtables", "output", "getdata"]

# NB raw tables don't have measures
def get_default_measure(tab_type):
    "Get default measure appropriate for table type"
    if tab_type == my_globals.COL_MEASURES: 
        return my_globals.FREQ
    elif tab_type == my_globals.ROW_SUMM:
        return my_globals.MEAN
    else:
        raise Exception, "Only dimension tables have measures"

def GetColDets(coltree, colRoot, var_labels):
    """
    Get names and labels of columns actually selected in GUI column tree.
    Returns col_names, col_labels.
    """
    full_col_labels = util.getSubTreeItems(coltree, colRoot)
    split_col_tree_labels = full_col_labels.split(", ")        
    col_names = [getdata.extractChoiceDets(x)[0] for x in split_col_tree_labels]
    col_labels = [var_labels.get(x, x.title()) for x in col_names]
    return col_names, col_labels


class MakeTable(object):
    "Needed to split  modules for manageability"
        
    def UpdateVarDets(self):
        "Update all labels, including those already displayed"
        self.fil_var_dets = self.txtVarDetsFile.GetValue()
        self.var_labels, self.var_notes, self.var_types, self.val_dics = \
            projects.GetVarDets(self.fil_var_dets)
        # update dim trees
        rowdescendants = util.getTreeCtrlDescendants(self.rowtree, self.rowRoot)
        self.RefreshDescendants(self.rowtree, rowdescendants)
        coldescendants = util.getTreeCtrlDescendants(self.coltree, self.colRoot)
        self.RefreshDescendants(self.coltree, coldescendants)
        # update demo area
        self.demo_tab.var_labels = self.var_labels
        self.demo_tab.val_dics = self.val_dics
        self.UpdateDemoDisplay()
        
    def RefreshDescendants(self, tree, descendants):
        ""
        for descendant in descendants:
            var_name, unused = \
                getdata.extractChoiceDets(tree.GetItemText(descendant))
            fresh_label = getdata.getChoiceItem(self.var_labels, var_name)
            tree.SetItemText(descendant, fresh_label)

    # table type
    def OnTabTypeChange(self, event):
        "Respond to change of table type"
        self.UpdateByTabType()
    
    def UpdateByTabType(self):
        self.tab_type = self.radTabType.GetSelection() #for convenience
        #delete all row and col vars
        self.rowtree.DeleteChildren(self.rowRoot)
        self.coltree.DeleteChildren(self.colRoot)
        #link to appropriate demo table type
        titles = ["\"%s\"" % x for x \
                  in self.txtTitles.GetValue().split("\n")]
        Subtitles = ["\"%s\"" % x for x \
                     in self.txtSubtitles.GetValue().split("\n")]
        if self.tab_type == my_globals.COL_MEASURES:
            self.chkTotalsRow.SetValue(False)
            self.chkFirstAsLabel.SetValue(False)
            self.EnableOpts(enable=False)
            self.EnableRowSel(enable=True)
            self.EnableColButtons()
            self.demo_tab = demotables.GenDemoTable(txtTitles=self.txtTitles, 
                             txtSubtitles=self.txtSubtitles,
                             colRoot=self.colRoot,                               
                             rowRoot=self.rowRoot, 
                             rowtree=self.rowtree, 
                             coltree=self.coltree, 
                             col_no_vars_item=self.col_no_vars_item, 
                             var_labels=self.var_labels, 
                             val_dics=self.val_dics,
                             fil_css=self.fil_css)
        elif self.tab_type == my_globals.ROW_SUMM:
            self.chkTotalsRow.SetValue(False)
            self.chkFirstAsLabel.SetValue(False)
            self.EnableOpts(enable=False)
            self.EnableRowSel(enable=True)
            self.EnableColButtons()
            self.demo_tab = demotables.SummDemoTable(txtTitles=self.txtTitles, 
                             txtSubtitles=self.txtSubtitles,
                             colRoot=self.colRoot,                                  
                             rowRoot=self.rowRoot, 
                             rowtree=self.rowtree, 
                             coltree=self.coltree, 
                             col_no_vars_item=self.col_no_vars_item, 
                             var_labels=self.var_labels, 
                             val_dics=self.val_dics,
                             fil_css=self.fil_css)
        elif self.tab_type == my_globals.RAW_DISPLAY:
            self.EnableOpts(enable=True)
            self.EnableRowSel(enable=False)
            self.btnColConf.Disable()
            self.btnColAddUnder.Disable()
            self.demo_tab = demotables.DemoRawTable(txtTitles=self.txtTitles, 
                     txtSubtitles=self.txtSubtitles,                                 
                     colRoot=self.colRoot, 
                     coltree=self.coltree, 
                     flds=self.flds,
                     var_labels=self.var_labels,
                     val_dics=self.val_dics,
                     fil_css=self.fil_css,
                     chkTotalsRow=self.chkTotalsRow,
                     chkFirstAsLabel=self.chkFirstAsLabel)
        #in case they were disabled and then we changed tab type
        self.UpdateDemoDisplay()
        
    def EnableOpts(self, enable=True):
        "Enable (or disable) options"
        self.chkTotalsRow.Enable(enable)
        self.chkFirstAsLabel.Enable(enable)
        
    def OnChkTotalsRow(self, event):
        "Update display as total rows checkbox changes"
        self.UpdateDemoDisplay()

    def OnChkFirstAsLabel(self, event):
        "Update display as first column as label checkbox changes"
        self.UpdateDemoDisplay()
                
    # titles/subtitles
    def OnTitleChange(self, event):
        "Update display as titles change"
        self.UpdateDemoDisplay()

    def OnSubtitleChange(self, event):
        "Update display as subtitles change"
        self.UpdateDemoDisplay()
        
    # run 
    def too_long(self):
        # check not a massive report table
        too_long = False
        if self.tab_type == my_globals.RAW_DISPLAY:
            # get various db settings
            dbdetsobj = getdata.getDbDetsObj(self.dbe, self.default_dbs, 
                                             self.default_tbls, self.conn_dets)
            conn, cur = dbdetsobj.get_conn_cur()
            # count records in table
            quoter = getdata.get_obj_quoter_func(self.dbe)
            s = "SELECT COUNT(*) FROM %s" % quoter(self.tbl)
            cur.execute(s)
            n_rows = cur.fetchone()[0]
            conn.close()
            if n_rows > 500:
                if wx.MessageBox(_("This report has %s rows. "
                                   "Do you wish to run it?") % n_rows, 
                                   caption=_("LONG REPORT"), 
                                   style=wx.YES_NO) == wx.NO:
                    too_long = True
        return too_long
   
    def OnButtonRun(self, event):
        """
        Generate script to special location (INT_SCRIPT_PATH), 
            run script putting output in special location 
            (INT_REPORT_PATH) and into report file, and finally, 
            display html output.
        """
        debug = False
        run_ok, missing_dim, has_rows, has_cols = self.TableConfigOK()
        if run_ok:
            if self.too_long():
                return
            # hourglass cursor
            curs = wx.StockCursor(wx.CURSOR_WAIT)
            self.SetCursor(curs)
            if debug: print(self.fil_css)
            css_fils, css_idx = output.GetCssDets(self.fil_report, self.fil_css)
            script = self.getScript(has_rows, has_cols, css_idx)
            strContent = output.RunReport(OUTPUT_MODULES, self.fil_report, 
                self.chkAddToReport.IsChecked(), css_fils, script, 
                self.conn_dets, self.dbe, self.db, self.tbl, self.default_dbs, 
                self.default_tbls)
            # Return to normal cursor
            curs = wx.StockCursor(wx.CURSOR_ARROW)
            self.SetCursor(curs)
            output.DisplayReport(self, strContent)
        else:
            wx.MessageBox(_("Missing %s data") % missing_dim)

    # export script
    def OnButtonExport(self, event):
        """
        Export script for table to file currently displayed (if enough data).
        If the file doesn't exist, make one and add the preliminary code.
        If a file exists, but is empty, put the preliminary code in then
            the new exported script.
        If the file exists and is not empty, append the script on the end.
        """
        export_ok, missing_dim, has_rows, has_cols = self.TableConfigOK()
        if export_ok:
            css_fils, css_idx = output.GetCssDets(self.fil_report, self.fil_css)
            script = self.getScript(has_rows, has_cols, css_idx)
            output.ExportScript(script, self.fil_script, 
                                self.fil_report, css_fils, self.conn_dets, 
                                self.dbe, self.db, self.tbl, self.default_dbs, 
                                self.default_tbls)
        else:
            wx.MessageBox(_("Missing %s data") % missing_dim) 
    
    def getScript(self, has_rows, has_cols, css_idx):
        "Build script from inputs"
        script_lst = []
        # set up variables required for passing into main table instantiation
        if self.tab_type in [my_globals.COL_MEASURES, my_globals.ROW_SUMM]:
            script_lst.append("tree_rows = dimtables.DimNodeTree()")
            for child in util.getTreeCtrlChildren(tree=self.rowtree, 
                                                  parent=self.rowRoot):
                child_fld_name, unused = \
                    getdata.extractChoiceDets(self.rowtree.GetItemText(child))
                self.addToParent(script_lst=script_lst, tree=self.rowtree, 
                             parent=self.rowtree, 
                             parent_node_label="tree_rows",
                             child=child, child_fld_name=child_fld_name)
            script_lst.append("tree_cols = dimtables.DimNodeTree()")
            if has_cols:
                for child in util.getTreeCtrlChildren(tree=self.coltree, 
                                                      parent=self.colRoot):
                    child_fld_name, unused = \
                        getdata.extractChoiceDets(\
                                            self.coltree.GetItemText(child))
                    self.addToParent(script_lst=script_lst, tree=self.coltree, 
                                 parent=self.coltree, 
                                 parent_node_label="tree_cols",
                                 child=child, child_fld_name=child_fld_name)
        elif self.tab_type == my_globals.RAW_DISPLAY:
            col_names, col_labels = GetColDets(self.coltree, self.colRoot, 
                                               self.var_labels)
            script_lst.append("col_names = " + pprint.pformat(col_names))
            script_lst.append("col_labels = " + pprint.pformat(col_labels))
            script_lst.append("flds = " + pprint.pformat(self.flds))
            script_lst.append("var_labels = " + pprint.pformat(self.var_labels))
            script_lst.append("val_dics = " + pprint.pformat(self.val_dics))
        # process title dets
        titles = ["%s" % x for x \
                  in self.txtTitles.GetValue().split("\n")]
        subtitles = ["%s" % x for x \
                     in self.txtSubtitles.GetValue().split("\n")]
        # NB the following text is all going to be run
        if self.tab_type == my_globals.COL_MEASURES:
            script_lst.append("tab_test = dimtables.GenTable(titles=" + \
                              unicode(titles) + ",\n    subtitles=" + \
                              unicode(subtitles) + \
                              ",\n    dbe=\"" + self.dbe + \
                              "\",\n    datasource=\"" + self.tbl + \
                              "\", cur=cur, tree_rows=tree_rows, " + \
                              "tree_cols=tree_cols)")
        elif self.tab_type == my_globals.ROW_SUMM:
            script_lst.append("tab_test = dimtables.SummTable(titles=" + \
                              unicode(titles) + ",\n    subtitles=" + \
                              unicode(subtitles) + \
                              ",\n    dbe=\"" + self.dbe + \
                              "\",\n    datasource=\"" + self.tbl + \
                              "\", cur=cur, tree_rows=tree_rows, " + \
                              "tree_cols=tree_cols)")
        elif self.tab_type == my_globals.RAW_DISPLAY:
            tot_rows = "True" if self.chkTotalsRow.IsChecked() else "False"
            first_label = "True" if self.chkFirstAsLabel.IsChecked() \
                else "False"
            script_lst.append("tab_test = rawtables.RawTable(titles=" + \
                unicode(titles) + ",\n    subtitles=" + \
                unicode(subtitles) + \
                ",\n    dbe=\"" + self.dbe + \
                "\",\n    datasource=\"%s\"" % self.tbl + ", cur=cur," + \
                " col_names=col_names, col_labels=col_labels, flds=flds, " + \
                "\n    var_labels=var_labels, val_dics=val_dics, " + \
                "add_total_row=%s, " % tot_rows + \
                "\nfirst_col_as_label=%s)" % first_label)
        if self.tab_type in [my_globals.COL_MEASURES, my_globals.ROW_SUMM]:
            script_lst.append("tab_test.prepTable(%s)" % css_idx)
            script_lst.append("max_cells = 5000")
            script_lst.append("if tab_test.getCellNOk(max_cells=max_cells):")
            script_lst.append("    " + \
                        "fil.write(tab_test.getHTML(%s, " % css_idx + \
                        "page_break_after=False))")
            script_lst.append("else:")
            script_lst.append("    " + \
                              "fil.write(\"Table not made.  Number \" + \\" + \
                              "\n        \"of cells exceeded limit \" + \\" + \
                              "\n        \"of %s\" % max_cells)")
        else:
            script_lst.append("fil.write(tab_test.getHTML(%s, " % css_idx + \
                              "page_break_after=False))")
        return "\n".join(script_lst)

    def addToParent(self, script_lst, tree, parent, parent_node_label, 
                    child, child_fld_name):
        """
        Add script code for adding child nodes to parent nodes.
        tree - TreeListCtrl tree
        parent, child - TreeListCtrl items
        parent_node_label - for parent_node_label.addChild(...)
        child_fld_name - used to get variable label, and value labels
            from relevant dics; plus as the field name
        """
        # add child to parent
        if child == self.col_no_vars_item:
            fld_arg = ""
        else:
            fld_arg = "fld=\"%s\", " % child_fld_name
        #print(self.var_labels) #debug
        #print(self.val_dics) #debug
        var_label = self.var_labels.get(child_fld_name, 
                                        child_fld_name.title())
        labels_dic = self.val_dics.get(child_fld_name, {})
        child_node_label = "node_" + "_".join(child_fld_name.split(" "))
        item_conf = tree.GetItemPyData(child)
        measures_lst = item_conf.measures_lst
        measures = ", ".join([("my_globals." + \
                               my_globals.script_export_measures_dic[x]) for \
                               x in measures_lst])
        if measures:
            measures_arg = ", \n    measures=[%s]" % measures
        else:
            measures_arg = ""
        if item_conf.has_tot:
            tot_arg = ", \n    has_tot=True"
        else:
            tot_arg = ""
        sort_order_arg = ", \n    sort_order=\"%s\"" % \
            item_conf.sort_order
        numeric_arg = ", \n    bolnumeric=%s" % item_conf.bolnumeric
        script_lst.append(child_node_label + \
                          " = dimtables.DimNode(" + fld_arg + \
                          "\n    label=\"" + unicode(var_label) + \
                          "\", \n    labels=" + unicode(labels_dic) + \
                          measures_arg + tot_arg + sort_order_arg + \
                          numeric_arg + ")")
        script_lst.append("%s.addChild(%s)" % (parent_node_label, 
                                               child_node_label))
        # send child through for each grandchild
        for grandchild in util.getTreeCtrlChildren(tree=tree, 
                                                   parent=child):
            grandchild_fld_name, unused = \
                getdata.extractChoiceDets(tree.GetItemText(grandchild))
            self.addToParent(script_lst=script_lst, tree=tree, 
                             parent=child, 
                             parent_node_label=child_node_label,
                             child=grandchild, 
                             child_fld_name=grandchild_fld_name)
    
    def OnButtonHelp(self, event):
        """
        Export script if enough data to create table.
        """
        wx.MessageBox("Not available yet in this version")
        
    # clear button
    def ClearDims(self):
        "Clear dim trees"
        self.rowtree.DeleteChildren(self.rowRoot)
        self.coltree.DeleteChildren(self.colRoot)
        self.UpdateDemoDisplay()

    #def OnClearEnterWindow(self, event):
    #    "Hover over CLEAR button"
    #    self.statusbar.SetStatusText("Clear settings")

    def OnButtonClear(self, event):
        "Clear all settings"
        self.txtTitles.SetValue("")        
        self.txtSubtitles.SetValue("")
        self.radTabType.SetSelection(my_globals.COL_MEASURES)
        self.tab_type = my_globals.COL_MEASURES
        self.rowtree.DeleteChildren(self.rowRoot)
        self.coltree.DeleteChildren(self.colRoot)
        self.UpdateByTabType()
        self.UpdateDemoDisplay()

    def OnClose(self, event):
        "Close app"
        try:
            self.conn.close()
            # add end to each open script file and close.
            for fil_script in self.open_scripts:
                # add ending code to script
                f = file(fil_script, "a")
                output.AddClosingScriptCode(f)
                f.close()
        except Exception:
            pass
        finally:
            self.Destroy()
            event.Skip()
            
    # demo table display
    def UpdateDemoDisplay(self):
        """
        Update demo table display with random data.
        Always use one css only (the current one).
        """
        demo_tbl_html = self.demo_tab.getDemoHTMLIfOK(css_idx=0)
        #print("\n" + demo_tbl_html + "\n") #debug
        self.html.ShowHTML(demo_tbl_html)

    def TableConfigOK(self):
        """
        Is the table configuration sufficient to export as script or HTML?
        Summary only requires rows (can have both)
        Raw only requires cols (and cannot have rows)
        And gen requires both        
        """
        has_rows = util.getTreeCtrlChildren(tree=self.rowtree, 
                                    parent=self.rowRoot)
        has_cols = util.getTreeCtrlChildren(tree=self.coltree, 
                                         parent=self.colRoot)
        export_ok = False
        missing_dim = None
        if self.tab_type == my_globals.ROW_SUMM:
            if has_rows:
                export_ok = True
            else:
                missing_dim = _("row")
        elif self.tab_type == my_globals.RAW_DISPLAY:
            if has_cols:
                export_ok = True
            else:
                missing_dim = _("column")
        elif self.tab_type == my_globals.COL_MEASURES:
            if has_rows and has_cols:
                export_ok = True
            else:
                missing_dim = _("row and column")
        return (export_ok, missing_dim, has_rows, has_cols)
            

class ItemConfig(object):
    """
    Item config storage and retrieval.
    Has: measures, has_tot, sort order, bolnumeric
    """
    
    def __init__(self, measures_lst=None, has_tot=False, 
                 sort_order=my_globals.SORT_NONE, bolnumeric=False):
        if measures_lst:
            self.measures_lst = measures_lst
        else:
            self.measures_lst = []
        self.has_tot = has_tot
        self.sort_order = sort_order
        self.bolnumeric = bolnumeric
    
    def hasData(self):
        "Has the item got any extra config e.g. measures, a total?"
        return self.measures_lst or self.has_tot or \
            self.sort_order != my_globals.SORT_NONE
    
    def getSummary(self, verbose=False):
        "String summary of data"
        str_parts = []
        total_part = _("Has TOTAL") if self.has_tot else None
        if total_part:
            str_parts.append(total_part)
        if self.sort_order == my_globals.SORT_NONE:
            sort_order_part = None
        elif self.sort_order == my_globals.SORT_LABEL:
            sort_order_part = _("Sort by Label")
        elif self.sort_order == my_globals.SORT_FREQ_ASC:
            sort_order_part = _("Sort by Freq (Asc)")
        elif self.sort_order == my_globals.SORT_FREQ_DESC:
            sort_order_part = _("Sort by Freq (Desc)")            
        if sort_order_part:
            str_parts.append(sort_order_part)
        if verbose:
            if self.bolnumeric:
                str_parts.append(_("Numeric"))
            else:
                str_parts.append(_("Not numeric"))
        measures = ", ".join(self.measures_lst)
        measures_part = _("Measures: %s") % measures if measures else None
        if measures_part:
            str_parts.append(measures_part)
        return "; ".join(str_parts)
