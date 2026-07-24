import { useEffect, useState } from 'react';
import api from '@/services/api';
import toast from 'react-hot-toast';
import { GitBranch, Check, X, Clock, ArrowRight } from 'lucide-react';

export default function WorkflowPage() {
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [states, setStates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/workflow/definitions').then(({ data }) => setWorkflows(data)).finally(() => setLoading(false));
  }, []);

  const viewWorkflow = async (id: string) => {
    try {
      const { data } = await api.get(`/workflow/definitions/${id}`);
      setSelected(data);
      setStates(data.states);
    } catch { toast.error('Failed to load workflow'); }
  };

  if (loading) return <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" /></div>;

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900">Workflow Approvals</h2>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <GitBranch className="h-5 w-5 text-brand-600" /> Approval Chains
          </h3>
          <div className="space-y-2">
            {workflows.map(w => (
              <button key={w.id} onClick={() => viewWorkflow(w.id)}
                className={`w-full text-left p-4 rounded-lg border transition-colors ${selected?.id === w.id ? 'border-brand-400 bg-brand-50' : 'border-gray-100 hover:bg-gray-50'}`}>
                <p className="font-semibold text-gray-900">{w.name}</p>
                <p className="text-xs text-gray-500 capitalize">Entity: {w.entity_type.replace('_', ' ')}</p>
              </button>
            ))}
          </div>
        </div>

        {selected && (
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">{selected.name} — States</h3>
            <div className="space-y-3">
              {states.map((s, i) => (
                <div key={s.name} className="flex items-center gap-3">
                  <div className="flex flex-col items-center">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold"
                      style={{ backgroundColor: s.color || '#6b7280' }}
                    >
                      {i + 1}
                    </div>
                    {i < states.length - 1 && <div className="w-0.5 h-6 bg-gray-300" />}
                  </div>
                  <div className="flex-1 p-3 rounded-lg border border-gray-100">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-sm">{s.display}</p>
                        <p className="text-xs text-gray-400">
                          Required: <span className="capitalize">{s.required_role?.replace('_', ' ')}</span>
                        </p>
                      </div>
                      {s.is_final ? (
                        <Check className="h-5 w-5 text-green-500" />
                      ) : (
                        <Clock className="h-4 w-4 text-gray-400" />
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-4">
              Each state has a required role. Only users with that role can approve transitions.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
