"""
TRANSICIONES ÉPICAS para el montaje (numpy + OpenCV). Cada una recibe el cuadro que sale (A), el que entra (B)
y t en [0, 1] dentro de la unión, y devuelve el cuadro mezclado. Todas esconden el corte con MOVIMIENTO
(desenfoque de velocidad, zoom, giro) o con un golpe de luz, nunca con un fundido plano.

Cada transición puede llevar un efecto de sonido alineado con el centro de la unión.

  latigazo   paneo rapidísimo con desenfoque de movimiento (dir: izq, der, arriba, abajo)
  zoom       la cámara se mete de golpe en A (desenfoque radial) y sale de B   · cambio de escena con fuerza
  flash      golpe de luz blanca + sacudida de B                                · impacto, cifra, revelación
  giro       A gira y se desenfoca, B entra girando al revés                    · confusión, viaje, vértigo
  tinta      una mancha de tinta crece y destapa B (borde oscuro, orgánico)     · cambio de época, recuerdo
  iris       círculo de caricatura que se cierra en un punto y se abre en B     · remate, chiste, final
  glitch     separación RGB + franjas corridas + parpadeo                       · golpe emocional, «nadie lo escuchó»
  destello   barrido de luz cálida (fuga de luz) que lava A y revela B          · recuerdo, sueño, esperanza
  caida      latigazo hacia abajo con golpe grave al aterrizar                  · bajar al pozo, a la cárcel
  subida     latigazo hacia arriba                                              · salir, ascender, el trono
  negro      a negro y de negro, lento                                          · antes de la reflexión
  fundido    fundido cruzado suave (solo si de verdad hace falta calma)

Uso:  from transiciones import aplicar, SONIDO
      x = aplicar("latigazo", A, B, t, dir="izq")      (A y B: float32 HxWx3 en 0..255)
"""
import math
import numpy as np
import cv2

def _ss(t):
    t = min(1.0, max(0.0, t)); return t * t * t * (t * (6 * t - 15) + 10)

def _desplaza(img, dx, dy):
    h, w = img.shape[:2]
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

def _blur_dir(img, k, vertical=False):
    k = int(k)
    if k < 2: return img
    return cv2.blur(img, (1, k) if vertical else (k, 1))

def _escala_rot(img, s, ang=0.0, cx=None, cy=None):
    h, w = img.shape[:2]
    cx = w / 2 if cx is None else cx; cy = h / 2 if cy is None else cy
    M = cv2.getRotationMatrix2D((cx, cy), ang, s)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

def _zoom_blur(img, s, fuerza, n=7, cx=None, cy=None):
    """desenfoque radial: promedio de copias escaladas entre s y s*(1+fuerza)"""
    if fuerza < 0.005: return _escala_rot(img, s, 0, cx, cy)
    acc = np.zeros_like(img)
    for i in range(n):
        acc += _escala_rot(img, s * (1 + fuerza * i / (n - 1)), 0, cx, cy)
    return acc / n

def _sacudir(img, amp, f):
    if amp < 0.5: return img
    return _desplaza(img, amp * math.sin(f * 2.9), amp * 0.7 * math.cos(f * 3.7 + 1))

# ------------------------------------------------------------------------------------------- tipos
def latigazo(A, B, t, dir="izq"):
    h, w = A.shape[:2]
    vert = dir in ("arriba", "abajo")
    L = h if vert else w
    sgn = -1 if dir in ("izq", "arriba") else 1          # hacia dónde se va A
    if t < 0.5:
        u = (t / 0.5) ** 2.2                              # A acelera
        d = sgn * L * 0.55 * u; vel = L * 0.55 * 2.2 * (t / 0.5) ** 1.2 / 6
        img = _desplaza(A, 0 if vert else d, d if vert else 0)
    else:
        u = 1 - ((1 - t) / 0.5) ** 2.2                    # B frena
        d = -sgn * L * 0.55 * (1 - u); vel = L * 0.55 * 2.2 * ((1 - t) / 0.5) ** 1.2 / 6
        img = _desplaza(B, 0 if vert else d, d if vert else 0)
    img = _blur_dir(img, min(vel, L * 0.25), vert)
    # en el centro, una pizca de mezcla para que no se vea el salto
    m = max(0.0, 1 - abs(t - 0.5) / 0.08)
    if m > 0:
        otro = _blur_dir(B if t < 0.5 else A, L * 0.2, vert)
        img = img * (1 - 0.5 * m) + otro * 0.5 * m
    return img

