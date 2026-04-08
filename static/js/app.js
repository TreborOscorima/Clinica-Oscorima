const loginView = document.getElementById("login-view");
const routerView = document.getElementById("router-view");
const routeTitle = document.getElementById("route-title");
const routeContent = document.getElementById("route-content");
const bodyEl = document.body;
const sidebarEl = document.getElementById("sidebar");
const navToggleBtn = document.getElementById("nav-toggle");
const footerYear = document.querySelector('.sidebar__footer small');
if (footerYear) {
  footerYear.textContent = '© ' + new Date().getFullYear() + ' Clínica Estética WAYKI SAC';
}



const routes = {
  dashboard: () => {
    routeTitle.textContent = "Dashboard General";
    const shortcuts = [
      { route: "turnos", icon: "🗓️", title: "Turnos", description: "Gestione la agenda de los profesionales." },
      { route: "caja", icon: "💳", title: "Caja", description: "Movimientos, cobros y facturación." },
      { route: "pacientes", icon: "🧑‍🤝‍🧑", title: "Pacientes", description: "Fichas, altas rápidas e historiales." },
      { route: "profesionales", icon: "🩺", title: "Profesionales", description: "Directorio del equipo y especialidades." },
      { route: "inventario", icon: "📦", title: "Inventario", description: "Control de stock e insumos médicos." },
      { route: "servicios", icon: "💼", title: "Servicios", description: "Precios y catálogo de tratamientos." },
      { route: "reportes", icon: "📈", title: "Reportes", description: "Análisis y exportación de datos." },
      { route: "configuracion", icon: "⚙️", title: "Ajustes", description: "Permisos, roles y usuarios del sistema." },
    ];

    routeContent.innerHTML = `
      <div class="page-shell">
        <header class="page-header" style="margin-bottom: var(--space-5);">
          <div>
            <p class="page-header__eyebrow" style="color: var(--color-primary); font-weight: 600; text-transform: uppercase;">Bienvenido(a)</p>
            <h1 class="page-header__title" style="font-size: 2rem;">Centro de Control</h1>
            <p style="color: var(--color-muted); font-size: 1.05rem;">Acceda a todos los módulos desde aquí.</p>
          </div>
        </header>

        <div class="dashboard-shortcuts" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: var(--space-5);">
          ${shortcuts
            .map(
              (item) => `
                <article class="card card--shortcut" data-route="${item.route}" tabindex="0" role="button" aria-label="Ir a ${item.title}" style="display: flex; flex-direction: row; align-items: flex-start; gap: var(--space-4); padding: var(--space-4);">
                  <div style="font-size: 2rem; background: var(--color-primary-soft); width: 64px; height: 64px; border-radius: 16px; display: flex; align-items: center; justify-content: center;">
                    ${item.icon}
                  </div>
                  <div style="flex: 1;">
                    <h3 class="card__title" style="margin-bottom: 4px;">${item.title}</h3>
                    <p class="card__subtitle" style="font-size: 0.9rem; line-height: 1.4;">${item.description}</p>
                  </div>
                </article>
              `
            )
            .join("")}
        </div>
      </div>
    `;

    routeContent.querySelectorAll(".card--shortcut").forEach((card) => {
      card.addEventListener("click", () => navigate(card.dataset.route));
      card.addEventListener("keypress", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          navigate(card.dataset.route);
        }
      });
    });
  },
  pacientes: window.PacientesModule.render,
  turnos: window.TurnosModule.render,
  servicios: window.ServiciosModule.render,
  profesionales: window.ProfesionalesModule.render,
  caja: window.CajaModule.render,
  inventario: window.InventarioModule.render,
  reportes: window.ReportesModule.render,
  configuracion: window.ConfigModule.render,
};

function setActiveNav(route) {
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.toggle('is-active', link.dataset.route === route);
  });
}

function closeSidebar() {
  if (!sidebarEl) return;
  sidebarEl.classList.remove('sidebar--open');
  bodyEl.classList.remove('sidebar-open');
}



