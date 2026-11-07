"""
Segurança da camada web: sessão (Flask-Login), proteção de rotas, CSRF, limite de tentativas e cabeçalhos.

Princípio: NEGAR POR PADRÃO. Toda rota exige login, exceto as listadas em PUBLIC_ENDPOINTS. Uma rota
nova nasce protegida; liberá-la é uma decisão explícita (e um teste percorre `app.url_map` para garantir).
"""
import time
from urllib.parse import urlparse

from flask import Flask, current_app, render_template, request, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, UserMixin, current_user, logout_user
from flask_wtf.csrf import CSRFError, CSRFProtect

from application.dtos.identity_dtos import SessionUserDTO
from domain.identity import policy

csrf = CSRFProtect()
limiter = Limiter(get_remote_address, storage_uri="memory://", default_limits=[])

# Únicas rotas acessíveis sem login: entrar, definir a senha pelo convite, recuperar a senha e os estáticos.
PUBLIC_ENDPOINTS = frozenset({
    "static",
    "auth.login",
    "auth.authenticate",
    "auth.activate",
    "auth.set_password",
    "auth.forgot_password",
    "auth.request_recovery",
    "auth.recover",
    "auth.reset_password",
})


class SessionUser(UserMixin):
    """Adaptador entre o usuário autenticado e o Flask-Login. O domínio não conhece o Flask."""

    def __init__(self, dto: SessionUserDTO):
        self.dto = dto

    def get_id(self) -> str:
        return self.dto.session_id

    @property
    def principal(self):
        return self.dto.principal

    @property
    def display_name(self) -> str:
        return self.dto.display_name

    @property
    def username(self) -> str:
        return self.dto.username

    @property
    def role(self):
        return self.dto.role


def is_safe_next(target: str | None) -> bool:
    """Só caminhos relativos do próprio site: impede que o login redirecione para um site de terceiros."""
    if not target or not target.startswith("/") or target.startswith("//") or target.startswith("/\\"):
        return False
    parsed = urlparse(target)
    return not parsed.scheme and not parsed.netloc and "\\" not in target and "\n" not in target and "\r" not in target


def _auth_service():
    return current_app.auth_service_factory()


def init_security(app: Flask) -> None:
    # Um gerenciador de login POR aplicação: um objeto global compartilharia o carregador de desenvolvimento
    # (auto-login) com qualquer outra aplicação criada no mesmo processo.
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = None       # sem aviso extra ao redirecionar
    login_manager.session_protection = "basic"
    csrf.init_app(app)
    limiter.init_app(app)

    @login_manager.user_loader
    def load_user(session_id: str):
        dto = _auth_service().load_session_user(session_id)
        return SessionUser(dto) if dto else None

    if not app.config["AUTH_ENABLED"]:
        @login_manager.request_loader
        def load_development_user(_request):
            """Desenvolvimento (AUTH_ENABLED=false): autentica sozinho como o usuário configurado. A autorização
            continua valendo, porque há um usuário de verdade por trás."""
            if current_app.config["AUTH_ENABLED"]:          # defesa em profundidade: nunca com a proteção ligada
                return None
            dto = _auth_service().find_session_user_by_username(current_app.config["DEV_AUTO_LOGIN_USERNAME"])
            return SessionUser(dto) if dto else None

    @app.before_request
    def guard():
        if request.endpoint is None or request.endpoint == "static":
            return None
        authenticated = current_user.is_authenticated
        if authenticated and current_app.config["AUTH_ENABLED"]:
            login_at = session.get("login_at")
            absolute = current_app.config["SESSION_ABSOLUTE_TIMEOUT_HOURS"] * 3600
            if not isinstance(login_at, (int, float)) or time.time() - login_at > absolute:
                logout_user()
                session.clear()
                authenticated = False
        if request.endpoint in PUBLIC_ENDPOINTS or authenticated:
            return None
        return current_app.login_manager.unauthorized()

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # Os links de convite e de recuperação trazem o token na URL: nunca vazá-lo pelo cabeçalho Referer.
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.endpoint != "static":
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.context_processor
    def inject_security_context():
        return {
            "auth_enabled": current_app.config["AUTH_ENABLED"],
            "can_manage_users": current_user.is_authenticated and policy.can_manage_users(current_user.principal),
        }

    @app.errorhandler(CSRFError)
    def csrf_failed(_error):
        return render_template(
            "auth/message.html", title="Requisição inválida",
            message="A sua sessão expirou ou a requisição não foi reconhecida. Volte, recarregue a página e tente de novo.",
        ), 400

    @app.errorhandler(429)
    def too_many_requests(_error):
        return render_template(
            "auth/message.html", title="Muitas tentativas",
            message="Foram feitas muitas tentativas em pouco tempo. Aguarde um pouco e tente novamente.",
        ), 429

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template(
            "auth/message.html", title="Acesso negado",
            message="Você não tem permissão para acessar esta página.",
        ), 403
