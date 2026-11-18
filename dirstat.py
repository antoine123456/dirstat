#!/usr/bin/env python3
"""dirstat.py - carte d'occupation disque façon WinDirStat.

Usage :  python3 dirstat.py DOSSIER [-o carte.html] [--no-open]

Parcourt DOSSIER (lecture seule), puis écrit une page HTML autonome contenant
une carte interactive (treemap) des fichiers, colorés par type.
"""
import argparse
import datetime
import json
import os
import sys
import webbrowser

MAX_LEAVES = 100000  # les fichiers plus petits que total/MAX_LEAVES sont regroupés par dossier


def scan(path, stats):
    """Retourne (enfants, taille) pour un dossier. enfant = [nom, taille] ou [nom, [enfants]]."""
    children, total = [], 0
    try:
        entries = list(os.scandir(path))
    except OSError:
        stats["errors"] += 1
        return children, total
    for e in entries:
        try:
            if e.is_symlink():
                continue
            if e.is_dir(follow_symlinks=False):
                sub, size = scan(e.path, stats)
                if size > 0:
                    children.append([e.name, sub, size])
                    total += size
            elif e.is_file(follow_symlinks=False):
                size = e.stat(follow_symlinks=False).st_size
                stats["files"] += 1
                if stats["files"] % 5000 == 0:
                    print(f"  {stats['files']} fichiers…", file=sys.stderr)
                if size > 0:
                    children.append([e.name, size])
                    total += size
        except OSError:
            stats["errors"] += 1
    return children, total


def prune(children, threshold):
    """Regroupe les petits fichiers d'un dossier et retire la taille mémorisée des dossiers."""
    out, small_n, small_size = [], 0, 0
    for c in children:
        if isinstance(c[1], list):
            out.append([c[0], prune(c[1], threshold)])
        elif c[1] < threshold:
            small_n += 1
            small_size += c[1]
        else:
            out.append(c)
    if small_n == 1:
        only = next(c for c in children if not isinstance(c[1], list) and c[1] < threshold)
        out.append(only)
    elif small_n > 1:
        out.append([f"({small_n} petits fichiers)", small_size, 1])
    return out


