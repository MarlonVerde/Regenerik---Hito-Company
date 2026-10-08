# UI Web - Análisis de Incidencias

Interfaz de entrega para el flujo de análisis:

- Carga de CSV por selector o drag and drop.
- Envío a `POST /api/incidents/analyze`.
- Visualización de métricas, desgloses e índice de satisfacción.
- Descarga de resultados desde `GET /api/incidents/results/export`.

## Archivos

- `index.html`
- `app.js`
- `styles.css`

## Uso

1. Levanta la API en `services/api`.
2. Abre `uis/web/index.html` en el navegador.
3. Verifica que la URL de API sea `http://127.0.0.1:8000`.
