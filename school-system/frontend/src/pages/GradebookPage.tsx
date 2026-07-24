import { useEffect, useState } from 'react';
import api from '@/services/api';
import type { Assessment, Mark, Student } from '@/types';
import toast from 'react-hot-toast';
import { ClipboardCheck, BarChart3 } from 'lucide-react';

export default function GradebookPage() {
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [selected, setSelected] = useState<Assessment | null>(null);
  const [marks, setMarks] = useState<Record<string, { score: string; remarks: string }>>({});
  const [students, setStudents] = useState<Student[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ subject_id: '', class_id: '', name: '', assessment_type: 'test', max_score: '100', weight: '1', term_id: '' });

  useEffect(() => {
    api.get('/gradebook/assessments').then(({ data }) => setAssessments(data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    Promise.all([
      api.get(`/gradebook/assessments/${selected.id}/marks`),
      api.get(`/gradebook/assessments/${selected.id}/stats`),
      api.get('/students', { params: { class_id: selected.class_id, status: 'active', page_size: 200 } }),
    ]).then(([mRes, sRes, stRes]) => {
      const mMap: Record<string, { score: string; remarks: string }> = {};
      mRes.data.forEach((m: Mark) => { mMap[m.student_id] = { score: String(m.score), remarks: m.remarks || '' }; });
      setMarks(mMap);
      setStats(sRes.data);
      setStudents(stRes.data.items);
    }).catch(() => toast.error('Failed to load'))
    .finally(() => setLoading(false));
  }, [selected]);

  const saveMarks = async () => {
    if (!selected) return;
    const payload = Object.entries(marks).map(([student_id, { score, remarks }]) => ({
      student_id, score: parseFloat(score) || 0, remarks,
    }));
    try {
      await api.post(`/gradebook/assessments/${selected.id}/marks`, payload);
      toast.success('Marks saved!');
      const { data } = await api.get(`/gradebook/assessments/${selected.id}/stats`);
      setStats(data);
    } catch { toast.error('Failed to save marks'); }
  };

  const createAssessment = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/gradebook/assessments', { ...form, max_score: parseFloat(form.max_score), weight: parseFloat(form.weight) });
      toast.success('Assessment created');
      setShowForm(false);
      const { data } = await api.get('/gradebook/assessments');
      setAssessments(data);
    } catch (err: any) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900">Gradebook</h2>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary gap-2">
          <ClipboardCheck className="h-4 w-4" /> New Assessment
        </button>
      </div>

      {showForm && (
        <div className="card mb-6">
          <form onSubmit={createAssessment} className="grid gap-4 sm:grid-cols-3">
            <div><label className="label">Name *</label><input className="input-field" required value={form.name} onChange={e => setForm({...form, name: e.target.value})} /></div>
            <div><label className="label">Type</label><select className="input-field" value={form.assessment_type} onChange={e => setForm({...form, assessment_type: e.target.value})}><option value="test">Test</option><option value="exam">Exam</option><option value="quiz">Quiz</option><option value="assignment">Assignment</option><option value="project">Project</option></select></div>
            <div><label className="label">Max Score</label><input type="number" className="input-field" value={form.max_score} onChange={e => setForm({...form, max_score: e.target.value})} /></div>
            <div className="sm:col-span-3 flex gap-3 justify-end">
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
              <button type="submit" className="btn-primary">Create</button>
            </div>
          </form>
        </div>
      )}

      {/* Assessment selector */}
      <div className="mb-4 flex gap-2 flex-wrap">
        {assessments.map(a => (
          <button key={a.id} onClick={() => setSelected(a)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${selected?.id === a.id ? 'bg-brand-600 text-white' : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'}`}>
            {a.name}
          </button>
        ))}
      </div>

      {/* Stats */}
      {stats && (
        <div className="card mb-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
            <div><p className="text-2xl font-bold text-gray-900">{stats.average}</p><p className="text-xs text-gray-500">Average</p></div>
            <div><p className="text-2xl font-bold text-green-600">{stats.highest}</p><p className="text-xs text-gray-500">Highest</p></div>
            <div><p className="text-2xl font-bold text-red-600">{stats.lowest}</p><p className="text-xs text-gray-500">Lowest</p></div>
            <div><p className="text-2xl font-bold text-brand-600">{stats.total_students}</p><p className="text-xs text-gray-500">Students</p></div>
          </div>
          {/* Grade distribution */}
          {stats.grade_distribution && (
            <div className="mt-4 flex flex-wrap gap-2">
              {Object.entries(stats.grade_distribution).map(([grade, count]) => (
                <span key={grade} className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium">{grade}: {count as number}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Marks entry */}
      {selected && !loading && (
        <div className="card">
          <div className="space-y-1">
            {students.map(s => (
              <div key={s.id} className="flex items-center gap-3 rounded-lg border border-gray-100 p-3 hover:bg-gray-50">
                <span className="text-sm font-medium w-24 truncate">{s.full_name}</span>
                <input type="number" className="input-field w-20 text-sm" placeholder="Score"
                  value={marks[s.id]?.score || ''}
                  onChange={e => setMarks({...marks, [s.id]: { ...marks[s.id], score: e.target.value }})} />
                <span className="text-xs text-gray-400">/ {selected.max_score}</span>
                <input className="input-field flex-1 text-xs" placeholder="Remarks"
                  value={marks[s.id]?.remarks || ''}
                  onChange={e => setMarks({...marks, [s.id]: { ...marks[s.id], remarks: e.target.value }})} />
              </div>
            ))}
          </div>
          <button onClick={saveMarks} className="btn-primary mt-4">Save Marks</button>
        </div>
      )}
    </div>
  );
}
