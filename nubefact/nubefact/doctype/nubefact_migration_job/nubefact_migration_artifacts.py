from __future__ import annotations

import base64
import binascii
import io
import re
import stat
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

import requests
from frappe.utils import cstr

from nubefact.utils import _download_public_file

MAX_ENCODED_SIZE = 100 * 1024 * 1024
MAX_ARCHIVE_SIZE = 75 * 1024 * 1024
MAX_UNCOMPRESSED_SIZE = 100 * 1024 * 1024
MAX_ZIP_ENTRIES = 20
MAX_COMPRESSION_RATIO = 100
DESPATCH_NAMESPACE = "urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2"
APPLICATION_RESPONSE_NAMESPACE = "urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"
BASE64_FIELDS = ("pdf_zip_base64", "xml_zip_base64", "cdr_zip_base64")


class ArtifactValidationError(ValueError):
	"""A provider artifact is unsafe, ambiguous, or belongs to another GRE."""


@dataclass
class InspectedArtifacts:
	logical: dict[str, bytes] = field(default_factory=dict)
	containers: dict[str, bytes] = field(default_factory=dict)
	errors: dict[str, str] = field(default_factory=dict)
	retryable_errors: set[str] = field(default_factory=set)
	conflicting_kinds: set[str] = field(default_factory=set)


def canonical_document_identity(series: Any, number: Any) -> tuple[str, int]:
	normalized_series = cstr(series or "").strip().upper()
	if not re.fullmatch(r"T[A-Z0-9]{3}", normalized_series):
		raise ArtifactValidationError("La identidad no corresponde a una serie GRE Remitente Txxx.")
	number_text = cstr(number or "").strip()
	if not re.fullmatch(r"\d+", number_text) or not 1 <= int(number_text) <= 99_999_999:
		raise ArtifactValidationError("La identidad contiene un número de GRE inválido.")
	return normalized_series, int(number_text)


def inspect_base64_artifacts(
	response: dict[str, Any],
	*,
	expected_series: str,
	expected_number: int,
	kinds: set[str] | None = None,
) -> InspectedArtifacts:
	"""Decode and content-classify provider ZIP fields without trusting labels.

	A bad provider field is attributed to its nominal kind. Valid transposed fields
	are attributed by content, and contradictory candidates invalidate only their
	actual logical kind.
	"""

	result = InspectedArtifacts()
	for fieldname in BASE64_FIELDS:
		encoded = response.get(fieldname)
		if encoded in (None, ""):
			continue
		nominal_kind = fieldname.split("_", 1)[0]
		try:
			if not isinstance(encoded, str):
				raise ArtifactValidationError(f"{fieldname} no contiene Base64 válido.")
			compact = "".join(encoded.split())
			if len(compact.encode("ascii", errors="ignore")) > MAX_ENCODED_SIZE:
				raise ArtifactValidationError(f"{fieldname} supera el límite codificado de 100 MB.")
			try:
				container = base64.b64decode(compact, validate=True)
			except (ValueError, binascii.Error) as exc:
				raise ArtifactValidationError(f"{fieldname} no contiene Base64 válido.") from exc
			if len(container) > MAX_ARCHIVE_SIZE:
				raise ArtifactValidationError(f"{fieldname} supera el límite de archivo ZIP de 75 MB.")
			classification, content = inspect_zip_container(
				container,
				expected_series=expected_series,
				expected_number=expected_number,
			)
		except ArtifactValidationError as exc:
			if kinds is None or nominal_kind in kinds:
				result.errors[nominal_kind] = _safe_error(exc)
			continue
		if kinds is not None and classification not in kinds:
			continue
		if _add_inspected_candidate(result, classification, content):
			result.containers[fieldname] = container
	return result


