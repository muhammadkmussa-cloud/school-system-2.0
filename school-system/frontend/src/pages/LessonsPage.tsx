import { useEffect, useState, useCallback } from 'react';
import api from '@/services/api';
import type { LessonPlan } from '@/types';
import toast from 'react-hot-toast';
import { Plus, BookOpen, Copy, CheckCircle } from 'lucide-react';

export default function LessonsPage() {
  const [lessons, setLessons] = useState<LessonPlan[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [subjects, setSubjects] = useState<any[]>([]);
  const [classes, setClasses] = useState<any[]>([]);
  const [form, setForm] = useState({
    subject_id: '', class_id: '', topic: '', objectives: '', activities: '',
    teaching_resources: '', assessment: '', homework: '', week_number: '', term_number: '',
  });

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/lessons', { params: { page, page_size: 20 } });
      setLessons(data.items);
      setTotal(data.total);
    } catch { toast.error('Failed'); }
    finally { setLoading(false); }
  }, [page]);

  const fetchLookups = async () => {
    try {
      const [sRes, cRes] = await Promise.all([
        api.get('/academic/subjects'),
        api.get('/academic/classes'),
      ]);
      setSubjects(sRes.data);
      setClasses(cRes.data);
    } catch { /* optional */ }
  };

  useEffect(() => { fetchLookups(); }, []);
  useEffect(() => { fetch(); }, [fetch]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/lessons', {
        ...form,
        week_number: form.week_number ? parseInt(form.week_number) : null,
        term_number: form.term_number ? parseInt(form.term_number) : null,
      });
      toast.success('Lesson plan created');
      setShowForm(false);
      fetch();
    } catch (err: any) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const handleDuplicate = async (id: string) => {
    try {
      await api.post('/lessons/duplicate', { source_plan_id: id });
      toast.success('Lesson duplicated');
      fetch();
    } catch { toast.error('Failed to duplicate'); }
  };

  const handleComplete = async (id: string) => {
    try {
      await api.post(`/lessons/${id}/complete`);
      toast.success('Marked complete');
      fetch();
    } catch { toast.error('Failed'); }
  };

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900">Lesson Plans</h2>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary gap-2">
          <Plus className="h-4 w-4" /> New Lesson
        </button>
      </div>

      {showForm && (
        <div className="card mb-6">
          <form onSubmit={handleCreate} className="grid gap-4 sm:grid-cols-2">
            <div><label className="label">Subject *</label><select className="input-field" required value={form.subject_id} onChange={e => setForm({...form, subject_id: e.target.value})}><option value="">Select subject</option>{subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></div>
            <div><label className="label">Class *</label><select className="input-field" required value={form.class_id} onChange={e => setForm({...form, class_id: e.target.value})}><option value="">Select class</option>{classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
            <div><label className="label">Topic *</label><input className="input-field" required value={form.topic} onChange={e => setForm({...form, topic: e.target.value})} /></div>
            <div><label className="label">Week</label><input type="number" className="input-field" value={form.week_number} onChange={e => setForm({...form, week_number: e.target.value})} /></div>
            <div className="sm:col-span-2"><label className="label">Objectives</label><textarea className="input-field" rows={2} value={form.objectives} onChange={e => setForm({...form, objectives: e.target.value})} /></div>
            <div className="sm:col-span-2"><label className="label">Activities</label><textarea className="input-field" rows={2} value={form.activities} onChange={e => setForm({...form, activities: e.target.value})} /></div>
            <div><label className="label">Resources</label><input className="input-field" value={form.teaching_resources} onChange={e => setForm({...form, teaching_resources: e.target.value})} /></div>
            <div><label className="label">Homework</label><input className="input-field" value={form.homework} onChange={e => setForm({...form, homework: e.target.value})} /></div>
            <div className="sm:col-span-2 flex gap-3 justify-end">
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
              <button type="submit" className="btn-primary">Save Lesson</button>
            </div>
          </form>
        </div>
      )}

      <div className="space-y-3">
        {loading ? (
          <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" /></div>
        ) : lessons.length === 0 ? (
          <div className="card text-center py-12">
            <BookOpen className="mx-auto h-12 w-12 text-gray-300 mb-4" />
            <p className="text-gray-500">No lesson plans yet.</p>
          </div>
        ) : (
          lessons.map(l => (
            <div key={l.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-gray-900">{l.topic}</h3>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      l.completion_status === 'completed' ? 'bg-green-100 text-green-700' :
                      l.completion_status === 'in_progress' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-gray-100 text-gray-600'
                    }`}>{l.completion_status}</span>
                  </div>
                  {l.objectives && <p className="text-sm text-gray-600 mt-1">{l.objectives.slice(0, 200)}{l.objectives.length > 200 ? '…' : ''}</p>}
                  <div className="flex gap-3 mt-2 text-xs text-gray-400">
                    {l.week_number && <span>Week {l.week_number}</span>}
                    <span>Created {new Date(l.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="flex gap-1 ml-4">
                  {l.completion_status !== 'completed' && (
                    <button onClick={() => handleComplete(l.id)} className="p-2 rounded hover:bg-green-50 text-green-600" title="Mark Complete">
                      <CheckCircle className="h-4 w-4" />
                    </button>
                  )}
                  <button onClick={() => handleDuplicate(l.id)} className="p-2 rounded hover:bg-gray-100 text-gray-500" title="Duplicate">
                    <Copy className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
