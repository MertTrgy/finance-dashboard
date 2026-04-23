import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend,
} from 'recharts';
import './SpendingChart.css';

const fmt = (v) =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(v);

const RADIAN = Math.PI / 180;

const CustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
  if (percent < 0.05) return null; // hide labels on tiny slices
  const r  = innerRadius + (outerRadius - innerRadius) * 0.55;
  const x  = cx + r * Math.cos(-midAngle * RADIAN);
  const y  = cy + r * Math.sin(-midAngle * RADIAN);
  return (
    <text
      x={x} y={y}
      fill="#fff"
      textAnchor="middle"
      dominantBaseline="central"
      style={{ fontFamily: 'DM Sans', fontSize: 11, fontWeight: 500 }}
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};

const PieTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="chart-tooltip">
      <span style={{ color: d.payload.color }}>■ </span>
      {d.name}: <strong>{fmt(d.value)}</strong>
    </div>
  );
};

export default function SpendingChart({ summary }) {
  const hasCategories = summary?.by_category?.length > 0;

  // Overview bar data
  const overviewData = [{
    name: 'This month',
    Income:   parseFloat(summary?.income   || 0),
    Expenses: parseFloat(summary?.expenses || 0),
  }];

  // Pie data — top 8 categories
  const pieData = hasCategories
    ? summary.by_category.slice(0, 8).map((c) => ({
        name:  c.category__name  || 'Uncategorised',
        value: parseFloat(c.total),
        color: c.category__color || '#888780',
      }))
    : [];

  return (
    <div className="chart-wrap">
      {/* Overview bar */}
      <p className="chart-section-label">Overview</p>
      <ResponsiveContainer width="100%" height={110}>
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
          <Tooltip
            formatter={(value, name) => [fmt(value), name]}
            contentStyle={{
              fontFamily: 'DM Sans', fontSize: 13,
              background: '#1a1a1a', border: 'none',
              borderRadius: 8, color: '#fff',
            }}
            cursor={{ fill: 'rgba(0,0,0,0.03)' }}
          />
          <Legend wrapperStyle={{ fontFamily: 'DM Sans', fontSize: 12, color: '#888' }} />
          <Bar dataKey="Income"   fill="#15803d" radius={[4,4,0,0]} maxBarSize={60} />
          <Bar dataKey="Expenses" fill="#b91c1c" radius={[4,4,0,0]} maxBarSize={60} />
        </BarChart>
      </ResponsiveContainer>

      {/* Pie chart */}
      <p className="chart-section-label" style={{ marginTop: '1.5rem' }}>By category</p>
      {!hasCategories ? (
        <div className="chart-empty">
          <p>Add transactions with categories to see breakdown</p>
        </div>
      ) : (
        <div className="pie-wrap">
          <ResponsiveContainer width="55%" height={200}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%" cy="50%"
                outerRadius={88}
                innerRadius={44}
                dataKey="value"
                labelLine={false}
                label={<CustomLabel />}
              >
                {pieData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} stroke="none" />
                ))}
              </Pie>
              <Tooltip content={<PieTooltip />} />
            </PieChart>
          </ResponsiveContainer>

          {/* Legend */}
          <div className="pie-legend">
            {pieData.map((d) => (
              <div key={d.name} className="pie-legend-row">
                <span className="pie-legend-dot" style={{ background: d.color }} />
                <span className="pie-legend-name">{d.name}</span>
                <span className="pie-legend-val">{fmt(d.value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}