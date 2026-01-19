import React,{ useState, useRef, useEffect } from 'react';
import { Link } from "react-router-dom";

const tableData = [
	{money: '542', name:'Dr. Jackson', date:'01 November 2023',status:'Successful', color:'success'},
	{money: '200', name:'Niketan', date:'21 August 2023',status:'Canceled', color:'danger'},
	{money: '405', name:'Dr. Mike', date:'09 September 2023',status:'Pending', color:'warning '},
	{money: '610', name:'Herry Benre', date:'12 October 2023',status:'Canceled', color:'danger'},
];

const PaymentTable = () =>{
	const [data, setData] = useState(
		document.querySelectorAll("#example2_wrapper tbody tr")
	);
	const sort = 10;
	const activePag = useRef(0);
	const [test] = useState(0);

	// Active data
	const chageData = (frist, sec) => {
		for (var i = 0; i < data.length; ++i) {
			if (i >= frist && i < sec) {
				data[i].classList.remove("d-none");
			} else {
				data[i].classList.add("d-none");
			}
		}
	};
   // use effect
   useEffect(() => {
      setData(document.querySelectorAll("#example2_wrapper tbody tr"));      
	}, [test]);

  
   // Active pagginarion
   activePag.current === 0 && chageData(0, sort);
   
   
   const chackboxFun = (type) => {
	setTimeout(() => {
		const chackbox = document.querySelectorAll(".sorting_1 input");
		const motherChackBox = document.querySelector(".sorting_asc input");
		for (let i = 0; i < chackbox.length; i++) {
			const element = chackbox[i];
			if (type === "all") {
				if (motherChackBox.checked) {
					element.checked = true;
				} else {
					element.checked = false;
				}
			} else {
				if (!element.checked) {
					motherChackBox.checked = false;
				break;
				} else {
					motherChackBox.checked = true;
				}
			}
		}
	}, 100);
   };
	return(
		<>
			<div className="table-responsive">
				<div id="example2_wrapper" className="dataTables_wrapper no-footer">
					<table
						id="example2"
						className="table table-responsive-sm mb-0"
					>
						<thead>
							<tr role="row">
								<th className="sorting_asc ">
									<div className="form-check">
										<input type="checkbox" onClick={() => chackboxFun("all")} className="form-check-input" id="checkAll" required=""/>
										<label className="form-check-label" htmlFor="checkAll"></label>
									</div>
								</th>
								<th className="sorting_asc"><strong>Amount</strong></th>
								<th className="sorting"><strong>NAME</strong></th>
								<th className="sorting"><strong>DATE</strong></th>
								<th className="sorting"><strong>STATUS</strong></th>
								<th style={{width:"85px"}}><strong>EDIT</strong></th>
							</tr>
						</thead>
						<tbody>
							{tableData.map(( data,  ind)=>(
								<tr role="row" className="odd" key={ind}>
									<td className="sorting_1">
										<div className="form-check">
											<input type="checkbox" 
												onClick={() => chackboxFun()} className="form-check-input"
												id={`customCheckBox2${ind + 1}`}
												required=""
											/>
											<label className="form-check-label" htmlFor={`customCheckBox2${ind + 1}`} />
										</div>
									</td>
									<td><b>${data.money}</b></td>
									<td>{data.name}</td>
									<td>{data.date}</td>
									<td className="recent-stats">
										<i className={`fa fa-circle me-1 text-${data.color}`} />
										{data.status}
									</td>
									<td>
										<Link to={"#"} className="btn btn-primary shadow btn-xs sharp me-2"><i className="fa fa-pencil" /></Link>
										<Link to={"#"} className="btn btn-danger shadow btn-xs sharp"><i className="fa fa-trash" /></Link>
									</td>
								</tr>
							))}							
						</tbody>
					</table>
				</div>
			</div>
		</>
	)
}
export default PaymentTable;