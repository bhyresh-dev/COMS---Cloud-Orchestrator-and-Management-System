import { useEffect, useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useResources } from '../contexts/ResourceContext';

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

// Resource dependency definitions — what each type depends on
const DEPENDENCIES = {
  'Lambda Function': [
    { type: 'IAM Role', label: 'Execution Role', reason: 'Lambda requires an IAM role to assume permissions at runtime', key: 'ec2' },
    { type: 'CloudWatch Log Group', label: 'Log Group', reason: 'Lambda automatically writes execution logs to CloudWatch', key: 'logs' },
  ],
  'EC2 Instance': [
    { type: 'IAM Role', label: 'Instance Profile', reason: 'EC2 instances use IAM roles to access AWS services securely', key: 'iam' },
  ],
  'SNS Topic': [
    { type: 'CloudWatch Log Group', label: 'Delivery Logs', reason: 'SNS can log message delivery status to CloudWatch', key: 'logs' },
  ],
  'S3 Bucket': [],
  'IAM Role': [],
  'CloudWatch Log Group': [],
};

const TYPE_KEY = {
  'S3 Bucket': 's3', 'IAM Role': 'iam', 'EC2 Instance': 'ec2',
  'Lambda Function': 'lambda', 'SNS Topic': 'sns', 'CloudWatch Log Group': 'logs',
};

const TYPE_COLOR = {
  'S3 Bucket':            'from-violet-500 to-indigo-600',
  'IAM Role':             'from-pink-500 to-rose-600',
  'EC2 Instance':         'from-cyan-500 to-blue-600',
  'Lambda Function':      'from-amber-500 to-orange-600',
  'SNS Topic':            'from-emerald-500 to-teal-600',
  'CloudWatch Log Group': 'from-slate-500 to-gray-600',
};

