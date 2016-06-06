//Details on ticks etc http://www.ibm.com/developerworks/web/library/wa-moredojocharts/
makeBarChart = function(chartname, series, conf){
    nChart = conf["n_chart"];
    nChartFontColour = conf["filled_font_colour"]
    /*chartwide function setting - have access to val.element (Column), val.index (0), val.run.data (y_vals), shape, x, y, chart, plot, hAxis, eventMask, type, event
    val.run has chart, group, htmlElements, dirty, stroke, fill, plot, data, dyn, name
    val.run = val.run.chart.series[0]
    val.run.chart has margins, stroke, fill, delayInMs, theme, axes, stack, plots, series, runs, dirty,coords,node,surface,dim,offsets,plotArea AND any other variables I put in with the options - the third parameter of addSeries().
    val.run.data has 0,1,2,3,4 etc such that val.run.data[0] is the y-val for the first item  */
    var getTooltip = function(val){
        var tip = val.run.yLbls[val.index];
        return tip;
    };
    var dc = dojox.charting;
    var mychart = new dc.Chart2D(
        chartname,
        {margins:
            {l: conf["margin_offset_l"],
             t: 10,
             r: 10,
             b: 10+conf["axis_lbl_drop"]},
        yTitleOffset: conf["y_title_offset"]});
    var sofa_theme = new dc.Theme({
        chart:{
	        stroke: conf["outer_chart_border_colour"],
        	fill: null, //conf["outer_bg"],
	        pageStyle: null // suggested page style as an object suitable for dojo.style()
	    },
	    plotarea:{
	        stroke: conf["inner_chart_border_colour"],
	        fill: conf["inner_bg"]
	    },
	    axis:{
	        stroke:	{ // the axis itself
	            color: conf["axis_colour"],
	            width: null
	        },
            tick: {	// used as a foundation for all ticks
	            color:     conf["tick_colour"],
	            position:  "center",
	            fontColor: conf["axis_lbl_font_colour"]
	        },
	        majorTick:	{ // major ticks on axis, and used for major gridlines
	            width:  conf["gridline_width"],
	            length: 6, 
                color: conf["major_gridline_colour"]
	        },
	        minorTick:	{ // minor ticks on axis, and used for minor gridlines
	            width:  0.8,
	            length: 3
	        },
	        microTick:	{ // minor ticks on axis, and used for minor gridlines
	            width:  0.5,
	            length: 1
	        }
	    }
    });

    mychart.setTheme(sofa_theme);
    mychart.addAxis("x",
        {title: conf["x_title"],
         labels: conf["xaxis_lbls"],
         minorTicks: conf["minor_ticks"], 
         font: "normal normal normal " + conf["xfontsize"] + "pt Arial",
         rotation: conf["axis_lbl_rotate"]
    });
    mychart.addAxis("y",
       {title: conf["y_title"],
        vertical: true,
        includeZero: true, 
        max: conf["ymax"],
        font: "normal normal normal 10pt Arial",
        fontWeight: 12
    });
    mychart.addPlot("grid", {type: "Grid",
                    hMajorLines: true,
                    hMinorLines: false,
                    vMajorLines: false,
                    vMinorLines: false });
    mychart.addPlot("default",
        {type: "ClusteredColumns",
         gap: conf["xgap"],
         shadows: {dx: 12, dy: 12}}
    );
    var i
    for (i in series){
        mychart.addSeries(series[i]["seriesLabel"], series[i]["yVals"], series[i]["options"]);
    }
    var anim_a = new dc.action2d.Highlight(mychart, "default", {
        highlight: conf["highlight"],
        duration: 450,
        easing:   dojo.fx.easing.sineOut
    });
    var anim_b = new dc.action2d.Shake(mychart, "default");
    var anim_c = new dc.action2d.Tooltip(mychart, "default", {text: getTooltip, 
        tooltipBorderColour: conf["tooltip_border_colour"],
        connectorStyle: conf["connector_style"]});
    mychart.render();
    var legend = new dojox.charting.widget.Legend({chart: mychart, horizontal: 6}, ("legend" + chartname.substr(0,1).toUpperCase() + chartname.substr(1)));
}

