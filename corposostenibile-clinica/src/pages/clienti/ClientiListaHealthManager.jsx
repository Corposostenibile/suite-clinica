import { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import clientiService from '../../services/clientiService';
import teamService from '../../services/teamService';
import { useAuth } from '../../context/AuthContext';
import './ClientiList.css';

const ROLE_COLORS = {
  hm: { bg: '#f3e8ff', text: '#9333ea', badge: '#9333ea' },
  n: { bg: '#dcfce7', text: '#16a34a', badge: '#22c55e' },
  c: { bg: '#dbeafe', text: '#2563eb', badge: '#3b82f6' },
  p: { bg: '#fce7f3', text: '#db2777', badge: '#ec4899' },
};

const MAIN_TABS = [
  { key: 'scadenze', label: 'In Scadenza', icon: 'ri-alarm-warning-line' },
  { key: 'insoddisfatti', label: 'Insoddisfatti', icon: 'ri-emotion-unhappy-line' },
  { key: 'ghost', label: 'Ghost', icon: 'ri-ghost-line' },
  { key: 'pausa', label: 'In Pausa', icon: 'ri-pause-circle-line' },
  { key: 'recensioni', label: 'Recensioni', icon: 'ri-star-line' },
  { key: 'coordinatrici_hm', label: 'Pannello di controllo coordinatrici HM', icon: 'ri-dashboard-line' },
];

const REVIEW_TABS = [
  { key: '', label: 'Tutti', icon: 'ri-list-check', color: '#6366f1' },
  { key: 'none', label: 'Mai Invitati', icon: 'ri-mail-close-line', color: '#94a3b8' },
  { key: 'pending', label: 'In Attesa', icon: 'ri-time-line', color: '#f59e0b' },
  { key: 'reviewed', label: 'Con Recensione', icon: 'ri-star-fill', color: '#22c55e' },
];

const EXPIRY_TABS = [
  { key: 30, label: 'Entro 30 giorni', icon: 'ri-alarm-warning-line', color: '#ef4444' },
  { key: 60, label: 'Da 30 a 60 giorni', icon: 'ri-timer-line', color: '#f59e0b' },
  { key: 90, label: 'Da 60 a 90 giorni', icon: 'ri-time-line', color: '#3b82f6' },
];

const SATISFACTION_TABS = [
  { key: 8, label: 'Da 7 a 8', icon: 'ri-emotion-normal-line', color: '#f59e0b' },
  { key: 7, label: 'Da 6 a 7', icon: 'ri-emotion-unhappy-line', color: '#f97316' },
  { key: 6, label: 'Sotto il 6', icon: 'ri-emotion-sad-line', color: '#ef4444' },
];

function ClientiListaHealthManager() {
  const { user } = useAuth();

  const visualButtons = [
    { key: 'generale', to: '/clienti-lista', label: 'Lista Generale', icon: 'ri-list-check' },
    { key: 'nutrizione', to: '/clienti-nutrizione', label: 'Nutrizione', icon: 'ri-restaurant-line' },
    { key: 'coach', to: '/clienti-coach', label: 'Coach', icon: 'ri-run-line' },
    { key: 'psicologia', to: '/clienti-psicologia', label: 'Psicologia', icon: 'ri-mental-health-line' },
    { key: 'health_manager', to: '/clienti-health-manager', label: 'Health Manager', icon: 'ri-heart-pulse-line' },
  ];

  // Main tab state
  const [mainTab, setMainTab] = useState('scadenze');

  // Scadenze state
  const [expiryDays, setExpiryDays] = useState(30);
  const [expiryData, setExpiryData] = useState([]);
  const [expiryCounts, setExpiryCounts] = useState({ 30: 0, 60: 0, 90: 0 });
  const [expiryPagination, setExpiryPagination] = useState({ page: 1, perPage: 25, total: 0, totalPages: 0 });
  const [expiryLoading, setExpiryLoading] = useState(false);

  // Insoddisfatti state
  const [satThreshold, setSatThreshold] = useState(8);
  const [satData, setSatData] = useState([]);
  const [satCounts, setSatCounts] = useState({ 8: 0, 7: 0, 6: 0 });
  const [satPagination, setSatPagination] = useState({ page: 1, perPage: 25, total: 0, totalPages: 0 });
  const [satLoading, setSatLoading] = useState(false);

  // Ghost/Pausa state
  const [statusData, setStatusData] = useState([]);
  const [statusPagination, setStatusPagination] = useState({ page: 1, perPage: 25, total: 0, totalPages: 0 });
  const [statusLoading, setStatusLoading] = useState(false);

  // Recensioni state
  const [reviewStatus, setReviewStatus] = useState('');
  const [reviewData, setReviewData] = useState([]);
  const [reviewCounts, setReviewCounts] = useState({ totale_attivi: 0, con_recensione: 0, in_attesa: 0, mai_invitati: 0 });
  const [reviewPagination, setReviewPagination] = useState({ page: 1, perPage: 25, total: 0, totalPages: 0 });
  const [reviewLoading, setReviewLoading] = useState(false);
  const [sendingAction, setSendingAction] = useState(null);
  const [trustpilotMeta, setTrustpilotMeta] = useState({
    enabled: false,
    missing_config: [],
    webhook_configured: false,
  });

  // Shared
  const [error, setError] = useState(null);
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const searchTimerRef = useRef(null);

  // Pannello coordinatrici HM
  const [coordData, setCoordData] = useState([]);
  const [coordHealthManagers, setCoordHealthManagers] = useState([]);
  const [coordPagination, setCoordPagination] = useState({ page: 1, perPage: 25, total: 0, totalPages: 0 });
  const [coordLoading, setCoordLoading] = useState(false);
  const [coordSortBy, setCoordSortBy] = useState('health_manager');
  const [coordSortDir, setCoordSortDir] = useState('asc');
  const [coordFlagFilters, setCoordFlagFilters] = useState({
    check_in_completed: '',
    contacted_for_renewal: '',
    renewal_completed: '',
    contacted_for_review: '',
    review_completed: '',
  });
  const coordTableScrollRef = useRef(null);
  const coordTopScrollRef = useRef(null);
  const coordScrollSyncLockRef = useRef(false);
  const [coordScroll, setCoordScroll] = useState({
    canLeft: false,
    canRight: false,
    hasOverflow: false,
    scrollWidth: 0,
  });

  const getApiErrorMessage = (err, fallback) => {
    const description = err?.response?.data?.description;
    const message = err?.response?.data?.message;
    const errorText = err?.response?.data?.error;
    return description || message || errorText || fallback;
  };

  // Health Manager filter (admin/TL only)
  const roleValue = user?.role?.value || user?.role;
  const specialtyValue = user?.specialty?.value || user?.specialty;
  const isAdmin = Boolean(
    user?.is_admin ||
    roleValue === 'admin' ||
    String(specialtyValue || '').toLowerCase() === 'cco'
  );
  const isHmTeamLeader = Boolean(
    roleValue === 'team_leader' && (
      user?.is_health_manager_team_leader ||
      String(specialtyValue || '').toLowerCase() === 'health_manager' ||
      String(user?.department?.name || '').toLowerCase().includes('health') ||
      String(user?.department?.name || '').toLowerCase().includes('customer success') ||
      (Array.isArray(user?.teams_led) && user.teams_led.some((team) => {
        const teamType = team?.team_type?.value || team?.team_type;
        return String(teamType || '').toLowerCase() === 'health_manager';
      }))
    )
  );
  const isImpersonatingSession = Boolean(user?.impersonating);
  const canFilterByHm = isAdmin || isHmTeamLeader || isImpersonatingSession;
  const [healthManagers, setHealthManagers] = useState([]);
  const [selectedHmId, setSelectedHmId] = useState('');

  useEffect(() => {
    if (!canFilterByHm) return;
    const fetchHms = async () => {
      try {
        const data = await teamService.getTeamMembers({
          per_page: 100,
          active: '1',
          role: 'health_manager',
        });
        setHealthManagers(data.members || []);
      } catch (err) {
        console.error('Error fetching HMs:', err);
      }
    };
    fetchHms();
  }, [canFilterByHm]);

  // ── Fetch Scadenze ──
  const fetchExpiring = useCallback(async () => {
    setExpiryLoading(true);
    setError(null);
    try {
      const data = await clientiService.getClientiExpiring({
        days: expiryDays,
        page: expiryPagination.page,
        per_page: expiryPagination.perPage,
        q: debouncedSearch || undefined,
        health_manager_id: selectedHmId || undefined,
      });
      setExpiryData(data.data || []);
      setExpiryCounts(data.counts || { 30: 0, 60: 0, 90: 0 });
      setExpiryPagination(prev => ({ ...prev, total: data.pagination?.total || 0, totalPages: data.pagination?.pages || 0 }));
    } catch (err) {
      console.error('Error fetching expiring:', err);
      setError('Errore nel caricamento');
    } finally {
      setExpiryLoading(false);
    }
  }, [expiryDays, expiryPagination.page, expiryPagination.perPage, debouncedSearch, selectedHmId]);

  // ── Fetch Insoddisfatti ──
  const fetchUnsatisfied = useCallback(async () => {
    setSatLoading(true);
    setError(null);
    try {
      const data = await clientiService.getClientiUnsatisfied({
        threshold: satThreshold,
        page: satPagination.page,
        per_page: satPagination.perPage,
        q: debouncedSearch || undefined,
        health_manager_id: selectedHmId || undefined,
      });
      setSatData(data.data || []);
      setSatCounts(data.counts || { 8: 0, 7: 0, 6: 0 });
      setSatPagination(prev => ({ ...prev, total: data.pagination?.total || 0, totalPages: data.pagination?.pages || 0 }));
    } catch (err) {
      console.error('Error fetching unsatisfied:', err);
      setError('Errore nel caricamento');
    } finally {
      setSatLoading(false);
    }
  }, [satThreshold, satPagination.page, satPagination.perPage, debouncedSearch, selectedHmId]);

  useEffect(() => {
    if (mainTab === 'scadenze') fetchExpiring();
  }, [mainTab, fetchExpiring]);

  useEffect(() => {
    if (mainTab === 'insoddisfatti') fetchUnsatisfied();
  }, [mainTab, fetchUnsatisfied]);

  // ── Fetch Ghost/Pausa ──
  const fetchByStatus = useCallback(async () => {
    setStatusLoading(true);
    setError(null);
    try {
      const data = await clientiService.getClienti({
        stato_cliente: mainTab, // 'ghost' or 'pausa'
        page: statusPagination.page,
        per_page: statusPagination.perPage,
        q: debouncedSearch || undefined,
        health_manager_id: selectedHmId || undefined,
      });
      setStatusData(data.data || []);
      setStatusPagination(prev => ({ ...prev, total: data.pagination?.total || 0, totalPages: data.pagination?.pages || 0 }));
    } catch (err) {
      console.error('Error fetching status clients:', err);
      setError('Errore nel caricamento');
    } finally {
      setStatusLoading(false);
    }
  }, [mainTab, statusPagination.page, statusPagination.perPage, debouncedSearch, selectedHmId]);

  useEffect(() => {
    if (mainTab === 'ghost' || mainTab === 'pausa') fetchByStatus();
  }, [mainTab, fetchByStatus]);

  // ── Fetch Recensioni ──
  const fetchReviews = useCallback(async () => {
    setReviewLoading(true);
    setError(null);
    try {
      const data = await clientiService.getTrustpilotOverview({
        page: reviewPagination.page,
        per_page: reviewPagination.perPage,
        q: debouncedSearch || undefined,
        health_manager_id: selectedHmId || undefined,
        status: reviewStatus || undefined,
      });
      setReviewData(data.data || []);
      setReviewCounts(data.counts || { totale_attivi: 0, con_recensione: 0, in_attesa: 0, mai_invitati: 0 });
      setReviewPagination(prev => ({ ...prev, total: data.pagination?.total || 0, totalPages: data.pagination?.pages || 0 }));
      setTrustpilotMeta({
        enabled: Boolean(data.enabled),
        missing_config: Array.isArray(data.missing_config) ? data.missing_config : [],
        webhook_configured: Boolean(data.webhook_configured),
      });
    } catch (err) {
      console.error('Error fetching reviews:', err);
      setError(getApiErrorMessage(err, 'Errore nel caricamento recensioni'));
    } finally {
      setReviewLoading(false);
    }
  }, [reviewPagination.page, reviewPagination.perPage, debouncedSearch, selectedHmId, reviewStatus]);

  useEffect(() => {
    if (mainTab === 'recensioni') fetchReviews();
  }, [mainTab, fetchReviews]);

  const fetchHmCoordinatriciDashboard = useCallback(async () => {
    setCoordLoading(true);
    setError(null);
    try {
      const data = await clientiService.getHmCoordinatriciDashboard({
        page: coordPagination.page,
        per_page: coordPagination.perPage,
        q: debouncedSearch || undefined,
        health_manager_id: selectedHmId || undefined,
        sort_by: coordSortBy,
        sort_dir: coordSortDir,
        ...Object.fromEntries(Object.entries(coordFlagFilters).filter(([, value]) => Boolean(value))),
      });
      setCoordData(data.data || []);
      setCoordHealthManagers(data.health_managers || []);
      setCoordPagination(prev => ({ ...prev, total: data.pagination?.total || 0, totalPages: data.pagination?.pages || 0 }));
    } catch (err) {
      console.error('Error fetching coordinatrici HM dashboard:', err);
      setError(getApiErrorMessage(err, 'Errore nel caricamento pannello coordinatrici HM'));
    } finally {
      setCoordLoading(false);
    }
  }, [coordPagination.page, coordPagination.perPage, debouncedSearch, selectedHmId, coordSortBy, coordSortDir, coordFlagFilters]);

  useEffect(() => {
    if (mainTab === 'coordinatrici_hm') fetchHmCoordinatriciDashboard();
  }, [mainTab, fetchHmCoordinatriciDashboard]);

  const handleGenerateLink = async (clienteId) => {
    setSendingAction(`link-${clienteId}`);
    try {
      const result = await clientiService.generateTrustpilotLink(clienteId);
      const link = result?.data?.trustpilot_link;
      if (link) await navigator.clipboard.writeText(link);
      fetchReviews();
    } catch (err) {
      console.error('Error generating link:', err);
      setError(getApiErrorMessage(err, 'Errore nella generazione del link Trustpilot'));
    }
    finally { setSendingAction(null); }
  };

  const handleSendInvite = async (clienteId) => {
    setSendingAction(`invite-${clienteId}`);
    try {
      await clientiService.sendTrustpilotInvite(clienteId);
      fetchReviews();
    } catch (err) {
      console.error('Error sending invite:', err);
      setError(getApiErrorMessage(err, 'Errore nell\'invio invito Trustpilot'));
    }
    finally { setSendingAction(null); }
  };

  // ── Search ──
  const handleSearchInput = (value) => {
    setSearchInput(value);
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      setDebouncedSearch(value);
      setExpiryPagination(prev => ({ ...prev, page: 1 }));
      setSatPagination(prev => ({ ...prev, page: 1 }));
      setCoordPagination(prev => ({ ...prev, page: 1 }));
    }, 400);
  };

  useEffect(() => () => { if (searchTimerRef.current) clearTimeout(searchTimerRef.current); }, []);

  // ── Helpers ──
  const renderTeamAvatar = (teamUser, roleKey, roleLabel) => {
    if (!teamUser) return null;
    const colors = ROLE_COLORS[roleKey] || ROLE_COLORS.hm;
    const initials = `${teamUser.first_name?.[0] || ''}${teamUser.last_name?.[0] || ''}`.toUpperCase();
    return (
      <span key={`${roleKey}-${teamUser.id}`} className="cl-avatar-wrap" title={`${roleLabel}: ${teamUser.full_name || `${teamUser.first_name} ${teamUser.last_name}`}`}>
        {teamUser.avatar_url || teamUser.avatar_path ? (
          <img src={teamUser.avatar_url || teamUser.avatar_path} alt={teamUser.full_name} className="cl-avatar-img" />
        ) : (
          <span className="cl-avatar-initials" style={{ background: colors.bg, color: colors.text }}>{initials}</span>
        )}
        <span className="cl-avatar-role-badge" style={{ background: colors.badge }}>{roleKey.toUpperCase()}</span>
      </span>
    );
  };

  const renderTeamCell = (cliente) => {
    const has = cliente.health_manager_user || cliente.nutrizionista_user || cliente.coach_user || cliente.psicologa_user;
    return (
      <div className="cl-team-avatars">
        {cliente.health_manager_user && renderTeamAvatar(cliente.health_manager_user, 'hm', 'Health Manager')}
        {cliente.nutrizionista_user && renderTeamAvatar(cliente.nutrizionista_user, 'n', 'Nutrizionista')}
        {cliente.coach_user && renderTeamAvatar(cliente.coach_user, 'c', 'Coach')}
        {cliente.psicologa_user && renderTeamAvatar(cliente.psicologa_user, 'p', 'Psicologo')}
        {!has && <span className="cl-empty">&mdash;</span>}
      </div>
    );
  };

  const renderStatoBadge = (stato) => {
    if (!stato) return <span className="cl-empty">&mdash;</span>;
    const colorMap = { attivo: '#22c55e', ghost: '#64748b', pausa: '#f59e0b', stop: '#ef4444' };
    const bgMap = { attivo: 'rgba(34,197,94,0.1)', ghost: 'rgba(100,116,139,0.1)', pausa: 'rgba(245,158,11,0.1)', stop: 'rgba(239,68,68,0.1)' };
    return (
      <span className="cl-badge" style={{ background: bgMap[stato] || '#f1f5f9', color: colorMap[stato] || '#64748b' }}>
        <i className="ri-circle-fill" style={{ fontSize: '6px' }}></i>{' '}{stato}
      </span>
    );
  };

  const getUrgencyStyle = (giorni) => {
    if (giorni == null) return { bg: '#f1f5f9', color: '#64748b' };
    if (giorni <= 7) return { bg: '#fef2f2', color: '#dc2626' };
    if (giorni <= 14) return { bg: '#fff7ed', color: '#ea580c' };
    if (giorni <= 30) return { bg: '#fefce8', color: '#ca8a04' };
    if (giorni <= 60) return { bg: '#eff6ff', color: '#2563eb' };
    return { bg: '#f0fdf4', color: '#16a34a' };
  };

  const getRatingStyle = (avg) => {
    if (avg == null) return { bg: '#f1f5f9', color: '#64748b' };
    if (avg < 5) return { bg: '#fef2f2', color: '#dc2626' };
    if (avg < 6) return { bg: '#fff7ed', color: '#ea580c' };
    if (avg < 7) return { bg: '#fefce8', color: '#ca8a04' };
    if (avg < 8) return { bg: '#eff6ff', color: '#2563eb' };
    return { bg: '#f0fdf4', color: '#16a34a' };
  };

  const getPageNumbers = (pag) => {
    const pages = [];
    const total = pag.totalPages;
    const current = pag.page;
    if (total <= 5) { for (let i = 1; i <= total; i++) pages.push(i); }
    else if (current <= 3) { for (let i = 1; i <= 5; i++) pages.push(i); }
    else if (current >= total - 2) { for (let i = total - 4; i <= total; i++) pages.push(i); }
    else { for (let i = current - 2; i <= current + 2; i++) pages.push(i); }
    return pages;
  };

  const renderPagination = (pag, onPageChange) => {
    if (pag.totalPages <= 1) return null;
    return (
      <div className="cl-pagination">
        <span className="cl-pagination-info">
          Pagina <strong>{pag.page}</strong> di <strong>{pag.totalPages}</strong>{' '}&bull; {pag.total} risultati
        </span>
        <div className="cl-pagination-buttons">
          <button className="cl-page-btn" onClick={() => onPageChange(1)} disabled={pag.page === 1}>&laquo;</button>
          <button className="cl-page-btn" onClick={() => onPageChange(pag.page - 1)} disabled={pag.page === 1}>&lsaquo;</button>
          {getPageNumbers(pag).map((p) => (
            <button key={p} className={`cl-page-btn${pag.page === p ? ' active' : ''}`} onClick={() => onPageChange(p)}>{p}</button>
          ))}
          <button className="cl-page-btn" onClick={() => onPageChange(pag.page + 1)} disabled={pag.page === pag.totalPages}>&rsaquo;</button>
          <button className="cl-page-btn" onClick={() => onPageChange(pag.totalPages)} disabled={pag.page === pag.totalPages}>&raquo;</button>
        </div>
      </div>
    );
  };

  const isStatusTab = mainTab === 'ghost' || mainTab === 'pausa';
  const isReviewTab = mainTab === 'recensioni';
  const isCoordinatriciTab = mainTab === 'coordinatrici_hm';
  const loading = isReviewTab
    ? reviewLoading
    : isCoordinatriciTab
      ? coordLoading
      : mainTab === 'scadenze'
        ? expiryLoading
        : mainTab === 'insoddisfatti'
          ? satLoading
          : statusLoading;
  const clienti = isReviewTab ? [] : mainTab === 'scadenze' ? expiryData : mainTab === 'insoddisfatti' ? satData : statusData;

  const canAccessCoordinatriciPanel = Boolean(isAdmin || isHmTeamLeader || isImpersonatingSession);
  const visibleMainTabs = MAIN_TABS.filter((tab) => tab.key !== 'coordinatrici_hm' || canAccessCoordinatriciPanel);
  const hmFilterOptions = isCoordinatriciTab && coordHealthManagers.length > 0 ? coordHealthManagers : healthManagers;

  const formatDate = (value) => (value ? new Date(value).toLocaleDateString('it-IT') : '\u2014');

  const toggleCoordSort = (field) => {
    if (coordSortBy === field) {
      setCoordSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setCoordSortBy(field);
      setCoordSortDir('asc');
    }
    setCoordPagination((prev) => ({ ...prev, page: 1 }));
  };

  const renderSortableHeader = (label, field) => {
    const isActive = coordSortBy === field;
    return (
      <button
        type="button"
        onClick={() => toggleCoordSort(field)}
        className="cl-th-sort"
      >
        <span>{label}</span>
        <i className={isActive ? (coordSortDir === 'asc' ? 'ri-arrow-up-s-line' : 'ri-arrow-down-s-line') : 'ri-expand-up-down-line'}></i>
      </button>
    );
  };

  const updateCoordScrollMetrics = useCallback(() => {
    const el = coordTableScrollRef.current;
    if (!el) return;
    const hasOverflow = el.scrollWidth > el.clientWidth + 1;
    setCoordScroll({
      canLeft: el.scrollLeft > 0,
      canRight: el.scrollLeft + el.clientWidth < el.scrollWidth - 1,
      hasOverflow,
      scrollWidth: el.scrollWidth,
    });
  }, []);

  const syncCoordTopFromTable = useCallback(() => {
    const tableEl = coordTableScrollRef.current;
    const topEl = coordTopScrollRef.current;
    if (!tableEl || !topEl || coordScrollSyncLockRef.current) return;
    coordScrollSyncLockRef.current = true;
    topEl.scrollLeft = tableEl.scrollLeft;
    coordScrollSyncLockRef.current = false;
    updateCoordScrollMetrics();
  }, [updateCoordScrollMetrics]);

  const syncCoordTableFromTop = useCallback(() => {
    const tableEl = coordTableScrollRef.current;
    const topEl = coordTopScrollRef.current;
    if (!tableEl || !topEl || coordScrollSyncLockRef.current) return;
    coordScrollSyncLockRef.current = true;
    tableEl.scrollLeft = topEl.scrollLeft;
    coordScrollSyncLockRef.current = false;
    updateCoordScrollMetrics();
  }, [updateCoordScrollMetrics]);

  const scrollCoordTable = (dir) => {
    const el = coordTableScrollRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * 260, behavior: 'smooth' });
  };

  useEffect(() => {
    if (!isCoordinatriciTab) return;
    updateCoordScrollMetrics();
    const onResize = () => updateCoordScrollMetrics();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [isCoordinatriciTab, coordData, updateCoordScrollMetrics]);

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="cl-header">
        <div>
          <h4>Visuale Health Manager</h4>
          <p className="cl-header-sub">Monitoraggio clienti</p>
        </div>
        <div className="cl-view-pills">
          {visualButtons.map((btn) => (
            <Link key={btn.key} to={btn.to} className={`cl-view-pill${btn.key === 'health_manager' ? ' active' : ''}`}>
              <i className={btn.icon}></i> {btn.label}
            </Link>
          ))}
        </div>
      </div>

      {/* Main tabs: Scadenze / Insoddisfatti */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
        {visibleMainTabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => {
              setMainTab(tab.key);
              setSearchInput('');
              setDebouncedSearch('');
              setStatusPagination(prev => ({ ...prev, page: 1 }));
              setReviewPagination(prev => ({ ...prev, page: 1 }));
              setCoordPagination(prev => ({ ...prev, page: 1 }));
            }}
            style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              padding: '10px 20px', borderRadius: '12px', border: '1px solid',
              borderColor: mainTab === tab.key ? '#25B36A' : '#e5e7eb',
              background: mainTab === tab.key ? 'rgba(37,179,106,0.08)' : '#fff',
              color: mainTab === tab.key ? '#166534' : '#374151',
              fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <i className={tab.icon} style={{ fontSize: '16px' }}></i>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Sub-tabs Recensioni */}
      {isReviewTab && (
      <div className="cl-stats-row">
        {REVIEW_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => { setReviewStatus(tab.key); setReviewPagination(prev => ({ ...prev, page: 1 })); }}
            className="cl-stat-card"
            style={{
              cursor: 'pointer',
              border: reviewStatus === tab.key ? `2px solid ${tab.color}` : '2px solid transparent',
              background: reviewStatus === tab.key ? `${tab.color}08` : undefined,
              transition: 'all 0.2s ease',
            }}
          >
            <div>
              <div className="cl-stat-value">
                {tab.key === '' ? reviewCounts.totale_attivi
                  : tab.key === 'none' ? reviewCounts.mai_invitati
                  : tab.key === 'pending' ? reviewCounts.in_attesa
                  : reviewCounts.con_recensione}
              </div>
              <div className="cl-stat-label">{tab.label}</div>
            </div>
            <div className="cl-stat-icon" style={{ background: `${tab.color}15`, color: tab.color }}>
              <i className={tab.icon}></i>
            </div>
          </button>
        ))}
      </div>
      )}

      {/* Sub-tabs (filter cards) — only for scadenze/insoddisfatti */}
      {(mainTab === 'scadenze' || mainTab === 'insoddisfatti') && (
      <div className="cl-stats-row">
        {mainTab === 'scadenze' ? (
          EXPIRY_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => { setExpiryDays(tab.key); setExpiryPagination(prev => ({ ...prev, page: 1 })); }}
              className="cl-stat-card"
              style={{
                cursor: 'pointer',
                border: expiryDays === tab.key ? `2px solid ${tab.color}` : '2px solid transparent',
                background: expiryDays === tab.key ? `${tab.color}08` : undefined,
                transition: 'all 0.2s ease',
              }}
            >
              <div>
                <div className="cl-stat-value">{expiryCounts[String(tab.key)] || 0}</div>
                <div className="cl-stat-label">{tab.label}</div>
              </div>
              <div className="cl-stat-icon" style={{ background: `${tab.color}15`, color: tab.color }}>
                <i className={tab.icon}></i>
              </div>
            </button>
          ))
        ) : (
          SATISFACTION_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => { setSatThreshold(tab.key); setSatPagination(prev => ({ ...prev, page: 1 })); }}
              className="cl-stat-card"
              style={{
                cursor: 'pointer',
                border: satThreshold === tab.key ? `2px solid ${tab.color}` : '2px solid transparent',
                background: satThreshold === tab.key ? `${tab.color}08` : undefined,
                transition: 'all 0.2s ease',
              }}
            >
              <div>
                <div className="cl-stat-value">{satCounts[String(tab.key)] || 0}</div>
                <div className="cl-stat-label">{tab.label}</div>
              </div>
              <div className="cl-stat-icon" style={{ background: `${tab.color}15`, color: tab.color }}>
                <i className={tab.icon}></i>
              </div>
            </button>
          ))
        )}
      </div>
      )}

      {/* Search + HM filter */}
      <div className="cl-search-row">
        <div className="cl-search-wrap">
          <i className="ri-search-line cl-search-icon"></i>
          <input
            type="text"
            className="cl-search-input"
            placeholder="Cerca paziente per nome..."
            value={searchInput}
            onChange={(e) => handleSearchInput(e.target.value)}
          />
        </div>
        {canFilterByHm && hmFilterOptions.length > 0 && (
          <select
            className="cl-search-input"
            style={{ maxWidth: '240px', padding: '10px 14px', borderRadius: '12px', border: '1px solid #e5e7eb', fontSize: '13px', fontWeight: 600, color: '#374151', cursor: 'pointer' }}
            value={selectedHmId}
            onChange={(e) => {
              setSelectedHmId(e.target.value);
              setExpiryPagination(prev => ({ ...prev, page: 1 }));
              setSatPagination(prev => ({ ...prev, page: 1 }));
              setCoordPagination(prev => ({ ...prev, page: 1 }));
            }}
          >
            <option value="">Tutti gli Health Manager</option>
            {hmFilterOptions.map((hm) => (
              <option key={hm.id} value={hm.id}>{hm.full_name || hm.name || `HM #${hm.id}`}</option>
            ))}
          </select>
        )}
      </div>

      {isCoordinatriciTab && (
        <div className="cl-coord-filters-row">
          {[
            ['check_in_completed', 'Check-in'],
            ['contacted_for_renewal', 'Contattato rinnovo'],
            ['renewal_completed', 'Rinnovo'],
            ['contacted_for_review', 'Contattato review'],
            ['review_completed', 'Review'],
          ].map(([key, label]) => (
            <select
              key={key}
              className="cl-coord-filter-select"
              value={coordFlagFilters[key]}
              onChange={(e) => {
                const value = e.target.value;
                setCoordFlagFilters((prev) => ({ ...prev, [key]: value }));
                setCoordPagination((prev) => ({ ...prev, page: 1 }));
              }}
            >
              <option value="">{label}: tutti</option>
              <option value="yes">{label}: SI</option>
              <option value="no">{label}: NO</option>
            </select>
          ))}
          <button
            type="button"
            className="cl-coord-filter-reset"
            onClick={() => {
              setCoordFlagFilters({
                check_in_completed: '',
                contacted_for_renewal: '',
                renewal_completed: '',
                contacted_for_review: '',
                review_completed: '',
              });
              setCoordPagination((prev) => ({ ...prev, page: 1 }));
            }}
          >
            <i className="ri-refresh-line"></i> Reset filtri
          </button>
        </div>
      )}

      {/* ── Recensioni Content ── */}
      {isReviewTab && (
        <>
          {reviewLoading ? (
            <div className="cl-loading">
              <div className="cl-spinner" style={{ margin: '0 auto' }}></div>
              <p className="cl-loading-text">Caricamento...</p>
            </div>
          ) : reviewData.length === 0 ? (
            <div className="cl-empty-state">
              <div className="cl-empty-icon"><i className="ri-star-line"></i></div>
              <h5 className="cl-empty-title">Nessun cliente trovato</h5>
              <p className="cl-empty-desc">
                {reviewStatus === 'none' ? 'Nessun cliente senza inviti Trustpilot' :
                 reviewStatus === 'pending' ? 'Nessun cliente con inviti in attesa' :
                 reviewStatus === 'reviewed' ? 'Nessun cliente con recensione pubblicata' :
                 'Nessun cliente attivo'}
              </p>
            </div>
          ) : (
            <>
              <div className="cl-table-card">
                <div className="table-responsive">
                  <table className="cl-table">
                    <thead>
                      <tr>
                        <th style={{ minWidth: 180 }}>Cliente</th>
                        <th style={{ minWidth: 130 }}>Pacchetto</th>
                        <th style={{ minWidth: 120 }}>Health Manager</th>
                        <th style={{ minWidth: 80, textAlign: 'center' }}>Inviti</th>
                        <th style={{ minWidth: 90, textAlign: 'center' }}>Stato</th>
                        <th style={{ minWidth: 80, textAlign: 'center' }}>Stelle</th>
                        <th style={{ minWidth: 100, textAlign: 'center' }}>Ultimo Invito</th>
                        <th style={{ minWidth: 90, textAlign: 'center' }}>Metodo</th>
                        <th style={{ textAlign: 'right', minWidth: 140 }}>Azioni</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reviewData.map((row) => {
                        const tp = row.trustpilot || {};
                        const latest = tp.ultimo_invito;
                        return (
                          <tr key={row.cliente_id}>
                            <td>
                              <Link to={`/clienti-dettaglio/${row.cliente_id}`} className="cl-name-link">
                                {row.nome_cognome}
                              </Link>
                              {row.mail && <div style={{ fontSize: 11, color: '#94a3b8' }}>{row.mail}</div>}
                            </td>
                            <td>
                              {row.programma_attuale ? (
                                <span className="cl-badge" style={{ background: '#f0fdf4', color: '#166534', fontSize: 12, fontWeight: 600 }}>
                                  {row.programma_attuale}
                                </span>
                              ) : <span className="cl-empty">&mdash;</span>}
                            </td>
                            <td style={{ fontSize: 13 }}>
                              {row.health_manager_user?.full_name || <span className="cl-empty">&mdash;</span>}
                            </td>
                            <td style={{ textAlign: 'center' }}>
                              <span className="cl-badge" style={{
                                background: tp.total_inviti > 0 ? 'rgba(99,102,241,.1)' : '#f1f5f9',
                                color: tp.total_inviti > 0 ? '#6366f1' : '#94a3b8',
                                fontWeight: 700,
                              }}>
                                {tp.total_inviti || 0}
                              </span>
                            </td>
                            <td style={{ textAlign: 'center' }}>
                              {tp.ha_recensione ? (
                                <span className="cl-badge" style={{ background: 'rgba(34,197,94,.1)', color: '#16a34a', fontWeight: 700 }}>
                                  <i className="ri-check-line" style={{ marginRight: 3 }}></i>Pubblicata
                                </span>
                              ) : tp.total_inviti > 0 ? (
                                <span className="cl-badge" style={{ background: 'rgba(245,158,11,.1)', color: '#d97706', fontWeight: 600 }}>
                                  <i className="ri-time-line" style={{ marginRight: 3 }}></i>In attesa
                                </span>
                              ) : (
                                <span className="cl-badge" style={{ background: '#f1f5f9', color: '#94a3b8' }}>
                                  Mai invitato
                                </span>
                              )}
                            </td>
                            <td style={{ textAlign: 'center' }}>
                              {tp.stelle_migliore ? (
                                <span style={{ color: '#f59e0b', fontWeight: 700, fontSize: 14 }}>
                                  {'★'.repeat(tp.stelle_migliore)}{'☆'.repeat(5 - tp.stelle_migliore)}
                                </span>
                              ) : <span className="cl-empty">&mdash;</span>}
                            </td>
                            <td style={{ textAlign: 'center', fontSize: 12 }}>
                              {latest?.data_richiesta ? (
                                new Date(latest.data_richiesta).toLocaleDateString('it-IT')
                              ) : <span className="cl-empty">&mdash;</span>}
                            </td>
                            <td style={{ textAlign: 'center' }}>
                              {latest?.invitation_method ? (
                                <span className="cl-badge" style={{
                                  background: latest.invitation_method === 'email_invitation' ? 'rgba(59,130,246,.1)' : 'rgba(100,116,139,.1)',
                                  color: latest.invitation_method === 'email_invitation' ? '#2563eb' : '#475569',
                                  fontSize: 11,
                                }}>
                                  {latest.invitation_method === 'email_invitation' ? 'Email' : 'Link'}
                                </span>
                              ) : <span className="cl-empty">&mdash;</span>}
                            </td>
                            <td style={{ textAlign: 'right' }}>
                              <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                                <button
                                  className="cl-action-btn"
                                  title="Genera Link"
                                  disabled={sendingAction === `link-${row.cliente_id}`}
                                  onClick={() => handleGenerateLink(row.cliente_id)}
                                  style={{ background: 'rgba(37,179,106,.08)', color: '#25B36A' }}
                                >
                                  {sendingAction === `link-${row.cliente_id}` ? <i className="ri-loader-4-line"></i> : <i className="ri-link"></i>}
                                </button>
                                <button
                                  className="cl-action-btn"
                                  title="Invia Email"
                                  disabled={sendingAction === `invite-${row.cliente_id}`}
                                  onClick={() => handleSendInvite(row.cliente_id)}
                                  style={{ background: 'rgba(59,130,246,.08)', color: '#3b82f6' }}
                                >
                                  {sendingAction === `invite-${row.cliente_id}` ? <i className="ri-loader-4-line"></i> : <i className="ri-mail-send-line"></i>}
                                </button>
                                {latest?.trustpilot_link && (
                                  <button
                                    className="cl-action-btn"
                                    title="Copia Link"
                                    onClick={async () => { await navigator.clipboard.writeText(latest.trustpilot_link); }}
                                    style={{ background: 'rgba(100,116,139,.08)', color: '#64748b' }}
                                  >
                                    <i className="ri-clipboard-line"></i>
                                  </button>
                                )}
                                <Link to={`/clienti-dettaglio/${row.cliente_id}?tab=marketing`} className="cl-action-btn" title="Dettaglio Marketing">
                                  <i className="ri-eye-line"></i>
                                </Link>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
              {renderPagination(reviewPagination, (p) => setReviewPagination(prev => ({ ...prev, page: p })))}
            </>
          )}
        </>
      )}

      {/* ── Pannello Coordinatrici HM ── */}
      {isCoordinatriciTab && (
        <>
          {error && <div className="cl-error" style={{ marginBottom: 12 }}>{error}</div>}
          {coordLoading ? (
            <div className="cl-loading">
              <div className="cl-spinner" style={{ margin: '0 auto' }}></div>
              <p className="cl-loading-text">Caricamento...</p>
            </div>
          ) : coordData.length === 0 ? (
            <div className="cl-empty-state">
              <div className="cl-empty-icon"><i className="ri-dashboard-line"></i></div>
              <h5 className="cl-empty-title">Nessun cliente trovato</h5>
              <p className="cl-empty-desc">Nessun paziente associato al filtro Health Manager selezionato.</p>
            </div>
           ) : (
             <>
               <div className="cl-table-card">
                 <div className="cl-top-scroll-wrap">
                   <button
                     type="button"
                     className="cl-top-scroll-arrow cl-top-scroll-arrow-left"
                     onClick={() => scrollCoordTable(-1)}
                     disabled={!coordScroll.canLeft}
                     aria-label="Scorri tabella a sinistra"
                   >
                     <i className="ri-arrow-left-s-line"></i>
                   </button>
                   <div
                     className="cl-top-scroll"
                     ref={coordTopScrollRef}
                     onScroll={syncCoordTableFromTop}
                   >
                     <div className="cl-top-scroll-inner" style={{ width: `${Math.max(coordScroll.scrollWidth, 1)}px` }}></div>
                   </div>
                   <button
                     type="button"
                     className="cl-top-scroll-arrow cl-top-scroll-arrow-right"
                     onClick={() => scrollCoordTable(1)}
                     disabled={!coordScroll.canRight}
                     aria-label="Scorri tabella a destra"
                   >
                     <i className="ri-arrow-right-s-line"></i>
                   </button>
                 </div>
                 <div
                   className="table-responsive"
                   ref={coordTableScrollRef}
                   onScroll={syncCoordTopFromTable}
                 >
                   <table className="cl-table">
                     <thead>
                       <tr>
                         <th style={{ minWidth: 180 }}>Nome cliente</th>
                         <th style={{ minWidth: 160 }}>{renderSortableHeader('HM', 'health_manager')}</th>
                         <th style={{ minWidth: 150 }}>{renderSortableHeader('Data onboarding', 'onboarding_date')}</th>
                         <th style={{ minWidth: 150 }}>{renderSortableHeader('Data inizio percorso', 'path_start_date')}</th>
                         <th style={{ minWidth: 150 }}>{renderSortableHeader('Data fine percorso', 'path_end_date')}</th>
                         <th style={{ minWidth: 150 }}>{renderSortableHeader('Data check-in call', 'check_in_call_date')}</th>
                         <th style={{ minWidth: 115, textAlign: 'center' }}>Check-in</th>
                         <th style={{ minWidth: 160 }}>{renderSortableHeader('Data call rinnovo', 'renewal_call_date')}</th>
                         <th style={{ minWidth: 170, textAlign: 'center' }}>Contattato per il rinnovo</th>
                         <th style={{ minWidth: 110, textAlign: 'center' }}>Rinnovo</th>
                         <th style={{ minWidth: 150, textAlign: 'center' }}>Contattato per review</th>
                         <th style={{ minWidth: 120, textAlign: 'center' }}>Review</th>
                         <th style={{ textAlign: 'right', minWidth: 80 }}>Azioni</th>
                       </tr>
                     </thead>
                    <tbody>
                      {coordData.map((row) => {
                        const yesNoBadge = (value, isMock) => (
                          <span className="cl-badge" style={{
                            background: value ? 'rgba(34,197,94,.12)' : 'rgba(148,163,184,.18)',
                            color: value ? '#166534' : '#64748b',
                            fontWeight: 700,
                          }}>
                            {value ? 'SI' : 'NO'}{isMock ? ' (mock)' : ''}
                          </span>
                        );
                        return (
                          <tr key={row.cliente_id}>
                            <td>
                              <Link to={`/clienti-dettaglio/${row.cliente_id}`} className="cl-name-link">
                                {row.nome_cognome}
                              </Link>
                            </td>
                            <td>{row.health_manager_name || <span className="cl-empty">{'\u2014'}</span>}</td>
                            <td>{formatDate(row.onboarding_date)}</td>
                            <td>{formatDate(row.path_start_date)}</td>
                            <td>{formatDate(row.path_end_date)}</td>
                            <td>{formatDate(row.check_in_call_date)}</td>
                            <td style={{ textAlign: 'center' }}>{yesNoBadge(Boolean(row.flags?.check_in_completed), Boolean(row.flags_mocked?.check_in_completed))}</td>
                            <td>{formatDate(row.renewal_call_date)}</td>
                            <td style={{ textAlign: 'center' }}>{yesNoBadge(Boolean(row.flags?.contacted_for_renewal), Boolean(row.flags_mocked?.contacted_for_renewal))}</td>
                            <td style={{ textAlign: 'center' }}>{yesNoBadge(Boolean(row.flags?.renewal_completed), Boolean(row.flags_mocked?.renewal_completed))}</td>
                            <td style={{ textAlign: 'center' }}>{yesNoBadge(Boolean(row.flags?.contacted_for_review), Boolean(row.flags_mocked?.contacted_for_review))}</td>
                            <td style={{ textAlign: 'center' }}>{yesNoBadge(Boolean(row.flags?.review_completed), Boolean(row.flags_mocked?.review_completed))}</td>
                            <td style={{ textAlign: 'right' }}>
                              <Link to={`/clienti-dettaglio/${row.cliente_id}`} className="cl-action-btn" title="Dettaglio">
                                <i className="ri-eye-line"></i>
                              </Link>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {renderPagination(coordPagination, (p) => setCoordPagination(prev => ({ ...prev, page: p })))}
            </>
          )}
        </>
      )}

      {/* Content (non-review tabs) */}
      {!isReviewTab && !isCoordinatriciTab && (loading ? (
        <div className="cl-loading">
          <div className="cl-spinner" style={{ margin: '0 auto' }}></div>
          <p className="cl-loading-text">Caricamento...</p>
        </div>
      ) : error ? (
        <div className="cl-error">{error}</div>
      ) : clienti.length === 0 ? (
        <div className="cl-empty-state">
          <div className="cl-empty-icon">
            <i className={mainTab === 'scadenze' ? 'ri-calendar-check-line' : mainTab === 'insoddisfatti' ? 'ri-emotion-happy-line' : mainTab === 'ghost' ? 'ri-ghost-line' : 'ri-pause-circle-line'}></i>
          </div>
          <h5 className="cl-empty-title">
            {mainTab === 'scadenze' ? 'Nessun cliente in scadenza' : mainTab === 'insoddisfatti' ? 'Nessun cliente insoddisfatto' : mainTab === 'ghost' ? 'Nessun cliente ghost' : 'Nessun cliente in pausa'}
          </h5>
          <p className="cl-empty-desc">
            {mainTab === 'scadenze'
              ? expiryDays === 30
                ? 'Non ci sono clienti con rinnovo entro 30 giorni'
                : expiryDays === 60
                  ? 'Non ci sono clienti con rinnovo tra 30 e 60 giorni'
                  : 'Non ci sono clienti con rinnovo tra 60 e 90 giorni'
              : `Non ci sono clienti con media voti inferiore a ${satThreshold}`
            }
          </p>
        </div>
      ) : (
        <>
          <div className="cl-table-card">
            <div className="table-responsive">
              <table className="cl-table">
                <thead>
                  <tr>
                    <th style={{ minWidth: '180px' }}>Cliente</th>
                    <th style={{ minWidth: '90px' }}>Stato</th>
                    {mainTab === 'scadenze' ? (
                      <>
                        <th style={{ minWidth: '110px' }}>Scadenza</th>
                        <th style={{ minWidth: '90px', textAlign: 'center' }}>Giorni</th>
                        <th style={{ minWidth: '120px' }}>Pacchetto</th>
                      </>
                    ) : mainTab === 'insoddisfatti' ? (
                      <>
                        <th style={{ minWidth: '70px', textAlign: 'center' }}>Media</th>
                        <th style={{ minWidth: '60px', textAlign: 'center' }}>Nutri</th>
                        <th style={{ minWidth: '60px', textAlign: 'center' }}>Coach</th>
                        <th style={{ minWidth: '60px', textAlign: 'center' }}>Psico</th>
                        <th style={{ minWidth: '70px', textAlign: 'center' }}>Percorso</th>
                        <th style={{ minWidth: '110px' }}>Ultimo Check</th>
                      </>
                    ) : (
                      <>
                        <th style={{ minWidth: '120px' }}>Pacchetto</th>
                        <th style={{ minWidth: '110px' }}>Data Rinnovo</th>
                      </>
                    )}
                    <th style={{ minWidth: '120px' }}>Team</th>
                    <th style={{ textAlign: 'right', minWidth: '80px' }}>Azioni</th>
                  </tr>
                </thead>
                <tbody>
                  {clienti.map((cliente) => (
                    <tr key={cliente.cliente_id}>
                      <td>
                        <Link to={`/clienti-dettaglio/${cliente.cliente_id}`} className="cl-name-link">
                          {cliente.nome_cognome}
                        </Link>
                      </td>
                      <td>{renderStatoBadge(cliente.stato_cliente)}</td>
                      {mainTab === 'scadenze' ? (
                        <>
                          <td>
                            {cliente.data_rinnovo ? (
                              <span style={{ fontSize: '13px', fontWeight: 600, color: '#1e293b' }}>
                                {new Date(cliente.data_rinnovo).toLocaleDateString('it-IT')}
                              </span>
                            ) : <span className="cl-empty">&mdash;</span>}
                          </td>
                          <td style={{ textAlign: 'center' }}>
                            {(() => {
                              const u = getUrgencyStyle(cliente.giorni_rimanenti);
                              return (
                                <span className="cl-badge" style={{ background: u.bg, color: u.color, fontWeight: 700, fontSize: '13px', minWidth: '48px', display: 'inline-block', textAlign: 'center' }}>
                                  {cliente.giorni_rimanenti != null ? `${cliente.giorni_rimanenti}g` : '\u2014'}
                                </span>
                              );
                            })()}
                          </td>
                          <td>
                            {cliente.programma_attuale ? (
                              <span className="cl-badge" style={{ background: '#f0fdf4', color: '#166534', fontSize: '12px', fontWeight: 600 }}>
                                {cliente.programma_attuale}
                              </span>
                            ) : <span className="cl-empty">&mdash;</span>}
                          </td>
                        </>
                      ) : mainTab === 'insoddisfatti' ? (
                        <>
                          <td style={{ textAlign: 'center' }}>
                            {(() => {
                              const r = getRatingStyle(cliente.avg_rating);
                              return (
                                <span className="cl-badge" style={{ background: r.bg, color: r.color, fontWeight: 700, fontSize: '13px', minWidth: '40px', display: 'inline-block', textAlign: 'center' }}>
                                  {cliente.avg_rating != null ? cliente.avg_rating : '\u2014'}
                                </span>
                              );
                            })()}
                          </td>
                          <td style={{ textAlign: 'center' }}>
                            {(() => {
                              const r = getRatingStyle(cliente.avg_nutrizione);
                              return cliente.avg_nutrizione != null ? (
                                <span className="cl-badge" style={{ background: r.bg, color: r.color, fontWeight: 600, fontSize: '12px', minWidth: '36px', display: 'inline-block', textAlign: 'center' }}>
                                  {cliente.avg_nutrizione}
                                </span>
                              ) : <span className="cl-empty">&mdash;</span>;
                            })()}
                          </td>
                          <td style={{ textAlign: 'center' }}>
                            {(() => {
                              const r = getRatingStyle(cliente.avg_coach);
                              return cliente.avg_coach != null ? (
                                <span className="cl-badge" style={{ background: r.bg, color: r.color, fontWeight: 600, fontSize: '12px', minWidth: '36px', display: 'inline-block', textAlign: 'center' }}>
                                  {cliente.avg_coach}
                                </span>
                              ) : <span className="cl-empty">&mdash;</span>;
                            })()}
                          </td>
                          <td style={{ textAlign: 'center' }}>
                            {(() => {
                              const r = getRatingStyle(cliente.avg_psicologia);
                              return cliente.avg_psicologia != null ? (
                                <span className="cl-badge" style={{ background: r.bg, color: r.color, fontWeight: 600, fontSize: '12px', minWidth: '36px', display: 'inline-block', textAlign: 'center' }}>
                                  {cliente.avg_psicologia}
                                </span>
                              ) : <span className="cl-empty">&mdash;</span>;
                            })()}
                          </td>
                          <td style={{ textAlign: 'center' }}>
                            {(() => {
                              const r = getRatingStyle(cliente.avg_percorso);
                              return cliente.avg_percorso != null ? (
                                <span className="cl-badge" style={{ background: r.bg, color: r.color, fontWeight: 600, fontSize: '12px', minWidth: '36px', display: 'inline-block', textAlign: 'center' }}>
                                  {cliente.avg_percorso}
                                </span>
                              ) : <span className="cl-empty">&mdash;</span>;
                            })()}
                          </td>
                          <td>
                            {cliente.last_check_date ? (
                              <span style={{ fontSize: '13px', color: '#1e293b' }}>
                                {new Date(cliente.last_check_date).toLocaleDateString('it-IT')}
                              </span>
                            ) : <span className="cl-empty">&mdash;</span>}
                          </td>
                        </>
                      ) : (
                        <>
                          <td>
                            {cliente.programma_attuale ? (
                              <span className="cl-badge" style={{ background: '#f0fdf4', color: '#166534', fontSize: '12px', fontWeight: 600 }}>
                                {cliente.programma_attuale}
                              </span>
                            ) : <span className="cl-empty">&mdash;</span>}
                          </td>
                          <td>
                            {cliente.data_rinnovo ? (
                              <span style={{ fontSize: '13px', fontWeight: 600, color: '#1e293b' }}>
                                {new Date(cliente.data_rinnovo).toLocaleDateString('it-IT')}
                              </span>
                            ) : <span className="cl-empty">&mdash;</span>}
                          </td>
                        </>
                      )}
                      <td>{renderTeamCell(cliente)}</td>
                      <td style={{ textAlign: 'right' }}>
                        <Link to={`/clienti-dettaglio/${cliente.cliente_id}`} className="cl-action-btn" title="Dettaglio">
                          <i className="ri-eye-line"></i>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {mainTab === 'scadenze'
            ? renderPagination(expiryPagination, (p) => setExpiryPagination(prev => ({ ...prev, page: p })))
            : mainTab === 'insoddisfatti'
              ? renderPagination(satPagination, (p) => setSatPagination(prev => ({ ...prev, page: p })))
              : renderPagination(statusPagination, (p) => setStatusPagination(prev => ({ ...prev, page: p })))
          }
        </>
      ))}
    </div>
  );
}

export default ClientiListaHealthManager;