export default function ResourcesPage() {
  const { type } = useParams();
  const { resources: allResources, loading, refresh } = useResources();
  const meta = RESOURCE_META[type] || { label: 'Resources', type: type, desc: '' };

  const [selected, setSelected] = useState(null);
  const [error] = useState(null);

  const resources = useMemo(
    () => allResources.filter(r => r.resource_type === meta.type),
    [allResources, meta.type],
  );

  // Reset selection when type changes; request a fresh load in case cache is stale
  useEffect(() => { setSelected(null); refresh(); }, [type]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex min-h-full bg-[#080b14]">

      {/* ── List panel ───────────────────────────────────────── */}
      <div className={`flex flex-col ${selected ? 'w-[320px] flex-shrink-0 border-r border-white/[0.06]' : 'flex-1'}`}>
        <div className="px-8 pt-10 pb-6 border-b border-white/[0.06]">
          <h1 className="text-2xl font-semibold text-white tracking-tight">{meta.label}</h1>
          <p className="mt-1 text-sm text-white/45">{meta.desc}</p>
        </div>

        <div className="px-6 py-5 flex-1">
          {error && (
            <div className="px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400 mb-5">{error}</div>
          )}
          {loading && <p className="text-white/35 text-sm">Loading...</p>}

          {!loading && !error && resources.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="w-14 h-14 rounded-2xl bg-white/[0.04] border border-white/[0.07] flex items-center justify-center text-white/20 mb-4 text-2xl">—</div>
              <p className="text-white/45 text-sm font-medium">No {meta.label.toLowerCase()} found</p>
              <p className="text-white/25 text-xs mt-1">Use the chat assistant on the dashboard to create one.</p>
            </div>
          )}

          {!loading && !error && resources.length > 0 && (
            <div className={selected ? 'space-y-2' : 'grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3'}>
              {resources.map((r, i) => (
                selected ? (
                  <button key={r.id} onClick={() => setSelected(r)}
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
                      <p className="text-white/35 text-[11px] mt-0.5">{r.region || '—'}</p>
                    </div>
                  </button>
                ) : (
                  <button key={r.id} onClick={() => setSelected(r)}
                    className="group bg-white/[0.04] border border-white/[0.07] rounded-xl p-4 hover:bg-white/[0.07] hover:border-white/[0.12] transition-all text-left"
                  >
                    <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${BUCKET_GRADIENTS[i % BUCKET_GRADIENTS.length]} mb-3 shadow-lg`} />
                    <p className="text-white/85 text-sm font-medium truncate font-mono">{r.resource_name}</p>
                    <p className="text-white/40 text-xs mt-1">{r.region || '—'}</p>
                    <p className="text-white/25 text-[11px] mt-0.5">{fmtDate(r.timestamp)}</p>
                    <p className={`text-[11px] mt-1 capitalize ${r.status === 'pending' ? 'text-amber-400/70' : 'text-white/30'}`}>{r.status}</p>
                  </button>
                )
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Detail panel ─────────────────────────────────────── */}
      {selected && (
        <div className="flex-1 overflow-y-auto px-8 py-8 space-y-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-mono text-lg font-semibold text-white">{selected.resource_name}</p>
              <p className="text-white/40 text-sm mt-0.5">{meta.label.replace(/s$/, '')}</p>
            </div>
            <button onClick={() => setSelected(null)}
              className="text-white/25 hover:text-white/60 transition-colors text-xl leading-none mt-1">×</button>
          </div>

          {/* Status badge */}
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2.5 py-1 rounded-full border capitalize ${
              selected.status === 'active'  ? 'bg-emerald-500/12 text-emerald-400 border-emerald-500/20' :
              selected.status === 'pending' ? 'bg-amber-500/12 text-amber-400 border-amber-500/20' :
              'bg-white/[0.06] text-white/40 border-white/[0.08]'
            }`}>
              {selected.status}
            </span>
          </div>

          {/* Resource Info */}
          <DetailCard title="Resource Info">
            <Row label="Name"    value={selected.resource_name} mono />
            <Row label="Type"    value={selected.resource_type} />
            <Row label="Region"  value={selected.region || '—'} />
            <Row label="Status"  value={selected.status} />
            <Row label="Created" value={fmtDateTime(selected.timestamp)} />
          </DetailCard>

          {/* Configuration */}
          {selected.details && Object.keys(selected.details).length > 0 && (
            <DetailCard title="Configuration">
              {Object.entries(selected.details).map(([k, v]) => (
                <Row key={k} label={k.replace(/_/g, ' ')} value={String(v)} />
              ))}
            </DetailCard>
          )}

          {/* Dependency Graph */}
          <DependencyGraph resource={selected} allResources={allResources} />

          {/* Ownership */}
          <DetailCard title="Ownership">
            <Row label="Created by"  value={selected.user_email || selected.user_id || '—'} />
            <Row label="Role"        value={selected.created_by_role || '—'} />
            <Row label="Resource ID" value={selected.id} mono />
          </DetailCard>
        </div>
      )}
    </div>
  );
}

function DependencyGraph({ resource, allResources }) {
  const deps = DEPENDENCIES[resource.resource_type] || [];
  if (deps.length === 0) return null;

  return (
    <div>
      <p className="text-[11px] font-semibold text-white/25 uppercase tracking-widest mb-2">Dependencies</p>
      <div className="bg-[#0d0f17] border border-white/[0.07] rounded-xl p-4 space-y-3">

        {/* Current resource node */}
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${TYPE_COLOR[resource.resource_type] || 'from-white/10 to-white/5'} flex-shrink-0 shadow-sm`} />
          <div>
            <p className="text-xs font-semibold text-white/80 font-mono">{resource.resource_name}</p>
            <p className="text-[11px] text-white/35">{resource.resource_type}</p>
          </div>
          <div className="ml-auto">
            <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
              resource.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
              : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
            }`}>{resource.status}</span>
          </div>
        </div>

        {/* Dependency lines */}
        {deps.map((dep, i) => {
          const matching = allResources.filter(r => r.resource_type === dep.type);
          const hasDep = matching.length > 0;
          const key = TYPE_KEY[dep.type];

          return (
            <div key={i}>
              {/* Connector line */}
              <div className="flex items-center gap-2 ml-4 mb-2">
                <div className="w-px h-4 bg-white/[0.08]" />
                <div className="w-4 h-px bg-white/[0.08]" />
                <span className="text-[10px] text-white/20 font-mono">requires</span>
              </div>

              {/* Dependency node */}
              <div className={`ml-8 flex items-center gap-3 px-3 py-2.5 rounded-xl border transition-colors ${
                hasDep
                  ? 'border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.05]'
                  : 'border-dashed border-white/[0.06] bg-transparent'
              }`}>
                <div className={`w-7 h-7 rounded-lg bg-gradient-to-br ${TYPE_COLOR[dep.type] || 'from-white/10 to-white/5'} flex-shrink-0 ${!hasDep ? 'opacity-30' : ''}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <p className={`text-xs font-medium truncate ${hasDep ? 'text-white/70' : 'text-white/30'}`}>
                      {dep.label}
                    </p>
                    <span className="text-[10px] text-white/20">·</span>
                    <span className="text-[10px] text-white/25">{dep.type}</span>
                  </div>
                  <p className="text-[11px] text-white/25 mt-0.5 leading-snug">{dep.reason}</p>
                  {hasDep && (
                    <p className="text-[11px] text-emerald-400/70 mt-0.5">
                      {matching.length} found: {matching.slice(0, 2).map(r => r.resource_name).join(', ')}{matching.length > 2 ? ` +${matching.length - 2} more` : ''}
                    </p>
                  )}
                </div>
                <div className="flex-shrink-0">
                  {hasDep ? (
                    <Link to={`/resources/${key}`}
                      className="text-[10px] px-2 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.08] text-white/40 hover:text-white/70 transition-colors border border-white/[0.06]">
                      View
                    </Link>
                  ) : (
                    <span className="text-[10px] text-white/20 border border-dashed border-white/[0.08] px-2 py-1 rounded-lg">
                      Not found
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
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
