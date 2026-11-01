# Mapa ORCID · FISABIO

> Nota técnica del mapa interactivo de cobertura ORCID y producción visible de los 31 centros FISABIO.
> Acompaña a los artefactos de `data/` y al HTML `data/mapa_orcid_v2.html`.
> Documentación narrativa completa: `C:\Users\gipsy\Documents\Obsidian Vault\03 Proyectos\FISABIO\Arquitectura-Pipeline-ORCID.md`.

**Publicado en:** <https://gipsy93-collab.github.io/Ciencia_Abierta_Fisabio/mapa-orcid/>
**Repositorio:** `gipsy93-collab/Ciencia_Abierta_Fisabio`, rama `main`, carpeta `mapa-orcid/` (commit `0ccc497`).

---

## 1. Qué muestra

El mapa tiene **tres capas de cobertura** conmutables y **dos métricas de tamaño**:

| Elemento | Qué representa |
|---|---|
| **Relleno de la burbuja** | Cobertura seleccionada: ORCID declarada (589), ORCID ampliada (666) o producción (914) |
| **Tamaño de la burbuja** | Mediana de obras: ORCID (solo personas con ORCID) o unión (ORCID + portal) |
| **Anillo cian** | Cobertura de producción; el hueco del anillo es lo que el ORCID no ve |
| **Punto cian** | Coordenada exacta del edificio (geocodificada) |
| **Línea guía** | Une el punto exacto con la burbuja cuando dos centros se solapan |

### Las tres coberturas

- **ORCID declarada:** personas con ORCID en su ficha del portal. 589 / 1.087 = **54,2 %**.
- **ORCID ampliada:** declarada + recuperada por solape de DOI, coautores o nombre+afiliación. 666 / 1.087 = **61,3 %**.
- **Producción:** personas con al menos una obra por ORCID o por el portal. 914 / 1.087 = **84,1 %**.

### Las dos medianas

- **Mediana ORCID:** solo personas con obras vía ORCID. Está **inflada por selección**: quien tiene ORCID suele ser quien más publica.
- **Mediana unión:** personas con obras por cualquiera de las dos vías. Corrige el sesgo.

Ejemplos del cambio:

| Centro | Mediana ORCID | Mediana unión |
|---|---|---|
| Vinalopó | 53 | **8** |
| San Juan de Alicante | 51 | **14** |
| Elche | 42 | **16** |
| Dr. Peset | 48 | **22** |
| Elda | 17 | **6** |

### El hallazgo

La brecha entre ORCID y producción es lo que el CRIS ve y el ORCID no:

| Centro | Cobertura ORCID | Producción |
|---|---|---|
| Elda | 24,3 % | **70,3 %** |
| Vinalopó | 32,1 % | **64,3 %** |
| Castellón | 44,6 % | **83,1 %** |
| San Juan | 42,9 % | **79,2 %** |
| Dr. Peset | 56,6 % | **92,3 %** |

El mapa mide **visibilidad**, no actividad investigadora. Un centro con 80 % de ORCID no investiga más que uno con 30 %; solo es más visible para esta infraestructura.

---

## 2. Fuentes

| Fuente | Qué aporta | Límite |
|---|---|---|
| Portal FISABIO (`fisabio.portalinvestigacion.com`) | Roster, ficha, ORCID declarado, publicaciones con DOI | 1 req/s; el listado masivo no trae ORCID |
| OpenAlex (`api.openalex.org`) | Autor por ORCID, obras, citas, `authorships` | `cursor=` da 401 sin clave; usar `page=` |
| ORCID registry (`pub.orcid.org`) | Validación de nombre y afiliación | No todos los perfiles tienen afiliación pública |
| Fundanet / CRIS | Registro institucional de producción | No accesible desde el equipo corporativo |

---

## 3. Artefactos

| Archivo | Contenido |
|---|---|
| `data/mapa_orcid_v2.html` | Mapa interactivo autocontenido (D3.js + datos + GeoJSON embebidos) |
| `data/mapa_orcid_dataset_v2.json` | Dataset por centro con las tres coberturas, dos medianas, pares y obras |
| `data/mapa_orcid_dataset.json` | Dataset v1 (solo ORCID), conservado para comparación |
| `data/cv_provincias.geojson` | Provincias de Castellón, Valencia y Alicante |
| `data/portal_publicaciones.jsonl` | Publicaciones por investigador (20.616 pares, 11.154 únicas) |
| `data/portal_doi_openalex.json` | DOI → obra OpenAlex + authorships |
| `data/orcid_reverso_multisenal.csv` | 102 candidatos ORCID clasificados; 77 ya escritos (25 DOI + 42 solape/coautor + 6 nombre/afiliación + 4 variante/invertido/incompleto/OpenAlex) y quedan 16 a revisar + 6 descartados + 3 sospechosos |
| `data/cosecha_orcid.csv` | ORCID declarado de las 1.087 fichas |
| `data/anclaje_orcid.csv` | 475 autores OpenAlex con métricas |
| `data/author_work.jsonl` | 31.882 pares persona-obra vía ORCID |