makePieChart = function(chartname, slices, conf){
    nChartFontColour = conf["filled_font_colour"]
    nChart = conf["n_chart"];
    var pieStroke = "#8b9b98";
    var dc = dojox.charting;
    var mychart = new dc.Chart2D(chartname);
    var sofa_theme = new dc.Theme({
		colors: conf["slice_colours"],
        chart: {
	        stroke: null,
        	fill: null,
	        pageStyle: null // suggested page style as an object suitable for dojo.style()
	    },
		plotarea: {
			fill: conf["filled_outer_bg"]
		}
	});
    mychart.setTheme(sofa_theme);
    mychart.addPlot("default", {
            type: "Pie",
            font: "normal normal " + conf["slice_fontsize"] + "px Tahoma",
            fontColor: conf["filled_font_colour"],
            labelOffset: conf['lbl_offset'],
            radius: conf['radius']
        });

    var pieSeries = Array();
    var i;
    for (i in slices){
        pieSeries[i] = 
        {
            y: slices[i]["y"],
            text: slices[i]["text"],
            stroke: pieStroke,
            tooltip: slices[i]["tooltip"]
        }
    }
    mychart.addSeries("Series A", pieSeries);
    var anim_a = new dc.action2d.MoveSlice(mychart, "default");
    var anim_b = new dc.action2d.Highlight(mychart, "default", {
        highlight: conf["highlight"],
        duration: 450,
        easing:   dojo.fx.easing.sineOut
    });
    var anim_c = new dc.action2d.Tooltip(mychart, "default", 
        {tooltipBorderColour: conf['tooltip_border_colour'],
         connectorStyle: conf['connector_style']});
    mychart.render();
}

function zeropad_date(num){
    if (num < 10) {
        return "0" + num
    } else {
        return num
    }   
}

// A single parameter function to get labels from epoch milliseconds
function labelfTime(o)
{
   var dt = new Date();
   dt.setTime(o);
   var d = dt.getFullYear() + "-" + zeropad_date(dt.getMonth()+1) + "-" + zeropad_date(dt.getDate());
   //console.log(o+"="+d);
   return d;
}

makeLineChart = function(chartname, series, conf){
    nChartFontColour = conf["filled_font_colour"]
    nChart = conf["n_chart"];
    var getTooltip = function(val){
        var tip = val.run.yLbls[val.index];
        return tip;
    };
    var dc = dojox.charting;
    var mychart = new dc.Chart2D(chartname,
        {margins: {
            l: conf['margin_offset_l'],
            t: 10,
            r: 10,
            b: 10+conf['axis_lbl_drop'],
            yTitleOffset: conf['y_title_offset']}});
    var sofa_theme = new dc.Theme({
        chart:{
	        stroke: null,
        	fill: conf["outer_bg"],
	        pageStyle: null // suggested page style as an object suitable for dojo.style()
	    },
	    plotarea:{
	        stroke: null,
	        fill: conf["inner_bg"]
	    },
	    axis:{
	        stroke:	{ // the axis itself
	            color: null,
	            width: null
	        },
            tick: {	// used as a foundation for all ticks
	            color:     null,
	            position:  "center",
	            fontColor: conf["axis_lbl_font_colour"]
	        },
	        majorTick:	{ // major ticks on axis, and used for major gridlines
	            width:  conf['gridline_width'],
	            length: 6, 
                color: conf["major_gridline_colour"]
	        },
	        minorTick:	{ // minor ticks on axis, and used for minor gridlines
	            width:  2,
	            length: 4,
                color: conf["major_gridline_colour"]
	        },
	        microTick:	{ // minor ticks on axis, and used for minor gridlines
	            width:  1.7,
	            length: 3,
                color: null
	        }
	    }
    });
    mychart.setTheme(sofa_theme);
    // x-axis
    var xaxis_conf = {
        title: conf['x_title'],
        font: "normal normal normal " + conf["xfontsize"] + "pt Arial",
        rotation: conf['axis_lbl_rotate'],
        minorTicks: conf['minor_ticks'],
        microTicks: conf['micro_ticks'],
        minorLabels: conf['minor_ticks']
    };
    if (conf['time_series']) {
        xaxis_conf.labelFunc = labelfTime;
    } else {
        xaxis_conf.labels = conf["xaxis_lbls"];
    };
    mychart.addAxis("x", xaxis_conf);
    // y-axis
    mychart.addAxis("y", {title: conf['y_title'],
                    vertical: true, includeZero: true, 
                    max: conf["ymax"],
                    font: "normal normal normal 10pt Arial", fontWeight: 12
    });
    mychart.addPlot("default", {type: "Lines", markers: true, shadows: {dx: 2, dy: 2, dw: 2}});
    mychart.addPlot("unmarked", {type: "Lines", markers: false});
    mychart.addPlot("curved", {type: "Lines", markers: false, tension: "S"});
    mychart.addPlot("grid", {type: "Grid", vMajorLines: false});
    var i
    for (i in series){
        mychart.addSeries(series[i]["seriesLabel"], series[i]["seriesVals"], series[i]["options"]);
    }
    var anim_a = new dc.action2d.Magnify(mychart, "default");
    var anim_b = new dc.action2d.Tooltip(mychart, "default", {text: getTooltip, 
        tooltipBorderColour: conf['tooltip_border_colour'], connectorStyle: conf['connector_style']});
    mychart.render();
    var legend = new dojox.charting.widget.Legend(
        {chart: mychart},
        ("legend" + chartname.substr(0,1).toUpperCase() + chartname.substr(1)));
}

