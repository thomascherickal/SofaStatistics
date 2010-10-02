
makeBarChart = function(chartname, series, chartconf){
    // allow charts made without newest config items to keep working
    var gridlineWidth = (chartconf["gridlineWidth"]) ? chartconf["gridlineWidth"] : 3;
    var tooltipBorderColour = (chartconf["tooltipBorderColour"]) ? chartconf["tooltipBorderColour"] : "#ada9a5";
    var outerChartBorderColour = (chartconf["outerChartBorderColour"]) ? chartconf["outerChartBorderColour"] : null;
    var innerChartBorderColour = (chartconf["innerChartBorderColour"]) ? chartconf["innerChartBorderColour"] : null;
    var outerBg = (chartconf["outerBg"]) ? chartconf["outerBg"] : null;
    var axisColour = (chartconf["axisColour"]) ? chartconf["axisColour"] : null;
    var tickColour = (chartconf["tickColour"]) ? chartconf["tickColour"] : null;
    var minorTicks = (chartconf["minorTicks"]) ? chartconf["minorTicks"] : false;
    var xTitle = (chartconf["xTitle"]) ? chartconf["xTitle"] : "";
    var axisLabelDrop = (chartconf["axisLabelDrop"]) ? chartconf["axisLabelDrop"] : 30;
    var yTitle = (chartconf["yTitle"]) ? chartconf["yTitle"] : "Frequency";
    var connectorStyle = (chartconf["connectorStyle"]) ? chartconf["connectorStyle"] : "defbrown";

    var getSum = function(myNums){
        var i
        var sum = 0
        for (i in myNums) {
            sum += myNums[i]
        }
        return sum
    }    

    // chartwide functon setting - have access to val.element (Column), val.index (0), val.run.data (y_vals)
    var getTooltip = function(val){
        var seriesSum = getSum(val.run.data);
        return val.y + "<br>(" + Math.round((1000*val.y)/seriesSum)/10 + "%)";
    };

    var dc = dojox.charting;
    var mychart = new dc.Chart2D(chartname, {margins: {l: 10, t: 10, r: 10, b: 10+axisLabelDrop}});
    var sofa_theme = new dc.Theme({
        chart:{
	        stroke: outerChartBorderColour,
        	fill: outerBg,
	        pageStyle: null // suggested page style as an object suitable for dojo.style()
	    },
	    plotarea:{
	        stroke: innerChartBorderColour,
	        fill: chartconf["gridBg"]
	    },
	    axis:{
	        stroke:	{ // the axis itself
	            color: axisColour,
	            width: null
	        },
            tick: {	// used as a foundation for all ticks
	            color:     tickColour,
	            position:  "center",
	            fontColor: chartconf["axisLabelFontColour"]
	        },
	        majorTick:	{ // major ticks on axis, and used for major gridlines
	            width:  gridlineWidth,
	            length: 6, 
                color: chartconf["majorGridlineColour"]
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
    mychart.addAxis("x", {title: xTitle,
                    labels: chartconf["xaxisLabels"], minorTicks: minorTicks, 
                    font: "normal normal normal " + chartconf["xfontsize"] + "pt Arial"
    });
    mychart.addAxis("y", {title: yTitle,
                    vertical: true, includeZero: true, font: "normal normal normal 10pt Arial", fontWeight: 12
    });
    mychart.addPlot("default", {type: "ClusteredColumns", gap: chartconf["xgap"], shadows: {dx: 12, dy: 12}});
    mychart.addPlot("grid", {type: "Grid", vMajorLines: false});
    var i
    for (i in series){
        mychart.addSeries(series[i]["seriesLabel"], series[i]["yVals"], series[i]["style"]);
    }
    var anim_a = new dc.action2d.Highlight(mychart, "default", {
        highlight: chartconf["sofaHl"],
        duration: 450,
        easing:   dojo.fx.easing.sineOut
    });
    var anim_b = new dc.action2d.Shake(mychart, "default");
    var anim_c = new dc.action2d.Tooltip(mychart, "default", {text: getTooltip, 
        tooltipBorderColour: tooltipBorderColour, connectorStyle: connectorStyle});
    mychart.render();
    var legend = new dojox.charting.widget.Legend({chart: mychart}, ("legend" + chartname.substr(0,1).toUpperCase() + chartname.substr(1)));
}

makePieChart = function(chartname, slices, chartconf){
    // allow charts made without newest config items to keep working

    var tooltipBorderColour = (chartconf["tooltipBorderColour"]) ? chartconf["tooltipBorderColour"] : "#ada9a5";
    var outerChartBorderColour = (chartconf["outerChartBorderColour"]) ? chartconf["outerChartBorderColour"] : null;
    var innerChartBorderColour = (chartconf["innerChartBorderColour"]) ? chartconf["innerChartBorderColour"] : null;
    var outerBg = (chartconf["outerBg"]) ? chartconf["outerBg"] : null;
    var pieStroke = "#8b9b98";
    var connectorStyle = (chartconf["connectorStyle"]) ? chartconf["connectorStyle"] : "defbrown";

    var dc = dojox.charting;
    var mychart = new dc.Chart2D(chartname);
    
    
    var sofa_theme = new dc.Theme({
		colors: chartconf["sliceColours"],
        chart: {
	        stroke: outerChartBorderColour,
        	fill: outerBg,
	        pageStyle: null // suggested page style as an object suitable for dojo.style()
	    },
		plotarea: {
			fill: chartconf["innerBg"]
		}
	});
    mychart.setTheme(sofa_theme);
    mychart.addPlot("default", {
            type: "Pie",
            font: "normal normal " + chartconf["sliceFontsize"] + "px Tahoma",
            fontColor: chartconf["labelFontColour"],
            labelOffset: -30,
            radius: 140
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
        highlight: chartconf["sofaHl"],
        duration: 450,
        easing:   dojo.fx.easing.sineOut
    });
    var anim_c = new dc.action2d.Tooltip(mychart, "default", {tooltipBorderColour: tooltipBorderColour, connectorStyle: connectorStyle});
    mychart.render();
    //var legend = new dojox.charting.widget.Legend({chart: mychart}, ("legend" + chartname.substr(0,1).toUpperCase() + chartname.substr(1)));
}

makeLineChart = function(chartname, series, chartconf){
    // allow charts made without newest config items to keep working
    var gridlineWidth = (chartconf["gridlineWidth"]) ? chartconf["gridlineWidth"] : 3;
    var tooltipBorderColour = (chartconf["tooltipBorderColour"]) ? chartconf["tooltipBorderColour"] : "#ada9a5";
    var outerChartBorderColour = (chartconf["outerChartBorderColour"]) ? chartconf["outerChartBorderColour"] : null;
    var innerChartBorderColour = (chartconf["innerChartBorderColour"]) ? chartconf["innerChartBorderColour"] : null;
    var axisColour = (chartconf["axisColour"]) ? chartconf["axisColour"] : null;
    var tickColour = (chartconf["tickColour"]) ? chartconf["tickColour"] : "black";
    var minorTicks = (chartconf["minorTicks"]) ? chartconf["minorTicks"] : false;
    var microTicks = (chartconf["microTicks"]) ? chartconf["microTicks"] : false;
    var xTitle = (chartconf["xTitle"]) ? chartconf["xTitle"] : "";
    var axisLabelDrop = (chartconf["axisLabelDrop"]) ? chartconf["axisLabelDrop"] : 30;
    var yTitle = (chartconf["yTitle"]) ? chartconf["yTitle"] : "Frequency";
    var connectorStyle = (chartconf["connectorStyle"]) ? chartconf["connectorStyle"] : "defbrown";

    var getSum = function(myNums){
        var i
        var sum = 0
        for (i in myNums) {
            sum += myNums[i]
        }
        return sum
    }    

    // chartwide functon setting - have access to val.element (Column), val.index (0), val.run.data (y_vals)
    var getTooltip = function(val){
        var seriesSum = getSum(val.run.data);
        return val.y + "<br>(" + Math.round((1000*val.y)/seriesSum)/10 + "%)";
    };

    var dc = dojox.charting;
    var mychart = new dc.Chart2D(chartname, {margins: {l: 10, t: 10, r: 10, b: 10+axisLabelDrop}});
    var sofa_theme = new dc.Theme({
        chart:{
	        stroke: outerChartBorderColour,
        	fill: null,
	        pageStyle: null // suggested page style as an object suitable for dojo.style()
	    },
	    plotarea:{
	        stroke: innerChartBorderColour,
	        fill: chartconf["gridBg"]
	    },
	    axis:{
	        stroke:	{ // the axis itself
	            color: axisColour,
	            width: null
	        },
            tick: {	// used as a foundation for all ticks
	            color:     tickColour,
	            position:  "center",
	            fontColor: chartconf["axisLabelFontColour"]
	        },
	        majorTick:	{ // major ticks on axis, and used for major gridlines
	            width:  gridlineWidth,
	            length: 6, 
                color: chartconf["majorGridlineColour"]
	        },
	        minorTick:	{ // minor ticks on axis, and used for minor gridlines
	            width:  2,
	            length: 4,
                color: chartconf["majorGridlineColour"]
	        },
	        microTick:	{ // minor ticks on axis, and used for minor gridlines
	            width:  1.7,
	            length: 3,
                color: tickColour
	        }
	    }
    });
    mychart.setTheme(sofa_theme);
    mychart.addAxis("x", {title: xTitle,
                    labels: chartconf["xaxisLabels"], minorTicks: minorTicks, microTicks: microTicks, minorLabels: minorTicks,
                    font: "normal normal normal " + chartconf["xfontsize"] + "pt Arial"
    });
    mychart.addAxis("y", {title: yTitle,
                    vertical: true, includeZero: true, font: "normal normal normal 10pt Arial", fontWeight: 12
    });
    mychart.addPlot("default", {type: "Lines", markers: true, shadows: {dx: 2, dy: 2, dw: 2}});
    mychart.addPlot("grid", {type: "Grid", vMajorLines: false});
    var i
    for (i in series){
        mychart.addSeries(series[i]["seriesLabel"], series[i]["yVals"], series[i]["style"]);
    }
    var anim_a = new dc.action2d.Magnify(mychart, "default");
    var anim_b = new dc.action2d.Tooltip(mychart, "default", {text: getTooltip, 
        tooltipBorderColour: tooltipBorderColour, connectorStyle: connectorStyle});
    mychart.render();
    var legend = new dojox.charting.widget.Legend({chart: mychart}, ("legend" + chartname.substr(0,1).toUpperCase() + chartname.substr(1)));
}

makeAreaChart = function(chartname, series, chartconf){
    // allow charts made without newest config items to keep working
    var gridlineWidth = (chartconf["gridlineWidth"]) ? chartconf["gridlineWidth"] : 3;
    var tooltipBorderColour = (chartconf["tooltipBorderColour"]) ? chartconf["tooltipBorderColour"] : "#ada9a5";
    var outerChartBorderColour = (chartconf["outerChartBorderColour"]) ? chartconf["outerChartBorderColour"] : null;
    var innerChartBorderColour = (chartconf["innerChartBorderColour"]) ? chartconf["innerChartBorderColour"] : null;
    var outerBg = (chartconf["outerBg"]) ? chartconf["outerBg"] : null;
    var axisColour = (chartconf["axisColour"]) ? chartconf["axisColour"] : null;
    var tickColour = (chartconf["tickColour"]) ? chartconf["tickColour"] : "black";
    var minorTicks = (chartconf["minorTicks"]) ? chartconf["minorTicks"] : false;
    var microTicks = (chartconf["microTicks"]) ? chartconf["microTicks"] : false;
    var yTitle = (chartconf["yTitle"]) ? chartconf["yTitle"] : "Frequency";
    var connectorStyle = (chartconf["connectorStyle"]) ? chartconf["connectorStyle"] : "defbrown";

    var getSum = function(myNums){
        var i
        var sum = 0
        for (i in myNums) {
            sum += myNums[i]
        }
        return sum
    }    

    // chartwide functon setting - have access to val.element (Column), val.index (0), val.run.data (y_vals)
    var getTooltip = function(val){
        var seriesSum = getSum(val.run.data);
        return val.y + "<br>(" + Math.round((1000*val.y)/seriesSum)/10 + "%)";
    };

    var dc = dojox.charting;
    var mychart = new dc.Chart2D(chartname);
    var sofa_theme = new dc.Theme({
        chart:{
	        stroke: outerChartBorderColour,
        	fill: null,
	        pageStyle: null // suggested page style as an object suitable for dojo.style()
	    },
	    plotarea:{
	        stroke: innerChartBorderColour,
	        fill: chartconf["gridBg"]
	    },
	    axis:{
	        stroke:	{ // the axis itself
	            color: axisColour,
	            width: null
	        },
            tick: {	// used as a foundation for all ticks
	            color:     tickColour,
	            position:  "center",
	            fontColor: chartconf["axisLabelFontColour"]
	        },
	        majorTick:	{ // major ticks on axis, and used for major gridlines
	            width:  gridlineWidth,
	            length: 6, 
                color: chartconf["majorGridlineColour"]
	        },
	        minorTick:	{ // minor ticks on axis, and used for minor gridlines
	            width:  2,
	            length: 4,
                color: chartconf["majorGridlineColour"]
	        },
	        microTick:	{ // minor ticks on axis, and used for minor gridlines
	            width:  1.7,
	            length: 3,
                color: tickColour
	        }
	    }
    });
    mychart.setTheme(sofa_theme);
    mychart.addAxis("x", {
                    labels: chartconf["xaxisLabels"], minorTicks: minorTicks,  microTicks: microTicks, minorLabels: minorTicks,
                    font: "normal normal normal " + chartconf["xfontsize"] + "pt Arial"
    });
    mychart.addAxis("y", {title: yTitle,  // normal normal bold
                    vertical: true, includeZero: true, font: "normal normal normal 10pt Arial", fontWeight: 12
    });
    mychart.addPlot("default", {type: "Areas", lines: true, areas: true, markers: true});
    mychart.addPlot("grid", {type: "Grid", vMajorLines: false});
    var i
    for (i in series){
        mychart.addSeries(series[i]["seriesLabel"], series[i]["yVals"], series[i]["style"]);
    }
    var anim_a = new dc.action2d.Magnify(mychart, "default");
    var anim_b = new dc.action2d.Tooltip(mychart, "default", {text: getTooltip, 
        tooltipBorderColour: tooltipBorderColour, connectorStyle: connectorStyle});
    mychart.render();
    var legend = new dojox.charting.widget.Legend({chart: mychart}, ("legend" + chartname.substr(0,1).toUpperCase() + chartname.substr(1)));
}

makeHistogram = function(chartname, datadets, chartconf){
    // allow charts made without newest config items to keep working
    var gridlineWidth = (chartconf["gridlineWidth"]) ? chartconf["gridlineWidth"] : 3;
    var tooltipBorderColour = (chartconf["tooltipBorderColour"]) ? chartconf["tooltipBorderColour"] : "#ada9a5";
    var outerChartBorderColour = (chartconf["outerChartBorderColour"]) ? chartconf["outerChartBorderColour"] : null;
    var innerChartBorderColour = (chartconf["innerChartBorderColour"]) ? chartconf["innerChartBorderColour"] : null;
    var outerBg = (chartconf["outerBg"]) ? chartconf["outerBg"] : null;
    var axisColour = (chartconf["axisColour"]) ? chartconf["axisColour"] : null;
    var tickColour = (chartconf["tickColour"]) ? chartconf["tickColour"] : null;
    var minorTicks = (chartconf["minorTicks"]) ? chartconf["minorTicks"] : false;
    var yTitle = (chartconf["yTitle"]) ? chartconf["yTitle"] : "P";
    var connectorStyle = (chartconf["connectorStyle"]) ? chartconf["connectorStyle"] : "defbrown";

    // chartwide functon setting - have access to val.element (Column), val.index (0), val.run.data (y_vals)
    var getTooltip = function(val){
        return "Values: " + datadets["binLabels"][val.index] + "<br>" + yTitle + ": " + val.y;
    };

    var dc = dojox.charting;
    var mychart = new dc.Chart2D(chartname);
    var sofa_theme = new dc.Theme({
        chart:{
	        stroke: outerChartBorderColour,
        	fill: outerBg,
	        pageStyle: null // suggested page style as an object suitable for dojo.style()
	    },
	    plotarea:{
	        stroke: innerChartBorderColour,
	        fill: chartconf["gridBg"]
	    },
	    axis:{
	        stroke:	{ // the axis itself
	            color: axisColour,
	            width: null
	        },
            tick: {	// used as a foundation for all ticks
	            color:     tickColour,
	            position:  "center",
	            fontColor: chartconf["axisLabelFontColour"]
	        },
	        majorTick:	{ // major ticks on axis, and used for major gridlines
	            width:  gridlineWidth,
	            length: 6, 
                color: chartconf["majorGridlineColour"]
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
                    labels: chartconf["xaxisLabels"], minorTicks: false, microTicks: false,
                    font: "normal normal normal " + chartconf["xfontsize"] + "pt Arial"
    });
    mychart.addAxis("x2", {min: chartconf["minVal"], max: chartconf["maxVal"],
                    minorTicks: minorTicks, 
                    font: "normal normal normal " + chartconf["xfontsize"] + "pt Arial"
    });
    mychart.addAxis("y", {title: yTitle,  // normal normal bold
                    vertical: true, includeZero: true, font: "normal normal normal 10pt Arial", fontWeight: 12
    });
    mychart.addPlot("default", {type: "ClusteredColumns", gap: 0, shadows: {dx: 12, dy: 12}});
    mychart.addPlot("grid", {type: "Grid", vMajorLines: false});
    mychart.addPlot("othergrid", {type: "Areas", hAxis: "x2", vAxis: "y"});
    mychart.addSeries(datadets["seriesLabel"], datadets["yVals"], datadets["style"]);

    var anim_a = new dc.action2d.Highlight(mychart, "default", {
        highlight: chartconf["sofaHl"],
        duration: 450,
        easing:   dojo.fx.easing.sineOut
    });
    var anim_b = new dc.action2d.Shake(mychart, "default");
    var anim_c = new dc.action2d.Tooltip(mychart, "default", {text: getTooltip, 
        tooltipBorderColour: tooltipBorderColour, connectorStyle: connectorStyle});
    mychart.render();
}

makeScatterplot = function(chartname, datadets, chartconf){
    // allow charts made without newest config items to keep working
    var gridlineWidth = (chartconf["gridlineWidth"]) ? chartconf["gridlineWidth"] : 3;
    var tooltipBorderColour = (chartconf["tooltipBorderColour"]) ? chartconf["tooltipBorderColour"] : "#ada9a5";
    var outerChartBorderColour = (chartconf["outerChartBorderColour"]) ? chartconf["outerChartBorderColour"] : null;
    var innerChartBorderColour = (chartconf["innerChartBorderColour"]) ? chartconf["innerChartBorderColour"] : null;
    var outerBg = (chartconf["outerBg"]) ? chartconf["outerBg"] : null;
    var axisColour = (chartconf["axisColour"]) ? chartconf["axisColour"] : null;
    var tickColour = (chartconf["tickColour"]) ? chartconf["tickColour"] : null;
    var minorTicks = (chartconf["minorTicks"]) ? chartconf["minorTicks"] : false;
    var xTitle = (chartconf["xTitle"]) ? chartconf["xTitle"] : "Variable A";
    var axisLabelDrop = (chartconf["axisLabelDrop"]) ? chartconf["axisLabelDrop"] : 0;
    var yTitle = (chartconf["yTitle"]) ? chartconf["yTitle"] : "Variable B";
    var connectorStyle = (chartconf["connectorStyle"]) ? chartconf["connectorStyle"] : "defbrown";

    // chartwide functon setting - have access to val.element (Column), val.index (0), val.run.data (y_vals)
    var getTooltip = function(val){
        return "(x: " + val.x + ", y: " + val.y + ")";
    };

    var dc = dojox.charting;
    var mychart = new dc.Chart2D(chartname, {margins: {l: 10, t: 10, r: 10, b: 10+axisLabelDrop}});
    var sofa_theme = new dc.Theme({
        chart:{
	        stroke: outerChartBorderColour,
        	fill: outerBg,
	        pageStyle: null // suggested page style as an object suitable for dojo.style()
	    },
	    plotarea:{
	        stroke: innerChartBorderColour,
	        fill: chartconf["gridBg"]
	    },
	    axis:{
	        stroke:	{ // the axis itself
	            color: axisColour,
	            width: null
	        },
            tick: {	// used as a foundation for all ticks
	            color:     tickColour,
	            position:  "center",
	            fontColor: chartconf["axisLabelFontColour"]
	        },
	        majorTick:	{ // major ticks on axis, and used for major gridlines
	            width:  gridlineWidth,
	            length: 6, 
                color: chartconf["majorGridlineColour"]
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
    mychart.addAxis("x", {title: xTitle,
                    min: 0, max: chartconf["xmax"],
                    minorTicks: true, microTicks: false,
                    font: "normal normal normal " + chartconf["xfontsize"] + "pt Arial"
    });
    mychart.addAxis("y", {title: yTitle,
                    min: 0, max: chartconf["ymax"],
                    vertical: true, includeZero: true, font: "normal normal normal 10pt Arial", fontWeight: 12
    });
    mychart.addPlot("default", {type: "Scatter"});
    mychart.addPlot("grid", {type: "Grid", vMajorLines: true});
    mychart.addSeries(datadets["seriesLabel"], datadets["xyPairs"], datadets["style"]);

    var anim_a = new dc.action2d.Highlight(mychart, "default", {
        highlight: chartconf["sofaHl"],
        duration: 450,
        easing:   dojo.fx.easing.sineOut
    });
    var anim_b = new dc.action2d.Shake(mychart, "default");
    var anim_c = new dc.action2d.Tooltip(mychart, "default", {text: getTooltip, 
        tooltipBorderColour: tooltipBorderColour, connectorStyle: connectorStyle});
    mychart.render();
}
