import pytest


class TestInMemoryDeliveryRepository:
    def test_find_all_returns_empty_initially(self, repo):
        assert repo.find_all() == []

    def test_save_and_find_by_id(self, repo, models):
        d = models.Delivery(order_id="order-1")
        repo.save(d)
        found = repo.find_by_id(d.id)
        assert found is not None
        assert found.id == d.id
        assert found.order_id == "order-1"

    def test_find_by_id_returns_none_for_unknown(self, repo):
        assert repo.find_by_id("unknown") is None

    def test_find_by_order_id(self, repo, models):
        d1 = models.Delivery(order_id="order-1")
        d2 = models.Delivery(order_id="order-2")
        repo.save(d1)
        repo.save(d2)
        found = repo.find_by_order_id("order-2")
        assert found is not None
        assert found.id == d2.id

    def test_find_by_order_id_returns_none(self, repo):
        assert repo.find_by_order_id("unknown") is None

    def test_save_updates_existing(self, repo, models):
        d = models.Delivery(order_id="order-1", status=models.DeliveryStatus.PENDING_ASSIGNMENT)
        repo.save(d)
        d.status = models.DeliveryStatus.ASSIGNED
        repo.save(d)
        found = repo.find_by_id(d.id)
        assert found.status == models.DeliveryStatus.ASSIGNED

    def test_find_all_returns_all(self, repo, models):
        for i in range(3):
            repo.save(models.Delivery(order_id=f"order-{i}"))
        assert len(repo.find_all()) == 3
