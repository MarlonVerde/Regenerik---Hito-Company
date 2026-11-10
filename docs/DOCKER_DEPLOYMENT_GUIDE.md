# Guía de despliegue Docker — BRASALAND

> Documento de entrega académica. Describe la configuración Docker real del monorepo, verificada mediante auditoría (Fase 1) y pruebas de construcción/ejecución/conectividad (Fase 2). No requiere VPS ni despliegue público: el objetivo es demostrar que el proyecto completo se ejecuta, se comunica entre servicios y funciona en un entorno local reproducible.

## 1. Introducción y objetivo de Docker en BRASALAND

BRASALAND es un monorepo con tres aplicaciones independientes (frontend público, backoffice administrativo y backend API) que deben ejecutarse coordinadas y comunicarse entre sí. Docker y Docker Compose se usan para:

- Empaquetar cada aplicación con sus dependencias exactas, evitando el clásico "en mi máquina funciona".
- Levantar las tres aplicaciones con **un único comando**.
- Conectarlas mediante una red interna, sin exponer puertos innecesarios al host.
- Reproducir el entorno de forma idéntica en cualquier máquina con Docker instalado.

## 2. Arquitectura del monorepo y sus tres aplicaciones

```
Regenerik---Hito-Company/
├── uis/
│   ├── web/                 # Frontend público (HTML/CSS/JS)
│   ├── backoffice/          # Backoffice legacy estático (solo assets activos)
│   ├── backoffice-next/     # Backoffice activo (Next.js + React)
│   ├── nginx.conf           # Configuración Nginx (puertos 3000/3001)
│   └── Dockerfile           # Imagen del servicio "interfaces"
├── services/
│   ├── api/                 # Backend FastAPI (Python)
│   └── Dockerfile           # Imagen del servicio "backend"
└── docker-compose.yml       # Orquestación de los 3 servicios
```

| Aplicación | Tecnología | Ubicación | Servicio Compose |
|---|---|---|---|
| Frontend público | HTML, CSS, JavaScript | `uis/web` (+ `index.html`, `application.html` en la raíz) | `interfaces` |
| Backoffice administrativo | Next.js 16 + React 19 | `uis/backoffice-next` | `backoffice` |
| Backend | Python + FastAPI | `services/api` | `backend` |

## 3. Función de cada contenedor

### `interfaces` (Nginx)
- Imagen construida desde [uis/Dockerfile](../uis/Dockerfile).
- Sirve como **punto de entrada único** del stack: publica los puertos 3000 y 3001 al host.
- Sirve directamente los archivos estáticos del frontend público (`uis/web`, `index.html`, `application.html`, `uis/shared`) y los assets legacy de `uis/backoffice`.
- Hace **proxy inverso** hacia `backoffice` (Next.js) y hacia `backend` (FastAPI) para las rutas administrativas y de API.

### `backoffice` (Next.js)
- Imagen multi-stage construida desde [uis/backoffice-next/Dockerfile](../uis/backoffice-next/Dockerfile) (`node:22-alpine`, build `standalone`).
- No publica puertos al host (`expose: 3002`): solo es alcanzable desde `interfaces` y desde la red interna.
- Expone rutas de API propias (`app/api/[...path]/route.js`) que actúan como **proxy server-side** hacia el backend usando la variable `BACKEND_INTERNAL_URL=http://backend:8000`. El navegador nunca llama directamente al backend; todo pasa por el mismo origen de Next.js.
- Incluye `healthcheck` interno contra `/uis/backoffice/login/`.

### `backend` (FastAPI)
- Imagen construida desde [services/Dockerfile](../services/Dockerfile) (`python:3.12-slim`, dependencias instaladas con `uv`).
- Publica el puerto 8000 también directo al host (además de la red interna), útil para pruebas rápidas sin pasar por Nginx.
- Expone los endpoints de negocio (`inventory`, `auth`, `profiles`, `suppliers`, `users`) y los de salud `/health` y `/health/ready`.
- Corre con `uvicorn --reload`, apropiado para el entorno de desarrollo/entrega local descrito en este documento.

## 4. Función de Docker Compose

[docker-compose.yml](../docker-compose.yml) orquesta los tres servicios (`interfaces`, `backoffice`, `backend`) como una única unidad:

- Define el **orden de arranque** (`depends_on`).
- Crea y comparte la **red interna** `company_network` entre los tres servicios.
- Declara el **volumen nombrado** `api_data` para persistencia de datos locales del backend.
- Centraliza las **variables de entorno** del backend, exigiendo explícitamente `DATABASE_URL` y `AUTH_SECRET_KEY` (`${VAR:?...}`), que deben definirse en el archivo `.env` de la raíz.
- Permite construir y levantar todo el stack con un único comando.

## 5. Función de Nginx y comunicación interna

[uis/nginx.conf](../uis/nginx.conf) define dos bloques `server` equivalentes (puertos 3000 y 3001) que:

