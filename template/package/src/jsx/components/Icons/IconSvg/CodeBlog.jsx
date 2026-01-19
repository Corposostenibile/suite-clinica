import React, {useState} from 'react';
import {Link} from 'react-router-dom';
import {Modal} from 'react-bootstrap';


const CodeBlog = () =>{
	const [backspaceSvg, setBackspaceSvg] = useState(false);
	const [backspaceCode, setBackspaceCode] = useState(false);
	const [cmdSvg, setCmdSvg] = useState(false);
	const [cmdCode, setCmdCode] = useState(false);
	const [codeSvg, setCodeSvg] = useState(false);
	const [codeCode, setCodeCode] = useState(false);
	const [commitSvg, setCommitSvg] = useState(false);
	const [commitCode, setCommitCode] = useState(false);
	const [compilingSvg, setCompilingSvg] = useState(false);
	const [compilingCode, setCompilingCode] = useState(false);
	const [controlSvg, setControlSvg] = useState(false);
	const [controlCode, setControlCode] = useState(false);
	const [doneSvg, setDoneSvg] = useState(false);
	const [doneCode, setDoneCode] = useState(false);
	const [errorSvg, setErrorSvg] = useState(false);
	const [errorCode, setErrorCode] = useState(false);
	const [gitSvg, setGitSvg] = useState(false);
	const [gitCode, setGitCode] = useState(false);
	const [git2Svg, setGit2Svg] = useState(false);
	const [git2Code, setGit2Code] = useState(false);
	const [git3Svg, setGit3Svg] = useState(false);
	const [git3Code, setGit3Code] = useState(false);
	const [git4Svg, setGit4Svg] = useState(false);
	const [git4Code, setGit4Code] = useState(false);
	const [githubSvg, setGithubSvg] = useState(false);
	const [githubCode, setGithubCode] = useState(false);
	const [infoSvg, setInfoSvg] = useState(false);
	const [infoCode, setInfoCode] = useState(false);
	const [leftSvg, setLeftSvg] = useState(false);
	const [leftCode, setLeftCode] = useState(false);
	const [loadingSvg, setLoadingSvg] = useState(false);
	const [loadingCode, setLoadingCode] = useState(false);
	const [lockSvg, setLockSvg] = useState(false);
	const [lockCode, setLockCode] = useState(false);
	const [lockOverSvg, setLockOverSvg] = useState(false);
	const [lockOverCode, setLockOverCode] = useState(false);
	const [minusSvg, setMinusSvg] = useState(false);
	const [minusCode, setMinusCode] = useState(false);
	const [optionSvg, setOptionSvg] = useState(false);
	const [optionCode, setOptionCode] = useState(false);
	const [plusSvg, setPlusSvg] = useState(false);
	const [plusCode, setPlusCode] = useState(false);
	const [puzzleSvg, setPuzzleSvg] = useState(false);
	const [puzzleCode, setPuzzleCode] = useState(false);
	const [questionSvg, setQuestionSvg] = useState(false);
	const [questionCode, setQuestionCode] = useState(false);
	const [rightSvg, setRightSvg] = useState(false);
	const [rightCode, setRightCode] = useState(false);
	const [settingsSvg, setSettingsSvg] = useState(false);
	const [settingsCode, setSettingsCode] = useState(false);
	const [shiftSvg, setShiftSvg] = useState(false);
	const [shiftCode, setShiftCode] = useState(false);
	const [spySvg, setSpySvg] = useState(false);
	const [spyCode, setSpyCode] = useState(false);
	const [stopSvg, setStopSvg] = useState(false);
	const [stopCode, setStopCode] = useState(false);
	const [terminalSvg, setTerminalSvg] = useState(false);
	const [terminalCode, setTerminalCode] = useState(false);
	const [thunderSvg, setThunderSvg] = useState(false);
	const [thunderCode, setThunderCode] = useState(false);
	const [timeSvg, setTimeSvg] = useState(false);
	const [timeCode, setTimeCode] = useState(false);
	const [warningSvg, setWarningSvg] = useState(false);
	const [warningCode, setWarningCode] = useState(false);
	const [warning2Svg, setWarning2Svg] = useState(false);
	const [warning2Code, setWarning2Code] = useState(false);
	return(
		<>
			<div className="row">
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className=" svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<path d="M8.42034438,20 L21,20 C22.1045695,20 23,19.1045695 23,18 L23,6 C23,4.8954305 22.1045695,4 21,4 L8.42034438,4 C8.15668432,4 7.90369297,4.10412727 7.71642146,4.28972363 L0.653241109,11.2897236 C0.260966303,11.6784895 0.25812177,12.3116481 0.646887666,12.7039229 C0.648995955,12.7060502 0.651113791,12.7081681 0.653241109,12.7102764 L7.71642146,19.7102764 C7.90369297,19.8958727 8.15668432,20 8.42034438,20 Z" fill="#000000" opacity="0.3"></path>
																	<path d="M12.5857864,12 L11.1715729,10.5857864 C10.7810486,10.1952621 10.7810486,9.56209717 11.1715729,9.17157288 C11.5620972,8.78104858 12.1952621,8.78104858 12.5857864,9.17157288 L14,10.5857864 L15.4142136,9.17157288 C15.8047379,8.78104858 16.4379028,8.78104858 16.8284271,9.17157288 C17.2189514,9.56209717 17.2189514,10.1952621 16.8284271,10.5857864 L15.4142136,12 L16.8284271,13.4142136 C17.2189514,13.8047379 17.2189514,14.4379028 16.8284271,14.8284271 C16.4379028,15.2189514 15.8047379,15.2189514 15.4142136,14.8284271 L14,13.4142136 L12.5857864,14.8284271 C12.1952621,15.2189514 11.5620972,15.2189514 11.1715729,14.8284271 C10.7810486,14.4379028 10.7810486,13.8047379 11.1715729,13.4142136 L12.5857864,12 Z" fill="#000000"></path>
																</g>
															</svg> </div>
														<div className="svg-classname">
															Backspace.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setBackspaceSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setBackspaceCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={backspaceSvg} onHide={setBackspaceSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" id="svg_img_label_Backspacesvg">Backspace.svg</h5>
																		<button type="button" className="close" onClick={()=>setBackspaceSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Backspace.svg"/&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setBackspaceSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={backspaceCode} onHide={setBackspaceCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Backspace.svg</h5>
																		<button type="button" className="close" onClick={()=>setBackspaceCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;path d="M8.42034438,20 L21,20 C22.1045695,20 23,19.1045695 23,18 L23,6 C23,4.8954305 22.1045695,4 21,4 L8.42034438,4 C8.15668432,4 7.90369297,4.10412727 7.71642146,4.28972363 L0.653241109,11.2897236 C0.260966303,11.6784895 0.25812177,12.3116481 0.646887666,12.7039229 C0.648995955,12.7060502 0.651113791,12.7081681 0.653241109,12.7102764 L7.71642146,19.7102764 C7.90369297,19.8958727 8.15668432,20 8.42034438,20 Z" fill="#000000" opacity="0.3"/&gt;
        &lt;path d="M12.5857864,12 L11.1715729,10.5857864 C10.7810486,10.1952621 10.7810486,9.56209717 11.1715729,9.17157288 C11.5620972,8.78104858 12.1952621,8.78104858 12.5857864,9.17157288 L14,10.5857864 L15.4142136,9.17157288 C15.8047379,8.78104858 16.4379028,8.78104858 16.8284271,9.17157288 C17.2189514,9.56209717 17.2189514,10.1952621 16.8284271,10.5857864 L15.4142136,12 L16.8284271,13.4142136 C17.2189514,13.8047379 17.2189514,14.4379028 16.8284271,14.8284271 C16.4379028,15.2189514 15.8047379,15.2189514 15.4142136,14.8284271 L14,13.4142136 L12.5857864,14.8284271 C12.1952621,15.2189514 11.5620972,15.2189514 11.1715729,14.8284271 C10.7810486,14.4379028 10.7810486,13.8047379 11.1715729,13.4142136 L12.5857864,12 Z" fill="#000000"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setBackspaceCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className=" svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<path d="M9,15 L7.5,15 C6.67157288,15 6,15.6715729 6,16.5 C6,17.3284271 6.67157288,18 7.5,18 C8.32842712,18 9,17.3284271 9,16.5 L9,15 Z M9,15 L9,9 L15,9 L15,15 L9,15 Z M15,16.5 C15,17.3284271 15.6715729,18 16.5,18 C17.3284271,18 18,17.3284271 18,16.5 C18,15.6715729 17.3284271,15 16.5,15 L15,15 L15,16.5 Z M16.5,9 C17.3284271,9 18,8.32842712 18,7.5 C18,6.67157288 17.3284271,6 16.5,6 C15.6715729,6 15,6.67157288 15,7.5 L15,9 L16.5,9 Z M9,7.5 C9,6.67157288 8.32842712,6 7.5,6 C6.67157288,6 6,6.67157288 6,7.5 C6,8.32842712 6.67157288,9 7.5,9 L9,9 L9,7.5 Z M11,13 L13,13 L13,11 L11,11 L11,13 Z M13,11 L13,7.5 C13,5.56700338 14.5670034,4 16.5,4 C18.4329966,4 20,5.56700338 20,7.5 C20,9.43299662 18.4329966,11 16.5,11 L13,11 Z M16.5,13 C18.4329966,13 20,14.5670034 20,16.5 C20,18.4329966 18.4329966,20 16.5,20 C14.5670034,20 13,18.4329966 13,16.5 L13,13 L16.5,13 Z M11,16.5 C11,18.4329966 9.43299662,20 7.5,20 C5.56700338,20 4,18.4329966 4,16.5 C4,14.5670034 5.56700338,13 7.5,13 L11,13 L11,16.5 Z M7.5,11 C5.56700338,11 4,9.43299662 4,7.5 C4,5.56700338 5.56700338,4 7.5,4 C9.43299662,4 11,5.56700338 11,7.5 L11,11 L7.5,11 Z" fill="#000000" fill-rule="nonzero"></path>
																</g>
															</svg> </div>
														<div className="svg-classname">
															CMD.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setCmdSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setCmdCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={cmdSvg} onHide={setCmdSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >CMD.svg</h5>
																		<button type="button" className="close" onClick={()=>setCmdSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/CMD.svg"/&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setCmdSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={cmdCode} onHide={setCmdCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >CMD.svg</h5>
																		<button type="button" className="close" onClick={()=>setCmdCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;path d="M9,15 L7.5,15 C6.67157288,15 6,15.6715729 6,16.5 C6,17.3284271 6.67157288,18 7.5,18 C8.32842712,18 9,17.3284271 9,16.5 L9,15 Z M9,15 L9,9 L15,9 L15,15 L9,15 Z M15,16.5 C15,17.3284271 15.6715729,18 16.5,18 C17.3284271,18 18,17.3284271 18,16.5 C18,15.6715729 17.3284271,15 16.5,15 L15,15 L15,16.5 Z M16.5,9 C17.3284271,9 18,8.32842712 18,7.5 C18,6.67157288 17.3284271,6 16.5,6 C15.6715729,6 15,6.67157288 15,7.5 L15,9 L16.5,9 Z M9,7.5 C9,6.67157288 8.32842712,6 7.5,6 C6.67157288,6 6,6.67157288 6,7.5 C6,8.32842712 6.67157288,9 7.5,9 L9,9 L9,7.5 Z M11,13 L13,13 L13,11 L11,11 L11,13 Z M13,11 L13,7.5 C13,5.56700338 14.5670034,4 16.5,4 C18.4329966,4 20,5.56700338 20,7.5 C20,9.43299662 18.4329966,11 16.5,11 L13,11 Z M16.5,13 C18.4329966,13 20,14.5670034 20,16.5 C20,18.4329966 18.4329966,20 16.5,20 C14.5670034,20 13,18.4329966 13,16.5 L13,13 L16.5,13 Z M11,16.5 C11,18.4329966 9.43299662,20 7.5,20 C5.56700338,20 4,18.4329966 4,16.5 C4,14.5670034 5.56700338,13 7.5,13 L11,13 L11,16.5 Z M7.5,11 C5.56700338,11 4,9.43299662 4,7.5 C4,5.56700338 5.56700338,4 7.5,4 C9.43299662,4 11,5.56700338 11,7.5 L11,11 L7.5,11 Z" fill="#000000" fill-rule="nonzero"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setCmdCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className=" svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<path d="M17.2718029,8.68536757 C16.8932864,8.28319382 16.9124644,7.65031935 17.3146382,7.27180288 C17.7168119,6.89328641 18.3496864,6.91246442 18.7282029,7.31463817 L22.7282029,11.5646382 C23.0906029,11.9496882 23.0906029,12.5503176 22.7282029,12.9353676 L18.7282029,17.1853676 C18.3496864,17.5875413 17.7168119,17.6067193 17.3146382,17.2282029 C16.9124644,16.8496864 16.8932864,16.2168119 17.2718029,15.8146382 L20.6267538,12.2500029 L17.2718029,8.68536757 Z M6.72819712,8.6853647 L3.37324625,12.25 L6.72819712,15.8146353 C7.10671359,16.2168091 7.08753558,16.8496835 6.68536183,17.2282 C6.28318808,17.6067165 5.65031361,17.5875384 5.27179713,17.1853647 L1.27179713,12.9353647 C0.909397125,12.5503147 0.909397125,11.9496853 1.27179713,11.5646353 L5.27179713,7.3146353 C5.65031361,6.91246155 6.28318808,6.89328354 6.68536183,7.27180001 C7.08753558,7.65031648 7.10671359,8.28319095 6.72819712,8.6853647 Z" fill="#000000" fill-rule="nonzero"></path>
																	<rect fill="#000000" opacity="0.3" transform="translate(12.000000, 12.000000) rotate(-345.000000) translate(-12.000000, -12.000000) " x="11" y="4" width="2" height="16" rx="1"></rect>
																</g>
															</svg> </div>
														<div className="svg-classname">
															Code.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setCodeSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setCodeCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={codeSvg} onHide={setCodeSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Code.svg</h5>
																		<button type="button" className="close" onClick={()=>setCodeSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Code.svg"/&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setCodeSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={codeCode} onHide={setCodeCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Code.svg</h5>
																		<button type="button" className="close" onClick={()=>setCodeCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;path d="M17.2718029,8.68536757 C16.8932864,8.28319382 16.9124644,7.65031935 17.3146382,7.27180288 C17.7168119,6.89328641 18.3496864,6.91246442 18.7282029,7.31463817 L22.7282029,11.5646382 C23.0906029,11.9496882 23.0906029,12.5503176 22.7282029,12.9353676 L18.7282029,17.1853676 C18.3496864,17.5875413 17.7168119,17.6067193 17.3146382,17.2282029 C16.9124644,16.8496864 16.8932864,16.2168119 17.2718029,15.8146382 L20.6267538,12.2500029 L17.2718029,8.68536757 Z M6.72819712,8.6853647 L3.37324625,12.25 L6.72819712,15.8146353 C7.10671359,16.2168091 7.08753558,16.8496835 6.68536183,17.2282 C6.28318808,17.6067165 5.65031361,17.5875384 5.27179713,17.1853647 L1.27179713,12.9353647 C0.909397125,12.5503147 0.909397125,11.9496853 1.27179713,11.5646353 L5.27179713,7.3146353 C5.65031361,6.91246155 6.28318808,6.89328354 6.68536183,7.27180001 C7.08753558,7.65031648 7.10671359,8.28319095 6.72819712,8.6853647 Z" fill="#000000" fill-rule="nonzero"/&gt;
        &lt;rect fill="#000000" opacity="0.3" transform="translate(12.000000, 12.000000) rotate(-345.000000) translate(-12.000000, -12.000000) " x="11" y="4" width="2" height="16" rx="1"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setCodeCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className=" svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<path d="M20.5,11 L22.5,11 C23.3284271,11 24,11.6715729 24,12.5 C24,13.3284271 23.3284271,14 22.5,14 L20.5,14 C19.6715729,14 19,13.3284271 19,12.5 C19,11.6715729 19.6715729,11 20.5,11 Z M1.5,11 L3.5,11 C4.32842712,11 5,11.6715729 5,12.5 C5,13.3284271 4.32842712,14 3.5,14 L1.5,14 C0.671572875,14 1.01453063e-16,13.3284271 0,12.5 C-1.01453063e-16,11.6715729 0.671572875,11 1.5,11 Z" fill="#000000" opacity="0.3"></path>
																	<path d="M12,16 C13.6568542,16 15,14.6568542 15,13 C15,11.3431458 13.6568542,10 12,10 C10.3431458,10 9,11.3431458 9,13 C9,14.6568542 10.3431458,16 12,16 Z M12,18 C9.23857625,18 7,15.7614237 7,13 C7,10.2385763 9.23857625,8 12,8 C14.7614237,8 17,10.2385763 17,13 C17,15.7614237 14.7614237,18 12,18 Z" fill="#000000" fill-rule="nonzero"></path>
																</g>
															</svg> </div>
														<div className="svg-classname">
															Commit.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setCommitSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setCommitCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={commitSvg} onHide={setCommitSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Commit.svg</h5>
																		<button type="button" className="close" onClick={()=>setCommitSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Commit.svg"/&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setCommitSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={commitCode} onHide={setCommitCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Commit.svg</h5>
																		<button type="button" className="close" onClick={()=>setCommitCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;path d="M20.5,11 L22.5,11 C23.3284271,11 24,11.6715729 24,12.5 C24,13.3284271 23.3284271,14 22.5,14 L20.5,14 C19.6715729,14 19,13.3284271 19,12.5 C19,11.6715729 19.6715729,11 20.5,11 Z M1.5,11 L3.5,11 C4.32842712,11 5,11.6715729 5,12.5 C5,13.3284271 4.32842712,14 3.5,14 L1.5,14 C0.671572875,14 1.01453063e-16,13.3284271 0,12.5 C-1.01453063e-16,11.6715729 0.671572875,11 1.5,11 Z" fill="#000000" opacity="0.3"/&gt;
        &lt;path d="M12,16 C13.6568542,16 15,14.6568542 15,13 C15,11.3431458 13.6568542,10 12,10 C10.3431458,10 9,11.3431458 9,13 C9,14.6568542 10.3431458,16 12,16 Z M12,18 C9.23857625,18 7,15.7614237 7,13 C7,10.2385763 9.23857625,8 12,8 C14.7614237,8 17,10.2385763 17,13 C17,15.7614237 14.7614237,18 12,18 Z" fill="#000000" fill-rule="nonzero"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setCommitCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className=" svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<path d="M2.56066017,10.6819805 L4.68198052,8.56066017 C5.26776695,7.97487373 6.21751442,7.97487373 6.80330086,8.56066017 L8.9246212,10.6819805 C9.51040764,11.267767 9.51040764,12.2175144 8.9246212,12.8033009 L6.80330086,14.9246212 C6.21751442,15.5104076 5.26776695,15.5104076 4.68198052,14.9246212 L2.56066017,12.8033009 C1.97487373,12.2175144 1.97487373,11.267767 2.56066017,10.6819805 Z M14.5606602,10.6819805 L16.6819805,8.56066017 C17.267767,7.97487373 18.2175144,7.97487373 18.8033009,8.56066017 L20.9246212,10.6819805 C21.5104076,11.267767 21.5104076,12.2175144 20.9246212,12.8033009 L18.8033009,14.9246212 C18.2175144,15.5104076 17.267767,15.5104076 16.6819805,14.9246212 L14.5606602,12.8033009 C13.9748737,12.2175144 13.9748737,11.267767 14.5606602,10.6819805 Z" fill="#000000" opacity="0.3"></path>
																	<path d="M8.56066017,16.6819805 L10.6819805,14.5606602 C11.267767,13.9748737 12.2175144,13.9748737 12.8033009,14.5606602 L14.9246212,16.6819805 C15.5104076,17.267767 15.5104076,18.2175144 14.9246212,18.8033009 L12.8033009,20.9246212 C12.2175144,21.5104076 11.267767,21.5104076 10.6819805,20.9246212 L8.56066017,18.8033009 C7.97487373,18.2175144 7.97487373,17.267767 8.56066017,16.6819805 Z M8.56066017,4.68198052 L10.6819805,2.56066017 C11.267767,1.97487373 12.2175144,1.97487373 12.8033009,2.56066017 L14.9246212,4.68198052 C15.5104076,5.26776695 15.5104076,6.21751442 14.9246212,6.80330086 L12.8033009,8.9246212 C12.2175144,9.51040764 11.267767,9.51040764 10.6819805,8.9246212 L8.56066017,6.80330086 C7.97487373,6.21751442 7.97487373,5.26776695 8.56066017,4.68198052 Z" fill="#000000"></path>
																</g>
															</svg> </div>
														<div className="svg-classname">
															Compiling.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setCompilingSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setCompilingCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={compilingSvg} onHide={setCompilingSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Compiling.svg</h5>
																		<button type="button" className="close" onClick={()=>setCompilingSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Compiling.svg"/&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setCompilingSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={compilingCode} onHide={setCompilingCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Compiling.svg</h5>
																		<button type="button" className="close" onClick={()=>setCompilingCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;path d="M2.56066017,10.6819805 L4.68198052,8.56066017 C5.26776695,7.97487373 6.21751442,7.97487373 6.80330086,8.56066017 L8.9246212,10.6819805 C9.51040764,11.267767 9.51040764,12.2175144 8.9246212,12.8033009 L6.80330086,14.9246212 C6.21751442,15.5104076 5.26776695,15.5104076 4.68198052,14.9246212 L2.56066017,12.8033009 C1.97487373,12.2175144 1.97487373,11.267767 2.56066017,10.6819805 Z M14.5606602,10.6819805 L16.6819805,8.56066017 C17.267767,7.97487373 18.2175144,7.97487373 18.8033009,8.56066017 L20.9246212,10.6819805 C21.5104076,11.267767 21.5104076,12.2175144 20.9246212,12.8033009 L18.8033009,14.9246212 C18.2175144,15.5104076 17.267767,15.5104076 16.6819805,14.9246212 L14.5606602,12.8033009 C13.9748737,12.2175144 13.9748737,11.267767 14.5606602,10.6819805 Z" fill="#000000" opacity="0.3"/&gt;
        &lt;path d="M8.56066017,16.6819805 L10.6819805,14.5606602 C11.267767,13.9748737 12.2175144,13.9748737 12.8033009,14.5606602 L14.9246212,16.6819805 C15.5104076,17.267767 15.5104076,18.2175144 14.9246212,18.8033009 L12.8033009,20.9246212 C12.2175144,21.5104076 11.267767,21.5104076 10.6819805,20.9246212 L8.56066017,18.8033009 C7.97487373,18.2175144 7.97487373,17.267767 8.56066017,16.6819805 Z M8.56066017,4.68198052 L10.6819805,2.56066017 C11.267767,1.97487373 12.2175144,1.97487373 12.8033009,2.56066017 L14.9246212,4.68198052 C15.5104076,5.26776695 15.5104076,6.21751442 14.9246212,6.80330086 L12.8033009,8.9246212 C12.2175144,9.51040764 11.267767,9.51040764 10.6819805,8.9246212 L8.56066017,6.80330086 C7.97487373,6.21751442 7.97487373,5.26776695 8.56066017,4.68198052 Z" fill="#000000"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setCompilingCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<path d="M12,6.5 L3.64413575,13.7649112 C3.22168696,14.1206575 2.59083515,14.0665845 2.2350888,13.6441357 C1.87934245,13.221687 1.93341546,12.5908352 2.35586425,12.2350888 L11.0057493,4.44493319 C11.5881366,3.95450184 12.4455639,3.97817779 13,4.5 L21.6853647,12.2718 C22.0875384,12.6503165 22.1067165,13.2831909 21.7282,13.6853647 C21.3496835,14.0875384 20.7168091,14.1067165 20.3146353,13.7282 L12,6.5 Z" fill="#000000" fill-rule="nonzero"></path>
																</g>
															</svg> </div>
														<div className="svg-classname">
															Control.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setControlSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setControlCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={controlSvg} onHide={setControlSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Control.svg</h5>
																		<button type="button" className="close" onClick={()=>setControlSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Control.svg"/&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setControlSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={controlCode} onHide={setControlCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Control.svg</h5>
																		<button type="button" className="close" onClick={()=>setControlCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;path d="M12,6.5 L3.64413575,13.7649112 C3.22168696,14.1206575 2.59083515,14.0665845 2.2350888,13.6441357 C1.87934245,13.221687 1.93341546,12.5908352 2.35586425,12.2350888 L11.0057493,4.44493319 C11.5881366,3.95450184 12.4455639,3.97817779 13,4.5 L21.6853647,12.2718 C22.0875384,12.6503165 22.1067165,13.2831909 21.7282,13.6853647 C21.3496835,14.0875384 20.7168091,14.1067165 20.3146353,13.7282 L12,6.5 Z" fill="#000000" fill-rule="nonzero"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setControlCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
			</div>
			<div className="row">										
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"></circle>
																	<path d="M16.7689447,7.81768175 C17.1457787,7.41393107 17.7785676,7.39211077 18.1823183,7.76894473 C18.5860689,8.1457787 18.6078892,8.77856757 18.2310553,9.18231825 L11.2310553,16.6823183 C10.8654446,17.0740439 10.2560456,17.107974 9.84920863,16.7592566 L6.34920863,13.7592566 C5.92988278,13.3998345 5.88132125,12.7685345 6.2407434,12.3492086 C6.60016555,11.9298828 7.23146553,11.8813212 7.65079137,12.2407434 L10.4229928,14.616916 L16.7689447,7.81768175 Z" fill="#000000" fill-rule="nonzero"></path>
																</g>
															</svg> </div>
														<div className="svg-classname">
															Done-circle.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setDoneSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setDoneCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={doneSvg} onHide={setDoneSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Done-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setDoneSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Done-circle.svg"/&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setDoneSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={doneCode} onHide={setDoneCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Done-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setDoneCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"/&gt;
        &lt;path d="M16.7689447,7.81768175 C17.1457787,7.41393107 17.7785676,7.39211077 18.1823183,7.76894473 C18.5860689,8.1457787 18.6078892,8.77856757 18.2310553,9.18231825 L11.2310553,16.6823183 C10.8654446,17.0740439 10.2560456,17.107974 9.84920863,16.7592566 L6.34920863,13.7592566 C5.92988278,13.3998345 5.88132125,12.7685345 6.2407434,12.3492086 C6.60016555,11.9298828 7.23146553,11.8813212 7.65079137,12.2407434 L10.4229928,14.616916 L16.7689447,7.81768175 Z" fill="#000000" fill-rule="nonzero"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setDoneCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"></circle>
																	<path d="M12.0355339,10.6213203 L14.863961,7.79289322 C15.2544853,7.40236893 15.8876503,7.40236893 16.2781746,7.79289322 C16.6686989,8.18341751 16.6686989,8.81658249 16.2781746,9.20710678 L13.4497475,12.0355339 L16.2781746,14.863961 C16.6686989,15.2544853 16.6686989,15.8876503 16.2781746,16.2781746 C15.8876503,16.6686989 15.2544853,16.6686989 14.863961,16.2781746 L12.0355339,13.4497475 L9.20710678,16.2781746 C8.81658249,16.6686989 8.18341751,16.6686989 7.79289322,16.2781746 C7.40236893,15.8876503 7.40236893,15.2544853 7.79289322,14.863961 L10.6213203,12.0355339 L7.79289322,9.20710678 C7.40236893,8.81658249 7.40236893,8.18341751 7.79289322,7.79289322 C8.18341751,7.40236893 8.81658249,7.40236893 9.20710678,7.79289322 L12.0355339,10.6213203 Z" fill="#000000"></path>
																</g>
															</svg>  </div>
														<div className="svg-classname">
															Error-circle.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setErrorSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setErrorCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={errorSvg} onHide={setErrorSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Error-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setErrorSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Error-circle.svg"/&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setErrorSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={errorCode} onHide={setErrorCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Error-circle.svg	</h5>
																		<button type="button" className="close" onClick={()=>setErrorCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"/&gt;
        &lt;path d="M12.0355339,10.6213203 L14.863961,7.79289322 C15.2544853,7.40236893 15.8876503,7.40236893 16.2781746,7.79289322 C16.6686989,8.18341751 16.6686989,8.81658249 16.2781746,9.20710678 L13.4497475,12.0355339 L16.2781746,14.863961 C16.6686989,15.2544853 16.6686989,15.8876503 16.2781746,16.2781746 C15.8876503,16.6686989 15.2544853,16.6686989 14.863961,16.2781746 L12.0355339,13.4497475 L9.20710678,16.2781746 C8.81658249,16.6686989 8.18341751,16.6686989 7.79289322,16.2781746 C7.40236893,15.8876503 7.40236893,15.2544853 7.79289322,14.863961 L10.6213203,12.0355339 L7.79289322,9.20710678 C7.40236893,8.81658249 7.40236893,8.18341751 7.79289322,7.79289322 C8.18341751,7.40236893 8.81658249,7.40236893 9.20710678,7.79289322 L12.0355339,10.6213203 Z" fill="#000000"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setErrorCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<rect fill="#000000" opacity="0.3" x="11" y="8" width="2" height="9" rx="1"></rect>
																	<path d="M12,21 C13.1045695,21 14,20.1045695 14,19 C14,17.8954305 13.1045695,17 12,17 C10.8954305,17 10,17.8954305 10,19 C10,20.1045695 10.8954305,21 12,21 Z M12,23 C9.790861,23 8,21.209139 8,19 C8,16.790861 9.790861,15 12,15 C14.209139,15 16,16.790861 16,19 C16,21.209139 14.209139,23 12,23 Z" fill="#000000" fill-rule="nonzero"></path>
																	<path d="M12,7 C13.1045695,7 14,6.1045695 14,5 C14,3.8954305 13.1045695,3 12,3 C10.8954305,3 10,3.8954305 10,5 C10,6.1045695 10.8954305,7 12,7 Z M12,9 C9.790861,9 8,7.209139 8,5 C8,2.790861 9.790861,1 12,1 C14.209139,1 16,2.790861 16,5 C16,7.209139 14.209139,9 12,9 Z" fill="#000000" fill-rule="nonzero"></path>
																</g>
															</svg>  </div>
														<div className="svg-classname">
															Git#1.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setGitSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setGitCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={gitSvg} onHide={setGitSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Git#1.svg</h5>
																		<button type="button" className="close" onClick={()=>setGitSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Git#1.svg"/&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setGitSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={gitCode} onHide={setGitCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Git#1.svg</h5>
																		<button type="button" className="close" onClick={()=>setGitCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;rect fill="#000000" opacity="0.3" x="11" y="8" width="2" height="9" rx="1"/&gt;
        &lt;path d="M12,21 C13.1045695,21 14,20.1045695 14,19 C14,17.8954305 13.1045695,17 12,17 C10.8954305,17 10,17.8954305 10,19 C10,20.1045695 10.8954305,21 12,21 Z M12,23 C9.790861,23 8,21.209139 8,19 C8,16.790861 9.790861,15 12,15 C14.209139,15 16,16.790861 16,19 C16,21.209139 14.209139,23 12,23 Z" fill="#000000" fill-rule="nonzero"/&gt;
        &lt;path d="M12,7 C13.1045695,7 14,6.1045695 14,5 C14,3.8954305 13.1045695,3 12,3 C10.8954305,3 10,3.8954305 10,5 C10,6.1045695 10.8954305,7 12,7 Z M12,9 C9.790861,9 8,7.209139 8,5 C8,2.790861 9.790861,1 12,1 C14.209139,1 16,2.790861 16,5 C16,7.209139 14.209139,9 12,9 Z" fill="#000000" fill-rule="nonzero"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setGitCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<rect fill="#000000" opacity="0.3" x="5" y="8" width="2" height="8" rx="1"></rect>
																	<path d="M6,21 C7.1045695,21 8,20.1045695 8,19 C8,17.8954305 7.1045695,17 6,17 C4.8954305,17 4,17.8954305 4,19 C4,20.1045695 4.8954305,21 6,21 Z M6,23 C3.790861,23 2,21.209139 2,19 C2,16.790861 3.790861,15 6,15 C8.209139,15 10,16.790861 10,19 C10,21.209139 8.209139,23 6,23 Z" fill="#000000" fill-rule="nonzero"></path>
																	<rect fill="#000000" opacity="0.3" x="17" y="8" width="2" height="8" rx="1"></rect>
																	<path d="M18,21 C19.1045695,21 20,20.1045695 20,19 C20,17.8954305 19.1045695,17 18,17 C16.8954305,17 16,17.8954305 16,19 C16,20.1045695 16.8954305,21 18,21 Z M18,23 C15.790861,23 14,21.209139 14,19 C14,16.790861 15.790861,15 18,15 C20.209139,15 22,16.790861 22,19 C22,21.209139 20.209139,23 18,23 Z" fill="#000000" fill-rule="nonzero"></path>
																	<path d="M6,7 C7.1045695,7 8,6.1045695 8,5 C8,3.8954305 7.1045695,3 6,3 C4.8954305,3 4,3.8954305 4,5 C4,6.1045695 4.8954305,7 6,7 Z M6,9 C3.790861,9 2,7.209139 2,5 C2,2.790861 3.790861,1 6,1 C8.209139,1 10,2.790861 10,5 C10,7.209139 8.209139,9 6,9 Z" fill="#000000" fill-rule="nonzero"></path>
																	<path d="M18,7 C19.1045695,7 20,6.1045695 20,5 C20,3.8954305 19.1045695,3 18,3 C16.8954305,3 16,3.8954305 16,5 C16,6.1045695 16.8954305,7 18,7 Z M18,9 C15.790861,9 14,7.209139 14,5 C14,2.790861 15.790861,1 18,1 C20.209139,1 22,2.790861 22,5 C22,7.209139 20.209139,9 18,9 Z" fill="#000000" fill-rule="nonzero"></path>
																</g>
															</svg>  </div>
														<div className="svg-classname">
															Git#2.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setGit2Svg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setGit2Code(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={git2Svg} onHide={setGit2Svg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Git#2.svg</h5>
																		<button type="button" className="close" onClick={()=>setGit2Svg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Git#2.svg"/&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setGit2Svg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={git2Code} onHide={setGit2Code}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Git#2.svg</h5>
																		<button type="button" className="close" onClick={()=>setGit2Code(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;rect fill="#000000" opacity="0.3" x="11" y="8" width="2" height="9" rx="1"/&gt;
        &lt;path d="M12,21 C13.1045695,21 14,20.1045695 14,19 C14,17.8954305 13.1045695,17 12,17 C10.8954305,17 10,17.8954305 10,19 C10,20.1045695 10.8954305,21 12,21 Z M12,23 C9.790861,23 8,21.209139 8,19 C8,16.790861 9.790861,15 12,15 C14.209139,15 16,16.790861 16,19 C16,21.209139 14.209139,23 12,23 Z" fill="#000000" fill-rule="nonzero"/&gt;
        &lt;path d="M12,7 C13.1045695,7 14,6.1045695 14,5 C14,3.8954305 13.1045695,3 12,3 C10.8954305,3 10,3.8954305 10,5 C10,6.1045695 10.8954305,7 12,7 Z M12,9 C9.790861,9 8,7.209139 8,5 C8,2.790861 9.790861,1 12,1 C14.209139,1 16,2.790861 16,5 C16,7.209139 14.209139,9 12,9 Z" fill="#000000" fill-rule="nonzero"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setGit2Code(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<path d="M7,11 L15,11 C16.1045695,11 17,10.1045695 17,9 L17,8 L19,8 L19,9 C19,11.209139 17.209139,13 15,13 L7,13 L7,15 C7,15.5522847 6.55228475,16 6,16 C5.44771525,16 5,15.5522847 5,15 L5,9 C5,8.44771525 5.44771525,8 6,8 C6.55228475,8 7,8.44771525 7,9 L7,11 Z" fill="#000000" opacity="0.3"></path>
																	<path d="M6,21 C7.1045695,21 8,20.1045695 8,19 C8,17.8954305 7.1045695,17 6,17 C4.8954305,17 4,17.8954305 4,19 C4,20.1045695 4.8954305,21 6,21 Z M6,23 C3.790861,23 2,21.209139 2,19 C2,16.790861 3.790861,15 6,15 C8.209139,15 10,16.790861 10,19 C10,21.209139 8.209139,23 6,23 Z" fill="#000000" fill-rule="nonzero"></path>
																	<path d="M18,7 C19.1045695,7 20,6.1045695 20,5 C20,3.8954305 19.1045695,3 18,3 C16.8954305,3 16,3.8954305 16,5 C16,6.1045695 16.8954305,7 18,7 Z M18,9 C15.790861,9 14,7.209139 14,5 C14,2.790861 15.790861,1 18,1 C20.209139,1 22,2.790861 22,5 C22,7.209139 20.209139,9 18,9 Z" fill="#000000" fill-rule="nonzero"></path>
																	<path d="M6,7 C7.1045695,7 8,6.1045695 8,5 C8,3.8954305 7.1045695,3 6,3 C4.8954305,3 4,3.8954305 4,5 C4,6.1045695 4.8954305,7 6,7 Z M6,9 C3.790861,9 2,7.209139 2,5 C2,2.790861 3.790861,1 6,1 C8.209139,1 10,2.790861 10,5 C10,7.209139 8.209139,9 6,9 Z" fill="#000000" fill-rule="nonzero"></path>
																</g>
															</svg>  </div>
														<div className="svg-classname">
															Git#3.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setGit3Svg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setGit3Code(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={git3Svg} onHide={setGit3Svg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Git#3.svg</h5>
																		<button type="button" className="close" onClick={()=>setGit3Svg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Git#3.svg"/&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setGit3Svg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={git3Code} onHide={setGit3Code}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Git#3.svg</h5>
																		<button type="button" className="close" onClick={()=>setGit3Code(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;path d="M7,11 L15,11 C16.1045695,11 17,10.1045695 17,9 L17,8 L19,8 L19,9 C19,11.209139 17.209139,13 15,13 L7,13 L7,15 C7,15.5522847 6.55228475,16 6,16 C5.44771525,16 5,15.5522847 5,15 L5,9 C5,8.44771525 5.44771525,8 6,8 C6.55228475,8 7,8.44771525 7,9 L7,11 Z" fill="#000000" opacity="0.3"/&gt;
        &lt;path d="M6,21 C7.1045695,21 8,20.1045695 8,19 C8,17.8954305 7.1045695,17 6,17 C4.8954305,17 4,17.8954305 4,19 C4,20.1045695 4.8954305,21 6,21 Z M6,23 C3.790861,23 2,21.209139 2,19 C2,16.790861 3.790861,15 6,15 C8.209139,15 10,16.790861 10,19 C10,21.209139 8.209139,23 6,23 Z" fill="#000000" fill-rule="nonzero"/&gt;
        &lt;path d="M18,7 C19.1045695,7 20,6.1045695 20,5 C20,3.8954305 19.1045695,3 18,3 C16.8954305,3 16,3.8954305 16,5 C16,6.1045695 16.8954305,7 18,7 Z M18,9 C15.790861,9 14,7.209139 14,5 C14,2.790861 15.790861,1 18,1 C20.209139,1 22,2.790861 22,5 C22,7.209139 20.209139,9 18,9 Z" fill="#000000" fill-rule="nonzero"/&gt;
        &lt;path d="M6,7 C7.1045695,7 8,6.1045695 8,5 C8,3.8954305 7.1045695,3 6,3 C4.8954305,3 4,3.8954305 4,5 C4,6.1045695 4.8954305,7 6,7 Z M6,9 C3.790861,9 2,7.209139 2,5 C2,2.790861 3.790861,1 6,1 C8.209139,1 10,2.790861 10,5 C10,7.209139 8.209139,9 6,9 Z" fill="#000000" fill-rule="nonzero"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setGit3Code(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<path d="M6,7 C7.1045695,7 8,6.1045695 8,5 C8,3.8954305 7.1045695,3 6,3 C4.8954305,3 4,3.8954305 4,5 C4,6.1045695 4.8954305,7 6,7 Z M6,9 C3.790861,9 2,7.209139 2,5 C2,2.790861 3.790861,1 6,1 C8.209139,1 10,2.790861 10,5 C10,7.209139 8.209139,9 6,9 Z" fill="#000000" fill-rule="nonzero"></path>
																	<path d="M7,11.4648712 L7,17 C7,18.1045695 7.8954305,19 9,19 L15,19 L15,21 L9,21 C6.790861,21 5,19.209139 5,17 L5,8 L5,7 L7,7 L7,8 C7,9.1045695 7.8954305,10 9,10 L15,10 L15,12 L9,12 C8.27142571,12 7.58834673,11.8052114 7,11.4648712 Z" fill="#000000" fill-rule="nonzero" opacity="0.3"></path>
																	<path d="M18,22 C19.1045695,22 20,21.1045695 20,20 C20,18.8954305 19.1045695,18 18,18 C16.8954305,18 16,18.8954305 16,20 C16,21.1045695 16.8954305,22 18,22 Z M18,24 C15.790861,24 14,22.209139 14,20 C14,17.790861 15.790861,16 18,16 C20.209139,16 22,17.790861 22,20 C22,22.209139 20.209139,24 18,24 Z" fill="#000000" fill-rule="nonzero"></path>
																	<path d="M18,13 C19.1045695,13 20,12.1045695 20,11 C20,9.8954305 19.1045695,9 18,9 C16.8954305,9 16,9.8954305 16,11 C16,12.1045695 16.8954305,13 18,13 Z M18,15 C15.790861,15 14,13.209139 14,11 C14,8.790861 15.790861,7 18,7 C20.209139,7 22,8.790861 22,11 C22,13.209139 20.209139,15 18,15 Z" fill="#000000" fill-rule="nonzero"></path>
																</g>
															</svg>  </div>
														<div className="svg-classname">
															Git#4.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setGit4Svg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setGit4Code(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={git4Svg} onHide={setGit4Svg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Git#4.svg</h5>
																		<button type="button" className="close" onClick={()=>setGit4Svg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Git#4.svg"/&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setGit4Svg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={git4Code} onHide={setGit4Code}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Git#4.svg</h5>
																		<button type="button" className="close" onClick={()=>setGit4Code(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;path d="M6,7 C7.1045695,7 8,6.1045695 8,5 C8,3.8954305 7.1045695,3 6,3 C4.8954305,3 4,3.8954305 4,5 C4,6.1045695 4.8954305,7 6,7 Z M6,9 C3.790861,9 2,7.209139 2,5 C2,2.790861 3.790861,1 6,1 C8.209139,1 10,2.790861 10,5 C10,7.209139 8.209139,9 6,9 Z" fill="#000000" fill-rule="nonzero"/&gt;
        &lt;path d="M7,11.4648712 L7,17 C7,18.1045695 7.8954305,19 9,19 L15,19 L15,21 L9,21 C6.790861,21 5,19.209139 5,17 L5,8 L5,7 L7,7 L7,8 C7,9.1045695 7.8954305,10 9,10 L15,10 L15,12 L9,12 C8.27142571,12 7.58834673,11.8052114 7,11.4648712 Z" fill="#000000" fill-rule="nonzero" opacity="0.3"/&gt;
        &lt;path d="M18,22 C19.1045695,22 20,21.1045695 20,20 C20,18.8954305 19.1045695,18 18,18 C16.8954305,18 16,18.8954305 16,20 C16,21.1045695 16.8954305,22 18,22 Z M18,24 C15.790861,24 14,22.209139 14,20 C14,17.790861 15.790861,16 18,16 C20.209139,16 22,17.790861 22,20 C22,22.209139 20.209139,24 18,24 Z" fill="#000000" fill-rule="nonzero"/&gt;
        &lt;path d="M18,13 C19.1045695,13 20,12.1045695 20,11 C20,9.8954305 19.1045695,9 18,9 C16.8954305,9 16,9.8954305 16,11 C16,12.1045695 16.8954305,13 18,13 Z M18,15 C15.790861,15 14,13.209139 14,11 C14,8.790861 15.790861,7 18,7 C20.209139,7 22,8.790861 22,11 C22,13.209139 20.209139,15 18,15 Z" fill="#000000" fill-rule="nonzero"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setGit4Code(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
			</div>	
			<div className="row">
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<path d="M16.5428932,17.4571068 L11,11.9142136 L11,4 C11,3.44771525 11.4477153,3 12,3 C12.5522847,3 13,3.44771525 13,4 L13,11.0857864 L17.9571068,16.0428932 L20.1464466,13.8535534 C20.3417088,13.6582912 20.6582912,13.6582912 20.8535534,13.8535534 C20.9473216,13.9473216 21,14.0744985 21,14.2071068 L21,19.5 C21,19.7761424 20.7761424,20 20.5,20 L15.2071068,20 C14.9309644,20 14.7071068,19.7761424 14.7071068,19.5 C14.7071068,19.3673918 14.7597852,19.2402148 14.8535534,19.1464466 L16.5428932,17.4571068 Z" fill="#000000" fill-rule="nonzero"></path>
																	<path d="M7.24478854,17.1447885 L9.2464466,19.1464466 C9.34021479,19.2402148 9.39289321,19.3673918 9.39289321,19.5 C9.39289321,19.7761424 9.16903559,20 8.89289321,20 L3.52893218,20 C3.25278981,20 3.02893218,19.7761424 3.02893218,19.5 L3.02893218,14.136039 C3.02893218,14.0034307 3.0816106,13.8762538 3.17537879,13.7824856 C3.37064094,13.5872234 3.68722343,13.5872234 3.88248557,13.7824856 L5.82567301,15.725673 L8.85405776,13.1631936 L10.1459422,14.6899662 L7.24478854,17.1447885 Z" fill="#000000" fill-rule="nonzero" opacity="0.3"></path>
																</g>
															</svg>  </div>
														<div className="svg-classname">
															Github.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setGithubSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setGithubCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={githubSvg} onHide={setGithubSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Github.svg</h5>
																		<button type="button" className="close" onClick={()=>setGithubSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Github.svg"/&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setGithubSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={githubCode} onHide={setGithubCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Github.svg</h5>
																		<button type="button" className="close" onClick={()=>setGithubCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;path d="M6,7 C7.1045695,7 8,6.1045695 8,5 C8,3.8954305 7.1045695,3 6,3 C4.8954305,3 4,3.8954305 4,5 C4,6.1045695 4.8954305,7 6,7 Z M6,9 C3.790861,9 2,7.209139 2,5 C2,2.790861 3.790861,1 6,1 C8.209139,1 10,2.790861 10,5 C10,7.209139 8.209139,9 6,9 Z" fill="#000000" fill-rule="nonzero"/&gt;
        &lt;path d="M7,11.4648712 L7,17 C7,18.1045695 7.8954305,19 9,19 L15,19 L15,21 L9,21 C6.790861,21 5,19.209139 5,17 L5,8 L5,7 L7,7 L7,8 C7,9.1045695 7.8954305,10 9,10 L15,10 L15,12 L9,12 C8.27142571,12 7.58834673,11.8052114 7,11.4648712 Z" fill="#000000" fill-rule="nonzero" opacity="0.3"/&gt;
        &lt;path d="M18,22 C19.1045695,22 20,21.1045695 20,20 C20,18.8954305 19.1045695,18 18,18 C16.8954305,18 16,18.8954305 16,20 C16,21.1045695 16.8954305,22 18,22 Z M18,24 C15.790861,24 14,22.209139 14,20 C14,17.790861 15.790861,16 18,16 C20.209139,16 22,17.790861 22,20 C22,22.209139 20.209139,24 18,24 Z" fill="#000000" fill-rule="nonzero"/&gt;
        &lt;path d="M18,13 C19.1045695,13 20,12.1045695 20,11 C20,9.8954305 19.1045695,9 18,9 C16.8954305,9 16,9.8954305 16,11 C16,12.1045695 16.8954305,13 18,13 Z M18,15 C15.790861,15 14,13.209139 14,11 C14,8.790861 15.790861,7 18,7 C20.209139,7 22,8.790861 22,11 C22,13.209139 20.209139,15 18,15 Z" fill="#000000" fill-rule="nonzero"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setGithubCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"></circle>
																	<rect fill="#000000" x="11" y="10" width="2" height="7" rx="1"></rect>
																	<rect fill="#000000" x="11" y="7" width="2" height="2" rx="1"></rect>
																</g>
															</svg>  </div>
														<div className="svg-classname">
															Info-circle.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setInfoSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setInfoCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={infoSvg} onHide={setInfoSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Info-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setInfoSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Info-circle.svg"/&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setInfoSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={infoCode} onHide={setInfoCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Info-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setInfoCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"/&gt;
        &lt;rect fill="#000000" x="11" y="10" width="2" height="7" rx="1"/&gt;
        &lt;rect fill="#000000" x="11" y="7" width="2" height="2" rx="1"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setInfoCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"></circle>
																	<path d="M6.96323356,15.1775211 C6.62849853,15.5122561 6.08578582,15.5122561 5.75105079,15.1775211 C5.41631576,14.842786 5.41631576,14.3000733 5.75105079,13.9653383 L10.8939067,8.82248234 C11.2184029,8.49798619 11.7409054,8.4866328 12.0791905,8.79672747 L17.2220465,13.5110121 C17.5710056,13.8308912 17.5945795,14.3730917 17.2747004,14.7220508 C16.9548212,15.0710098 16.4126207,15.0945838 16.0636617,14.7747046 L11.5257773,10.6149773 L6.96323356,15.1775211 Z" fill="#000000" fill-rule="nonzero" transform="translate(11.500001, 12.000001) scale(-1, 1) rotate(-270.000000) translate(-11.500001, -12.000001) "></path>
																</g>
															</svg>  </div>
														<div className="svg-classname">
															Left-circle.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setLeftSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setLeftCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={leftSvg} onHide={setLeftSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Left-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setLeftSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Left-circle.svg"/&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setLeftSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={leftCode} onHide={setLeftCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Left-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setLeftCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"/&gt;
        &lt;path d="M6.96323356,15.1775211 C6.62849853,15.5122561 6.08578582,15.5122561 5.75105079,15.1775211 C5.41631576,14.842786 5.41631576,14.3000733 5.75105079,13.9653383 L10.8939067,8.82248234 C11.2184029,8.49798619 11.7409054,8.4866328 12.0791905,8.79672747 L17.2220465,13.5110121 C17.5710056,13.8308912 17.5945795,14.3730917 17.2747004,14.7220508 C16.9548212,15.0710098 16.4126207,15.0945838 16.0636617,14.7747046 L11.5257773,10.6149773 L6.96323356,15.1775211 Z" fill="#000000" fill-rule="nonzero" transform="translate(11.500001, 12.000001) scale(-1, 1) rotate(-270.000000) translate(-11.500001, -12.000001) "/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setLeftCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<g>
																		<polygon points="0 0 24 0 24 24 0 24"></polygon>
																	</g>
																	<path d="M12,4 L12,6 C8.6862915,6 6,8.6862915 6,12 C6,15.3137085 8.6862915,18 12,18 C15.3137085,18 18,15.3137085 18,12 C18,10.9603196 17.7360885,9.96126435 17.2402578,9.07513926 L18.9856052,8.09853149 C19.6473536,9.28117708 20,10.6161442 20,12 C20,16.418278 16.418278,20 12,20 C7.581722,20 4,16.418278 4,12 C4,7.581722 7.581722,4 12,4 Z" fill="#000000" fill-rule="nonzero" opacity="0.3" transform="translate(12.000000, 12.000000) scale(-1, 1) translate(-12.000000, -12.000000) "></path>
																</g>
															</svg>  </div>
														<div className="svg-classname">
															Loading.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setLoadingSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setLoadingCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={loadingSvg} onHide={setLoadingSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Loading.svg</h5>
																		<button type="button" className="close" onClick={()=>setLoadingSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Loading.svg"/&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setLoadingSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={loadingCode} onHide={setLoadingCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Loading.svg</h5>
																		<button type="button" className="close" onClick={()=>setLoadingCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"/&gt;
        &lt;path d="M6.96323356,15.1775211 C6.62849853,15.5122561 6.08578582,15.5122561 5.75105079,15.1775211 C5.41631576,14.842786 5.41631576,14.3000733 5.75105079,13.9653383 L10.8939067,8.82248234 C11.2184029,8.49798619 11.7409054,8.4866328 12.0791905,8.79672747 L17.2220465,13.5110121 C17.5710056,13.8308912 17.5945795,14.3730917 17.2747004,14.7220508 C16.9548212,15.0710098 16.4126207,15.0945838 16.0636617,14.7747046 L11.5257773,10.6149773 L6.96323356,15.1775211 Z" fill="#000000" fill-rule="nonzero" transform="translate(11.500001, 12.000001) scale(-1, 1) rotate(-270.000000) translate(-11.500001, -12.000001) "/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setLoadingCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"></circle>
																	<path d="M14.5,11 C15.0522847,11 15.5,11.4477153 15.5,12 L15.5,15 C15.5,15.5522847 15.0522847,16 14.5,16 L9.5,16 C8.94771525,16 8.5,15.5522847 8.5,15 L8.5,12 C8.5,11.4477153 8.94771525,11 9.5,11 L9.5,10.5 C9.5,9.11928813 10.6192881,8 12,8 C13.3807119,8 14.5,9.11928813 14.5,10.5 L14.5,11 Z M12,9 C11.1715729,9 10.5,9.67157288 10.5,10.5 L10.5,11 L13.5,11 L13.5,10.5 C13.5,9.67157288 12.8284271,9 12,9 Z" fill="#000000"></path>
																</g>
															</svg>   </div>
														<div className="svg-classname">
															Lock-circle.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setLockSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setLockCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={lockSvg} onHide={setLockSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Lock-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setLockSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Lock-circle.svg&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setLockSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={lockCode} onHide={setLockCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Lock-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setLockCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"/&gt;
        &lt;path d="M14.5,11 C15.0522847,11 15.5,11.4477153 15.5,12 L15.5,15 C15.5,15.5522847 15.0522847,16 14.5,16 L9.5,16 C8.94771525,16 8.5,15.5522847 8.5,15 L8.5,12 C8.5,11.4477153 8.94771525,11 9.5,11 L9.5,10.5 C9.5,9.11928813 10.6192881,8 12,8 C13.3807119,8 14.5,9.11928813 14.5,10.5 L14.5,11 Z M12,9 C11.1715729,9 10.5,9.67157288 10.5,10.5 L10.5,11 L13.5,11 L13.5,10.5 C13.5,9.67157288 12.8284271,9 12,9 Z" fill="#000000"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setLockCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<path d="M7.38979581,2.8349582 C8.65216735,2.29743306 10.0413491,2 11.5,2 C17.2989899,2 22,6.70101013 22,12.5 C22,18.2989899 17.2989899,23 11.5,23 C5.70101013,23 1,18.2989899 1,12.5 C1,11.5151324 1.13559454,10.5619345 1.38913364,9.65805651 L3.31481075,10.1982117 C3.10672013,10.940064 3,11.7119264 3,12.5 C3,17.1944204 6.80557963,21 11.5,21 C16.1944204,21 20,17.1944204 20,12.5 C20,7.80557963 16.1944204,4 11.5,4 C10.54876,4 9.62236069,4.15592757 8.74872191,4.45446326 L9.93948308,5.87355717 C10.0088058,5.95617272 10.0495583,6.05898805 10.05566,6.16666224 C10.0712834,6.4423623 9.86044965,6.67852665 9.5847496,6.69415008 L4.71777931,6.96995273 C4.66931162,6.97269931 4.62070229,6.96837279 4.57348157,6.95710938 C4.30487471,6.89303938 4.13906482,6.62335149 4.20313482,6.35474463 L5.33163823,1.62361064 C5.35654118,1.51920756 5.41437908,1.4255891 5.49660017,1.35659741 C5.7081375,1.17909652 6.0235153,1.2066885 6.2010162,1.41822583 L7.38979581,2.8349582 Z" fill="#000000" opacity="0.3"></path>
																	<path d="M14.5,11 C15.0522847,11 15.5,11.4477153 15.5,12 L15.5,15 C15.5,15.5522847 15.0522847,16 14.5,16 L9.5,16 C8.94771525,16 8.5,15.5522847 8.5,15 L8.5,12 C8.5,11.4477153 8.94771525,11 9.5,11 L9.5,10.5 C9.5,9.11928813 10.6192881,8 12,8 C13.3807119,8 14.5,9.11928813 14.5,10.5 L14.5,11 Z M12,9 C11.1715729,9 10.5,9.67157288 10.5,10.5 L10.5,11 L13.5,11 L13.5,10.5 C13.5,9.67157288 12.8284271,9 12,9 Z" fill="#000000"></path>
																</g>
															</svg>   </div>
														<div className="svg-classname">
															Lock-overturning.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setLockOverSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setLockOverCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={lockOverSvg} onHide={setLockOverSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Lock-overturning.svg</h5>
																		<button type="button" className="close" onClick={()=>setLockOverSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Lock-overturning.svg&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setLockOverSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={lockOverCode} onHide={setLockOverCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title" >Lock-overturning.svg</h5>
																		<button type="button" className="close" onClick={()=>setLockOverCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"/&gt;
        &lt;path d="M14.5,11 C15.0522847,11 15.5,11.4477153 15.5,12 L15.5,15 C15.5,15.5522847 15.0522847,16 14.5,16 L9.5,16 C8.94771525,16 8.5,15.5522847 8.5,15 L8.5,12 C8.5,11.4477153 8.94771525,11 9.5,11 L9.5,10.5 C9.5,9.11928813 10.6192881,8 12,8 C13.3807119,8 14.5,9.11928813 14.5,10.5 L14.5,11 Z M12,9 C11.1715729,9 10.5,9.67157288 10.5,10.5 L10.5,11 L13.5,11 L13.5,10.5 C13.5,9.67157288 12.8284271,9 12,9 Z" fill="#000000"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setLockOverCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
			</div>	
			<div className="row">
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"></circle>
																	<rect fill="#000000" x="6" y="11" width="12" height="2" rx="1"></rect>
																</g>
															</svg>  </div>
														<div className="svg-classname">
															Minus.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setMinusSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setMinusCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={minusSvg} onHide={setMinusSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Minus.svg</h5>
																		<button type="button" className="close" onClick={()=>setMinusSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Minus.svg&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setMinusSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={minusCode} onHide={setMinusCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Minus.svg</h5>
																		<button type="button" className="close" onClick={()=>setMinusCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"/&gt;
        &lt;rect fill="#000000" x="6" y="11" width="12" height="2" rx="1"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setMinusCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<rect fill="#000000" opacity="0.3" x="12" y="7" width="10" height="2" rx="1"></rect>
																	<path d="M2,9 C1.44771525,9 1,8.55228475 1,8 C1,7.44771525 1.44771525,7 2,7 L7.35012691,7 C8.14050434,7 8.85674733,7.46546704 9.17775001,8.18772307 L12.6498731,16 L22,16 C22.5522847,16 23,16.4477153 23,17 C23,17.5522847 22.5522847,18 22,18 L12.6498731,18 C11.8594957,18 11.1432527,17.534533 10.82225,16.8122769 L7.35012691,9 L2,9 Z" fill="#000000" fill-rule="nonzero"></path>
																</g>
															</svg>  </div>
														<div className="svg-classname">
															Option.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setOptionSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setOptionCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={optionSvg} onHide={setOptionSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Option.svg</h5>
																		<button type="button" className="close" onClick={()=>setOptionSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Option.svg&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setOptionSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={optionCode} onHide={setOptionCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Option.svg</h5>
																		<button type="button" className="close" onClick={()=>setOptionCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;rect fill="#000000" opacity="0.3" x="12" y="7" width="10" height="2" rx="1"/&gt;
        &lt;path d="M2,9 C1.44771525,9 1,8.55228475 1,8 C1,7.44771525 1.44771525,7 2,7 L7.35012691,7 C8.14050434,7 8.85674733,7.46546704 9.17775001,8.18772307 L12.6498731,16 L22,16 C22.5522847,16 23,16.4477153 23,17 C23,17.5522847 22.5522847,18 22,18 L12.6498731,18 C11.8594957,18 11.1432527,17.534533 10.82225,16.8122769 L7.35012691,9 L2,9 Z" fill="#000000" fill-rule="nonzero"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setOptionCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"></circle>
																	<path d="M11,11 L11,7 C11,6.44771525 11.4477153,6 12,6 C12.5522847,6 13,6.44771525 13,7 L13,11 L17,11 C17.5522847,11 18,11.4477153 18,12 C18,12.5522847 17.5522847,13 17,13 L13,13 L13,17 C13,17.5522847 12.5522847,18 12,18 C11.4477153,18 11,17.5522847 11,17 L11,13 L7,13 C6.44771525,13 6,12.5522847 6,12 C6,11.4477153 6.44771525,11 7,11 L11,11 Z" fill="#000000"></path>
																</g>
															</svg> 	</div>	
															<div className="svg-classname">
															Plus.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setPlusSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setPlusCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={plusSvg} onHide={setPlusSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Plus.svg</h5>
																		<button type="button" className="close" onClick={()=>setPlusSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Plus.svg&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setPlusSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={plusCode} onHide={setPlusCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Plus.svg</h5>
																		<button type="button" className="close" onClick={()=>setPlusCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"/&gt;
        &lt;path d="M11,11 L11,7 C11,6.44771525 11.4477153,6 12,6 C12.5522847,6 13,6.44771525 13,7 L13,11 L17,11 C17.5522847,11 18,11.4477153 18,12 C18,12.5522847 17.5522847,13 17,13 L13,13 L13,17 C13,17.5522847 12.5522847,18 12,18 C11.4477153,18 11,17.5522847 11,17 L11,13 L7,13 C6.44771525,13 6,12.5522847 6,12 C6,11.4477153 6.44771525,11 7,11 L11,11 Z" fill="#000000"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setPlusCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<path d="M19,11 L20,11 C21.6568542,11 23,12.3431458 23,14 C23,15.6568542 21.6568542,17 20,17 L19,17 L19,20 C19,21.1045695 18.1045695,22 17,22 L5,22 C3.8954305,22 3,21.1045695 3,20 L3,17 L5,17 C6.65685425,17 8,15.6568542 8,14 C8,12.3431458 6.65685425,11 5,11 L3,11 L3,8 C3,6.8954305 3.8954305,6 5,6 L8,6 L8,5 C8,3.34314575 9.34314575,2 11,2 C12.6568542,2 14,3.34314575 14,5 L14,6 L17,6 C18.1045695,6 19,6.8954305 19,8 L19,11 Z" fill="#000000" opacity="0.3"></path>
																</g>
															</svg>	</div>	
															<div className="svg-classname">
															Puzzle.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setPuzzleSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setPuzzleCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={puzzleSvg} onHide={setPuzzleSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Puzzle.svg</h5>
																		<button type="button" className="close" onClick={()=>setPuzzleSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Puzzle.svg&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setPuzzleSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={puzzleCode} onHide={setPuzzleCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Puzzle.svg</h5>
																		<button type="button" className="close" onClick={()=>setPuzzleCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"/&gt;
        &lt;path d="M11,11 L11,7 C11,6.44771525 11.4477153,6 12,6 C12.5522847,6 13,6.44771525 13,7 L13,11 L17,11 C17.5522847,11 18,11.4477153 18,12 C18,12.5522847 17.5522847,13 17,13 L13,13 L13,17 C13,17.5522847 12.5522847,18 12,18 C11.4477153,18 11,17.5522847 11,17 L11,13 L7,13 C6.44771525,13 6,12.5522847 6,12 C6,11.4477153 6.44771525,11 7,11 L11,11 Z" fill="#000000"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setPuzzleCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"></circle>
																	<path d="M12,16 C12.5522847,16 13,16.4477153 13,17 C13,17.5522847 12.5522847,18 12,18 C11.4477153,18 11,17.5522847 11,17 C11,16.4477153 11.4477153,16 12,16 Z M10.591,14.868 L10.591,13.209 L11.851,13.209 C13.447,13.209 14.602,11.991 14.602,10.395 C14.602,8.799 13.447,7.581 11.851,7.581 C10.234,7.581 9.121,8.799 9.121,10.395 L7.336,10.395 C7.336,7.875 9.31,5.922 11.851,5.922 C14.392,5.922 16.387,7.875 16.387,10.395 C16.387,12.915 14.392,14.868 11.851,14.868 L10.591,14.868 Z" fill="#000000"></path>
																</g>
															</svg>	</div>	
															<div className="svg-classname">
															Question-circle.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setQuestionSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setQuestionCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={questionSvg} onHide={setQuestionSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Question-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setQuestionSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Question-circle.svg&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setQuestionSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={questionCode} onHide={setQuestionCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Question-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setQuestionCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"/&gt;
        &lt;path d="M12,16 C12.5522847,16 13,16.4477153 13,17 C13,17.5522847 12.5522847,18 12,18 C11.4477153,18 11,17.5522847 11,17 C11,16.4477153 11.4477153,16 12,16 Z M10.591,14.868 L10.591,13.209 L11.851,13.209 C13.447,13.209 14.602,11.991 14.602,10.395 C14.602,8.799 13.447,7.581 11.851,7.581 C10.234,7.581 9.121,8.799 9.121,10.395 L7.336,10.395 C7.336,7.875 9.31,5.922 11.851,5.922 C14.392,5.922 16.387,7.875 16.387,10.395 C16.387,12.915 14.392,14.868 11.851,14.868 L10.591,14.868 Z" fill="#000000"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setQuestionCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>	
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"></circle>
																	<path d="M7.96323356,15.1775211 C7.62849853,15.5122561 7.08578582,15.5122561 6.75105079,15.1775211 C6.41631576,14.842786 6.41631576,14.3000733 6.75105079,13.9653383 L11.8939067,8.82248234 C12.2184029,8.49798619 12.7409054,8.4866328 13.0791905,8.79672747 L18.2220465,13.5110121 C18.5710056,13.8308912 18.5945795,14.3730917 18.2747004,14.7220508 C17.9548212,15.0710098 17.4126207,15.0945838 17.0636617,14.7747046 L12.5257773,10.6149773 L7.96323356,15.1775211 Z" fill="#000000" fill-rule="nonzero" transform="translate(12.500001, 12.000001) rotate(-270.000000) translate(-12.500001, -12.000001) "></path>
																</g>
															</svg>	</div>	
															<div className="svg-classname">
															Right-circle.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setRightSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setRightCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={rightSvg} onHide={setRightSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Right-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setRightSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Right-circle.svg&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setRightSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={rightCode} onHide={setRightCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Right-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setRightCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"/&gt;
        &lt;path d="M7.96323356,15.1775211 C7.62849853,15.5122561 7.08578582,15.5122561 6.75105079,15.1775211 C6.41631576,14.842786 6.41631576,14.3000733 6.75105079,13.9653383 L11.8939067,8.82248234 C12.2184029,8.49798619 12.7409054,8.4866328 13.0791905,8.79672747 L18.2220465,13.5110121 C18.5710056,13.8308912 18.5945795,14.3730917 18.2747004,14.7220508 C17.9548212,15.0710098 17.4126207,15.0945838 17.0636617,14.7747046 L12.5257773,10.6149773 L7.96323356,15.1775211 Z" fill="#000000" fill-rule="nonzero" transform="translate(12.500001, 12.000001) rotate(-270.000000) translate(-12.500001, -12.000001) "/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setRightCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
			</div>									
			<div className="row">									
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<path d="M18.6225,9.75 L18.75,9.75 C19.9926407,9.75 21,10.7573593 21,12 C21,13.2426407 19.9926407,14.25 18.75,14.25 L18.6854912,14.249994 C18.4911876,14.250769 18.3158978,14.366855 18.2393549,14.5454486 C18.1556809,14.7351461 18.1942911,14.948087 18.3278301,15.0846699 L18.372535,15.129375 C18.7950334,15.5514036 19.03243,16.1240792 19.03243,16.72125 C19.03243,17.3184208 18.7950334,17.8910964 18.373125,18.312535 C17.9510964,18.7350334 17.3784208,18.97243 16.78125,18.97243 C16.1840792,18.97243 15.6114036,18.7350334 15.1896699,18.3128301 L15.1505513,18.2736469 C15.008087,18.1342911 14.7951461,18.0956809 14.6054486,18.1793549 C14.426855,18.2558978 14.310769,18.4311876 14.31,18.6225 L14.31,18.75 C14.31,19.9926407 13.3026407,21 12.06,21 C10.8173593,21 9.81,19.9926407 9.81,18.75 C9.80552409,18.4999185 9.67898539,18.3229986 9.44717599,18.2361469 C9.26485393,18.1556809 9.05191298,18.1942911 8.91533009,18.3278301 L8.870625,18.372535 C8.44859642,18.7950334 7.87592081,19.03243 7.27875,19.03243 C6.68157919,19.03243 6.10890358,18.7950334 5.68746499,18.373125 C5.26496665,17.9510964 5.02757002,17.3784208 5.02757002,16.78125 C5.02757002,16.1840792 5.26496665,15.6114036 5.68716991,15.1896699 L5.72635306,15.1505513 C5.86570889,15.008087 5.90431906,14.7951461 5.82064513,14.6054486 C5.74410223,14.426855 5.56881236,14.310769 5.3775,14.31 L5.25,14.31 C4.00735931,14.31 3,13.3026407 3,12.06 C3,10.8173593 4.00735931,9.81 5.25,9.81 C5.50008154,9.80552409 5.67700139,9.67898539 5.76385306,9.44717599 C5.84431906,9.26485393 5.80570889,9.05191298 5.67216991,8.91533009 L5.62746499,8.870625 C5.20496665,8.44859642 4.96757002,7.87592081 4.96757002,7.27875 C4.96757002,6.68157919 5.20496665,6.10890358 5.626875,5.68746499 C6.04890358,5.26496665 6.62157919,5.02757002 7.21875,5.02757002 C7.81592081,5.02757002 8.38859642,5.26496665 8.81033009,5.68716991 L8.84944872,5.72635306 C8.99191298,5.86570889 9.20485393,5.90431906 9.38717599,5.82385306 L9.49484664,5.80114977 C9.65041313,5.71688974 9.7492905,5.55401473 9.75,5.3775 L9.75,5.25 C9.75,4.00735931 10.7573593,3 12,3 C13.2426407,3 14.25,4.00735931 14.25,5.25 L14.249994,5.31450877 C14.250769,5.50881236 14.366855,5.68410223 14.552824,5.76385306 C14.7351461,5.84431906 14.948087,5.80570889 15.0846699,5.67216991 L15.129375,5.62746499 C15.5514036,5.20496665 16.1240792,4.96757002 16.72125,4.96757002 C17.3184208,4.96757002 17.8910964,5.20496665 18.312535,5.626875 C18.7350334,6.04890358 18.97243,6.62157919 18.97243,7.21875 C18.97243,7.81592081 18.7350334,8.38859642 18.3128301,8.81033009 L18.2736469,8.84944872 C18.1342911,8.99191298 18.0956809,9.20485393 18.1761469,9.38717599 L18.1988502,9.49484664 C18.2831103,9.65041313 18.4459853,9.7492905 18.6225,9.75 Z" fill="#000000" fill-rule="nonzero" opacity="0.3"></path>
																	<path d="M12,15 C13.6568542,15 15,13.6568542 15,12 C15,10.3431458 13.6568542,9 12,9 C10.3431458,9 9,10.3431458 9,12 C9,13.6568542 10.3431458,15 12,15 Z" fill="#000000"></path>
																</g>
															</svg> 	</div>	
															<div className="svg-classname">
															Settings#4.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setSettingsSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setSettingsCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={settingsSvg} onHide={setSettingsSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Settings#4.svg</h5>
																		<button type="button" className="close" onClick={()=>setSettingsSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Settings#4.svg&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setSettingsSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={settingsCode} onHide={setSettingsCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Settings#4.svg</h5>
																		<button type="button" className="close" onClick={()=>setSettingsCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;path d="M18.6225,9.75 L18.75,9.75 C19.9926407,9.75 21,10.7573593 21,12 C21,13.2426407 19.9926407,14.25 18.75,14.25 L18.6854912,14.249994 C18.4911876,14.250769 18.3158978,14.366855 18.2393549,14.5454486 C18.1556809,14.7351461 18.1942911,14.948087 18.3278301,15.0846699 L18.372535,15.129375 C18.7950334,15.5514036 19.03243,16.1240792 19.03243,16.72125 C19.03243,17.3184208 18.7950334,17.8910964 18.373125,18.312535 C17.9510964,18.7350334 17.3784208,18.97243 16.78125,18.97243 C16.1840792,18.97243 15.6114036,18.7350334 15.1896699,18.3128301 L15.1505513,18.2736469 C15.008087,18.1342911 14.7951461,18.0956809 14.6054486,18.1793549 C14.426855,18.2558978 14.310769,18.4311876 14.31,18.6225 L14.31,18.75 C14.31,19.9926407 13.3026407,21 12.06,21 C10.8173593,21 9.81,19.9926407 9.81,18.75 C9.80552409,18.4999185 9.67898539,18.3229986 9.44717599,18.2361469 C9.26485393,18.1556809 9.05191298,18.1942911 8.91533009,18.3278301 L8.870625,18.372535 C8.44859642,18.7950334 7.87592081,19.03243 7.27875,19.03243 C6.68157919,19.03243 6.10890358,18.7950334 5.68746499,18.373125 C5.26496665,17.9510964 5.02757002,17.3784208 5.02757002,16.78125 C5.02757002,16.1840792 5.26496665,15.6114036 5.68716991,15.1896699 L5.72635306,15.1505513 C5.86570889,15.008087 5.90431906,14.7951461 5.82064513,14.6054486 C5.74410223,14.426855 5.56881236,14.310769 5.3775,14.31 L5.25,14.31 C4.00735931,14.31 3,13.3026407 3,12.06 C3,10.8173593 4.00735931,9.81 5.25,9.81 C5.50008154,9.80552409 5.67700139,9.67898539 5.76385306,9.44717599 C5.84431906,9.26485393 5.80570889,9.05191298 5.67216991,8.91533009 L5.62746499,8.870625 C5.20496665,8.44859642 4.96757002,7.87592081 4.96757002,7.27875 C4.96757002,6.68157919 5.20496665,6.10890358 5.626875,5.68746499 C6.04890358,5.26496665 6.62157919,5.02757002 7.21875,5.02757002 C7.81592081,5.02757002 8.38859642,5.26496665 8.81033009,5.68716991 L8.84944872,5.72635306 C8.99191298,5.86570889 9.20485393,5.90431906 9.38717599,5.82385306 L9.49484664,5.80114977 C9.65041313,5.71688974 9.7492905,5.55401473 9.75,5.3775 L9.75,5.25 C9.75,4.00735931 10.7573593,3 12,3 C13.2426407,3 14.25,4.00735931 14.25,5.25 L14.249994,5.31450877 C14.250769,5.50881236 14.366855,5.68410223 14.552824,5.76385306 C14.7351461,5.84431906 14.948087,5.80570889 15.0846699,5.67216991 L15.129375,5.62746499 C15.5514036,5.20496665 16.1240792,4.96757002 16.72125,4.96757002 C17.3184208,4.96757002 17.8910964,5.20496665 18.312535,5.626875 C18.7350334,6.04890358 18.97243,6.62157919 18.97243,7.21875 C18.97243,7.81592081 18.7350334,8.38859642 18.3128301,8.81033009 L18.2736469,8.84944872 C18.1342911,8.99191298 18.0956809,9.20485393 18.1761469,9.38717599 L18.1988502,9.49484664 C18.2831103,9.65041313 18.4459853,9.7492905 18.6225,9.75 Z" fill="#000000" fill-rule="nonzero" opacity="0.3"/&gt;
        &lt;path d="M12,15 C13.6568542,15 15,13.6568542 15,12 C15,10.3431458 13.6568542,9 12,9 C10.3431458,9 9,10.3431458 9,12 C9,13.6568542 10.3431458,15 12,15 Z" fill="#000000"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setSettingsCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className="svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<path d="M12.5936684,18.0752333 L12.5936684,14.4063316 L18.5936684,14.4063316 L18.5936684,8.40633161 L12.5936684,8.40633161 L12.5936684,4.73208782 L5.92209543,11.3984411 L12.5936684,18.0752333 Z M14.5936684,6.40633161 L19.5936684,6.40633161 C20.1459531,6.40633161 20.5936684,6.85404686 20.5936684,7.40633161 L20.5936684,15.4063316 C20.5936684,15.9586164 20.1459531,16.4063316 19.5936684,16.4063316 L14.5936684,16.4063316 L14.5936684,21.0946697 C14.5936684,21.2936837 14.5145702,21.484538 14.3737911,21.6252071 C14.0807833,21.9179858 13.6059096,21.9178001 13.313131,21.6247924 L3.62379074,11.9278722 C3.33101216,11.6348644 3.33119799,11.1599907 3.6242058,10.8672121 L13.3135459,1.18545264 C13.4541812,1.04492729 13.6448577,0.965990217 13.8436684,0.965990217 C14.257882,0.965990217 14.5936684,1.30177665 14.5936684,1.71599022 L14.5936684,6.40633161 Z" fill="#000000" fill-rule="nonzero" transform="translate(11.998998, 11.405330) scale(-1, 1) rotate(-270.000000) translate(-11.998998, -11.405330) "></path>
																</g>
															</svg> 	</div>	
															<div className="svg-classname">
															Shift.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setShiftSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setShiftCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={shiftSvg} onHide={setShiftSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Shift.svg</h5>
																		<button type="button" className="close" onClick={()=>setShiftSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Shift.svg&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setShiftSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={shiftCode} onHide={setShiftCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Shift.svg</h5>
																		<button type="button" className="close" onClick={()=>setShiftCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;path d="M18.6225,9.75 L18.75,9.75 C19.9926407,9.75 21,10.7573593 21,12 C21,13.2426407 19.9926407,14.25 18.75,14.25 L18.6854912,14.249994 C18.4911876,14.250769 18.3158978,14.366855 18.2393549,14.5454486 C18.1556809,14.7351461 18.1942911,14.948087 18.3278301,15.0846699 L18.372535,15.129375 C18.7950334,15.5514036 19.03243,16.1240792 19.03243,16.72125 C19.03243,17.3184208 18.7950334,17.8910964 18.373125,18.312535 C17.9510964,18.7350334 17.3784208,18.97243 16.78125,18.97243 C16.1840792,18.97243 15.6114036,18.7350334 15.1896699,18.3128301 L15.1505513,18.2736469 C15.008087,18.1342911 14.7951461,18.0956809 14.6054486,18.1793549 C14.426855,18.2558978 14.310769,18.4311876 14.31,18.6225 L14.31,18.75 C14.31,19.9926407 13.3026407,21 12.06,21 C10.8173593,21 9.81,19.9926407 9.81,18.75 C9.80552409,18.4999185 9.67898539,18.3229986 9.44717599,18.2361469 C9.26485393,18.1556809 9.05191298,18.1942911 8.91533009,18.3278301 L8.870625,18.372535 C8.44859642,18.7950334 7.87592081,19.03243 7.27875,19.03243 C6.68157919,19.03243 6.10890358,18.7950334 5.68746499,18.373125 C5.26496665,17.9510964 5.02757002,17.3784208 5.02757002,16.78125 C5.02757002,16.1840792 5.26496665,15.6114036 5.68716991,15.1896699 L5.72635306,15.1505513 C5.86570889,15.008087 5.90431906,14.7951461 5.82064513,14.6054486 C5.74410223,14.426855 5.56881236,14.310769 5.3775,14.31 L5.25,14.31 C4.00735931,14.31 3,13.3026407 3,12.06 C3,10.8173593 4.00735931,9.81 5.25,9.81 C5.50008154,9.80552409 5.67700139,9.67898539 5.76385306,9.44717599 C5.84431906,9.26485393 5.80570889,9.05191298 5.67216991,8.91533009 L5.62746499,8.870625 C5.20496665,8.44859642 4.96757002,7.87592081 4.96757002,7.27875 C4.96757002,6.68157919 5.20496665,6.10890358 5.626875,5.68746499 C6.04890358,5.26496665 6.62157919,5.02757002 7.21875,5.02757002 C7.81592081,5.02757002 8.38859642,5.26496665 8.81033009,5.68716991 L8.84944872,5.72635306 C8.99191298,5.86570889 9.20485393,5.90431906 9.38717599,5.82385306 L9.49484664,5.80114977 C9.65041313,5.71688974 9.7492905,5.55401473 9.75,5.3775 L9.75,5.25 C9.75,4.00735931 10.7573593,3 12,3 C13.2426407,3 14.25,4.00735931 14.25,5.25 L14.249994,5.31450877 C14.250769,5.50881236 14.366855,5.68410223 14.552824,5.76385306 C14.7351461,5.84431906 14.948087,5.80570889 15.0846699,5.67216991 L15.129375,5.62746499 C15.5514036,5.20496665 16.1240792,4.96757002 16.72125,4.96757002 C17.3184208,4.96757002 17.8910964,5.20496665 18.312535,5.626875 C18.7350334,6.04890358 18.97243,6.62157919 18.97243,7.21875 C18.97243,7.81592081 18.7350334,8.38859642 18.3128301,8.81033009 L18.2736469,8.84944872 C18.1342911,8.99191298 18.0956809,9.20485393 18.1761469,9.38717599 L18.1988502,9.49484664 C18.2831103,9.65041313 18.4459853,9.7492905 18.6225,9.75 Z" fill="#000000" fill-rule="nonzero" opacity="0.3"/&gt;
        &lt;path d="M12,15 C13.6568542,15 15,13.6568542 15,12 C15,10.3431458 13.6568542,9 12,9 C10.3431458,9 9,10.3431458 9,12 C9,13.6568542 10.3431458,15 12,15 Z" fill="#000000"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setShiftCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className=" svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<path d="M12,3 C16.418278,3 20,6.581722 20,11 L20,21 C20,21.5522847 19.5522847,22 19,22 L5,22 C4.44771525,22 4,21.5522847 4,21 L4,11 C4,6.581722 7.581722,3 12,3 Z M9,10 C7.34314575,10 6,11.3431458 6,13 C6,14.6568542 7.34314575,16 9,16 L15,16 C16.6568542,16 18,14.6568542 18,13 C18,11.3431458 16.6568542,10 15,10 L9,10 Z" fill="#000000"></path>
																	<path d="M15,14 C14.4477153,14 14,13.5522847 14,13 C14,12.4477153 14.4477153,12 15,12 C15.5522847,12 16,12.4477153 16,13 C16,13.5522847 15.5522847,14 15,14 Z M9,14 C8.44771525,14 8,13.5522847 8,13 C8,12.4477153 8.44771525,12 9,12 C9.55228475,12 10,12.4477153 10,13 C10,13.5522847 9.55228475,14 9,14 Z" fill="#000000" opacity="0.3"></path>
																</g>
															</svg> </div>
														<div className="svg-classname">
															Spy.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setSpySvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setSpyCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={spySvg} onHide={setSpySvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Spy.svg</h5>
																		<button type="button" className="close" onClick={()=>setSpySvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Spy.svg&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setSpySvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={spyCode} onHide={setSpyCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Spy.svg</h5>
																		<button type="button" className="close" onClick={()=>setSpyCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;path d="M12,3 C16.418278,3 20,6.581722 20,11 L20,21 C20,21.5522847 19.5522847,22 19,22 L5,22 C4.44771525,22 4,21.5522847 4,21 L4,11 C4,6.581722 7.581722,3 12,3 Z M9,10 C7.34314575,10 6,11.3431458 6,13 C6,14.6568542 7.34314575,16 9,16 L15,16 C16.6568542,16 18,14.6568542 18,13 C18,11.3431458 16.6568542,10 15,10 L9,10 Z" fill="#000000"/&gt;
        &lt;path d="M15,14 C14.4477153,14 14,13.5522847 14,13 C14,12.4477153 14.4477153,12 15,12 C15.5522847,12 16,12.4477153 16,13 C16,13.5522847 15.5522847,14 15,14 Z M9,14 C8.44771525,14 8,13.5522847 8,13 C8,12.4477153 8.44771525,12 9,12 C9.55228475,12 10,12.4477153 10,13 C10,13.5522847 9.55228475,14 9,14 Z" fill="#000000" opacity="0.3"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setSpyCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className=" svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<path d="M12,22 C6.4771525,22 2,17.5228475 2,12 C2,6.4771525 6.4771525,2 12,2 C17.5228475,2 22,6.4771525 22,12 C22,17.5228475 17.5228475,22 12,22 Z M12,20 C16.418278,20 20,16.418278 20,12 C20,7.581722 16.418278,4 12,4 C7.581722,4 4,7.581722 4,12 C4,16.418278 7.581722,20 12,20 Z M19.0710678,4.92893219 L19.0710678,4.92893219 C19.4615921,5.31945648 19.4615921,5.95262146 19.0710678,6.34314575 L6.34314575,19.0710678 C5.95262146,19.4615921 5.31945648,19.4615921 4.92893219,19.0710678 L4.92893219,19.0710678 C4.5384079,18.6805435 4.5384079,18.0473785 4.92893219,17.6568542 L17.6568542,4.92893219 C18.0473785,4.5384079 18.6805435,4.5384079 19.0710678,4.92893219 Z" fill="#000000" fill-rule="nonzero" opacity="0.3"></path>
																</g>
															</svg> </div>
														<div className="svg-classname">
															Stop.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setStopSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setStopCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={stopSvg} onHide={setStopSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Stop.svg</h5>
																		<button type="button" className="close" onClick={()=>setStopSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Stop.svg&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setStopSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={stopCode} onHide={setStopCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Stop.svg</h5>
																		<button type="button" className="close" onClick={()=>setStopCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;path d="M12,22 C6.4771525,22 2,17.5228475 2,12 C2,6.4771525 6.4771525,2 12,2 C17.5228475,2 22,6.4771525 22,12 C22,17.5228475 17.5228475,22 12,22 Z M12,20 C16.418278,20 20,16.418278 20,12 C20,7.581722 16.418278,4 12,4 C7.581722,4 4,7.581722 4,12 C4,16.418278 7.581722,20 12,20 Z M19.0710678,4.92893219 L19.0710678,4.92893219 C19.4615921,5.31945648 19.4615921,5.95262146 19.0710678,6.34314575 L6.34314575,19.0710678 C5.95262146,19.4615921 5.31945648,19.4615921 4.92893219,19.0710678 L4.92893219,19.0710678 C4.5384079,18.6805435 4.5384079,18.0473785 4.92893219,17.6568542 L17.6568542,4.92893219 C18.0473785,4.5384079 18.6805435,4.5384079 19.0710678,4.92893219 Z" fill="#000000" fill-rule="nonzero" opacity="0.3"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setStopCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className=" svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<polygon points="0 0 24 0 24 24 0 24"></polygon>
																	<path d="M3.70710678,15.7071068 C3.31658249,16.0976311 2.68341751,16.0976311 2.29289322,15.7071068 C1.90236893,15.3165825 1.90236893,14.6834175 2.29289322,14.2928932 L8.29289322,8.29289322 C8.67147216,7.91431428 9.28105859,7.90106866 9.67572463,8.26284586 L15.6757246,13.7628459 C16.0828436,14.1360383 16.1103465,14.7686056 15.7371541,15.1757246 C15.3639617,15.5828436 14.7313944,15.6103465 14.3242754,15.2371541 L9.03007575,10.3841378 L3.70710678,15.7071068 Z" fill="#000000" fill-rule="nonzero" transform="translate(9.000003, 11.999999) rotate(-270.000000) translate(-9.000003, -11.999999) "></path>
																	<rect fill="#000000" opacity="0.3" x="12" y="17" width="10" height="2" rx="1"></rect>
																</g>
															</svg> </div>
														<div className="svg-classname">
															Terminal.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setTerminalSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setTerminalCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={terminalSvg} onHide={setTerminalSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Terminal.svg</h5>
																		<button type="button" className="close" onClick={()=>setTerminalSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Terminal.svg&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setTerminalSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={terminalCode} onHide={setTerminalCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Terminal.svg</h5>
																		<button type="button" className="close" onClick={()=>setTerminalCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;polygon points="0 0 24 0 24 24 0 24"/&gt;
        &lt;path d="M3.70710678,15.7071068 C3.31658249,16.0976311 2.68341751,16.0976311 2.29289322,15.7071068 C1.90236893,15.3165825 1.90236893,14.6834175 2.29289322,14.2928932 L8.29289322,8.29289322 C8.67147216,7.91431428 9.28105859,7.90106866 9.67572463,8.26284586 L15.6757246,13.7628459 C16.0828436,14.1360383 16.1103465,14.7686056 15.7371541,15.1757246 C15.3639617,15.5828436 14.7313944,15.6103465 14.3242754,15.2371541 L9.03007575,10.3841378 L3.70710678,15.7071068 Z" fill="#000000" fill-rule="nonzero" transform="translate(9.000003, 11.999999) rotate(-270.000000) translate(-9.000003, -11.999999) "/&gt;
        &lt;rect fill="#000000" opacity="0.3" x="12" y="17" width="10" height="2" rx="1"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setTerminalCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className=" svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"></circle>
																	<path d="M12.4208204,17.1583592 L15.4572949,11.0854102 C15.6425368,10.7149263 15.4923686,10.2644215 15.1218847,10.0791796 C15.0177431,10.0271088 14.9029083,10 14.7864745,10 L12,10 L12,7.17705098 C12,6.76283742 11.6642136,6.42705098 11.25,6.42705098 C10.965921,6.42705098 10.7062236,6.58755277 10.5791796,6.84164079 L7.5427051,12.9145898 C7.35746316,13.2850737 7.50763142,13.7355785 7.87811529,13.9208204 C7.98225687,13.9728912 8.09709167,14 8.21352549,14 L11,14 L11,16.822949 C11,17.2371626 11.3357864,17.572949 11.75,17.572949 C12.034079,17.572949 12.2937764,17.4124472 12.4208204,17.1583592 Z" fill="#000000"></path>
																</g>
															</svg> </div>
														<div className="svg-classname">
															Thunder-circle.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setThunderSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setThunderCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={thunderSvg} onHide={setThunderSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Thunder-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setThunderSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Thunder-circle.svg&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setThunderSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={thunderCode} onHide={setThunderCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Thunder-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setThunderCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"/&gt;
        &lt;path d="M12.4208204,17.1583592 L15.4572949,11.0854102 C15.6425368,10.7149263 15.4923686,10.2644215 15.1218847,10.0791796 C15.0177431,10.0271088 14.9029083,10 14.7864745,10 L12,10 L12,7.17705098 C12,6.76283742 11.6642136,6.42705098 11.25,6.42705098 C10.965921,6.42705098 10.7062236,6.58755277 10.5791796,6.84164079 L7.5427051,12.9145898 C7.35746316,13.2850737 7.50763142,13.7355785 7.87811529,13.9208204 C7.98225687,13.9728912 8.09709167,14 8.21352549,14 L11,14 L11,16.822949 C11,17.2371626 11.3357864,17.572949 11.75,17.572949 C12.034079,17.572949 12.2937764,17.4124472 12.4208204,17.1583592 Z" fill="#000000"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setThunderCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												
			</div>	
			<div className="row">
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className=" svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<path d="M10.9630156,7.5 L11.0475062,7.5 C11.3043819,7.5 11.5194647,7.69464724 11.5450248,7.95024814 L12,12.5 L15.2480695,14.3560397 C15.403857,14.4450611 15.5,14.6107328 15.5,14.7901613 L15.5,15 C15.5,15.2109164 15.3290185,15.3818979 15.1181021,15.3818979 C15.0841582,15.3818979 15.0503659,15.3773725 15.0176181,15.3684413 L10.3986612,14.1087258 C10.1672824,14.0456225 10.0132986,13.8271186 10.0316926,13.5879956 L10.4644883,7.96165175 C10.4845267,7.70115317 10.7017474,7.5 10.9630156,7.5 Z" fill="#000000"></path>
																	<path d="M7.38979581,2.8349582 C8.65216735,2.29743306 10.0413491,2 11.5,2 C17.2989899,2 22,6.70101013 22,12.5 C22,18.2989899 17.2989899,23 11.5,23 C5.70101013,23 1,18.2989899 1,12.5 C1,11.5151324 1.13559454,10.5619345 1.38913364,9.65805651 L3.31481075,10.1982117 C3.10672013,10.940064 3,11.7119264 3,12.5 C3,17.1944204 6.80557963,21 11.5,21 C16.1944204,21 20,17.1944204 20,12.5 C20,7.80557963 16.1944204,4 11.5,4 C10.54876,4 9.62236069,4.15592757 8.74872191,4.45446326 L9.93948308,5.87355717 C10.0088058,5.95617272 10.0495583,6.05898805 10.05566,6.16666224 C10.0712834,6.4423623 9.86044965,6.67852665 9.5847496,6.69415008 L4.71777931,6.96995273 C4.66931162,6.97269931 4.62070229,6.96837279 4.57348157,6.95710938 C4.30487471,6.89303938 4.13906482,6.62335149 4.20313482,6.35474463 L5.33163823,1.62361064 C5.35654118,1.51920756 5.41437908,1.4255891 5.49660017,1.35659741 C5.7081375,1.17909652 6.0235153,1.2066885 6.2010162,1.41822583 L7.38979581,2.8349582 Z" fill="#000000" opacity="0.3"></path>
																</g>
															</svg></div>
														<div className="svg-classname">
															Time-schedule.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setTimeSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setTimeCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={timeSvg} onHide={setTimeSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Time-schedule.svg</h5>
																		<button type="button" className="close" onClick={()=>setTimeSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Time-schedule.svg&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setTimeSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={timeCode} onHide={setTimeCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Time-schedule.svg</h5>
																		<button type="button" className="close" onClick={()=>setTimeCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;path d="M10.9630156,7.5 L11.0475062,7.5 C11.3043819,7.5 11.5194647,7.69464724 11.5450248,7.95024814 L12,12.5 L15.2480695,14.3560397 C15.403857,14.4450611 15.5,14.6107328 15.5,14.7901613 L15.5,15 C15.5,15.2109164 15.3290185,15.3818979 15.1181021,15.3818979 C15.0841582,15.3818979 15.0503659,15.3773725 15.0176181,15.3684413 L10.3986612,14.1087258 C10.1672824,14.0456225 10.0132986,13.8271186 10.0316926,13.5879956 L10.4644883,7.96165175 C10.4845267,7.70115317 10.7017474,7.5 10.9630156,7.5 Z" fill="#000000"/&gt;
        &lt;path d="M7.38979581,2.8349582 C8.65216735,2.29743306 10.0413491,2 11.5,2 C17.2989899,2 22,6.70101013 22,12.5 C22,18.2989899 17.2989899,23 11.5,23 C5.70101013,23 1,18.2989899 1,12.5 C1,11.5151324 1.13559454,10.5619345 1.38913364,9.65805651 L3.31481075,10.1982117 C3.10672013,10.940064 3,11.7119264 3,12.5 C3,17.1944204 6.80557963,21 11.5,21 C16.1944204,21 20,17.1944204 20,12.5 C20,7.80557963 16.1944204,4 11.5,4 C10.54876,4 9.62236069,4.15592757 8.74872191,4.45446326 L9.93948308,5.87355717 C10.0088058,5.95617272 10.0495583,6.05898805 10.05566,6.16666224 C10.0712834,6.4423623 9.86044965,6.67852665 9.5847496,6.69415008 L4.71777931,6.96995273 C4.66931162,6.97269931 4.62070229,6.96837279 4.57348157,6.95710938 C4.30487471,6.89303938 4.13906482,6.62335149 4.20313482,6.35474463 L5.33163823,1.62361064 C5.35654118,1.51920756 5.41437908,1.4255891 5.49660017,1.35659741 C5.7081375,1.17909652 6.0235153,1.2066885 6.2010162,1.41822583 L7.38979581,2.8349582 Z" fill="#000000" opacity="0.3"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setTimeCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className=" svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"></circle>
																	<rect fill="#000000" x="11" y="7" width="2" height="8" rx="1"></rect>
																	<rect fill="#000000" x="11" y="16" width="2" height="2" rx="1"></rect>
																</g>
															</svg></div>
														<div className="svg-classname">
															Warning-1-circle.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setWarningSvg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setWarningCode(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={warningSvg} onHide={setWarningSvg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Warning-1-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setWarningSvg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Warning-1-circle.svg&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setWarningSvg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={warningCode} onHide={setWarningCode}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Warning-1-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setWarningCode(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;circle fill="#000000" opacity="0.3" cx="12" cy="12" r="10"/&gt;
        &lt;rect fill="#000000" x="11" y="7" width="2" height="8" rx="1"/&gt;
        &lt;rect fill="#000000" x="11" y="16" width="2" height="2" rx="1"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setWarningCode(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
												<div className="col-xl-2 col-lg-3 col-xxl-3 col-md-4 col-sm-6 col-12">
													<div className=" svg-icons-ov">
														<div className="svg-icons-prev">
															<svg xmlns="http://www.w3.org/2000/svg"  width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon">
																<g stroke="none" strokeWidth="1" fill="none" fillRule="evenodd">
																	<rect x="0" y="0" width="24" height="24"></rect>
																	<path d="M11.1669899,4.49941818 L2.82535718,19.5143571 C2.557144,19.9971408 2.7310878,20.6059441 3.21387153,20.8741573 C3.36242953,20.9566895 3.52957021,21 3.69951446,21 L21.2169432,21 C21.7692279,21 22.2169432,20.5522847 22.2169432,20 C22.2169432,19.8159952 22.1661743,19.6355579 22.070225,19.47855 L12.894429,4.4636111 C12.6064401,3.99235656 11.9909517,3.84379039 11.5196972,4.13177928 C11.3723594,4.22181902 11.2508468,4.34847583 11.1669899,4.49941818 Z" fill="#000000" opacity="0.3"></path>
																	<rect fill="#000000" x="11" y="9" width="2" height="7" rx="1"></rect>
																	<rect fill="#000000" x="11" y="17" width="2" height="2" rx="1"></rect>
																</g>
															</svg></div>
														<div className="svg-classname">
															Warning-2-circle.svg </div>
														<div className="svg-icon-popup">
															<Link to={"#"} onClick={()=>setWarning2Svg(true)} className="btn btn-sm btn-brand"><i className="fa fa-picture-o"></i></Link>
															<Link to={"#"} onClick={()=>setWarning2Code(true)} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
														</div>
														<Modal show={warning2Svg} onHide={setWarning2Svg}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Warning-2-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setWarning2Svg(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>&lt;img src="assets/media/icons/svg/Code/Warning-2-circle.svg&gt;</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setWarning2Svg(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
														<Modal show={warning2Code} onHide={setWarning2Code}>
															<div className="modal-dialog-centered" role="document">
																<div className="modal-content">
																	<div className="modal-header">
																		<h5 className="modal-title">Warning-2-circle.svg</h5>
																		<button type="button" className="close" onClick={()=>setWarning2Code(false)}><span>×</span>
																		</button>
																	</div>
																	<div className="modal-body">
																		<pre>{`&lt;svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1" className="svg-main-icon"&gt;
    &lt;g stroke="none" strokeWidth="1" fill="none" fillRule="evenodd"&gt;
        &lt;rect x="0" y="0" width="24" height="24"/&gt;
        &lt;path d="M11.1669899,4.49941818 L2.82535718,19.5143571 C2.557144,19.9971408 2.7310878,20.6059441 3.21387153,20.8741573 C3.36242953,20.9566895 3.52957021,21 3.69951446,21 L21.2169432,21 C21.7692279,21 22.2169432,20.5522847 22.2169432,20 C22.2169432,19.8159952 22.1661743,19.6355579 22.070225,19.47855 L12.894429,4.4636111 C12.6064401,3.99235656 11.9909517,3.84379039 11.5196972,4.13177928 C11.3723594,4.22181902 11.2508468,4.34847583 11.1669899,4.49941818 Z" fill="#000000" opacity="0.3"/&gt;
        &lt;rect fill="#000000" x="11" y="9" width="2" height="7" rx="1"/&gt;
        &lt;rect fill="#000000" x="11" y="17" width="2" height="2" rx="1"/&gt;
    &lt;/g&gt;
&lt;/svg&gt;`}</pre>
																	</div>
																	<div className="modal-footer">
																		<button type="button" className="btn btn-secondary" onClick={()=>setWarning2Code(false)}>Close</button>
																	</div>
																</div>
															</div>
														</Modal>
													</div>
												</div>
			</div>	
			
												
		</>
	)
}
export default CodeBlog;