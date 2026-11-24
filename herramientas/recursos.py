"""Busca y baja recursos 3D gratuitos (CC0) de las dos bibliotecas que sirven para esto.

Las dos son **CC0**: uso libre, también comercial, sin pagar y sin tener que dar crédito.
  - Poly Haven (polyhaven.com): modelos fotoescaneados, texturas PBR y cielos HDRI.
  - ambientCG (ambientcg.com): la mayor colección de materiales PBR en CC0.

Uso:
  python recursos.py buscar arbol roca arena          # busca en las dos bibliotecas
  python recursos.py bajar ph:island_tree_01          # modelo de Poly Haven (blend + texturas)
  python recursos.py bajar ph:farm_field_puresky      # cielo HDRI
  python recursos.py bajar ph:asphalt_02              # textura de Poly Haven
  python recursos.py bajar acg:Ground037              # material de ambientCG (zip, se descomprime)
  python recursos.py catalogo                         # escribe recursos/CATALOGO.md con lo que hay

Todo cae en  recursos/polyhaven/  y  recursos/ambientcg/  en la raíz del paquete.

Trampas ya resueltas aquí dentro (no volver a pisarlas):
  - las dos APIs responden 403 sin cabecera User-Agent;
  - el .blend de Poly Haven NO trae las texturas: hay que bajar también su lista `include`
    y dejarla en ./textures/ al lado del .blend;
  - ambientCG entrega un zip por resolución, no archivos sueltos.
"""
import io
import json
import os
import sys
import urllib.parse
import urllib.request
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(RAIZ, "recursos")
UA = {"User-Agent": "Mozilla/5.0 (compatible; shorts-animados-3d/1.0)"}
PH = "https://api.polyhaven.com"
ACG = "https://ambientcg.com/api/v2"


def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120)


def _json(url):
    return json.load(_get(url))


def _bajar(url, destino):
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    datos = _get(url).read()
    with open(destino, "wb") as f:
        f.write(datos)
    return len(datos)


# ---------------------------------------------------------------- buscar
def buscar(palabras):
    pal = [p.lower() for p in palabras]
    print("=== Poly Haven ===")
    for tipo, etiqueta in (("models", "modelo"), ("textures", "textura"), ("hdris", "cielo")):
        try:
            d = _json(f"{PH}/assets?t={tipo}")
        except Exception as e:
            print(f"  ({tipo} no se pudo consultar: {e})")
            continue
        for k, v in d.items():
            heno = (k + " " + v.get("name", "") + " " + " ".join(v.get("categories", []) + v.get("tags", []))).lower()
            if any(p in heno for p in pal):
                print(f"  ph:{k:38s} {etiqueta:8s} {v.get('name','')}")
    print("=== ambientCG ===")
    for p in pal:
        try:
            d = _json(f"{ACG}/full_json?type=Material&include=downloadData&limit=12&q={urllib.parse.quote(p)}")
        except Exception as e:
            print(f"  ({p} no se pudo consultar: {e})")
            continue
        for a in d.get("foundAssets", []):
            tam = ""
            for _, items in list(a.get("downloadFolders", {}).items())[:1]:
                for f in items.get("downloadFiletypeCategories", {}).get("zip", {}).get("downloads", []):
                    if f.get("attribute") == "2K-JPG":
                        tam = f"{f.get('size', 0) / 1e6:.0f} MB (2K)"
            print(f"  acg:{a.get('assetId'):37s} material  {tam}")


# ---------------------------------------------------------------- bajar
def bajar_polyhaven(ident, res="2k"):
    info = _json(f"{PH}/info/{ident}")
    tipo = {0: "hdri", 1: "textura", 2: "modelo"}.get(info.get("type"), "?")
    archivos = _json(f"{PH}/files/{ident}")
    base = os.path.join(DEST, "polyhaven")
    total = 0
    if tipo == "modelo":
        entrada = archivos["blend"].get(res) or archivos["blend"]["1k"]
        total += _bajar(entrada["blend"]["url"], os.path.join(base, f"{ident}_{res}.blend"))
        for rel, meta in entrada["blend"].get("include", {}).items():
            total += _bajar(meta["url"], os.path.join(base, rel.replace("/", os.sep)))
    elif tipo == "hdri":
        total += _bajar(archivos["hdri"][res]["hdr"]["url"], os.path.join(base, "hdri", f"{ident}_{res}.hdr"))
    else:
        for mapa in ("Diffuse", "nor_gl", "arm", "Rough", "AO", "Displacement"):
            if mapa not in archivos:
                continue
            try:
                meta = archivos[mapa][res]["jpg"]
            except Exception:
                continue
            total += _bajar(meta["url"], os.path.join(base, "texturas", ident, f"{ident}_{mapa.lower()}.jpg"))
    print(f"  ph:{ident} ({tipo}) -> {total / 1e6:.1f} MB")
    return total


