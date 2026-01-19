import React,{useContext, useEffect} from 'react';
import {Link} from 'react-router-dom';
import loadable from "@loadable/component";
import pMinDelay from "p-min-delay";

import { Sparklines, SparklinesLine} from "react-sparklines";


//Import Components
import { ThemeContext } from "../../../context/ThemeContext";
import PaymentTable from './Elements/PaymentTable';
import TopProducts from './Elements/TopProducts';
import ActivityTab from './Elements/ActivityTab';
import UserActivity from './Elements/UserActivity';

const AreaChart2Canvas = loadable(() =>
	pMinDelay(import("./Elements/AreaChart2Canvas"), 1000)
);
const ChartWidget2 = loadable(() =>
	pMinDelay(import("./Elements/ChartWidget2"), 1000)
);
const ShareProfitCanvas2 = loadable(() =>
	pMinDelay(import("./Elements/ShareProfitCanvas2"), 1000)
);
const ActiveUserCanvas = loadable(() =>
	pMinDelay(import("./Elements/ActiveUserCanvas"), 1000)
);

const sampleData = [  6,2,8,4,3,8,4,3,6,5,9,2, ];

const Home = () => {
	const { 
        changeBackground,
        changeSideBarStyle,
        chnageSidebarColor,
        changeNavigationHader    
    } = useContext(ThemeContext);
	  useEffect(() => {
		changeBackground({ value: "light", label: "Light" });
        changeSideBarStyle({ value: "mini", label: "Mini" });
        chnageSidebarColor("color_3");
        changeNavigationHader("color_3");
       
	}, []);
	return(
		<>
			<AllSection />
		</>
	)
}

