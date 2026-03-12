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

    def _build_html_body(self, payload: SubmissionEmailPayload) -> str:
        # Template HTML elegante e compacto
        urgencia_badge = f'<span style="background-color: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 10px;">URGENTE</span>' if payload.urgencia else ""
        
        # Limita descrição aos 100 primeiros caracteres
        desc_curta = (payload.descricao[:100] + "...") if len(payload.descricao) > 100 else payload.descricao
        
        return f"""
        <html>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #334155; line-height: 1.4; margin: 0; padding: 0;">
                <div style="max-width: 600px; margin: 20px auto; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
                    <div style="background-color: #0c4a6e; padding: 20px; text-align: center;">
                        <h1 style="color: white; margin: 0; font-size: 22px; letter-spacing: 1px;">Comunica IME!</h1>
                    </div>
                    <div style="padding: 24px;">
                        <p style="font-size: 16px; margin-top: 0;">Olá,</p>
                        <p style="font-size: 14px;">Uma nova solicitação foi registrada na plataforma.</p>
                        
                        <div style="background-color: #f8fafc; padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #0ea5e9;">
                            <h3 style="margin-top: 0; color: #0284c7; font-size: 14px; text-transform: uppercase;">Detalhes da Demanda</h3>
                            <table style="width: 100%; font-size: 12px; border-collapse: collapse;">
                                <tr><td style="padding: 4px 0; color: #64748b; width: 120px;"><b>Solicitante:</b></td><td style="padding: 4px 0;">{payload.solicitante}</td></tr>
                                <tr><td style="padding: 4px 0; color: #64748b;"><b>E-mail:</b></td><td style="padding: 4px 0;">{payload.email}</td></tr>
                                <tr><td style="padding: 4px 0; color: #64748b;"><b>Unidade:</b></td><td style="padding: 4px 0;">{payload.unidade}</td></tr>
                                <tr><td style="padding: 4px 0; color: #64748b;"><b>Tipo:</b></td><td style="padding: 4px 0;">{payload.tipo} {urgencia_badge}</td></tr>
                                <tr><td style="padding: 4px 0; color: #64748b;"><b>Previsão:</b></td><td style="padding: 4px 0;">{payload.data_publicacao}</td></tr>
                            </table>
                        </div>

                        <div style="margin-top: 20px;">
                            <h3 style="font-size: 13px; color: #334155; margin-bottom: 8px;">Breve Descrição:</h3>
                            <div style="font-size: 12px; color: #475569; background: #fff; border: 1px solid #f1f5f9; padding: 10px; border-radius: 4px; font-style: italic;">
                                "{desc_curta}"
                            </div>
                        </div>

                        <p style="font-size: 12px; color: #64748b; margin-top: 30px; text-align: center;">
                            Para ver todos os detalhes e anexos, acesse o <b>Painel de Controle NEX</b>.
                        </p>
                    </div>
                    <div style="background-color: #f1f5f9; padding: 15px; text-align: center; font-size: 11px; color: #94a3b8;">
                        Mensagem automática enviada pelo sistema Comunica IME - UFBA.
                    </div>
                </div>
            </body>
        </html>
        """

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
        
        # Enviando como HTML
        html_content = self._build_html_body(payload)
        message.set_content("Para visualizar esta mensagem, utilize um cliente de e-mail com suporte a HTML.")
        message.add_alternative(html_content, subtype='html')

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

