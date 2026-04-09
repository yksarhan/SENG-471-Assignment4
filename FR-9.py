from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Literal
from uuid import uuid4


Frequency = Literal["daily", "twice_daily", "weekly"]
DoseStatus = Literal["scheduled", "notified", "taken", "missed"]


@dataclass
class Medication:
	medication_id: str
	user_id: str
	name: str
	dosage: str
	frequency: Frequency
	scheduled_time: time
	active: bool = True


@dataclass
class DoseEvent:
	event_id: str
	medication_id: str
	user_id: str
	scheduled_for: datetime
	status: DoseStatus = "scheduled"
	notification_sent_at: datetime | None = None
	taken_at: datetime | None = None


@dataclass
class Notification:
	notification_id: str
	event_id: str
	user_id: str
	title: str
	message: str
	created_at: datetime
	action: str = "mark_taken"


class PushNotificationService:
	"""Simple in-memory notifier used to model push notifications."""

	def __init__(self) -> None:
		self.sent_notifications: list[Notification] = []

	def send(self, notification: Notification) -> None:
		self.sent_notifications.append(notification)


@dataclass
class MedicationHistoryRecord:
	medication_name: str
	dosage: str
	scheduled_for: datetime
	status: DoseStatus
	notification_sent_at: datetime | None
	taken_at: datetime | None


class MedicationReminderSystem:
	"""
	FR-9 Medication logging + reminder scheduling.
	Also provides history records suitable for health record integration (FR-12 linkage).
	"""

	MISSED_WINDOW = timedelta(minutes=30)

	def __init__(self, notifier: PushNotificationService | None = None) -> None:
		self._notifier = notifier or PushNotificationService()
		self._medications: dict[str, Medication] = {}
		self._events: dict[str, DoseEvent] = {}

	# --- Medication CRUD ---
	def add_medication(
		self,
		*,
		user_id: str,
		name: str,
		dosage: str,
		frequency: Frequency,
		scheduled_time: time,
		start_date: date | None = None,
	) -> Medication:
		medication = Medication(
			medication_id=str(uuid4()),
			user_id=user_id,
			name=name,
			dosage=dosage,
			frequency=frequency,
			scheduled_time=scheduled_time,
		)
		self._medications[medication.medication_id] = medication
		self._seed_events(medication, start_date=start_date)
		return medication

	def edit_medication(
		self,
		medication_id: str,
		*,
		name: str | None = None,
		dosage: str | None = None,
		frequency: Frequency | None = None,
		scheduled_time: time | None = None,
		from_date: date | None = None,
	) -> Medication:
		medication = self._get_medication_or_raise(medication_id)
		if name is not None:
			medication.name = name
		if dosage is not None:
			medication.dosage = dosage
		if frequency is not None:
			medication.frequency = frequency
		if scheduled_time is not None:
			medication.scheduled_time = scheduled_time

		# Regenerate only future events to preserve existing history.
		cutoff = datetime.combine(from_date or date.today(), time.min)
		for event in list(self._events.values()):
			if event.medication_id == medication_id and event.scheduled_for >= cutoff and event.status == "scheduled":
				del self._events[event.event_id]

		self._seed_events(medication, start_date=from_date)
		return medication

	def delete_medication(self, medication_id: str) -> None:
		medication = self._get_medication_or_raise(medication_id)
		medication.active = False

	def list_medications(self, user_id: str) -> list[Medication]:
		return [m for m in self._medications.values() if m.user_id == user_id and m.active]

	# --- Reminder Scheduling + Delivery ---
	def process_due_reminders(self, now: datetime | None = None) -> list[Notification]:
		now = now or datetime.now()
		notifications: list[Notification] = []

		for event in self._events.values():
			medication = self._medications.get(event.medication_id)
			if medication is None or not medication.active:
				continue

			if event.status == "scheduled" and now >= event.scheduled_for:
				note = Notification(
					notification_id=str(uuid4()),
					event_id=event.event_id,
					user_id=event.user_id,
					title="Medication Reminder",
					message=f"Time to take {medication.name} ({medication.dosage}).",
					created_at=now,
				)
				self._notifier.send(note)
				notifications.append(note)
				event.status = "notified"
				event.notification_sent_at = now

			if event.status in {"scheduled", "notified"} and now >= event.scheduled_for + self.MISSED_WINDOW:
				event.status = "missed"

		return notifications

	def mark_dose_taken_from_notification(
		self,
		*,
		notification_id: str,
		taken_at: datetime | None = None,
	) -> DoseEvent:
		note = next((n for n in self._notifier.sent_notifications if n.notification_id == notification_id), None)
		if note is None:
			raise ValueError("Notification not found.")

		event = self._events.get(note.event_id)
		if event is None:
			raise ValueError("Dose event not found.")

		event.status = "taken"
		event.taken_at = taken_at or datetime.now()
		return event

	# --- Health History (FR-12 linkage) ---
	def get_medication_history(self, user_id: str) -> list[MedicationHistoryRecord]:
		records: list[MedicationHistoryRecord] = []
		for event in sorted(self._events.values(), key=lambda e: e.scheduled_for):
			if event.user_id != user_id:
				continue
			medication = self._medications.get(event.medication_id)
			if medication is None:
				continue

			records.append(
				MedicationHistoryRecord(
					medication_name=medication.name,
					dosage=medication.dosage,
					scheduled_for=event.scheduled_for,
					status=event.status,
					notification_sent_at=event.notification_sent_at,
					taken_at=event.taken_at,
				)
			)
		return records

	# --- Internal helpers ---
	def _seed_events(self, medication: Medication, start_date: date | None = None, days: int = 14) -> None:
		today = start_date or date.today()

		for offset in range(days):
			day = today + timedelta(days=offset)

			if medication.frequency == "daily":
				times = [medication.scheduled_time]
			elif medication.frequency == "twice_daily":
				second = (datetime.combine(day, medication.scheduled_time) + timedelta(hours=12)).time()
				times = [medication.scheduled_time, second]
			else:  # weekly
				# Only schedule on the weekday that matches start_date.
				if day.weekday() != today.weekday():
					continue
				times = [medication.scheduled_time]

			for dose_time in times:
				scheduled_for = datetime.combine(day, dose_time)
				event = DoseEvent(
					event_id=str(uuid4()),
					medication_id=medication.medication_id,
					user_id=medication.user_id,
					scheduled_for=scheduled_for,
				)
				self._events[event.event_id] = event

	def _get_medication_or_raise(self, medication_id: str) -> Medication:
		medication = self._medications.get(medication_id)
		if medication is None:
			raise ValueError("Medication not found.")
		return medication


if __name__ == "__main__":
	# Minimal demonstration.
	system = MedicationReminderSystem()
	med = system.add_medication(
		user_id="u-42",
		name="Metformin",
		dosage="500mg",
		frequency="daily",
		scheduled_time=time(9, 0),
	)

	now = datetime.combine(date.today(), time(9, 0))
	reminders = system.process_due_reminders(now)
	if reminders:
		system.mark_dose_taken_from_notification(notification_id=reminders[0].notification_id, taken_at=now)

	history = system.get_medication_history("u-42")
	print(f"Active medications: {len(system.list_medications('u-42'))}")
	print(f"History records: {len(history)}")
