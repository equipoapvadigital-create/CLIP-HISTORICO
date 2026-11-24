"""
MEDIR LA FORMA DE NARRAR de una voz (para copiar el TONO de una referencia, no su timbre):
  - sílabas por segundo (aprox. por picos de energía) y palabras por segundo si hay subtítulos,
  - tono: mediana en Hz y en semitonos, RANGO (p10–p90) y movimiento (cuánto sube y baja entre sílabas),
  - pausas: cuántas y de cuánto (> 0.25 s),
  - energía: rango dinámico de la voz (p90 − p20 en dB) y «ataque» (qué tan golpeadas son las sílabas).
Uso: python medir_voz.py voz.wav [voz2.wav ...]      (mejor con la voz SOLA: stems/vocals.wav de rea-video)
"""
import sys, json
import numpy as np, librosa

def medir(ruta):
    y, sr = librosa.load(ruta, sr=16000, mono=True)
    hop = 160
    rms = librosa.feature.rms(y=y, frame_length=640, hop_length=hop)[0]
    db = 20 * np.log10(rms + 1e-6)
    voz = db > np.percentile(db, 95) - 30
    dur_voz = voz.sum() * hop / sr
    # pausas: tramos sin voz de más de 0.25 s dentro del habla
    pausas, n = [], 0
    for v in voz:
        if not v: n += 1
        else:
            if n * hop / sr > 0.25: pausas.append(n * hop / sr)
            n = 0
    # sílabas: picos de la envolvente de energía (suavizada) con voz
    env = np.convolve(rms, np.ones(5) / 5, "same")
    picos = librosa.util.peak_pick(env, pre_max=6, post_max=6, pre_avg=10, post_avg=10, delta=np.percentile(env, 60) * 0.15, wait=6)
    picos = [p for p in picos if voz[p]]
    f0, vf, _ = librosa.pyin(y, fmin=70, fmax=400, sr=sr, frame_length=1024, hop_length=hop)
    f0 = f0[vf & ~np.isnan(f0)]
    st = 12 * np.log2(f0 / np.median(f0))
    salto = np.abs(np.diff(st))
    return {
        "archivo": ruta, "segundos_con_voz": round(float(dur_voz), 1),
        "silabas_por_seg": round(len(picos) / max(dur_voz, 1e-3), 2),
        "tono_mediana_hz": round(float(np.median(f0)), 1),
        "tono_rango_semitonos_p10_p90": round(float(np.percentile(st, 90) - np.percentile(st, 10)), 1),
        "tono_movimiento_st_por_cuadro": round(float(np.mean(salto[salto < 3])), 3),
        "pausas_>0.25s_por_minuto": round(len(pausas) / max(dur_voz, 1e-3) * 60, 1),
        "pausa_media_s": round(float(np.mean(pausas)), 2) if pausas else 0,
        "energia_rango_db_p20_p90": round(float(np.percentile(db[voz], 90) - np.percentile(db[voz], 20)), 1),
    }

if __name__ == "__main__":
    for r in sys.argv[1:]: print(json.dumps(medir(r), ensure_ascii=False))
