"""
SEO Blueprint
=============
Rutas estáticas en la raíz para robots.txt y sitemap.xml.
"""

import os
from flask import Blueprint, send_from_directory, current_app
from utils.shared import PROJECT_ROOT

seo_bp = Blueprint('seo', __name__)


@seo_bp.route('/robots.txt', endpoint='robots')
def robots():
    """Servir robots.txt desde static/."""
    static_dir = os.path.join(PROJECT_ROOT, 'static')
    return send_from_directory(static_dir, 'robots.txt')


@seo_bp.route('/sitemap.xml', endpoint='sitemap')
def sitemap():
    """Servir sitemap.xml desde static/."""
    static_dir = os.path.join(PROJECT_ROOT, 'static')
    return send_from_directory(static_dir, 'sitemap.xml')
