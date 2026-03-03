import { useState, useEffect } from 'react';
import { Badge } from 'react-bootstrap';
import videoCallService from '../../services/videoCallService';

/**
 * Video call history component. Can be embedded in the client detail page.
 * Shows past calls with duration, status, and dates.
 */
export default function VideoCallHistory({ clienteId }) {
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    videoCallService.getHistory(clienteId)
      .then(({ data }) => setCalls(data.sessions || []))
      .catch(() => setCalls([]))
      .finally(() => setLoading(false));
  }, [clienteId]);

  const formatDuration = (seconds) => {
    if (!seconds) return '-';
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}m ${s}s`;
  };

  const statusBadge = (status) => {
    const variants = {
      waiting: 'warning',
      active: 'success',
      ended: 'secondary',
      cancelled: 'danger',
    };
    const labels = {
      waiting: 'In attesa',
      active: 'In corso',
      ended: 'Terminata',
      cancelled: 'Annullata',
    };
    return <Badge bg={variants[status] || 'secondary'}>{labels[status] || status}</Badge>;
  };

  if (loading) return <small className="text-muted">Caricamento storico videochiamate...</small>;
  if (!calls.length) return <small className="text-muted">Nessuna videochiamata registrata</small>;

  return (
    <div className="videocall-history">
      <table className="table table-sm table-hover mb-0">
        <thead>
          <tr>
            <th>Data</th>
            <th>Durata</th>
            <th>Stato</th>
          </tr>
        </thead>
        <tbody>
          {calls.map((call) => (
            <tr key={call.id}>
              <td>
                <small>
                  {call.created_at
                    ? new Date(call.created_at).toLocaleDateString('it-IT', {
                        day: '2-digit', month: 'short', year: 'numeric',
                        hour: '2-digit', minute: '2-digit',
                      })
                    : '-'}
                </small>
              </td>
              <td><small>{formatDuration(call.duration_seconds)}</small></td>
              <td>{statusBadge(call.status)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
