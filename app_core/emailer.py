from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app_core.config import AppConfig
from app_core.domain import channels_label, normalize_channels


@dataclass
class SubmissionEmailPayload:
    solicitante: str
    email: str
    unidade: str
    solicitando_como: str
    tipo: str
    canais: list[str]
    descricao: str
    data_publicacao: str
    urgencia: bool = False


class EmailNotifier:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def _build_subject(self, payload: SubmissionEmailPayload) -> str:
        prefix = "[URGENTE] " if payload.urgencia else ""
        return f"{prefix}Comunica IME - {payload.tipo}"

    def _build_body(self, payload: SubmissionEmailPayload) -> str:
        canais = channels_label(normalize_channels(payload.canais))
        urgencia = "SIM" if payload.urgencia else "NAO"
        return (
            "Solicitacao registrada na plataforma Comunica IME.\n\n"
            f"Solicitante: {payload.solicitante}\n"
            f"E-mail: {payload.email}\n"
            f"Unidade: {payload.unidade}\n"
            f"Solicitando como: {payload.solicitando_como}\n"
            f"Tipo: {payload.tipo}\n"
            f"Canais: {canais}\n"
            f"Data de publicacao: {payload.data_publicacao}\n"
            f"Urgencia: {urgencia}\n\n"
            "Descricao:\n"
            f"{payload.descricao}\n"
        )

    def send_submission_notifications(
        self, payload: SubmissionEmailPayload
    ) -> list[str]:
        # If e-mail is not enabled, we silently skip so the app flow is not blocked.
        if not self.config.email_enabled:
            return []

        if not self.config.smtp_host or not self.config.email_from:
            return [
                "EMAIL_ENABLED=true, mas SMTP_HOST/EMAIL_FROM nao foram configurados."
            ]

        recipients = [payload.email] if payload.email else []
        for bcc in self.config.email_bcc:
            if bcc and bcc not in recipients:
                recipients.append(bcc)
        if not recipients:
            return ["Nao ha destinatarios para envio de e-mail."]

        message = EmailMessage()
        message["From"] = self.config.email_from
        message["To"] = ", ".join(recipients)
        message["Subject"] = self._build_subject(payload)
        message.set_content(self._build_body(payload))

        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=30) as server:
                if self.config.smtp_use_tls:
                    server.starttls()
                if self.config.smtp_username:
                    server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(message)
        except Exception as exc:
            return [f"Falha no envio de e-mail: {exc}"]

        return []