function AllSection(){
    return(        
        <div className="row">
            <div className="col-xl-9 col-xxl-12">
                <div className="row">
                    <div className="col-xl-3 col-xxl-3 col-lg-6 col-sm-6">
                        <div className="card overflow-hidden">
                            <div className="card-body pb-0 px-4 pt-4">
                                <div className="row">
                                    <div className="col">
                                        <h5 className="mb-1">2000</h5>
                                        <span className="text-success">Total Sale</span>
                                    </div>
                                </div>
                            </div>
                            <div className="chart-wrapper">									
                                <AreaChart2Canvas />
                            </div>
                        </div>
                    </div>
                    <div className="col-xl-3 col-xxl-3 col-lg-6 col-sm-6">
                        <div className="card bg-success	overflow-hidden">
                            <div className="card-body pb-0 px-4 pt-4">
                                <div className="row">
                                    <div className="col">
                                        <h5 className="text-white mb-1">$14000</h5>
                                        <span className="text-white">Total Eraning</span>
                                    </div>
                                </div>
                            </div>
                            <div className="chart-wrapper" style={{width:"100%"}}>
                                <Sparklines data={sampleData}>
                                    <SparklinesLine color="#39f4bc" 
                                        style={{stroke : "#20dea6", strokeWidth: 1,fill: "#fff"}}
                                    />
                                </Sparklines>
                            </div>
                        </div>
                    </div>
                    <div className="col-xl-3 col-xxl-3 col-lg-6 col-sm-6">
                        <div className="card bg-primary overflow-hidden">
                            <div className="card-body pb-0 px-4 pt-4">
                                <div className="row">
                                    <div className="col text-white">
                                        <h5 className="text-white mb-1">570</h5>
                                        <span>VIEWS OF YOUR PROJECT</span>
                                    </div>
                                </div>
                            </div>
                            <div className="chart-wrapper px-2">									
                                <ChartWidget2 />
                            </div>
                        </div>
                    </div>
                    <div className="col-xl-3 col-xxl-3 col-lg-6 col-sm-6">
                        <div className="card overflow-hidden">
                            <div className="card-body px-4 py-4">
                                <h5 className="mb-3">1700 / <small className="text-primary">Sales Status</small></h5>
                                <div className="chart-point">
                                    <div className="check-point-area">											
                                        <ShareProfitCanvas2 />
                                    </div>
                                    <ul className="chart-point-list">
                                        <li><i className="fa fa-circle text-primary me-1" /> 40% Tickets</li>
                                        <li><i className="fa fa-circle text-success me-1" /> 35% Events</li>
                                        <li><i className="fa fa-circle text-warning me-1" /> 25% Other</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>		
                    <div className="col-xl-4 col-xxl-4 col-lg-12 col-md-12">
                        <div className="card">
                            <div className="card-header border-0 pb-0">
                                <h4 className="card-title">Timeline</h4>
                            </div>
                            <div className="card-body p-0">									
                                <div id="DZ_W_TimeLine1" className="widget-timeline dz-scroll style-1 px-4 ms-2 py-2 my-4" style={{height:"250px"}}>
                                    <ul className="timeline">
                                        <li>
                                            <div className="timeline-badge primary"></div>
                                            <Link to={"#"} className="timeline-panel text-muted" >
                                                <span>10 minutes ago</span>
                                                <h6 className="mb-0">Youtube, a video-sharing website <strong className="text-primary">$500</strong>.</h6>
                                            </Link>
                                        </li>
                                        <li>
                                            <div className="timeline-badge info">
                                            </div>
                                            <Link to={"#"} className="timeline-panel text-muted">
                                                <span>20 minutes ago</span>
                                                <h6 className="mb-0">New order placed <strong className="text-info">#XF-2356.</strong></h6>
                                                <p className="mb-0">Quisque a consequat ante Sit...</p>
                                            </Link>
                                        </li>
                                        <li>
                                            <div className="timeline-badge danger">
                                            </div>
                                            <Link to={"#"} className="timeline-panel text-muted">
                                                <span>30 minutes ago</span>
                                                <h6 className="mb-0">john just buy your product <strong className="text-warning">Sell $250</strong></h6>
                                            </Link>
                                        </li>
                                        <li>
                                            <div className="timeline-badge success">
                                            </div>
                                            <Link to={"#"} className="timeline-panel text-muted">
                                                <span>15 minutes ago</span>
                                                <h6 className="mb-0">StumbleUpon is acquired by eBay. </h6>
                                            </Link>
                                        </li>
                                    </ul>
                                </div>									
                            </div>
                        </div>
                    </div>	
                    <div className="col-xl-8 col-xxl-8 col-lg-12 col-md-12">
                        <div className="card">
                            <div className="card-header border-0 pb-0">
                                <h4 className="card-title">Recent Payments Queue</h4>
                            </div>
                            <div className="card-body">
                                <PaymentTable />
                            </div>
                        </div>	
                    </div>
                </div>	
            </div>	
            <div className="col-xl-3 col-xxl-4 col-lg-12 col-md-12">
                <div className="card bg-primary text-white">
                    <div className="card-header pb-0 border-0">
                        <h4 className="card-title text-white">TOP PRODUCTS</h4>
                    </div>
                    <TopProducts />
                </div>	
            </div>
            <div className="col-xl-3 col-xxl-4 col-lg-6 col-md-6">
                <div className="card bg-info activity_overview">
                    <div className="card-header  border-0 pb-3 ">
                        <h4 className="card-title text-white">Activity</h4>
                    </div>
                    <ActivityTab />
                </div>	
            </div>
            <div className="col-xl-3 col-xxl-4 col-lg-6 col-md-6">
                <div className="card active_users">
                    <div className="card-header bg-success border-0 pb-0">
                        <h4 className="card-title text-white">Active Users</h4>
                    </div>
                    <div className="bg-success">
                        <ActiveUserCanvas />
                    </div>
                    <div className="card-body pt-0">
                        <div className="list-group-flush mt-4">
                            <div className="list-group-item bg-transparent d-flex justify-content-between px-0 py-1 font-weight-semi-bold border-0 border-bottom" 
                                style={{borderColor: "rgba(255, 255, 255, 0.15)"}}
                            >
                                <p className="mb-0">Top Active Pages</p>
                                <p className="mb-0">Active Users</p>
                            </div>
                            <div className="list-group-item bg-transparent d-flex justify-content-between px-0 py-1 border-0 border-bottom" 
                                style={{borderColor: "rgba(255, 255, 255, 0.05)"}}
                            >
                                <p className="mb-0">/bootstrap-themes/</p>
                                <p className="mb-0">3</p>
                            </div>
                            <div className="list-group-item bg-transparent d-flex justify-content-between px-0 py-1 border-0 border-bottom" 
                                style={{borderColor: "rgba(255, 255, 255, 0.05)"}}
                            >
                                <p className="mb-0">/tags/html5/</p>
                                <p className="mb-0">3</p>
                            </div>								
                            <div className="list-group-item bg-transparent d-flex justify-content-between px-0 py-1 border-0 border-bottom" 
                                style={{borderColor: "rgba(255, 255, 255, 0.05)"}}
                            >
                                <p className="mb-0">/100-best-themes...all-time/</p>
                                <p className="mb-0">1</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div className="col-xl-6 col-xxl-12 col-lg-12 col-md-12">
                <UserActivity />
            </div>
        </div>	
    )
}

export {AllSection};
export default Home;