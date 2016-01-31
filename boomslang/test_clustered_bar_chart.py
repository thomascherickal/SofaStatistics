import Bar
import Plot
import ClusteredBars

ok_data = [[1, 2, 1], [1, 2, 1], [1, 2, 3]]
bad_data = [[0, 2, 0], [0, 2, 0], [1, 2, 3]]

# ////////////////////////////////////////////////////////////////////
# Put this module in the boomslang folder
# set img_name and set data to either good_data or bad_data
img_name = "wonky_clustered_bar_chart3.png"
data = bad_data
# ////////////////////////////////////////////////////////////////////

plot = Plot.Plot()
y_label = "Frequency"
var_label_a = "Nations"
val_labels_a = ["Angola", "Bolivia", "Canada"]
val_labels_b = ["Ants", "Beetles", "Cockroaches"]
plot.hasLegend(columns=3, location="lower left")
plot.setAxesLabelSize(11)
plot.setLegendLabelSize(9)
colours = ["#333435", "#CCD9D7", "white"]
clustered_bars = ClusteredBars.ClusteredBars()
for i, val_label_b in enumerate(val_labels_b):
    cluster = Bar.Bar()
    x_vals = range(3)
    cluster.xValues = x_vals
    y_vals = data[i]
    cluster.yValues = y_vals
    cluster.color = colours[i]
    cluster.label = val_label_b
    clustered_bars.add(cluster)
clustered_bars.spacing = 0.5
clustered_bars.xTickLabels = val_labels_a
plot.add(clustered_bars)
plot.setXLabel(var_label_a)
plot.setYLabel(y_label)
plot.save(img_name)
print "FINISHED"
