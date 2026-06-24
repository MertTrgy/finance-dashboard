import { useState, useEffect } from 'react';
import api from '../services/api';

export function useMarketOverview() {
  const [indices, setIndices]   = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);

  useEffect(() => {
    api.get('/market/overview/')
      .then(({ data }) => setIndices(data.indices || []))
      .catch(() => setError('Market data unavailable'))
      .finally(() => setLoading(false));
  }, []);

  return { indices, loading, error };
}

export function useMarketNews(ticker = '^GSPC', limit = 5) {
  const [news, setNews]       = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/market/news/', { params: { ticker, limit } })
      .then(({ data }) => setNews(data.news || []))
      .catch(() => setNews([]))
      .finally(() => setLoading(false));
  }, [ticker, limit]);

  return { news, loading };
}

export function useCorrelation() {
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    api.get('/market/correlation/')
      .then(({ data }) => {
        if (data.error) setError(data.error);
        else setResult(data);
      })
      .catch(() => setError('Correlation analysis unavailable'))
      .finally(() => setLoading(false));
  }, []);

  return { result, loading, error };
}
