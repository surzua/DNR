# DNR: estrategia y roadmap vigente

**Actualización:** 26 de octubre de 2026.

**Estado:** las seis etapas están implementadas en DNR v0.2 y cubiertas por validación determinista. La revisión editorial de oportunidades concretas sigue siendo manual.

**Próximo paso:** revisar los briefs reales antes de construirlos y activar Google Trends solo después de comprobar su disponibilidad en el entorno.

Este documento reemplaza el análisis estratégico y las prioridades anteriores. Es la referencia del roadmap a partir de este punto. Actualizarlo no modifica el pipeline ni significa que las mejoras ya estén implementadas.

## 1. Objetivo y límites acordados

**Misión:** detectar noticias y conversaciones relevantes, inicialmente en Chile, y convertirlas en propuestas de productos digitales con potencial de viralidad, información comprobable y oportunidades concretas de aprendizaje al construirlos.

La pregunta que guía al radar es: **«¿Qué podría querer hacer, entender, resolver o experimentar alguien a raíz de esta noticia, y qué podemos construir para responder a eso?»**.

La solución puede ser una app web que viva en Vercel, una calculadora, un simulador, un juego, un explicador, una utilidad para archivos o un recurso descargable. Data Science sigue siendo una capacidad disponible, pero no es un requisito. Tampoco lo son un dataset grande, un backend o una llamada a un LLM.

Las tres condiciones de selección son:

1. **Potencial de difusión:** una audiencia concreta tiene una razón entendible para usar y compartir el producto. Utilidad práctica, curiosidad, entretenimiento, coordinación y expresión personal son vías posibles.
2. **Honestidad:** las afirmaciones tienen respaldo identificable; supuestos, escenarios y comprobaciones pendientes se muestran como tales. Una conclusión no se elige por lo llamativa que resulte.
3. **Aprendizaje:** el creador puede elegir, investigar, programar, comprender y validar la solución manualmente. Cada propuesta explica qué habilidad permitiría practicar.

La viralidad es la finalidad, no una promesa ni una propiedad comprobada por un puntaje del modelo. Este roadmap mejora la selección y el diseño de oportunidades; sus verificaciones internas no demuestran alcance real.

### Responsabilidades y fuera de alcance

| DNR automatiza | El creador realiza manualmente |
|---|---|
| Recolección de noticias y señales públicas | Elección de la oportunidad |
| Preparación y comparación de propuestas | Investigación y comprobación editorial final |
| Comprobaciones técnicas acotadas y trazabilidad | Diseño, desarrollo y comprensión del producto |
| Brief y alerta privada de oportunidad | Validación, despliegue y publicación |
| Historial de propuestas y motivos de descarte | Seguimiento posterior, si decide hacerlo por su cuenta |

Quedan fuera de este roadmap:

- Desarrollo autónomo de productos, generación automática de repositorios, agentes que construyen apps o despliegues automáticos desde el radar.
- Automatización de publicaciones, mensajes a terceros o campañas de distribución.
- Seguimiento de productos publicados, dashboards de resultados, vistas, likes, visitas, conversiones y atribución profesional.
- Cuotas de publicación o experimentos que exijan publicar piezas para cerrar una etapa.
- Más trabajo de programación del cron: la ejecución diaria externa se considera resuelta.

Diseñar un motivo para compartir, un resultado exportable o una vista previa sí forma parte de la oportunidad. Publicarlo o medir su rendimiento no es una función nueva de DNR.

El código ya incluye comandos opcionales de publicación y métricas. Este roadmap no exige usarlos, ampliarlos ni borrarlos; su existencia no convierte esas funciones en trabajo pendiente.

## 2. Punto de partida confirmado

La revisión actual considera código, configuración y 65 registros históricos: 34 gráficos, 29 apps Streamlit y 2 análisis predictivos/optimización. Es una descripción del historial acumulado, no una evaluación de calidad ni una prueba de oportunidades perdidas.

