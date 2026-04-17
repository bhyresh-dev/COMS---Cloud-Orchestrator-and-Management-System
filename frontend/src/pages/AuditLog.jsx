import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';

export default function AuditLog() {
  const { getToken } = useAuth();
  const [logs,    setLogs]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await api.get('/api/audit', getToken);
      setLogs(data.logs || []);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }, [getToken]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="flex flex-col min-h-full bg-[#080b14]">
      <div className="px-8 pt-10 pb-6 border-b border-white/[0.06]">
        <h1 className="text-2xl font-semibold text-white tracking-tight">Audit Log</h1>
        <p className="mt-1 text-sm text-white/40">Complete record of all platform actions.</p>
      </div>

      <div className="px-8 py-6">
        {error && (
          <div className="px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400 mb-6">
            {error}
          </div>
        )}
        {loading && <p className="text-white/30 text-sm">Loading...</p>}

        {!loading && !error && (
          <div className="bg-[#0d0f17] border border-white/[0.07] rounded-2xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  {['Action', 'Status', 'User', 'Timestamp'].map(h => (
                    <th key={h} className="px-5 py-3.5 text-left text-[11px] font-semibold text-white/30 uppercase tracking-widest">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {logs.length === 0 ? (
                  <tr><td colSpan={4} className="px-5 py-10 text-center text-white/25 text-sm">No audit entries found.</td></tr>
                ) : logs.map((log, i) => (
                  <tr key={i} className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
                    <td className="px-5 py-3 font-mono text-xs text-white/65">{log.action}</td>
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
                    <td className="px-5 py-3 text-white/45 text-xs">{log.user_email || log.user_id || '—'}</td>
                    <td className="px-5 py-3 text-white/30 text-xs">{fmtDate(log.timestamp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function fmtDate(iso) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  catch { return iso; }
}
