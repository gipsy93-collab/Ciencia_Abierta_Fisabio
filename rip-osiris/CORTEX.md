# CORTEX · rip-osiris

> **Memoria técnica del proyecto.** La memoria general de Gipsy vive en el vault:
> `C:\Users\gipsy\Documents\Obsidian Vault\CORTEX.md`
>
> Documentación narrativa del pipeline:
> `...\Obsidian Vault\03 Proyectos\FISABIO\Arquitectura-Pipeline-ORCID.md`
>
> Nota técnica del mapa:
> `docs\mapa-orcid.md`

**Actualizado:** 01-11-2026
**Rama de trabajo:** `feat/rip-demo-rastreo` (el mapa publicado está en `main`)
**Ruta:** `C:\Users\gipsy\repos\Ciencia_Abierta_Fisabio\rip-osiris`

---

## 1. Estado actual

| Indicador | Valor |
|---|---|
| Roster del portal | **1.087** |
| ORCID declarado en la ficha | **589 (54,2 %)** |
| ORCID ampliado (declarado + recuperado) | **669 (61,5 %)** |
| Personas con producción (ORCID o portal) | **914 (84,1 %)** |
| Publicaciones únicas del portal | **11.154** |
| Pares persona-obra del portal | **20.616** |
| Publicaciones del portal con DOI | **9.534 (85,5 %)** |
| Publicaciones del portal con año/tipo | **20.616 (100 %)** |
| DOIs del portal resueltos en OpenAlex | **9.479 (99,4 %)** |
| Pares persona-obra vía ORCID | **31.882** |
| Obras únicas vía ORCID | **22.216** |
| Unión de ambas vías (pares) | **38.928** |
| Unión de ambas vías (obras) | **25.472** |
| Candidatos ORCID inverso | **102** |
| Ya escritos | **77** (25 DOI + 42 solape/coautor + 6 nombre/afiliación + 4 variante/invertido/incompleto/OpenAlex) |
| A revisar | **16** |
| Descartados | **6** |
| Sospechosos | **3** |

---

## 2. Estado de la base

`data/rip_osiris.sqlite` · **escrita el 01-11-2026** con backup previo en `data/rip_osiris.backup-2026-11-01.sqlite`.

| Tabla | Filas | Estado |
|---|---:|---|
| `researchers` | 1.087 | **669 con ORCID**: 589 `portal_ficha` + 25 `reverso_doi` + 45 `reverso_multisenal` + 6 `reverso_nombre_afiliacion` + 1 `reverso_nombre_variante` + 1 `reverso_openalex` + 1 `reverso_nombre_invertido` + 1 `reverso_nombre_incompleto` |
| `works` | **26.260** | 21.453 con DOI; 1.620 portal-only sin DOI, ya con año/tipo; 3 sin título |
| `work_ids` | **55.762** | 23.155 OpenAlex + 21.453 DOI + 11.154 portal |
| `author_work` | **54.087** | 31.863 `orcid_exacto` + 1.614 `orcid_reverso` + 17.514 `portal_doi` + 3.096 `portal_publicacion` |
| `outputs` | 212 | censo previo de centros, no toca este pipeline |

`PRAGMA integrity_check` = **ok** · `PRAGMA foreign_key_check` = **0 incidencias**.

**Fuera de la escritura:** los 22 candidatos pendientes de revisión (11 con señales mixtas, 10 a revisar y 1 probable) y los 3 sospechosos. No se ha borrado ni modificado nada previo.

**Pendiente de escritura incremental:** completada el 01-11-2026: **788 obras nuevas** y **1.614 pares `orcid_reverso`**, reutilizando las 25.472 obras existentes sin duplicarlas.

---

## 3. Artefactos (fuente de verdad)

