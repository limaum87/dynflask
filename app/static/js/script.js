/**
 * DynFlask — Frontend Scripts (Vanilla JS)
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize Lucide icons
  lucide.createIcons();
});

// ============================
// Sidebar
// ============================

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (!sidebar || !overlay) return;

  const isOpen = !sidebar.classList.contains('-translate-x-full');
  if (isOpen) {
    sidebar.classList.add('-translate-x-full');
    overlay.classList.add('hidden');
  } else {
    sidebar.classList.remove('-translate-x-full');
    overlay.classList.remove('hidden');
  }
}

// Close sidebar on resize to desktop
window.addEventListener('resize', () => {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (!sidebar || !overlay) return;

  if (window.innerWidth >= 1024) {
    sidebar.classList.remove('-translate-x-full');
    overlay.classList.add('hidden');
  } else {
    sidebar.classList.add('-translate-x-full');
  }
});

// ============================
// Modal
// ============================

function openModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
  // Re-initialize icons inside modal
  setTimeout(() => lucide.createIcons(), 50);
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.add('hidden');
  document.body.style.overflow = '';
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('[id$="-modal"]:not(.hidden)').forEach((modal) => {
      closeModal(modal.id);
    });
  }
});

// ============================
// Edit Host Modal
// ============================

function openEditModal(hostId, hostname, recordType, ttl, provider) {
  const form = document.getElementById('edit-form');
  const hostnameInput = document.getElementById('edit-hostname');
  const recordTypeSelect = document.getElementById('edit-record-type');
  const ttlInput = document.getElementById('edit-ttl');
  const providerSelect = document.getElementById('edit-provider');

  if (!form || !hostnameInput || !recordTypeSelect || !ttlInput) return;

  form.action = `/edit/${hostId}`;
  hostnameInput.value = hostname;
  recordTypeSelect.value = recordType;
  ttlInput.value = ttl;
  if (providerSelect) providerSelect.value = provider || 'cloudflare';

  openModal('edit-modal');
}

// ============================
// Delete Host Modal
// ============================

function openDeleteModal(hostId, hostname) {
  const form = document.getElementById('delete-form');
  const hostnameEl = document.getElementById('delete-hostname');

  if (!form || !hostnameEl) return;

  form.action = `/delete/${hostId}`;
  hostnameEl.textContent = hostname;

  openModal('delete-modal');
}

// ============================
// Copy Token
// ============================

function copyToken(token, element) {
  navigator.clipboard.writeText(token).then(() => {
    // Show feedback
    const codeEl = element.closest('div')?.querySelector('code');
    if (codeEl) {
      codeEl.classList.add('copied');
      setTimeout(() => codeEl.classList.remove('copied'), 2000);
    }

    // Show tooltip on the button
    if (element.tagName === 'BUTTON') {
      const originalHTML = element.innerHTML;
      element.innerHTML = '<i data-lucide="check" class="h-3.5 w-3.5 text-emerald-500"></i>';
      lucide.createIcons();
      setTimeout(() => {
        element.innerHTML = originalHTML;
        lucide.createIcons();
      }, 2000);
    }
  }).catch((err) => {
    // Fallback: select text
    const codeEl = element.closest('div')?.querySelector('code');
    if (codeEl) {
      const range = document.createRange();
      range.selectNodeContents(codeEl);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
    }
  });
}

// ============================
// Password visibility toggle
// ============================

function togglePasswordVisibility(inputId, button) {
  const input = document.getElementById(inputId);
  if (!input) return;

  if (input.type === 'password') {
    input.type = 'text';
    button.innerHTML = '<i data-lucide="eye-off" class="h-4 w-4"></i>';
  } else {
    input.type = 'password';
    button.innerHTML = '<i data-lucide="eye" class="h-4 w-4"></i>';
  }
  lucide.createIcons();
}

// ============================
// Auto-dismiss flash messages
// ============================

document.addEventListener('DOMContentLoaded', () => {
  const flashMessages = document.querySelectorAll('.flash-enter');
  if (flashMessages.length > 0) {
    setTimeout(() => {
      flashMessages.forEach((el) => {
        el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        el.style.opacity = '0';
        el.style.transform = 'translateY(-8px)';
        setTimeout(() => el.remove(), 500);
      });
    }, 6000);
  }
});
