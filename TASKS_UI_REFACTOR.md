# Tasks: Refatoração Visual — Dashboard SaaS Moderno (Shadcn UI + Tailwind CSS)

## Objetivo

Transformar a UI atual do DynFlask (baseada em AdminLTE/Bootstrap 4) em um layout moderno de dashboard SaaS, com visual inspirado em **Shadcn UI + Tailwind CSS**, mantendo toda a lógica de negócio intocada.

---

## Análise do Estado Atual

### Stack visual atual
| Item | Atual |
|---|---|
| Framework CSS | AdminLTE 3.2 + Bootstrap 4 |
| Ícones | Font Awesome 6.4 |
| Fonte | Source Sans Pro |
| JS | jQuery 3.7 + Bootstrap JS |
| CSS customizado | Mínimo (`style.css` com 8 linhas) |
| JS customizado | Mínimo (`script.js` com 1 `console.log`) |

### Páginas/Componentes existentes
| Arquivo | Função |
|---|---|
| `layout.html` | Layout base com sidebar, navbar, footer |
| `index.html` | Dashboard — formulário de adicionar host + tabela de hosts + modais de edição |
| `login.html` | Página de login standalone (não herda de layout) |
| `settings.html` | Formulário de configurações Cloudflare (Zone ID + API Token) |

### Componentes visuais identificados
1. **Layout base** — sidebar escura + navbar clara + content wrapper
2. **Sidebar** — logo, info do usuário, menu de navegação (Dashboard, Configurações)
3. **Navbar/Header** — botão toggle menu + logout
4. **Cards** — com header e body (usados em formulários e tabelas)
5. **Formulários** — inputs, selects, labels, help text
6. **Tabela** — listagem de hosts com ações (editar/excluir)
7. **Modal** — edição de host (inline por host, um modal por linha)
8. **Botões** — primary, warning, danger, sm
9. **Alertas flash** — sucesso, erro, etc.
10. **Página de login** — card centralizado com inputs e botão

### Problemas da UI atual
- Visual datado (AdminLTE tem cara de painel antigo)
- Bootstrap 4 é legado (atual é 5)
- jQuery como dependência apenas para toggle de sidebar
- Modais inline na tabela (um modal `<div>` por linha — polui o DOM)
- CSS customizado quase inexistente
- Sidebar dark-primary com visual pesado
- Sem responsividade refinada para mobile
- Sem dark mode
- Sem estados de loading/empty state
- Sem feedback visual moderno nos botões/inputs

---

## Stack Alvo

| Item | Escolha | Justificativa |
|---|---|---|
| CSS Framework | **Tailwind CSS v3.4+** (via CDN ou build) | Utility-first, moderno, leve |
| Componentes | **Shadcn UI** (adaptado para Jinja2/HTML) | Visual clean, sem framework JS pesado |
| Ícones | **Lucide Icons** (via CDN) | Minimalistas, combinam com Shadcn |
| Fonte | **Inter** (Google Fonts) | Fonte padrão de SaaS modernos |
| JS | **Vanilla JS** (zero jQuery) | Remover dependência do jQuery |
| Modais | **Dialog nativo** ou JS vanilla | Remover dependência Bootstrap JS |
| Build | **CDN (Tailwind Play CDN)** | Sem build step, simplifica o deploy no Flask |

> **Nota sobre Shadcn UI**: Como Shadcn é originalmente feito para React, vamos usar os **estilos/padrões visuais** do Shadcn (cores, bordas, sombras, espaçamentos) recriados em HTML + Tailwind. Não precisamos de React.

---

## Plano de Refatoração (Resumo)

1. **Preparar infraestrutura** — Tailwind CDN, fontes, ícones, design tokens
2. **Criar componentes base** — layout, sidebar, header, cards, botões, inputs
3. **Refatorar layout.html** — novo layout com sidebar + header modernos
4. **Refatorar login.html** — página de login com visual Shadcn
5. **Refatorar index.html** — dashboard com cards, tabela, modal modernos
6. **Refatorar settings.html** — formulário limpo com cards
7. **Polimento final** — responsividade, dark mode, transições, edge cases

