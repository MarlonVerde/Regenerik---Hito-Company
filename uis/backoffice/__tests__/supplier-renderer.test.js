const { buildSupplierRow } = require('../supplier-renderer');

class FakeElement {
  constructor(tagName) {
    this.tagName = tagName;
    this.children = [];
    this.dataset = {};
    this.textContent = '';
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }

  append(...children) {
    children.forEach((child) => this.appendChild(child));
  }

  replaceChildren(...children) {
    this.children = children;
  }

  set innerHTML(value) {
    throw new Error(`Unsafe HTML assignment attempted: ${value}`);
  }
}

describe('supplier renderer', () => {
  beforeEach(() => {
    global.document = { createElement: (tagName) => new FakeElement(tagName) };
  });

  afterEach(() => {
    delete global.document;
  });

  test('renders a supplier name containing script markup as inert text', () => {
    const payload = "<script>alert('XSS')</script>";
    const row = buildSupplierRow({
      id: 'supplier-1',
      name: payload,
      country: 'Colombia',
      categories: ['carne'],
      rate_per_unit: 10,
      currency: 'COP',
      status: 'active',
    });

    expect(row.children[0].textContent).toBe(payload);
    expect(row.children.some((child) => child.tagName === 'script')).toBe(false);
    expect(row.children[0].children).toHaveLength(0);
  });
});