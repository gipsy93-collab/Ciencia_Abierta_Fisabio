"""Genera una vista navegable de los datasets encontrados (HTML autocontenido)."""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "rip_osiris.sqlite"
SALIDA = ROOT / "data" / "vista_datasets.html"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
filas = [dict(r) for r in con.execute(
    """SELECT d.pid, d.title, d.year, d.type, d.sources, d.n_versiones,
              d.access_rights, d.license, d.health_category_propuesta,
              d.holder, d.url, d.notes, d.work_id
       FROM datasets d ORDER BY d.year DESC, d.title""")]
con.close()

datos = [{
    "pid": f["pid"],
    "title": f["title"],
    "year": f["year"],
    "type": f["type"],
    "sources": (f["sources"] or "").replace("|", ", "),
    "versiones": f["n_versiones"],
    "acceso": f["access_rights"] or "unknown",
    "licencia": f["license"],
    "categoria": f["health_category_propuesta"],
    "tenedor": f["holder"],
    "url": f["url"],
    "work": bool(f["work_id"]),
    "ckan": (f["pid"] or "").startswith("ckan:"),
    "anomalo": bool(f["year"] and f["year"] > 2026),
    "suplemento": (f["title"] or "").lower().startswith("additional file"),
} for f in filas]

kpi = {
    "total": len(datos),
    "datasets": sum(1 for d in datos if d["type"] == "dataset"),
    "software": sum(1 for d in datos if d["type"] == "software"),
    "licencia": sum(1 for d in datos if d["licencia"]),
    "ckan": sum(1 for d in datos if d["ckan"]),
    "con_work": sum(1 for d in datos if d["work"]),
}

payload = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
anio = date.today().isoformat()

HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Datasets de FISABIO · censo 2026</title>
<style>
  :root{
    --bg:#0b1220; --panel:#111a2c; --line:#1e2a44; --ink:#e8eefc; --muted:#8fa3c4;
    --cyan:#22d3ee; --violet:#a78bfa; --green:#34d399; --amber:#fbbf24; --rose:#fb7185;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
       font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
  header{padding:28px 32px 18px;border-bottom:1px solid var(--line)}
  h1{margin:0 0 6px;font-size:1.45rem;letter-spacing:-.01em}
  h1 span{color:var(--cyan)}
  .sub{color:var(--muted);font-size:.85rem;max-width:70ch;line-height:1.5}
  .kpis{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0 0}
  .kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;
       padding:10px 14px;min-width:118px}
  .kpi b{display:block;font-size:1.5rem;line-height:1.1;font-variant-numeric:tabular-nums}
  .kpi small{color:var(--muted);font-size:.68rem;text-transform:uppercase;letter-spacing:.09em}
  .controls{display:flex;gap:10px;flex-wrap:wrap;padding:16px 32px;border-bottom:1px solid var(--line);
            position:sticky;top:0;background:rgba(11,18,32,.94);backdrop-filter:blur(8px);z-index:5}
  input[type=search],select{background:var(--panel);border:1px solid var(--line);color:var(--ink);
       border-radius:9px;padding:8px 11px;font-size:.82rem;outline:none}
  input[type=search]{min-width:280px}
  input:focus,select:focus{border-color:var(--cyan)}
  .chk{display:flex;align-items:center;gap:7px;font-size:.8rem;color:var(--muted)}
  button{background:var(--panel);border:1px solid var(--line);color:var(--ink);border-radius:9px;
         padding:8px 12px;font-size:.8rem;cursor:pointer}
  button:hover{border-color:var(--cyan);color:var(--cyan)}
  .wrap{padding:0 32px 40px}
  table{width:100%;border-collapse:collapse;font-size:.8rem}
  thead th{position:sticky;top:65px;background:var(--bg);text-align:left;color:var(--muted);
           font-size:.66rem;text-transform:uppercase;letter-spacing:.09em;padding:11px 8px;
           border-bottom:1px solid var(--line);cursor:pointer;user-select:none;white-space:nowrap}
  tbody td{padding:9px 8px;border-bottom:1px solid rgba(30,42,68,.55);vertical-align:top}
  tbody tr:hover{background:rgba(34,211,238,.05)}
  .t{font-weight:600;line-height:1.35}
  .t a{color:var(--ink);text-decoration:none}
  .t a:hover{color:var(--cyan);text-decoration:underline}
  .muted{color:var(--muted)}
  .tag{display:inline-block;padding:2px 7px;border-radius:999px;font-size:.62rem;
       text-transform:uppercase;letter-spacing:.06em;white-space:nowrap}
  .ds{background:rgba(34,211,238,.14);color:var(--cyan)}
  .sw{background:rgba(167,139,250,.16);color:var(--violet)}
  .public{background:rgba(52,211,153,.15);color:var(--green)}
  .restricted{background:rgba(251,191,36,.15);color:var(--amber)}
  .non_public{background:rgba(251,113,133,.14);color:var(--rose)}
  .unknown{background:rgba(143,163,196,.13);color:var(--muted)}
  .rev{background:rgba(251,191,36,.15);color:var(--amber);margin-left:6px}
  .cat{font-size:.68rem;color:var(--muted)}
  .num{font-variant-numeric:tabular-nums;color:var(--muted)}
  .empty{padding:40px;text-align:center;color:var(--muted)}
  footer{padding:0 32px 40px;color:var(--muted);font-size:.7rem;line-height:1.6;max-width:110ch}
  @media(max-width:760px){
    header,.controls,.wrap,footer{padding-left:14px;padding-right:14px}
    .hide-sm{display:none}
    thead th{top:105px}
    input[type=search]{min-width:100%}
  }
