import { useEffect, useState } from 'react';
import api from '@/services/api';
import toast from 'react-hot-toast';
import { Globe, BookMarked, Award, CheckCircle } from 'lucide-react';

export default function CurriculumPage() {
  const [curricula, setCurricula] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [selectedDetail, setSelectedDetail] = useState<any>(null);
  const [myCurriculum, setMyCurriculum] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get('/curriculum'),
      api.get('/curriculum/my/levels'),
    ]).then(([all, my]) => {
      setCurricula(all.data);
      setMyCurriculum(my.data);
    }).finally(() => setLoading(false));
  }, []);

  const viewDetail = async (id: string) => {
    try {
      const { data } = await api.get(`/curriculum/${id}`);
      setSelectedDetail(data);
      setSelected(id);
    } catch { toast.error('Failed to load curriculum detail'); }
  };

  const assignCurriculum = async (id: string) => {
    try {
      await api.post(`/curriculum/assign?curriculum_id=${id}`);
      toast.success('Curriculum assigned!');
      const { data } = await api.get('/curriculum/my/levels');
      setMyCurriculum(data);
    } catch (err: any) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  if (loading) return <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" /></div>;

  const countryFlags: Record<string, string> = {
    'Kenya': '🇰🇪', 'Nigeria': '🇳🇬', 'South Africa': '🇿🇦', 'International': '🌍',
  };

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Globe className="h-6 w-6 text-brand-600" /> Curriculum Settings
        </h2>
      </div>

      {/* Current curriculum */}
      {myCurriculum?.curriculum && (
        <div className="card mb-6 bg-brand-50 border-brand-200">
          <div className="flex items-center gap-3">
            <CheckCircle className="h-5 w-5 text-brand-600" />
            <div>
              <p className="font-semibold text-brand-900">Active: {myCurriculum.curriculum}</p>
              <p className="text-xs text-brand-600">{myCurriculum.levels?.length || 0} levels configured</p>
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Curriculum list */}
        <div className="lg:col-span-1">
          <h3 className="text-lg font-semibold mb-4">Available Curricula</h3>
          <div className="space-y-2">
            {curricula.map(c => (
              <button key={c.id}
                onClick={() => viewDetail(c.id)}
                className={`w-full text-left p-4 rounded-lg border transition-colors ${
                  selected === c.id ? 'border-brand-400 bg-brand-50' : 'border-gray-100 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm flex items-center gap-2">
                      {countryFlags[c.country || ''] || '📚'} {c.name}
                    </p>
                    <p className="text-xs text-gray-400 font-mono">{c.code}</p>
                  </div>
                  {myCurriculum?.curriculum === c.name && (
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Active</span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Curriculum detail */}
        {selectedDetail ? (
          <div className="lg:col-span-2 space-y-6">
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold">{selectedDetail.name}</h3>
                  <p className="text-sm text-gray-500">{selectedDetail.country} · {selectedDetail.code}</p>
                  {selectedDetail.description && (
                    <p className="text-xs text-gray-400 mt-1">{selectedDetail.description}</p>
                  )}
                </div>
                {myCurriculum?.curriculum !== selectedDetail.name && (
                  <button onClick={() => assignCurriculum(selectedDetail.id)} className="btn-primary text-xs">
                    Set as Active
                  </button>
                )}
              </div>

              {/* Levels */}
              <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1">
                <BookMarked className="h-4 w-4" /> Levels ({selectedDetail.levels?.length || 0})
              </h4>
              <div className="flex flex-wrap gap-2 mb-6">
                {selectedDetail.levels?.map((l: any) => (
                  <span key={l.code} className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium ${
                    l.terminal ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'bg-gray-50 text-gray-700 border border-gray-200'
                  }`}>
                    {l.name}
                    {l.terminal && <span className="text-blue-400">🎓</span>}
                  </span>
                ))}
              </div>

              {/* Grading */}
              {selectedDetail.grading && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1">
                    <Award className="h-4 w-4" /> Grading: {selectedDetail.grading.name}
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {selectedDetail.grading.bands?.map((b: any) => (
                      <div key={b.letter} className="flex items-center justify-between p-2 rounded-lg bg-gray-50 border border-gray-100">
                        <span className="font-bold text-sm">{b.letter}</span>
                        <span className="text-xs text-gray-500">{b.min}–{b.max}%</span>
                        <span className="text-xs text-gray-400">{b.points}pts</span>
                      </div>
                    ))}
                  </div>
                  {selectedDetail.grading.bands && (
                    <div className="mt-3 flex flex-wrap gap-1">
                      {selectedDetail.grading.bands.map((b: any) => (
                        <span key={b.letter} className="text-xs text-gray-400 italic">{b.remark}{b !== selectedDetail.grading.bands[selectedDetail.grading.bands.length-1] ? ' · ' : ''}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="lg:col-span-2 card flex items-center justify-center py-16 text-gray-400">
            <div className="text-center">
              <Globe className="mx-auto h-12 w-12 mb-3" />
              <p>Select a curriculum to view details</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
