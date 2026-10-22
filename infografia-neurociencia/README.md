# Infografía interactiva — «Estamos pensando la ciencia abierta»

Pieza divulgativa del taller de diagnóstico de necesidades del proyecto **OpenScience4Health** (FCT-25-22602), coordinado por Fisabio con la UPV y la UV y financiado por FECYT (convocatoria I+P).

- **Qué es:** infografía interactiva en un único HTML. El cerebro es la metáfora («estamos pensando la ciencia abierta») y cada zona abre una de las **7 secciones** del taller.
- **Portada (5 zonas):** Contexto del proyecto · Contexto del taller · Participantes · De barreras a necesidades · Temáticas priorizadas.
- **Página 2 (2 zonas):** Comentarios y conclusiones · Pasos siguientes.
- **Página 3:** cierre y galería (prevista para fotografías del taller).

## Cómo abrirla

Doble clic en `Infografia-Neurociencia.html`. Funciona sin conexión: las imágenes y la tipografía están embebidas.

Navegación: flechas inferiores o teclado (`←` `→`); las ventanas se cierran con la `X`, `Esc` o el marco azul.

## Estructura

```
infografia-neurociencia/
├── Infografia-Neurociencia.html   ← pieza final (autocontenida)
├── assets/                        ← arte de los cerebros y tipografía
└── src/
    ├── template.html              ← plantilla con los textos y la composición
    └── build.py                   ← genera el HTML final (Pillow)
```

Para regenerar tras editar la plantilla:

```bash
python src/build.py
```

## Próximo paso: fotografías

Las fotos del taller se guardarán en `assets/fotos/` (no se incrustan en el HTML) y se mostrarán en:

- **El taller:** 2-4 fotografías de la sesión.
- **Participantes:** foto de grupo.
- **Página 3:** galería con pies de foto, crédito y ampliación al clic.

Conviene confirmar el consentimiento de las personas que aparezcan y anotar la autoría de cada imagen.

## Origen

- Réplica basada en la plantilla de Genially «Infografía Neurociencia».
- Contenido: `CONTEXTO TALLER PROYECTO_.md.crdownload` (documento de trabajo del taller).
- Textos del taller pendientes de cerrar: listado de las 7 entidades, conclusiones y pasos siguientes.
