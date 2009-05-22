import wx
import random
from datetime import datetime
import pprint
import sys
import os

import demotables
import dimtables
import getdata
import make_table_gui
import projects
import rawtables
import showhtml
import table_entry
import tabreports
import util

SCRIPT_PATH = util.get_script_path()
LOCAL_PATH = util.get_local_path()
HAS_TOTAL = "Total" #doubles as display label
COL_MEASURES = 0 #indexes in tab type
ROW_SUMM = 1
RAW_DISPLAY = 2

COL_MEASURES_TREE_LBL = "Column measures"

# NB raw tables don't have measures
def get_default_measure(tab_type):
    "Get default measure appropriate for table type"
    if tab_type == COL_MEASURES: 
        return dimtables.FREQ
    elif tab_type == ROW_SUMM:
        return dimtables.MEAN
    else:
        raise Exception, "Only dimension tables have measures"
    
def AddClosingScriptCode(f):
    "Add ending code to script.  Nb leaves open file."
    f.write("\n\n#" + "-"*50 + "\n")
    f.write("\nfil.write(tabreports.getHtmlFtr())")
    f.write("\nfil.close()")

def getVarItem(var_labels, var_name):
    return "%s (%s)" % (var_labels.get(var_name, var_name.title()),
                        var_name)

def extractVarDets(choice_text):
    """
    Extract var_name, var_label from tree item e.g. return "gender"
        and "Gender" from "Gender (gender)".
    """
    if choice_text == COL_MEASURES_TREE_LBL:
        var_name = choice_text
        var_label = choice_text
    else:
        start_idx = choice_text.index("(") + 1
        end_idx = choice_text.index(")")
        var_name = choice_text[start_idx:end_idx]
        var_label = choice_text[:start_idx - 2]
    return var_name, var_label

def GetColDets(coltree, colRoot, var_labels):
    """
    Get names and labels of columns actually selected in GUI column tree.
    Returns col_names, col_labels.
    """
    full_col_labels = util.getSubTreeItems(coltree, colRoot)
    split_col_tree_labels = full_col_labels.split(", ")        
    col_names = [extractVarDets(x)[0] for x in split_col_tree_labels]
    col_labels = [var_labels.get(x, x.title()) for x in col_names]
    return col_names, col_labels