makeAreaChart = function(chartname, series, conf){
    nChartFontColour = conf["filled_font_colour"]
    nChart = conf["n_chart"];
    var getTooltip = function(val){
        var tip = val.run.yLbls[val.index];
        return tip;
    };
    var dc = dojox.charting;
    var mychart = new dc.Chart2D(chartname,
        {margins: {
            l: conf['margin_offset_l'],
            t: 10,
            r: 10,
            b: 10+conf['axis_lbl_drop']},
        yTitleOffset: conf['y_title_offset']});
    var sofa_theme = new dc.Theme({
        chart:{
	        stroke: null,
        	fill: null,
	        pageStyle: null // suggested page style as an object suitable for dojo.style()
	    },
	    plotarea:{
	        stroke: null,
	        fill: conf["inner_bg"]
	    },
	    axis:{
	        stroke:	{ // the axis itself
	            color: null,
	            width: null
	        },
            tick: {	// used as a foundation for all ticks
	            color:     "black",
	            position:  "center",
	            fontColor: conf["axis_lbl_font_colour"]
	        },
	        majorTick:	{ // major ticks on axis, and used for major gridlines
	            width:  conf['gridline_width'],
	            length: 6, 
                color: conf["major_gridline_colour"]
	        },
	        minorTick:	{ // minor ticks on axis, and used for minor gridlines
	            width:  2,
	            length: 4,
                color: conf["major_gridline_colour"]
	        },
	        microTick:	{ // minor ticks on axis, and used for minor gridlines
	            width:  1.7,
	            length: 3,
                color: "black"
	        }
	    }
    });
    mychart.setTheme(sofa_theme);
    // x-axis
    var xaxis_conf = {
        title: conf['x_title'],
        font: "normal normal normal " + conf["xfontsize"] + "pt Arial",
        rotation: conf['axis_lbl_rotate'],
        minorTicks: conf['minor_ticks'],
        microTicks: conf['micro_ticks'],
        minorLabels: conf['minor_ticks']
    };
    if (conf['time_series']) {
        xaxis_conf.labelFunc = labelfTime;
    } else {
        xaxis_conf.labels = conf["xaxis_lbls"];
    };
    mychart.addAxis("x", xaxis_conf);
    // y-axis
    mychart.addAxis("y", {title: conf['y_title'],  // normal normal bold
                    vertical: true, includeZero: true, 
                    max: conf["ymax"], 
                    font: "normal normal normal 10pt Arial", fontWeight: 12
    });
    mychart.addPlot("default", {type: "Areas", lines: true, areas: true, markers: true});
    mychart.addPlot("unmarked", {type: "Areas", lines: true, areas: true, markers: false});
    mychart.addPlot("grid", {type: "Grid", vMajorLines: false});
    var i
    for (i in series){
        mychart.addSeries(series[i]["seriesLabel"], series[i]["seriesVals"], series[i]["options"]);
    }
    var anim_a = new dc.action2d.Magnify(mychart, "default");
    var anim_b = new dc.action2d.Tooltip(mychart, "default",
        {text: getTooltip, 
         tooltipBorderColour: conf['tooltip_border_colour'],
         connectorStyle: conf['connector_style']});
    mychart.render();
}

