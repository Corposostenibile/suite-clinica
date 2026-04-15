const STATUS_LABELS = {
    nuovo: 'Nuovo',
    in_triage: 'In triage',
    in_lavorazione: 'In lavorazione',
    in_attesa_utente: 'In attesa tua',
    da_testare: 'Da testare',
    risolto: 'Risolto',
    non_valido: 'Non valido',
};

export default function TicketStatusBadge({ status }) {
    const label = STATUS_LABELS[status] || status || 'Sconosciuto';
    return (
        <span className={`its-status-badge status-${status || 'sconosciuto'}`}>
            {label}
        </span>
    );
}
