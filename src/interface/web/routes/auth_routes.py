import hashlib
import time

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_limiter.util import get_remote_address
from flask_login import current_user, login_required, login_user, logout_user

from application.services.auth_service import AuthService
from application.services.credential_service import SET_PASSWORD_PURPOSES, CredentialService
from domain.shared.exceptions import AuthenticationFailedError, DomainValidationError
from interface.web.security import SessionUser, is_safe_next, limiter

bp = Blueprint('auth', __name__)

GENERIC_INVALID_LINK = "Link inválido, expirado ou já utilizado."


def get_auth_service() -> AuthService:
    return current_app.auth_service_factory()


def get_credential_service() -> CredentialService:
    return current_app.credential_service_factory()


# --- Chaves de limite de tentativas ---

def _identifier_key() -> str:
    return (request.form.get("identifier") or "").strip().lower()[:200] or get_remote_address()


def _email_key() -> str:
    return (request.form.get("email") or "").strip().lower()[:200] or get_remote_address()


def _token_key() -> str:
    token = (request.view_args or {}).get("token", "")
    return "token:" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


def _user_key() -> str:
    return f"user:{current_user.get_id()}" if current_user.is_authenticated else get_remote_address()


def _start_session(dto) -> None:
    """Abre uma sessão NOVA (evita fixação de sessão) com os prazos de inatividade e de duração."""
    session.clear()
    login_user(SessionUser(dto))
    session.permanent = True
    session["login_at"] = int(time.time())


# --- Login e logout ---

@bp.route('/login', methods=['GET'])
def login():
    if current_user.is_authenticated and current_app.config["AUTH_ENABLED"]:
        return redirect(url_for('dashboard.index'))
    return render_template('auth/login.html', next=request.args.get('next', ''), identifier='', error=None)


@bp.route('/authenticate', methods=['POST'])
@limiter.limit("30 per minute")
@limiter.limit("5 per minute", key_func=_identifier_key)
def authenticate():
    identifier = request.form.get('identifier')
    next_url = request.form.get('next', '')
    try:
        dto = get_auth_service().authenticate(identifier, request.form.get('password'))
    except AuthenticationFailedError as error:
        return render_template(
            'auth/login.html', next=next_url, identifier=identifier or '', error=str(error),
        ), 401

    _start_session(dto)
    return redirect(next_url if is_safe_next(next_url) else url_for('dashboard.index'))


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    session.clear()
    flash("Você saiu do sistema.", "success")
    return redirect(url_for('auth.login'))


# --- Troca da própria senha ---

@bp.route('/change-password', methods=['GET'])
@login_required
def change_password():
    return render_template('auth/change_password.html', error=None)


@bp.route('/update-password', methods=['POST'])
@login_required
@limiter.limit("5 per minute", key_func=_user_key)
def update_password():
    try:
        dto = get_auth_service().change_own_password(
            current_user.dto.id,
            request.form.get('current_password'),
            request.form.get('password'),
            request.form.get('password_confirmation'),
        )
    except DomainValidationError as error:
        return render_template('auth/change_password.html', error=str(error)), 400

    # A senha mudou, então o identificador da sessão também: renova só a sessão atual (as demais caem),
    # sem reiniciar o prazo absoluto desde o login.
    login_user(SessionUser(dto))
    flash("Senha alterada com sucesso. Os outros acessos abertos foram encerrados.", "success")
    return redirect(url_for('dashboard.index'))


# --- Definir a senha por convite (ativação / redefinição de administrador do sistema) ---

def _invalid_link(status: int = 400):
    return render_template('auth/message.html', title="Link inválido", message=GENERIC_INVALID_LINK), status


@bp.route('/activate/<token>', methods=['GET'])
@limiter.limit("30 per minute")
def activate(token):
    try:
        info = get_credential_service().inspect_invitation(token, SET_PASSWORD_PURPOSES)
    except AuthenticationFailedError:
        return _invalid_link()
    return render_template('auth/set_password.html', token=token, info=info, error=None)


@bp.route('/set-password/<token>', methods=['POST'])
@limiter.limit("10 per minute")
@limiter.limit("20 per hour", key_func=_token_key)
def set_password(token):
    service = get_credential_service()
    try:
        service.complete_invitation(
            token, request.form.get('code'), request.form.get('password'), request.form.get('password_confirmation'),
        )
    except DomainValidationError as error:
        try:
            info = service.inspect_invitation(token, SET_PASSWORD_PURPOSES)
        except AuthenticationFailedError:
            return _invalid_link()
        return render_template('auth/set_password.html', token=token, info=info, error=str(error)), 400
    except AuthenticationFailedError as error:
        return render_template(
            'auth/message.html', title="Não foi possível definir a senha", message=str(error)
        ), 400

    flash("Senha definida com sucesso. Entre com o seu usuário e a nova senha.", "success")
    return redirect(url_for('auth.login'))


# --- Recuperação autônoma ("Esqueci minha senha") ---

@bp.route('/forgot-password', methods=['GET'])
def forgot_password():
    return render_template('auth/forgot_password.html')


@bp.route('/request-recovery', methods=['POST'])
@limiter.limit("10 per hour")
@limiter.limit("3 per hour", key_func=_email_key)
def request_recovery():
    # A resposta é SEMPRE a mesma, exista ou não uma conta elegível com este e-mail.
    get_credential_service().request_recovery(request.form.get('email'))
    return render_template('auth/recovery_requested.html')


@bp.route('/recover/<token>', methods=['GET'])
@limiter.limit("30 per minute")
def recover(token):
    try:
        get_credential_service().inspect_recovery(token)
    except AuthenticationFailedError:
        return _invalid_link()
    return render_template('auth/reset_password.html', token=token, error=None)


@bp.route('/reset-password/<token>', methods=['POST'])
@limiter.limit("10 per hour")
def reset_password(token):
    try:
        get_credential_service().complete_recovery(
            token, request.form.get('password'), request.form.get('password_confirmation'),
        )
    except DomainValidationError as error:
        return render_template('auth/reset_password.html', token=token, error=str(error)), 400
    except AuthenticationFailedError:
        return _invalid_link()

    flash("Senha redefinida com sucesso. Entre com o seu usuário e a nova senha.", "success")
    return redirect(url_for('auth.login'))