makeHistogram = function(chartname, datadets, conf){
    nChartFontColour = conf["filled_font_colour"]
    nChart = conf["n_chart"];
    // chartwide function setting - have access to val.element (Column), val.index (0), val.run.data (y_vals)
    var getTooltip = function(val){
        return "Values: " + datadets["binLabels"][val.index] + "<br>" + conf['y_title'] + ": " + val.y;
    };
    var dc = dojox.charting;
    var mychart = new dc.Chart2D(chartname,
       {margins: {
            l: conf['margin_offset_l'],
            t: 10,
            r: 10,
            b: 10},
        yTitleOffset: conf['y_title_offset']});

    var sofa_theme = new dc.Theme({
        chart:{
	        stroke: null,
        	fill: conf["outer_bg"],
	        pageStyle: null // suggested page style as an object suitable for dojo.style()
	    },
	    plotarea:{
	        stroke: conf['axis_lbl_font_colour'],
	        fill: conf["inner_bg"]
	    },
	    axis:{
	        stroke:	{ // the axis itself
	            color: conf['axis_lbl_font_colour'],
	            width: null
	        },
            tick: {	// used as a foundation for all ticks
	            color:     null,
	            position:  "center",
	            fontColor: conf["axis_lbl_font_colour"]
	        },
	        majorTick:	{ // major ticks on axis, and used for major gridlines
	            width:  conf['gridline_width'],
	            length: 6, 
                color: conf["major_gridline_colour"]
	        },
	        minorTick:	{ // minor ticks on axis, and used for minor gridlines
	            width:  0.8,
	            length: 3
	        },
	        microTick:	{ // minor ticks on axis, and used for minor gridlines
	            width:  0.5,
	            length: 1
	        }
	    }
    });
    mychart.setTheme(sofa_theme);
    mychart.addAxis("x", {title: datadets["seriesLabel"],
                    labels: conf["xaxis_lbls"], minorTicks: false, microTicks: false,
                    font: "normal normal normal " + conf["xfontsize"] + "pt Arial"
    });
    mychart.addAxis("x2", {
        min: conf["minval"],
        max: conf["maxval"],
        minorTicks: conf['minor_ticks'], 
        font: "normal normal normal " + conf["xfontsize"] + "pt Arial"
    });
    mychart.addAxis("y", {title: conf['y_title'],  // normal normal bold
                    vertical: true, includeZero: true, font: "normal normal normal 10pt Arial", fontWeight: 12
    });
    mychart.addPlot("normal", {type: "Lines", markers: true, shadows: {dx: 2, dy: 2, dw: 2}}); // must come first to be seen!
    mychart.addPlot("default", {type: "Columns", gap: 0, shadows: {dx: 12, dy: 12}});
    mychart.addPlot("grid", {type: "Grid", vMajorLines: false});
    mychart.addPlot("othergrid", {type: "Areas", hAxis: "x2", vAxis: "y"});
    mychart.addSeries(datadets["seriesLabel"], datadets["yVals"], datadets["style"]);
    if(conf['inc_normal'] == true){
        mychart.addPlot("normal", {type: "Lines", markers: false, shadows: {dx: 2, dy: 2, dw: 2}});
        mychart.addSeries("Normal Dist Curve", datadets["normYs"], datadets["normStyle"]); 
    }
    var anim_a = new dc.action2d.Highlight(mychart, "default", {
        highlight: conf["highlight"],
        duration: 450,
        easing:   dojo.fx.easing.sineOut
    });
    var anim_b = new dc.action2d.Shake(mychart, "default");
    var anim_c = new dc.action2d.Tooltip(
        mychart,
        "default",
        {text: getTooltip, 
         tooltipBorderColour: conf['tooltip_border_colour'],
         connectorStyle: conf['connector_style']});
    mychart.render();
}