| Archivo | Contenido |
|---|---|
| `data/cosecha_orcid.csv` | 1.087 fichas con ORCID declarado |
| `data/anclaje_orcid.csv` | 475 autores OpenAlex con métricas |
| `data/author_work.jsonl` | 31.882 pares persona-obra vía ORCID |
| `data/portal_publicaciones.jsonl` | 20.616 pares / 11.154 publicaciones del portal |
| `data/portal_doi_openalex.json` | DOI → obra OpenAlex + authorships |
| `data/orcid_reverso_candidatos.csv` | 102 candidatos ORCID con apoyo |
| `data/orcid_reverso_validado.csv` | Validación contra `pub.orcid.org` |
| `data/orcid_reverso_multisenal.csv` | Clasificación final (DOI + nombre + afiliación + apoyo) |
| `data/mapa_orcid_dataset_v2.json` | Dataset del mapa con las tres capas |
| `data/mapa_orcid_v2.html` | Mapa interactivo autocontenido |
| `data/cv_provincias.geojson` | Provincias de Castellón, Valencia y Alicante |

---

## 4. Scripts

En `scripts/`:

| Script | Qué hace |
|---|---|
| `pipeline_portal.py` | Cosecha publicaciones + DOI → OpenAlex + ORCID inverso + validación |
| `valida_multisenal.py` | Reclasifica los 102 candidatos con nombre + afiliación + solape DOI + apoyo |
| `agrega_orcid_pendientes.py` | Añade los candidatos con evidencia fuerte (nombre alto + ≥1 DOI) |
| `agrega_orcid_variantes.py` | Añade los 6 casos claros de variante / 1-de-1 DOI |
| `agrega_orcid_coautores.py` | Añade los 28 con DOI ≥50 % + coautores + nombre compatible |
| `revision_orcid_personas.py` | Genera la ficha por persona (portal, ORCID, DOI, coautores) |
| `fase1_dataset_v2.py` | Genera `mapa_orcid_dataset_v2.json` |
| `genera_mapa_v2.py` | Genera `mapa_orcid_v2.html` |
| `piloto_orcid_reverso.py` | Piloto de recuperación inversa (30 sin ORCID) |
| `parser_pubs.py` | Parser de la lista de publicaciones del portal |
| `reparse_publicaciones.py` | Re-parsea la caché y recupera año/tipo sin DOI |
| `actualiza_works_year.py` | Vuelca año/tipo del portal a `works` (solo nulos) |
| `genera_hoja_confirmacion.py` | Genera la hoja de confirmación ORCID (80 + 3) |
| `importa_confirmaciones.py` | Importa confirmaciones/rechazos con backup y transacción |
| `valida_orcid_checksum.py` | Valida el dígito de control de los 669 ORCID |
| `sensibilidad_medianas.py` | Sensibilidad de las medianas a recuperados, no-DOI y homónimos |
| `cruza_fundanet.py` | Cruce de los 9 ORCID de Fundanet con la base |
| `importa_centros_fundanet.py` | Importa el centro de Fundanet como afiliación con procedencia (dry-run/`--write`) |
| `registra_verificaciones_orcid.py` | Crea `orcid_verifications` y registra confirmaciones (oauth/persona/institucion) |
| `backup_util.py` | Nombre de backup libre del día (evita sobrescribir backups) |

---

## 5. Mapa

- **Publicado:** <https://gipsy93-collab.github.io/Ciencia_Abierta_Fisabio/mapa-orcid/>
- **Portada:** <https://gipsy93-collab.github.io/Ciencia_Abierta_Fisabio/> (tercera pieza)
- **Repo:** `gipsy93-collab/Ciencia_Abierta_Fisabio`, `main`, carpeta `mapa-orcid/`, commit `0ccc497`
- **Local:** `data/mapa_orcid_v2.html`
- **Tres capas:** ORCID declarada (589) · ampliada (620) · producción (914)
- **Dos medianas:** ORCID (inflada) vs unión (corregida)
- **Anillo cian:** producción; el hueco es lo que el ORCID no ve
- **Punto cian:** coordenada exacta del edificio

---

## 6. Pendientes

