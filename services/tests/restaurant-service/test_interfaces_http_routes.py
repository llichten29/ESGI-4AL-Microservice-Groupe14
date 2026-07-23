class TestRestaurantRoutes:
    def test_create_restaurant(self, restaurant_client):
        resp = restaurant_client.post('/restaurants', json={
            "name": "Pizza Place",
            "cuisine_type": "ITALIAN",
            "phone": "+33123456789"
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Pizza Place"
        assert data["cuisine_type"] == "ITALIAN"
        assert data["id"] is not None

    def test_create_restaurant_missing_body(self, restaurant_client):
        resp = restaurant_client.post('/restaurants', json={})
        assert resp.status_code == 400

    def test_list_restaurants(self, restaurant_client):
        restaurant_client.post('/restaurants', json={"name": "A"})
        restaurant_client.post('/restaurants', json={"name": "B"})
        resp = restaurant_client.get('/restaurants')
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["restaurants"]) == 2

    def test_get_restaurant(self, restaurant_client):
        create_resp = restaurant_client.post('/restaurants', json={"name": "Detail"})
        rest_id = create_resp.get_json()["id"]
        resp = restaurant_client.get(f'/restaurants/{rest_id}')
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Detail"

    def test_get_restaurant_not_found(self, restaurant_client):
        resp = restaurant_client.get('/restaurants/nonexistent')
        assert resp.status_code == 404

    def test_update_restaurant(self, restaurant_client):
        create_resp = restaurant_client.post('/restaurants', json={"name": "Old"})
        rest_id = create_resp.get_json()["id"]
        resp = restaurant_client.put(f'/restaurants/{rest_id}', json={"name": "New"})
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "New"

    def test_create_menu(self, restaurant_client):
        create_resp = restaurant_client.post('/restaurants', json={"name": "Menu Test"})
        rest_id = create_resp.get_json()["id"]
        resp = restaurant_client.post(f'/restaurants/{rest_id}/menus', json={"name": "Lunch"})
        assert resp.status_code == 201
        assert resp.get_json()["name"] == "Lunch"

    def test_list_menus(self, restaurant_client):
        create_resp = restaurant_client.post('/restaurants', json={"name": "Menus List"})
        rest_id = create_resp.get_json()["id"]
        restaurant_client.post(f'/restaurants/{rest_id}/menus', json={"name": "M1"})
        restaurant_client.post(f'/restaurants/{rest_id}/menus', json={"name": "M2"})
        resp = restaurant_client.get(f'/restaurants/{rest_id}/menus')
        assert resp.status_code == 200
        assert len(resp.get_json()["menus"]) == 2

    def test_get_menu(self, restaurant_client):
        create_resp = restaurant_client.post('/restaurants', json={"name": "Menu Get"})
        rest_id = create_resp.get_json()["id"]
        menu_resp = restaurant_client.post(f'/restaurants/{rest_id}/menus', json={"name": "Special"})
        menu_id = menu_resp.get_json()["id"]
        resp = restaurant_client.get(f'/restaurants/{rest_id}/menus/{menu_id}')
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Special"

    def test_update_menu(self, restaurant_client):
        create_resp = restaurant_client.post('/restaurants', json={"name": "Menu Upd"})
        rest_id = create_resp.get_json()["id"]
        menu_resp = restaurant_client.post(f'/restaurants/{rest_id}/menus', json={"name": "Old"})
        menu_id = menu_resp.get_json()["id"]
        resp = restaurant_client.put(f'/restaurants/{rest_id}/menus/{menu_id}', json={"name": "New"})
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "New"

    def test_delete_menu(self, restaurant_client):
        create_resp = restaurant_client.post('/restaurants', json={"name": "Menu Del"})
        rest_id = create_resp.get_json()["id"]
        menu_resp = restaurant_client.post(f'/restaurants/{rest_id}/menus', json={"name": "To Delete"})
        menu_id = menu_resp.get_json()["id"]
        resp = restaurant_client.delete(f'/restaurants/{rest_id}/menus/{menu_id}')
        assert resp.status_code == 204

    def test_create_menu_item(self, restaurant_client):
        create_resp = restaurant_client.post('/restaurants', json={"name": "Item"})
        rest_id = create_resp.get_json()["id"]
        menu_resp = restaurant_client.post(f'/restaurants/{rest_id}/menus', json={"name": "Menu"})
        menu_id = menu_resp.get_json()["id"]
        resp = restaurant_client.post(
            f'/restaurants/{rest_id}/menus/{menu_id}/items',
            json={"name": "Pizza", "price": 12.50}
        )
        assert resp.status_code == 201
        assert resp.get_json()["name"] == "Pizza"

    def test_validate_order(self, restaurant_client):
        create_resp = restaurant_client.post('/restaurants', json={"name": "Valid"})
        rest_id = create_resp.get_json()["id"]
        menu_resp = restaurant_client.post(f'/restaurants/{rest_id}/menus', json={"name": "Menu"})
        menu_id = menu_resp.get_json()["id"]
        item_resp = restaurant_client.post(
            f'/restaurants/{rest_id}/menus/{menu_id}/items',
            json={"name": "Dish", "price": 10.0}
        )
        item_id = item_resp.get_json()["id"]
        resp = restaurant_client.post(
            f'/restaurants/{rest_id}/validate',
            json={"items": [{"dishId": item_id, "quantity": 1}]}
        )
        assert resp.status_code == 200
        assert resp.get_json()["isValid"] is True

    def test_accept_order(self, restaurant_client):
        create_resp = restaurant_client.post('/restaurants', json={"name": "Accept"})
        rest_id = create_resp.get_json()["id"]
        resp = restaurant_client.post(
            f'/restaurants/{rest_id}/orders/order-123/accept',
            json={"estimatedPrepTime": 15}
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ACCEPTED"

    def test_reject_order(self, restaurant_client):
        create_resp = restaurant_client.post('/restaurants', json={"name": "Reject"})
        rest_id = create_resp.get_json()["id"]
        resp = restaurant_client.post(
            f'/restaurants/{rest_id}/orders/order-123/reject',
            json={"reason": "OUT_OF_STOCK"}
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "REJECTED"

    def test_update_order_status(self, restaurant_client):
        create_resp = restaurant_client.post('/restaurants', json={"name": "Status"})
        rest_id = create_resp.get_json()["id"]
        resp = restaurant_client.patch(
            f'/restaurants/{rest_id}/orders/order-123/status',
            json={"status": "PREPARING"}
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "PREPARING"

    def test_update_order_status_missing_status(self, restaurant_client):
        create_resp = restaurant_client.post('/restaurants', json={"name": "No Status"})
        rest_id = create_resp.get_json()["id"]
        resp = restaurant_client.patch(
            f'/restaurants/{rest_id}/orders/order-123/status',
            json={}
        )
        assert resp.status_code == 400


class TestMenuItemRoutes:
    def _menu_with_item(self, restaurant_client):
        rest_id = restaurant_client.post('/restaurants', json={"name": "Items"}).get_json()["id"]
        menu_id = restaurant_client.post(
            f'/restaurants/{rest_id}/menus', json={"name": "Menu"}
        ).get_json()["id"]
        item = restaurant_client.post(
            f'/restaurants/{rest_id}/menus/{menu_id}/items',
            json={
                "name": "Burger",
                "price": 9.0,
                "options": [{"name": "Cheese", "price": 1.0, "is_default": True}],
            },
        ).get_json()
        return rest_id, menu_id, item

    def test_get_menu_item(self, restaurant_client):
        rest_id, menu_id, item = self._menu_with_item(restaurant_client)
        resp = restaurant_client.get(f'/restaurants/{rest_id}/menus/{menu_id}/items/{item["id"]}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["name"] == "Burger"
        assert data["options"][0]["name"] == "Cheese"

    def test_get_menu_item_not_found(self, restaurant_client):
        rest_id, menu_id, _ = self._menu_with_item(restaurant_client)
        resp = restaurant_client.get(f'/restaurants/{rest_id}/menus/{menu_id}/items/unknown')
        assert resp.status_code == 404

    def test_update_menu_item(self, restaurant_client):
        rest_id, menu_id, item = self._menu_with_item(restaurant_client)
        resp = restaurant_client.put(
            f'/restaurants/{rest_id}/menus/{menu_id}/items/{item["id"]}',
            json={"name": "Double Burger", "price": 12.0},
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Double Burger"

    def test_delete_menu_item(self, restaurant_client):
        rest_id, menu_id, item = self._menu_with_item(restaurant_client)
        resp = restaurant_client.delete(f'/restaurants/{rest_id}/menus/{menu_id}/items/{item["id"]}')
        assert resp.status_code == 204
        resp = restaurant_client.get(f'/restaurants/{rest_id}/menus/{menu_id}/items/{item["id"]}')
        assert resp.status_code == 404


class TestErrorBranches:
    def test_update_restaurant_missing_body(self, restaurant_client):
        rest_id = restaurant_client.post('/restaurants', json={"name": "R"}).get_json()["id"]
        assert restaurant_client.put(f'/restaurants/{rest_id}', json={}).status_code == 400

    def test_create_menu_missing_body(self, restaurant_client):
        rest_id = restaurant_client.post('/restaurants', json={"name": "R"}).get_json()["id"]
        assert restaurant_client.post(f'/restaurants/{rest_id}/menus', json={}).status_code == 400

    def test_create_menu_item_missing_body(self, restaurant_client):
        rest_id = restaurant_client.post('/restaurants', json={"name": "R"}).get_json()["id"]
        menu_id = restaurant_client.post(
            f'/restaurants/{rest_id}/menus', json={"name": "M"}
        ).get_json()["id"]
        resp = restaurant_client.post(f'/restaurants/{rest_id}/menus/{menu_id}/items', json={})
        assert resp.status_code == 400

    def test_validate_order_missing_body(self, restaurant_client):
        rest_id = restaurant_client.post('/restaurants', json={"name": "R"}).get_json()["id"]
        assert restaurant_client.post(f'/restaurants/{rest_id}/validate', json={}).status_code == 400

    def test_validate_order_unknown_dish_is_invalid(self, restaurant_client):
        rest_id = restaurant_client.post('/restaurants', json={"name": "R"}).get_json()["id"]
        resp = restaurant_client.post(
            f'/restaurants/{rest_id}/validate',
            json={"items": [{"dishId": "unknown", "quantity": 1}]},
        )
        data = resp.get_json()
        assert data["isValid"] is False
        assert "reason" in data

    def test_validate_order_unknown_restaurant_returns_error_shape(self, restaurant_client):
        resp = restaurant_client.post(
            '/restaurants/nope/validate',
            json={"items": [{"dishId": "d1", "quantity": 1}]},
        )
        data = resp.get_json()
        assert data["isValid"] is False
        assert "code" in data

    def test_menu_routes_unknown_restaurant(self, restaurant_client):
        assert restaurant_client.get('/restaurants/nope/menus').status_code == 404
        assert restaurant_client.get('/restaurants/nope/menus/m1').status_code == 404
        assert restaurant_client.put('/restaurants/nope/menus/m1', json={"name": "X"}).status_code == 404
        assert restaurant_client.delete('/restaurants/nope/menus/m1').status_code == 404

    def test_accept_and_reject_unknown_restaurant(self, restaurant_client):
        assert restaurant_client.post('/restaurants/nope/orders/o1/accept', json={}).status_code == 404
        assert restaurant_client.post('/restaurants/nope/orders/o1/reject', json={}).status_code == 404


class TestSerializers:
    def test_restaurant_with_address_hours_and_coordinates(self, restaurant_client):
        resp = restaurant_client.post('/restaurants', json={
            "name": "Complet",
            "address": {
                "street": "1 rue de la Paix",
                "city": "Paris",
                "postal_code": "75002",
                "coordinates": {"latitude": 48.87, "longitude": 2.33},
            },
            "opening_hours": [
                {"day": "monday", "open_time": "09:00", "close_time": "22:00"},
            ],
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["address"]["city"] == "Paris"
        assert data["address"]["coordinates"]["latitude"] == 48.87
        assert data["opening_hours"][0]["day"] == "monday"
