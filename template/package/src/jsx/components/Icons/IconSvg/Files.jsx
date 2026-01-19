import React,{useReducer} from 'react';
import {Link} from 'react-router-dom';
import { Modal } from 'react-bootstrap';


import { ICONS } from '../../../constant/theme';

const svgBlogData = [
    {Iconname : 'Cloud-Download.svg', svgtype : ICONS.CloudDownload},
    {Iconname : 'Cloud-Upload.svg', svgtype : ICONS.CloudUpload},
    {Iconname : 'Compilation.svg', svgtype : ICONS.Compilation},
    {Iconname : 'Compiled-File.svg', svgtype : ICONS.CompiledFile},
    {Iconname : 'Deleted-File.svg', svgtype : ICONS.DeletedFile},
    {Iconname : 'Deleted-Folder.svg', svgtype : ICONS.DeletedFolder},
    {Iconname : 'Download.svg', svgtype : ICONS.Download},
    {Iconname : 'Downloaded-File.svg', svgtype : ICONS.DownloadedFile},
    {Iconname : 'Downloads-Folder.svg', svgtype : ICONS.DownloadsFolder},
    {Iconname : 'Export.svg', svgtype : ICONS.Export},
    {Iconname : 'File-Cloud.svg', svgtype : ICONS.FileCloud},
    {Iconname : 'File-Done.svg', svgtype : ICONS.FileDone},
    {Iconname : 'File-Minus.svg', svgtype : ICONS.FileMinus},
    {Iconname : 'File-Plus.svg', svgtype : ICONS.FilePlus},
    {Iconname : 'File.svg', svgtype : ICONS.File},
    {Iconname : 'Folder-Check.svg', svgtype : ICONS.FolderCheck},
    {Iconname : 'Folder-Cloud.svg', svgtype : ICONS.FolderCloud},
    {Iconname : 'Folder-Error.svg', svgtype : ICONS.FolderError},
    {Iconname : 'Folder-Heart.svg', svgtype : ICONS.FolderHeart},
    {Iconname : 'Folder-Minus.svg', svgtype : ICONS.FolderMinus},
    {Iconname : 'Folder-Plus.svg', svgtype : ICONS.FolderPlus},
    {Iconname : 'Folder-Solid.svg', svgtype : ICONS.FolderSolid},
    {Iconname : 'Folder-Star.svg', svgtype : ICONS.FolderStar},
    {Iconname : 'Folder-Thunder.svg', svgtype : ICONS.FolderThunder},
    {Iconname : 'Folder.svg', svgtype : ICONS.Folder},
    {Iconname : 'Group-Folders.svg', svgtype : ICONS.GroupFolders},
    {Iconname : 'Import.svg', svgtype : ICONS.Import},
       
];

const Files = () => {
    const initialState = false;
    const reducer = (state, action) =>{   
        switch (action.type){
            case 'imageModal':
                return { ...state, imageModal: !state.imageModal, content : action.content}
            case 'svgModal':
                return { ...state, svgModal: !state.svgModal, content : action.content, title: action.title}			
            default:
                return state
        }	
    }
    const [state, dispatch] = useReducer(reducer, initialState);
    return (
        <>
            <div className="card-header">Files</div>
            <div className="row">							
                {svgBlogData.map((item, ind)=>(
                    <div className="col-xl-2 col-lg-4 col-xxl-2 col-md-6 col-sm-6 col-12 m-b20" key={ind}>	
                        <div className="svg-icons-ov">
                            <div className="svg-icons-prev">
                                <div dangerouslySetInnerHTML={{ __html: item.svgtype }} />                                                    
                            </div>
                            <div className="svg-classname">{item.Iconname}</div>
                            <div className="svg-icon-popup">
                                <Link to={"#"}  onClick={() => dispatch({type:'imageModal', content: item.Iconname })} className="btn btn-sm btn-brand"><i className="fa-solid fa-image"></i></Link>
                                <Link to={"#"} onClick={() => dispatch({type:'svgModal', content: item.Iconname, title : item.svgtype })} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
                            </div>
                            
                        </div>
                    </div>
                ))}
            </div>
                           
                <Modal className="modal fade" show={state.imageModal} onHide={()=>dispatch({type:'imageModal'})} centered>                                
                    <div className="modal-content">
                        <div className="modal-header">
                            <h5 className="modal-title" id="svg_img_label_Brassieresvg">{state.content}</h5>
                            <button type="button" className="btn-close" onClick={() => dispatch({type:'imageModal'})}></button>
                        </div>
                        <div className="modal-body">                               
                            <pre>                           
{`import MyImage from "../icons/svgicons/${state.content}";
export default function Imageblog() {   
return  
    <div>
    <img src={MyImage} alt="Example" />   
    </div>
}`}
;
                            </pre>
                        </div>
                        <div className="modal-footer">
                            <button type="button" className="btn btn-secondary" onClick={() => dispatch({type:'imageModal'})}>Close</button>
                        </div>
                    </div>
                
                </Modal>
                <Modal className="modal fade" show={state.svgModal} onHide={()=>dispatch({type:'svgModal'})} centered >                    
                    <div className="modal-content">
                        <div className="modal-header">
                            <h5 className="modal-title" id="svg_inline_label_Brassieresvg">{state.content}</h5>
                            <button type="button" className="btn-close"   onClick={() => dispatch({type:'svgModal'})}>
                            </button>
                        </div>
                        <div className="modal-body">
<pre>   
{state.title}    
</pre>
                        </div>
                        <div className="modal-footer">
                            <button type="button" className="btn btn-secondary" onClick={() => dispatch({type:'svgModal'})}>Close</button>
                        </div>
                    </div>
                    
                </Modal>  
        </>
    );
};

export default Files;