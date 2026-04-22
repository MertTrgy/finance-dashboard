import './SummaryCards.css';

const fmt = (n) =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(n ?? 0);

export default function SummaryCards({ summary, loading }) {
  if (loading || !summary) {
    return (
      <div className="sc-grid">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="sc-card sc-skeleton" />
        ))}
      </div>
    );
  }

  const cards = [
    { label: 'Income',   value: fmt(summary.income),   cls: 'income'  },
    { label: 'Expenses', value: fmt(summary.expenses),  cls: 'expense' },
    { label: 'Balance',  value: fmt(summary.balance),
      cls: Number(summary.balance) >= 0 ? 'positive' : 'negative' },
  ];

  return (
    <div className="sc-grid">
      {cards.map((c) => (
        <div key={c.label} className={`sc-card ${c.cls}`}>
          <span className="sc-label">{c.label}</span>
          <span className="sc-value">{c.value}</span>
        </div>
      ))}
    </div>
  );
}