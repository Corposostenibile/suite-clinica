import { SVGICON } from "../../constant/theme";



export const MenuList2 = [
    {
        title:'',
        classStyle:"blank",
        content : []
    },
    //Dashboard
    {
        title: 'Dashboard',	
        classsChange: 'mm-collapse',		
        iconStyle: SVGICON.Dashboard,
        eventKey:"Dashboard1",
        content: [
            {
                title: 'Light',
                to: 'dashboard',					
            },           
            {
                title: 'Dark',
                to: 'dashboard-dark',					
            },                       
            {
                title: 'Mini Sidebar',
                to: 'index-3',					
            },                       
            {
                title: 'Sidebar',
                to: 'index-4',					
            },                                  
              
        ],
    },
    {
        title:'CMS',        
        classsChange : 'mm-collapse',
        iconStyle: SVGICON.CmsSvg,
        eventKey:"Cms",
        content : [
            {
                title:'Content',
                to:'content'
            },            
            {
                title:'Menu',
                to:'menu'
            },
            {
                title:'Email Template',
                to:'email-template'
            },
           
            {
                title:'Blog',
                to:'blog'
            },            
        ],
    },
    
   {
        name:'doubleArray',
        title:"APPS",
        mainArray : [
             //Apps
                {
                    title: 'Apps',	
                    classsChange: 'mm-collapse',
                    iconStyle: SVGICON.AppSvg,
                    content: [
                        {
                            title: 'Profile',
                            to: 'app-profile'
                        },  
                       
                        {
                            title: 'Email',   
                            metisMenu:"has-menu",             
                            hasMenu : true,
                            content: [
                                {
                                    title: 'Compose',
                                    to: 'email-compose',
                                },
                                {
                                    title: 'Inbox',
                                    to: 'email-inbox',
                                },
                                {
                                    title: 'Read',
                                    to: 'email-read',
                                }
                            ],
                        },
                        {
                            title:'Calendar',
                            to: 'app-calender'
                        },
                        {
                            title: 'Shop',
                            //to: './',
                            metisMenu:"has-menu", 
                            hasMenu : true,
                            content: [
                                {
                                    title: 'Product Grid',
                                    to: 'ecom-product-grid',
                                },
                                {
                                    title: 'Product List',
                                    to: 'ecom-product-list',
                                },
                                {
                                    title: 'Product Details',
                                    to: 'ecom-product-detail',
                                },
                                {
                                    title: 'Order',
                                    to: 'ecom-product-order',
                                },
                                {
                                    title: 'Checkout',
                                    to: 'ecom-checkout',
                                },
                                {
                                    title: 'Invoice',
                                    to: 'ecom-invoice',
                                },
                                {
                                    title: 'Customers',
                                    to: 'ecom-customers',
                                },
                            ],
                        },
                    ],
                    
                },
                                
                //Charts
                {
                    title: 'Charts',	
                    classsChange: 'mm-collapse',
                    iconStyle: SVGICON.Charts,
                    content: [
                        
                        {
                            title: 'RechartJs',
                            to: 'chart-rechart',					
                        },
                        {
                            title: 'Chartjs',
                            to: 'chart-chartjs',					
                        },
                        {
                            title: 'Sparkline',
                            to: 'chart-sparkline',					
                        },
                        {
                            title: 'Apexchart',
                            to: 'chart-apexchart',					
                        },
                    ]
                },

        ]
        
   },


   {
        name:"doubleArray",
        title:"COMPONENTS",
        mainArray : [
            //Boosttrap
            {
                title: 'Bootstrap',	
                classsChange: 'mm-collapse',
                iconStyle: SVGICON.Bootstrap,
                content: [
                    {
                        title: 'Accordion',
                        to: 'ui-accordion',					
                    },
                    {
                        title: 'Alert',
                        to: 'ui-alert',					
                    },
                    {
                        title: 'Badge',
                        to: 'ui-badge',					
                    },
                    {
                        title: 'Button',
                        to: 'ui-button',					
                    },
                    {
                        title: 'Modal',
                        to: 'ui-modal',					
                    },
                    {
                        title: 'Button Group',
                        to: 'ui-button-group',					
                    },
                    {
                        title: 'List Group',
                        to: 'ui-list-group',					
                    },
                    {
                        title:'Media Object',
                        to:'ui-media-object'
                    },
                    {
                        title: 'Cards',
                        to: 'ui-card',					
                    },
                    {
                        title: 'Carousel',
                        to: 'ui-carousel',					
                    },
                    {
                        title: 'Dropdown',
                        to: 'ui-dropdown',					
                    },
                    {
                        title: 'Popover',
                        to: 'ui-popover',					
                    },
                    {
                        title: 'Progressbar',
                        to: 'ui-progressbar',					
                    },
                    {
                        title: 'Tab',
                        to: 'ui-tab',					
                    },
                    {
                        title: 'Typography',
                        to: 'ui-typography',					
                    },
                    {
                        title: 'Pagination',
                        to: 'ui-pagination',					
                    },
                    {
                        title: 'Grid',
                        to: 'ui-grid',					
                    },
                ]
            },
        //plugins
            {
                title:'Plugins',
                classsChange: 'mm-collapse',
                iconStyle : SVGICON.Plugins,
                content : [
                    {
                        title:'Select 2',
                        to: 'uc-select2',
                    },            
                    {
                        title:'Sweet Alert',
                        to: 'uc-sweetalert',
                    },
                    {
                        title:'Toastr',
                        to: 'uc-toastr',
                    },           
                    {
                        title:'Light Gallery',
                        to: 'uc-lightgallery',
                    },
                ]
            },
            //Widget
            {   
                title:'Widget',        
                iconStyle: SVGICON.Widget,
                classsChange: 'mm-collapse',
                // to: 'widget-basic',
                content : [
                    {
                        title:'Widget Card',
                        to:'widget-card'
                    },
                    {
                        title:'Widget Chart',
                        to:'widget-chart'
                    },
                    {
                        title:'Widget List',
                        to:'widget-list'
                    },
                ]
            },

            {
                title:'Icons',        
                classsChange : 'mm-collapse',
                iconStyle: SVGICON.PageSvg,
                content : [            
                    {
                        title:'SVG Icons',
                        to:'icon-svg'
                    },
                
                ],
            },
        ],
   },
    
   

     
    //Forms
    {
        title:'Forms',
        classsChange: 'mm-collapse',
        iconStyle: SVGICON.Forms,
        content : [
            {
                title:'Form Elements',
                to: 'form-element',
            },
            {
                title:'Wizard',
                to: 'form-wizard',
            },
            {
                title:'CkEditor',
                to: 'form-ckeditor',
            },
            {
                title:'Pickers',
                to: 'form-pickers',
            },
            {
                title:'Form Validate',
                to: 'form-validation',
            },

        ]
    },

   
    //Table
    {
        title:'Table',
        classsChange: 'mm-collapse',
        iconStyle: SVGICON.Table,
        content : [
            {
                title:'Table Filtering',
                to: 'table-filtering',
            },
            {
                title:'Table Sorting',
                to: 'table-sorting',
            },
            {
                title:'Bootstrap',
                to: 'table-bootstrap-basic',
            },
            // {
            //     title:'Tables',
            //     to: 'table-datatable-basic',
            // },
        ]
    },
    
    //Pages
    {
        title:'Pages',
        classsChange: 'mm-collapse',
        iconStyle: SVGICON.Pages,
        content : [                
            {
                title: 'Error 400',
                to : 'page-error-400',
            },
            {
                title: 'Error 403',
                to : 'page-error-403',
            },
            {
                title: 'Error 404',
                to : 'page-error-404',
            },
            {
                title: 'Error 500',
                to : 'page-error-500',
            },
            {
                title: 'Error 503',
                to : 'page-error-503',
            },
            {
                title:'Lock Screen',
                to: 'page-lock-screen',
            }                
        ]
    },
    
]

