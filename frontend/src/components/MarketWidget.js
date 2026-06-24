import { useState } from 'react';
import { useMarketOverview, useMarketNews } from '../hooks/useMarket';
import './MarketWidget.css';

export default function MarketWidget() {
  const { indices, loading: idxLoading } = useMarketOverview();
  const { news,    loading: newsLoading } = useMarketNews('^GSPC', 4);
  const [tab, setTab] = useState('indices'); // 'indices' | 'news'

  return (
    <div className="mw-wrap">
      <div className="mw-header">
        <span className="mw-title">Markets</span>
        <div className="mw-tabs">
          <button
            className={`mw-tab ${tab === 'indices' ? 'active' : ''}`}
            onClick={() => setTab('indices')}
          >Indices</button>
          <button
            className={`mw-tab ${tab === 'news' ? 'active' : ''}`}
            onClick={() => setTab('news')}
          >News</button>
        </div>
        <span className="mw-live">● Live</span>
      </div>

      {tab === 'indices' && (
        <div className="mw-indices">
          {idxLoading
            ? [...Array(4)].map((_, i) => <div key={i} className="mw-skeleton" />)
            : indices.map((idx) => (
              <div key={idx.ticker} className="mw-index-row">
                <div className="mw-idx-info">
                  <span className="mw-idx-label">{idx.label}</span>
                  <span className="mw-idx-ticker">{idx.ticker}</span>
                </div>
                <div className="mw-idx-prices">
                  <span className="mw-idx-price">
                    {idx.currency === 'GBP' ? '£' : '$'}
                    {idx.price.toLocaleString()}
                  </span>
                  <span className={`mw-idx-change ${idx.change_pct >= 0 ? 'up' : 'down'}`}>
                    {idx.change_pct >= 0 ? '▲' : '▼'} {Math.abs(idx.change_pct).toFixed(2)}%
                  </span>
                </div>
              </div>
            ))
          }
        </div>
      )}

      {tab === 'news' && (
        <div className="mw-news">
          {newsLoading
            ? [...Array(4)].map((_, i) => <div key={i} className="mw-skeleton" />)
            : news.length === 0
              ? <p className="mw-empty">No news available</p>
              : news.map((item, i) => (
                <a
                  key={i}
                  href={item.url || '#'}
                  target="_blank"
                  rel="noreferrer"
                  className="mw-news-item"
                >
                  <span className="mw-news-title">{item.title}</span>
                  <span className="mw-news-meta">
                    {item.source}{item.published ? ` · ${item.published}` : ''}
                  </span>
                </a>
              ))
          }
        </div>
      )}
    </div>
  );
}