class MakeTable(object):
    "Needed to split  modules for managability"

    # database/ tables (and views)
    def OnDatabaseSel(self, event):
        """
        Reset dbe, database, cursor, tables, table, tables dropdown, 
            fields, has_unique, and idxs after a database selection.
        Clear dim areas.
        """
        getdata.ResetDataAfterDbSel(self)
        self.ClearDims()
                
    def OnTableSel(self, event):
        """
        Reset table, fields, has_unique, and idxs.
        Clear dim areas.
        """       
        getdata.ResetDataAfterTblSel(self)
        self.ClearDims()

    # report output
    def OnButtonReportPath(self, event):
        "Open dialog and takes the report file selected (if any)"
        dlgGetFile = wx.FileDialog(self, "Choose a report output file:", 
            defaultDir=os.path.join(LOCAL_PATH, "reports"), 
            defaultFile="", 
            wildcard="HTML files (*.htm)|*.htm|HTML files (*.html)|*.html")
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            self.fil_report = "%s" % dlgGetFile.GetPath()
            self.txtReportFile.SetValue(self.fil_report)
        dlgGetFile.Destroy()
        
    #def ReportPathEnterWindow(self, event):
    #    "Hover over Report Path Browse button"
    #    self.statusbar.SetStatusText("Select html file for reporting ...")
    
    def OnReportFileLostFocus(self, event):
        "Reset report output file"
        self.fil_report = self.txtReportFile.GetValue()
    
    # script output
    def OnButtonScriptPath(self, event):
        "Open dialog and takes the script file selected (if any)"
        dlgGetFile = wx.FileDialog(self, "Choose a file to export scripts to:", 
            defaultDir=os.path.join(LOCAL_PATH, "scripts"), 
            defaultFile="", wildcard="Scripts (*.py)|*.py")
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            self.fil_script = "%s" % dlgGetFile.GetPath()
            self.txtScriptFile.SetValue(self.fil_script)
        dlgGetFile.Destroy()
    
    #def ScriptPathEnterWindow(self, event):
    #    "Hover over Script Path Browse button"
    #    self.statusbar.SetStatusText("Select output script file ...")

    def OnScriptFileLostFocus(self, event):
        "Reset script file"
        self.fil_script = self.txtScriptFile.GetValue()
    
    # label config
    def OnLabelFileLostFocus(self, event):
        ""
        self.UpdateLabels()

    def OnButtonLabelPath(self, event):
        "Open dialog and takes the labels file selected (if any)"
        dlgGetFile = wx.FileDialog(self, "Choose a label config file:", 
            defaultDir=os.path.join(LOCAL_PATH, "lbls"), 
            defaultFile="", wildcard="Config files (*.lbls)|*.lbls")
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            fil_labels = "%s" % dlgGetFile.GetPath()
            self.txtLabelsFile.SetValue(fil_labels)
            self.UpdateLabels()
        dlgGetFile.Destroy()
        
    def UpdateLabels(self):
        "Update all labels, including those already displayed"
        self.fil_labels = self.txtLabelsFile.GetValue()
        self.var_labels, self.var_notes, self.val_dics = \
            projects.GetLabels(self.fil_labels)
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
            var_name, _ = extractVarDets(tree.GetItemText(descendant))
            fresh_label = getVarItem(self.var_labels, var_name)
            tree.SetItemText(descendant, fresh_label)

    #def LabelPathEnterWindow(self, event):
    #    "Hover over Label Path Browse button"
    #    self.statusbar.SetStatusText("Select source of variable " + \
    #                                 "and value labels ...")
        
    # css table style
    def OnButtonCssPath(self, event):
        "Open dialog and takes the css file selected (if any)"
        dlgGetFile = wx.FileDialog(self, "Choose a css table style file:", 
            defaultDir=os.path.join(LOCAL_PATH, "css"), 
            defaultFile="", 
            wildcard="CSS files (*.css)|*.css")
            #MUST have a parent to enforce modal in Windows
        if dlgGetFile.ShowModal() == wx.ID_OK:
            fil_css = "%s" % dlgGetFile.GetPath()
            self.txtCssFile.SetValue(fil_css)
            self.UpdateCss()
        dlgGetFile.Destroy()
    
    def UpdateCss(self):
        "Update css, including for demo table"
        self.fil_css = self.txtCssFile.GetValue()
        self.demo_tab.fil_css = self.fil_css
        self.UpdateDemoDisplay()
        
    #def CssPathEnterWindow(self, event):
    #    "Hover over Css Path Browse button"
    #    self.statusbar.SetStatusText("Select css table style file for " + \
    #                                 "reporting ...")
    
    def OnCssFileLostFocus(self, event):
        "Reset css file"
        self.UpdateCss()

    # table type
    def OnTabTypeChange(self, event):
        "Respond to change of table type"
        self.tab_type = self.radTabType.GetSelection() #for convenience
        #delete all row and col vars
        self.rowtree.DeleteChildren(self.rowRoot)
        self.coltree.DeleteChildren(self.colRoot)
        #link to appropriate demo table type
        titles = ["\"%s\"" % x for x \
                  in self.txtTitles.GetValue().split("\n")]
        Subtitles = ["\"%s\"" % x for x \
                     in self.txtSubtitles.GetValue().split("\n")]
        if self.tab_type == COL_MEASURES:
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
        elif self.tab_type == ROW_SUMM:
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
        elif self.tab_type == RAW_DISPLAY:
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
    def OnButtonRun(self, event):
        """
        Generate script to special location (INT_SCRIPT_PATH), 
            run script putting output in special location 
            (INT_REPORT_PATH), display html output.
        """
        run_ok, missing_dim, has_rows, has_cols = self.TableConfigOK()
        if run_ok:
            # hourglass cursor
            curs = wx.StockCursor(wx.CURSOR_WAIT)
            self.SetCursor(curs)
            #self.statusbar.SetStatusText("Please wait for report " + \
            #                             "to be produced")   
            # generate script
            f = file(projects.INT_SCRIPT_PATH, "w")
            self.InsertPrelimCode(fil=f, fil_report=projects.INT_REPORT_PATH)
            self.AppendExportedScript(f, has_rows, has_cols)
            AddClosingScriptCode(f)
            f.close()
            # run script
            f = file(projects.INT_SCRIPT_PATH, "r")
            script = f.read()
            f.close()
            exec(script)
            f = file(projects.INT_REPORT_PATH, "r")
            strContent = f.read()
            f.close()
            # Return to normal cursor
            curs = wx.StockCursor(wx.CURSOR_ARROW)
            self.SetCursor(curs)
            #self.statusbar.SetStatusText("")
            # display results
            dlg = showhtml.ShowHTML(parent=self, content=strContent, 
                                    file_name=projects.INT_REPORT_FILE, 
                                    title="Report", 
                                    print_folder=projects.INTERNAL_FOLDER)
            dlg.ShowModal()
            dlg.Destroy()
        else:
            wx.MessageBox("Missing %s data" % missing_dim)

    #def OnRunEnterWindow(self, event):
    #    "Hover over RUN button"
    #    self.statusbar.SetStatusText("Export HTML table to file")
        
    # export script
    def OnButtonExport(self, event):
        """
        Export script if enough data to create table.
        """
        export_ok, missing_dim, has_rows, has_cols = self.TableConfigOK()
        if export_ok:
            self.ExportScript(has_rows, has_cols)
        else:
            wx.MessageBox("Missing %s data" % missing_dim) 
    
    def ExportScript(self, has_rows, has_cols):
        """
        Export script for table to file currently displayed.
        If the file doesn't exist, make one and add the preliminary code.
        If a file exists, but is empty, put the preliminary code in then
            the new exported script.
        If the file exists and is not empty, append the script on the end.
        """
        if self.fil_script in self.open_scripts:
            # see if empty or not
            f = file(self.fil_script, "r+")
            lines = f.readlines()
            empty_fil = False if lines else True            
            if empty_fil:
                self.InsertPrelimCode(fil=f)
            # insert exported script
            self.AppendExportedScript(f, has_rows, has_cols)
        else:
            # add file name to list, create file, insert preliminary code, 
            # and insert exported script.
            self.open_scripts.append(self.fil_script)
            f = file(self.fil_script, "w")
            self.InsertPrelimCode(fil=f)
            self.AppendExportedScript(f, has_rows, has_cols)
        f.close()
    
    def InsertPrelimCode(self, fil, fil_report=None):
        """
        Insert preliminary code at top of file.
        fil - open file handle ready for writing.
        NB files always start from scratch per make tables session.
        """         
        fil.write("#! /usr/bin/env python")
        fil.write("\n# -*- coding: utf-8 -*-\n")            
        fil.write("\nimport dimtables")
        fil.write("\nimport rawtables")
        fil.write("\nimport tabreports")
        fil.write("\nimport getdata\n")
        if not fil_report:
            fil_report = self.fil_report
        fil.write("\nfil = file(r\"%s\", \"w\")" % fil_report)
        fil.write("\nfil.write(tabreports.getHtmlHdr(\"Report(s)\", " + \
                  "fil_css=r\"%s\"))" % self.fil_css)
    
    def AppendExportedScript(self, fil, has_rows, has_cols):
        """
        Append exported script onto file.
        fil - open file handle ready for writing
        """
        datestamp = datetime.now().strftime("Script " + \
                                        "exported %d/%m/%Y at %I:%M %p")
        # Fresh connection for each in case it changes in between tables
        getdata.setDbInConnDets(self.dbe, self.conn_dets, self.db)
        conn_dets_str = pprint.pformat(self.conn_dets)
        fil.write("\nconn_dets = %s" % conn_dets_str)
        fil.write("\nconn, cur, dbs, tbls, flds, has_unique, idxs = \\" + \
            "\n    getdata.getDbDetsObj(" + \
            """dbe="%s", conn_dets=conn_dets, \n    db="%s", tbl="%s")""" % \
                (self.dbe, self.db, self.tbl_name) + \
            ".getDbDets()" )
        fil.write("\n\n#%s\n#%s\n" % ("-"*50, datestamp))
        fil.write(self.getScript(has_rows, has_cols))
        fil.write("\nconn.close()")
        
    def getScript(self, has_rows, has_cols):
        "Build script from inputs"
        script_lst = []
        # set up variables required for passing into main table instantiation
        if self.tab_type in [COL_MEASURES, ROW_SUMM]:
            script_lst.append("tree_rows = dimtables.DimNodeTree()")
            for child in util.getTreeCtrlChildren(tree=self.rowtree, 
                                                  parent=self.rowRoot):
                child_fld_name, _ = \
                    extractVarDets(self.rowtree.GetItemText(child))
                self.addToParent(script_lst=script_lst, tree=self.rowtree, 
                             parent=self.rowtree, 
                             parent_node_label="tree_rows",
                             child=child, child_fld_name=child_fld_name)
            script_lst.append("tree_cols = dimtables.DimNodeTree()")
            if has_cols:
                for child in util.getTreeCtrlChildren(tree=self.coltree, 
                                                      parent=self.colRoot):
                    child_fld_name, _ = \
                        extractVarDets(self.coltree.GetItemText(child))
                    self.addToParent(script_lst=script_lst, tree=self.coltree, 
                                 parent=self.coltree, 
                                 parent_node_label="tree_cols",
                                 child=child, child_fld_name=child_fld_name)
        elif self.tab_type == RAW_DISPLAY:
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
        if self.tab_type == COL_MEASURES:
            script_lst.append("tab_test = dimtables.GenTable(titles=" + \
                              str(titles) + ",\n    subtitles=" + \
                              str(subtitles) + \
                              ",\n    dbe=\"" + self.dbe + \
                              "\",\n    datasource=\"" + self.tbl_name + \
                              "\", cur=cur, tree_rows=tree_rows, " + \
                              "tree_cols=tree_cols)")
        elif self.tab_type == ROW_SUMM:
            script_lst.append("tab_test = dimtables.SummTable(titles=" + \
                              str(titles) + ",\n    subtitles=" + \
                              str(subtitles) + \
                              ",\n    dbe=\"" + self.dbe + \
                              "\",\n    datasource=\"" + self.tbl_name + \
                              "\", cur=cur, tree_rows=tree_rows, " + \
                              "tree_cols=tree_cols)")
        elif self.tab_type == RAW_DISPLAY:
            tot_rows = "True" if self.chkTotalsRow.IsChecked() else "False"
            first_label = "True" if self.chkFirstAsLabel.IsChecked() \
                else "False"
            script_lst.append("tab_test = rawtables.RawTable(titles=" + \
                str(titles) + ",\n    subtitles=" + \
                str(subtitles) + \
                ",\n    dbe=\"" + self.dbe + \
                "\",\n    datasource=\"%s\"" % self.tbl_name + ", cur=cur," + \
                " col_names=col_names, col_labels=col_labels, flds=flds, " + \
                "\n    var_labels=var_labels, val_dics=val_dics, " + \
                "add_total_row=%s, " % tot_rows + \
                "\nfirst_col_as_label=%s)" % first_label)
        if self.tab_type in [COL_MEASURES, ROW_SUMM]:
            script_lst.append("tab_test.prepTable()")
            script_lst.append("max_cells = 5000")
            script_lst.append("if tab_test.getCellNOk(max_cells=max_cells):")
            script_lst.append("    fil.write(tab_test.getHTML(page_break_after=False))")
            script_lst.append("else:")
            script_lst.append("    fil.write(\"Table not made.  Number \" + \\" + \
                              "\n        \"of cells exceeded limit \" + \\" + \
                              "\n        \"of %s\" % max_cells)")
        else:
            script_lst.append("fil.write(tab_test.getHTML(page_break_after=False))")
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
        #print self.var_labels #debug
        #print self.val_dics #debug
        var_label = self.var_labels.get(child_fld_name, 
                                        child_fld_name.title())
        labels_dic = self.val_dics.get(child_fld_name, {})
        child_node_label = "node_" + "_".join(child_fld_name.split(" "))
        item_conf = tree.GetItemPyData(child)
        measures_lst = item_conf.measures_lst
        measures = ", ".join([("dimtables." + \
                               dimtables.script_export_measures_dic[x]) for \
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
                          "\n    label=\"" + str(var_label) + \
                          "\", \n    labels=" + str(labels_dic) + \
                          measures_arg + tot_arg + sort_order_arg + \
                          numeric_arg + ")")
        script_lst.append("%s.addChild(%s)" % (parent_node_label, 
                                               child_node_label))
        # send child through for each grandchild
        for grandchild in util.getTreeCtrlChildren(tree=tree, 
                                                   parent=child):
            grandchild_fld_name, _ = \
                extractVarDets(tree.GetItemText(grandchild))
            self.addToParent(script_lst=script_lst, tree=tree, 
                             parent=child, 
                             parent_node_label=child_node_label,
                             child=grandchild, 
                             child_fld_name=grandchild_fld_name)
    
    #def OnExportEnterWindow(self, event):
    #    "Hover over EXPORT button"
    #    self.statusbar.SetStatusText("Export python code for making " + \
    #                                 "table to file")
        
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
        self.radTabType.SetSelection(COL_MEASURES)
        self.tab_type = COL_MEASURES
        self.rowtree.DeleteChildren(self.rowRoot)
        self.coltree.DeleteChildren(self.colRoot)
        self.UpdateDemoDisplay()
    
    # help
    #def OnHelpEnterWindow(self, event):
    #    "Hover over HELP button"
    #    self.statusbar.SetStatusText("Get help")    
        
    # close
    #def OnCloseEnterWindow(self, event):
    #    "Hover over CLOSE button"
    #    self.statusbar.SetStatusText("Close application")

    def OnClose(self, event):
        "Close app"
        try:
            self.conn.close()
            # add end to each open script file and close.
            for fil_script in self.open_scripts:
                # add ending code to script
                f = file(fil_script, "a")
                AddClosingScriptCode(f)
                f.close()
        except Exception:
            pass
        finally:
            self.Destroy()
            
    # demo table display
    def UpdateDemoDisplay(self):
        "Update demo table display with random data"
        demo_tbl_html = self.demo_tab.getDemoHTMLIfOK()
        #print "\n" + demo_tbl_html + "\n" #debug
        self.html.ShowHTML(demo_tbl_html)
        
    # misc
    #def BlankStatusBar(self, event):
    #    """Blank the status bar"""
    #    self.statusbar.SetStatusText("")

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
        if self.tab_type == ROW_SUMM:
            if has_rows:
                export_ok = True
            else:
                missing_dim = "row"
        elif self.tab_type == RAW_DISPLAY:
            if has_cols:
                export_ok = True
            else:
                missing_dim = "column"
        elif self.tab_type == COL_MEASURES:
            if has_rows and has_cols:
                export_ok = True
            else:
                missing_dim = "row and column"
        return (export_ok, missing_dim, has_rows, has_cols)
            

class ItemConfig(object):
    """
    Item config storage and retrieval.
    Has: measures, has_tot, sort order, bolnumeric
    """
    
    def __init__(self, measures_lst=None, has_tot=False, 
                 sort_order=dimtables.SORT_NONE, bolnumeric=False):
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
            self.sort_order != dimtables.SORT_NONE
    
    def getSummary(self, verbose=False):
        "String summary of data"
        str_parts = []
        total_part = "Has TOTAL" if self.has_tot else None
        if total_part:
            str_parts.append(total_part)
        if self.sort_order == dimtables.SORT_NONE:
            sort_order_part = None
        elif self.sort_order == dimtables.SORT_LABEL:
            sort_order_part = "Sort by Label"
        elif self.sort_order == dimtables.SORT_FREQ_ASC:
            sort_order_part = "Sort by Freq (Asc)"
        elif self.sort_order == dimtables.SORT_FREQ_DESC:
            sort_order_part = "Sort by Freq (Desc)"            
        if sort_order_part:
            str_parts.append(sort_order_part)
        if verbose:
            if self.bolnumeric:
                str_parts.append("Numeric")
            else:
                str_parts.append("Not numeric")
        measures = ", ".join(self.measures_lst)
        measures_part = "Measures: %s" % measures if measures else None
        if measures_part:
            str_parts.append(measures_part)
        return "; ".join(str_parts)
