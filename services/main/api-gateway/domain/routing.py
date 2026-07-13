from domain.models import RouteRule, RouteMatch


class RoutingTable:
    def __init__(self):
        self._rules: list[RouteRule] = []

    def add_rule(self, rule: RouteRule):
        self._rules.append(rule)

    def match(self, method: str, path: str) -> RouteMatch | None:
        for rule in self._rules:
            params = rule.match(method, path)
            if params is not None:
                return RouteMatch(rule=rule, path_params=params)
        return None
