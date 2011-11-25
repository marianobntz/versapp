#!/usr/bin/python
# -*- coding: utf-8 -*-
# $Id$
#
import os
import logging
import re
import webapp2
import jinja2
import versapp
from versapp.utils import walk_tree, tree_paths

IS_GOOGLE = os.environ.get('SERVER_SOFTWARE','').lower().startswith('google')
IS_DEVELOPMENT = not IS_GOOGLE

WWW_HOST = "www.versapp.net"
CDN1_HOST = "cdn1.versapp.net"
CDN2_HOST = "cdn2.versapp.net"
PAGES_CC = versapp.CC_PUBLIC(max_age=versapp.day) if IS_GOOGLE else versapp.config.CC_NO_CACHE
DEFAULT_CC = versapp.CC_PUBLIC(max_age=versapp.year) if IS_GOOGLE else versapp.config.CC_NO_CACHE
TEMPLATES_PATH = versapp.config.DEFAULT_TEMPLATES_PATH

def get_model(id):
	# logging.error(id)
	return {'id': id, 'name': 'nn'+id }
global_map = {
	'get_model': get_model,
}
app_config = {
	'default_cache_control': DEFAULT_CC,
}
static_path = 'static'

app = versapp.initialize(template_path=TEMPLATES_PATH, debug=IS_DEVELOPMENT, template_globals=global_map, config=app_config, 
						 canonical_netloc=WWW_HOST, cdn_netlocs=[CDN1_HOST,CDN2_HOST])

def add_html_template_routes(routes):
	# we walk default language files
	sources_path = os.path.join(TEMPLATES_PATH, os.path.join(versapp.config.DEFAULT_LANGUAGE, 'html'))
	for path in tree_paths(sources_path):
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
		route = versapp.TemplateHandler.new_route( template, template_format=template_format, name=name, sitemap=True, cache_control=PAGES_CC)
		routes.append(route)
#
def add_webmaster_routes(routes):
	sources_path = os.path.join(static_path, 'webmaster')
	for path in tree_paths(sources_path):
		template = "/" + path
		template_file = os.path.join(sources_path, path)
		route = versapp.new_route(versapp.StaticHandler, template, template_file=template_file, name=path)
		routes.append(route)
#
models = []
for a in range(0, 10):
	models.append((['aaaa'], {'id': '%05d' % a}))
def albums():
	result = []
	for a in range(0, 2):
		result.append((['bbb'], {'id': 'esooo %04d' % a}))
	return result


routes = [
	versapp.new_route(versapp.StaticHandler, '/favicon.ico', name="favicon.ico", template_file='static/external/favicon.ico'),
	versapp.TemplateHandler.new_route('/css/rtf-<Revision:\d\d\d\d\d>.css', name='rtf.css', template_file='base/css/rtf.css', versioned_arg="Revision", _netloc=CDN1_HOST, _full=True),

	versapp.new_route(versapp.TemplateHandler, '/modelos/<id:\d\d\d\d\d>', name='modelo', template_format='%(Language)s/html/modelo_.html', sitemap=True, sitemap_args=models, cache_control=PAGES_CC),
	versapp.new_route(versapp.TemplateHandler, '/albums/<id>', name='album', template_format='%(Language)s/html/album_.html', sitemap=True, sitemap_args=albums, cache_control=PAGES_CC),

	versapp.build_route('/images/<image>', name="images", _netloc=CDN2_HOST),
	versapp.build_route('/css/jquery.css', name="jquery.css", _netloc="aaasss"),
	# faltan los robots.txt
]

add_html_template_routes(routes)
add_webmaster_routes(routes)
for r in routes:
	app.router.add(r)



# def main():
# 	app.run()

# if __name__ == '__main__':
# 	main()
