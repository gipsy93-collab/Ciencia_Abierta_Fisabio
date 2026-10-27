/* =====================================================================
   Arte — acuarela puntillista determinista sobre canvas 2D
   Sin dependencias, sin red, sin estado global mutable.
   Cada lámina se genera a partir de una semilla -> mismo dibujo siempre.
   ===================================================================== */
(function (global) {
  'use strict';

  var PALETA = {
    papel: '#F7F1E4',
    papelAlto: '#FCF8EE',
    tinta: '#1D0F44',
    tintaSuave: '#5B4B7E',
    coral: '#FF647D',
    rojo: '#EB003B',
    orcid: '#A6CE39',
    verde: '#63AA16',
    indigo: '#3B2A6B',
    ocre: '#E0B071'
  };

  /* ---- utilidades ---------------------------------------------------- */

  function prng(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function rgb(hex) {
    var h = hex.replace('#', '');
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
  }

  function rgba(hex, alpha) {
    var c = rgb(hex);
    return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + (alpha == null ? 1 : alpha) + ')';
  }

  function mezcla(hex, otro, t) {
    var a = rgb(hex), b = rgb(otro);
    var m = [0, 1, 2].map(function (i) { return Math.round(a[i] + (b[i] - a[i]) * t); });
    return 'rgb(' + m[0] + ',' + m[1] + ',' + m[2] + ')';
  }

  /* Prepara un canvas para el tamaño CSS actual, con DPR acotado a 2. */
  function preparar(canvas) {
    var dpr = Math.min(global.devicePixelRatio || 1, 2);
    var caja = canvas.getBoundingClientRect();
    var w = Math.max(1, Math.round(caja.width));
    var h = Math.max(1, Math.round(caja.height));
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
    }
    var ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    return { ctx: ctx, w: w, h: h, dpr: dpr };
  }

  /* ---- papel --------------------------------------------------------- */

  var _grano = null;
  function grano() {
    if (_grano) return _grano;
    var t = document.createElement('canvas');
    t.width = t.height = 180;
    var c = t.getContext('2d');
    var img = c.createImageData(180, 180);
    var r = prng(20261027);
    for (var i = 0; i < img.data.length; i += 4) {
      var v = 150 + Math.round((r() - 0.5) * 70);
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
      img.data[i + 3] = 255;
    }
    c.putImageData(img, 0, 0);
    _grano = t;
    return t;
  }

  function papel(ctx, w, h, seed, tono) {
    var r = prng(seed || 1);
    ctx.save();
    ctx.fillStyle = tono || PALETA.papel;
    ctx.fillRect(0, 0, w, h);

    // fibras muy tenues
    var n = Math.round((w * h) / 900);
    for (var i = 0; i < n; i++) {
      var x = r() * w, y = r() * h;
      var len = 5 + r() * 30, ang = (r() - 0.5) * 0.45;
      ctx.strokeStyle = i % 4 ? 'rgba(29,15,68,0.022)' : 'rgba(255,255,255,0.30)';
      ctx.lineWidth = 0.6;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x + Math.cos(ang) * len, y + Math.sin(ang) * len);
      ctx.stroke();
    }

    // grano
    ctx.globalCompositeOperation = 'multiply';
    ctx.globalAlpha = 0.11;
    ctx.fillStyle = ctx.createPattern(grano(), 'repeat');
    ctx.fillRect(0, 0, w, h);
    ctx.restore();
  }

  /* ---- aguadas ------------------------------------------------------- */

  /* Mancha de pigmento: varias pasadas suaves, borde húmedo y granulación. */
  function aguada(ctx, o) {
    var r = prng(o.seed);
    var capas = o.capas || 11;
    var alfa = o.alpha == null ? 0.5 : o.alpha;
    var color = o.color || PALETA.indigo;

    ctx.save();
    ctx.globalCompositeOperation = 'multiply';

    for (var i = 0; i < capas; i++) {
      var rr = o.r * (0.55 + r() * 0.5);
      var cx = o.x + (r() - 0.5) * o.r * 0.5;
      var cy = o.y + (r() - 0.5) * o.r * 0.5;
      var g = ctx.createRadialGradient(cx, cy, rr * 0.04, cx, cy, rr);
      g.addColorStop(0, rgba(color, alfa * (0.36 + r() * 0.3)));
      g.addColorStop(0.55, rgba(color, alfa * 0.22));
      g.addColorStop(1, rgba(color, 0));
      ctx.fillStyle = g;
      blob(ctx, cx, cy, rr, r, (o.wob || 1) * (0.07 + r() * 0.07));
      ctx.fill();
    }

    // borde húmedo
    ctx.filter = 'blur(' + Math.max(3, o.r * 0.05) + 'px)';
    ctx.strokeStyle = rgba(color, alfa * 0.2);
    ctx.lineWidth = Math.max(2, o.r * 0.05);
    blob(ctx, o.x, o.y, o.r * 0.86, prng(o.seed + 7), (o.wob || 1) * 0.05);
    ctx.stroke();
    ctx.filter = 'none';

    // granulación
    var ng = Math.round(o.r * o.r * 0.02);
    for (var k = 0; k < ng; k++) {
      var a = r() * Math.PI * 2;
      var rad = Math.sqrt(r()) * o.r * 0.95;
      var px = o.x + Math.cos(a) * rad;
      var py = o.y + Math.sin(a) * rad;
      ctx.globalAlpha = 0.05 + r() * 0.12;
      ctx.fillStyle = r() > 0.72 ? mezcla(color, PALETA.tinta, 0.4) : color;
      ctx.beginPath();
      ctx.arc(px, py, 0.5 + r() * 1.5, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  function blob(ctx, cx, cy, r, rnd, wob) {
    var pts = 18;
    ctx.beginPath();
    for (var k = 0; k <= pts; k++) {
      var a = (k / pts) * Math.PI * 2;
      var rad = r * (1 + (rnd() - 0.5) * (wob * 2));
      var px = cx + Math.cos(a) * rad;
      var py = cy + Math.sin(a) * rad;
      if (k === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.closePath();
  }

  /* Mancha de pigmento: borde irregular y grano, como una gota seca. */
  function mancha(ctx, o) {
    var r = prng(o.seed);
    var radio = o.r;
    ctx.save();
    ctx.globalCompositeOperation = 'multiply';

    for (var k = 0; k < 6; k++) {
      ctx.globalAlpha = 0.26 + r() * 0.12;
      ctx.fillStyle = o.color;
      blob(ctx,
        o.x + (r() - 0.5) * radio * 0.16,
        o.y + (r() - 0.5) * radio * 0.16,
        radio * (0.82 + r() * 0.16),
        r, 0.10 + r() * 0.08);
      ctx.fill();
    }

    ctx.globalAlpha = 0.34;
    ctx.strokeStyle = o.color;
    ctx.lineWidth = Math.max(1.4, radio * 0.05);
    blob(ctx, o.x, o.y, radio * 0.95, prng(o.seed + 3), 0.09);
    ctx.stroke();

    for (var i = 0; i < 90; i++) {
      var ang = r() * Math.PI * 2;
      var rad = Math.sqrt(r()) * radio * 1.02;
      ctx.globalAlpha = 0.05 + r() * 0.14;
      ctx.fillStyle = r() > 0.8 ? mezcla(o.color, PALETA.tinta, 0.35) : o.color;
      ctx.beginPath();
      ctx.arc(o.x + Math.cos(ang) * rad, o.y + Math.sin(ang) * rad, 0.4 + r() * 1.2, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  /* ---- puntillismo --------------------------------------------------- */

  /* Campo de puntos con jitter. densidad(u,v) devuelve 0..1 o {p, c}. */
  function campo(ctx, o) {
    var r = prng(o.seed);
    var paso = o.paso || 4.6;
    var base = o.radio || 1.15;
    var alfa = o.alpha == null ? 0.9 : o.alpha;

    ctx.save();
    ctx.globalCompositeOperation = o.comp || 'multiply';

    for (var y = paso * 0.5; y < o.h; y += paso) {
      for (var x = paso * 0.5; x < o.w; x += paso) {
        var px = x + (r() - 0.5) * paso * 0.95;
        var py = y + (r() - 0.5) * paso * 0.95;
        var d = o.densidad(px / o.w, py / o.h, px, py);
        if (!d) continue;
        var p = (typeof d === 'number') ? d : d.p;
        if (r() > p) continue;
        var col = (typeof d === 'object' && d.c) || o.color || PALETA.tinta;
        var rr = base * (0.45 + r() * 1.05) * (o.escala || 1) * ((d && d.s) || 1);
        ctx.globalAlpha = alfa * (0.45 + r() * 0.55);
        ctx.fillStyle = col;
        ctx.beginPath();
        ctx.arc(px, py, rr, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    ctx.restore();
  }

  function disco(u, v, cx, cy, rx, ry) {
    var dx = (u - cx) / rx, dy = (v - cy) / ry;
    var d = Math.sqrt(dx * dx + dy * dy);
    return Math.max(0, 1 - d);
  }

  function anillo(u, v, cx, cy, r, grosor) {
    var d = Math.hypot(u - cx, v - cy);
    return Math.max(0, 1 - Math.abs(d - r) / grosor);
  }


  /* ---- huella digital ------------------------------------------------- */

  /* Banda de cresta (0..1) para coordenadas locales [-1,1]. */
  function bandaHuella(nx, ny) {
    var r = Math.sqrt(nx * nx + ny * ny);
    if (r > 1) return 0;

    var th = Math.atan2(ny, nx);
    var meneo = 0.075 * Math.sin(3 * th + 1.1) +
                0.04 * Math.sin(7 * th + 2.4) +
                0.028 * Math.sin(2 * th - 0.7);
    var rr = r * (1 + meneo) + 0.015 * Math.sin(r * 9);

    var fase = r < 0.23
      ? (rr * 30 + th * 1.9)                 /* núcleo en espiral */
      : (rr * Math.PI * 2 * 8.4);            /* crestas concéntricas */

    var c = Math.cos(fase);
    var banda = Math.max(0, Math.abs(c) - 0.60) / 0.40;
    return banda;
  }

  function pintarHuella(ctx, o) {
    var w = o.w, h = o.h, r = prng(o.seed);
    var paso = o.paso || 3.1;
    var cx = o.cx, cy = o.cy, rx = o.rx, ry = o.ry;
    var alpha = o.alpha == null ? 0.85 : o.alpha;

    ctx.save();
    ctx.globalCompositeOperation = o.comp || 'multiply';

    for (var y = 0; y < h; y += paso) {
      for (var x = 0; x < w; x += paso) {
        var px = x + (r() - 0.5) * paso * 0.9;
        var py = y + (r() - 0.5) * paso * 0.9;
        var nx = (px - cx) / rx, ny = (py - cy) / ry;

        if (o.hueco) {
          var hx = px - o.hueco.x, hy = py - o.hueco.y;
          if (hx * hx + hy * hy < o.hueco.r * o.hueco.r) continue;
        }

        var b = bandaHuella(nx, ny);
        if (b <= 0.015) continue;
        if (r() > b * 0.94) continue;

        /* cortes de cresta, como una huella de verdad */
        var celda = Math.floor(nx * 9) * 17 + Math.floor(ny * 9) * 5;
        if (celda % 23 === 0 && r() > 0.35) continue;

        ctx.globalAlpha = alpha * (0.5 + r() * 0.5);
        ctx.fillStyle = o.color;
        ctx.beginPath();
        ctx.arc(px, py, 0.55 + r() * 1.45, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    ctx.restore();
  }

  /* Lámina: dos huellas idénticas que se pisan; ORCID en el cruce. */
  function laminasHuella(canvas, seed) {
    var p = preparar(canvas);
    var ctx = p.ctx, w = p.w, h = p.h;
    var s = seed || 11;
    var base = Math.min(w, h);

    papel(ctx, w, h, s, PALETA.papelAlto);

    aguada(ctx, { x: w * 0.34, y: h * 0.52, r: base * 0.46, color: PALETA.coral, alpha: 0.16, seed: s + 1 });
    aguada(ctx, { x: w * 0.66, y: h * 0.47, r: base * 0.44, color: PALETA.indigo, alpha: 0.16, seed: s + 2 });

    /* reserva de papel en el cruce */
    var cx = w * 0.5, cy = h * 0.5, r0 = base * 0.155;
    var claro = ctx.createRadialGradient(cx, cy, r0 * 0.1, cx, cy, r0);
    claro.addColorStop(0, PALETA.papelAlto);
    claro.addColorStop(0.54, PALETA.papelAlto);
    claro.addColorStop(1, 'rgba(252,248,238,0)');
    ctx.save();
    ctx.fillStyle = claro;
    ctx.beginPath();
    ctx.arc(cx, cy, r0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    var rx = base * 0.30, ry = base * 0.405;
    var sello = { x: w * 0.5, y: h * 0.5, r: base * 0.155 };
    pintarHuella(ctx, { w: w, h: h, seed: s + 21, cx: w * 0.355, cy: h * 0.50, rx: rx, ry: ry, color: PALETA.indigo, alpha: 0.82, hueco: sello });
    pintarHuella(ctx, { w: w, h: h, seed: s + 22, cx: w * 0.645, cy: h * 0.50, rx: rx, ry: ry, color: PALETA.rojo, alpha: 0.74, hueco: sello });

    aguada(ctx, { x: cx, y: cy, r: base * 0.115, color: PALETA.orcid, alpha: 0.30, seed: s + 3 });

    /* anillo del identificador, por encima */
    campo(ctx, {
      w: w, h: h, seed: s + 33, paso: 3.6, radio: 1.5, comp: 'source-over', alpha: 0.95,
      densidad: function (u, v) {
        var an = anillo(u, v, 0.5, 0.5, 0.098, 0.009);
        return an > 0.25 ? { p: an, c: PALETA.verde, s: 1.15 } : null;
      }
    });

    ctx.save();
    ctx.globalAlpha = 0.9;
    ctx.fillStyle = PALETA.verde;
    ctx.beginPath();
    ctx.arc(cx, cy, Math.min(w, h) * 0.011, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    /* chispas de tinta */
    var rr2 = prng(s + 40);
    ctx.save();
    for (var i = 0; i < 60; i++) {
      var x = rr2() * w, y = rr2() * h;
      var nx = (x - w * 0.5) / (rx * 1.15), ny = (y - h * 0.5) / (ry * 1.15);
      if (nx * nx + ny * ny < 1) continue;
      ctx.globalAlpha = 0.08 + rr2() * 0.16;
      ctx.fillStyle = rr2() > 0.5 ? PALETA.rojo : PALETA.tinta;
      ctx.beginPath();
      ctx.arc(x, y, 0.5 + rr2() * 1.2, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  /* Huella grande y tenue para el fondo de la portada. */
  function fondoHuella(canvas, seed) {
    var p = preparar(canvas);
    var ctx = p.ctx, w = p.w, h = p.h;
    var base = Math.min(w, h);
    if (!w || !h) return;
    pintarHuella(ctx, {
      w: w, h: h, seed: seed || 5,
      cx: w * 0.5, cy: h * 0.5,
      rx: base * 0.62, ry: base * 0.78,
      color: PALETA.verde, alpha: 0.16, paso: 4.4
    });
  }

  /* ---- láminas ------------------------------------------------------- */

  /* Dos identidades que se solapan y un identificador que las ordena. */
  function laminasClones(canvas, seed) {
    var p = preparar(canvas);
    var ctx = p.ctx, w = p.w, h = p.h;
    var s = seed || 11;
    var base = Math.min(w, h);

    papel(ctx, w, h, s, PALETA.papelAlto);

    aguada(ctx, { x: w * 0.34, y: h * 0.52, r: base * 0.44, color: PALETA.coral, alpha: 0.30, seed: s + 1 });
    aguada(ctx, { x: w * 0.67, y: h * 0.48, r: base * 0.42, color: PALETA.indigo, alpha: 0.28, seed: s + 2 });

    // reserva de papel: el identificador limpia el cruce de las dos identidades
    var cx = w * 0.5, cy = h * 0.5, r0 = base * 0.155;
    var claro = ctx.createRadialGradient(cx, cy, r0 * 0.1, cx, cy, r0);
    claro.addColorStop(0, PALETA.papelAlto);
    claro.addColorStop(0.52, PALETA.papelAlto);
    claro.addColorStop(1, 'rgba(252,248,238,0)');
    ctx.save();
    ctx.fillStyle = claro;
    ctx.beginPath();
    ctx.arc(cx, cy, r0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    aguada(ctx, { x: w * 0.5, y: h * 0.5, r: base * 0.13, color: PALETA.orcid, alpha: 0.34, seed: s + 3 });

    campo(ctx, {
      w: w, h: h, seed: s + 10, paso: 4.2, radio: 1.3,
      densidad: function (u, v) {
        var cA = 0.365, cB = 0.635, rx = 0.235, ry = 0.30;
        var a = disco(u, v, cA, 0.5, rx, ry);
        var b = disco(u, v, cB, 0.5, rx, ry);
        var bordeA = anillo(u, v, cA, 0.5, rx * 0.97, 0.018);
        var bordeB = anillo(u, v, cB, 0.5, rx * 0.97, 0.018);
        var nucleo = anillo(u, v, 0.5, 0.5, 0.105, 0.013);
        var hueco = disco(u, v, 0.5, 0.5, 0.095, 0.095);
        var dentro = Math.max(a, b);
        var solape = Math.min(a, b);
        var color = a > b ? PALETA.rojo : PALETA.indigo;

        if (nucleo > 0.05) return { p: 0.5 + nucleo * 0.5, c: PALETA.verde, s: 1.2 };
        if (hueco > 0.02) return null;

        if (solape > 0.05) {
          return { p: 0.26 + solape * 0.46, c: PALETA.tinta, s: 1.05 };
        }
        if (dentro > 0.02) {
          var lado = a > b ? (u - cA) / rx : (u - cB) / rx;
          var cresciente = Math.max(0, lado);
          var contorno = Math.max(bordeA, bordeB);
          var peso = 0.03 + 0.12 * Math.pow(1 - dentro, 1.4) + contorno * 0.85 + cresciente * cresciente * 0.36;
          return { p: Math.min(0.9, peso), c: color, s: contorno > 0.15 ? 1.3 : 1 };
        }
        var ecoA = anillo(u, v, 0.29, 0.44, 0.315, 0.005);
        var ecoB = anillo(u, v, 0.71, 0.56, 0.315, 0.005);
        if (ecoA > 0.22) return { p: ecoA * 0.6, c: PALETA.tintaSuave };
        if (ecoB > 0.22) return { p: ecoB * 0.6, c: PALETA.tintaSuave };
        if ((u * 9.1 + v * 5.7) % 1 < 0.028) return { p: 0.5, c: PALETA.rojo };
        return null;
      }
    });

    // anillo del identificador, por encima de la tinta
    campo(ctx, {
      w: w, h: h, seed: s + 33, paso: 4.2, radio: 1.5, comp: 'source-over', alpha: 0.95,
      densidad: function (u, v) {
        var an = anillo(u, v, 0.5, 0.5, 0.108, 0.008);
        return an > 0.25 ? { p: an, c: PALETA.verde } : null;
      }
    });

    // sello: punto de tinta verde en el centro del solape
    ctx.save();
    ctx.globalAlpha = 0.9;
    ctx.fillStyle = PALETA.verde;
    ctx.beginPath();
    ctx.arc(w * 0.5, h * 0.5, Math.min(w, h) * 0.011, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // chispas de tinta fuera de las manchas
    var r = prng(s + 40);
    ctx.save();
    for (var i = 0; i < 46; i++) {
      var x = r() * w, y = r() * h;
      var u = x / w, v = y / h;
      if (disco(u, v, 0.365, 0.5, 0.27, 0.33) > 0 || disco(u, v, 0.635, 0.5, 0.27, 0.33) > 0) continue;
      ctx.globalAlpha = 0.10 + r() * 0.22;
      ctx.fillStyle = r() > 0.6 ? PALETA.rojo : PALETA.tinta;
      ctx.beginPath();
      ctx.arc(x, y, 0.5 + r() * 1.2, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  /* Medallón abstracto para la portada: anillo de tinta y constelación. */
  function laminaOrbita(canvas, seed) {
    var p = preparar(canvas);
    var ctx = p.ctx, w = p.w, h = p.h;
    var s = seed || 5;
    papel(ctx, w, h, s);
    aguada(ctx, { x: w * 0.5, y: h * 0.5, r: Math.min(w, h) * 0.5, color: PALETA.orcid, alpha: 0.3, seed: s + 1 });
    aguada(ctx, { x: w * 0.62, y: h * 0.42, r: Math.min(w, h) * 0.3, color: PALETA.verde, alpha: 0.2, seed: s + 2 });

    campo(ctx, {
      w: w, h: h, seed: s + 3, paso: 4.2, radio: 1.1,
      densidad: function (u, v) {
        var an = anillo(u, v, 0.5, 0.5, 0.34, 0.02);
        var an2 = anillo(u, v, 0.5, 0.5, 0.22, 0.012);
        var centro = disco(u, v, 0.5, 0.5, 0.14, 0.14);
        if (an > 0.1) return { p: an * 0.95, c: PALETA.indigo };
        if (an2 > 0.12) return { p: an2 * 0.5, c: PALETA.tintaSuave };
        if (centro > 0.1) return { p: centro * 0.5, c: PALETA.orcid };
        return null;
      }
    });
  }

  global.Arte = {
    PALETA: PALETA,
    prng: prng,
    preparar: preparar,
    papel: papel,
    aguada: aguada,
    campo: campo,
    laminasClones: laminasClones,
    laminaOrbita: laminaOrbita,
    mancha: mancha,
    laminasHuella: laminasHuella,
    fondoHuella: fondoHuella
  };
})(window);
