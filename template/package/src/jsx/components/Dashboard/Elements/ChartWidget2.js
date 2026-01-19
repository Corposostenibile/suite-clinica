import React, { Component } from "react";
import { Bar } from "react-chartjs-2";

class ChartWidget2 extends Component {
  render() {
	 
    const data = {
		defaultFontFamily: 'Poppins',
		 labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
		datasets: [{
			label: "My First dataset",
			data: [65, 59, 80, 81, 56, 55, 40, 88, 45, 95, 54, 76],
			borderColor: "rgba(0, 0, 0, 250)",
			borderWidth: "0",
			backgroundColor: "#a0bfff", 
			hoverBackgroundColor: "#a0bfff",
			barPercentage: 0.3, 
		}]
    };

    const options = {
		plugins : {
			legend: false,
		},
		responsive: true, 
		maintainAspectRatio: false,  
		scales: {
			y: {
				display: false, 
				max: 100, 
				min: 0, 
				ticks: {
					beginAtZero: true, 
					display: false, 
					stepSize: 10
				}, 
				grid: {
					display: false, 
					drawBorder: false
				}
			},
			x: {
				display: false, 				
				grid: {
					display: false, 
					drawBorder: false
				}, 
				ticks: {
					display: false
				}
			}
		}
      
    };

    return (
      <div >
        <Bar
          data={data}         
          height={this.props.height ? this.props.height : 85}
          options={options}
        />
      </div>
    );
  }
}

export default ChartWidget2;
