from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal


GoalType = Literal["lose_weight", "improve_endurance", "build_strength", "general_fitness"]
Intensity = Literal["low", "moderate", "high"]


@dataclass(frozen=True)
class WorkoutSuggestion:
	exercise_type: str
	duration_minutes: int
	intensity: Intensity
	description: str


@dataclass(frozen=True)
class WorkoutLog:
	workout_type: str
	duration_minutes: int
	intensity: Intensity
	logged_on: date


@dataclass
class UserProfile:
	user_id: str
	goal: GoalType
	activity_history: list[WorkoutLog] = field(default_factory=list)
	suggestions_last_refreshed_on: date | None = None

	def set_goal(self, goal: GoalType) -> None:
		self.goal = goal

	def log_workout(self, log: WorkoutLog) -> None:
		self.activity_history.append(log)


class WorkoutRecommendationEngine:
	"""Generates goal-aligned workout suggestions that adapt with user data."""

	_WEEK = timedelta(days=7)

	_GOAL_BASE_SUGGESTIONS: dict[GoalType, list[WorkoutSuggestion]] = {
		"lose_weight": [
			WorkoutSuggestion("Brisk Walk", 30, "moderate", "Steady pace walk to support calorie burn."),
			WorkoutSuggestion("Cycling", 35, "moderate", "Low-impact cardio for sustained fat loss."),
			WorkoutSuggestion("HIIT Circuit", 20, "high", "Short, intense intervals to boost metabolism."),
		],
		"improve_endurance": [
			WorkoutSuggestion("Jogging", 35, "moderate", "Build aerobic capacity with continuous cardio."),
			WorkoutSuggestion("Rowing", 30, "moderate", "Full-body endurance training."),
			WorkoutSuggestion("Tempo Run", 25, "high", "Increase lactate threshold and stamina."),
		],
		"build_strength": [
			WorkoutSuggestion("Bodyweight Strength", 30, "moderate", "Push, pull, and squat patterns for strength."),
			WorkoutSuggestion("Dumbbell Training", 40, "high", "Progressive overload for muscle and strength gains."),
			WorkoutSuggestion("Core Stability", 20, "moderate", "Improve trunk strength and movement control."),
		],
		"general_fitness": [
			WorkoutSuggestion("Mixed Cardio", 25, "moderate", "Balanced cardio session for heart health."),
			WorkoutSuggestion("Mobility + Stretch", 20, "low", "Improve flexibility and recovery."),
			WorkoutSuggestion("Circuit Training", 30, "moderate", "Combine cardio and strength in one session."),
		],
	}

	@classmethod
	def generate_suggestions(cls, user: UserProfile, today: date | None = None) -> list[WorkoutSuggestion]:
		today = today or date.today()

		if cls._must_refresh(user, today):
			user.suggestions_last_refreshed_on = today

		suggestions = [
			cls._adjust_for_history(suggestion, user.activity_history)
			for suggestion in cls._GOAL_BASE_SUGGESTIONS[user.goal]
		]
		return suggestions

	@classmethod
	def _must_refresh(cls, user: UserProfile, today: date) -> bool:
		if user.suggestions_last_refreshed_on is None:
			return True
		return (today - user.suggestions_last_refreshed_on) >= cls._WEEK

	@staticmethod
	def _adjust_for_history(
		suggestion: WorkoutSuggestion,
		history: list[WorkoutLog],
	) -> WorkoutSuggestion:
		if not history:
			return suggestion

		recent = sorted(history, key=lambda w: w.logged_on, reverse=True)[:8]
		avg_duration = sum(w.duration_minutes for w in recent) / len(recent)

		# Keep recommendations realistic by nudging duration toward recent capacity.
		adjusted_duration = suggestion.duration_minutes
		if avg_duration >= suggestion.duration_minutes + 10:
			adjusted_duration = min(suggestion.duration_minutes + 5, 60)
		elif avg_duration <= suggestion.duration_minutes - 10:
			adjusted_duration = max(suggestion.duration_minutes - 5, 15)

		intensity_counts = {"low": 0, "moderate": 0, "high": 0}
		for workout in recent:
			intensity_counts[workout.intensity] += 1

		dominant_intensity = max(intensity_counts, key=intensity_counts.get)
		adjusted_intensity: Intensity = suggestion.intensity

		# If user consistently trains hard, include one more challenging recommendation.
		if dominant_intensity == "high" and suggestion.intensity == "moderate":
			adjusted_intensity = "high"
		# If user has mostly lower intensity history, keep suggestions approachable.
		elif dominant_intensity == "low" and suggestion.intensity == "high":
			adjusted_intensity = "moderate"

		return WorkoutSuggestion(
			exercise_type=suggestion.exercise_type,
			duration_minutes=adjusted_duration,
			intensity=adjusted_intensity,
			description=suggestion.description,
		)


if __name__ == "__main__":
	profile = UserProfile(user_id="u-100", goal="improve_endurance")
	profile.log_workout(WorkoutLog("Jogging", 30, "moderate", date.today() - timedelta(days=2)))
	profile.log_workout(WorkoutLog("Cycling", 40, "high", date.today() - timedelta(days=1)))

	for item in WorkoutRecommendationEngine.generate_suggestions(profile):
		print(
			f"{item.exercise_type} | {item.duration_minutes} min | {item.intensity} | {item.description}"
		)
