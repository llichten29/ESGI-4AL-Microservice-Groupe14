class TestInMemoryRatingRepository:
    def test_save_and_find_by_id(self, repo, models):
        rating = models.Rating(score=4, target_id="rest-1", target_type="RESTAURANT")
        repo.save(rating)
        found = repo.find_by_id(rating.id)
        assert found.score == 4

    def test_find_by_id_returns_none_for_missing(self, repo):
        assert repo.find_by_id("missing") is None

    def test_find_by_target_filters_correctly(self, repo, models):
        repo.save(models.Rating(score=5, target_id="r1", target_type="RESTAURANT"))
        repo.save(models.Rating(score=3, target_id="r1", target_type="RESTAURANT"))
        repo.save(models.Rating(score=4, target_id="r2", target_type="RESTAURANT"))
        results = repo.find_by_target("r1", "RESTAURANT")
        assert len(results) == 2
        assert all(r.target_id == "r1" for r in results)

    def test_find_all_returns_all(self, repo, models):
        repo.save(models.Rating(target_id="r1"))
        repo.save(models.Rating(target_id="r2"))
        assert len(repo.find_all()) == 2
