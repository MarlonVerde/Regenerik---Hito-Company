# REPORT - Mejoras de rendimiento

Fecha de la serie comparable: 2026-10-09, 23:06-23:17 UTC.
Se conservan las mismas tres URLs y los mismos perfiles de dispositivo.
Resultados: medianas de tres pasadas. Protocolo y excepcion de arranque:
[AUDIT.md](AUDIT.md).

## Resumen

- Frontends auditados: website corporativo y backoffice existentes.
- Paginas medidas: http://127.0.0.1:8080/, http://127.0.0.1:8080/application.html
  y http://127.0.0.1:8080/uis/backoffice/, en Mobile y Desktop.
- Cambios principales: imagen WebP responsiva, CSS compilado, fuentes locales,
  carga inicial estable, peticion de perfil eliminada y mejoras de accesibilidad.
- Componente extraido: [BrasalandStatusActions](uis/shared/status-actions.js).
- Linea base: `b4fedef`; implementacion de optimizaciones: `3b94f38`.

## Correcciones aplicadas

### Correccion 1 - Imagen y CSS publicos

- Problemas originales: PNG pesado y compilador Tailwind remoto bloqueante.
- Causas raiz: un recurso de 2,964,476 bytes para todos los anchos y estilos
  generados en cada navegador en vez de compilados previamente.
- Archivos modificados: [index.html](index.html), [application.html](application.html),
  [package.json](package.json), [package-lock.json](package-lock.json),
  [tailwind.config.js](tailwind.config.js), [public.css](uis/web/public.css),
  [public.min.css](uis/web/public.min.css), [build-frontend-assets.mjs](scripts/build-frontend-assets.mjs)
  y tres WebP en `uis/web/assets/`.
- Cambio realizado: eliminar Play CDN, compilar las clases existentes, conservar
  la imagen original y ofrecer variantes WebP con proporciones reales y prioridad alta.
- Verificacion funcional: `npm run build:frontends`, imagen decodificada, ausencia
  de desbordamiento y formulario dependiente comprobados en 412 y 1350 px.
- Commit: `3b94f38` (paquete de cambios, no commit individual por recurso).
- Medicion antes: portada movil Performance 72, LCP 16.356 s, FCP 2.198 s;
  registro movil Performance 96, LCP 2.177 s.
- Medicion despues: portada movil Performance 100, LCP 1.204 s, FCP 0.754 s;
  registro movil Performance 100, LCP 0.996 s.
- Atribucion: mejora del paquete publico; no hay medicion aislada WebP frente a CSS.

### Correccion 2 - Estabilidad y carga del dashboard

- Problemas originales: CLS alto, fuentes bloqueantes, perfil repetido y overflow movil.
- Causas raiz: se pintaba el login intermedio, `me.profile` se solicitaba de nuevo,
  menu sin wrap y contenedores grid que adoptaban el ancho intrinseco de la tabla.
- Archivos modificados: [app.js](uis/backoffice/app.js), [index.html](uis/backoffice/index.html),
  [styles.css](uis/backoffice/styles.css), [build-frontend-assets.mjs](scripts/build-frontend-assets.mjs)
  y fuentes/licencias en `uis/backoffice/assets/`.
- Cambio realizado: estado inicial `aria-busy`, fuentes locales con preload,
  reutilizacion del perfil, menu flexible y scroll contenido de tabla.
- Verificacion funcional: dashboard real con 15 proveedores; login/logout,
  filtros, tarifa editada/restaurada, CSV/exportacion y perfil comprobados con Playwright.
- Commit: `3b94f38`.
- Medicion antes: movil Performance 79, LCP 2.457 s, CLS 0.307; tres peticiones
  de inicializacion y desbordamiento de documento.
- Medicion despues: movil Performance 99, LCP 1.861 s, CLS 0.011; dos peticiones
  y sin desbordamiento de documento. TBT pasa de 0 a 17 ms, no se oculta ese coste.