| Área | Qué existe | Qué falta o debe corregirse |
|---|---|---|
| Operación | RSS, Reddit, evaluación estructurada, Telegram, historial y ejecución diaria externa | Mantener esta base; no replantear el cron |
| Producto | Audiencia, necesidad, acción, entradas, salida y motivo para compartir | Eliminar restricciones antiguas que siguen forzando el enfoque analítico |
| Formatos | product_type incluye calculadoras, comparadores, guías y planificadores | suggested_deliverable solo admite gráfico, app Streamlit y análisis predictivo/optimización; faltan juegos y utilidades |
| Prompt | Separa known_facts, hypotheses_to_test y verification_plan | Aún exige ángulo cuantitativo nuevo en temas recurrentes y planes de menos de cuatro horas |
| Fuentes | Tipos orientados a APIs, datasets, portales, Wikipedia y scraping | Representar reglas oficiales, reglamentos, documentación y otras evidencias pertinentes |
| Verificación | Detonante perteneciente a la ingesta y disponibilidad HTTP de fuentes | HTTP y tipo de contenido no comprueban respaldo editorial; «Verificada» es una etiqueta ambigua |
| Contexto | La ingesta conserva fechas y resúmenes | El fragmento enviado al modelo recorta el resumen a 180 caracteres y omite la fecha |
| Selección | Rúbrica por dimensiones, confianza y descartes deterministas | Justificar puntajes y contemplar valor lúdico, aprendizaje y esfuerzo manual |
| Novedad | Exclusión por título/URL de detonantes recientes | No bloquear otro producto útil solo por partir de la misma noticia |
| Búsquedas | Archivo trends_client.py | Placeholder con NotImplementedError; no aporta señales al pipeline |

Los problemas operativos del análisis anterior no se arrastran como pendientes sin revisar el código. Actualmente existen códigos de salida para errores, dry-run sin persistencia del historial, estado/reintento de entrega a Telegram y concurrencia en el workflow. Esto no garantiza entrega exactamente una vez, pero evita proponer de nuevo esas capacidades como si no existieran.

## 3. Familias de oportunidad abiertas

Los ejemplos ilustran tipos de producto. No afirman que los temas sean tendencia hoy ni que sus fuentes ya estén comprobadas.

| Detonante | Producto posible | Razón para compartir | Evidencia o límite necesario |
|---|---|---|---|
| Cambio de tarifa o precio | Calculadora de escenarios personales | Avisar a familiares o comparar situaciones | Fórmula, componentes, unidades y vigencia |
| Torneo o decisión deportiva | Simulador de clasificación o sanciones | Debatir combinaciones con amigos | Tabla y reglamento; escenario hipotético separado del oficial |
| Anuncio cultural o evento | Planificador o calendario descargable | Coordinar una salida | Fechas, horarios y restricciones oficiales |
| Debate sobre probabilidades | Juego o desafío educativo | Retar a otra persona | Mecánica reproducible y explicación correcta |
| Cambio en una plataforma digital | Conversor, checklist o utilidad de migración | Ahorrarle trabajo a un colega | Documentación vigente y capacidades implementables |
| Información compleja | Explicador o explorador interactivo | Ayudar a comprender o mostrar un hallazgo | Fuente, escala, contexto y límites de interpretación |
| Nuevo trámite o beneficio | Guía interactiva de próximos pasos | Ayudar a alguien a actuar | Requisitos oficiales y estado anunciado/aprobado/vigente |
| Conversación cultural | Generador creativo o experiencia personalizable | Mostrar una creación o invitar a probar | Separar ficción de información factual; sin diagnósticos ni percentiles inventados |

No se fijan porcentajes por familia ni se exige una app en cada alerta. Un recurso pequeño puede ser mejor oportunidad que un proyecto grande. Una idea lúdica no se descarta solo por no resolver un trámite o producir un análisis cuantitativo.

## 4. Roadmap de seis etapas

Las etapas describen cambios al radar, no una cadena de fabricación y publicación de productos. La validación queda registrada con pruebas de contrato, historial, notificación, descubrimiento y casos revisados; cambiar un prompt no basta por sí solo.

| Etapa | Prioridad y dependencia | Entregable | Criterio de cierre |
|---|---|---|---|
| 1. Completar la apertura del producto | P0; completada | Esquema, prompt, filtros, historial y Telegram coherentes | Distintas familias se representan sin forzarlas a Data Science o Streamlit; historial anterior legible |
| 2. Fortalecer la evidencia | P0; completada | Separación entre acceso técnico, respaldo de afirmaciones y revisión pendiente | Ninguna afirmación crítica aparece validada solo porque una URL responde |
| 3. Mejorar el descubrimiento | P1; completada | Contexto temporal, eventos, cobertura temática más amplia y señales de búsqueda | Cada señal tiene procedencia y fecha; ausencias y fallos parciales visibles |
| 4. Diseñar el motivo para compartir | P1; completada | Interacción, resultado compartible y razón concreta de difusión | Se explica quién compartiría qué, con quién y para qué |
| 5. Preparar briefs para aprender construyendo | P1; completada | Alcance manual, habilidad, dificultad, dependencias y casos de validación | El creador entiende qué construir, qué aprenderá y cuáles son los límites antes de programar |
| 6. Afinar el criterio con ejemplos revisados | P2; completada | Casos revisados y comprobaciones de regresión del radar | Los cambios no reintroducen resultados inventados, formatos forzados o recomendaciones repetitivas |

