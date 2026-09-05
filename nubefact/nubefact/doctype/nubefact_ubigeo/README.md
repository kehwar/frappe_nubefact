# INEI UBIGEO dataset

`ubigeos_inei_2025.csv` contains the district-level records from the official
INEI **Sistema de Consulta de Códigos Estandarizados**, period 2025.

- Source page: <https://webapp.inei.gob.pe:8443/sisconcode/publico.htm>
- Official national Excel export:
  <https://webapp.inei.gob.pe:8443/sisconcode/web/ubigeo/listaBusquedaUbigeoPorUbicacionGeograficaXls/8/1/1/null/null/null>
- Retrieved: 2026-09-05
- Original Excel SHA-256: `c037e6ad965c0b652f1c7c71773a4a1f397642238f4ff75c203ff3d6683e944e`
- Normalized CSV SHA-256: `db880993966e4d947899faf2efe51912cc89896a481bd7f67c01215a81a40e64`
- Records: 1,892 unique six-digit district UBIGEO codes

The CSV retains the department, province, and district spelling and accents from
the INEI export. Report headings, blank rows, and repeated page headers were
removed. Each code combines the two-digit department, province, and district
components supplied by INEI. The loader normalizes geographic names to uppercase
when creating `Nubefact Ubigeo` records.
