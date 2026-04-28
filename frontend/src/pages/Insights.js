import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useForecasts, useAnomalies } from '../hooks/useML';
import { useToast, ToastContainer } from '../components/Toast';
import './Insights.css';

const fmt = (n) =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(n ?? 0);

const monthLabel = (ym) => {
  if (!ym) return '';
  const [y, m] = ym.split('-');
  return new Date(y, m - 1).toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });
};

const TREND_ICON  = { up: '↑', down: '↓', stable: '→' };
const TREND_COLOR = { up: '#b91c1c', down: '#15803d', stable: '#888' };
const TREND_LABEL = { up: 'Increasing', down: 'Decreasing', stable: 'Stable' };

export default function Insights() {
  const navigate       = useNavigate();
  const { logout }     = useAuth();
  const { toasts }     = useToast();

  const { forecasts, nextMonth, loading: fLoading, error: fError } = useForecasts();
  const { anomalyIds, loading: aLoading } = useAnomalies();

  const totalForecast = forecasts.reduce((s, f) => s + f.predicted_amount, 0);
  const risingCats    = forecasts.filter((f) => f.trend === 'up');

  return (
    <div className="ins-page">
      <header className="dash-header">
        <button className="back-btn" onClick={() => navigate('/')}>← Dashboard</button>
        <span className="dash-logo">Finance</span>
        <button
          className="logout-btn"
          onClick={() => { logout(); navigate('/login'); }}
        >
          Sign out
        </button>
      </header>

      <main className="ins-main">
        <div>
          <h1 className="ins-heading">Insights</h1>
          <p className="ins-sub">ML-powered forecasts and anomaly detection</p>
        </div>

        {/* ── Forecast section ── */}
        <div className="ins-card">
          <div className="ins-card-header">
            <h2 className="ins-card-title">Spend forecast</h2>
            {nextMonth && (
              <span className="ins-card-badge">{monthLabel(nextMonth)}</span>
            )}
          </div>

          {fLoading ? (
            <div className="ins-skeleton-stack">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="ins-skeleton" style={{ animationDelay: `${i * 0.07}s` }} />
              ))}
            </div>
          ) : fError ? (
            <div className="ins-notice ins-notice--warn">
              <span>Need at least 2 months of categorised transactions to generate forecasts.</span>
            </div>
          ) : forecasts.length === 0 ? (
            <div className="ins-notice">
              <span>No categorised transactions found. Add some categories to your transactions.</span>
            </div>
          ) : (
            <>
              {/* Total summary */}
              <div className="ins-total-row">
                <span className="ins-total-label">Predicted total</span>
                <span className="ins-total-value">{fmt(totalForecast)}</span>
              </div>

              {risingCats.length > 0 && (
                <div className="ins-notice ins-notice--warn" style={{ marginBottom: '1rem' }}>
                  <span>
                    Rising spend in:{' '}
                    {risingCats.map((c, i) => (
                      <span key={c.category_id}>
                        {i > 0 && ', '}
                        <strong>{c.category_name}</strong>
                      </span>
                    ))}
                  </span>
                </div>
              )}

              {/* Per-category forecast rows */}
              <div className="ins-forecast-list">
                {forecasts.map((f) => (
                  <div key={f.category_id} className="ins-forecast-row">
                    <span
                      className="ins-cat-dot"
                      style={{ background: f.category_color }}
                    />
                    <span className="ins-cat-name">{f.category_name}</span>
                    <span className="ins-months-used">
                      {f.months_used} month{f.months_used !== 1 ? 's' : ''} data
                    </span>
                    <span
                      className="ins-trend"
                      style={{ color: TREND_COLOR[f.trend] }}
                      title={TREND_LABEL[f.trend]}
                    >
                      {TREND_ICON[f.trend]}
                    </span>
                    <span className="ins-forecast-amount">{fmt(f.predicted_amount)}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* ── Anomaly section ── */}
        <div className="ins-card">
          <div className="ins-card-header">
            <h2 className="ins-card-title">Anomaly detection</h2>
          </div>

          {aLoading ? (
            <div className="ins-skeleton" />
          ) : anomalyIds.size === 0 ? (
            <div className="ins-notice ins-notice--good">
              <span>
                No unusual transactions detected — or not enough data yet (need 10+ transactions).
              </span>
            </div>
          ) : (
            <div className="ins-notice ins-notice--warn">
              <span>
                <strong>{anomalyIds.size}</strong> transaction
                {anomalyIds.size !== 1 ? 's' : ''} flagged as unusual amounts.
                These are marked with an <em>unusual</em> badge on the dashboard.
              </span>
            </div>
          )}

          <p className="ins-explainer">
            Anomaly detection uses IsolationForest — a machine learning algorithm that
            identifies transactions that are statistically unusual compared to your
            normal spending patterns. A transaction can be flagged for being much
            larger than usual or occurring on an unusual day of the month.
          </p>
        </div>

        {/* ── How it works ── */}
        <div className="ins-card ins-how-card">
          <h2 className="ins-card-title">How the ML works</h2>
          <div className="ins-how-grid">
            <div className="ins-how-item">
              <span className="ins-how-icon">◈</span>
              <strong>Forecasting</strong>
              <p>Linear regression on your last 6 months of spend per category. The slope tells us if you're spending more or less over time.</p>
            </div>
            <div className="ins-how-item">
              <span className="ins-how-icon">◉</span>
              <strong>Anomalies</strong>
              <p>IsolationForest scores each transaction by how different it is from the rest. The 10% most unusual are flagged.</p>
            </div>
            <div className="ins-how-item">
              <span className="ins-how-icon">◎</span>
              <strong>Auto-categorise</strong>
              <p>TF-IDF + Naive Bayes trains on your past note→category pairs. When you type a note, it suggests the most likely category.</p>
            </div>
          </div>
        </div>
      </main>

      <ToastContainer toasts={toasts} />
    </div>
  );
}