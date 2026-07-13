import pytest


class TestCreateRating:
    def test_creates_rating_and_publishes_event(self, rating_service, rating_payload, mock_broker):
        rating = rating_service.create_rating(rating_payload)
        assert rating.score == 5
        assert rating.target_id == "rest-1"
        assert rating.target_type == "RESTAURANT"
        assert rating.order_id == "order-1"

        kwargs = mock_broker.publish_event.call_args.kwargs
        assert kwargs["exchange"] == "rating.events"
        assert kwargs["routing_key"] == "rating.created"
        assert kwargs["event_data"]["entity_type"] == "RESTAURANT"
        assert kwargs["event_data"]["entity_id"] == "rest-1"
        assert kwargs["event_data"]["score"] == 5
        assert kwargs["event_data"]["average_score"] == 5.0
        assert kwargs["event_data"]["review_count"] == 1

    def test_rejects_score_below_1(self, rating_service, rating_payload, models):
        rating_payload["score"] = 0
        with pytest.raises(models.InvalidScore):
            rating_service.create_rating(rating_payload)

    def test_rejects_score_above_5(self, rating_service, rating_payload, models):
        rating_payload["score"] = 6
        with pytest.raises(models.InvalidScore):
            rating_service.create_rating(rating_payload)

    def test_does_not_publish_without_broker(self, repo, rating_payload):
        from application.rating_service import RatingService
        svc = RatingService(repository=repo, broker=None)
        rating = svc.create_rating(rating_payload)
        assert rating.score == 5

    def test_default_target_type_is_restaurant(self, rating_service, mock_broker):
        payload = {"target_id": "rest-1", "score": 4}
        rating = rating_service.create_rating(payload)
        assert rating.target_type == "RESTAURANT"


class TestRecomputeSummary:
    def test_average_is_computed_correctly(self, rating_service):
        rating_service.create_rating({"target_id": "rest-1", "target_type": "RESTAURANT", "score": 5})
        rating_service.create_rating({"target_id": "rest-1", "target_type": "RESTAURANT", "score": 3})
        summary = rating_service.get_summary("rest-1", "RESTAURANT")
        assert summary.average_score == 4.0
        assert summary.review_count == 2


class TestGetRating:
    def test_get_by_id_returns_rating(self, rating_service, rating_payload):
        created = rating_service.create_rating(rating_payload)
        found = rating_service.get_rating(created.id)
        assert found.id == created.id
        assert found.score == 5

    def test_get_unknown_raises_404(self, rating_service, models):
        with pytest.raises(models.RatingNotFound):
            rating_service.get_rating("unknown")

    def test_get_ratings_for_target(self, rating_service):
        rating_service.create_rating({"target_id": "rest-1", "target_type": "RESTAURANT", "score": 4})
        rating_service.create_rating({"target_id": "rest-2", "target_type": "RESTAURANT", "score": 5})
        ratings = rating_service.get_ratings_for_target("rest-1", "RESTAURANT")
        assert len(ratings) == 1

    def test_get_summary_for_target_without_ratings(self, rating_service):
        summary = rating_service.get_summary("rest-99", "RESTAURANT")
        assert summary.average_score == 0.0
        assert summary.review_count == 0