- Sirven el frontend público (`/`, `/uis/web/...`) directamente desde el sistema de archivos del contenedor.
- Redirigen las rutas legacy del backoffice estático (`/uis/web/login`, `/register`, etc.) hacia el backoffice Next.js activo (`/uis/backoffice/...`), preservando query params.
- Hacen `proxy_pass` de `location ^~ /uis/backoffice/` hacia `http://backoffice:3002` (nombre del servicio Docker, resuelto por la red interna `company_network`).
- Sirven los assets legacy de `/uis/backoffice/assets/` directo desde disco (sin pasar por el proxy).
- Hacen `proxy_pass` de `/backend/` hacia `http://backend:8000/`, exponiendo el backend también a través de Nginx.
- Bloquean el acceso a archivos `.bak`, `.old`, `.orig`, `.save` con `return 404`.

La comunicación interna entre contenedores usa siempre el **nombre del servicio** como hostname (`backend`, `backoffice`), resuelto automáticamente por el DNS interno de Docker dentro de `company_network`. Verificado en la Fase 2:

- `interfaces → backoffice:3002` → HTML de Next.js servido correctamente.
- `interfaces → backend:8000` → `{"status":"alive"}`.
- `backoffice → backend:8000` (proxy server-side) → `{"status":"alive"}`.

## 6. Puertos utilizados y direcciones locales

| Servicio | Puerto interno | Puerto publicado | Acceso local |
|---|---|---|---|
| `interfaces` (Nginx) | 3000, 3001 | `3000`, `3001` | http://localhost:3000 / http://localhost:3001 |
| `backoffice` (Next.js) | 3002 | *no publicado* | Solo vía Nginx: http://localhost:3000/uis/backoffice/ |
| `backend` (FastAPI) | 8000 | `8000` | http://localhost:8000 (directo) y http://localhost:3000/backend/ (vía Nginx) |

## 7. Red Docker `company_network`

Declarada en `docker-compose.yml` como red `bridge` nombrada `company_network`, compartida por los tres servicios. Es la única red del stack: garantiza que `interfaces`, `backoffice` y `backend` se vean entre sí por nombre de servicio, sin necesidad de IPs fijas ni de publicar puertos internos al host.

## 8. Persistencia mediante el volumen `api_data`

El servicio `backend` monta:

```yaml
volumes:
  - .:/app
  - api_data:/app/services/api/data/local
```

- `.:/app` monta el repositorio completo para habilitar recarga en caliente (`--reload`) durante el desarrollo.
- `api_data` es un **volumen nombrado** que se superpone a la ruta `/app/services/api/data/local` (coincide con `BRASALAND_DATA_DIR`). Esto asegura que los datos locales persistentes del backend **sobreviven** a `docker compose down` y a la recreación de contenedores, independientemente del bind mount del código fuente.

## 9. Conexión con PostgreSQL externo

El backend **no incluye un contenedor de base de datos**. `DATABASE_URL` (definida en `.env`) apunta a una instancia PostgreSQL externa gestionada (Supabase, vía *connection pooler* en el puerto 6543). Esto implica:

- No hay riesgo de pérdida de datos de negocio al recrear contenedores Docker, porque la base de datos vive fuera del stack.
- El endpoint `/health/ready` valida la conectividad real contra esa base de datos ejecutando `SELECT 1`.

## 10. Variables de entorno necesarias

Definidas en el archivo `.env` de la raíz (no versionado, excluido por `.gitignore` y `.dockerignore`). **Ninguno de sus valores reales se incluye en este documento.**

| Variable | Usada por | Propósito |
|---|---|---|
| `DATABASE_URL` | `backend` | Cadena de conexión a PostgreSQL (obligatoria) |
| `AUTH_SECRET_KEY` | `backend` | Clave de firma de tokens JWT (obligatoria) |
| `CORS_ALLOWED_ORIGINS` | `backend` | Orígenes permitidos para CORS (por defecto incluye `localhost:3000` y `:3001`) |
| `BRASALAND_DATA_DIR` | `backend` | Ruta de datos locales persistentes (por defecto `/app/services/api/data/local`, respaldada por el volumen `api_data`) |
| `APP_ENV` | `backend` | Entorno de ejecución |
| `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` | `backend` (seed) | Credenciales del usuario administrador inicial |
| `BRASALAND_SEED_USER_ID` | `backend` (seed) | Identificador de usuario semilla |
| `BACKEND_INTERNAL_URL` | `backoffice` (definida directamente en `docker-compose.yml`, no en `.env`) | URL interna del backend (`http://backend:8000`) usada por las rutas API de Next.js |

Existe una plantilla de referencia sin valores reales en `.env.example` (raíz) y `services/api/.env.example`.

## 11. Requisitos previos

- Docker Engine 24+ y Docker Compose v2 (validado con Docker 29.3.0 y Compose v2.40.3).
- Archivo `.env` en la raíz del repositorio con, al menos, `DATABASE_URL` y `AUTH_SECRET_KEY` definidos (ver sección 10).
- Puertos `3000`, `3001` y `8000` libres en el host.

