#! /usr/bin/env python
# -*- coding: utf-8 -*-

import boomslang
import wx
import wxmpl
import pylab # must import after wxmpl so matplotlib.use() is always first

import my_globals
import core_stats
import wxmpl

def gen_config(axes_labelsize=14, xtick_labelsize=10, ytick_labelsize=10):
    params = {"axes.labelsize": axes_labelsize,
              "xtick.labelsize": xtick_labelsize,
              "ytick.labelsize": ytick_labelsize,
              }
    pylab.rcParams.update(params)

def config_clustered_barchart(plot, var_label_a, y_label, val_labels_a_n, 
                              val_labels_a, val_labels_b, as_in_bs_lst):
    """
    Clustered bar charts
    Var A defines the clusters and B the split within the clusters
    e.g. gender vs country = gender as boomslang bars and country as values 
        within bars.
    """
    debug = False
    # only need 6 because program limits to that. See core_stats.get_obs_exp().
    colours = ["#333435", "#CCD9D7", "white", "#909090", "black", "#333345"]
    clustered_bars = boomslang.ClusteredBars()
    for i, val_label_b in enumerate(val_labels_b):
        cluster = boomslang.Bar()
        x_vals = range(val_labels_a_n)
        cluster.xValues = x_vals
        y_vals = as_in_bs_lst[i]
        if debug:
            print("x_vals: %s" % x_vals)
            print("y_vals: %s" % y_vals)
        cluster.yValues = y_vals
        cluster.color = colours[i]
        cluster.label = val_label_b
        clustered_bars.add(cluster)
    clustered_bars.spacing = 0.5
    clustered_bars.xTickLabels = val_labels_a
    if debug: print("xTickLabels: %s" % clustered_bars.xTickLabels)
    plot.add(clustered_bars)
    plot.setXLabel(var_label_a)
    plot.setYLabel(y_label)

def config_hist(fig, vals, var_label, hist_label=None, thumbnail=False):    
    """
    Configure histogram with subplot of normal distribution curve.
    Size is set externally. 
    """
    axes = fig.gca()
    if thumbnail:
        nbins = 20
        axes.axis("off")
        normal_line_width = 1
    else:
        nbins = 100
        axes.set_xlabel(var_label)
        axes.set_ylabel('P')
        if not hist_label:
            hist_label = _("Histogram for %s") % var_label
        axes.set_title(hist_label)
        normal_line_width = 4
    n, bins, patches = axes.hist(vals, nbins, normed=1, 
        facecolor=my_globals.FACECOLOR, edgecolor=my_globals.EDGECOLOR)
    mu = core_stats.mean(vals)
    sigma = core_stats.stdev(vals)
    y = pylab.normpdf(bins, mu, sigma)
    l = axes.plot(bins, y,  color=my_globals.NORM_LINE_COLOR, 
                  linewidth=normal_line_width)

def config_scatterplot(fig, sample_a, sample_b, label_a, label_b, a_vs_b):
    """
    Configure scatterplot with line of best fit.
    Size is set externally. 
    """
    pylab.plot(sample_a, sample_b, 'o', color=my_globals.FACECOLOR, 
               label=a_vs_b)
    p = pylab.polyfit(sample_a, sample_b, 1)
    pylab.plot(sample_a, pylab.polyval(p, sample_a), "-", 
               color=my_globals.NORM_LINE_COLOR, linewidth=4,
               label="Line of best fit")
    axes = fig.gca()
    axes.set_xlabel(label_a)
    axes.set_ylabel(label_b)
    pylab.legend(loc="best")

        
class HistDlg(wxmpl.PlotDlg):
    def __init__(self, parent, vals, var_label, hist_label):
        wxmpl.PlotDlg.__init__(self, parent, 
            title=_("Similar to normal distribution curve?"), size=(10.0, 6.0), 
            dpi=96)
        btnOK = wx.Button(self, wx.ID_OK)
        btnOK.Bind(wx.EVT_BUTTON, self.OnOK)
        self.sizer.Add(btnOK, 0, wx.ALIGN_RIGHT|wx.ALL, 10)
        fig = self.get_figure()
        config_hist(fig, vals, var_label, hist_label)
        self.draw()
        self.SetSizer(self.sizer)
        self.Fit()

    def OnOK(self, event):
        self.Destroy()