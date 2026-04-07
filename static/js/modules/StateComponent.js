/**
 * StateComponent.js — Clase base reactiva para módulos complejos
 *
 * Uso:
 *   class GrillaModule extends StateComponent {
 *     initialState() { return { turnos: [], loading: false, filtro: "" }; }
 *     template()     { return `<div>...</div>`; }
 *   }
 *   const grilla = new GrillaModule("#route-content");
 *   grilla.mount();
 *
 * Compatible con el stack actual (Vanilla JS + Flask + Jinja2).
 * No requiere build tools ni dependencias externas.
 */

class StateComponent {
  /**
   * @param {string|HTMLElement} container — Selector CSS o elemento DOM donde montar
   */
  constructor(container) {
    this._container =
      typeof container === "string"
        ? document.querySelector(container)
        : container;

    /** @type {Record<string, Function[]>} listeners de eventos de la instancia */
    this._listeners = {};

    /** @type {boolean} indica si el componente está montado en el DOM */
    this._mounted = false;

    // Proxy reactivo: cualquier set() en this.state dispara un re-render
    this._state = new Proxy(this.initialState(), {
      set: (target, prop, value) => {
        const changed = target[prop] !== value;
        target[prop] = value;
        if (changed && this._mounted) {
          this._scheduleRender();
        }
        return true;
      },
    });
  }

  // ─── API Pública ────────────────────────────────────────────────────────────

  /**
   * Estado inicial del componente. Sobreescribir en subclases.
   * @returns {Record<string, any>}
   */
  initialState() {
    return {};
  }

  /**
   * HTML que representará el estado actual. Sobreescribir en subclases.
   * @returns {string}
   */
  template() {
    return "";
  }

  /**
   * Hook que se ejecuta DESPUÉS del primer render.
   * Ideal para adjuntar event listeners al DOM recién creado.
   */
  afterMount() {}

  /**
   * Hook que se ejecuta DESPUÉS de cada re-render por cambio de estado.
   */
  afterUpdate() {}

  /**
   * Hook que se ejecuta antes de desmontar el componente.
   */
  beforeDestroy() {}

  /**
   * Acceso al estado reactivo.
   * @returns {Record<string, any>}
   */
  get state() {
    return this._state;
  }

  /**
   * Actualiza múltiples propiedades del estado a la vez.
   * Solo dispara un re-render único (batcheado) aunque actualices N props.
   * @param {Record<string, any>} partial
   */
  update(partial = {}) {
    this._pauseRender = true;
    Object.assign(this._state, partial);
    this._pauseRender = false;
    if (this._mounted) {
      this._scheduleRender();
    }
  }

  /**
   * Monta el componente en el contenedor. Llama a afterMount() al finalizar.
   */
  mount() {
    if (!this._container) {
      console.warn("[StateComponent] Contenedor no encontrado.");
      return this;
    }
    this._mounted = true;
    this._render();
    this.afterMount();
    return this;
  }

  /**
   * Desmonta el componente, limpia listeners y vacía el contenedor.
   */
  destroy() {
    this.beforeDestroy();
    this._mounted = false;
    this._listeners = {};
    if (this._container) {
      this._container.innerHTML = "";
    }
  }

  /**
   * Suscribirse a un evento de la instancia.
   * @param {string} event
   * @param {Function} handler
   */
  on(event, handler) {
    if (!this._listeners[event]) this._listeners[event] = [];
    this._listeners[event].push(handler);
    return this;
  }

  /**
   * Emitir un evento hacia los suscriptores de esta instancia.
   * @param {string} event
   * @param {any} data
   */
  emit(event, data) {
    (this._listeners[event] || []).forEach((fn) => fn(data));
    return this;
  }

  // ─── Internals ──────────────────────────────────────────────────────────────

  _render() {
    if (!this._container || !this._mounted) return;
    this._container.innerHTML = this.template();
  }

  _scheduleRender() {
    if (this._pauseRender) return;
    if (this._renderFrame) cancelAnimationFrame(this._renderFrame);
    this._renderFrame = requestAnimationFrame(() => {
      this._render();
      this.afterUpdate();
      this._renderFrame = null;
    });
  }
}


// ─── Ejemplo de uso: TurnosGrilla ────────────────────────────────────────────
/**
 * Ejemplo concreto de cómo usar StateComponent para la grilla de turnos.
 * Este patrón reemplaza la manipulación manual del DOM en turnos.js.
 *
 * USAGE en turnos.js:
 *
 *   const grilla = new TurnosGrillaComponent("#route-content");
 *   grilla.on("turno-selected", (turno) => abrirDetalleTurno(turno));
 *   grilla.mount();
 *   grilla.update({ loading: true });
 *   API.request("/api/turnos").then((data) => grilla.update({ turnos: data, loading: false }));
 */
class TurnosGrillaComponent extends StateComponent {
  initialState() {
    return {
      turnos: [],
      loading: false,
      filtro: "",
      page: 1,
    };
  }

  template() {
    const { turnos, loading, filtro } = this.state;

    if (loading) {
      return `<div class="loading-spinner" aria-label="Cargando turnos…">
                <span class="spinner"></span> Cargando turnos…
              </div>`;
    }

    const filtered = filtro
      ? turnos.filter(
          (t) =>
            t.paciente_nombre?.toLowerCase().includes(filtro.toLowerCase()) ||
            t.profesional_nombre?.toLowerCase().includes(filtro.toLowerCase())
        )
      : turnos;

    if (!filtered.length) {
      return `<p class="empty-state">No hay turnos para mostrar.</p>`;
    }

    const rows = filtered
      .map(
        (t) => `
        <tr data-id="${t.id}" class="turno-row" tabindex="0" role="button" aria-label="Ver turno de ${t.paciente_nombre}">
          <td>${t.fecha_hora ?? "—"}</td>
          <td>${t.paciente_nombre ?? "—"}</td>
          <td>${t.profesional_nombre ?? "—"}</td>
          <td><span class="badge badge--${t.estado?.toLowerCase()}">${t.estado ?? "—"}</span></td>
          <td>
            <button class="btn btn--sm btn--primary btn-ver-turno" data-id="${t.id}">Ver</button>
          </td>
        </tr>`
      )
      .join("");

    return `
      <div class="table-responsive" style="overflow-x: auto;">
        <table class="data-table" aria-label="Grilla de turnos">
          <thead>
            <tr>
              <th>Fecha y Hora</th>
              <th>Paciente</th>
              <th>Profesional</th>
              <th>Estado</th>
              <th>Acción</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  afterMount() {
    this._bindEvents();
  }

  afterUpdate() {
    this._bindEvents();
  }

  _bindEvents() {
    if (!this._container) return;
    this._container.querySelectorAll(".btn-ver-turno").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const id = parseInt(btn.dataset.id, 10);
        const turno = this.state.turnos.find((t) => t.id === id);
        if (turno) this.emit("turno-selected", turno);
      });
    });
  }
}

// Exportar al scope global para compatibilidad con el sistema de módulos actual
window.StateComponent = StateComponent;
window.TurnosGrillaComponent = TurnosGrillaComponent;
