from flask import request, jsonify

from app.api import api_bp
from app.services import product_service


@api_bp.route('/products')
def list_products():
    return jsonify(product_service.get_products())


@api_bp.route('/products/<int:product_id>')
def get_product(product_id):
    product = product_service.get_product(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    return jsonify(product)


@api_bp.route('/products/<int:product_id>/fire-ratings')
def get_product_fire_ratings(product_id):
    return jsonify(product_service.get_product_fire_ratings(product_id))


@api_bp.route('/products/<int:product_id>/failure-temps')
def get_product_failure_temps(product_id):
    fire_rating_id = request.args.get('fire_rating_id', type=int)
    if fire_rating_id is None:
        return jsonify({'error': 'Query parameter fire_rating_id is required'}), 400
    return jsonify(product_service.get_product_failure_temps(product_id, fire_rating_id))


@api_bp.route('/origins')
def list_origins():
    return jsonify(product_service.get_origins())
