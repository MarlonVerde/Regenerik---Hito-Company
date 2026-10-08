# Carpeta `scripts`

Esta carpeta contiene **scripts auxiliares** del monorepo: automatizaciones de desarrollo, utilidades de mantenimiento, tareas repetitivas (setup, lint, migraciones, generación de datos, etc.) y tooling interno.

- **Propósito principal**: agrupar herramientas de soporte que no pertenecen a una app/agente/pipeline específico, pero facilitan el trabajo del equipo.
- **Recomendación**: documenta cada script (qué hace, parámetros, requisitos, ejemplos de uso) y procura que sean reproducibles (y seguros) en distintos entornos.

## Script de validación de incidencias

Archivo: `scripts/incidents_pipeline.py`

Objetivo:
- Validar registros de incidencias de un CSV.
- Detectar y contar registros incompletos o corruptos.
- Excluir inválidos del análisis principal.
- Generar métricas sobre registros válidos.

Entradas:
- CSV de incidencias con cabeceras.
- JSON de reglas con:
	- `required_fields`
	- `allowed_values` (por ejemplo: `status`, `category`)

Ejemplo de reglas:
- `data/raw/incidents_rules.example.json`

Uso:

```bash
python3 scripts/incidents_pipeline.py \
	--input data/raw/incidents_sample.csv \
	--rules data/raw/incidents_rules.example.json \
	--output-dir data/process/incidents_output
```

Salidas:
- `valid_records.csv`: registros válidos.
- `invalid_records.csv`: registros inválidos con motivo de error y número de fila.
- `summary.json`: resumen de totales, tasas de invalidez, desglose de errores y métricas de válidos.
