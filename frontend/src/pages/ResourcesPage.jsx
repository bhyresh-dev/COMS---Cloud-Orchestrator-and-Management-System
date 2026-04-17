import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';

const RESOURCE_META = {
  s3:     { label: 'S3 Buckets',       type: 'S3 Bucket',             desc: 'Your S3 storage buckets.' },
  iam:    { label: 'IAM Roles',        type: 'IAM Role',              desc: 'Identity and access management roles.' },
  ec2:    { label: 'EC2 Instances',    type: 'EC2 Instance',          desc: 'Virtual machine instances.' },
  lambda: { label: 'Lambda Functions', type: 'Lambda Function',       desc: 'Serverless function deployments.' },
  sns:    { label: 'SNS Topics',       type: 'SNS Topic',             desc: 'Simple notification service topics.' },
  logs:   { label: 'Log Groups',       type: 'CloudWatch Log Group',  desc: 'CloudWatch log groups.' },
};

const BUCKET_GRADIENTS = [
  'from-violet-500 to-indigo-600', 'from-pink-500 to-rose-600',
  'from-cyan-500 to-blue-600',     'from-amber-500 to-orange-600',
  'from-emerald-500 to-teal-600',
];

// Which fields to surface per resource type
const DETAIL_FIELDS = {
  s3:     ['region', 'access_level', 'purpose'],
  iam:    ['trust_policy_service', 'description'],
  ec2:    ['instance_type', 'region', 'purpose'],
  lambda: ['runtime', 'handler', 'region', 'description'],
  sns:    ['region'],
  logs:   ['region'],
};