---

## Fase 0 — Preparação e Planejamento

### Task 0.1 — Definir design tokens

- [x] Criar arquivo `app/static/css/tokens.css` com variáveis CSS customizadas:
  ```css
  :root {
    /* Cores primárias */
    --primary: #0f172a;       /* slate-900 */
    --primary-foreground: #ffffff;

    /* Background */
    --background: #ffffff;
    --foreground: #0f172a;
    --muted: #f1f5f9;         /* slate-100 */
    --muted-foreground: #64748b; /* slate-500 */

    /* Borders */
    --border: #e2e8f0;        /* slate-200 */
    --input: #e2e8f0;
    --ring: #0f172a;

    /* Accent */
    --accent: #f1f5f9;
    --accent-foreground: #0f172a;

    /* Destructive */
    --destructive: #ef4444;

    /* Card */
    --card: #ffffff;
    --card-foreground: #0f172a;

    /* Radius */
    --radius: 0.5rem;

    /* Sidebar */
    --sidebar-bg: #0f172a;
    --sidebar-text: #cbd5e1;
    --sidebar-active: #ffffff;
    --sidebar-hover: #1e293b;
  }
  ```
- [x] Definir escala de espaçamento (4px base)
- [x] Definir escala tipográfica (text-xs, text-sm, text-base, text-lg, text-xl, text-2xl)

### Task 0.2 — Configurar Tailwind CSS via CDN

- [x] Adicionar Tailwind Play CDN no `<head>` do layout:
  ```html
  <script src="https://cdn.tailwindcss.com"></script>
  ```
- [x] Configurar o `tailwind.config` inline para extender com as cores/tokens:
  ```html
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            primary: '#0f172a',
            muted: '#f1f5f9',
            border: '#e2e8f0',
            destructive: '#ef4444',
          },
          fontFamily: {
            sans: ['Inter', 'sans-serif'],
          },
        }
      }
    }
  </script>
  ```

### Task 0.3 — Configurar fontes e ícones

- [x] Adicionar Google Fonts (Inter):
  ```html
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  ```
- [x] Adicionar Lucide Icons via CDN:
  ```html
  <script src="https://unpkg.com/lucide@latest"></script>
  ```
- [x] Remover Font Awesome e Source Sans Pro

### Task 0.4 — Criar estrutura de componentes

- [x] Criar diretório `app/templates/components/` para partials reutilizáveis:
  ```
  app/templates/components/
  ├── _sidebar.html
  ├── _header.html
  ├── _flash_messages.html
  ├── _button.html
  ├── _card.html
  ├── _input.html
  ├── _modal.html
  ├── _badge.html
  └── _empty_state.html
  ```
- [x] Cada componente será um macro Jinja2 ou um include

---

## Fase 1 — Componentes Base

### Task 1.1 — Componente: Card

- [x] Criar `app/templates/components/_card.html` como macro Jinja2:
  ```html
  {% macro card(title="", description="", class="") %}
  <div class="rounded-lg border border-slate-200 bg-white shadow-sm {{ class }}">
    {% if title %}
    <div class="flex flex-col space-y-1.5 p-6">
      <h3 class="text-lg font-semibold leading-none tracking-tight">{{ title }}</h3>
      {% if description %}
      <p class="text-sm text-slate-500">{{ description }}</p>
      {% endif %}
    </div>
    {% endif %}
    <div class="p-6 pt-0">
      {{ caller() }}
    </div>
  </div>
  {% endmacro %}
  ```
- [x] Suportar variants: default, bordered, shadow

### Task 1.2 — Componente: Botão

