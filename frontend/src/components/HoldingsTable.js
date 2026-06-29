import './HoldingsTable.css';

const fmtCcy = (n, ccy = 'USD') => {
  if (n === null || n === undefined) return '—';
  const sym = ccy === 'GBP' ? '£' : ccy === 'EUR' ? '€' : '$';
  return `${sym}${Math.abs(parseFloat(n)).toLocaleString('en-GB', {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  })}`;
};

const fmtPct = (n) =>
  n !== null && n !== undefined
    ? `${parseFloat(n) >= 0 ? '+' : ''}${parseFloat(n).toFixed(2)}%`
    : '—';

const fmtShares = (n, dp = 6) =>
  n !== null && n !== undefined
    ? parseFloat(n).toLocaleString('en-GB', { maximumFractionDigits: dp })
    : '—';

export default function HoldingsTable({ holdings, onRemove }) {
  if (!holdings.length) {
    return (
      <div className="ht-empty">
        <p className="ht-empty-text">No holdings yet</p>
        <p className="ht-empty-sub">Click "Add holding" above to get started</p>
      </div>
    );
  }

  return (
    <div className="ht-wrap">
      <table className="ht-table">
        <thead>
          <tr>
            <th>Stock</th>
            <th>Shares</th>
            <th className="ht-right">Buy price</th>
            <th className="ht-right">Current price</th>
            <th className="ht-right">Today</th>
            <th className="ht-right">Cost basis</th>
            <th className="ht-right">Value today</th>
            <th className="ht-right">Gain / Loss</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => {
            const ccy         = h.original_currency || 'USD';
            const hasSplit    = parseFloat(h.split_factor || 1) > 1;
            const gainClass   = h.gain === null ? '' : h.gain >= 0 ? 'ht-up' : 'ht-down';
            const changeClass = h.change_pct >= 0 ? 'ht-up' : 'ht-down';

            return (
              <tr key={h.id}>

                {/* Stock name + date */}
                <td>
                  <div className="ht-stock">
                    <span className="ht-ticker">{h.ticker}</span>
                    <span className="ht-name">{h.name !== h.ticker ? h.name : ''}</span>
                    {h.buy_date && (
                      <span className="ht-date">since {h.buy_date}</span>
                    )}
                  </div>
                </td>

                {/* Shares — the key redesigned column */}
                <td>
                  <div className="ht-shares">
                    {hasSplit ? (
                      <>
                        {/* Original row */}
                        <div className="ht-shares-row ht-shares-original">
                          <span className="ht-shares-dot ht-dot-original" />
                          <span className="ht-shares-label">Original</span>
                          <span className="ht-shares-num">{fmtShares(h.quantity)}</span>
                        </div>

                        {/* Split arrow */}
                        <div className="ht-split-arrow">
                          <span className="ht-split-line" />
                          <span className="ht-split-badge">
                            ×{parseFloat(h.split_factor).toLocaleString('en-GB', { maximumFractionDigits: 0 })} split
                          </span>
                        </div>

                        {/* Today row */}
                        <div className="ht-shares-row ht-shares-today">
                          <span className="ht-shares-dot ht-dot-today" />
                          <span className="ht-shares-label">Today</span>
                          <span className="ht-shares-num ht-shares-num-today">
                            {fmtShares(h.adjusted_quantity)}
                          </span>
                        </div>
                      </>
                    ) : (
                      /* No split — show single row */
                      <div className="ht-shares-row">
                        <span className="ht-shares-dot ht-dot-original" />
                        <span className="ht-shares-num">{fmtShares(h.quantity)}</span>
                        <span className="ht-shares-nosplit">no splits</span>
                      </div>
                    )}
                  </div>
                </td>

                {/* Buy price */}
                <td className="ht-right ht-mono">
                  {h.buy_price !== null
                    ? <>{fmtCcy(h.buy_price, ccy)}<span className="ht-adj">adj.</span></>
                    : <span className="ht-null">—</span>
                  }
                </td>

                {/* Current price */}
                <td className="ht-right ht-mono">
                  {h.current_price !== null
                    ? fmtCcy(h.current_price, ccy)
                    : <span className="ht-null">—</span>
                  }
                </td>

                {/* Today's % move */}
                <td className={`ht-right ${changeClass}`}>
                  {h.change_pct !== undefined ? fmtPct(h.change_pct) : '—'}
                </td>

                {/* Cost basis */}
                <td className="ht-right ht-mono">
                  {h.cost_basis !== null
                    ? fmtCcy(h.cost_basis, ccy)
                    : <span className="ht-null">—</span>
                  }
                </td>

                {/* Current value */}
                <td className="ht-right ht-mono ht-bold">
                  {h.current_value !== null
                    ? fmtCcy(h.current_value, ccy)
                    : <span className="ht-null">—</span>
                  }
                </td>

                {/* Gain / Loss */}
                <td className={`ht-right ${gainClass}`}>
                  {h.gain !== null ? (
                    <div className="ht-gain">
                      <span>{h.gain >= 0 ? '+' : ''}{fmtCcy(h.gain, ccy)}</span>
                      <span className="ht-gain-pct">{fmtPct(h.gain_pct)}</span>
                    </div>
                  ) : <span className="ht-null">—</span>}
                </td>

                {/* Remove */}
                <td>
                  <button
                    className="ht-remove"
                    onClick={() => onRemove(h)}
                    title={`Remove ${h.ticker}`}
                  >✕</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}