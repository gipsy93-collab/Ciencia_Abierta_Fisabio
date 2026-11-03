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
| **Relleno de la burbuja** | Cobertura seleccionada: ORCID declarada (589), ORCID ampliada (669) o producción (914) |
| **Tamaño de la burbuja** | Mediana de obras: ORCID (solo personas con ORCID) o unión (ORCID + portal) |
| **Anillo cian** | Cobertura de producción; el hueco del anillo es lo que el ORCID no ve |
| **Punto cian** | Coordenada exacta del edificio (geocodificada) |
| **Línea guía** | Une el punto exacto con la burbuja cuando dos centros se solapan |

### Las tres coberturas

- **ORCID declarada:** personas con ORCID en su ficha del portal. 589 / 1.087 = **54,2 %**.
- **ORCID ampliada:** declarada + recuperada por solape de DOI, coautores o nombre+afiliación. 669 / 1.087 = **61,5 %**.
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
3. **3.096 publicaciones (27,8 %) no tienen DOI**, pero ya tienen año y tipo tras el re-parse de la caché.
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

- Publicado el 01-11-2026 (commit `209b952`): fix móvil, caché completa 80/80, revisión final (669) y corrección del layout inicial.
- Corregido: `computeLayout()` se ejecuta antes de crear los grupos; al recargar, las burbujas ya no se acumulan en `(0,0)`.
- Dataset v2 con 31 centros, tres capas y 669 ORCID ampliados.
- Base escrita de forma idempotente: **669 ORCID**, **26.260 obras**, **55.762 work_ids**, **54.087 author_work** (31.863 `orcid_exacto` + 1.614 `orcid_reverso` + 17.514 `portal_doi` + 3.096 `portal_publicacion`).
- Pendiente: revisión humana de **16 descartados + 3 en revisión + 3 sospechosos**. Añadidos en la revisión final: Ángel Moya, María Cuenca y Juan Francisco Navarro; Carmen Hernández queda fuera por afiliación UAB y una sola obra.
- Pendiente: enriquecer los 3 títulos que quedaron como `(sin título)` cuando OpenAlex se recupere (caché resumible en `data/openalex_titles.json`).

## 8. Fiabilidad y sensibilidad (02-11-2026)

- **Dígito de control ORCID:** **669/669 válidos** (ISO 7064 mod 11-2). No hay erratas de tecleo.
- **Reproducibilidad:** la mediana base del análisis de sensibilidad coincide con el dataset publicado (diferencia **0,0**).
- **Sensibilidad de la mediana:**
  - Quitar los **80 ORCID recuperados**: la mayoría de centros no cambia; el mayor descenso es La Ribera (28→22), seguido de Dr. Peset (24→22), Elche (18→16), San Juan (16→14) y Elda (7→6).
  - Quitar las **obras sin DOI**: es la mayor fuente de incertidumbre (Transfusiones 95→75, CAP Elda 10→1, Sagunto 24→16, FISABIO 40→32, DG Salud Pública 22→15).
  - Quitar los **188 pares con año imposible**: **no cambia ninguna mediana**; afecta a perfiles individuales, no a los centros.
  - Los **cuatro centros de la brecha** (Elda, Vinalopó, Castellón, San Juan) se mueven como máximo **2 puntos** entre escenarios.
- **Lectura:** las medianas de los centros grandes y de los cuatro centros de la brecha son robustas; las de los centros pequeños (n<10) son frágiles y deben leerse con cautela. La incertidumbre principal son las **obras sin DOI**, no los ORCID recuperados ni los homónimos.

## 9. Piloto de centro con Fundanet (02-11-2026)

- **Fuente:** volcado de 9 investigadores con ORCID de Fundanet (nombre, «Centro del Tercero», departamento, área).
- **Cruce de identidad:** **9/9 coinciden** con la base, mismo ORCID y fuente `portal_ficha`; **9/9 checksum válidos**; **0 gaps, 0 conflictos**. El ORCID de Fundanet es un subconjunto del portal: **no añade cobertura de identificador**.
- **Lo que sí aporta:** el **centro**. 4 de los 9 no tenían centro en la base y Fundanet sí lo declara.
- **Escrito** (`scripts/importa_centros_fundanet.py --write`, backup `rip_osiris.backup-2026-11-02-b.sqlite`, transacción única):

  | Persona | Centro añadido | Match |
  |---|---|---|
  | Jose Miguel Sequi Sabater | H. Francesc de Borja de Gandía | prefijo (truncado) |
  | Jaime Falco Martinez | H. Vinalopó Salud | prefijo (truncado) |
  | Carla Miro Vicedo | H. Virgen de los Lirios de Alcoi | prefijo (truncado) |
  | Ainhoa Romero Espinós | H. Virgen de los Lirios de Alcoi | prefijo (truncado) |

- **Control de idempotencia:** los otros 5 ya tenían centro y el script los detecta como `ya_tiene_centro` (mismo `org_id`); una segunda ejecución da **0 inserciones**. **0 conflictos** de centro.
- **Procedencia:** `source='fundanet'`, `method='fundanet_centro_tercero'`, `status='declarado_institucion'`, `confidence=0,85` (valor truncado). El `evidence_literal` guarda el literal **tal como vino**, con la marca de truncamiento y el departamento.
- **Efecto:** «sin centro» pasa de **188 a 184**; total de afiliaciones 1.860 → 1.864. `integrity_check` ok, 0 FK rotas.
- **Límite declarado:** el campo es «Centro del Tercero», **no** «Colectivo de Pertenencia». Para Ana Belso sabemos que el Colectivo («Hospital General de Elda») coincide con la base, pero en los otros 4 el valor viene truncado. Antes de escalar a los 184 hay que pedir el **Colectivo de Pertenencia completo**.

