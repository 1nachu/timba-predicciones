"""
Flask-Caching Instance
======================
Instancia compartida de Flask-Caching desacoplada de la app para evitar importaciones circulares.
"""

from flask_caching import Cache

cache = Cache()
