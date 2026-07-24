import { useEffect, useState, useRef } from 'react';
import api from '@/services/api';
import { useAuthStore } from '@/store/auth';
import toast from 'react-hot-toast';
import {
  Users, Search, ToggleLeft, ToggleRight, Key, Printer, Download, Upload,
  UserPlus, Eye, Pencil, CheckSquare, Square, Mail, FileSpreadsheet,
  RefreshCw, AlertTriangle, X, ChevronLeft, ChevronRight, Plus,
  Lock, Unlock, ShieldAlert,
} from 'lucide-react';
import clsx from 'clsx';
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
  user_status?: 'pending_first_login' | 'active' | 'locked' | 'disabled';
  must_change_password?: boolean;
}

interface BulkImportPreview {
  full_name: string;
  email: string;
  phone?: string;
  employee_number?: string;
  subjects?: string[];
  assigned_classes?: string[];
  assigned_streams?: string[];
}

export default function StaffManagement() {
  const user = useAuthStore((s) => s.user);
  const isSchoolAdmin = user?.role === 'school_admin' || user?.role === 'platform_admin';
  const isTeacherView = user?.role === 'teacher';
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Table state
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  // Selection
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectAll, setSelectAll] = useState(false);

  // Dashboard stats
  const [stats, setStats] = useState({ total: 0, active: 0, pending: 0, disabled: 0 });

  // Modals
  const [showCreate, setShowCreate] = useState(false);
  const [showBulkImport, setShowBulkImport] = useState(false);
  const [showCredentials, setShowCredentials] = useState(false);
  const [credentials, setCredentials] = useState<any[]>([]);
  const [resetResult, setResetResult] = useState<{ teacher_id: string; new_password: string } | null>(null);

  // Bulk import state
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importPreview, setImportPreview] = useState<BulkImportPreview[]>([]);
  const [importErrors, setImportErrors] = useState<any[]>([]);
  const [importValid, setImportValid] = useState(false);
  const [importing, setImporting] = useState(false);

  // Create form
  const [form, setForm] = useState({ employee_number: '', full_name: '', email: '', phone: '' });

  const fetchTeachers = async () => {
    try {
      const { data } = await api.get<PaginatedResponse<Teacher>>('/teachers', {
        params: { page, page_size: pageSize, search },
      });
      setTeachers(data.items);
      setTotal(data.total);
      const active = data.items.filter((t: Teacher) => t.is_active).length;
      setStats(prev => ({ ...prev, total: data.total, active, pending: data.total - active }));
    } catch { /* silent */ }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchTeachers(); }, [page, search]);

  const handleSelectAll = () => {
    if (selectAll) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(teachers.map(t => t.id)));
    }
    setSelectAll(!selectAll);
  };

  const handleSelectOne = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelectedIds(next);
    setSelectAll(next.size === teachers.length);
  };

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

  const handleToggleActive = async (id: string) => {
    try {
      const { data } = await api.post(`/teachers/${id}/toggle-active`);
      setTeachers(teachers.map(t => t.id === id ? data : t));
      toast.success('Status updated');
      fetchTeachers();
    } catch { toast.error('Failed'); }
  };

  const handleResetPassword = async (id: string) => {
    try {
      const { data } = await api.post(`/teachers/${id}/reset-password`);
      setResetResult({ teacher_id: id, new_password: data.new_password });
      toast.success('Password reset');
    } catch { toast.error('Failed'); }
  };

  const handleBatchReset = async () => {
    if (selectedIds.size === 0) return toast.error('Select teachers first');
    let count = 0;
    for (const id of selectedIds) {
      try {
        await api.post(`/teachers/${id}/reset-password`);
        count++;
      } catch { /* skip */ }
    }
    toast.success(`${count} passwords reset`);
  };

  const handleLockAccount = async (id: string) => {
    try {
      await api.post(`/teachers/${id}/lock`);
      toast.success('Account locked');
      fetchTeachers();
    } catch { toast.error('Failed to lock account'); }
  };

  const handleUnlockAccount = async (id: string) => {
    try {
      await api.post(`/teachers/${id}/unlock`);
      toast.success('Account unlocked');
      fetchTeachers();
    } catch { toast.error('Failed to unlock account'); }
  };

  const handleForceResetPassword = async (id: string) => {
    try {
      const { data } = await api.post(`/teachers/${id}/force-reset`);
      setResetResult({ teacher_id: id, new_password: data.new_password });
      toast.success('Password force-reset');
      fetchTeachers();
    } catch { toast.error('Failed to force reset'); }
  };

  const handleBatchToggle = async (activate: boolean) => {
    if (selectedIds.size === 0) return toast.error('Select teachers first');
    let count = 0;
    for (const id of selectedIds) {
      try {
        const teacher = teachers.find(t => t.id === id);
        if (teacher && teacher.is_active !== activate) {
          await api.post(`/teachers/${id}/toggle-active`);
          count++;
        }
      } catch { /* skip */ }
    }
    toast.success(`${count} teacher(s) ${activate ? 'activated' : 'disabled'}`);
    fetchTeachers();
  };

  const handlePrintCredentials = () => {
    if (credentials.length === 0) return toast.error('No credentials to print');
    const rows = credentials.map((t: any) => `
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
    w.document.write(`<html><head><title>Staff Credentials</title><style>
body{font-family:Arial,sans-serif;padding:40px;max-width:900px;margin:auto}
h1{font-size:20px;margin-bottom:4px}
p{color:#666;font-size:13px;margin-bottom:20px}
table{width:100%;border-collapse:collapse}
th{background:#f5f5f5;border:1px solid #ccc;padding:8px 10px;text-align:left;font-size:11px;text-transform:uppercase;color:#333}
td{border:1px solid #ccc;padding:6px 10px;font-size:12px}
.warn{background:#fff3cd;padding:10px 14px;border-radius:4px;margin-bottom:20px;font-size:12px;border:1px solid #ffc107}
.footer{margin-top:30px;color:#999;font-size:10px;text-align:center}
</style></head><body>
<h1>School Management System — Staff Credentials</h1>
<p>Generated: ${new Date().toLocaleString()} | School Admin: ${user?.full_name || 'N/A'}</p>
<div class="warn"><strong>⚠ Important:</strong> These are temporary passwords. Teachers must change their password on first login. Keep this document secure.</div>
<table><thead><tr><th>Employee #</th><th>Name</th><th>Username</th><th>Temp Password</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table>
<p class="footer">This document contains sensitive credentials. Distribute only to authorized staff.</p>
</body></html>`);
    w.document.close();
    w.print();
  };

  // ── File Import ──────────────────────────────────────────────────

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportFile(file);

    const reader = new FileReader();
    reader.onload = async (ev) => {
      const base64 = (ev.target?.result as string)?.split(',')[1];
      if (!base64) return toast.error('Could not read file');
      try {
        const { data } = await api.post('/onboarding/setup/step-3/validate', {
          file_content: base64,
          filename: file.name,
        });
        setImportErrors(data.errors || []);
        setImportPreview(data.preview || []);
        setImportValid(data.valid);
      } catch (err: any) {
        toast.error(err.response?.data?.detail || 'Validation failed');
      }
    };
    reader.readAsDataURL(file);
  };

  const handleConfirmImport = async () => {
    if (!importFile) return;
    setImporting(true);
    const reader = new FileReader();
    reader.onload = async (ev) => {
      const base64 = (ev.target?.result as string)?.split(',')[1];
      if (!base64) { setImporting(false); return toast.error('Could not read file'); }
      try {
        const { data } = await api.post('/onboarding/setup/step-3/confirm', {
          file_content: base64,
          filename: importFile.name,
        });
        setCredentials(data.teachers || []);
        setShowCredentials(true);
        setShowBulkImport(false);
        toast.success(`${data.total_created} teachers imported`);
        fetchTeachers();
      } catch (err: any) {
        toast.error(err.response?.data?.detail || 'Import failed');
      } finally { setImporting(false); }
    };
    reader.readAsDataURL(importFile);
  };

  const handleBulkProvision = async () => {
    try {
      const { data } = await api.post('/teachers/bulk', { count: 10 });
      setCredentials(data.teachers);
      setShowCredentials(true);
      toast.success(`${data.created} accounts created`);
      fetchTeachers();
    } catch (err: any) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  // ── Export ───────────────────────────────────────────────────────

  const handleExportCSV = () => {
    const csv = [
      ['Employee #', 'Full Name', 'Email', 'Phone', 'Status'],
      ...teachers.map(t => [t.employee_number, t.full_name, t.email, t.phone || '', t.is_active ? 'Active' : 'Pending']),
    ].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'teachers_export.csv'; a.click();
    URL.revokeObjectURL(url);
    toast.success('Exported');
  };

  // ── Render ───────────────────────────────────────────────────────

  if (isTeacherView) {
    return (
      <div className="card text-center py-16">
        <Users className="mx-auto h-12 w-12 text-gray-300 mb-4" />
        <p className="text-gray-500 text-lg">Your profile is managed by your school administrator.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Dashboard */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total Teachers', value: stats.total, color: 'text-blue-600', bg: 'bg-blue-50' },
          { label: 'Active', value: stats.active, color: 'text-emerald-600', bg: 'bg-emerald-50' },
          { label: 'Pending Activation', value: stats.pending, color: 'text-amber-600', bg: 'bg-amber-50' },
          { label: 'Disabled', value: stats.disabled, color: 'text-red-600', bg: 'bg-red-50' },
        ].map(s => (
          <div key={s.label} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <p className={clsx('text-2xl font-bold', s.color)}>{s.value}</p>
            <p className="text-sm text-gray-500 mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
          <input className="input-field pl-9" placeholder="Search teachers…" value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }} />
        </div>
        <div className="flex flex-wrap gap-2">
          {selectedIds.size > 0 && (
            <>
              <button onClick={() => handleBatchToggle(true)} className="btn-secondary text-xs gap-1">
                <CheckSquare className="h-3.5 w-3.5" /> Activate ({selectedIds.size})
              </button>
              <button onClick={() => handleBatchToggle(false)} className="btn-secondary text-xs gap-1">
                <Square className="h-3.5 w-3.5" /> Disable
              </button>
              <button onClick={handleBatchReset} className="btn-secondary text-xs gap-1">
                <RefreshCw className="h-3.5 w-3.5" /> Reset Passwords
              </button>
            </>
          )}
          <button onClick={handleExportCSV} className="btn-secondary gap-1.5 text-sm">
            <FileSpreadsheet className="h-4 w-4" /> Export
          </button>
          <button onClick={() => setShowBulkImport(true)} className="btn-secondary gap-1.5 text-sm">
            <Upload className="h-4 w-4" /> Import
          </button>
          <button onClick={handleBulkProvision} className="btn-secondary gap-1.5 text-sm">
            <UserPlus className="h-4 w-4" /> Generate 10
          </button>
          <button onClick={() => setShowCreate(true)} className="btn-primary gap-1.5 text-sm">
            <Plus className="h-4 w-4" /> Add Teacher
          </button>
        </div>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold">New Teacher</h3>
            <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600"><X className="h-5 w-5" /></button>
          </div>
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

      {/* Bulk Import Modal */}
      {showBulkImport && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold">Import Staff</h3>
            <button onClick={() => { setShowBulkImport(false); setImportFile(null); setImportErrors([]); setImportPreview([]); }} className="text-gray-400 hover:text-gray-600"><X className="h-5 w-5" /></button>
          </div>
          <div className="space-y-4">
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-brand-400 transition-colors">
              <Upload className="mx-auto h-8 w-8 text-gray-400 mb-2" />
              <p className="text-sm text-gray-500 mb-2">Upload a CSV or Excel (.xlsx) file</p>
              <a href="/api/v1/onboarding/setup/staff-template" className="text-sm text-brand-600 hover:underline">Download template</a>
              <div className="mt-3">
                <button onClick={() => fileInputRef.current?.click()} className="btn-secondary">Choose File</button>
                <input ref={fileInputRef} type="file" accept=".csv,.xlsx" className="hidden" onChange={handleFileSelect} />
              </div>
              {importFile && <p className="text-sm text-gray-600 mt-2">{importFile.name}</p>}
            </div>

            {/* Validation Errors */}
            {importErrors.length > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <div className="flex items-center gap-2 text-red-800 font-medium text-sm mb-2">
                  <AlertTriangle className="h-4 w-4" /> {importErrors.length} error(s) found
                </div>
                <ul className="text-sm text-red-700 space-y-1 max-h-40 overflow-y-auto">
                  {importErrors.map((e: any, i: number) => (
                    <li key={i}>Row {e.row}: <strong>{e.field}</strong> — {e.message}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Preview */}
            {importPreview.length > 0 && (
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">Preview ({importPreview.length} valid rows)</p>
                <div className="overflow-x-auto border rounded-lg max-h-48 overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr className="border-b">
                        <th className="text-left p-2 font-semibold text-gray-600">Name</th>
                        <th className="text-left p-2 font-semibold text-gray-600">Email</th>
                        <th className="text-left p-2 font-semibold text-gray-600">Subjects</th>
                        <th className="text-left p-2 font-semibold text-gray-600">Classes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {importPreview.map((r, i) => (
                        <tr key={i} className="border-b last:border-0">
                          <td className="p-2">{r.full_name}</td>
                          <td className="p-2 text-xs">{r.email}</td>
                          <td className="p-2 text-xs">{(r.subjects || []).join(', ')}</td>
                          <td className="p-2 text-xs">{(r.assigned_classes || []).join(', ')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <button onClick={handleConfirmImport} disabled={!importValid || importing}
                  className="btn-primary mt-3 gap-2">
                  {importing ? 'Importing…' : <><Upload className="h-4 w-4" /> Confirm Import ({importPreview.length} teachers)</>}
                </button>
              </div>
            )}

            {importFile && importErrors.length === 0 && importPreview.length === 0 && (
              <p className="text-sm text-gray-500 text-center py-4">No valid rows found. Check the file format.</p>
            )}
          </div>
        </div>
      )}

      {/* Credentials Display */}
      {showCredentials && (
        <div className="card border-emerald-200">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-emerald-800">
              <CheckSquare className="h-5 w-5 inline mr-2" />
              {credentials.length} Account(s) Created
            </h3>
            <button onClick={() => setShowCredentials(false)} className="text-gray-400 hover:text-gray-600"><X className="h-5 w-5" /></button>
          </div>
          <div className="overflow-x-auto border rounded-lg max-h-80 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr className="border-b">
                  <th className="text-left p-2.5 font-semibold text-gray-600">Employee #</th>
                  <th className="text-left p-2.5 font-semibold text-gray-600">Name</th>
                  <th className="text-left p-2.5 font-semibold text-gray-600">Username</th>
                  <th className="text-left p-2.5 font-semibold text-gray-600">Temp Password</th>
                  <th className="text-left p-2.5 font-semibold text-gray-600">Status</th>
                </tr>
              </thead>
              <tbody>
                {credentials.map((t: any) => (
                  <tr key={t.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="p-2.5 font-mono text-xs">{t.employee_number}</td>
                    <td className="p-2.5">{t.full_name}</td>
                    <td className="p-2.5 font-mono text-xs">{t.email}</td>
                    <td className="p-2.5">
                      <code className="bg-gray-100 px-2 py-0.5 rounded font-mono text-xs tracking-wider">
                        {t.temp_password}
                      </code>
                    </td>
                    <td className="p-2.5">
                      <span className="rounded-full bg-amber-100 text-amber-700 px-2 py-0.5 text-xs font-medium">Pending</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex gap-2 mt-4">
            <button onClick={handlePrintCredentials} className="btn-secondary gap-1.5">
              <Printer className="h-4 w-4" /> Print
            </button>
            <button onClick={() => {
              const csv = [['Employee #','Name','Username','Temp Password','Status'],
                ...credentials.map((t: any) => [t.employee_number, t.full_name, t.email, t.temp_password, t.is_active ? 'Active' : 'Pending']),
              ].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
              const blob = new Blob([csv], { type: 'text/csv' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a'); a.href = url; a.download = 'credentials.csv'; a.click();
              URL.revokeObjectURL(url);
            }} className="btn-secondary gap-1.5">
              <Download className="h-4 w-4" /> CSV
            </button>
          </div>
        </div>
      )}

      {/* Reset Password Dialog */}
      {resetResult && (
        <div className="card border-amber-200 bg-amber-50">
          <div className="flex items-start gap-3">
            <Key className="h-5 w-5 text-amber-600 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-amber-900">Password Reset</h3>
              <div className="flex items-center gap-2 mt-2">
                <code className="bg-white px-3 py-1.5 rounded border border-amber-300 font-mono text-sm tracking-wider">
                  {resetResult.new_password}
                </code>
                <button onClick={() => { navigator.clipboard.writeText(resetResult.new_password); toast.success('Copied!'); }}
                  className="text-sm text-amber-700 hover:text-amber-900 font-medium">Copy</button>
              </div>
            </div>
            <button onClick={() => setResetResult(null)} className="text-amber-400 hover:text-amber-600 text-xl leading-none">&times;</button>
          </div>
        </div>
      )}

      {/* Teacher Table */}
      <div className="overflow-x-auto border rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr className="border-b">
              <th className="p-3 w-10">
                <input type="checkbox" checked={selectAll} onChange={handleSelectAll}
                  className="rounded border-gray-300 text-brand-600 focus:ring-brand-500" />
              </th>
              <th className="text-left p-3 font-semibold text-gray-600">Employee #</th>
              <th className="text-left p-3 font-semibold text-gray-600">Name</th>
              <th className="text-left p-3 font-semibold text-gray-600">Email</th>
              <th className="text-left p-3 font-semibold text-gray-600">Phone</th>
              <th className="text-left p-3 font-semibold text-gray-600">Status</th>
              <th className="text-left p-3 font-semibold text-gray-600">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="text-center py-8 text-gray-400">Loading…</td></tr>
            ) : teachers.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-12 text-gray-400">
                <Users className="mx-auto h-8 w-8 mb-2 opacity-50" />
                No teachers found. Add your first teacher above.
              </td></tr>
            ) : teachers.map(teacher => (
              <tr key={teacher.id} className={clsx('border-b last:border-0 hover:bg-gray-50',
                selectedIds.has(teacher.id) && 'bg-brand-50')}>
                <td className="p-3">
                  <input type="checkbox" checked={selectedIds.has(teacher.id)}
                    onChange={() => handleSelectOne(teacher.id)}
                    className="rounded border-gray-300 text-brand-600 focus:ring-brand-500" />
                </td>
                <td className="p-3 font-mono text-xs">{teacher.employee_number}</td>
                <td className="p-3 font-medium">{teacher.full_name}</td>
                <td className="p-3 text-gray-600">{teacher.email}</td>
                <td className="p-3 text-gray-500">{teacher.phone || '—'}</td>
                <td className="p-3">
                  <span className={clsx('rounded-full px-2 py-0.5 text-xs font-medium',
                    teacher.user_status === 'active' && 'bg-green-100 text-green-700',
                    teacher.user_status === 'pending_first_login' && 'bg-amber-100 text-amber-700',
                    teacher.user_status === 'locked' && 'bg-red-100 text-red-700',
                    teacher.user_status === 'disabled' && 'bg-gray-100 text-gray-500',
                    !teacher.user_status && (teacher.is_active ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'),
                  )}>
                    {teacher.user_status === 'active' && 'Active'}
                    {teacher.user_status === 'pending_first_login' && 'Pending'}
                    {teacher.user_status === 'locked' && 'Locked'}
                    {teacher.user_status === 'disabled' && 'Disabled'}
                    {!teacher.user_status && (teacher.is_active ? 'Active' : 'Pending')}
                  </span>
                </td>
                <td className="p-3">
                  <div className="flex items-center gap-1">
                    <button onClick={() => handleToggleActive(teacher.id)}
                      className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700" title="Toggle active">
                      {teacher.is_active ? <ToggleRight className="h-4 w-4 text-green-600" /> : <ToggleLeft className="h-4 w-4 text-gray-400" />}
                    </button>
                    {teacher.user_status === 'locked' ? (
                      <button onClick={() => handleUnlockAccount(teacher.id)}
                        className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-green-600" title="Unlock account">
                        <Unlock className="h-4 w-4" />
                      </button>
                    ) : (
                      <button onClick={() => handleLockAccount(teacher.id)}
                        className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-red-600" title="Lock account">
                        <Lock className="h-4 w-4" />
                      </button>
                    )}
                    <button onClick={() => handleForceResetPassword(teacher.id)}
                      className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-purple-600" title="Force reset password">
                      <ShieldAlert className="h-4 w-4" />
                    </button>
                    <button onClick={() => handleResetPassword(teacher.id)}
                      className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-amber-600" title="Reset password">
                      <Key className="h-4 w-4" />
                    </button>
                    <button className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-blue-600" title="View">
                      <Eye className="h-4 w-4" />
                    </button>
                    <button className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-brand-600" title="Edit">
                      <Pencil className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > pageSize && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500">{total} teacher{total !== 1 ? 's' : ''}</span>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="btn-secondary text-xs gap-1">
              <ChevronLeft className="h-3 w-3" /> Previous
            </button>
            <span className="px-3 py-1.5 text-gray-500">Page {page} of {Math.ceil(total / pageSize)}</span>
            <button disabled={page * pageSize >= total} onClick={() => setPage(page + 1)} className="btn-secondary text-xs gap-1">
              Next <ChevronRight className="h-3 w-3" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