- [x] **Escritura en la base** con backup y transacción (01-11-2026): **669 ORCID** (589 + 25 + 45 + 6 + 1 + 1 + 1 + 1), 26.260 obras, 55.762 IDs, 54.087 vínculos.
- [ ] Revisión humana de `data/revision_orcid_personas.md` (**16 descartados + 3 en revisión**) + 3 sospechosos. Añadidos en la revisión final: Ángel Moya, María Cuenca y Juan Francisco Navarro; Carmen Hernández queda fuera por afiliación UAB y una sola obra.
- [ ] **Confirmación ORCID:** hoja `data/hoja_confirmacion_orcid.csv` con **83 personas** (80 recuperadas + 3 en revisión). Rellenar `decision` (`confirmar`/`rechazar`/`revisar`) y `confirmado_por` (`persona`/`institucion`), y ejecutar `python scripts/importa_confirmaciones.py --write`.
- [x] Validar el dígito de control de los 669 ORCID: **669/669 válidos**.
- [x] Análisis de sensibilidad: mediana estable a recuperados y homónimos; la incertidumbre principal son las obras sin DOI.
- [x] 3.096 publicaciones del portal sin DOI ni año: re-parseadas desde la caché; ahora tienen año y tipo (`works.year` nulo 1; `works.type` nulo 788).
- [x] **Piloto de centro con Fundanet** (02-11-2026): los 9 ORCID del volcado coinciden 9/9 con la base (0 gaps, 0 conflictos); 4 no tenían centro y se añadió con `source='fundanet'` (Sequi → Francesc de Borja; Falco → Vinalopó; Miro y Romero → Virgen de los Lirios). «Sin centro» 188 → **184**. Backup `rip_osiris.backup-2026-11-02-b.sqlite`.
- [ ] **Escalar el centro a los 184 restantes:** hace falta el export de Fundanet con **Colectivo de Pertenencia completo** (el volcado trae «Centro del Tercero» truncado).
- [x] **Taxonomía de verificación ORCID** (02-11-2026): `orcid_source` sigue siendo **procedencia**; la tabla nueva `orcid_verifications` guarda **quién confirmó** (`metodo`: `oauth` 1,00 · `persona` 0,95 · `institucion` 0,80), con `fuente`, `evidencia`, `confianza` y `fecha`. Cargadas **9 verificaciones institucionales** (Fundanet); **0 OAuth**. `importa_confirmaciones.py` ya escribe en la tabla.
- [x] **Mapa v3** (02-11-2026): regenerado con «sin centro» 184 y «ORCID confirmado» en el tooltip; publicado en `main` (`5e11bf5`).
- [ ] 19 grupos sin centro declarado: Fundanet o sede de la GVA.
- [ ] Rastrear la web pública de FISABIO y la memoria de gestión (pendiente acordado).
- [ ] Mover los scripts de `scripts/` al flujo del proyecto (tests, CLI) si se consolida.

---

## 7. Decisiones metodológicas

1. **Mediana, no media.** Distribución asimétrica; Elda 13/17/214 → media 81, mediana 17.
2. **Dos medianas.** La ORCID está inflada por selección; la unión corrige con el portal.
3. **ORCID como llave.** El nombre falla por homónimos; el ORCID resuelve el 81 % de los que lo declaran.
4. **ORCID inverso multiseñal.** Nombre + afiliación + solape DOI + apoyo. Un candidato con una sola obra es hipótesis; con ≥2 y validación es dato.
5. **No inferir centro por nombre.** El centro se deriva del grupo público; 188 quedan sin centro y se declaran. **Excepción:** el centro declarado por la institución (Fundanet) sí se importa, con `source='fundanet'`, evidencia literal y confianza menor si el valor viene truncado.
6. **El portal no es el universo.** 146 personas sin ORCID no tienen publicaciones en el CRIS; 3.096 publicaciones no tienen DOI, aunque ya tienen año/tipo; 788 obras ORCID no tienen tipo.
7. **La cobertura no es calidad.** Mide adopción de infraestructura, no actividad investigadora.

---

## 8. Comandos rápidos

```powershell
cd C:\Users\gipsy\repos\Ciencia_Abierta_Fisabio\rip-osiris
$env:PYTHONPATH="."

# Regenerar dataset y mapa
python scripts\fase1_dataset_v2.py
python scripts\genera_mapa_v2.py

# Reclasificar candidatos ORCID
python scripts\valida_multisenal.py

# Pipeline completo (si hay que rehacerlo)
python scripts\pipeline_portal.py all
```