def main():
    ap = argparse.ArgumentParser(description="Carte d'occupation disque façon WinDirStat")
    ap.add_argument("folder", help="dossier à analyser")
    ap.add_argument("-o", "--output", help="fichier HTML à écrire (défaut : dirstat-<dossier>.html)")
    ap.add_argument("--no-open", action="store_true", help="ne pas ouvrir le navigateur à la fin")
    args = ap.parse_args()

    root = os.path.abspath(os.path.expanduser(args.folder))
    if not os.path.isdir(root):
        sys.exit(f"Dossier introuvable : {root}")
    name = os.path.basename(root.rstrip(os.sep)) or root
    out = args.output or f"dirstat-{name}.html"

    print(f"Analyse de {root}…", file=sys.stderr)
    stats = {"files": 0, "errors": 0}
    children, total = scan(root, stats)
    tree = [name, prune(children, total / MAX_LEAVES)]
    meta = {
        "name": name,
        "files": stats["files"],
        "errors": stats["errors"],
        "date": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    data = json.dumps(tree, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = (TEMPLATE.replace("__TITLE__", name.replace("<", "&lt;"))
            .replace("__META__", json.dumps(meta, ensure_ascii=False).replace("</", "<\\/"))
            .replace("__DATA__", data))
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{stats['files']} fichiers, {total / 1e9:.2f} Go -> {out}", file=sys.stderr)
    if not args.no_open:
        webbrowser.open("file://" + os.path.abspath(out))


TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DirStat – __TITLE__</title>
<style>
  :root { --bg:#0b0b0c; --panel:#131316; --fg:#e9e9ea; --dim:#8b8b90; --line:#2a2a2e; --acc:#4c9aff; }
  * { box-sizing:border-box; }
  html,body { height:100%; margin:0; background:var(--bg); color:var(--fg);
    font:13px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif; }
  body { display:flex; flex-direction:column; }
  header { flex:none; display:flex; align-items:center; gap:12px; padding:8px 12px;
    border-bottom:1px solid var(--line); min-height:42px; }
  #crumbs { display:flex; flex-wrap:wrap; align-items:center; gap:2px; font-size:14px; min-width:0; }
  #crumbs button { background:none; border:0; color:var(--acc); font:inherit; cursor:pointer;
    padding:2px 5px; border-radius:4px; }
  #crumbs button:hover { background:#1c1c20; }
  #crumbs button:focus-visible, .row:focus-visible, #up:focus-visible { outline:2px solid var(--acc); outline-offset:1px; }
  #crumbs .cur { color:var(--fg); font-weight:600; padding:2px 5px; }
  #crumbs .sep { color:var(--dim); }
  #up { background:#1c1c20; color:var(--fg); border:1px solid var(--line); border-radius:6px;
    padding:4px 10px; font:inherit; cursor:pointer; }
  #up:disabled { opacity:.35; cursor:default; }
  #info { margin-left:auto; color:var(--dim); white-space:nowrap; font-variant-numeric:tabular-nums; }
  main { flex:1; display:flex; min-height:0; }
  #map { flex:1; position:relative; min-width:0; cursor:pointer; touch-action:manipulation;
    -webkit-tap-highlight-color:transparent; }
  #map canvas { position:absolute; inset:0; width:100%; height:100%; display:block; }
  #over { pointer-events:none; }
  aside { flex:none; width:320px; border-left:1px solid var(--line); background:var(--panel);
    display:flex; flex-direction:column; min-height:0; }
  aside section { display:flex; flex-direction:column; min-height:0; flex:1; }
  aside section + section { border-top:1px solid var(--line); }
  aside h2 { flex:none; margin:0; padding:8px 12px 6px; font-size:11px; font-weight:600;
    letter-spacing:.06em; text-transform:uppercase; color:var(--dim); }
  .list { overflow:auto; flex:1; padding-bottom:6px; }
  .row { position:relative; display:flex; align-items:center; gap:8px; width:100%; padding:3px 12px;
    background:none; border:0; color:inherit; font:inherit; text-align:left; cursor:default; }
  button.row { cursor:pointer; }
  .row:hover, .row.on { background:#1f1f24; }
  .row .bar { position:absolute; left:0; top:0; bottom:0; background:rgba(76,154,255,.13); pointer-events:none; }
  .row .sw { flex:none; width:11px; height:11px; border-radius:2px; }
  .row .nm { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; position:relative; }
  .row .sz { flex:none; white-space:nowrap; color:var(--dim); font-variant-numeric:tabular-nums; position:relative; }
  .row .pc { flex:none; width:54px; white-space:nowrap; text-align:right; color:var(--dim); font-variant-numeric:tabular-nums; position:relative; }
  .row.dim { opacity:.4; }
  #tip { position:fixed; z-index:10; display:none; pointer-events:none; max-width:420px;
    background:#26262b; border:1px solid #3a3a40; border-radius:8px; padding:7px 10px;
    box-shadow:0 6px 20px rgba(0,0,0,.5); }
  #tip b { display:block; word-break:break-all; }
  #tip .s { font-variant-numeric:tabular-nums; }
  #tip .p { color:var(--dim); font-size:12px; word-break:break-all; }
  footer { flex:none; padding:5px 12px; border-top:1px solid var(--line); color:var(--dim);
    font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-height:27px; }
  @media (max-width: 720px) {
    header { flex-wrap:wrap; gap:2px 10px; padding:4px 8px; min-height:0; }
    #up { padding:3px 8px; }
    #info { margin-left:0; width:100%; order:3; font-size:12px; white-space:normal; }
    main { flex-direction:column; }
    #map { min-height:0; }
    aside { width:auto; height:30vh; border-left:0; border-top:1px solid var(--line); flex-direction:row; }
    aside section + section { border-top:0; border-left:1px solid var(--line); }
    aside section { min-width:0; }
    .row { padding:5px 8px; gap:6px; }
    .row .pc { display:none; }
    #tip { max-width:calc(100vw - 16px); }
    footer { white-space:normal; }
  }
