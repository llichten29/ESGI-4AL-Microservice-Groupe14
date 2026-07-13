from domain.models import RouteRule, RouteMatch
from domain.routing import RoutingTable


class TestRouteRule:
    def test_match_exact_path(self):
        rule = RouteRule('/orders', 'POST', 'http://order-service:8001')
        params = rule.match('POST', '/orders')
        assert params == {}

    def test_match_with_params(self):
        rule = RouteRule('/orders/<order_id>', 'GET', 'http://order-service:8001')
        params = rule.match('GET', '/orders/abc-123')
        assert params == {'order_id': 'abc-123'}

    def test_match_multiple_params(self):
        rule = RouteRule('/restaurants/<rid>/orders/<oid>/accept', 'POST', 'http://restaurant-service:8002')
        params = rule.match('POST', '/restaurants/r1/orders/o1/accept')
        assert params == {'rid': 'r1', 'oid': 'o1'}

    def test_no_match_wrong_method(self):
        rule = RouteRule('/orders', 'POST', 'http://order-service:8001')
        assert rule.match('GET', '/orders') is None

    def test_no_match_wrong_path(self):
        rule = RouteRule('/orders', 'POST', 'http://order-service:8001')
        assert rule.match('POST', '/payments') is None

    def test_match_wildcard_path(self):
        rule = RouteRule('/restaurants/*', 'GET', 'http://restaurant-service:8002')
        params = rule.match('GET', '/restaurants/anything/here')
        assert params == {}


class TestRoutingTable:
    def test_match_returns_correct_rule(self):
        rt = RoutingTable()
        rt.add_rule(RouteRule('/orders', 'POST', 'http://order-service:8001'))
        rt.add_rule(RouteRule('/orders/<id>', 'GET', 'http://order-service:8001'))

        match = rt.match('GET', '/orders/123')
        assert match is not None
        assert match.rule.service_url == 'http://order-service:8001'
        assert match.path_params == {'id': '123'}

    def test_no_match_returns_none(self):
        rt = RoutingTable()
        rt.add_rule(RouteRule('/orders', 'POST', 'http://order-service:8001'))

        assert rt.match('GET', '/unknown') is None

    def test_empty_table_returns_none(self):
        rt = RoutingTable()
        assert rt.match('GET', '/anything') is None

    def test_first_match_wins_order(self):
        rt = RoutingTable()
        rt.add_rule(RouteRule('/orders/<id>', 'GET', 'http://order-service:8001', 10))
        rt.add_rule(RouteRule('/orders/123', 'GET', 'http://special:9000', 5))

        match = rt.match('GET', '/orders/123')
        assert match is not None
        assert match.rule.service_url == 'http://order-service:8001'
