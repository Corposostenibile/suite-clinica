import { useState, useEffect, useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, Legend,
} from 'recharts';
import api from '../services/api';

const COLORS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6'];

const MONTHS = [
  'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
  'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre',
];

const MONTH_ABBR_MAP = {
  'Jan': 'Gennaio', 'Feb': 'Febbraio', 'Mar': 'Marzo', 'Apr': 'Aprile',
  'May': 'Maggio', 'Jun': 'Giugno', 'Jul': 'Luglio', 'Aug': 'Agosto',
  'Sep': 'Settembre', 'Oct': 'Ottobre', 'Nov': 'Novembre', 'Dec': 'Dicembre',
};

// Parser for "Utenti" CSV (Respond.io user performance logs)
function parseUtentiCSV(text) {
  const lines = text.trim().split('\n');
  if (lines.length < 2) return [];

  const headers = lines[0].split(',').map(h => h.replace(/"/g, '').trim());
  const utenteIdx = headers.indexOf('Utente');
  const messaggiIdx = headers.indexOf('Messaggi Inviati');

  if (utenteIdx === -1 || messaggiIdx === -1) return [];

  const results = [];
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(',').map(c => c.replace(/"/g, '').trim());
    if (cols.length > Math.max(utenteIdx, messaggiIdx)) {
      const utente = cols[utenteIdx];
      const messaggi = parseInt(cols[messaggiIdx], 10);
      if (utente && !isNaN(messaggi)) {
        results.push({ utente, messaggi_inviati: messaggi });
      }
    }
  }
  return results;
}

// Parser for "Contatti" CSV (bar chart daily contacts)
function parseContattiCSV(text) {
  const lines = text.replace(/^\uFEFF/, '').trim().split('\n');
  if (lines.length < 2) return null;

  const headers = lines[0].split(',').map(h => h.trim());
  const users = headers.slice(1); // skip "category"

  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(',').map(c => c.trim());
    if (cols.length < 2) continue;
    const dayMatch = cols[0].match(/^(\d+)/);
    if (!dayMatch) continue;
    const giorno = parseInt(dayMatch[1], 10);
    const utenti = {};
    for (let j = 1; j < cols.length && j < headers.length; j++) {
      utenti[users[j - 1]] = parseInt(cols[j], 10) || 0;
    }
    rows.push({ giorno, utenti });
  }

  return { users, rows };
}

// Parser for "Funnel" CSV (lifecycle journey breakdown)
function parseFunnelCSV(text) {
  const lines = text.replace(/^\uFEFF/, '').trim().split('\n');
  if (lines.length < 2) return [];

  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    // Handle quoted CSV fields
    const cols = [];
    let current = '';
    let inQuotes = false;
    for (const ch of lines[i]) {
      if (ch === '"') { inQuotes = !inQuotes; continue; }
      if (ch === ',' && !inQuotes) { cols.push(current.trim()); current = ''; continue; }
      current += ch;
    }
    cols.push(current.trim());

    if (cols.length < 8) continue;
    const fase = cols[0];
    if (!fase) continue;

    const parsePercent = (s) => { const n = parseFloat(s.replace('%', '').replace(',', '.')); return isNaN(n) ? 0 : n; };
    const parseNum = (s) => { const n = parseInt(s, 10); return isNaN(n) ? 0 : n; };

    rows.push({
      fase,
      tasso_conversione: parsePercent(cols[1]),
      tempo_medio_fase: parseFloat(cols[2]) || 0,
      tasso_abbandono: parsePercent(cols[3]),
      cold: parseNum(cols[4]),
      non_in_target: parseNum(cols[5]),
      prenotato_non_in_target: parseNum(cols[6]),
      under: parseNum(cols[7]),
    });
  }
  return rows;
}

function ContactsTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: '#fff',
      borderRadius: '12px',
      boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
      padding: '12px 16px',
      border: 'none',
    }}>
      <p style={{ margin: 0, fontWeight: 600, color: '#1e293b', fontSize: '13px' }}>Giorno {label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ margin: '3px 0 0', color: p.color, fontSize: '12px' }}>
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  );
}

function MessaggiTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const data = payload[0].payload;
  const value = data.messaggi ?? data.totale ?? 0;
  const labelText = data.messaggi != null ? 'messaggi' : 'contatti';
  return (
    <div style={{
      background: '#fff',
      borderRadius: '12px',
      boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
      padding: '12px 16px',
      border: 'none',
    }}>
      <p style={{ margin: 0, fontWeight: 600, color: '#1e293b', fontSize: '14px' }}>{data.utente}</p>
      <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '13px' }}>
        {value.toLocaleString()} {labelText}
      </p>
    </div>
  );
}

