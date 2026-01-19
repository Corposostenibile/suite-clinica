import React from 'react';
import { CKEditor } from '@ckeditor/ckeditor5-react';
import ClassicEditor from '@ckeditor/ckeditor5-build-classic';




const CkEditorBlog = () => {
    return (
        <>
            <CKEditor
                editor={ ClassicEditor }           
                
                onChange={ ( event ) => {
                    // const data = editor.getData();
                    
                } }               
            />  
        </>
    );
};

export default CkEditorBlog;