makeScatterplot = function(chartname, series, conf){
    nChartFontColour = conf["filled_font_colour"]
    nChart = conf["n_chart"];
    // chartwide function setting - have access to val.element (Column), val.index (0), val.run.data (y_vals)
    var getTooltip = function(val){
        return "(x: " + val.x + ", y: " + val.y + ")";
    };
    var dc = dojox.charting;
    var mychart = new dc.Chart2D(
        chartname,
        {margins:
            {l: conf['margin_offset_l'],
             t: 10,
             r: 10,
             b: 10+conf['axis_lbl_drop']},
         yTitleOffset: conf['y_title_offset']});
    var sofa_theme = new dc.Theme({
        chart:{
	        stroke: null,
        	fill: conf['outer_bg'],
	        pageStyle: null // suggested page style as an object suitable for dojo.style()
	    },
	    plotarea:{
	        stroke: null,
	        fill: conf["inner_bg"]
	    },
	    axis:{
	        stroke:	{ // the axis itself
	            color: conf['axis_lbl_font_colour'],
	            width: null
	        },
            tick: {	// used as a foundation for all ticks
	            color:     conf['tick_colour'],
	            position:  "center",
	            fontColor: conf["axis_lbl_font_colour"]
	        },
	        majorTick:	{ // major ticks on axis, and used for major gridlines
	            width:  conf["gridline_width"],
	            length: 6, 
                color: conf["major_gridline_colour"]
	        },
	        minorTick:	{ // minor ticks on axis, and used for minor gridlines
	            width:  0.8,
	            length: 3
	        },
	        microTick:	{ // minor ticks on axis, and used for minor gridlines
	            width:  0.5,
	            length: 1
	        }
	    }
    });
    mychart.setTheme(sofa_theme);
    mychart.addAxis("x", {title: conf['x_title'],
                    min: conf["xmin"], max: conf["xmax"],
                    minorTicks: conf['minor_ticks'], microTicks: false,
                    font: "normal normal normal " + conf["xfontsize"] + "pt Arial"
    });
    mychart.addAxis("y", {title: conf['y_title'],
                    min: conf["ymin"], max: conf["ymax"],
                    vertical: true, font: "normal normal normal 10pt Arial", fontWeight: 12
    });
    // plot line first so on top
    if(conf['inc_regression_js'] == true){
        mychart.addPlot("regression", {type: "Lines", markers: false, shadows: {dx: 2, dy: 2, dw: 2}});
        for (i in series){
            try {
                mychart.addSeries(series[i]["lineLabel"], series[i]["xyLinePairs"], series[i]["lineStyle"]);
            } catch(err) {
                /*do nothing*/
            }
        }
    }
    mychart.addPlot("default", {type: "Scatter"});
    mychart.addPlot("grid", {type: "Grid", vMajorLines: true});
    var i
    for (i in series){
        mychart.addSeries(series[i]["seriesLabel"], series[i]["xyPairs"], series[i]["style"]);
    }
    var anim_a = new dc.action2d.Magnify(mychart, "default");
    var anim_b = new dc.action2d.Tooltip(mychart, "default",
       {text: getTooltip, 
        tooltipBorderColour: conf['tooltip_border_colour'],
        connectorStyle: conf['connector_style']});
    mychart.render();
    var legend = new dojox.charting.widget.Legend({chart: mychart}, ("legend" + chartname.substr(0,1).toUpperCase() + chartname.substr(1)));
    var anim_a = new dc.action2d.Highlight(mychart, "default", {
        highlight: conf["highlight"],
        duration: 450,
        easing:   dojo.fx.easing.sineOut
    });
    var anim_b = new dc.action2d.Shake(mychart, "default");
    var anim_c = new dc.action2d.Tooltip(mychart, "default", {text: getTooltip, 
        tooltipBorderColour: conf['tooltip_border_colour'],
        connectorStyle: conf['connector_style']});
    mychart.render();
}

