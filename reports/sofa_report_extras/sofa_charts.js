
makePieChart = function(chartname, slices, chartconf){
    // allow charts made without newest config items to keep working

    var tooltipBorderColour = (chartconf["tooltipBorderColour"]) ? chartconf["tooltipBorderColour"] : "#ada9a5";
    var outerChartBorderColour = (chartconf["outerChartBorderColour"]) ? chartconf["outerChartBorderColour"] : null;
    var innerChartBorderColour = (chartconf["innerChartBorderColour"]) ? chartconf["innerChartBorderColour"] : null;
    var outerBg = (chartconf["outerBg"]) ? chartconf["outerBg"] : null;
    var pieStroke = "#8b9b98";

    var dc = dojox.charting;
    var mychart = new dc.Chart2D(chartname);
    
    
    var sofa_theme = new dc.Theme({
		colors: chartconf["sliceColours"],
        chart: {
	        stroke: outerChartBorderColour,
        	fill: outerBg,
	        pageStyle: null // suggested page style as an object suitable for dojo.style()
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
    var anim_c = new dc.action2d.Tooltip(mychart, "default", {tooltipBorderColour: tooltipBorderColour});
    mychart.render();
    //var legend = new dojox.charting.widget.Legend({chart: mychart}, ("legend" + chartname.substr(0,1).toUpperCase() + chartname.substr(1)));
}

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

    //mychart.setTheme(dc.themes.PlotKit.blue); //purple, red, cyan, green etc

    mychart.addAxis("x", {
                    labels: chartconf["xaxisLabels"], minorTicks: minorTicks, 
                    font: "normal normal normal " + chartconf["xfontsize"] + "pt Arial"
    });
    mychart.addAxis("y", { // normal normal bold
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
    var anim_c = new dc.action2d.Tooltip(mychart, "default", {tooltipBorderColour: tooltipBorderColour});
    mychart.render();
    var legend = new dojox.charting.widget.Legend({chart: mychart}, ("legend" + chartname.substr(0,1).toUpperCase() + chartname.substr(1)));
}
