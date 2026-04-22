import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import './SpendingChart.css';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  const fmt = (v) =>
    new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(v);
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-label">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.fill }}>
          {p.name}: {fmt(p.value)}
        </p>
      ))}
    </div>
  );
};

export default function SpendingChart({ summary }) {
  if (!summary?.by_category?.length) {
    return (
      <div className="chart-empty">
        <p>No category data yet — add some transactions with categories</p>
      </div>
    );
  }

  // Build data for bar chart: top 6 expense categories + combined income bar
  const catData = summary.by_category.slice(0, 6).map((c) => ({
    name: c.category__name || 'Uncategorised',
    Expenses: parseFloat(c.total),
  }));

  // Simple two-bar overview for income vs expenses
  const overviewData = [
    { name: 'This month', Income: parseFloat(summary.income || 0), Expenses: parseFloat(summary.expenses || 0) },
  ];

  return (
    <div className="chart-wrap">
      <p className="chart-section-label">Overview</p>
      <ResponsiveContainer width="100%" height={120}>
        <BarChart data={overviewData} barCategoryGap="40%">
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0ede8" />
          <XAxis dataKey="name" tick={{ fontFamily: 'DM Sans', fontSize: 12, fill: '#aaa' }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontFamily: 'DM Sans', fontSize: 11, fill: '#aaa' }} axisLine={false} tickLine={false}
            tickFormatter={(v) => `£${v}`} width={52} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,0,0,0.03)' }} />
          <Legend wrapperStyle={{ fontFamily: 'DM Sans', fontSize: 12, color: '#888' }} />
          <Bar dataKey="Income"   fill="#15803d" radius={[4,4,0,0]} maxBarSize={60} />
          <Bar dataKey="Expenses" fill="#b91c1c" radius={[4,4,0,0]} maxBarSize={60} />
        </BarChart>
      </ResponsiveContainer>

      <p className="chart-section-label" style={{ marginTop: '1.5rem' }}>By category</p>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={catData} barCategoryGap="30%">
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0ede8" />
          <XAxis dataKey="name" tick={{ fontFamily: 'DM Sans', fontSize: 11, fill: '#aaa' }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontFamily: 'DM Sans', fontSize: 11, fill: '#aaa' }} axisLine={false} tickLine={false}
            tickFormatter={(v) => `£${v}`} width={52} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,0,0,0.03)' }} />
          <Bar dataKey="Expenses" fill="#1a1a1a" radius={[4,4,0,0]} maxBarSize={48} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}