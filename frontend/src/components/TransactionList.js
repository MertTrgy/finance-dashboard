import './TransactionList.css';

const fmt = (amount) =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(amount);

const fmtDate = (dateStr) =>
  new Date(dateStr).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

export default function TransactionList({ transactions, loading, error, onEdit, onDelete }) {
  if (loading) {
    return (
      <div className="tl-stack">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="tl-skeleton" style={{ animationDelay: `${i * 0.06}s` }} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="tl-empty">
        <div className="tl-empty-icon tl-empty-icon--error">!</div>
        <p className="tl-empty-text">Failed to load</p>
        <p className="tl-empty-sub">{error}</p>
      </div>
    );
  }

  if (!transactions.length) {
    return (
      <div className="tl-empty">
        <div className="tl-empty-icon">₤</div>
        <p className="tl-empty-text">No transactions yet</p>
        <p className="tl-empty-sub">Add your first one above</p>
      </div>
    );
  }

  return (
    <div className="tl-stack">
      {transactions.map((t) => (
        <div
          key={t.id}
          className={`tl-row ${t.type}`}
          onClick={() => onEdit(t)}
          title="Click to edit"
        >
          <div className="tl-dot" />
          <div className="tl-info">
            <span className="tl-note">{t.note || t.category_detail?.name || '—'}</span>
            <span className="tl-meta">
              {t.category_detail?.name && t.note ? `${t.category_detail.name} · ` : ''}
              {fmtDate(t.date)}
              {/* Foreign currency badge */}
              {t.original_currency && t.original_currency !== 'GBP' && (
                <span className="tl-currency-badge">
                  {t.original_currency} {parseFloat(t.original_amount).toFixed(2)}
                </span>
              )}
            </span>
          </div>
          <span className={`tl-amount ${t.type}`}>
            {t.type === 'income' ? '+' : '−'}{fmt(t.amount)}
          </span>
          <button
            className="tl-delete"
            onClick={(e) => { e.stopPropagation(); onDelete(t.id); }}
            aria-label="Delete transaction"
          >✕</button>
        </div>
      ))}
    </div>
  );
}