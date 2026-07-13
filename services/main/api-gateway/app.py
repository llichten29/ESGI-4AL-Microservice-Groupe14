import os

from flask import Flask, jsonify, send_from_directory, Response
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SWAGGER_UI = """<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>FoodDelivery API - Documentation</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css"/>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.onload = () => SwaggerUIBundle({
      url: '/openapi.yaml',
      dom_id: '#swagger-ui'
    });
  </script>
</body>
</html>"""


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    CORS(app)

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "healthy", "service": "api-gateway"})

    @app.route('/openapi.yaml', methods=['GET'])
    def openapi_spec():
        return send_from_directory(BASE_DIR, 'openapi.yaml', mimetype='application/yaml')

    @app.route('/docs', methods=['GET'])
    def docs():
        return Response(SWAGGER_UI, mimetype='text/html')

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "Internal server error"}), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=app.config.get('SERVICE_PORT', 8000), debug=app.config.get('DEBUG', False))
