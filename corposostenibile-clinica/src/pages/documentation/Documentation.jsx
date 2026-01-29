import React from 'react';

const Documentation = () => {
    const docUrl = "/documentation/static/"; 

    return (
        <div style={{ 
            width: 'calc(100% + 60px)',
            height: 'calc(100vh - 140px)',
            margin: '-30px',
            backgroundColor: '#fff',
            overflow: 'hidden'
        }}>
            <iframe 
                src={docUrl} 
                title="Corposostenibile Documentation"
                style={{
                    width: '100%',
                    height: '100%',
                    border: 'none',
                    display: 'block'
                }}
            />
        </div>
    );
};

export default Documentation;
