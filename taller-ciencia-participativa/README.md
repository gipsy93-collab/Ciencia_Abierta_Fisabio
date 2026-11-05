# Infografía interactiva — «Estamos pensando la ciencia abierta»

Pieza divulgativa del taller de diagnóstico de necesidades del proyecto **OpenScience4Health** (FCT-25-22602), coordinado por Fisabio con la UPV y la UV y financiado por FECYT (convocatoria I+P).

- **Qué es:** infografía interactiva en HTML. El cerebro es la metáfora («estamos pensando la ciencia abierta»); cada zona se conecta con las demás mediante sinapsis animadas y abre una ventana de detalle.
- **Portada:** presentación del taller y de su contexto (OpenScience4Health, Semana del Acceso Abierto, 20-10-2026), con el cerebro a la derecha, la energía neuronal entre sus áreas y los logos institucionales. Accesos: El taller · Metodología · Participantes · Necesidades · Prioridades.
- **El taller (zona 1):** objetivo general y los cuatro objetivos específicos, con una fotografía del proceso en el botón sobre el cerebro.
- **Metodología (zona 2):** dinámica cualitativa de validación y priorización, materiales de trabajo y el cuadro de las 25 necesidades agrupadas en seis ejes (N01–N25).
- **Proceso en imágenes (m2b):** galería de las cinco fotografías del taller (tarjetas N15/N19, votación y mesas), con pies editables y lightbox.
- **Participantes (zona 3):** el botón «+» sobre el cerebro abre la tabla de las 22 personas (19 participantes + 2 observadoras + ponente) acompañada de una fotografía del grupo.
- **Necesidades (zona 4):** los seis ejes (N01–N25) distribuidos en tarjetas alrededor del cerebro; el botón «+» abre el ranking de las 13 necesidades priorizadas con la imagen del panel grupal.
- **Prioridades (zona 5):** cuatro botones de categoría (Estrategia 19, Gobernanza 13, Infraestructuras 11 y Financiación 10); cada uno abre su ventana con la plantilla de caracterización y cuatro pestañas: diagnóstico actual, actores clave, transformación requerida y causas subyacentes.
- **Página 2:** Comentarios y conclusiones · Pasos siguientes (con las 4 conclusiones del informe: financiación continuada, estrategia y estructura, coordinación e interoperabilidad, gobernanza inclusiva; y el insumo directo a la Conselleria de Sanitat / CoARA).
- **Agradecimientos (página 3):** cierre con el texto de agradecimiento, la referencia del proyecto y las bandas de logos. Las fotografías ya viven en sus apartados correspondientes (m1, m2b, m3b, m4b y m5a–m5d).

## Cómo abrirla

Doble clic en `Taller-Ciencia-Participativa.html` (requiere las carpetas `assets/fotos/` y `assets/informe/` a su lado). Las imágenes del arte y la tipografía van embebidas; las fotografías y los logos son **referenciados**, no incrustados.

Navegación: flechas inferiores o teclado (`←` `→`); las ventanas se cierran con la `X`, `Esc` o el marco azul.

**Teclado:** `←`/`A` y `→`/`D` cambian de página; `↑`/`↓` recorren las zonas; `W` abre la zona enfocada; `X` vuelve o cierra; en Prioridades, `A`/`D` cambian de categoría o de pestaña; `Tab` mantiene el foco dentro de la ventana; `Esc` cierra. Las fotos son enfocables y se amplían con `W` o `Enter`.

## Estructura

```
Taller-Ciencia-Participativa/
├── Taller-Ciencia-Participativa.html   ← pieza publicable (fotos y logos referenciados)
├── assets/                        ← arte de los cerebros y tipografía
│   ├── fotos/                     ← fotografías del taller (referenciadas)
│   └── informe/                   ← imágenes del informe y bandas de logos (referenciadas)
└── src/
    ├── template.html              ← plantilla con los textos y la composición
    ├── textos.json                ← capa de overrides de textos (build la incrusta)
    ├── build.py                   ← genera el HTML final (Pillow) y sincroniza fotos e informe a dist/
    ├── verificar_informe.py       ← QA Playwright de la pieza (90 comprobaciones)
    ├── verificar_textos.py        ← QA de textos, editor y salida publicable (75 comprobaciones)
    └── verificar_teclado.py       ← QA de navegación por teclado y foco (31 comprobaciones)
```

## Origen y contenido

- Réplica basada en la plantilla de Genially «Infografía Neurociencia» (S88), con editor de textos y doble salida taller/publicable (S92).
- Textos de conclusiones, pasos siguientes y entidades tomados del **Informe de Resultados OpenScience4Health** (20-10-2026) y del listado de entidades confirmado por coordinación (S93-S94).
- Participantes: Fisabio (coordinadora), la Fundació de l'Hospital General Universitari de València, INCLIVA, ISABIAL, la Fundació de l'Hospital Provincial de Castelló, el Instituto de Investigación Sanitaria La Fe, y las entidades socias UPV y UV.

## Pendiente

- Comentarios literales del tramo final del taller (`CONTEXTO TALLER PROYECTO_.md.crdownload`, cortado en «Conclusiones/Comentarios»): se añadirán cuando coordinación disponga del texto (así lo indica Gipsy).
- Crédito de las fotografías en sus ventanas; no hay personas identificables (no requiere consentimiento). Valorar autoría por imagen si Gipsy la aporta.
- Revisión final de textos y contraste antes de la difusión.
