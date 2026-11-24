"""
EL NARRADOR CON TONOS (Chatterbox, gratis). Una sola voz que CAMBIA de tono a lo largo del video:
intriga, golpe seco, tristeza, burla, susurro, épica… como un narrador que te está contando un chisme.

Cómo se marca el guion (una línea = un bloque de respiración; cada [tono] abre un tramo nuevo dentro de la línea):
    [intriga] La puerta llevaba años cerrada.
    [golpe] Esa mañana apareció abierta.
Sin etiqueta = [normal]. Cada tramo se genera en UNA pasada con su propia emoción de Chatterbox y luego se le da
color con un procesado suave (tono en semitonos, tempo, volumen, ecualización, eco). Los tramos de una línea se
unen con fundidos cortos (de corrido, nunca «macheteado»); entre líneas, la pausa que pida cada tono.

Lo que hace que se OIGA el cambio (la emoción sola de Chatterbox casi no se nota, lo dijo el usuario):
  - contraste de VELOCIDAD (rápido 1.10 contra lento 0.90),
  - contraste de TONO (−2 a +1.5 semitonos); el VOLUMEN casi igual (±2 dB): nunca debe sentirse que la voz «baja»,
  - pausas dramáticas SOLO antes de la revelación y del golpe,
  - ecualización: el susurro sin graves y cercano; lo épico con cuerpo y eco de sala.

Uso:
  python narrador.py guion_tonos.txt salida_dir                        (voz nueva, tiempos libres)
  python narrador.py guion_tonos.txt salida_dir --encajar frases.json   (cada línea se estira/encoge para caber en
                                         la ventana de la versión vieja: así la animación ya hecha sigue en sincronía)
  --solo 3,7   regenera solo esos tramos ·  --muestra   genera solo las 3 primeras líneas (para escuchar antes)
Salidas: voz_final.wav, palabras_final.json, frases.json, tramos.json (qué tono va dónde: lo usa la mezcla).
"""
import argparse, difflib, json, os, re, subprocess, unicodedata
from pathlib import Path

# tono: emoción y guía de Chatterbox + procesado. st = semitonos, tempo >1 = más rápido, db = volumen,
# eq: None | "cerca" (susurro: sin graves, presencia) | "cuerpo" (graves y calidez) | "frio" (sin brillo),
# eco: 0..1 (sala), antes/despues: pausa en s alrededor del tramo
TONOS = {
    "normal":     dict(ex=0.55, cfg=0.45, temp=0.80, st=0.0,  tempo=1.00, db=0,  eq=None,     eco=0.0,  antes=0.00, despues=0.00),
    "intriga":    dict(ex=0.40, cfg=0.30, temp=0.75, st=-1.0, tempo=0.93, db=-2, eq="cerca",  eco=0.10, antes=0.00, despues=0.10),
    "suspenso":   dict(ex=0.35, cfg=0.30, temp=0.70, st=-1.5, tempo=0.90, db=-3, eq="cerca",  eco=0.15, antes=0.15, despues=0.20),
    "susurro":    dict(ex=0.25, cfg=0.30, temp=0.70, st=-0.5, tempo=0.92, db=-7, eq="cerca",  eco=0.05, antes=0.15, despues=0.10),
    "intimo":     dict(ex=0.35, cfg=0.35, temp=0.75, st=-0.5, tempo=0.95, db=-3, eq="cerca",  eco=0.05, antes=0.10, despues=0.05),
    "golpe":      dict(ex=0.85, cfg=0.55, temp=0.80, st=-1.0, tempo=1.00, db=2,  eq="cuerpo", eco=0.12, antes=0.22, despues=0.12),
    "revelacion": dict(ex=0.70, cfg=0.35, temp=0.80, st=0.5,  tempo=0.94, db=0,  eq="cuerpo", eco=0.15, antes=0.35, despues=0.05),
    "epico":      dict(ex=0.95, cfg=0.50, temp=0.85, st=-1.5, tempo=0.96, db=2,  eq="cuerpo", eco=0.30, antes=0.05, despues=0.10),
    "triste":     dict(ex=0.35, cfg=0.30, temp=0.70, st=-1.0, tempo=0.90, db=-2, eq="frio",   eco=0.10, antes=0.05, despues=0.10),
    "oscuro":     dict(ex=0.45, cfg=0.30, temp=0.75, st=-2.0, tempo=0.93, db=-1, eq="cuerpo", eco=0.20, antes=0.05, despues=0.05),
    "frio":       dict(ex=0.30, cfg=0.40, temp=0.70, st=-1.0, tempo=0.97, db=-1, eq="frio",   eco=0.0,  antes=0.10, despues=0.0),
    "calido":     dict(ex=0.65, cfg=0.45, temp=0.85, st=0.5,  tempo=1.02, db=0,  eq="cuerpo", eco=0.05, antes=0.0,  despues=0.0),
    "alegre":     dict(ex=1.00, cfg=0.55, temp=0.90, st=1.0,  tempo=1.06, db=1,  eq=None,     eco=0.0,  antes=0.0,  despues=0.0),
    "burla":      dict(ex=0.90, cfg=0.55, temp=0.90, st=1.0,  tempo=1.04, db=0,  eq=None,     eco=0.0,  antes=0.0,  despues=0.05),
    "firme":      dict(ex=0.60, cfg=0.50, temp=0.75, st=-0.5, tempo=0.97, db=0,  eq="cuerpo", eco=0.08, antes=0.10, despues=0.05),
    "rapido":     dict(ex=0.65, cfg=0.55, temp=0.80, st=0.5,  tempo=1.10, db=0,  eq=None,     eco=0.0,  antes=0.0,  despues=0.0),
    "urgente":    dict(ex=1.10, cfg=0.60, temp=0.85, st=1.5,  tempo=1.10, db=2,  eq=None,     eco=0.0,  antes=0.0,  despues=0.0),
}