function AppointmentSetting() {
  const [activeTab, setActiveTab] = useState('contatti');

  // Utenti state
  const [utentiData, setUtentiData] = useState([]);
  const [utentiLoading, setUtentiLoading] = useState(true);
  const [utentiViewIndex, setUtentiViewIndex] = useState(0);

  // Contatti state
  const [contattiData, setContattiData] = useState([]);
  const [contattiLoading, setContattiLoading] = useState(true);
  const [contattiViewIndex, setContattiViewIndex] = useState(0);

  // Funnel state
  const [funnelData, setFunnelData] = useState([]);
  const [funnelLoading, setFunnelLoading] = useState(true);
  const [funnelViewIndex, setFunnelViewIndex] = useState(0);

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState('');
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [uploadMessage, setUploadMessage] = useState(null);

  // Fetch data
  const fetchUtenti = useCallback(async () => {
    try {
      const res = await api.get('/appointment-setting/messages');
      if (res.data.success) setUtentiData(res.data.data);
    } catch (err) { console.error('Error fetching utenti:', err); }
    finally { setUtentiLoading(false); }
  }, []);

  const fetchContatti = useCallback(async () => {
    try {
      const res = await api.get('/appointment-setting/contacts');
      if (res.data.success) setContattiData(res.data.data);
    } catch (err) { console.error('Error fetching contatti:', err); }
    finally { setContattiLoading(false); }
  }, []);

  const fetchFunnel = useCallback(async () => {
    try {
      const res = await api.get('/appointment-setting/funnel');
      if (res.data.success) setFunnelData(res.data.data);
    } catch (err) { console.error('Error fetching funnel:', err); }
    finally { setFunnelLoading(false); }
  }, []);

  useEffect(() => { fetchUtenti(); fetchContatti(); fetchFunnel(); }, [fetchUtenti, fetchContatti, fetchFunnel]);

  // Sorted months for Utenti
  const utentiMonths = [...new Set(
    utentiData.map(d => `${d.mese} ${d.anno}`)
  )].sort((a, b) => {
    const [mA, yA] = a.split(' ');
    const [mB, yB] = b.split(' ');
    return (parseInt(yA) - parseInt(yB)) || (MONTHS.indexOf(mA) - MONTHS.indexOf(mB));
  });

  // Sorted months for Contatti
  const contattiMonths = [...new Set(
    contattiData.map(d => `${d.mese} ${d.anno}`)
  )].sort((a, b) => {
    const [mA, yA] = a.split(' ');
    const [mB, yB] = b.split(' ');
    return (parseInt(yA) - parseInt(yB)) || (MONTHS.indexOf(mA) - MONTHS.indexOf(mB));
  });

  // Sorted months for Funnel
  const funnelMonths = [...new Set(
    funnelData.map(d => `${d.mese} ${d.anno}`)
  )].sort((a, b) => {
    const [mA, yA] = a.split(' ');
    const [mB, yB] = b.split(' ');
    return (parseInt(yA) - parseInt(yB)) || (MONTHS.indexOf(mA) - MONTHS.indexOf(mB));
  });

  // Navigate to latest month on load
  useEffect(() => {
    if (utentiMonths.length > 0 && utentiViewIndex === 0) setUtentiViewIndex(utentiMonths.length - 1);
  }, [utentiMonths.length]);

  useEffect(() => {
    if (contattiMonths.length > 0 && contattiViewIndex === 0) setContattiViewIndex(contattiMonths.length - 1);
  }, [contattiMonths.length]);

  useEffect(() => {
    if (funnelMonths.length > 0 && funnelViewIndex === 0) setFunnelViewIndex(funnelMonths.length - 1);
  }, [funnelMonths.length]);

  // Upload handler
  const handleFileUpload = useCallback(async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!selectedMonth) {
      setUploadMessage({ type: 'error', text: 'Seleziona un mese prima di caricare il CSV.' });
      e.target.value = '';
      return;
    }

    const reader = new FileReader();
    reader.onload = async (evt) => {
      const text = evt.target.result;

      if (activeTab === 'utenti') {
        const parsed = parseUtentiCSV(text);
        if (!parsed.length) {
          setUploadMessage({ type: 'error', text: 'CSV non valido. Colonne richieste: Utente, Messaggi Inviati.' });
          return;
        }
        try {
          const res = await api.post('/appointment-setting/messages', {
            mese: selectedMonth, anno: selectedYear, utenti: parsed,
          });
          if (res.data.success) {
            setUploadMessage({ type: 'success', text: `Salvati ${res.data.saved} utenti per ${selectedMonth} ${selectedYear}.` });
            await fetchUtenti();
            setTimeout(() => setShowModal(false), 800);
          }
        } catch { setUploadMessage({ type: 'error', text: 'Errore nel salvataggio.' }); }
      } else if (activeTab === 'contatti') {
        const parsed = parseContattiCSV(text);
        if (!parsed || !parsed.rows.length) {
          setUploadMessage({ type: 'error', text: 'CSV non valido. Formato richiesto: category, utente1, utente2, ...' });
          return;
        }
        try {
          const res = await api.post('/appointment-setting/contacts', {
            mese: selectedMonth, anno: selectedYear, rows: parsed.rows,
          });
          if (res.data.success) {
            setUploadMessage({ type: 'success', text: `Salvati ${res.data.saved} record per ${selectedMonth} ${selectedYear}.` });
            await fetchContatti();
            setTimeout(() => setShowModal(false), 800);
          }
        } catch { setUploadMessage({ type: 'error', text: 'Errore nel salvataggio.' }); }
      } else {
        const parsed = parseFunnelCSV(text);
        if (!parsed.length) {
          setUploadMessage({ type: 'error', text: 'CSV non valido. Formato lifecycle journey breakdown richiesto.' });
          return;
        }
        try {
          const res = await api.post('/appointment-setting/funnel', {
            mese: selectedMonth, anno: selectedYear, rows: parsed,
          });
          if (res.data.success) {
            setUploadMessage({ type: 'success', text: `Salvate ${res.data.saved} fasi per ${selectedMonth} ${selectedYear}.` });
            await fetchFunnel();
            setTimeout(() => setShowModal(false), 800);
          }
        } catch { setUploadMessage({ type: 'error', text: 'Errore nel salvataggio.' }); }
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  }, [activeTab, selectedMonth, selectedYear, fetchUtenti, fetchContatti, fetchFunnel]);

  // Utenti chart data
  const currentUtentiMonth = utentiMonths[utentiViewIndex] || '';
  const utentiChartData = utentiData
    .filter(d => `${d.mese} ${d.anno}` === currentUtentiMonth)
    .sort((a, b) => b.messaggi_inviati - a.messaggi_inviati)
    .map(d => ({ utente: d.utente, messaggi: d.messaggi_inviati }));

  const totalMessages = utentiChartData.reduce((sum, d) => sum + d.messaggi, 0);
  const topSender = utentiChartData[0];

  // Contatti chart data
  const currentContattiMonth = contattiMonths[contattiViewIndex] || '';
  const contattiFiltered = contattiData.filter(d => `${d.mese} ${d.anno}` === currentContattiMonth);
  const contattiUsers = [...new Set(contattiFiltered.map(d => d.utente))];
  const contattiChartData = [];
  const days = [...new Set(contattiFiltered.map(d => d.giorno))].sort((a, b) => a - b);
  for (const day of days) {
    const row = { giorno: day };
    for (const user of contattiUsers) {
      const entry = contattiFiltered.find(d => d.giorno === day && d.utente === user);
      row[user] = entry ? entry.contatti : 0;
    }
    contattiChartData.push(row);
  }

  const totalContatti = contattiFiltered.reduce((sum, d) => sum + d.contatti, 0);
  const contattiPerCanale = contattiUsers.map(user => ({
    utente: user,
    totale: contattiFiltered.filter(d => d.utente === user).reduce((s, d) => s + d.contatti, 0),
  })).sort((a, b) => b.totale - a.totale);
  const topContatti = contattiPerCanale.length > 0 ? { user: contattiPerCanale[0].utente, sum: contattiPerCanale[0].totale } : { user: '', sum: 0 };

  // Funnel chart data
  const currentFunnelMonth = funnelMonths[funnelViewIndex] || '';
  const funnelFiltered = funnelData.filter(d => `${d.mese} ${d.anno}` === currentFunnelMonth);

  const currentYear = new Date().getFullYear();
  const years = [currentYear - 1, currentYear, currentYear + 1];

  const loading = activeTab === 'utenti' ? utentiLoading : activeTab === 'funnel' ? funnelLoading : contattiLoading;
  if (loading) {
    return (
      <div className="container-fluid p-0">
        <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '400px' }}>
          <div className="spinner-border text-primary" role="status" />
        </div>
      </div>
    );
  }

  const sortedMonths = activeTab === 'utenti' ? utentiMonths : activeTab === 'funnel' ? funnelMonths : contattiMonths;
  const viewIndex = activeTab === 'utenti' ? utentiViewIndex : activeTab === 'funnel' ? funnelViewIndex : contattiViewIndex;
  const setViewIndex = activeTab === 'utenti' ? setUtentiViewIndex : activeTab === 'funnel' ? setFunnelViewIndex : setContattiViewIndex;
  const canGoPrev = viewIndex > 0;
  const canGoNext = viewIndex < sortedMonths.length - 1;
  const currentMonthKey = sortedMonths[viewIndex] || '';

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h4 className="mb-1" style={{ fontWeight: 700, color: '#1e293b' }}>Appointment Setting</h4>
          <p className="text-muted mb-0">Dashboard Performance</p>
        </div>
        <button
          className="btn d-flex align-items-center gap-2"
          onClick={() => { setShowModal(true); setUploadMessage(null); }}
          style={{
            background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
            color: '#fff',
            borderRadius: '12px',
            padding: '10px 20px',
            fontWeight: 500,
            border: 'none',
            boxShadow: '0 4px 12px rgba(99,102,241,0.3)',
          }}
        >
          <i className="ri-upload-2-line"></i>
          Carica CSV
        </button>
      </div>

      {/* Tabs */}
      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '12px' }}>
        <div className="card-body p-2">
          <div className="d-flex flex-wrap gap-2">
            {[
              { key: 'contatti', label: 'Influencer', icon: 'ri-contacts-book-line' },
              { key: 'funnel', label: 'Funnel', icon: 'ri-filter-line' },
              { key: 'utenti', label: 'Utenti', icon: 'ri-user-line' },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className="btn"
                style={{
                  borderRadius: '8px',
                  padding: '10px 20px',
                  background: activeTab === tab.key
                    ? 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)'
                    : 'transparent',
                  color: activeTab === tab.key ? 'white' : '#64748b',
                  fontWeight: activeTab === tab.key ? 600 : 500,
                  fontSize: '14px',
                  border: 'none',
                  transition: 'all 0.2s ease',
                }}
              >
                <i className={`${tab.icon} me-2`}></i>
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      {sortedMonths.length > 0 && (
        <div className="row g-3 mb-4">
          {activeTab === 'utenti' ? (
            <>
              <div className="col-sm-6 col-xl-3">
                <KPICard icon="ri-message-3-line" iconBg="#ede9fe" iconColor="#6366f1"
                  value={totalMessages.toLocaleString()} label="Messaggi Totali" />
              </div>
              <div className="col-sm-6 col-xl-3">
                <KPICard icon="ri-team-line" iconBg="#dcfce7" iconColor="#16a34a"
                  value={utentiChartData.length} label="Utenti Attivi" />
              </div>
              <div className="col-sm-6 col-xl-3">
                <KPICard icon="ri-bar-chart-line" iconBg="#fef3c7" iconColor="#d97706"
                  value={utentiChartData.length > 0 ? Math.round(totalMessages / utentiChartData.length).toLocaleString() : 0} label="Media per Utente" />
              </div>
              <div className="col-sm-6 col-xl-3">
                <KPICard icon="ri-trophy-line" iconBg="#fce7f3" iconColor="#ec4899"
                  value={topSender ? topSender.utente.split(' ')[0] : '—'} label="Top Performer" small />
              </div>
            </>
          ) : activeTab === 'funnel' ? (
            <>
              <div className="col-sm-6 col-xl-3">
                <KPICard icon="ri-filter-line" iconBg="#ede9fe" iconColor="#6366f1"
                  value={funnelFiltered.length} label="Fasi del Funnel" />
              </div>
              <div className="col-sm-6 col-xl-3">
                <KPICard icon="ri-arrow-up-circle-line" iconBg="#dcfce7" iconColor="#16a34a"
                  value={funnelFiltered.length > 0 ? `${(funnelFiltered.reduce((s, d) => s + d.tasso_conversione, 0) / funnelFiltered.length).toFixed(1)}%` : '—'} label="Media Conversione" />
              </div>
              <div className="col-sm-6 col-xl-3">
                <KPICard icon="ri-arrow-down-circle-line" iconBg="#fef3c7" iconColor="#d97706"
                  value={funnelFiltered.length > 0 ? `${(funnelFiltered.reduce((s, d) => s + d.tasso_abbandono, 0) / funnelFiltered.length).toFixed(1)}%` : '—'} label="Media Abbandono" />
              </div>
              <div className="col-sm-6 col-xl-3">
                <KPICard icon="ri-ice-cream-line" iconBg="#fce7f3" iconColor="#ec4899"
                  value={funnelFiltered.reduce((s, d) => s + d.cold, 0)} label="Totale Cold" />
              </div>
            </>
          ) : (
            <>
              <div className="col-sm-6 col-xl-6">
                <KPICard icon="ri-contacts-book-line" iconBg="#ede9fe" iconColor="#6366f1"
                  value={totalContatti.toLocaleString()} label="Contatti Totali" />
              </div>
              <div className="col-sm-6 col-xl-6">
                <KPICard icon="ri-trophy-line" iconBg="#fce7f3" iconColor="#ec4899"
                  value={topContatti.user ? topContatti.user.split(' ')[0] : '—'} label="Top Performer" small />
              </div>
            </>
          )}
        </div>
      )}

      {/* Chart Card */}
      {sortedMonths.length > 0 ? (
        <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
          <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
            <div className="d-flex align-items-center justify-content-between">
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className={`${activeTab === 'contatti' ? 'ri-contacts-book-line' : activeTab === 'funnel' ? 'ri-filter-line' : 'ri-bar-chart-grouped-line'} me-2 text-primary`}></i>
                {activeTab === 'contatti' ? 'Contatti Giornalieri Per Influencer' : activeTab === 'funnel' ? 'Tasso di Conversione per Fase' : 'Messaggi Inviati per Utente'}
              </h6>
              <div className="d-flex align-items-center gap-2">
                <NavButton direction="left" disabled={!canGoPrev} onClick={() => setViewIndex(i => i - 1)} />
                <span style={{ fontWeight: 600, color: '#1e293b', fontSize: '14px', minWidth: '130px', textAlign: 'center' }}>
                  {currentMonthKey}
                </span>
                <NavButton direction="right" disabled={!canGoNext} onClick={() => setViewIndex(i => i + 1)} />
              </div>
            </div>
          </div>
          <div className="card-body px-4 pb-4 pt-2">
            {activeTab === 'utenti' ? (
              <ResponsiveContainer width="100%" height={380}>
                <BarChart data={utentiChartData} margin={{ top: 10, right: 10, left: 0, bottom: 50 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="utente" angle={-20} textAnchor="end" height={70}
                    tick={{ fontSize: 12, fill: '#64748b' }} axisLine={{ stroke: '#e2e8f0' }} tickLine={false} />
                  <YAxis tick={{ fontSize: 12, fill: '#94a3b8' }} axisLine={false} tickLine={false}
                    tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} />
                  <Tooltip content={<MessaggiTooltip />} cursor={{ fill: 'rgba(99,102,241,0.04)' }} />
                  <Bar dataKey="messaggi" radius={[8, 8, 0, 0]} maxBarSize={60}>
                    {utentiChartData.map((_, idx) => (
                      <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : activeTab === 'funnel' ? (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={funnelFiltered} layout="vertical" margin={{ top: 10, right: 30, left: 20, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 12, fill: '#94a3b8' }} axisLine={false} tickLine={false}
                    tickFormatter={(v) => `${v}%`} domain={[0, 100]} />
                  <YAxis type="category" dataKey="fase" width={140}
                    tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
                  <Tooltip formatter={(v) => `${v.toFixed(1)}%`} cursor={{ fill: 'rgba(99,102,241,0.04)' }} />
                  <Bar dataKey="tasso_conversione" name="Conversione" radius={[0, 8, 8, 0]} maxBarSize={40}>
                    {funnelFiltered.map((_, idx) => (
                      <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <ResponsiveContainer width="100%" height={380}>
                <BarChart data={contattiChartData} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="giorno" tick={{ fontSize: 12, fill: '#64748b' }}
                    axisLine={{ stroke: '#e2e8f0' }} tickLine={false} />
                  <YAxis tick={{ fontSize: 12, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <Tooltip content={<ContactsTooltip />} cursor={{ fill: 'rgba(99,102,241,0.04)' }} />
                  <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '12px' }} />
                  {contattiUsers.map((user, idx) => (
                    <Bar key={user} dataKey={user} stackId="a" fill={COLORS[idx % COLORS.length]}
                      radius={idx === contattiUsers.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0]} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      ) : (
        <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
          <div className="card-body text-center py-5">
            <div className="d-flex align-items-center justify-content-center rounded-circle mx-auto mb-3"
              style={{ width: '80px', height: '80px', background: '#f1f5f9' }}>
              <i className="ri-bar-chart-2-line" style={{ fontSize: '32px', color: '#94a3b8' }}></i>
            </div>
            <h5 className="mb-2" style={{ color: '#475569', fontWeight: 600 }}>Nessun dato disponibile</h5>
            <p className="text-muted mb-0">Usa il bottone "Carica CSV" per importare i dati da Respond.io</p>
          </div>
        </div>
      )}

      {/* Totale per Canale Chart */}
      {activeTab === 'contatti' && contattiPerCanale.length > 0 && (
        <div className="card border-0 shadow-sm mt-4" style={{ borderRadius: '16px' }}>
          <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
              <i className="ri-pie-chart-line me-2 text-primary"></i>
              Totale Mensile per Influencer — {currentContattiMonth}
            </h6>
          </div>
          <div className="card-body px-4 pb-4 pt-2">
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={contattiPerCanale} margin={{ top: 10, right: 10, left: 0, bottom: 50 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="utente" angle={-20} textAnchor="end" height={70}
                  tick={{ fontSize: 12, fill: '#64748b' }} axisLine={{ stroke: '#e2e8f0' }} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: '#94a3b8' }} axisLine={false} tickLine={false}
                  tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v} />
                <Tooltip content={<MessaggiTooltip />} cursor={{ fill: 'rgba(99,102,241,0.04)' }} />
                <Bar dataKey="totale" radius={[8, 8, 0, 0]} maxBarSize={60}>
                  {contattiPerCanale.map((_, idx) => (
                    <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Funnel extra charts */}
      {activeTab === 'funnel' && funnelFiltered.length > 0 && (
        <>
          {/* Tasso di Abbandono */}
          <div className="card border-0 shadow-sm mt-4" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-arrow-down-circle-line me-2 text-warning"></i>
                Tasso di Abbandono per Fase
              </h6>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={funnelFiltered} layout="vertical" margin={{ top: 10, right: 30, left: 20, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 12, fill: '#94a3b8' }} axisLine={false} tickLine={false}
                    tickFormatter={(v) => `${v}%`} />
                  <YAxis type="category" dataKey="fase" width={140}
                    tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
                  <Tooltip formatter={(v) => `${v.toFixed(2)}%`} cursor={{ fill: 'rgba(239,68,68,0.04)' }} />
                  <Bar dataKey="tasso_abbandono" name="Abbandono" radius={[0, 8, 8, 0]} maxBarSize={35} fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Breakdown per Fase */}
          <div className="card border-0 shadow-sm mt-4" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-bar-chart-horizontal-line me-2 text-primary"></i>
                Breakdown per Fase
              </h6>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={funnelFiltered} margin={{ top: 10, right: 10, left: 0, bottom: 50 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="fase" angle={-15} textAnchor="end" height={70}
                    tick={{ fontSize: 11, fill: '#64748b' }} axisLine={{ stroke: '#e2e8f0' }} tickLine={false} />
                  <YAxis tick={{ fontSize: 12, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <Tooltip cursor={{ fill: 'rgba(99,102,241,0.04)' }} />
                  <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '12px' }} />
                  <Bar dataKey="cold" name="Cold" stackId="a" fill="#6366f1" />
                  <Bar dataKey="non_in_target" name="Non in Target" stackId="a" fill="#06b6d4" />
                  <Bar dataKey="prenotato_non_in_target" name="Prenotato Non In Target" stackId="a" fill="#f59e0b" />
                  <Bar dataKey="under" name="Under" stackId="a" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Tempo Medio in Fase */}
          <div className="card border-0 shadow-sm mt-4" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-time-line me-2 text-success"></i>
                Tempo Medio in Fase (giorni)
              </h6>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={funnelFiltered.map(d => ({ ...d, giorni: Math.round(d.tempo_medio_fase / 86400) }))}
                  layout="vertical" margin={{ top: 10, right: 30, left: 20, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 12, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="fase" width={140}
                    tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
                  <Tooltip formatter={(v) => `${v} giorni`} cursor={{ fill: 'rgba(16,185,129,0.04)' }} />
                  <Bar dataKey="giorni" name="Giorni" radius={[0, 8, 8, 0]} maxBarSize={35} fill="#10b981" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}

      {/* Upload Modal */}
      {showModal && (
        <>
          <div className="modal-backdrop fade show" style={{ zIndex: 1050 }} onClick={() => setShowModal(false)}></div>
          <div className="modal fade show d-block" style={{ zIndex: 1055 }} tabIndex="-1" onClick={() => setShowModal(false)}>
            <div className="modal-dialog modal-dialog-centered" onClick={e => e.stopPropagation()}>
              <div className="modal-content border-0" style={{ borderRadius: '16px', boxShadow: '0 20px 60px rgba(0,0,0,0.15)' }}>
                <div className="modal-header border-0 px-4 pt-4 pb-0">
                  <div>
                    <h5 className="modal-title fw-bold" style={{ color: '#1e293b' }}>Carica CSV Respond.io</h5>
                    <p className="text-muted small mb-0 mt-1">
                      {activeTab === 'contatti' ? 'Importa contatti giornalieri' : activeTab === 'funnel' ? 'Importa lifecycle journey breakdown' : 'Importa performance messaggi'}
                    </p>
                  </div>
                  <button type="button" className="btn-close" onClick={() => setShowModal(false)}></button>
                </div>
                <div className="modal-body px-4 py-4">
                  <div className="row g-3 mb-3">
                    <div className="col-7">
                      <label className="form-label small fw-medium" style={{ color: '#475569' }}>Mese</label>
                      <select className="form-select" value={selectedMonth}
                        onChange={(e) => setSelectedMonth(e.target.value)}
                        style={{ borderRadius: '10px', borderColor: '#e2e8f0' }}>
                        <option value="">Seleziona mese...</option>
                        {MONTHS.map(m => <option key={m} value={m}>{m}</option>)}
                      </select>
                    </div>
                    <div className="col-5">
                      <label className="form-label small fw-medium" style={{ color: '#475569' }}>Anno</label>
                      <select className="form-select" value={selectedYear}
                        onChange={(e) => setSelectedYear(parseInt(e.target.value))}
                        style={{ borderRadius: '10px', borderColor: '#e2e8f0' }}>
                        {years.map(y => <option key={y} value={y}>{y}</option>)}
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="form-label small fw-medium" style={{ color: '#475569' }}>File CSV</label>
                    <input type="file" className="form-control" accept=".csv"
                      onChange={handleFileUpload}
                      style={{ borderRadius: '10px', borderColor: '#e2e8f0' }} />
                  </div>
                  {uploadMessage && (
                    <div className={`alert ${uploadMessage.type === 'error' ? 'alert-danger' : 'alert-success'} py-2 mt-3 mb-0`}
                      style={{ borderRadius: '10px', fontSize: '14px' }}>
                      {uploadMessage.text}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function KPICard({ icon, iconBg, iconColor, value, label, small }) {
  return (
    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
      <div className="card-body py-3">
        <div className="d-flex align-items-center gap-3">
          <div className="d-flex align-items-center justify-content-center rounded-circle"
            style={{ width: '48px', height: '48px', background: iconBg, flexShrink: 0 }}>
            <i className={icon} style={{ color: iconColor, fontSize: '20px' }}></i>
          </div>
          <div>
            <h4 className="mb-0 fw-bold" style={{ color: '#1e293b', fontSize: small ? '16px' : undefined }}>
              {value}
            </h4>
            <span className="text-muted small">{label}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function NavButton({ direction, disabled, onClick }) {
  return (
    <button
      className="btn btn-sm d-flex align-items-center justify-content-center"
      disabled={disabled}
      onClick={onClick}
      style={{
        width: '36px',
        height: '36px',
        borderRadius: '10px',
        border: '1px solid #e2e8f0',
        background: disabled ? '#f1f5f9' : '#f8fafc',
        color: disabled ? '#cbd5e1' : '#475569',
        transition: 'all 0.15s',
      }}
    >
      <i className={`ri-arrow-${direction}-s-line`} style={{ fontSize: '18px' }}></i>
    </button>
  );
}

export default AppointmentSetting;
