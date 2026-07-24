import { useEffect, useState } from 'react';
import api from '@/services/api';
import toast from 'react-hot-toast';
import { Calendar, ChevronLeft, ChevronRight, Clock, MapPin, Download } from 'lucide-react';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const HOURS = Array.from({ length: 11 }, (_, i) => i + 7); // 7 AM to 5 PM

export default function CalendarView() {
  const [events, setEvents] = useState<any[]>([]);
  const [weekStart, setWeekStart] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - d.getDay() + 1);
    return d.toISOString().slice(0, 10);
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get('/calendar/my', { params: { week_start: weekStart } })
      .then(({ data }) => setEvents(data.events))
      .catch(() => toast.error('Failed to load calendar'))
      .finally(() => setLoading(false));
  }, [weekStart]);

  const prevWeek = () => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() - 7);
    setWeekStart(d.toISOString().slice(0, 10));
  };

  const nextWeek = () => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + 7);
    setWeekStart(d.toISOString().slice(0, 10));
  };

  const downloadICS = () => {
    window.open('/api/v1/calendar/my.ics', '_blank');
  };

  const getEventsForDayHour = (day: number, hour: number) => {
    return events.filter(e => {
      const evtDate = new Date(e.start);
      const evtDay = evtDate.getDay() === 0 ? 6 : evtDate.getDay() - 1;
      const evtHour = evtDate.getHours();
      return evtDay === day && evtHour === hour;
    });
  };

  const formatWeekRange = () => {
    const start = new Date(weekStart);
    const end = new Date(start);
    end.setDate(end.getDate() + 4); // Fri
    return `${start.toLocaleDateString('en-KE', { month: 'short', day: 'numeric' })} – ${end.toLocaleDateString('en-KE', { month: 'short', day: 'numeric', year: 'numeric' })}`;
  };

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Calendar className="h-6 w-6 text-brand-600" /> Calendar
        </h2>
        <button onClick={downloadICS} className="btn-secondary gap-1 text-xs">
          <Download className="h-3 w-3" /> Subscribe (ICS)
        </button>
      </div>

      {/* Week nav */}
      <div className="card mb-4">
        <div className="flex items-center justify-between">
          <button onClick={prevWeek} className="btn-secondary text-xs gap-1">
            <ChevronLeft className="h-3 w-3" /> Previous
          </button>
          <span className="font-semibold text-sm">{formatWeekRange()}</span>
          <button onClick={nextWeek} className="btn-secondary text-xs gap-1">
            Next <ChevronRight className="h-3 w-3" />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <div className="min-w-[700px]">
            {/* Header row */}
            <div className="grid grid-cols-8 border-b border-gray-200">
              <div className="p-2 text-xs font-semibold text-gray-400 text-center">Time</div>
              {DAYS.slice(0, 5).map(day => (
                <div key={day} className="p-2 text-xs font-semibold text-gray-600 text-center">{day}</div>
              ))}
            </div>

            {/* Time grid */}
            {HOURS.map(hour => (
              <div key={hour} className="grid grid-cols-8 border-b border-gray-100 min-h-[60px]">
                <div className="p-2 text-xs text-gray-400 text-center font-mono">
                  {String(hour).padStart(2, '0')}:00
                </div>
                {[0, 1, 2, 3, 4].map(day => {
                  const dayEvents = getEventsForDayHour(day, hour);
                  return (
                    <div key={day} className="p-1 border-l border-gray-50">
                      {dayEvents.map(evt => (
                        <div key={evt.id} className="rounded bg-brand-100 border border-brand-200 p-1.5 mb-1 text-xs">
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3 text-brand-600" />
                            <span className="font-medium text-brand-800 truncate">{evt.title}</span>
                          </div>
                          {evt.room && (
                            <div className="flex items-center gap-1 text-brand-500 mt-0.5">
                              <MapPin className="h-3 w-3" />
                              <span>Room {evt.room}</span>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  );
                })}
              </div>
            ))}

            {events.length === 0 && (
              <div className="text-center py-8 text-gray-400">
                <Calendar className="mx-auto h-8 w-8 mb-2" />
                <p className="text-sm">No lessons scheduled this week.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