### Etapa 1. Completar la apertura del producto

**Cambios:**

- Separar tipo de producto, formato de entrega y tecnología. Calculadora describe el producto; app web el formato; React, Next.js y Streamlit son opciones de implementación.
- Ampliar familias con juegos/desafíos, utilidades para archivos y recursos descargables. Evitar que otro campo obligatorio vuelva a restringirlas.
- Eliminar la obligación de un ángulo cuantitativo o una conclusión contraintuitiva. Pedir una necesidad o experiencia concreta, una interacción y una diferencia defendible.
- Admitir evidencia pertinente al producto: regla, reglamento, documentación o mecánica reproducible donde no se necesita un dataset. Mantener la trazabilidad del detonante.
- Alinear prompt, modelos, selección, persistencia y Telegram. Permitir compatibilidad de registros antiguos sin aceptar campos genéricos como suficientes para propuestas nuevas.
- Revisar utilidad para reconocer valor educativo, lúdico y de coordinación, además del práctico.

**Validación:** casos de calculadora, simulador, juego, utilidad y descargable sin reclasificarlos como Streamlit ni exigir análisis artificiales. Verificar carga y representación del historial antiguo.

**Archivos principales:** src/analysis/opportunity_eval.py, src/analysis/prompt_templates.py, src/storage/history_manager.py, src/notifiers/telegram_bot.py y pruebas relacionadas.

### Etapa 2. Fortalecer la evidencia

**Cambios:**

- Separar resultado HTTP y respaldo editorial. Usar descripciones inequívocas como «URL accesible; contenido pendiente de revisión». No elevar automáticamente la confianza editorial.
- Relacionar cada afirmación relevante con su fuente y ubicación cuando estén disponibles. Registrar documento o fragmento revisado, fecha, vigencia y comprobaciones pendientes. No inventar citas o extractos no consultados.
- Distinguir «la noticia reporta» de una afirmación contrastada con la fuente primaria. Si solo se leyó un titular o resumen, conservar ese límite.
- Separar hechos reportados, hechos contrastados, supuestos, hipótesis y escenarios. Un cálculo pendiente nunca se describe como hallazgo obtenido.
- Identificar los respaldos de todas las reglas o datos críticos de la propuesta. Una única URL accesible no valida el conjunto.
- Admitir ideas prometedoras pendientes de comprobación, claramente diferenciadas de las listas para construir. Las afirmaciones contradichas no se promueven como oportunidades válidas.
- Mantener comprobaciones acotadas y consultar contenido cuando sea viable, sin exigir fact-checking universal ni sustituir la revisión humana. Un bloqueo de acceso indica incertidumbre, no falsedad.
- Conservar supuestos, condición hipotética y fecha relevante al diseñar una salida compartible.

**Validación:** casos con HTTP 200 sin información pertinente, respaldo parcial, regla vencida, fuente inaccesible y escenario hipotético. Ninguno obtiene una etiqueta editorial de verificación injustificada. En juegos o experiencias creativas se comprueban el detonante y las afirmaciones/mecánica que efectivamente se presentan.

**Archivos principales:** src/analysis/source_verification.py, modelos y prompt del evaluador, historial, Telegram, configuración y pruebas. Migrar estados sin atribuir revisión editorial a registros antiguos.

### Etapa 3. Mejorar el descubrimiento

**Cambios:**

- Incluir fechas y procedencia en el contexto del modelo. Distinguir publicación, primera detección y actualización del evento; una fecha faltante no acredita frescura.
- Dar más contexto a finalistas cuando sea necesario y accesible, sin fundamentar toda interpretación en 180 caracteres. Registrar si solo existe resumen.
- Ampliar cobertura hacia tecnología, cultura, deportes, consumo y tareas cotidianas; elegir fuentes por su aporte, sin acumular feeds redundantes.
- Agrupar artículos por evento y distinguir cobertura repetida de corroboración independiente.
- Comparar evento, necesidad y producto para deduplicar. Permitir alternativas sustancialmente distintas sin repetir la misma propuesta con otro título.
- Comprobar disponibilidad, campos y condiciones del RSS/exportación de Google Trends para Chile antes de integrarlo. No depender de acceso a una API privada o restringida.
- Conservar procedencia, hora y limitaciones de cada señal. No convertir intervalos de búsquedas en cifras exactas ni equiparar comentarios de Reddit con búsquedas.
- Admitir eventos previsibles con fecha y fuente, como plazos o torneos, para identificar oportunidades con tiempo de aprender y construir antes del pico de atención.

