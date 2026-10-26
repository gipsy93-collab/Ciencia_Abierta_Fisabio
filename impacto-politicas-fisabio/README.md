# Impacto de FISABIO en Políticas Públicas

Este proyecto busca evaluar e inspeccionar el impacto de la investigación de FISABIO en las políticas públicas, actuando como una base de datos similar a Overton.

## Arquitectura

El flujo de trabajo es el siguiente:

```text
[ Catálogo FISABIO ]
(OpenAlex / PubMed API)
        │
        ▼
[ Corpus de Políticas Sanitarias ] ───► [ Pipeline Local ]
(GVA Sanitat, Min. Sanidad, ECDC, OMS)   1. Extracción de texto y bibliografía (PyMuPDF)
                                         2. Filtro regex / Fuzzy Match contra autores y títulos FISABIO
                                         3. Resolución de ambigüedad semántica (bge-embeddings / GLiNER)
                                         4. Persistencia en SQLite / DuckDB
```

## Estructura del proyecto

- `data/`: Almacenamiento de corpus, bases de datos (SQLite/DuckDB) y datos intermedios.
- `docs/`: Documentación adicional del proyecto.
- `src/`: Scripts del pipeline (extracción, matching, base de datos).
