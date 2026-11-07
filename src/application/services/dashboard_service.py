from application.dtos.dashboard_dtos import EntityCountsDTO
from application.interfaces.unit_of_work import AbstractUnitOfWork

class DashboardService:
    """
    Visão geral da aplicação: quantidade de registros de cada entidade.
    Sem nenhum acoplamento com Web, HTTP ou SQL.
    """
    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    def get_entity_counts(self) -> EntityCountsDTO:
        # Conta via list_all(): os volumes de uma família são pequenos. Se crescerem,
        # trocar por um count() nos repositórios, sem mudar este contrato.
        with self.uow:
            return EntityCountsDTO(
                families=len(self.uow.families.list_all()),
                members=len(self.uow.members.list_all()),
                users=len(self.uow.users.list_all()),
                cost_centers=len(self.uow.family_cost_centers.list_all()),
                categories=len(self.uow.categories.list_all()),
            )