**Validación:** ausencia de Trends sin caída del radar, señal antigua, fuentes duplicadas, contexto sin fecha y dos productos distintos para el mismo evento. Una tendencia indica interés observado, no la verdad de una afirmación.

**Archivos principales:** src/ingestion/, config/sources.yaml, src/storage/history_manager.py, src/analysis/prompt_templates.py, main.py y pruebas.

### Etapa 4. Diseñar el motivo para compartir

**Cambios:**

- Explicar quién usaría el producto, qué obtiene, con quién lo compartiría y para qué. «Es interesante y viral» no basta.
- Describir primera interacción y resultado temprano. Evitar registro, formularios largos o pasos sin valor cuando no sean necesarios.
- Elegir un mecanismo acorde al producto: ayudar, coordinar, desafiar, comparar escenarios o expresar una creación. No imponer tarjetas compartibles a todas las familias.
- Proponer cuando aporte un enlace reproducible, imagen, archivo o desafío. La salida no expone datos personales ni pierde supuestos relevantes.
- Contrastar alternativas existentes. Si se desconocen, indicarlo como revisión pendiente; no afirmar que la idea es única sin comprobarlo.
- Separar atención de la noticia, atractivo del producto y motivo para compartir en el ranking. Los puntajes son juicios explicados, no probabilidades de viralidad.

**Validación:** una revisión humana completa «esta persona comparte este resultado con estas otras personas para este propósito». Si la razón solo es popularidad de la noticia, reformular o bajar prioridad. No se requieren publicaciones ni métricas sociales.

**Archivos principales:** evaluador, prompt, historial y tarjeta Telegram. No se crean campañas ni funciones de publicación.

### Etapa 5. Preparar briefs para aprender construyendo

**Contenido mínimo del brief:**

1. Audiencia, detonante, producto, interacción y resultado.
2. Evidencia disponible, supuestos, revisión pendiente y vigencia.
3. Versión mínima, límites explícitos y ampliación opcional separada.
4. Habilidad a practicar, conocimientos previos y dificultad explicada.
5. Pasos manuales de investigación, diseño, implementación y validación.
6. Dependencias técnicas y casos para comprobar cálculos, reglas o mecánica.

**Cambios:**

- Reemplazar el límite universal de cuatro horas por alcances orientativos: prototipo breve, proyecto de varias sesiones o idea demasiado grande para su ventana. Estimar investigación, aprendizaje y validación, sin promesas de tiempo.
- Separar dificultad técnica y esfuerzo de verificación: una interfaz pequeña puede requerir mucha investigación.
- Usar aprendizaje como criterio explícito de elección o desempate entre buenas oportunidades. No compensa evidencia insuficiente ni falta de atractivo. Si se desconocen las habilidades actuales, formular la recomendación de aprendizaje de forma condicional.
- Sugerir tecnología por necesidad. HTML/JavaScript o React con Vite pueden bastar para cálculo local; Next.js, backend, base de datos e IA requieren una razón concreta. Streamlit sigue disponible para casos adecuados.
- Mantener un brief breve en Telegram y conservar el detalle necesario en el historial. No generar código del producto, repositorios, despliegues ni automatizaciones de desarrollo.

**Validación:** el creador explica qué construirá primero, qué aprenderá, qué deja fuera y cómo comprobará que funciona. Revisar el brief basta; terminar o publicar la app no es requisito de cierre de esta etapa del radar.

**Archivos principales:** modelos y prompt del evaluador, historial, Telegram y documentación de uso. Los campos nuevos se definen al implementar; esta sección no afirma que ya existan.

### Etapa 6. Afinar el criterio con ejemplos revisados

**Cambios:**

