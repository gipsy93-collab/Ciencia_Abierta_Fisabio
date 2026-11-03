# Ficha EHDS de los conjuntos de datos de FISABIO

> **Qué es este documento:** la descripción de los 6 conjuntos de datos del catálogo institucional de FISABIO según el marco del Espacio Europeo de Datos de Salud, con lo que se sabe, lo que falta y lo que habría que declarar antes de marzo de 2029.

---

## 1. Siglas

| Sigla | Inglés | Español | Qué es |
|---|---|---|---|
| **EHDS** | European Health Data Space | **EEDS — Espacio Europeo de Datos de Salud** | El reglamento y su infraestructura |
| **HDAB** | Health Data Access Body | **OADS — Organismo de Acceso a Datos de Salud** | Autoridad que evalúa solicitudes y expide permisos de uso secundario |
| **SPE** | Secure Processing Environment | **Entorno de tratamiento seguro** | Espacio cerrado donde se analizan los datos; solo salen resultados no personales |
| **HealthDCAT-AP** | Health DCAT Application Profile | Perfil HealthDCAT-AP | Extensión del estándar DCAT-AP para describir datos de salud |
| **DCAT-AP** | DCAT Application Profile | — | Estándar europeo de metadatos de catálogos |
| **CKAN** | Comprehensive Knowledge Archive Network | — | Software de catálogo que usa FISABIO |
| **PID** | Persistent Identifier | Identificador persistente | DOI, Handle, ARK… |
| **ENDS** | — | Espacio Nacional de Datos de Salud | Implementación española del EHDS |
| **MQA** | Metadata Quality Assessment | Evaluación de calidad de metadatos | Modelo de data.europa.eu (completitud, coherencia, accesibilidad, actualidad, usabilidad) |
| **TEHDAS2** | — | Segunda acción conjunta | Proyecto que apoya la implantación |

**EHDS** es la sigla inglesa; en español el nombre oficial es **EEDS**. En documentos de la Comisión y en HealthDCAT-AP se usa EHDS.

## 2. Marco normativo y fechas

| Norma | Qué hace | Fecha |
|---|---|---|
| **Reglamento (UE) 2025/327** | Crea el EEDS. Uso primario y secundario | En vigor **26-03-2025** |
| Aplicación general | — | **26-03-2027** |
| **Reglamento de Ejecución (UE) 2026/2098** | Metadatos mínimos por conjunto de datos (art. 77.4), con HealthDCAT-AP como marco | Publicado 18-09-2026 · **aplica 26-03-2029** |
| Hitos posteriores | Obligaciones adicionales | 2029 y 2031 |

**Lo que exige a un tenedor de datos como FISABIO:** describir cada conjunto de datos disponible para uso secundario con los metadatos mínimos del anexo parte B del 2026/2098, expresados en HealthDCAT-AP, para que el catálogo nacional pueda federarse en HealthData@EU.

## 3. Elementos obligatorios (HealthDCAT-AP R8, nivel no público)

| # | Elemento | Cardinalidad | Qué pide |
|---|---|---|---|
| 1 | **Access rights** | 1 | público / restringido / no público (vocabulario NAL) |
| 2 | **Applicable legislation** | 1..n | ELI de la norma aplicable (p. ej. `…/reg/2025/327/oj`) |
| 3 | **Description** | 1..n | Descripción libre |
| 4 | **Health category** | 1..n | Categoría del art. 51 (imagen médica, HCE, genómica, registros…) |
| 5 | **Health data access body** | 1 | Organismo competente que da acceso |
| 6 | **Identifier** | 1..n | Identificador principal del conjunto |
| 7 | **Structured data** | 1 | Booleano; si `true`, exige descripción de variables (CSVW) |
| 8 | **Title** | 1..n | Título |

Recomendados (0..*): purpose, legal basis, personal data, quality annotation, retention period, coding system, code values, population coverage, temporal/geographical coverage, number of records, number of unique individuals, provenance, publisher, custodian, contact point.

## 4. Matriz de cumplimiento

Leyenda: **✔** declarado · **~** derivable pero sin vocabulario · **✘** ausente.

| Elemento | BIMCV-COVID19− | BIMCV-COVID19+ | BIMCV Prostate | PadChest | DHR FIHGUV | DHR ISABIAL |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Access rights | ✔ | ✘ | ✘ | ✘ | ✔ | ✔ |
| Applicable legislation | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ |
| Description | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| Health category | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ |
| Health data access body | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ |
| Identifier | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ |
| Structured data | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ |
| Title | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| **Cumple 8/8** | **3** | **2** | **2** | **2** | **3** | **3** |
| License | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ |

**Resultado: 2 o 3 de 8 elementos obligatorios.** Los dos que siempre se cumplen son los triviales (título y descripción). Ninguno tiene licencia, identificador persistente, categoría de salud ni organismo de acceso.

**Cuidado con `access_rights`:** solo 3 de los 6 lo declaran. El catálogo **muestra «Abierto» cuando el campo está vacío**, que es un valor por defecto engañoso: ausencia de declaración no es apertura. El dato correcto es «sin declarar».

## 5. Fichas

### 5.1. PadChest — ficha completa (plantilla)

