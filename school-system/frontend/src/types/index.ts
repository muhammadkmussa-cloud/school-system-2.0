/* ── Core types for School Management System Web Client ── */

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'platform_admin' | 'school_admin' | 'deputy_principal' | 'head_teacher' | 'teacher';
  phone: string | null;
  last_login_at: string | null;
  school_id: string;
  created_at: string;

  // Account lifecycle (replaces is_active/is_verified)
  username: string | null;
  status: 'pending_first_login' | 'active' | 'locked' | 'disabled';
  must_change_password: boolean;
  terms_accepted: boolean;
  profile_completed: boolean;
  password_changed_at: string | null;
  is_active: boolean;  // computed from status
  is_verified: boolean;  // computed from must_change_password
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface School {
  id: string;
  name: string;
  code: string;
  email: string | null;
  phone: string | null;
  address: string | null;
  logo_url: string | null;
  is_active: boolean;
  subscription_tier: string;
  created_at: string;
}

export interface Student {
  id: string;
  admission_number: string;
  full_name: string;
  gender: 'male' | 'female' | 'other';
  date_of_birth: string;
  class_id: string;
  stream_id: string | null;
  academic_year_id: string;
  parent_name: string | null;
  parent_phone: string | null;
  parent_email: string | null;
  medical_notes: string | null;
  status: 'active' | 'archived' | 'transferred' | 'graduated';
  created_at: string;
}

export interface Teacher {
  id: string;
  employee_number: string;
  full_name: string;
  email: string;
  phone: string | null;
  is_active: boolean;
  user_id: string | null;
  created_at: string;
}

export interface AcademicYear {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  created_at: string;
}

export interface Term {
  id: string;
  academic_year_id: string;
  name: string;
  term_number: number;
  start_date: string;
  end_date: string;
  is_current: boolean;
}

export interface Class {
  id: string;
  name: string;
  level: number | null;
  description: string | null;
}

export interface Stream {
  id: string;
  class_id: string;
  name: string;
}

export interface Subject {
  id: string;
  code: string;
  name: string;
  description: string | null;
  department_id: string | null;
}

export interface Department {
  id: string;
  name: string;
  description: string | null;
}

export interface Timetable {
  id: string;
  name: string;
  academic_year_id: string;
  is_active: boolean;
  entries: TimetableEntry[];
  created_at: string;
}

export interface TimetableEntry {
  id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  subject_id: string;
  teacher_id: string;
  class_id: string;
  room: string | null;
}

export interface AttendanceRecord {
  id: string;
  student_id: string;
  class_id: string;
  recorded_by: string;
  attendance_date: string;
  status: 'present' | 'absent' | 'late' | 'excused';
  remarks: string | null;
}

export interface Assessment {
  id: string;
  subject_id: string;
  teacher_id: string;
  class_id: string;
  term_id: string | null;
  name: string;
  assessment_type: 'exam' | 'test' | 'quiz' | 'assignment' | 'project';
  max_score: number;
  weight: number;
  date_administered: string | null;
}

export interface Mark {
  id: string;
  assessment_id: string;
  student_id: string;
  score: number;
  grade: string | null;
  remarks: string | null;
}

export interface LessonPlan {
  id: string;
  teacher_id: string;
  subject_id: string;
  class_id: string;
  topic: string;
  objectives: string | null;
  activities: string | null;
  teaching_resources: string | null;
  assessment: string | null;
  homework: string | null;
  completion_status: 'planned' | 'in_progress' | 'completed';
  week_number: number | null;
  term_number: number | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface DashboardAdmin {
  total_students: number;
  total_teachers: number;
  total_classes: number;
  attendance_today: {
    present: number;
    total: number;
    percentage: number;
  };
  recent_assessments: number;
}

export interface DashboardTeacher {
  today_timetable: {
    subject_id: string;
    class_id: string;
    start: string;
    end: string;
    room: string | null;
  }[];
  pending_attendance: string[];
  lessons_this_week: number;
}

export interface Notification {
  id: string;
  school_id: string;
  recipient_id: string;
  title: string;
  body: string;
  channel: string;
  priority: 'normal' | 'high' | 'urgent';
  read: boolean;
  metadata_?: Record<string, any> | null;
  sent_at: string | null;
  read_at: string | null;
  created_at: string;
}
