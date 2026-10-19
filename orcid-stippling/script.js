/**
 * ==========================================================================
 * ORCID: DEL CAOS A LA IDENTIDAD DIGITAL UNÍVOCA
 * Visualización Voronoi Stippling (Relajación de Lloyd) · Homenaje a Margarita Salas
 * ==========================================================================
 *
 * Técnica inspirada en Mike Bostock y Adrian Secord (Weighted Voronoi Stippling).
 * Desarrollado para la Unidad de Ciencia Abierta de Fisabio / Proyecto OSIRIS.
 *
 * STACK: HTML5 Canvas, JavaScript Vanilla, D3.js (v7) y d3-delaunay (v6).
 */

/* ==========================================================================
   SECCIÓN CONFIGURABLE — AJUSTA AQUÍ TUS PARÁMETROS
   ========================================================================== */
const CONFIG = {
  // 1. RUTA DE LA IMAGEN
  // Para mejores resultados: imagen en escala de grises, alto contraste y tamaño 600x600 px.
  imagePath: "margarita_salas_bw.png",

  // 2. NÚMERO DE PARTÍCULAS (Puntos de estarcido / stippling)
  // Valores recomendados: entre 3.000 y 6.000 (5.000 ofrece excelente balance entre detalle y fluidez)
  particleCount: 5000,

  // 3. DIMENSIONES DEL LIENZO BASE (coordenadas lógicas)
  width: 600,
  height: 600,

  // 4. PARÁMETROS DEL ALGORITMO DE LLOYD
  // Número de iteraciones para que los centroides ponderados converjan al retrato
  lloydIterations: 24,

  // Radio de las partículas (en píxeles) según la densidad de la zona:
  particleRadiusMin: 1.0, // Zonas claras / luces
  particleRadiusMax: 2.5, // Zonas oscuras / sombras y contrastes

  // 5. COORDENADAS (x, y), RADIO (r) Y CONTENIDO DE LOS 4 NODOS INTERACTIVOS
  // Ajusta 'x', 'y' y 'r' para calibrar la posición exacta sobre la foto de Margarita Salas.
  nodes: [
    {
      id: "node-1",
      badge: "Nodo 1 · Zona Superior",
      zoneName: "La Identidad Digital",
      x: 300,  // Coordenada horizontal (centro)
      y: 110,  // Coordenada vertical (frente / cabello)
      r: 65,   // Radio del área interactiva (hitbox)
      title: "De la confusión a la identidad unívoca.",
      text: "La duplicidad de nombres provoca que trabajos ajenos se nos atribuyan o que perdamos citas propias. ORCID soluciona esto proporcionando un identificador universal, único y persistente, compatible con otras plataformas. Para empezar, define una firma única e incluye tu filiación institucional."
    },
    {
      id: "node-2",
      badge: "Nodo 2 · Zona Central / Ojos",
      zoneName: "Control de Visibilidad",
      x: 300,  // Coordenada horizontal
      y: 245,  // Coordenada vertical (mirada / rostro)
      r: 65,   // Radio del área interactiva
      title: "Tú decides qué se ve.",
      text: "Al crear tu perfil, tienes control absoluto de la privacidad. Puedes elegir que tu información sea pública (para todo el mundo), visible solo para partes de confianza, o estrictamente privada."
    },
    {
      id: "node-3",
      badge: "Nodo 3 · Zona Inferior / Manos",
      zoneName: "Construcción del Perfil",
      x: 300,  // Coordenada horizontal
      y: 485,  // Coordenada vertical (manos / bata de laboratorio)
      r: 75,   // Radio del área interactiva
      title: "Enriquecimiento y Gestión.",
      text: "Un perfil ORCID permite añadir tu biografía, experiencia profesional, formación académica, proyectos financiados y producción científica. Si tienes perfiles duplicados, nunca los borres: unifica y mantén el ID preferido."
    },
    {
      id: "node-4",
      badge: "Nodo 4 · Zona Periférica",
      zoneName: "Conectividad",
      x: 480,  // Coordenada horizontal (margen derecho)
      y: 350,  // Coordenada vertical
      r: 70,   // Radio del área interactiva
      title: "El centro de tu red académica.",
      text: "ORCID se vincula mediante asistentes de búsqueda con plataformas como Web of Science, Scopus, Crossref, DataCite o BASE para importar metadatos automáticamente."
    }
  ]
};

