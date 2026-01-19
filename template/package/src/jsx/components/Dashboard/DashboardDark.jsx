import React,{useContext, useEffect} from 'react';
import { AllSection } from './Home';

import { ThemeContext } from "../../../context/ThemeContext";

const DashboardDark  = () => {
	const { changeBackground } = useContext(ThemeContext);
	  useEffect(() => {
		changeBackground({ value: "dark", label: "Dark" });
	}, []);
	
	return(
		<>
			<AllSection />
		</>
	)
}
export default DashboardDark;