### 9.1. Taxonomía de verificación ORCID (02-11-2026)

Se separa **procedencia** de **confirmación**. Antes se mezclaban en `orcid_source`.

| Concepto | Dónde vive | Valores |
|---|---|---|
| De dónde salió el ORCID | `researchers.orcid_source` | `portal_ficha`, `reverso_doi`, `reverso_multisenal`, `reverso_nombre_afiliacion`, `reverso_nombre_variante`, `reverso_nombre_invertido`, `reverso_nombre_incompleto`, `reverso_openalex`, `confirmado_persona`, `confirmado_institucion`, `rechazado_revision` |
| Quién lo confirmó | `orcid_verifications` | `metodo`: `oauth` (1,00) · `persona` (0,95) · `institucion` (0,80); más `fuente`, `evidencia`, `confianza` y `fecha` |

- **Una persona puede tener varias verificaciones** (institucional + personal + OAuth). La tabla guarda historial; la procedencia no se sobrescribe.
- **Primera carga:** 9 verificaciones `institucion`/`fundanet` (los 9 ORCID del volcado, ya coincidentes con el portal). Ninguna es OAuth: **no hay verificación absoluta**.
- **El importador de la hoja** (`importa_confirmaciones.py`) escribe también en `orcid_verifications` (`metodo=persona|institucion`, `fuente=hoja_confirmacion`); un rechazo retira la verificación de ese ORCID.
- **El mapa** muestra «ORCID confirmado» en el tooltip avanzado y `orcid_verificados` en el dataset (total 9: 0 oauth, 0 persona, 9 institución).

## 10. Export completo de Fundanet (03-11-2026)

**Entrada:** `qtkfmbyx.hzt.xlsx` — 1.106 filas, 602 con ORCID, 1.092 con «Centro del Tercero».

### 10.1. Qué confirma y qué no

| Comprobación | Resultado | Lectura |
|---|---|---|
| ORCID del portal presentes en Fundanet | **586 / 589** | El CRIS replica el portal |
| Conflictos de ORCID | **3** | Galbis Caravajal, Hernández Mijares, Íñiguez Hernández: portal y CRIS discrepan |
| ORCID recuperados presentes en Fundanet | **0 / 80** | **Fundanet no puede validar lo inferido** |
| Personas sin centro que ganan uno | **179** | De 184 |
| Centros externos (universidades, empresas) | **24** | No se inventan: se listan |

**Conclusión:** Fundanet sirve para **adscripción**, no para verificar ORCID. Los 80 recuperados siguen necesitando confirmación personal.

### 10.2. Lo escrito

`scripts/importa_centros_fundanet_full.py --write` → **155 centros** (`source='fundanet'`, `method='fundanet_centro_tercero'`, `status='declarado_institucion'`, confianza 0,90, evidencia literal con departamento). Backup `rip_osiris.backup-2026-11-02-f.sqlite`. `integrity_check` ok, 0 FK.

**«Sin centro»: 184 → 29.**

No se tocan: **156 personas con centro distinto** (centro del grupo ≠ centro del tercero: alguien puede estar contratado por la universidad y trabajar en un grupo del hospital), los **3 conflictos** de ORCID, **1 ORCID nuevo** (Juan Carlos Sánchez López, UMH) y **19 filas fuera del roster** (incluidas `PRUEBA` y `SEMICROL, S.L`).

### 10.3. Efecto en las medianas

| Centro | n | Mediana unión | Cobertura ORCID | Producción |
|---|---:|---:|---:|---:|
| Alcoi | 14 → **38** | 15 → **6,5** | 85,7 % → **52,6 %** | 92,9 % → 84,2 % |
| Sagunto | 10 → 16 | 24,5 → **8** | 50,0 % → 43,8 % | 100 % → 100 % |
| La Pedrera (Denia) | 8 → 18 | 8 → **3** | 37,5 % → 27,8 % | 87,5 % → 72,2 % |
| FISABIO Salud Pública | 143 → 173 | 40 → 33 | 79,7 % → 75,1 % | 94,4 % → 91,9 % |
| Elche | 155 → 178 | 18 → 18 | 51,6 % → 48,9 % | 79,4 % → 80,3 % |
| Dr. Peset | 143 → 162 | 23,5 → **25** | 56,6 % → **58,6 %** | 92,3 % → 93,2 % |
| *(sin centro)* | 184 → **29** | 9 → **19,5** | 47,3 % → 58,6 % | 78,8 % → 82,8 % |

**Los cuatro centros de la brecha** se mueven poco: Elda mediana 7→6 (producción 70,3→71,1 %), Vinalopó 9→7 (65,5→67,7 %), Castellón 9,5→8 (83,1→78,9 %), San Juan 16→16,5 (79,2→80,0 %).

### 10.4. El hallazgo incómodo

**La cobertura del 85,7 % de Alcoi era un artefacto.** Se calculaba sobre 14 personas porque 24 de sus investigadores no tenían centro asignado. Con el denominador corregido (38), baja al **52,6 %**. Lo mismo, en menor medida, en Sagunto y La Pedrera.

Es la primera vez que una corrección de datos **invalida una afirmación previa** del mapa. La brecha de los cuatro centros se mantiene; la excelencia de Alcoi, no.

**Estado:** dataset y mapa regenerados y **publicados** el 03-11-2026 (commit `aca68ce` en `main`, <https://gipsy93-collab.github.io/Ciencia_Abierta_Fisabio/mapa-orcid/>). El pie del mapa lleva la nota de corrección. Copias previas en `*.pre-fundanet.*`.
