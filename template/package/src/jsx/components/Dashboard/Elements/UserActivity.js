import {Tab, Nav} from 'react-bootstrap';

import HistoryActivity from './HistoryActivity';

const UserActivity = () => {
	return(
		<>
			<Tab.Container defaultActiveKey="Day">
				<div id="user-activity" className="card">
					<div className="card-header border-0 pb-0 d-sm-flex d-block">
						<div>
							<h4 className="card-title">History 2013 - 2021</h4>
							<p className="mb-1">Lorem Ipsum is simply dummy text of the printing</p>
						</div>
						<div className="card-action">
							<Nav as="ul" className="nav nav-tabs" role="tablist">
								<Nav.Item as="li" className="nav-item">
									<Nav.Link className="nav-link"  eventKey="Day">
										Monthly
									</Nav.Link>
								</Nav.Item >
								<Nav.Item as="li" className="nav-item">
									<Nav.Link className="nav-link"  eventKey="Month" >
										Weekly
									</Nav.Link>
								</Nav.Item >
								<Nav.Item as="li" className="nav-item">
									<Nav.Link className="nav-link" eventKey="Year" >
										Today
									</Nav.Link>
								</Nav.Item >
							</Nav>
						</div>
					</div>
					<div className="card-body">						
						<Tab.Content  id="myTabContent">
							<Tab.Pane eventKey="Day" >
								<HistoryActivity dataActive={0} />
							</Tab.Pane>
							<Tab.Pane eventKey="Month" >
								<HistoryActivity dataActive={1} />
							</Tab.Pane>
							<Tab.Pane eventKey="Year">
								<HistoryActivity dataActive={2} />
							</Tab.Pane>
						</Tab.Content>
					</div>
				</div>
			</Tab.Container>	
		</>
	)
}
export default UserActivity;
