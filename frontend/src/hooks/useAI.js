import { useState, useCallback, useRef } from 'react';

const SUGGESTED_QUESTIONS = [
  'Why am I overspending this month?',
  'How does my spending compare to last month?',
  'Which category should I cut back on?',
  'Am I on track to save money this month?',
  'What are my biggest expenses?',
  'Give me a summary of my finances',
];

export function useAI(month) {
  const [messages, setMessages]   = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError]         = useState(null);
  const abortRef                  = useRef(null);

  // Read the active provider from localStorage so the hook
  // always uses whatever the user last selected in Settings
  const getProvider = () => {
    try {
      const stored = localStorage.getItem('finance_ai_settings');
      return stored ? JSON.parse(stored).provider : 'gemini';
    } catch {
      return 'gemini';
    }
  };

  const sendMessage = useCallback(async (userText) => {
    if (!userText.trim() || streaming) return;

    const userMsg    = { role: 'user', content: userText.trim() };
    const newHistory = [...messages, userMsg];
    setMessages(newHistory);
    setStreaming(true);
    setError(null);

    // Add placeholder the streaming will fill
    setMessages([...newHistory, { role: 'assistant', content: '' }]);

    const token    = localStorage.getItem('access');
    const provider = getProvider();

    try {
      const controller = new AbortController();
      abortRef.current = controller;

      const res = await fetch('http://localhost:8000/api/ai/chat/', {
        method:  'POST',
        headers: {
          'Content-Type':  'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body:   JSON.stringify({ messages: newHistory, month, provider }),
        signal: controller.signal,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let   buffer  = '';
      let   full    = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const payload = line.slice(6);
          if (payload === '[DONE]') break;
          full += payload.replace(/\\n/g, '\n');
          const snapshot = full;
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = { role: 'assistant', content: snapshot };
            return updated;
          });
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError('Could not reach the AI. Check your settings and server.');
        setMessages((prev) => prev.filter((_, i) => i < prev.length - 1));
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }, [messages, streaming, month]);

  const stop  = () => abortRef.current?.abort();
  const clear = () => { setMessages([]); setError(null); };

  return { messages, streaming, error, sendMessage, stop, clear, suggestedQuestions: SUGGESTED_QUESTIONS };
}