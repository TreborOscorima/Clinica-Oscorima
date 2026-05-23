"""
Servicio de notificaciones: Email (SMTP) y WhatsApp (Twilio).

Activación mediante variables de entorno:
  NOTIF_EMAIL_ENABLED=true   → habilita email
  NOTIF_WA_ENABLED=true      → habilita WhatsApp
  SMTP_USER / SMTP_PASSWORD  → credenciales SMTP
  TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_WA_FROM → credenciales Twilio
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from clinica_app.config import (
    CLINICA_NOMBRE,
    NOTIF_EMAIL_ENABLED,
    NOTIF_WA_ENABLED,
    SMTP_FROM,
    SMTP_FROM_NAME,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WA_FROM,
)

log = logging.getLogger(__name__)


# ── Email ──────────────────────────────────────────────────────────────────────

def send_email(to: str, subject: str, body_html: str, body_text: str = "") -> bool:
    """Envía un email. Devuelve True si tuvo éxito, False en caso contrario."""
    if not NOTIF_EMAIL_ENABLED:
        log.debug("Email desactivado. Destino: %s | Asunto: %s", to, subject)
        return False
    if not SMTP_USER or not SMTP_PASSWORD:
        log.warning("Email habilitado pero sin credenciales SMTP configuradas")
        return False
    if not to:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{SMTP_FROM_NAME} <{SMTP_FROM or SMTP_USER}>"
        msg["To"]      = to

        if body_text:
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM or SMTP_USER, [to], msg.as_string())

        log.info("Email enviado a %s | Asunto: %s", to, subject)
        return True

    except Exception as exc:
        log.error("Error enviando email a %s: %s", to, exc)
        return False


# ── WhatsApp (Twilio) ──────────────────────────────────────────────────────────

def send_whatsapp(to: str, message: str) -> bool:
    """Envía un mensaje de WhatsApp vía Twilio. Devuelve True si tuvo éxito."""
    if not NOTIF_WA_ENABLED:
        log.debug("WhatsApp desactivado. Destino: %s", to)
        return False
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        log.warning("WhatsApp habilitado pero sin credenciales Twilio configuradas")
        return False
    if not to:
        return False

    try:
        from twilio.rest import Client  # type: ignore[import]
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        wa_to = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
        client.messages.create(body=message, from_=TWILIO_WA_FROM, to=wa_to)
        log.info("WhatsApp enviado a %s", to)
        return True
    except ImportError:
        log.error("Twilio no instalado. Ejecutá: pip install twilio")
        return False
    except Exception as exc:
        log.error("Error enviando WhatsApp a %s: %s", to, exc)
        return False


# ── Templates de mensajes ──────────────────────────────────────────────────────

def _turno_email_html(turno: dict[str, Any], titulo: str, extra: str = "") -> str:
    paciente  = turno.get("paciente_nombre", "Paciente")
    fecha     = turno.get("fecha_hora", "")
    profesional = turno.get("profesional_nombre") or "a confirmar"
    servicio  = turno.get("servicio_nombre") or "consulta"
    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;max-width:500px;margin:0 auto;">
      <div style="background:#0284c7;padding:20px;border-radius:8px 8px 0 0;">
        <h2 style="color:white;margin:0;">{CLINICA_NOMBRE}</h2>
      </div>
      <div style="padding:24px;background:#fff;border:1px solid #e5e7eb;border-top:0;border-radius:0 0 8px 8px;">
        <h3 style="color:#0284c7;">{titulo}</h3>
        <p>Hola <strong>{paciente}</strong>,</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
          <tr><td style="padding:8px;background:#f0f9ff;font-weight:bold;">Fecha y hora</td>
              <td style="padding:8px;background:#f0f9ff;">{fecha}</td></tr>
          <tr><td style="padding:8px;">Profesional</td>
              <td style="padding:8px;">{profesional}</td></tr>
          <tr><td style="padding:8px;background:#f0f9ff;">Servicio</td>
              <td style="padding:8px;background:#f0f9ff;">{servicio}</td></tr>
        </table>
        {f'<p style="color:#666;">{extra}</p>' if extra else ''}
        <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0;">
        <p style="color:#9ca3af;font-size:12px;">Este mensaje fue generado automáticamente por {CLINICA_NOMBRE}.</p>
      </div>
    </body></html>
    """


