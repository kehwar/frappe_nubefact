from __future__ import annotations

from frappe.tests.utils import FrappeTestCase

from nubefact.nubefact.doctype.nubefact_facturacion.nubefact_facturacion_import_xml import (
    parse_import_cpe_xml_payload,
)


_DESPATCH_ADVICE_XML = """\
<DespatchAdvice xmlns="urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2">
  <ID>T001-25</ID>
  <IssueDate>2026-02-27</IssueDate>
  <Note>OBS: observaciones</Note>
  <DeliveryCustomerParty>
    <Party>
      <PartyIdentification><ID schemeID="6">20600695771</ID></PartyIdentification>
      <PartyLegalEntity><RegistrationName>NUBEFACT SA</RegistrationName></PartyLegalEntity>
    </Party>
  </DeliveryCustomerParty>
  <Shipment>
    <Delivery>
      <DeliveryAddress>
        <ID>211101</ID>
        <AddressLine><Line>DIRECCION LLEGADA</Line></AddressLine>
      </DeliveryAddress>
      <Despatch>
        <DespatchAddress>
          <ID>151021</ID>
          <AddressLine><Line>DIRECCION PARTIDA</Line></AddressLine>
        </DespatchAddress>
      </Despatch>
    </Delivery>
  </Shipment>
  <DespatchLine>
    <DeliveredQuantity unitCode="NIU">1.0</DeliveredQuantity>
    <Item>
      <Description>DETALLE DEL PRODUCTO 1</Description>
      <SellersItemIdentification><ID>001</ID></SellersItemIdentification>
    </Item>
  </DespatchLine>
  <DespatchLine>
    <DeliveredQuantity unitCode="NIU">2.0</DeliveredQuantity>
    <Item>
      <Description>DETALLE DEL PRODUCTO 2</Description>
      <SellersItemIdentification><ID>002</ID></SellersItemIdentification>
    </Item>
  </DespatchLine>
</DespatchAdvice>
"""


class TestNubefactFacturacionImportXML(FrappeTestCase):
    def test_parse_despatch_advice_xml(self):
        payload = parse_import_cpe_xml_payload(_DESPATCH_ADVICE_XML)

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