- Atribucion: paquete interno medido; contribucion individual de fuentes al CLS no aislada.

### Correccion 3 - Accesibilidad y SEO apropiado

- Problemas originales: contraste insuficiente, selects/fecha/tarifas sin nombre,
  falta de viewport y de metadescripciones publicas.
- Archivos modificados: [application.html](application.html), [index.html](index.html),
  [tailwind.config.js](tailwind.config.js), [supplier-renderer.js](uis/backoffice/supplier-renderer.js),
  [supplier-renderer.test.js](uis/backoffice/__tests__/supplier-renderer.test.js)
  e [index.html del dashboard](uis/backoffice/index.html).
- Cambio realizado: nombres accesibles, autocomplete, viewport, contraste,
  descripciones y `noindex, nofollow` del panel interno.
- Verificacion funcional: formulario y tarifa siguen funcionando; nombres
  accesibles comprobados por pruebas y Lighthouse. No se cambiaron sus reglas de negocio.
- Commit: `3b94f38`.
- Medicion antes: Accessibility portada 92, registro 77 y dashboard 93;
  SEO publico 91/90 y SEO interno 90.
- Medicion despues: Accessibility 100 en las seis combinaciones, SEO publico 100
  y SEO interno 50 por exclusion intencionada de buscadores.

### Reparacion previa - Arranque del dashboard

- Problema y causa: colision entre funciones globales y declaraciones `const`,
  impedia autenticar/renderizar. No era una optimizacion de un dashboard funcional.
- Archivos: [utils.js](uis/backoffice/utils.js) y [utils.test.js](uis/backoffice/__tests__/utils.test.js).
- Cambio: encapsular auxiliares con IIFE, conservando `window.BackofficeUtils` y CommonJS.
- Verificacion: prueba de colision de declaraciones y dashboard real autenticado.
- Commit: `b4fedef`. Medicion previa funcional: **N/D**; estado roto en `audit/blocked/`.
  La serie `before` empieza despues de esta reparacion minima.

## Refactorizacion

- Casos de duplicacion identificados: **2**, detallados en [AUDIT.md](AUDIT.md).
- Abstraccion implementada: componente DOM `BrasalandStatusActions.render` para
  acciones de reintento/enlace; el resumen de incidencias queda como segundo candidato.
- Archivos que lo reutilizan: [uis/web/app.js](uis/web/app.js) y
  [uis/backoffice/app.js](uis/backoffice/app.js); ambos HTML cargan el script compartido.
- Distribucion: [uis/Dockerfile](uis/Dockerfile) incluye `uis/shared`.
- Prueba: `npm run check:frontends` comprueba un solo bloque por estado,
  callback unico y carga en ambas consolas; Docker construye correctamente.
- Commit: `3b94f38`. Mejora de Lighthouse atribuible al componente: **N/D**;
  el beneficio demostrado es mantenibilidad, no velocidad.

## Comparacion Lighthouse

Cada celda expresa `antes -> despues`.

| Frontend / URL / modo | Performance antes | Performance despues | Diferencia (puntos) |
| --- | --- | --- | --- |
| Website `/`, Mobile | 72 | 100 | +28 |
| Website `/`, Desktop | 85 | 100 | +15 |
| Website `/application.html`, Mobile | 96 | 100 | +4 |
| Website `/application.html`, Desktop | 100 | 100 | 0 |
| Backoffice `/uis/backoffice/`, Mobile | 79 | 99 | +20 |
| Backoffice `/uis/backoffice/`, Desktop | 86 | 100 | +14 |

