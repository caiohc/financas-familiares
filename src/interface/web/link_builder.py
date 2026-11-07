from typing import Optional

from flask import url_for

from application.interfaces.link_builder import AbstractLinkBuilder


class FlaskLinkBuilder(AbstractLinkBuilder):
    """Monta os links dos e-mails.

    Com `base_url` (APP_BASE_URL), o endereço vem da configuração. Sem ele (só em desenvolvimento), vem
    do cabeçalho Host da requisição, que quem faz a requisição controla: por isso em produção a
    configuração é obrigatória (um atacante poderia pedir a recuperação da senha de uma vítima com um
    Host forjado e fazer o e-mail legítimo apontar para o site dele).
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url.rstrip("/") if base_url else None

    def _build(self, endpoint: str, token: str) -> str:
        if self.base_url:
            return self.base_url + url_for(endpoint, token=token)
        return url_for(endpoint, token=token, _external=True)

    def invitation_link(self, token: str) -> str:
        return self._build("auth.activate", token)

    def recovery_link(self, token: str) -> str:
        return self._build("auth.recover", token)
