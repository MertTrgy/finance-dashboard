import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

export function useBudgets(month) {
  const [budgets, setBudgets] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const params = month ? { month } : {};
      const { data } = await api.get('/budgets/', { params });
      setBudgets(data.results ?? data);
    } catch {
      setBudgets([]);
    } finally {
      setLoading(false);
    }
  }, [month]);

  useEffect(() => { fetch(); }, [fetch]);

  const upsertBudget = async (categoryId, limit, month) => {
    // Check if one already exists for this category+month
    const existing = budgets.find(
      (b) => b.category === categoryId && b.month === month
    );
    if (existing) {
      const { data } = await api.patch(`/budgets/${existing.id}/`, { limit });
      setBudgets((prev) => prev.map((b) => (b.id === existing.id ? data : b)));
      return data;
    } else {
      const { data } = await api.post('/budgets/', { category: categoryId, limit, month });
      setBudgets((prev) => [...prev, data]);
      return data;
    }
  };

  const deleteBudget = async (id) => {
    await api.delete(`/budgets/${id}/`);
    setBudgets((prev) => prev.filter((b) => b.id !== id));
  };

  return { budgets, loading, upsertBudget, deleteBudget, refetch: fetch };
}