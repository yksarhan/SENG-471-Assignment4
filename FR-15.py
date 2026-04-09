from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass(frozen=True)
class DailyHealthRecord:
	recorded_on: date
	activity_minutes: int
	sleep_hours: float
	steps: int
	resting_heart_rate: int


@dataclass(frozen=True)
class GoalTargets:
	daily_activity_minutes: int
	daily_sleep_hours: float
	daily_steps: int
	weekly_activity_minutes: int


@dataclass(frozen=True)
class CircularGoalGraph:
	metric: str
	current: float
	target: float
	percent_complete: float


@dataclass(frozen=True)
class TrendPoint:
	day: date
	value: float


@dataclass(frozen=True)
class WeeklySummary:
	week_start: date
	total_activity_minutes: int
	average_sleep_hours: float
	average_resting_heart_rate: float
	goal_achievement_percent: float


@dataclass(frozen=True)
class DashboardView:
	circular_goal_graphs: list[CircularGoalGraph]
	activity_trend: list[TrendPoint]
	health_marker_trend: list[TrendPoint]
	goal_progress_trend: list[TrendPoint]
	weekly_summary: WeeklySummary
	interactive_daily_breakdown_available: bool = True


class DashboardAnalyticsService:
	"""
	FR-15 dashboard analytics engine.
	- Renders dashboard once at least one day of records exists.
	- Provides circular goal graphs for multiple metrics.
	- Produces weekly trend lines for activity and health markers.
	- Supports interactive daily breakdown lookups.
	- Keeps visual data consistent with health history records.
	"""

	def __init__(self, goal_targets: GoalTargets) -> None:
		self._goal_targets = goal_targets
		self._history: list[DailyHealthRecord] = []

	def log_daily_record(self, record: DailyHealthRecord) -> None:
		self._history = [r for r in self._history if r.recorded_on != record.recorded_on]
		self._history.append(record)
		self._history.sort(key=lambda r: r.recorded_on)

	def get_health_history(self) -> list[DailyHealthRecord]:
		return list(self._history)

	def render_dashboard(self, today: date | None = None) -> DashboardView:
		if not self._history:
			raise ValueError("Dashboard requires at least 1 day of recorded activity.")

		today = today or self._history[-1].recorded_on
		weekly_records = self._get_weekly_records(today)
		if not weekly_records:
			weekly_records = [self._history[-1]]

		latest = weekly_records[-1]
		circular_graphs = self._build_circular_goal_graphs(latest, weekly_records)

		activity_trend = [TrendPoint(day=r.recorded_on, value=float(r.activity_minutes)) for r in weekly_records]
		health_marker_trend = [TrendPoint(day=r.recorded_on, value=float(r.resting_heart_rate)) for r in weekly_records]
		goal_progress_trend = [
			TrendPoint(day=r.recorded_on, value=self._daily_goal_percent(r))
			for r in weekly_records
		]

		weekly_summary = self._build_weekly_summary(today, weekly_records)

		return DashboardView(
			circular_goal_graphs=circular_graphs,
			activity_trend=activity_trend,
			health_marker_trend=health_marker_trend,
			goal_progress_trend=goal_progress_trend,
			weekly_summary=weekly_summary,
			interactive_daily_breakdown_available=True,
		)

	def get_daily_breakdown(self, day: date) -> dict[str, float | int | str]:
		"""Interactive-style drilldown payload for a selected day in the chart."""
		record = next((r for r in self._history if r.recorded_on == day), None)
		if record is None:
			raise ValueError("No record found for the selected day.")

		return {
			"date": record.recorded_on.isoformat(),
			"activity_minutes": record.activity_minutes,
			"sleep_hours": record.sleep_hours,
			"steps": record.steps,
			"resting_heart_rate": record.resting_heart_rate,
			"daily_goal_achievement_percent": round(self._daily_goal_percent(record), 2),
		}

	def _build_circular_goal_graphs(
		self,
		latest: DailyHealthRecord,
		weekly_records: list[DailyHealthRecord],
	) -> list[CircularGoalGraph]:
		weekly_activity_total = sum(r.activity_minutes for r in weekly_records)

		return [
			CircularGoalGraph(
				metric="Daily Activity Minutes",
				current=float(latest.activity_minutes),
				target=float(self._goal_targets.daily_activity_minutes),
				percent_complete=_to_percent(latest.activity_minutes, self._goal_targets.daily_activity_minutes),
			),
			CircularGoalGraph(
				metric="Daily Sleep Hours",
				current=float(latest.sleep_hours),
				target=float(self._goal_targets.daily_sleep_hours),
				percent_complete=_to_percent(latest.sleep_hours, self._goal_targets.daily_sleep_hours),
			),
			CircularGoalGraph(
				metric="Weekly Activity Minutes",
				current=float(weekly_activity_total),
				target=float(self._goal_targets.weekly_activity_minutes),
				percent_complete=_to_percent(weekly_activity_total, self._goal_targets.weekly_activity_minutes),
			),
		]

	def _build_weekly_summary(self, today: date, weekly_records: list[DailyHealthRecord]) -> WeeklySummary:
		week_start = today - timedelta(days=6)
		total_activity = sum(r.activity_minutes for r in weekly_records)
		avg_sleep = sum(r.sleep_hours for r in weekly_records) / len(weekly_records)
		avg_rhr = sum(r.resting_heart_rate for r in weekly_records) / len(weekly_records)
		avg_goal_achievement = sum(self._daily_goal_percent(r) for r in weekly_records) / len(weekly_records)

		return WeeklySummary(
			week_start=week_start,
			total_activity_minutes=total_activity,
			average_sleep_hours=round(avg_sleep, 2),
			average_resting_heart_rate=round(avg_rhr, 2),
			goal_achievement_percent=round(avg_goal_achievement, 2),
		)

	def _daily_goal_percent(self, record: DailyHealthRecord) -> float:
		activity_pct = _to_percent(record.activity_minutes, self._goal_targets.daily_activity_minutes)
		sleep_pct = _to_percent(record.sleep_hours, self._goal_targets.daily_sleep_hours)
		steps_pct = _to_percent(record.steps, self._goal_targets.daily_steps)
		return (activity_pct + sleep_pct + steps_pct) / 3

	def _get_weekly_records(self, today: date) -> list[DailyHealthRecord]:
		start = today - timedelta(days=6)
		return [r for r in self._history if start <= r.recorded_on <= today]


def _to_percent(current: float, target: float) -> float:
	if target <= 0:
		return 0.0
	return round(min((current / target) * 100, 100.0), 2)


if __name__ == "__main__":
	service = DashboardAnalyticsService(
		GoalTargets(
			daily_activity_minutes=45,
			daily_sleep_hours=8.0,
			daily_steps=8000,
			weekly_activity_minutes=300,
		)
	)

	today = date.today()
	service.log_daily_record(DailyHealthRecord(today - timedelta(days=2), 35, 7.2, 6200, 72))
	service.log_daily_record(DailyHealthRecord(today - timedelta(days=1), 50, 8.1, 9100, 70))
	service.log_daily_record(DailyHealthRecord(today, 42, 7.8, 7800, 69))

	dashboard = service.render_dashboard(today=today)
	drilldown = service.get_daily_breakdown(today)

	print(f"Circular graphs: {len(dashboard.circular_goal_graphs)}")
	print(f"Activity trend points: {len(dashboard.activity_trend)}")
	print(f"Weekly activity total: {dashboard.weekly_summary.total_activity_minutes}")
	print(f"Drilldown date: {drilldown['date']}")
