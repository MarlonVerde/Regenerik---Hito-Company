from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


def _send_via_resend(to_email: str, subject: str, html_body: str) -> None:
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY no configurada")

    payload = json.dumps(
        {
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }
    ).encode("utf-8")

    try:
        request = urllib.request.Request(
            RESEND_API_URL,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status >= 300:
                raise RuntimeError(f"Resend respondio con status {response.status}")
    except urllib.error.URLError as error:
        raise RuntimeError(f"No se pudo conectar con el servicio de email: {error.reason}") from error


def _send_via_sendgrid(to_email: str, subject: str, html_body: str) -> None:
    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("SENDGRID_FROM_EMAIL")
    if not api_key or not from_email:
        raise RuntimeError("SENDGRID_API_KEY o SENDGRID_FROM_EMAIL no configuradas")

    payload = json.dumps(
        {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": from_email},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_body}],
        }
    ).encode("utf-8")

    try:
        request = urllib.request.Request(
            SENDGRID_API_URL,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status >= 300:
                raise RuntimeError(f"SendGrid respondio con status {response.status}")
    except urllib.error.URLError as error:
        raise RuntimeError(f"No se pudo conectar con el servicio de email: {error.reason}") from error


def send_password_reset_email(to_email: str, reset_link: str, expires_in_minutes: int) -> bool:
    """Envia el correo de recuperacion. Devuelve False si no se pudo enviar (sin filtrar el error al cliente)."""
    provider = os.getenv("EMAIL_PROVIDER", "").strip().lower()
    subject = "Recupera tu contraseña - Brasaland"
    html_body = f"""
    <!doctype html>
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta charset="utf-8" />
      </head>
      <body style="margin:0; padding:24px 12px; background:#f6f1e8; font-family: Arial, Helvetica, sans-serif;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td align="center">
              <table role="presentation" width="100%" style="max-width:480px; background:#fffdf8; border-radius:12px; padding:24px;" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="font-size:18px; font-weight:bold; color:#1d1b1a; padding-bottom:12px;">
                    Brasaland
                  </td>
                </tr>
                <tr>
                  <td style="font-size:15px; color:#1d1b1a; line-height:1.5; padding-bottom:20px;">
                    Recibimos una solicitud para restablecer tu contraseña. Toca el botón para crear una nueva.
                  </td>
                </tr>
                <tr>
                  <td align="center" style="padding-bottom:20px;">
                    <a href="{reset_link}"
                       style="display:inline-block; background:#bd3b13; color:#ffffff; text-decoration:none;
                              font-size:16px; font-weight:bold; padding:14px 28px; border-radius:999px;">
                      Restablecer contraseña
                    </a>
                  </td>
                </tr>
                <tr>
                  <td style="font-size:13px; color:#5f5a54; line-height:1.5;">
                    Este enlace expira en {expires_in_minutes} minutos. Si no solicitaste este cambio, ignora este mensaje.
                  </td>
                </tr>
                <tr>
                  <td style="font-size:12px; color:#5f5a54; padding-top:16px; word-break:break-all;">
                    Si el botón no funciona, copia y pega este enlace: {reset_link}
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    try:
        if provider == "resend":
            _send_via_resend(to_email, subject, html_body)
        elif provider == "sendgrid":
            _send_via_sendgrid(to_email, subject, html_body)
        else:
            logger.warning("EMAIL_PROVIDER no configurado; no se envió email de recuperación.")
            return False
    except (urllib.error.URLError, RuntimeError) as error:
        logger.error("No se pudo enviar el email de recuperacion: %s", error)
        return False

    return True