- [x] Criar `app/templates/components/_button.html`:
  ```html
  {% macro button(label="", variant="default", size="default", type="button", class="", icon="") %}
  {% set variants = {
    "default": "bg-slate-900 text-white hover:bg-slate-800",
    "destructive": "bg-red-500 text-white hover:bg-red-600",
    "outline": "border border-slate-200 bg-white hover:bg-slate-100 text-slate-900",
    "ghost": "hover:bg-slate-100 text-slate-900",
    "secondary": "bg-slate-100 text-slate-900 hover:bg-slate-200",
  } %}
  {% set sizes = {
    "default": "h-10 px-4 py-2",
    "sm": "h-8 px-3 text-xs",
    "lg": "h-12 px-8",
    "icon": "h-10 w-10",
  } %}
  <button type="{{ type }}"
    class="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 disabled:pointer-events-none disabled:opacity-50 {{ variants[variant] }} {{ sizes[size] }} {{ class }}">
    {% if icon %}<i data-lucide="{{ icon }}" class="h-4 w-4"></i>{% endif %}
    {{ label }}
  </button>
  {% endmacro %}
  ```
- [x] Variants: default, destructive, outline, ghost, secondary
- [x] Sizes: default, sm, lg, icon

### Task 1.3 — Componente: Input

- [x] Criar `app/templates/components/_input.html`:
  ```html
  {% macro input(name, label="", type="text", value="", placeholder="", required=false, help="", class="") %}
  <div class="space-y-2 {{ class }}">
    {% if label %}
    <label for="{{ name }}" class="text-sm font-medium leading-none text-slate-700">
      {{ label }}
    </label>
    {% endif %}
    <input type="{{ type }}"
      id="{{ name }}"
      name="{{ name }}"
      value="{{ value }}"
      placeholder="{{ placeholder }}"
      {% if required %}required{% endif %}
      class="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
    {% if help %}
    <p class="text-sm text-slate-500">{{ help }}</p>
    {% endif %}
  </div>
  {% endmacro %}
  ```

### Task 1.4 — Componente: Select

- [x] Criar `app/templates/components/_select.html`:
  ```html
  {% macro select(name, label="", options=[], selected="", required=false, class="") %}
  <div class="space-y-2 {{ class }}">
    {% if label %}
    <label for="{{ name }}" class="text-sm font-medium leading-none text-slate-700">{{ label }}</label>
    {% endif %}
    <select id="{{ name }}" name="{{ name }}" {% if required %}required{% endif %}
      class="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2">
      {% for value, text in options %}
      <option value="{{ value }}" {% if value == selected %}selected{% endif %}>{{ text }}</option>
      {% endfor %}
    </select>
  </div>
  {% endmacro %}
  ```

### Task 1.5 — Componente: Badge

- [x] Criar `app/templates/components/_badge.html`:
  ```html
  {% macro badge(label="", variant="default") %}
  {% set variants = {
    "default": "border-transparent bg-slate-100 text-slate-800",
    "success": "border-transparent bg-emerald-100 text-emerald-800",
    "warning": "border-transparent bg-amber-100 text-amber-800",
    "destructive": "border-transparent bg-red-100 text-red-800",
    "outline": "text-slate-700 border-slate-200",
  } %}
  <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors border {{ variants[variant] }}">
    {{ label }}
  </span>
  {% endmacro %}
  ```

### Task 1.6 — Componente: Modal/Dialog

- [x] Criar `app/templates/components/_modal.html`:
  ```html
  {% macro modal(id, title="") %}
  <div id="{{ id }}" class="fixed inset-0 z-50 hidden">
    <!-- Backdrop -->
    <div class="fixed inset-0 bg-black/50" onclick="closeModal('{{ id }}')"></div>
    <!-- Dialog -->
    <div class="fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-lg border border-slate-200 bg-white p-6 shadow-lg">
      <div class="flex flex-col space-y-1.5 text-center sm:text-left">
        <h3 class="text-lg font-semibold leading-none tracking-tight">{{ title }}</h3>
      </div>
      <div class="mt-4">
        {{ caller() }}
      </div>
      <button onclick="closeModal('{{ id }}')"
        class="absolute right-4 top-4 rounded-sm opacity-70 hover:opacity-100 transition-opacity">
        <i data-lucide="x" class="h-4 w-4"></i>
      </button>
    </div>
  </div>
  {% endmacro %}
  ```
