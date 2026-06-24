import { useState, useEffect } from 'react';
import api from '../services/api';

export function usePortfolio() {
  const [portfolio, setPortfolio] = useState(null); // full response with totals
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);

  const fetch = () => {
    setLoading(true);
    api.get('/portfolio/')
      .then(({ data }) => setPortfolio(data))
      .catch(() => setError('Could not load portfolio'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetch(); }, []);

  const addHolding = async (payload) => {
    const { data } = await api.post('/portfolio/', payload);
    fetch(); // refresh with live prices
    return data;
  };

  const removeHolding = async (id) => {
    await api.delete(`/portfolio/${id}/`);
    setPortfolio((prev) => prev ? {
      ...prev,
      holdings: prev.holdings.filter((h) => h.id !== id),
    } : prev);
  };

  return {
    holdings:       portfolio?.holdings || [],
    totalValue:     portfolio?.total_value || 0,
    totalCost:      portfolio?.total_cost  || 0,
    totalGain:      portfolio?.total_gain  || 0,
    totalGainPct:   portfolio?.total_gain_pct || 0,
    loading, error,
    addHolding, removeHolding, refetch: fetch,
  };
}
