from __future__ import annotations

import base64
import importlib
import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urlparse


def _load_crypto_dependencies() -> tuple[Any, Any, Any]:
	"""Dynamically loads cryptography modules when available."""
	try:
		primitives = importlib.import_module("cryptography.hazmat.primitives")
		aead = importlib.import_module("cryptography.hazmat.primitives.ciphers.aead")
		pbkdf2 = importlib.import_module("cryptography.hazmat.primitives.kdf.pbkdf2")
		return aead.AESGCM, pbkdf2.PBKDF2HMAC, primitives.hashes
	except Exception:
		return None, None, None


@dataclass(frozen=True)
class EncryptedPayload:
	algorithm: str
	nonce_b64: str
	ciphertext_b64: str
	created_at: datetime


@dataclass
class PrivacySettings:
	share_with_research: bool = False
	share_with_insurance: bool = False
	allowed_external_targets: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class HealthRecord:
	record_id: str
	user_id: str
	category: str
	data: dict[str, Any]
	created_at: datetime


@dataclass(frozen=True)
class PromptRecord:
	prompt_id: str
	user_id: str
	prompt_text: str
	created_at: datetime


@dataclass(frozen=True)
class PrivacyScreenModel:
	user_id: str
	share_with_research: bool
	share_with_insurance: bool
	allowed_external_targets: list[str]
	controls_visible: bool = True


class Aes256GcmEncryptor:
	"""AES-256-GCM at-rest encryption provider."""

	ALGORITHM = "AES-256-GCM"

	def __init__(self, key: bytes) -> None:
		aesgcm_cls, _, _ = _load_crypto_dependencies()
		if aesgcm_cls is None:
			raise RuntimeError(
				"Missing dependency 'cryptography'. Install it to enable AES-256-GCM encryption."
			)
		if len(key) != 32:
			raise ValueError("Key must be 32 bytes for AES-256.")
		self._aesgcm = aesgcm_cls(key)

	@classmethod
	def from_passphrase(cls, passphrase: str, *, salt: bytes | None = None) -> Aes256GcmEncryptor:
		_, pbkdf2_cls, hashes_mod = _load_crypto_dependencies()
		if pbkdf2_cls is None or hashes_mod is None:
			raise RuntimeError(
				"Missing dependency 'cryptography'. Install it to derive AES-256 keys safely."
			)
		salt = salt or secrets.token_bytes(16)
		kdf = pbkdf2_cls(
			algorithm=hashes_mod.SHA256(),
			length=32,
			salt=salt,
			iterations=390000,
		)
		key = kdf.derive(passphrase.encode("utf-8"))
		return cls(key)

	def encrypt_dict(self, payload: dict[str, Any]) -> EncryptedPayload:
		plaintext = json.dumps(payload, separators=(",", ":")).encode("utf-8")
		nonce = secrets.token_bytes(12)
		ciphertext = self._aesgcm.encrypt(nonce, plaintext, None)
		return EncryptedPayload(
			algorithm=self.ALGORITHM,
			nonce_b64=base64.b64encode(nonce).decode("ascii"),
			ciphertext_b64=base64.b64encode(ciphertext).decode("ascii"),
			created_at=datetime.utcnow(),
		)

	def decrypt_dict(self, encrypted: EncryptedPayload) -> dict[str, Any]:
		nonce = base64.b64decode(encrypted.nonce_b64.encode("ascii"))
		ciphertext = base64.b64decode(encrypted.ciphertext_b64.encode("ascii"))
		plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
		return json.loads(plaintext.decode("utf-8"))


class TransportSecurityValidator:
	"""Enforces HTTPS/TLS use for all data transmission paths."""

	MIN_TLS_VERSION = "1.2"

	@staticmethod
	def assert_https_url(url: str) -> None:
		parsed = urlparse(url)
		if parsed.scheme.lower() != "https":
			raise ValueError("All data transmission must use HTTPS/TLS.")

	@staticmethod
	def assert_tls_version(version: str) -> None:
		normalized = version.replace("TLS", "").strip()
		if normalized not in {"1.2", "1.3"}:
			raise ValueError("TLS 1.2+ is required for data transmission.")