export default function ResourcesPage() {
  const { type } = useParams();
  const { getToken } = useAuth();
  const meta = RESOURCE_META[type] || { label: 'Resources', type: type, desc: '' };

  const [resources, setResources] = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState(null);
  const [selected,  setSelected]  = useState(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await api.get('/api/resources', getToken);
      const all  = data.resources || [];
      setResources(all.filter(r => r.resource_type === meta.type));
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }, [getToken, meta.type]);

  useEffect(() => { load(); setSelected(null); }, [load]);

  return (
    <div className="flex min-h-full bg-[#080b14]">

      {/* ── List panel ───────────────────────────────────────── */}
      <div className={`flex flex-col ${selected ? 'w-[340px] flex-shrink-0 border-r border-white/[0.06]' : 'flex-1'}`}>
        <div className="px-8 pt-10 pb-6 border-b border-white/[0.06]">
          <h1 className="text-2xl font-semibold text-white tracking-tight">{meta.label}</h1>
          <p className="mt-1 text-sm text-white/40">{meta.desc}</p>
        </div>

        <div className="px-6 py-5 flex-1">
          {error && (
            <div className="px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400 mb-5">{error}</div>
          )}
          {loading && <p className="text-white/30 text-sm">Loading...</p>}

          {!loading && !error && resources.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="w-14 h-14 rounded-2xl bg-white/[0.04] border border-white/[0.07] flex items-center justify-center text-white/20 mb-4 text-2xl">
                —
              </div>
              <p className="text-white/40 text-sm font-medium">No {meta.label.toLowerCase()} found</p>
              <p className="text-white/20 text-xs mt-1">Use the chat assistant on the dashboard to create one.</p>
            </div>
          )}

          {!loading && !error && resources.length > 0 && (
            <div className={selected
              ? 'space-y-2'
              : 'grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3'
            }>
              {resources.map((r, i) => (
                selected ? (
                  // Compact list when detail panel is open
                  <button
                    key={r.id}
                    onClick={() => setSelected(r)}
                    className={[
                      'w-full flex items-center gap-3 px-3 py-3 rounded-xl border text-left transition-all',
                      selected?.id === r.id
                        ? 'bg-white/[0.08] border-white/[0.12]'
                        : 'bg-white/[0.03] border-white/[0.06] hover:bg-white/[0.06]',
                    ].join(' ')}
                  >
                    <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${BUCKET_GRADIENTS[i % BUCKET_GRADIENTS.length]} flex-shrink-0`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-white/80 text-xs font-mono font-medium truncate">{r.resource_name}</p>
                      <p className="text-white/30 text-[11px] mt-0.5">{r.region || '—'}</p>
                    </div>
                  </button>
                ) : (
                  // Card grid when no selection
                  <button
                    key={r.id}
                    onClick={() => setSelected(r)}
                    className="group bg-white/[0.04] border border-white/[0.07] rounded-xl p-4 hover:bg-white/[0.07] hover:border-white/[0.12] transition-all text-left"
                  >
                    <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${BUCKET_GRADIENTS[i % BUCKET_GRADIENTS.length]} mb-3 shadow-lg`} />
                    <p className="text-white/85 text-sm font-medium truncate font-mono">{r.resource_name}</p>
                    <p className="text-white/35 text-xs mt-1">{r.region || '—'}</p>
                    <p className="text-white/20 text-[11px] mt-0.5">{fmtDate(r.timestamp)}</p>
                    <p className={`text-[11px] mt-1 capitalize ${r.status === 'pending' ? 'text-amber-400/60' : 'text-white/30'}`}>{r.status}</p>
                  </button>
                )
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Detail panel ─────────────────────────────────────── */}
      {selected && (
        <div className="flex-1 px-8 py-8">
          <div className="flex items-start justify-between mb-6">
            <div>
              <p className="font-mono text-lg font-semibold text-white">{selected.resource_name}</p>
              <p className="text-white/40 text-sm mt-0.5">{meta.label.replace(/s$/, '')}</p>
            </div>
            <button onClick={() => setSelected(null)}
              className="text-white/25 hover:text-white/60 transition-colors text-xl leading-none mt-1">×</button>
          </div>

          {/* Status badge */}
          <div className="flex items-center gap-2 mb-6">
            <span className={`text-xs px-2.5 py-1 rounded-full border capitalize ${
              selected.status === 'active'  ? 'bg-emerald-500/12 text-emerald-400 border-emerald-500/20' :
              selected.status === 'pending' ? 'bg-amber-500/12 text-amber-400 border-amber-500/20' :
              'bg-white/[0.06] text-white/40 border-white/[0.08]'
            }`}>
              {selected.status}
            </span>
          </div>

          {/* Details */}
          <div className="space-y-4">
            <DetailCard title="Resource Info">
              <Row label="Name"    value={selected.resource_name} mono />
              <Row label="Type"    value={selected.resource_type} />
              <Row label="Region"  value={selected.region || '—'} />
              <Row label="Status"  value={selected.status} />
              <Row label="Created" value={fmtDateTime(selected.timestamp)} />
            </DetailCard>

            {/* Type-specific fields from details object */}
            {selected.details && Object.keys(selected.details).length > 0 && (
              <DetailCard title="Configuration">
                {Object.entries(selected.details).map(([k, v]) => (
                  <Row key={k} label={k.replace(/_/g, ' ')} value={String(v)} />
                ))}
              </DetailCard>
            )}

            <DetailCard title="Ownership">
              <Row label="Created by" value={selected.user_email || selected.user_id || '—'} />
              <Row label="Role"       value={selected.created_by_role || '—'} />
              <Row label="Resource ID" value={selected.id} mono />
            </DetailCard>
          </div>
        </div>
      )}
    </div>
  );
}

function DetailCard({ title, children }) {
  return (
    <div>
      <p className="text-[11px] font-semibold text-white/25 uppercase tracking-widest mb-2">{title}</p>
      <div className="bg-[#0d0f17] border border-white/[0.07] rounded-xl divide-y divide-white/[0.04]">
        {children}
      </div>
    </div>
  );
}

function Row({ label, value, mono = false }) {
  return (
    <div className="flex items-start gap-4 px-4 py-3">
      <span className="text-white/30 text-xs w-28 flex-shrink-0 capitalize pt-0.5">{label}</span>
      <span className={`text-xs flex-1 break-all ${mono ? 'font-mono text-white/50' : 'text-white/70'}`}>{value}</span>
    </div>
  );
}

function fmtDate(iso) {
  if (!iso) return '';
  try { return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }); }
  catch { return iso; }
}

function fmtDateTime(iso) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  catch { return iso; }
}
