import { useState, useMemo } from 'react';
import {
  ResponsiveContainer, AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts';

const ACCENT = '#25B36A';

const PERIOD_FILTERS = [
  { key: '1m', label: '1M', months: 1 },
  { key: '3m', label: '3M', months: 3 },
  { key: '6m', label: '6M', months: 6 },
  { key: 'all', label: 'Tutto', months: null },
];

const WELLNESS_METRICS = [
  { key: 'energy_rating', label: 'Energia', color: '#FF6B35' },
  { key: 'sleep_rating', label: 'Sonno', color: '#6C5CE7' },
  { key: 'mood_rating', label: 'Umore', color: '#00B894' },
  { key: 'strength_rating', label: 'Forza', color: '#E17055' },
  { key: 'motivation_rating', label: 'Motivazione', color: '#0984E3' },
  { key: 'digestion_rating', label: 'Digestione', color: '#FDCB6E' },
  { key: 'hunger_rating', label: 'Fame', color: '#E84393' },
];

const DCA_METRICS = [
  { key: 'mood_balance_rating', label: 'Equilibrio Umore', color: '#6C5CE7' },
  { key: 'food_plan_serenity', label: 'Serenità Alimentare', color: '#00B894' },
  { key: 'food_weight_worry', label: 'Preoccupazione Peso', color: '#E17055' },
  { key: 'emotional_eating', label: 'Eating Emotivo', color: '#E84393' },
  { key: 'body_comfort', label: 'Comfort Corporeo', color: '#0984E3' },
  { key: 'sleep_satisfaction', label: 'Soddisfazione Sonno', color: '#FDCB6E' },
  { key: 'motivation_level', label: 'Motivazione', color: '#FF6B35' },
  { key: 'self_compassion', label: 'Auto-compassione', color: '#A29BFE' },
  { key: 'long_term_sustainability', label: 'Sostenibilità', color: '#55EFC4' },
];

const formatDate = (isoStr) => {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  return d.toLocaleDateString('it-IT', { day: '2-digit', month: 'short' });
};

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: '#fff', border: '1px solid #e0e0e0', borderRadius: 10,
      padding: '10px 14px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
      fontSize: 13,
    }}>
      <div style={{ fontWeight: 600, marginBottom: 6, color: '#333' }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: p.color, display: 'inline-block' }} />
          <span style={{ color: '#666' }}>{p.name}:</span>
          <span style={{ fontWeight: 600, color: '#333' }}>{p.value != null ? p.value : '—'}</span>
        </div>
      ))}
    </div>
  );
};

const cardStyle = {
  background: '#fff',
  borderRadius: 14,
  border: '1px solid #e8ecf0',
  padding: '20px 20px 14px',
  marginBottom: 20,
  boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
};

const cardTitleStyle = {
  fontSize: 16, fontWeight: 600, color: '#1a1a2e', margin: '0 0 16px',
  display: 'flex', alignItems: 'center', gap: 8,
};

