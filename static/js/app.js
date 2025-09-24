const loginView = document.getElementById("login-view");
const routerView = document.getElementById("router-view");
const routeTitle = document.getElementById("route-title");
const routeContent = document.getElementById("route-content");

const routes = {
  dashboard: () => {
    routeTitle.textContent = "Dashboard";
    routeContent.innerHTML = `
      <section class="dashboard-header">
        <div>
          <h3 class="dashboard-title">Resumen diario</h3>
          <p class="dashboard-subtitle muted">Seguimiento de actividad y recursos de la clínica.</p>
        </div>
        <div class="dashboard-actions">
          <button class="btn btn-secondary" type="button">Ver reportes</button>
          <button class="btn btn-primary" type="button">Nuevo turno</button>
        </div>
      </section>

      <section class="dashboard-grid">
        <article class="card stat-card">
          <div class="stat-header">
            <span class="stat-label">Turnos de hoy</span>
            <span class="stat-trend trend-up">↑ 18%</span>
          </div>
          <div class="stat-value">48</div>
          <p class="muted">12 pendientes de confirmación</p>
        </article>
        <article class="card stat-card">
          <div class="stat-header">
            <span class="stat-label">Pacientes activos</span>
            <span class="stat-trend trend-up">↑ 6%</span>
          </div>
          <div class="stat-value">312</div>
          <p class="muted">24 nuevos este mes</p>
        </article>
        <article class="card stat-card">
          <div class="stat-header">
            <span class="stat-label">Ingresos</span>
            <span class="stat-trend trend-up">↑ 9%</span>
          </div>
          <div class="stat-value">$ 185K</div>
          <p class="muted">Facturado en los últimos 7 días</p>
        </article>
        <article class="card stat-card">
          <div class="stat-header">
            <span class="stat-label">Satisfacción</span>
            <span class="stat-trend trend-down">↓ 2%</span>
          </div>
          <div class="stat-value">4.6</div>
          <p class="muted">Promedio de encuestas</p>
        </article>
      </section>

      <section class="dashboard-columns">
        <div class="dashboard-column">
          <article class="card">
            <div class="card-header">
              <h3>Agenda del día</h3>
              <p class="card-subtitle">Última actualización 08:30</p>
            </div>
            <ul class="list">
              <li class="list-item">
                <span class="list-time">08:30</span>
                <div class="list-body">
                  <p class="list-title">Juan Pérez</p>
                  <p class="list-meta">Consulta general · Dr. García</p>
                </div>
                <span class="pill">Confirmado</span>
              </li>
              <li class="list-item">
                <span class="list-time">09:15</span>
                <div class="list-body">
                  <p class="list-title">María López</p>
                  <p class="list-meta">Limpieza facial · Lic. Campos</p>
                </div>
                <span class="pill">En espera</span>
              </li>
              <li class="list-item">
                <span class="list-time">10:00</span>
                <div class="list-body">
                  <p class="list-title">Carlos Ruiz</p>
                  <p class="list-meta">Evaluación post tratamiento · Dra. Vega</p>
                </div>
                <span class="pill">Check-in</span>
              </li>
            </ul>
          </article>

          <article class="card">
            <div class="card-header">
              <h3>Indicadores de ocupación</h3>
              <p class="card-subtitle">Capacidad utilizada por área</p>
            </div>
            <ul class="list">
              <li class="list-item">
                <div class="list-body">
                  <p class="list-title">Consultorios</p>
                  <p class="list-meta">6 de 8 en uso</p>
                  <div class="progress-track">
                    <div class="progress-bar" style="width: 75%"></div>
                  </div>
                </div>
                <span class="pill">75%</span>
              </li>
              <li class="list-item">
                <div class="list-body">
                  <p class="list-title">Cabinas estéticas</p>
                  <p class="list-meta">4 de 6 en uso</p>
                  <div class="progress-track">
                    <div class="progress-bar" style="width: 68%"></div>
                  </div>
                </div>
                <span class="pill">68%</span>
              </li>
              <li class="list-item">
                <div class="list-body">
                  <p class="list-title">Post operatorio</p>
                  <p class="list-meta">2 de 5 en uso</p>
                  <div class="progress-track">
                    <div class="progress-bar" style="width: 40%"></div>
                  </div>
                </div>
                <span class="pill">40%</span>
              </li>
            </ul>
          </article>
        </div>

        <div class="dashboard-column">
          <article class="card">
            <div class="card-header">
              <h3>Equipo en turno</h3>
              <p class="card-subtitle">Estado del personal asignado hoy</p>
            </div>
            <ul class="list">
              <li class="list-item list-item--center">
                <div class="avatar" aria-hidden="true">AG</div>
                <div class="list-body">
                  <p class="list-title">Dra. Ana Gómez</p>
                  <p class="list-meta">Dermatóloga · 12 turnos</p>
                </div>
                <span class="pill">En sala</span>
              </li>
              <li class="list-item list-item--center">
                <div class="avatar" aria-hidden="true">LC</div>
                <div class="list-body">
                  <p class="list-title">Lic. Laura Campos</p>
                  <p class="list-meta">Esteticista · 8 turnos</p>
                </div>
                <span class="pill">Atendiendo</span>
              </li>
              <li class="list-item list-item--center">
                <div class="avatar" aria-hidden="true">JV</div>
                <div class="list-body">
                  <p class="list-title">Dr. Julio Vega</p>
                  <p class="list-meta">Cirujano · 5 turnos</p>
                </div>
                <span class="pill">Disponible</span>
              </li>
            </ul>
          </article>

          <article class="card">
            <div class="card-header">
              <h3>Accesos rápidos</h3>
              <p class="card-subtitle">Atajos para tareas recurrentes</p>
            </div>
            <div class="quick-actions">
              <button class="btn btn-primary" type="button">Crear turno</button>
              <button class="btn btn-secondary" type="button">Registrar pago</button>
              <button class="btn btn-secondary" type="button">Agregar paciente</button>
            </div>
            <p class="muted">Acciones frecuentes para comenzar el día.</p>
          </article>
        </div>
      </section>
    `;
  },
  pacientes: window.PacientesModule.render,
  turnos: window.TurnosModule.render,
  servicios: window.ServiciosModule.render,
  profesionales: window.ProfesionalesModule.render,
  caja: window.CajaModule.render,
  inventario: window.InventarioModule.render,
  reportes: window.ReportesModule.render,
};

