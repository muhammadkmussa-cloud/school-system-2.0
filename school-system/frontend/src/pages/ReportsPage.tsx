import { useState } from 'react';
import api from '@/services/api';
import toast from 'react-hot-toast';
import { FileBarChart, Download, FileSpreadsheet, Users, GraduationCap, ClipboardList } from 'lucide-react';

export default function ReportsPage() {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [reportType, setReportType] = useState<string>('');

  const generateReport = async (type: string) => {
    setLoading(true);
    setReportType(type);
    try {
      const { data } = await api.get(`/reports/${type}`);
      setReport(data);
    } catch { toast.error('Failed to generate report'); }
    finally { setLoading(false); }
  };

  const downloadCSV = async (type: string) => {
    try {
      const response = await api.get(`/reports/${type}`, {
        params: { format: 'csv' },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(new Blob([response.data], { type: 'text/csv' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `${type}_report.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error('Failed to export CSV'); }
  };

  const reportCards = [
    { id: 'attendance', icon: ClipboardList, label: 'Attendance Report', color: 'blue' },
    { id: 'students', icon: GraduationCap, label: 'Student List', color: 'purple' },
    { id: 'teacher-workload', icon: Users, label: 'Teacher Workload', color: 'amber' },
    { id: 'subject-performance', icon: FileBarChart, label: 'Subject Performance', color: 'green' },
  ];

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900">Reports</h2>
      </div>

      {/* Report cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        {reportCards.map(r => (
          <button key={r.id} onClick={() => generateReport(r.id)}
            className="card text-left hover:shadow-md transition-shadow cursor-pointer">
            <div className={`flex h-10 w-10 items-center justify-center rounded-lg bg-${r.color}-100 mb-3`}>
              <r.icon className={`h-5 w-5 text-${r.color}-600`} />
            </div>
            <p className="font-semibold text-gray-900">{r.label}</p>
            <p className="text-xs text-gray-400 mt-1">Click to generate</p>
          </button>
        ))}
      </div>

      {/* Report output */}
      {loading && (
        <div className="card flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
        </div>
      )}

      {report && !loading && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 capitalize">{reportType} Report</h3>
            <button onClick={() => downloadCSV(reportType)} className="btn-secondary gap-2 text-xs">
              <Download className="h-3 w-3" /> Export CSV
            </button>
          </div>

          {/* Attendance */}
          {reportType === 'attendance' && (
            <div>
              <p className="text-sm text-gray-500 mb-4">{report.total} records found</p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="border-b"><th className="table-header">Date</th><th className="table-header">Student ID</th><th className="table-header">Status</th><th className="table-header">Remarks</th></tr></thead>
                  <tbody>
                    {report.records?.slice(0, 50).map((r: any, i: number) => (
                      <tr key={i} className="border-b border-gray-100"><td className="table-cell">{r.date}</td><td className="table-cell font-mono text-xs">{r.student_id?.slice(0,8)}</td><td className="table-cell capitalize">{r.status}</td><td className="table-cell text-xs">{r.remarks || '—'}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Students */}
          {reportType === 'students' && (
            <div>
              <p className="text-sm text-gray-500 mb-4">{report.total} students</p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="border-b"><th className="table-header">Admission #</th><th className="table-header">Name</th><th className="table-header">Gender</th><th className="table-header">Status</th></tr></thead>
                  <tbody>
                    {report.students?.slice(0, 50).map((r: any, i: number) => (
                      <tr key={i} className="border-b border-gray-100"><td className="table-cell font-mono text-xs">{r.admission_number}</td><td className="table-cell">{r.full_name}</td><td className="table-cell capitalize">{r.gender}</td><td className="table-cell capitalize">{r.status}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Teacher Workload */}
          {reportType === 'teacher-workload' && (
            <div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="border-b"><th className="table-header">Teacher</th><th className="table-header">Emp #</th><th className="table-header">Lessons</th><th className="table-header">Assessments</th></tr></thead>
                  <tbody>
                    {report.teachers?.map((t: any, i: number) => (
                      <tr key={i} className="border-b border-gray-100"><td className="table-cell">{t.name}</td><td className="table-cell font-mono text-xs">{t.employee_number}</td><td className="table-cell">{t.lessons}</td><td className="table-cell">{t.assessments}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Subject Performance */}
          {reportType === 'subject-performance' && (
            <div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="border-b"><th className="table-header">Subject ID</th><th className="table-header">Average</th><th className="table-header">Highest</th><th className="table-header">Lowest</th><th className="table-header">Marks</th></tr></thead>
                  <tbody>
                    {report.subjects?.map((s: any, i: number) => (
                      <tr key={i} className="border-b border-gray-100"><td className="table-cell font-mono text-xs">{s.subject_id?.slice(0,8)}</td><td className="table-cell font-semibold">{s.average}</td><td className="table-cell text-green-600">{s.highest}</td><td className="table-cell text-red-600">{s.lowest}</td><td className="table-cell">{s.total_marks_recorded}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