- [x] Criar JS vanilla para `openModal(id)` e `closeModal(id)`:
  ```javascript
  function openModal(id) {
    document.getElementById(id).classList.remove('hidden');
  }
  function closeModal(id) {
    document.getElementById(id).classList.add('hidden');
  }
  ```
- [x] Substituir modais Bootstrap (um por host) por modal único reutilizável via JS

### Task 1.7 — Componente: Flash Messages (Toast)

- [x] Criar `app/templates/components/_flash_messages.html`:
  ```html
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for category, message in messages %}
      <div class="mb-4 flex items-center gap-3 rounded-lg border p-4 {{
        'border-emerald-200 bg-emerald-50 text-emerald-800' if category == 'success' else
        'border-red-200 bg-red-50 text-red-800' if category == 'error' or category == 'danger' else
        'border-amber-200 bg-amber-50 text-amber-800' if category == 'warning' else
        'border-blue-200 bg-blue-50 text-blue-800'
      }}">
        <i data-lucide="{{
          'check-circle-2' if category == 'success' else
          'x-circle' if category == 'error' or category == 'danger' else
          'alert-triangle' if category == 'warning' else
          'info'
        }}" class="h-5 w-5 shrink-0"></i>
        <p class="text-sm font-medium">{{ message }}</p>
      </div>
      {% endfor %}
    {% endif %}
  {% endwith %}
  ```
- [x] Auto-dismiss após 5 segundos (JS vanilla)

### Task 1.8 — Componente: Empty State

- [x] Criar `app/templates/components/_empty_state.html`:
  ```html
  {% macro empty_state(icon="inbox", title="", description="") %}
  <div class="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 p-8 text-center">
    <div class="flex h-16 w-16 items-center justify-center rounded-full bg-slate-100">
      <i data-lucide="{{ icon }}" class="h-8 w-8 text-slate-400"></i>
    </div>
    <h3 class="mt-4 text-lg font-semibold text-slate-900">{{ title }}</h3>
    <p class="mt-2 text-sm text-slate-500">{{ description }}</p>
  </div>
  {% endmacro %}
  ```

---

## Fase 2 — Layout Principal

### Task 2.1 — Componente: Sidebar

- [x] Criar `app/templates/components/_sidebar.html`:
  - Logo **DynFlask** no topo (texto estilizado)
  - Menu de navegação com ícones Lucide:
    - Dashboard (`layout-dashboard`)
    - Configurações (`settings`)
  - Item ativo com highlight (bg `slate-800`, text white)
  - Hover suave
  - Colapsar em mobile (overlay)
  - Footer com versão/branding
- [x] Visual: fundo `slate-900`, texto `slate-300`, ativo `slate-800` com borda esquerda accent

### Task 2.2 — Componente: Header

- [x] Criar `app/templates/components/_header.html`:
  - À esquerda: breadcrumb ou título da página
  - À direita: avatar/nome do usuário + dropdown com logout
  - Botão de toggle sidebar em mobile (hamburger)
  - Separador inferior sutil (border-b)
  - Visual: fundo branco, shadow-sm, padding adequado

### Task 2.3 — Refatorar `layout.html`

- [x] Remover toda dependência de AdminLTE e Bootstrap
- [x] Estrutura HTML nova:
  ```html
  <body class="min-h-screen bg-slate-50 font-sans antialiased">
    <!-- Sidebar -->
    {% include 'components/_sidebar.html' %}

    <!-- Main Content Area -->
    <div class="lg:pl-64">
      <!-- Header -->
      {% include 'components/_header.html' %}

      <!-- Page Content -->
      <main class="px-6 py-8">
        {% block content %}{% endblock %}
      </main>
    </div>
  </body>
  ```
