#!/usr/bin/env python
# -*- coding: utf-8 -*-
# $Id$
#
import os
import logging
import re
import webapp2
import jinja2
import versapp
from versapp.utils import walk_tree
from google.appengine.api import app_identity

IS_GOOGLE = os.environ.get('SERVER_SOFTWARE','').lower().startswith('google')
IS_DEVELOPMENT = not IS_GOOGLE

HOST = os.environ['HTTP_HOST']
WWW_HOST = "www.%s" % app_identity.get_default_version_hostname() if IS_GOOGLE else None
CDN1_HOST = "cdn1.%s" % app_identity.get_default_version_hostname() if IS_GOOGLE else None
CDN2_HOST = "cdn2.%s" % app_identity.get_default_version_hostname() if IS_GOOGLE else None
PAGES_CC = versapp.CC_PUBLIC(max_age=versapp.day) if IS_GOOGLE else versapp.CC_NO_CACHE
DEFAULT_CC = versapp.CC_PUBLIC(max_age=versapp.year) if IS_GOOGLE else versapp.CC_NO_CACHE

def get_model(id):
	logging.error(id)
	return {'id': id, 'name': 'nn'+id }
global_map = {
	'get_model': get_model,
	'css_netloc': CDN1_HOST or HOST,
	'img_netloc': CDN2_HOST or HOST,
}
app_config = {
	'_canonical_netloc': WWW_HOST or HOST,
	'default_cache_control': DEFAULT_CC,
}
templates_path = 'templates'
static_path = 'static'
app = versapp.initialize(template_path=templates_path, debug=True, globals=global_map, config=app_config)

def build_html_template_routes():
	routes = []
	# we walk default language files
	sources_path = os.path.join(templates_path, os.path.join(versapp.DEFAULT_LANGUAGE, 'html'))
	base_paths = walk_tree(sources_path)
	for path in base_paths:
		if not path.endswith('.html'):
			continue
		template = "/" + path[:-5] # we remove the html extension here
		name = path[:-5]
		if name.endswith('_'):
			# this is a convention to skip templates
			continue
		if template.endswith("index"):
			template = template[:-5]
		template_format = "%(Language)s/html/" + path
		route = versapp.new_route(versapp.TemplateHandler, template, template_format=template_format, name=name, in_sitemap=True, cache_control=PAGES_CC)
		routes.append(route)
	return routes
#
def build_webmaster_routes():
	routes = []
	sources_path = os.path.join(static_path, 'webmaster')
	base_paths = walk_tree(sources_path)
	for path in base_paths:
		template = "/" + path
		template_file = os.path.join(sources_path, path)
		route = versapp.new_route(versapp.StaticHandler, template, template_file=template_file, name=path)
		routes.append(route)
	return routes
#
models = [(['aaaa'], {'id': '00001'}, 1), ([], {'id': '00002'},1)]
def albums():
	return [([], {'id': 'mickey-mouse'},3), ([], {'id': 'disney'},2)]
routes = [
	versapp.new_route(versapp.StaticHandler, '/favicon.ico', name="favicon.ico", template_file='static/external/favicon.ico'),
	versapp.new_route(versapp.TemplateHandler, '/css/rtf-<Revision:\d\d\d\d\d>.css', name='rtf.css', template_file='base/css/rtf.css', versioned_arg="Revision"),

	versapp.new_route(versapp.TemplateHandler, '/modelos/<id:\d\d\d\d\d>', name='modelo', template_format='%(Language)s/html/modelo_.html', in_sitemap=True, sitemap_args=models, cache_control=PAGES_CC),
	versapp.new_route(versapp.TemplateHandler, '/albums/<id>', name='album', template_format='%(Language)s/html/album_.html', in_sitemap=True, sitemap_args=albums, cache_control=PAGES_CC),

	versapp.new_route(versapp.TemplateHandler, '/sitemap.xml', name='sitemap', template_file='sitemap.xml', cache_control=versapp.CC_NO_CACHE),
	versapp.new_route(versapp.StaticHandler, '/images/<image>', name="images", template_file="kk", build_only='true'),
]

routes.extend(build_html_template_routes())
routes.extend(build_webmaster_routes())
for r in routes:
	app.router.add(r)



def main():
	app.run()

if __name__ == '__main__':
	main()
