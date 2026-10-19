# AUDIT - Auditoria inicial

Fecha: 2026-10-09. Rama: `perf/auditoria-lighthouse`.
Revision inicial: `41d9b18`; linea base funcional versionada: `b4fedef`.
Se trabaja sobre el monorepo de empresa existente,
sin reconstruir ni redisenar las aplicaciones.

## Superficies reales

La web corporativa es [index.html](index.html) y su segunda vista es el
formulario Brasa Points en [application.html](application.html).
[uis/web/index.html](uis/web/index.html) es otra consola protegida, no la
portada publica. No existen scripts Next.js `dev`, `build` o `start` por frontend.
La configuracion Docker existente redirige sus raices a consolas internas;
por eso no se uso para las mediciones de la web publica.

| Pagina | URL fija | Dispositivos |
| --- | --- | --- |
| Portada | http://127.0.0.1:8080/ | Movil y escritorio |
| Registro | http://127.0.0.1:8080/application.html | Movil y escritorio |
| Dashboard | http://127.0.0.1:8080/uis/backoffice/ | Movil y escritorio |

## Entorno de medicion

- Ubuntu 24.04, Node 24.14.0, Lighthouse 12.8.2 y Playwright 1.56.1.
- Chromium 141.0.7390.37, headless, sin extensiones, mismo binario en ambas fases.
- Archivos estaticos con `python -m http.server 8080`; sin HMR ni compilador
  de desarrollo. El CSS final esta precompilado. No se compara dev con produccion.
- Movil: 412 x 823, DPR 1, RTT simulado 150 ms, 1638.4 Kbps y CPU x4.
- Escritorio: 1350 x 940, DPR 1, RTT simulado 40 ms, 10240 Kbps y CPU x1.
- Tres pasadas secuenciales por combinacion; se informa la mediana, no la mejor.
- Proceso Chrome nuevo por pasada. Se vacia la cache HTTP despues de la captura
  y antes de Lighthouse. `disableStorageReset` conserva solo la sesion necesaria;
  las aplicaciones no tienen service workers. Los informes contienen la configuracion completa.
- API FastAPI real en 8000, datos TinyDB aislados bajo `/tmp/brasaland-lighthouse-data`
  y `DATABASE_URL` SQLite temporal. No se utilizaron datos ni credenciales reales.
- Usuario temporal del mismo rol y con el mismo perfil en cada fase; 15 proveedores
  semilla, mismos filtros vacios. El dashboard se comprueba autenticado y con filas.
- Las capturas Playwright son de comprobacion visual, sin throttling; las metricas
  proceden de Lighthouse. Las trazas `sessionRequests` son diagnostico local,
  no una medicion de rendimiento de produccion.

## Puntuaciones iniciales

Medianas de tres pasadas en las URLs de la tabla anterior. Unidades: segundos
para LCP/FCP, milisegundos para TBT/TTFB; CLS no tiene unidad.

