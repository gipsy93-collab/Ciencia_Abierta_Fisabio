# Infografía interactiva · «Estamos pensando la ciencia abierta»

Pieza divulgativa del taller de diagnóstico de necesidades del proyecto **OpenScience4Health** (FCT-25-22602), coordinado por Fisabio con la UPV y la UV y financiado por FECYT (convocatoria I+P).

- **Qué es:** infografía interactiva en un único HTML. El cerebro es la metáfora («estamos pensando la ciencia abierta») y cada zona abre una ventana de detalle.
- **Portada (5 zonas):** El taller · Metodología y diagnóstico de necesidades · Participantes · Necesidades · Prioridades.
- **Página 2 (2 zonas):** Conclusiones · Pasos siguientes.
- **Página 3:** cierre de agradecimientos con las bandas de logos.
- **14 ventanas de detalle:** las 5 del cerebro de portada, la galería del proceso (`m2b`, cinco fotos), la tabla de las **22 personas** del taller (`m3b`), el **ranking de las 13 necesidades priorizadas** (`m4b`) y las cuatro ventanas de caracterización `m5a`–`m5d` (estrategia, gobernanza, infraestructuras y financiación), más las dos de la página 2.

## Cómo abrirla

Doble clic en `Ciencia-abierta.html`. Funciona sin conexión: el arte, la tipografía y las imágenes del informe van embebidos. Las **fotografías del taller** son referenciadas, así que la carpeta `assets/` debe ir al lado.

Navegación: flechas inferiores o teclado (`←` `→`), y las ventanas se cierran con la `X`, `Esc` o el velo.

## Arte del cerebro

Las nueve láminas son el **arte original de la plantilla** de Genially («Infografía Neurociencia»), no una captura reducida:

- `src/compone_cerebro.py` recompone en un SVG por lámina las dos capas que sirve el visor original: la **línea** (PNG con transparencia: 966×811 la vista lateral y 697×866 cada mitad de la superior) y el **color** (una mancha vectorial por zona).
- Los datos de origen están en `assets/origen/` (`zonas.json` y las tres capas de tinta); `assets/cerebro/` guarda los nueve SVG ya compuestos.
- `build.py` los regenera e incrusta en cada compilación, así que el arte se puede rehacer sin volver a Genially.

## Estructura

```
taller-ciencia-participativa/
├── Ciencia-abierta.html                pieza publicable (fotos referenciadas)
├── index.html                          redirección a la pieza
├── assets/
│   ├── cerebro/                        nueve SVG del cerebro (arte original)
│   ├── origen/                         manchas de color y capas de línea del original
│   ├── fotos/                          fotografías del taller (referenciadas)
│   └── informe/                        imágenes del informe (mapa, panel, plantillas, logos)
└── src/
    ├── template.html                   plantilla con los textos y la composición
    ├── compone_cerebro.py              recompone el arte del cerebro en SVG
    ├── build.py                        genera el HTML final (taller y publicable)
    ├── textos.json                     capa de overrides de textos (hoy vacía)
    └── verificar_*.py                  comprobaciones automáticas (informe, textos, teclado)
```

## Recompilar

```bash
python src/build.py
```

Escribe `Taller-Ciencia-Participativa.html` (con editor de textos) y `dist/Ciencia-abierta.html` (publicable, sin editor), y sincroniza `assets/fotos/` y `assets/informe/` a `dist/`.

Verificación: `python src/verificar_informe.py` (90 comprobaciones), `python src/verificar_textos.py` (75) y `python src/verificar_teclado.py` (31).

## Origen y contenido

- Réplica basada en la plantilla de Genially «Infografía Neurociencia», con editor de textos y doble salida taller/publicable.
- Textos del **Informe de Resultados OpenScience4Health** (jornada del 20-10-2026): 19 participantes de nueve instituciones, cuatro mesas, 25 tarjetas de necesidades en seis ejes, 13 necesidades priorizadas y cuatro temáticas caracterizadas.
- Participantes: Fisabio (coordinadora), la Fundació de l'Hospital General Universitari de València, INCLIVA, ISABIAL, la Fundació de l'Hospital Provincial de Castelló, el Instituto de Investigación Sanitaria La Fe, y las entidades socias UPV y UV. Ponencia de Enrique Orduña-Malea (UPV) y dos observadoras de la UV.

## Pendiente

- Comentarios literales del tramo final del taller: se añadirán cuando coordinación disponga del texto.
- Crédito por imagen en la galería (las fotos no incluyen personas identificables, así que no requieren consentimiento).
