# Auditoría de implementación GRE contra el manual JSON de NubeFact

## Alcance y fuente

Auditoría estática de la implementación Frappe en `nubefact/nubefact/doctype/nubefact_guia_de_remision*`, sus importadores, `nubefact/hooks.py`, el cliente HTTP y las utilidades compartidas. Línea base del repositorio: `26988dd238a44b7c1c56dc1b92087ca472b09663`.

Fuente primaria oficial:

- Documento: [Google Doc oficial](https://docs.google.com/document/d/1GCmIJNJVmuOD3LC0itdhdTu6260nJBIEmOwFdnIu5II/edit), enlazado desde `references/nubefact-docs/NUBEFACT DOC API JSON V1.md:7`.
- Texto usado para esta auditoría: [exportación `text/plain`](https://docs.google.com/document/d/1GCmIJNJVmuOD3LC0itdhdTu6260nJBIEmOwFdnIu5II/export?format=txt) (1,009 líneas, 31,680 bytes, SHA-256 `e7d6aac775d23dc279cf7e5285b4120e0a08d8893c5836854918457cea8aefe9` al consultarlo).

La exportación es un documento vivo. Las conclusiones siguientes corresponden exactamente a esa captura y describen la línea base auditada, antes de las correcciones posteriores. **Leyenda:** **M** = coincide; **X** = discrepancia confirmada; **P** = cobertura parcial o falta de validación; **A** = ambigüedad del manual.

## Estado de remediación

Las discrepancias **X/P** confirmadas en esta auditoría fueron corregidas después de la línea base: soporte v1.7, catálogos y validaciones, payload por tipo y transporte, fidelidad de importación JSON/XML, consistencia y persistencia de respuestas, y polling. Las regresiones se cubren en los tres seams públicos relevantes:

- comportamiento del documento GRE y ciclo RPC de Frappe;
- importación JSON;
- importación UBL `DespatchAdvice` XML.

La ambigüedad **A** de `fecha_de_entrega_al_transportista` se conserva deliberadamente: se exige para tipo 7 con transporte público y se acepta de forma opcional para tipo 8, porque el cuadro formal y el ejemplo oficial v1.7 se contradicen.

## Changelog oficial comprobado

La exportación contiene todo el historial 1.1–1.7:

| Versión / fecha | Hecho citado del changelog oficial |
|---|---|
| 1.1 — 30/11/2022 | “Para generar Guías se necesitan DOS PASOS”: primero `generar_guia` (sin PDF/XML), luego `consultar_guia`; SUNAT puede tardar segundos o minutos. |
| 1.2 — 03/12/2022 | “Información para descargar GRE desde la misma Sunat. Dar de baja una GRE desde la Sunat con Clave Sol”. |
| 1.3 — 17/12/2022 | “Generar GRE Transportista” y pruebas en DEMO. |
| 1.4 — 20/09/2023 | “Documento relacionado a la guía de Remisión”. |
| 1.5 — 30/11/2023 | “Vehículos Secundarios y Conductores Secundarios”. |
| 1.6 — 01/12/2023 | “Se agrega el indicador SUNAT_Envio_IndicadorTrasladoVehiculoM1L”. |
| **1.7 — 01/06/2026** | **“Se agrega el nuevo campo ‘Fecha de entrega de bienes al transportista’ para GRE Remitente”.** |

## Resultado ejecutivo

La base funcional es correcta: autenticación, generación de tipos 7/8, consulta posterior, tablas anidadas, persistencia de los campos de estado y descarga por URL están implementadas. Sin embargo, **la implementación no está al día con 1.7** y no aplica gran parte de las restricciones declaradas por el manual.

Discrepancias confirmadas de mayor impacto:

1. **No existe soporte de primer nivel para `fecha_de_entrega_al_transportista` 1.7**: no está en el DocType, payload, validación ni importadores (`nubefact_guia_de_remision.json:7-104`; `nubefact_guia_de_remision.py:147-207`; `nubefact_guia_de_remision_import.py:49-113`). Sólo podría inyectarse manualmente mediante el escape genérico `custom` (`nubefact_guia_de_remision.py:262`; `nubefact_guia_de_remision.json:527-529`).
2. **`numero` es obligatorio en el manual pero no en la validación** y se omite del payload si está vacío (`nubefact_guia_de_remision_schema.py:17-33`; `nubefact_guia_de_remision.py:175-184`).
3. **Catálogos desalineados:** motivos `03` y `17` faltan y aparece `19` no documentado; indicador `07` falta; tipos de documento de conductor `A` y `0` faltan; el transportista permite códigos distintos de `6`; y se ofrece PDF `A5`, aunque el manual GRE sólo enumera `A4` y `TICKET` (`nubefact_guia_de_remision.json:241-255,284-288,315-319,355-359,467-470`).
4. **La consulta automática del formulario está rota para GRE:** el watcher compartido busca `estado_del_comprobante === "Pendiente de Aceptación"`, mientras GRE usa `status === "Pendiente de Aceptacion"` (`nubefact/public/js/nubefact.bundle.js:28-30`; `nubefact_guia_de_remision.json:112-119`). La consulta manual y el cron cada cinco minutos sí funcionan (`nubefact_guia_de_remision.js:26-33`; `nubefact/hooks.py:170-176`).
5. **Tres respuestas Base64 documentadas no se conservan como campos/archivos:** `pdf_zip_base64`, `xml_zip_base64`, `cdr_zip_base64` se quedan únicamente dentro del JSON íntegro del API Log; el documento sólo extrae URLs y estado (`nubefact_guia_de_remision.py:338-362`; `nubefact/utils/nubefact/__init__.py:70-85`; `nubefact/nubefact/doctype/nubefact_api_log/nubefact_api_log.py:43-66`).
6. **No hay pruebas GRE reales**: la clase de prueba está vacía (`nubefact_guia_de_remision/test_nubefact_guia_de_remision.py:8-9`).

## Cabecera de `generar_guia`: comparación exhaustiva

| Campo(s) oficial(es) | Estado | Implementación y diferencia |
|---|---:|---|
| `operacion` | **M** | Se fija exactamente a `generar_guia` (`nubefact_guia_de_remision.py:147-149`). |
| `tipo_de_comprobante` | **M/P** | Select 7/8 y serialización numérica correctos (`nubefact_guia_de_remision.json:128-133`; `.py:149`). No hay validación de coherencia serie/tipo. |
| `serie` | **P** | Está y es obligatoria por presencia, pero no se valida longitud 4 ni prefijo `T` para tipo 7 / `V` para tipo 8 (`nubefact_guia_de_remision_schema.py:17-20`; `.json:142-145`). |
| `numero` | **X** | El manual exige entero de 1–8 dígitos sin ceros iniciales. El campo es `Int`, pero no es requerido ni se valida rango; vacío implica que no se envía (`.json:148-152`; `.py:175-184`). |
| `cliente_tipo_de_documento` | **M/P** | Códigos `6,1,4,7,A,0` completos y enviados como texto (`.json:175-179`; `.py:151`). No se validan las longitudes/naturaleza del número asociado. La etiqueta genérica “Cliente” no aclara que significa destinatario en tipo 7 y remitente en tipo 8. |
| `cliente_numero_de_documento`, `cliente_denominacion`, `cliente_direccion` | **M/P** | Representados, obligatorios y enviados (`nubefact_guia_de_remision_schema.py:21-24`; `.py:152-154`). Sin máximos 15/100/100 ni validación según tipo de documento. |
| `cliente_email`, `_1`, `_2` | **M/P** | Opcionales y omitidos si vacíos (`.py:175-182`), pero sin validación de email o máximo 250 (`.json:200-212`). |
| `fecha_de_emision` | **M/P** | Obligatoria y convertida a `DD-MM-YYYY` (`nubefact/utils/__init__.py:16-17`; `.py:155`). No se exige “fecha actual” ni máximo un día anterior. |
| `observaciones` | **M/P/A** | Campo y envío opcional correctos (`.json:522-524`; `.py:182`). No se limita longitud. El manual contradice su descripción “0 hasta 1000 caracteres” con la columna “Hasta 5”. |
| `motivo_de_traslado` (sólo tipo 7) | **X** | Se requiere para tipo 7 (`.py:293-298`), pero el Select omite los códigos oficiales `03` (venta con entrega a terceros) y `17` (bienes para transformación), y agrega `19`, ausente del manual capturado (`.json:241-245`). Para tipo 8 se manda además la clave vacía porque forma parte del payload base (`.py:159`). |
| `motivo_de_traslado_otros_descripcion` | **P** | Se puede enviar (`.py:183`), pero no se exige exclusivamente cuando motivo=`13`, ni se valida texto alfanumérico/70 caracteres (`.json:247-250`). |
| `documento_relacionado_codigo` | **P/A** | Select `50/52` y envío disponibles (`.json:252-255`; `.py:184`), sin exigirlo para importación/exportación ni validar el formato DAM/DS. El texto oficial mezcla en esta fila el tipo `50/52` y el formato completo DAM/DS, que luego también atribuye a `items.codigo_dam`. |
| `peso_bruto_total` | **M/P** | Obligatorio y enviado como texto decimal (`nubefact_guia_de_remision_schema.py:25`; `.py:160`). Cero queda invalidado por presencia, pero se aceptan negativos y no se controla precisión/rango. |
| `peso_bruto_unidad_de_medida` | **M** | Select restringido a `KGM/TNE`, obligatorio (`.json:269-272`; `nubefact_guia_de_remision_schema.py:26`). |
| `numero_de_bultos` (sólo tipo 7) | **M/P** | `Int` y obligatorio para tipo 7 (`.json:275-277`; `.py:293-298`). No se valida 1–6 dígitos/positivo. Para tipo 8 se envía una clave vacía no presente en el ejemplo oficial (`.py:162`). |
| `tipo_de_transporte` (sólo tipo 7) | **M/P** | `01/02` y obligatorio para tipo 7 (`.json:258-261`; `.py:293-311`). Para tipo 8 también se envía vacío (`.py:163`). |
| `fecha_de_inicio_de_traslado` | **M/P** | Obligatoria para ambos tipos y formateada correctamente (`nubefact_guia_de_remision_schema.py:27`; `.py:156-158`). No se valida relación temporal. |
| **`fecha_de_entrega_al_transportista`** | **X/A** | **Ausente de DocType, payload, esquema e importación**, pese a v1.7. El cuadro formal dice tipo 7 + transporte público y “Obligatorio”; contradictoriamente, el ejemplo oficial de tipo 8 también contiene el campo y lo describe erróneamente como “Fecha de inicio del traslado”. |
| `transportista_documento_tipo`, `_numero`, `_denominacion` | **X/P** | Se exigen correctamente para tipo 7 público (`.py:300-305`; `nubefact_guia_de_remision_schema.py:43-47`), pero el tipo permite `6,1,4,7,A,0` cuando el manual sólo permite RUC `6`; tampoco se validan RUC de 11 caracteres ni denominación ≤100 (`.json:284-297`). |
| `transportista_placa_numero` | **M/P** | Obligatoria para tipos 7/8 (`nubefact_guia_de_remision_schema.py:28`) y enviada (`.py:190`). No se valida 6–8, mayúsculas, ausencia de guiones ni que no sean ceros (`.json:300-303`). |
| `tuc_vehiculo_principal` | **M/P** | Representado y opcional (`.json:305-308`; `.py:191`), pero no se restringe a tipo 8 ni a 10–15 caracteres alfanuméricos mayúsculos sin guion. El importador JSON lo descarta. |
| `conductor_documento_tipo`, `_numero`, `_nombre`, `_apellidos`, `_numero_licencia` | **X/P** | La condicionalidad principal sí coincide: requeridos para tipo 7 privado y todo tipo 8 (`.py:306-323`; `nubefact_guia_de_remision_schema.py:49-56`). Los Select principal/secundario omiten los códigos oficiales `A` y `0` (`.json:315-319`; `../nubefact_guia_de_remision_conductor_secundario.json:17-22`). No se validan longitudes ni licencia de 9–10 caracteres. |
| `conductor_denominacion` | **P/A** | Existe y se envía (`.json:326-329`; `.py:194`), pero no se exige ni se importa. El cuadro oficial la presenta como condicional bajo las mismas reglas del conductor, mientras ambos ejemplos oficiales omiten este campo y usan nombre/apellidos: requisito ambiguo. |
| `destinatario_documento_tipo`, `_numero`, `_denominacion` (tipo 8) | **M/P** | Se exigen y sólo se agregan al payload tipo 8 (`.py:210-217,313-323`; `nubefact_guia_de_remision_schema.py:58-63`). Códigos completos; sin validación de longitudes o número por tipo. |
| `mtc` | **M/P** | Campo opcional enviado si tiene valor (`.json:350-352`; `.py:198`), sin máximo 20 ni mayúsculas alfanuméricas. El importador JSON lo descarta. |
| `sunat_envio_indicador` | **X/P** | El manual permite `01–05` en tipo 8 y `04–07` en tipo 7. El Select sólo ofrece `01–06`: falta `07` (`SUNAT_Envio_IndicadorVehiculoConductoresTransp`) y permite combinaciones inválidas por tipo (`.json:355-359`). No se valida su condicionalidad; el importador lo descarta. El código `06` incorporado en changelog 1.6 sí está. |
| `subcontratador_documento_tipo`, `_numero`, `_denominacion` | **M/P** | Todos están en UI/payload y el tipo queda restringido a `6` (`.json:361-384`; `.py:200-202`). No se exigen cuando indicador=`02`, no se impide usarlos fuera de ese caso y no se validan 11/250 caracteres. El importador los descarta. |
| `pagador_servicio_documento_tipo_identidad`, `_numero_identidad`, `_denominacion` | **M/P** | Campos, códigos y payload están (`.json:386-409`; `.py:203-205`), pero no se exigen cuando indicador=`03`, no se prohíben fuera de ese caso y no se validan longitudes. El importador los descarta. |
| `punto_de_partida_ubigeo`, `_direccion` | **M/P** | Obligatorios y enviados; pueden inferirse del Local (`nubefact_guia_de_remision_schema.py:29-30`; `.py:98-118,164-165`). Sin longitud 6/150 ni catálogo de ubigeo. |
| `punto_de_partida_codigo_establecimiento_sunat` | **M/P** | Representado, inferible y enviado si existe (`.json:426-428`; `.py:109-118,185`). No se exige para motivos `04/18` ni se validan 4 caracteres. |
| `punto_de_llegada_ubigeo`, `_direccion` | **M/P** | Obligatorios y enviados (`nubefact_guia_de_remision_schema.py:31-32`; `.py:166-167`), sin longitud/catálogo. |
| `punto_de_llegada_codigo_establecimiento_sunat` | **M/P** | Representado y enviado si existe (`.json:445-447`; `.py:186`), pero sin condición `04/18` ni longitud 4. |
| `enviar_automaticamente_al_cliente` | **M/A** | Siempre envía las cadenas JSON `"true"/"false"` (`.py:168-170`), igual que los ejemplos oficiales. El cuadro declara tipo Boolean, lo que normalmente implicaría literales JSON `true/false` sin comillas: contradicción documental. |
| `formato_de_pdf` | **X** | El manual GRE limita a `A4` o `TICKET`; la UI permite además `A5` (`.json:467-470`). Se envía incluso vacío, como los ejemplos (`.py:171`). |
| `items`, `documento_relacionado`, `vehiculos_secundarios`, `conductores_secundarios` | **M/P** | Las cuatro estructuras se serializan con los nombres oficiales (`.py:130-145,219-260`). Las reglas particulares se detallan abajo. |

**Brecha transversal de validación.** El esquema sólo contiene listas de presencia (`nubefact_guia_de_remision_schema.py:16-77`): no implementa las longitudes, regex, rangos, catálogos, prefijos, fechas ni casi ninguna dependencia condicional del manual. Además, el usuario puede activar `skip_field_validation` (`nubefact_guia_de_remision.json:461-465`) y `custom` puede sobrescribir cualquier clave del payload y de cada fila (`nubefact/utils/__init__.py:73-102`). Esto es útil como escape de compatibilidad, pero no equivale a cobertura tipada/validada.

## Reglas de estructuras anidadas

### Ítems

- **M — forma:** se envían `unidad_de_medida`, `codigo`, `descripcion`, `cantidad`, `codigo_dam` con cantidad convertida a texto (`nubefact_guia_de_remision.py:130-145`). La validación exige exactamente los tres campos obligatorios declarados: unidad, descripción y cantidad (`nubefact_guia_de_remision_schema.py:65`; `.py:271-276`).
- **P — unidad:** `Data` permite NIU/ZZ y cualquier unidad del Catálogo 65, pero no comprueba que las unidades de ese catálogo se usen para importación/exportación (`../nubefact_guia_de_remision_item.json:17-20`).
- **P — DAM/DS:** `codigo_dam` existe, pero no se exige para motivos `08/09` ni se valida el formato oficial de 23 caracteres (`../nubefact_guia_de_remision_item.json:41-44`).
- **P — límites:** no se validan código/descripcion ≤250 ni cantidad positiva con hasta 12 enteros/10 decimales. El Float puede perder precisión respecto del valor decimal textual del manual (`../nubefact_guia_de_remision_item.json:29-38`).
- **X menor — ayuda UI:** la ayuda afirma que `items.codigo` es obligatorio (`nubefact_guia_de_remision.js:104-108`), aunque manual y backend lo consideran opcional.

### Documentos relacionados

- **M — forma/códigos:** tabla y payload cubren exactamente `tipo`, `serie`, `numero`; el Select contiene `01`, `03`, `09`, `31` (`../nubefact_guia_de_remision_documento_relacionado.json:15-31`; `nubefact_guia_de_remision.py:219-231`). Toda fila suministrada exige los tres (`nubefact_guia_de_remision_schema.py:67`).
- **P — formato:** no se verifican serie de 4 caracteres, número entero sin ceros iniciales/1–8 dígitos ni coherencia serie/tipo. `numero` se almacena como `Data`, no `Int` (`../nubefact_guia_de_remision_documento_relacionado.json:22-31`).

### Vehículos secundarios

- **M — forma:** `placa_numero` obligatoria y `tuc` opcional se serializan correctamente (`nubefact_guia_de_remision.py:233-245`; `nubefact_guia_de_remision_schema.py:69`).
- **X/P — máximo y ámbito:** el manual permite **máximo dos**; no hay límite de filas. Tampoco se validan placa 6–8/sin guiones/no ceros ni TUC 10–15 alfanumérico mayúsculo. `tuc` se enviará también para tipo 7 si el usuario lo llena, aunque el manual lo reserva al transportista (`../nubefact_guia_de_remision_vehiculo_secundario.json:13-29`).

### Conductores secundarios

- **M — forma:** las cinco claves oficiales se serializan (`nubefact_guia_de_remision.py:246-260`).
- **X/P — máximo, códigos y condición:** el manual permite **máximo dos**, pero la tabla no tiene límite. El Select omite `A/0`; toda fila suministrada exige siempre los cinco campos, sin condicionar tipo 7 a transporte privado ni definir expresamente el comportamiento tipo 8 (`nubefact_guia_de_remision_schema.py:71-77`; `../nubefact_guia_de_remision_conductor_secundario.json:17-45`). El ejemplo oficial tipo 8 sí incluye conductores secundarios, aunque el cuadro sólo enuncia la condición para tipo 7: **ambigüedad documental**.

## Respuesta, generación y consulta

### Campos de respuesta

| Campo oficial | Estado | Cobertura actual |
|---|---:|---|
| `tipo_de_comprobante`, `serie` | **P** | Ya existen como datos de solicitud, pero la respuesta no se verifica ni actualiza con ellos (`nubefact_guia_de_remision.py:338-362`). |
| `numero` | **M** | Se toma de la respuesta, con fallback al número local, y recompone el título (`.py:342-349`). |
| `enlace`, `aceptada_por_sunat` | **M** | Persistidos y usados para estado (`.py:342-350,357`). |
| `sunat_description`, `sunat_note`, `sunat_responsecode`, `sunat_soap_error` | **M/P** | Persistidos (`.py:352-356`). Sólo `sunat_soap_error` alimenta `error_message`; una respuesta HTTP exitosa con `aceptada_por_sunat=false` y rechazo en descripción/código queda como “Pendiente” (`.py:346-356`; `nubefact/utils/nubefact/__init__.py:56-63,96-125`). El manual no define cómo distinguir rechazo terminal de espera. |
| `pdf_zip_base64`, `xml_zip_base64`, `cdr_zip_base64` | **X** | No hay campos ni extracción; sólo permanecen en `response_payload` del API Log. No se decodifican ni adjuntan. |
| `cadena_para_codigo_qr` | **M** | Persistida (`nubefact_guia_de_remision.py:361`; `.json:623-627`). |
| `enlace_del_pdf`, `enlace_del_xml`, `enlace_del_cdr` | **M** | Persistidos y luego descargados/adjuntados asíncronamente si son HTTP(S) (`.py:358-360,426-440`; `nubefact/utils/__init__.py:105-164`). |
| `nota_importante` de los ejemplos de generación | **P** | No se muestra ni persiste en la GRE, aunque queda en el API Log. No aparece en el cuadro formal de campos de respuesta. |

**Ambigüedades/errores editoriales de la respuesta oficial:** el cuadro se titula “...PARA FACTURAS, BOLETAS Y NOTAS” aunque describe GRE; las descripciones de `pdf_zip_base64` y `xml_zip_base64` intercambian “xml”/“pdf”; el ejemplo de consulta usa `.crd` para CDR y dos URLs sin `/guia/`. La implementación consume las URLs devueltas sin reconstruirlas, por lo que esos errores de ejemplo no la afectan.

### Flujo de dos pasos

- **M — generar:** botón y endpoint permiten enviar sólo estados Borrador/Error, construyen `generar_guia`, registran solicitud/respuesta y pasan a Aceptada o Pendiente (`nubefact_guia_de_remision.js:20-24,58-85`; `nubefact_guia_de_remision.py:365-396`).
- **M — consultar:** `consultar_guia` envía tipo, serie y número exactamente como el ejemplo oficial (`nubefact_guia_de_remision.py:443-458`). Existe botón manual (`nubefact_guia_de_remision.js:26-33`).
- **P — polling backend:** cron cada cinco minutos consulta hasta 20 pendientes más antiguos (`nubefact/hooks.py:170-176`; `nubefact_guia_de_remision.py:406-423`). Cumple el segundo paso, aunque puede retrasarlo respecto de “segundos o minutos”.
- **X — polling en formulario:** no funciona por los nombres/valores de estado incompatibles indicados en el resumen (`nubefact/public/js/nubefact.bundle.js:28-30`; `nubefact_guia_de_remision.json:112-119`).
- **P — estado terminal:** toda respuesta válida con `aceptada_por_sunat=false` se marca Pendiente, incluso si trae error SUNAT en campos distintos de `sunat_soap_error`; puede seguir siendo consultada indefinidamente (`nubefact_guia_de_remision.py:342-356,406-418`).
- **M — HTTP/autenticación:** POST a la ruta configurada con `Authorization` y `Content-Type: application/json`, timeout y log completo (`nubefact/utils/nubefact/__init__.py:31-85`). La ruta admite URL completa o UUID bajo `https://api.nubefact.com/api/v1` (`nubefact/nubefact/doctype/nubefact_local/nubefact_local.py:61-79`).

## Baja/cancelación

**M.** El manual es inequívoco: “Las Guías de Remisión Electrónica (GRE) se pueden dar de baja únicamente desde la SUNAT con la Clave Sol.” Por tanto, que no exista operación API, botón ni estado de anulación GRE es coherente, no una funcionalidad faltante. El API Log sólo enumera `generar_guia` y `consultar_guia` para GRE (`nubefact/nubefact/doctype/nubefact_api_log/nubefact_api_log.json:34-39`), y la UI sólo ofrece enviar, consultar y descargar (`nubefact_guia_de_remision.js:20-56`). La aplicación tampoco registra localmente que una baja se haya realizado directamente en SUNAT; el manual no documenta una respuesta/API para sincronizarla.

## Importadores

La importación no forma parte del contrato de NubeFact, pero sí afecta si un JSON oficial puede convertirse sin pérdida en una GRE Frappe.

### JSON

- **M parcial:** importa los campos básicos, ambas fechas antiguas, destinatario, puntos, códigos de establecimiento, cuatro tablas y booleano de envío (`nubefact_guia_de_remision_import.py:49-160`).
- **X — pérdida de campos oficiales:** descarta `fecha_de_entrega_al_transportista` (además inexistente), `tuc_vehiculo_principal`, `conductor_denominacion`, `mtc`, `sunat_envio_indicador`, los tres campos `subcontratador_*` y los tres `pagador_servicio_*`. También descarta claves desconocidas en vez de conservarlas en `custom` (`.py:49-113`).
- **P — aceptación indiscriminada:** sólo comprueba que el JSON sea un objeto; no valida `operacion=generar_guia`, tipo 7/8 ni esquema (`.py:163-172`). La creación solicita explícitamente omitir validación (`.py:31-45`), por lo que puede producir borradores incompletos que deberán corregirse antes del envío.
- **M — fechas:** normaliza `DD-MM-YYYY` a fecha Frappe (`.py:175-184`).

### XML SUNAT `DespatchAdvice`

- **M parcial:** rechaza CDR/otros XML, infiere 7/8 por serie T/V y extrae número, fechas, cliente, peso, motivo, modalidad, puntos, transportista, ítems y documentos relacionados (`nubefact_guia_de_remision_import_xml.py:10-144,147-193,244-271`).
- **P — borrador incompleto:** no extrae placa/conductor principal, TUC/MTC/indicadores, códigos de establecimiento, fecha 1.7, vehículos o conductores secundarios ni `codigo_dam`; una GRE importada normalmente requiere edición antes de superar la validación (`.py:34-144`).
- **P — inferencia tipo 8:** para tipo 8 copia `DeliveryCustomerParty` tanto a `cliente_*` como a `destinatario_*` (`.py:28-64,135-143`). **Inferencia:** esto puede confundir remitente y destinatario, que el manual define como entidades diferentes para GRE Transportista; debe verificarse con XML reales porque el manual JSON no especifica el mapeo UBL.
- **P:** ante ausencia de bultos fuerza `"1"` (`.py:83-87`), aunque el campo sólo aplica formalmente a tipo 7.

## Cobertura que sí coincide

Además de los **M** anteriores:

- El modelo tiene todos los campos de cabecera anteriores a 1.7 salvo las discrepancias explícitas, y representa los aportes 1.4 (documentos), 1.5 (vehículos/conductores secundarios) y 1.6 (indicador `06`) (`nubefact_guia_de_remision.json:241-514`).
- Los payloads hijos permiten extensiones mediante JSON `custom`, útil ante campos nuevos (`nubefact_guia_de_remision.py:130-145,219-262`).
- Solicitudes y respuestas completas quedan auditadas y vinculadas a la GRE (`nubefact/utils/nubefact/__init__.py:70-85`; `nubefact/nubefact/doctype/nubefact_api_log/nubefact_api_log.py:26-67`).
- Los enlaces oficiales PDF/XML/CDR se conservan y se adjuntan en privado sin bloquear el flujo si falla una descarga (`nubefact/utils/__init__.py:105-164`).

## Prioridades de corrección inferidas

1. Agregar `fecha_de_entrega_al_transportista` a DocType, payload, validación e importadores, resolviendo con NubeFact si tipo 8 debe enviarla por la contradicción del ejemplo.
2. Corregir catálogos (`motivo` 03/17, indicador 07 y reglas por tipo, conductor A/0, transportista sólo 6, formatos PDF) y exigir `numero`.
3. Implementar dependencias y límites de alto riesgo: fecha, serie/prefijo, peso, placa/licencia/TUC, motivo 13, importación/exportación, indicadores 02/03, códigos de establecimiento y máximo dos secundarios.
4. Corregir el watcher GRE y definir un estado de rechazo terminal basado en la respuesta real de producción.
5. Hacer que el importador JSON sea sin pérdida para todos los campos oficiales y añadir pruebas de payload tipo 7 público/privado, tipo 8, consulta, respuesta pendiente/aceptada/rechazada e importación.

Estas prioridades son **inferencias de ingeniería**; no agregan requisitos distintos de los hechos citados del manual.