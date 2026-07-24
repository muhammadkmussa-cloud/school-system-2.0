import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';
import PlatformLayout from '@/components/layout/PlatformLayout';
import SchoolLayout from '@/components/layout/SchoolLayout';
import LoginPage from '@/pages/LoginPage';
import FirstLoginWizard from '@/features/auth/FirstLoginWizard';

// Platform Admin pages
import PlatformDashboard from '@/pages/platform/PlatformDashboard';
import SchoolsPage from '@/pages/SchoolsPage';

// School Admin pages (existing, reused)
import SchoolDashboard from '@/pages/school/SchoolDashboard';
import StudentsPage from '@/pages/StudentsPage';
import TeachersPage from '@/pages/TeachersPage';
import AcademicPage from '@/pages/AcademicPage';
import TimetablePage from '@/pages/TimetablePage';
import AttendancePage from '@/pages/AttendancePage';
import GradebookPage from '@/pages/GradebookPage';
import LessonsPage from '@/pages/LessonsPage';
import ReportsPage from '@/pages/ReportsPage';
import ExamsPage from '@/pages/ExamsPage';
import WorkflowPage from '@/pages/WorkflowPage';
import CurriculumPage from '@/pages/CurriculumPage';
import SetupWizard from '@/features/setup/SetupWizard';
import PromotionManager from '@/features/promotion/PromotionManager';
import ImportManager from '@/features/imports/ImportManager';
import CalendarView from '@/features/calendar/CalendarView';
import AssignmentManager from '@/features/assignments/AssignmentManager';
import AdvancedDashboard from '@/features/dashboard/AdvancedDashboard';
import AuditPage from '@/pages/AuditPage';
import BillingPage from '@/features/billing/BillingPage';
import StaffManagement from '@/features/staff/StaffManagement';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function PlatformGuard({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  if (user?.role !== 'platform_admin') return <Navigate to="/" replace />;
  return <>{children}</>;
}

function SchoolGuard({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === 'platform_admin') return <Navigate to="/admin" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/first-login" element={<FirstLoginWizard />} />

      {/* Platform Admin Console — completely separate layout and pages */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <PlatformGuard>
              <PlatformLayout />
            </PlatformGuard>
          </ProtectedRoute>
        }
      >
        <Route index element={<PlatformDashboard />} />
        <Route path="schools" element={<SchoolsPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="billing" element={<BillingPage />} />
        <Route path="settings" element={<div className="text-gray-400 text-center py-20">Platform Settings (coming soon)</div>} />
        <Route path="revenue" element={<div className="text-gray-400 text-center py-20">Revenue Dashboard (coming soon)</div>} />
        <Route path="subscriptions" element={<div className="text-gray-400 text-center py-20">Subscription Management (coming soon)</div>} />
        <Route path="users" element={<div className="text-gray-400 text-center py-20">Platform Users (coming soon)</div>} />
        <Route path="analytics" element={<div className="text-gray-400 text-center py-20">Platform Analytics (coming soon)</div>} />
        <Route path="monitoring" element={<div className="text-gray-400 text-center py-20">API Monitoring (coming soon)</div>} />
        <Route path="health" element={<div className="text-gray-400 text-center py-20">System Health (coming soon)</div>} />
        <Route path="database" element={<div className="text-gray-400 text-center py-20">Database Status (coming soon)</div>} />
        <Route path="jobs" element={<div className="text-gray-400 text-center py-20">Background Jobs (coming soon)</div>} />
        <Route path="integrations" element={<div className="text-gray-400 text-center py-20">Integrations (coming soon)</div>} />
        <Route path="feature-flags" element={<div className="text-gray-400 text-center py-20">Feature Flags (coming soon)</div>} />
        <Route path="backups" element={<div className="text-gray-400 text-center py-20">Backup &amp; Restore (coming soon)</div>} />
        <Route path="announcements" element={<div className="text-gray-400 text-center py-20">Announcements (coming soon)</div>} />
        <Route path="support" element={<div className="text-gray-400 text-center py-20">Support Tickets (coming soon)</div>} />
        <Route path="roles" element={<div className="text-gray-400 text-center py-20">Roles &amp; Permissions (coming soon)</div>} />
        <Route path="plans" element={<div className="text-gray-400 text-center py-20">Plans &amp; Pricing (coming soon)</div>} />
        <Route path="invoices" element={<div className="text-gray-400 text-center py-20">Invoices (coming soon)</div>} />
        <Route path="payments" element={<div className="text-gray-400 text-center py-20">Payments (coming soon)</div>} />
      </Route>

      {/* School Admin / Teacher App — uses SchoolLayout */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <SchoolGuard>
              <SchoolLayout />
            </SchoolGuard>
          </ProtectedRoute>
        }
      >
        <Route index element={<SchoolDashboard />} />
        <Route path="dashboard" element={<SchoolDashboard />} />
        <Route path="students" element={<StudentsPage />} />
        <Route path="teachers" element={<TeachersPage />} />
        <Route path="academic" element={<AcademicPage />} />
        <Route path="timetable" element={<TimetablePage />} />
        <Route path="attendance" element={<AttendancePage />} />
        <Route path="gradebook" element={<GradebookPage />} />
        <Route path="lessons" element={<LessonsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="schools" element={<Navigate to="/admin/schools" replace />} />
        <Route path="exams" element={<ExamsPage />} />
        <Route path="workflow" element={<WorkflowPage />} />
        <Route path="curriculum" element={<CurriculumPage />} />
        <Route path="calendar" element={<CalendarView />} />
        <Route path="assignments" element={<AssignmentManager />} />
        <Route path="setup" element={<SetupWizard />} />
        <Route path="promotion" element={<PromotionManager />} />
        <Route path="import" element={<ImportManager />} />
        <Route path="analytics" element={<AdvancedDashboard />} />
        <Route path="billing" element={<BillingPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="staff" element={<StaffManagement />} />

        {/* School Namespaced routes (for new sidebar links) */}
        <Route path="school/students" element={<StudentsPage />} />
        <Route path="school/admissions" element={<StudentsPage />} />
        <Route path="school/teachers" element={<TeachersPage />} />
        <Route path="school/academic" element={<AcademicPage />} />
        <Route path="school/subjects" element={<AcademicPage />} />
        <Route path="school/timetable" element={<TimetablePage />} />
        <Route path="school/attendance" element={<AttendancePage />} />
        <Route path="school/lessons" element={<LessonsPage />} />
        <Route path="school/assignments" element={<AssignmentManager />} />
        <Route path="school/exams" element={<ExamsPage />} />
        <Route path="school/gradebook" element={<GradebookPage />} />
        <Route path="school/curriculum" element={<CurriculumPage />} />
        <Route path="school/reports" element={<ReportsPage />} />
        <Route path="school/analytics" element={<AdvancedDashboard />} />
        <Route path="school/calendar" element={<CalendarView />} />
        <Route path="school/workflow" element={<WorkflowPage />} />
        <Route path="school/staff" element={<StaffManagement />} />
        <Route path="school/setup" element={<SetupWizard />} />
        <Route path="school/promotion" element={<PromotionManager />} />
        <Route path="school/import" element={<ImportManager />} />
        <Route path="school/communication" element={<div className="text-gray-500 text-center py-20">Communication (coming soon)</div>} />
        <Route path="school/library" element={<div className="text-gray-500 text-center py-20">Library (coming soon)</div>} />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
