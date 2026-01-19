import React from 'react';
import {Dropdown} from 'react-bootstrap';

//images
import avtar1 from './../../../../images/avatar/1.jpg';
import LineChartCanvas from './LineChartCanvas';

function DropdownBlog(){
	return(
		<Dropdown className="dropdown">
			<Dropdown.Toggle as="button"  type="button" className="btn btn-primary light sharp i-false" >
				<svg width="20px" height="20px" viewBox="0 0 24 24" version="1.1">
					<g stroke="none" strokeWidth="1" fill="none" fillRule="evenodd">
						<rect x="0" y="0" width="24" height="24"/>
						<circle fill="#000000" cx="5" cy="12" r="2"/>
						<circle fill="#000000" cx="12" cy="12" r="2"/>
						<circle fill="#000000" cx="19" cy="12" r="2"/></g>
					</svg>
			</Dropdown.Toggle>
			<Dropdown.Menu className="dropdown-menu">
				<Dropdown.Item>Edit</Dropdown.Item>
				<Dropdown.Item>Delete</Dropdown.Item>
			</Dropdown.Menu>
		</Dropdown>
	)
} 

const timeline = [
	{  title:'Dr Sultads Send You', demo:'image'},
	{  title:'Resport created', demo:'name', },
	{  title:'Reminder : Treatment', demo:'icon',  },
];

const TopProducts = () =>{
	return(
		<>
			<div className="card-body"> 
				<div className="widget-media">
					<ul className="timeline">
						{timeline.map((data , ind)=>(
							<li key={ind}>
								<div className="timeline-panel">
									{
									    data.demo === "image" ? 
											<div className="media me-2">
												<img alt="man" width="50" src={avtar1} />
											</div>
										:
										data.demo === "name" ?
											<div className="media me-2 media-info">
												KG
											</div>
										:
										data.demo === "icon" ? 
											<div className="media me-2 media-success">
												<i className="fa fa-home" />
											</div>
										:
										""
									}
									<div className="media-body">
										<h5 className="mb-1 text-white">{data.title}</h5>
										<small className="d-block">29 July 2021 - 02:26 PM</small>
									</div>
									<DropdownBlog />
								</div>
							</li>
						
						))}												
					</ul>
				</div>
			</div>	
			<LineChartCanvas />	
		</>
	)
}
export default TopProducts;