# VOCES DE PERSONAJES («audio de ficción»): en el guion, {voz:demonio} antes de un tramo hace que ESE tramo lo diga
# el personaje con su propio timbre, no el narrador citándolo. Ej.:
#   [urgente] Y una voz que no era la suya gritó: {voz:demonio} «¡No me atormentes, Jesús!»
# formante "shifted" cambia el tamaño de la garganta (timbre de otra persona); grave = pitch < 1, cuerpo grande.
# capa = segunda voz una octava abajo mezclada (demonio, «somos muchos»); eco = sala; dist = aspereza.
VOCES = {
    "jesus":    dict(pitch=0.93, ex=0.40, cfg=0.30, eco=0.22, capa=0.0, dist=0.0, tempo=0.95),
    "demonio":  dict(pitch=0.78, ex=0.95, cfg=0.45, eco=0.45, capa=0.55, dist=0.35, tempo=0.97),
    "legion":   dict(pitch=0.82, ex=0.90, cfg=0.40, eco=0.55, capa=0.7, dist=0.25, tempo=0.95, coro=True),
    "hombre":   dict(pitch=0.88, ex=0.60, cfg=0.45, eco=0.08, capa=0.0, dist=0.0, tempo=1.0),
    "viejo":    dict(pitch=0.84, ex=0.45, cfg=0.30, eco=0.10, capa=0.0, dist=0.08, tempo=0.92),
    "joven":    dict(pitch=1.08, ex=0.70, cfg=0.50, eco=0.06, capa=0.0, dist=0.0, tempo=1.03),
    "mujer":    dict(pitch=1.22, ex=0.65, cfg=0.45, eco=0.08, capa=0.0, dist=0.0, tempo=1.0),
    "nino":     dict(pitch=1.35, ex=0.80, cfg=0.50, eco=0.05, capa=0.0, dist=0.0, tempo=1.05),
    "nina":     dict(pitch=1.48, ex=0.85, cfg=0.50, eco=0.04, capa=0.0, dist=0.0, tempo=1.06),
    "papa":     dict(pitch=0.90, ex=0.60, cfg=0.45, eco=0.05, capa=0.0, dist=0.0, tempo=1.0),
    "mama":     dict(pitch=1.20, ex=0.65, cfg=0.45, eco=0.05, capa=0.0, dist=0.0, tempo=1.0),
    "multitud": dict(pitch=0.95, ex=0.85, cfg=0.50, eco=0.30, capa=0.0, dist=0.0, tempo=1.0, coro=True),
}

