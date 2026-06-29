import { useState } from 'react';
import TickerSearch from './TickerSearch';
import { usePricePreview } from '../hooks/usePortfolio';

const today = () => new Date().toISOString().split('T')[0];

const fmtCcy = (n, ccy = 'USD') => {
  if (n === null || n === undefined) return '—';
  const sym = ccy === 'GBP' ? '£' : ccy === 'EUR' ? '€' : '$';
  return `${sym}${Math.abs(parseFloat(n)).toLocaleString('en-GB', {
    minimumFractionDigits: 2, maximumFractionDigits: 4,
  })}`;
};

export default function AddHoldingForm({ onAdd, onCancel }) {
  const [ticker,   setTicker]   = useState('');
  const [quantity, setQuantity] = useState('');
  const [buyDate,  setBuyDate]  = useState('');
  const [buyPrice, setBuyPrice] = useState('');
  const [saving,   setSaving]   = useState(false);
  const [error,    setError]    = useState('');

  const { preview, loading: prevLoading, error: prevError, fetchPreview, clear } = usePricePreview();

  // When user selects from autocomplete
  const handleTickerSelect = (result) => {
    setTicker(result.ticker);
    if (buyDate) fetchPreview(result.ticker, buyDate);
  };

  // When user manually edits ticker text
  const handleTickerChange = (val) => {
    setTicker(val);
    if (val && buyDate) fetchPreview(val, buyDate);
    else if (!val) clear();
  };

  const handleDateChange = (date) => {
    setBuyDate(date);
    if (ticker && date) fetchPreview(ticker, date);
    else clear();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!ticker.trim()) { setError('Ticker symbol is required.'); return; }
    if (!quantity || parseFloat(quantity) <= 0) { setError('Quantity must be greater than 0.'); return; }

    setSaving(true);
    try {
      const payload = {
        ticker:    ticker.trim().toUpperCase(),
        quantity:  parseFloat(quantity),
        buy_date:  buyDate || undefined,
        buy_price: buyPrice ? parseFloat(buyPrice) : undefined,
      };
      const result = await onAdd(payload);
      if (result?.splits_applied?.length > 0) {
        // Parent will show toast — no need for alert
      }
      onCancel();
    } catch (err) {
      setError(err.response?.data?.error || 'Could not add holding.');
    } finally {
      setSaving(false);
    }
  };

  // Compute predicted current shares for the preview
  const splitFactor        = preview?.split_factor || 1;
  const qty                = parseFloat(quantity || 0);
  const predictedAdjusted  = qty * splitFactor;

  return (
    <div className="pf-card">
      <h2 className="pf-card-title">Add holding</h2>
      {error && <div className="pf-error">{error}</div>}

      <form onSubmit={handleSubmit} className="pf-form">
        <div className="pf-form-grid">

          {/* Ticker with autocomplete */}
          <div className="pf-field">
            <label>Ticker symbol *</label>
            <TickerSearch
              value={ticker}
              onChange={handleTickerChange}
              onSelect={handleTickerSelect}
              placeholder='Type "amazon", "AMZN", or "AM"…'
            />
          </div>

          {/* Quantity */}
          <div className="pf-field">
            <label>
              Shares purchased *
              {preview?.split_factor > 1 && qty > 0 && (
                <span className="pf-label-hint">
                  {' '}→ {predictedAdjusted.toLocaleString('en-GB', { maximumFractionDigits: 6 })} today (×{splitFactor} split)
                </span>
              )}
            </label>
            <input
              className="pf-input"
              type="number" min="0.000001" step="any"
              placeholder="e.g. 0.3"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              required
            />
          </div>

          {/* Purchase date */}
          <div className="pf-field">
            <label>
              Purchase date
              <span className="pf-label-hint"> — we fetch the closing price</span>
            </label>
            <input
              className="pf-input"
              type="date" max={today()}
              value={buyDate}
              onChange={(e) => handleDateChange(e.target.value)}
            />
          </div>

          {/* Manual price override */}
          <div className="pf-field">
            <label>
              Buy price
              <span className="pf-label-hint">
                {prevLoading
                  ? ' — fetching…'
                  : preview
                    ? ` — auto: ${fmtCcy(preview.buy_price, preview.currency)}`
                    : ' — leave blank to auto-fetch'}
              </span>
            </label>
            <input
              className="pf-input"
              type="number" min="0" step="any"
              placeholder={preview ? preview.buy_price.toFixed(4) : 'Optional manual override'}
              value={buyPrice}
              onChange={(e) => setBuyPrice(e.target.value)}
            />
          </div>
        </div>

        {/* Price preview */}
        {prevLoading && (
          <div className="pf-preview loading">
            Looking up {ticker || '…'} on {buyDate}…
          </div>
        )}

        {prevError && !prevLoading && (
          <div className="pf-preview error">⚠ {prevError}</div>
        )}

        {preview && !prevLoading && (
          <div className="pf-preview success">
            <div className="pf-preview-row">
              <span className="pf-preview-label">Closing price on {preview.actual_date}</span>
              <span className="pf-preview-val">
                {fmtCcy(preview.buy_price, preview.currency)}
                <span className="pf-preview-adj"> (split-adjusted)</span>
              </span>
            </div>

            {/* Shares calculation */}
            {qty > 0 && (
              <div className="pf-shares-preview">
                <div className="pf-shares-row">
                  <span className="pf-shares-label">Original shares</span>
                  <span className="pf-shares-val">{qty.toLocaleString('en-GB', { maximumFractionDigits: 6 })}</span>
                </div>
                {preview.split_factor > 1 && (
                  <>
                    <div className="pf-shares-row pf-shares-split">
                      <span className="pf-shares-label">
                        {preview.splits.length} split(s): {preview.splits.map((s, i) => (
                          <span key={i}>{i > 0 && ', '}{s.date} ({s.ratio}:1)</span>
                        ))}
                      </span>
                      <span className="pf-shares-factor">×{splitFactor}</span>
                    </div>
                    <div className="pf-shares-row pf-shares-today">
                      <span className="pf-shares-label">Shares you hold today</span>
                      <span className="pf-shares-val pf-shares-highlight">
                        {predictedAdjusted.toLocaleString('en-GB', { maximumFractionDigits: 6 })}
                      </span>
                    </div>
                  </>
                )}
                {preview.split_factor <= 1 && (
                  <div className="pf-no-split">✓ No splits — shares unchanged since {buyDate}</div>
                )}
              </div>
            )}
          </div>
        )}

        <div className="pf-form-actions">
          <button type="button" className="pf-btn-cancel" onClick={onCancel}>Cancel</button>
          <button type="submit" className="pf-btn-submit" disabled={saving}>
            {saving ? 'Saving…' : 'Add holding'}
          </button>
        </div>
      </form>
    </div>
  );
}