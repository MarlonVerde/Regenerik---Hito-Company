const menuContent = document.getElementById('menu-content');

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function localImagePath(path) {
  const url = new URL(path, import.meta.url);
  if (url.origin !== window.location.origin || !url.pathname.startsWith('/uis/web/menu/assets/')) {
    throw new Error('La imagen debe ser un recurso local del menú.');
  }
  return url.href;
}

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function validatePhoto(photo) {
  if (!photo || typeof photo !== 'object' || !isNonEmptyString(photo.alt) || !isNonEmptyString(photo.src)) {
    throw new Error('Fotografía inválida.');
  }
  localImagePath(photo.src);
  if (photo.smallSrc !== undefined) {
    if (!isNonEmptyString(photo.smallSrc)) throw new Error('Ruta de imagen alternativa inválida.');
    localImagePath(photo.smallSrc);
  }
  if (!Number.isInteger(photo.width) || photo.width <= 0 || !Number.isInteger(photo.height) || photo.height <= 0) {
    throw new Error('Dimensiones de fotografía inválidas.');
  }
  if (!isNonEmptyString(photo.author) || !isNonEmptyString(photo.license)) {
    throw new Error('Atribución de fotografía incompleta.');
  }
  for (const value of [photo.source, photo.licenseUrl]) {
    if (!isNonEmptyString(value)) throw new Error('Enlace de atribución incompleto.');
    const url = new URL(value);
    if (url.protocol !== 'https:') throw new Error('Los enlaces de fotografía deben usar HTTPS.');
  }
}

function validateMenu(data) {
  if (!data || typeof data !== 'object' || !['demo', 'approved'].includes(data.status) ||
      !isNonEmptyString(data.notice) || !Array.isArray(data.categories) || data.categories.length !== 8) {
    throw new Error('Catálogo incompleto.');
  }
  if (data.currency !== null && (typeof data.currency !== 'string' || !/^[A-Z]{3}$/.test(data.currency))) {
    throw new Error('Moneda inválida.');
  }
  const ids = new Set();
  for (const category of data.categories) {
    if (!category || !isNonEmptyString(category.id) || ids.has(category.id) ||
        !isNonEmptyString(category.name) || !isNonEmptyString(category.eyebrow) ||
        !Array.isArray(category.products) || category.products.length === 0 || !document.getElementById(category.id)) {
      throw new Error('Categoría inválida.');
    }
    ids.add(category.id);
    if (category.image !== undefined && category.image !== null) validatePhoto(category.image);
    for (const product of category.products) {
      if (!product || !isNonEmptyString(product.name) || !isNonEmptyString(product.description) ||
          !(product.price === null || (Number.isFinite(product.price) && product.price >= 0))) {
        throw new Error('Producto incompleto.');
      }
      if (product.image !== undefined && product.image !== null) validatePhoto(product.image);
    }
  }
  if (data.heroImage) {
    if (!isNonEmptyString(data.heroImage.alt) || !isNonEmptyString(data.heroImage.src)) throw new Error('Imagen de portada inválida.');
    localImagePath(data.heroImage.src);
    if (data.heroImage.smallSrc !== undefined) {
      if (!isNonEmptyString(data.heroImage.smallSrc)) throw new Error('Ruta de portada alternativa inválida.');
      localImagePath(data.heroImage.smallSrc);
    }
  }
}

function photograph(photo) {
  const figure = element('figure', 'menu-photo');
  const image = element('img');
  image.src = localImagePath(photo.src);
  if (photo.smallSrc) image.srcset = `${localImagePath(photo.smallSrc)} 480w, ${localImagePath(photo.src)} 960w`;
  image.sizes = '(max-width: 600px) calc(100vw - 40px), (max-width: 1000px) 45vw, 35vw';
  image.alt = photo.alt;
  image.width = photo.width;
  image.height = photo.height;
  image.loading = 'lazy';
  image.decoding = 'async';
  image.addEventListener('error', () => {
    image.remove();
    figure.classList.add('menu-photo-unavailable');
    figure.prepend(element('p', '', 'Fotografía no disponible'));
  }, { once: true });
  figure.append(image, element('figcaption', '', 'Fotografía ilustrativa'));
  return figure;
}

function productList(category, data) {
  const list = element('ul', 'menu-product-list');
  for (const product of category.products) {
    const item = element('li', 'menu-product');
    const description = element('div', 'menu-product-copy');
    description.append(element('h3', '', product.name), element('p', '', product.description));
    let price = 'Por confirmar';
    if (data.status !== 'demo' && data.currency && Number.isFinite(product.price) && product.price >= 0) {
      price = new Intl.NumberFormat('es', { style: 'currency', currency: data.currency }).format(product.price);
    }
    item.append(description, element('span', 'menu-price', price));
    if (product.image) item.append(photograph(product.image));
    list.append(item);
  }
  return list;
}

function categoryHeading(category, index) {
  const header = element('div', 'menu-category-heading');
  const heading = element('h2', '', category.name);
  heading.id = `heading-${category.id}`;
  header.append(element('span', 'menu-category-number', String(index + 1).padStart(2, '0')), heading, element('p', 'menu-category-eyebrow', category.eyebrow));
  return header;
}

function credits(categories) {
  const list = document.getElementById('photo-credits');
  const seen = new Set();
  const entries = categories.flatMap(category => [
    { label: category.name, photo: category.image },
    ...category.products.filter(product => product.image).map(product => ({ label: product.name, photo: product.image })),
  ]);
  for (const entry of entries) {
    const photo = entry.photo;
    if (!photo || seen.has(photo.source)) continue;
    seen.add(photo.source);
    const row = element('li');
    const source = element('a', '', `${entry.label}: ${photo.author}`);
    source.href = photo.source;
    const license = element('a', '', photo.license);
    license.href = photo.licenseUrl;
    row.append(source, document.createTextNode(' · '), license);
    list.append(row);
  }
}

async function loadMenu() {
  try {
    const response = await fetch(new URL('./menu-data.json', import.meta.url), { cache: 'no-store' });
    if (!response.ok) throw new Error('No se pudo leer el catálogo.');
    const data = await response.json();
    validateMenu(data);
    document.getElementById('demo-notice').textContent = data.notice;
    for (const [index, category] of data.categories.entries()) {
      const section = document.getElementById(category.id);
      if (!section || !Array.isArray(category.products)) throw new Error('Categoría inválida.');
      const content = category.id === 'parrilla' ? section.querySelector('.category-content') : section;
      content.append(categoryHeading(category, index), productList(category, data));
      if (category.image) {
        const target = category.id === 'parrilla' ? section.querySelector('.category-photo') : section;
        target.append(photograph(category.image));
      }
    }
    if (data.heroImage) {
      const hero = document.getElementById('menu-hero-image');
      hero.src = localImagePath(data.heroImage.src);
      if (data.heroImage.smallSrc) hero.srcset = `${localImagePath(data.heroImage.smallSrc)} 960w, ${localImagePath(data.heroImage.src)} 1440w`;
      hero.sizes = '100vw';
      hero.alt = data.heroImage.alt;
      hero.hidden = false;
      hero.addEventListener('error', () => { hero.hidden = true; }, { once: true });
    }
    credits(data.categories);
    document.getElementById('menu-loading').hidden = true;
  } catch {
    document.getElementById('menu-loading').hidden = true;
    for (const section of document.querySelectorAll('.menu-feature, .menu-food-grid, .menu-drinks, .menu-category-navigation, .menu-hero-link')) section.hidden = true;
    document.getElementById('menu-error').hidden = false;
  } finally {
    menuContent.setAttribute('aria-busy', 'false');
  }
}

loadMenu();