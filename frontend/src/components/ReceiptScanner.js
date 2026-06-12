import { useState, useRef } from 'react';
import { useReceipt } from '../hooks/useReceipt';
import './ReceiptScanner.css';

export default function ReceiptScanner({ categories, onSaved }) {
  const fileRef = useRef(null);
  const { scanning, saving, scanResult, error, scanImage, saveReceipt, clearResult } = useReceipt();

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) scanImage(file);
    // Reset input so the same file can be re-selected
    e.target.value = '';
  };

  return (
    <>
      {/* Upload trigger button */}
      <button
        className="receipt-btn"
        onClick={() => fileRef.current?.click()}
        disabled={scanning}
        title="Scan a receipt or bill"
      >
        {scanning ? (
          <span className="receipt-btn-inner">
            <span className="receipt-spinner" />
            Scanning…
          </span>
        ) : (
          <span className="receipt-btn-inner">
            <span className="receipt-icon">⎙</span>
            Scan receipt
          </span>
        )}
      </button>

      {/* Hidden file input */}
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />

      {/* Error toast */}
      {error && !scanResult && (
        <div className="receipt-error-banner">
          {error}
          <button onClick={clearResult}>✕</button>
        </div>
      )}

      {/* Review modal */}
      {scanResult && (
        <ReceiptReviewModal
          result={scanResult}
          categories={categories}
          saving={saving}
          onSave={async (payload) => {
            const tx = await saveReceipt(payload);
            onSaved(tx);
          }}
          onClose={clearResult}
        />
      )}
    </>
  );
}


// ── Review modal ──────────────────────────────────────────────────────────────

function ReceiptReviewModal({ result, categories, saving, onSave, onClose }) {
  const [merchant,    setMerchant]    = useState(result.merchant || '');
  const [receiptDate, setReceiptDate] = useState(result.date || '');
  const [note,        setNote]        = useState(`${result.merchant || 'Receipt'} receipt`);
  const [categoryId,  setCategoryId]  = useState('');
  const [items,       setItems]       = useState(
    result.items.map((item, i) => ({
      ...item,
      id:          i,
      category_id: item.suggested_category_id || '',
      included:    true,
    }))
  );
  const [saveMode, setSaveMode] = useState('total'); // 'total' | 'items'

  const expenseCategories = categories.filter((c) => c.type === 'expense');

  const updateItem = (id, key, value) => {
    setItems((prev) => prev.map((it) => (it.id === id ? { ...it, [key]: value } : it)));
  };

  const includedItems = items.filter((i) => i.included);
  const computedTotal = saveMode === 'items'
    ? includedItems.reduce((s, i) => s + parseFloat(i.total_price || 0), 0)
    : parseFloat(result.total || 0);

  const handleSave = () => {
    onSave({
      merchant:    merchant,
      date:        receiptDate,
      currency:    result.currency || 'GBP',
      total:       computedTotal,
      note:        note,
      category_id: categoryId || null,
      items:       saveMode === 'items'
        ? includedItems.map((i) => ({
            name:        i.name,
            quantity:    i.quantity,
            unit_price:  i.unit_price,
            total_price: parseFloat(i.total_price),
            category_id: i.category_id || null,
            raw_text:    i.raw_text || '',
          }))
        : result.items.map((i) => ({
            name:        i.name,
            quantity:    i.quantity,
            unit_price:  i.unit_price,
            total_price: parseFloat(i.total_price),
            category_id: i.suggested_category_id || null,
            raw_text:    i.raw_text || '',
          })),
    });
  };

  const fmt = (n) => `£${parseFloat(n || 0).toFixed(2)}`;

  return (
    <div className="rr-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="rr-modal">
        {/* Header */}
        <div className="rr-header">
          <span className="rr-title">Review receipt</span>
          <button className="rr-close" onClick={onClose}>✕</button>
        </div>

        <div className="rr-body">
          {/* Top fields */}
          <div className="rr-fields">
            <div className="rr-field">
              <label>Merchant</label>
              <input value={merchant} onChange={(e) => setMerchant(e.target.value)} />
            </div>
            <div className="rr-field">
              <label>Date</label>
              <input type="date" value={receiptDate} onChange={(e) => setReceiptDate(e.target.value)} />
            </div>
            <div className="rr-field">
              <label>Note</label>
              <input value={note} onChange={(e) => setNote(e.target.value)} />
            </div>
            <div className="rr-field">
              <label>Category</label>
              <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
                <option value="">No category</option>
                {expenseCategories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Save mode toggle */}
          <div className="rr-mode-toggle">
            <button
              className={`rr-mode-btn ${saveMode === 'total' ? 'active' : ''}`}
              onClick={() => setSaveMode('total')}
            >
              Save as total ({fmt(result.total)})
            </button>
            <button
              className={`rr-mode-btn ${saveMode === 'items' ? 'active' : ''}`}
              onClick={() => setSaveMode('items')}
            >
              Save with line items ({result.items.length} items)
            </button>
          </div>

          {/* Items table */}
          {result.items.length > 0 && (
            <div className="rr-items">
              <div className="rr-items-header">
                <span>Item</span>
                <span>Qty</span>
                <span>Price</span>
                <span>Category</span>
                {saveMode === 'items' && <span>Include</span>}
              </div>

              {items.map((item) => (
                <div
                  key={item.id}
                  className={`rr-item-row ${!item.included && saveMode === 'items' ? 'excluded' : ''}`}
                >
                  <input
                    className="rr-item-name"
                    value={item.name}
                    onChange={(e) => updateItem(item.id, 'name', e.target.value)}
                  />
                  <input
                    className="rr-item-num"
                    type="number"
                    value={item.quantity}
                    onChange={(e) => updateItem(item.id, 'quantity', e.target.value)}
                    min="0.01" step="0.01"
                  />
                  <input
                    className="rr-item-num"
                    type="number"
                    value={item.total_price}
                    onChange={(e) => updateItem(item.id, 'total_price', e.target.value)}
                    min="0" step="0.01"
                  />
                  <div className="rr-item-cat">
                    {item.suggested_category_name && !item.category_id && (
                      <span className="rr-suggestion">
                        {item.suggested_category_name}
                        {' '}
                        <span className="rr-conf">
                          {Math.round((item.suggestion_confidence || 0) * 100)}%
                        </span>
                      </span>
                    )}
                    <select
                      value={item.category_id || ''}
                      onChange={(e) => updateItem(item.id, 'category_id', e.target.value)}
                    >
                      <option value="">—</option>
                      {expenseCategories.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                  </div>
                  {saveMode === 'items' && (
                    <input
                      type="checkbox"
                      checked={item.included}
                      onChange={(e) => updateItem(item.id, 'included', e.target.checked)}
                      className="rr-item-check"
                    />
                  )}
                </div>
              ))}

              <div className="rr-total-row">
                <span>Total</span>
                <span />
                <span className="rr-total-val">{fmt(computedTotal)}</span>
                <span />
              </div>
            </div>
          )}

          {/* No items detected notice */}
          {result.items.length === 0 && (
            <div className="rr-no-items">
              No line items detected. The receipt will be saved as a single transaction
              of {fmt(result.total)}.
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="rr-footer">
          <button className="rr-cancel" onClick={onClose}>Cancel</button>
          <button className="rr-save" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : `Save transaction · ${fmt(computedTotal)}`}
          </button>
        </div>
      </div>
    </div>
  );
}