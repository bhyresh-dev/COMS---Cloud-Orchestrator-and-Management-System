import { useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';

// ── Icons ────────────────────────────────────────────────────
const I = ({ d, size = 16, fill = 'none' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke="currentColor"
    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);
const PlusIcon    = () => <I d="M12 5v14M5 12h14" />;
const ArrowUpIcon = () => <I d="M12 19V5M5 12l7-7 7 7" />;
const ChevronDown = () => <I d="M6 9l6 6 6-6" size={14} />;
const ArrowRight  = () => <I d="M5 12h14M12 5l7 7-7 7" size={14} />;
const BucketIcon  = () => <I d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />;
const TrashIcon   = () => <I d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" />;
const ZapIcon     = () => <I d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="currentColor" stroke="none" />;
const XIcon       = () => <I d="M18 6L6 18M6 6l12 12" size={14} />;

const TABS = ['My Buckets', 'Recent Activity', 'Pending'];
const BUCKET_GRADIENTS = [
  'from-violet-500 to-indigo-600',
  'from-pink-500   to-rose-600',
  'from-cyan-500   to-blue-600',
  'from-amber-500  to-orange-600',
  'from-emerald-500 to-teal-600',
];

export default function Dashboard() {
  const { profile, getToken } = useAuth();
  const firstName = profile?.name?.split(' ')[0] || profile?.email?.split('@')[0] || 'you';

  // Chat state
  const [message,     setMessage]    = useState('');
  const [submitting,  setSubmitting] = useState(false);
  const [chatOpen,    setChatOpen]   = useState(false);
  const [messages,    setMessages]   = useState([]);       // [{role,text,status,data}]
  const [convHistory, setConvHistory] = useState([]);      // raw backend history
  const chatEndRef = useRef(null);

  // Buckets / tabs
  const [buckets,   setBuckets]  = useState([]);
  const [buckLoad,  setBuckLoad] = useState(true);
  const [activeTab, setActiveTab] = useState('My Buckets');

  const loadBuckets = useCallback(async () => {
    setBuckLoad(true);
    try {
      const data = await api.get('/api/buckets', getToken);
      setBuckets(data.buckets || []);
    } catch { /* silent */ }
    finally { setBuckLoad(false); }
  }, [getToken]);

  useEffect(() => { loadBuckets(); }, [loadBuckets]);

  // Auto-scroll chat to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSubmit() {
    const text = message.trim();
    if (!text || submitting) return;

    // Open chat panel on first message
    if (!chatOpen) setChatOpen(true);

    // Add user bubble
    setMessages(prev => [...prev, { role: 'user', text }]);
    setMessage('');
    setSubmitting(true);

    try {
      const data = await api.post('/api/nlp/process', {
        message: text,
        conversation_history: convHistory,
      }, getToken);

      // Update conversation history for next round
      setConvHistory(data.conversation_history || []);

      // Build AI bubble
      const aiMsg = { role: 'ai', text: data.message, status: data.status, data };

      setMessages(prev => [...prev, aiMsg]);

      if (data.status === 'executed') {
        loadBuckets();
        // Reset conversation after successful execution
        setConvHistory([]);
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'ai', text: err.message || 'Something went wrong.', status: 'error', data: null,
      }]);
      setConvHistory([]);
    } finally {
      setSubmitting(false);
    }
  }

  function handleNewConversation() {
    setMessages([]);
    setConvHistory([]);
    setChatOpen(false);
  }

  async function handleDelete(name) {
    if (!window.confirm(`Delete "${name}"?`)) return;
    try {
      await api.del(`/api/buckets/${encodeURIComponent(name)}`, getToken);
      loadBuckets();
    } catch (err) { alert(`Delete failed: ${err.message}`); }
  }

  return (
    <div className="flex flex-col min-h-full">

      {/* ── Hero ─────────────────────────────────────────────── */}
      <div className="relative hero-gradient flex flex-col items-center px-8 py-20 overflow-hidden">
        <h1 className="text-4xl font-bold text-white mb-8 tracking-tight text-center drop-shadow-md">
          What should we provision, {firstName}?
        </h1>

        <div className="w-full max-w-2xl flex flex-col gap-3">

          {/* ── Chat panel ─────────────────────────────────── */}
          {chatOpen && (
            <div className="bg-[#0d1020]/90 backdrop-blur-md border border-white/[0.10] rounded-2xl overflow-hidden shadow-2xl shadow-black/60">
              {/* Panel header */}
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.07]">
                <div className="flex items-center gap-2 text-white/50 text-xs font-medium">
                  <span className="text-violet-400"><ZapIcon /></span>
                  COMS Assistant
                </div>
                <button
                  onClick={handleNewConversation}
                  className="text-white/25 hover:text-white/60 transition-colors"
                  title="New conversation"
                >
                  <XIcon />
                </button>
              </div>

              {/* Messages */}
              <div className="max-h-[360px] overflow-y-auto px-4 py-3 space-y-3 scrollbar-thin">
                {messages.map((msg, i) => (
                  <ChatBubble key={i} msg={msg} />
                ))}
                {submitting && (
                  <div className="flex items-center gap-2.5">
                    <div className="w-6 h-6 rounded-full bg-violet-600/30 border border-violet-500/30 flex items-center justify-center flex-shrink-0">
                      <ZapIcon />
                    </div>
                    <div className="flex gap-1 items-center py-2">
                      <span className="w-1.5 h-1.5 bg-white/30 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-1.5 h-1.5 bg-white/30 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-1.5 h-1.5 bg-white/30 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
            </div>
          )}

          {/* ── NLP Input ──────────────────────────────────── */}
          <div className="bg-[#161926]/80 backdrop-blur-md border border-white/[0.11] rounded-2xl px-5 pt-4 pb-3 shadow-2xl shadow-black/50">
            <textarea
              value={message}
              onChange={e => setMessage(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
              rows={2}
              placeholder={
                convHistory.length > 0
                  ? 'Reply to COMS...'
                  : 'Ask COMS to provision a cloud resource for your team...'
              }
              className="w-full bg-transparent text-white/90 placeholder-white/28 outline-none text-[15px] leading-relaxed resize-none"
            />

            {/* Toolbar row */}
            <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-white/[0.07]">
              <button
                onClick={handleNewConversation}
                className="text-white/35 hover:text-white/65 transition-colors p-1 rounded-lg hover:bg-white/[0.06]"
                title="New conversation"
              >
                <PlusIcon />
              </button>

              <div className="flex items-center gap-3">
                {convHistory.length > 0 && (
                  <span className="text-[11px] text-violet-400/70 border border-violet-500/20 bg-violet-500/10 px-2 py-0.5 rounded-full">
                    in conversation
                  </span>
                )}
                <div className="flex items-center gap-1.5 text-white/45 text-sm hover:text-white/70 cursor-pointer transition-colors select-none">
                  <span>Build</span>
                  <ChevronDown />
                </div>
                <button
                  onClick={handleSubmit}
                  disabled={!message.trim() || submitting}
                  className="bg-white/[0.18] hover:bg-white/[0.28] disabled:opacity-30 disabled:cursor-not-allowed rounded-full p-2 transition-colors"
                >
                  {submitting
                    ? <span className="block w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    : <ArrowUpIcon />}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Bottom panel ─────────────────────────────────────── */}
      <div className="flex-1 bg-[#0d0f17] rounded-t-2xl px-8 pt-6 pb-10 min-h-[380px]">
        <div className="flex items-center gap-1 mb-6">
          {TABS.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={[
                'px-4 py-1.5 rounded-full text-sm font-medium transition-colors',
                activeTab === tab ? 'bg-white/[0.10] text-white' : 'text-white/40 hover:text-white/65',
              ].join(' ')}
            >
              {tab}
            </button>
          ))}
          <button
            onClick={loadBuckets}
            className="ml-auto flex items-center gap-1.5 text-white/35 hover:text-white/60 text-sm transition-colors"
          >
            Browse all <ArrowRight />
          </button>
        </div>

        {activeTab === 'My Buckets'      && <BucketsGrid buckets={buckets} loading={buckLoad} onDelete={handleDelete} />}
        {activeTab === 'Recent Activity' && <RecentActivity getToken={getToken} />}
        {activeTab === 'Pending'         && <PendingList    getToken={getToken} />}
      </div>
    </div>
  );
}

// ── Chat bubble ──────────────────────────────────────────────
function ChatBubble({ msg }) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-violet-600/25 border border-violet-500/20 rounded-2xl rounded-tr-sm px-4 py-2.5">
          <p className="text-white/85 text-sm leading-relaxed">{msg.text}</p>
        </div>
      </div>
    );
  }

  // AI bubble
  const status = msg.status;
  const data   = msg.data;

  const statusColors = {
    executed:             'text-emerald-400',
    clarification_needed: 'text-blue-400',
    pending_approval:     'text-amber-400',
    denied:               'text-red-400',
    error:                'text-red-400',
  };
  const statusLabels = {
    executed:             '✓ Executed',
    clarification_needed: '? Clarification needed',
    pending_approval:     '⏳ Pending approval',
    denied:               '✗ Denied',
    error:                '✗ Error',
  };

  return (
    <div className="flex items-start gap-2.5">
      <div className="w-6 h-6 rounded-full bg-violet-600/30 border border-violet-500/30 flex items-center justify-center flex-shrink-0 mt-0.5">
        <ZapIcon />
      </div>
      <div className="flex-1 min-w-0">
        {status && (
          <p className={`text-[11px] font-semibold mb-1 ${statusColors[status] || 'text-white/40'}`}>
            {statusLabels[status] || status}
          </p>
        )}
        <p className="text-white/75 text-sm leading-relaxed">{msg.text}</p>

        {/* Violations */}
        {data?.violations?.length > 0 && (
          <div className="mt-2 space-y-0.5">
            {data.violations.map((v, i) => (
              <p key={i} className="text-red-400 text-xs">{v}</p>
            ))}
          </div>
        )}

        {/* Auto-applied defaults for high-risk resources */}
        {data?.status === 'pending_approval' && data?.risk_result && (
          <div className="mt-2 bg-amber-500/[0.06] border border-amber-500/20 rounded-xl p-3 space-y-1.5">
            {data.risk_result.auto_applied && Object.keys(data.risk_result.auto_applied).length > 0 && (
              <div className="space-y-1 mb-2">
                <p className="text-[11px] font-semibold text-white/40 uppercase tracking-wider">Auto-applied defaults</p>
                {Object.entries(data.risk_result.auto_applied).map(([k, v]) => (
                  <p key={k} className="text-xs text-white/55">
                    <span className="text-white/30">{k.replace(/_/g, ' ')}: </span>
                    <span className="font-mono text-white/70">{String(v)}</span>
                  </p>
                ))}
              </div>
            )}
            <div className="flex items-center gap-2 pt-1 border-t border-amber-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
              <p className="text-xs text-amber-400 font-medium">Admin approval required before execution</p>
            </div>
          </div>
        )}

        {/* Resource details (executed) */}
        {data?.resource && Object.keys(data.resource).length > 0 && (
          <div className="mt-2 bg-white/[0.04] border border-white/[0.07] rounded-xl p-3 font-mono text-xs space-y-1">
            {Object.entries(data.resource).map(([k, v]) => (
              <div key={k}>
                <span className="text-white/30">{k}: </span>
                <span className="text-white/65">{String(v)}</span>
              </div>
            ))}
          </div>
        )}

        {/* Pipeline stages */}
        {data?.pipeline_stages?.length > 0 && (
          <div className="mt-2 pt-2 border-t border-white/[0.06] space-y-1">
            {data.pipeline_stages.map((s, i) => (
              <div key={i} className="flex items-center gap-2 text-[11px]">
                <span className={s.status === 'success' || s.status === 'approved' ? 'text-emerald-400' : 'text-red-400'}>
                  {s.status === 'success' || s.status === 'approved' ? '✓' : '✗'}
                </span>
                <span className="text-white/40 flex-1">{s.stage}</span>
                <span className="text-white/20">{s.time_seconds}s</span>
              </div>
            ))}
            {data.total_time_seconds > 0 && (
              <p className="text-white/20 text-[10px] pt-0.5">{data.total_time_seconds.toFixed(2)}s total</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Bucket grid ──────────────────────────────────────────────
function BucketsGrid({ buckets, loading, onDelete }) {
  if (loading) return <p className="text-white/30 text-sm">Loading buckets...</p>;
  if (buckets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="w-12 h-12 rounded-xl bg-white/[0.05] flex items-center justify-center text-white/25 mb-3">
          <BucketIcon />
        </div>
        <p className="text-white/40 text-sm">No buckets yet.</p>
        <p className="text-white/22 text-xs mt-1">Submit a request above to create your first S3 bucket.</p>
      </div>
    );
  }
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
      {buckets.map((b, i) => (
        <div
          key={b.id || b.resource_name}
          className="group bg-white/[0.04] border border-white/[0.07] rounded-xl p-4 hover:bg-white/[0.07] hover:border-white/[0.12] transition-all cursor-pointer"
        >
          <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${BUCKET_GRADIENTS[i % BUCKET_GRADIENTS.length]} mb-3 shadow-lg`} />
          <p className="text-white/85 text-sm font-medium truncate leading-tight">{b.resource_name}</p>
          <p className="text-white/35 text-xs mt-1">{b.region}</p>
          <p className="text-white/20 text-[11px] mt-0.5">{fmtDate(b.timestamp)}</p>
          <button
            onClick={e => { e.stopPropagation(); onDelete(b.resource_name); }}
            className="mt-2 opacity-0 group-hover:opacity-100 text-white/30 hover:text-red-400 transition-all"
          >
            <TrashIcon />
          </button>
        </div>
      ))}
    </div>
  );
}

// ── Recent activity ──────────────────────────────────────────
function RecentActivity({ getToken }) {
  const [logs, setLogs] = useState([]);
  const [load, setLoad] = useState(true);
  useEffect(() => {
    api.get('/api/audit?limit=10', getToken)
      .then(d => setLogs(d.entries || []))
      .catch(() => {})
      .finally(() => setLoad(false));
  }, [getToken]);
  if (load) return <p className="text-white/30 text-sm">Loading...</p>;
  if (!logs.length) return <p className="text-white/30 text-sm">No recent activity.</p>;
  return (
    <div className="space-y-2 max-w-2xl">
      {logs.map(l => (
        <div key={l.id} className="flex items-center gap-4 bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3">
          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${l.status === 'success' ? 'bg-emerald-400' : l.status === 'denied' ? 'bg-red-400' : 'bg-amber-400'}`} />
          <span className="text-white/70 text-sm flex-1 truncate">{l.action}</span>
          <span className="text-white/25 text-xs flex-shrink-0">{fmtDate(l.timestamp)}</span>
        </div>
      ))}
    </div>
  );
}

// ── Pending approvals ────────────────────────────────────────
function PendingList({ getToken }) {
  const [items, setItems] = useState([]);
  const [load,  setLoad]  = useState(true);
  useEffect(() => {
    api.get('/api/approvals', getToken)
      .then(d => setItems(d.approvals || []))
      .catch(() => {})
      .finally(() => setLoad(false));
  }, [getToken]);
  if (load) return <p className="text-white/30 text-sm">Loading...</p>;
  if (!items.length) return <p className="text-white/30 text-sm">No pending approvals.</p>;
  return (
    <div className="space-y-2 max-w-2xl">
      {items.map(a => (
        <div key={a.id} className="flex items-start gap-4 bg-white/[0.03] border border-amber-500/20 rounded-xl px-4 py-3">
          <span className="w-2 h-2 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-white/75 text-sm">{a.parsed_request?.intent?.replace(/_/g, ' ')}</p>
            <p className="text-white/30 text-xs mt-0.5">{fmtDate(a.timestamp)}</p>
          </div>
          <span className="text-amber-400 text-xs bg-amber-500/10 px-2 py-0.5 rounded-full flex-shrink-0">pending</span>
        </div>
      ))}
    </div>
  );
}

function fmtDate(iso) {
  if (!iso) return '';
  try { return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }); }
  catch { return iso; }
}
