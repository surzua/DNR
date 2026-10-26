# DNR: ampliar oportunidades y construir alcance con utilidad

Fecha: 25 de octubre de 2026. Análisis del repositorio actual, sus 54 oportunidades históricas y fuentes externas. Las recomendaciones son propuestas; no modifican el pipeline vigente. La ejecución diaria mediante cron externo se considera resuelta.

## 1. Diagnóstico

Sí conviene ampliar el alcance. El radar ya contempla simuladores y apps, pero los interpreta dentro de un marco de Data Science y periodismo de datos. La limitación principal es la pregunta que intenta responder: «¿qué análisis cuantitativo puedo hacer con esta noticia?». Propongo agregar «¿qué necesita entender, calcular, decidir o hacer una persona a raíz de esta noticia, y qué podemos construir para ayudarla?».

Propuesta de misión: **Detectar cambios y conversaciones relevantes en Chile y transformarlos en herramientas y explicaciones digitales útiles, verificables y fáciles de compartir.**

La analítica, la programación web y la IA son capacidades disponibles. El formato se elige según la necesidad y el tiempo; no es necesario encontrar un dataset grande para justificar cada propuesta. Una calculadora con una fórmula pública, un asistente basado en reglas verificadas o un planificador con fechas oficiales también pueden tener valor.

La ampliación abre oportunidades plausibles. No permite cuantificar cuántas se perdieron: el historial conserva seleccionados, no todas las alternativas ni sus descartes. Tampoco prueba que una app tenga más alcance que un gráfico. Eso requiere publicar y medir.

## 2. Evidencia interna

| Hallazgo | Interpretación y acción |
|---|---|
| 31 de 54 candidatos son gráficos; 23 son apps Streamlit | Ya existe interés por interactividad, pero el formato de app está ligado a un framework. Separar producto y tecnología. |
| El schema solo admite gráfico, app Streamlit y análisis predictivo/optimización | No permite expresar directamente guías interactivas, planificadores, comparadores, juegos, generadores y verificadores basados en reglas. |
| Prompt centrado en ángulos contraintuitivos y evidencia cuantitativa | Puede privilegiar una historia llamativa sobre una tarea práctica. Incorporar necesidad, audiencia, acción y motivo para compartir. |
| Los 54 registros tienen estado `candidate` | El archivo no documenta selección, publicación ni resultados. No se puede evaluar éxito con él; podría existir seguimiento fuera del repositorio. |
| 37 de 54 combinaciones de puntajes son (9,8), (8,9) u (8,8) | Hay poca discriminación entre seleccionados. Como el historial ya está filtrado, esto no demuestra mala calibración por sí solo. Guardar también descartes y justificaciones. |
| El modelo propone fuentes, pero la evaluación no consulta esas páginas | «Fuente concreta» no implica dato encontrado o utilizable. Introducir verificación de viabilidad. |
| Hay propuestas con cifras, causalidad y conclusiones anticipadas | El generador necesita distinguir hechos de la noticia, hipótesis y hallazgos todavía inexistentes. |

Ejemplos del historial, citados como contenido generado y no como hechos comprobados:

- Una propuesta afirma que un escaneo «demuestra» que más del 60% de los dominios de apuestas elude bloqueos, cuando ese escaneo es parte del plan pendiente. Además, probar DNS/HTTP desde un resolvedor no demuestra por sí solo el bloqueo efectivo en todos los proveedores.
- Otra atribuye pérdidas de un fondo previsional a exposición agresiva a derivados, antes de descargar y analizar carteras. La existencia de una pérdida no identifica su causa.
- Otra equipara ejecución presupuestaria municipal con recursos disponibles para enfrentar emergencias. Ese vínculo requiere validar clasificación contable, compromisos, liquidez y fecha de los datos.

Cambio editorial prioritario: reemplazar «los datos demuestran X» por «comprobar si X, usando Y; si no se verifica, publicar el resultado real». Una conclusión no se elige por su potencial de viralidad.

## 3. Familias de oportunidad

Los ejemplos siguientes ilustran respuestas a tipos de noticias y temas del historial; no son afirmaciones de que sean tendencia hoy ni de que sus fuentes ya estén verificadas.

