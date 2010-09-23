#! /usr/bin/env python
# -*- coding: utf-8 -*-

import boomslang
import wx
import wxmpl
import pylab # must import after wxmpl so matplotlib.use() is always first

import my_globals as mg
import lib
import core_stats
import wxmpl

def gen_config(axes_labelsize=14, xtick_labelsize=10, ytick_labelsize=10):
    params = {"axes.labelsize": axes_labelsize,
              "xtick.labelsize": xtick_labelsize,
              "ytick.labelsize": ytick_labelsize,
              }
    pylab.rcParams.update(params)

def config_clustered_barchart(grid_bg, bar_colours, line_colour, plot, 
                              var_label_a, y_label, val_labels_a_n, 
                              val_labels_a, val_labels_b, as_in_bs_lst):
    """
    Clustered bar charts
    Var A defines the clusters and B the split within the clusters
    e.g. gender vs country = gender as boomslang bars and country as values 
        within bars.
    """
    debug = False
    clustered_bars = boomslang.ClusteredBars()
    clustered_bars.grid_bg = grid_bg
    for i, val_label_b in enumerate(val_labels_b):
        cluster = boomslang.Bar()
        x_vals = range(val_labels_a_n)
        cluster.xValues = x_vals
        y_vals = as_in_bs_lst[i]
        if debug:
            print("x_vals: %s" % x_vals)
            print("y_vals: %s" % y_vals)
        cluster.yValues = y_vals
        cluster.color = bar_colours[i]
        cluster.edgeColor = "white"
        cluster.label = val_label_b
        clustered_bars.add(cluster)
    clustered_bars.spacing = 0.5
    clustered_bars.xTickLabels = val_labels_a
    if debug: print("xTickLabels: %s" % clustered_bars.xTickLabels)
    plot.add(clustered_bars)
    plot.setXLabel(var_label_a)
    plot.setYLabel(y_label)

def config_hist(fig, vals, var_label, hist_label=None, thumbnail=False, 
                grid_bg=mg.MPL_BGCOLOR, bar_colour=mg.MPL_FACECOLOR, 
                line_colour=mg.MPL_NORM_LINE_COLOR):    
    """
    Configure histogram with subplot of normal distribution curve.
    Size is set externally. 
    """
    debug = False
    axes = fig.gca()
    rect = axes.patch
    rect.set_facecolor(grid_bg)
    n_vals = len(vals)
    nbins = lib.get_nbins_from_vals(vals)    
    if thumbnail:
        nbins = round(nbins/2, 0)
        if nbins < 5: 
            nbins = 5
        axes.axis("off")
        normal_line_width = 1
    else:
        axes.set_xlabel(var_label)
        axes.set_ylabel('P')
        if not hist_label:
            hist_label = _("Histogram for %s") % var_label
        axes.set_title(hist_label)
        normal_line_width = 4
    n, bins, patches = axes.hist(vals, nbins, normed=1, facecolor=bar_colour,
                                 edgecolor=line_colour)
    if debug: print(n, bins, patches)
    mu = core_stats.mean(vals)
    sigma = core_stats.stdev(vals)
    y = pylab.normpdf(bins, mu, sigma)
    l = axes.plot(bins, y,  color=line_colour, linewidth=normal_line_width)

def config_scatterplot(grid_bg, dot_colour, line_colour, fig, sample_a, 
                       sample_b, label_a, label_b, a_vs_b):
    """
    Configure scatterplot with line of best fit.
    Size is set externally. 
    """
    pylab.plot(sample_a, sample_b, 'o', color=dot_colour, label=a_vs_b, 
               markeredgecolor=line_colour)
    p = pylab.polyfit(sample_a, sample_b, 1)
    pylab.plot(sample_a, pylab.polyval(p, sample_a), u"-", 
               color=line_colour, linewidth=4, 
               label="Line of best fit")
    axes = fig.gca()
    axes.set_xlabel(label_a)
    axes.set_ylabel(label_b)
    rect = axes.patch
    rect.set_facecolor(grid_bg)
    pylab.legend(loc="best")

        
class HistDlg(wxmpl.PlotDlg):
    def __init__(self, parent, vals, var_label, hist_label):
        wxmpl.PlotDlg.__init__(self, parent, 
            title=_("Similar to normal distribution curve?"), size=(10.0, 6.0), 
            dpi=96)
        btn_ok = wx.Button(self, wx.ID_OK)
        btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        self.sizer.Add(btn_ok, 0, wx.ALIGN_RIGHT|wx.ALL, 10)
        fig = self.get_figure()
        config_hist(fig, vals, var_label, hist_label)
        self.draw()
        self.SetSizer(self.sizer)
        self.Fit()

    def on_ok(self, event):
        self.Destroy()