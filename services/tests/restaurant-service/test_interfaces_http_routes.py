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
