# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision_import_xml import (
	parse_import_despatch_xml_payload,
)

DESPATCH_XML = """<?xml version="1.0" encoding="UTF-8"?>
<DespatchAdvice xmlns="urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
 <cbc:ID>{series}-25</cbc:ID>
 <cbc:IssueDate>2026-06-01</cbc:IssueDate>
 <cac:DespatchSupplierParty><cac:Party>
  <cac:PartyIdentification><cbc:ID schemeID="6">20600000001</cbc:ID></cac:PartyIdentification>
  <cac:PartyLegalEntity><cbc:RegistrationName>REMITENTE XML</cbc:RegistrationName><cac:RegistrationAddress><cac:AddressLine><cbc:Line>DIRECCION REMITENTE XML</cbc:Line></cac:AddressLine></cac:RegistrationAddress></cac:PartyLegalEntity>
 </cac:Party></cac:DespatchSupplierParty>
 <cac:DeliveryCustomerParty><cac:Party>
  <cac:PartyIdentification><cbc:ID schemeID="1">12345678</cbc:ID></cac:PartyIdentification>
  <cac:PartyLegalEntity><cbc:RegistrationName>DESTINATARIO XML</cbc:RegistrationName></cac:PartyLegalEntity>
 </cac:Party></cac:DeliveryCustomerParty>
 <cac:AdditionalDocumentReference><cbc:ID>F001-10</cbc:ID><cbc:DocumentTypeCode>01</cbc:DocumentTypeCode></cac:AdditionalDocumentReference>
 <cac:Shipment>
  <cbc:HandlingCode>08</cbc:HandlingCode>
  <cbc:GrossWeightMeasure unitCode="KGM">10.5</cbc:GrossWeightMeasure>
  {packages}
  <cbc:SpecialInstructions>SUNAT_Envio_IndicadorVehiculoConductoresTransp</cbc:SpecialInstructions>
  <cac:ShipmentStage>
   <cbc:TransportModeCode>02</cbc:TransportModeCode>
   <cac:TransitPeriod><cbc:StartDate>2026-06-02</cbc:StartDate></cac:TransitPeriod>
   <cac:LoadingTransportEvent><cbc:OccurrenceDate>2026-06-03</cbc:OccurrenceDate></cac:LoadingTransportEvent>
   <cac:CarrierParty>
    <cac:PartyIdentification><cbc:ID schemeID="6">20600000002</cbc:ID></cac:PartyIdentification>
    <cac:PartyLegalEntity><cbc:RegistrationName>TRANSPORTISTA XML</cbc:RegistrationName><cbc:CompanyID>MTC123</cbc:CompanyID></cac:PartyLegalEntity>
   </cac:CarrierParty>
   <cac:DriverPerson><cbc:ID schemeID="1">11111111</cbc:ID><cbc:FirstName>JUAN</cbc:FirstName><cbc:FamilyName>PEREZ</cbc:FamilyName><cbc:JobTitle>Principal</cbc:JobTitle><cac:IdentityDocumentReference><cbc:ID>Q12345678</cbc:ID></cac:IdentityDocumentReference></cac:DriverPerson>
   <cac:DriverPerson><cbc:ID schemeID="A">ABC123</cbc:ID><cbc:FirstName>ANA</cbc:FirstName><cbc:FamilyName>LOPEZ</cbc:FamilyName><cbc:JobTitle>Secundario</cbc:JobTitle><cac:IdentityDocumentReference><cbc:ID>Q12345679</cbc:ID></cac:IdentityDocumentReference></cac:DriverPerson>
  </cac:ShipmentStage>
  <cac:Delivery>
   <cac:DeliveryAddress><cbc:ID>150102</cbc:ID><cbc:AddressTypeCode>0002</cbc:AddressTypeCode><cac:AddressLine><cbc:Line>DESTINO XML</cbc:Line></cac:AddressLine></cac:DeliveryAddress>
   <cac:Despatch><cac:DespatchAddress><cbc:ID>150101</cbc:ID><cbc:AddressTypeCode>0001</cbc:AddressTypeCode><cac:AddressLine><cbc:Line>ORIGEN XML</cbc:Line></cac:AddressLine></cac:DespatchAddress></cac:Despatch>
  </cac:Delivery>
  <cac:TransportHandlingUnit><cac:TransportEquipment>
   <cbc:ID>ABC123</cbc:ID><cac:ApplicableTransportMeans><cbc:RegistrationNationalityID>ABC1234567</cbc:RegistrationNationalityID></cac:ApplicableTransportMeans>
   <cac:AttachedTransportEquipment><cbc:ID>ABC124</cbc:ID><cac:ApplicableTransportMeans><cbc:RegistrationNationalityID>ABC1234568</cbc:RegistrationNationalityID></cac:ApplicableTransportMeans></cac:AttachedTransportEquipment>
  </cac:TransportEquipment></cac:TransportHandlingUnit>
 </cac:Shipment>
 <cac:DespatchLine>
  <cbc:DeliveredQuantity unitCode="NIU">2</cbc:DeliveredQuantity>
  <cac:Item><cbc:Description>ITEM XML</cbc:Description><cac:SellersItemIdentification><cbc:ID>ITEM-1</cbc:ID></cac:SellersItemIdentification>
   <cac:AdditionalItemProperty><cbc:Name>Numeración de la DAM o DS</cbc:Name><cbc:Value>123-1234-10-123456</cbc:Value></cac:AdditionalItemProperty>
   <cac:AdditionalItemProperty><cbc:Name>Número de serie en la DAM o DS</cbc:Name><cbc:Value>1</cbc:Value></cac:AdditionalItemProperty>
  </cac:Item>
 </cac:DespatchLine>
</DespatchAdvice>
"""