def bajar_ambientcg(ident, res="2K-JPG"):
    # por id exacto (el buscador por texto NO encuentra los identificadores)
    d = _json(f"{ACG}/full_json?id={urllib.parse.quote(ident)}&include=downloadData")
    activos = d.get("foundAssets", [])
    if not activos:
        d = _json(f"{ACG}/full_json?type=Material&include=downloadData&limit=1&q={urllib.parse.quote(ident)}")
        activos = d.get("foundAssets", [])
    if not activos:
        print(f"  acg:{ident} no encontrado")
        return 0
    a = activos[0]
    enlace = None
    for _, items in a.get("downloadFolders", {}).items():
        for f in items.get("downloadFiletypeCategories", {}).get("zip", {}).get("downloads", []):
            if f.get("attribute") == res:
                enlace = f["downloadLink"]
    if not enlace:
        print(f"  acg:{ident} sin {res}")
        return 0
    datos = _get(enlace).read()
    carpeta = os.path.join(DEST, "ambientcg", a["assetId"])
    os.makedirs(carpeta, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        z.extractall(carpeta)
    print(f"  acg:{a['assetId']} -> {len(datos) / 1e6:.1f} MB ({len(z.namelist())} archivos)")
    return len(datos)


def bajar(ids):
    total = 0
    for x in ids:
        fuente, _, ident = x.partition(":")
        if fuente == "ph":
            total += bajar_polyhaven(ident)
        elif fuente == "acg":
            total += bajar_ambientcg(ident)
        else:
            print(f"  fuente desconocida en '{x}' (usa ph: o acg:)")
    print(f"TOTAL {total / 1e6:.1f} MB")


# ---------------------------------------------------------------- catálogo
def catalogo():
    lineas = ["# Recursos descargados (todos CC0: uso libre, también comercial, sin atribución)", ""]
    ph = os.path.join(DEST, "polyhaven")
    if os.path.isdir(ph):
        lineas += ["## Poly Haven", "", "| recurso | qué es | peso |", "|---|---|---|"]
        for n in sorted(os.listdir(ph)):
            ruta = os.path.join(ph, n)
            if os.path.isfile(ruta) and n.endswith(".blend"):
                lineas.append(f"| `{n}` | modelo | {os.path.getsize(ruta) / 1e6:.1f} MB |")
        for sub, que in (("hdri", "cielo HDRI"), ("texturas", "textura PBR")):
            d = os.path.join(ph, sub)
            if os.path.isdir(d):
                for n in sorted(os.listdir(d)):
                    r = os.path.join(d, n)
                    peso = os.path.getsize(r) if os.path.isfile(r) else sum(
                        os.path.getsize(os.path.join(r, f)) for f in os.listdir(r))
                    lineas.append(f"| `{sub}/{n}` | {que} | {peso / 1e6:.1f} MB |")
    acg = os.path.join(DEST, "ambientcg")
    if os.path.isdir(acg):
        lineas += ["", "## ambientCG", "", "| material | archivos | peso |", "|---|---|---|"]
        for n in sorted(os.listdir(acg)):
            r = os.path.join(acg, n)
            fs = os.listdir(r)
            peso = sum(os.path.getsize(os.path.join(r, f)) for f in fs)
            lineas.append(f"| `{n}` | {len(fs)} | {peso / 1e6:.1f} MB |")
    ruta = os.path.join(DEST, "CATALOGO.md")
    os.makedirs(DEST, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")
    print("escrito", ruta)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "buscar"
    args = sys.argv[2:]
    if cmd == "buscar":
        buscar(args or ["tree"])
    elif cmd == "bajar":
        bajar(args)
    elif cmd == "catalogo":
        catalogo()
    else:
        print(__doc__)
