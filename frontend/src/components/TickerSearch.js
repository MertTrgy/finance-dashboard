import { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';
import './TickerSearch.css';

const TYPE_LABEL = {
  EQUITY:         'Stock',
  ETF:            'ETF',
  MUTUALFUND:     'Fund',
  INDEX:          'Index',
  CRYPTOCURRENCY: 'Crypto',
};

const TYPE_COLOR = {
  EQUITY:         '#185fa5',
  ETF:            '#15803d',
  MUTUALFUND:     '#b45309',
  INDEX:          '#7c3aed',
  CRYPTOCURRENCY: '#b91c1c',
};

function useDebounce(value, delay) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export default function TickerSearch({ value, onChange, onSelect, placeholder = 'AMZN, AAPL, or type "amazon"…' }) {
  const [query,       setQuery]       = useState(value || '');
  const [results,     setResults]     = useState([]);
  const [loading,     setLoading]     = useState(false);
  const [open,        setOpen]        = useState(false);
  const [highlighted, setHighlighted] = useState(-1);
  const inputRef = useRef(null);
  const listRef  = useRef(null);

  const debouncedQuery = useDebounce(query, 300);

  // Fetch suggestions when query changes
  useEffect(() => {
    if (!debouncedQuery || debouncedQuery.length < 1) {
      setResults([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    api.get('/market/search/', { params: { q: debouncedQuery } })
      .then(({ data }) => {
        setResults(data.results || []);
        setOpen((data.results || []).length > 0);
        setHighlighted(-1);
      })
      .catch(() => setResults([]))
      .finally(() => setLoading(false));
  }, [debouncedQuery]);

  const handleSelect = useCallback((result) => {
    setQuery(result.ticker);
    setOpen(false);
    setResults([]);
    onChange?.(result.ticker);
    onSelect?.(result);
    inputRef.current?.focus();
  }, [onChange, onSelect]);

  const handleKeyDown = (e) => {
    if (!open || !results.length) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlighted((h) => Math.min(h + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlighted((h) => Math.max(h - 1, 0));
    } else if (e.key === 'Enter' && highlighted >= 0) {
      e.preventDefault();
      handleSelect(results[highlighted]);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  const handleChange = (e) => {
    const v = e.target.value.toUpperCase();
    setQuery(v);
    onChange?.(v);
  };

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (!inputRef.current?.parentElement?.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div className="ts-wrap">
      <div className="ts-input-wrap">
        <input
          ref={inputRef}
          className="pf-input ts-input"
          placeholder={placeholder}
          value={query}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => results.length > 0 && setOpen(true)}
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
        />
        {loading && <span className="ts-spinner" />}
      </div>

      {open && results.length > 0 && (
        <ul className="ts-dropdown" ref={listRef}>
          {results.map((r, i) => (
            <li
              key={r.ticker}
              className={`ts-item ${i === highlighted ? 'highlighted' : ''}`}
              onMouseDown={(e) => { e.preventDefault(); handleSelect(r); }}
              onMouseEnter={() => setHighlighted(i)}
            >
              <div className="ts-item-left">
                <span className="ts-ticker">{r.ticker}</span>
                <span
                  className="ts-type"
                  style={{
                    color:       TYPE_COLOR[r.type] || '#888',
                    background:  (TYPE_COLOR[r.type] || '#888') + '14',
                  }}
                >
                  {TYPE_LABEL[r.type] || r.type}
                </span>
              </div>
              <div className="ts-item-right">
                <span className="ts-name">{r.name}</span>
                {r.exchange && <span className="ts-exch">{r.exchange}</span>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}