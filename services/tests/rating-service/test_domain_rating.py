import pytest


class TestRatingValidation:
    def test_create_rating_with_valid_score(self, models):
        r = models.Rating(score=4)
        assert r.score == 4

    def test_rating_has_default_fields(self, models):
        r = models.Rating()
        assert r.id != ""
        assert r.created_at != ""
        assert r.score == 0

    def test_rating_summary_defaults(self, models):
        s = models.RatingSummary(target_id="rest-1", target_type="RESTAURANT")
        assert s.average_score == 0.0
        assert s.review_count == 0
