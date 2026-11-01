"""Genera el mapa ORCID v2 (tres capas + anillo de producción) con datos embebidos."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DATOS = json.loads((ROOT / "data" / "mapa_orcid_dataset_v2.json").read_text(encoding="utf-8"))
GEO = json.loads((ROOT / "data" / "cv_provincias.geojson").read_text(encoding="utf-8"))
SALIDA = ROOT / "data" / "mapa_orcid_v2.html"

datos_js = json.dumps(DATOS, ensure_ascii=False).replace("</", "<\\/")
geo_js = json.dumps(GEO, ensure_ascii=False).replace("</", "<\\/")

HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mapa ORCID · FISABIO · cobertura y producción</title>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<style>
  :root{
    --bg:#070b16; --panel:rgba(15,23,42,.72); --line:rgba(148,163,184,.18);
    --txt:#e2e8f0; --muted:#94a3b8; --cyan:#22d3ee; --violet:#a78bfa; --rose:#fb7185; --amber:#fbbf24;
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;background:var(--bg);color:var(--txt);
    font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif;overflow:hidden}
  #app{display:flex;height:100vh}
  #panel{width:390px;flex:0 0 390px;padding:22px 20px;overflow-y:auto;
    background:linear-gradient(180deg,rgba(15,23,42,.92),rgba(7,11,22,.96));
    border-right:1px solid var(--line);backdrop-filter:blur(14px)}
  #panel::-webkit-scrollbar{width:6px}
  #panel::-webkit-scrollbar-thumb{background:#1e293b;border-radius:3px}
  h1{font-size:1.15rem;font-weight:700;margin:0 0 2px;letter-spacing:-.01em}
  h1 span{color:var(--cyan)}
  .sub{font-size:.72rem;color:var(--muted);margin-bottom:18px;line-height:1.45}
  .block{margin-bottom:18px}
  .block h2{font-size:.62rem;text-transform:uppercase;letter-spacing:.14em;
    color:var(--muted);margin:0 0 9px;font-weight:600}
  .chips{display:flex;flex-wrap:wrap;gap:6px}
  .chip{font-size:.68rem;padding:5px 10px;border-radius:999px;cursor:pointer;
    border:1px solid var(--line);color:var(--muted);background:transparent;
    transition:all .18s ease;user-select:none}
  .chip:hover{border-color:#334155;color:var(--txt)}
  .chip.on{background:linear-gradient(135deg,rgba(34,211,238,.18),rgba(167,139,250,.18));
    border-color:rgba(34,211,238,.5);color:#e0f2fe;box-shadow:0 0 14px rgba(34,211,238,.12)}
  .toggle{display:flex;align-items:center;gap:9px;font-size:.74rem;color:var(--muted);
    padding:5px 0;cursor:pointer}
  .toggle input{accent-color:var(--cyan);width:14px;height:14px}
  .legend-row{display:flex;align-items:center;gap:8px;font-size:.64rem;color:var(--muted);margin-top:6px}
  .bar{height:7px;border-radius:4px;flex:1;background:linear-gradient(90deg,#38bdf8,#818cf8,#c084fc,#fb7185)}
  .dots{display:flex;align-items:flex-end;gap:8px;margin-top:8px;height:44px}
  .dot-wrap{display:flex;flex-direction:column;align-items:center;gap:4px;font-size:.58rem;color:var(--muted)}
  .dot{border-radius:50%;background:rgba(148,163,184,.35);border:1px solid rgba(148,163,184,.5)}
  .note{font-size:.68rem;line-height:1.55;color:#cbd5e1;background:rgba(30,41,59,.45);
    border:1px solid var(--line);border-left:3px solid var(--rose);border-radius:8px;padding:11px 13px}
  .note b{color:#fda4af}
  .note .ex{margin-top:7px;font-family:ui-monospace,monospace;font-size:.61rem;
    color:var(--muted);line-height:1.55}
  .note.amber{border-left-color:var(--amber)}
  .note.amber b{color:#fcd34d}
  .foot{font-size:.58rem;color:#475569;line-height:1.55;margin-top:16px;
    border-top:1px solid var(--line);padding-top:11px}
  #map-container{flex:1;position:relative;background:
    radial-gradient(ellipse at 50% 40%,#0c1526 0%,#070b16 70%)}
  svg{width:100%;height:100%;display:block;cursor:grab}
  svg:active{cursor:grabbing}
  .province{fill:#0e1729;stroke:#1e3355;stroke-width:1.1}
  .bubble{cursor:pointer;transition:filter .2s}
  .bubble:hover{filter:brightness(1.35) drop-shadow(0 0 10px currentColor)}
  .label{font-size:9px;fill:#cbd5e1;pointer-events:none;opacity:0;transition:opacity .2s;
    paint-order:stroke;stroke:#070b16;stroke-width:3px;stroke-linejoin:round}
  .label.always{opacity:.7}
  .bubble-group:hover .label{opacity:1}
  #tooltip{position:absolute;pointer-events:none;opacity:0;transition:opacity .16s;
    background:rgba(10,16,30,.97);border:1px solid rgba(34,211,238,.35);
    border-radius:11px;padding:13px 15px;min-width:260px;max-width:320px;
    box-shadow:0 18px 44px rgba(0,0,0,.6),0 0 0 1px rgba(34,211,238,.08);backdrop-filter:blur(10px);z-index:10}
  #tooltip .t-name{font-size:.8rem;font-weight:700;color:#f1f5f9;line-height:1.3;margin-bottom:2px}
  #tooltip .t-type{font-size:.58rem;text-transform:uppercase;letter-spacing:.1em;color:var(--cyan);margin-bottom:10px}
  #tooltip table{width:100%;border-collapse:collapse;font-size:.66rem}
  #tooltip td{padding:3px 0;color:var(--muted)}
  #tooltip td:last-child{text-align:right;color:#f1f5f9;font-weight:600;font-variant-numeric:tabular-nums}
  #tooltip .sep td{border-top:1px solid rgba(148,163,184,.15);padding-top:7px}
  #tooltip .warn{margin-top:8px;font-size:.61rem;color:#fda4af;line-height:1.4;
    border-top:1px solid rgba(251,113,133,.2);padding-top:7px}
  #tooltip .t-coord{font-size:.55rem;color:#64748b;margin-top:8px;
    border-top:1px solid rgba(148,163,184,.12);padding-top:6px;line-height:1.4}
  #hint{position:absolute;bottom:14px;right:16px;font-size:.6rem;color:#334155;letter-spacing:.03em}
  @media(max-width:860px){
    #app{flex-direction:column}
    #panel{width:100%;flex:0 0 42vh;max-height:42vh;border-right:0;
      border-bottom:1px solid var(--line);padding:14px 16px}
    #map-container{min-height:58vh}
  }
</style>
</head>
<body>
<div id="app">
  <aside id="panel">
    <h1>Mapa <span>ORCID</span> · FISABIO</h1>
    <div class="sub">Cobertura del identificador y producción visible.<br>1.087 personas · 31 centros · dos vías: ORCID y portal (CRIS).</div>

    <div class="block">
      <h2>Relleno = cobertura</h2>
      <div class="chips" id="color-chips">
        <div class="chip on" data-k="cobertura_declarada_pct">ORCID declarada</div>
        <div class="chip" data-k="cobertura_ampliada_pct">ORCID ampliada</div>
        <div class="chip" data-k="cobertura_produccion_pct">Producción</div>
      </div>
      <div class="legend-row"><span id="legend-min">0 %</span><div class="bar" id="legend-bar"></div><span id="legend-max">100 %</span></div>
    </div>

    <div class="block">
      <h2>Tamaño = mediana de obras</h2>
      <div class="chips" id="size-chips">
        <div class="chip" data-k="mediana_orcid">Mediana ORCID</div>
        <div class="chip on" data-k="mediana_union">Mediana unión</div>
      </div>
      <div class="dots" id="size-legend"></div>
    </div>

    <div class="block">
      <h2>Filtros</h2>
      <label class="toggle"><input type="checkbox" id="f-small" checked> Ocultar centros con &lt; 5 personas con producción</label>
      <label class="toggle"><input type="checkbox" id="f-limbo" checked> Mostrar «sin centro»</label>
    </div>

    <div class="block">
      <h2>El anillo</h2>
      <div class="legend-row">
        <span style="width:10px;height:10px;border-radius:50%;border:2px solid var(--cyan);display:inline-block"></span>
        <span>arco cian = cobertura de producción</span>
      </div>
      <div class="legend-row" style="margin-top:4px">
        <span style="width:10px;height:10px;border-radius:50%;border:1px solid #334155;display:inline-block"></span>
        <span>el hueco del anillo = lo que el ORCID no ve</span>
      </div>
    </div>

    <div class="block">
      <h2>Dos medianas, no una</h2>
      <div class="note">
        La mediana ORCID está <b>inflada por selección</b>: solo cuenta a quienes tienen ORCID, que suelen ser los más productivos. En <b>Vinalopó</b> era 53; al incluir las publicaciones del portal, la mediana unión baja a <b>8</b>.
        <div class="ex">Vinalopó · ORCID: 7 personas · mediana 53<br>Vinalopó · unión: 18 personas · mediana 8</div>
      </div>
      <div class="note amber" style="margin-top:9px">
        <b>La brecha es el hallazgo:</b> Elda tiene 24 % de cobertura ORCID pero <b>70 % de producción</b>; Vinalopó, 32 % y 64 %. El CRIS ve investigadores que el ORCID no identifica.
      </div>
    </div>

    <div class="foot">
      Fuente: fichas del portal FISABIO + ORCID declarado y recuperado + publicaciones del portal + OpenAlex.<br>
      __COBERTURA_RECUPERADOS__<br>
      Mediana unión = personas con obras por cualquiera de las dos vías.<br>
      El punto cian marca la coordenada exacta; la burbuja solo se separa cuando dos centros coinciden.
    </div>
  </aside>

  <main id="map-container">
    <svg id="map"></svg>
    <div id="tooltip"></div>
    <div id="hint">rueda = zoom · arrastrar = mover · clic en burbuja = fijar</div>
  </main>
</div>

<script>
const DATA = __DATOS__;
const GEO = __GEO__;
const centers = DATA.centros.map(d => Object.assign({}, d));

// "sin centro" al mar
centers.forEach(d => {
  if (d.tipo === 'sin_centro') { d.lon = d.lon + 0.34; d.lat = d.lat - 0.11; }
});

const mapEl = document.getElementById('map-container');
let W = mapEl.clientWidth || 1;
let H = mapEl.clientHeight || 1;

const svg = d3.select('#map').attr('viewBox', [0, 0, W, H]);
const gRoot = svg.append('g');
const gProv = gRoot.append('g');
const gLead = gRoot.append('g');
const gBub = gRoot.append('g');
const gDots = gRoot.append('g');

const projection = d3.geoMercator().fitExtent([[70, 70], [W - 70, H - 70]], GEO);
const path = d3.geoPath(projection);

gProv.selectAll('path')
  .data(GEO.features).join('path')
  .attr('class', 'province').attr('d', path);

const sinC = centers.find(d => d.tipo === 'sin_centro');

// layout anticolisión radial
centers.forEach((d, i) => { d._i = i; });
let anchors = [], layout = [];

function computeLayout() {
  anchors = centers.map(d => {
    const p = projection([d.lon, d.lat]);
    return { x: p[0], y: p[1] };
  });
  const CLUSTER_PX = 18;
  const usados = new Array(centers.length).fill(false);
  const racimos = [];
  for (let i = 0; i < centers.length; i++) {
    if (usados[i]) continue;
    const grupo = [i]; usados[i] = true;
    for (let j = i + 1; j < centers.length; j++) {
      if (usados[j]) continue;
      if (Math.hypot(anchors[i].x - anchors[j].x, anchors[i].y - anchors[j].y) < CLUSTER_PX) {
        grupo.push(j); usados[j] = true;
      }
    }
    racimos.push(grupo);
  }
  layout = anchors.map(a => ({ x: a.x, y: a.y }));
  racimos.forEach(grupo => {
    if (grupo.length === 1) return;
    const cx = d3.mean(grupo, i => anchors[i].x);
    const cy = d3.mean(grupo, i => anchors[i].y);
    const R = 18 + 11 * grupo.length;
    grupo.forEach((idx, k) => {
      const ang = -Math.PI / 2 + (2 * Math.PI * k) / grupo.length;
      layout[idx] = { x: cx + R * Math.cos(ang), y: cy + R * Math.sin(ang) };
    });
  });
}
function pos(d) { return layout[d._i] || anchors[d._i] || { x: 0, y: 0 }; }

const PALETTE = ['#38bdf8', '#818cf8', '#c084fc', '#fb7185'];
const PALETTE_PROD = ['#2dd4bf', '#fbbf24', '#fb7185', '#ef4444'];
function colorScale() {
  if (colorMetric === 'cobertura_produccion_pct') {
    return d3.scaleLinear().domain([40, 60, 80, 100]).range(PALETTE_PROD).clamp(true);
  }
  return d3.scaleLinear().domain([0, 45, 75, 100]).range(PALETTE).clamp(true);
}

let colorMetric = 'cobertura_declarada_pct';
let sizeMetric = 'mediana_union';
let pinned = null;

const tip = d3.select('#tooltip');
const container = document.getElementById('map-container');

const tipoLabel = {
  hospital: 'hospital', fisabio: 'FISABIO / dirección general',
  primaria: 'atención primaria', otros: 'otro centro',
  sin_centro: 'sin adscripción en el portal'
};

function val(d, k) { const v = d[k]; return v == null ? 0 : v; }
function maxSize() { return d3.max(centers, d => val(d, sizeMetric)) || 1; }
function sizeScale() {
  return d3.scaleSqrt().domain([0, maxSize()]).range([4, 38]);
}
function visible(d) {
  if (d.tipo === 'sin_centro' && !document.getElementById('f-limbo').checked) return false;
  if (document.getElementById('f-small').checked && d.n_efectivo_union < 5) return false;
  return true;
}

function shortName(n) {
  if (n === '(sin centro)') return 'sin centro';
  return n.replace('HOSPITAL GENERAL UNIVERSITARIO DE ', 'H.G.U. ')
          .replace('HOSPITAL UNIVERSITARIO ', 'H.U. ')
          .replace('HOSPITAL ', 'H. ')
          .replace('CENTRO DE ATENCIÓN PRIMARIA ', 'C.A.P. ')
          .replace('FISABIO SALUD PÚBLICA', 'FISABIO SP');
}

// entrada: grupos + anillo + burbuja + etiqueta
const groups = gBub.selectAll('g.bubble-group')
  .data(centers).join('g')
  .attr('class', 'bubble-group')
  .attr('data-centro', d => d.centro)
  .attr('transform', d => {
    const p = pos(d);
    return `translate(${p.x},${p.y})`;
  });

groups.append('circle').attr('class', 'ring-bg')
  .attr('r', 0).attr('fill', 'none')
  .attr('stroke', '#1e293b').attr('stroke-width', 2.4).attr('opacity', .7);

groups.append('circle').attr('class', 'ring-prod')
  .attr('r', 0).attr('fill', 'none')
  .attr('stroke', '#22d3ee').attr('stroke-width', 2.4)
  .attr('opacity', .85)
  .attr('transform', 'rotate(-90)')
  .attr('stroke-linecap', 'round');

groups.append('circle').attr('class', 'bubble')
  .attr('r', 0)
  .attr('fill-opacity', d => d.tipo === 'sin_centro' ? .10 : .55)
  .attr('stroke-width', 1.3)
  .attr('stroke-dasharray', d => d.tipo === 'sin_centro' ? '3,3' : null);

groups.append('text').attr('class', 'label')
  .classed('always', d => d.tipo === 'sin_centro')
  .attr('text-anchor', 'middle').attr('dy', 0)
  .text(d => shortName(d.centro));

function radius(d) {
  if (!visible(d)) return 0;
  if (!d.n_efectivo_union) return 3;
  return sizeScale()(val(d, sizeMetric));
}

function ringDash(r, pct) {
  const circ = 2 * Math.PI * (r + 5);
  return `${circ * Math.max(0, Math.min(100, pct)) / 100} ${circ}`;
}

function updateLegend() {
  const bar = document.getElementById('legend-bar');
  const min = document.getElementById('legend-min');
  const max = document.getElementById('legend-max');
  if (colorMetric === 'cobertura_produccion_pct') {
    bar.style.background = 'linear-gradient(90deg,#2dd4bf,#fbbf24,#fb7185,#ef4444)';
    min.textContent = '40 %'; max.textContent = '100 %';
  } else {
    bar.style.background = 'linear-gradient(90deg,#38bdf8,#818cf8,#c084fc,#fb7185)';
    min.textContent = '0 %'; max.textContent = '100 %';
  }
}

function paint(animate) {
  const r = d => radius(d);
  const dur = animate ? 650 : 0;
  const ease = d3.easeCubicOut;

  groups.select('circle.bubble')
    .transition().duration(dur).ease(ease)
    .attr('r', d => r(d))
    .attr('fill', d => d.tipo === 'sin_centro' ? 'rgba(148,163,184,.10)' : colorScale()(val(d, colorMetric)))
    .attr('stroke', d => d.tipo === 'sin_centro' ? '#94a3b8' : colorScale()(val(d, colorMetric)));

  groups.select('circle.ring-bg')
    .transition().duration(dur).ease(ease)
    .attr('r', d => r(d) + 5);

  groups.select('circle.ring-prod')
    .transition().duration(dur).ease(ease)
    .attr('r', d => r(d) + 5)
    .attr('stroke-dasharray', d => ringDash(r(d), d.cobertura_produccion_pct));

  groups.select('text.label')
    .attr('dy', d => d.tipo === 'sin_centro' ? r(d) + 16 : -r(d) - 9)
    .style('display', d => visible(d) && d.n_efectivo_union > 0 ? null : 'none');

  groups.style('pointer-events', d => visible(d) ? null : 'none')
        .style('opacity', d => visible(d) ? 1 : 0);

  drawSizeLegend(sizeScale());
  drawLeaders();
}

function drawSizeLegend(s) {
  const box = d3.select('#size-legend').html('');
  const max = maxSize();
  [0, Math.round(max * .25), Math.round(max * .5), Math.round(max)].forEach(t => {
    const w = d3.create('div').attr('class', 'dot-wrap');
    const px = Math.max(4, s(t));
    w.append('div').attr('class', 'dot')
      .style('width', px + 'px').style('height', px + 'px');
    w.append('span').text(t);
    box.node().appendChild(w.node());
  });
}

function drawLeaders() {
  gLead.selectAll('*').remove();
  gDots.selectAll('*').remove();
  centers.forEach((d, i) => {
    if (!visible(d)) return;
    const a = anchors[i], p = layout[i];
    if (!a || !p) return;
    if (Math.hypot(p.x - a.x, p.y - a.y) > 3) {
      gLead.append('line')
        .attr('x1', a.x).attr('y1', a.y)
        .attr('x2', p.x).attr('y2', p.y)
        .attr('stroke', '#64748b').attr('stroke-width', .7).attr('opacity', .45);
    }
    if (d.tipo !== 'sin_centro') {
      gDots.append('circle')
        .attr('data-centro', d.centro)
        .attr('cx', a.x).attr('cy', a.y).attr('r', 2.2)
        .attr('fill', '#67e8f9').attr('stroke', '#070b16')
        .attr('stroke-width', .9).attr('opacity', .95);
    }
  });
  if (sinC && visible(sinC)) {
    const val = projection([39.4699, -0.3763]);
    const p = pos(sinC);
    gLead.append('line')
      .attr('x1', val[0]).attr('y1', val[1])
      .attr('x2', p.x).attr('y2', p.y)
      .attr('stroke', '#475569').attr('stroke-width', .8)
      .attr('stroke-dasharray', '2,5').attr('opacity', .3);
  }
}

function showTip(evt, d) {
  const rect = container.getBoundingClientRect();
  const gap = d.brecha_pct >= 0 ? `+${d.brecha_pct}` : `${d.brecha_pct}`;
  tip.style('opacity', 1)
     .style('left', Math.min(evt.clientX - rect.left + 14, rect.width - 330) + 'px')
     .style('top', Math.min(evt.clientY - rect.top + 14, rect.height - 320) + 'px')
     .html(`
       <div class="t-name">${d.centro}</div>
       <div class="t-type">${tipoLabel[d.tipo] || d.tipo}</div>
       <table>
         <tr><td>Cobertura ORCID declarada</td><td>${d.cobertura_declarada_pct}% (${d.orcid_declarado}/${d.total_roster})</td></tr>
         <tr><td>ORCID recuperado</td><td>+${d.orcid_recuperado}</td></tr>
         <tr><td>Cobertura ORCID ampliada</td><td>${d.cobertura_ampliada_pct}%</td></tr>
         <tr><td>Producción (ORCID + portal)</td><td>${d.cobertura_produccion_pct}% (${d.con_produccion}/${d.total_roster})</td></tr>
         <tr class="sep"><td>Brecha de visibilidad</td><td>${gap} puntos</td></tr>
         <tr><td>Mediana ORCID</td><td>${d.mediana_orcid ?? '—'} (n=${d.n_efectivo_orcid})</td></tr>
         <tr><td>Mediana unión</td><td>${d.mediana_union ?? '—'} (n=${d.n_efectivo_union})</td></tr>
         <tr class="sep"><td>Pares persona-obra</td><td>${d.pares_union.toLocaleString('es-ES')}</td></tr>
         <tr><td>Obras únicas</td><td>${d.obras_union.toLocaleString('es-ES')}</td></tr>
         <tr><td>· vía ORCID</td><td>${d.pares_orcid.toLocaleString('es-ES')} pares · ${d.obras_orcid.toLocaleString('es-ES')} obras</td></tr>
         <tr><td>· vía portal</td><td>${d.pares_portal.toLocaleString('es-ES')} pares · ${d.obras_portal.toLocaleString('es-ES')} obras</td></tr>
       </table>
       ${d.n_efectivo_union > 0 && d.n_efectivo_union < 5
         ? `<div class="warn">⚠ n = ${d.n_efectivo_union}: mediana frágil, un solo caso la mueve.</div>` : ''}
       <div class="t-coord">📍 ${Number(d.lat).toFixed(4)}, ${Number(d.lon).toFixed(4)}<br>${d.coord_fuente || ''}</div>
     `);
}
function hideTip() { if (!pinned) tip.style('opacity', 0); }

groups.select('circle.bubble')
  .on('mouseenter', (evt, d) => { if (!pinned) showTip(evt, d); })
  .on('mousemove', (evt, d) => { if (!pinned) showTip(evt, d); })
  .on('mouseleave', hideTip)
  .on('click', function(evt, d) {
    evt.stopPropagation();
    pinned = (pinned === d) ? null : d;
    if (pinned) showTip(evt, d); else hideTip();
  });

svg.on('click', () => { pinned = null; hideTip(); });

const zoom = d3.zoom().scaleExtent([1, 8]).on('zoom', evt => {
  gRoot.attr('transform', evt.transform);
});
svg.call(zoom);

document.querySelectorAll('#color-chips .chip').forEach(ch => {
  ch.addEventListener('click', () => {
    document.querySelectorAll('#color-chips .chip').forEach(x => x.classList.remove('on'));
    ch.classList.add('on');
    colorMetric = ch.dataset.k;
    updateLegend();
    paint(true);
  });
});
document.querySelectorAll('#size-chips .chip').forEach(ch => {
  ch.addEventListener('click', () => {
    document.querySelectorAll('#size-chips .chip').forEach(x => x.classList.remove('on'));
    ch.classList.add('on');
    sizeMetric = ch.dataset.k;
    paint(true);
  });
});
document.getElementById('f-small').addEventListener('change', () => paint(true));
document.getElementById('f-limbo').addEventListener('change', () => paint(true));

computeLayout();
updateLegend();
paint(false);
groups.select('circle.bubble')
  .transition().duration(900).ease(d3.easeCubicOut)
  .attr('r', d => radius(d));
groups.select('circle.ring-bg')
  .transition().duration(900).ease(d3.easeCubicOut)
  .attr('r', d => radius(d) + 5);
groups.select('circle.ring-prod')
  .transition().duration(900).ease(d3.easeCubicOut)
  .attr('r', d => radius(d) + 5)
  .attr('stroke-dasharray', d => ringDash(radius(d), d.cobertura_produccion_pct));
groups.select('text.label').attr('dy', d => d.tipo === 'sin_centro' ? radius(d) + 16 : -radius(d) - 9);

window.addEventListener('resize', () => {
  W = mapEl.clientWidth || 1;
  H = mapEl.clientHeight || 1;
  svg.attr('viewBox', [0, 0, W, H]);
  projection.fitExtent([[70, 70], [W - 70, H - 70]], GEO);
  gProv.selectAll('path').attr('d', path);
  computeLayout();
  groups.attr('transform', d => {
    const p = pos(d);
    return `translate(${p.x},${p.y})`;
  });
  paint(false);
});
</script>
</body>
</html>
"""

if "orcid_recuperados_con_obras_completas" in DATOS:
    incluidos = int(DATOS["orcid_recuperados_con_obras_completas"])
    pendientes = int(DATOS.get("orcid_recuperados_pendientes_de_cosecha", 0))
    nota_recuperados = (
        f"Obras ORCID de perfiles recuperados: cosecha completa para {incluidos}; "
        f"{pendientes} pendientes y excluidos de esa métrica."
    )
else:
    nota_recuperados = "Estado de cosecha ORCID recuperado no disponible; regenere primero el dataset."
HTML = (HTML.replace("__DATOS__", datos_js)
        .replace("__GEO__", geo_js)
        .replace("__COBERTURA_RECUPERADOS__", nota_recuperados))
SALIDA.write_text(HTML, encoding="utf-8")
print(f"HTML escrito: {SALIDA} · {len(HTML):,} chars")
