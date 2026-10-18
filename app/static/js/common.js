/**
 * SaaS Admin Dashboard - Common Interactivity & Utility Helpers
 */

/**
 * Display a dynamic Bootstrap toast alert
 * @param {string} message - Toast message text
 * @param {string} type - 'success', 'danger', 'warning', 'info'
 */
function showToast(message, type = 'success') {
  let toastContainer = document.querySelector('.toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
    document.body.appendChild(toastContainer);
  }

  const bgClass = type === 'danger' ? 'bg-danger text-white' :
                  type === 'success' ? 'bg-success text-white' :
                  type === 'warning' ? 'bg-warning text-dark' :
                  'bg-info text-white';

  const iconClass = type === 'danger' ? 'bi-exclamation-octagon-fill' :
                    type === 'success' ? 'bi-check-circle-fill' :
                    type === 'warning' ? 'bi-exclamation-triangle-fill' :
                    'bi-info-circle-fill';

  const toastId = 'toast-' + Math.random().toString(36).substring(2, 9);
  const toastHtml = `
    <div id="${toastId}" class="toast align-items-center ${bgClass} border-0 shadow-lg" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="d-flex">
        <div class="toast-body d-flex align-items-center">
          <i class="bi ${iconClass} me-2 fs-5"></i>
          <span>${message}</span>
        </div>
        <button type="button" class="btn-close ${type !== 'warning' ? 'btn-close-white' : ''} me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>
  `;

  toastContainer.insertAdjacentHTML('beforeend', toastHtml);
  const toastElement = document.getElementById(toastId);
  const bsToast = new bootstrap.Toast(toastElement, { delay: 4000 });
  bsToast.show();

  toastElement.addEventListener('hidden.bs.toast', () => {
    toastElement.remove();
  });
}

/**
 * Handle resource deletion via fetch with CSRF protection and UX confirmation
 * @param {string} url - Target DELETE endpoint URL
 * @param {string} itemName - Name of item being deleted for confirmation prompt
 */
function confirmDelete(url, itemName) {
  if (!confirm(`Are you sure you want to delete ${itemName}? This action cannot be undone.`)) {
    return;
  }

  const csrfMeta = document.querySelector('meta[name="csrf-token"]');
  let csrfToken = csrfMeta ? csrfMeta.content : '';

  if (!csrfToken) {
    const cookies = document.cookie.split('; ');
    const csrfCookie = cookies.find(row => row.startsWith('csrf_token='));
    if (csrfCookie) {
      csrfToken = csrfCookie.split('=')[1];
    }
  }

  fetch(url, {
    method: 'DELETE',
    headers: {
      'X-CSRF-Token': csrfToken,
      'Accept': 'application/json'
    }
  })
  .then(async response => {
    if (response.ok) {
      showToast(`${itemName} deleted successfully.`, 'success');
      setTimeout(() => {
        location.reload();
      }, 500);
    } else {
      let errorMsg = 'Failed to delete item.';
      try {
        const data = await response.json();
        if (data && data.detail) {
          errorMsg = data.detail;
        }
      } catch (e) {
        // Fallback to HTTP status
        errorMsg = `Server returned status ${response.status}`;
      }
      showToast(errorMsg, 'danger');
    }
  })
  .catch(err => {
    console.error('Delete error:', err);
    showToast('A network error occurred while attempting to delete.', 'danger');
  });
}

/**
 * Global initialization
 */
document.addEventListener('DOMContentLoaded', () => {
  // Mobile sidebar toggler & backdrop
  const toggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');

  if (toggle && sidebar) {
    toggle.addEventListener('click', () => {
      sidebar.classList.toggle('show');
      if (backdrop) {
        backdrop.classList.toggle('show');
      }
    });
  }

  if (backdrop && sidebar) {
    backdrop.addEventListener('click', () => {
      sidebar.classList.remove('show');
      backdrop.classList.remove('show');
    });
  }

  // Auto-show server rendered flash toasts if present
  document.querySelectorAll('.toast').forEach(toastEl => {
    const bsToast = new bootstrap.Toast(toastEl, { delay: 5000 });
    bsToast.show();
  });
});