ap = argparse.ArgumentParser(); ap.add_argument("guion"); ap.add_argument("sal")
ap.add_argument("--encajar", default=None, help="frases.json viejo: cada línea cabe en su ventana")
ap.add_argument("--solo", default=None); ap.add_argument("--semilla", type=int, default=9100, help="otra semilla = otras tomas al rehacer con --solo"); ap.add_argument("--muestra", action="store_true")
ap.add_argument("--entre", type=float, default=None, help="pausa base entre líneas (s); por defecto la del estilo")
ap.add_argument("--voz-ref", default=None, help="wav de 10–20 s de la voz del narrador (con permiso de su dueño): Chatterbox la clona")
ap.add_argument("--estilo", default="narrador", help="forma de narrar (ESTILOS): ref3 = la referencia del oeste que eligió el usuario")
a = ap.parse_args()

def modelo_local(variable, archivo):
    ubicacion = os.environ.get(variable)
    if not ubicacion:
        ap.error(f"Indica una carpeta local mediante {variable}.")
    carpeta = Path(ubicacion).expanduser().resolve()
    if not (carpeta / archivo).is_file():
        ap.error(f"Falta {archivo} en la carpeta local indicada en {variable}.")
    return carpeta

modelo_tts = modelo_local("CHATTERBOX_DIR", "t3_mtl23ls_v2.safetensors")
modelo_asr = modelo_local("WHISPER_MODEL", "model.bin")
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
import numpy as np, torch, torchaudio as ta, librosa
os.makedirs(a.sal, exist_ok=True)
# ESTILOS de narración, MEDIDOS con herramientas/medir_voz.py (se copia la FORMA de narrar, no el timbre de nadie):
#   (~194 Hz contra 143 nuestra), entonación más viva (0.39 contra 0.33 st por cuadro), ~4.6 sílabas/s.
ESTILOS = {
    # «narrador» (pedido del usuario: la voz aguda/robótica sonaba horrible): UNA sola voz, SIN subir ni bajar el tono
    # con rubberband (eso la volvía robótica) y sin voces de personajes. El dinamismo sale de la propia actuación de
    # Chatterbox (exageración por tono), de las pausas y de la puntuación del guion. Solo una EQ y compresión suaves.
    # ref6 (Dino Rex, medido): grave 118 Hz, 5,4 sílabas/s, 35 micro-pausas/min de 0,29 s, poco sube-y-baja de tono.
    # Escribe UNA frase corta por línea: la pausa entre líneas es la micro-pausa. Después acelera con tempo (sin tono).
    "ref6": dict(st=0.0, tempo=1.00, pausa=0.35, ex=0.0, entre=0.22, natural=True,
                 ex_max=0.45, temp_max=0.65, f0_meta=115, f0_pico=195),
    "narrador": dict(st=0.0, tempo=1.00, pausa=0.8, ex=0.10, entre=0.10, natural=True,
                     # 2ª queja: «aún tiene tonos muy agudos, se ve robótico» (medido: mediana 149 Hz, picos 275 Hz).
                     # La exageración alta de Chatterbox hace CHILLAR: se topa, se baja la temperatura y, entre las
                     # tomas buenas, se prefiere la más grave y estable (voz de locutor ~115 Hz, picos < 200 Hz).
                     ex_max=0.55, temp_max=0.68, f0_meta=118, f0_pico=200),
    # «estudio» (3ª queja: errores, palabras en otro idioma, «suena robótico»): igual que narrador pero más quieto
    # (menos exageración y temperatura), hasta 8 tomas y solo se acepta la que Whisper oye casi igual al guion.
    "estudio": dict(st=0.0, tempo=1.00, pausa=0.7, ex=0.0, entre=0.12, natural=True, tomas=6, acepta=0.95,
                    ex_max=0.45, temp_max=0.62, f0_meta=118, f0_pico=200),
    "ref3":  dict(st=2.5, tempo=1.05, pausa=0.25, ex=0.15, entre=0.07),
    "calmo": dict(st=0.0, tempo=1.00, pausa=1.00, ex=0.00, entre=0.28),
    "intriga_seca": dict(st=0.0, tempo=1.00, pausa=0.55, ex=0.05, entre=0.10, seco=True),
}
EST = ESTILOS[a.estilo]
if a.entre is None: a.entre = EST["entre"]

