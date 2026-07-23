import os

import pytest
import yaml
from flask import Flask, jsonify

from openapi_validator import (
    OpenApiRequestValidator,
    load_spec,
    register_openapi_validation,
    resolve_refs,
)

ENDPOINTS_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'ressources', 'endpoints'
)

SPEC = {
    'openapi': '3.0.3',
    'info': {'title': 'Test Service API', 'version': '1.0.0'},
    'paths': {
        '/things': {
            'post': {
                'requestBody': {
                    'required': True,
                    'content': {
                        'application/json': {
                            'schema': {'$ref': '#/components/schemas/ThingInput'}
                        }
                    },
                },
                'responses': {'201': {'description': 'Created'}},
            },
            'get': {
                'parameters': [
                    {'name': 'q', 'in': 'query', 'required': True, 'schema': {'type': 'string'}}
                ],
                'responses': {'200': {'description': 'OK'}},
            },
        },
        '/things/{thing_id}': {
            'get': {'responses': {'200': {'description': 'OK'}}},
        },
    },
    'components': {
        'schemas': {
            'ThingInput': {
                'type': 'object',
                'required': ['name', 'size'],
                'properties': {
                    'name': {'type': 'string'},
                    'size': {'type': 'integer', 'minimum': 1, 'maximum': 5},
                    'note': {'type': 'string', 'nullable': True},
                },
            }
        }
    },
}


@pytest.fixture
def spec_path(tmp_path):
    path = tmp_path / 'test-service.openapi.yaml'
    path.write_text(yaml.safe_dump(SPEC), encoding='utf-8')
    return str(path)


def _build_app(spec_path, strict=False):
    app = Flask(__name__)
    app.config['TESTING'] = True
    register_openapi_validation(app, 'test-service', spec_path=spec_path, strict=strict)

    @app.route('/things', methods=['POST'])
    def create_thing():
        return jsonify({"created": True}), 201

    @app.route('/things', methods=['GET'])
    def list_things():
        return jsonify({"things": []})

    @app.route('/things/<thing_id>', methods=['GET'])
    def get_thing(thing_id):
        return jsonify({"id": thing_id})

    @app.route('/extra', methods=['POST'])
    def extra():
        return jsonify({"extra": True})

    return app


@pytest.fixture
def client(spec_path):
    return _build_app(spec_path).test_client()


class TestResolveRefs:
    def test_inlines_local_refs(self):
        resolved = resolve_refs(SPEC, SPEC)
        schema = resolved['paths']['/things']['post']['requestBody']['content']['application/json']['schema']
        assert schema['required'] == ['name', 'size']
        assert schema['properties']['size']['maximum'] == 5

    def test_converts_nullable_to_jsonschema_type(self):
        resolved = resolve_refs(SPEC, SPEC)
        note = resolved['components']['schemas']['ThingInput']['properties']['note']
        assert note['type'] == ['string', 'null']

    def test_keeps_nullable_when_conversion_disabled(self):
        resolved = resolve_refs(SPEC, SPEC, convert_nullable=False)
        note = resolved['components']['schemas']['ThingInput']['properties']['note']
        assert note == {'type': 'string', 'nullable': True}

    def test_detects_circular_refs(self):
        spec = {
            'components': {'schemas': {'A': {'$ref': '#/components/schemas/A'}}}
        }
        with pytest.raises(ValueError):
            resolve_refs(spec, spec)


class TestRequestValidation:
    def test_valid_body_passes(self, client):
        response = client.post('/things', json={"name": "box", "size": 3})
        assert response.status_code == 201

    def test_out_of_range_value_rejected(self, client):
        response = client.post('/things', json={"name": "box", "size": 99})
        assert response.status_code == 400
        assert response.get_json()['error']['code'] == 'SCHEMA_VALIDATION_FAILED'

    def test_wrong_type_rejected(self, client):
        response = client.post('/things', json={"name": 42, "size": 3})
        assert response.status_code == 400
        assert response.get_json()['error']['code'] == 'SCHEMA_VALIDATION_FAILED'

    def test_missing_required_field_rejected(self, client):
        response = client.post('/things', json={"name": "box"})
        assert response.status_code == 400
        assert response.get_json()['error']['code'] == 'SCHEMA_VALIDATION_FAILED'

    def test_missing_required_body_rejected(self, client):
        response = client.post('/things')
        assert response.status_code == 400
        assert response.get_json()['error']['code'] == 'INVALID_INPUT'

    def test_nullable_field_accepts_null(self, client):
        response = client.post('/things', json={"name": "box", "size": 3, "note": None})
        assert response.status_code == 201

    def test_missing_required_query_param_rejected(self, client):
        response = client.get('/things')
        assert response.status_code == 400
        assert response.get_json()['error']['code'] == 'MISSING_PARAMETER'

    def test_present_query_param_passes(self, client):
        response = client.get('/things?q=box')
        assert response.status_code == 200

    def test_path_parameter_route_matches(self, client):
        response = client.get('/things/42')
        assert response.status_code == 200

    def test_unmatched_route_passes_through(self, client):
        response = client.post('/extra', json={"anything": True})
        assert response.status_code == 200

    def test_strict_mode_rejects_unmatched_route(self, spec_path):
        client = _build_app(spec_path, strict=True).test_client()
        response = client.post('/extra', json={"anything": True})
        assert response.status_code == 404
        assert response.get_json()['error']['code'] == 'ROUTE_NOT_IN_CONTRACT'

    def test_serves_contract_on_openapi_yaml(self, client):
        response = client.get('/openapi.yaml')
        assert response.status_code == 200
        served = yaml.safe_load(response.data)
        assert served['info']['title'] == 'Test Service API'

    def test_missing_spec_file_disables_validation(self):
        app = Flask(__name__)
        app.config['TESTING'] = True
        result = register_openapi_validation(app, 'ghost-service', spec_path='/nonexistent/ghost.yaml')
        assert result is None

        @app.route('/anything', methods=['POST'])
        def anything():
            return jsonify({"ok": True})

        response = app.test_client().post('/anything', json={})
        assert response.status_code == 200


class TestRealContracts:
    def test_all_contracts_parse_and_resolve(self):
        files = sorted(
            f for f in os.listdir(ENDPOINTS_DIR) if f.endswith('.openapi.yaml')
        )
        assert len(files) == 10
        for filename in files:
            spec = load_spec(os.path.join(ENDPOINTS_DIR, filename))
            assert spec['openapi'] == '3.0.3', filename
            assert 'info' in spec and 'paths' in spec, filename
            resolved = resolve_refs(spec, spec)
            OpenApiRequestValidator(resolved)

    def test_rating_contract_validates_requests(self):
        app = Flask(__name__)
        app.config['TESTING'] = True
        register_openapi_validation(
            app,
            'rating-service',
            spec_path=os.path.join(ENDPOINTS_DIR, 'rating-service.openapi.yaml'),
        )

        @app.route('/ratings', methods=['POST'])
        def create_rating():
            return jsonify({"created": True}), 201

        client = app.test_client()
        valid = client.post('/ratings', json={"target_id": "rest-1", "score": 5})
        assert valid.status_code == 201
        invalid = client.post('/ratings', json={"target_id": "rest-1", "score": 0})
        assert invalid.status_code == 400
        assert invalid.get_json()['error']['code'] == 'SCHEMA_VALIDATION_FAILED'
        missing = client.post('/ratings', json={"score": 4})
        assert missing.status_code == 400