def inspect_zip_container(
	container: bytes, *, expected_series: str, expected_number: int
) -> tuple[str, bytes]:
	try:
		archive = zipfile.ZipFile(io.BytesIO(container))
	except (zipfile.BadZipFile, OSError) as exc:
		raise ArtifactValidationError("El contenido Base64 no es un ZIP válido.") from exc

	with archive:
		members = archive.infolist()
		if not members or len(members) > MAX_ZIP_ENTRIES:
			raise ArtifactValidationError("El ZIP debe contener entre 1 y 20 entradas.")
		total = 0
		candidates: list[tuple[str, bytes]] = []
		for member in members:
			_validate_member(member)
			if member.is_dir():
				continue
			total += member.file_size
			if member.file_size > MAX_UNCOMPRESSED_SIZE or total > MAX_UNCOMPRESSED_SIZE:
				raise ArtifactValidationError("El contenido descomprimido supera 100 MB.")
			if member.file_size and (
				member.compress_size == 0 or member.file_size / member.compress_size > MAX_COMPRESSION_RATIO
			):
				raise ArtifactValidationError("El ZIP supera la relación máxima de compresión 100:1.")
			content = archive.read(member)
			if _has_archive_magic(content):
				raise ArtifactValidationError("No se permiten archivos comprimidos anidados.")
			kind = classify_artifact_content(
				content,
				expected_series=expected_series,
				expected_number=expected_number,
			)
			if kind:
				candidates.append((kind, content))

		if len(candidates) != 1:
			raise ArtifactValidationError(
				"El ZIP debe contener exactamente un artefacto PDF, XML o CDR válido."
			)
		return candidates[0]


def _validate_member(member: zipfile.ZipInfo) -> None:
	name = member.filename.replace("\\", "/")
	path = PurePosixPath(name)
	if path.is_absolute() or ".." in path.parts or not name or re.match(r"^[A-Za-z]:", name):
		raise ArtifactValidationError("El ZIP contiene una ruta no permitida.")
	if member.flag_bits & 0x1:
		raise ArtifactValidationError("El ZIP contiene una entrada cifrada.")
	mode = member.external_attr >> 16
	file_type = stat.S_IFMT(mode)
	if file_type and (
		stat.S_ISLNK(mode) or (not member.is_dir() and file_type not in {stat.S_IFREG, stat.S_IFDIR})
	):
		raise ArtifactValidationError("El ZIP contiene enlaces o entradas especiales.")
	if PurePosixPath(name).suffix.lower() in {".zip", ".rar", ".7z", ".gz", ".tar"}:
		raise ArtifactValidationError("No se permiten archivos comprimidos anidados.")