lineas = [l.strip() for l in open(a.guion, encoding="utf-8") if l.strip() and not l.startswith("#")]
if a.muestra: lineas = lineas[:3]
def partir(l):
    """'[intriga] aaa {voz:demonio} «bbb» ccc' -> [('intriga','aaa'), ('intriga@demonio','«bbb»'), ('intriga','ccc')]
    [tono] sigue valiendo hasta el próximo [tono]; {voz:x} vale SOLO para la cita «…» que viene (o el resto del tramo)."""
    out, tono, voz = [], "normal", None
    for m in re.finditer(r"\[([a-zA-Záéíóú]+)\]|\{voz:([a-zA-Záéíóú]+)\}|([^\[\{]+)", l):
        if m.group(1):
            tono = m.group(1).lower()
            if tono not in TONOS: raise SystemExit(f"tono desconocido: [{tono}] (hay: {', '.join(TONOS)})")
        elif m.group(2):
            voz = m.group(2).lower()
            if voz not in VOCES: raise SystemExit(f"voz desconocida: {{voz:{voz}}} (hay: {', '.join(VOCES)})")
        else:
            txt = m.group(3).strip()
            if not txt: continue
            if voz:
                cita = re.match(r"(«[^»]*»[.!?…,]*)(.*)", txt)
                if cita:
                    out.append((f"{tono}@{voz}", cita.group(1).strip()))
                    if cita.group(2).strip(): out.append((tono, cita.group(2).strip()))
                else:
                    out.append((f"{tono}@{voz}", txt))
                voz = None
            else:
                out.append((tono, txt))
    return out
PLAN = [partir(l) for l in lineas]

# Whisper escribe los números con cifras y los nombres en su ortografía original: se pasan a palabras (si no,
# «Mil ochocientos once» contra «1811» daba 0 de parecido y la toma buena se descartaba o la mala se aceptaba)
from num2words import num2words
ALIAS = {"jack": "yak", "welch": "uelch", "friedman": "friman", "fridman": "friman", "nottingham": "notingam", "byron": "bairon",
         "ludd": "lud", "sherwood": "sherwud", "mit": "eme i te", "ia": "ia", "york": "york"}
def norm(t):
    t = re.sub(r"(\d)[.,](\d{3})", r"\1\2", t)
    t = re.sub(r"\d+", lambda m: " " + num2words(int(m.group()), lang="es") + " ", t)
    t = unicodedata.normalize("NFD", t.lower()); t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    out = []
    for w in re.findall(r"[a-zñ]+", t): out += ALIAS.get(w, w).split()
    return out

from chatterbox.mtl_tts import ChatterboxMultilingualTTS   # noqa: E402
from faster_whisper import WhisperModel                     # noqa: E402
_dev = "cuda" if torch.cuda.is_available() else "cpu"
tts = ChatterboxMultilingualTTS.from_local(modelo_tts, _dev)
asr = WhisperModel(str(modelo_asr), device="cpu", compute_type="int8", local_files_only=True)
SR = tts.sr
def a16k(x): return ta.functional.resample(torch.from_numpy(x)[None], SR, 16000)[0].numpy().astype(np.float32)

