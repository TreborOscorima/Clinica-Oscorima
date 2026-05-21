window.ReportesModule = (function(){
  const money = (value) => Number(value || 0).toLocaleString("es-PE", { style: "currency", currency: "PEN" });

  function buildParams(mapper){
    const params = new URLSearchParams();
    Object.entries(mapper).forEach(([key, value]) => {
      const val = typeof value === "function" ? value() : value;
      if (val !== undefined && val !== null && String(val).trim() !== ""){
        params.set(key, String(val).trim());
      }
    });
    return params;
  }

  async function downloadReport(basePath, params, fallbackName){
    const headers = {};
    try {
      await API.ensureAccessToken();
    } catch (err) {
      alert("Sesion expirada. Inicia sesion nuevamente.");
      return;
    }
    if (!API.hasSession()) {
      alert("Sesion expirada. Inicia sesion nuevamente.");
      return;
    }
    const token = API.token();
    if (token) headers["Authorization"] = "Bearer " + token;
    const url = `${basePath}${params.toString() ? `?${params}` : ""}`;
    try {
      const res = await fetch(url, { headers });
      if (!res.ok){
        let message = `Error ${res.status}`;
        try {
          const data = await res.json();
          message = data.message || message;
        } catch (err) {
          try {
            message = await res.text();
          } catch (err2) {
            // swallow
          }
        }
        throw new Error(message);
      }
      const blob = await res.blob();
      let filename = fallbackName;
      const disposition = res.headers.get("content-disposition") || "";
      const match = disposition.match(/filename="?([^";]+)"?/i);
      if (match && match[1]){
        filename = match[1];
      }
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        URL.revokeObjectURL(link.href);
        link.remove();
      }, 0);
    } catch (error){
      alert(error.message || "No se pudo descargar el reporte");
    }
  }

  const req = async (path) => API.request(path);

  function render(){
    routeTitle.textContent = "Reportes";
    routeContent.innerHTML = `
      <div class="page-shell animate-in">

        <!-- Facturación — full width -->
        <div class="module-panel" style="margin-bottom:16px">
          <div class="panel-header">
            <h2 class="panel-title">Facturación / Caja</h2>
            <span class="muted" style="font-size:.85rem">Ingresos, egresos y exportaciones</span>
          </div>
          <div class="panel-body">
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px">
              <div class="field-group"><label class="field-label">Desde</label><input id="rf-desde" type="datetime-local" class="input"></div>
              <div class="field-group"><label class="field-label">Hasta</label><input id="rf-hasta" type="datetime-local" class="input"></div>
              <div class="field-group"><label class="field-label">Agrupar por</label>
                <select id="rf-group" class="input">
                  <option value="metodo">Método de pago</option>
                  <option value="dia">Día</option>
                  <option value="servicio">Servicio</option>
                  <option value="profesional">Profesional</option>
                  <option value="paciente">Paciente</option>
                  <option value="producto">Producto</option>
                </select>
              </div>
              <div class="field-group"><label class="field-label">Tipo</label>
                <select id="rf-tipo" class="input">
                  <option value="">Ambos</option>
                  <option value="ingreso">Ingreso</option>
                  <option value="egreso">Egreso</option>
                </select>
              </div>
              <div class="field-group"><label class="field-label">Método de pago</label>
                <select id="rf-metodo" class="input">
                  <option value="">Todos</option>
                  <option value="efectivo">Efectivo</option>
                  <option value="tarjeta">Tarjeta</option>
                  <option value="transferencia">Transferencia</option>
                  <option value="otro">Otro</option>
                </select>
              </div>
            </div>
            <div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:10px;margin-top:12px;border-bottom:1px dashed var(--color-border);padding-bottom:12px">
              <button id="rf-run" class="button button--primary">Calcular en pantalla</button>
              <div style="display:flex;gap:8px;flex-wrap:wrap">
                <button id="rf-excel" class="button button--ghost button--sm">Exportar Excel</button>
                <button id="rf-pdf" class="button button--ghost button--sm">Exportar PDF</button>
                <a id="rf-csv" class="button button--ghost button--sm" target="_blank" rel="noopener" style="display:flex;align-items:center">CSV</a>
              </div>
            </div>
            <div id="rf-total" style="font-weight:600;font-size:1rem;margin:10px 0;color:var(--color-text)"></div>
            <table class="table">
              <thead><tr><th>Clave (agrupación)</th><th>Monto Total</th></tr></thead>
              <tbody id="rf-tbody"><tr><td colspan="2" class="muted" style="padding:12px">Sin datos</td></tr></tbody>
            </table>
          </div>
        </div>

        <!-- 3 cards de exportación -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px">

          <!-- Turnos -->
          <div class="module-panel">
            <div class="panel-header"><h2 class="panel-title">Agenda y Turnos</h2></div>
            <div class="panel-body">
              <div class="field-row">
                <div class="field-group"><label class="field-label">Desde</label><input id="rt-desde" type="datetime-local" class="input"></div>
                <div class="field-group"><label class="field-label">Hasta</label><input id="rt-hasta" type="datetime-local" class="input"></div>
              </div>
              <div class="field-row">
                <div class="field-group"><label class="field-label">Estado</label>
                  <select id="rt-estado" class="input">
                    <option value="">Todos</option>
                    <option value="pendiente">Pendiente</option>
                    <option value="confirmado">Confirmado</option>
                    <option value="cancelado">Cancelado</option>
                    <option value="atendido">Atendido</option>
                  </select>
                </div>
                <div class="field-group"><label class="field-label">Profesional ID</label><input id="rt-profesional" type="number" min="1" placeholder="Opcional" class="input"></div>
              </div>
              <div class="field-group"><label class="field-label">Servicio ID</label><input id="rt-servicio" type="number" min="1" placeholder="Opcional" class="input"></div>
              <div class="field-row" style="margin-top:12px">
                <button id="rt-excel" class="button button--ghost button--full">Excel</button>
                <button id="rt-pdf" class="button button--ghost button--full">PDF</button>
              </div>
            </div>
          </div>

          <!-- Inventario -->
          <div class="module-panel">
            <div class="panel-header"><h2 class="panel-title">Movimientos de Inventario</h2></div>
            <div class="panel-body">
              <div class="field-row">
                <div class="field-group"><label class="field-label">Desde</label><input id="ri-desde" type="datetime-local" class="input"></div>
                <div class="field-group"><label class="field-label">Hasta</label><input id="ri-hasta" type="datetime-local" class="input"></div>
              </div>
              <div class="field-row">
                <div class="field-group"><label class="field-label">Tipo</label>
                  <select id="ri-tipo" class="input">
                    <option value="">Todos</option>
                    <option value="ingreso">Ingreso</option>
                    <option value="egreso">Egreso</option>
                    <option value="ajuste">Ajuste</option>
                  </select>
                </div>
                <div class="field-group"><label class="field-label">Producto ID</label><input id="ri-producto" type="number" min="1" placeholder="Opcional" class="input"></div>
              </div>
              <div class="field-row" style="margin-top:12px">
                <button id="ri-excel" class="button button--ghost button--full">Excel</button>
                <button id="ri-pdf" class="button button--ghost button--full">PDF</button>
              </div>
            </div>
          </div>

          <!-- Pacientes -->
          <div class="module-panel">
            <div class="panel-header"><h2 class="panel-title">Crecimiento de Pacientes</h2></div>
            <div class="panel-body">
              <div class="field-row">
                <div class="field-group"><label class="field-label">Alta Desde</label><input id="rp-desde" type="date" class="input"></div>
                <div class="field-group"><label class="field-label">Alta Hasta</label><input id="rp-hasta" type="date" class="input"></div>
              </div>
              <p class="muted" style="margin:8px 0;font-size:.85rem">Exporta el listado según la fecha de registro en el sistema.</p>
              <div class="field-row" style="margin-top:12px">
                <button id="rp-excel" class="button button--ghost button--full">Excel</button>
                <button id="rp-pdf" class="button button--ghost button--full">PDF</button>
              </div>
            </div>
          </div>

        </div>
      </div>
    `;

    // Facturación
    const facBody = document.getElementById("rf-tbody");
    const facTotal = document.getElementById("rf-total");
    const facturacionParams = () => buildParams({
      desde: () => document.getElementById("rf-desde").value,
      hasta: () => document.getElementById("rf-hasta").value,
      group_by: () => document.getElementById("rf-group").value,
      tipo: () => document.getElementById("rf-tipo").value,
      metodo: () => document.getElementById("rf-metodo").value,
    });
    document.getElementById("rf-run").addEventListener("click", async () => {
      const params = facturacionParams();
      facTotal.textContent = "Calculando...";
      try {
        const data = await req(`/api/reportes/facturacion?${params}`);
        const rows = Array.isArray(data?.data) ? data.data : [];
        if (!rows.length){
          facBody.innerHTML = '<tr><td colspan="2" class="table__empty muted">Sin resultados</td></tr>';
        } else {
          facBody.innerHTML = rows.map((row) => `<tr><td>${row.clave}</td><td>${money(row.monto)}</td></tr>`).join("");
        }
        const resumen = data?.resumen || {};
        const ingresos = Number(resumen.ingresos ?? 0);
        const egresos = Number(resumen.egresos ?? 0);
        const neto = Number(resumen.neto ?? ingresos - egresos);
        facTotal.textContent = `Ingresos: ${money(ingresos)} | Egresos: ${money(egresos)} | Neto: ${money(neto)}`;
        document.getElementById("rf-csv").href = `/api/reportes/exportar/csv?tipo=facturacion${params.toString() ? `&${params}` : ""}`;
      } catch (error){
        facBody.innerHTML = `<tr><td colspan="2" class="table__empty">${error.message || error}</td></tr>`;
        facTotal.textContent = error.message || "Error al calcular";
      }
    });
    document.getElementById("rf-excel").addEventListener("click", () => {
      downloadReport("/api/reportes/facturacion/export/excel", facturacionParams(), "reporte_facturacion.xlsx");
    });
    document.getElementById("rf-pdf").addEventListener("click", () => {
      downloadReport("/api/reportes/facturacion/export/pdf", facturacionParams(), "reporte_facturacion.pdf");
    });

    // Pacientes - exportes
    const pacientesFilters = () => buildParams({
      desde: () => document.getElementById("rp-desde").value,
      hasta: () => document.getElementById("rp-hasta").value,
    });

    document.getElementById("rp-excel").addEventListener("click", () => {
      const params = pacientesFilters();
      downloadReport("/api/reportes/pacientes/export/excel", params, "reporte_pacientes.xlsx");
    });
    document.getElementById("rp-pdf").addEventListener("click", () => {
      const params = pacientesFilters();
      downloadReport("/api/reportes/pacientes/export/pdf", params, "reporte_pacientes.pdf");
    });

    // Inventario exportes
    const inventarioParams = () => buildParams({
      desde: () => document.getElementById("ri-desde").value,
      hasta: () => document.getElementById("ri-hasta").value,
      tipo: () => document.getElementById("ri-tipo").value,
      producto_id: () => document.getElementById("ri-producto").value,
    });
    document.getElementById("ri-excel").addEventListener("click", () => {
      downloadReport("/api/reportes/inventario/export/excel", inventarioParams(), "reporte_inventario.xlsx");
    });
    document.getElementById("ri-pdf").addEventListener("click", () => {
      downloadReport("/api/reportes/inventario/export/pdf", inventarioParams(), "reporte_inventario.pdf");
    });

    // Turnos exportes
    const turnosParams = () => buildParams({
      desde: () => document.getElementById("rt-desde").value,
      hasta: () => document.getElementById("rt-hasta").value,
      estado: () => document.getElementById("rt-estado").value,
      profesional_id: () => document.getElementById("rt-profesional").value,
      servicio_id: () => document.getElementById("rt-servicio").value,
    });
    document.getElementById("rt-excel").addEventListener("click", () => {
      downloadReport("/api/reportes/turnos/export/excel", turnosParams(), "reporte_turnos.xlsx");
    });
    document.getElementById("rt-pdf").addEventListener("click", () => {
      downloadReport("/api/reportes/turnos/export/pdf", turnosParams(), "reporte_turnos.pdf");
    });
  }

  return { render };
})();
