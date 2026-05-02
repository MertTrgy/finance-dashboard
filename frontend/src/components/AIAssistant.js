import { useState, useRef, useEffect } from 'react';
import { useAI } from '../hooks/useAI';
import './AIAssistant.css';

const PROVIDER_LABELS = {
  claude: { name: 'Claude',  color: '#d97757' },
  gemini: { name: 'Gemini',  color: '#185fa5' },
  ollama: { name: 'Ollama',  color: '#15803d' },
};

function getActiveProvider() {
  try {
    const s = localStorage.getItem('finance_ai_settings');
    return s ? JSON.parse(s).provider : 'gemini';
  } catch { return 'gemini'; }
}

const renderContent = (text) => {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**'))
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith('`') && part.endsWith('`'))
      return <code key={i} className="ai-inline-code">{part.slice(1, -1)}</code>;
    return part.split('\n').map((line, j, arr) => (
      <span key={`${i}-${j}`}>{line}{j < arr.length - 1 && <br />}</span>
    ));
  });
};

export default function AIAssistant({ month }) {
  const { messages, streaming, error, sendMessage, stop, clear, suggestedQuestions } = useAI(month);
  const [input, setInput]     = useState('');
  const bottomRef             = useRef(null);
  const inputRef              = useRef(null);
  const provider              = getActiveProvider();
  const providerMeta          = PROVIDER_LABELS[provider] || PROVIDER_LABELS.gemini;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || streaming) return;
    const text = input.trim();
    setInput('');
    await sendMessage(text);
    inputRef.current?.focus();
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  return (
    <div className="ai-wrap">
      <div className="ai-header">
        <div className="ai-header-left">
          <span className="ai-icon">◈</span>
          <span className="ai-title">Finance assistant</span>
          <span
            className="ai-badge"
            style={{ background: `${providerMeta.color}18`, color: providerMeta.color }}
          >
            {providerMeta.name}
          </span>
        </div>
        {messages.length > 0 && (
          <button className="ai-clear" onClick={clear}>Clear</button>
        )}
      </div>

      <div className="ai-body">
        {messages.length === 0 && (
          <div className="ai-empty">
            <p className="ai-empty-hint">Ask me anything about your finances</p>
            <div className="ai-suggestions">
              {suggestedQuestions.map((q) => (
                <button key={q} className="ai-suggestion" onClick={() => !streaming && sendMessage(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.length > 0 && (
          <div className="ai-messages">
            {messages.map((msg, i) => (
              <div key={i} className={`ai-msg ai-msg--${msg.role}`}>
                {msg.role === 'assistant' && <span className="ai-msg-icon">◈</span>}
                <div className="ai-msg-content">
                  {msg.content
                    ? renderContent(msg.content)
                    : <span className="ai-cursor">▋</span>
                  }
                  {streaming && i === messages.length - 1 && msg.role === 'assistant' && msg.content && (
                    <span className="ai-cursor">▋</span>
                  )}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}

        {error && <div className="ai-error">{error}</div>}
      </div>

      <div className="ai-input-row">
        <textarea
          ref={inputRef}
          className="ai-input"
          placeholder="Ask about your spending, budget, or finances…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          rows={1}
          disabled={streaming}
        />
        {streaming
          ? <button className="ai-send ai-stop" onClick={stop} title="Stop">■</button>
          : <button className="ai-send" onClick={handleSend} disabled={!input.trim()} title="Send">↑</button>
        }
      </div>
      <p className="ai-disclaimer">
        Using {providerMeta.name} · Change provider in{' '}
        <a href="/ai-settings" className="ai-settings-link">AI Settings</a>
      </p>
    </div>
  );
}