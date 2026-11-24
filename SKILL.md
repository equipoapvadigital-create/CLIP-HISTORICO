---
name: clip-historico
description: Crea shorts narrativos históricos o bíblicos en español, con guion de retención, narración cinematográfica y animación 2D, 2.5D o 3D. Planea, produce y verifica video vertical con audio.
---

# CLIP HISTORICO

Empieza por el tema, la audiencia, el estilo y la duración. Respeta las decisiones previas de la persona. Trabaja en la carpeta que haya elegido y guarda por separado el guion, la voz, las escenas, los renders intermedios y el MP4 final.

Durante la producción utiliza modelos, materiales y grabaciones locales. La comprobación de fuentes se puede hacer con material entregado por la persona.

## Guion

- Verifica los datos con fuentes fiables. Distingue un relato transmitido, una dramatización y un hecho documentado. Guarda las fuentes con el guion.
- Abre en el segundo cero con una contradicción, una decisión costosa o una imagen que deje una pregunta. Da el contexto mínimo para que el episodio se entienda por sí solo.
- Organiza la historia en causa y efecto. Cada bloque cambia lo que el público sabe o lo que está en juego. Introduce motivos, consecuencias y detalles que se puedan animar. Evita repetir el gancho o describir lo que ya muestra la imagen.
- En una serie de cuatro partes, reserva un conflicto y un desenlace para cada capítulo. Un final abierto debe resolver la promesa de su propio episodio y dejar una pregunta concreta para el siguiente.
- Para 60 segundos, escribe unas 150–175 palabras como punto de partida. Usa lectura real, pausas y tiempos de la voz para ajustar. Guarda una tabla de planos y audio por bloque. Si hay llamada a seguir, intégrala después de la resolución y dale una razón ligada a la historia.

## Voz y sonido

- Usa un narrador en español, con intriga, énfasis y pausas naturales. Evita eco continuo, cambios artificiales de tono y voces clonadas sin autorización. Marca emociones por tramo. Reserva el silencio breve para un giro o un detalle que merece oírse.
- El [narrador local](audio/narrador.py) genera WAV y tiempos por palabra. Usa `--estilo intriga_seca` para conservar el timbre. Revisa nombres, cantidades y finales con la transcripción y escucha puntos críticos antes de montar.
- Diseña un ambiente por lugar y sincroniza golpes con su cuadro, no con el corte más cercano. Usa timbres distintos para metal, cuerda, madera y tela. Da protagonismo a la voz. Como punto de partida, apunta a −14 LUFS y un pico verdadero por debajo de −1 dBTP.

## Imagen y montaje

- Elige animación 2D ilustrada en Remotion para diálogo, personajes planos en escenarios 3D para profundidad, o Blender para realismo. Lee [Producción y montaje](guias/produccion.md).
- Diseña siluetas y reacciones distintas. Anima pelo, ropa y objetos con anticipación e inercia. En diálogo, acércate a quien habla y vuelve al plano general cuando cambie la situación.
- Llena el encuadre con elementos que expliquen el lugar. Usa primer plano, sujeto y fondo con paralaje, perspectiva atmosférica y una fuente de luz que también afecte al personaje. Reserva partículas y sacudidas para las acciones que las motivan.
- Alterna planos generales, reacciones e insertos. Corta sobre acciones o miradas. Usa insertos de objetos para mostrar una causa o un cambio que un plano general ocultaría. Ajusta el ritmo a la escena.
- Usa subtítulos si el formato lo pide. Agrupa 2–4 palabras, destaca las relevantes, conserva contraste y respeta el margen seguro y las caras.

## Render y revisión

- Empieza con cuadros de prueba. Confirma que la GPU elegida funciona antes de anunciar tiempos. En Blender, usa el dispositivo disponible o CPU. Renderiza cuadros numerados en carpetas por toma y conserva los archivos que permitan retomar.
- Exporta MP4 H.264 vertical a 1080 × 1920 y 30 fps con voz, música y efectos. Si el encargo fija una duración exacta, verifica video y audio por separado con ffprobe.
- Revisa cuadros de todas las tomas, la primera y última imagen, el cierre de las secuencias de texturas, el audio y la sincronía. Decodifica el archivo completo con FFmpeg. Entrega la ruta, la duración y una nota breve sobre cualquier limitación real.
- Si preparas un lanzador para otra persona, usa rutas relativas, comprueba dependencias y muestra errores claros. Conserva sus archivos y credenciales en su equipo.
