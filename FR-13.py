from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import uuid4


DialTarget = Literal["emergency_service", "contact"]


@dataclass(frozen=True)
class EmergencyContact:
	contact_id: str
	name: str
	phone_number: str


@dataclass
class EmergencyProfile:
	user_id: str
	emergency_service_number: str = "911"
	contacts: list[EmergencyContact] = field(default_factory=list)


@dataclass(frozen=True)
class DialRequest:
	user_id: str
	target_type: DialTarget
	phone_number: str
	initiated_at: datetime
	taps_used: int


@dataclass(frozen=True)
class NotificationEvent:
	user_id: str
	contact_id: str
	phone_number: str
	message: str
	sent_at: datetime


@dataclass(frozen=True)
class SOSResult:
	dial_request: DialRequest
	notifications: list[NotificationEvent]


class EmergencyFeatureService:
	"""
	FR-13 emergency/safety functionality:
	- SOS is reachable in <= 2 taps from any main screen
	- Manage up to 3 emergency contacts
	- Quick dial emergency service or configured contact
	- SOS can notify all saved emergency contacts
	"""

	MAX_CONTACTS = 3

	# Each main screen maps to minimum taps needed to reach SOS.
	_SOS_TAP_MAP: dict[str, int] = {
		"home": 1,
		"dashboard": 1,
		"activity": 2,
		"profile": 2,
		"medication": 2,
		"nutrition": 2,
		"settings": 1,
	}

	def __init__(self) -> None:
		self._profiles: dict[str, EmergencyProfile] = {}

	# --- Accessibility ---
	def is_sos_reachable_within_two_taps(self, from_screen: str) -> bool:
		taps = self._SOS_TAP_MAP.get(from_screen.lower())
		if taps is None:
			# Unknown screens are considered non-compliant until mapped explicitly.
			return False
		return taps <= 2

	def is_sos_prominently_accessible(self, from_screen: str) -> bool:
		# Prominence is modeled as one-tap access.
		taps = self._SOS_TAP_MAP.get(from_screen.lower())
		return taps == 1

	# --- Profile / Contact Management ---
	def get_or_create_profile(self, user_id: str) -> EmergencyProfile:
		if user_id not in self._profiles:
			self._profiles[user_id] = EmergencyProfile(user_id=user_id)
		return self._profiles[user_id]

	def set_emergency_service_number(self, user_id: str, number: str) -> None:
		profile = self.get_or_create_profile(user_id)
		profile.emergency_service_number = number

	def add_emergency_contact(self, user_id: str, name: str, phone_number: str) -> EmergencyContact:
		profile = self.get_or_create_profile(user_id)
		if len(profile.contacts) >= self.MAX_CONTACTS:
			raise ValueError("A maximum of 3 emergency contacts is allowed.")

		contact = EmergencyContact(contact_id=str(uuid4()), name=name, phone_number=phone_number)
		profile.contacts.append(contact)
		return contact

	def edit_emergency_contact(
		self,
		user_id: str,
		contact_id: str,
		*,
		name: str | None = None,
		phone_number: str | None = None,
	) -> EmergencyContact:
		profile = self.get_or_create_profile(user_id)
		index = self._find_contact_index(profile, contact_id)
		current = profile.contacts[index]

		updated = EmergencyContact(
			contact_id=current.contact_id,
			name=name if name is not None else current.name,
			phone_number=phone_number if phone_number is not None else current.phone_number,
		)
		profile.contacts[index] = updated
		return updated

	def delete_emergency_contact(self, user_id: str, contact_id: str) -> None:
		profile = self.get_or_create_profile(user_id)
		index = self._find_contact_index(profile, contact_id)
		del profile.contacts[index]

	def list_emergency_contacts(self, user_id: str) -> list[EmergencyContact]:
		return list(self.get_or_create_profile(user_id).contacts)

	# --- Quick Dial / SOS ---
	def quick_dial_emergency_service(self, user_id: str, taps_used: int = 1) -> DialRequest:
		if taps_used > 2:
			raise ValueError("Quick dial must be completable within 2 taps.")
		profile = self.get_or_create_profile(user_id)
		return DialRequest(
			user_id=user_id,
			target_type="emergency_service",
			phone_number=profile.emergency_service_number,
			initiated_at=datetime.now(),
			taps_used=taps_used,
		)

	def quick_dial_contact(self, user_id: str, contact_id: str, taps_used: int = 2) -> DialRequest:
		if taps_used > 2:
			raise ValueError("Quick dial must be completable within 2 taps.")
		profile = self.get_or_create_profile(user_id)
		index = self._find_contact_index(profile, contact_id)
		contact = profile.contacts[index]
		return DialRequest(
			user_id=user_id,
			target_type="contact",
			phone_number=contact.phone_number,
			initiated_at=datetime.now(),
			taps_used=taps_used,
		)

	def activate_sos(self, user_id: str, from_screen: str = "home") -> SOSResult:
		if not self.is_sos_reachable_within_two_taps(from_screen):
			raise ValueError("SOS is not reachable within 2 taps from this screen.")

		profile = self.get_or_create_profile(user_id)

		# Immediate call defaults to emergency services for reliability.
		dial_request = DialRequest(
			user_id=user_id,
			target_type="emergency_service",
			phone_number=profile.emergency_service_number,
			initiated_at=datetime.now(),
			taps_used=self._SOS_TAP_MAP[from_screen.lower()],
		)

		notifications: list[NotificationEvent] = []
		for contact in profile.contacts:
			notifications.append(
				NotificationEvent(
					user_id=user_id,
					contact_id=contact.contact_id,
					phone_number=contact.phone_number,
					message="SOS activated. Please check on the user immediately.",
					sent_at=datetime.now(),
				)
			)

		return SOSResult(dial_request=dial_request, notifications=notifications)

	# --- Internal ---
	@staticmethod
	def _find_contact_index(profile: EmergencyProfile, contact_id: str) -> int:
		for index, contact in enumerate(profile.contacts):
			if contact.contact_id == contact_id:
				return index
		raise ValueError("Emergency contact not found.")


if __name__ == "__main__":
	service = EmergencyFeatureService()
	user = "user-1"

	c1 = service.add_emergency_contact(user, "Alex", "+1-555-1000")
	service.add_emergency_contact(user, "Sam", "+1-555-2000")

	assert service.is_sos_reachable_within_two_taps("home")
	assert service.is_sos_reachable_within_two_taps("activity")

	dial = service.quick_dial_contact(user, c1.contact_id)
	sos = service.activate_sos(user, from_screen="home")

	print(f"Quick dial -> {dial.phone_number}")
	print(f"SOS dial -> {sos.dial_request.phone_number}")
	print(f"Notified contacts -> {len(sos.notifications)}")
