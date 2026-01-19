import React, { Component } from "react";
import { Line } from "react-chartjs-2";

const data = {
  defaultFontFamily: "Poppins",
  labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"],
  datasets: [
    {
      label: "My First dataset",
      data: [25, 20, 60, 41, 66, 45, 80],
      borderColor: "rgba(58, 122, 254, 1)",
      borderWidth: "2",
      backgroundColor: "rgba(58, 122, 254,1)",
      pointBackgroundColor: "rgba(58, 122, 254,1)",
	    tension:0.4
    },
    {
      label: "My Second dataset",
      data: [5, 20, 15, 41, 35, 65, 80],
      borderColor: "rgba(235,100,29, 1)",
      borderWidth: "2",
      backgroundColor: "rgba(235,100,29, 1)",
      pointBackgroundColor: "rgba(235,100,29, 1)",
	     tension:0.4
    },
  ],
};

const options = {
  plugins:{
	  legend: false,
	  tooltip: {
		intersect: false,
	  },
	  hover: {
		// mode: "nearest",
		intersect: true,
	  }
  },
  scales: {
    y: 
      {
        max: 100,
        min: 0,
        ticks: {
          beginAtZero: true,
          stepSize: 20,
          padding: 10,
        },
      },
    
    x: 
      {
        ticks: {
          padding: 5,
        },
      },
    
  },
};
class DualLine extends Component {
  render() {
    return <Line data={data} options={options} height={150} />;
  }
}

export default DualLine;
