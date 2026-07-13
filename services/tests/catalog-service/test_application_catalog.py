class TestEventProjections:
    def test_on_restaurant_registered_creates_entry(self, catalog_service, restaurant_registered):
        catalog_service.on_restaurant_registered(restaurant_registered)
        entry = catalog_service.repository.find_by_id("rest-1")
        assert entry is not None
        assert entry.name == "Chez Testeur"
        assert entry.cuisine_type == "ITALIAN"
        assert entry.is_open is True

    def test_on_restaurant_updated_updates_name(self, catalog_service, restaurant_registered):
        catalog_service.on_restaurant_registered(restaurant_registered)
        catalog_service.on_restaurant_updated({
            "restaurant_id": "rest-1",
            "name": "Chez Testeur 2.0"
        })
        entry = catalog_service.repository.find_by_id("rest-1")
        assert entry.name == "Chez Testeur 2.0"

    def test_on_restaurant_closed_sets_is_open_false(self, catalog_service, restaurant_registered):
        catalog_service.on_restaurant_registered(restaurant_registered)
        catalog_service.on_restaurant_closed({"restaurant_id": "rest-1"})
        entry = catalog_service.repository.find_by_id("rest-1")
        assert entry.is_open is False

    def test_on_menu_updated_indexes_dishes(self, catalog_service, restaurant_registered, menu_updated):
        catalog_service.on_restaurant_registered(restaurant_registered)
        catalog_service.on_menu_updated(menu_updated)
        entry = catalog_service.repository.find_by_id("rest-1")
        assert len(entry.dishes) == 2
        assert entry.dishes[0].name == "Pizza"
        assert entry.dishes[0].price == 12.5

    def test_on_rating_created_updates_score(self, catalog_service, restaurant_registered):
        catalog_service.on_restaurant_registered(restaurant_registered)
        catalog_service.on_rating_created({
            "entity_type": "RESTAURANT",
            "entity_id": "rest-1",
            "average_score": 4.5,
            "review_count": 10
        })
        entry = catalog_service.repository.find_by_id("rest-1")
        assert entry.rating == 4.5
        assert entry.review_count == 10

    def test_on_rating_created_ignores_non_restaurant(self, catalog_service, restaurant_registered):
        catalog_service.on_restaurant_registered(restaurant_registered)
        catalog_service.on_rating_created({
            "entity_type": "DISH",
            "entity_id": "rest-1",
            "average_score": 4.0,
            "review_count": 5
        })
        entry = catalog_service.repository.find_by_id("rest-1")
        assert entry.rating == 0.0


class TestSearchQueries:
    def test_search_by_name(self, catalog_service, restaurant_registered, menu_updated):
        catalog_service.on_restaurant_registered(restaurant_registered)
        catalog_service.on_menu_updated(menu_updated)
        result = catalog_service.search_restaurants(query="Chez")
        assert result["total"] == 1

    def test_search_by_cuisine_type(self, catalog_service, restaurant_registered, second_restaurant):
        catalog_service.on_restaurant_registered(restaurant_registered)
        catalog_service.on_restaurant_registered(second_restaurant)
        result = catalog_service.search_restaurants(cuisine_type="ITALIAN")
        assert result["total"] == 1
        assert result["restaurants"][0].name == "Chez Testeur"

    def test_search_by_open_status(self, catalog_service, restaurant_registered, second_restaurant):
        catalog_service.on_restaurant_registered(restaurant_registered)
        catalog_service.on_restaurant_registered(second_restaurant)
        catalog_service.on_restaurant_closed({"restaurant_id": "rest-1"})
        result = catalog_service.search_restaurants(is_open=True)
        assert result["total"] == 1
        assert result["restaurants"][0].name == "Sushi Bar"

    def test_search_by_min_rating(self, catalog_service, restaurant_registered, second_restaurant):
        catalog_service.on_restaurant_registered(restaurant_registered)
        catalog_service.on_restaurant_registered(second_restaurant)
        catalog_service.on_rating_created({
            "entity_type": "RESTAURANT", "entity_id": "rest-1",
            "average_score": 4.5, "review_count": 10
        })
        catalog_service.on_rating_created({
            "entity_type": "RESTAURANT", "entity_id": "rest-2",
            "average_score": 3.0, "review_count": 5
        })
        result = catalog_service.search_restaurants(min_rating=4.0)
        assert result["total"] == 1
        assert result["restaurants"][0].name == "Chez Testeur"

    def test_pagination(self, catalog_service, restaurant_registered, second_restaurant):
        catalog_service.on_restaurant_registered(restaurant_registered)
        catalog_service.on_restaurant_registered(second_restaurant)
        result = catalog_service.search_restaurants(limit=1, offset=0)
        assert result["total"] == 2
        assert len(result["restaurants"]) == 1

    def test_search_dishes_by_name(self, catalog_service, restaurant_registered, menu_updated):
        catalog_service.on_restaurant_registered(restaurant_registered)
        catalog_service.on_menu_updated(menu_updated)
        dishes = catalog_service.search_dishes(query="Pizza")
        assert len(dishes) == 1
        assert dishes[0]["name"] == "Pizza"

    def test_search_dishes_by_max_price(self, catalog_service, restaurant_registered, menu_updated):
        catalog_service.on_restaurant_registered(restaurant_registered)
        catalog_service.on_menu_updated(menu_updated)
        dishes = catalog_service.search_dishes(max_price=13.0)
        assert len(dishes) == 1
        assert dishes[0]["name"] == "Pizza"

    def test_search_dishes_by_restaurant(self, catalog_service, restaurant_registered, menu_updated, second_restaurant):
        catalog_service.on_restaurant_registered(restaurant_registered)
        catalog_service.on_restaurant_registered(second_restaurant)
        catalog_service.on_menu_updated(menu_updated)
        dishes = catalog_service.search_dishes(restaurant_id="rest-1")
        assert len(dishes) == 2

    def test_results_sorted_by_rating_then_name(self, catalog_service, restaurant_registered, second_restaurant):
        catalog_service.on_restaurant_registered(restaurant_registered)
        catalog_service.on_restaurant_registered(second_restaurant)
        catalog_service.on_rating_created({
            "entity_type": "RESTAURANT", "entity_id": "rest-1",
            "average_score": 4.0, "review_count": 10
        })
        catalog_service.on_rating_created({
            "entity_type": "RESTAURANT", "entity_id": "rest-2",
            "average_score": 4.0, "review_count": 5
        })
        result = catalog_service.search_restaurants()
        names = [e.name for e in result["restaurants"]]
        assert names == ["Chez Testeur", "Sushi Bar"]
