import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'coms_chat_sessions';
const ACTIVE_KEY  = 'coms_active_session';

function loadSessions() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }
  catch { return []; }
}

const MAX_SESSIONS = 30;
const MAX_MESSAGES_PER_SESSION = 100;

function saveSessions(sessions) {
  const pruned = sessions.slice(0, MAX_SESSIONS).map(s => ({
    ...s,
    messages:    (s.messages    || []).slice(-MAX_MESSAGES_PER_SESSION),
    convHistory: (s.convHistory || []).slice(-40),
  }));
  localStorage.setItem(STORAGE_KEY, JSON.stringify(pruned));
}

const ChatContext = createContext(null);

export function ChatProvider({ children }) {
  const [sessions,       setSessions]       = useState(loadSessions);
  const [activeId,       setActiveId]       = useState(() => localStorage.getItem(ACTIVE_KEY) || null);
  const [messages,       setMessages]       = useState([]);
  const [convHistory,    setConvHistory]    = useState([]);

  // Derive active session
  const activeSession = sessions.find(s => s.id === activeId) || null;

  // Sync messages when active session changes
  useEffect(() => {
    if (activeSession) {
      setMessages(activeSession.messages || []);
      setConvHistory(activeSession.convHistory || []);
    } else {
      setMessages([]);
      setConvHistory([]);
    }
  }, [activeId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (activeId) localStorage.setItem(ACTIVE_KEY, activeId);
    else localStorage.removeItem(ACTIVE_KEY);
  }, [activeId]);

  function _persist(id, msgs, hist) {
    setSessions(prev => {
      const updated = prev.map(s =>
        s.id === id ? { ...s, messages: msgs, convHistory: hist, updatedAt: Date.now() } : s
      );
      saveSessions(updated);
      return updated;
    });
  }

  function newSession() {
    const id = `chat_${Date.now()}`;
    const session = { id, title: 'New chat', messages: [], convHistory: [], createdAt: Date.now(), updatedAt: Date.now() };
    setSessions(prev => {
      const updated = [session, ...prev];
      saveSessions(updated);
      return updated;
    });
    setActiveId(id);
    setMessages([]);
    setConvHistory([]);
    return id;
  }

  function selectSession(id) {
    setActiveId(id);
  }

  function deleteSession(id) {
    setSessions(prev => {
      const updated = prev.filter(s => s.id !== id);
      saveSessions(updated);
      if (activeId === id) {
        setActiveId(updated.length > 0 ? updated[0].id : null);
      }
      return updated;
    });
  }

  const appendMessage = useCallback((msg, id) => {
    const sid = id || activeId;
    if (!sid) return;
    setMessages(prev => {
      const updated = [...prev, msg];
      // Update title from first user message
      setSessions(ss => {
        const session = ss.find(s => s.id === sid);
        const title = (msg.role === 'user' && session?.messages?.length === 0)
          ? msg.text.slice(0, 40) + (msg.text.length > 40 ? '…' : '')
          : session?.title || 'New chat';
        const updatedSessions = ss.map(s =>
          s.id === sid ? { ...s, messages: updated, title, updatedAt: Date.now() } : s
        );
        saveSessions(updatedSessions);
        return updatedSessions;
      });
      return updated;
    });
  }, [activeId]);

  const updateConvHistory = useCallback((hist, id) => {
    const sid = id || activeId;
    if (!sid) return;
    setConvHistory(hist);
    setSessions(prev => {
      const updated = prev.map(s => s.id === sid ? { ...s, convHistory: hist, updatedAt: Date.now() } : s);
      saveSessions(updated);
      return updated;
    });
  }, [activeId]);

  function ensureSession() {
    if (activeId && sessions.find(s => s.id === activeId)) return activeId;
    return newSession();
  }

  return (
    <ChatContext.Provider value={{
      sessions, activeId, activeSession,
      messages, convHistory,
      newSession, selectSession, deleteSession,
      appendMessage, updateConvHistory, ensureSession,
      setMessages, setConvHistory,
    }}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error('useChat must be used inside ChatProvider');
  return ctx;
}
