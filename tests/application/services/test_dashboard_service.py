import uuid

from application.services.dashboard_service import DashboardService
from domain.family.entities import Family, FamilyCostCenter, Member
from domain.financial.entities import Category, TransactionType
from fakes.family_fakes import FakeUnitOfWork

def test_counts_every_entity_type():
    uow = FakeUnitOfWork()
    family = Family(name="Silva")
    uow.families.save(family)
    uow.families.save(Family(name="Souza"))
    uow.members.save(Member(family_id=family.id, name="João"))
    uow.members.save(Member(family_id=family.id, name="Maria"))
    uow.members.save(Member(family_id=uuid.uuid4(), name="Pedro"))
    uow.family_cost_centers.save(FamilyCostCenter(family_id=family.id, name="Casa de Praia"))
    uow.categories.save(Category(name="Lazer", type=TransactionType.EXPENSE))
    uow.categories.save(Category(name="Salário", type=TransactionType.INCOME))

    counts = DashboardService(uow).get_entity_counts()

    assert (counts.families, counts.members, counts.cost_centers, counts.categories) == (2, 3, 1, 2)

def test_counts_are_zero_when_nothing_is_registered():
    counts = DashboardService(FakeUnitOfWork()).get_entity_counts()

    assert (counts.families, counts.members, counts.cost_centers, counts.categories) == (0, 0, 0, 0)
