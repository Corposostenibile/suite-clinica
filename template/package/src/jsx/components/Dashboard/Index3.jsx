import React,{useContext, useEffect} from 'react';
import { AllSection } from './Home';

import { ThemeContext } from "../../../context/ThemeContext";

const Index3 = () => {
    const { 
		changeBackground,				
        changeNavigationHader,
        changeSideBarStyle,
        chnageSidebarColor
	} = useContext(ThemeContext);
	useEffect(() => {
		changeBackground({ value: "light", label: "Light" });				
		changeSideBarStyle({ value: "mini", label: "Mini" });				
		changeNavigationHader("color_3");				
		chnageSidebarColor("color_1");				
	}, []);
    return (
        <>
            <AllSection />
        </>
    );
};

export default Index3;