</style>
</head>
<body>
<header>
  <button id="up" title="Dossier parent (Échap)">↑ Parent</button>
  <nav id="crumbs" aria-label="Chemin"></nav>
  <span id="info"></span>
</header>
<main>
  <div id="map"><canvas id="cv"></canvas><canvas id="over"></canvas></div>
  <aside>
    <section><h2 id="hContent">Contenu</h2><div class="list" id="content"></div></section>
    <section><h2>Types de fichiers</h2><div class="list" id="types"></div></section>
  </aside>
</main>
<footer id="status">Survolez la carte · clic : entrer dans un dossier · Échap : remonter</footer>
<div id="tip"></div>

<script>
const RAW = __DATA__;
const META = __META__;

// ---------- Données ----------
const NOEXT = '(sans extension)', MISC = '(divers)';
function extOf(name) {
  const i = name.lastIndexOf('.');
  if (i <= 0 || name.length - i > 9 || name.length - i < 2) return NOEXT;
  return name.slice(i).toLowerCase();
}
function build(a, parent) {
  const n = { n: a[0], p: parent, g: 0 };
  if (Array.isArray(a[1])) {
    n.c = a[1].map(c => build(c, n));
    n.c.sort((x, y) => y.s - x.s);
    n.s = n.c.reduce((t, c) => t + c.s, 0);
  } else {
    n.s = a[1];
    n.e = a[2] ? MISC : extOf(a[0]);
  }
  return n;
}
const root = build(RAW, null);
let view = root;

const fmtNum = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 });
function fmt(b) {
  const u = ['octets', 'Ko', 'Mo', 'Go', 'To'];
  let i = 0;
  while (b >= 1000 && i < u.length - 1) { b /= 1000; i++; }
  return (i ? fmtNum.format(b >= 100 ? Math.round(b) : b) : b) + ' ' + u[i];
}
const pct = (a, b) => b ? fmtNum.format(100 * a / b) + ' %' : '';
function pathOf(n) { const p = []; for (; n; n = n.p) p.unshift(n.n); return p.join('/'); }

// ---------- Types / couleurs ----------
const PALETTE = ['#4c9aff', '#ff5c5c', '#3ecf8e', '#f5c542', '#b07cff', '#ff8a3d',
                 '#2fd3d3', '#ff6fb5', '#9bd13d', '#8892ff', '#c9a27a'];
const OTHER = '#6b6b73', DIRCOL = '#4a4a52';
const exts = new Map();
(function walk(n) {
  if (n.c) { n.c.forEach(walk); return; }
  const e = exts.get(n.e) || { e: n.e, s: 0, k: 0 };
  e.s += n.s; e.k++; exts.set(n.e, e);
})(root);
const extList = [...exts.values()].sort((a, b) => b.s - a.s);
let ci = 0;
for (const e of extList) e.col = (e.e !== MISC && ci < PALETTE.length) ? PALETTE[ci++] : OTHER;
function mix(hex, t) { // t>0 vers blanc, t<0 vers noir
  const v = parseInt(hex.slice(1), 16), to = t > 0 ? 255 : 0, k = Math.abs(t);
  const f = s => Math.round(((v >> s) & 255) * (1 - k) + to * k);
  return `rgb(${f(16)},${f(8)},${f(0)})`;
}
const shades = new Map();
function shade(col) {
  let s = shades.get(col);
  if (!s) { s = [mix(col, .28), col, mix(col, -.38)]; shades.set(col, s); }
  return s;
}
const colOf = n => n.c ? DIRCOL : exts.get(n.e).col;
let filter = null; // extension mise en évidence

