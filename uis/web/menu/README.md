# Menu de muestra de BRASALAND

Pagina estatica en `/uis/web/menu/`, sin endpoints nuevos, dependencias
adicionales ni conexiones a bases de datos. Utiliza el CSS publico existente
y una hoja exclusiva con selectores limitados a `.menu-page`.

## Datos pendientes de aprobacion

`menu-data.json` centraliza ocho categorias y 24 productos de demostracion.
El estado es `demo`, los precios son `null` y la moneda es `null`. El renderer
muestra `Por confirmar` para todos los precios de esta carta de muestra.
No se declara disponibilidad, tamano, marca ofertada ni informacion nutricional.

Confirmar productos, nombres, ingredientes, recetas, moneda de cada mercado,
precios, disponibilidad y fotografias oficiales antes de presentar la carta
como oferta comercial. Los ejemplos no son un catalogo oficial de BRASALAND.
Cada producto admite opcionalmente un objeto `image` con el mismo formato de
las imagenes de categoria. Se muestran atribuciones para esas imagenes tambien.

## Fotografias y licencia

`assets/PHOTOS.md` registra los ocho archivos de origen en Wikimedia Commons,
sus autores y licencias CC BY o CC BY-SA. Las mismas atribuciones aparecen en
la seccion desplegable `Fotografias y licencias` del pie de pagina.

El registro de fuentes de `assets/PHOTOS.md` identifica las obras originales,
autores y licencias, y afirma que se descargaron los originales. Un registro
anterior afirmaba que algunas imágenes procedían de miniaturas oficiales tras
un HTTP 429. Como esas afirmaciones difieren, el método de descarga queda sin
resolver y no debe presentarse como verificado hasta contrastarlo con el
historial de descarga. Las copias WebP locales son adaptaciones de las obras
identificadas y mantienen las licencias indicadas.

Las 18 copias WebP son recortes y redimensionados a 480 x 300 y 960 x 600,
mas cabecera a 960 x 540 y 1440 x 810. No son imagenes generadas ni fotografias
de platos de BRASALAND. Las adaptaciones conservan la licencia indicada por
archivo, incluyendo CompartirIgual en las que usan CC BY-SA. El resto del sitio
no adopta esa licencia por mostrar las fotografias.

## Visualizacion y publicacion

La carpeta `uis/web` ya esta montada en Nginx en el entorno de desarrollo;
la nueva pagina puede comprobarse directamente en `/uis/web/menu/` sin
reconstruir servicios. El HTML raiz de la portada se copia a la imagen Docker,
por lo que sus dos enlaces nuevos necesitan una sincronizacion posterior
autorizada para aparecer en la portada servida por 3000/3001. Esta tarea no
ejecuta reconstrucciones, recreaciones ni despliegues.

El aviso de muestra es visible y la pagina declara `noindex, nofollow`.
Esas medidas no son un control de acceso ni garantizan que la URL sea privada:
el montaje existente hace que la pagina sea accesible a quien tenga acceso
al servidor del proyecto. No se debe anunciar como carta oficial sin aprobacion.