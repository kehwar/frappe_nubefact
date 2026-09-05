import json

import frappe
from frappe.utils import cstr
from frappe.utils.file_manager import save_file

from nubefact.utils import (
	NUBEFACT_BASE64_FIELDS,
	attach_nubefact_base64_file,
	without_nubefact_base64_fields,
)

_DOCTYPES = (
	"Nubefact Facturacion",
	"Nubefact Guia De Remision",
)
_ARTIFACT_FIELDS = {
	"pdf": "pdf_zip_base64",
	"xml": "xml_zip_base64",
	"cdr": "cdr_zip_base64",
}


def execute():
	_attach_stored_base64_artifacts()
	_scrub_response_attachments()
	frappe.model.delete_fields(
		{doctype: list(NUBEFACT_BASE64_FIELDS) for doctype in _DOCTYPES},
		delete=1,
	)


def _attach_stored_base64_artifacts():
	"""Preserve any legacy encoded artifact that was not already attached."""
	for doctype in _DOCTYPES:
		if not all(frappe.db.has_column(doctype, fieldname) for fieldname in NUBEFACT_BASE64_FIELDS):
			continue

		documents = frappe.db.sql(
			f"""
				SELECT `name`, `title`
				FROM `tab{doctype}`
				WHERE {' OR '.join(f"COALESCE(`{fieldname}`, '') != ''" for fieldname in NUBEFACT_BASE64_FIELDS)}
			""",
			as_dict=True,
		)
		for document in documents:
			base_name = cstr(document.title).strip() or cstr(document.name)
			filenames = frappe.get_all(
				"File",
				filters={
					"attached_to_doctype": doctype,
					"attached_to_name": document.name,
				},
				pluck="file_name",
			)
			for extension, fieldname in _ARTIFACT_FIELDS.items():
				if _artifact_is_attached(filenames, base_name, extension):
					continue
				encoded_content = cstr(frappe.db.get_value(doctype, document.name, fieldname) or "")
				if encoded_content:
					attach_nubefact_base64_file(
						encoded_content=encoded_content,
						filename=f"{base_name}-{extension}.zip",
						doctype=doctype,
						docname=document.name,
					)


def _artifact_is_attached(filenames: list[str], base_name: str, extension: str) -> bool:
	return any(
		(filename.startswith(base_name) and filename.endswith(f".{extension}"))
		or (filename.startswith(f"{base_name}-{extension}") and filename.endswith(".zip"))
		for filename in filenames
	)


def _scrub_response_attachments():
	files = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": ["in", _DOCTYPES],
			"file_name": ["like", "%-response%.json"],
		},
		fields=[
			"name",
			"file_name",
			"attached_to_doctype",
			"attached_to_name",
			"attached_to_field",
			"folder",
			"is_private",
		],
	)
	for file_record in files:
		try:
			file_doc = frappe.get_doc("File", file_record.name)
			content = file_doc.get_content()
			if isinstance(content, bytes):
				content = content.decode("utf-8")
			payload = json.loads(content)
		except (
			OSError,
			TypeError,
			UnicodeDecodeError,
			json.JSONDecodeError,
			frappe.DoesNotExistError,
			frappe.ValidationError,
		):
			continue
		if not isinstance(payload, dict) or not any(
			fieldname in payload for fieldname in NUBEFACT_BASE64_FIELDS
		):
			continue

		sanitized_content = json.dumps(
			without_nubefact_base64_fields(payload),
			ensure_ascii=False,
			default=str,
			indent=2,
		).encode("utf-8")
		save_file(
			fname=file_record.file_name,
			content=sanitized_content,
			dt=file_record.attached_to_doctype,
			dn=file_record.attached_to_name,
			df=file_record.attached_to_field,
			folder=file_record.folder,
			is_private=file_record.is_private,
		)
		frappe.delete_doc(
			"File",
			file_record.name,
			ignore_permissions=True,
		)
