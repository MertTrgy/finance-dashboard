import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { usePortfolio } from '../hooks/usePortfolio';
import { useCorrelation } from '../hooks/useMarket';
import { useToast, ToastContainer } from '../components/Toast';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import './Portfolio.css';

const fmt = (n, currency = 'USD') => {
  const sym = currency === 'GBP' ? '£' : '$';
  return `${sym}${Math.abs(parseFloat(n || 0)).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const fmtGBP = (n) => `£${parseFloat(n || 0).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const today = () => new Date().toISOString().split('T')[0];

const BLANK = { ticker: '', quantity: '', buy_price: '', buy_date: today() };

export default function Portfolio() {
  const navigate    = useNavigate();
  const { logout }  = useAuth();
  const { toasts, toast } = useToast();
  const {
    holdings, totalValue, totalCost, totalGain, totalGainPct,
    loading, error, addHolding, removeHolding,
  } = usePortfolio();
  const { result: corr, loading: corrLoading, error: corrError } = useCorrelation();

  const [form, setForm]       = useState(BLANK);
  const [saving, setSaving]   = useState(false);
  const [formErr, setFormErr] = useState('');
  const [showForm, setShowForm] = useState(false);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleAdd = async (e) => {
    e.preventDefault();
    setFormErr('');
    if (!form.ticker) { setFormErr('Ticker is required.'); return; }
    if (!form.quantity || parseFloat(form.quantity) <= 0) { setFormErr('Enter a valid quantity.'); return; }
    setSaving(true);
    try {
      await addHolding({
        ticker:    form.ticker.toUpperCase(),
        quantity:  parseFloat(form.quantity),
        buy_price: form.buy_price ? parseFloat(form.buy_price) : null,
        buy_date:  form.buy_date || null,
      });
      setForm(BLANK);
      setShowForm(false);
      toast.success(`${form.ticker.toUpperCase()} added to portfolio`);
    } catch (err) {
      const d = err.response?.data;
      setFormErr(d ? Object.values(d).flat()[0] : 'Could not add holding.');
    } finally {
      setSaving(false);
    }
  };

  const handleRemove = async (h) => {
    if (!window.confirm(`Remove ${h.ticker} from portfolio?`)) return;
    try {
      await removeHolding(h.id);
      toast.success(`${h.ticker} removed`);
    } catch {
      toast.error('Could not remove holding.');
    }
  };

  const corrColor = corr?.direction === 'inverse' ? '#b91c1c'
                  : corr?.direction === 'positive' ? '#15803d' : '#888';

  return (
    <div className="pf-page">
      <header className="dash-header">
        <button className="back-btn" onClick={() => navigate('/')}>← Dashboard</button>
        <span className="dash-logo">Finance</span>
        <button className="logout-btn" onClick={() => { logout(); navigate('/login'); }}>Sign out</button>
      </header>

      <main className="pf-main">
        <div className="pf-title-row">
          <div>
            <h1 className="pf-heading">Portfolio</h1>
            <p className="pf-sub">Track your stocks and see how they correlate with your spending</p>
          </div>
          <button className="add-btn" onClick={() => setShowForm((s) => !s)}>
            {showForm ? 'Cancel' : '+ Add holding'}
          </button>
        </div>

        {/* Add holding form */}
        {showForm && (
          <div className="pf-card">
            <h2 className="pf-card-title">New holding</h2>
            {formErr && <div className="pf-error">{formErr}</div>}
            <form onSubmit={handleAdd} className="pf-form">
              <div className="pf-form-grid">
                <div className="tf-field">
                  <label>Ticker symbol</label>
                  <input
                    placeholder="AAPL, TSLA, ^FTSE…"
                    value={form.ticker}
                    onChange={(e) => set('ticker', e.target.value)}
                    className="pf-input"
                    required
                  />
                </div>
                <div className="tf-field">
                  <label>Shares owned</label>
                  <input
                    type="number" min="0.0001" step="any" placeholder="10"
                    value={form.quantity}
                    onChange={(e) => set('quantity', e.target.value)}
                    className="pf-input"
                    required
                  />
                </div>
                <div className="tf-field">
                  <label>Buy price (optional)</label>
                  <input
                    type="number" min="0" step="any" placeholder="150.00"
                    value={form.buy_price}
                    onChange={(e) => set('buy_price', e.target.value)}
                    className="pf-input"
                  />
                </div>
                <div className="tf-field">
                  <label>Buy date (optional)</label>
                  <input
                    type="date" value={form.buy_date}
                    onChange={(e) => set('buy_date', e.target.value)}
                    className="pf-input"
                  />
                </div>
              </div>
              <button type="submit" className="auth-btn" disabled={saving} style={{ marginTop: '0.5rem' }}>
                {saving ? 'Looking up…' : 'Add holding'}
              </button>
              <p className="pf-hint">
                Use Yahoo Finance ticker symbols — e.g. AAPL (Apple), TSLA (Tesla),
                SGLN.L (Invesco Gold), ^FTSE (FTSE 100 index watchlist)
              </p>
            </form>
          </div>
        )}

        {/* Portfolio summary cards */}
        {holdings.length > 0 && (
          <div className="pf-summary-grid">
            <div className="pf-summary-card">
              <span className="pf-summary-label">Total value</span>
              <span className="pf-summary-value">{fmt(totalValue)}</span>
            </div>
            <div className="pf-summary-card">
              <span className="pf-summary-label">Cost basis</span>
              <span className="pf-summary-value">{fmt(totalCost)}</span>
            </div>
            <div className={`pf-summary-card ${totalGain >= 0 ? 'gain' : 'loss'}`}>
              <span className="pf-summary-label">Total gain / loss</span>
              <span className="pf-summary-value">
                {totalGain >= 0 ? '+' : ''}{fmt(totalGain)}
                <span className="pf-summary-pct">({totalGainPct >= 0 ? '+' : ''}{parseFloat(totalGainPct).toFixed(2)}%)</span>
              </span>
            </div>
          </div>
        )}

        {/* Holdings table */}
        <div className="pf-card">
          <h2 className="pf-card-title">Holdings</h2>
          {loading ? (
            <div className="pf-skeleton-stack">
              {[...Array(3)].map((_, i) => <div key={i} className="tl-skeleton" />)}
            </div>
          ) : error ? (
            <p className="pf-error">{error}</p>
          ) : holdings.length === 0 ? (
            <div className="pf-empty">
              <p className="tl-empty-text">No holdings yet</p>
              <p className="tl-empty-sub">Add your first stock above</p>
            </div>
          ) : (
            <div className="pf-table-wrap">
              <table className="pf-table">
                <thead>
                  <tr>
                    <th>Ticker</th>
                    <th>Shares</th>
                    <th>Buy price</th>
                    <th>Current</th>
                    <th>Today</th>
                    <th>Value</th>
                    <th>Gain / Loss</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((h) => (
                    <tr key={h.id}>
                      <td>
                        <span className="pf-ticker">{h.ticker}</span>
                        <span className="pf-name">{h.name}</span>
                      </td>
                      <td>{parseFloat(h.quantity).toLocaleString()}</td>
                      <td>{h.buy_price ? fmt(h.buy_price) : '—'}</td>
                      <td className="pf-mono">{fmt(h.current_price)}</td>
                      <td className={h.change_pct >= 0 ? 'pf-up' : 'pf-down'}>
                        {h.change_pct >= 0 ? '▲' : '▼'} {Math.abs(h.change_pct).toFixed(2)}%
                      </td>
                      <td className="pf-mono">{fmt(h.current_value)}</td>
                      <td className={h.gain >= 0 ? 'pf-up' : 'pf-down'}>
                        {h.gain >= 0 ? '+' : ''}{fmt(h.gain)}
                        <span className="pf-pct"> ({h.gain_pct >= 0 ? '+' : ''}{h.gain_pct.toFixed(2)}%)</span>
                      </td>
                      <td>
                        <button className="pf-remove" onClick={() => handleRemove(h)}>✕</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Spending vs market correlation */}
        <div className="pf-card">
          <h2 className="pf-card-title">Spending vs market correlation</h2>

          {corrLoading ? (
            <div className="pf-skeleton-stack">
              {[...Array(2)].map((_, i) => <div key={i} className="tl-skeleton" />)}
            </div>
          ) : corrError || corr?.error ? (
            <div className="pf-notice pf-notice--warn">
              {corrError || corr?.error}
            </div>
          ) : corr && (
            <>
              {/* Summary */}
              <div className="corr-summary">
                <div className="corr-coef" style={{ color: corrColor }}>
                  {corr.correlation > 0 ? '+' : ''}{corr.correlation?.toFixed(2)}
                </div>
                <div className="corr-meta">
                  <span className="corr-strength">{corr.strength} {corr.direction} correlation</span>
                  <span className="corr-index">vs {corr.best_index} · {corr.data_points} months data</span>
                </div>
              </div>

              <p className="corr-interpretation">{corr.interpretation}</p>

              {/* Chart */}
              {corr.monthly_data?.length > 2 && (
                <div style={{ marginTop: '1rem' }}>
                  <p className="chart-section-label">Monthly spending vs market return</p>
                  <ResponsiveContainer width="100%" height={180}>
                    <LineChart data={corr.monthly_data} margin={{ left: 0, right: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0ede8" />
                      <XAxis dataKey="month" tick={{ fontFamily: 'DM Sans', fontSize: 10, fill: '#aaa' }} axisLine={false} tickLine={false} />
                      <YAxis yAxisId="spending" tick={{ fontFamily: 'DM Sans', fontSize: 10, fill: '#aaa' }} axisLine={false} tickLine={false} tickFormatter={(v) => `£${v}`} width={55} />
                      <YAxis yAxisId="market" orientation="right" tick={{ fontFamily: 'DM Sans', fontSize: 10, fill: '#aaa' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} width={40} />
                      <Tooltip
                        contentStyle={{ fontFamily: 'DM Sans', fontSize: 12, background: '#1a1a1a', border: 'none', borderRadius: 8, color: '#fff' }}
                        formatter={(val, name) => name === 'spending' ? [`£${val}`, 'Spending'] : [`${val}%`, 'Market return']}
                      />
                      <ReferenceLine yAxisId="market" y={0} stroke="#e2e0da" />
                      <Line yAxisId="spending" type="monotone" dataKey="spending" stroke="#1a1a1a" strokeWidth={2} dot={false} />
                      <Line yAxisId="market"   type="monotone" dataKey="market_return" stroke={corrColor} strokeWidth={2} dot={false} strokeDasharray="4 2" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Prediction */}
              {corr.prediction && (
                <div className="corr-prediction">
                  <div className="corr-pred-header">
                    <span className="corr-pred-title">Spending prediction for {corr.prediction.next_month}</span>
                    <span className={`corr-confidence conf-${corr.prediction.confidence}`}>
                      {corr.prediction.confidence} confidence
                    </span>
                  </div>
                  <div className="corr-pred-amount">{fmtGBP(corr.prediction.predicted_spending)}</div>
                  <p className="corr-pred-basis">
                    Based on {corr.best_index} currently at {corr.prediction.current_mkt_return >= 0 ? '+' : ''}{corr.prediction.current_mkt_return}% this month
                    and your historical spending pattern.
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </main>

      <ToastContainer toasts={toasts} />
    </div>
  );
}