def _turno_wa_text(turno: dict[str, Any], titulo: str, extra: str = "") -> str:
    paciente  = turno.get("paciente_nombre", "Paciente")
    fecha     = turno.get("fecha_hora", "")
    profesional = turno.get("profesional_nombre") or "a confirmar"
    servicio  = turno.get("servicio_nombre") or "consulta"
    lines = [
        f"*{CLINICA_NOMBRE}* — {titulo}",
        f"",
        f"Hola {paciente} 👋",
        f"📅 *Fecha/hora:* {fecha}",
        f"👨‍⚕️ *Profesional:* {profesional}",
        f"🩺 *Servicio:* {servicio}",
    ]
    if extra:
        lines.append(f"\n{extra}")
    return "\n".join(lines)


# ── Funciones de alto nivel ────────────────────────────────────────────────────

def notificar_turno_nuevo(turno: dict[str, Any], paciente_email: str = "", paciente_tel: str = "") -> None:
    """Notifica al paciente que se creó un nuevo turno."""
    titulo = "Tu turno fue agendado"
    extra  = "Te esperamos. Si necesitás reprogramar, comunicate con nosotros."

    if paciente_email:
        send_email(
            paciente_email,
            f"{CLINICA_NOMBRE} — Turno confirmado",
            _turno_email_html(turno, titulo, extra),
            body_text=_turno_wa_text(turno, titulo, extra),
        )
    if paciente_tel:
        send_whatsapp(paciente_tel, _turno_wa_text(turno, titulo, extra))


def notificar_turno_confirmado(turno: dict[str, Any], paciente_email: str = "", paciente_tel: str = "") -> None:
    """Notifica que el turno fue confirmado por el profesional."""
    titulo = "Tu turno fue confirmado ✅"
    extra  = "El profesional confirmó tu turno. ¡Nos vemos!"

    if paciente_email:
        send_email(
            paciente_email,
            f"{CLINICA_NOMBRE} — Turno confirmado",
            _turno_email_html(turno, titulo, extra),
            body_text=_turno_wa_text(turno, titulo, extra),
        )
    if paciente_tel:
        send_whatsapp(paciente_tel, _turno_wa_text(turno, titulo, extra))


def notificar_turno_cancelado(turno: dict[str, Any], paciente_email: str = "", paciente_tel: str = "") -> None:
    """Notifica que el turno fue cancelado."""
    titulo = "Tu turno fue cancelado"
    motivo = turno.get("motivo_cancelacion")
    extra  = f"Motivo: {motivo}" if motivo else "Comunicate con nosotros para reprogramar."

    if paciente_email:
        send_email(
            paciente_email,
            f"{CLINICA_NOMBRE} — Turno cancelado",
            _turno_email_html(turno, titulo, extra),
            body_text=_turno_wa_text(turno, titulo, extra),
        )
    if paciente_tel:
        send_whatsapp(paciente_tel, _turno_wa_text(turno, titulo, extra))


def notificar_recordatorio(turno: dict[str, Any], paciente_email: str = "", paciente_tel: str = "") -> None:
    """Recordatorio 24h antes del turno."""
    titulo = "Recordatorio: tenés un turno mañana 📅"
    extra  = "Te recordamos tu turno programado para mañana. ¡Te esperamos!"

    if paciente_email:
        send_email(
            paciente_email,
            f"{CLINICA_NOMBRE} — Recordatorio de turno",
            _turno_email_html(turno, titulo, extra),
            body_text=_turno_wa_text(turno, titulo, extra),
        )
    if paciente_tel:
        send_whatsapp(paciente_tel, _turno_wa_text(turno, titulo, extra))
