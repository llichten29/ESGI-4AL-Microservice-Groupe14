import pytest
from domain.models import Customer, CustomerAddress, OrderRef


class TestMongoDBCustomerRepository:
    @pytest.fixture
    def repo(self, customer_repo):
        return customer_repo

    def test_find_by_id_returns_none_for_empty(self, repo):
        assert repo.find_by_id("nonexistent") is None

    def test_save_and_find_by_id(self, repo):
        customer = Customer(id="c1", name="Alice", email="alice@test.com", password_hash="hash123")
        repo.save(customer)
        found = repo.find_by_id("c1")
        assert found is not None
        assert found.name == "Alice"
        assert found.email == "alice@test.com"
        assert found.password_hash == "hash123"

    def test_find_by_email(self, repo):
        customer = Customer(id="c2", name="Bob", email="bob@test.com", password_hash="hash")
        repo.save(customer)
        found = repo.find_by_email("bob@test.com")
        assert found is not None
        assert found.id == "c2"

    def test_find_by_email_returns_none_for_unknown(self, repo):
        assert repo.find_by_email("unknown@test.com") is None

    def test_save_updates_existing(self, repo):
        customer = Customer(id="c3", name="Original", email="orig@test.com")
        repo.save(customer)
        customer.name = "Updated"
        repo.save(customer)
        found = repo.find_by_id("c3")
        assert found.name == "Updated"

    def test_delete_removes_customer(self, repo):
        customer = Customer(id="c4", name="To Delete", email="del@test.com")
        repo.save(customer)
        repo.delete("c4")
        assert repo.find_by_id("c4") is None

    def test_save_with_addresses_and_orders(self, repo):
        customer = Customer(
            id="c5",
            name="Full",
            email="full@test.com",
            addresses=[CustomerAddress(id="a1", label="Home", street="1 Main St", is_default=True)],
            orders=[OrderRef(order_id="o1", status="CREATED", total=10.0)]
        )
        repo.save(customer)
        found = repo.find_by_id("c5")
        assert len(found.addresses) == 1
        assert found.addresses[0].label == "Home"
        assert len(found.orders) == 1
        assert found.orders[0].order_id == "o1"
