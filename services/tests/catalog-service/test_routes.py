class TestCatalogRoutes:
    def test_search_restaurants_returns_200(self, catalog_client, restaurant_registered, catalog_service):
        catalog_service.on_restaurant_registered(restaurant_registered)
        resp = catalog_client.get('/restaurants/search?query=Chez')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total"] == 1
        assert body["restaurants"][0]["name"] == "Chez Testeur"

    def test_search_restaurants_empty_result(self, catalog_client):
        resp = catalog_client.get('/restaurants/search?query=Nothing')
        assert resp.status_code == 200
        assert resp.get_json()["total"] == 0

    def test_search_restaurants_by_cuisine(self, catalog_client, restaurant_registered, catalog_service):
        catalog_service.on_restaurant_registered(restaurant_registered)
        resp = catalog_client.get('/restaurants/search?cuisineType=ITALIAN')
        assert resp.status_code == 200
        assert resp.get_json()["total"] == 1

    def test_search_restaurants_by_open(self, catalog_client, restaurant_registered, catalog_service):
        catalog_service.on_restaurant_registered(restaurant_registered)
        resp = catalog_client.get('/restaurants/search?isOpen=true')
        assert resp.status_code == 200
        assert resp.get_json()["total"] == 1

    def test_search_dishes_returns_200(self, catalog_client, restaurant_registered, menu_updated, catalog_service):
        catalog_service.on_restaurant_registered(restaurant_registered)
        catalog_service.on_menu_updated(menu_updated)
        resp = catalog_client.get('/dishes/search?query=Pizza')
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["dishes"]) == 1
        assert body["dishes"][0]["name"] == "Pizza"

    def test_search_dishes_by_max_price(self, catalog_client, restaurant_registered, menu_updated, catalog_service):
        catalog_service.on_restaurant_registered(restaurant_registered)
        catalog_service.on_menu_updated(menu_updated)
        resp = catalog_client.get('/dishes/search?maxPrice=13.0')
        assert resp.status_code == 200
        assert len(resp.get_json()["dishes"]) == 1
