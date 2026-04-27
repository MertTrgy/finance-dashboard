import { useState, useEffect } from 'react';
import api from '../services/api';

// Module-level cache so rates are only fetched once per app session
let _cache = null;

export function useCurrencies() {
  const [currencies, setCurrencies] = useState(_cache?.currencies || []);
  const [rates, setRates]           = useState(_cache?.rates || {});
  const [loading, setLoading]       = useState(!_cache);

  useEffect(() => {
    if (_cache) return;
    api.get('/currencies/')
      .then(({ data }) => {
        _cache = data;
        setCurrencies(data.currencies);
        setRates(data.rates);
      })
      .catch(() => {
        // Fallback: just GBP
        setCurrencies(['GBP']);
        setRates({});
      })
      .finally(() => setLoading(false));
  }, []);

  /**
   * Convert an amount from a given currency to GBP for preview.
   * Returns null if the rate isn't available.
   */
  const previewGBP = (amount, fromCurrency) => {
    if (!amount || fromCurrency === 'GBP') return null;
    const rate = rates[fromCurrency];
    if (!rate) return null;
    // rates are GBP→X, so to get X→GBP we divide by rate
    return (parseFloat(amount) / rate).toFixed(2);
  };

  return { currencies, rates, loading, previewGBP };
}