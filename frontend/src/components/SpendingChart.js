import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, Cell,
} from 'recharts';
import './SpendingChart.css';

const fmt = (v) =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(v);

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-label">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color || p.fill }}>
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
        <p>No category data yet — add transactions with categories</p>
      </div>
    );
  }

  // Overview: income vs expenses
  const overviewData = [
    {
      name: 'This month',
      Income:   parseFloat(summary.income   || 0),
      Expenses: parseFloat(summary.expenses || 0),
    },
  ];

  // By-category: each entry keeps its color from the API
  const catData = summary.by_category.slice(0, 8).map((c) => ({
    name:  c.category__name  || 'Uncategorised',
    color: c.category__color || '#888780',
    total: parseFloat(c.total),
  }));

  return (
    <div className="chart-wrap">
      <p className="chart-section-label">Overview</p>
      <ResponsiveContainer width="100%" height={120}>
        <BarChart data={overviewData} barCategoryGap="40%">
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0ede8" />
          <XAxis
            dataKey="name"
            tick={{ fontFamily: 'DM Sans', fontSize: 12, fill: '#aaa' }}
            axisLine={false} tickLine={false}
          />
          <YAxis
            tick={{ fontFamily: 'DM Sans', fontSize: 11, fill: '#aaa' }}
            axisLine={false} tickLine={false}
            tickFormatter={(v) => `£${v}`} width={52}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,0,0,0.03)' }} />
          <Legend wrapperStyle={{ fontFamily: 'DM Sans', fontSize: 12, color: '#888' }} />
          <Bar dataKey="Income"   fill="#15803d" radius={[4,4,0,0]} maxBarSize={60} />
          <Bar dataKey="Expenses" fill="#b91c1c" radius={[4,4,0,0]} maxBarSize={60} />
        </BarChart>
      </ResponsiveContainer>

      <p className="chart-section-label" style={{ marginTop: '1.5rem' }}>By category</p>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={catData} barCategoryGap="30%">
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0ede8" />
          <XAxis
            dataKey="name"
            tick={{ fontFamily: 'DM Sans', fontSize: 11, fill: '#aaa' }}
            axisLine={false} tickLine={false}
          />
          <YAxis
            tick={{ fontFamily: 'DM Sans', fontSize: 11, fill: '#aaa' }}
            axisLine={false} tickLine={false}
            tickFormatter={(v) => `£${v}`} width={52}
          />
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              return (
                <div className="chart-tooltip">
                  <p className="chart-tooltip-label">{label}</p>
                  <p style={{ color: payload[0]?.payload?.color }}>
                    {fmt(payload[0]?.value)}
                  </p>
                </div>
              );
            }}
            cursor={{ fill: 'rgba(0,0,0,0.03)' }}
          />
          {/* Single Bar with one Cell per entry so each bar gets its own color */}
          <Bar dataKey="total" radius={[4,4,0,0]} maxBarSize={48}>
            {catData.map((entry, index) => (
              <Cell key={index} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}