// ---------- Mise en page (treemap « squarified ») ----------
let gen = 0, W = 0, H = 0;
function layout(n, x, y, w, h) {
  n.x = x; n.y = y; n.w = w; n.h = h; n.g = gen; n.r = false;
  if (!n.c || w < 3 || h < 3 || !n.s) return;
  n.r = true;
  const kids = n.c, scale = w * h / n.s;
  let rx = x, ry = y, rw = w, rh = h, i = 0;
  while (i < kids.length && kids[i].s > 0) {
    const short = Math.min(rw, rh), s2 = short * short;
    let sum = 0, best = Infinity, j = i, mx = 0, mn = Infinity;
    while (j < kids.length && kids[j].s > 0) {
      const a = kids[j].s * scale, ns = sum + a;
      const nmx = Math.max(mx, a), nmn = Math.min(mn, a);
      const worst = Math.max(s2 * nmx / (ns * ns), ns * ns / (s2 * nmn));
      if (worst > best) break;
      best = worst; sum = ns; mx = nmx; mn = nmn; j++;
    }
    const thick = sum / short;
    let off = 0;
    for (let k = i; k < j; k++) {
      const len = kids[k].s * scale / thick;
      if (rw >= rh) layout(kids[k], rx, ry + off, thick, len);
      else layout(kids[k], rx + off, ry, len, thick);
      off += len;
    }
    if (rw >= rh) { rx += thick; rw -= thick; } else { ry += thick; rh -= thick; }
    i = j;
  }
}

// ---------- Dessin ----------
const map = document.getElementById('map'), cv = document.getElementById('cv'), over = document.getElementById('over');
const ctx = cv.getContext('2d'), octx = over.getContext('2d');
function paint(n) {
  const { x, y, w, h } = n;
  if (w < .4 || h < .4) return;
  const col = colOf(n), dim = filter && n.e !== filter;
  ctx.globalAlpha = dim ? .13 : 1;
  const gap = (w > 3 && h > 3) ? .6 : 0;
  if (w > 9 && h > 9 && !dim) {
    const s = shade(col), g = ctx.createLinearGradient(x, y, x + w, y + h);
    g.addColorStop(0, s[0]); g.addColorStop(.45, s[1]); g.addColorStop(1, s[2]);
    ctx.fillStyle = g;
  } else ctx.fillStyle = col;
  ctx.fillRect(x, y, w - gap, h - gap);
}
function draw(n, depth) {
  if (n.c && n.r) {
    for (const k of n.c) { if (k.g !== gen) break; draw(k, depth + 1); }
    if (depth === 1 || depth === 2) {
      ctx.globalAlpha = 1;
      ctx.strokeStyle = depth === 1 ? 'rgba(0,0,0,.85)' : 'rgba(0,0,0,.45)';
      ctx.lineWidth = depth === 1 ? 2 : 1;
      ctx.strokeRect(n.x, n.y, n.w, n.h);
    }
  } else paint(n);
}
function render() {
  const r = map.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  W = Math.max(1, r.width); H = Math.max(1, r.height);
  for (const c of [cv, over]) { c.width = Math.round(W * dpr); c.height = Math.round(H * dpr); }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); octx.setTransform(dpr, 0, 0, dpr, 0, 0);
  gen++;
  layout(view, 0, 0, W, H);
  ctx.globalAlpha = 1; ctx.fillStyle = '#0b0b0c'; ctx.fillRect(0, 0, W, H);
  draw(view, 0);
  ctx.globalAlpha = 1;
  drawOver();
}