cache = os.path.join(a.sal, "tramos"); os.makedirs(cache, exist_ok=True)
solo = set(int(x) for x in a.solo.split(",")) if a.solo else None
informe, k_global = [], 0
def generar(i, tono, texto):
    base, _, voz = tono.partition("@")
    P = dict(TONOS[base])
    if voz: P.update({k: VOCES[voz][k] for k in ("ex", "cfg")})
    vr = os.path.splitext(os.path.basename(a.voz_ref))[0] if a.voz_ref else "base"
    ruta = os.path.join(cache, f"t{i:02d}_{tono.replace('@', '_')}_{a.estilo}_{vr}.npy")
    if os.path.exists(ruta) and (solo is None or i not in solo): return np.load(ruta)
    habla = texto.replace("…", ",").replace("«", "").replace("»", "")
    meta = norm(texto); mejor = None
    for intento in range(EST.get("tomas", 4 if EST.get('natural') else 8)):   # 4 tomas basta (8 tardaba ~1 h por guion)
        torch.manual_seed(a.semilla + 100 * i + intento)
        ex = min(EST.get("ex_max", 1.2), P["ex"] + EST["ex"]); tmp_ = min(EST.get("temp_max", 1.0), P["temp"])
        cfg_ = P["cfg"]
        if EST.get("tomas") and intento >= 3:      # si falla, más quieto y más pegado al texto
            ex = min(ex, 0.35); tmp_ = min(tmp_, 0.5); cfg_ = max(cfg_, 0.5)
        w = tts.generate(habla, language_id="es", exaggeration=ex, cfg_weight=cfg_, temperature=tmp_,
                         **({"audio_prompt_path": a.voz_ref} if a.voz_ref else {}))[0].numpy()
        sg, _ = asr.transcribe(a16k(w), language="es", word_timestamps=True)
        pw = [x for s in sg for x in s.words]
        oido = norm(" ".join(x.word for x in pw))
        r = difflib.SequenceMatcher(a=meta, b=oido).ratio()
        sobra = max(0, len(oido) - len(meta)); huecos = sum(1 for p, q in zip(pw, pw[1:]) if q.start - p.end > 0.9)
        nota = r - 0.15 * sobra - 0.1 * huecos
        if len(w) / SR > 1.2 + 0.75 * len(meta): nota -= 1.0       # mucho más larga que el texto: inventó cosas
        agudo = 0.0
        if EST.get("f0_meta"):          # castigar las tomas agudas o chillonas
            f0 = librosa.yin(a16k(w), fmin=60, fmax=450, sr=16000, frame_length=1024)
            f0 = f0[(f0 > 65) & (f0 < 440)]
            if len(f0):
                agudo = max(0, np.median(f0) - EST["f0_meta"]) / 60 + max(0, np.percentile(f0, 95) - EST["f0_pico"]) / 80
            nota -= agudo
        if pw: w = w[int(max(0, pw[0].start - 0.08) * SR):int(min(len(w) / SR, pw[-1].end + 0.25) * SR)]
        if mejor is None or nota > mejor[0]: mejor = (nota, w, intento, r)
        if EST.get("tomas"):   # estudio: lo que importa es que DIGA el guion; una pausa en «…» o algo de tono no la tumba
            if r >= EST["acepta"] and sobra == 0 and agudo < 0.5: break
        elif r >= EST.get("acepta", 0.95) and sobra == 0 and huecos == 0 and agudo < 0.35: break
    nota, w, k, r = mejor
    np.save(ruta, w.astype(np.float32))
    informe.append({"tramo": i, "tono": tono, "texto": texto, "nota": round(nota, 3), "palabras": round(r, 3), "intentos": k + 1})
    print(f"{i:2d} [{tono}] nota {nota:.2f} ({k + 1} int.)  {texto[:55]}", flush=True)
    return w

def ffx(w, filtros, tmp):
    ent, sal = tmp + "_vin.wav", tmp + "_vout.wav"
    ta.save(ent, torch.from_numpy(w)[None], SR)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", ent, "-af", ",".join(filtros), "-ar", str(SR), sal], check=True)
    y, _ = ta.load(sal); os.remove(ent); os.remove(sal)
    return y[0].numpy().astype(np.float32)

