import { useState, useEffect, useCallback } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useChat } from '../contexts/ChatContext';
import { api } from '../api';

const Icon = ({ d, size = 16, fill = 'none', stroke = 'currentColor' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke={stroke} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);
const HomeIcon    = () => <Icon d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z M9 22V12h6v10" />;
const ShieldIcon  = () => <Icon d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />;
const UserIcon    = () => <Icon d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2 M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" />;
const UsersIcon   = () => <Icon d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2 M23 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75" />;
const LogIcon     = () => <Icon d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M16 13H8 M16 17H8 M10 9H8" />;
const ZapIcon     = () => <Icon d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="currentColor" stroke="none" />;
const MenuIcon    = () => <Icon d="M3 12h18M3 6h18M3 18h18" />;
const ChevronLeft = () => <Icon d="M15 18l-6-6 6-6" size={14} />;
const ChevronDown = () => <Icon d="M6 9l6 6 6-6" size={13} />;
const ChevronRight = () => <Icon d="M9 18l6-6-6-6" size={13} />;
const BucketIcon  = () => <Icon d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" size={13} />;
const LayersIcon  = () => <Icon d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" size={13} />;
const ChatIcon    = () => <Icon d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" size={13} />;
const TrashIcon   = () => <Icon d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" size={12} />;
const PlusIcon    = () => <Icon d="M12 5v14M5 12h14" size={14} />;

const RESOURCE_TYPES = [
  { key: 's3',      label: 'S3 Buckets',       icon: <BucketIcon />,  type: 'S3 Bucket'            },
  { key: 'iam',     label: 'IAM Roles',         icon: <ShieldIcon />,  type: 'IAM Role'             },
  { key: 'ec2',     label: 'EC2 Instances',     icon: <LayersIcon />,  type: 'EC2 Instance'         },
  { key: 'lambda',  label: 'Lambda Functions',  icon: <ZapIcon />,     type: 'Lambda Function'      },
  { key: 'sns',     label: 'SNS Topics',        icon: <LayersIcon />,  type: 'SNS Topic'            },
  { key: 'logs',    label: 'Log Groups',        icon: <LayersIcon />,  type: 'CloudWatch Log Group' },
];

function NavItem({ icon, label, to, onClick }) {
  const { pathname } = useLocation();
  const active = to && (pathname === to || pathname.startsWith(to + '/'));
  const cls = [
    'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors cursor-pointer select-none',
    active ? 'bg-white/[0.08] text-white' : 'text-white/55 hover:bg-white/[0.05] hover:text-white/85',
  ].join(' ');
  const content = (
    <>
      <span className={active ? 'text-white/80' : 'text-white/40'}>{icon}</span>
      <span className="flex-1 font-medium">{label}</span>
    </>
  );
  return to ? <Link to={to} className={cls}>{content}</Link>
            : <div className={cls} onClick={onClick}>{content}</div>;
}

function SectionLabel({ children }) {
  return <p className="px-3 pt-4 pb-1 text-[11px] font-semibold text-white/30 uppercase tracking-widest">{children}</p>;
}

function truncate(str, max = 18) {
  if (!str) return '';
  return str.length > max ? str.slice(0, max) + '…' : str;
}

export default function Layout({ children }) {
  const { profile, getToken } = useAuth();
  const { sessions, activeId, selectSession, newSession, deleteSession } = useChat();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const [collapsed,      setCollapsed]      = useState(false);
  const [resourcesOpen,  setResourcesOpen]  = useState(true);
  const [historyOpen,    setHistoryOpen]    = useState(true);
  const [resourceCounts, setResourceCounts] = useState({});

  const isAdmin = profile?.role === 'admin';
  const initials = profile?.name?.charAt(0)?.toUpperCase() || profile?.email?.charAt(0)?.toUpperCase() || 'U';
  const username = profile?.name?.split(' ')[0] || profile?.email?.split('@')[0] || '';

  const loadCounts = useCallback(async () => {
    try {
      const data = await api.get('/api/resources', getToken);
      const resources = data.resources || [];
      const counts = {};
      RESOURCE_TYPES.forEach(rt => {
        counts[rt.key] = resources.filter(r => r.resource_type === rt.type).length;
      });
      setResourceCounts(counts);
    } catch { /* silent */ }
  }, [getToken]);

  useEffect(() => { loadCounts(); }, [loadCounts, pathname]);

  function handleNewChat() {
    newSession();
    navigate('/dashboard');
  }

  function handleSelectSession(id) {
    selectSession(id);
    navigate('/dashboard');
  }

  return (
    <div className="flex h-screen bg-[#080b14] overflow-hidden">

      {/* ── Sidebar ──────────────────────────────────────────── */}
      <aside className={[
        'flex-shrink-0 flex flex-col h-full bg-[#0d0f17] border-r border-white/[0.07] transition-all duration-200',
        collapsed ? 'w-[56px]' : 'w-[240px]',
      ].join(' ')}>

        {/* Logo row — clicking logo goes to /dashboard */}
        <div className="h-14 flex items-center justify-between px-4 flex-shrink-0">
          {!collapsed && (
            <Link to="/dashboard" className="flex items-center gap-2.5 group">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-900/40 group-hover:shadow-violet-700/50 transition-shadow">
                <ZapIcon />
              </div>
              <span className="text-white font-semibold text-sm tracking-tight group-hover:text-white/85 transition-colors">COMS</span>
            </Link>
          )}
          {collapsed && (
            <div className="flex items-center justify-between w-full">
              <Link to="/dashboard">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
                  <ZapIcon />
                </div>
              </Link>
              <button onClick={() => setCollapsed(false)}
                className="text-white/25 hover:text-white/60 transition-colors">
                <MenuIcon />
              </button>
            </div>
          )}
          {!collapsed && (
            <button onClick={() => setCollapsed(true)}
              className="text-white/25 hover:text-white/60 transition-colors ml-2">
              <ChevronLeft />
            </button>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 pb-3 space-y-0.5">
          {collapsed ? (
            <>
              <Link to="/dashboard" className="flex items-center justify-center py-2.5 text-white/40 hover:text-white/75 transition-colors"><HomeIcon /></Link>
              {isAdmin && <Link to="/audit" className="flex items-center justify-center py-2.5 text-white/40 hover:text-white/75 transition-colors"><LogIcon /></Link>}
              <Link to="/security"  className="flex items-center justify-center py-2.5 text-white/40 hover:text-white/75 transition-colors"><ShieldIcon /></Link>
              <Link to="/approvals" className="flex items-center justify-center py-2.5 text-white/40 hover:text-white/75 transition-colors"><UserIcon /></Link>
              {isAdmin && <Link to="/admin" className="flex items-center justify-center py-2.5 text-white/40 hover:text-white/75 transition-colors"><UsersIcon /></Link>}
            </>
          ) : (
            <>
              <NavItem icon={<HomeIcon />}   label="Home"      to="/dashboard" />
              {isAdmin && <NavItem icon={<LogIcon />} label="Audit Log" to="/audit" />}
              <NavItem icon={<ShieldIcon />} label="Security"  to="/security" />
              <NavItem icon={<UserIcon />}   label="Approvals" to="/approvals" />
              {isAdmin && <NavItem icon={<UsersIcon />} label="Admin Dashboard" to="/admin" />}

              {/* ── Chat History ─────────────────────────────── */}
              <SectionLabel>Chat History</SectionLabel>
              <div className="flex items-center gap-1 mb-0.5">
                <button
                  onClick={() => setHistoryOpen(o => !o)}
                  className="flex-1 flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-white/55 hover:bg-white/[0.05] hover:text-white/80 transition-colors"
                >
                  <span className="text-white/35"><ChatIcon /></span>
                  <span className="flex-1 font-medium text-left">Conversations</span>
                  <span className="text-white/25 transition-transform duration-150" style={{ transform: historyOpen ? 'rotate(180deg)' : '' }}>
                    <ChevronDown />
                  </span>
                </button>
                <button onClick={handleNewChat} title="New chat"
                  className="p-1.5 rounded-lg text-white/25 hover:text-white/65 hover:bg-white/[0.05] transition-colors flex-shrink-0">
                  <PlusIcon />
                </button>
              </div>

              {historyOpen && (
                <div className="ml-3 pl-3 border-l border-white/[0.06] space-y-0.5 mt-0.5 max-h-48 overflow-y-auto">
                  {sessions.length === 0 && (
                    <p className="text-[11px] text-white/25 px-2 py-2">No conversations yet.</p>
                  )}
                  {sessions.map(s => {
                    const active = s.id === activeId && pathname === '/dashboard';
                    return (
                      <div key={s.id}
                        className={[
                          'group flex items-center gap-1.5 px-2 py-1.5 rounded-lg transition-colors cursor-pointer',
                          active ? 'bg-white/[0.08] text-white/85' : 'text-white/45 hover:bg-white/[0.04] hover:text-white/70',
                        ].join(' ')}
                        onClick={() => handleSelectSession(s.id)}
                      >
                        <span className="flex-1 text-xs truncate">{s.title || 'New chat'}</span>
                        <button
                          onClick={e => { e.stopPropagation(); deleteSession(s.id); }}
                          className="opacity-0 group-hover:opacity-100 text-white/25 hover:text-red-400 transition-all flex-shrink-0 p-0.5"
                        >
                          <TrashIcon />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* ── All Resources dropdown ────────────────── */}
              <SectionLabel>Resources</SectionLabel>
              <button
                onClick={() => setResourcesOpen(o => !o)}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-white/55 hover:bg-white/[0.05] hover:text-white/80 transition-colors"
              >
                <span className="text-white/35"><LayersIcon /></span>
                <span className="flex-1 font-medium text-left">All Resources</span>
                <span className="text-white/25 transition-transform duration-150" style={{ transform: resourcesOpen ? 'rotate(180deg)' : '' }}>
                  <ChevronDown />
                </span>
              </button>

              {resourcesOpen && (
                <div className="ml-3 pl-3 border-l border-white/[0.06] space-y-0.5 mt-0.5">
                  {RESOURCE_TYPES.map(rt => {
                    const count = resourceCounts[rt.key] ?? 0;
                    const active = pathname === `/resources/${rt.key}`;
                    return (
                      <Link
                        key={rt.key}
                        to={`/resources/${rt.key}`}
                        className={[
                          'flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs transition-colors',
                          active ? 'bg-white/[0.08] text-white/90' : 'text-white/45 hover:bg-white/[0.04] hover:text-white/75',
                        ].join(' ')}
                      >
                        <span className={active ? 'text-white/75' : 'text-white/30'}>{rt.icon}</span>
                        <span className="flex-1">{rt.label}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${count > 0 ? 'bg-white/[0.08] text-white/50' : 'text-white/20'}`}>
                          {count}
                        </span>
                      </Link>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </nav>

        {/* Bottom — profile row */}
        {!collapsed ? (
          <div className="px-3 pb-4 border-t border-white/[0.06] pt-3">
            <div onClick={() => navigate('/profile')}
              className="flex items-center gap-2.5 px-1 py-1 cursor-pointer group rounded-lg hover:bg-white/[0.04] transition-colors">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-pink-500 to-violet-600 flex items-center justify-center text-white text-xs font-bold group-hover:ring-2 group-hover:ring-violet-500/50 transition-all flex-shrink-0">
                {initials}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-white/70 truncate font-medium">{truncate(username, 20)}</p>
                <p className="text-[10px] text-white/35 capitalize">{profile?.role}</p>
              </div>
              <ChevronRight />
            </div>
          </div>
        ) : (
          <div className="px-3 pb-4 border-t border-white/[0.06] pt-3 flex justify-center">
            <div onClick={() => navigate('/profile')}
              className="w-7 h-7 rounded-full bg-gradient-to-br from-pink-500 to-violet-600 flex items-center justify-center text-white text-xs font-bold cursor-pointer hover:ring-2 hover:ring-violet-500/50 transition-all">
              {initials}
            </div>
          </div>
        )}
      </aside>

      {/* ── Main ─────────────────────────────────────────────── */}
      <main className="flex-1 min-w-0 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
