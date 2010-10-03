#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os

import boomslang
import wx
import wxmpl
import pylab # must import after wxmpl so matplotlib.use() is always first

import my_globals as mg
import lib
import core_stats
import wxmpl

int_imgs_n = 0 # for internal images so always unique

def save_report_img(add_to_report, report_name, save_func=pylab.savefig, 
                    dpi=None):
    """
    report_name -- full path to report
    If adding to report, save image to a subfolder in reports named after the 
        report.  Return a relative image source. Make subfolder if not present.
        Use image name guaranteed not to collide.  Count items in subfolder and
        use index as part of name.
    If not adding to report, save image to internal folder, and return absolute
        image source.  Remember to alternate sets of names so always the 
        freshest image showing in html (without having to reload etc).
    """
    debug = False
    if add_to_report:
        # look in report folder for subfolder
        imgs_path = os.path.join(report_name[:-len(".htm")] + u"_images", u"")
        if debug: print("imgs_path: %s" % imgs_path)
        try:
            os.mkdir(imgs_path)
        except OSError, e:
            pass # already there
        n_imgs = len(os.listdir(imgs_path))
        file_name = u"%03d.png" % n_imgs
        img_path = os.path.join(imgs_path, file_name) # absolute
        args = [img_path]
        kwargs = {"dpi": dpi} if dpi else {}
        save_func(*args, **kwargs)
        if debug: print("Just saved %s" % img_path)
        subfolder = os.path.split(imgs_path[:-1])[1]
        img_src = os.path.join(subfolder, file_name) #relative so can shift html
        if debug: print("add_to_report img_src: %s" % img_src)
    else:
        # must ensure internal images are always different each time we
        # refresh html.  Otherwise might just show old version of same-named 
        # image file!
        global int_imgs_n
        int_imgs_n += 1
        img_src = mg.INT_IMG_ROOT + u"_%03d.png" % int_imgs_n
        if debug: print(img_src)
        args = [img_src]
        kwargs = {"dpi": dpi} if dpi else {}
        save_func(*args, **kwargs)
        if debug: print("Just saved %s" % img_src)
    if debug: print("img_src: %s" % img_src)
    return img_src

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
    # use nicest bins practical
    n_bins, lower_limit, upper_limit = lib.get_bins(min(vals), max(vals))
    y_vals, start, bin_width, unused = \
             core_stats.histogram(vals, n_bins, defaultreallimits=[lower_limit, 
                                                                   upper_limit])
    y_vals, start, bin_width = lib.fix_sawtoothing(vals, n_bins, y_vals, start, 
                                                   bin_width)    
    if thumbnail:
        n_bins = round(n_bins/2, 0)
        if n_bins < 5: 
            n_bins = 5
        axes.axis("off")
        normal_line_width = 1
    else:
        axes.set_xlabel(var_label)
        axes.set_ylabel('P')
        if not hist_label:
            hist_label = _("Histogram for %s") % var_label
        axes.set_title(hist_label)
        normal_line_width = 4
    # see entry for hist in http://matplotlib.sourceforge.net/api/axes_api.html
    n, bins, patches = axes.hist(vals, n_bins, normed=1, 
                                 range=(lower_limit, upper_limit),
                                 facecolor=bar_colour, edgecolor=line_colour)
    if debug: print(n, bins, patches)
    mu = core_stats.mean(vals)
    sigma = core_stats.stdev(vals)
    y = pylab.normpdf(bins, mu, sigma)
    # ensure enough y-axis to show all of normpdf
    ymin, ymax = axes.get_ylim()
    if debug:
        print(y)
        print(ymin, ymax)
        print("norm max: %s; axis max: %s" % (max(y), ymax))
    if max(y) > ymax:
        axes.set_ylim(ymax=1.05*max(y))
    l = axes.plot(bins, y, color=line_colour, linewidth=normal_line_width)

def config_scatterplot(grid_bg, dot_colour, dot_borders, line_colour, fig, 
                       sample_a, sample_b, label_a, label_b, a_vs_b):
    """
    Configure scatterplot with line of best fit.
    Size is set externally. 
    """
    marker_edge_colour = line_colour if dot_borders else dot_colour
    pylab.plot(sample_a, sample_b, 'o', color=dot_colour, label=a_vs_b, 
               markeredgecolor=marker_edge_colour)
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

def add_scatterplot(grid_bg, dot_colour, dot_borders, line_colour, sample_a, 
                    sample_b, label_a, label_b, a_vs_b, title_dets_html, 
                    add_to_report, report_name, html):
    """
    Toggle prefix so every time this is run internally only, a different image 
        is referred to in the html <img src=...>.
    This works because there is only ever one scatterplot per internal html.
    """
    debug = False
    fig = pylab.figure()
    fig.set_size_inches((7.5, 4.5)) # see dpi to get image size in pixels
    config_scatterplot(grid_bg, dot_colour, dot_borders, line_colour, fig, 
                       sample_a, sample_b, label_a, label_b, a_vs_b)
    img_src = save_report_img(add_to_report, report_name, 
                              save_func=pylab.savefig, dpi=100)
    html.append(title_dets_html)
    html.append(u"\n<img src='%s'>" % img_src)
    if debug: print("Just linked to %s" % img_src)


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