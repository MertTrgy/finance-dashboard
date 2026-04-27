import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useRecurring } from '../hooks/useRecurring';
import { useCategories } from '../hooks/useTransactions';
import { useCurrencies } from '../hooks/useCurrencies';
import { useToast, ToastContainer } from '../components/Toast';
import './Recurring.css';

const today = () => new Date().toISOString().split('T')[0];

const fmtDate = (d) =>
  new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

const BLANK = {
  type: 'expense', amount: '', currency: 'GBP',
  frequency: 'monthly', next_due: today(),
  note: '', category: '',
};

export default function Recurring() {
  const navigate          = useNavigate();
  const { logout }        = useAuth();
  const { toasts, toast } = useToast();
  const { rules, loading, addRule, toggleRule, deleteRule } = useRecurring();
  const { categories }    = useCategories();
  const { currencies }    = useCurrencies();

  const [form, setForm]       = useState(BLANK);
  const [saving, setSaving]   = useState(false);
  const [formError, setFormError] = useState('');
  const [showForm, setShowForm]   = useState(false);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const filteredCats = categories.filter((c) => c.type === form.type);

  const handleAdd = async (e) => {
    e.preventDefault();
    setFormError('');
    if (!form.amount || Number(form.amount) <= 0) {
      setFormError('Enter a valid amount.');
      return;
    }
    setSaving(true);
    try {
      await addRule({
        type:              form.type,
        amount:            parseFloat(form.amount).toFixed(2),
        original_currency: form.currency,
        frequency:         form.frequency,
        next_due:          form.next_due,
        note:              form.note,
        category:          form.category || null,
      });
      setForm(BLANK);
      setShowForm(false);
      toast.success('Recurring rule created');
    } catch (err) {
      if (err.response) {
        const d = err.response.data;
        setFormError(d ? Object.values(d).flat()[0] : 'Could not create rule.');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (rule) => {
    try {
      await toggleRule(rule);
      toast.success(rule.active ? 'Rule paused' : 'Rule resumed');
    } catch {
      toast.error('Could not update rule.');
    }
  };

  const handleDelete = async (rule) => {
    if (!window.confirm(`Delete this recurring ${rule.frequency} rule?`)) return;
    try {
      await deleteRule(rule.id);
      toast.success('Rule deleted');
    } catch {
      toast.error('Could not delete rule.');
    }
  };

  return (
    <div className="rec-page">
      <header className="dash-header">
        <button className="back-btn" onClick={() => navigate('/')}>← Dashboard</button>
        <span className="dash-logo">Finance</span>
        <button className="logout-btn" onClick={() => { logout(); navigate('/login'); }}>Sign out</button>
      </header>

      <main className="rec-main">
        <div className="rec-title-row">
          <div>
            <h1 className="rec-heading">Recurring transactions</h1>
            <p className="rec-sub">Auto-create weekly or monthly transactions</p>
          </div>
          <button className="add-btn" onClick={() => setShowForm((s) => !s)}>
            {showForm ? 'Cancel' : '+ New rule'}
          </button>
        </div>

        {/* Add rule form */}
        {showForm && (
          <div className="rec-card">
            <h2 className="rec-card-title">New recurring rule</h2>
            {formError && <div className="rec-error">{formError}</div>}
            <form onSubmit={handleAdd} className="rec-form">
              {/* Type toggle */}
              <div className="tf-toggle">
                {['expense', 'income'].map((t) => (
                  <button
                    key={t} type="button"
                    className={`tf-toggle-btn ${form.type === t ? 'active' : ''} ${t}`}
                    onClick={() => { set('type', t); set('category', ''); }}
                  >
                    {t === 'expense' ? '− Expense' : '+ Income'}
                  </button>
                ))}
              </div>

              <div className="rec-form-grid">
                {/* Amount + currency */}
                <div className="tf-field">
                  <label>Amount</label>
                  <div className="tf-amount-row">
                    <select value={form.currency} onChange={(e) => set('currency', e.target.value)} className="tf-currency-select">
                      {currencies.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                    <input
                      type="number" min="0.01" step="0.01" placeholder="0.00"
                      value={form.amount} onChange={(e) => set('amount', e.target.value)}
                      className="tf-amount-input" required
                    />
                  </div>
                </div>

                {/* Frequency */}
                <div className="tf-field">
                  <label>Frequency</label>
                  <select value={form.frequency} onChange={(e) => set('frequency', e.target.value)} className="cat-select">
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>

                {/* Next due */}
                <div className="tf-field">
                  <label>First / next due date</label>
                  <input type="date" value={form.next_due} onChange={(e) => set('next_due', e.target.value)} required />
                </div>

                {/* Category */}
                <div className="tf-field">
                  <label>Category <span className="tf-optional">(optional)</span></label>
                  <select value={form.category} onChange={(e) => set('category', e.target.value)} className="cat-select">
                    <option value="">No category</option>
                    {filteredCats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
              </div>

              {/* Note */}
              <div className="tf-field">
                <label>Note <span className="tf-optional">(optional)</span></label>
                <input
                  type="text" placeholder="e.g. Netflix, Rent, Salary…"
                  value={form.note} onChange={(e) => set('note', e.target.value)}
                  maxLength={255} className="cat-input"
                />
              </div>

              <button type="submit" className="auth-btn" disabled={saving}>
                {saving ? 'Creating…' : 'Create rule'}
              </button>
            </form>
          </div>
        )}

        {/* Rules list */}
        {loading ? (
          <div className="rec-card">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="tl-skeleton" style={{ marginBottom: 6, animationDelay: `${i * 0.07}s` }} />
            ))}
          </div>
        ) : rules.length === 0 ? (
          <div className="rec-card rec-empty">
            <div className="tl-empty-icon">↻</div>
            <p className="tl-empty-text">No recurring rules yet</p>
            <p className="tl-empty-sub">Create one above to auto-generate transactions</p>
          </div>
        ) : (
          <div className="rec-card">
            <h2 className="rec-card-title">Active rules</h2>
            <div className="rec-list">
              {rules.map((rule) => (
                <div key={rule.id} className={`rec-row ${rule.active ? '' : 'paused'}`}>
                  <div className="rec-freq-badge">
                    {rule.frequency === 'weekly' ? 'W' : 'M'}
                  </div>
                  <div className="rec-info">
                    <span className="rec-note">
                      {rule.note || rule.category_detail?.name || `${rule.frequency} ${rule.type}`}
                    </span>
                    <span className="rec-meta">
                      {rule.original_currency !== 'GBP'
                        ? `${rule.original_currency} ${rule.amount}`
                        : `£${rule.amount}`
                      }
                      {' · '}Next: {fmtDate(rule.next_due)}
                      {!rule.active && <span className="rec-paused-badge"> · Paused</span>}
                    </span>
                  </div>
                  <span className={`rec-type-badge ${rule.type}`}>
                    {rule.type}
                  </span>
                  <button
                    className="rec-toggle"
                    onClick={() => handleToggle(rule)}
                    title={rule.active ? 'Pause' : 'Resume'}
                  >
                    {rule.active ? '⏸' : '▶'}
                  </button>
                  <button
                    className="cat-delete"
                    onClick={() => handleDelete(rule)}
                    title="Delete rule"
                  >✕</button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* How it works */}
        <div className="rec-card rec-info-card">
          <h2 className="rec-card-title">How it works</h2>
          <p className="rec-info-text">
            Rules don't run automatically in development. Run the management command manually
            to process any due rules:
          </p>
          <code className="rec-code">python manage.py process_recurring</code>
          <p className="rec-info-text" style={{ marginTop: '0.75rem' }}>
            In production (Railway / Render) add a cron job to run this daily at 01:00 UTC.
            Each run creates one transaction per due rule and advances the next due date forward.
          </p>
        </div>
      </main>

      <ToastContainer toasts={toasts} />
    </div>
  );
}