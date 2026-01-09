// AgenticOCR - Main JavaScript

// API Base URL
const API_BASE = window.location.origin;

// Get auth token from localStorage
function getAuthToken() {
  return localStorage.getItem('auth_token');
}

// Set auth token
function setAuthToken(token) {
  localStorage.setItem('auth_token', token);
}

// Clear auth token
function clearAuthToken() {
  localStorage.removeItem('auth_token');
}

// API Request Helper
async function apiRequest(endpoint, options = {}) {
  const token = getAuthToken();

  const headers = {
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      // Unauthorized - redirect to login
      clearAuthToken();
      window.location.href = '/login';
      return null;
    }

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error?.message || data.detail || 'Request failed');
    }

    return data;
  } catch (error) {
    console.error('API Request failed:', error);
    throw error;
  }
}

// Show toast notification
function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `alert alert-${type}`;
  toast.style.position = 'fixed';
  toast.style.top = '20px';
  toast.style.right = '20px';
  toast.style.zIndex = '9999';
  toast.style.minWidth = '300px';
  toast.innerHTML = `
    <strong>${type === 'success' ? '✓' : '✗'}</strong>
    <span>${message}</span>
  `;

  document.body.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 4000);
}

// Modal functions
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
  }
}

// Copy to clipboard
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('Copied to clipboard!', 'success');
  }).catch(() => {
    showToast('Failed to copy', 'danger');
  });
}

// Format date
function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

// Format currency
function formatCurrency(cents, currency = 'USD') {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
  }).format(cents / 100);
}

// Format bytes
function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Show loading state
function showLoading(element) {
  element.disabled = true;
  element.innerHTML = '<span class="loading"></span> Loading...';
}

// Hide loading state
function hideLoading(element, originalText) {
  element.disabled = false;
  element.innerHTML = originalText;
}

// File upload handler
function handleFileUpload(inputElement, callback) {
  inputElement.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      callback(file);
    }
  });
}

// Initialize tooltips
function initTooltips() {
  const tooltips = document.querySelectorAll('[data-tooltip]');
  tooltips.forEach(el => {
    el.addEventListener('mouseenter', (e) => {
      const tooltip = document.createElement('div');
      tooltip.className = 'tooltip';
      tooltip.textContent = el.dataset.tooltip;
      document.body.appendChild(tooltip);

      const rect = el.getBoundingClientRect();
      tooltip.style.position = 'fixed';
      tooltip.style.top = `${rect.bottom + 5}px`;
      tooltip.style.left = `${rect.left}px`;
    });

    el.addEventListener('mouseleave', () => {
      const tooltip = document.querySelector('.tooltip');
      if (tooltip) tooltip.remove();
    });
  });
}

// Pagination handler
class Pagination {
  constructor(totalItems, itemsPerPage, onPageChange) {
    this.totalItems = totalItems;
    this.itemsPerPage = itemsPerPage;
    this.currentPage = 1;
    this.onPageChange = onPageChange;
  }

  getTotalPages() {
    return Math.ceil(this.totalItems / this.itemsPerPage);
  }

  goToPage(page) {
    if (page >= 1 && page <= this.getTotalPages()) {
      this.currentPage = page;
      this.onPageChange(page);
      this.render();
    }
  }

  render(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const totalPages = this.getTotalPages();
    let html = '<div class="pagination">';

    // Previous button
    html += `<button class="btn btn-sm btn-secondary" ${this.currentPage === 1 ? 'disabled' : ''} onclick="pagination.goToPage(${this.currentPage - 1})">Previous</button>`;

    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
      if (i === 1 || i === totalPages || (i >= this.currentPage - 2 && i <= this.currentPage + 2)) {
        html += `<button class="btn btn-sm ${i === this.currentPage ? 'btn-primary' : 'btn-secondary'}" onclick="pagination.goToPage(${i})">${i}</button>`;
      } else if (i === this.currentPage - 3 || i === this.currentPage + 3) {
        html += '<span>...</span>';
      }
    }

    // Next button
    html += `<button class="btn btn-sm btn-secondary" ${this.currentPage === totalPages ? 'disabled' : ''} onclick="pagination.goToPage(${this.currentPage + 1})">Next</button>`;

    html += '</div>';
    container.innerHTML = html;
  }
}

// Search and filter handler
function setupSearchFilter(inputId, tableId, columnIndices = [0]) {
  const input = document.getElementById(inputId);
  const table = document.getElementById(tableId);

  if (!input || !table) return;

  input.addEventListener('keyup', function() {
    const filter = this.value.toLowerCase();
    const rows = table.getElementsByTagName('tr');

    for (let i = 1; i < rows.length; i++) {
      let shouldShow = false;

      columnIndices.forEach(colIndex => {
        const cell = rows[i].getElementsByTagName('td')[colIndex];
        if (cell) {
          const text = cell.textContent || cell.innerText;
          if (text.toLowerCase().indexOf(filter) > -1) {
            shouldShow = true;
          }
        }
      });

      rows[i].style.display = shouldShow ? '' : 'none';
    }
  });
}

// Form validation
function validateForm(formElement) {
  const inputs = formElement.querySelectorAll('input[required], textarea[required], select[required]');
  let isValid = true;

  inputs.forEach(input => {
    if (!input.value.trim()) {
      input.classList.add('error');
      isValid = false;
    } else {
      input.classList.remove('error');
    }
  });

  return isValid;
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
  // Initialize tooltips
  initTooltips();

  // Setup mobile menu toggle
  const menuToggle = document.getElementById('menuToggle');
  const sidebar = document.querySelector('.sidebar');

  if (menuToggle && sidebar) {
    menuToggle.addEventListener('click', () => {
      sidebar.classList.toggle('mobile-open');
    });
  }

  // Close modals on outside click
  window.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
      e.target.classList.remove('active');
    }
  });

  // Setup logout button
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      clearAuthToken();
      window.location.href = '/login';
    });
  }
});

// Export for use in other scripts
window.agenticOCR = {
  apiRequest,
  showToast,
  openModal,
  closeModal,
  copyToClipboard,
  formatDate,
  formatCurrency,
  formatBytes,
  showLoading,
  hideLoading,
  handleFileUpload,
  setupSearchFilter,
  validateForm,
  Pagination,
};
