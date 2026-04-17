import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';

const Icon = ({ d, size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={d} /></svg>
);
const ChevronDown  = () => <Icon d="M6 9l6 6 6-6" />;
const ChevronRight = () => <Icon d="M9 18l6-6-6-6" />;

// Group entries into "sessions" — entries within 15 min of each other belong to same session
function groupBySessions(entries) {
  if (!entries.length) return [];
  const sorted = [...entries].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  const groups = [];
  let current = null;

  for (const entry of sorted) {
    const t = new Date(entry.timestamp).getTime();
    if (!current || current.start - t > 15 * 60 * 1000) {
      current = { id: entry.timestamp, start: t, label: fmtDateTime(entry.timestamp), entries: [] };
      groups.push(current);
    }
    current.entries.push(entry);
  }
  return groups;
}

export default function AuditLog() {
  const { getToken, profile } = useAuth();
  const navigate = useNavigate();
  const isAdmin = profile?.role === 'admin';

  const [logs,     setLogs]     = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState(null);
  const [openGroups, setOpenGroups] = useState({});

  useEffect(() => {
    if (profile && !isAdmin) navigate('/dashboard', { replace: true });
  }, [profile, isAdmin, navigate]);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await api.get('/api/audit?limit=200', getToken);
      const entries = data.entries || [];
      setLogs(entries);
      // Open the first group by default
      const groups = groupBySessions(entries);
      if (groups.length > 0) setOpenGroups({ [groups[0].id]: true });
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }, [getToken]);

  useEffect(() => { if (isAdmin) load(); }, [load, isAdmin]);

  const sessions = groupBySessions(logs);

  function toggleGroup(id) {
    setOpenGroups(prev => ({ ...prev, [id]: !prev[id] }));
  }

  return (
    <div className="flex flex-col min-h-full bg-[#080b14]">
      <div className="px-8 pt-10 pb-6 border-b border-white/[0.06]">
        <h1 className="text-2xl font-semibold text-white tracking-tight">Audit Log</h1>
        <p className="mt-1 text-sm text-white/50">Complete record of all platform actions, grouped by session.</p>
      </div>

      <div className="px-8 py-6 space-y-3">
        {error && (
          <div className="px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400 mb-4">
            {error}
          </div>
        )}
        {loading && <p className="text-white/35 text-sm">Loading...</p>}

        {!loading && !error && sessions.length === 0 && (
          <p className="text-white/30 text-sm">No audit entries found.</p>
        )}

        {!loading && !error && sessions.map((group, gi) => (
          <div key={group.id} className="bg-[#0d0f17] border border-white/[0.07] rounded-2xl overflow-hidden">
            {/* Group header */}
            <button
              onClick={() => toggleGroup(group.id)}
              className="w-full flex items-center gap-3 px-5 py-3.5 border-b border-white/[0.06] hover:bg-white/[0.02] transition-colors"
            >
              <span className="text-white/30">
                {openGroups[group.id] ? <ChevronDown /> : <ChevronRight />}
              </span>
              <span className="text-sm font-medium text-white/70 flex-1 text-left">Session — {group.label}</span>
              <span className="text-xs text-white/30 bg-white/[0.04] px-2 py-0.5 rounded-full">
                {group.entries.length} action{group.entries.length !== 1 ? 's' : ''}
              </span>
            </button>

            {/* Group entries */}
            {openGroups[group.id] && (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/[0.05]">
                    {['Action', 'Status', 'User', 'Timestamp'].map(h => (
                      <th key={h} className="px-5 py-3 text-left text-[11px] font-semibold text-white/30 uppercase tracking-widest">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {group.entries.map((log, i) => (
                    <tr key={i} className="border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02] transition-colors">
                      <td className="px-5 py-3 font-mono text-xs text-white/70">{log.action}</td>
                      <td className="px-5 py-3">
                        <span className={[
                          'text-xs px-2 py-0.5 rounded-full border',
                          log.status === 'success'
                            ? 'bg-emerald-500/12 text-emerald-400 border-emerald-500/20'
                            : 'bg-red-500/12 text-red-400 border-red-500/20',
                        ].join(' ')}>
                          {log.status}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-white/55 text-xs">{log.user_email || log.user_id || '—'}</td>
                      <td className="px-5 py-3 text-white/35 text-xs">{fmtDateTime(log.timestamp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function fmtDateTime(iso) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  catch { return iso; }
}
