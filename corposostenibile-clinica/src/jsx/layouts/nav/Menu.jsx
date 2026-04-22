import { SVGICON } from "../../constant/theme.jsx";

export const MenuList = [
    // ==================== TOP SECTION ====================
    {
        title: 'MAIN MENU',
        classsChange: 'menu-title',
        extraclass: "first"
    },
    // Dashboard
    {
        title: 'Dashboard',
        iconStyle: SVGICON.Dashboard,
        to: 'welcome',
    },
    // Calendario
    {
        title: 'Calendario',
        iconStyle: SVGICON.Calendar,
        to: 'calendario',
    },
    // {
    //     title: 'Libreria Loom',
    //     iconStyle: SVGICON.Loom,
    //     to: 'loom-library',
    // },
    // Chat
    {
        title: 'Chat',
        iconStyle: SVGICON.Chat,
        to: 'chat',
    },
    // Task
    {
        title: 'Task',
        iconStyle: SVGICON.Task,
        to: 'task',
    },
    // Formazione
    {
        title: 'Formazione',
        iconStyle: SVGICON.Learning,
        to: 'formazione',
    },

    // ==================== CLIENTI SECTION ====================
    {
        title: 'CLIENTI',
        classsChange: 'menu-title'
    },
    // Pazienti
    {
        title: 'Pazienti',
        iconStyle: SVGICON.Health,
        to: 'clienti-lista',
    },
    // Assegnazioni dashboard madre (Sales GHL + Storico HM)
    {
        title: 'Assegnazioni',
        iconStyle: SVGICON.PeopleArrow,
        to: 'admin/assegnazioni-dashboard',
    },
    // Assegnazioni v1 (Old Suite - TEMPORANEO)
    {
        title: 'Assegnazioni v1',
        iconStyle: SVGICON.PeopleArrow,
        to: 'assegnazioni-old-suite',
    },
    // Check
    {
        title: 'Check',
        iconStyle: SVGICON.Check,
        to: 'check-azienda',
    },

    // ==================== TEAM SECTION ====================
    {
        title: 'TEAM',
        classsChange: 'menu-title'
    },
    // Profilo - il titolo viene sostituito dinamicamente con il nome utente nel SideBar
    {
        title: 'Profilo',
        iconStyle: SVGICON.Profile,
        to: 'profilo',
        isProfile: true, // Flag per identificare questo item come profilo utente
    },
    // Team - Gestione Team per Specializzazione
    {
        title: 'Team',
        iconStyle: SVGICON.Team,
        to: 'teams',
    },
    // Professionisti
    {
        title: 'Professionisti',
        iconStyle: SVGICON.Users,
        to: 'team-lista',
    },
    // Quality
    {
        title: 'Quality',
        iconStyle: SVGICON.Quality,
        to: 'quality',
    },
    // In Prova
    {
        title: 'In Prova',
        iconStyle: SVGICON.Trial,
        to: 'in-prova',
    },
];