def caida(A, B, t, **k): return latigazo(A, B, t, dir="abajo")
def subida(A, B, t, **k): return latigazo(A, B, t, dir="arriba")

def zoom(A, B, t, cx=None, cy=None):
    if t < 0.5:
        u = (t / 0.5) ** 2.4
        img = _zoom_blur(A, 1 + 1.8 * u, 0.35 * u, cx=cx, cy=cy)
    else:
        u = ((1 - t) / 0.5) ** 2.4
        img = _zoom_blur(B, 1 + 0.9 * u, 0.3 * u, cx=cx, cy=cy)
    luz = max(0.0, 1 - abs(t - 0.5) / 0.12) * 0.5
    return img * (1 - luz) + 255 * luz

def flash(A, B, t, color=(255, 255, 255), f=0):
    blanco = np.array(color, np.float32)
    if t < 0.4:
        u = (t / 0.4) ** 2
        img = A * (1 - u) + blanco * u
    else:
        u = (t - 0.4) / 0.6
        img = blanco * (1 - _ss(u)) ** 1.5 + B * (1 - (1 - _ss(u)) ** 1.5)
        img = _sacudir(img, 26 * (1 - u) ** 2, f)      # el golpe sacude el cuadro que entra
    return img

def giro(A, B, t):
    if t < 0.5:
        u = (t / 0.5) ** 2.2
        base = _escala_rot(A, 1 + 0.6 * u, -120 * u)
        acc = sum(_escala_rot(A, 1 + 0.6 * u, -120 * u + 12 * u * i) for i in range(5)) / 5
    else:
        u = ((1 - t) / 0.5) ** 2.2
        base = _escala_rot(B, 1 + 0.6 * u, 120 * u)
        acc = sum(_escala_rot(B, 1 + 0.6 * u, 120 * u - 12 * u * i) for i in range(5)) / 5
    return base * 0.3 + acc * 0.7

