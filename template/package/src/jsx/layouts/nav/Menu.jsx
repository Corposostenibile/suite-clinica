import { SVGICON } from "../../constant/theme";

export const MenuList = [
    //Content
    {
        title: 'MAIN MENU',
        classsChange: 'menu-title',
        extraclass: "first"
    },
    //Dashboard
    {
        title: 'Dashboard',	
        classsChange: 'mm-collapse',		
        iconStyle: SVGICON.Dashboard,
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

    //Content
    {
        title: 'CMS',
        classsChange: 'menu-title'
    },
    {
        title:'CMS',
        // update : 'New',
        classsChange : 'mm-collapse',
        iconStyle: SVGICON.CmsSvg,
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

     //Content
    {
        title: 'APPS',
        classsChange: 'menu-title'
    },
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
                title: 'Post Details',
                to: 'post-details'
            },
            {
                title: 'Email',                
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

    //Content
    {
        title: 'COMPONENTS',
        classsChange: 'menu-title'
    },
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
        //classsChange: 'mm-collapse',
        iconStyle: SVGICON.Widget,
        to: 'widget-basic',
    },

    {
        title:'Icons',        
        classsChange : 'mm-collapse',
        iconStyle: SVGICON.PageSvg,
        content : [
            
            {
                title:'SVG Icons',
                to:'svg-icons'
            },
            
        ],
    },

     //Content
     {
        title: 'FORMS',
        classsChange: 'menu-title'
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

    //Content
    {
        title: 'TABLE',
        classsChange: 'menu-title'
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
    //Content
    {
        title: 'EXTRA',
        classsChange: 'menu-title'
    },
    //Pages
    {
        title:'Pages',
        classsChange: 'mm-collapse',
        iconStyle: SVGICON.Pages,
        content : [
            {
                title:'Error',
                hasMenu : true,
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
                ],
            },
            {
                title:'Lock Screen',
                to: 'page-lock-screen',
            },

        ]
    },
    
]