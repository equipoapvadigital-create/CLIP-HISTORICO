"""
Caja del dibujo (lo que NO es transparente) en cada cuadro de un clip 2D, para saber dónde está el personaje
en pantalla y que los subtítulos nunca lo tapen.
Uso: python cajas_alfa.py <carpeta_clip>   (lee <clip>/seq/*.png, escribe <clip>/cajas.json)
Cada entrada: [x0, y0, x1, y1] en píxeles del lienzo (800x1200) o null si el cuadro está vacío.
"""
import json, os, sys
import numpy as np
from PIL import Image

base = sys.argv[1]
seq = os.path.join(base, "seq")
cajas = []
for n in sorted(os.listdir(seq)):
    a = np.asarray(Image.open(os.path.join(seq, n)).getchannel("A"))
    ys, xs = np.nonzero(a > 24)
    cajas.append(None if len(xs) == 0 else [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())])
json.dump(cajas, open(os.path.join(base, "cajas.json"), "w"))
print(base, len(cajas), "cuadros")
