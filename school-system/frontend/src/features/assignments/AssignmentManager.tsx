import { useEffect, useState } from 'react';
import api from '@/services/api';
import toast from 'react-hot-toast';
import { Plus, ClipboardList, CheckCircle, Clock, FileText, BarChart3 } from 'lucide-react';

export default function AssignmentManager() {
  const [assignments, setAssignments] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [submissions, setSubmissions] = useState<any>(null);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    subject_id: '', class_id: '', title: '', description: '',
    assignment_type: 'homework', due_date: '', max_score: '',
  });

  useEffect(() => {
    api.get('/assignments').then(({ data }) => setAssignments(data.items)).finally(() => setLoading(false));
  }, []);

  const createAssignment = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = { ...form };
      if (form.max_score) payload.max_score = parseFloat(form.max_score);
      await api.post('/assignments', payload);
      toast.success('Assignment created');
      setShowForm(false);
      const { data } = await api.get('/assignments');
      setAssignments(data.items);
    } catch (err: any) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const viewSubmissions = async (a: any) => {
    setSelected(a);
    try {
      const { data } = await api.get(`/assignments/${a.id}/submissions`);
      setSubmissions(data);
    } catch { toast.error('Failed to load submissions'); }
  };

  const gradeSubmission = async (subId: string, score: number) => {
    try {
      await api.post(`/assignments/submissions/${subId}/grade`, { score });
      toast.success('Graded!');
      if (selected) viewSubmissions(selected);
    } catch { toast.error('Failed'); }
  };

  if (loading) return <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" /></div>;

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900">Digital Assignments</h2>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary gap-2">
          <Plus className="h-4 w-4" /> New Assignment
        </button>
      </div>

      {showForm && (
        <div className="card mb-6">
          <form onSubmit={createAssignment} className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2"><label className="label">Title *</label><input className="input-field" required value={form.title} onChange={e => setForm({...form, title: e.target.value})} /></div>
            <div><label className="label">Type</label><select className="input-field" value={form.assignment_type} onChange={e => setForm({...form, assignment_type: e.target.value})}>
              <option value="homework">Homework</option><option value="classwork">Classwork</option><option value="project">Project</option><option value="takeaway">Takeaway</option>
            </select></div>
            <div><label className="label">Due Date *</label><input type="datetime-local" className="input-field" required value={form.due_date} onChange={e => setForm({...form, due_date: e.target.value})} /></div>
            <div><label className="label">Max Score</label><input type="number" className="input-field" value={form.max_score} onChange={e => setForm({...form, max_score: e.target.value})} /></div>
            <div className="sm:col-span-2"><label className="label">Description</label><textarea className="input-field" rows={3} value={form.description} onChange={e => setForm({...form, description: e.target.value})} /></div>
            <div className="sm:col-span-2 flex gap-3 justify-end">
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
              <button type="submit" className="btn-primary">Create</button>
            </div>
          </form>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-brand-600" /> Assignments
          </h3>
          {assignments.length === 0 ? (
            <p className="text-gray-400 text-sm py-8 text-center">No assignments yet.</p>
          ) : (
            <div className="space-y-2">
              {assignments.map(a => (
                <button key={a.id} onClick={() => viewSubmissions(a)}
                  className={`w-full text-left p-3 rounded-lg border transition-colors ${selected?.id === a.id ? 'border-brand-400 bg-brand-50' : 'border-gray-100 hover:bg-gray-50'}`}>
                  <p className="font-medium text-sm">{a.title}</p>
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                    <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> Due: {new Date(a.due_date).toLocaleDateString()}</span>
                    {a.max_score && <span>Max: {a.max_score} pts</span>}
                    <span className="capitalize">{a.assignment_type}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {submissions && (
          <div className="card">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-brand-600" /> Submissions
            </h3>
            {submissions.stats && (
              <div className="grid grid-cols-4 gap-2 mb-4">
                <div className="text-center p-2 bg-gray-50 rounded"><p className="text-lg font-bold">{submissions.stats.total_students}</p><p className="text-xs text-gray-500">Total</p></div>
                <div className="text-center p-2 bg-green-50 rounded"><p className="text-lg font-bold text-green-700">{submissions.stats.submitted}</p><p className="text-xs text-green-600">Submitted</p></div>
                <div className="text-center p-2 bg-yellow-50 rounded"><p className="text-lg font-bold text-yellow-700">{submissions.stats.pending}</p><p className="text-xs text-yellow-600">Pending</p></div>
                <div className="text-center p-2 bg-blue-50 rounded"><p className="text-lg font-bold text-blue-700">{submissions.stats.graded}</p><p className="text-xs text-blue-600">Graded</p></div>
              </div>
            )}
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {submissions.submissions?.map((s: any) => (
                <div key={s.id} className="flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-gray-50">
                  <span className="text-xs font-mono w-20 truncate">{s.student_id?.slice(0,8)}</span>
                  {s.submitted_at ? (
                    <span className="flex items-center gap-1 text-xs text-green-600"><CheckCircle className="h-3 w-3" /> Submitted</span>
                  ) : (
                    <span className="text-xs text-gray-400">Not submitted</span>
                  )}
                  {s.grade && <span className="text-xs font-bold ml-auto">{s.grade}</span>}
                  {s.score != null && <span className="text-xs">{s.score}</span>}
                  {s.submitted_at && s.score == null && (
                    <input type="number" className="input-field w-16 text-xs ml-auto" placeholder="Score"
                      onKeyDown={e => { if (e.key === 'Enter') gradeSubmission(s.id, parseFloat((e.target as HTMLInputElement).value)); }} />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
