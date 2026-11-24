"""
Mapa de normales para un personaje 2D (PNG con alfa) -> el dibujo reacciona a la luz 3D.

Idea (como en juegos 2D con iluminación dinámica y en Spider-Verse):
la silueta se "infla" como un cojín: el centro sobresale, los bordes se curvan hacia atrás.
Así un foco a la izquierda ilumina el lado izquierdo del muñeco y deja el derecho en sombra,
una luz de contra le dibuja un borde brillante (rim), etc. El dibujo NO lleva la luz pintada.

Uso:  python normales_2d.py entrada.png [salida_normal.png]
"""
import sys
import numpy as np
from PIL import Image, ImageFilter


def altura(alfa, radios=(4, 10, 22, 40)):
    """suma de desenfoques del alfa: centro alto, bordes que bajan suave (cojín)"""
    a = Image.fromarray((alfa * 255).astype(np.uint8))
    h = np.zeros_like(alfa)
    for r in radios:
        h += np.asarray(a.filter(ImageFilter.GaussianBlur(r)), dtype=np.float32) / 255.0
    h /= len(radios)
    return h * alfa


def detalle(rgb, alfa):
    """las líneas de tinta y los pliegues hunden un poco la superficie (relieve fino)"""
    lum = rgb.mean(axis=2) / 255.0
    g = np.asarray(Image.fromarray((lum * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)), dtype=np.float32) / 255.0
    return g * alfa


def recortar(png):
    """quita el margen vacío: la carta mide lo que mide el muñeco y los pies tocan el borde de abajo"""
    im = Image.open(png).convert("RGBA")
    caja = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if caja:
        im = im.crop((max(caja[0] - 6, 0), max(caja[1] - 6, 0), min(caja[2] + 6, im.width), caja[3]))
        im.save(png)
    return png


def normales(png, salida=None, fuerza=6.0, fuerza_detalle=0.6, recorte=True):
    if recorte:
        recortar(png)
    im = Image.open(png).convert("RGBA")
    arr = np.asarray(im, dtype=np.float32)
    alfa = arr[..., 3] / 255.0
    h = altura(alfa) + detalle(arr[..., :3], alfa) * fuerza_detalle * 0.15
    gy, gx = np.gradient(h)
    nx, ny, nz = -gx * fuerza * 10, gy * fuerza * 10, np.ones_like(h)   # convención OpenGL (Y arriba)
    largo = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    n = np.stack([nx / largo, ny / largo, nz / largo], axis=-1)
    rgb = ((n * 0.5 + 0.5) * 255).astype(np.uint8)
    rgb[alfa < 0.02] = (128, 128, 255)
    salida = salida or png.replace(".png", "_n.png")
    Image.fromarray(rgb, "RGB").save(salida)
    return salida


if __name__ == "__main__":
    import os, glob
    if os.path.isdir(sys.argv[1]):       # carpeta de secuencia: no recorta (los pies quedan en la línea del suelo)
        sal = sys.argv[2]; os.makedirs(sal, exist_ok=True)
        for f in sorted(glob.glob(os.path.join(sys.argv[1], "*.png"))):
            normales(f, os.path.join(sal, os.path.basename(f)), recorte=False)
        print("listo", sal)
    else:
        print(normales(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