_ruido_cache = {}
def _ruido(h, w, semilla=3):
    key = (h, w, semilla)
    if key not in _ruido_cache:
        r = np.random.default_rng(semilla)
        n = np.zeros((h, w), np.float32)
        for esc, peso in ((8, 1.0), (24, 0.5), (64, 0.25)):
            m = r.random((max(2, h // esc), max(2, w // esc))).astype(np.float32)
            n += cv2.resize(m, (w, h), interpolation=cv2.INTER_CUBIC) * peso
        n = (n - n.min()) / (n.max() - n.min())
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        rad = np.hypot((xx - w * 0.5) / w, (yy - h * 0.55) / h)
        _ruido_cache[key] = 0.55 * n + 0.45 * (1 - rad / rad.max())
    return _ruido_cache[key]

def tinta(A, B, t, semilla=3):
    h, w = A.shape[:2]
    n = _ruido(h, w, semilla)
    umbral = 1 - _ss(t) * 1.08
    mask = (n > umbral).astype(np.float32)
    mask = cv2.GaussianBlur(mask, (0, 0), 1.2)
    borde = np.clip(1 - np.abs(n - umbral) / 0.018, 0, 1)[..., None]   # el filo de la mancha, en tinta oscura
    img = A * (1 - mask[..., None]) + B * mask[..., None]
    tin = np.array([22, 16, 20], np.float32)
    k = borde * (0.95 if 0.02 < t < 0.98 else 0)
    return img * (1 - k) + tin * k

def iris(A, B, t, cx=None, cy=None):
    h, w = A.shape[:2]
    cx = w / 2 if cx is None else cx; cy = h * 0.42 if cy is None else cy
    R = math.hypot(max(cx, w - cx), max(cy, h - cy))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.hypot(xx - cx, yy - cy)
    if t < 0.5:
        r = R * (1 - _ss(t / 0.5)); src = A
    else:
        r = R * _ss((t - 0.5) / 0.5); src = B
    dentro = np.clip((r - d) / 2.0 + 0.5, 0, 1)[..., None]
    aro = np.clip(1 - np.abs(d - r) / 9, 0, 1)[..., None]
    img = src * dentro                              # afuera: negro de caricatura
    return img * (1 - aro) + np.array([10, 8, 10], np.float32) * aro

def glitch(A, B, t, f=0):
    src = A if t < 0.5 else B
    h, w = src.shape[:2]
    fuerza = max(0.0, 1 - abs(t - 0.5) / 0.5) ** 0.7
    r = np.random.default_rng(int(f * 7919 + 13))
    img = src.copy()
    off = int(28 * fuerza)
    if off:
        img[..., 0] = np.roll(src[..., 0], off, axis=1)
        img[..., 2] = np.roll(src[..., 2], -off, axis=1)
    for _ in range(int(10 * fuerza)):
        y0 = r.integers(0, h - 20); alto = r.integers(8, 90)
        img[y0:y0 + alto] = np.roll(img[y0:y0 + alto], int(r.integers(-120, 120) * fuerza), axis=1)
    if 0.4 < t < 0.6 and r.random() < 0.5: img = img * 0.55 + (B if t < 0.5 else A) * 0.45
    return img

def destello(A, B, t, color=(255, 214, 160)):
    h, w = A.shape[:2]
    base = A * (1 - _ss(t)) + B * _ss(t)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # una banda de luz diagonal que barre el cuadro y florece en el centro
    pos = -0.4 + 1.8 * t
    banda = np.exp(-((xx / w * 0.7 + yy / h * 0.6 - pos) ** 2) / 0.02)
    flor = math.sin(math.pi * t) ** 2
    luz = np.clip(banda * 0.85 + flor * 0.55, 0, 1)[..., None]
    c = np.array(color, np.float32)
    return base * (1 - luz) + (base * 0.3 + c * 0.9).clip(0, 255) * luz

def negro(A, B, t):
    if t < 0.5: return A * (1 - _ss(t / 0.5))
    return B * _ss((t - 0.5) / 0.5)

def fundido(A, B, t): return A * (1 - _ss(t)) + B * _ss(t)

TIPOS = {"latigazo": latigazo, "caida": caida, "subida": subida, "zoom": zoom, "flash": flash, "giro": giro,
         "tinta": tinta, "iris": iris, "glitch": glitch, "destello": destello, "negro": negro, "fundido": fundido}
# cuántos cuadros dura cada una (a 30 fps). La toma debe traer al menos la mitad de cola de cada lado.
DURACION = {"latigazo": 10, "caida": 12, "subida": 12, "zoom": 10, "flash": 8, "giro": 12, "tinta": 14, "iris": 16,
            "glitch": 8, "destello": 16, "negro": 18, "fundido": 12}
# efectos de sonido por tipo: (id del banco de earshot, desfase en s respecto del centro de la unión, peso)
SONIDO = {
    "latigazo": [("whoosh_fast/whip", 0.0, 0.9), ("cut_hit/air", 0.02, 0.35)],
    "caida": [("downlifter/air_fall", -0.25, 0.7), ("cut_hit/sub", 0.18, 0.8)],
    "subida": [("riser/snatch", -0.15, 0.7), ("pro_zip/up", 0.0, 0.5)],
    "zoom": [("whoosh_big/thump", 0.0, 0.9), ("pro_impact/short", 0.03, 0.6)],
    "flash": [("reverse_swell/short", -0.08, 0.6), ("pro_impact/air", 0.0, 0.9)],
    "giro": [("whoosh_big/swell", 0.0, 0.8)],
    "tinta": [("swipe/velvet", 0.0, 0.7), ("drip/drop", 0.2, 0.4)],
    "iris": [("pro_zip/down", -0.1, 0.6), ("pro_pop/boop", 0.25, 0.6)],
    "glitch": [("pro_glitch/standard", 0.0, 0.7)],
    "destello": [("reverse_swell/breath", -0.1, 0.6), ("pro_shimmer/m1", 0.05, 0.5)],
    "negro": [("downlifter/sub_sink", 0.0, 0.6)],
    "fundido": [],
}

def aplicar(tipo, A, B, t, **k):
    fn = TIPOS[tipo]
    import inspect
    acepta = inspect.signature(fn).parameters
    return np.clip(fn(A, B, t, **{a: b for a, b in k.items() if a in acepta}), 0, 255)

if __name__ == "__main__":
    # hoja de prueba: cada transición en 7 momentos entre dos imágenes de entrada
    import sys, os
    from PIL import Image
    a = np.asarray(Image.open(sys.argv[1]).convert("RGB").resize((270, 480)), np.float32)
    b = np.asarray(Image.open(sys.argv[2]).convert("RGB").resize((270, 480)), np.float32)
    filas = []
    for tipo in TIPOS:
        filas.append(np.concatenate([aplicar(tipo, a, b, t, f=i) for i, t in enumerate(np.linspace(0.1, 0.9, 7))], 1))
    Image.fromarray(np.concatenate(filas, 0).astype(np.uint8)).save(sys.argv[3])
    print("hoja:", sys.argv[3])
