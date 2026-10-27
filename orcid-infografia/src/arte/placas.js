/* =====================================================================
   Placas — ocho láminas de acuarela puntillista, una por nodo.
   Depende de art.js (window.Arte). Deterministas por semilla.
   ===================================================================== */
(function (global) {
  'use strict';

  var A = global.Arte;
  var P = A.PALETA;

  /* ---- helpers ------------------------------------------------------- */

  function base(canvas, seed, aguadas) {
    var p = A.preparar(canvas);
    A.papel(p.ctx, p.w, p.h, seed, P.papelAlto);
    (aguadas || []).forEach(function (c, i) {
      A.aguada(p.ctx, {
        x: p.w * c[0], y: p.h * c[1], r: Math.min(p.w, p.h) * c[2],
        color: c[3], alpha: c[4], seed: seed + i + 1
      });
    });
    p.ctx.globalCompositeOperation = 'multiply';
    return p;
  }

  function puntos(canvas, fn) {
    var p = A.preparar(canvas);
    var ctx = p.ctx;
    A.papel(ctx, p.w, p.h, 0, P.papelAlto);
    ctx.save();
    ctx.globalCompositeOperation = 'multiply';
    fn(ctx, p.w, p.h, p);
    ctx.restore();
  }

  function discoPuntos(ctx, cx, cy, r, color, seed, densidad, paso, radio) {
    var rnd = A.prng(seed);
    paso = paso || 3.4;
    for (var y = cy - r; y <= cy + r; y += paso) {
      for (var x = cx - r; x <= cx + r; x += paso) {
        var px = x + (rnd() - 0.5) * paso * 0.9;
        var py = y + (rnd() - 0.5) * paso * 0.9;
        var d = Math.sqrt((px - cx) * (px - cx) + (py - cy) * (py - cy)) / r;
        if (d > 1) continue;
        if (rnd() > densidad * (1 - d * 0.18)) continue;
        ctx.globalAlpha = 0.45 + rnd() * 0.55;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(px, py, (radio || 1.1) * (0.55 + rnd() * 0.9), 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  function anilloPuntos(ctx, cx, cy, r, grosor, color, seed, densidad, paso, radio) {
    var rnd = A.prng(seed);
    paso = paso || 3.2;
    for (var y = cy - r - grosor * 3; y <= cy + r + grosor * 3; y += paso) {
      for (var x = cx - r - grosor * 3; x <= cx + r + grosor * 3; x += paso) {
        var px = x + (rnd() - 0.5) * paso * 0.9;
        var py = y + (rnd() - 0.5) * paso * 0.9;
        var d = Math.abs(Math.sqrt((px - cx) * (px - cx) + (py - cy) * (py - cy)) - r);
        if (d > grosor) continue;
        var b = 1 - d / grosor;
        if (rnd() > densidad * b) continue;
        ctx.globalAlpha = 0.45 + rnd() * 0.55;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(px, py, (radio || 1.1) * (0.55 + rnd() * 0.9), 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  function lineaPuntos(ctx, x1, y1, x2, y2, color, seed, paso, radio, alpha, jitter) {
    var rnd = A.prng(seed);
    var len = Math.sqrt((x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1));
    var n = Math.max(2, Math.floor(len / (paso || 4)));
    jitter = jitter == null ? 2.4 : jitter;
    for (var i = 0; i <= n; i++) {
      var t = i / n;
      var x = x1 + (x2 - x1) * t + (rnd() - 0.5) * jitter * 2;
      var y = y1 + (y2 - y1) * t + (rnd() - 0.5) * jitter * 2;
      ctx.globalAlpha = (alpha || 0.7) * (0.6 + rnd() * 0.4);
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, (radio || 1) * (0.5 + rnd() * 0.9), 0, Math.PI * 2);
      ctx.fill();
    }
  }

  /* Catmull-Rom para trazos orgánicos */
  function curva(puntos, muestras) {
    var out = [];
    for (var i = 0; i < puntos.length - 1; i++) {
      var p0 = puntos[Math.max(0, i - 1)];
      var p1 = puntos[i];
      var p2 = puntos[i + 1];
      var p3 = puntos[Math.min(puntos.length - 1, i + 2)];
      for (var j = 0; j < muestras; j++) {
        var t = j / muestras;
        var t2 = t * t, t3 = t2 * t;
        out.push([
          0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
          0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
        ]);
      }
    }
    return out;
  }

  function salpicadura(ctx, w, h, seed, n) {
    var r = A.prng(seed);
    for (var i = 0; i < (n || 60); i++) {
      ctx.globalAlpha = 0.07 + r() * 0.16;
      ctx.fillStyle = r() > 0.5 ? P.rojo : P.tinta;
      ctx.beginPath();
      ctx.arc(r() * w, r() * h, 0.5 + r() * 1.2, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  /* ---- 01 · dos huellas ---------------------------------------------- */
  function clones(canvas) {
    A.laminasHuella(canvas, 11);
  }

  /* ---- 02 · firma y filiación ---------------------------------------- */
  function firma(canvas) {
    var seed = 21;
    var p = base(canvas, seed, [
      [0.36, 0.56, 0.40, P.coral, 0.20],
      [0.64, 0.44, 0.40, P.indigo, 0.16]
    ]);
    var ctx = p.ctx, w = p.w, h = p.h;

    // bloques de filiación (faint)
    ctx.save();
    ctx.globalCompositeOperation = 'multiply';
    [[0.09, 0.12], [0.09, 0.235]].forEach(function (b, k) {
      var x = w * b[0], y = h * b[1], bw = w * 0.26, bh = h * 0.07;
      for (var yy = y; yy <= y + bh; yy += 4.2) {
        for (var xx = x; xx <= x + bw; xx += 4.2) {
          var borde = (yy - y < 3) || (y + bh - yy < 3) || (xx - x < 3) || (x + bw - xx < 3);
          if (!borde) continue;
          ctx.globalAlpha = 0.34;
          ctx.fillStyle = P.tintaSuave;
          ctx.beginPath();
          ctx.arc(xx, yy, 1, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    });
    ctx.restore();

    // firma
    var trazo = curva([
      [w * 0.10, h * 0.68], [w * 0.14, h * 0.52], [w * 0.17, h * 0.44],
      [w * 0.21, h * 0.48], [w * 0.23, h * 0.62], [w * 0.25, h * 0.70],
      [w * 0.28, h * 0.56], [w * 0.30, h * 0.46], [w * 0.34, h * 0.50],
      [w * 0.36, h * 0.66], [w * 0.39, h * 0.60], [w * 0.43, h * 0.48],
      [w * 0.48, h * 0.44], [w * 0.53, h * 0.54], [w * 0.58, h * 0.62],
      [w * 0.63, h * 0.52], [w * 0.68, h * 0.46], [w * 0.73, h * 0.52],
      [w * 0.77, h * 0.62], [w * 0.81, h * 0.52], [w * 0.85, h * 0.44]
    ], 22);
    var rnd = A.prng(seed + 5);
    ctx.save();
    ctx.globalCompositeOperation = 'multiply';
    trazo.forEach(function (pt, i) {
      var t = i / trazo.length;
      var grosor = 1.2 + 2.2 * Math.abs(Math.sin(t * Math.PI * 7.3));
      for (var k = 0; k < 3; k++) {
        ctx.globalAlpha = 0.55 + rnd() * 0.35;
        ctx.fillStyle = P.tinta;
        ctx.beginPath();
        ctx.arc(pt[0] + (rnd() - 0.5) * 2.6, pt[1] + (rnd() - 0.5) * 2.6, grosor * (0.6 + rnd() * 0.7), 0, Math.PI * 2);
        ctx.fill();
      }
    });
    // rúbrica: cola y subrayado
    var cola = curva([[w * 0.85, h * 0.44], [w * 0.87, h * 0.62], [w * 0.84, h * 0.70]], 12);
    var sub = curva([[w * 0.84, h * 0.70], [w * 0.72, h * 0.73], [w * 0.58, h * 0.71], [w * 0.46, h * 0.74]], 14);
    cola.concat(sub).forEach(function (pt) {
      for (var k = 0; k < 2; k++) {
        ctx.globalAlpha = 0.5 + rnd() * 0.3;
        ctx.beginPath();
        ctx.arc(pt[0] + (rnd() - 0.5) * 2.2, pt[1] + (rnd() - 0.5) * 2.2, 1 + rnd() * 1.4, 0, Math.PI * 2);
        ctx.fill();
      }
    });
    ctx.restore();

    // sello ORCID al final de la firma
    A.aguada(ctx, { x: w * 0.88, y: h * 0.68, r: Math.min(w, h) * 0.055, color: P.orcid, alpha: 0.35, seed: seed + 9 });
    anilloPuntos(ctx, w * 0.88, h * 0.68, Math.min(w, h) * 0.042, 3, P.verde, seed + 10, 0.95, 2.6, 1.2);
    ctx.save();
    ctx.fillStyle = P.verde;
    ctx.globalAlpha = 0.9;
    ctx.beginPath();
    ctx.arc(w * 0.88, h * 0.68, Math.min(w, h) * 0.008, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    salpicadura(ctx, w, h, seed + 30, 40);
  }

  /* ---- 03 · dieciséis dígitos ---------------------------------------- */
  function dieciseis(canvas) {
    var seed = 31;
    var p = base(canvas, seed, [
      [0.50, 0.50, 0.46, P.orcid, 0.16],
      [0.64, 0.40, 0.28, P.verde, 0.10]
    ]);
    var ctx = p.ctx, w = p.w, h = p.h;
    var cx = w * 0.5, cy = h * 0.5, R = Math.min(w, h);

    // anillos tenues
    anilloPuntos(ctx, cx, cy, R * 0.40, 2.2, P.tintaSuave, seed + 1, 0.22, 4.6, 0.85);
    anilloPuntos(ctx, cx, cy, R * 0.335, 1.8, P.tintaSuave, seed + 2, 0.18, 4.8, 0.8);

    // dieciséis barras (los dígitos del identificador)
    for (var i = 0; i < 16; i++) {
      var a = (i / 16) * Math.PI * 2 - Math.PI / 2;
      var x = cx + Math.cos(a) * R * 0.29;
      var y = cy + Math.sin(a) * R * 0.29;
      var largo = R * (i % 4 === 0 ? 0.055 : 0.038);
      var grueso = R * 0.012;
      var color = i % 4 === 0 ? P.rojo : P.tinta;
      var rnd = A.prng(seed + 100 + i);
      for (var yy = -largo / 2; yy <= largo / 2; yy += 2.4) {
        for (var xx = -grueso / 2; xx <= grueso / 2; xx += 2.4) {
          ctx.globalAlpha = 0.6 + rnd() * 0.35;
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(x + xx + (rnd() - 0.5) * 0.9, y + yy + (rnd() - 0.5) * 0.9, 0.9 + rnd() * 0.5, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }

    // núcleo: aro del identificador
    anilloPuntos(ctx, cx, cy, R * 0.10, 3.4, P.verde, seed + 41, 0.95, 2.8, 1.2);
    discoPuntos(ctx, cx, cy, R * 0.018, P.verde, seed + 42, 1, 2.4, 1.1);

    salpicadura(ctx, w, h, seed + 50, 40);
  }

  /* ---- 04 · cuatro pasos --------------------------------------------- */
  function cuatro(canvas) {
    var seed = 41;
    var p = base(canvas, seed, [
      [0.24, 0.56, 0.36, P.coral, 0.14],
      [0.74, 0.44, 0.36, P.indigo, 0.14]
    ]);
    var ctx = p.ctx, w = p.w, h = p.h;
    var y = h * 0.52;
    var xs = [0.18, 0.39, 0.61, 0.82].map(function (v) { return w * v; });
    var r = Math.min(w, h) * 0.088;

    // guía
    lineaPuntos(ctx, xs[0], y, xs[3], y, P.tintaSuave, seed + 1, 5, 0.9, 0.35, 1.6);

    xs.forEach(function (x, i) {
      anilloPuntos(ctx, x, y, r, 3.2, P.tinta, seed + 10 + i, 0.55, 3.4, 0.9);
      discoPuntos(ctx, x, y, r * 0.86, i === 3 ? P.verde : P.indigo, seed + 20 + i,
        0.10 + i * 0.30, 3.5, 1.05);
    });

    // check en el último
    var ck = xs[3];
    ctx.save();
    ctx.globalCompositeOperation = 'source-over';
    for (var k = 0; k < 2; k++) {
      lineaPuntos(ctx, ck - r * 0.22, y + k * 1.6, ck - r * 0.02, y + r * 0.22 + k * 1.6, P.papelAlto, seed + 60 + k, 2.2, 2.2, 0.95, 0.6);
      lineaPuntos(ctx, ck - r * 0.02, y + r * 0.22 + k * 1.6, ck + r * 0.26, y - r * 0.20 + k * 1.6, P.papelAlto, seed + 70 + k, 2.2, 2.2, 0.95, 0.6);
    }
    ctx.restore();

    salpicadura(ctx, w, h, seed + 80, 40);
  }

  /* ---- 05 · visibilidad ---------------------------------------------- */
  function visibilidad(canvas) {
    var seed = 51;
    var p = base(canvas, seed, [
      [0.22, 0.58, 0.34, P.coral, 0.16],
      [0.50, 0.44, 0.32, P.indigo, 0.12],
      [0.78, 0.58, 0.32, P.verde, 0.12]
    ]);
    var ctx = p.ctx, w = p.w, h = p.h;
    var y = h * 0.52, r = Math.min(w, h) * 0.135;

    // todo el mundo: disco lleno
    discoPuntos(ctx, w * 0.20, y, r, P.rojo, seed + 1, 0.95, 3.4, 1.15);
    // partes de confianza: media luna
    var rnd = A.prng(seed + 2);
    for (var yy = y - r; yy <= y + r; yy += 3.4) {
      for (var xx = w * 0.5 - r; xx <= w * 0.5 + r; xx += 3.4) {
        var px = xx + (rnd() - 0.5) * 3, py = yy + (rnd() - 0.5) * 3;
        var d = Math.sqrt((px - w * 0.5) * (px - w * 0.5) + (py - y) * (py - y)) / r;
        if (d > 1) continue;
        var dens = px < w * 0.5 ? 0.95 : 0.10;
        if (rnd() > dens) continue;
        ctx.globalAlpha = 0.45 + rnd() * 0.55;
        ctx.fillStyle = P.indigo;
        ctx.beginPath();
        ctx.arc(px, py, 1.15 * (0.55 + rnd() * 0.9), 0, Math.PI * 2);
        ctx.fill();
      }
    }
    // solo yo: aro
    anilloPuntos(ctx, w * 0.80, y, r, 5.2, P.verde, seed + 3, 0.95, 3.0, 1.3);
    anilloPuntos(ctx, w * 0.80, y, r * 0.55, 1.6, P.tintaSuave, seed + 4, 0.35, 4.2, 0.9);

    salpicadura(ctx, w, h, seed + 10, 45);
  }

  /* ---- 06 · gestión (archivo) ---------------------------------------- */
  function archivo(canvas) {
    var seed = 61;
    var p = base(canvas, seed, [
      [0.30, 0.58, 0.38, P.indigo, 0.12],
      [0.72, 0.42, 0.34, P.coral, 0.10]
    ]);
    var ctx = p.ctx, w = p.w, h = p.h;

    var cols = 4, filas = 3;
    var x0 = w * 0.08, y0 = h * 0.13;
    var anchoTotal = w * 0.84, altoTotal = h * 0.74;
    var gapX = w * 0.025, gapY = h * 0.035;
    var mw = (anchoTotal - gapX * (cols - 1)) / cols;
    var mh = (altoTotal - gapY * (filas - 1)) / filas;

    for (var f = 0; f < filas; f++) {
      for (var c = 0; c < cols; c++) {
        var x = x0 + c * (mw + gapX);
        var y = y0 + f * (mh + gapY);
        var activa = (f === 1 && c === 2);
        var color = activa ? P.rojo : P.tintaSuave;
        var alpha = activa ? 0.62 : 0.22;

        ctx.save();
        ctx.globalAlpha = alpha;
        ctx.fillStyle = color;
        for (var xx = x; xx <= x + mw; xx += 4.2) {
          ctx.beginPath(); ctx.arc(xx, y, 1.1, 0, Math.PI * 2); ctx.fill();
          ctx.beginPath(); ctx.arc(xx, y + mh, 1.1, 0, Math.PI * 2); ctx.fill();
        }
        for (var yy = y; yy <= y + mh; yy += 4.2) {
          ctx.beginPath(); ctx.arc(x, yy, 1.1, 0, Math.PI * 2); ctx.fill();
          ctx.beginPath(); ctx.arc(x + mw, yy, 1.1, 0, Math.PI * 2); ctx.fill();
        }
        // asa
        ctx.globalAlpha = alpha + 0.2;
        ctx.beginPath();
        ctx.arc(x + mw / 2, y + mh / 2, activa ? 3.6 : 2.2, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

        if (activa) {
          discoPuntos(ctx, x + mw / 2, y + mh / 2, Math.min(mw, mh) * 0.34, P.rojo, seed + 80, 0.9, 3.0, 1.2);
          anilloPuntos(ctx, x + mw / 2, y + mh / 2, Math.min(mw, mh) * 0.34, 2.4, P.tinta, seed + 81, 0.5, 3.6, 0.9);
        } else {
          discoPuntos(ctx, x + mw / 2, y + mh / 2, Math.min(mw, mh) * 0.30, P.indigo, seed + 20 + f * 10 + c, 0.10, 4.4, 0.9);
        }
      }
    }

    salpicadura(ctx, w, h, seed + 90, 35);
  }

  /* ---- 07 · red / piloto automático ---------------------------------- */
  function red(canvas) {
    var seed = 71;
    var p = base(canvas, seed, [
      [0.50, 0.52, 0.44, P.orcid, 0.18],
      [0.30, 0.40, 0.28, P.coral, 0.10]
    ]);
    var ctx = p.ctx, w = p.w, h = p.h;
    var cx = w * 0.5, cy = h * 0.52, R = Math.min(w, h);

    // centro
    anilloPuntos(ctx, cx, cy, R * 0.10, 4.2, P.verde, seed + 1, 0.95, 2.8, 1.3);
    discoPuntos(ctx, cx, cy, R * 0.045, P.tinta, seed + 2, 0.9, 2.6, 1.1);

    // seis satélites
    for (var i = 0; i < 6; i++) {
      var a = (i / 6) * Math.PI * 2 - Math.PI / 2;
      var x = cx + Math.cos(a) * R * 0.30;
      var y = cy + Math.sin(a) * R * 0.30;
      lineaPuntos(ctx, cx + Math.cos(a) * R * 0.12, cy + Math.sin(a) * R * 0.12,
        x - Math.cos(a) * R * 0.055, y - Math.sin(a) * R * 0.055,
        P.tintaSuave, seed + 10 + i, 5.2, 0.95, 0.55, 1.4);
      discoPuntos(ctx, x, y, R * 0.055, i % 2 ? P.coral : P.indigo, seed + 20 + i, 0.85, 2.8, 1.2);
      anilloPuntos(ctx, x, y, R * 0.075, 2.0, P.tinta, seed + 30 + i, 0.4, 3.6, 0.9);
    }

    salpicadura(ctx, w, h, seed + 40, 45);
  }

  /* ---- 08 · duplicados ----------------------------------------------- */
  function fusion(canvas) {
    var seed = 81;
    var p = base(canvas, seed, [
      [0.34, 0.52, 0.34, P.indigo, 0.12],
      [0.62, 0.50, 0.34, P.coral, 0.14]
    ]);
    var ctx = p.ctx, w = p.w, h = p.h;
    var y = h * 0.52, r = Math.min(w, h) * 0.20;

    // original tenue
    anilloPuntos(ctx, w * 0.38, y, r, 3.0, P.tintaSuave, seed + 1, 0.30, 4.2, 0.9);
    discoPuntos(ctx, w * 0.38, y, r * 0.88, P.indigo, seed + 2, 0.08, 4.4, 0.9);

    // duplicado que se queda
    anilloPuntos(ctx, w * 0.62, y, r, 4.0, P.tinta, seed + 3, 0.60, 3.2, 1.0);
    discoPuntos(ctx, w * 0.62, y, r * 0.88, P.rojo, seed + 4, 0.16, 3.6, 1.05);

    // flecha de fusión
    var pts = curva([[w * 0.46, y - r * 1.12], [w * 0.50, y - r * 1.30], [w * 0.56, y - r * 1.10]], 18);
    pts.forEach(function (pt) {
      ctx.save();
      ctx.globalAlpha = 0.55;
      ctx.fillStyle = P.rojo;
      ctx.beginPath();
      ctx.arc(pt[0], pt[1], 1.4, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    });
    lineaPuntos(ctx, w * 0.56, y - r * 1.10, w * 0.60, y - r * 0.92, P.rojo, seed + 5, 3, 1.4, 0.7, 1);
    lineaPuntos(ctx, w * 0.60, y - r * 0.92, w * 0.56, y - r * 0.92, P.rojo, seed + 6, 3, 1.4, 0.7, 1);

    // sello en el cruce
    A.aguada(ctx, { x: w * 0.50, y: y, r: Math.min(w, h) * 0.075, color: P.orcid, alpha: 0.28, seed: seed + 7 });
    anilloPuntos(ctx, w * 0.50, y, Math.min(w, h) * 0.055, 3.2, P.verde, seed + 8, 0.95, 2.6, 1.2);
    ctx.save();
    ctx.fillStyle = P.verde;
    ctx.globalAlpha = 0.9;
    ctx.beginPath();
    ctx.arc(w * 0.50, y, Math.min(w, h) * 0.011, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    salpicadura(ctx, w, h, seed + 20, 40);
  }

  var PLACAS = {
    clones: clones,
    firma: firma,
    dieciseis: dieciseis,
    cuatro: cuatro,
    visibilidad: visibilidad,
    archivo: archivo,
    red: red,
    fusion: fusion
  };

  global.Placas = {
    pintar: function (id, canvas) {
      var fn = PLACAS[id];
      if (fn) fn(canvas);
    },
    ids: Object.keys(PLACAS)
  };
})(window);
