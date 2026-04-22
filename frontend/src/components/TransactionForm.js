import { useState } from 'react';
import './TransactionForm.css';

const today = () => new Date().toISOString().split('T')[0];

export default function TransactionForm({ categories, onAdd, onClose }) {
  const [form, setForm] = useState({
    type: 'expense',
    amount: '',
    date: today(),
    note: '',
    category: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState('');

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const filteredCats = categories.filter((c) => c.type === form.type);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!form.amount || isNaN(form.amount) || Number(form.amount) <= 0) {
      setError('Enter a valid amount.');
      return;
    }
    setSaving(true);
    try {
      await onAdd({
        type:     form.type,
        amount:   parseFloat(form.amount).toFixed(2),
        date:     form.date,
        note:     form.note,
        category: form.category || null,
      });
      onClose();
    } catch (err) {
      const d = err.response?.data;
      setError(d ? Object.values(d).flat()[0] : 'Could not save transaction.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="tf-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="tf-modal">
        <div className="tf-header">
          <span className="tf-title">New transaction</span>
          <button className="tf-close" onClick={onClose}>✕</button>
        </div>

        {error && <div className="tf-error">{error}</div>}

        <form onSubmit={handleSubmit} className="tf-form">
          {/* Type toggle */}
          <div className="tf-toggle">
            {['expense', 'income'].map((t) => (
              <button
                key={t}
                type="button"
                className={`tf-toggle-btn ${form.type === t ? 'active' : ''} ${t}`}
                onClick={() => { set('type', t); set('category', ''); }}
              >
                {t === 'expense' ? '− Expense' : '+ Income'}
              </button>
            ))}
          </div>

          {/* Amount */}
          <div className="tf-field">
            <label>Amount (£)</label>
            <input
              type="number"
              min="0.01"
              step="0.01"
              placeholder="0.00"
              value={form.amount}
              onChange={(e) => set('amount', e.target.value)}
              className="tf-amount-input"
              required
            />
          </div>

          {/* Date */}
          <div className="tf-field">
            <label>Date</label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => set('date', e.target.value)}
              required
            />
          </div>

          {/* Category */}
          <div className="tf-field">
            <label>Category <span className="tf-optional">(optional)</span></label>
            <select
              value={form.category}
              onChange={(e) => set('category', e.target.value)}
            >
              <option value="">No category</option>
              {filteredCats.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            {filteredCats.length === 0 && (
              <span className="tf-hint">No {form.type} categories yet — add some in Settings</span>
            )}
          </div>

          {/* Note */}
          <div className="tf-field">
            <label>Note <span className="tf-optional">(optional)</span></label>
            <input
              type="text"
              placeholder="What was this for?"
              value={form.note}
              onChange={(e) => set('note', e.target.value)}
              maxLength={255}
            />
          </div>

          <div className="tf-actions">
            <button type="button" className="tf-cancel" onClick={onClose}>Cancel</button>
            <button
              type="submit"
              className={`tf-submit ${form.type}`}
              disabled={saving}
            >
              {saving ? 'Saving…' : `Add ${form.type}`}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}