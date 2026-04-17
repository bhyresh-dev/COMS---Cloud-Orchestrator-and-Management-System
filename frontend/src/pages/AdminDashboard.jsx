import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';

const BUCKET_GRADIENTS = [
  'from-violet-500 to-indigo-600', 'from-pink-500 to-rose-600',
  'from-cyan-500 to-blue-600',     'from-amber-500 to-orange-600',
  'from-emerald-500 to-teal-600',
];

export default function AdminDashboard() {
  const { getToken } = useAuth();
  const [buckets, setBuckets] = useState([]);
  const [users,   setUsers]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [activeTab, setTab]   = useState('Buckets');

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [bd, ud] = await Promise.all([
        api.get('/api/admin/buckets', getToken),
        api.get('/api/admin/users',   getToken),
      ]);
      setBuckets(bd.buckets || []);
      setUsers(ud.users     || []);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }, [getToken]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="flex flex-col min-h-full bg-[#080b14]">

      {/* Header */}
      <div className="px-8 pt-10 pb-6 border-b border-white/[0.06]">
        <h1 className="text-2xl font-semibold text-white tracking-tight">Admin Dashboard</h1>
        <p className="mt-1 text-sm text-white/40">Platform-wide resource and user management.</p>
      </div>

      {/* Stats strip */}
      {!loading && !error && (
        <div className="flex gap-4 px-8 py-5 border-b border-white/[0.06]">
          <StatCard label="Total Buckets" value={buckets.length} gradient="from-violet-500 to-indigo-600" />
          <StatCard label="Total Users"   value={users.length}   gradient="from-pink-500 to-rose-600"    />
          <StatCard label="Admins"        value={users.filter(u => u.role === 'admin').length} gradient="from-amber-500 to-orange-500" />
        </div>
      )}

      {/* Tabs */}
      <div className="px-8 pt-5">
        <div className="flex items-center gap-1 mb-6">
          {['Buckets', 'Users'].map(tab => (
            <button
              key={tab}
              onClick={() => setTab(tab)}
              className={[
                'px-4 py-1.5 rounded-full text-sm font-medium transition-colors',
                activeTab === tab ? 'bg-white/[0.10] text-white' : 'text-white/40 hover:text-white/65',
              ].join(' ')}
            >
              {tab}
            </button>
          ))}
          <button
            onClick={load}
            className="ml-auto text-xs text-white/30 hover:text-white/60 transition-colors"
          >
            Refresh
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400 mb-6">
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && <p className="text-white/30 text-sm">Loading...</p>}

        {/* Buckets tab */}
        {!loading && !error && activeTab === 'Buckets' && (
          <div className="bg-[#0d0f17] border border-white/[0.07] rounded-2xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  {['Bucket', 'Region', 'Creator', 'Created', 'Status'].map(h => (
                    <th key={h} className="px-5 py-3.5 text-left text-[11px] font-semibold text-white/30 uppercase tracking-widest">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {buckets.length === 0 ? (
                  <tr><td colSpan={5} className="px-5 py-10 text-center text-white/25 text-sm">No active buckets.</td></tr>
                ) : buckets.map((b, i) => (
                  <tr key={b.id} className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className={`w-7 h-7 rounded-lg bg-gradient-to-br ${BUCKET_GRADIENTS[i % BUCKET_GRADIENTS.length]} flex-shrink-0`} />
                        <span className="font-mono text-xs text-white/75">{b.resource_name}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-white/50 text-xs">{b.region}</td>
                    <td className="px-5 py-3.5 text-white/45 text-xs">{b.user_email || '—'}</td>
                    <td className="px-5 py-3.5 text-white/35 text-xs">{fmtDate(b.timestamp)}</td>
                    <td className="px-5 py-3.5">
                      <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/12 text-emerald-400 border border-emerald-500/20">
                        {b.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Users tab */}
        {!loading && !error && activeTab === 'Users' && (
          <div className="bg-[#0d0f17] border border-white/[0.07] rounded-2xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  {['User', 'Role', 'Resources', 'Joined'].map(h => (
                    <th key={h} className="px-5 py-3.5 text-left text-[11px] font-semibold text-white/30 uppercase tracking-widest">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr><td colSpan={4} className="px-5 py-10 text-center text-white/25 text-sm">No users found.</td></tr>
                ) : users.map(u => (
                  <tr key={u.id} className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-pink-500 to-violet-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                          {u.email?.charAt(0).toUpperCase()}
                        </div>
                        <span className="text-white/75 text-sm">{u.email}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className={[
                        'text-xs px-2 py-0.5 rounded-full border',
                        u.role === 'admin'
                          ? 'bg-indigo-500/15 text-indigo-400 border-indigo-500/25'
                          : 'bg-white/[0.06] text-white/45 border-white/[0.08]',
                      ].join(' ')}>
                        {u.role}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-white/50 text-sm">{u.resource_count ?? 0}</td>
                    <td className="px-5 py-3.5 text-white/30 text-xs">{fmtDate(u.createdAt)}</td>
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

function StatCard({ label, value, gradient }) {
  return (
    <div className="flex items-center gap-4 bg-[#0d0f17] border border-white/[0.07] rounded-xl px-5 py-4 min-w-[160px]">
      <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${gradient} flex-shrink-0`} />
      <div>
        <p className="text-2xl font-bold text-white leading-none">{value}</p>
        <p className="text-xs text-white/35 mt-1">{label}</p>
      </div>
    </div>
  );
}

function fmtDate(iso) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }); }
  catch { return iso; }
}