// --- navegación centralizada ---
function navigate(route) {
  const fn = routes[route];
  // actualizar hash (permite refrescar / deep link)
  if (location.hash !== `#/${route}` && !location.hash.startsWith(`#/${route}?`)) {
    location.hash = `#/${route}`;
  }
  routeTitle.textContent = route.charAt(0).toUpperCase() + route.slice(1);
  if (typeof fn === "function") {
    fn();
  } else {
    routeContent.innerHTML = "<div class='card'>Ruta no encontrada</div>";
  }
}

// abre la ruta del hash si existe (ej: #/caja?turno=5)
function openFromHash() {
  if (!API.token()) return; // si no hay token, no navegar
  if (location.hash.startsWith("#/")) {
    const route = location.hash.slice(2).split("?")[0];
    if (routes[route]) return navigate(route);
  }
  // por defecto
  navigate("dashboard");
}

// --- auth guard ---
function checkAuth() {
  const has = !!API.token();
  loginView.style.display = has ? "none" : "block";
  routerView.style.display = has ? "block" : "none";
  if (has) openFromHash();
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
    loginMsg.textContent = "Completá email y contraseña.";
    return;
  }
  try {
    const res = await API.request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    const token = res.access_token || res.token;
    if (!token) throw new Error("La respuesta no trajo token.");
    API.setToken(token);
    loginMsg.textContent = "¡Bienvenido!";
    checkAuth();
  } catch (e) {
    loginMsg.textContent = e.message || "Credenciales inválidas o servidor no disponible.";
  }
}

if (loginForm) loginForm.addEventListener("submit", doLogin);
if (btnLogin)  btnLogin.addEventListener("click", doLogin);

// --- links del sidebar (bloquea si no hay token) ---
document.querySelectorAll("nav a[data-route]").forEach(a => {
  a.addEventListener("click", (ev) => {
    ev.preventDefault();
    if (!API.token()) { checkAuth(); return; }
    const route = a.dataset.route;
    navigate(route);
  });
});

// --- logout ---
document.getElementById("logout").addEventListener("click", (e) => {
  e.preventDefault();
  localStorage.removeItem("token");
  // limpiar hash para evitar que reabra una ruta protegida
  location.hash = "";
  checkAuth();
});

// --- cambiar de ruta si cambia el hash (ej: desde Turnos -> Caja con ?turno=ID) ---
window.addEventListener("hashchange", () => {
  if (!API.token()) return;
  openFromHash();
});

// boot
checkAuth();
