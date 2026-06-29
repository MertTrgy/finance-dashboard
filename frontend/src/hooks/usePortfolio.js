import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

export function usePortfolio() {
  const [portfolio, setPortfolio] = useState(null);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetch = useCallback((silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    api.get('/portfolio/')
      .then(({ data }) => setPortfolio(data))
      .catch((err) => setError(err.response?.data?.error || 'Could not load portfolio'))
      .finally(() => { setLoading(false); setRefreshing(false); });
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  // ── Refresh — clears cache, re-fetches live prices ──────────────────────
  const refresh = async () => {
    setRefreshing(true);
    try {
      await api.post('/portfolio/refresh/');
    } catch {
      // ignore — will still re-fetch
    }
    fetch(true);
  };

  const addHolding = async (payload) => {
    const { data } = await api.post('/portfolio/', payload);
    await fetch(true);
    return data;
  };

  const removeHolding = async (id) => {
    await api.delete(`/portfolio/${id}/`);
    setPortfolio((prev) =>
      prev ? { ...prev, holdings: prev.holdings.filter((h) => h.id !== id) } : prev
    );
  };

  return {
    holdings:       portfolio?.holdings || [],
    totalValue:     portfolio?.total_value   || 0,
    totalCost:      portfolio?.total_cost    || 0,
    totalGain:      portfolio?.total_gain    || 0,
    totalGainPct:   portfolio?.total_gain_pct || 0,
    loading,
    refreshing,
    error,
    refresh,
    addHolding,
    removeHolding,
    refetch: fetch,
  };
}

// ── Price preview hook — call when user picks a date ─────────────────────────
export function usePricePreview() {
  const [preview,  setPreview]  = useState(null);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState(null);

  const fetchPreview = useCallback(async (ticker, date) => {
    if (!ticker || !date || ticker.length < 1 || date.length < 10) {
      setPreview(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    setPreview(null);
    try {
      const { data } = await api.get('/market/historical-price/', {
        params: { ticker: ticker.toUpperCase(), date },
      });
      setPreview(data);
    } catch (err) {
      setError(err.response?.data?.error || 'Could not fetch price for that date.');
      setPreview(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = () => { setPreview(null); setError(null); };

  return { preview, loading, error, fetchPreview, clear };
}