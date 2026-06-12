import { useState, useCallback } from 'react';
import api from '../services/api';

export function useReceipt() {
  const [scanning, setScanning]   = useState(false);
  const [saving, setSaving]       = useState(false);
  const [scanResult, setScanResult] = useState(null); // structured receipt data
  const [error, setError]         = useState(null);

  /**
   * Convert a File object to base64 and send to the scan endpoint.
   * Sets scanResult on success — triggers the review modal.
   */
  const scanImage = useCallback(async (file) => {
    setScanning(true);
    setError(null);
    setScanResult(null);

    try {
      // Read file as base64
      const base64 = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload  = () => resolve(reader.result); // includes data:image/...;base64, prefix
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      const { data } = await api.post('/receipt/scan/', {
        image:     base64,
        mime_type: file.type,
      });

      setScanResult(data);
    } catch (err) {
      const msg = err.response?.data?.error || 'Receipt scanning failed.';
      setError(msg);
    } finally {
      setScanning(false);
    }
  }, []);

  /**
   * Save the reviewed receipt data as a transaction + line items.
   * payload shape matches /api/receipt/save/ body.
   */
  const saveReceipt = useCallback(async (payload) => {
    setSaving(true);
    setError(null);
    try {
      const { data } = await api.post('/receipt/save/', payload);
      setScanResult(null);
      return data;
    } catch (err) {
      const msg = err.response?.data?.error || 'Could not save receipt.';
      setError(msg);
      throw err;
    } finally {
      setSaving(false);
    }
  }, []);

  const clearResult = () => {
    setScanResult(null);
    setError(null);
  };

  return { scanning, saving, scanResult, error, scanImage, saveReceipt, clearResult };
}