import { useState, useRef, useEffect, useCallback } from 'react';
import './DatePicker.css';

const MONTHS_IT = [
  'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
  'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'
];
const DAYS_IT = ['Lu', 'Ma', 'Me', 'Gi', 'Ve', 'Sa', 'Do'];

function parseDateStr(str) {
  if (!str) return null;
  const [y, m, d] = str.split('-').map(Number);
  if (!y || !m || !d) return null;
  return new Date(y, m - 1, d);
}

function toISODate(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function formatDisplay(str) {
  if (!str) return '';
  const d = parseDateStr(str);
  if (!d) return str;
  return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`;
}

function getDaysInMonth(year, month) {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfWeek(year, month) {
  const day = new Date(year, month, 1).getDay();
  return day === 0 ? 6 : day - 1; // Monday = 0
}

export default function DatePicker({
  value,
  onChange,
  className = '',
  disabled = false,
  placeholder = 'gg/mm/aaaa',
  name,
  style,
  min,
  max,
  ...rest
}) {
  const [open, setOpen] = useState(false);
  const [viewYear, setViewYear] = useState(() => {
    const d = parseDateStr(value);
    return d ? d.getFullYear() : new Date().getFullYear();
  });
  const [viewMonth, setViewMonth] = useState(() => {
    const d = parseDateStr(value);
    return d ? d.getMonth() : new Date().getMonth();
  });
  const [dropUp, setDropUp] = useState(false);
  const wrapRef = useRef(null);
  const calRef = useRef(null);

  // Sync view to value when it changes externally
  useEffect(() => {
    const d = parseDateStr(value);
    if (d) {
      setViewYear(d.getFullYear());
      setViewMonth(d.getMonth());
    }
  }, [value]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open]);

  // Position calendar above or below
  useEffect(() => {
    if (!open || !wrapRef.current) return;
    const rect = wrapRef.current.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    setDropUp(spaceBelow < 320 && rect.top > 320);
  }, [open]);

  const fireChange = useCallback((isoVal) => {
    if (!onChange) return;
    const syntheticEvent = {
      target: { value: isoVal, name: name || '' },
      currentTarget: { value: isoVal, name: name || '' },
      preventDefault: () => {},
      stopPropagation: () => {},
    };
    onChange(syntheticEvent);
  }, [onChange, name]);

  const handleSelect = (day) => {
    const iso = toISODate(new Date(viewYear, viewMonth, day));
    fireChange(iso);
    setOpen(false);
  };

  const handleClear = (e) => {
    e.stopPropagation();
    fireChange('');
    setOpen(false);
  };

  const prevMonth = () => {
    if (viewMonth === 0) { setViewMonth(11); setViewYear(y => y - 1); }
    else setViewMonth(m => m - 1);
  };

  const nextMonth = () => {
    if (viewMonth === 11) { setViewMonth(0); setViewYear(y => y + 1); }
    else setViewMonth(m => m + 1);
  };

  const today = new Date();
  const todayISO = toISODate(today);
  const selectedDate = parseDateStr(value);
  const daysInMonth = getDaysInMonth(viewYear, viewMonth);
  const firstDay = getFirstDayOfWeek(viewYear, viewMonth);

  const minDate = parseDateStr(min);
  const maxDate = parseDateStr(max);

  const isDisabledDay = (day) => {
    const d = new Date(viewYear, viewMonth, day);
    if (minDate && d < minDate) return true;
    if (maxDate && d > maxDate) return true;
    return false;
  };

  const cells = [];
  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  return (
    <div className={`dp-wrap${disabled ? ' dp-disabled' : ''}`} ref={wrapRef} style={style}>
      <div
        className={`dp-input-wrap ${className}`}
        onClick={() => { if (!disabled) setOpen(!open); }}
        role="button"
        tabIndex={disabled ? -1 : 0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); if (!disabled) setOpen(!open); } }}
      >
        <span className={`dp-display ${value ? '' : 'dp-placeholder'}`}>
          {value ? formatDisplay(value) : placeholder}
        </span>
        <span className="dp-icons">
          {value && !disabled && (
            <span className="dp-clear" onClick={handleClear} title="Cancella data">
              <i className="ri-close-line"></i>
            </span>
          )}
          <i className="ri-calendar-line dp-cal-icon"></i>
        </span>
      </div>

      {open && (
        <div className="dp-overlay" onClick={() => setOpen(false)}>
          <div className="dp-dropdown dp-centered" ref={calRef} onClick={(e) => e.stopPropagation()}>
            <div className="dp-nav">
              <button type="button" className="dp-nav-btn" onClick={prevMonth}><i className="ri-arrow-left-s-line"></i></button>
              <span className="dp-nav-label">{MONTHS_IT[viewMonth]} {viewYear}</span>
              <button type="button" className="dp-nav-btn" onClick={nextMonth}><i className="ri-arrow-right-s-line"></i></button>
            </div>
            <div className="dp-grid dp-days-header">
              {DAYS_IT.map(d => <span key={d} className="dp-day-label">{d}</span>)}
            </div>
            <div className="dp-grid dp-days">
              {cells.map((day, i) => {
                if (day === null) return <span key={`e-${i}`} className="dp-cell dp-empty"></span>;
                const iso = toISODate(new Date(viewYear, viewMonth, day));
                const isSelected = selectedDate && iso === toISODate(selectedDate);
                const isToday = iso === todayISO;
                const dayDisabled = isDisabledDay(day);
                return (
                  <button
                    type="button"
                    key={day}
                    className={`dp-cell${isSelected ? ' dp-selected' : ''}${isToday ? ' dp-today' : ''}${dayDisabled ? ' dp-day-disabled' : ''}`}
                    onClick={() => { if (!dayDisabled) handleSelect(day); }}
                    disabled={dayDisabled}
                  >
                    {day}
                  </button>
                );
              })}
            </div>
            <div className="dp-footer">
              <button type="button" className="dp-today-btn" onClick={() => {
                setViewYear(today.getFullYear());
                setViewMonth(today.getMonth());
                handleSelect(today.getDate());
              }}>Oggi</button>
            </div>
          </div>
        </div>
      )}

      {/* Hidden native input for form compatibility */}
      <input type="hidden" name={name} value={value || ''} {...rest} />
    </div>
  );
}