// ---------- Survol ----------
let hover = null, sideHover = null;
function hit(x, y) {
  let n = view;
  while (n.c && n.r) {
    let f = null;
    for (const k of n.c) {
      if (k.g !== gen) break;
      if (x >= k.x && x < k.x + k.w && y >= k.y && y < k.y + k.h) { f = k; break; }
    }
    if (!f) break;
    n = f;
  }
  return n === view ? null : n;
}
function topOf(n) { while (n && n.p !== view) n = n.p; return n; }
function outline(n, col, lw) {
  if (!n || n.g !== gen) return;
  octx.strokeStyle = col; octx.lineWidth = lw;
  octx.strokeRect(n.x + lw / 2, n.y + lw / 2, Math.max(1, n.w - lw), Math.max(1, n.h - lw));
}
function drawOver() {
  octx.clearRect(0, 0, W, H);
  if (sideHover) { outline(sideHover, '#fff', 2); return; }
  if (!hover) return;
  const t = topOf(hover);
  if (t && t !== hover) outline(t, 'rgba(255,255,255,.55)', 1.5);
  outline(hover, '#fff', 2);
}
const tip = document.getElementById('tip'), status = document.getElementById('status');
function showTip(n, ev) {
  tip.textContent = '';
  const b = document.createElement('b'); b.textContent = n.n + (n.c ? '/' : '');
  const s = document.createElement('div'); s.className = 's';
  s.textContent = fmt(n.s) + ' · ' + pct(n.s, view.s) + ' de « ' + view.n + ' »';
  const p = document.createElement('div'); p.className = 'p'; p.textContent = pathOf(n.p);
  tip.append(b, s, p);
  tip.style.display = 'block';
  const tw = tip.offsetWidth, th = tip.offsetHeight;
  let x = ev.clientX + 14, y = ev.clientY + 16;
  if (x + tw > innerWidth - 6) x = ev.clientX - tw - 10;
  if (y + th > innerHeight - 6) y = ev.clientY - th - 10;
  tip.style.left = Math.max(4, x) + 'px'; tip.style.top = Math.max(4, y) + 'px';
}
const TOUCH_STATUS = 'Touchez la carte pour identifier · touchez à nouveau pour entrer · ↑ Parent pour remonter';
const DEFAULT_STATUS = matchMedia('(hover: none)').matches ? TOUCH_STATUS : status.textContent;
status.textContent = DEFAULT_STATUS;
function nodeAt(ev) {
  const r = map.getBoundingClientRect();
  return hit(ev.clientX - r.left, ev.clientY - r.top);
}
function point(n, ev) { // met en évidence n (survol à la souris, premier toucher au doigt)
  if (n !== hover) { hover = n; drawOver(); markRow(); }
  if (n) { showTip(n, ev); status.textContent = pathOf(n) + '  —  ' + fmt(n.s); }
  else { tip.style.display = 'none'; status.textContent = DEFAULT_STATUS; }
}
function unpoint() {
  hover = null; tip.style.display = 'none'; status.textContent = DEFAULT_STATUS; drawOver(); markRow();
}
// Souris : le survol suit le pointeur. Toucher : le premier toucher montre l'élément,
// un second toucher dans le même dossier y entre.
let lastPointer = 'mouse';
map.addEventListener('pointermove', ev => { if (ev.pointerType === 'mouse') point(nodeAt(ev), ev); });
map.addEventListener('pointerleave', ev => { if (ev.pointerType === 'mouse') unpoint(); });
map.addEventListener('pointerdown', ev => { lastPointer = ev.pointerType; });
map.addEventListener('click', ev => {
  const n = nodeAt(ev), t = n && topOf(n);
  if (lastPointer !== 'mouse') {
    const prev = hover && topOf(hover);
    if (t && t.c && t === prev) go(t);
    else point(n, ev);
    return;
  }
  if (t && t.c) go(t);
});
document.addEventListener('pointerdown', ev => {
  if (ev.pointerType !== 'mouse' && hover && !map.contains(ev.target)) unpoint();
});

