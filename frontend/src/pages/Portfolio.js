import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { usePortfolio } from '../hooks/usePortfolio';
import { useCorrelation } from '../hooks/useMarket';
import { useToast, ToastContainer } from '../components/Toast';
import AddHoldingForm from '../components/AddHoldingForm';
import HoldingsTable  from '../components/HoldingsTable';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import './Portfolio.css';

const fmtGBP = (n) =>
  n !== null && n !== undefined
    ? `£${parseFloat(n).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : '—';

const fmtCcy = (n, ccy = 'USD') => {
  if (n === null || n === undefined) return '—';
  const sym = ccy === 'GBP' ? '£' : ccy === 'EUR' ? '€' : '$';
  return `${sym}${Math.abs(parseFloat(n)).toLocaleString('en-GB', {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  })}`;
};

const fmtPct = (n) =>
  n !== null && n !== undefined
    ? `${parseFloat(n) >= 0 ? '+' : ''}${parseFloat(n).toFixed(2)}%`
    : '—';

export default function Portfolio() {
  const navigate          = useNavigate();
  const { logout }        = useAuth();
  const { toasts, toast } = useToast();

  const {
    holdings, totalValue, totalCost, totalGain, totalGainPct,
    loading, refreshing, error,
    refresh, addHolding, removeHolding,
  } = usePortfolio();

  const { result: corr, loading: corrLoading, error: corrError } = useCorrelation();

  const [showForm, setShowForm] = useState(false);

  const handleAdd = async (payload) => {
    try {
      const result = await addHolding(payload);
      if (result?.splits_applied?.length > 0) {
        const s = result.splits_applied;
        toast.success(
          `${payload.ticker} added · ${s.length} split(s) found — ` +
          `${payload.quantity} shares → ${parseFloat(result.adjusted_quantity).toLocaleString()} today`
        );
      } else {
        toast.success(`${payload.ticker} added to portfolio`);
      }
      return result;
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not add holding.');
      throw err;
    }
  };

  const handleRemove = async (h) => {
    if (!window.confirm(`Remove ${h.ticker} from your portfolio?`)) return;
    try {
      await removeHolding(h.id);
      toast.success(`${h.ticker} removed`);
    } catch {
      toast.error('Could not remove holding.');
    }
  };

  const handleRefresh = async () => {
    await refresh();
    toast.success('Prices refreshed from Yahoo Finance');
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
        {/* Title */}
        <div className="pf-title-row">
          <div>
            <h1 className="pf-heading">Portfolio</h1>
            <p className="pf-sub">Live prices · Split-adjusted history · Spending correlation</p>
          </div>
          <div className="pf-title-actions">
            <button
              className="pf-btn-refresh"
              onClick={handleRefresh}
              disabled={refreshing || loading}
            >
              {refreshing ? '⟳ Refreshing…' : '⟳ Refresh prices'}
            </button>
            <button className="add-btn" onClick={() => setShowForm((s) => !s)}>
              {showForm ? '✕ Cancel' : '+ Add holding'}
            </button>
          </div>
        </div>

        {/* Add form */}
        {showForm && (
          <AddHoldingForm
            onAdd={handleAdd}
            onCancel={() => setShowForm(false)}
          />
        )}

        {/* Summary cards */}
        {holdings.length > 0 && (
          <div className="pf-summary-grid">
            <div className="pf-summary-card">
              <span className="pf-summary-label">Total value today</span>
              <span className="pf-summary-value">{fmtCcy(totalValue)}</span>
            </div>
            <div className="pf-summary-card">
              <span className="pf-summary-label">Total invested</span>
              <span className="pf-summary-value">{fmtCcy(totalCost)}</span>
            </div>
            <div className={`pf-summary-card ${totalGain >= 0 ? 'gain' : 'loss'}`}>
              <span className="pf-summary-label">Total return</span>
              <span className="pf-summary-value">
                {totalGain >= 0 ? '+' : ''}{fmtCcy(totalGain)}
                <span className="pf-summary-pct"> ({fmtPct(totalGainPct)})</span>
              </span>
            </div>
          </div>
        )}

        {/* Holdings */}
        <div className="pf-card">
          <div className="pf-card-header">
            <h2 className="pf-card-title">Holdings</h2>
            <span className="pf-card-hint">
              "Original" = shares purchased · "Today" = shares after all splits
            </span>
          </div>

          {loading ? (
            <div className="pf-skeleton-stack">
              {[...Array(3)].map((_, i) => <div key={i} className="pf-skeleton" />)}
            </div>
          ) : error ? (
            <div className="pf-error">{error}</div>
          ) : (
            <HoldingsTable holdings={holdings} onRemove={handleRemove} />
          )}
        </div>

        {/* Correlation */}
        <div className="pf-card">
          <h2 className="pf-card-title">Spending vs market correlation</h2>
          {corrLoading ? (
            <div className="pf-skeleton-stack">
              {[...Array(2)].map((_, i) => <div key={i} className="pf-skeleton" />)}
            </div>
          ) : (corrError || corr?.error) ? (
            <div className="pf-notice--warn">{corrError || corr?.error}</div>
          ) : corr ? (
            <>
              <div className="corr-summary">
                <div className="corr-coef" style={{ color: corrColor }}>
                  {corr.correlation >= 0 ? '+' : ''}{corr.correlation?.toFixed(2)}
                </div>
                <div className="corr-meta">
                  <span className="corr-strength">{corr.strength} {corr.direction} correlation</span>
                  <span className="corr-index">vs {corr.best_index} · {corr.data_points} months</span>
                </div>
              </div>
              <p className="corr-interpretation">{corr.interpretation}</p>
              {corr.monthly_data?.length > 2 && (
                <ResponsiveContainer width="100%" height={180}>
                  <LineChart data={corr.monthly_data} margin={{ left: 0, right: 8, top: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0ede8" />
                    <XAxis dataKey="month" tick={{ fontFamily:'DM Sans', fontSize:10, fill:'#aaa' }} axisLine={false} tickLine={false}/>
                    <YAxis yAxisId="s" tick={{ fontFamily:'DM Sans', fontSize:10, fill:'#aaa' }} axisLine={false} tickLine={false} tickFormatter={(v) => `£${v}`} width={55}/>
                    <YAxis yAxisId="m" orientation="right" tick={{ fontFamily:'DM Sans', fontSize:10, fill:'#aaa' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} width={40}/>
                    <Tooltip contentStyle={{ fontFamily:'DM Sans', fontSize:12, background:'#1a1a1a', border:'none', borderRadius:8, color:'#fff' }} formatter={(val, name) => name === 'spending' ? [`£${val}`, 'Spending'] : [`${val}%`, 'Market']}/>
                    <ReferenceLine yAxisId="m" y={0} stroke="#e2e0da"/>
                    <Line yAxisId="s" type="monotone" dataKey="spending"      stroke="#1a1a1a" strokeWidth={2} dot={false}/>
                    <Line yAxisId="m" type="monotone" dataKey="market_return" stroke={corrColor} strokeWidth={2} dot={false} strokeDasharray="4 2"/>
                  </LineChart>
                </ResponsiveContainer>
              )}
              {corr.prediction && (
                <div className="corr-prediction">
                  <div className="corr-pred-header">
                    <span className="corr-pred-title">Prediction for {corr.prediction.next_month}</span>
                    <span className={`corr-confidence conf-${corr.prediction.confidence}`}>
                      {corr.prediction.confidence} confidence
                    </span>
                  </div>
                  <div className="corr-pred-amount">{fmtGBP(corr.prediction.predicted_spending)}</div>
                  <p className="corr-pred-basis">
                    Based on {corr.best_index} at {corr.prediction.current_mkt_return >= 0 ? '+' : ''}{corr.prediction.current_mkt_return}% this month.
                  </p>
                </div>
              )}
            </>
          ) : null}
        </div>
      </main>

      <ToastContainer toasts={toasts} />
    </div>
  );
}