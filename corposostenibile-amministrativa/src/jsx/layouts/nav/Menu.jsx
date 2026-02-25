export const MenuList = [
  // Team Tickets
  {
    title: 'TEAM TICKETS',
    classsChange: 'menu-title',
  },
  {
    title: 'Dashboard',
    iconStyle: <i className="fas fa-ticket-alt" />,
    to: '/team-tickets',
  },
  {
    title: 'Analytics',
    iconStyle: <i className="fas fa-chart-bar" />,
    to: '/team-tickets/analytics',
  },
  // SOP Chatbot
  {
    title: 'SOP CHATBOT',
    classsChange: 'menu-title',
  },
  {
    title: 'Documenti',
    iconStyle: <i className="fas fa-file-alt" />,
    to: '/sop-documents',
  },
  {
    title: 'Chat Test',
    iconStyle: <i className="fas fa-robot" />,
    to: '/sop-chat',
  },
  {
    title: 'AMMINISTRAZIONE',
    classsChange: 'menu-title',
    adminOnly: true,
  },
  {
    title: 'Notifiche Push',
    iconStyle: <i className="fas fa-bell" />,
    to: '/admin/push-notifications',
    adminOnly: true,
  },
];
