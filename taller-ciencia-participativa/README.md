# Infografía interactiva — «Estamos pensando la ciencia abierta»

Pieza divulgativa del taller de diagnóstico de necesidades del proyecto **OpenScience4Health** (FCT-25-22602), coordinado por Fisabio con la UPV y la UV y financiado por FECYT (convocatoria I+P).

- **Qué es:** infografía interactiva en HTML. El cerebro es la metáfora («estamos pensando la ciencia abierta») y cada zona abre una de las **7 secciones** del taller.
- **Portada (5 zonas):** Contexto del proyecto · Contexto del taller · Participantes · De barreras a necesidades · Temáticas priorizadas.
- **Página 2 (2 zonas):** Comentarios y conclusiones · Pasos siguientes (con las 4 conclusiones del informe: financiación continuada, estrategia y estructura, coordinación e interoperabilidad, gobernanza inclusiva; y el insumo directo a la Conselleria de Sanitat / CoARA).
- **Página 3:** galería del taller en 5 fotografías (con pies editables) y cierre con créditos.

## Cómo abrirla

Doble clic en `Taller-Ciencia-Participativa.html` (requiere la carpeta `assets/fotos/` a su lado para la galería). Las imágenes del arte y la tipografía van embebidas; las fotografías del taller son **referenciadas**, no incrustadas.

Navegación: flechas inferiores o teclado (`←` `→`); las ventanas se cierran con la `X`, `Esc` o el marco azul.

## Estructura

```
Taller-Ciencia-Participativa/
├── Taller-Ciencia-Participativa.html   ← pieza publicable (fotos referenciadas)
├── assets/                        ← arte de los cerebros y tipografía
│   └── fotos/                     ← fotografías del taller (referenciadas, no incrustadas)
└── src/
    ├── template.html              ← plantilla con los textos y la composición
    ├── textos.json                ← capa de overrides de textos (build la incrusta)
    └── build.py                   ← genera el HTML final (Pillow) y sincroniza fotos a dist/
```

## Origen y contenido

- Réplica basada en la plantilla de Genially «Infografía Neurociencia» (S88), con editor de textos y doble salida taller/publicable (S92).
- Textos de conclusiones, pasos siguientes y entidades tomados del **Informe de Resultados OpenScience4Health** (20-10-2026) y del listado de entidades confirmado por coordinación (S93-S94).
- Participantes: Fisabio (coordinadora), la Fundació de l'Hospital General Universitari de València, INCLIVA, ISABIAL, la Fundació de l'Hospital Provincial de Castelló, el Instituto de Investigación Sanitaria La Fe, y las entidades socias UPV y UV.

## Pendiente

- Confirmar consentimiento de las personas que aparezcan en las fotografías y anotar la autoría de cada imagen (pie "Fotografías del taller · Fisabio" genérico).
- Los comentarios literales del tramo final del documento del taller (`CONTEXTO TALLER PROYECTO_.md.crdownload`, cortado en «Conclusiones/Comentarios») siguen sin fuente.