def voz_personaje(w, voz, tmp):
    """el timbre del personaje: otra garganta (formante corrido), capa una octava abajo, aspereza, sala, coro"""
    V = VOCES[voz]
    y = ffx(w, [f"rubberband=pitch={V['pitch']:.3f}:tempo={V['tempo']:.3f}:formant=shifted"], tmp)
    if V.get("capa"):
        baja = ffx(w, [f"rubberband=pitch={V['pitch'] * 0.5:.3f}:tempo={V['tempo']:.3f}:formant=shifted"], tmp)
        n = min(len(y), len(baja)); y = y[:n] + V["capa"] * baja[:n]
    if V.get("coro"):     # varias gargantas a la vez: copias corridas en tono y tiempo
        n = len(y); acc = y.copy()
        for k, (pp, ms) in enumerate(((1.06, 23), (0.94, 37), (1.12, 51))):
            c = ffx(w, [f"rubberband=pitch={V['pitch'] * pp:.3f}:tempo={V['tempo']:.3f}:formant=shifted", f"adelay={ms}"], tmp)
            m = min(n, len(c)); acc[:m] += 0.55 * c[:m]
        y = acc
    f = []
    if V.get("dist"): f.append(f"asoftclip=type=atan:param={1 + 4 * V['dist']:.2f}")
    if V.get("eco"): f.append(f"aecho=0.8:0.7:60|120|190:{0.4 * V['eco']:.3f}|{0.3 * V['eco']:.3f}|{0.2 * V['eco']:.3f}")
    return ffx(y, f, tmp) if f else y

def procesar(w, tono, tmp):
    """el color del tono: tono y tempo con rubberband (sin efecto ardilla), ecualización, eco y volumen"""
    P = TONOS[tono]
    if EST.get("natural"):   # sin rubberband: la voz tal cual, con cuerpo y presencia de locutor
        # cuerpo en graves, SIN realce de agudos (el realce en 3 kHz sumaba a lo «robótico»), un poco menos de
        # 4–6 kHz (lo metálico del vocoder) y un de-esser suave
        return ffx(w, ["highpass=f=65", "equalizer=f=130:t=q:w=1:g=3", "equalizer=f=4500:t=q:w=1.5:g=-3",
                       "equalizer=f=7500:t=q:w=1:g=-2", "deesser=i=0.4", "lowpass=f=11000",
                       "acompressor=threshold=-20dB:ratio=2.5:attack=10:release=120"], tmp)
    if EST.get("seco"):
        return ffx(w, ["highpass=f=75", "acompressor=threshold=-18dB:ratio=1.4:attack=16:release=110"], tmp)
    f = [f"rubberband=pitch={2 ** ((P['st'] + EST['st']) / 12):.4f}:tempo={P['tempo'] * EST['tempo']:.3f}:formant=preserved"]
    if P["eq"] == "cerca": f += ["highpass=f=170", "equalizer=f=3500:t=q:w=1.2:g=3", "acompressor=threshold=-24dB:ratio=3"]
    if P["eq"] == "cuerpo": f += ["equalizer=f=140:t=q:w=1:g=3", "equalizer=f=2800:t=q:w=1:g=1.5"]
    if P["eq"] == "frio": f += ["equalizer=f=250:t=q:w=1:g=-2", "lowpass=f=7000"]
    if P["eco"] > 0: f += [f"aecho=0.85:0.6:45|85|140:{0.35 * P['eco']:.3f}|{0.25 * P['eco']:.3f}|{0.15 * P['eco']:.3f}"]
    f += [f"volume={P['db']}dB"]
    ent, sal = tmp + "_in.wav", tmp + "_out.wav"
    ta.save(ent, torch.from_numpy(w)[None], SR)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", ent, "-af", ",".join(f), "-ar", str(SR), sal], check=True)
    y, _ = ta.load(sal); os.remove(ent); os.remove(sal)
    return y[0].numpy().astype(np.float32)

def fade(x, n_in, n_out):
    x = x.copy(); n_in = min(n_in, len(x)); n_out = min(n_out, len(x))
    x[:n_in] *= np.sin(np.linspace(0, np.pi / 2, n_in)) ** 2
    x[len(x) - n_out:] *= np.cos(np.linspace(0, np.pi / 2, n_out)) ** 2
    return x
