from .api_routes import register_api_routes


def register_routes(bp):
    register_api_routes(bp)
