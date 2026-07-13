import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class RouteRule:
    path_pattern: str
    method: str
    service_url: str
    timeout: float = 10.0

    def _to_regex(self) -> re.Pattern:
        pattern = re.sub(r'<(\w+)>', r'(?P<\1>[^/]+)', self.path_pattern)
        pattern = pattern.replace('*', '.*')
        return re.compile(f'^{pattern}$')

    def match(self, method: str, path: str) -> Optional[dict]:
        if method != self.method:
            return None
        regex = self._to_regex()
        match = regex.match(path)
        if match:
            return match.groupdict()
        return None


@dataclass
class RouteMatch:
    rule: RouteRule
    path_params: dict
    remaining_path: str = ''
