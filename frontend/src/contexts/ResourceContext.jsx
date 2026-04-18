import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from './AuthContext';
import { api } from '../api';

const CACHE_TTL = 30_000; // 30 seconds

const ResourceContext = createContext(null);

export function ResourceProvider({ children }) {
  const { getToken, profile } = useAuth();
  const [resources,  setResources]  = useState([]);
  const [loading,    setLoading]    = useState(false);
  const [lastFetch,  setLastFetch]  = useState(0);
  const inflightRef = useRef(null);

  const refresh = useCallback(async (force = false) => {
    const now = Date.now();
    if (!force && now - lastFetch < CACHE_TTL) return;
    // Deduplicate concurrent calls
    if (inflightRef.current) return inflightRef.current;

    setLoading(true);
    inflightRef.current = api.get('/api/resources', getToken)
      .then(data => {
        setResources(data.resources || []);
        setLastFetch(Date.now());
      })
      .catch(() => {})
      .finally(() => { setLoading(false); inflightRef.current = null; });

    return inflightRef.current;
  }, [getToken, lastFetch]);

  // Initial load when profile is available
  useEffect(() => {
    if (profile) refresh(true);
  }, [profile]); // eslint-disable-line react-hooks/exhaustive-deps

  // Listen for resource creation/deletion events
  useEffect(() => {
    let timer;
    const handler = () => { clearTimeout(timer); timer = setTimeout(() => refresh(true), 600); };
    window.addEventListener('coms:resource-created', handler);
    window.addEventListener('coms:resource-deleted', handler);
    return () => {
      window.removeEventListener('coms:resource-created', handler);
      window.removeEventListener('coms:resource-deleted', handler);
      clearTimeout(timer);
    };
  }, [refresh]);

  return (
    <ResourceContext.Provider value={{ resources, loading, refresh }}>
      {children}
    </ResourceContext.Provider>
  );
}

export function useResources() {
  const ctx = useContext(ResourceContext);
  if (!ctx) throw new Error('useResources must be used inside ResourceProvider');
  return ctx;
}
