import { useState, useEffect } from 'react';
import api from '../services/api';

export function useRecurring() {
  const [rules, setRules]     = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/recurring/')
      .then(({ data }) => setRules(data.results ?? data))
      .catch(() => setRules([]))
      .finally(() => setLoading(false));
  }, []);

  const addRule = async (payload) => {
    const { data } = await api.post('/recurring/', payload);
    setRules((prev) => [...prev, data]);
    return data;
  };

  const toggleRule = async (rule) => {
    const { data } = await api.patch(`/recurring/${rule.id}/`, { active: !rule.active });
    setRules((prev) => prev.map((r) => (r.id === rule.id ? data : r)));
    return data;
  };

  const deleteRule = async (id) => {
    await api.delete(`/recurring/${id}/`);
    setRules((prev) => prev.filter((r) => r.id !== id));
  };

  return { rules, loading, addRule, toggleRule, deleteRule };
}