| Campo | Valor | Estado |
|---|---|---|
| **Title** | PadChest: un gran conjunto de datos de imágenes de rayos X de tórax con informes anotados de etiquetas múltiples | ✔ declarado |
| **Description** | Conjunto etiquetado a gran escala de radiografías de tórax con informes asociados; más de 160.000 imágenes de 67.000 pacientes | ✔ declarado |
| **Identifier** | `ckan:padchest` (propuesto). El DOI de la publicación descriptora es `10.1016/j.media.2020.101797`, pero **no es el identificador del recurso** | ✘ |
| **Access rights** | Cerrado según CKAN (`False`). Debe expresarse como `non-public` del vocabulario NAL | ~ |
| **Health category** | *Medical imaging* (propuesta) | ✘ |
| **Applicable legislation** | `http://data.europa.eu/eli/reg/2025/327/oj` (propuesta) | ✘ |
| **Health data access body** | Ministerio de Sanidad (coordinador, proyecto HDAB-ES). **Sin designación formal confirmada para uso secundario** | ✘ |
| **Structured data** | `false` (imágenes + informes, no tabla de variables) | ✘ |
| **License** | — | ✘ |
| **Purpose / legal basis** | — | ✘ |
| **Quality annotation** | — | ✘ |
| **Landing page** | https://health-dcat.fisabio.san.gva.es/dataset/padchest | ✔ |
| **Publisher / Custodian** | FISABIO | ~ |
| **Modified** | 2026-09-01 | ✔ |

### 5.2. Resto de conjuntos

| Conjunto | Título | Acceso (CKAN) | Health category (propuesta) | Identificador | Observación |
|---|---|---|---|---|---|
| `bimcv-covid19negative` | BIMCV-COVID19−: imágenes de RX y TC de pacientes negativos | **Público** (declarado) | Medical imaging | ✘ | El único con acceso público declarado; sin licencia |
| `bimcv-covid19-positivos` | BIMCV-COVID19+: imágenes de RX y TC de pacientes positivos | **Sin declarar** | Medical imaging | ✘ | La web lo pinta como «Abierto» |
| `bimcv-prostate` | BIMCV Prostate Dataset V1 | **Sin declarar** | Medical imaging | ✘ | >9.000 sesiones de RM, 16 centros |
| `padchest` | PadChest: imágenes de tórax con informes anotados | **Sin declarar** | Medical imaging | ✘ | La web lo pinta como «Abierto» |
| `dhr-fihguv` | DHR del FIHGUV para GVA PharmaTrace Hub | **Restringido** (declarado) | Electronic health records | ✘ | Tenedor: FIHGUV, no FISABIO |
| `dhr-isabial` | DHR de ISABIAL para GVAPharmaTrace Hub | **Restringido** (declarado) | Electronic health records | ✘ | Tenedor: ISABIAL, no FISABIO |

El acceso sale de `access_rights`, el único campo que es declaración. **`isopen` no sirve**: vale `False` en los 6, incluso en el que declara acceso público.

## 6. Brechas principales

1. **Identificador persistente: 0 de 6.** Sin PID no hay federación posible con HealthData@EU.
2. **Licencia: 0 de 6.** «License not specified» no es una licencia. Fuera del catálogo, **90 de los 134 recursos sí declaran licencia**: el problema no es del personal investigador, es del catálogo.
3. **El catálogo confunde «no declarado» con «abierto».** Tres de los seis tienen `access_rights` vacío y la web los muestra con la etiqueta verde «Abierto». Para datos de salud, el valor por defecto debería ser «sin declarar», nunca «abierto».
4. **Organismo de acceso: 0 de 6.** El HDAB español está en construcción (HDAB-ES); conviene seguirlo.
5. **Categoría de salud: 0 de 6.** Es el campo que permite buscar por tipo de dato; sin él el catálogo no es navegable.
6. **Tenedor mal atribuido en 2 casos:** los DHR son de FIHGUV e ISABIAL, no de FISABIO. El catálogo mezcla tenedor y publicador.
7. **`Structured data` sin declarar en 6 de 6:** obliga a decidir si hay tabla de variables y, si la hay, a publicarla en CSVW.

## 7. Qué haría falta para llegar a 2029

| Acción | Esfuerzo | Impacto |
|---|---|---|
| Asignar PID a los 6 (DOI vía DataCite/Zenodo o URI persistente) | Bajo | Desbloquea la federación |
| Declarar licencia y condiciones de uso | Bajo | Requisito legal y de reutilización |
| Mapear `access_rights` al vocabulario NAL (3 valores) | Bajo | Cumple el elemento 1 |
| Asignar `health category` del art. 51 | Medio | Navegabilidad y búsqueda |
| Declarar `structured data` y, si procede, variables en CSVW | Medio | Calidad de metadatos |
| Separar tenedor (FIHGUV, ISABIAL) de publicador (FISABIO) | Bajo | Exactitud legal |
| Verificar el HDAB competente antes de 2029 | Seguimiento | Requisito del elemento 5 |

## 8. Nota metodológica

- Los datos provienen de la API CKAN del catálogo (`/api/3/action/package_show`) y de la especificación HealthDCAT-AP Release 8.
- Las «propuestas» son inferencias documentadas, **no declaraciones de la institución**, y así se marcan.
- El catálogo institucional cubre **6 de los ~114 conjuntos de datos únicos** que FISABIO publica con DOI. La ficha EHDS afecta a los datos en poder de la institución, no solo a los publicados.
- El Reglamento de Ejecución 2026/2098 no se ha podido leer íntegro en EUR-Lex (bloqueo de acceso automatizado); la lista de elementos se ha tomado del **Metadata Model Explorer de HealthData@EU** y de HealthDCAT-AP R8. Antes de una declaración formal, contrastar con el anexo parte B del DOUE.
