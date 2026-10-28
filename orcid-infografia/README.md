# Crea tu ORCID fácil

Guía interactiva del taller **«Identificador único del personal investigador. ORCID»** de la Unidad de Ciencia Abierta de Fisabio (12-11-2025).

- Pieza publicada: <https://gipsy93-collab.github.io/Ciencia_Abierta_Fisabio/orcid-infografia/>
- Portal de piezas: <https://gipsy93-collab.github.io/Ciencia_Abierta_Fisabio/>
- Editor de textos: `editor.html` (misma carpeta, sin enlace público)

## Estado

**v2.0 · infografía de una sola lámina.** Rehecha sobre la distribución del ejemplo de Genially que pasó Gipsy (`Infografía Conectores Akihabara`): título arriba, anillo de ocho botones circulares alrededor del identificador y subtítulo abajo; cada botón abre su ventana con el detalle. La v1.0 (página larga de ocho secciones) queda como hito.

- `index.html` — publicable, 324 KB, autocontenida (fuentes, logo y arte incrustados; **cero peticiones externas**).
- `editor.html` — 329 KB, con editor de textos y descarga de la versión final.
- `poster.html` + `boletin/crea-tu-orcid-facil-1080x1920.png` — cartel estático para el boletín.
- Verificación: `python src/verificar.py` → **117** comprobaciones (consola limpia, 3 anchos sin desbordamiento, 8 nodos, 8 ventanas, 8 láminas pintadas, enlaces directos, las 4 interacciones, teclado y contraste AA).
- `muestra.html` — muestra de diseño aprobada (v0.3), se conserva como hito.

## Distribución

- **Lámina fija de 1080 × 1620** (2:3) escalada para caber en la ventana, sin scroll.
- **Ocho botones circulares** repartidos en anillo (radio 35 % de la órbita) con el número en serif itálica y la etiqueta dentro; conectores punteados con el medallón ORCID y anillo graduado de 72 marcas.
- **Cada botón abre una ventana** (ficha) con cabecera (número, marca, título), lámina a la derecha y el texto, la cita, la lista y su interacción. Cierre con X, `Esc` o clic en el velo; flechas ← → para pasar de una a otra; `#n01`…`#n08` como enlace directo.
- **En móvil** (< 760 px) el anillo pasa a lista de ocho conexiones con el medallón arriba; la ventana ocupa la pantalla y la X queda fija.
- Las cuatro interacciones viven dentro de su ventana (ya no hay modal aparte).


## Estructura

```
orcid-infografia/
  index.html            publicable (Pages)
  editor.html           con editor de textos
  poster.html           cartel 1080×1920
  muestra.html          muestra de diseño aprobada
  boletin/
    crea-tu-orcid-facil-1080x1920.png
  assets/
    fonts/              Fraunces (normal + itálica) y Outfit, woff2
    orcid-id.svg        logo oficial, sin alterar
  src/
    template.html       HTML + CSS + JS de la pieza
    textos.json         overrides de textos incrustados al compilar
    build.py            genera index.html, editor.html y poster.html
    verificar.py        Playwright: 117 comprobaciones
    poster.html         fuente del cartel
    poster.py           render del PNG
    arte/
      art.js            motor de acuarela puntillista (papel, aguada, huellas)
      placas.js         ocho láminas, una por nodo
  tools/
    shot.py             capturas de la muestra
    pliego.html         pliego de contacto de las ocho láminas
  capturas/             QA (no se publica, ver .gitignore)
```

## Editar los textos

1. Abrir `editor.html` en el navegador (Chrome o Edge).
2. «Editar textos» → escribir. Los cambios se guardan en `localStorage` de ese navegador.
3. «Exportar textos.json» → guardar en `src/textos.json`.
4. Recompilar: `python src/build.py`. Los textos quedan incrustados en `index.html`.

También se puede trabajar directamente sobre `src/template.html` (todo el contenido está ahí, con `data-edit` por texto).

## Reconstruir

```powershell
python src/build.py      # index.html + editor.html + poster.html
python src/poster.py     # boletin/crea-tu-orcid-facil-1080x1920.png
python src/verificar.py  # comprobaciones + capturas
```

Requiere Playwright con el canal `chrome` (`pip install playwright`).

## Contenido y fidelidad

Ocho nodos, mapeados a las diapositivas del taller:

| Nodo | Tema | Fuente | Interacción |
|---|---|---|---|
| 01 | Clones, identidad | diapos 5-6 | Prueba rápida (modal) |
| 02 | Firma y filiación | 7-8 | Cuatro fórmulas de Fisabio + copiar |
| 03 | Qué es ORCID | 9-10 | — |
| 04 | Cuatro pasos | 11-16 | — |
| 05 | Visibilidad | 15 | Simulador de visibilidad |
| 06 | Gestión del perfil | 17-19 | — |
| 07 | Piloto automático | 23-24 | Menú «+ Add» desplegable |
| 08 | Duplicados y cierre | 20, 25 | Enlaces de cierre |

- Cita: Díaz-Redondo y Frías-Montoya, 2018, p. 12 (diapo 5).
- Identificador de ejemplo: `0000-0002-1825-0097` (registro de prueba público, no de una persona real).
- **No se usa** el dato «87 % elige Todo el mundo»: no está en el taller (viene del guion del vídeo).
- Las cuatro definiciones de visibilidad (todo el mundo / partes de confianza / solo yo) son la semántica estándar de ORCID; el taller solo enumera las opciones.

## Arte

Estilo: acuarela puntillista generativa sobre papel, con la paleta Fisabio/ORCID. Todo se dibuja en `<canvas>` al cargar; no hay imágenes de arte.

| Nodo | Lámina | Semilla |
|---|---|---|
| 01 | Dos huellas superpuestas + sello | 11 |
| 02 | Firma y rúbrica + bloques de filiación | 21 |
| 03 | Anillo de dieciséis barras (el iD) | 31 |
| 04 | Cuatro discos en secuencia + check | 41 |
| 05 | Disco lleno, medio y aro | 51 |
| 06 | Retícula de cajones de archivo | 61 |
| 07 | Red de seis satélites | 71 |
| 08 | Dos anillos que se fusionan | 81 |

Deterministas por semilla: el mismo dibujo en cada carga y en cada dispositivo.

## Diseño y accesibilidad

- Lámina: título centrado, medallón ORCID con anillo graduado de 72 marcas y ocho botones circulares en anillo; en móvil pasa a lista de conexiones con el medallón arriba.
- Contraste AA verificado: texto verde 4.66, sello rojo 5.85, tinta 15.50, tinta suave 6.78.
- Teclado: foco visible, ventana con trampa de foco, `Escape` cierra y ← → cambian de conexión; los nodos llevan `aria-label` y `aria-expanded`.
- `prefers-reduced-motion` desactiva animaciones; sin scroll horizontal a 390/768/1440.
- Impresión: oculta la navegación y el fondo animado.

## Publicación

GitHub Pages sirve la rama `main` en la raíz. El portal es `index.html`; esta pieza vive en `orcid-infografia/`. Para publicar: commit de `index.html`, `portal/` y `orcid-infografia/`, y push a `main`.
