import sys
import os

import pytest


_notification_base = os.path.join(os.path.dirname(__file__), '..', '..', 'main', 'notification-service')
_other_bases = [
    p for p in sys.path
    if ('-service' in p or 'api-gateway' in p) and 'notification-service' not in p
]
for p in _other_bases:
    sys.path.remove(p)

_conflicting_modules = ['domain', 'application', 'infrastructure', 'interfaces', 'app', 'config']
for mod in list(sys.modules.keys()):
    parts = mod.split('.')
    if parts[0] in _conflicting_modules:
        sys.modules.pop(mod, None)

sys.path.insert(0, _notification_base)


@pytest.fixture
def notification_repo():
    from infrastructure.repositories import InMemoryNotificationRepository
    return InMemoryNotificationRepository()


@pytest.fixture
def notification_service(notification_repo):
    from application.notification_service import NotificationService
    return NotificationService(repository=notification_repo)


@pytest.fixture
def notification_app(notification_service):
    from flask import Flask
    from interfaces.http.routes import routes as notification_routes
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.notification_service = notification_service
    app.register_blueprint(notification_routes)
    return app


@pytest.fixture
def notification_client(notification_app):
    return notification_app.test_client()