def rms_voz(x):
    f = x[: len(x) // 480 * 480].reshape(-1, 480); e = np.sqrt((f ** 2).mean(1))
    return float(np.sqrt((e[e > e.max() * 0.15] ** 2).mean()))
def unir(a_, b_, hueco, cruce=0.03):
    if a_ is None: return b_
    a_ = np.concatenate([a_, np.zeros(int(SR * max(hueco, cruce)), np.float32)])
    n = int(SR * cruce); a_[-n:] += b_[:n]
    return np.concatenate([a_, b_[n:]])

# 1) generar crudo, igualar volumen ANTES del color (así el ±dB de cada tono es real), 2) color, 3) unir
crudos = []
for li, tramos in enumerate(PLAN):
    for tono, texto in tramos:
        crudos.append((li, tono, texto, generar(k_global, tono, texto))); k_global += 1
ref = np.median([rms_voz(w) for *_, w in crudos])
tmp = os.path.join(a.sal, "_tmp")
lineas_audio, tramos_info = [], []
for li in range(len(PLAN)):
    voz, cursor = None, 0.0
    for (l2, tono, texto, w) in crudos:
        if l2 != li: continue
        base, _, personaje = tono.partition("@")
        w = procesar(w * (ref / rms_voz(w)), base, tmp)
        if personaje and not EST.get("natural"): w = voz_personaje(w, personaje, tmp)
        # después del color, volver a igualar: el tono se oye en velocidad/timbre/pausas, el VOLUMEN solo ±2 dB
        # (el usuario notó que la voz «bajaba» en susurro/intriga/suspenso: quedaban 10–18 dB abajo)
        w = w * (ref / rms_voz(w)) * 10 ** (max(-2, min(2, TONOS[base]["db"])) / 20)
        w = fade(w, int(0.02 * SR), int(0.08 * SR))
        hueco = 0.0 if voz is None else (0.10 + TONOS[tono.split("@")[0]]["antes"]) * EST["pausa"]
        ini = 0.0 if voz is None else len(voz) / SR + hueco
        voz = unir(voz, w, hueco)
        tramos_info.append({"linea": li, "tono": tono, "texto": texto, "t0_local": round(ini, 3), "t1_local": round(len(voz) / SR, 3)})
    lineas_audio.append(voz)

# 4) montar la línea de tiempo: libre, o encajada en las ventanas de la versión vieja
if a.encajar:
    viejo = json.load(open(a.encajar, encoding="utf-8"))
    assert len(viejo) == len(lineas_audio), f"el guion tiene {len(lineas_audio)} líneas y {a.encajar} {len(viejo)}"
    total = viejo[-1]["t1"] + 0.6
    voz = np.zeros(int(SR * total) + SR, np.float32)
    fin_prev = -1.0
    for li, (w, v) in enumerate(zip(lineas_audio, viejo)):
        ini_t = max(v["t0"], fin_prev + 0.12)                       # nunca encima de la línea anterior
        sig = viejo[li + 1]["t0"] - 0.12 if li + 1 < len(viejo) else v["t1"] + 0.3
        meta = max(0.3, min(v["t1"], sig) - ini_t); tiene = len(w) / SR
        k = max(0.85, min(1.25, tiene / meta))                      # >1 acelera (hasta 1.25 si no cabe)
        if abs(k - 1) > 0.01:
            ent, sal = tmp + "_in.wav", tmp + "_out.wav"
            ta.save(ent, torch.from_numpy(lineas_audio[li])[None], SR)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", ent, "-af", f"rubberband=tempo={k:.4f}:formant=preserved", sal], check=True)
            w = ta.load(sal)[0][0].numpy().astype(np.float32); os.remove(ent); os.remove(sal)
        i0 = int(ini_t * SR); voz[i0:i0 + len(w)] += w[: len(voz) - i0]
        fin_prev = ini_t + len(w) / SR
        for t in tramos_info:
            if t["linea"] == li: t["t0"] = round(ini_t + t["t0_local"] / k, 3); t["t1"] = round(ini_t + t["t1_local"] / k, 3)
        print(f"línea {li}: {tiene:.2f} s -> ventana {meta:.2f} s (x{k:.3f})")
else:
    voz, t_ = None, 0.0
    for li, w in enumerate(lineas_audio):
        primero = PLAN[li][0][0]
        hueco = 0.0 if voz is None else a.entre + (TONOS[primero.split("@")[0]]["antes"] + TONOS[PLAN[li - 1][-1][0].split("@")[0]]["despues"]) * EST["pausa"]
        t_ = 0.0 if voz is None else len(voz) / SR + hueco
        voz = unir(voz, w, hueco, cruce=0.04)
        for t in tramos_info:
            if t["linea"] == li: t["t0"] = round(t_ + t["t0_local"], 3); t["t1"] = round(t_ + t["t1_local"], 3)
    voz = np.concatenate([voz, np.zeros(int(0.5 * SR), np.float32)])

bruta = os.path.join(a.sal, "voz_bruta.wav"); final = os.path.join(a.sal, "voz_final.wav")
ta.save(bruta, torch.from_numpy(voz)[None], SR)
# loudness de todo junto, con rango amplio para que el susurro siga siendo susurro
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", bruta, "-af", "acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=2,loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", "48000", final], check=True)

# 5) tiempos por palabra sobre el audio final (para subtítulos, efectos y animación)
wv, sr2 = ta.load(final)
x16 = ta.functional.resample(wv.mean(0, keepdim=True), sr2, 16000)[0].numpy().astype(np.float32)
segs, _ = asr.transcribe(x16, language="es", word_timestamps=True)
W = [w_ for s in segs for w_ in s.words]
texto_total = " ".join(t for tr in PLAN for _, t in tr)
guion_pal = [p for p in texto_total.split() if re.search(r"\w", p)]
gn = [(norm(p) or [""])[0] for p in guion_pal]; on = [(norm(w_.word) or [""])[0] for w_ in W]
sm = difflib.SequenceMatcher(a=gn, b=on, autojunk=False)
t0 = [None] * len(gn); t1 = [None] * len(gn)
for blk in sm.get_matching_blocks():
    for k in range(blk.size): t0[blk.a + k] = W[blk.b + k].start; t1[blk.a + k] = W[blk.b + k].end
for i in range(len(gn)):
    if t0[i] is None:
        prev = t1[i - 1] if i > 0 and t1[i - 1] is not None else 0.0
        k = i + 1
        while k < len(gn) and t0[k] is None: k += 1
        nxt = t0[k] if k < len(gn) else wv.shape[1] / sr2
        n = k - i; paso = (nxt - prev) / (n + 1)
        for m in range(n): t0[i + m] = prev + paso * (m + 0.2); t1[i + m] = prev + paso * (m + 1)
pal = [{"w": g, "t0": round(float(p), 3), "t1": round(float(q), 3)} for g, p, q in zip(guion_pal, t0, t1)]
json.dump(pal, open(os.path.join(a.sal, "palabras_final.json"), "w", encoding="utf-8"), ensure_ascii=False)
fr, i = [], 0
for tr in PLAN:
    b = " ".join(t for _, t in tr); n = len([p for p in b.split() if re.search(r"\w", p)])
    fr.append({"t0": pal[i]["t0"], "t1": pal[i + n - 1]["t1"], "texto": b}); i += n
json.dump(fr, open(os.path.join(a.sal, "frases.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
json.dump(tramos_info, open(os.path.join(a.sal, "tramos.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
json.dump(informe, open(os.path.join(a.sal, "control_calidad.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"listo: {wv.shape[1] / sr2:.1f} s, Whisper emparejó {sum(b.size for b in sm.get_matching_blocks())}/{len(gn)}")
for t in tramos_info: print(f"{t['t0']:6.2f}-{t['t1']:6.2f} [{t['tono']}] {t['texto'][:60]}")

