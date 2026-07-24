import { useEffect, useState } from 'react';
import api from '@/services/api';
import type { School } from '@/types';
import toast from 'react-hot-toast';
import { Plus, Building2, ToggleLeft, ToggleRight } from 'lucide-react';
import { useAuthStore } from '@/store/auth';

export default function SchoolsPage() {
  const user = useAuthStore((s) => s.user);
  const [schools, setSchools] = useState<School[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', code: '', email: '', phone: '', address: '' });

  useEffect(() => {
    if (user?.role !== 'platform_admin') return;
    api.get('/schools')
      .then(({ data }) => setSchools(data.items))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user?.role]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/schools', form);
      toast.success('School created');
      setShowForm(false);
      const { data } = await api.get('/schools');
      setSchools(data.items);
    } catch (err: any) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const toggleActive = async (id: string) => {
    try {
      const { data } = await api.post(`/schools/${id}/toggle-active`);
      setSchools(schools.map(s => s.id === id ? data : s));
      toast.success('Status updated');
    } catch { toast.error('Failed'); }
  };

  if (user?.role !== 'platform_admin') {
    return <div className="card"><p className="text-gray-500">Access restricted to platform administrators.</p></div>;
  }

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900">Schools</h2>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary gap-2">
          <Plus className="h-4 w-4" /> Register School
        </button>
      </div>

      {showForm && (
        <div className="card mb-6">
          <form onSubmit={handleCreate} className="grid gap-4 sm:grid-cols-2">
            <div><label className="label">School Name *</label><input className="input-field" required value={form.name} onChange={e => setForm({...form, name: e.target.value})} /></div>
            <div><label className="label">Code *</label><input className="input-field" required value={form.code} onChange={e => setForm({...form, code: e.target.value})} /></div>
            <div><label className="label">Email</label><input type="email" className="input-field" value={form.email} onChange={e => setForm({...form, email: e.target.value})} /></div>
            <div><label className="label">Phone</label><input className="input-field" value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} /></div>
            <div className="sm:col-span-2"><label className="label">Address</label><input className="input-field" value={form.address} onChange={e => setForm({...form, address: e.target.value})} /></div>
            <div className="sm:col-span-2 flex gap-3 justify-end">
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
              <button type="submit" className="btn-primary">Register</button>
            </div>
          </form>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {schools.map(s => (
          <div key={s.id} className="card">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-100">
                  <Building2 className="h-5 w-5 text-brand-600" />
                </div>
                <div>
                  <p className="font-semibold text-gray-900">{s.name}</p>
                  <p className="text-xs text-gray-500 font-mono">{s.code}</p>
                </div>
              </div>
              <button onClick={() => toggleActive(s.id)} title="Toggle active">
                {s.is_active ? <ToggleRight className="h-5 w-5 text-green-600" /> : <ToggleLeft className="h-5 w-5 text-gray-400" />}
              </button>
            </div>
            {s.email && <p className="mt-2 text-xs text-gray-500">{s.email}</p>}
            <div className="mt-3 flex items-center gap-2">
              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 capitalize">{s.subscription_tier}</span>
              <span className={`rounded-full px-2 py-0.5 text-xs ${s.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {s.is_active ? 'Active' : 'Suspended'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
