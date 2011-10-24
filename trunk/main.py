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

HOST = os.environ['HTTP_HOST']
CDN1_HOST = "cdn1.%s" % os.environ['HTTP_HOST']
CDN2_HOST = "cdn2.%s" % os.environ['HTTP_HOST']
IS_GOOGLE = os.environ.get('SERVER_SOFTWARE','').lower().startswith('google')
IS_DEVELOPMENT = not IS_GOOGLE

def get_model(id):
	logging.error(id)
	return {'id': id, 'name': 'nn'+id }
global_map = {
	'get_model': get_model,
	'canonical_netloc': 'localhost:8080',
	'css_netloc': HOST if IS_DEVELOPMENT else CDN1_HOST,
	'img_netloc': HOST if IS_DEVELOPMENT else CDN2_HOST,
}

templates_path = 'templates'
app = versapp.initialize(template_path=templates_path, debug=True, globals=global_map)

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
		route = versapp.new_route(versapp.TemplateHandler, template, template_format=template_format, name=name, in_sitemap=True)
		routes.append(route)
	return routes
#
class SitemapHandler(versapp.TemplateHandler):
	def build_mapping(self):
		entries = []
		for r in routes:
			if r.in_sitemap:
				for args, kwargs in r.get_sitemap_args():
					kwargs['_full'] = True
					loc = r.build(self.request, args, kwargs) 
					entries.append((loc, 'aaa'))
		m_a = self.mapping_args
		m_a['entries'] = entries
		return m_a
		
models = [([], {'id': '00001'}), ([], {'id': '00002'})]
def albums():
	return [([], {'id': 'mickey-mouse'}), ([], {'id': 'disney'})]
routes = [
	versapp.new_route(versapp.StaticHandler, '/favicon.ico', name="favicon.ico", template_file='static/external/favicon.ico'),
	versapp.new_route(versapp.TemplateHandler, '/css/rtf-<Revision:\d\d\d\d\d>.css', name='rtf.css', template_file='base/css/rtf.css', versioned_arg="Revision"),

	versapp.new_route(versapp.TemplateHandler, '/modelos/<id:\d\d\d\d\d>', name='modelo', template_format='%(Language)s/html/modelo_.html', in_sitemap=True, sitemap_args=models),
	versapp.new_route(versapp.TemplateHandler, '/albums/<id>', name='album', template_format='%(Language)s/html/album_.html', in_sitemap=True, sitemap_args=albums),

	versapp.new_route(SitemapHandler, '/sitemap.xml', name='sitemap', template_file='sitemap.xml'),
	versapp.new_route(versapp.StaticHandler, '/images/<image>', name="images", template_file="kk", build_only='true'),
]

routes.extend(build_html_template_routes())
for r in routes:
	app.router.add(r)



def main():
	app.run()

if __name__ == '__main__':
	main()
