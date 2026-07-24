import { useEffect, useState, useCallback } from 'react';
import api from '@/services/api';
import toast from 'react-hot-toast';
import { Shield, History, Filter } from 'lucide-react';

export default function AuditPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ entity_type: '', action: '' });

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { page, page_size: 50 };
      if (filters.entity_type) params.entity_type = filters.entity_type;
      if (filters.action) params.action = filters.action;
      const { data } = await api.get('/audit', { params });
      setLogs(data.logs);
      setTotal(data.total);
    } catch { toast.error('Failed to load audit trail'); }
    finally { setLoading(false); }
  }, [page, filters]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const entityTypes = ['student', 'mark', 'attendance', 'report', 'teacher', 'assessment', 'lesson'];
  const actions = ['create', 'update', 'delete', 'export', 'approve', 'reject', 'login', 'logout'];

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Shield className="h-6 w-6 text-brand-600" /> Audit Trail
        </h2>
      </div>

      {/* Filters */}
      <div className="card mb-4">
        <div className="flex flex-wrap gap-3 items-center">
          <Filter className="h-4 w-4 text-gray-400" />
          <select className="input-field w-auto text-xs" value={filters.entity_type}
            onChange={e => { setFilters({...filters, entity_type: e.target.value}); setPage(1); }}>
            <option value="">All entities</option>
            {entityTypes.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <select className="input-field w-auto text-xs" value={filters.action}
            onChange={e => { setFilters({...filters, action: e.target.value}); setPage(1); }}>
            <option value="">All actions</option>
            {actions.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
          <span className="text-xs text-gray-400 ml-auto">{total} records</span>
        </div>
      </div>

      {/* Logs */}
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-gray-200">
            <th className="table-header">Time</th>
            <th className="table-header">Actor</th>
            <th className="table-header">Action</th>
            <th className="table-header">Entity</th>
            <th className="table-header">Summary</th>
          </tr></thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="table-cell text-center py-8">Loading…</td></tr>
            ) : logs.length === 0 ? (
              <tr><td colSpan={5} className="table-cell text-center py-8 text-gray-400">
                <History className="mx-auto h-8 w-8 mb-2" /> No audit records found.
              </td></tr>
            ) : (
              logs.map(l => (
                <tr key={l.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="table-cell text-xs text-gray-400">{new Date(l.created_at).toLocaleString()}</td>
                  <td className="table-cell">
                    <span className="font-medium">{l.actor_name || 'System'}</span>
                    <span className="text-xs text-gray-400 ml-1 capitalize">({l.actor_role})</span>
                  </td>
                  <td className="table-cell">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                      l.action === 'create' ? 'bg-green-100 text-green-700' :
                      l.action === 'delete' ? 'bg-red-100 text-red-700' :
                      l.action === 'update' ? 'bg-blue-100 text-blue-700' :
                      l.action === 'approve' ? 'bg-purple-100 text-purple-700' :
                      l.action === 'reject' ? 'bg-orange-100 text-orange-700' :
                      'bg-gray-100 text-gray-600'
                    }`}>{l.action}</span>
                  </td>
                  <td className="table-cell text-xs">
                    <span className="capitalize">{l.entity_type}</span>
                    <span className="text-gray-400 ml-1 font-mono">#{l.entity_id?.slice(0,8)}</span>
                  </td>
                  <td className="table-cell text-xs text-gray-600 max-w-xs truncate">{l.summary || '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {total > 50 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t">
            <p className="text-xs text-gray-500">Page {page} of {Math.ceil(total/50)}</p>
            <div className="flex gap-2">
              <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page===1} className="btn-secondary text-xs">Previous</button>
              <button onClick={() => setPage(p => p+1)} disabled={page*50>=total} className="btn-secondary text-xs">Next</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
