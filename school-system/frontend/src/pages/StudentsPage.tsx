import { useEffect, useState, useCallback } from 'react';
import api from '@/services/api';
import type { Student, PaginatedResponse } from '@/types';
import toast from 'react-hot-toast';
import { Plus, Search, Edit, Archive, ArrowRightLeft, GraduationCap } from 'lucide-react';

export default function StudentsPage() {
  const [students, setStudents] = useState<Student[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [classes, setClasses] = useState<any[]>([]);
  const [years, setYears] = useState<any[]>([]);
  const [formData, setFormData] = useState({
    admission_number: '',
    full_name: '',
    gender: 'male',
    date_of_birth: '',
    class_id: '',
    stream_id: '',
    academic_year_id: '',
    parent_name: '',
    parent_phone: '',
    parent_email: '',
    medical_notes: '',
  });

  useEffect(() => {
    (async () => {
      try {
        const [cRes, yRes] = await Promise.all([
          api.get('/academic/classes'),
          api.get('/academic/years'),
        ]);
        setClasses(cRes.data);
        setYears(yRes.data);
      } catch { /* optional */ }
    })();
  }, []);

  const fetchStudents = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<PaginatedResponse<Student>>('/students', {
        params: { page, page_size: 20, search },
      });
      setStudents(data.items);
      setTotal(data.total);
    } catch {
      toast.error('Failed to load students');
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => { fetchStudents(); }, [fetchStudents]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/students', formData);
      toast.success('Student created');
      setShowForm(false);
      fetchStudents();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create student');
    }
  };

  const handleArchive = async (id: string) => {
    try {
      await api.post(`/students/${id}/archive`);
      toast.success('Student archived');
      fetchStudents();
    } catch {
      toast.error('Failed to archive');
    }
  };

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900">Students</h2>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary gap-2">
          <Plus className="h-4 w-4" />
          Add Student
        </button>
      </div>

      {/* Search */}
      <div className="mb-4 relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          type="text"
          className="input-field pl-10"
          placeholder="Search by name or admission number…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        />
      </div>

      {/* Create form */}
      {showForm && (
        <div className="card mb-6">
          <h3 className="text-lg font-semibold mb-4">Register New Student</h3>
          <form onSubmit={handleCreate} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className="label">Admission Number *</label>
              <input className="input-field" required value={formData.admission_number}
                onChange={e => setFormData({...formData, admission_number: e.target.value})} />
            </div>
            <div>
              <label className="label">Full Name *</label>
              <input className="input-field" required value={formData.full_name}
                onChange={e => setFormData({...formData, full_name: e.target.value})} />
            </div>
            <div>
              <label className="label">Gender</label>
              <select className="input-field" value={formData.gender}
                onChange={e => setFormData({...formData, gender: e.target.value})}>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="label">Date of Birth *</label>
              <input type="date" className="input-field" required value={formData.date_of_birth}
                onChange={e => setFormData({...formData, date_of_birth: e.target.value})} />
            </div>
            <div>
              <label className="label">Class</label>
              <select className="input-field" value={formData.class_id}
                onChange={e => setFormData({...formData, class_id: e.target.value})}>
                <option value="">Select class</option>
                {classes.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Academic Year</label>
              <select className="input-field" value={formData.academic_year_id}
                onChange={e => setFormData({...formData, academic_year_id: e.target.value})}>
                <option value="">Select year</option>
                {years.map((y: any) => <option key={y.id} value={y.id}>{y.name || y.year}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Parent Name</label>
              <input className="input-field" value={formData.parent_name}
                onChange={e => setFormData({...formData, parent_name: e.target.value})} />
            </div>
            <div>
              <label className="label">Parent Phone</label>
              <input className="input-field" value={formData.parent_phone}
                onChange={e => setFormData({...formData, parent_phone: e.target.value})} />
            </div>
            <div>
              <label className="label">Parent Email</label>
              <input type="email" className="input-field" value={formData.parent_email}
                onChange={e => setFormData({...formData, parent_email: e.target.value})} />
            </div>
            <div className="sm:col-span-2 flex gap-3 justify-end">
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
              <button type="submit" className="btn-primary">Save Student</button>
            </div>
          </form>
        </div>
      )}

      {/* Table */}
      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="table-header">Admission #</th>
              <th className="table-header">Name</th>
              <th className="table-header">Gender</th>
              <th className="table-header">Status</th>
              <th className="table-header">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="table-cell text-center py-8">Loading…</td></tr>
            ) : students.length === 0 ? (
              <tr><td colSpan={5} className="table-cell text-center py-8 text-gray-500">No students found</td></tr>
            ) : (
              students.map((s) => (
                <tr key={s.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="table-cell font-mono text-xs">{s.admission_number}</td>
                  <td className="table-cell font-medium">{s.full_name}</td>
                  <td className="table-cell capitalize">{s.gender}</td>
                  <td className="table-cell">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                      s.status === 'active' ? 'bg-green-100 text-green-700' :
                      s.status === 'archived' ? 'bg-gray-100 text-gray-600' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>{s.status}</span>
                  </td>
                  <td className="table-cell">
                    <div className="flex gap-1">
                      <button className="p-1.5 rounded hover:bg-gray-100 text-gray-500" title="Edit">
                        <Edit className="h-4 w-4" />
                      </button>
                      <button onClick={() => handleArchive(s.id)} className="p-1.5 rounded hover:bg-red-50 text-red-500" title="Archive">
                        <Archive className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {total > 20 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-500">Showing {(page-1)*20+1}-{Math.min(page*20, total)} of {total}</p>
            <div className="flex gap-2">
              <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page === 1} className="btn-secondary text-xs">Previous</button>
              <button onClick={() => setPage(p => p+1)} disabled={page * 20 >= total} className="btn-secondary text-xs">Next</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
