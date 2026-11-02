# Regla de fuentes · tres capas de acceso

> **Decisión del 02-11-2026.** Se usa la capa más simple que resuelva el problema. Se sube de capa solo cuando la anterior falla por una razón objetiva, nunca por comodidad.

## Las tres capas

| Capa | Cuándo | Ejemplos | Coste | Determinista |
|---|---|---|---|---|
| **1 · API abierta** | siempre que exista endpoint documentado | DataCite, Zenodo, OpenAlex, ORCID, Crossref, CKAN | **0 €** | Sí |
| **2 · Fetch de documento** | solo si no hay API | memorias, transparencia, PDFs | **0 €** (1.000 URL/día) | Sí, con caché |
| **3 · Navegador con agente** | login, multipaso o marcado hostil **y autorización escrita** | Fundanet | **0,016 $/paso** | **No** |

## Orden de decisión

```
¿Hay endpoint documentado y con términos de uso?
  sí → capa 1
  no → ¿es un documento estático (HTML/PDF), aunque lo pinte JS?
         sí → capa 2, con caché en disco
         no → ¿requiere sesión, formularios o marcado cambiante?
                sí → ¿hay autorización escrita?
                       sí → capa 3, con evidence_literal + captura + fecha
                       no → NO SE HACE: se solicita el export
                no → replantear el problema
```

## Por qué este orden

1. **Auditabilidad.** Una respuesta de API se puede repetir y diffear. Una extracción de agente, no.
2. **Coste.** La capa 1 y la 2 son gratis; la 3 no.
3. **Trazabilidad.** Sin clave canónica (DOI, ORCID, id propio) el dato no se puede enlazar ni verificar.

## Coste medido (02-11-2026)

| Operación | Capa | Coste |
|---|---|---|
| Censo de 238 registros → 134 recursos | 1 | **0 €** (~90 llamadas) |
| 16 URLs + PDF de 145 páginas | 2 | **0 €** |
| 2 ejecuciones del agente (6 pasos) | 3 | **0,096 $** |

La capa 3 no aportó nada que un regex de dos segundos no diera. **Se sube de capa por necesidad, nunca por comodidad.**

## Regla de evidencia

Ningún dato de capa 3 entra en la base sin:

- `evidence_literal` (el texto tal como apareció),
- URL de origen,
- captura o traza,
- fecha de consulta.

Sin eso no es dato: es una impresión.

## Criterios de admisión de una fuente nueva

- endpoint documentado o fichero estable, no scraping frágil;
- términos de uso y `robots.txt` compatibles;
- licencia de los metadatos explícita;
- clave canónica (DOI, ORCID, identificador propio);
- fecha de consulta registrada.

## Consecuencias en el código

- Las fuentes de capa 1 se implementan con `urllib`/`httpx` y caché en `data/`; nunca con navegador.
- Las fuentes de capa 2 guardan el texto extraído en `data/` para no repetir la llamada.
- Las fuentes de capa 3, si llegan, van a `researcher_affiliations` o `works` con `source` propio y `confidence < 1`.
- Un script nuevo **declara en su docstring la capa** que usa.

## Aplicación actual

| Fuente | Capa | Script |
|---|:--:|---|
| Portal FISABIO | 1 | `pipeline_portal.py`, `cosecha_orcid.py` |
| OpenAlex | 1 | `ancla_orcid.py`, `escribe_db_pipeline.py` |
| ORCID registry | 1 | `valida_multisenal.py` |
| DataCite / Zenodo / CKAN / Figshare | 1 | `censo_datasets_fisabio.py` |
| TinyFish Fetch | 2 | (prueba; pendiente de integrar en el rastreo de memorias) |
| Fundanet | 3 | pendiente de autorización y export |
