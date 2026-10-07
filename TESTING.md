# Plan y ejecución de pruebas

La suite cubre la lógica de autenticación, usuarios, perfiles, proveedores y análisis de incidentes. Las aserciones verifican decisiones de negocio y no detalles internos de serialización HTTP o del framework.

## Plan definido antes de implementar los tests

### Autenticación

| Endpoint o función | Camino feliz | Caso límite | Modo de fallo | Motivo |
|---|---|---|---|---|
| `POST /auth/login` | Credenciales válidas generan token bearer | Contraseña vacía | Email inexistente o contraseña incorrecta | Protege el acceso y evita aceptar entradas incompletas |
| `GET /auth/me` | Devuelve el usuario autenticado y su perfil | Usuario sin perfil | Falta de token o token inválido | Verifica identidad y acceso protegido |
| `POST /auth/forgot-password` | Solicitud para una cuenta existente envía recuperación | Email desconocido mantiene respuesta genérica | Email malformado o proveedor no invocado para cuenta inexistente | Evita enumeración de cuentas |
| `POST /auth/reset-password` | Token válido cambia la contraseña | Token de un solo uso después del cambio | Token expirado, malformado o con huella antigua | Evita reutilización y cambios no autorizados |
| `POST /auth/change-password` | Contraseña actual correcta permite cambio | Nueva contraseña en el mínimo permitido | Contraseña actual incorrecta o request inválido | Protege la modificación de credenciales |
| `hash_password` / `verify_password` | Hash verifica la contraseña original | Contraseña de longitud mínima | Contraseña equivocada o hash inválido | Asegura la lógica criptográfica básica |
| `create_access_token` | Incluye sujeto y expiración | Expiración personalizada | Token expirado rechazado | Cubre la regresión de expiración reportada |

### Backoffice y operaciones

| Endpoint | Camino feliz | Caso límite | Modo de fallo |
|---|---|---|---|
| Usuarios | Crear y listar usuario | Email duplicado | Acceso a otro usuario no autorizado |
| Perfiles | Crear/actualizar perfil | Campos opcionales o vacíos | Teléfono inválido |
| Proveedores | Filtrar, crear, actualizar y eliminar | Filtros vacíos o valor mínimo válido | País/moneda inválidos o proveedor inexistente |
| Incidentes | Analizar CSV válido y exportar resultados | Archivo vacío | Extensión incorrecta, CSV inválido o falta de autenticación |

Los dos grupos de backoffice priorizados para API-042 son **proveedores** e **incidentes**. Ambos tienen camino feliz, límites y fallos en `tests/test_suppliers.py` y `tests/test_incidents.py`; sus módulos alcanzan 92% y 82% respectivamente.

## Backend

Desde la raíz del repositorio:

```bash
cd services/api
uv sync
cd ../..
uv run pytest --cov=services/api --cov-report=term-missing
```

También funciona desde `services/api` con `uv run pytest --cov=. --cov-report=term-missing`.

Resultado histórico de la suite anterior: **20 tests passed** y **76% de cobertura total**. Esas cifras ya no representan la suite actual.

> El resultado anterior quedó obsoleto al añadirse la integración SQLModel. La suite vigente incluye pruebas para registro/roles, health/readiness, CORS, recuperación de contraseña e inventario.

### Entorno aislado y ejecución vigente

`tests/conftest.py` configura TinyDB y SQLite bajo un directorio temporal del sistema; no utiliza ni modifica `services/api/data/auth.json`. Desde la raíz:

```bash
uv lock --check
uv lock --check --project services/api
uv sync --locked --no-install-project
uv run --locked pytest -q --cov=services/api --cov=services/routers/inventory --cov-report=term-missing
```

La prueba de concurrencia real usa `SELECT FOR UPDATE`, por lo que solo se ejecuta cuando `BRASALAND_TEST_DATABASE_URL` apunta a PostgreSQL de pruebas. Con SQLite queda marcada como omitida; otro test comprueba que la consulta PostgreSQL contiene el lock.

El conjunto registrado incluye auth, usuarios/perfiles, proveedores, incidentes, inventario y healthchecks. No se afirma cobertura de un test si no aparece en el reporte ejecutado.

Para actualizar específicamente la cobertura del backoffice:

```bash
uv run pytest --cov=services/api/routes/suppliers.py --cov=services/api/main.py --cov-report=term-missing
```

También se puede usar `pytest` si el entorno ya tiene las dependencias instaladas.

La suite incluye, para los endpoints principales, camino feliz, límites y fallos: credenciales inválidas, campos vacíos, usuarios duplicados, tokens expirados o reutilizados, autorización, filtros inválidos, proveedores inexistentes, payloads inconsistentes y archivos CSV vacíos o con extensión incorrecta.

## Revisión asistida por IA y ajustes encontrados

Se revisaron casos adicionales de tokens expirados, tokens de recuperación de un solo uso, enumeración de cuentas, campos vacíos, usuarios duplicados, autorización entre usuarios y moneda inconsistente. El boilerplate generado fue revisado contra las implementaciones reales antes de incorporarlo.

Durante la revisión se corrigió el fixture de pruebas para construir `ProfileCreate` (en lugar de pasar un diccionario al store) y se ajustó el CSV de prueba al esquema real de incidentes. No se requirió cambiar lógica de producción: las pruebas no descubrieron un bug funcional.

## Frontend — Jest

Aunque el frontend es JavaScript estático y no TypeScript/Next.js, sí contiene helpers reutilizables del backoffice. FE-019 cubre tres funciones en `uis/backoffice/utils.js`:

- `parseApiError`: interpreta detalles string, objetos y payloads ausentes.
- `normalizeApiBase`: limpia URLs y aplica un valor por defecto.
- `formatFileSize`: presenta tamaños de archivos y rechaza valores inválidos.

Ejecutar independientemente desde la raíz:

```bash
npm install
npm test
```

El runner descubre los tests en `uis/backoffice/__tests__` y recoge cobertura de todos los módulos `uis/backoffice/**/*.js` (no solo helpers). Los módulos sin tests aparecen como 0% en el reporte. Ejecutar:

```bash
npm ci
npm test -- --runInBand
```

La validación de sintaxis JS se puede ejecutar con `find uis -name '*.js' -print0 | xargs -0 -n1 node --check`.

## Configuración del backend para pruebas

- La app no crea tablas al importarse. Inicializa una base configurada con `cd services/api && uv run python init_db.py`.
- `/health` comprueba liveness del proceso; `/health/ready` verifica la conexión SQL con `SELECT 1`.
- No es necesario configurar credenciales de email para pytest: el fixture deshabilita el envío real y usa almacenamiento temporal.
- El smoke concurrente PostgreSQL requiere `BRASALAND_TEST_DATABASE_URL`; no reutilices la base de producción para tests.
