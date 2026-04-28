import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

// ── Spend forecasting ─────────────────────────────────────────────────────────
export function useForecasts() {
  const [forecasts, setForecasts]   = useState([]);
  const [nextMonth, setNextMonth]   = useState('');
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState(null);

  useEffect(() => {
    api.get('/ml/forecast/')
      .then(({ data }) => {
        setForecasts(data.forecasts);
        setNextMonth(data.next_month);
      })
      .catch(() => setError('Forecast unavailable — add more transactions first.'))
      .finally(() => setLoading(false));
  }, []);

  return { forecasts, nextMonth, loading, error };
}

// ── Anomaly detection ─────────────────────────────────────────────────────────
export function useAnomalies(month) {
  const [anomalyIds, setAnomalyIds] = useState(new Set());
  const [loading, setLoading]       = useState(true);

  const fetch = useCallback(() => {
    setLoading(true);
    const params = month ? { month } : {};
    api.get('/ml/anomalies/', { params })
      .then(({ data }) => setAnomalyIds(new Set(data.anomaly_ids)))
      .catch(() => setAnomalyIds(new Set()))
      .finally(() => setLoading(false));
  }, [month]);

  useEffect(() => { fetch(); }, [fetch]);

  return { anomalyIds, loading };
}

// ── Category suggestion ───────────────────────────────────────────────────────
export function useCategorySuggestion() {
  const [suggestion, setSuggestion] = useState(null);
  const [loading, setLoading]       = useState(false);

  const suggest = useCallback(async (note) => {
    if (!note || note.length < 3) { setSuggestion(null); return; }
    setLoading(true);
    try {
      const { data } = await api.post('/ml/suggest-category/', { note });
      // Only show suggestion if confidence is reasonable
      if (data.suggestion && data.suggestion.confidence >= 0.3) {
        setSuggestion(data.suggestion);
      } else {
        setSuggestion(null);
      }
    } catch {
      setSuggestion(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = () => setSuggestion(null);

  return { suggestion, loading, suggest, clear };
}