def _has_archive_magic(content: bytes) -> bool:
	return content.startswith(
		(b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08", b"Rar!\x1a\x07", b"7z\xbc\xaf'\x1c", b"\x1f\x8b")
	) or (len(content) > 262 and content[257:262] == b"ustar")


def classify_artifact_content(content: bytes, *, expected_series: str, expected_number: int) -> str | None:
	if content.startswith(b"%PDF"):
		return "pdf"
	try:
		root = ET.fromstring(content)
	except ET.ParseError:
		return None

	namespace, local_name = _split_tag(root.tag)
	if local_name == "DespatchAdvice":
		if namespace != DESPATCH_NAMESPACE:
			raise ArtifactValidationError("El XML no usa el namespace UBL DespatchAdvice esperado.")
		_validate_despatch_identity(root, expected_series, expected_number)
		return "xml"
	if local_name == "ApplicationResponse":
		if namespace != APPLICATION_RESPONSE_NAMESPACE:
			raise ArtifactValidationError("El CDR no usa el namespace UBL ApplicationResponse esperado.")
		_validate_cdr_identity(root, expected_series, expected_number)
		return "cdr"
	return None


def inspect_url_artifacts(
	response: dict[str, Any],
	*,
	expected_series: str,
	expected_number: int,
	kinds: set[str] | None = None,
	before_request: Callable[[], None] | None = None,
	after_request: Callable[[], None] | None = None,
) -> InspectedArtifacts:
	"""Fetch provider-returned URLs and validate each URL by its logical field."""

	result = InspectedArtifacts()
	fields = {
		"pdf": "enlace_del_pdf",
		"xml": "enlace_del_xml",
		"cdr": "enlace_del_cdr",
	}
	for expected_kind, fieldname in fields.items():
		if kinds is not None and expected_kind not in kinds:
			continue
		url = response.get(fieldname)
		if not cstr(url or "").strip():
			continue
		if before_request:
			before_request()
		try:
			content = _download_public_file(cstr(url).strip())
			kind, logical_content = _classify_direct_or_zip(
				content,
				expected_series=expected_series,
				expected_number=expected_number,
			)
			if kind != expected_kind:
				raise ArtifactValidationError(
					f"{fieldname} no contiene el artefacto {expected_kind.upper()} esperado."
				)
			_add_inspected_candidate(result, kind, logical_content)
		except Exception as exc:
			result.errors[expected_kind] = _safe_error(exc)
			if _is_retryable_download_error(exc):
				result.retryable_errors.add(expected_kind)
		finally:
			if after_request:
				after_request()
	return result


def collect_response_artifacts(
	response: dict[str, Any],
	*,
	expected_series: str,
	expected_number: int,
	kinds: set[str] | None = None,
	before_request: Callable[[], None] | None = None,
	after_request: Callable[[], None] | None = None,
) -> InspectedArtifacts:
	"""Try URL and Base64 sources, rejecting conflicting logical candidates."""

	urls = inspect_url_artifacts(
		response,
		expected_series=expected_series,
		expected_number=expected_number,
		kinds=kinds,
		before_request=before_request,
		after_request=after_request,
	)
	base64_artifacts = inspect_base64_artifacts(
		response,
		expected_series=expected_series,
		expected_number=expected_number,
		kinds=kinds,
	)
	for kind, message in base64_artifacts.errors.items():
		if kind not in base64_artifacts.logical and kind not in urls.logical:
			urls.errors[kind] = message
	for kind, content in base64_artifacts.logical.items():
		_add_inspected_candidate(urls, kind, content)
	urls.containers.update(base64_artifacts.containers)
	urls.retryable_errors.update(base64_artifacts.retryable_errors)
	for kind in tuple(urls.errors):
		if kind in urls.logical and kind not in urls.conflicting_kinds:
			urls.errors.pop(kind, None)
	return urls


def _classify_direct_or_zip(
	content: bytes, *, expected_series: str, expected_number: int
) -> tuple[str | None, bytes]:
	if zipfile.is_zipfile(io.BytesIO(content)):
		return inspect_zip_container(
			content,
			expected_series=expected_series,
			expected_number=expected_number,
		)
	return (
		classify_artifact_content(
			content,
			expected_series=expected_series,
			expected_number=expected_number,
		),
		content,
	)


def _validate_cdr_identity(root: ET.Element, expected_series: str, expected_number: int) -> None:
	references: list[str] = []
	for node in root.iter():
		if _split_tag(node.tag)[1] != "DocumentReference":
			continue
		for child in node.iter():
			if _split_tag(child.tag)[1] == "ID" and cstr(child.text or "").strip():
				references.append(cstr(child.text).strip())
				break
	if not references:
		raise ArtifactValidationError("El CDR no contiene la identidad del documento de referencia.")
	for reference in references:
		if "-" not in reference:
			raise ArtifactValidationError("El CDR contiene una identidad de referencia inválida.")
		series, number = reference.split("-", 1)
		if canonical_document_identity(series, number) != canonical_document_identity(
			expected_series, expected_number
		):
			raise ArtifactValidationError("El CDR pertenece a otra serie o número.")


def _validate_despatch_identity(root: ET.Element, expected_series: str, expected_number: int) -> None:
	identity = ""
	for child in list(root):
		if _split_tag(child.tag)[1] == "ID":
			identity = cstr(child.text or "").strip()
			break
	if "-" not in identity:
		raise ArtifactValidationError("El XML DespatchAdvice no contiene una identidad válida.")
	series, number = identity.split("-", 1)
	actual = canonical_document_identity(series, number)
	expected = canonical_document_identity(expected_series, expected_number)
	if actual != expected:
		raise ArtifactValidationError("El XML pertenece a otra serie o número.")


def _split_tag(tag: str) -> tuple[str, str]:
	if tag.startswith("{") and "}" in tag:
		namespace, local_name = tag[1:].split("}", 1)
		return namespace, local_name
	return "", tag


def _add_inspected_candidate(result: InspectedArtifacts, kind: str, content: bytes) -> bool:
	if kind in result.conflicting_kinds:
		return False
	current = result.logical.get(kind)
	if current is not None and current != content:
		result.logical.pop(kind, None)
		result.conflicting_kinds.add(kind)
		result.errors[kind] = f"NubeFact devolvió candidatos {kind.upper()} contradictorios."
		return False
	result.logical[kind] = content
	result.errors.pop(kind, None)
	result.retryable_errors.discard(kind)
	return True


def _is_retryable_download_error(exc: Exception) -> bool:
	if isinstance(exc, requests.HTTPError):
		status = getattr(exc.response, "status_code", None)
		return status == 429 or bool(status and status >= 500)
	if isinstance(exc, requests.RequestException):
		return "URL de descarga no permitida" not in cstr(exc)
	return False


def _safe_error(exc: Exception) -> str:
	text = cstr(exc or "").strip()
	return text[:500] or "No se pudo validar el artefacto."