| Pagina | Dispositivo | Performance | Accessibility | Best Practices | SEO |
| --- | --- | --- | --- | --- | --- |
| Portada | Movil | 72 -> 100 | 92 -> 100 | 100 -> 100 | 91 -> 100 |
| Portada | Escritorio | 85 -> 100 | 92 -> 100 | 100 -> 100 | 91 -> 100 |
| Registro | Movil | 96 -> 100 | 77 -> 100 | 93 -> 100 | 90 -> 100 |
| Registro | Escritorio | 100 -> 100 | 77 -> 100 | 96 -> 100 | 90 -> 100 |
| Dashboard | Movil | 79 -> 99 | 93 -> 100 | 100 -> 100 | 90 -> 50 |
| Dashboard | Escritorio | 86 -> 100 | 93 -> 100 | 100 -> 100 | 90 -> 50 |

El descenso SEO interno corresponde a `noindex`; no es una regresion de SEO
publico. Una puntuacion 100 de laboratorio no garantiza velocidad ni accesibilidad
perfectas en todos los dispositivos reales.

## Metricas de carga

| Pagina / dispositivo | LCP (s) | CLS | FCP (s) | TBT (ms) | TTFB (ms) | Bytes transferidos |
| --- | --- | --- | --- | --- | --- | --- |
| Portada movil | 16.356 -> 1.204 | 0 -> 0 | 2.198 -> 0.754 | 0 -> 0 | 1.66 -> 1.33 | 3,098,448 -> 73,616 |
| Portada escritorio | 2.724 -> 0.365 | 0 -> 0 | 0.528 -> 0.207 | 0 -> 0 | 0.49 -> 0.85 | 3,098,459 -> 138,257 |
| Registro movil | 2.177 -> 0.996 | 0 -> 0 | 2.177 -> 0.754 | 0 -> 0 | 0.72 -> 1.38 | 134,626 -> 18,003 |
| Registro escritorio | 0.516 -> 0.274 | 0 -> 0 | 0.516 -> 0.204 | 0 -> 0 | 1.86 -> 1.76 | 134,624 -> 18,003 |
| Dashboard movil | 2.457 -> 1.861 | 0.307 -> 0.011 | 2.306 -> 1.061 | 0 -> 17 | 0.81 -> 0.90 | 83,522 -> 87,819 |
| Dashboard escritorio | 0.676 -> 0.458 | 0.256 -> 0.012 | 0.676 -> 0.290 | 0 -> 0 | 1.63 -> 0.92 | 83,522 -> 87,819 |

La portada movil reduce el LCP un 92.6% y la transferencia un 97.6%.
Las seis medianas finales cumplen LCP <= 2.5 s y CLS <= 0.1.
No hay afirmacion sobre INP: no fue medido. TBT movil interno sube a 17 ms y los
bytes internos aumentan un 5.1%; se informa ese coste, aunque LCP y CLS mejoran.
La mejora interna viene de la ruta critica y la estabilidad, no de menos bytes.
TTFB es local y pequenas variaciones no se atribuyen a los cambios frontend.
Las muestras individuales y su variabilidad quedan en los JSON; por ejemplo,
Performance inicial del dashboard movil fue 79, 72 y 79.

## Cambios entregados

- CSS Tailwind compilado localmente para las dos paginas publicas, sin compilador
  CDN en runtime y manteniendo clases y estructura.
- Misma imagen de Brasaland en WebP de 480, 768 y 1152 px; `srcset`, `sizes`,
  dimensiones 1536 x 1024 y prioridad de descarga. Se conserva el PNG original.
- Fuentes Space Grotesk e IBM Plex Mono locales, con licencias OFL junto a los
  archivos; scripts `defer` y precarga de la fuente principal del dashboard.
- Correccion minima del bloqueo global de auxiliares, con prueba especifica.
- Perfil reutilizado desde `/auth/me`: 3 -> 2 llamadas de inicializacion.
- Estado `aria-busy` evita pintar y sustituir la pantalla de acceso durante la
  carga; se libera tambien en el manejo de error. No se modifica la autenticacion.
- Menu que envuelve y tabla que se desplaza dentro de su contenedor movil.
- Nombres accesibles para controles de registro y tarifas, contraste suficiente
  y metadescripciones publicas; exclusividad `noindex` de la vista interna.
