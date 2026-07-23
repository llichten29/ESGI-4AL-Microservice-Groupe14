import logging
import os
import re

import yaml
from flask import jsonify, request, send_file
from jsonschema import Draft4Validator
from jsonschema.exceptions import best_match

logger = logging.getLogger(__name__)

_HTTP_METHODS = ('get', 'post', 'put', 'patch', 'delete')


def load_spec(spec_path: str) -> dict:
    with open(spec_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def _lookup_ref(ref: str, spec: dict):
    if not ref.startswith('#/'):
        raise ValueError(f"Unsupported $ref target: {ref}")
    node = spec
    for part in ref[2:].split('/'):
        node = node[part]
    return node


def resolve_refs(node, spec: dict, seen: frozenset = frozenset(), convert_nullable: bool = True):
    """Return a copy of node with every local $ref inlined and, by default, nullable translated for jsonschema."""
    if isinstance(node, dict):
        ref = node.get('$ref')
        if isinstance(ref, str):
            if ref in seen:
                raise ValueError(f"Circular $ref detected: {ref}")
            return resolve_refs(_lookup_ref(ref, spec), spec, seen | {ref}, convert_nullable)
        resolved = {
            key: resolve_refs(value, spec, seen, convert_nullable)
            for key, value in node.items()
        }
        if convert_nullable and resolved.pop('nullable', False) is True \
                and isinstance(resolved.get('type'), str):
            resolved['type'] = [resolved['type'], 'null']
        return resolved
    if isinstance(node, list):
        return [resolve_refs(item, spec, seen, convert_nullable) for item in node]
    return node


class OpenApiRequestValidator:
    def __init__(self, spec: dict, strict: bool = False):
        self.strict = strict
        self._operations = self._build_index(spec)

    @staticmethod
    def _build_index(spec: dict) -> list:
        operations = []
        paths = sorted(spec.get('paths', {}).items(), key=lambda item: item[0].count('{'))
        for path, path_item in paths:
            pattern = re.compile('^' + re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', path) + '$')
            for method in _HTTP_METHODS:
                operation = path_item.get(method)
                if not isinstance(operation, dict):
                    continue
                request_body = operation.get('requestBody') or {}
                schema = (
                    request_body.get('content', {})
                    .get('application/json', {})
                    .get('schema')
                )
                body_validator = Draft4Validator(schema) if schema else None
                body_required = bool(request_body.get('required'))
                required_params = [
                    parameter['name']
                    for parameter in operation.get('parameters', [])
                    if parameter.get('in') == 'query' and parameter.get('required')
                ]
                operations.append(
                    (method.upper(), pattern, body_validator, body_required, required_params)
                )
        return operations

    def _find_operation(self, method: str, path: str):
        for op_method, pattern, body_validator, body_required, required_params in self._operations:
            if op_method == method and pattern.match(path):
                return body_validator, body_required, required_params
        return None

    def validate(self, method: str, path: str, body, args):
        operation = self._find_operation(method, path)
        if operation is None:
            if self.strict:
                return (
                    {"error": {"code": "ROUTE_NOT_IN_CONTRACT",
                               "message": f"{method} {path} is not defined in the OpenAPI contract"}},
                    404,
                )
            return None
        body_validator, body_required, required_params = operation
        for name in required_params:
            if name not in args:
                return (
                    {"error": {"code": "MISSING_PARAMETER",
                               "message": f"Missing required query parameter '{name}'"}},
                    400,
                )
        if body_required and body is None:
            return (
                {"error": {"code": "INVALID_INPUT", "message": "Request body required"}},
                400,
            )
        if body is not None and body_validator is not None:
            error = best_match(body_validator.iter_errors(body))
            if error is not None:
                location = '.'.join(str(part) for part in error.absolute_path) or 'body'
                return (
                    {"error": {"code": "SCHEMA_VALIDATION_FAILED",
                               "message": f"{location}: {error.message}"}},
                    400,
                )
        return None


def register_openapi_validation(app, service_name: str, spec_path: str = None, strict: bool = False):
    path = spec_path or os.environ.get('OPENAPI_SPEC_PATH') or os.path.join(
        app.root_path, '..', '..', 'ressources', 'endpoints', f'{service_name}.openapi.yaml'
    )
    path = os.path.abspath(path)
    if not os.path.exists(path):
        logger.warning("OpenAPI contract not found at %s, request validation disabled", path)
        return None

    raw_spec = load_spec(path)
    spec = resolve_refs(raw_spec, raw_spec)
    validator = OpenApiRequestValidator(spec, strict=strict)
    logger.info("OpenAPI request validation enabled for %s from %s", service_name, path)

    @app.before_request
    def validate_against_contract():
        if request.method in ('OPTIONS', 'HEAD'):
            return None
        result = validator.validate(
            request.method,
            request.path,
            request.get_json(silent=True),
            request.args,
        )
        if result is not None:
            payload, status = result
            return jsonify(payload), status
        return None

    if 'openapi_spec' not in app.view_functions:
        @app.route('/openapi.yaml', methods=['GET'], endpoint='openapi_spec')
        def openapi_spec():
            return send_file(path, mimetype='application/yaml')

    return validator
