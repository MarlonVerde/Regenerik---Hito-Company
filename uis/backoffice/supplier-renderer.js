(function initializeSupplierRenderer(root) {
  function appendCell(row, value) {
    const cell = root.document.createElement('td');
    cell.textContent = value == null ? '' : String(value);
    row.appendChild(cell);
    return cell;
  }

  function buildSupplierRow(supplier) {
    const row = root.document.createElement('tr');
    appendCell(row, supplier.name);
    appendCell(row, supplier.country);
    appendCell(row, Array.isArray(supplier.categories) ? supplier.categories.join(', ') : '');
    appendCell(row, supplier.rate_per_unit);
    appendCell(row, supplier.currency);

    const statusCell = appendCell(row, '');
    const badge = root.document.createElement('span');
    badge.className = `status-badge ${supplier.status}`;
    badge.textContent = supplier.status;
    statusCell.appendChild(badge);

    const actionsCell = root.document.createElement('td');
    const actions = root.document.createElement('div');
    actions.className = 'row-actions';

    const rateForm = root.document.createElement('form');
    rateForm.className = 'inline-rate';
    rateForm.dataset.action = 'rate';
    rateForm.dataset.id = String(supplier.id);
    const rateInput = root.document.createElement('input');
    rateInput.name = 'rate';
    rateInput.type = 'number';
    rateInput.min = '0.01';
    rateInput.step = '0.01';
    rateInput.value = String(supplier.rate_per_unit);
    rateInput.required = true;
    const rateButton = root.document.createElement('button');
    rateButton.className = 'btn';
    rateButton.type = 'submit';
    rateButton.textContent = 'Tarifa';
    rateForm.append(rateInput, rateButton);

    const nextStatus = supplier.status === 'active' ? 'suspended' : 'active';
    const statusButton = root.document.createElement('button');
    statusButton.className = 'btn';
    statusButton.dataset.action = 'status';
    statusButton.dataset.id = String(supplier.id);
    statusButton.dataset.status = nextStatus;
    statusButton.textContent = nextStatus === 'active' ? 'Activar' : 'Suspender';

    actions.append(rateForm, statusButton);
    actionsCell.appendChild(actions);
    row.appendChild(actionsCell);
    return row;
  }

  const renderer = { buildSupplierRow };
  root.BackofficeSupplierRenderer = renderer;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = renderer;
  }
})(typeof window !== 'undefined' ? window : globalThis);