</style>
</head>
<body>
<header>
  <h1>Datasets de <span>FISABIO</span> · lo que el catálogo no muestra</h1>
  <p class="sub">Censo a __FECHA__ con dos vías independientes: afiliación institucional y los 669 ORCID del
  pipeline, cruzados con DataCite, Zenodo, OpenAlex, el catálogo CKAN y Figshare. Deduplicado por título:
  las versiones de Zenodo con DOI propio cuentan como un solo recurso.</p>
  <div class="kpis">
    <div class="kpi"><b>__TOTAL__</b><small>recursos únicos</small></div>
    <div class="kpi"><b>__DATASETS__</b><small>datasets</small></div>
    <div class="kpi"><b>__SOFTWARE__</b><small>software</small></div>
    <div class="kpi"><b>__LICENCIA__</b><small>con licencia</small></div>
    <div class="kpi"><b>__CKAN__</b><small>en el catálogo</small></div>
  </div>
</header>

<div class="controls">
  <input type="search" id="q" placeholder="Buscar por título, DOI, licencia…">
  <select id="tipo"><option value="">Todos los tipos</option><option value="dataset">Datasets</option><option value="software">Software</option></select>
  <select id="acceso">
    <option value="">Cualquier acceso</option>
    <option value="public">Público</option>
    <option value="restricted">Restringido</option>
    <option value="non_public">No público</option>
    <option value="unknown">Desconocido</option>
  </select>
  <select id="anio"><option value="">Cualquier año</option></select>
  <label class="chk"><input type="checkbox" id="soloCkan"> solo catálogo CKAN</label>
  <button id="csv">Descargar CSV</button>
  <span class="muted" id="cuenta" style="align-self:center;font-size:.75rem"></span>
</div>

<div class="wrap">
  <table>
    <thead><tr>
      <th data-k="year" style="width:58px">Año</th>
      <th data-k="type" style="width:86px">Tipo</th>
      <th data-k="title">Título</th>
      <th data-k="acceso" style="width:104px">Acceso</th>
      <th data-k="licencia" style="width:120px" class="hide-sm">Licencia</th>
      <th data-k="categoria" style="width:170px" class="hide-sm">Categoría (propuesta)</th>
      <th data-k="sources" style="width:170px" class="hide-sm">Fuente</th>
    </tr></thead>
    <tbody id="tb"></tbody>
  </table>
  <div class="empty" id="vacio" hidden>Nada coincide con el filtro.</div>
</div>

<footer>
  <b>Qué es y qué no es.</b> Esto cuenta lo que FISABIO publica con identificador en registros abiertos;
  no cuenta los datos que la institución custodia y que el EHDS obliga a poner a disposición bajo permiso.
  La categoría de salud es una <b>propuesta</b> por palabras clave del título, no una declaración de la institución.
  La afiliación es texto libre: quien no declare FISABIO solo aparece si su ORCID está entre los 669 del pipeline.
  Las versiones de Zenodo se agrupan por título; un mismo recurso puede tener varios DOI.
  Generado el __FECHA__ · RIP-OSIRIS.
</footer>

<script>
const DATOS = __DATOS__;
const tb = document.getElementById('tb');
const q = document.getElementById('q');
const fTipo = document.getElementById('tipo');
const fAcceso = document.getElementById('acceso');
const fAnio = document.getElementById('anio');
const soloCkan = document.getElementById('soloCkan');
const cuenta = document.getElementById('cuenta');
const vacio = document.getElementById('vacio');