// --- navegación centralizada ---
function navigate(route) {
  const fn = routes[route];
  if (location.hash !== `#/${route}` && !location.hash.startsWith(`#/${route}?`)) {
    location.hash = `#/${route}`;
  }
  routeTitle.textContent = route.charAt(0).toUpperCase() + route.slice(1);
  setActiveNav(route);
  closeSidebar();
  if (typeof fn === "function") {
    fn();
  } else {
    routeContent.innerHTML = "<div class='card'>Ruta no encontrada</div>";
  }
}

// abre la ruta del hash si existe (ej: #/caja?turno=5)
function openFromHash() {
  if (!API.hasSession()) return; // si no hay token valido, no navegar
  if (location.hash.startsWith("#/")) {
    const route = location.hash.slice(2).split("?")[0];
    if (routes[route]) return navigate(route);
  }
  // por defecto
  navigate("dashboard");
}

// --- auth guard ---
async function checkAuth() {
  let has = API.hasSession();
  if (has) {
    try {
      await API.ensureAccessToken();
      has = API.hasSession();
    } catch (err) {
      has = false;
    }
  }
  loginView.style.display = has ? "none" : "block";
  routerView.style.display = has ? "block" : "none";
  document.body.classList.toggle('is-authenticated', has);
  if (!has) {
    closeSidebar();
  } else {
    openFromHash();
  }
}

// --- login wiring (click + submit + errores) ---
const loginForm = document.getElementById("login-form");
const btnLogin  = document.getElementById("btn-login");
const emailEl   = document.getElementById("login-email");
const passEl    = document.getElementById("login-pass");
const loginMsg  = document.getElementById("login-msg");

async function doLogin(ev) {
  ev.preventDefault();
  loginMsg.textContent = "";
  const email = (emailEl.value || "").trim();
  const password = passEl.value || "";
  if (!email || !password) {
    loginMsg.textContent = "Completa email y contrasena.";
    return;
  }
  try {
    const res = await API.request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      auth: "none",
    });
    const { access_token, refresh_token, expires_at, refresh_expires_at } = res || {};
    if (!access_token || !refresh_token) {
      throw new Error("La respuesta no incluyo tokens de sesion.");
    }
    API.setTokens({
      accessToken: access_token,
      refreshToken: refresh_token,
      expiresAt: expires_at,
      refreshExpiresAt: refresh_expires_at,
    });
    loginMsg.textContent = "Bienvenido!";
    await checkAuth();
  } catch (e) {
    API.clearTokens();
    loginMsg.textContent = (e && e.message) || "Credenciales invalidas o servidor no disponible.";
  }
}

if (loginForm) loginForm.addEventListener("submit", doLogin);
if (btnLogin)  btnLogin.addEventListener("click", doLogin);

// --- links del sidebar (bloquea si no hay token) ---
document.querySelectorAll("nav a[data-route]").forEach(a => {
  a.addEventListener("click", (ev) => {
    ev.preventDefault();
    if (!API.hasSession()) { checkAuth(); return; }
    const route = a.dataset.route;
    navigate(route);
    closeSidebar();
  });
});

if (navToggleBtn && sidebarEl) {
  navToggleBtn.addEventListener('click', () => {
    const willOpen = !sidebarEl.classList.contains('sidebar--open');
    sidebarEl.classList.toggle('sidebar--open', willOpen);
    bodyEl.classList.toggle('sidebar-open', willOpen);
  });
}



if (sidebarEl) {
  document.addEventListener("click", (ev) => {
    if (!bodyEl.classList.contains('sidebar-open')) return;
    if (sidebarEl.contains(ev.target)) return;
    if (navToggleBtn && navToggleBtn.contains(ev.target)) return;
    closeSidebar();
  });
}

window.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape" && bodyEl.classList.contains('sidebar-open')) {
    closeSidebar();
  }
});

window.addEventListener("resize", () => {
  if (window.innerWidth >= 960) {
    closeSidebar();
  }
});

window.addEventListener("api:session-ended", () => {
  checkAuth();
});

// --- logout ---
document.getElementById("logout").addEventListener("click", async (e) => {
  e.preventDefault();
  API.clearTokens();
  location.hash = "";
  closeSidebar();
  await checkAuth();
});

// --- cambiar de ruta si cambia el hash (ej: desde Turnos -> Caja con ?turno=ID) ---
window.addEventListener("hashchange", () => {
  if (!API.hasSession()) return;
  openFromHash();
});

// boot
checkAuth();
