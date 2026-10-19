# ORCID: Del Caos a la Identidad Digital Unívoca
## Visualización Voronoi Stippling (Relajación de Lloyd) · Homenaje a Margarita Salas

Visualización interactiva creativa para la **Unidad de Ciencia Abierta de Fisabio** (Proyecto OSIRIS · Convocatoria María de Guzmán L2, FECYT).

---

## 🎨 Metáfora Conceptual
1. **El Caos**: 5.000 partículas en movimiento browniano y colisiones representan la dispersión de la identidad académica, duplicidades de firma, citas perdidas y métricas fragmentadas.
2. **El Orden (ORCID)**: Al activar el botón **«Generar ORCID»**, las partículas convergen mediante relajación de Lloyd ponderada hacia sus posiciones de equilibrio, revelando el retrato de la científica **Margarita Salas**.
3. **Nodos Interactivos (Fase 2)**: Al pasar el cursor o pulsar sobre 4 áreas clave, las partículas se dispersan elásticamente y se despliegan cuadros flotantes de información:
   - **Nodo 1 (Zona Superior)**: *De la confusión a la identidad unívoca* (Identidad digital, firma única, filiación).
   - **Nodo 2 (Zona Central / Ojos)**: *Tú decides qué se ve* (Control de visibilidad y privacidad).
   - **Nodo 3 (Zona Inferior / Manos)**: *Enriquecimiento y Gestión* (Construcción del perfil, biografía, unificación).
   - **Nodo 4 (Zona Periférica)**: *El centro de tu red académica* (Conectividad con WoS, Scopus, Crossref, DataCite, BASE).

---

## 🚀 Cómo Ejecutar

### Opción 1: Servidor local rápido (recomendado para evitar restricciones CORS de `file://`)
Abre una terminal en esta carpeta y ejecuta:
```bash
# Con Python:
python -m http.server 8080

# O con Node:
npx serve .
```
Luego accede en tu navegador a: `http://localhost:8080`

### Opción 2: Apertura directa
Puedes hacer doble clic en `index.html`. Si la política de seguridad local de tu navegador bloquea la carga de la imagen vía `file://`, la aplicación activará automáticamente una **silueta procedural de fallback** y podrás cargar tu imagen pulsando en **«Cambiar Imagen»** o arrastrándola directamente sobre el lienzo.

---

## 🖼️ Preparación de la Imagen `margarita_salas_bw.png`
1. Recorta la fotografía con relación de aspecto cuadrada (ideal: **600 × 600 px**).
2. Conviértela a **escala de grises**.
3. Aumenta el **contraste** (los negros profundos atraerán mayor densidad de partículas y las luces quedarán despejadas).
4. Guarda el archivo con el nombre exacto `margarita_salas_bw.png` en esta misma carpeta.

---

## ⚙️ Calibración de Nodos en `script.js`
En la cabecera de `script.js`, dentro del objeto `CONFIG.nodes`, puedes modificar en cualquier momento las coordenadas `(x, y)` y el radio `r` de cada nodo para adaptarlo a cualquier encuadre fotográfico.
