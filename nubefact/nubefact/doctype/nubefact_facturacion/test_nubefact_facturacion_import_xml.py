from __future__ import annotations

from pathlib import Path

from frappe.tests.utils import FrappeTestCase

from nubefact.nubefact.doctype.nubefact_facturacion.nubefact_facturacion_import_xml import (
    parse_import_cpe_xml_payload,
)


class TestNubefactFacturacionImportXML(FrappeTestCase):
    def test_parse_despatch_advice_xml_examples(self):
        asset_names = [
            "cpe-example-ejemplo-json-generar-cpe-boleta-1-gravada.xml",
            "cpe-example-ejemplo-json-generar-cpe-factura-1-gravada.xml",
        ]

        for asset_name in asset_names:
            payload = parse_import_cpe_xml_payload(_read_xml_asset(asset_name))

            self.assertEqual(payload.get("serie"), "T001")
            self.assertEqual(payload.get("numero"), "25")
            self.assertEqual(payload.get("fecha_de_emision"), "2026-02-27")
            self.assertEqual(payload.get("cliente_tipo_de_documento"), "6")
            self.assertEqual(payload.get("cliente_numero_de_documento"), "20600695771")
            self.assertEqual(payload.get("cliente_denominacion"), "NUBEFACT SA")
            self.assertEqual(payload.get("cliente_direccion"), "DIRECCION LLEGADA")
            self.assertEqual(payload.get("ubigeo_origen"), "151021")
            self.assertEqual(payload.get("direccion_origen"), "DIRECCION PARTIDA")
            self.assertEqual(payload.get("ubigeo_destino"), "211101")
            self.assertEqual(payload.get("direccion_destino"), "DIRECCION LLEGADA")
            self.assertEqual(payload.get("observaciones"), "observaciones")

            items = payload.get("items") or []
            self.assertEqual(len(items), 2)
            self.assertEqual(items[0].get("unidad_de_medida"), "NIU")
            self.assertEqual(items[0].get("codigo"), "001")
            self.assertEqual(items[0].get("descripcion"), "DETALLE DEL PRODUCTO 1")
            self.assertEqual(items[0].get("cantidad"), "1.0")
            self.assertEqual(items[1].get("codigo"), "002")


def _read_xml_asset(asset_name: str) -> str:
    app_root = Path(__file__).resolve().parents[4]
    asset_path = (
        app_root
        / ".agents"
        / "skills"
        / "nubefact-api-implementation"
        / "assets"
        / asset_name
    )
    return asset_path.read_text(encoding="utf-8")