/* ==========================================================================
   ESTADOS DE LA SIMULACIÓN
   ========================================================================== */
const STATE = {
  CHAOS: "CHAOS",          // Partículas en movimiento browniano y desorden
  CALCULATING: "CALC",    // Calculando relajación de Voronoi
  ORDERING: "ORDERING",    // Transición guiada hacia el retrato
  SETTLED: "SETTLED"       // Retrato estable con sutil respiración orgánica
};

class VoronoiStippleSimulation {
  constructor(config) {
    this.config = config;
    this.state = STATE.CHAOS;

    // Elementos del DOM
    this.canvas = document.getElementById("stippleCanvas");
    this.ctx = this.canvas.getContext("2d");
    this.nodeOverlay = document.getElementById("nodeOverlay");
    this.loaderOverlay = document.getElementById("loaderOverlay");
    this.loaderMessage = document.getElementById("loaderMessage");
    this.statusPill = document.getElementById("statusPill");
    this.statusDesc = document.getElementById("statusDesc");
    this.btnOrder = document.getElementById("btnOrder");
    this.btnChaos = document.getElementById("btnChaos");
    this.imageFileInput = document.getElementById("imageFileInput");
    this.toggleGuides = document.getElementById("toggleGuides");

    // Modal elements
    this.modalOverlay = document.getElementById("modalOverlay");
    this.modalCard = document.getElementById("modalCard");
    this.modalBadge = document.getElementById("modalBadge");
    this.modalZoneTag = document.getElementById("modalZoneTag");
    this.modalTitle = document.getElementById("modalTitle");
    this.modalText = document.getElementById("modalText");
    this.modalClose = document.getElementById("modalClose");
    this.modalUnderstoodBtn = document.getElementById("modalUnderstoodBtn");

    // Estado interno
    this.particles = [];
    this.imageWeights = null;
    this.imageLoaded = false;
    this.voronoiCalculated = false;
    this.activeHoverNode = null;
    this.mouse = { x: -1000, y: -1000, isHovering: false, isNearNode: false };
    this.pixelRatio = window.devicePixelRatio || 1;

    // Inicialización
    this.initCanvasDPI();
    this.initParticles();
    this.initNodeGuides();
    this.initEventListeners();
    this.loadImage(this.config.imagePath);

    // Arrancar el bucle de animación a 60 FPS
    this.lastTime = performance.now();
    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);
  }

  /* ------------------------------------------------------------------------
     1. AJUSTE DE RESOLUCIÓN (RETINA / HIGH DPI)
     ------------------------------------------------------------------------ */
  initCanvasDPI() {
    const w = this.config.width;
    const h = this.config.height;

    this.canvas.width = w * this.pixelRatio;
    this.canvas.height = h * this.pixelRatio;
    this.canvas.style.width = `${w}px`;
    this.canvas.style.height = `${h}px`;

    // Escalar el contexto para dibujar siempre con coordenadas lógicas (600x600)
    this.ctx.scale(this.pixelRatio, this.pixelRatio);
  }

  /* ------------------------------------------------------------------------
     2. INICIALIZACIÓN DE PARTÍCULAS
     ------------------------------------------------------------------------ */
  initParticles() {
    this.particles = [];
    const n = this.config.particleCount;
    const w = this.config.width;
    const h = this.config.height;

    for (let i = 0; i < n; i++) {
      // Posición inicial aleatoria dentro del canvas
      const x = Math.random() * w;
      const y = Math.random() * h;

      // Velocidad caótica inicial (movimiento browniano)
      const angle = Math.random() * Math.PI * 2;
      const speed = 0.6 + Math.random() * 1.4;

      this.particles.push({
        id: i,
        // Posición actual
        x: x,
        y: y,
        // Velocidades
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        // Posición de destino tras relajación de Voronoi
        targetX: x,
        targetY: y,
        // Radio del punto
        currentRadius: 1.4 + Math.random() * 0.8,
        targetRadius: 1.6,
        // Fase y frecuencia para la sutil respiración armónica
        phase: Math.random() * Math.PI * 2,
        breathSpeed: 0.0015 + Math.random() * 0.001,
        // Amortiguación
        friction: 0.94
      });
    }
  }

  /* ------------------------------------------------------------------------
     3. CARGA Y PONDERACIÓN DE LA IMAGEN
     ------------------------------------------------------------------------ */
  loadImage(src) {
    this.imageLoaded = false;
    this.voronoiCalculated = false;

    const img = new Image();
    img.crossOrigin = "Anonymous";

    img.onload = () => {
      this.processImageWeights(img);
      this.imageLoaded = true;
      // Precalcular las posiciones de Voronoi en segundo plano
      this.precalculateVoronoi();
    };

    img.onerror = () => {
      console.warn(`[ORCID Stippling] No se pudo cargar '${src}'. Generando silueta procedural de prueba.`);
      this.generateFallbackPattern();
      this.imageLoaded = true;
      this.precalculateVoronoi();
    };

    img.src = src;
  }

  processImageWeights(img) {
    const w = this.config.width;
    const h = this.config.height;

    // Crear canvas offscreen para extraer datos de píxeles
    const offCanvas = document.createElement("canvas");
    offCanvas.width = w;
    offCanvas.height = h;
    const offCtx = offCanvas.getContext("2d");

    // Dibujar imagen ajustándola al lienzo cuadrado de 600x600 px
    offCtx.fillStyle = "#ffffff";
    offCtx.fillRect(0, 0, w, h);
    offCtx.drawImage(img, 0, 0, w, h);

    const imgData = offCtx.getImageData(0, 0, w, h).data;
    const weights = new Float32Array(w * h);

    // Extraer luminancia e invertir: oscuro = mayor peso/densidad
    for (let i = 0, j = 0; i < imgData.length; i += 4, j++) {
      const r = imgData[i];
      const g = imgData[i + 1];
      const b = imgData[i + 2];

      // Luminancia estándar perceptiva ITU-R BT.601
      const brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

      // Invertir (0 = blanco, 1 = negro) y aplicar curva gamma (2.2) para alto contraste
      const darkness = 1 - brightness;
      weights[j] = Math.pow(Math.max(0, darkness), 2.2);
    }

    this.imageWeights = weights;
  }

  generateFallbackPattern() {
    // Genera un patrón procedural reconocible (silueta de científica con microscopio y doble hélice)
    const w = this.config.width;
    const h = this.config.height;
    const weights = new Float32Array(w * h);

    const cx = w / 2;
    const cy = h / 2;

    for (let y = 0, i = 0; y < h; y++) {
      for (let x = 0; x < w; x++, i++) {
        // Cabeza / cabello / rostro
        const dHead = Math.hypot(x - cx, y - (cy - 60));
        // Torso / bata de laboratorio
        const dTorso = Math.hypot(x - cx, y - (cy + 130));
        // Ojos
        const dEyeL = Math.hypot(x - (cx - 28), y - (cy - 70));
        const dEyeR = Math.hypot(x - (cx + 28), y - (cy - 70));

        let val = 0;
        if (dHead < 110) val += 0.75;
        if (dHead < 80) val -= 0.35; // rostro más claro
        if (dEyeL < 12 || dEyeR < 12) val += 0.8; // cejas/ojos
        if (dTorso < 170) val += 0.6; // hombros

        // Borde exterior suave
        val *= Math.max(0, 1 - Math.hypot(x - cx, y - cy) / (w * 0.48));

        weights[i] = Math.max(0, Math.min(1, val));
      }
    }

    this.imageWeights = weights;
  }

  /* ------------------------------------------------------------------------
     4. ALGORITMO DE VORONOI STIPPLING (RELAJACIÓN DE LLOYD PONDERADA)
     ------------------------------------------------------------------------ */
  async precalculateVoronoi() {
    if (!this.imageWeights || typeof d3 === "undefined" || !d3.Delaunay) {
      console.warn("Esperando librerías D3 / d3-delaunay...");
      return;
    }

    const n = this.config.particleCount;
    const w = this.config.width;
    const h = this.config.height;
    const iterations = this.config.lloydIterations;
    const weights = this.imageWeights;

    // 1. Muestreo inicial ponderado (rejection sampling) para converger más rápido
    const points = new Float64Array(n * 2);
    let count = 0;
    let attempts = 0;
    const maxAttempts = n * 40;

    while (count < n && attempts < maxAttempts) {
      attempts++;
      const rx = Math.floor(Math.random() * w);
      const ry = Math.floor(Math.random() * h);
      const pixelIdx = ry * w + rx;
      const weight = weights[pixelIdx];

      // Aceptar con probabilidad proporcional a la densidad
      if (Math.random() < weight + 0.05) {
        points[count * 2] = rx;
        points[count * 2 + 1] = ry;
        count++;
      }
    }

    // Rellenar aleatoriamente si quedaron puntos pendientes
    while (count < n) {
      points[count * 2] = Math.random() * w;
      points[count * 2 + 1] = Math.random() * h;
      count++;
    }

    // 2. Iteraciones de Relajación de Lloyd
    // Optimizada mediante 'delaunay.find(x, y, warmIndex)' sobre la cuadrícula
    const centroidsX = new Float64Array(n);
    const centroidsY = new Float64Array(n);
    const cellWeights = new Float64Array(n);

    for (let it = 0; it < iterations; it++) {
      const delaunay = new d3.Delaunay(points);

      centroidsX.fill(0);
      centroidsY.fill(0);
      cellWeights.fill(0);

      // Recorrer los píxeles acumulando centroides ponderados
      let c = 0;
      for (let y = 0, i = 0; y < h; y++) {
        for (let x = 0; x < w; x++, i++) {
          const weight = weights[i];
          // Búsqueda contigua ultrarrápida: el píxel actual suele estar en la misma celda o vecina
          c = delaunay.find(x, y, c);
          cellWeights[c] += weight;
          centroidsX[c] += x * weight;
          centroidsY[c] += y * weight;
        }
      }

      // Desplazar cada punto al centro de masa de su celda de Voronoi
      for (let i = 0; i < n; i++) {
        const totalW = cellWeights[i];
        if (totalW > 0) {
          points[i * 2] = centroidsX[i] / totalW;
          points[i * 2 + 1] = centroidsY[i] / totalW;
        }
      }
    }

    // 3. Asignar las posiciones finales de reposo a cada partícula
    const minR = this.config.particleRadiusMin;
    const maxR = this.config.particleRadiusMax;

    // Calcular peso máximo de celda para normalizar el radio de los puntos
    let maxCellWeight = 1;
    for (let i = 0; i < n; i++) {
      if (cellWeights[i] > maxCellWeight) maxCellWeight = cellWeights[i];
    }

    for (let i = 0; i < n; i++) {
      const p = this.particles[i];
      p.targetX = points[i * 2];
      p.targetY = points[i * 2 + 1];

      // El radio del punto aumenta en zonas densas/oscuras (técnica de estarcido)
      const normDensity = Math.min(1, cellWeights[i] / (maxCellWeight * 0.75));
      p.targetRadius = minR + normDensity * (maxR - minR);
    }

    this.voronoiCalculated = true;
    console.log(`[ORCID Stippling] Voronoi calculado exitosamente tras ${iterations} iteraciones.`);
  }

  /* ------------------------------------------------------------------------
     5. LÓGICA DE TRANSICIÓN Y FÍSICA DE PARTÍCULAS
     ------------------------------------------------------------------------ */
  startOrdering() {
    if (!this.voronoiCalculated) {
      this.loaderOverlay.classList.remove("hidden");
      this.loaderMessage.textContent = "Procesando retrato de Margarita Salas mediante Voronoi...";
      setTimeout(async () => {
        await this.precalculateVoronoi();
        this.loaderOverlay.classList.add("hidden");
        this.executeOrderTransition();
      }, 50);
      return;
    }

    this.executeOrderTransition();
  }

  executeOrderTransition() {
    this.state = STATE.ORDERING;
    this.statusPill.className = "status-pill status-ordering";
    this.statusPill.textContent = "Estado: Convergencia ORCID";
    this.statusDesc.textContent = "Asignando coordenadas persistentes: de la dispersión al orden.";
  }

  resetToChaos() {
    this.state = STATE.CHAOS;
    this.statusPill.className = "status-pill status-chaos";
    this.statusPill.textContent = "Estado: Caos inicial";
    this.statusDesc.textContent = "5.000 partículas en movimiento browniano (atribución dispersa).";

    // Reinyectar velocidad caótica a todas las partículas
    for (const p of this.particles) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 1.0 + Math.random() * 2.0;
      p.vx = Math.cos(angle) * speed;
      p.vy = Math.sin(angle) * speed;
      p.currentRadius = 1.4 + Math.random() * 0.8;
    }
  }

  /* ------------------------------------------------------------------------
     6. BUCLE PRINCIPAL DE ANIMACIÓN Y FÍSICA
     ------------------------------------------------------------------------ */
  animate(currentTime) {
    const dt = Math.min(32, currentTime - this.lastTime);
    this.lastTime = currentTime;

    const ctx = this.ctx;
    const w = this.config.width;
    const h = this.config.height;

    // Limpiar el lienzo
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, w, h);

    const isChaos = this.state === STATE.CHAOS;
    const isOrdering = this.state === STATE.ORDERING;
    const isSettled = this.state === STATE.SETTLED;

    // Variables de resorte para la convergencia
    const springK = 0.045; // Fuerza atractora al centroide
    const damping = 0.88;  // Fricción de frenado

    // Detección de dispersión por interacción de ratón
    const mouseX = this.mouse.x;
    const mouseY = this.mouse.y;
    const hasMouse = this.mouse.isHovering;

    // Radio de dispersión táctil sobre nodos activos
    let repelRadius = 75;
    let repelStrength = 3.5;

    let totalDisplacement = 0;

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];

      if (isChaos) {
        // ESTADO 1: CAOS BROWNIANO
        // Fluctuación aleatoria
        p.vx += (Math.random() - 0.5) * 0.35;
        p.vy += (Math.random() - 0.5) * 0.35;

        // Amortiguación suave para no acelerar infinitamente
        p.vx *= 0.985;
        p.vy *= 0.985;

        p.x += p.vx;
        p.y += p.vy;

        // Rebotes elásticos en los bordes
        if (p.x < 5) { p.x = 5; p.vx = Math.abs(p.vx); }
        if (p.x > w - 5) { p.x = w - 5; p.vx = -Math.abs(p.vx); }
        if (p.y < 5) { p.y = 5; p.vy = Math.abs(p.vy); }
        if (p.y > h - 5) { p.y = h - 5; p.vy = -Math.abs(p.vy); }

      } else {
        // ESTADOS 2 y 3: CONVERGENCIA O RETRATO ASENTADO
        // Resorte hacia la coordenada meta (targetX, targetY)
        const dx = p.targetX - p.x;
        const dy = p.targetY - p.y;
        totalDisplacement += Math.abs(dx) + Math.abs(dy);

        p.vx += dx * springK;
        p.vy += dy * springK;
        p.vx *= damping;
        p.vy *= damping;

        p.x += p.vx;
        p.y += p.vy;

        // Ajuste gradual del radio del punto
        p.currentRadius += (p.targetRadius - p.currentRadius) * 0.05;

        // Sutil efecto de "respiración" orgánica en reposo
        if (isSettled) {
          const breath = Math.sin(currentTime * p.breathSpeed + p.phase) * 0.45;
          p.x += breath * 0.3;
          p.y += breath * 0.3;
        }

        // DISPERSIÓN REACTIVA: Si el ratón interactúa cerca de un nodo
        if (hasMouse) {
          const distToMouse = Math.hypot(p.x - mouseX, p.y - mouseY);
          if (distToMouse < repelRadius && distToMouse > 0.1) {
            const force = (1 - distToMouse / repelRadius) * repelStrength;
            const pushX = ((p.x - mouseX) / distToMouse) * force;
            const pushY = ((p.y - mouseY) / distToMouse) * force;
            p.vx += pushX;
            p.vy += pushY;
          }
        }
      }

      // Dibujar la partícula (punto de estarcido)
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.currentRadius, 0, Math.PI * 2);

      if (isChaos) {
        // En caos: puntos de color gris pizarra oscuro con ligera variabilidad
        ctx.fillStyle = "#334155";
      } else {
        // En orden: tinta profunda con tono ébano (#111827)
        ctx.fillStyle = "#111827";
      }
      ctx.fill();
    }

    // Transición de estado: Si las partículas ya están muy cerca de su objetivo
    if (isOrdering && totalDisplacement / this.particles.length < 0.6) {
      this.state = STATE.SETTLED;
      this.statusPill.className = "status-pill status-settled";
      this.statusPill.textContent = "Estado: Retrato Consolidado";
      this.statusDesc.textContent = "ORCID establecido · Explora los 4 nodos interactivos.";
    }

    // Dibujar conexiones tenues en estado de Caos (metáfora de citas rotas / duplicidad)
    if (isChaos) {
      this.drawChaosConnections(ctx);
    }

    requestAnimationFrame(this.animate);
  }

  drawChaosConnections(ctx) {
    // Dibuja sutiles enlaces entre partículas muy cercanas para sugerir la confusión de homonimias
    ctx.lineWidth = 0.5;
    ctx.strokeStyle = "rgba(245, 158, 11, 0.12)";
    const sampleSize = 180; // Muestrear solo una parte para mantener 60 FPS

    ctx.beginPath();
    for (let i = 0; i < sampleSize; i++) {
      const p1 = this.particles[i];
      for (let j = i + 1; j < sampleSize; j++) {
        const p2 = this.particles[j];
        const dist = Math.hypot(p1.x - p2.x, p1.y - p2.y);
        if (dist < 32) {
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
        }
      }
    }
    ctx.stroke();
  }

  /* ------------------------------------------------------------------------
     7. SUPERPOSICIÓN DE GUÍAS DE NODOS (SVG)
     ------------------------------------------------------------------------ */
  initNodeGuides() {
    this.nodeOverlay.innerHTML = "";
    const ns = "http://www.w3.org/2000/svg";

    this.config.nodes.forEach((node, index) => {
      const group = document.createElementNS(ns, "g");
      group.setAttribute("id", `guide-${node.id}`);

      // Círculo del área interactiva (hitbox visual)
      const circle = document.createElementNS(ns, "circle");
      circle.setAttribute("cx", node.x);
      circle.setAttribute("cy", node.y);
      circle.setAttribute("r", node.r);
      circle.setAttribute("class", "node-circle-guide");
      circle.setAttribute("id", `circle-${node.id}`);

      // Etiqueta numerada sobre la zona
      const text = document.createElementNS(ns, "text");
      text.setAttribute("x", node.x);
      text.setAttribute("y", node.y - node.r - 8);
      text.setAttribute("class", "node-label-guide");
      text.textContent = `0${index + 1} · ${node.zoneName}`;

      group.appendChild(circle);
      group.appendChild(text);
      this.nodeOverlay.appendChild(group);
    });
  }

  /* ------------------------------------------------------------------------
     8. INTERACTIVIDAD, HITBOXES Y MODALES (FASE 2)
     ------------------------------------------------------------------------ */
  initEventListeners() {
    // 1. Botón "Generar ORCID"
    this.btnOrder.addEventListener("click", () => {
      this.startOrdering();
    });

    // 2. Botón "Restablecer Caos"
    this.btnChaos.addEventListener("click", () => {
      this.resetToChaos();
    });

    // 3. Toggle de Guías Visuales
    this.toggleGuides.addEventListener("change", (e) => {
      if (e.target.checked) {
        this.nodeOverlay.classList.remove("hidden-guides");
      } else {
        this.nodeOverlay.classList.add("hidden-guides");
      }
    });

    // 4. Carga de imagen local alternativa
    this.imageFileInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (event) => {
        this.loadImage(event.target.result);
      };
      reader.readAsDataURL(file);
    });

    // 5. Arrastrar y soltar imagen sobre el lienzo
    this.canvas.addEventListener("dragover", (e) => e.preventDefault());
    this.canvas.addEventListener("drop", (e) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file && file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = (event) => this.loadImage(event.target.result);
        reader.readAsDataURL(file);
      }
    });

    // 6. Seguimiento del ratón sobre el canvas para detección de Hitboxes
    const getLogicalMousePos = (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const scaleX = this.config.width / rect.width;
      const scaleY = this.config.height / rect.height;
      return {
        x: (e.clientX - rect.left) * scaleX,
        y: (e.clientY - rect.top) * scaleY
      };
    };

    this.canvas.addEventListener("mousemove", (e) => {
      const pos = getLogicalMousePos(e);
      this.mouse.x = pos.x;
      this.mouse.y = pos.y;
      this.mouse.isHovering = true;

      // Verificar si está dentro de alguna de las 4 hitboxes
      const hitNode = this.detectHitNode(pos.x, pos.y);
      this.highlightNode(hitNode ? hitNode.id : null);
    });

    this.canvas.addEventListener("mouseleave", () => {
      this.mouse.isHovering = false;
      this.mouse.x = -1000;
      this.mouse.y = -1000;
      this.highlightNode(null);
    });

    // 7. Clic sobre el lienzo para abrir información del nodo
    this.canvas.addEventListener("click", (e) => {
      const pos = getLogicalMousePos(e);
      const hitNode = this.detectHitNode(pos.x, pos.y);
      if (hitNode) {
        this.openModal(hitNode);
      }
    });

    // 8. Clic sobre los botones de la barra lateral
    document.querySelectorAll(".node-pill").forEach((btn) => {
      btn.addEventListener("click", () => {
        const nodeId = btn.getAttribute("data-node");
        const node = this.config.nodes.find((n) => n.id === nodeId);
        if (node) {
          this.openModal(node);
          this.highlightNode(nodeId);
        }
      });
    });

    // 9. Cierre del modal flotante
    this.modalClose.addEventListener("click", () => this.closeModal());
    this.modalUnderstoodBtn.addEventListener("click", () => this.closeModal());

    this.modalOverlay.addEventListener("click", (e) => {
      if (e.target === this.modalOverlay) {
        this.closeModal();
      }
    });

    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !this.modalOverlay.classList.contains("hidden")) {
        this.closeModal();
      }
    });
  }

  detectHitNode(x, y) {
    for (const node of this.config.nodes) {
      const dist = Math.hypot(x - node.x, y - node.y);
      if (dist <= node.r) {
        return node;
      }
    }
    return null;
  }

  highlightNode(nodeId) {
    // Actualizar guías SVG
    this.config.nodes.forEach((n) => {
      const circle = document.getElementById(`circle-${n.id}`);
      if (circle) {
        if (n.id === nodeId) {
          circle.classList.add("active");
        } else {
          circle.classList.remove("active");
        }
      }
    });

    // Actualizar sidebar pills
    document.querySelectorAll(".node-pill").forEach((pill) => {
      if (pill.getAttribute("data-node") === nodeId) {
        pill.classList.add("active");
      } else {
        pill.classList.remove("active");
      }
    });
  }

  openModal(node) {
    this.modalBadge.textContent = node.badge.toUpperCase();
    this.modalZoneTag.textContent = node.zoneName;
    this.modalTitle.textContent = node.title;
    this.modalText.textContent = node.text;

    this.modalOverlay.classList.remove("hidden");
    this.modalOverlay.setAttribute("aria-hidden", "false");
  }

  closeModal() {
    this.modalOverlay.classList.add("hidden");
    this.modalOverlay.setAttribute("aria-hidden", "true");
  }
}

/* ==========================================================================
   ARRANQUE DE LA APLICACIÓN AL CARGAR EL DOM
   ========================================================================== */
window.addEventListener("DOMContentLoaded", () => {
  window.stippleSim = new VoronoiStippleSimulation(CONFIG);
});
