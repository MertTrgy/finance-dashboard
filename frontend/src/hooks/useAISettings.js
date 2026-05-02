import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

const STORAGE_KEY = 'finance_ai_settings';

const DEFAULTS = {
  provider:      'gemini',   // 'claude' | 'gemini' | 'ollama'
  anthropic_key: '',
  gemini_key:    '',
  ollama_model:  'llama3',
  ollama_url:    'http://localhost:11434',
};

export function useAISettings() {
  const [settings, setSettings] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? { ...DEFAULTS, ...JSON.parse(stored) } : DEFAULTS;
    } catch {
      return DEFAULTS;
    }
  });

  const [providerStatus, setProviderStatus] = useState(null);
  const [saving, setSaving]                 = useState(false);
  const [saveMsg, setSaveMsg]               = useState('');

  // Fetch provider status from backend on mount
  useEffect(() => {
    api.get('/ai/providers/')
      .then(({ data }) => setProviderStatus(data))
      .catch(() => {});
  }, []);

  const save = useCallback(async (updates) => {
    const next = { ...settings, ...updates };
    setSettings(next);

    // Persist to localStorage (never send keys anywhere except the backend call below)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {}

    // Push to backend so the running Django instance knows which provider to use
    setSaving(true);
    setSaveMsg('');
    try {
      const { data } = await api.post('/ai/providers/', {
        provider:     next.provider,
        anthropic_key: next.anthropic_key,
        gemini_key:    next.gemini_key,
        ollama_model:  next.ollama_model,
        ollama_url:    next.ollama_url,
      });
      setProviderStatus(data);
      setSaveMsg('Saved');
    } catch (err) {
      setSaveMsg('Could not save — is the server running?');
    } finally {
      setSaving(false);
      setTimeout(() => setSaveMsg(''), 3000);
    }
  }, [settings]);

  return { settings, providerStatus, saving, saveMsg, save };
}