export default function ProgressoTab({ responses = [], loading }) {
  const [period, setPeriod] = useState('all');

  const { weeklyData, dcaData } = useMemo(() => {
    const cutoff = (() => {
      const filter = PERIOD_FILTERS.find(f => f.key === period);
      if (!filter?.months) return null;
      const d = new Date();
      d.setMonth(d.getMonth() - filter.months);
      return d.toISOString();
    })();

    const weekly = responses
      .filter(r => r.type === 'weekly' && r.submit_date_iso)
      .filter(r => !cutoff || r.submit_date_iso >= cutoff)
      .sort((a, b) => a.submit_date_iso.localeCompare(b.submit_date_iso))
      .map(r => ({
        date: formatDate(r.submit_date_iso),
        dateIso: r.submit_date_iso,
        weight: r.weight,
        ...Object.fromEntries(WELLNESS_METRICS.map(m => [m.key, r[m.key]])),
      }));

    const dca = responses
      .filter(r => r.type === 'dca' && r.submit_date_iso)
      .filter(r => !cutoff || r.submit_date_iso >= cutoff)
      .sort((a, b) => a.submit_date_iso.localeCompare(b.submit_date_iso))
      .map(r => ({
        date: formatDate(r.submit_date_iso),
        dateIso: r.submit_date_iso,
        ...Object.fromEntries(DCA_METRICS.map(m => [m.key, r[m.key]])),
      }));

    return { weeklyData: weekly, dcaData: dca };
  }, [responses, period]);

  // Check which wellness metrics actually have data
  const activeWellnessMetrics = useMemo(() =>
    WELLNESS_METRICS.filter(m => weeklyData.some(d => d[m.key] != null)),
    [weeklyData]
  );

  const activeDcaMetrics = useMemo(() =>
    DCA_METRICS.filter(m => dcaData.some(d => d[m.key] != null)),
    [dcaData]
  );

  const hasWeightData = weeklyData.some(d => d.weight != null);
  const hasWeekly = weeklyData.length > 0 && (hasWeightData || activeWellnessMetrics.length > 0);
  const hasDca = dcaData.length > 0 && activeDcaMetrics.length > 0;

  if (loading) {
    return (
      <div className="cd-loading">
        <div className="spinner-border text-primary" role="status" />
        <p className="cd-loading-text" style={{ marginTop: 8 }}>Caricamento dati progresso...</p>
      </div>
    );
  }

  if (!hasWeekly && !hasDca) {
    return (
      <div className="cd-empty">
        <i className="ri-line-chart-line cd-empty-icon" />
        <h5>Nessun dato disponibile</h5>
        <p className="cd-empty-text">I grafici di progresso appariranno quando il paziente compilerà i check periodici.</p>
      </div>
    );
  }

  return (
    <div>
      {/* Period filter */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 20 }}>
        {PERIOD_FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => setPeriod(f.key)}
            style={{
              padding: '6px 16px', borderRadius: 20, border: '1.5px solid',
              borderColor: period === f.key ? ACCENT : '#ddd',
              background: period === f.key ? ACCENT : '#fff',
              color: period === f.key ? '#fff' : '#666',
              fontWeight: 600, fontSize: 13, cursor: 'pointer',
              transition: 'all .2s',
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* ===== WEEKLY SECTION ===== */}
      {hasWeekly && (
        <>
          <h5 style={{ fontSize: 15, fontWeight: 700, color: '#1a1a2e', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <i className="ri-calendar-check-line" style={{ color: ACCENT }} />
            Check Settimanale
          </h5>

          {/* Weight chart */}
          {hasWeightData && (
            <div style={cardStyle}>
              <div style={cardTitleStyle}>
                <i className="ri-scales-line" style={{ color: ACCENT }} />
                Andamento Peso (kg)
              </div>
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={weeklyData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <defs>
                    <linearGradient id="weightGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={ACCENT} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={ACCENT} stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#999' }} />
                  <YAxis
                    tick={{ fontSize: 12, fill: '#999' }}
                    domain={['auto', 'auto']}
                    tickFormatter={v => `${v}`}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone" dataKey="weight" name="Peso"
                    stroke={ACCENT} strokeWidth={2.5} fill="url(#weightGrad)"
                    dot={{ r: 4, fill: ACCENT, strokeWidth: 0 }}
                    activeDot={{ r: 6, fill: ACCENT, stroke: '#fff', strokeWidth: 2 }}
                    connectNulls
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Wellness chart */}
          {activeWellnessMetrics.length > 0 && (
            <div style={cardStyle}>
              <div style={cardTitleStyle}>
                <i className="ri-heart-pulse-line" style={{ color: '#FF6B35' }} />
                Parametri Wellness (0-10)
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={weeklyData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#999' }} />
                  <YAxis domain={[0, 10]} tick={{ fontSize: 12, fill: '#999' }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend
                    iconType="circle" iconSize={8}
                    wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
                  />
                  {activeWellnessMetrics.map(m => (
                    <Line
                      key={m.key} type="monotone" dataKey={m.key} name={m.label}
                      stroke={m.color} strokeWidth={2} dot={{ r: 3, strokeWidth: 0, fill: m.color }}
                      activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2 }}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}

      {/* ===== DCA SECTION ===== */}
      {hasDca && (
        <>
          <h5 style={{ fontSize: 15, fontWeight: 700, color: '#1a1a2e', marginBottom: 16, marginTop: hasWeekly ? 10 : 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            <i className="ri-mental-health-line" style={{ color: '#6C5CE7' }} />
            Check DCA
          </h5>

          <div style={cardStyle}>
            <div style={cardTitleStyle}>
              <i className="ri-psychotherapy-line" style={{ color: '#6C5CE7' }} />
              Benessere Psicologico (1-5)
            </div>
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={dcaData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#999' }} />
                <YAxis domain={[1, 5]} tick={{ fontSize: 12, fill: '#999' }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  iconType="circle" iconSize={8}
                  wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
                />
                {activeDcaMetrics.map(m => (
                  <Line
                    key={m.key} type="monotone" dataKey={m.key} name={m.label}
                    stroke={m.color} strokeWidth={2} dot={{ r: 3, strokeWidth: 0, fill: m.color }}
                    activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2 }}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}
