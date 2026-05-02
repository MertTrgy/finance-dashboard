import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useAISettings } from '../hooks/useAISettings';
import './AISettings.css';

const PROVIDERS = [
  {
    id:    'gemini',
    name:  'Gemini',
    tag:   'Free tier available',
    tagColor: '#15803d',
    desc:  'Google Gemini 2.0 Flash. Free tier: 1,500 requests/day. Best starting point.',
    link:  'https://aistudio.google.com',
    linkLabel: 'Get free key at aistudio.google.com',
    fields: [
      { key: 'gemini_key', label: 'Gemini API key', placeholder: 'AIza...', type: 'password' },
    ],
  },
  {
    id:    'ollama',
    name:  'Ollama',
    tag:   'Completely free',
    tagColor: '#185fa5',
    desc:  'Runs locally on your Mac. No API key, no cost, works offline. Install from ollama.ai then run: ollama pull llama3',
    link:  'https://ollama.ai',
    linkLabel: 'Download Ollama',
    fields: [
      { key: 'ollama_model', label: 'Model name', placeholder: 'llama3', type: 'text' },
      { key: 'ollama_url',   label: 'Ollama URL',  placeholder: 'http://localhost:11434', type: 'text' },
    ],
  },
  {
    id:    'claude',
    name:  'Claude',
    tag:   'Paid — best quality',
    tagColor: '#d97757',
    desc:  'Anthropic Claude Sonnet. ~$0.003 per conversation. Best quality for financial analysis.',
    link:  'https://console.anthropic.com',
    linkLabel: 'Get key at console.anthropic.com',
    fields: [
      { key: 'anthropic_key', label: 'Anthropic API key', placeholder: 'sk-ant-...', type: 'password' },
    ],
  },
];

export default function AISettings() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { settings, providerStatus, saving, saveMsg, save } = useAISettings();

  const [local, setLocal] = useState(settings);

  const setField = (key, value) => setLocal((s) => ({ ...s, [key]: value }));

  const handleSave = () => save(local);

  const handleProviderSelect = (id) => {
    const next = { ...local, provider: id };
    setLocal(next);
    save(next);
  };

  return (
    <div className="ais-page">
      <header className="dash-header">
        <button className="back-btn" onClick={() => navigate('/')}>← Dashboard</button>
        <span className="dash-logo">Finance</span>
        <button className="logout-btn" onClick={() => { logout(); navigate('/login'); }}>Sign out</button>
      </header>

      <main className="ais-main">
        <div>
          <h1 className="ais-heading">AI settings</h1>
          <p className="ais-sub">Choose your AI provider and configure API keys</p>
        </div>

        {/* Provider selector */}
        <div className="ais-providers">
          {PROVIDERS.map((p) => {
            const active  = local.provider === p.id;
            const ready   = providerStatus?.[p.id]?.available;
            return (
              <div
                key={p.id}
                className={`ais-provider-card ${active ? 'active' : ''}`}
                onClick={() => handleProviderSelect(p.id)}
              >
                <div className="ais-provider-header">
                  <div className="ais-provider-name-row">
                    <span className="ais-provider-name">{p.name}</span>
                    <span
                      className="ais-provider-tag"
                      style={{ color: p.tagColor, background: `${p.tagColor}14` }}
                    >
                      {p.tag}
                    </span>
                  </div>
                  <div className={`ais-radio ${active ? 'active' : ''}`} />
                </div>
                <p className="ais-provider-desc">{p.desc}</p>
                <div className="ais-provider-status">
                  <span className={`ais-status-dot ${ready ? 'ready' : 'not-ready'}`} />
                  <span className="ais-status-label">
                    {ready ? 'Configured and ready' : 'Not yet configured'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Key inputs for active provider */}
        {PROVIDERS.map((p) => {
          if (local.provider !== p.id) return null;
          return (
            <div key={p.id} className="ais-card">
              <h2 className="ais-card-title">{p.name} configuration</h2>

              <a href={p.link} target="_blank" rel="noreferrer" className="ais-ext-link">
                {p.linkLabel} →
              </a>

              <div className="ais-fields">
                {p.fields.map((f) => (
                  <div key={f.key} className="tf-field">
                    <label>{f.label}</label>
                    <input
                      type={f.type}
                      placeholder={f.placeholder}
                      value={local[f.key] || ''}
                      onChange={(e) => setField(f.key, e.target.value)}
                      autoComplete="off"
                    />
                  </div>
                ))}
              </div>

              <div className="ais-save-row">
                <button
                  className="ais-save-btn"
                  onClick={handleSave}
                  disabled={saving}
                >
                  {saving ? 'Saving…' : 'Save configuration'}
                </button>
                {saveMsg && (
                  <span className={`ais-save-msg ${saveMsg === 'Saved' ? 'ok' : 'err'}`}>
                    {saveMsg}
                  </span>
                )}
              </div>
            </div>
          );
        })}

        {/* Ollama setup guide */}
        {local.provider === 'ollama' && (
          <div className="ais-card ais-guide">
            <h2 className="ais-card-title">Setting up Ollama on your Mac</h2>
            <div className="ais-steps">
              <div className="ais-step">
                <span className="ais-step-num">1</span>
                <div>
                  <strong>Install Ollama</strong>
                  <code className="ais-code">brew install ollama</code>
                  <span className="ais-step-or">or download from ollama.ai</span>
                </div>
              </div>
              <div className="ais-step">
                <span className="ais-step-num">2</span>
                <div>
                  <strong>Start the server</strong>
                  <code className="ais-code">ollama serve</code>
                </div>
              </div>
              <div className="ais-step">
                <span className="ais-step-num">3</span>
                <div>
                  <strong>Pull a model</strong>
                  <code className="ais-code">ollama pull llama3</code>
                  <span className="ais-step-or">llama3 (~4GB) is a good balance of speed and quality</span>
                </div>
              </div>
              <div className="ais-step">
                <span className="ais-step-num">4</span>
                <div>
                  <strong>No API key needed</strong>
                  <span className="ais-step-or">Just make sure the URL above matches your Ollama server</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Info card */}
        <div className="ais-card ais-info">
          <h2 className="ais-card-title">How the AI uses your data</h2>
          <p className="ais-info-text">
            Every time you send a message, the assistant reads your current month's transactions,
            budget status, spending breakdown, and recent history directly from the database.
            This context is sent to the AI provider as part of the conversation — your data
            is not stored by any AI provider between sessions.
          </p>
          <p className="ais-info-text" style={{ marginTop: '0.5rem' }}>
            Ollama is the most private option — everything stays on your machine.
          </p>
        </div>
      </main>
    </div>
  );
}