export const componentArray = [
    //Boosttrap
    {
        title: 'Bootstrap',	
        classsChange: 'mm-collapse',
        iconStyle: SVGICON.Bootstrap,
        number:"17",
        content: [
            {
                title: 'Accordion',
                to: 'ui-accordion',					
            },
            {
                title: 'Alert',
                to: 'ui-alert',					
            },
            {
                title: 'Badge',
                to: 'ui-badge',					
            },
            {
                title: 'Button',
                to: 'ui-button',					
            },
            {
                title: 'Modal',
                to: 'ui-modal',					
            },
            {
                title: 'Button Group',
                to: 'ui-button-group',					
            },
            {
                title: 'List Group',
                to: 'ui-list-group',					
            },
            {
                title:'Media Object',
                to:'ui-media-object'
            },
            {
                title: 'Cards',
                to: 'ui-card',					
            },
            {
                title: 'Carousel',
                to: 'ui-carousel',					
            },
            {
                title: 'Dropdown',
                to: 'ui-dropdown',					
            },
            {
                title: 'Popover',
                to: 'ui-popover',					
            },
            {
                title: 'Progressbar',
                to: 'ui-progressbar',					
            },
            {
                title: 'Tab',
                to: 'ui-tab',					
            },
            {
                title: 'Typography',
                to: 'ui-typography',					
            },
            {
                title: 'Pagination',
                to: 'ui-pagination',					
            },
            {
                title: 'Grid',
                to: 'ui-grid',					
            },
        ]
    },
    //plugins
    {
        title:'Plugins',
        classsChange: 'mm-collapse',
        iconStyle : SVGICON.Plugins,
        number:"04",
        content : [
            {
                title:'Select 2',
                to: 'uc-select2',
            },            
            {
                title:'Sweet Alert',
                to: 'uc-sweetalert',
            },
            {
                title:'Toastr',
                to: 'uc-toastr',
            },           
            {
                title:'Light Gallery',
                to: 'uc-lightgallery',
            },
        ]
    },
    //Widget
    {   
        title:'Widget',     
        classsChange: 'mm-collapse',   
        iconStyle: SVGICON.Widget,        
        number:"03",
        content : [
            {
                title:'Widget Card',
                to:'widget-card'
            },
            {
                title:'Widget Chart',
                to:'widget-chart'
            },
            {
                title:'Widget List',
                to:'widget-list'
            },
        ]
    },

    {
        title:'Svg Icons',        
        classsChange : 'mm-collapse',
        iconStyle: SVGICON.IconPage,
        number:"01",
        content : [            
            {
                title:'SVG Icons',
                to:'icon-svg'
            },
           
        ],
    },
];