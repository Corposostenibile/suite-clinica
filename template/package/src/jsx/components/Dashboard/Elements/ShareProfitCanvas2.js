import React, { Component } from "react";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import { Doughnut } from "react-chartjs-2";

ChartJS.register(ArcElement, Tooltip, Legend);

class ShareProfitCanvas extends Component {
  render() {
	 
    const data = {
      datasets: [
        {
          data: [45, 25, 20],
          borderWidth: 3, 
          borderColor: "rgba(255, 255, 255, 1)",
          backgroundColor: [
            "rgba(58, 122, 254, 1)",
            "rgba(255, 159, 0, 1)",
            "rgba(41, 200, 112, 1)"
          ],
          hoverBackgroundColor: [
            "rgba(58, 122, 254, 0.9)",
            "rgba(255, 159, 0, .9)",
            "rgba(41, 200, 112, .9)"
          ]
        },
      ],
    };

    const options = {
      weight: 1,	
      cutout: "70%",
      responsive: true,
      maintainAspectRatio: false
      
    };

    return (
      <div >
        <Doughnut
          data={data}
         // width={this.props.width ? this.props.width : 433}
          height={this.props.height ? this.props.height : 100}
          options={options}
        />
      </div>
    );
  }
}

export default ShareProfitCanvas;
