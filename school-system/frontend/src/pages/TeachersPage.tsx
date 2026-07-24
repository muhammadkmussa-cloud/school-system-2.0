import { useEffect, useState } from 'react';
import api from '@/services/api';
import { useAuthStore } from '@/store/auth';
import toast from 'react-hot-toast';
import { Plus, Search, ToggleLeft, ToggleRight, Key, Printer, Download, UserPlus } from 'lucide-react';
import type { PaginatedResponse } from '@/types';

interface Teacher {
  id: string;
  employee_number: string;
  full_name: string;
  email: string;
  phone: string | null;
  is_active: boolean;
  user_id: string;
  created_at: string;
}

interface TeacherCredential {
  id: string;
  employee_number: string;
  full_name: string;
  email: string;
  temp_password: string;
  is_active: boolean;
}

export default function TeachersPage() {
  const user = useAuthStore((s) => s.user);
  const isSchoolAdmin = user?.role === 'school_admin' || user?.role === 'platform_admin';
  const isTeacher = user?.role === 'teacher';

  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  // Create modal
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ employee_number: '', full_name: '', email: '', phone: '' });

  // Bulk create
  const [showBulk, setShowBulk] = useState(false);
  const [bulkCount, setBulkCount] = useState(10);
  const [bulkResult, setBulkResult] = useState<TeacherCredential[]>([]);

  // Reset password
  const [resetResult, setResetResult] = useState<{ teacher_id: string; new_password: string } | null>(null);

  const fetchTeachers = async () => {
    try {
      const { data } = await api.get<PaginatedResponse<Teacher>>('/teachers', {
        params: { page, page_size: pageSize, search },
      });
      setTeachers(data.items);
      setTotal(data.total);
    } catch { /* silent */ }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchTeachers(); }, [page, search]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/teachers', form);
      toast.success('Teacher created');
      setShowCreate(false);
      setForm({ employee_number: '', full_name: '', email: '', phone: '' });
      fetchTeachers();
    } catch (err: any) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const handleBulkCreate = async () => {
    if (bulkCount < 1) return;
    try {
      const { data } = await api.post('/teachers/bulk', { count: bulkCount });
      setBulkResult(data.teachers);
      toast.success(`${data.created} teacher accounts provisioned`);
      fetchTeachers();
    } catch (err: any) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const handleToggleActive = async (id: string) => {
    try {
      const { data } = await api.post(`/teachers/${id}/toggle-active`);
      setTeachers(teachers.map(t => t.id === id ? data : t));
      toast.success('Status updated');
    } catch { toast.error('Failed'); }
  };

  const handleResetPassword = async (id: string) => {
    try {
      const { data } = await api.post(`/teachers/${id}/reset-password`);
      setResetResult({ teacher_id: id, new_password: data.new_password });
      toast.success('Password reset');
    } catch { toast.error('Failed'); }
  };

  const handlePrintCredentials = () => {
    if (bulkResult.length === 0) return;
    const rows = bulkResult.map(t => `
      <tr>
        <td style="border:1px solid #ccc;padding:6px 10px;font-family:monospace">${t.employee_number}</td>
        <td style="border:1px solid #ccc;padding:6px 10px">${t.full_name}</td>
        <td style="border:1px solid #ccc;padding:6px 10px;font-family:monospace">${t.email}</td>
        <td style="border:1px solid #ccc;padding:6px 10px;font-family:monospace">${t.temp_password}</td>
        <td style="border:1px solid #ccc;padding:6px 10px">${t.is_active ? 'Active' : 'Pending'}</td>
      </tr>
    `).join('');
    const w = window.open('', '_blank');
    if (!w) return;
    w.document.write(`<html><head><title>Staff Credentials</title>
<style>body{font-family:Arial,sans-serif;padding:40px}h1{font-size:20px}table{width:100%;border-collapse:collapse}th{background:#f5f5f5;border:1px solid #ccc;padding:8px 10px;text-align:left}td{border:1px solid #ccc;padding:6px 10px}</style></head><body>
<h1>School Management System — Staff Credentials</h1>
<p style="color:#666">Generated: ${new Date().toLocaleString()}</p>
<table><thead><tr><th>Employee #</th><th>Name</th><th>Username</th><th>Temp Password</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table></body></html>`);
    w.document.close();
    w.print();
  };

  if (isTeacher) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-500">Your teacher profile is managed by your school administrator.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-2xl font-bold text-gray-900">Teachers</h2>
        {isSchoolAdmin && (
          <div className="flex gap-2">
            <button onClick={() => { setShowBulk(!showBulk); setBulkResult([]); }} className="btn-secondary gap-2">
              <UserPlus className="h-4 w-4" /> Bulk Create
            </button>
            <button onClick={() => setShowCreate(!showCreate)} className="btn-primary gap-2">
              <Plus className="h-4 w-4" /> Add Teacher
            </button>
          </div>
        )}
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
        <input
          className="input-field pl-9"
          placeholder="Search teachers by name or email…"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
        />
      </div>

      {/* Create Individual Teacher Form */}
      {showCreate && (
        <div className="card">
          <h3 className="text-base font-semibold mb-4">New Teacher</h3>
          <form onSubmit={handleCreate} className="grid gap-4 sm:grid-cols-2">
            <div><label className="label">Employee Number *</label><input className="input-field" required value={form.employee_number} onChange={e => setForm({...form, employee_number: e.target.value})} /></div>
            <div><label className="label">Full Name *</label><input className="input-field" required value={form.full_name} onChange={e => setForm({...form, full_name: e.target.value})} /></div>
            <div><label className="label">Email *</label><input type="email" className="input-field" required value={form.email} onChange={e => setForm({...form, email: e.target.value})} /></div>
            <div><label className="label">Phone</label><input className="input-field" value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} /></div>
            <div className="sm:col-span-2 flex gap-3 justify-end">
              <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</button>
              <button type="submit" className="btn-primary">Create Teacher</button>
            </div>
          </form>
        </div>
      )}

      {/* Bulk Create */}
      {showBulk && (
        <div className="card">
          <h3 className="text-base font-semibold mb-4">Bulk Create Teacher Accounts</h3>
          {bulkResult.length === 0 ? (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
                Enter the number of teacher accounts to generate. The system will auto-create accounts with temporary credentials.
              </div>
              <div className="flex gap-3 items-end">
                <div>
                  <label className="label">Number of Teachers</label>
                  <input type="number" className="input-field w-32" min={1} max={200}
                    value={bulkCount} onChange={e => setBulkCount(parseInt(e.target.value) || 1)} />
                </div>
                <button onClick={handleBulkCreate} className="btn-primary gap-2">
                  <UserPlus className="h-4 w-4" /> Generate
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-800 flex items-center gap-2">
                {bulkResult.length} accounts created
              </div>
              <div className="overflow-x-auto border rounded-lg max-h-80 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr className="border-b">
                      <th className="text-left p-2.5 font-semibold text-gray-600">Employee #</th>
                      <th className="text-left p-2.5 font-semibold text-gray-600">Name</th>
                      <th className="text-left p-2.5 font-semibold text-gray-600">Email (Username)</th>
                      <th className="text-left p-2.5 font-semibold text-gray-600">Temp Password</th>
                      <th className="text-left p-2.5 font-semibold text-gray-600">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bulkResult.map(t => (
                      <tr key={t.id} className="border-b last:border-0 hover:bg-gray-50">
                        <td className="p-2.5 font-mono text-xs">{t.employee_number}</td>
                        <td className="p-2.5">{t.full_name}</td>
                        <td className="p-2.5 font-mono text-xs">{t.email}</td>
                        <td className="p-2.5 font-mono text-xs tracking-wider">{t.temp_password}</td>
                        <td className="p-2.5">
                          <span className="rounded-full bg-amber-100 text-amber-700 px-2 py-0.5 text-xs font-medium">Pending</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex gap-2">
                <button onClick={handlePrintCredentials} className="btn-secondary gap-2"><Printer className="h-4 w-4" /> Print</button>
                <button onClick={() => {
                  const csv = [['Employee #','Name','Email','Temp Password','Status'],
                    ...bulkResult.map(t => [t.employee_number, t.full_name, t.email, t.temp_password, t.is_active ? 'Active' : 'Pending']),
                  ].map(r => r.join(',')).join('\n');
                  const blob = new Blob([csv], { type: 'text/csv' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a'); a.href = url; a.download = 'staff_credentials.csv'; a.click();
                  URL.revokeObjectURL(url);
                }} className="btn-secondary gap-2"><Download className="h-4 w-4" /> CSV</button>
                <button onClick={() => { setBulkResult([]); setBulkCount(10); }} className="btn-secondary">Create More</button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Reset Password Dialog */}
      {resetResult && (
        <div className="card border-amber-200 bg-amber-50">
          <div className="flex items-start gap-3">
            <Key className="h-5 w-5 text-amber-600 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-amber-900">Password Reset Successful</h3>
              <p className="text-sm text-amber-800 mt-1">New temporary password:</p>
              <div className="flex items-center gap-2 mt-2">
                <code className="bg-white px-3 py-1.5 rounded border border-amber-300 font-mono text-sm tracking-wider">
                  {resetResult.new_password}
                </code>
                <button onClick={() => { navigator.clipboard.writeText(resetResult.new_password); toast.success('Copied!'); }}
                  className="text-amber-700 hover:text-amber-900">
                  Copy
                </button>
              </div>
              <p className="text-xs text-amber-700 mt-2">The teacher must use this password on next login.</p>
            </div>
            <button onClick={() => setResetResult(null)} className="text-amber-400 hover:text-amber-600">&times;</button>
          </div>
        </div>
      )}

      {/* Teachers Table */}
      <div className="overflow-x-auto border rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr className="border-b">
              <th className="text-left p-3 font-semibold text-gray-600">Employee #</th>
              <th className="text-left p-3 font-semibold text-gray-600">Name</th>
              <th className="text-left p-3 font-semibold text-gray-600">Email</th>
              <th className="text-left p-3 font-semibold text-gray-600">Phone</th>
              <th className="text-left p-3 font-semibold text-gray-600">Status</th>
              {isSchoolAdmin && <th className="text-left p-3 font-semibold text-gray-600">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="text-center py-8 text-gray-400">Loading…</td></tr>
            ) : teachers.length === 0 ? (
              <tr><td colSpan={6} className="text-center py-8 text-gray-400">No teachers found</td></tr>
            ) : teachers.map((teacher) => (
              <tr key={teacher.id} className="border-b last:border-0 hover:bg-gray-50">
                <td className="p-3 font-mono text-xs">{teacher.employee_number}</td>
                <td className="p-3 font-medium">{teacher.full_name}</td>
                <td className="p-3 text-gray-600">{teacher.email}</td>
                <td className="p-3 text-gray-500">{teacher.phone || '—'}</td>
                <td className="p-3">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    teacher.is_active ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                  }`}>
                    {teacher.is_active ? 'Active' : 'Pending'}
                  </span>
                </td>
                {isSchoolAdmin && (
                  <td className="p-3">
                    <div className="flex items-center gap-1.5">
                      <button onClick={() => handleToggleActive(teacher.id)} className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700" title="Toggle active">
                        {teacher.is_active ? <ToggleRight className="h-4 w-4 text-green-600" /> : <ToggleLeft className="h-4 w-4 text-gray-400" />}
                      </button>
                      <button onClick={() => handleResetPassword(teacher.id)} className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-amber-600" title="Reset password">
                        <Key className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > pageSize && (
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>{total} teacher{total !== 1 ? 's' : ''} total</span>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="btn-secondary text-xs">Previous</button>
            <button disabled={page * pageSize >= total} onClick={() => setPage(page + 1)} className="btn-secondary text-xs">Next</button>
          </div>
        </div>
      )}
    </div>
  );
}
