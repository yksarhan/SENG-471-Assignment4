import threading
import time
from datetime import datetime, date
from typing import Dict, Optional

class ActivityMetrics:
    def __init__(self, steps: int = 0, active_minutes: int = 0, calories: float = 0.0):
        self.steps = steps
        self.active_minutes = active_minutes
        self.calories = calories

    def add(self, steps: int = 0, active_minutes: int = 0, calories: float = 0.0):
        self.steps += steps
        self.active_minutes += active_minutes
        self.calories += calories

    def to_dict(self):
        return {"steps": self.steps, "active_minutes": self.active_minutes, "calories": self.calories}


class ActivityTracker:
    def __init__(self, poll_interval_seconds: int = 300):
        self.poll_interval_seconds = poll_interval_seconds
        self._history: Dict[str, ActivityMetrics] = {}
        self._lock = threading.Lock()
        self._poll_timer: Optional[threading.Timer] = None
        self._running = False

    def _day_key(self, at: Optional[datetime] = None) -> str:
        at = at or datetime.now()
        return at.date().isoformat()

    def _get_or_create_metrics(self, day_key: str) -> ActivityMetrics:
        if day_key not in self._history:
            self._history[day_key] = ActivityMetrics()
        return self._history[day_key]

    def add_activity(self, steps: int = 0, active_minutes: int = 0, calories: float = 0.0, when: Optional[datetime] = None):
        key = self._day_key(when)
        with self._lock:
            metrics = self._get_or_create_metrics(key)
            metrics.add(steps=steps, active_minutes=active_minutes, calories=calories)

    def get_today_metrics(self) -> Dict[str, float]:
        key = self._day_key()
        with self._lock:
            metrics = self._get_or_create_metrics(key)
            return metrics.to_dict()

    def get_metrics_for_day(self, day: date) -> Dict[str, float]:
        key = day.isoformat()
        with self._lock:
            if key not in self._history:
                return {"steps": 0, "active_minutes": 0, "calories": 0.0}
            return self._history[key].to_dict()

    def get_history(self) -> Dict[str, Dict[str, float]]:
        with self._lock:
            return {k: v.to_dict() for k, v in self._history.items()}

    def _poll_update(self, callback):
        if not self._running:
            return
        try:
            callback(self.get_today_metrics())
        finally:
            self._poll_timer = threading.Timer(self.poll_interval_seconds, self._poll_update, args=(callback,))
            self._poll_timer.daemon = True
            self._poll_timer.start()

    def start_polling(self, callback):
        if self._running:
            return
        self._running = True
        self._poll_update(callback)

    def stop_polling(self):
        self._running = False
        if self._poll_timer:
            self._poll_timer.cancel()
            self._poll_timer = None


def format_dashboard(metrics: Dict[str, float]) -> str:
    return (
        f"Daily Activity (updated {datetime.now().strftime('%H:%M:%S')}):\n"
        f"- Steps: {metrics.get('steps', 0)}\n"
        f"- Active Minutes: {metrics.get('active_minutes', 0)}\n"
        f"- Estimated Calories: {metrics.get('calories', 0.0):.2f}\n"
    )


if __name__ == "__main__":
    tracker = ActivityTracker(poll_interval_seconds=300)  # 5 min
    tracker.add_activity(steps=1200, active_minutes=12, calories=45.0)
    tracker.add_activity(steps=600, active_minutes=8, calories=25.0)
    print(format_dashboard(tracker.get_today_metrics()))

    def dashboard_update(data):
        print("Polling update:")
        print(format_dashboard(data))

    tracker.start_polling(dashboard_update)
    try:
        time.sleep(2)  # demo run (replace with app loop)
    finally:
        tracker.stop_polling()

    print("History:", tracker.get_history())