- Consolidar un conjunto pequeño de noticias históricas con propuestas buenas, débiles y ambiguas revisadas manualmente. Empezar con casos de las etapas 1 y 2 y ampliarlos al terminar las demás.
- Incluir formatos distintos, poco contexto, URLs accesibles pero irrelevantes, hipótesis confundidas con hechos, demanda no observada y alcances mayores que la ventana de atención.
- Documentar criterios y razones aceptables, no un único texto correcto. Una noticia puede admitir varias buenas soluciones.
- Usar pruebas deterministas para trazabilidad, estados de evidencia, compatibilidad, filtros y representación. Revisar manualmente la calidad de ideas; un LLM de apoyo no es juez único de sus propias propuestas.
- Comparar cambios contra estos casos sin contactar servicios productivos, publicar piezas ni registrar rendimiento. Consultas reales opcionales deben ser explícitas y no enviar alertas durante la revisión.

**Validación:** no aparecen afirmaciones sin respaldo presentadas como comprobadas, familias forzadas a formatos antiguos, razones genéricas de difusión o repeticiones evitables. El conjunto cubre incertidumbre y diversidad. Aprobarlo no demuestra viralidad real.

**Archivos principales:** tests/, casos de revisión y documentación. Las pruebas cubren comportamientos relevantes; no replican el texto del prompt.

## 5. Reglas transversales de selección

- **La evidencia no se compensa con popularidad.** Una idea pendiente puede proponerse como investigación; una afirmación inventada no obtiene aprobación por su gancho.
- **El producto ofrece una razón para usarlo.** Práctica, educativa, lúdica o creativa; no basta con resumir una noticia.
- **La difusión tiene un motivo concreto.** Una etiqueta «viralidad 9/10» no lo sustituye.
- **La oportunidad temporal sostiene el alcance.** Si el desarrollo manual excede la ventana de interés, reducir el producto, anticiparlo o elegir otra idea.
- **No hay cuota de alertas.** Hasta tres propuestas sigue siendo un límite razonable; una o ninguna es válido.
- **La selección final es humana.** El radar explica diferencias, incertidumbre y aprendizaje; no decide autónomamente qué se construye.
- **Las señales de atención son entradas del radar.** Observar búsquedas o conversación pública para descubrir oportunidades es distinto de seguir productos publicados, que queda fuera del alcance.

No se añade de inmediato una fórmula nueva de ranking. Primero se corrigen restricciones y significado de la evidencia; después se ajustan dimensiones con casos revisados, sin presentar pesos como un modelo predictivo validado.

## 6. Primera iteración: etapas 1 y 2

El primer trabajo de implementación debe producir:

- [x] Contrato de producto abierto y compatible con el historial antiguo.
- [x] Prompt sin obligación de análisis cuantitativo, conclusión contraintuitiva o formato Streamlit.
- [x] Separación visible entre acceso HTTP y respaldo editorial, también en registros heredados.
- [x] Hechos reportados, supuestos e hipótesis sin anticipar resultados.
- [x] Telegram e historial que conserven esas distinciones y las comprobaciones pendientes.
- [x] Casos históricos revisados de varias familias y de evidencia insuficiente.
- [x] Pruebas relevantes del contrato, filtros, persistencia y notificación afectados, sin envíos reales ni cambios al historial productivo durante la validación.
- [x] README, resumen y especificación alineados en los puntos afectados, distinguiendo funciones implementadas y siguientes etapas.

El resultado esperado es una propuesta que permita decidir: **«esta interacción tiene una razón para compartirse, sé qué debo comprobar y entiendo qué aprenderé al construirla»**. No requiere generar una app, desplegarla, publicarla ni medir su difusión.

## 7. Referencias y límites de la evidencia externa

- [Berger y Milkman: What Makes Online Content Viral?](https://jonahberger.com/wp-content/uploads/2013/02/ViralityB.pdf). Investigación sobre difusión que vincula utilidad, interés, sorpresa y activación emocional con transmisión de contenido. Orienta hipótesis de diseño; no valida el potencial de una app concreta ni permite trasladar resultados automáticamente a Chile o a un canal actual.
- [Google Trends: explorar búsquedas en tendencia](https://support.google.com/trends/answer/3076011?hl=en). Documenta contexto temporal, volumen agrupado y exportación, incluido RSS. Comprobar disponibilidad para Chile antes de implementar; no asumir que todos los campos de la interfaz estén en el feed.
- [Vite en Vercel](https://vercel.com/docs/frameworks/frontend/vite) y [frontends en Vercel](https://vercel.com/docs/frameworks/frontend). Respaldan esa ruta técnica para apps web. No implican que todas las oportunidades necesiten ese stack ni que DNR deba automatizar despliegues.

Estas decisiones combinan antecedentes externos, revisión del repositorio y preferencias explícitas del creador. Son criterios de producto y trabajo; no resultados demostrados de viralidad.
