# Caching Report

## Contexto y metodo

Se agrego middleware de timing en backend para registrar por peticion:

- metodo
- path
- status
- latencia en ms

Formato de log: `METHOD /path -> status | X.Yms`.

Para evidencia comparativa se ejecuto una medicion local con `TestClient` usando primer request (frio) y mediana de requests subsecuentes (cache caliente) sobre endpoints candidatos.

## Decisiones en frontend

### 1) Lazy loading de componentes/modulos

Se aplico carga diferida en dos modulos que no son necesarios en el primer render:

- `uis/backoffice/supplier-renderer.js`: ahora se importa dinamicamente solo cuando se va a renderizar el listado de proveedores.
- `uis/backoffice/summary-renderer.js`: nuevo modulo importado dinamicamente solo al analizar CSV de incidencias.

Razon:

- ambos modulos no son criticos para mostrar login, shell y navegacion inicial
- reducen trabajo inicial de parse/ejecucion de JS
- se cargan justo antes de uso real

### 2) Memoizacion estilo useMemo para calculo no trivial

Se implemento una utilidad generica de memoizacion por dependencias en:

- `uis/backoffice/utils.js` -> `createMemoizedByDependencies(dependencies, ...args)`

Uso aplicado en:

- `uis/backoffice/app.js` para calculo derivado de insights de proveedores (`computeSupplierInsights`)

Calculo memoizado:

- agregacion por pais y estado
- ranking top de categorias

Dependencias explicitas:

- token derivado de `id`, `status`, `country`, `rate_per_unit` por proveedor

Razon:

- evita recalcular agregaciones cuando no cambia el dataset
- mantiene costo de render estable en filtros o refrescos sin cambios efectivos

## Decisiones en backend

### 1) Middleware de timing

Implementado en `services/api/main.py`.

Objetivo:

- identificar endpoints con mayor costo para priorizar cache por evidencia

### 2) Cache TTL en proveedores

Archivo: `services/api/routes/suppliers.py`

Endpoints cacheados:

- `GET /suppliers` (TTL 60s, clave por filtros `country/category/status`)
- `GET /suppliers/{supplier_id}` (TTL 120s, clave por id)

Invalidacion:

- en `POST /suppliers`
- en `PATCH /suppliers/{id}/rate`
- en `PATCH /suppliers/{id}/status`
- en `DELETE /suppliers/{id}`

Estrategia:

- invalidacion total de listas
- invalidacion puntual de detalle por id

### 3) Cache TTL en inventario

Archivo: `services/routers/inventory.py`

Endpoints cacheados:

- `GET /inventory/products` (TTL 20s)
- `GET /inventory/products/{product_id}` (TTL 20s)
- `GET /inventory/orders` (TTL 15s)

Invalidacion:

- en `POST /inventory/products`
- en `POST /inventory/orders/inbound`
- en `POST /inventory/orders/outbound`

Estrategia:

- limpieza de listas al escribir
- invalidacion puntual de detalle cuando hay `product_id`

## Evidencia de impacto (medicion local)

Medicion con datos de prueba y 20 productos + movimientos:

- `/suppliers`: frio 3.77ms -> caliente 3.28ms (mejora 13.0%)
- `/inventory/products`: frio 15.76ms -> caliente 3.36ms (mejora 78.7%)
- `/inventory/orders`: frio 12.80ms -> caliente 4.04ms (mejora 68.4%)

Lectura:

- el mayor beneficio aparece en endpoints con joins/sumas y transformacion de respuesta
- proveedores gana menos por menor costo base, pero sigue siendo una ruta frecuente de UI

## Tradeoffs reconocidos (frescura vs rendimiento)

- Inventario usa TTL corto (15-20s) porque el dato cambia por operaciones de entrada/salida y la frescura es operativa.
- Proveedores tolera TTL mas alto (60-120s) porque cambia menos y su uso es mayormente de consulta/administracion.
- En ambos casos se combina TTL + invalidacion en escrituras para reducir ventana de staleness.

## Que no se cacheo y por que

No se cachearon endpoints de sesion o datos personales:

- `/auth/login`
- `/auth/me`
- `/profiles/me`
- endpoints de cambio o reset de password

Razon:

- contienen datos por usuario o credenciales
- riesgo de fuga de datos si una clave no acota por usuario
- poco beneficio frente a riesgo de seguridad/consistencia

## Cambios de implementacion (resumen)

- Nuevo cache en memoria TTL: `services/api/cache.py`
- Timing middleware: `services/api/main.py`
- Caches e invalidacion proveedores: `services/api/routes/suppliers.py`
- Caches e invalidacion inventario: `services/routers/inventory.py`
- Lazy loading + memoizacion frontend: `uis/backoffice/app.js`
- Helper de memoizacion: `uis/backoffice/utils.js`
- Modulo de render diferido de resumen: `uis/backoffice/summary-renderer.js`
- Contenedor de insights y ajuste de scripts: `uis/backoffice/index.html`
