from __future__ import annotations

import asyncio
from typing import Any

import reflex as rx

from clinica_app.config import CLINICA_NOMBRE
from clinica_app.database import get_async_session
from clinica_app.services import adjuntos as adj_svc
from clinica_app.services import consentimientos as cons_svc
from clinica_app.services import notas_clinicas as svc
from clinica_app.services import plantillas_consentimiento
from clinica_app.services import plantillas_nota
from clinica_app.services import especialidad as _especialidad
from clinica_app.services import recetas as rec_svc
from clinica_app.services import storage
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState

_ADJ_UPLOAD_ID = "hc_adjuntos"


class NotasClinicasState(BaseState):

    notas:       list[dict] = []
    total:       int        = 0
    page:        int        = 1
    per_page:    int        = 20
    total_pages: int        = 1

    # Paciente activo
    paciente_id:       int = 0
    paciente_nombre:   str = ""
    paciente_alergias: str = ""

    # Modal nueva/editar nota
    modal_abierto:  bool = False
    editar_id:      int  = 0
    form_tipo:      str  = "evolucion"
    form_contenido: str  = ""
    form_turno_id:  str  = ""
    form_error:     str  = ""
    is_saving:      bool = False
    is_loading:     bool = False

    # Catálogos
    profesionales_cat: list[dict] = []
    plantillas_cat:    list[dict] = []

    # ── Adjuntos (A2) ──────────────────────────────────────────────────────────
    adjuntos:      list[dict] = []
    adj_categoria: str        = "otro"
    adj_error:     str        = ""
    is_uploading:  bool       = False

    # ── Consentimiento informado (A4) ───────────────────────────────────────────
    cons_tipos_cat:      list[dict] = []
    modal_cons_abierto:  bool = False
    cons_tipo:           str  = "general"
    cons_procedimiento:  str  = ""
    cons_profesional:    str  = ""
    cons_observaciones:  str  = ""
    cons_error:          str  = ""
    is_generating_cons:  bool = False

    # ── Receta / indicación (A5) ────────────────────────────────────────────────
    rec_tipos_cat:       list[dict] = []
    modal_rec_abierto:   bool = False
    rec_tipo:            str  = "receta"
    rec_diagnostico:     str  = ""
    rec_cuerpo:          str  = ""
    rec_profesional:     str  = ""
    rec_error:           str  = ""
    is_generating_rec:   bool = False

    async def on_mount(self):
        self._expirar_si_vencio()
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("historia"):
            yield rx.redirect("/")
            return
        await self._cargar_catalogos()
        # Leer paciente_id desde query param ?paciente_id=X
        pid_str = self.router.url.query_parameters.get("paciente_id", "")
        if pid_str:
            try:
                self.paciente_id = int(pid_str)
                await self._cargar_nombre_paciente()
                await self._cargar_adjuntos()
                async for s in self.cargar():
                    yield s
            except (ValueError, TypeError):
                pass

    async def _cargar_nombre_paciente(self):
        from clinica_app.models.paciente import Paciente
        from sqlmodel import select
        async with get_async_session() as session:
            p = (await session.execute(
                select(Paciente).where(
                    Paciente.id == self.paciente_id,
                    Paciente.clinica_id == self.clinica_id,
                )
            )).scalars().first()
            if p:
                self.paciente_nombre   = p.nombre
                self.paciente_alergias = p.alergias or ""

    async def _cargar_catalogos(self):
        self.plantillas_cat = _especialidad.plantillas_para(self.clinica_rubro)
        self.cons_tipos_cat = plantillas_consentimiento.opciones()
        self.rec_tipos_cat  = rec_svc.tipos()
        from clinica_app.models.profesional import Profesional
        from sqlmodel import select
        async with get_async_session() as session:
            stmt_profs = select(Profesional).where(
                Profesional.clinica_id == self.clinica_id,
                Profesional.is_active.is_(True),
            )
            if self.sede_actual_id:
                stmt_profs = stmt_profs.where(Profesional.sede_id == self.sede_actual_id)
            profs = (await session.execute(stmt_profs.limit(100))).scalars().all()
            self.profesionales_cat = [
                {"id": str(p.id), "nombre": f"{p.nombres} {p.apellidos}"}
                for p in profs
            ]

    async def cargar(self):
        if not self.paciente_id:
            return
        self.is_loading = True
        yield
        async with get_async_session() as session:
            result = await svc.listar_por_paciente(
                session,
                self.clinica_id,
                self.paciente_id,
                sede_id=self.sede_actual_id,
                page=self.page,
                per_page=self.per_page,
            )
        self.notas       = result["data"]
        self.total       = result["total"]
        self.total_pages = result["pages"]
        self.is_loading = False

    async def set_paciente(self, paciente_id: int, nombre: str):
        self.paciente_id     = paciente_id
        self.paciente_nombre = nombre
        self.page            = 1
        async for s in self.cargar():
            yield s

    # ── Adjuntos (A2) ──────────────────────────────────────────────────────────

    def set_adj_categoria(self, v: str):
        self.adj_categoria = v

    async def _cargar_adjuntos(self):
        if not self.paciente_id:
            self.adjuntos = []
            return
        async with get_async_session() as session:
            self.adjuntos = await adj_svc.listar_por_paciente(
                session, self.clinica_id, self.paciente_id, sede_id=self.sede_actual_id
            )

    async def handle_upload(self, files: list[rx.UploadFile]):
        """Recibe los archivos subidos, los valida, guarda en disco y registra."""
        self.adj_error = ""
        if not self.tiene_permiso("historia", write=True):
            self.adj_error = "Sin permiso de escritura"
            return
        if not self.paciente_id:
            self.adj_error = "Seleccioná un paciente primero"
            return
        if not files:
            return

        self.is_uploading = True
        yield

        guardados = 0
        try:
            for file in files:
                data = await file.read()
                nombre = file.filename or file.name or "archivo"
                try:
                    stored = await asyncio.to_thread(
                        storage.guardar, self.clinica_id, nombre, data
                    )
                except ServiceError as exc:
                    self.adj_error = str(exc)
                    continue
                async with get_async_session() as session:
                    await adj_svc.crear(
                        session, self.clinica_id, self.paciente_id,
                        nombre=nombre,
                        stored_name=stored,
                        mime=file.content_type,
                        tamano=len(data),
                        categoria=self.adj_categoria,
                        created_by_id=self.user_id,
                        sede_id=self.sede_actual_id,
                    )
                guardados += 1
        except Exception:
            self.adj_error = "Ocurrió un error al subir el archivo."

        self.is_uploading = False
        await self._cargar_adjuntos()
        yield rx.clear_selected_files(_ADJ_UPLOAD_ID)

    async def eliminar_adjunto(self, adjunto_id: int):
        if not self.tiene_permiso("historia", write=True):
            return
        stored_name = ""
        async with get_async_session() as session:
            try:
                stored_name = await adj_svc.eliminar(
                    session, self.clinica_id, adjunto_id,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
            except ServiceError:
                pass
        # El archivo físico se borra fuera de la transacción (idempotente).
        if stored_name:
            await asyncio.to_thread(storage.eliminar, self.clinica_id, stored_name)
        await self._cargar_adjuntos()

    # ── Consentimiento informado (A4) ───────────────────────────────────────────

    def set_cons_tipo(self, v: str):          self.cons_tipo = v
    def set_cons_procedimiento(self, v: str): self.cons_procedimiento = v
    def set_cons_profesional(self, v: str):   self.cons_profesional = v
    def set_cons_observaciones(self, v: str): self.cons_observaciones = v

    def abrir_consentimiento(self):
        self.cons_tipo          = "general"
        self.cons_procedimiento = ""
        self.cons_profesional   = ""
        self.cons_observaciones = ""
        self.cons_error         = ""
        self.modal_cons_abierto = True

    def cerrar_consentimiento(self):
        self.modal_cons_abierto = False

    async def generar_consentimiento(self):
        self.cons_error = ""
        if not self.tiene_permiso("historia", write=True):
            self.cons_error = "Sin permiso de escritura"
            return
        if not self.paciente_id:
            self.cons_error = "Seleccioná un paciente primero"
            return
        if not self.cons_procedimiento.strip():
            self.cons_error = "Indicá el procedimiento"
            return

        self.is_generating_cons = True
        yield
        try:
            async with get_async_session() as session:
                await cons_svc.generar(
                    session, self.clinica_id, self.paciente_id,
                    tipo=self.cons_tipo,
                    procedimiento=self.cons_procedimiento,
                    profesional_nombre=self.cons_profesional,
                    observaciones=self.cons_observaciones,
                    usuario_id=self.user_id,
                    sede_id=self.sede_actual_id,
                    clinica_nombre=CLINICA_NOMBRE,
                )
        except ServiceError as exc:
            self.cons_error = str(exc)
            self.is_generating_cons = False
            return
        except RuntimeError as exc:
            self.cons_error = str(exc)
            self.is_generating_cons = False
            return
        except Exception:
            self.cons_error = "No se pudo generar el consentimiento."
            self.is_generating_cons = False
            return

        self.is_generating_cons = False
        self.modal_cons_abierto = False
        await self._cargar_adjuntos()

    # ── Receta / indicación (A5) ────────────────────────────────────────────────

    def set_rec_tipo(self, v: str):        self.rec_tipo = v
    def set_rec_diagnostico(self, v: str): self.rec_diagnostico = v
    def set_rec_cuerpo(self, v: str):      self.rec_cuerpo = v
    def set_rec_profesional(self, v: str): self.rec_profesional = v

    def abrir_receta(self):
        self.rec_tipo        = "receta"
        self.rec_diagnostico = ""
        self.rec_cuerpo      = ""
        self.rec_profesional = ""
        self.rec_error       = ""
        self.modal_rec_abierto = True

    def cerrar_receta(self):
        self.modal_rec_abierto = False

    async def generar_receta(self):
        self.rec_error = ""
        if not self.tiene_permiso("historia", write=True):
            self.rec_error = "Sin permiso de escritura"
            return
        if not self.paciente_id:
            self.rec_error = "Seleccioná un paciente primero"
            return
        if not self.rec_cuerpo.strip():
            self.rec_error = "Escribí el contenido"
            return

        self.is_generating_rec = True
        yield
        try:
            async with get_async_session() as session:
                await rec_svc.generar(
                    session, self.clinica_id, self.paciente_id,
                    tipo=self.rec_tipo,
                    cuerpo=self.rec_cuerpo,
                    diagnostico=self.rec_diagnostico,
                    profesional_nombre=self.rec_profesional,
                    usuario_id=self.user_id,
                    sede_id=self.sede_actual_id,
                    clinica_nombre=CLINICA_NOMBRE,
                )
        except ServiceError as exc:
            self.rec_error = str(exc)
            self.is_generating_rec = False
            return
        except RuntimeError as exc:
            self.rec_error = str(exc)
            self.is_generating_rec = False
            return
        except Exception:
            self.rec_error = "No se pudo generar el documento."
            self.is_generating_rec = False
            return

        self.is_generating_rec = False
        self.modal_rec_abierto = False
        await self._cargar_adjuntos()

    async def prev_page(self):
        if self.page > 1:
            self.page -= 1
            async for s in self.cargar():
                yield s

    async def next_page(self):
        if self.page < self.total_pages:
            self.page += 1
            async for s in self.cargar():
                yield s

    # ── Setters ────────────────────────────────────────────────────────────────

    def set_form_tipo(self, v: str):      self.form_tipo = v
    def set_form_contenido(self, v: str): self.form_contenido = v
    def set_form_turno_id(self, v: str):  self.form_turno_id = v

    def aplicar_plantilla(self, clave: str):
        """Inserta el esqueleto de la plantilla elegida en el contenido."""
        if not clave:
            return
        self.form_contenido = plantillas_nota.contenido(clave)

    # ── Modal ──────────────────────────────────────────────────────────────────

    def abrir_nueva(self):
        self.editar_id      = 0
        self.form_tipo      = "evolucion"
        self.form_contenido = ""
        self.form_turno_id  = ""
        self.form_error     = ""
        self.modal_abierto  = True

    def abrir_editar(self, nota: dict):
        # Defensa: una nota firmada no se edita (el botón se oculta en la UI, pero
        # blindamos el handler igual).
        if nota.get("firmada"):
            return
        self.editar_id      = nota.get("id") or 0
        self.form_tipo      = nota.get("tipo") or "evolucion"
        self.form_contenido = nota.get("contenido") or ""
        self.form_turno_id  = str(nota.get("turno_id") or "")
        self.form_error     = ""
        self.modal_abierto  = True

    def cerrar_modal(self):
        self.modal_abierto = False

    async def guardar(self):
        if not self.tiene_permiso("historia", write=True):
            self.form_error = "Sin permiso de escritura"
            return
        self.is_saving  = True
        self.form_error = ""
        yield

        payload: dict[str, Any] = {
            "paciente_id":    self.paciente_id,
            "tipo":           self.form_tipo,
            "contenido":      self.form_contenido,
            "turno_id":       int(self.form_turno_id) if self.form_turno_id.strip() else None,
            "profesional_id": self.user_id if self.is_profesional else None,
        }
        try:
            async with get_async_session() as session:
                if self.editar_id:
                    await svc.actualizar(session, self.clinica_id, self.editar_id, payload)
                else:
                    await svc.crear(session, self.clinica_id, payload, created_by_id=self.user_id, sede_id=self.sede_actual_id)
        except ServiceError as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving     = False
        self.modal_abierto = False
        async for s in self.cargar():
            yield s

    async def eliminar(self, nota_id: int):
        if not self.tiene_permiso("historia", write=True):
            return
        async with get_async_session() as session:
            try:
                await svc.eliminar(session, self.clinica_id, nota_id)
            except ServiceError:
                pass
        async for s in self.cargar():
            yield s

    async def firmar_nota(self, nota_id: int):
        """Firma una nota (la vuelve inmutable). Requiere permiso de escritura."""
        if not self.tiene_permiso("historia", write=True):
            return
        async with get_async_session() as session:
            try:
                await svc.firmar(
                    session, self.clinica_id, nota_id,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
            except ServiceError:
                pass
        async for s in self.cargar():
            yield s

    # ── Atajos de teclado ──────────────────────────────────────────────────────

    def handle_modal_key(self, key: str):
        if key == "Escape":
            self.cerrar_modal()

    async def handle_tabla_key(self, key: str):
        if key == "ArrowLeft":
            async for s in self.prev_page():
                yield s
        elif key == "ArrowRight":
            async for s in self.next_page():
                yield s