- Componente DOM compartido `BrasalandStatusActions`, consumido en ambas consolas
  y copiado por el Dockerfile. Segundo caso de duplicacion documentado sin refactor
  innecesario del analisis CSV.

## Verificacion

- `npm test -- --runInBand`: 12 pruebas en tres suites; umbral existente de
  cobertura de auxiliares satisfecho. La cobertura global no equivale a la de las rutas UI.
- `npm run check:frontends`: Chrome 412 y 1350 px; formulario dependiente y errores,
  login/logout real, 15 filas, filtros, tarifa editada y restaurada, CSV real,
  cuatro KPI, descarga CSV, perfil actualizado/restaurado y componente compartido
  cargado en ambas consolas. No hubo errores JavaScript sin capturar.
- Imagen renderizada y ausencia de desbordamiento de documento comprobadas;
  capturas finales revisadas. La tabla conserva su scroll horizontal propio.
- `docker build -t brasaland-perf-interfaces uis`: correcto, incluye `uis/shared`.
- Las auditorias finales verifican dashboard autenticado y URL sin redireccion
  a login; cada fase conserva seis capturas completas y seis capturas de resultados Lighthouse.

## Uso del agente

- Agente: GitHub Copilot, utilizado para ambos frontends.
- Skill utilizada: **ninguna** de las tres skills externas opcionales; no se
  instalo `core-web-vitals`, `performance` ni `web-perf`. No se declara uso inexistente.
- Herramientas utilizadas: Lighthouse por API, Chromium/Playwright y CDP para
  cache, navegacion, red y comprobacion de funciones. No se uso la pestana DevTools manual
  ni Chrome DevTools MCP; las capturas son de los reportes HTML de Lighthouse.
- Hallazgos comprobados: PNG pesado, Play CDN bloqueante, colision global,
  perfil duplicado, cambios de layout y controles sin nombre accesible.
- Cambios propuestos y aplicados: los documentados en las fichas anteriores.
  El segundo candidato de reutilizacion no se implemento. No se sugirio una
  correccion de hidratacion para HTML estatico ni una reescritura de arquitectura.

## Conclusion

- Mayor mejora observada: portada movil, LCP 16.356 -> 1.204 s y +28 puntos
  Performance, con el paquete de imagen responsiva y CSS compilado. La imagen
  era el recurso dominante, pero no se puede asignar una fraccion de la mejora
  a cada cambio sin pasadas aisladas.
- En el dashboard, CLS baja de 0.307 a 0.011 y mejora la carga sin cambiar los
  15 proveedores; la interfaz deja de desbordar el documento en movil.
- Metricas que no mejoraron: TBT movil interno sube a 17 ms y bytes internos
  aumentan 5.1%; SEO interno baja intencionadamente. INP queda **N/D**.
- Aprendizaje: medir con cache fria y sesion valida evita atribuir al codigo
  mejoras aparentes por cache o por haber auditado un login. Compartir un
  componente demuestra mantenibilidad, no automaticamente rendimiento.

### Limites del historial y del ciclo por correccion

La entrega original tiene una linea base y un commit agrupado de optimizaciones.
No se ejecutaron pasadas Lighthouse intermedias por cada correccion ni se crearon
commits separados para imagen, CSS y layout: esas mediciones son **N/D**.
El diagnostico en formato `AUDIT.md` se versiono con el informe final, no en el
primer commit. Por tanto, la secuencia historica no cumple literalmente los
pasos 03.4 y 05.4 de la rubrica ampliada. No se reescribe el historial publicado
ni se inventan tiempos o commits para ocultarlo. Las fichas permiten revisar
los cambios reales; para atribucion individual se requieren nuevas pruebas
controladas, identificadas como retrospectivas y separadas de la serie original.

## Reproduccion en Linux / Codespaces

