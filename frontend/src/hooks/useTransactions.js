import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

export function useTransactions(month, filters = {}) {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState(null);
  const [pagination, setPagination]     = useState({ count: 0, pages: 1, page: 1 });

  const fetch = useCallback(async (page = 1) => {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: 20 };
      if (month)            params.month     = month;
      if (filters.search)   params.search    = filters.search;
      if (filters.dateFrom) params.date_from = filters.dateFrom;
      if (filters.dateTo)   params.date_to   = filters.dateTo;
      if (filters.type)     params.type      = filters.type;
      if (filters.category) params.category  = filters.category;

      const { data } = await api.get('/transactions/', { params });

      // Handle both paginated and non-paginated responses
      if (data.results !== undefined) {
        setTransactions(data.results);
        setPagination({
          count: data.count,
          pages: data.pages || 1,
          page,
        });
      } else {
        setTransactions(Array.isArray(data) ? data : []);
        setPagination({ count: data.length || 0, pages: 1, page: 1 });
      }
    } catch {
      setError('Could not load transactions.');
    } finally {
      setLoading(false);
    }
  }, [month, filters.search, filters.dateFrom, filters.dateTo, filters.type, filters.category]); // eslint-disable-line

  useEffect(() => { fetch(1); }, [fetch]);

  const goToPage = (page) => fetch(page);

  const addTransaction = async (payload) => {
    const { data } = await api.post('/transactions/', payload);
    // Refresh the current view to respect filters/pagination
    await fetch(pagination.page);
    return data;
  };

  const editTransaction = async (id, payload) => {
    const { data } = await api.patch(`/transactions/${id}/`, payload);
    setTransactions((prev) => prev.map((t) => (t.id === id ? data : t)));
    return data;
  };

  const deleteTransaction = async (id) => {
    await api.delete(`/transactions/${id}/`);
    setTransactions((prev) => prev.filter((t) => t.id !== id));
  };

  return {
    transactions, loading, error, pagination, goToPage,
    refetch: fetch, addTransaction, editTransaction, deleteTransaction,
  };
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

  const updateCategory = async (id, payload) => {
    const { data } = await api.patch(`/categories/${id}/`, payload);
    setCategories((prev) => prev.map((c) => (c.id === id ? data : c)));
    return data;
  };

  const deleteCategory = async (id) => {
    await api.delete(`/categories/${id}/`);
    setCategories((prev) => prev.filter((c) => c.id !== id));
  };

  return { categories, addCategory, updateCategory, deleteCategory };
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