class SecureDataPlatform:
	"""
	NFR-5 secure health/prompt data platform.

	Controls implemented:
	- Health data and AI prompts encrypted at rest using AES-256-GCM.
	- HTTPS/TLS validation hooks for all transmission endpoints.
	- Per-user data isolation to prevent cross-user leakage.
	- Privacy settings model for explicit sharing consent.
	- No external sharing without user-approved target consent.
	"""

	def __init__(self, encryptor: Aes256GcmEncryptor) -> None:
		self._encryptor = encryptor
		self._privacy_settings: dict[str, PrivacySettings] = {}
		self._health_store: dict[str, dict[str, EncryptedPayload]] = {}
		self._prompt_store: dict[str, dict[str, EncryptedPayload]] = {}

	# --- Privacy Settings ---
	def get_privacy_screen(self, user_id: str) -> PrivacyScreenModel:
		settings = self._privacy_settings.setdefault(user_id, PrivacySettings())
		return PrivacyScreenModel(
			user_id=user_id,
			share_with_research=settings.share_with_research,
			share_with_insurance=settings.share_with_insurance,
			allowed_external_targets=sorted(settings.allowed_external_targets),
			controls_visible=True,
		)

	def update_privacy_settings(
		self,
		user_id: str,
		*,
		share_with_research: bool | None = None,
		share_with_insurance: bool | None = None,
		allow_targets: list[str] | None = None,
	) -> None:
		settings = self._privacy_settings.setdefault(user_id, PrivacySettings())
		if share_with_research is not None:
			settings.share_with_research = share_with_research
		if share_with_insurance is not None:
			settings.share_with_insurance = share_with_insurance
		if allow_targets is not None:
			settings.allowed_external_targets = set(allow_targets)

	# --- Secure Storage ---
	def store_health_data(self, user_id: str, category: str, data: dict[str, Any]) -> str:
		record_id = secrets.token_hex(12)
		record = HealthRecord(
			record_id=record_id,
			user_id=user_id,
			category=category,
			data=data,
			created_at=datetime.utcnow(),
		)
		payload = self._encryptor.encrypt_dict(
			{
				"record_id": record.record_id,
				"user_id": record.user_id,
				"category": record.category,
				"data": record.data,
				"created_at": record.created_at.isoformat(),
			}
		)
		self._health_store.setdefault(user_id, {})[record_id] = payload
		return record_id

	def store_ai_prompt(self, user_id: str, prompt_text: str) -> str:
		prompt_id = secrets.token_hex(12)
		record = PromptRecord(
			prompt_id=prompt_id,
			user_id=user_id,
			prompt_text=prompt_text,
			created_at=datetime.utcnow(),
		)
		payload = self._encryptor.encrypt_dict(
			{
				"prompt_id": record.prompt_id,
				"user_id": record.user_id,
				"prompt_text": record.prompt_text,
				"created_at": record.created_at.isoformat(),
			}
		)
		self._prompt_store.setdefault(user_id, {})[prompt_id] = payload
		return prompt_id

	def get_user_health_records(self, requester_id: str, target_user_id: str) -> list[dict[str, Any]]:
		self._assert_same_user(requester_id, target_user_id)
		records = self._health_store.get(target_user_id, {})
		return [self._encryptor.decrypt_dict(payload) for payload in records.values()]

	def get_user_prompt_history(self, requester_id: str, target_user_id: str) -> list[dict[str, Any]]:
		self._assert_same_user(requester_id, target_user_id)
		prompts = self._prompt_store.get(target_user_id, {})
		return [self._encryptor.decrypt_dict(payload) for payload in prompts.values()]

	# --- Sharing / Transmission ---
	def share_health_data_externally(
		self,
		requester_id: str,
		target_system: str,
		endpoint_url: str,
		tls_version: str,
		record_ids: list[str] | None = None,
	) -> list[dict[str, Any]]:
		settings = self._privacy_settings.setdefault(requester_id, PrivacySettings())
		if target_system not in settings.allowed_external_targets:
			raise PermissionError("External data sharing requires explicit user consent.")

		TransportSecurityValidator.assert_https_url(endpoint_url)
		TransportSecurityValidator.assert_tls_version(tls_version)

		user_records = self._health_store.get(requester_id, {})
		selected_ids = set(record_ids) if record_ids else set(user_records.keys())
		selected: list[dict[str, Any]] = []
		for record_id, payload in user_records.items():
			if record_id in selected_ids:
				selected.append(self._encryptor.decrypt_dict(payload))
		return selected

	def exposed_api_endpoints(self) -> list[str]:
		# Intentionally excludes prompt history endpoints to prevent accidental exposure.
		return [
			"GET /v1/privacy/settings",
			"PUT /v1/privacy/settings",
			"GET /v1/health/records",
			"POST /v1/health/records",
			"POST /v1/health/share",
		]

	# --- Security Verification ---
	def run_cross_user_isolation_test(self) -> bool:
		"""Simple penetration-test style check for cross-user data leakage."""
		user_a = "pentest-a"
		user_b = "pentest-b"

		self.store_health_data(user_a, "glucose", {"reading": 94})
		self.store_ai_prompt(user_a, "Summarize my glucose trend")

		try:
			_ = self.get_user_health_records(user_b, user_a)
			return False
		except PermissionError:
			pass

		try:
			_ = self.get_user_prompt_history(user_b, user_a)
			return False
		except PermissionError:
			pass

		return True

	@staticmethod
	def _assert_same_user(requester_id: str, target_user_id: str) -> None:
		if requester_id != target_user_id:
			raise PermissionError("Cross-user data access is not allowed.")


if __name__ == "__main__":
	# Demo-only execution path.
	encryptor = Aes256GcmEncryptor.from_passphrase("demo-master-key")
	platform = SecureDataPlatform(encryptor)

	uid = "user-100"
	platform.update_privacy_settings(uid, allow_targets=["trusted-research"])
	platform.store_health_data(uid, "medication", {"name": "Metformin", "dosage": "500mg"})
	platform.store_health_data(uid, "glucose", {"reading": 108, "unit": "mg/dL"})
	platform.store_ai_prompt(uid, "What is my average glucose this week?")

	own_records = platform.get_user_health_records(uid, uid)
	privacy_screen = platform.get_privacy_screen(uid)
	penetration_ok = platform.run_cross_user_isolation_test()

	print(f"Privacy controls visible: {privacy_screen.controls_visible}")
	print(f"Stored records: {len(own_records)}")
	print(f"Cross-user isolation passed: {penetration_ok}")