- [x] Remover imports: AdminLTE CSS/JS, Bootstrap CSS/JS, jQuery
- [x] Adicionar imports: Tailwind CDN, Inter font, Lucide Icons
- [x] Adicionar `lucide.createIcons()` no final do body
- [x] Manter blocks: `{% block title %}`, `{% block content %}`, `{% block page_title %}`

---

## Fase 3 — Páginas

### Task 3.1 — Refatorar `login.html`

- [x] Remover dependência AdminLTE
- [x] Layout: página full-screen com fundo `slate-50`
- [x] Card centralizado com:
  - Logo DynFlask no topo
  - Título "Bem-vindo de volta"
  - Subtítulo "Faça login para continuar"
  - Inputs com ícones Lucide (`user`, `lock`)
  - Botão "Entrar" (full-width, primary)
  - Link esqueceu senha (placeholder, sem funcionalidade)
- [x] Flash messages com componente `_flash_messages.html`
- [x] Visual: card branco com shadow-sm, rounded-xl, max-w-md

### Task 3.2 — Refatorar `index.html` (Dashboard)

- [x] Seção superior — **Cards de resumo** (stats):
  - Total de hosts
  - Hosts com IP atualizado
  - Hosts sem IP (aguardando)
  - Última atualização (do host mais recente)
- [x] Seção do formulário "Adicionar Novo Host":
  - Usar componente `_card.html`
  - Inputs com componentes `_input.html` e `_select.html`
  - Grid 3 colunas (hostname, tipo, TTL)
  - Botão "Adicionar Host" com ícone `plus`
- [x] Seção da tabela de hosts:
  - Usar componente `_card.html`
  - Header com título "Hosts" + botão "Adicionar" (opcional)
  - Tabela limpa com Tailwind:
    - Header: `bg-slate-50`, `text-xs uppercase tracking-wider text-slate-500`
    - Linhas: `border-b border-slate-100`, hover `bg-slate-50`
    - Coluna Token: campo `<code>` com botão de copiar
    - Coluna IP: badge de status (verde se tem IP, cinza se N/A)
    - Coluna Ações: botões outline (Editar) e ghost/destructive (Excluir)
  - Se tabela vazia: usar componente `_empty_state.html`
- [x] Substituir modais Bootstrap por modal Shadcn:
  - Um único modal reutilizável
  - Preencher via JS dinamicamente ao clicar "Editar"
  - Campos: hostname, tipo, TTL
  - Botões: Cancelar (outline) + Salvar (primary)
- [x] Manter todos os `url_for()` e nomes de campos nos forms

### Task 3.3 — Refatorar `settings.html`

- [x] Layout em grid: card principal (2/3) + card de info (1/3)
- [x] Card principal — formulário:
  - Título "Configurações do Cloudflare"
  - Campo Zone ID com ícone `key`
  - Campo API Token (type=password) com ícone `shield`
  - Help text em cada campo
  - Botão "Salvar Configurações" com ícone `save`
- [x] Card lateral — info:
  - Status da conexão (placeholder, sem lógica nova)
  - Documentação rápida: links para como obter Zone ID e API Token
- [x] Usar componentes `_card.html`, `_input.html`

---

## Fase 4 — JavaScript Vanilla

### Task 4.1 — Mover lógica de sidebar toggle para vanilla JS

- [x] Implementar toggle de sidebar em mobile:
  ```javascript
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');

  function toggleSidebar() {
    sidebar.classList.toggle('-translate-x-full');
    overlay.classList.toggle('hidden');
  }
  ```
- [x] Remover `data-widget="pushmenu"` do AdminLTE

### Task 4.2 — Criar lógica de modal dinâmico

