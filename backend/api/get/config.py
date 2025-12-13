"""GET /api/data/config endpoint handler."""

import json

from config import DATA_DIR, DOMAIN, PORT


def handle_api_data_config(handler):
    """GET /api/data/config - Get server configuration."""
    config_file_path = DATA_DIR / 'config.json'
    config_json = {}
    if config_file_path.is_file():
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config_json = json.load(f)
        except Exception as e:
            pass
    config_json['DOMAIN'] = DOMAIN
    config_json['PORT'] = PORT
    handler._send_response(200, data=config_json)
