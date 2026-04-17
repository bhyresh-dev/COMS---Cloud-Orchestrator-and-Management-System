import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';

const STATUS_FILTERS = ['all', 'pending', 'approved', 'rejected'];

const StatusBadge = ({ status }) => {
  const cfg = {
    pending:  'bg-amber-500/12 text-amber-400 border-amber-500/20',
    approved: 'bg-emerald-500/12 text-emerald-400 border-emerald-500/20',
    rejected: 'bg-red-500/12 text-red-400 border-red-500/20',
  }[status] || 'bg-white/[0.06] text-white/40 border-white/[0.08]';
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border capitalize ${cfg}`}>
      {status}
    </span>
  );
};

// Extract resource name from parsed_request parameters
function resourceName(a) {
  const p = a.parsed_request?.parameters || {};
  return (
    p.bucket_name || p.role_name || p.function_name ||
    p.instance_id || p.topic_name || p.log_group_name || null
  );
}

// Human-readable intent label
function intentLabel(a) {
  const intent = a.parsed_request?.intent || a.action || '';
  return intent.replace(/_/g, ' ');
}

// Username from email — show part before @
function displayUser(a) {
  const email = a.user_email || '';
  return email ? email.split('@')[0] : (a.user_id?.slice(0, 8) || '—');
}

export default function Approvals() {
  const { getToken, profile } = useAuth();
  const isAdmin = profile?.role === 'admin';

  const [approvals,   setApprovals]  = useState([]);
  const [loading,     setLoading]    = useState(true);
  const [error,       setError]      = useState(null);
  const [filter,      setFilter]     = useState(isAdmin ? 'pending' : 'all');
  const [acting,      setActing]     = useState(null);
  const [rejectModal, setRejectModal] = useState(null);
  const [remark,      setRemark]     = useState('');
  const [detail,      setDetail]     = useState(null); // approval to show in detail modal

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const qs = filter === 'all' ? '?status=all' : `?status=${filter}`;
      const data = await api.get(`/api/approvals${qs}`, getToken);
      setApprovals(data.approvals || []);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }, [getToken, filter]);

  useEffect(() => { load(); }, [load]);

  const approve = async (id, e) => {
    e.stopPropagation();
    setActing(id);
    try {
      await api.post(`/api/approvals/${id}/approve`, {}, getToken);
      await load();
    } catch (err) { setError(err.message); }
    finally { setActing(null); }
  };

  const openReject = (id, e) => { e.stopPropagation(); setRejectModal(id); setRemark(''); };

  const confirmReject = async () => {
    if (!rejectModal) return;
    setActing(rejectModal);
    try {
      await api.post(`/api/approvals/${rejectModal}/reject`, { reason: remark || 'Rejected by admin' }, getToken);
      setRejectModal(null);
      await load();
    } catch (err) { setError(err.message); }
    finally { setActing(null); }
  };

  return (
    <div className="flex flex-col min-h-full bg-[#080b14]">

      {/* Header */}
      <div className="px-8 pt-10 pb-6 border-b border-white/[0.06]">
        <h1 className="text-2xl font-semibold text-white tracking-tight">Approvals</h1>
        <p className="mt-1 text-sm text-white/40">
          {isAdmin ? 'Review and action resource requests.' : 'History of your resource requests.'}
        </p>
      </div>

      <div className="px-8 py-6">
        {/* Filter */}
        <div className="flex items-center gap-1 mb-5">
          {STATUS_FILTERS.map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={['px-3 py-1 rounded-full text-xs font-medium capitalize transition-colors',
                filter === f ? 'bg-white/[0.10] text-white' : 'text-white/40 hover:text-white/65'].join(' ')}>
              {f}
            </button>
          ))}
          <button onClick={load} className="ml-auto text-xs text-white/30 hover:text-white/60 transition-colors">
            Refresh
          </button>
        </div>

        {error && (
          <div className="px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400 mb-5">{error}</div>
        )}
        {loading && <p className="text-white/30 text-sm">Loading...</p>}

        {!loading && !error && (
          <div className="bg-[#0d0f17] border border-white/[0.07] rounded-2xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  {['Request', ...(isAdmin ? ['Requested by'] : []),
                    'Status', 'Submitted', 'Updated',
                    ...(isAdmin ? ['Actions'] : ['Remark'])
                  ].map(h => (
                    <th key={h} className="px-5 py-3.5 text-left text-[11px] font-semibold text-white/30 uppercase tracking-widest">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {approvals.length === 0 ? (
                  <tr><td colSpan={isAdmin ? 6 : 5} className="px-5 py-10 text-center text-white/25 text-sm">
                    No {filter === 'all' ? '' : filter} approvals found.
                  </td></tr>
                ) : approvals.map(a => {
                  const name = resourceName(a);
                  const intent = intentLabel(a);
                  return (
                    <tr key={a.id}
                      onClick={() => setDetail(a)}
                      className="border-b border-white/[0.04] hover:bg-white/[0.03] transition-colors cursor-pointer">

                      {/* Request — show resource name + intent type */}
                      <td className="px-5 py-3">
                        <div>
                          {name && <p className="font-mono text-xs text-white/80 font-semibold">{name}</p>}
                          <p className={`text-xs capitalize ${name ? 'text-white/35 mt-0.5' : 'text-white/65'}`}>{intent}</p>
                        </div>
                      </td>

                      {/* Requested by — username, not UID */}
                      {isAdmin && (
                        <td className="px-5 py-3">
                          <div>
                            <p className="text-white/70 text-xs font-medium">{displayUser(a)}</p>
                            <p className="text-white/30 text-[11px] mt-0.5">{a.user_email || '—'}</p>
                          </div>
                        </td>
                      )}

                      <td className="px-5 py-3"><StatusBadge status={a.status} /></td>
                      <td className="px-5 py-3 text-white/30 text-xs">{fmtDate(a.timestamp)}</td>
                      <td className="px-5 py-3 text-white/30 text-xs">
                        {a.updated_at || a.resolved_at ? fmtDate(a.updated_at || a.resolved_at) : '—'}
                      </td>

                      {isAdmin ? (
                        <td className="px-5 py-3">
                          {a.status === 'pending' ? (
                            <div className="flex gap-2" onClick={e => e.stopPropagation()}>
                              <button onClick={e => approve(a.id, e)} disabled={!!acting}
                                className="text-xs px-3 py-1 rounded-lg bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 hover:bg-emerald-500/25 transition-colors disabled:opacity-40">
                                {acting === a.id ? '…' : 'Approve'}
                              </button>
                              <button onClick={e => openReject(a.id, e)} disabled={!!acting}
                                className="text-xs px-3 py-1 rounded-lg bg-red-500/15 text-red-400 border border-red-500/25 hover:bg-red-500/25 transition-colors disabled:opacity-40">
                                Reject
                              </button>
                            </div>
                          ) : (
                            <span className="text-white/20 text-xs">{a.resolved_by ? `by ${a.resolved_by.split('@')[0]}` : '—'}</span>
                          )}
                        </td>
                      ) : (
                        <td className="px-5 py-3 text-white/35 text-xs italic">
                          {a.admin_remark || a.reject_reason || '—'}
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Detail modal ─────────────────────────────────────── */}
      {detail && <DetailModal approval={detail} onClose={() => setDetail(null)} />}

      {/* ── Reject modal ─────────────────────────────────────── */}
      {rejectModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 px-4">
          <div className="bg-[#0d0f17] border border-white/[0.10] rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <h2 className="text-white font-semibold mb-1">Reject Request</h2>
            <p className="text-white/40 text-sm mb-4">Optionally provide a reason visible to the user.</p>
            <textarea value={remark} onChange={e => setRemark(e.target.value)}
              placeholder="Reason for rejection (optional)..." rows={3}
              className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-4 py-2.5 text-white/80 text-sm outline-none placeholder-white/25 resize-none mb-4" />
            <div className="flex gap-3 justify-end">
              <button onClick={() => setRejectModal(null)} className="px-4 py-2 text-sm text-white/50 hover:text-white/80 transition-colors">Cancel</button>
              <button onClick={confirmReject} disabled={!!acting}
                className="px-4 py-2 text-sm bg-red-500/20 text-red-400 border border-red-500/30 rounded-xl hover:bg-red-500/30 transition-colors disabled:opacity-40">
                {acting ? 'Rejecting…' : 'Confirm Reject'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Detail modal ─────────────────────────────────────────────
function DetailModal({ approval: a, onClose }) {
  const params  = a.parsed_request?.parameters  || {};
  const context = a.parsed_request?.user_context || {};
  const risk    = a.risk_result || {};
  const name    = resourceName(a);

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 px-4" onClick={onClose}>
      <div className="bg-[#0d0f17] border border-white/[0.10] rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className="flex items-start justify-between px-6 py-5 border-b border-white/[0.07]">
          <div>
            {name && <p className="font-mono text-sm text-white font-semibold">{name}</p>}
            <p className="text-white/45 text-xs capitalize mt-0.5">{intentLabel(a)}</p>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={a.status} />
            <button onClick={onClose} className="text-white/30 hover:text-white/70 transition-colors text-lg leading-none">×</button>
          </div>
        </div>

        <div className="px-6 py-5 space-y-5 max-h-[70vh] overflow-y-auto">

          {/* Parameters */}
          {Object.keys(params).length > 0 && (
            <Section title="Parameters">
              {Object.entries(params).map(([k, v]) => (
                <Row key={k} label={k.replace(/_/g, ' ')} value={String(v)} />
              ))}
            </Section>
          )}

          {/* Context */}
          {Object.values(context).some(Boolean) && (
            <Section title="Context">
              {Object.entries(context).filter(([, v]) => v).map(([k, v]) => (
                <Row key={k} label={k} value={String(v)} />
              ))}
            </Section>
          )}

          {/* Risk */}
          {risk.tier && (
            <Section title="Risk">
              <Row label="tier"   value={risk.tier} />
              <Row label="reason" value={risk.reason} />
              {risk.auto_applied && Object.keys(risk.auto_applied).length > 0 && (
                Object.entries(risk.auto_applied).map(([k, v]) => (
                  <Row key={k} label={`auto: ${k.replace(/_/g, ' ')}`} value={String(v)} />
                ))
              )}
            </Section>
          )}

          {/* Meta */}
          <Section title="Request info">
            <Row label="request id"   value={a.id} mono />
            <Row label="submitted"    value={fmtDate(a.timestamp)} />
            {(a.updated_at || a.resolved_at) && <Row label="resolved" value={fmtDate(a.updated_at || a.resolved_at)} />}
            {a.resolved_by  && <Row label="resolved by" value={a.resolved_by} />}
            {a.admin_remark && <Row label="admin remark" value={a.admin_remark} />}
          </Section>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div>
      <p className="text-[11px] font-semibold text-white/25 uppercase tracking-widest mb-2">{title}</p>
      <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3 space-y-2">
        {children}
      </div>
    </div>
  );
}

function Row({ label, value, mono = false }) {
  return (
    <div className="flex items-start gap-3">
      <span className="text-white/35 text-xs w-32 flex-shrink-0 capitalize pt-0.5">{label}</span>
      <span className={`text-xs flex-1 break-all ${mono ? 'font-mono text-white/50' : 'text-white/70'}`}>{value}</span>
    </div>
  );
}

function fmtDate(iso) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  catch { return iso; }
}