// ---------- Navigation ----------
function go(n) {
  view = n; hover = null; sideHover = null; tip.style.display = 'none'; status.textContent = DEFAULT_STATUS;
  render(); renderCrumbs(); renderContent();
}
document.getElementById('up').onclick = () => { if (view.p) go(view.p); };
addEventListener('keydown', ev => {
  if ((ev.key === 'Escape' || ev.key === 'Backspace') && view.p) { ev.preventDefault(); go(view.p); }
});
function renderCrumbs() {
  const el = document.getElementById('crumbs'); el.textContent = '';
  const chain = []; for (let n = view; n; n = n.p) chain.unshift(n);
  chain.forEach((n, i) => {
    if (i) { const s = document.createElement('span'); s.className = 'sep'; s.textContent = '/'; el.append(s); }
    if (n === view) { const c = document.createElement('span'); c.className = 'cur'; c.textContent = n.n; el.append(c); }
    else { const b = document.createElement('button'); b.textContent = n.n; b.onclick = () => go(n); el.append(b); }
  });
  document.getElementById('up').disabled = !view.p;
  document.getElementById('info').textContent = fmt(view.s) +
    (view === root ? ' · ' + META.files.toLocaleString('fr-FR') + ' fichiers · ' + META.date : ' · ' + pct(view.s, root.s) + ' du total');
}

// ---------- Panneau latéral ----------
const MAXROWS = 300;
let rowOf = new Map();
function row(tag, col, name, size, part, total) {
  const r = document.createElement(tag); r.className = 'row';
  const bar = document.createElement('span'); bar.className = 'bar'; bar.style.width = (100 * part / (total || 1)) + '%';
  const sw = document.createElement('span'); sw.className = 'sw'; sw.style.background = col;
  const nm = document.createElement('span'); nm.className = 'nm'; nm.textContent = name; nm.title = name;
  const sz = document.createElement('span'); sz.className = 'sz'; sz.textContent = size;
  const pc = document.createElement('span'); pc.className = 'pc'; pc.textContent = pct(part, total);
  r.append(bar, sw, nm, sz, pc);
  return r;
}
function renderContent() {
  const el = document.getElementById('content'); el.textContent = ''; rowOf = new Map();
  document.getElementById('hContent').textContent = 'Contenu de « ' + view.n + ' »';
  const max = view.c.length ? view.c[0].s : 1;
  view.c.slice(0, MAXROWS).forEach(n => {
    const r = row(n.c ? 'button' : 'div', colOf(n), (n.c ? '▸ ' : '') + n.n, fmt(n.s), n.s, view.s);
    r.querySelector('.bar').style.width = (100 * n.s / max) + '%';
    if (n.c) r.onclick = () => go(n);
    r.onmouseenter = () => { sideHover = n; drawOver(); };
    r.onmouseleave = () => { sideHover = null; drawOver(); };
    rowOf.set(n, r); el.append(r);
  });
  if (view.c.length > MAXROWS) {
    const more = document.createElement('div'); more.className = 'row'; more.style.color = 'var(--dim)';
    more.textContent = '… et ' + (view.c.length - MAXROWS) + ' autres éléments';
    el.append(more);
  }
}
let marked = null;
function markRow() {
  const r = hover ? rowOf.get(topOf(hover)) : null;
  if (r === marked) return;
  if (marked) marked.classList.remove('on');
  marked = r || null;
  if (marked) { marked.classList.add('on'); marked.scrollIntoView({ block: 'nearest' }); }
}
function renderTypes() {
  const el = document.getElementById('types'); el.textContent = '';
  for (const e of extList) {
    const r = row('button', e.col, e.e, fmt(e.s), e.s, root.s);
    r.querySelector('.bar').style.width = (100 * e.s / extList[0].s) + '%';
    r.title = e.k.toLocaleString('fr-FR') + ' fichier(s) – cliquer pour mettre en évidence';
    r.setAttribute('aria-pressed', filter === e.e);
    if (filter === e.e) r.classList.add('on'); else if (filter) r.classList.add('dim');
    r.onclick = () => { filter = filter === e.e ? null : e.e; renderTypes(); render(); };
    el.append(r);
  }
}

new ResizeObserver(() => render()).observe(map);
renderCrumbs(); renderContent(); renderTypes(); render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
