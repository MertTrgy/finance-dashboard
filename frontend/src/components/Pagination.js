import './Pagination.css';

export default function Pagination({ pagination, onPageChange }) {
  const { count, pages, page } = pagination;
  if (!pages || pages <= 1) return null;

  const canPrev = page > 1;
  const canNext = page < pages;

  // Build visible page numbers — show at most 5 around current
  const getPages = () => {
    const range = [];
    const delta = 2;
    for (let i = Math.max(1, page - delta); i <= Math.min(pages, page + delta); i++) {
      range.push(i);
    }
    return range;
  };

  const visiblePages = getPages();
  const showFirst    = visiblePages[0] > 1;
  const showLast     = visiblePages[visiblePages.length - 1] < pages;

  return (
    <div className="pg-wrap">
      <span className="pg-count">{count} transaction{count !== 1 ? 's' : ''}</span>
      <div className="pg-controls">
        <button
          className="pg-btn"
          onClick={() => onPageChange(page - 1)}
          disabled={!canPrev}
          aria-label="Previous page"
        >‹</button>

        {showFirst && (
          <>
            <button className="pg-btn" onClick={() => onPageChange(1)}>1</button>
            {visiblePages[0] > 2 && <span className="pg-ellipsis">…</span>}
          </>
        )}

        {visiblePages.map((p) => (
          <button
            key={p}
            className={`pg-btn ${p === page ? 'active' : ''}`}
            onClick={() => onPageChange(p)}
          >
            {p}
          </button>
        ))}

        {showLast && (
          <>
            {visiblePages[visiblePages.length - 1] < pages - 1 && (
              <span className="pg-ellipsis">…</span>
            )}
            <button className="pg-btn" onClick={() => onPageChange(pages)}>{pages}</button>
          </>
        )}

        <button
          className="pg-btn"
          onClick={() => onPageChange(page + 1)}
          disabled={!canNext}
          aria-label="Next page"
        >›</button>
      </div>
    </div>
  );
}