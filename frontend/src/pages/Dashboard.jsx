import { useRef, useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useChat } from '../contexts/ChatContext';
import { api } from '../api';


const I = ({ d, size = 16, fill = 'none' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke="currentColor"
    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={d} /></svg>
);
const ArrowUpIcon = () => <I d="M12 19V5M5 12l7-7 7 7" />;
const PlusIcon    = () => <I d="M12 5v14M5 12h14" />;
const ZapIcon     = () => <I d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="currentColor" stroke="none" />;

const SUGGESTIONS = [
  'Create an S3 bucket for my project',
  'Create an IAM role for EC2',
  'Launch an EC2 instance',
  'Create a Lambda function',
];

export default function Dashboard() {
  const { profile, getToken } = useAuth();
  const firstName = profile?.name?.split(' ')[0] || profile?.email?.split('@')[0] || 'you';

  const {
    messages, convHistory,
    appendMessage, updateConvHistory,
    ensureSession, newSession,
  } = useChat();

  const [message,    setMessage]    = useState('');
  const [submitting, setSubmitting] = useState(false);
  const chatEndRef  = useRef(null);
  const textareaRef = useRef(null);

  const started = messages.length > 0;

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  async function handleSubmit(text) {
    const msg = (text || message).trim();
    if (!msg || submitting) return;

    const sid = ensureSession();
    appendMessage({ role: 'user', text: msg }, sid);
    setMessage('');
    setSubmitting(true);

    try {
      const data = await api.post('/api/nlp/process', { message: msg, conversation_history: convHistory }, getToken);
      const newHist = data.conversation_history || [];
      updateConvHistory(data.status === 'executed' ? [] : newHist, sid);
      appendMessage({ role: 'ai', text: data.message, status: data.status, data }, sid);
    } catch (err) {
      appendMessage({ role: 'ai', text: err.message || 'Something went wrong.', status: 'error', data: null }, sid);
      updateConvHistory([], sid);
    } finally { setSubmitting(false); }
  }

  function startNew() {
    newSession();
    setMessage('');
  }

  return (
    <div className="flex flex-col h-full bg-[#080b14]">

      {/* ── Chat history ─────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        {!started ? (
          <div className="flex flex-col items-center justify-center min-h-full px-8 pb-8 pt-16">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-900/40 mb-5">
              <ZapIcon />
            </div>
            <h1 className="text-3xl font-bold text-white tracking-tight text-center mb-2">
              Hi {firstName}, I'm COMS
            </h1>
            <p className="text-white/55 text-base text-center max-w-md mb-10">
              Your AI cloud orchestrator. Tell me what to provision and I'll handle the rest.
            </p>
            <div className="grid grid-cols-2 gap-2 w-full max-w-lg mb-10">
              {SUGGESTIONS.map(s => (
                <button key={s} onClick={() => handleSubmit(s)}
                  className="text-left px-4 py-3 bg-white/[0.05] hover:bg-white/[0.09] border border-white/[0.09] hover:border-white/[0.14] rounded-xl text-sm text-white/65 hover:text-white/90 transition-all">
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-2xl mx-auto px-6 py-8 space-y-6">
            {messages.map((msg, i) => <ChatMessage key={i} msg={msg} />)}
            {submitting && (
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-full bg-violet-600/30 border border-violet-500/30 flex items-center justify-center flex-shrink-0">
                  <ZapIcon />
                </div>
                <div className="flex gap-1 items-center">
                  {[0, 150, 300].map(d => (
                    <span key={d} className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce" style={{ animationDelay: `${d}ms` }} />
                  ))}
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
        )}
      </div>

      {/* ── Input bar ────────────────────────────────────────── */}
      <div className="flex-shrink-0 px-6 pb-6 pt-2">
        <div className="max-w-2xl mx-auto">
          <div className="bg-[#161926]/90 backdrop-blur-md border border-white/[0.13] rounded-2xl px-4 pt-3 pb-2.5 shadow-2xl shadow-black/50">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={e => setMessage(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
              rows={1}
              placeholder={convHistory.length > 0 ? 'Reply to COMS...' : 'Ask COMS to provision a resource...'}
              className="w-full bg-transparent text-white/90 placeholder-white/35 outline-none text-[15px] leading-relaxed resize-none"
              style={{ minHeight: '28px', maxHeight: '120px' }}
              onInput={e => { e.target.style.height = 'auto'; e.target.style.height = e.target.scrollHeight + 'px'; }}
            />
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/[0.08]">
              <div className="flex items-center gap-2">
                {started && (
                  <button onClick={startNew} title="New conversation"
                    className="text-white/40 hover:text-white/70 transition-colors p-1 rounded hover:bg-white/[0.06]">
                    <PlusIcon />
                  </button>
                )}
                {convHistory.length > 0 && (
                  <span className="text-[11px] text-violet-400/80 border border-violet-500/25 bg-violet-500/10 px-2 py-0.5 rounded-full">
                    in conversation
                  </span>
                )}
              </div>
              <button onClick={() => handleSubmit()} disabled={!message.trim() || submitting}
                className="bg-white/[0.18] hover:bg-white/[0.28] disabled:opacity-30 disabled:cursor-not-allowed rounded-full p-2 transition-colors">
                {submitting
                  ? <span className="block w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  : <ArrowUpIcon />}
              </button>
            </div>
          </div>
          <p className="text-center text-white/25 text-[11px] mt-2">COMS can make mistakes. Verify important actions.</p>
        </div>
      </div>
    </div>
  );
}

function ChatMessage({ msg }) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] bg-violet-600/20 border border-violet-500/25 rounded-2xl rounded-tr-sm px-4 py-3">
          <p className="text-white/90 text-sm leading-relaxed">{msg.text}</p>
        </div>
      </div>
    );
  }

  const { status, data } = msg;
  const colors = {
    executed:             'text-emerald-400',
    clarification_needed: 'text-blue-400',
    pending_approval:     'text-amber-400',
    denied:               'text-red-400',
    error:                'text-red-400',
  };
  const labels = {
    executed:             '✓ Executed',
    clarification_needed: '? Needs clarification',
    pending_approval:     '⏳ Pending approval',
    denied:               '✗ Denied',
    error:                '✗ Error',
  };

  return (
    <div className="flex items-start gap-3">
      <div className="w-7 h-7 rounded-full bg-violet-600/30 border border-violet-500/30 flex items-center justify-center flex-shrink-0 mt-0.5">
        <ZapIcon />
      </div>
      <div className="flex-1 min-w-0 space-y-2">
        {status && (
          <p className={`text-[11px] font-semibold ${colors[status] || 'text-white/50'}`}>
            {labels[status] || status}
          </p>
        )}
        <p className="text-white/85 text-sm leading-relaxed">{msg.text}</p>

        {status === 'pending_approval' && data?.risk_result && (
          <div className="bg-amber-500/[0.06] border border-amber-500/20 rounded-xl p-3 space-y-1.5">
            {data.risk_result.auto_applied && Object.keys(data.risk_result.auto_applied).length > 0 && (
              <div className="space-y-1 pb-2">
                <p className="text-[10px] font-semibold text-white/35 uppercase tracking-wider">Auto-applied defaults</p>
                {Object.entries(data.risk_result.auto_applied).map(([k, v]) => (
                  <p key={k} className="text-xs text-white/55">
                    <span className="text-white/30">{k.replace(/_/g, ' ')}: </span>
                    <span className="font-mono text-white/70">{String(v)}</span>
                  </p>
                ))}
              </div>
            )}
            <div className="flex items-center gap-2 pt-1.5 border-t border-amber-500/15">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
              <p className="text-xs text-amber-400 font-medium">Admin approval required before execution</p>
            </div>
          </div>
        )}

        {data?.violations?.length > 0 && (
          <div className="space-y-0.5">
            {data.violations.map((v, i) => <p key={i} className="text-red-400 text-xs">{v}</p>)}
          </div>
        )}

        {data?.resource && Object.keys(data.resource).length > 0 && (
          <div className="bg-white/[0.04] border border-white/[0.08] rounded-xl p-3 font-mono text-xs space-y-1">
            {Object.entries(data.resource).map(([k, v]) => (
              <div key={k}><span className="text-white/35">{k}: </span><span className="text-white/70">{String(v)}</span></div>
            ))}
          </div>
        )}

        {data?.pipeline_stages?.length > 0 && (
          <div className="pt-1 border-t border-white/[0.06] space-y-1">
            {data.pipeline_stages.map((s, i) => (
              <div key={i} className="flex items-center gap-2 text-[11px]">
                <span className={s.status === 'success' || s.status === 'approved' ? 'text-emerald-400' : 'text-red-400'}>
                  {s.status === 'success' || s.status === 'approved' ? '✓' : '✗'}
                </span>
                <span className="text-white/45 flex-1">{s.stage}</span>
                <span className="text-white/25">{s.time_seconds}s</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
