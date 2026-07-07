import pytest
from domain.models import Restaurant
from infrastructure.repositories import InMemoryRestaurantRepository


class TestInMemoryRestaurantRepository:
    @pytest.fixture
    def repo(self):
        return InMemoryRestaurantRepository()

    @pytest.fixture
    def sample_restaurant(self):
        return Restaurant(id="r1", name="Test Restaurant", cuisine_type="ITALIAN")

    def test_find_all_returns_empty_list_initially(self, repo):
        assert repo.find_all() == []

    def test_save_and_find_by_id(self, repo, sample_restaurant):
        repo.save(sample_restaurant)
        found = repo.find_by_id("r1")
        assert found is not None
        assert found.name == "Test Restaurant"

    def test_find_by_id_returns_none_for_unknown(self, repo):
        assert repo.find_by_id("nonexistent") is None

    def test_find_all_returns_all_saved(self, repo):
        r1 = Restaurant(id="r1", name="A")
        r2 = Restaurant(id="r2", name="B")
        repo.save(r1)
        repo.save(r2)
        results = repo.find_all()
        assert len(results) == 2

    def test_delete_removes_restaurant(self, repo, sample_restaurant):
        repo.save(sample_restaurant)
        repo.delete("r1")
        assert repo.find_by_id("r1") is None
        assert len(repo.find_all()) == 0

    def test_delete_nonexistent_does_not_raise(self, repo):
        repo.delete("nonexistent")