| Pagina / ruta real | Modo | Performance | Accessibility | Best Practices | SEO | LCP (s) | CLS | TBT (ms) | FCP (s) | TTFB (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Website `/` | Mobile | 72 | 92 | 100 | 91 | 16.356 | 0 | 0 | 2.198 | 1.66 |
| Website `/` | Desktop | 85 | 92 | 100 | 91 | 2.724 | 0 | 0 | 0.528 | 0.49 |
| Website `/application.html` | Mobile | 96 | 77 | 93 | 90 | 2.177 | 0 | 0 | 2.177 | 0.72 |
| Website `/application.html` | Desktop | 100 | 77 | 96 | 90 | 0.516 | 0 | 0 | 0.516 | 1.86 |
| Backoffice `/uis/backoffice/` | Mobile | 79 | 93 | 100 | 90 | 2.457 | 0.307 | 0 | 2.306 | 0.81 |
| Backoffice `/uis/backoffice/` | Desktop | 86 | 93 | 100 | 90 | 0.676 | 0.256 | 0 | 0.676 | 1.63 |

Origen: [audit/before/summary.json](audit/before/summary.json).
INP: **N/D** en las seis combinaciones; no se inventa ni se reemplaza por TBT.
Los valores de TTFB corresponden a `server-response-time` en los JSON.

## Excepcion de arranque anterior a la linea base

El dashboard original no ejecutaba `app.js`: las funciones globales de
[utils.js](uis/backoffice/utils.js) colisionaban con su desestructuracion
`const` en [app.js](uis/backoffice/app.js), provocando
`Identifier 'parseApiError' has already been declared`.

Antes de corregirlo se guardaron dos informes y dos capturas en
[audit/blocked/summary.json](audit/blocked/summary.json). Muestran la pantalla de
acceso sin un dashboard funcional; sus puntuaciones NO son una linea base valida.
Se encapsularon los auxiliares, conservando su contrato, y solo entonces se
midio el dashboard autenticado de `audit/before/`. La comparacion de rendimiento
del dashboard parte de esa reparacion minima, no del estado original roto.
Las pasadas exploratorias con cache caliente se descartaron y reemplazaron por
la serie fria documentada. No se presentan como evidencia comparable.

## Problemas detectados

| Hallazgo | Evidencia inicial | Causa raiz | Correccion |
| --- | --- | --- | --- |
| Portada lenta | LCP movil 16.356 s; 3,098,448 bytes transferidos | PNG original de 2,964,476 bytes servido a todos los dispositivos, sin variantes responsivas | WebP del mismo recurso, `srcset`, `sizes`, dimensiones intrinsecas y prioridad alta |
| CSS bloqueante | Tailwind remoto: ahorro estimado 1.46 s en portada movil y 1.49 s en registro | Play CDN descarga y ejecuta el compilador en cada navegador | Tailwind 3.4.17 compilado localmente, CSS minimo con las clases existentes |
| Saltos de layout internos | CLS movil 0.307 y escritorio 0.256 | Se pintaba el login antes de autenticar, luego se sustituia por contenido y filas; fuentes externas tardias | Estado inicial `aria-busy` sin pintar contenido intermedio, fuentes locales y preload |
| Trabajo de red duplicado | `/auth/me` -> `/profiles/me` -> `/suppliers` | El perfil ya estaba en `me.profile`, pero se solicitaba otra vez en serie | Consumir el perfil incluido en `/auth/me`; dos peticiones en vez de tres |
| Desbordamiento movil | Captura y `horizontalOverflow: true` del dashboard | Minimo intrinseco de hijos de grid y tabla, y menu sin wrap | `min-width: 0` en contenedores; scroll dentro de la tabla; menu flexible |
| Formulario poco accesible | Accessibility 77; controles sin nombre y Best Practices 93 movil | Placeholders usados como etiquetas, selects/fecha sin nombre y falta de viewport | Nombres accesibles, autocomplete y viewport, sin alterar la validacion |
| Tarifas sin etiqueta | Accessibility 93 del dashboard | Inputs creados dinamicamente sin nombre accesible | Etiqueta contextual por proveedor, con prueba de regresion |
| Contraste y SEO publico | Accessibility 92 y SEO 91 en portada | Blanco sobre rojo con contraste 3.76 y falta de descripcion | Rojo de contraste suficiente y metadescripciones especificas |

### Problema 1 - Imagen de portada

- Frontend y URL: website, http://127.0.0.1:8080/.
- Indicador afectado: LCP y transferencia, especialmente movil.
- Evidencia de Lighthouse: LCP movil 16.356 s; la imagen aparece como recurso
  dominante en `network-requests` del [informe inicial](audit/before/website-home-mobile-1.json).
- Archivo involucrado: [index.html](index.html) referencia directamente
  [Brasaland.png](Brasaland-company.md/Brasaland.png), de 1536 x 1024 y 2,964,476 bytes.
- Causa raiz comprobada: se descarga el mismo PNG pesado independientemente
  del ancho; no hay `srcset` ni variantes optimizadas.
- Solucion propuesta y aplicada: WebP responsivo del mismo recurso, dimensiones
  reales, `sizes` y prioridad alta; no usar lazy loading indiscriminado para el LCP.
- Riesgo y comprobacion: degradacion visual o seleccion de recurso incorrecta;
  comprobar la imagen cargada en ambos dispositivos y comparar LCP en la misma URL.

### Problema 2 - Compilador CSS en el navegador

- Frontend y URLs: website, `/` y `/application.html` en el origen 8080.
- Indicadores afectados: FCP, LCP y trabajo JavaScript de carga.
- Evidencia de Lighthouse: `render-blocking-resources` estima 1.46 s de ahorro
  en portada movil; [registro movil](audit/before/website-registration-mobile-1.json)
  estima 1.49 s para los recursos bloqueantes y detecta JavaScript no utilizado.
- Archivos involucrados: [index.html](index.html) y [application.html](application.html),
  ambos con `https://cdn.tailwindcss.com` en el estado inicial.
- Causa raiz comprobada: el compilador Play CDN bloquea el analisis de HTML y
  genera estilos en runtime. No existe un problema de hidratacion React: son HTML estaticos.
- Solucion propuesta y aplicada: compilar las clases existentes a
  [public.min.css](uis/web/public.min.css) con [tailwind.config.js](tailwind.config.js).
- Riesgo y comprobacion: clases ausentes en el build; comparar capturas, comprobar
  el formulario y verificar que no se descarga el compilador remoto.

### Problema 3 - Layout y ruta critica del dashboard

- Frontend y URL: backoffice, http://127.0.0.1:8080/uis/backoffice/.
- Indicadores afectados: CLS, FCP y LCP; ancho util en movil.
- Evidencia de Lighthouse: CLS 0.307 movil / 0.256 escritorio;
  `layout-shifts` identifica `main.layout` en el
  [informe inicial](audit/before/backoffice-dashboard-mobile-1.json).
  La traza local registra `/auth/me`, `/profiles/me`, `/suppliers` en serie.
- Archivos involucrados: [index.html](uis/backoffice/index.html),
  [app.js](uis/backoffice/app.js), [styles.css](uis/backoffice/styles.css) y la
  respuesta `profile` de [routes/auth.py](services/api/routes/auth.py).
- Causas comprobadas: login pintado antes de cambiar a contenido protegido,
  peticion redundante del perfil, hijos de grid con minimo intrinseco y menu sin wrap.
  Las fuentes Google estan en la ruta bloqueante; su contribucion aislada al CLS
  sigue siendo una hipotesis pendiente de validar, no una medicion por separado.
- Solucion propuesta y aplicada: no pintar el estado intermedio (`aria-busy`),
  consumir `me.profile`, alojar las mismas fuentes localmente, menu flexible y
  tabla con scroll contenido. No ocultar columnas ni reducir los datos auditados.
- Riesgo y comprobacion: contenido que quede oculto ante fallos, perfil vacio o
  acciones de tabla inaccesibles; probar login, filtros, tarifas, CSV, perfil y logout.

### Problema 4 - Accesibilidad y metadatos

- Frontends y URLs: `/`, `/application.html` y `/uis/backoffice/`.
- Indicadores afectados: Accessibility, Best Practices y SEO publico.
- Evidencia: `color-contrast` indica relacion 3.76 en la portada;
  `label` / `select-name` senalan controles de registro y tarifas sin nombre;
  falta `viewport` en registro y `meta-description` en las paginas publicas.
- Archivos involucrados: [application.html](application.html), [index.html](index.html),
  [tailwind.config.js](tailwind.config.js) y
  [supplier-renderer.js](uis/backoffice/supplier-renderer.js).
- Causa raiz comprobada: placeholders no sustituyen etiquetas, inputs generados
  sin nombre accesible y blanco sobre rojo insuficiente. No se atribuye a hidratacion.
- Solucion propuesta y aplicada: nombres accesibles, viewport, autocomplete,
  rojo de contraste suficiente y descripciones publicas. El dashboard permanece `noindex`.
- Riesgo y comprobacion: modificar accidentalmente validacion o interacciones;
  probar el formulario dependiente, tarifas y revisar las cuatro categorias.

## Codigo duplicado

### Caso 1 - Acciones de estado

- Archivos: [uis/web/app.js](uis/web/app.js) y [uis/backoffice/app.js](uis/backoffice/app.js).
- Codigo repetido: `addRetryButton` y `addHomeLink` crean el mismo contenedor,
  estilos, enlace/boton y eliminan el bloque previo de acciones.
- Por que conviene extraerlo: evitar divergencias de estilos, acciones duplicadas
  o botones que envien un formulario por accidente; un solo contrato para ambos consumidores.
- Abstraccion propuesta e implementada: componente DOM
  [BrasalandStatusActions](uis/shared/status-actions.js),
  `render(parent, { label, onAction, href })`. Devuelve el contenedor, conserva una
  unica instancia por estado y coordina callback o enlace segun la opcion.
- Verificacion: `npm run check:frontends` comprueba reemplazo de acciones,
  un unico callback y carga del componente en ambas consolas.

### Caso 2 - Resumen de incidencias

- Archivos: [uis/web/app.js](uis/web/app.js) y [uis/backoffice/app.js](uis/backoffice/app.js).
- Codigo repetido: `renderSummary`, tarjetas KPI, lista de invalidos, satisfaccion
  y tablas por categoria/estado.
- Por que convendria extraerlo: un solo tratamiento de datos incompletos,
  formatos numericos y orden de los KPI evitaria divergencias entre consolas.
- Abstraccion propuesta: `createIncidentSummaryRenderer(elements, onStatus)`
  devuelve `{ render(summary) }`; recibe nodos de cada pagina y un callback para
  el estado, sin acoplarse a la API ni a la autenticacion.
- Decision: candidato no implementado. No mejora el cuello de botella observado
  y ampliaria el cambio de renderizado del CSV. El primer caso satisface la extraccion minima.

No se anade React ni se llama Custom Hook a una funcion DOM. No se crea un
paquete compartido porque el despliegue estatico existente ya admite `uis/shared`.

## Evidencia y limites

- [Antes](audit/before/summary.json): 18 informes HTML, 18 JSON, 6 capturas de pagina
  y 6 capturas de resultados Lighthouse.
- [Despues](audit/after/summary.json): mismo numero y patron de nombres.
- Nombres: `<pagina>-<mobile|desktop>-<1|2|3>.html` y `.json`; capturas de pagina
  sin numero y resultados con sufijo `-lighthouse.png`.
- Las capturas de resultados se generaron posteriormente desde los HTML originales,
  sin nueva auditoria ni alteracion de las puntuaciones. `reportScreenshot` en el
  resumen identifica la pasada elegida, cuya puntuacion Performance coincide con
  la mediana. Las demas metricas de esa pasada pueden diferir de las medianas;
  el informe visual tambien redondea, por ejemplo, TBT a incrementos de 10 ms.
- LCP, CLS e INP son los Core Web Vitals actuales. FID fue sustituido por INP.
  Estos informes de carga aportan LCP, CLS, FCP, TBT y TTFB, NO un INP de campo.
  Las pruebas de clicks verifican funciones, no certifican INP. TBT no es INP.
- TTFB local no representa latencia de un despliegue real. El backend aislado no
  certifica PostgreSQL ni inventario. No se cambio codigo backend.
- `noindex, nofollow` del dashboard es intencionado: SEO interno baja a 50.
  No se fuerza la indexacion de un panel privado para obtener una puntuacion mayor.
- Quedan fuera: SEO de otras rutas, accesibilidad manual con lector de pantalla,
  INP real mediante RUM y comportamiento con miles de proveedores.
- `npm audit --omit=dev` informa cero vulnerabilidades de produccion. La instalacion
  detecto 54 avisos en herramientas de desarrollo (40 moderados, 14 altos);
  no se aplicaron upgrades forzados que cambiaran el motor de medicion a mitad de la comparacion.

Resultados y reproduccion: [REPORT.md](REPORT.md).