Desde la raiz, instalar dependencias fijadas y generar recursos:

```bash
npm ci
npx playwright install chromium
npm run build:frontends
```

Terminal A, servidor estatico (solo para pruebas locales):

```bash
python -m http.server 8080 --bind 0.0.0.0
```

Terminal B, usando el entorno Python existente que contiene requirements de API:

```bash
BRASALAND_DATA_DIR=/tmp/brasaland-lighthouse-data \
DATABASE_URL=sqlite:////tmp/brasaland-lighthouse.sqlite \
AUTH_SECRET_KEY="$(openssl rand -hex 32)" \
ACCESS_TOKEN_EXPIRE_MINUTES=480 \
./.venv-1/bin/uvicorn main:app --app-dir services/api --host 127.0.0.1 --port 8000
```

Terminal C:

```bash
npm test -- --runInBand
npm run check:frontends
npm run audit:frontends -- after
```

Para regenerar solamente las capturas de resultados, sin nueva auditoria ni API:

```bash
npm run audit:frontends -- before --capture-reports
npm run audit:frontends -- after --capture-reports
```

Este modo abre los HTML originales desde el servidor 8080. `summary.json`
registra la pasada de origen en `reportScreenshot`. Los PNG con sufijo
`-lighthouse.png` muestran una pasada concreta, no una combinacion artificial
de medianas; estas se consultan en las tablas y resumenes.

Los scripts crean usuarios temporales con claves aleatorias y los eliminan al
terminar. Deben ejecutarse contra la API de prueba, nunca contra produccion.
Si se reutiliza el directorio temporal, conservar exactamente los 15 proveedores
semilla. La prueba modifica una tarifa y la restaura; no debe interrumpirse.
Los JWT se redactan antes de guardar los informes; no se versionan datos de API.

`AUDIT_ORIGIN`, `AUDIT_API` y `AUDIT_RUNS` permiten configurar el escenario.
`AUDIT_PAGES=backoffice-dashboard` permite retomar solo esa pagina cuando ya
existe el resumen de la fase. El valor por defecto son tres pasadas.
Para recrear un verdadero `before`, usar la revision de linea base con la
reparacion minima (`b4fedef`), no ejecutar `before` sobre el codigo optimizado.
En esa revision el ejecutor se invoca directamente con herramientas externas:

```bash
npm install --prefix /tmp/brasaland-perf-tools lighthouse@12.8.2 playwright@1.56.1
/tmp/brasaland-perf-tools/node_modules/.bin/playwright install chromium
AUDIT_TOOLS=/tmp/brasaland-perf-tools node scripts/audit-frontends.mjs before
```

Cada fase
sobrescribe sus nombres de archivos, por lo que conviene preservar la evidencia
entregada antes de repetirla. No mezclar puertos, perfiles ni servidores.

## Entrega y evidencia

Los HTML pueden abrirse desde el servidor, por ejemplo:
[portada antes](audit/before/website-home-mobile-1.html),
[portada despues](audit/after/website-home-mobile-1.html),
[dashboard antes](audit/before/backoffice-dashboard-mobile-1.html) y
[dashboard despues](audit/after/backoffice-dashboard-mobile-1.html).
Resumenes completos: [before](audit/before/summary.json) y
[after](audit/after/summary.json). Estado original roto:
[blocked](audit/blocked/summary.json).

La entrega se versiona en `perf/auditoria-lighthouse`, en el mismo repositorio
de empresa; no se crea un repositorio nuevo. El remoto de empresa configurado es
`origin` (`4GeeksAcademy/Regenerik---Hito-Company`); `fork` es una copia personal
distinta y no se sustituye por ella para cumplir la entrega.

URL del repositorio de empresa:
https://github.com/4GeeksAcademy/Regenerik---Hito-Company

URL de la rama entregada:
https://github.com/4GeeksAcademy/Regenerik---Hito-Company/tree/perf/auditoria-lighthouse