---

## 4. Cómo se regenera

Requisitos: Python 3.11+, dependencias de `requirements.txt`, conexión a internet para OpenAlex/ORCID (el portal se cachea en `data/portal/`).

```powershell
cd C:\Users\gipsy\repos\Ciencia_Abierta_Fisabio\rip-osiris
$env:PYTHONPATH="."

# 1. Dataset v2 (lee los artefactos del pipeline)
python scripts\fase1_dataset_v2.py

# 2. HTML del mapa
python scripts\genera_mapa_v2.py

# 3. Publicar en GitHub Pages
#    copiar data/mapa_orcid_v2.html -> mapa-orcid/index.html en main
```

Los scripts viven en `scripts/` (`fase1_dataset_v2.py`, `genera_mapa_v2.py`, `pipeline_portal.py`, `valida_multisenal.py`, `piloto_orcid_reverso.py`, `parser_pubs.py`).

### Pipeline completo (si hay que rehacerlo)

1. **Cosecha ORCID:** 1.087 fichas a 1 req/s → `data/cosecha_orcid.csv`.
2. **Anclaje OpenAlex:** `filter=author.orcid` → `data/anclaje_orcid.csv` + `data/author_work.jsonl`.
3. **Publicaciones del portal:** `POST /get-publications` con `participant={portal_id}` → `data/portal_publicaciones.jsonl`.
4. **DOI → OpenAlex:** lotes de 50 DOIs → `data/portal_doi_openalex.json`.
5. **ORCID inverso:** DOI → authorships → ORCID; convergencia ≥2 obras y validación multiseñal → `data/orcid_reverso_multisenal.csv`.
6. **Dataset y mapa:** `fase1_dataset_v2.py` → `genera_mapa_v2.py`.

---

## 5. Límites que el mapa declara

1. **El portal no es el universo.** Su lista es el registro institucional (Fundanet/CRIS), no toda la producción.
2. **146 personas sin ORCID no tienen publicaciones en el portal.** No significa que no publiquen; significa que el CRIS no las registra.
3. **3.096 publicaciones (27,8 %) no tienen DOI ni año** en el parser actual. Se enlazan por `participant`, pero sin año.
4. **La mediana unión sigue siendo de las personas visibles**, no del censo completo del centro.
5. **n < 5** es frágil: un solo caso mueve la mediana. El tooltip lo advierte.
6. **La cobertura no es calidad:** mide adopción de una infraestructura, no actividad investigadora.
7. **El cruce sin DOI no es deduplicación completa.** Las obras sin DOI conservan el identificador de su fuente; una misma obra en el portal y OpenAlex puede quedar como dos obras.
8. **Los ORCID recuperados requieren cosecha completa para sus métricas.** Sus obras OpenAlex solo se incorporan si la caché contiene todas las páginas; el dataset informa cuántos quedan pendientes.

---

## 6. Reglas de validación y regeneración

- La afiliación cuenta como evidencia solo si ORCID declara FISABIO o el centro asignado a esa persona por el portal. La palabra genérica «hospital» no confirma una identidad.
- Dos o más DOI distintos en común, que representen al menos la mitad de los DOI del portal, pueden confirmar el candidato. Nombre y afiliación sin DOI compartido quedan como probable/revisión, no como confirmación automática.
- Se evalúan todos los ORCID candidatos de cada persona. Si más de uno supera el umbral, o el ORCID ya pertenece a otra persona, el caso queda para revisión.
- Un fallo al leer el perfil o sus publicaciones no se guarda como una lista vacía: la persona queda pendiente para reintento.
- Los scripts resuelven la raíz del proyecto desde su ubicación. `OPENALEX_MAILTO` permite configurar el correo de contacto del API.

Para actualizar los artefactos tras completar las cachés y revisar candidatos:

```powershell
python scripts\pipeline_portal.py 4
python scripts\valida_multisenal.py
python scripts\revision_orcid_personas.py
python scripts\escribe_db_pipeline.py
# Revisar el dry-run y aprobar los candidatos antes de ejecutar la escritura:
python scripts\escribe_db_pipeline.py --write
python scripts\fase1_dataset_v2.py
python scripts\genera_mapa_v2.py
```

`escribe_db_pipeline.py` crea una copia de seguridad antes de escribir. La revisión del CSV y del dry-run es necesaria porque el nuevo umbral puede cambiar qué identidades se aceptan; el mapa no actualiza la base por sí solo.

## 7. Estado

- La versión publicada anteriormente fue verificada (HTTP 200, sin errores de consola).
- Dataset v2 con 31 centros y las tres capas.
- El HTML y el dataset guardados no se regeneraron con estas correcciones; sus cifras reflejan la generación anterior hasta ejecutar el flujo actualizado.
- Hecho: escritura en la base (`researchers.orcid`, `works`, `work_ids`, `author_work`) con backup y transacción (666 ORCID · 25.472 obras · 52.473 vínculos).
- Pendiente: revisión humana de **16 a revisar + 6 descartados + 3 sospechosos** del ORCID inverso.