- [x] Função para preencher modal de edição com dados do host:
  ```javascript
  function openEditModal(hostId, hostname, recordType, ttl) {
    document.getElementById('edit-hostname').value = hostname;
    document.getElementById('edit-record-type').value = recordType;
    document.getElementById('edit-ttl').value = ttl;
    document.getElementById('edit-form').action = `/edit/${hostId}`;
    openModal('edit-modal');
  }
  ```
- [x] Remover todos os modais Bootstrap inline (um por host)
- [x] Ter apenas um modal no HTML, reutilizado para todos os hosts

### Task 4.3 — Botão de copiar token

- [x] Implementar cópia de token para clipboard:
  ```javascript
  function copyToken(token) {
    navigator.clipboard.writeText(token);
    // Mostrar tooltip "Copiado!" por 2 segundos
  }
  ```

### Task 4.4 — Auto-dismiss de flash messages

- [x] Adicionar fade-out automático após 5 segundos:
  ```javascript
  setTimeout(() => {
    document.querySelectorAll('.flash-message').forEach(el => {
      el.style.transition = 'opacity 0.5s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 500);
    });
  }, 5000);
  ```

### Task 4.5 — Inicializar Lucide Icons

- [x] Chamar `lucide.createIcons()` após carregamento da página
- [x] Re-chamar após abrir modais (para ícones dentro de modais)

---

## Fase 5 — Responsividade

### Task 5.1 — Sidebar responsiva

- [x] Desktop (`lg+`): sidebar fixa à esquerda, largura 256px, conteúdo com `lg:pl-64`
- [x] Tablet (`md`): sidebar colapsa em overlay, botão hamburger no header
- [x] Mobile (`sm`): sidebar totalmente escondida, overlay com animação slide-in
- [x] Animação suave de transição

### Task 5.2 — Tabela responsiva

- [x] Desktop: tabela normal com todas as colunas
- [x] Mobile: transformar em card-list (cada host vira um card) OU scroll horizontal com colunas essenciais
- [x] Esconder colunas menos importantes em telas pequenas (Token, TTL)

### Task 5.3 — Formulários responsivos

- [x] Desktop: grid de colunas (3 colunas no add host)
- [x] Mobile: stack vertical (1 coluna)
- [x] Inputs full-width em telas pequenas

### Task 5.4 — Login responsivo

- [x] Desktop: card centralizado com max-w-md
- [x] Mobile: card full-width com padding adequado

---

## Fase 6 — Polimento Visual

### Task 6.1 — Transições e micro-interações

- [x] Hover em botões: transição suave de cor (transition-colors duration-200)
- [x] Hover em linhas da tabela: bg-slate-50 suave
- [x] Focus em inputs: ring-2 com animação
- [x] Sidebar: transição de abertura/fechamento
- [x] Modal: fade-in do backdrop + scale-in do dialog

### Task 6.2 — Estados visuais

- [x] Botão disabled: opacity-50, cursor-not-allowed
- [x] Input disabled/readonly: bg-slate-50, opacity-50
- [x] Loading state em botões: spinner + texto "Salvando..."
- [x] Tabela vazia: empty state com ilustração
- [x] Confirmação de exclusão: modal de confirmação (não `confirm()` nativo)

### Task 6.3 — Tipografia e espaçamento

- [x] Padronizar headings: h1=text-2xl, h2=text-xl, h3=text-lg
- [x] Padronizar body text: text-sm (14px)
- [x] Espaçamento entre seções: mb-8
- [x] Espaçamento entre cards: gap-6
- [x] Padding interno dos cards: p-6
- [x] Garantir line-height adequado (leading-relaxed ou leading-normal)

### Task 6.4 — Dark mode (opcional)

