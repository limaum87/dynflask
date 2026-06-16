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
  setTimeout(() => lucide.createIcons(), 50);
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.add('hidden');
  document.body.style.overflow = '';
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('[id$="-modal"]:not(.hidden)').forEach((modal) => {
      closeModal(modal.id);
    });
  }
});

// ============================
// Zone Modals
// ============================

function openEditZoneModal(zoneId, name, provider) {
  const form = document.getElementById('edit-zone-form');
  const nameInput = document.getElementById('edit-zone-name');
  const providerSelect = document.getElementById('edit-zone-provider');
  if (!form || !nameInput || !providerSelect) return;

  form.action = `/zones/edit/${zoneId}`;
  nameInput.value = name;
  providerSelect.value = provider;
  openModal('edit-zone-modal');
}

function openDeleteZoneModal(zoneId, name) {
  const form = document.getElementById('delete-zone-form');
  const nameEl = document.getElementById('delete-zone-name');
  if (!form || !nameEl) return;

  form.action = `/zones/delete/${zoneId}`;
  nameEl.textContent = name;
  openModal('delete-zone-modal');
}

// ============================
// Host Modals
// ============================

function openEditModal(hostId, hostname, recordType, ttl, value = '') {
  const form = document.getElementById('edit-form');
  const hostnameInput = document.getElementById('edit-hostname');
  const recordTypeSelect = document.getElementById('edit-record-type');
  const ttlInput = document.getElementById('edit-ttl');
  const valueInput = document.getElementById('edit-value');

  if (!form || !hostnameInput || !recordTypeSelect || !ttlInput || !valueInput) return;

  form.action = `/host/edit/${hostId}`;
  hostnameInput.value = hostname;
  recordTypeSelect.value = recordType;
  ttlInput.value = ttl;
  valueInput.value = value;
  openModal('edit-modal');
}

function openDeleteModal(hostId, hostname) {
  const form = document.getElementById('delete-form');
  const hostnameEl = document.getElementById('delete-hostname');
  if (!form || !hostnameEl) return;

  form.action = `/host/delete/${hostId}`;
  hostnameEl.textContent = hostname;
  openModal('delete-modal');
}

// ============================
// Copy Token
// ============================

function copyToken(token, element) {
  navigator.clipboard.writeText(token).then(() => {
    const codeEl = element.closest('div')?.querySelector('code');
    if (codeEl) {
      codeEl.classList.add('copied');
      setTimeout(() => codeEl.classList.remove('copied'), 2000);
    }

    if (element.tagName === 'BUTTON') {
      const originalHTML = element.innerHTML;
      element.innerHTML = '<i data-lucide="check" class="h-3.5 w-3.5 text-emerald-500"></i>';
      lucide.createIcons();
      setTimeout(() => {
        element.innerHTML = originalHTML;
        lucide.createIcons();
      }, 2000);
    }
  }).catch(() => {
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
// Test Provider Connection
// ============================

function testProvider(provider) {
  const resultEl = document.getElementById(`test-result-${provider}`);
  if (!resultEl) return;

  // Show loading
  resultEl.classList.remove('hidden');
  resultEl.innerHTML = `
    <div class="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
      <svg class="h-4 w-4 animate-spin text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
      </svg>
      <span class="text-sm font-medium text-blue-700">Testando conexão...</span>
    </div>`;

  fetch(`/api/test-provider/${provider}`)
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success') {
        resultEl.innerHTML = `
          <div class="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 space-y-2">
            <div class="flex items-center gap-2">
              <i data-lucide="check-circle-2" class="h-4 w-4 text-emerald-600"></i>
              <span class="text-sm font-semibold text-emerald-700">Conexão OK!</span>
            </div>
            <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-[12px] text-emerald-800">
              <span class="text-emerald-600">Zona:</span>
              <span class="font-mono font-semibold">${data.zone_name}</span>
              <span class="text-emerald-600">Zone ID:</span>
              <span class="font-mono">${data.zone_id}</span>
              ${data.record_count !== undefined ? `<span class="text-emerald-600">Registros:</span><span>${data.record_count}</span>` : ''}
              ${data.comment ? `<span class="text-emerald-600">Comentário:</span><span>${data.comment}</span>` : ''}
            </div>
          </div>`;
      } else {
        resultEl.innerHTML = `
          <div class="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
            <i data-lucide="x-circle" class="h-4 w-4 text-red-600 mt-0.5 shrink-0"></i>
            <div>
              <p class="text-sm font-semibold text-red-700">Falha na conexão</p>
              <p class="text-[12px] text-red-600 mt-1">${data.message}</p>
            </div>
          </div>`;
      }
      lucide.createIcons();
    })
    .catch(err => {
      resultEl.innerHTML = `
        <div class="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <i data-lucide="x-circle" class="h-4 w-4 text-red-600"></i>
          <span class="text-sm text-red-700">Erro ao testar: ${err}</span>
        </div>`;
      lucide.createIcons();
    });
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