| Detonante | Necesidad concreta | Producto posible | Motivo para compartir | Condición de viabilidad |
|---|---|---|---|---|
| Cambio de tarifa eléctrica | Entender el impacto en mi cuenta | Calculadora de escenarios | Avisar a familiares | Fórmula, componentes y vigencia verificados; no aplicar un porcentaje nacional a toda la boleta sin respaldo |
| Cambio de peajes o viaje masivo | Presupuestar un trayecto | Comparador de peajes y combustible | Coordinar un viaje | Tarifas, categoría vehicular y supuestos claros; no prometer tráfico en vivo sin datos |
| Anuncio de beneficio o trámite | Saber requisitos y próximos pasos | Guía interactiva de requisitos | Ayudar a alguien | Reglas oficiales, estado anunciado/aprobado/vigente y enlace de solicitud oficial |
| Cambio laboral | Entender un horario o preparar una conversación | Planificador de jornada | Comparar escenarios en un equipo | Excepciones y reglas verificadas; no presentar una simulación como dictamen legal |
| Torneo deportivo | Explorar qué combinaciones clasifican | Simulador de escenarios | Debatir con amigos | Tabla, reglamento y desempates actuales |
| Debate sobre precios o inflación | Entender mi canasta | Comparador de escenarios de gasto | Comparar hábitos sin publicar datos privados | Canasta y supuestos explícitos; diferenciar precios individuales e índice agregado |
| Anuncio cultural o espectáculo | Organizar una salida | Calendario o planificador | Coordinar un grupo | Horarios oficiales y estado de actualización |
| Discusión viral sobre probabilidades | Entender una intuición equivocada | Minijuego o simulación visual | Desafiar a amigos | Resultado reproducible y explicación fiel |
| Cambio en una plataforma digital | Completar una tarea nueva | Herramienta de migración o checklist | Ayudar a colegas | Acceso permitido y tratamiento mínimo de datos |

Prioridad inicial sugerida: herramientas de costo de vida y trámites; luego explicaciones y simulaciones profesionales; finalmente experimentos lúdicos ligados a actualidad. Como hipótesis de cartera, probar 60% utilidad cotidiana, 30% explicación analítica y 10% exploración durante un mes, revisando el reparto según resultados. No son cuotas rígidas de alertas diarias.

En temas de emergencia, una herramienta debe apoyar información oficial y mostrar su fecha. Un mapa histórico no debe declarar una vivienda segura ni sustituir una alerta oficial.

## 4. De atención a uso y difusión

Una noticia crea un contexto de interés; la herramienta necesita además resolver una tarea. La cadena a diseñar es: alguien ve una promesa concreta, entiende su relevancia, obtiene un resultado y tiene una razón para compartirlo.

Preguntas obligatorias para una oportunidad:

1. ¿A quién afecta el cambio y qué pregunta se hace esa persona?
2. ¿Qué hace hoy para resolverla y qué herramienta existente ya la ayuda?
3. ¿Qué obtendrá con dos o tres entradas o una interacción breve?
4. ¿Por qué otra persona querría abrir el resultado o recibir la herramienta?
5. ¿Dónde se puede alcanzar a esa audiencia de forma pertinente?
6. ¿Qué evidencia hace confiable la respuesta?

Diseño propuesto para las apps: móvil primero, sin registro salvo necesidad real, ejemplo precargado, resultado temprano, fuentes visibles, fecha de actualización y supuestos editables. El objetivo inicial de obtener valor en menos de un minuto es una meta de diseño que hay que observar en uso, no una afirmación probada.

Cada producto debe incluir un paquete de distribución: promesa, demostración corta, imagen comprensible en un post y enlace. La pieza debe aportar valor incluso si el lector no abre la app. Para el producto, preparar una tarjeta de resultado opcional y un botón para copiar enlace o compartir; verificar que la vista previa funcione en los canales elegidos.

Compartir tiene razones distintas: utilidad («te puede servir»), coordinación («decidamos juntos»), curiosidad («prueba qué pasa») e identidad («este es mi resultado»). Elegir una razón concreta. No publicar sueldo, RUT, dirección u otros datos personales en URLs, imágenes o analítica.

LinkedIn puede servir para mostrar criterio y capacidad profesional; grupos y conversaciones pertinentes pueden distribuir una herramienta cotidiana; periodistas y organizaciones pueden amplificar recursos verificables. Cada oportunidad debe elegir un canal inicial y una audiencia, sin asumir preferencias del algoritmo ni automatizar mensajes a terceros.

