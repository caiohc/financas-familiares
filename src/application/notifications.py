"""
Textos dos e-mails de segurança (assunto, corpo). Texto simples, em pt-BR.

Regras: o e-mail do convite NUNCA traz o código (ele vai por outro canal) e nenhum e-mail
traz senha. Os links carregam o token, então não devem ser encaminhados.
"""


def _human_duration(hours: int | None = None, minutes: int | None = None) -> str:
    if hours is not None:
        return f"{hours} hora" + ("" if hours == 1 else "s")
    return f"{minutes} minuto" + ("" if minutes == 1 else "s")


def invitation_email(*, name: str, link: str, valid_for_hours: int, reset: bool) -> tuple[str, str]:
    if reset:
        subject = "Redefinição da sua senha de acesso"
        intro = "Um administrador solicitou a redefinição da sua senha de acesso."
        action = "definir a nova senha"
    else:
        subject = "Convite para ativar a sua conta"
        intro = "Você foi cadastrado no sistema de finanças da família."
        action = "ativar a sua conta e definir a sua senha"
    body = (
        f"Olá, {name}.\n\n"
        f"{intro}\n\n"
        f"Para {action}, abra o link abaixo. Ele vale por {_human_duration(hours=valid_for_hours)} e só pode ser usado uma vez:\n\n"
        f"{link}\n\n"
        "Na página, você precisará informar um CÓDIGO que o administrador lhe passou por outro meio "
        "(pessoalmente, telefone ou mensagem). O código não vai neste e-mail.\n\n"
        "Se você não esperava esta mensagem, ignore-a: nada acontece sem o código.\n"
    )
    return subject, body


def recovery_email(*, link: str, valid_for_minutes: int) -> tuple[str, str]:
    subject = "Recuperação de senha"
    body = (
        "Recebemos um pedido para redefinir a senha da sua conta.\n\n"
        f"Para escolher uma nova senha, abra o link abaixo. Ele vale por {_human_duration(minutes=valid_for_minutes)} "
        "e só pode ser usado uma vez:\n\n"
        f"{link}\n\n"
        "Se não foi você quem pediu, ignore esta mensagem: a sua senha continua a mesma.\n"
    )
    return subject, body


def password_changed_email(*, name: str | None) -> tuple[str, str]:
    subject = "A senha da sua conta foi alterada"
    greeting = f"Olá, {name}.\n\n" if name else ""
    body = (
        f"{greeting}"
        "A senha da sua conta acabou de ser alterada e todos os acessos abertos foram encerrados.\n\n"
        "Se não foi você, avise um administrador imediatamente.\n"
    )
    return subject, body
