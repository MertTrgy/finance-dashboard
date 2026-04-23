import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCategories } from '../hooks/useTransactions';
import { useBudgets } from '../hooks/useBudgets';
import { useAuth } from '../context/AuthContext';
import { useToast, ToastContainer } from '../components/Toast';
import './Categories.css';

const currentMonth = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
};

// Expanded palette — 24 colors across warm, cool, neutral families
const COLORS = [
  // greens
  '#15803d', '#16a34a', '#4ade80',
  // reds / pinks
  '#b91c1c', '#dc2626', '#f472b6',
  // blues
  '#1d4ed8', '#2563eb', '#38bdf8',
  // oranges / ambers
  '#b45309', '#d97706', '#fb923c',
  // purples
  '#7c3aed', '#9333ea', '#c084fc',
  // teals / cyans
  '#0e7490', '#0891b2', '#67e8f9',
  // pinks / roses
  '#be185d', '#e11d48', '#fda4af',
  // neutrals
  '#374151', '#6b7280', '#9ca3af',
];

export default function Categories() {
  const navigate    = useNavigate();
  const { logout }  = useAuth();
  const { toasts, toast } = useToast();
  const month       = currentMonth();

  const { categories, addCategory, updateCategory, deleteCategory } = useCategories();
  const { budgets, upsertBudget, deleteBudget } = useBudgets(month);

  const [form, setForm]           = useState({ name: '', type: 'expense', color: COLORS[0] });
  const [saving, setSaving]       = useState(false);
  const [formError, setFormError] = useState('');
  const [editBudget, setEditBudget]   = useState({});
  // Track which category has its color picker open
  const [colorPickerOpen, setColorPickerOpen] = useState(null);

  const handleAddCategory = async (e) => {
    e.preventDefault();
    setFormError('');
    if (!form.name.trim()) { setFormError('Name is required.'); return; }
    setSaving(true);
    const nameSnapshot = form.name;
    try {
      await addCategory(form);
      setForm({ name: '', type: 'expense', color: COLORS[0] });
      toast.success(`Category "${nameSnapshot}" created`);
    } catch (err) {
      if (err.response) {
        const d = err.response.data;
        setFormError(d ? Object.values(d).flat()[0] : 'Could not create category.');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleColorChange = async (cat, newColor) => {
    try {
      await updateCategory(cat.id, { color: newColor });
      setColorPickerOpen(null);
      toast.success(`Color updated for "${cat.name}"`);
    } catch {
      toast.error('Could not update color.');
    }
  };

  const handleDeleteCategory = async (cat) => {
    if (!window.confirm(`Delete "${cat.name}"? Transactions will lose this category.`)) return;
    try {
      await deleteCategory(cat.id);
      toast.success(`"${cat.name}" deleted`);
    } catch {
      toast.error('Could not delete category.');
    }
  };

  const handleBudgetSave = async (cat) => {
    const raw   = editBudget[cat.id];
    const limit = parseFloat(raw);
    if (isNaN(limit) || limit <= 0) { toast.error('Enter a valid budget amount.'); return; }
    try {
      await upsertBudget(cat.id, limit.toFixed(2), month);
      setEditBudget((prev) => ({ ...prev, [cat.id]: '' }));
      toast.success(`Budget set for "${cat.name}"`);
    } catch {
      toast.error('Could not save budget.');
    }
  };

  const handleBudgetDelete = async (budgetId, catName) => {
    try {
      await deleteBudget(budgetId);
      toast.success(`Budget removed for "${catName}"`);
    } catch {
      toast.error('Could not remove budget.');
    }
  };

  const getBudget = (catId) => budgets.find((b) => b.category === catId);
  const expenseCategories = categories.filter((c) => c.type === 'expense');
  const incomeCategories  = categories.filter((c) => c.type === 'income');

  return (
    <div className="cat-page" onClick={() => setColorPickerOpen(null)}>
      <header className="dash-header">
        <button className="back-btn" onClick={() => navigate('/')}>← Dashboard</button>
        <span className="dash-logo">Finance</span>
        <button className="logout-btn" onClick={() => { logout(); navigate('/login'); }}>
          Sign out
        </button>
      </header>

      <main className="cat-main">
        <h1 className="cat-heading">Categories</h1>
        <p className="cat-sub">Manage categories and set monthly budget limits</p>

        {/* Add category form */}
        <div className="cat-card">
          <h2 className="cat-card-title">New category</h2>
          {formError && <div className="cat-error">{formError}</div>}
          <form onSubmit={handleAddCategory} className="cat-form">
            <input
              type="text"
              placeholder="Category name"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              className="cat-input"
              maxLength={100}
            />
            <div className="cat-form-row">
              <select
                value={form.type}
                onChange={(e) => setForm((f) => ({ ...f, type: e.target.value }))}
                className="cat-select"
              >
                <option value="expense">Expense</option>
                <option value="income">Income</option>
              </select>
              <div className="color-picker-grid">
                {COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    className={`color-dot ${form.color === c ? 'selected' : ''}`}
                    style={{ background: c }}
                    onClick={() => setForm((f) => ({ ...f, color: c }))}
                  />
                ))}
              </div>
              <button type="submit" className="cat-add-btn" disabled={saving}>
                {saving ? 'Adding…' : 'Add'}
              </button>
            </div>
          </form>
        </div>

        <CategorySection
          title="Expense categories"
          categories={expenseCategories}
          getBudget={getBudget}
          editBudget={editBudget}
          setEditBudget={setEditBudget}
          colorPickerOpen={colorPickerOpen}
          setColorPickerOpen={setColorPickerOpen}
          onColorChange={handleColorChange}
          onDelete={handleDeleteCategory}
          onBudgetSave={handleBudgetSave}
          onBudgetDelete={handleBudgetDelete}
          showBudget={true}
        />

        <CategorySection
          title="Income categories"
          categories={incomeCategories}
          getBudget={getBudget}
          editBudget={editBudget}
          setEditBudget={setEditBudget}
          colorPickerOpen={colorPickerOpen}
          setColorPickerOpen={setColorPickerOpen}
          onColorChange={handleColorChange}
          onDelete={handleDeleteCategory}
          onBudgetSave={handleBudgetSave}
          onBudgetDelete={handleBudgetDelete}
          showBudget={false}
        />
      </main>

      <ToastContainer toasts={toasts} />
    </div>
  );
}

function CategorySection({
  title, categories, getBudget,
  editBudget, setEditBudget,
  colorPickerOpen, setColorPickerOpen,
  onColorChange, onDelete, onBudgetSave, onBudgetDelete,
  showBudget = true,
}) {
  if (!categories.length) return null;

  return (
    <div className="cat-card">
      <h2 className="cat-card-title">{title}</h2>
      <div className="cat-list">
        {categories.map((cat) => {
          const budget   = getBudget(cat.id);
          const isOpen   = colorPickerOpen === cat.id;

          return (
            <div key={cat.id} className="cat-row">
              {/* Color swatch — click to open inline picker */}
              <div
                className="cat-color-swatch"
                style={{ background: cat.color }}
                onClick={(e) => {
                  e.stopPropagation();
                  setColorPickerOpen(isOpen ? null : cat.id);
                }}
                title="Click to change color"
              />

              {/* Inline color picker popup */}
              {isOpen && (
                <div
                  className="inline-color-picker"
                  onClick={(e) => e.stopPropagation()}
                >
                  <span className="icp-label">Pick a color</span>
                  <div className="icp-grid">
                    {COLORS.map((c) => (
                      <button
                        key={c}
                        className={`color-dot ${cat.color === c ? 'selected' : ''}`}
                        style={{ background: c }}
                        onClick={() => onColorChange(cat, c)}
                      />
                    ))}
                  </div>
                </div>
              )}

              <span className="cat-name">{cat.name}</span>

              {showBudget && (
                <div className="budget-controls">
                  {budget ? (
                    <div className="budget-set">
                      <span className="budget-amount">
                        £{parseFloat(budget.limit).toFixed(2)}/mo
                      </span>
                      <button
                        className="budget-remove"
                        onClick={() => onBudgetDelete(budget.id, cat.name)}
                        title="Remove budget"
                      >✕</button>
                    </div>
                  ) : (
                    <div className="budget-input-row">
                      <input
                        type="number"
                        placeholder="Set limit £"
                        min="0.01"
                        step="0.01"
                        value={editBudget[cat.id] || ''}
                        onChange={(e) =>
                          setEditBudget((prev) => ({ ...prev, [cat.id]: e.target.value }))
                        }
                        className="budget-input"
                      />
                      <button
                        className="budget-save"
                        onClick={() => onBudgetSave(cat)}
                        disabled={!editBudget[cat.id]}
                      >Set</button>
                    </div>
                  )}
                </div>
              )}

              <button
                className="cat-delete"
                onClick={() => onDelete(cat)}
                title="Delete category"
              >✕</button>
            </div>
          );
        })}
      </div>
    </div>
  );
}