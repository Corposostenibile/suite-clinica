import React, { Component } from "react";
import { Bar } from "react-chartjs-2";

class DailySalesCanvas extends Component {
  render() {	 
    const data = {
		defaultFontFamily: 'Poppins',
		labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
		datasets: [{
			label: 'Expense',
			backgroundColor: '#3a7afe',
			hoverBackgroundColor: '#3a7afe', 
			data: ['20','14','18','25','27','22','12','24','20','14','18','16'],
			barPercentage: 0.5
		}, {
			label: 'Earning',
			backgroundColor: '#dfe3ec',
			hoverBackgroundColor: '#dfe3ec', 
			data: ['12','18','14','7','5','10','20','8','12','18','14','16'],
			barPercentage: 0.5
		}]
    };

    const options = {
		plugins:{
			legend: false,
		},
		title: {
			display: false
		},
		tooltips: {
			mode: 'index',
			intersect: false
		},
		responsive: true,
		maintainAspectRatio: false, 
		scales: {
			x: {
				display: false, 
				stacked: true,
				 
				ticks: {
					display: false
				}, 
				grid: {
					display: false, 
					drawBorder: false
				}
			},
			y: {
				display: false, 
				stacked: true, 
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

export default DailySalesCanvas;
