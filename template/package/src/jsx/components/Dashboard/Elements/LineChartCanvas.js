import React, { Component } from "react";
import { Line } from "react-chartjs-2";

import {
	Chart as ChartJS,
	CategoryScale,
	LinearScale,
	PointElement,
	LineElement,
	Title,
	Tooltip,
	Legend,
	Filler
} from 'chart.js';

ChartJS.register(
	CategoryScale,
	LinearScale,
	PointElement,
	LineElement,
	Title,
	Tooltip,
	Legend,
	Filler
  );

class LineChartCanvas extends Component {
  render() {
	 
    const data = {
		defaultFontFamily: 'Poppins',
		labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"],
		datasets: [{
			label: "My First dataset",
			data: [90, 80, 90, 70, 90, 75, 100],
			borderColor: 'rgba(255,255,255,0.30)',
			borderWidth: "1",
			backgroundColor: 'rgba(255,255,255,0.10)', 
			tension : "0.5",
			fill: true,
			// pointBackgroundColor: 'rgba(26, 51, 213, 0.5)'
		}, {
			label: "My First dataset",
			data: [70, 60, 70, 50, 70, 55, 80],
			borderColor: 'rgba(255,255,255,0.50)',
			borderWidth: "1",
			backgroundColor: 'rgba(255,255,255,0.20)',
			tension : "0.5",
			fill: true,
			// pointBackgroundColor: 'rgba(56, 164, 248, 1)'
		}]
    };

    const options = {
		responsive:true,
		plugins : {
			legend: false,
		}, 
		elements: {
			point:{
				radius: 0
			}
		},
		scales: {
			y: {
				max: 100, 
				min: 0, 
				ticks: {
					beginAtZero: true, 
					stepSize: 20, 
					padding: 10
				},
				display:false,
			},
			x: { 
				ticks: {
					padding: 5
				},
				display:false,
			}
		}
      
    };

    return (
      <div >
        <Line
          data={data}
         // width={this.props.width ? this.props.width : 433}
          height={this.props.height ? this.props.height : 150}
          options={options}
        />
      </div>
    );
  }
}

export default LineChartCanvas;
