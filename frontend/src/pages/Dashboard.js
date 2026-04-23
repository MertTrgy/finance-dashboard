import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTransactions, useCategories, useSummary } from '../hooks/useTransactions';
import { useToast, ToastContainer } from '../components/Toast';
import ErrorBoundary from '../components/ErrorBoundary';
import TransactionForm from '../components/TransactionForm';
import TransactionList from '../components/TransactionList';
import SummaryCards from '../components/SummaryCards';
import SpendingChart from '../components/SpendingChart';
import api from '../services/api';
import './Dashboard.css';

const currentMonth = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
};

const monthLabel = (ym) => {
  const [y, m] = ym.split('-');
  return new Date(y, m - 1).toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });
};

export default function Dashboard() {
  const { user, logout }  = useAuth();
  const navigate          = useNavigate();
  const { toasts, toast } = useToast();

  const [month, setMonth]           = useState(currentMonth());
  const [showForm, setShowForm]     = useState(false);
  const [editingTx, setEditingTx]   = useState(null); // transaction being edited
  const [exporting, setExporting]   = useState(false);
  const prevOverBudget              = useRef([]);

  const { transactions, loading: txLoading, error: txError,
          addTransaction, editTransaction, deleteTransaction } = useTransactions(month);
  const { categories }                    = useCategories();
  const { summary, loading: sumLoading }  = useSummary(month);

  // Over-budget toasts
  useEffect(() => {
    if (!summary?.over_budget?.length) return;
    summary.over_budget.forEach((ob) => {
      const warned = prevOverBudget.current.find((p) => p.category_id === ob.category_id);
      if (!warned) {
        toast.warning(`"${ob.category_name}" is over budget by £${parseFloat(ob.over_by).toFixed(2)}`);
      }
    });
    prevOverBudget.current = summary.over_budget;
  }, [summary]); // eslint-disable-line

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

  const handleAdd = async (payload) => {
    await addTransaction(payload);
    toast.success('Transaction added');
  };

  const handleEdit = async (id, payload) => {
    await editTransaction(id, payload);
    toast.success('Transaction updated');
  };

  const handleDelete = async (id) => {
    await deleteTransaction(id);
    toast.success('Transaction deleted');
  };

  const openEdit = (tx) => {
    setEditingTx(tx);
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    setEditingTx(null);
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const response = await api.get('/export/', {
        params: { month },
        responseType: 'blob',
      });
      const url  = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href  = url;
      link.setAttribute('download', `transactions-${month}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('CSV downloaded');
    } catch {
      toast.error('Export failed.');
    } finally {
      setExporting(false);
    }
  };

  const isCurrentMonth = month === currentMonth();

  return (
    <div className="dashboard">
      <header className="dash-header">
        <span className="dash-logo">Finance</span>
        <nav className="dash-nav">
          <Link to="/categories" className="dash-nav-link">Categories</Link>
        </nav>
        <div className="dash-user">
          <span className="dash-username">{user?.username}</span>
          <button onClick={handleLogout} className="logout-btn">Sign out</button>
        </div>
      </header>

      <main className="dash-main">
        {/* Month nav + actions */}
        <div className="dash-month-row">
          <div className="dash-month-nav">
            <button className="month-btn" onClick={prevMonth}>‹</button>
            <span className="month-label">{monthLabel(month)}</span>
            <button className="month-btn" onClick={nextMonth} disabled={isCurrentMonth}>›</button>
          </div>
          <div className="dash-actions">
            <button className="export-btn" onClick={handleExport} disabled={exporting}>
              {exporting ? 'Exporting…' : '↓ CSV'}
            </button>
            <button className="add-btn" onClick={() => { setEditingTx(null); setShowForm(true); }}>
              + Add transaction
            </button>
          </div>
        </div>

        {/* Over-budget banner */}
        {summary?.over_budget?.length > 0 && (
          <div className="over-budget-banner">
            <span className="ob-icon">!</span>
            <span>
              Over budget:{' '}
              {summary.over_budget.map((ob, i) => (
                <span key={ob.category_id}>
                  {i > 0 && ', '}
                  <strong>{ob.category_name}</strong>
                  {' '}(£{parseFloat(ob.over_by).toFixed(2)} over)
                </span>
              ))}
            </span>
          </div>
        )}

        {/* Summary cards */}
        <SummaryCards summary={summary} loading={sumLoading} />

        {/* Main grid */}
        <div className="dash-grid">
          <ErrorBoundary>
            <section className="dash-card">
              <h2 className="card-title">Spending</h2>
              <SpendingChart summary={summary} />
            </section>
          </ErrorBoundary>

          <ErrorBoundary>
            <section className="dash-card">
              <div className="card-title-row">
                <h2 className="card-title">Transactions</h2>
                {transactions.length > 0 && (
                  <span className="card-hint">Click a row to edit</span>
                )}
              </div>
              <TransactionList
                transactions={transactions}
                loading={txLoading}
                error={txError}
                onEdit={openEdit}
                onDelete={handleDelete}
              />
            </section>
          </ErrorBoundary>
        </div>
      </main>

      {showForm && (
        <TransactionForm
          categories={categories}
          onAdd={handleAdd}
          onEdit={handleEdit}
          onClose={closeForm}
          transaction={editingTx}
        />
      )}

      <ToastContainer toasts={toasts} />
    </div>
  );
}