makeBoxAndWhisker = function(chartname, series, seriesconf, conf){
    nChartFontColour = conf["filled_font_colour"]
    nChart = conf["n_chart"];
    // chartwide function setting - have access to val.element (Column), val.index (0), val.run.data (y_vals)
    var getTooltip = function(val){
        return val.y;
    };
    var dc = dojox.charting;
    var mychart = new dc.Chart2D(
        chartname,
        {margins:
            {l: conf['margin_offset_l'],
             t: 10,
             r: 10,
             b: 10+conf['axis_lbl_drop']},
         yTitleOffset: conf['y_title_offset']});
    var sofa_theme = new dc.Theme({
        chart:{
	        stroke:    null,
        	fill:      conf['outer_bg'],
	        pageStyle: null // suggested page style as an object suitable for dojo.style()
	    },
	    plotarea:{
	        stroke: null,
	        fill:   conf["inner_bg"]
	    },
	    axis:{
	        stroke:	{ // the axis itself
	            color: conf['axis_lbl_font_colour'],
	            width: null
	        },
            tick: {	// used as a foundation for all ticks
	            color:     conf['tick_colour'],
	            position:  "center",
	            fontColor: conf['axis_lbl_font_colour']
	        },
	        majorTick:	{ // major ticks on axis, and used for major gridlines
	            width:  conf['gridline_width'],
	            length: 6, 
                color:  conf['tick_colour'] // we have vMajorLines off so we don't need to match grid color e.g. null
	        },
	        minorTick:	{ // minor ticks on axis, and used for minor gridlines
	            width:  0.8,
	            length: 3
	        },
	        microTick:	{ // minor ticks on axis, and used for minor gridlines
	            width:  0.5,
	            length: 1
	        }
	    }
    });
    mychart.setTheme(sofa_theme);
    mychart.addPlot("default", {type: "Boxplot", markers: true});
    mychart.addPlot("grid", {type: "Grid", vMajorLines: false});
    mychart.addAxis(
        "x",
        {title: conf['x_title'],
         min: conf["xmin"],
         max: conf["xmax"], 
         majorTicks: true,
         minorTicks: conf['minor_ticks'],
         labels: conf["xaxis_lbls"],
         font: "normal normal normal " + conf["xfontsize"] + "pt Arial",
         rotation: conf['axis_lbl_rotate']});
    mychart.addAxis(
        "y",
        {title: conf['y_title'],
         vertical: true,
         min: conf["ymin"],
         max: conf["ymax"], 
         majorTicks: true,
         minorTicks: true,
         font: "normal normal normal " + conf["yfontsize"] + "pt Arial"});
    var i
    for (i in series){
        mychart.addSeries(series[i]["seriesLabel"], [], series[i]["boxDets"]);
    }
    var anim_a = new dc.action2d.Highlight(mychart, "default", {
        highlight: conf["highlight"],
        duration: 450,
        easing:   dojo.fx.easing.sineOut
    });
    var anim_b = new dc.action2d.Tooltip(
        mychart,
        "default",
        {text: getTooltip,
         tooltipBorderColour: conf['tooltip_border_colour'], 
         connectorStyle: conf['connector_style']});
    mychart.render();

    var dummychart = new dc.Chart2D("dum" + chartname);
    dummychart.addPlot("default", {type: "ClusteredColumns"});
    for (i in seriesconf){
        dummychart.addSeries(seriesconf[i]["seriesLabel"], [1,2], seriesconf[i]["seriesStyle"]);
    }
    dummychart.render();
    var legend = new dojox.charting.widget.Legend({chart: dummychart}, ("legend" + chartname.substr(0,1).toUpperCase() + chartname.substr(1)));

}
