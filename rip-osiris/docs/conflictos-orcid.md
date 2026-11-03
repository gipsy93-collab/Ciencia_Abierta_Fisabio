# Conflictos de ORCID entre el portal y Fundanet (03-11-2026)

Tres personas tienen un ORCID distinto en el portal y en el CRIS. Se resolvieron consultando el registro público de ORCID y OpenAlex, no por preferencia de fuente.

## Método

Para cada par se compararon tres cosas:

1. **Obras en el registro ORCID** (con DOI) y solapamiento entre los dos identificadores.
2. **Autor en OpenAlex** y número de obras, que es la fuente que usa el pipeline.
3. **Empleo declarado** en el perfil ORCID.

## Caso 1 · José Marcelo Galbis Caravajal — **corregido**

| | Portal (base) | Fundanet |
|---|---|---|
| ORCID | `0000-0002-0762-8023` | `0000-0002-1058-0171` |
| Obras en ORCID | **0** | 58 |
| Autor en OpenAlex | **no existe** | 153 obras · 1.045 citas |
| Vínculos en nuestra base | 32 (todos `portal_doi`) | — |

**Decisión:** el ORCID del portal está **vacío**. Se corrige al de Fundanet.

- `researchers.orcid` → `0000-0002-1058-0171`
- `orcid_source` → `confirmado_institucion`
- Registrado en `orcid_verifications` (`metodo='institucion'`, `fuente='fundanet'`, confianza 0,90)
- **153 vínculos nuevos**, 108 obras nuevas (45 ya existían por la vía del portal)
- Backup `rip_osiris.backup-2026-11-03-c.sqlite`; integridad ok

**Efecto en el mapa:** pasa de declarado a confirmado (589 → 588 declarados; 80 → 81 recuperados). Su centro, La Ribera, sube de 751 a 806 obras únicas; la mediana no se mueve.

## Caso 2 · Antonio Hernández Mijares — **se mantiene**

| | Portal (base) | Fundanet |
|---|---|---|
| ORCID | `0000-0003-4099-1905` | `0000-0003-2197-0607` |
| Obras en ORCID | 113 | 61 |
| Obras en común | — | **42 (68,9 % del menor)** |
| Autor en OpenAlex | **243 obras · 8.294 citas** | 53 obras · 552 citas |
| Empleo | Universidad de Valencia, Profesor Honorario (2019–) | — |

**Decisión:** se mantiene el del portal. El de Fundanet es una **cuenta duplicada parcial**. Cambiar reduciría la producción en ~190 obras.

**Acción pendiente:** que la persona fusione las dos cuentas en ORCID. Solo él puede hacerlo.

## Caso 3 · Carmen Íñiguez Hernández — **se mantiene**

| | Portal (base) | Fundanet |
|---|---|---|
| ORCID | `0000-0002-5156-0732` | `0000-0003-3471-4928` |
| Obras en ORCID | 97 | **244** |
| Obras en común | — | **94 (96,9 % del menor)** |
| OpenAlex | mismas dos fichas de autor para ambos ORCID | idem |
| Empleo | — | Universitat de València, Statistics and Computational Research |

**Decisión:** se mantiene el del portal porque **OpenAlex ya trata ambos ORCID como la misma persona** (devuelve las mismas dos fichas de autor para los dos). Para el pipeline son equivalentes.

**Acción pendiente:** en el registro ORCID, el de Fundanet está más completo (244 frente a 97). Conviene fusionarlos, conservando el que ella prefiera como principal.

## Regla que se deriva

> Ante dos ORCID para la misma persona, **no gana la fuente, gana la evidencia**: obras en el registro, autor en OpenAlex y solapamiento. Si el solapamiento es alto, es un duplicado y hay que fusionar; si uno está vacío, está mal.

## Resumen

| Persona | Decisión | Motivo |
|---|---|---|
| Galbis Caravajal | **Corregido a Fundanet** | El del portal no tiene obras ni autor |
| Hernández Mijares | **Se mantiene el del portal** | El de Fundanet es parcial (53 frente a 243) |
| Íñiguez Hernández | **Se mantiene el del portal** | OpenAlex los trata como la misma persona |