## 12. Instalación y construcción de imágenes

```bash
# Validar la configuración de Compose (sintaxis e interpolación de variables)
docker compose config --quiet

# Construir las 3 imágenes (interfaces, backoffice, backend)
docker compose build
```

Resultado verificado en la Fase 2: las 3 imágenes se construyen sin errores ni warnings.

## 13. Inicio del proyecto

```bash
docker compose up --build -d
```

Este único comando construye (si hay cambios) y levanta los tres servicios en segundo plano, conectados a `company_network`, con el volumen `api_data` ya disponible.

## 14. Detención del proyecto

```bash
docker compose down
```

Detiene y elimina los contenedores y la red, **conservando** el volumen nombrado `api_data` (no se usa `-v`), por lo que los datos locales persistentes no se pierden.

## 15. Consulta de contenedores y logs

```bash
# Estado de los contenedores
docker compose ps

# Logs de un servicio puntual
docker compose logs backend --tail=40
docker compose logs backoffice --tail=40
docker compose logs interfaces --tail=40

# Seguir logs en vivo
docker compose logs -f
```

## 16. Verificación de los endpoints de salud

```bash
# Backend — liveness
curl http://localhost:8000/health
# Respuesta esperada: {"status":"alive"}

# Backend — readiness (valida conexión real a PostgreSQL)
curl http://localhost:8000/health/ready
# Respuesta esperada: {"status":"ready"}

# Backend a través de Nginx
curl http://localhost:3000/backend/health

# Frontend público
curl -I http://localhost:3000/

# Menú del frontend público
curl -I http://localhost:3000/uis/web/menu/

# Backoffice Next.js a través de Nginx
curl -I http://localhost:3000/uis/backoffice/
curl -I http://localhost:3001/uis/backoffice/
```

## 17. Solución de problemas frecuentes

| Problema | Causa probable | Solución |
|---|---|---|
| `docker compose up` falla con `DATABASE_URL` o `AUTH_SECRET_KEY` no definidas | Falta el archivo `.env` en la raíz o no contiene esas claves | Crear `.env` a partir de `.env.example` y completar los valores reales (no versionar) |
| `502 Bad Gateway` en `/uis/backoffice/` justo después de `up` | Nginx arrancó antes de que Next.js o Uvicorn terminaran de inicializar (`depends_on` no espera *healthy*) | Reintentar la petición tras unos segundos, o esperar a que `docker compose ps` muestre `backoffice` como `healthy` |
| `503` en `/health/ready` | La base de datos PostgreSQL externa no es alcanzable (red, credenciales o pooler caído) | Verificar `DATABASE_URL` y la disponibilidad del servicio externo |
| `404` en `/favicon.ico` | No hay favicon configurado en el proyecto | Esperado, no afecta la funcionalidad |
| Cambios en `uis/web` o `uis/backoffice` no se reflejan | Esos directorios están montados como *bind mount* de solo lectura; `index.html`, `application.html` y `uis/shared` sí requieren reconstruir la imagen | Para esos últimos, ejecutar `docker compose up --build -d` nuevamente |
| Puerto ya en uso al hacer `up` | Otro proceso del host ocupa 3000, 3001 u 8000 | Liberar el puerto o detener el contenedor previo con `docker compose down` |

## 18. Resultados de las pruebas realizadas (Fases 1 y 2)

| Prueba | Resultado |
|---|---|
| `docker compose config --quiet` | Exit 0, sin errores |
| `docker compose build` (3 servicios) | Build exitoso, sin errores ni warnings |
| `docker compose up --build -d` | Los 3 contenedores en estado `Up` (`backoffice` además `healthy`) |
| Frontend público `/` | HTTP 200 |
| Menú `/uis/web/menu/` | HTTP 200 |
| Backoffice vía Nginx (puertos 3000 y 3001) | HTTP 200 |
| Backend `/health` (directo) | HTTP 200, `{"status":"alive"}` |
| Backend `/health/ready` (directo) | HTTP 200, `{"status":"ready"}` |
| Backend `/backend/health` (vía Nginx) | HTTP 200 |
| Recursos estáticos (CSS, imagen `.webp`, chunk Next.js `_next/static`) | HTTP 200 con `content-type` correcto |
| Conectividad interna `interfaces → backoffice:3002` | OK (HTML servido) |
| Conectividad interna `interfaces → backend:8000` | OK (`{"status":"alive"}`) |
| Conectividad interna `backoffice → backend:8000` | OK (`{"status":"alive"}`) |
| Errores 4xx/5xx en logs | Ninguno relevante (solo `404` esperado de `/favicon.ico`) |

**Veredicto:** el stack Docker de BRASALAND construye, arranca, persiste datos y comunica correctamente sus tres aplicaciones en un entorno 100% local, cumpliendo el objetivo de la entrega sin requerir VPS ni despliegue público.
