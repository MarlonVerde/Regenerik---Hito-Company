# Carpeta `uis`

Esta carpeta contiene **todas las interfaces de usuario** relacionadas con la compañía para el proyecto transversal de AI Engineering (por ejemplo: aplicaciones web, dashboards internos, portales de clientes, apps de Streamlit/Gradio, etc.).

Cada subcarpeta dentro de `uis/` debe corresponder a **una interfaz de usuario concreta** (por ejemplo `website`, `backoffice`) e incluir su propia documentación técnica y funcional.


## Interfaces implementadas

### `web`

Interfaz web para análisis de incidencias operativas:
- Carga de CSV (selector o drag and drop).
- Envío a `POST /api/incidents/analyze`.
- Visualización de métricas, desgloses e índice de satisfacción.
- Descarga de resultados desde `GET /api/incidents/results/export`.

Ubicación:
- `uis/web/index.html`
