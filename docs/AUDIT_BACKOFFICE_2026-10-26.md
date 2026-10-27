# Auditoria funcional y migracion del backoffice a Next.js

Fecha de ejecucion: 2026-10-26.

## Alcance y estado

El backoffice servido por Docker es ahora una aplicacion Next.js 16.4.3 con
React 19 y App Router, ubicada en `uis/backoffice-next`. Los archivos HTML
anteriores se conservan en el repositorio, pero Nginx no los sirve como
backoffice activo. La web publica y FastAPI conservan sus implementaciones.

Esta revision verifica los servicios desplegados, los contratos usados por el
backoffice y las suites existentes. No constituye una certificacion exhaustiva
de todos los archivos, ausencia de vulnerabilidades o preparacion para produccion.

## Diagnostico del login

- La API local respondia 200, mientras el puerto remoto privado 8000 devolvia
  302 a `github.dev/pf-signin`.
- Los scripts anteriores tenian una URL concreta de Codespaces como destino.
- El HTML del panel contenia otra copia de esa URL con prioridad sobre la
  configuracion del login.
- Los scripts se cacheaban durante siete dias. No se accedio al navegador
  personal del usuario para verificar su cache o almacenamiento.
- Antes de migrar, un navegador limpio completo login, identidad y proveedores
  con respuestas reales 200. La causa restante en el navegador del usuario no
  quedo reproducida, por lo que no se atribuye con certeza a la cache.

## Implementacion desplegada

- Nginx sirve la web publica en 3000 y 3001.
- `/uis/backoffice/` se reenvia al servicio Next.js, puerto interno 3002.
- Las rutas API de Next.js llaman a FastAPI mediante `http://backend:8000`.
- El JWT se conserva en una cookie HttpOnly y SameSite=Lax; no se expone al
  JavaScript del cliente. Secure se activa al recibir HTTPS del proxy.
- Logout elimina la cookie. Las respuestas API no se cachean.
- Las escrituras con un Origin externo se rechazan con 403.
- Se conservan resumen, registro/login/logout, recuperacion y restablecimiento,
  proveedores, inventario, movimientos, perfil, contrasena y usuarios.
- Los permisos y la validacion siguen siendo responsabilidad de FastAPI; el
  registro publico sigue creando usuarios sin privilegios administrativos.
- Las rutas antiguas del directorio de proveedores redirigen al nuevo backoffice.
- Nginx rechaza archivos `.bak`, `.old`, `.orig` y `.save`.
- Los resultados de incidentes se separan por usuario y la API rechaza archivos
  mayores de 10 MiB. Nginx permite 11 MiB para incluir el multipart.

## Verificacion realizada

| Comprobacion | Resultado observado |
| --- | --- |
| Compilacion Next.js y construccion Docker | Correctas |
| Contenedor Next.js | Healthy |
| Nginx y readiness SQL de FastAPI | Correctos, HTTP 200 |
| Suite Python existente | 34 passed, 1 skipped |
| Suite Jest existente | 14 passed, 3 suites passed |
| Login Next.js con API real | Correcto |
| Registro y entrada desde navegador movil | Correctos |
| Cookie HttpOnly y ausencia de JWT en localStorage | Verificadas |
| Logout y bloqueo posterior de vista protegida | Verificados |
| Ocho vistas operativas en 412 px | Sin overflow horizontal ni errores JS |
| Capturas de escritorio y movil | Revisadas |
| Proveedores: filtro de pais | Respuesta filtrada real correcta |
| Proveedor temporal: crear, tarifa, estado, eliminar | Correcto |
| Perfil y cambio de contrasena de cuenta temporal | Correctos |
| CSV: analisis y descarga results.csv | Correctos con API real |
| Recuperacion para email inexistente | HTTP 200 y mensaje generico |
| Aislamiento de incidentes entre dos usuarios | Verificado en entorno temporal |
| Archivo mayor de 10 MiB | HTTP 413 en entorno temporal |
| Backups accesibles anteriormente | Ahora HTTP 404 |
| Origin externo en escritura | HTTP 403 |

Las cuentas y proveedores temporales utilizados fueron eliminados. No se
cambiaron la contrasena, los permisos ni el perfil de cuentas existentes.
No se ejecutaron seeds, migraciones ni movimientos sobre el inventario real.

La primera comprobacion automatizada conto incorrectamente el anunciador
accesible vacio de Next.js como error. Una segunda espera detecto etiquetas
ambiguas en selects, que se corrigieron mediante htmlFor/id. El mensaje de
recuperacion se verifico finalmente por separado con API y navegador reales.
Estos fallos intermedios no se contabilizan como recorridos completos aprobados.

## Riesgos y verificaciones pendientes

- `npm audit --omit=dev` del proyecto Next.js: cero vulnerabilidades conocidas
  reportadas en esta ejecucion; no equivale a una garantia de seguridad.
- `npm audit` de las herramientas heredadas de la raiz: 32 avisos, 11 altos y
  21 moderados. No se aplicaron actualizaciones forzadas.
- `pip-audit` de las versiones instaladas en Docker reporto avisos en `ecdsa`
  0.19.2, `pip` 25.0.1, `python-jose` 3.5.0, `python-multipart` 0.0.20 y
  `starlette` 0.47.3. El resultado contiene avisos duplicados. Evaluar cada
  advisory y actualizar de forma compatible antes de exponer en produccion.
  No se intentaron explotaciones ni se certifica su alcance en este servicio.
- La concurrencia con PostgreSQL real sigue omitida: requiere una base de
  pruebas dedicada mediante `BRASALAND_TEST_DATABASE_URL`.
- Las escrituras de inventario se cubrieron con las pruebas aisladas existentes,
  no con movimientos de navegador sobre los datos reales.
- No se verifico el envio real de emails ni un restablecimiento por enlace de
  correo. Requiere configurar y verificar el proveedor y la URL publica.
- La gestion de usuarios administrativos no se ejercito modificando cuentas
  reales. Los permisos del backend se comprobaron mediante la suite existente.
- Los ultimos resultados de incidentes siguen en memoria, separados por usuario;
  se pierden al reiniciar y no se comparten entre multiples workers.
- Jest sigue midiendo el frontend heredado (12.28% de cobertura de lineas
  global); sus 14 pruebas no representan cobertura unitaria de Next.js.
  Next.js se verifico mediante compilacion y recorridos reales de navegador.
- No se realizaron pruebas de carga, pentesting completo, revision manual de
  cada archivo del repositorio ni comprobaciones desde el navegador personal
  del usuario.

## Arranque y comprobaciones

Desde la raiz, manteniendo las variables existentes de `.env`:

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=50 -f backoffice interfaces
curl http://127.0.0.1:8000/health/ready
.venv-1/bin/python -m pytest -q
npm test -- --runInBand
npm --prefix uis/backoffice-next ci
npm --prefix uis/backoffice-next run build
npm --prefix uis/backoffice-next audit --omit=dev
```

Web local: `http://localhost:3000/`.
Backoffice: `http://localhost:3000/uis/backoffice/login/`.
En Codespaces, abrir el puerto 3000 desde Ports. No es necesario publicar
el puerto 8000 para iniciar sesion en Next.js. El puerto 3002 es interno.

No es necesario eliminar la base de datos, restablecer contrasenas ni ejecutar
un seed para utilizar la migracion. Tras abrir por primera vez, comprobar que
la pantalla nueva muestra el backoffice Next.js y no el formulario anterior
con un campo de URL de API.