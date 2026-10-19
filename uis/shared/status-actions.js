(function initializeStatusActions(root) {
  function render(parent, { label, onAction, href }) {
    parent.querySelector('.status-actions')?.remove();
    const actions = root.document.createElement('div');
    actions.className = 'status-actions';
    actions.style.marginTop = '8px';
    const control = root.document.createElement(href ? 'a' : 'button');
    control.textContent = label;
    control.className = 'btn btn-small';
    if (href) {
      control.href = href;
    } else {
      control.type = 'button';
      control.onclick = (event) => {
        event.preventDefault();
        onAction();
      };
    }
    actions.appendChild(control);
    parent.appendChild(actions);
    return actions;
  }

  root.BrasalandStatusActions = { render };
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { render };
  }
})(typeof window !== 'undefined' ? window : globalThis);