## 5. Evidencia externa y límites

- Berger y Milkman estudian qué contenido se comparte y encuentran asociaciones con utilidad práctica, interés, sorpresa y activación emocional. La implicación propuesta para DNR es diseñar valor y una razón para compartir. No es evidencia de que una calculadora chilena en 2026 vaya a volverse viral. El estudio también muestra diferencias por forma de difusión: no conviene trasladar resultados entre canales sin medir. [Investigación original](https://jonahberger.com/wp-content/uploads/2013/02/ViralityB.pdf).
- El Digital News Report 2025 de Reuters Institute reporta 36% de confianza general en noticias para Chile y 37% que comparte noticias por redes, mensajería o email. Son resultados de esa edición y muestra, no un pronóstico de alcance para DNR. Refuerzan la importancia de confianza y distribución. [Chile 2025](https://reutersinstitute.politics.ox.ac.uk/digital-news-report/2025/chile).
- Google describe Trending Now como detector de aumentos de búsquedas con contexto temporal. Esa señal puede complementar la cobertura de medios y Reddit. El volumen de titulares no equivale a interés de búsqueda. [Descripción oficial](https://blog.google/products-and-platforms/products/search/google-trends-trending-now-update/).
- El anuncio de la API de Trends consultado describe acceso alpha limitado y datos hasta dos días atrás. No debe confundirse ese producto con Trending Now ni suponerse acceso irrestricto o idoneidad para detección inmediata. Antes de integrar, comprobar disponibilidad actual para la cuenta y el acceso permitido para Chile. [Anuncio oficial](https://developers.google.com/search/blog/2025/07/trends-api).
- Vercel documenta alertas y pausa de producción en Spend Management para planes compatibles. Configurar un importe por sí solo no detiene el consumo y la pausa tiene demoras. Esto favorece apps estáticas y cálculo local cuando basten. [Documentación oficial](https://vercel.com/docs/spend-management).

## 6. Cambios al motor de oportunidades

### Descubrimiento y verificación

Separar generación amplia de evaluación. Agrupar noticias del mismo evento y generar alternativas de análisis, herramienta práctica y experiencia interactiva. Después comprobar la fuente, la regla o el dato necesario para cada finalista. Enviar como máximo tres oportunidades sigue siendo razonable; reducir a una cuando solo haya una buena.

La trazabilidad debe ser verificable por código: el título y enlace detonantes tienen que corresponder a un artículo ingerido. Hoy el prompt lo exige, pero el filtro de salida no comprueba pertenencia al conjunto original. Que una URL sea HTTP(S) no demuestra que sea una fuente auténtica.

La validación de datos debe comprobar algo más que un HTTP 200: contenido correcto, variables disponibles, periodo, geografía, unidades, formato, licencia o condiciones de uso, y una muestra mínima utilizable. Registrar «propuesta», «localizada» y «verificada» como estados distintos. Las sugerencias prometedoras pero sin evidencia deben quedar como investigación pendiente.

### Ranking

Separar atención de la noticia, utilidad del producto y posibilidad de distribución. Reemplazar la aparente precisión del único puntaje de viralidad por dimensiones justificadas y una confianza explícita.

Gates previos: detonante real; fuente o regla verificada; alcance seguro y publicable; MVP dentro del presupuesto disponible. Una falla grave de evidencia no se compensa con popularidad.

Ranking inicial propuesto, con todas las dimensiones entre 0 y 5:

| Dimensión | Peso inicial | Evidencia que pedir |
|---|---:|---|
| Necesidad o utilidad | 25% | Tarea y audiencia específicas |
| Atención y oportunidad temporal | 20% | Señales observadas, timestamps y corroboración |
| Razón para compartir | 15% | Qué se comparte y a quién le sirve |
| Diferenciación | 15% | Alternativas existentes y mejora concreta |
| Tiempo hasta publicar | 15% | Trabajo total estimado y dependencias |
| Valor después de la noticia | 10% | Reutilización o mantenimiento razonable |

Es una rúbrica inicial, no un modelo predictivo validado. Guardar razones, incertidumbre y descartes; ajustarla con publicaciones reales. Cuando falte una señal, registrar ausencia en lugar de inventar una cifra. Normalizar señales dentro de cada fuente: comentarios de Reddit y cobertura periodística no tienen la misma unidad.

### Schema propuesto

Agregar `audience`, `user_need`, `user_action`, `product_type`, `inputs`, `output`, `share_reason`, `distribution_channel`, `existing_alternatives`, `evidence_status`, `verified_sources`, `hypotheses_to_test`, `attention_signals`, `confidence`, `build_hours`, `verification_hours`, `distribution_hours`, `maintenance_cost`, `expires_at` y `rejection_reason` cuando corresponda.

Separar `product_type` de `implementation_stack`: calculadora es un producto; Next.js o Streamlit es una implementación. Incluir rutas sin backend o sin IA. Conservar compatibilidad con el historial y el formateador de Telegram mediante valores predeterminados o una migración explícita.

## 7. Captación y vigencia

- Integrar Google Trends después de ampliar criterios y verificación. Su valor es corroborar demanda, descubrir preguntas y observar evolución; no sustituir el juicio editorial.
- Mantener RSS y Reddit con métricas de disponibilidad. Que falle una fuente no debe detener todas, pero sí quedar visible que la cobertura fue parcial.
- Registrar eventos y series temporales: primera detección, última actualización, fuentes independientes, señales y agotamiento. La cantidad de republicaciones no equivale a corroboración independiente.
- Agregar un calendario de eventos previsibles con fuentes oficiales: cambios con fecha de entrada en vigor, plazos, torneos y anuncios programados. Preparar un prototipo antes del pico puede ser más viable que empezar al día siguiente.
- El cron diario actual es una buena base. Solo aumentar frecuencia si se demuestra que las oportunidades llegan tarde; se puede probar ingesta barata cada pocas horas y evaluación adicional solo ante cambios importantes, sin convertirlo en requisito inicial.
- Separar ventana de noticia, vigencia de la regla y vida útil del producto. Un anuncio y una norma vigente merecen tratamientos distintos.
- Revisar deduplicación: actualmente excluir una noticia reciente antes de generar alternativas puede impedir un segundo producto útil con el mismo detonante. Distinguir evento, necesidad, ángulo, producto y estado de publicación.
- Alinear el prompt con `--days` y `--cooldown-days`: el texto todavía presenta una ventana fija de 24 horas y no siempre refleja la ventana usada realmente.

## 8. Producción y Vercel

Mantener DNR como radar y construir cada herramienta con un alcance explícito. Compartir componentes y plantillas para calculadoras, comparadores, guías, simuladores y tarjetas de resultados reduce el tiempo de producción.

Vercel es una opción razonable para frontends web. Usar HTML/JavaScript o React/Next.js con datos estáticos versionados cuando sea suficiente. Python puede preparar el dataset previamente; no necesita ejecutarse por visitante. Reservar servicios de backend para necesidades reales. Streamlit sigue siendo una opción válida cuando acelere una pieza analítica.

El presupuesto de tiempo debe incluir evidencia, diseño, pruebas de fórmulas y casos límite, experiencia móvil, despliegue, texto de publicación y verificación de enlaces. «Menos de cuatro horas» no debe significar solo que un prototipo arranca.

Si una noticia exige OCR extenso, geocodificación, modelos nuevos o múltiples fuentes inestables, reducir el alcance, cambiar de formato o descartarla. La IA puede ayudar a desarrollar y preparar contenido; no hace falta poner una llamada LLM por usuario en una herramienta que se resuelve con reglas.

Cada app publicada necesita propietario, fuente, fecha, versión de reglas y criterio de vencimiento. Si el dato deja de estar vigente, mostrar estado desactualizado o archivar la herramienta. Preparar caché y un presupuesto de infraestructura acorde al posible tráfico.

## 9. Observabilidad y fiabilidad pendientes

Hallazgos del flujo actual que conviene corregir al evolucionarlo:

1. **Fallos que parecen éxito:** `main.py` captura excepciones del evaluador y termina con `return`. El proceso puede salir con código 0 y no activar el paso `if: failure()` del workflow. Diferenciar fallo técnico y resultado válido sin oportunidades.
2. **Historial y envío mezclados:** las oportunidades se guardan antes del despacho. Si Telegram falla, quedan registradas y pueden quedar excluidas en la siguiente corrida. Registrar estado de entrega y reintentar sin duplicar envíos.
3. **Simulación con efectos:** `--dry-run` simula Telegram, pero sigue guardando candidatos en el historial. Dar a la simulación una semántica clara y aislar sus efectos del seguimiento productivo.
4. **Respuesta inválida como vacío:** si no se obtiene una estructura usable, el evaluador puede devolver cero oportunidades. Registrar ese caso como error de evaluación, no como ausencia de oportunidades.
5. **Parámetros dispersos:** los umbrales y límites aparecen en YAML, defaults de funciones y prompt; `main.py` no conecta todos esos valores a la evaluación. Unificar configuración efectiva y registrarla por corrida.
6. **Fallos de Telegram:** se registran resultados fallidos, pero el flujo no los convierte necesariamente en estado de fallo operativo. Registrar éxito parcial, reintentos y entrega final.
7. **Ejecuciones solapadas:** incorporar control de concurrencia o idempotencia para evitar notificaciones duplicadas y conflictos del historial si coinciden un disparo diario y uno manual.
8. **Seguimiento del cron:** la programación está resuelta; agregar un heartbeat permitiría distinguir «no empezó la corrida» de «empezó y falló». Una alerta interna no detecta que nunca se inició el proceso.

## 10. Métricas para aprender

Objetivo operativo recomendado: aumentar la cantidad de personas que obtienen un resultado útil y lo comparten, por hora de trabajo, conservando fuentes y cálculos confiables. Medir aparte el beneficio profesional: visitas al perfil, contactos pertinentes y conversaciones generadas.

| Etapa | Qué registrar |
|---|---|
| Descubrimiento | Cobertura de fuentes, candidatos, edad del detonante, señales disponibles |
| Selección | Aceptados, descartados, razón, incertidumbre y tiempo invertido |
| Producción | Horas reales hasta publicar, bloqueos y mantenimiento |
| Adquisición | Impresiones si el canal las ofrece, clics etiquetados y sesiones de llegada |
| Uso | Inicio y finalización de tarea, tiempo hasta resultado, abandonos |
| Difusión | Clic en compartir/copiar y visitas referidas cuando sean medibles |
| Calidad | Correcciones, errores de cálculo y reportes de datos vencidos |
| Resultado profesional | Contactos relevantes y oportunidades atribuibles con cautela |

Un clic en compartir no prueba una publicación ni una nueva visita. No inferir viralidad a partir de los puntajes del LLM ni confundir impresiones con uso. Parte de la mensajería privada no deja trazabilidad suficiente para atribución.

Experimento inicial de cuatro semanas: publicar 4–6 piezas que puedas verificar y mantener, cubriendo al menos dos formatos. Registrar el canal, la audiencia y el esfuerzo. Comparar finalización, uso y difusión por hora; no atribuir diferencias solo al formato si cambiaron tema, momento y distribución. Con una muestra pequeña, el resultado será aprendizaje direccional, no evidencia causal.

## 11. Prioridades

| Orden | Mejora | Resultado esperado | Tamaño relativo |
|---|---|---|---|
| P0 | Ampliar misión, prompt y schema a tareas y productos digitales | Más alternativas relevantes por noticia | Medio |
| P0 | Separar hipótesis y hechos; validar detonante y fuente mínima | Candidatos que se puedan defender y construir | Medio |
| P0 | Estados de evaluación, entrega y publicación; corregir fallos silenciosos | Saber qué pasó realmente en cada corrida | Medio |
| P1 | Nueva tarjeta Telegram: audiencia, tarea, MVP, evidencia y distribución | Poder elegir una oportunidad con rapidez | Pequeño |
| P1 | Plantilla reutilizable y primera herramienta publicada con medición | Completar el circuito hasta uso real | Medio |
| P1 | Ranking por dimensiones y archivo de descartes | Aprender por qué se selecciona cada idea | Medio |
| P1 | Google Trends y métricas temporales según acceso disponible | Corroborar demanda y vigencia | Medio |
| P2 | Calendario, seguimiento de eventos y mejor deduplicación | Anticipación y nuevas versiones útiles | Medio |
| P2 | Portafolio público, mantenimiento y reutilización | Acumular audiencia y activos | Medio |
| P3 | Generación más automática y nuevas fuentes complejas | Escalar patrones que ya rindan | Grande |

La primera iteración debería terminar con una herramienta real, evidencia verificada, distribución concreta y métricas básicas. Cambiar el prompt sin cerrar ese circuito aumentaría el inventario de ideas, pero no demostraría mayor alcance.
