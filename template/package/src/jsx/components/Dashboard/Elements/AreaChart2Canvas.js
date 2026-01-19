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

class AreaChart2Canvas extends Component {
  render() {
	 
    const data = {
		defaultFontFamily: 'Poppins',
		labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"],
		datasets: [{
			label: "My First dataset",
			data: [60, 80, 60, 40, 70, 55, 95],
			borderColor: "#10ca93",
			borderWidth: "3",
			backgroundColor: "rgba(16, 202, 147, 0.1)",
			tension : 0.5,
			fill: true,
		}]
    };

    const options = {
		plugins : {
			legend: false
		},
		tooltips: {
			enabled: false,
		},
		elements: {
			point:{
				radius: 0
			}
		},
		legend: false, 
		scales: {
			
			y: {			
				max: 100, 
				min: 0, 	
				beginAtZero: true, 
				ticks: {
					stepSize: 10, 
					padding: 2
				},
				display:false,
			},
			x: { 
				ticks: {
					padding: 2
				},
				display:false,
			}
		}
      
    };

    return (
      <div 
	  	// style={{width:"100%"}}
		>
        <Line
          data={data}         
          height={this.props.height ? this.props.height : 90}
		  
          options={options}
        />
      </div>
    );
  }
}

export default AreaChart2Canvas;
