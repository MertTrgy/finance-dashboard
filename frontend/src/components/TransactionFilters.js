import { useState, useEffect, useRef } from 'react';
import './TransactionFilters.css';

function useDebounce(value, ms = 400) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

export default function TransactionFilters({ categories, onChange }) {
  const [search,   setSearch]   = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo,   setDateTo]   = useState('');
  const [type,     setType]     = useState('');
  const [category, setCategory] = useState('');
  const [expanded, setExpanded] = useState(false);

  const debouncedSearch = useDebounce(search, 400);
  const prevRef         = useRef({});

  // Fire onChange only when values actually change
  useEffect(() => {
    const next = { search: debouncedSearch, dateFrom, dateTo, type, category };
    const prev = prevRef.current;
    const changed = Object.keys(next).some((k) => next[k] !== prev[k]);
    if (changed) {
      prevRef.current = next;
      onChange(next);
    }
  }, [debouncedSearch, dateFrom, dateTo, type, category]); // eslint-disable-line

  const hasFilters = search || dateFrom || dateTo || type || category;

  const clearAll = () => {
    setSearch('');
    setDateFrom('');
    setDateTo('');
    setType('');
    setCategory('');
  };

  return (
    <div className="tf-bar">
      {/* Search input — always visible */}
      <div className="tf-search-row">
        <div className="tf-search-wrap">
          <span className="tf-search-icon">⌕</span>
          <input
            type="text"
            className="tf-search-input"
            placeholder="Search transactions…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button className="tf-clear-search" onClick={() => setSearch('')}>✕</button>
          )}
        </div>
        <button
          className={`tf-filter-toggle ${expanded ? 'active' : ''} ${hasFilters && !expanded ? 'has-filters' : ''}`}
          onClick={() => setExpanded((e) => !e)}
          title="More filters"
        >
          ⊟ Filters{hasFilters && !expanded ? ' •' : ''}
        </button>
      </div>

      {/* Expanded filters */}
      {expanded && (
        <div className="tf-expanded">
          <div className="tf-filter-grid">
            <div className="tf-filter-field">
              <label>From</label>
              <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            </div>
            <div className="tf-filter-field">
              <label>To</label>
              <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            </div>
            <div className="tf-filter-field">
              <label>Type</label>
              <select value={type} onChange={(e) => setType(e.target.value)}>
                <option value="">All types</option>
                <option value="expense">Expense</option>
                <option value="income">Income</option>
              </select>
            </div>
            <div className="tf-filter-field">
              <label>Category</label>
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="">All categories</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          </div>
          {hasFilters && (
            <button className="tf-clear-all" onClick={clearAll}>
              Clear all filters
            </button>
          )}
        </div>
      )}
    </div>
  );
}