(function initializeInventoryPages() {
  const api = window.BackofficeInventoryApi;
  const pageName = document.body.dataset.inventoryPage;
  const LOW_STOCK_THRESHOLD = 5;
  const productStatus = document.getElementById('pageStatus');
  const currentUser = document.getElementById('currentUser');
  const logoutButton = document.getElementById('logoutBtn');
  let products = [];

  function setStatus(node, message, type = '') {
    node.textContent = message;
    node.className = `status ${type}`.trim();
  }

  function createCell(value) {
    const cell = document.createElement('td');
    cell.textContent = value == null || value === '' ? '—' : String(value);
    return cell;
  }

  function formatQuantity(value) {
    return new Intl.NumberFormat('es-CO', { maximumFractionDigits: 2 }).format(Number(value) || 0);
  }

  function formatDate(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('es-CO');
  }

  async function refreshProducts() {
    setStatus(productStatus, 'Cargando productos...', 'warn');
    try {
      products = await api.getProducts();
      setStatus(productStatus, `${products.length} productos cargados.`, 'ok');
      return true;
    } catch (error) {
      setStatus(productStatus, error.message || 'No se pudieron cargar los productos.', 'error');
      return false;
    }
  }

  function addOrderLink(row, productId, orderType, label) {
    const cell = document.createElement('td');
    const link = document.createElement('a');
    const route = orderType === 'inbound' ? '../orders/inbound/' : '../orders/outbound/';
    link.className = 'btn btn-small';
    link.href = `${route}?product=${encodeURIComponent(productId)}`;
    link.textContent = label;
    cell.appendChild(link);
    row.appendChild(cell);
  }

  function renderProducts() {
    const body = document.querySelector('#productsTable tbody');
    body.replaceChildren();

    if (!products.length) {
      const row = document.createElement('tr');
      const cell = createCell('No hay productos registrados.');
      cell.colSpan = 8;
      row.appendChild(cell);
      body.appendChild(row);
      return;
    }

    products.forEach((product) => {
      const row = document.createElement('tr');
      row.append(
        createCell(product.name),
        createCell(product.sku),
        createCell(product.category),
        createCell(product.country),
        createCell(product.unit),
      );

      const stockCell = document.createElement('td');
      const stock = Number(product.current_stock) || 0;
      const indicator = document.createElement('span');
      const lowStock = stock <= LOW_STOCK_THRESHOLD;
      indicator.className = `stock-indicator ${lowStock ? 'stock-low' : 'stock-healthy'}`;
      indicator.textContent = `${lowStock ? 'Bajo' : 'Saludable'}: ${formatQuantity(stock)} ${product.unit}`;
      stockCell.appendChild(indicator);
      row.appendChild(stockCell);

      addOrderLink(row, product.id, 'inbound', 'Registrar entrada');
      addOrderLink(row, product.id, 'outbound', 'Registrar salida');
      body.appendChild(row);
    });
  }

  function fillLocationOptions(select) {
    for (let locationId = 1; locationId <= 14; locationId += 1) {
      const option = document.createElement('option');
      option.value = String(locationId);
      option.textContent = `Sede ${String(locationId).padStart(2, '0')}`;
      select.appendChild(option);
    }
  }

  function fillProductOptions(select) {
    products
      .slice()
      .sort((first, second) => first.name.localeCompare(second.name, 'es'))
      .forEach((product) => {
        const option = document.createElement('option');
        option.value = String(product.id);
        option.textContent = `${product.name} (${product.sku})`;
        select.appendChild(option);
      });

    const requestedProduct = new URLSearchParams(window.location.search).get('product');
    if (requestedProduct && products.some((product) => String(product.id) === requestedProduct)) {
      select.value = requestedProduct;
    }
  }

  function initializeInboundForm() {
    const form = document.getElementById('inboundForm');
    const productSelect = form.elements.ingredient_id;
    const locationSelect = form.elements.location_id;
    const status = document.getElementById('formStatus');
    const submitButton = form.querySelector('button[type="submit"]');

    fillProductOptions(productSelect);
    fillLocationOptions(locationSelect);
    submitButton.disabled = products.length === 0;
    if (!products.length) {
      setStatus(status, 'Registra primero un producto para crear una entrada.', 'warn');
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      submitButton.disabled = true;
      setStatus(status, 'Registrando entrada...', 'warn');
      const payload = {
        ingredient_id: Number(productSelect.value),
        quantity: Number(form.elements.quantity.value),
        supplier_name: form.elements.supplier_name.value.trim(),
        location_id: Number(locationSelect.value),
      };

      try {
        await api.createInboundOrder(payload);
        form.reset();
        setStatus(status, 'Entrada registrada correctamente.', 'ok');
        await refreshProducts();
      } catch (error) {
        setStatus(status, `No se pudo registrar la entrada: ${error.message}`, 'error');
      } finally {
        submitButton.disabled = products.length === 0;
      }
    });
  }

  function initializeOutboundForm() {
    const form = document.getElementById('outboundForm');
    const productSelect = form.elements.ingredient_id;
    const quantityInput = form.elements.quantity;
    const quantityFeedback = document.getElementById('quantityFeedback');
    const stockValue = document.getElementById('selectedStock');
    const status = document.getElementById('formStatus');
    const submitButton = form.querySelector('button[type="submit"]');

    fillProductOptions(productSelect);
    fillLocationOptions(form.elements.location_id);
    submitButton.disabled = products.length === 0;

    function selectedProduct() {
      return products.find((product) => String(product.id) === productSelect.value);
    }

    function updateSelectedStock() {
      const product = selectedProduct();
      if (!product) {
        stockValue.textContent = 'Selecciona un producto';
        quantityFeedback.textContent = '';
        quantityFeedback.className = 'field-feedback';
        return;
      }

      const stock = Number(product.current_stock) || 0;
      stockValue.textContent = `${formatQuantity(stock)} ${product.unit}`;
      const requestedQuantity = Number(quantityInput.value);
      if (quantityInput.value && requestedQuantity > stock) {
        quantityFeedback.textContent = 'La cantidad supera el stock disponible.';
        quantityFeedback.className = 'field-feedback error';
      } else {
        quantityFeedback.textContent = `Disponible: ${formatQuantity(stock)} ${product.unit}`;
        quantityFeedback.className = 'field-feedback';
      }
    }

    productSelect.addEventListener('change', updateSelectedStock);
    quantityInput.addEventListener('input', updateSelectedStock);
    updateSelectedStock();

    if (!products.length) {
      setStatus(status, 'No hay productos disponibles para registrar una salida.', 'warn');
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const product = selectedProduct();
      const quantity = Number(quantityInput.value);
      if (!product) {
        setStatus(status, 'Selecciona un producto.', 'error');
        return;
      }
      if (quantity > Number(product.current_stock)) {
        quantityFeedback.textContent = 'La cantidad supera el stock disponible.';
        quantityFeedback.className = 'field-feedback error';
        quantityInput.focus();
        return;
      }

      submitButton.disabled = true;
      setStatus(status, 'Registrando salida...', 'warn');
      const payload = {
        ingredient_id: Number(productSelect.value),
        quantity,
        reason: form.elements.reason.value,
        location_id: Number(form.elements.location_id.value),
      };

      try {
        await api.createOutboundOrder(payload);
        form.reset();
        setStatus(status, 'Salida registrada correctamente.', 'ok');
        await refreshProducts();
        updateSelectedStock();
      } catch (error) {
        setStatus(status, `No se pudo registrar la salida: ${error.message}`, 'error');
        if (error.status === 400) {
          quantityFeedback.textContent = error.message;
          quantityFeedback.className = 'field-feedback error';
        }
      } finally {
        submitButton.disabled = products.length === 0;
      }
    });
  }

  async function loadOrders() {
    const body = document.querySelector('#ordersTable tbody');
    setStatus(productStatus, 'Cargando historial...', 'warn');
    try {
      const orders = await api.getOrders();
      body.replaceChildren();
      if (!orders.length) {
        const row = document.createElement('tr');
        const cell = createCell('Aún no hay movimientos de inventario.');
        cell.colSpan = 5;
        row.appendChild(cell);
        body.appendChild(row);
      } else {
        orders.forEach((order) => {
          const row = document.createElement('tr');
          row.append(
            createCell(order.ingredient?.name),
            createCell(formatQuantity(order.quantity)),
            createCell(order.movement_type === 'inbound' ? 'Entrada' : 'Salida'),
            createCell(formatDate(order.created_at)),
            createCell(order.user_uuid),
          );
          body.appendChild(row);
        });
      }
      setStatus(productStatus, `${orders.length} movimientos cargados.`, 'ok');
    } catch (error) {
      setStatus(productStatus, error.message || 'No se pudo cargar el historial.', 'error');
    }
  }

  async function initialize() {
    try {
      const user = await api.ensureAuthenticated();
      currentUser.textContent = `${user.email} (${user.role})`;
      logoutButton.addEventListener('click', () => {
        window.localStorage.removeItem('brasaland.jwt');
        window.location.href = `${window.location.pathname.split('/uis/backoffice/')[0]}/uis/backoffice/login/`;
      });

      if (pageName === 'products') {
        if (await refreshProducts()) renderProducts();
      } else if (pageName === 'inbound') {
        if (await refreshProducts()) initializeInboundForm();
      } else if (pageName === 'outbound') {
        if (await refreshProducts()) initializeOutboundForm();
      } else if (pageName === 'orders') {
        await loadOrders();
      }
    } catch (error) {
      setStatus(productStatus, error.message || 'No se pudo validar la sesión.', 'error');
    }
  }

  initialize();
})();