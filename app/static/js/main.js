/**
 * Audiobookarr – shared JavaScript utilities
 */

/** Show a dismissible alert in #alert-container. */
function showAlert(type, message) {
  const container = document.getElementById('alert-container');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `alert alert-${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

/** HTML-escape a string for safe insertion with innerHTML. */
function escHtml(str) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}
