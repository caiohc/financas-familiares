import uuid
from typing import List, Optional

from application.dtos.family_dtos import CreateMemberDTO, UpdateMemberDTO, MemberResponseDTO
from application.dtos.shared_dtos import DeletionPreviewDTO
from application.dtos.shared_dtos import DEFAULT_PAGE_SIZE, PageDTO
from application.services.pagination import build_page
from application.interfaces.unit_of_work import AbstractUnitOfWork
from domain.family.entities import Member
from domain.family.exceptions import member_already_exists, member_has_dependencies, member_not_found

class MemberService:
    """
    Orquestra as operações de negócio de membro da família.
    Sem nenhum acoplamento com Web, HTTP ou SQL.
    """
    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    def _to_dto(self, member: Member) -> MemberResponseDTO:
        return MemberResponseDTO(id=member.id, family_id=member.family_id, name=member.name)

    @staticmethod
    def _by_name(members: List[Member]) -> List[Member]:
        return sorted(members, key=lambda m: m.name.lower())

    def create_member(self, dto: CreateMemberDTO) -> MemberResponseDTO:
        with self.uow:
            member = Member(family_id=dto.family_id, name=dto.name)

            if self.uow.members.get_by_name(member.family_id, member.name):
                raise member_already_exists(member.name)

            self.uow.members.save(member)
            self.uow.commit()
            return self._to_dto(member)

    def get_member(self, member_id: uuid.UUID) -> MemberResponseDTO:
        with self.uow:
            member = self.uow.members.get_by_id(member_id)
            if not member:
                raise member_not_found(member_id)
            return self._to_dto(member)

    def list_family_members(self, family_id: uuid.UUID) -> List[MemberResponseDTO]:
        with self.uow:
            return [self._to_dto(m) for m in self._by_name(self.uow.members.list_by_family(family_id))]

    def list_all_members(self) -> List[MemberResponseDTO]:
        """Provisório, sem escopo de família: sem login ainda não há "a família do usuário atual"."""
        with self.uow:
            return [self._to_dto(m) for m in self._by_name(self.uow.members.list_all())]

    def list_all_members_page(
        self, page: Optional[int] = 1, page_size: Optional[int] = DEFAULT_PAGE_SIZE,
        sort_by: Optional[str] = None, sort_dir: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PageDTO[MemberResponseDTO]:
        with self.uow:
            return build_page(
                self.uow.members.list_page, self._to_dto, page, page_size, sort_by, sort_dir, ("name", "family"), search,
            )

    def update_member(self, member_id: uuid.UUID, dto: UpdateMemberDTO) -> MemberResponseDTO:
        with self.uow:
            member = self.uow.members.get_by_id(member_id)
            if not member:
                raise member_not_found(member_id)

            new_name = Member.normalize_name(dto.name)
            existing = self.uow.members.get_by_name(member.family_id, new_name)
            if existing and existing.id != member_id:
                raise member_already_exists(new_name)

            member.rename(new_name)
            self.uow.members.save(member)
            self.uow.commit()
            return self._to_dto(member)

    def preview_member_deletion(self, member_id: uuid.UUID) -> DeletionPreviewDTO:
        """Antecipa, para a tela de confirmação, se a exclusão será bloqueada e por quê."""
        with self.uow:
            member = self.uow.members.get_by_id(member_id)
            if not member:
                raise member_not_found(member_id)

            blocked = self.uow.members.has_dependencies(member_id)
            reason = str(member_has_dependencies(member_id)) if blocked else None
            return DeletionPreviewDTO(name=member.name, blocked_reason=reason)

    def delete_member(self, member_id: uuid.UUID) -> None:
        with self.uow:
            member = self.uow.members.get_by_id(member_id)
            if not member:
                raise member_not_found(member_id)

            if self.uow.members.has_dependencies(member_id):
                raise member_has_dependencies(member_id)

            self.uow.members.delete(member_id)
            self.uow.commit()
