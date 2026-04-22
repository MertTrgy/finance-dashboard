import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

export function useTransactions(month) {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = month ? { month } : {};
      const { data } = await api.get('/transactions/', { params });
      setTransactions(data.results ?? data);
    } catch (e) {
      setError('Could not load transactions.');
    } finally {
      setLoading(false);
    }
  }, [month]);

  useEffect(() => { fetch(); }, [fetch]);

  const addTransaction = async (payload) => {
    const { data } = await api.post('/transactions/', payload);
    setTransactions((prev) => [data, ...prev]);
    return data;
  };

  const deleteTransaction = async (id) => {
    await api.delete(`/transactions/${id}/`);
    setTransactions((prev) => prev.filter((t) => t.id !== id));
  };

  return { transactions, loading, error, refetch: fetch, addTransaction, deleteTransaction };
}

export function useCategories() {
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    api.get('/categories/').then(({ data }) => {
      setCategories(data.results ?? data);
    }).catch(() => {});
  }, []);

  const addCategory = async (payload) => {
    const { data } = await api.post('/categories/', payload);
    setCategories((prev) => [...prev, data]);
    return data;
  };

  return { categories, addCategory };
}

export function useSummary(month) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = month ? { month } : {};
    api.get('/summary/', { params })
      .then(({ data }) => setSummary(data))
      .catch(() => setSummary(null))
      .finally(() => setLoading(false));
  }, [month]);

  return { summary, loading };
}