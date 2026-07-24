import { useEffect, useState } from 'react';
import api from '@/services/api';
import toast from 'react-hot-toast';
import { Plus, BookOpen, Trophy, Users, BarChart3 } from 'lucide-react';
import type { AcademicYear, Term } from '@/types';

export default function ExamsPage() {
  const [series, setSeries] = useState<any[]>([]);
  const [terms, setTerms] = useState<Term[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [selected, setSelected] = useState<any>(null);
  const [rankings, setRankings] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    term_id: '', name: '', series_type: 'endterm',
    start_date: '', end_date: '', weight_percentage: '40',
  });

  useEffect(() => {
    Promise.all([
      api.get('/exams/series'),
      api.get('/academic/terms'),
    ]).then(([s, t]) => {
      setSeries(s.data);
      setTerms(t.data);
    }).finally(() => setLoading(false));
  }, []);

  const createSeries = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/exams/series', {
        ...form,
        weight_percentage: parseFloat(form.weight_percentage),
      });
      toast.success('Exam series created');
      setShowForm(false);
      const { data } = await api.get('/exams/series');
      setSeries(data);
    } catch (err: any) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const viewRankings = async (seriesItem: any) => {
    setSelected(seriesItem);
    try {
      // Get a class from the school
      const { data: classes } = await api.get('/academic/classes');
      if (classes.length > 0) {
        const { data } = await api.get(
          `/exams/results/class/${classes[0].id}/ranking?term_id=${seriesItem.term_id || ''}`
        );
        setRankings(data);
      }
    } catch { toast.error('Failed to load rankings'); }
  };

  if (loading) return <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" /></div>;

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900">Exam Management</h2>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary gap-2">
          <Plus className="h-4 w-4" /> New Exam Series
        </button>
      </div>

      {showForm && (
        <div className="card mb-6">
          <form onSubmit={createSeries} className="grid gap-4 sm:grid-cols-3">
            <div><label className="label">Name *</label><input className="input-field" required value={form.name} onChange={e => setForm({...form, name: e.target.value})} /></div>
            <div><label className="label">Type</label><select className="input-field" value={form.series_type} onChange={e => setForm({...form, series_type: e.target.value})}>
              <option value="cat">CAT</option><option value="midterm">Midterm</option><option value="endterm">End Term</option><option value="practical">Practical</option><option value="project">Project</option><option value="mock">Mock</option>
            </select></div>
            <div><label className="label">Term</label><select className="input-field" value={form.term_id} onChange={e => setForm({...form, term_id: e.target.value})}>
              <option value="">Select term…</option>
              {terms.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select></div>
            <div><label className="label">Start Date</label><input type="date" className="input-field" value={form.start_date} onChange={e => setForm({...form, start_date: e.target.value})} /></div>
            <div><label className="label">End Date</label><input type="date" className="input-field" value={form.end_date} onChange={e => setForm({...form, end_date: e.target.value})} /></div>
            <div><label className="label">Weight %</label><input type="number" className="input-field" value={form.weight_percentage} onChange={e => setForm({...form, weight_percentage: e.target.value})} /></div>
            <div className="sm:col-span-3 flex gap-3 justify-end">
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
              <button type="submit" className="btn-primary">Create Series</button>
            </div>
          </form>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-brand-600" /> Exam Series
          </h3>
          {series.length === 0 ? (
            <p className="text-gray-400 text-sm py-8 text-center">No exam series created yet.</p>
          ) : (
            <div className="space-y-2">
              {series.map(s => (
                <button key={s.id} onClick={() => viewRankings(s)}
                  className={`w-full text-left p-4 rounded-lg border transition-colors ${selected?.id === s.id ? 'border-brand-400 bg-brand-50' : 'border-gray-100 hover:bg-gray-50'}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-gray-900">{s.name}</p>
                      <p className="text-xs text-gray-500">{s.series_type} · {s.start_date} → {s.end_date} · Weight: {s.weight_percentage}%</p>
                    </div>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${s.is_published ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                      {s.is_published ? 'Published' : 'Draft'}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {rankings && (
          <div className="card">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Trophy className="h-5 w-5 text-yellow-500" /> Class Rankings
            </h3>
            <div className="space-y-1">
              {rankings.rankings?.slice(0, 10).map((r: any, i: number) => (
                <div key={r.student_id} className="flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-gray-50">
                  <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    i === 0 ? 'bg-yellow-100 text-yellow-800' :
                    i === 1 ? 'bg-gray-200 text-gray-700' :
                    i === 2 ? 'bg-orange-100 text-orange-700' :
                    'bg-gray-100 text-gray-500'
                  }`}>{r.rank}</span>
                  <span className="flex-1 font-medium text-sm">{r.name}</span>
                  <span className="text-sm font-bold text-brand-600">{r.mean}%</span>
                  <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">{r.grade}</span>
                </div>
              ))}
              {(!rankings.rankings || rankings.rankings.length === 0) && (
                <p className="text-gray-400 text-sm py-4 text-center">No rankings available.</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