const anios = [...new Set(DATOS.map(d => d.year).filter(Boolean))].sort((a,b) => b-a);
for (const a of anios) {
  const o = document.createElement('option'); o.value = a; o.textContent = a; fAnio.appendChild(o);
}

const etiquetaAcceso = { public:'Público', restricted:'Restringido', non_public:'No público', unknown:'Desconocido' };

let orden = { k:'year', asc:false };
let filtrados = [];

function render() {
  const texto = q.value.trim().toLowerCase();
  filtrados = DATOS.filter(d => {
    if (fTipo.value && d.type !== fTipo.value) return false;
    if (fAcceso.value && d.acceso !== fAcceso.value) return false;
    if (fAnio.value && String(d.year) !== fAnio.value) return false;
    if (soloCkan.checked && !d.ckan) return false;
    if (texto) {
      const blob = (d.title + ' ' + d.pid + ' ' + (d.licencia||'') + ' ' + (d.categoria||'') + ' ' + d.sources).toLowerCase();
      if (!blob.includes(texto)) return false;
    }
    return true;
  });
  filtrados.sort((a,b) => {
    const va = a[orden.k], vb = b[orden.k];
    if (va == null) return 1; if (vb == null) return -1;
    const c = (typeof va === 'number') ? va - vb : String(va).localeCompare(String(vb), 'es');
    return orden.asc ? c : -c;
  });

  tb.innerHTML = filtrados.map(d => {
    const href = d.url || (d.pid && d.pid.startsWith('10.') ? 'https://doi.org/' + d.pid : null);
    const titulo = href ? `<a href="${href}" target="_blank" rel="noopener">${esc(d.title)}</a>` : esc(d.title);
    const marca = d.anomalo
      ? '<span class="tag rev" title="Año posterior a 2026 en los metadatos de origen">año anómalo</span>'
      : (d.suplemento ? '<span class="tag rev" title="Fichero adicional (material suplementario), no un conjunto de datos">suplemento</span>' : '');
    return `<tr>
      <td class="num">${d.year || '—'}</td>
      <td><span class="tag ${d.type === 'dataset' ? 'ds' : 'sw'}">${d.type}</span></td>
      <td class="t">${titulo}${marca}<div class="muted" style="font-weight:400;font-size:.68rem">
        ${d.pid.startsWith('ckan:') ? 'catálogo CKAN' : d.pid}${d.work ? ' · enlazado a una obra' : ''}</div></td>
      <td><span class="tag ${d.acceso}">${etiquetaAcceso[d.acceso] || d.acceso}</span></td>
      <td class="muted hide-sm">${d.licencia ? esc(d.licencia) : '—'}</td>
      <td class="cat hide-sm">${d.categoria ? esc(d.categoria) : '—'}</td>
      <td class="muted hide-sm">${esc(d.sources)}</td>
    </tr>`;
  }).join('');

  vacio.hidden = filtrados.length > 0;
  cuenta.textContent = `${filtrados.length} de ${DATOS.length}`;
}

function esc(s) {
  return String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}

document.querySelectorAll('th[data-k]').forEach(th => {
  th.addEventListener('click', () => {
    const k = th.dataset.k;
    orden = { k, asc: (orden.k === k) ? !orden.asc : true };
    render();
  });
});
[q, fTipo, fAcceso, fAnio, soloCkan].forEach(el => el.addEventListener('input', render));

document.getElementById('csv').addEventListener('click', () => {
  const cols = ['year','type','title','pid','acceso','licencia','categoria','sources','url'];
  const head = cols.join(',');
  const lines = filtrados.map(d => cols.map(c => `"${String(d[c] ?? '').replace(/"/g,'""')}"`).join(','));
  const blob = new Blob([head + '\\n' + lines.join('\\n')], { type:'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'datasets-fisabio.csv';
  a.click();
  URL.revokeObjectURL(a.href);
});

render();
</script>
</body>
</html>
"""

html = (HTML.replace("__FECHA__", anio)
            .replace("__TOTAL__", str(kpi["total"]))
            .replace("__DATASETS__", str(kpi["datasets"]))
            .replace("__SOFTWARE__", str(kpi["software"]))
            .replace("__LICENCIA__", str(kpi["licencia"]))
            .replace("__CKAN__", str(kpi["ckan"]))
            .replace("__DATOS__", payload))

SALIDA.write_text(html, encoding="utf-8")
print(f"escrito {SALIDA} · {len(html):,} chars · {len(datos)} recursos")
print("kpi:", kpi)