- [x] Adicionar classe `dark` no `<html>` com toggle no header
- [x] Usar variáveis CSS para cores (já definidas nos tokens)
- [x] Adaptar cores dos componentes: bg → dark:bg, text → dark:text, border → dark:border
- [x] Sidebar mantém visual escuro em ambos os modos
- [x] Preferência salva em localStorage

---

## Fase 7 — Limpeza e Documentação

### Task 7.1 — Remover dependências legadas

- [x] Remover do layout todos os CDN imports:
  - AdminLTE CSS
  - AdminLTE JS
  - Bootstrap 4 CSS
  - Bootstrap 4 JS
  - jQuery
  - Font Awesome
  - Source Sans Pro
- [x] Remover `app/static/css/style.css` (será substituído por Tailwind)
- [x] Limpar `app/static/js/script.js` (remover `console.log` legado)

### Task 7.2 — Atualizar `style.css` customizado

- [x] Manter arquivo `app/static/css/style.css` apenas para overrides que Tailwind não cobre:
  - Scrollbar customizada (opcional)
  - Animações customizadas
  - Print styles

### Task 7.3 — Criar novo `script.js`

- [x] Organizar código vanilla JS:
  - `toggleSidebar()`
  - `openModal(id)` / `closeModal(id)`
  - `openEditModal(hostId, hostname, recordType, ttl)`
  - `copyToken(token, buttonId)`
  - `initFlashDismiss()`
  - `lucide.createIcons()`
- [x] DOMContentLoaded wrapper

### Task 7.4 — Atualizar README.md

- [x] Adicionar seção sobre stack visual:
  - Tailwind CSS
  - Shadcn UI (estilo visual)
  - Lucide Icons
  - Inter font
- [x] Remover menção a AdminLTE/Bootstrap

---

## Resumo de Arquivos Novos/Modificados

| Arquivo | Ação |
|---|---|
| `app/templates/components/_card.html` | 🆕 Novo |
| `app/templates/components/_button.html` | 🆕 Novo |
| `app/templates/components/_input.html` | 🆕 Novo |
| `app/templates/components/_select.html` | 🆕 Novo |
| `app/templates/components/_badge.html` | 🆕 Novo |
| `app/templates/components/_modal.html` | 🆕 Novo |
| `app/templates/components/_flash_messages.html` | 🆕 Novo |
| `app/templates/components/_empty_state.html` | 🆕 Novo |
| `app/templates/components/_sidebar.html` | 🆕 Novo |
| `app/templates/components/_header.html` | 🆕 Novo |
| `app/templates/layout.html` | ✏️ Reescrever |
| `app/templates/login.html` | ✏️ Reescrever |
| `app/templates/index.html` | ✏️ Reescrever |
| `app/templates/settings.html` | ✏️ Reescrever |
| `app/static/css/tokens.css` | 🆕 Novo |
| `app/static/css/style.css` | ✏️ Limpar/reescrever |
| `app/static/js/script.js` | ✏️ Reescrever (vanilla) |

**Total: 10 novos + 7 modificados = 17 arquivos**

---

## O que NÃO muda (restrições)

| Item | Regra |
|---|---|
| `main.py` | ❌ Não alterar |
| `models.py` | ❌ Não alterar |
| `cloudflare.py` | ❌ Não alterar |
| `requirements.txt` | ❌ Não alterar |
| `docker-compose.yml` | ❌ Não alterar |
| Endpoints/rotas | ❌ Não alterar |
| Nomes de campos de formulário | ❌ Não alterar |
| Validações backend | ❌ Não alterar |
| Lógica de flash messages | ❌ Não alterar |
| `url_for()` calls | ❌ Não alterar |

---

## Ordem sugerida de execução

```
Fase 0 (tokens + infra) → Fase 1 (componentes) → Fase 2 (layout) → Fase 3 (páginas) → Fase 4 (JS) → Fase 5 (responsivo) → Fase 6 (polimento) → Fase 7 (limpeza)
```

Cada fase pode ser feita de forma incremental e testada visualmente antes de avançar.
