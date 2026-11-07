"""
Quem pode fazer o quê com as CONTAS de usuário (ciclo de vida do acesso).

Escopo desta versão: cadastrar, editar, convidar, desativar e excluir usuários. A autorização
das demais operações do sistema (membros, centros de custo, contas financeiras...) ainda não
está especificada. Funções puras: sem Flask, sem banco, sem E/S. O `Principal` vem sempre da
sessão, nunca de formulário.

O alvo (`target`) é qualquer objeto com `id`, `role` e `family_id` (entidade ou DTO).
"""
import uuid
from dataclasses import dataclass
from typing import Optional, Protocol

from domain.identity.entities import Role


@dataclass(frozen=True)
class Principal:
    """Quem está agindo."""
    user_id: uuid.UUID
    role: Role
    family_id: Optional[uuid.UUID]


class _Target(Protocol):
    id: uuid.UUID
    role: Role
    family_id: Optional[uuid.UUID]


USER_MANAGER_ROLES = (Role.ROOT, Role.SYSTEM_ADMIN, Role.FAMILY_ADMIN)
CREATABLE_ROLES_BY_ACTOR = {
    Role.ROOT: (Role.SYSTEM_ADMIN,),
    Role.SYSTEM_ADMIN: (Role.SYSTEM_ADMIN, Role.FAMILY_ADMIN, Role.FAMILY_USER),
    Role.FAMILY_ADMIN: (Role.FAMILY_ADMIN, Role.FAMILY_USER),
}


def _same_family(actor: Principal, family_id: Optional[uuid.UUID]) -> bool:
    return actor.family_id is not None and actor.family_id == family_id


def can_manage_users(actor: Principal) -> bool:
    """Acesso à área de usuários. Usuário de família comum não administra ninguém.

    O administrador de família sem família não existe (as invariantes do domínio e do banco impedem), mas se
    um ator assim aparecesse a listagem ficaria sem o filtro do tenant e mostraria todos os usuários:
    por isso ele é negado aqui, na porta de entrada de toda operação.
    """
    if actor.role is Role.FAMILY_ADMIN:
        return actor.family_id is not None
    return actor.role in USER_MANAGER_ROLES


def creatable_roles(actor: Principal) -> tuple[Role, ...]:
    return CREATABLE_ROLES_BY_ACTOR.get(actor.role, ())


def can_create_user(actor: Principal, role: Optional[Role], family_id: Optional[uuid.UUID]) -> bool:
    """O root nunca é criado pela aplicação; o administrador de família só cria na própria família."""
    if role not in creatable_roles(actor):
        return False
    if actor.role is Role.FAMILY_ADMIN:
        return _same_family(actor, family_id)
    return True


def can_view_user(actor: Principal, target: _Target) -> bool:
    if actor.role in (Role.ROOT, Role.SYSTEM_ADMIN):
        return True
    if actor.role is Role.FAMILY_ADMIN:
        return _same_family(actor, target.family_id)
    return False


def can_manage_user(actor: Principal, target: _Target) -> bool:
    """Editar dados, desativar/reativar e excluir. Ninguém age sobre o root pela aplicação."""
    if target.role is Role.ROOT:
        return False
    if actor.role is Role.ROOT:
        return target.role is Role.SYSTEM_ADMIN
    if actor.role is Role.SYSTEM_ADMIN:
        return True
    if actor.role is Role.FAMILY_ADMIN:
        return target.role in (Role.FAMILY_ADMIN, Role.FAMILY_USER) and _same_family(actor, target.family_id)
    return False


def can_issue_invitation(actor: Principal, target: _Target) -> bool:
    """Convite de ativação (conta pendente) ou redefinição de senha de um administrador do sistema.

    - alvo administrador do sistema: só outro administrador do sistema (ou o root, como rede de
      segurança se o único administrador perder o acesso);
    - alvo usuário de família: administrador do sistema, ou administrador da MESMA família;
      vale só para conta pendente (quem já ativou redefine a própria senha: o serviço confere);
    - ninguém emite convite para si mesmo, nem para o root.
    """
    if target.id == actor.user_id or target.role is Role.ROOT:
        return False
    if target.role is Role.SYSTEM_ADMIN:
        return actor.role in (Role.ROOT, Role.SYSTEM_ADMIN)
    if actor.role is Role.SYSTEM_ADMIN:
        return True
    return actor.role is Role.FAMILY_ADMIN and _same_family(actor, target.family_id)
