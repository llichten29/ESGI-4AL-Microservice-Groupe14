class TestInMemoryCatalogRepository:
    def test_save_and_find_by_id(self, repo, models):
        entry = models.CatalogEntry(restaurant_id="rest-1", name="Chez Testeur")
        repo.save(entry)
        found = repo.find_by_id("rest-1")
        assert found is not None
        assert found.name == "Chez Testeur"

    def test_find_by_id_returns_none_for_missing(self, repo):
        assert repo.find_by_id("missing") is None

    def test_find_all_returns_all_entries(self, repo, models):
        repo.save(models.CatalogEntry(restaurant_id="r1"))
        repo.save(models.CatalogEntry(restaurant_id="r2"))
        assert len(repo.find_all()) == 2

    def test_save_overwrites_existing(self, repo, models):
        repo.save(models.CatalogEntry(restaurant_id="r1", name="First"))
        repo.save(models.CatalogEntry(restaurant_id="r1", name="Second"))
        assert len(repo.find_all()) == 1
        assert repo.find_by_id("r1").name == "Second"
