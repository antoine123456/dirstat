#!/usr/bin/env bash
# Regénère la démo en ligne (docs/index.html, servie par GitHub Pages).
#
# 1. Crée dans un dossier temporaire un faux dossier « Projets » : des fichiers
#    creux (sparse) de tailles variées, sur plusieurs niveaux, de types variés.
#    Ils n'occupent presque rien sur le disque mais ont leur taille apparente.
# 2. Le scanne avec dirstat.py.
# 3. Ajoute le bandeau « Démo de dirstat » en haut de la page.
#
# Usage : docs/make_demo.sh        (depuis n'importe où)
set -euo pipefail

cd "$(dirname "$0")/.."
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

python3 - "$TMP/Projets" <<'PY'
import os, random, sys

root = sys.argv[1]
rnd = random.Random(2026)          # graine fixe : la démo est la même à chaque fois
KB, MB, GB = 1000, 1000**2, 1000**3

def f(path, size):
    p = os.path.join(root, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as fh:
        fh.truncate(int(size))

def many(folder, pattern, n, lo, hi, start=1):
    for i in range(start, start + n):
        f(os.path.join(folder, pattern.format(i)), rnd.uniform(lo, hi))

# Photos
many("Photos/2025-ete-Bretagne", "IMG_{:04d}.HEIC", 140, 1.8*MB, 4.5*MB, 2101)
many("Photos/2025-ete-Bretagne", "IMG_{:04d}.MOV", 9, 60*MB, 450*MB, 2301)
many("Photos/2026-ski-Alpes", "DSC{:05d}.JPG", 90, 4*MB, 9*MB, 10421)
many("Photos/2026-ski-Alpes", "DJI_{:04d}.MP4", 6, 300*MB, 1.4*GB, 1)
many("Photos/Fete-de-famille/RAW", "DSC{:05d}.ARW", 60, 22*MB, 28*MB, 2001)
many("Photos/Fete-de-famille/Selection", "DSC{:05d}.jpg", 45, 5*MB, 11*MB, 2001)
many("Photos/Captures", "Capture {:03d}.png", 70, 150*KB, 2.5*MB)

# Vidéos
many("Videos/Montage-voyage/Rushes", "C{:04d}.MP4", 14, 250*MB, 1.6*GB, 1)
f("Videos/Montage-voyage/Export/voyage-final-4K.mov", 3.8*GB)
f("Videos/Montage-voyage/Export/voyage-final-1080p.mp4", 690*MB)
f("Videos/Montage-voyage/voyage.prproj", 46*MB)
many("Videos/Montage-voyage/Musique", "piste-{:02d}.wav", 6, 35*MB, 70*MB)
many("Videos/Tutoriels", "cours-{:02d}.mkv", 8, 180*MB, 900*MB)

# Musique
for a in range(1, 7):
    many(f"Musique/Album {a:02d}", "{:02d} - Titre.mp3", rnd.randint(9, 14), 4*MB, 11*MB)
many("Musique/Lossless", "{:02d} - Titre.flac", 24, 25*MB, 55*MB)

# Code
many("Code/site-perso/src", "page-{:02d}.ts", 30, 2*KB, 40*KB)
many("Code/site-perso/src/styles", "theme-{:02d}.css", 12, 1*KB, 25*KB)
many("Code/site-perso/public/img", "illustration-{:02d}.webp", 25, 80*KB, 900*KB)
for pkg in ["react", "lodash", "typescript", "esbuild", "vite", "eslint", "date-fns", "zod",
            "postcss", "tailwindcss", "rollup", "prettier"]:
    many(f"Code/site-perso/node_modules/{pkg}/dist", "module-{:03d}.js", rnd.randint(15, 60), 1*KB, 400*KB)
f("Code/site-perso/node_modules/esbuild/bin/esbuild", 9.6*MB)
f("Code/site-perso/node_modules/typescript/lib/typescript.js", 8.9*MB)
many("Code/site-perso/.git/objects/pack", "pack-{:02d}.pack", 3, 8*MB, 35*MB)
many("Code/analyse-donnees/data", "mesures-{:02d}.csv", 9, 40*MB, 520*MB)
many("Code/analyse-donnees/data", "resultats-{:02d}.parquet", 5, 30*MB, 180*MB)
many("Code/analyse-donnees/notebooks", "etude-{:02d}.ipynb", 7, 300*KB, 6*MB)
many("Code/analyse-donnees", "script-{:02d}.py", 10, 2*KB, 30*KB)
many("Code/appli-mobile/app/src", "Ecran{:02d}.kt", 25, 3*KB, 35*KB)
many("Code/appli-mobile/app/res", "icone-{:02d}.png", 40, 4*KB, 120*KB)
many("Code/appli-mobile/build/outputs", "app-release-{}.apk", 3, 45*MB, 70*MB)
f("Code/appli-mobile/build/intermediates/classes.jar", 210*MB)

# Documents
many("Documents/Factures", "facture-2026-{:03d}.pdf", 36, 60*KB, 400*KB)
many("Documents/Cours", "chapitre-{:02d}.pdf", 18, 2*MB, 35*MB)
many("Documents/Rapports", "rapport-{:02d}.docx", 12, 200*KB, 8*MB)
many("Documents/Rapports", "presentation-{:02d}.pptx", 6, 5*MB, 60*MB)
many("Documents/Rapports", "budget-{:02d}.xlsx", 8, 50*KB, 3*MB)
many("Documents/Livres", "livre-{:02d}.epub", 20, 500*KB, 6*MB)

# Design
many("Design/Affiches", "affiche-{:02d}.psd", 7, 90*MB, 420*MB)
many("Design/Affiches/Exports", "affiche-{:02d}.png", 7, 3*MB, 14*MB)
many("Design/Logos", "logo-{:02d}.ai", 9, 4*MB, 30*MB)
many("Design/Logos", "logo-{:02d}.svg", 9, 8*KB, 200*KB)
many("Design/Polices", "Police-{:02d}.otf", 14, 60*KB, 900*KB)

# Archives
f("Archives/sauvegarde-2024.zip", 6.2*GB)
f("Archives/photos-2019.tar.gz", 2.9*GB)
f("Archives/ancien-portable.dmg", 4.4*GB)
many("Archives/Installateurs", "installateur-{:02d}.pkg", 5, 120*MB, 900*MB)
PY

python3 dirstat.py "$TMP/Projets" -o docs/index.html --no-open

python3 - docs/index.html <<'PY'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
css = """  #demo { flex:none; display:flex; align-items:center; gap:14px; padding:6px 12px;
    background:#16243a; border-bottom:1px solid #24395a; color:#b9c7dc; font-size:12.5px; }
  #demo a { color:#8fbfff; text-decoration:none; white-space:nowrap; }
  #demo a:hover { text-decoration:underline; }
  #demo code { background:rgba(255,255,255,.08); border-radius:4px; padding:1px 5px;
    font:12px ui-monospace,SFMono-Regular,Menlo,monospace; color:#e9e9ea; white-space:nowrap; }
  #demo .msg { flex:1; min-width:0; }
  @media (max-width: 720px) { #demo { flex-wrap:wrap; gap:4px 12px; padding:6px 8px; font-size:12px; }
    #demo .msg { order:3; flex-basis:100%; } }
</style>"""
banner = """<body>
<div id="demo">
  <a href="https://antoine123456.github.io/">← antoine123456</a>
  <span class="msg">Démo de dirstat, scan d'un dossier d'exemple. Lance <code>python3 dirstat.py ~/Documents</code> pour le tien.</span>
  <a href="https://github.com/antoine123456/dirstat">Code sur GitHub</a>
</div>"""
assert s.count("</style>") == 1 and s.count("<body>") == 1
s = s.replace("</style>", css, 1).replace("<body>", banner, 1)
s = s.replace("<title>DirStat – Projets</title>", "<title>dirstat – démo en ligne</title>")
open(p, "w", encoding="utf-8").write(s)
PY

echo "docs/index.html regénéré."
