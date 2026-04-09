import datetime
import uuid
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class HealthGoal:
    goal_id: str
    metric: str
    target: float
    unit: str
    progress: float = 0.0
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = field(default_factory=datetime.datetime.now)

    def update_progress(self, amount: float):
        self.progress += amount
        self.updated_at = datetime.datetime.now()

    def progress_percent(self) -> float:
        if self.target <= 0:
            return 100.0
        return min(100.0, (self.progress / self.target) * 100.0)

    def is_completed(self) -> bool:
        return self.progress >= self.target

    def progress_bar(self, width: int = 30) -> str:
        pct = self.progress_percent()
        filled = int(width * pct / 100)
        empty = width - filled
        bar = "[" + "#" * filled + "-" * empty + "]"
        status = "COMPLETED" if self.is_completed() else "in progress"
        return f"{bar} {pct:6.2f}% ({status})"

    def display(self) -> str:
        marker = "✅" if self.is_completed() else "⌛"
        return (
            f"{marker} {self.metric} goal: {self.progress:.1f}/{self.target:.1f} {self.unit}\n"
            f"    {self.progress_bar()}"
        )


class GoalManager:
    def __init__(self):
        self.goals: Dict[str, HealthGoal] = {}

    def create_goal(self, metric: str, target: float, unit: str) -> str:
        goal_id = str(uuid.uuid4())
        goal = HealthGoal(goal_id=goal_id, metric=metric, target=target, unit=unit)
        self.goals[goal_id] = goal
        return goal_id

    def edit_goal(self, goal_id: str, target: float = None, unit: str = None):
        goal = self.goals.get(goal_id)
        if not goal:
            raise ValueError("Goal not found.")
        if target is not None:
            goal.target = target
        if unit is not None:
            goal.unit = unit
        goal.updated_at = datetime.datetime.now()

    def delete_goal(self, goal_id: str):
        if goal_id in self.goals:
            del self.goals[goal_id]
        else:
            raise ValueError("Goal not found.")

    def record_activity(self, metric: str, amount: float):
        updated = []
        for goal in self.goals.values():
            if goal.metric.lower() == metric.lower():
                goal.update_progress(amount)
                updated.append(goal)
        return updated

    def dashboard(self) -> str:
        if not self.goals:
            return "No goals created yet."
        lines = ["=== Goals Dashboard ==="]
        by_metric = {}
        for goal in self.goals.values():
            by_metric.setdefault(goal.metric, []).append(goal)

        for metric, goals in by_metric.items():
            lines.append(f"--- {metric.upper()} ---")
            for g in goals:
                lines.append(g.display())
        return "\n".join(lines)

    def get_goal(self, goal_id: str) -> HealthGoal:
        return self.goals[goal_id]


def _demo():
    manager = GoalManager()

    # acceptance: at least one goal per metric
    manager.create_goal("steps", 10000, "steps")
    manager.create_goal("calories", 2500, "kcal")
    manager.create_goal("exercise_minutes", 150, "min")

    print("Initial dashboard")
    print(manager.dashboard())
    print()

    # log activity and update indicators real-time
    activities = [
        ("steps", 3000),
        ("exercise_minutes", 20),
        ("calories", 500),
        ("steps", 4500),
        ("exercise_minutes", 45),
        ("calories", 1200),
        ("steps", 2800),  # should complete steps
        ("exercise_minutes", 85),
    ]
    for metric, amount in activities:
        updated_goals = manager.record_activity(metric, amount)
        print(f"Recorded {amount} {metric}")
        for g in updated_goals:
            state = "COMPLETED" if g.is_completed() else "in progress"
            print(f"  - {g.metric}: {g.progress:.1f}/{g.target:.1f} {g.unit} ({state})")
        print()

    print("Dashboard after activity logging")
    print(manager.dashboard())


if __name__ == "__main__":
    _demo()