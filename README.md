# CLIP HISTORICO

Skill en español para crear shorts narrativos con guion, voz cinematográfica y animación.

Empieza en [SKILL.md](SKILL.md). La [guía de producción](guias/produccion.md) detalla escenas, cámara, sonido, montaje y verificación. Las carpetas de plantillas contienen módulos de Remotion y síntesis de audio. Blender y FFmpeg se instalan según el motor elegido.

Para narración local, configura Python, FFmpeg y las dependencias de `audio/narrador.py`, entre ellas PyTorch, torchaudio, Chatterbox, faster-whisper, librosa y num2words. Puedes indicar modelos locales mediante `CHATTERBOX_DIR` y `WHISPER_MODEL`. Ejecuta `python audio/narrador.py guion.txt salida --estilo intriga_seca` con un párrafo de narración por línea y etiquetas opcionales como `[intriga]` o `[susurro]`.

Los módulos de animación y análisis se basan en parte en [claude-animated-shorts](https://github.com/mromidev/claude-animated-shorts). Consulta la licencia incluida.
