# Resumen del proyecto DNR v0.2

**Última revisión:** 26 de octubre de 2026

DNR es un radar de noticias y conversación pública chilena que prepara oportunidades para productos digitales. Su función es ayudar a decidir qué explorar o construir; no desarrolla, despliega ni publica esos productos.

## Flujo implementado

1. Recolecta RSS, Reddit, eventos previsibles configurados y, de forma opcional, el RSS público de Google Trends para Chile.
2. Conserva procedencia, publicación/evento, primera detección, actualización y limitaciones de señal. La cobertura relacionada se agrupa sin borrar fuentes.
3. Gemini genera una respuesta estructurada con producto, evidencia, interacción, motivo de difusión y brief de aprendizaje.
4. Los filtros validan trazabilidad del detonante, umbrales y duplicación por evento + producto + necesidad. Un mismo evento puede originar alternativas distintas.
5. La disponibilidad HTTP se registra separada de la evidencia editorial. El historial y Telegram muestran incertidumbre, comprobaciones pendientes y casos de validación.

## Resultado de una oportunidad

Cada propuesta conserva:

- audiencia, necesidad, primera interacción y resultado;
- producto, formato de entrega y tecnologías opcionales;
- hechos reportados/contrastados, supuestos, hipótesis, afirmaciones críticas y fuentes;
- circuito de difusión concreto y alternativas pendientes o revisadas;
- alcance mínimo, límites, aprendizaje, dependencias y casos para comprobarla.

Los estados editoriales son `Pendiente de revisión`, `Respaldo parcial` y `Lista para construir`. `accessible` solo describe una URL que respondió a la comprobación técnica.

## Estado y límites

Las seis etapas del roadmap están implementadas y ejercitadas por pruebas deterministas, incluidos casos revisados de formatos diversos e incertidumbre. Esto no prueba viralidad ni sustituye la investigación editorial final. La selección, construcción y publicación siguen siendo decisiones manuales del creador.

Consulta [README.md](../README.md) para uso local, [SYSTEM_SPEC.md](SYSTEM_SPEC.md) para el contrato técnico y [STRATEGY_REVIEW.md](STRATEGY_REVIEW.md) para los criterios y límites del producto.
