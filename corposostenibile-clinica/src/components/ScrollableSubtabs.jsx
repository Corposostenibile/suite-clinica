import { useRef, useState, useEffect, useCallback } from 'react';

/**
 * Wrapper around a `cd-subtabs` bar that adds scroll arrows
 * when the pills overflow their container.
 *
 * Usage:
 *   <ScrollableSubtabs style={{ marginBottom: '20px' }}>
 *     <button className="cd-subtab active green">…</button>
 *     …
 *   </ScrollableSubtabs>
 */
export default function ScrollableSubtabs({ children, className = '', style, ...rest }) {
  const ref = useRef(null);
  const [canLeft, setCanLeft] = useState(false);
  const [canRight, setCanRight] = useState(false);

  const update = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    setCanLeft(el.scrollLeft > 0);
    setCanRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 1);
  }, []);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    update();
    el.addEventListener('scroll', update, { passive: true });
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => {
      el.removeEventListener('scroll', update);
      ro.disconnect();
    };
  }, [update]);

  const scroll = useCallback((dir) => {
    const el = ref.current;
    if (!el) return;
    el.scrollBy({ left: dir * 200, behavior: 'smooth' });
  }, []);

  return (
    <div className={`cd-subtabs-wrapper ${className}`} style={style} {...rest}>
      {canLeft && (
        <button className="cd-subtabs-arrow cd-subtabs-arrow-left" onClick={() => scroll(-1)} aria-label="Scorri a sinistra">
          <i className="ri-arrow-left-s-line"></i>
        </button>
      )}
      <div className="cd-subtabs" ref={ref}>
        {children}
      </div>
      {canRight && (
        <button className="cd-subtabs-arrow cd-subtabs-arrow-right" onClick={() => scroll(1)} aria-label="Scorri a destra">
          <i className="ri-arrow-right-s-line"></i>
        </button>
      )}
    </div>
  );
}
