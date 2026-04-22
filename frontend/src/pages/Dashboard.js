import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTransactions, useCategories, useSummary } from '../hooks/useTransactions';
import TransactionForm from '../components/TransactionForm';
import TransactionList from '../components/TransactionList';
import SummaryCards from '../components/SummaryCards';
import SpendingChart from '../components/SpendingChart';
import './Dashboard.css';

// Current month as YYYY-MM string
const currentMonth = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
};

const monthLabel = (ym) => {
  const [y, m] = ym.split('-');
  return new Date(y, m - 1).toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });
};

export default function Dashboard() {
  const { user, logout }   = useAuth();
  const navigate           = useNavigate();
  const [month, setMonth]  = useState(currentMonth());
  const [showForm, setShowForm] = useState(false);

  const { transactions, loading: txLoading, addTransaction, deleteTransaction } =
    useTransactions(month);
  const { categories }              = useCategories();
  const { summary, loading: sumLoading } = useSummary(month);

  const handleLogout = () => { logout(); navigate('/login'); };

  const prevMonth = () => {
    const [y, m] = month.split('-').map(Number);
    const d = new Date(y, m - 2);
    setMonth(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
  };

  const nextMonth = () => {
    const [y, m] = month.split('-').map(Number);
    const d = new Date(y, m);
    const next = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    if (next <= currentMonth()) setMonth(next);
  };

  const isCurrentMonth = month === currentMonth();

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="dash-header">
        <span className="dash-logo">Finance</span>
        <div className="dash-user">
          <span className="dash-username">{user?.username}</span>
          <button onClick={handleLogout} className="logout-btn">Sign out</button>
        </div>
      </header>

      <main className="dash-main">
        {/* Month navigation */}
        <div className="dash-month-row">
          <div className="dash-month-nav">
            <button className="month-btn" onClick={prevMonth}>‹</button>
            <span className="month-label">{monthLabel(month)}</span>
            <button className="month-btn" onClick={nextMonth} disabled={isCurrentMonth}>›</button>
          </div>
          <button className="add-btn" onClick={() => setShowForm(true)}>
            + Add transaction
          </button>
        </div>

        {/* Summary cards */}
        <SummaryCards summary={summary} loading={sumLoading} />

        {/* Two-column layout: chart + transactions */}
        <div className="dash-grid">
          <section className="dash-card">
            <h2 className="card-title">Spending</h2>
            <SpendingChart summary={summary} />
          </section>

          <section className="dash-card">
            <h2 className="card-title">Transactions</h2>
            <TransactionList
              transactions={transactions}
              loading={txLoading}
              onDelete={deleteTransaction}
            />
          </section>
        </div>
      </main>

      {/* Modal form */}
      {showForm && (
        <TransactionForm
          categories={categories}
          onAdd={addTransaction}
          onClose={() => setShowForm(false)}
        />
      )}
    </div>
  );
}