class TestNubefactGuiaDeRemisionImportXML(FrappeTestCase):
	def test_parse_remitente_despatch_advice_preserves_transport_data(self):
		payload = parse_import_despatch_xml_payload(
			DESPATCH_XML.format(
				series="TTT1",
				packages="<cbc:TotalTransportHandlingUnitQuantity>3</cbc:TotalTransportHandlingUnitQuantity>",
			)
		)

		self.assertEqual(payload["fecha_de_entrega_al_transportista"], "2026-06-03")
		self.assertEqual(payload["transportista_placa_numero"], "ABC123")
		self.assertEqual(payload["tuc_vehiculo_principal"], "ABC1234567")
		self.assertEqual(payload["conductor_numero_licencia"], "Q12345678")
		self.assertEqual(payload["mtc"], "MTC123")
		self.assertEqual(payload["sunat_envio_indicador"], "07")
		self.assertEqual(payload["punto_de_partida_codigo_establecimiento_sunat"], "0001")
		self.assertEqual(payload["punto_de_llegada_codigo_establecimiento_sunat"], "0002")
		self.assertEqual(payload["items"][0]["codigo_dam"], "1/123-1234-10-123456")
		self.assertEqual(payload["vehiculos_secundarios"][0], {"placa_numero": "ABC124", "tuc": "ABC1234568"})
		self.assertEqual(payload["conductores_secundarios"][0]["documento_tipo"], "A")

	def test_parse_transportista_maps_sender_and_recipient_without_inventing_packages(self):
		payload = parse_import_despatch_xml_payload(DESPATCH_XML.format(series="VVV1", packages=""))

		self.assertEqual(payload["tipo_de_comprobante"], "8")
		self.assertEqual(payload["cliente_numero_de_documento"], "20600000001")
		self.assertEqual(payload["cliente_direccion"], "DIRECCION REMITENTE XML")
		self.assertEqual(payload["destinatario_documento_numero"], "12345678")
		self.assertNotIn("numero_de_bultos", payload)

	def test_parse_rejects_cdr_malformed_and_unsupported_xml(self):
		invalid_series = DESPATCH_XML.format(series="GGG1", packages="")
		for xml in ("<ApplicationResponse />", "<Invoice />", "<not-closed>", invalid_series):
			with self.subTest(xml=xml):
				with self.assertRaises(frappe.ValidationError):
					parse_import_despatch_xml_payload(xml)
