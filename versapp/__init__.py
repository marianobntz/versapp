#!/usr/bin/python
# -*- coding: utf-8 -*-
# $Id$
#
"""
    versapp
    =======

    Very simple but complete web application framework

    :copyright: 2011 by mariano@benitez.nu
    :license: Apache Sotware License, see LICENSE for details.
"""
import os
import logging
import datetime
import re

import webob
import webapp2
from webapp2_extras import jinja2 as webapp2_jinja2

from utils import *
from routes import *
from handlers import *

DEFAULT_LANGUAGE = APP_LANGUAGE_DEFAULT
DEFAULT_SITEMAP_GROUP = "default"
DEFAULT_TEMPLATES_PATH = 'templates'
CC_NO_CACHE = "no-cache"
CC_PUBLIC = lambda max_age: "public, max-age=%s" % max_age
CC_PRIVATE = lambda max_age: "private, max-age=%s" % max_age
day = 24*60*60
year = 365*day

class WSGIApplication(webapp2.WSGIApplication):
	def __init__(self, **kwargs):
		super(WSGIApplication, self).__init__(**kwargs)
		self.router.set_dispatcher(self.__class__.custom_dispatcher)

	@staticmethod
	def custom_dispatcher(router, request, response):
		request.environ['REQUEST_LANGUAGE'] = request_language(request)
		rv = router.default_dispatcher(request, response)
		if isinstance(rv, basestring):
			rv = webapp2.Response(rv)
		elif isinstance(rv, tuple):
			rv = webapp2.Response(*rv)

		return rv
#
def initialize(**kwargs):
	"""Creates a new WSGIApplication with the proper configuration
	
	Args:
		template_path: base directory for jinja2 templates. default 'templates'.
		
		template_globals: dict for global variables available for jinja2 templates.
		
		cdn_netlocs: dict for network locations of each CDN host
		
		canonical_netloc: network location for the canonical URI. Mandatory
		
	:param canonical_scheme:
		URI scheme for canonical URIs.
	:param sitemap:
		include the handlers required to render a sitemap and rebuild them. default True
	:param default_language:
		define the default language for the application. used for canonical rendering.
	:returns:
		a new :class:`WSGIApplication` instance.
	"""
	#
	# Hint: do not replace jinja2 default_config, update it
	template_path = kwargs.pop('template_path', DEFAULT_TEMPLATES_PATH)
	webapp2_jinja2.default_config['template_path'] = template_path # TODO (mariano@versalitas.com.ar) verify template_path exists
	
	template_globals = kwargs.pop('template_globals', {})
	template_globals['uri_for'] = webapp2.uri_for
	webapp2_jinja2.default_config['globals'] = template_globals
	
	webapp2_jinja2.default_config['environment_args']['trim_blocks'] = True

	app_config = kwargs.setdefault('config', {})
	app_config['canonical_netloc'] = kwargs.pop('canonical_netloc')
	app_config['canonical_scheme'] = kwargs.pop('canonical_scheme', None)
	app_config['canonical_language'] = kwargs.pop('canonical_language', DEFAULT_LANGUAGE)
	app_config[CDN_NETLOCS] = kwargs.pop(CDN_NETLOCS, {})
	
	sitemap = kwargs.pop('sitemap', True)
	if sitemap:
		routes = kwargs.setdefault('routes', [])
		routes.append(SitemapHandler.render_route())
		routes.append(SitemapHandler.rebuild_route())
	return WSGIApplication(**kwargs)
#

#
#
class SitemapEntry(object):
	def __init__(self, loc, lastmod=None, image_loc=None, priority=None, changefreq=None):
		self.loc = loc
		self.priority = priority
		self.lastmod = lastmod
		self.image_loc = image_loc
		self.changefreq = changefreq
#
class SitemapEntries(db.Model):
	group = db.StringProperty()
	loc = db.StringProperty()
	etag = db.StringProperty()
	lastmod = db.DateProperty(auto_now=True)
	priority = db.StringProperty()
	changefreq = db.StringProperty()
	image_loc = db.StringProperty()
	#
	@classmethod
	def get_entries(cls, group):
		# ToDo (mariano): implement caching
		result = []
		for r in db.Query(cls).filter("group =", group):
			result.append(r)
		return result
	@classmethod
	def update(cls, group, loc, etag, priority=None, changefreq=None, image_loc=None):
		SitemapEntries(key_name=loc, group=group, loc=loc, etag=etag, priority=priority, changefreq=changefreq, image_loc=image_loc).put()
#
class SitemapHandler(RequestHandler):
	"""We support multiple sitemaps in the application by using the sitemap attribute when defining the routes using this handler.
	"""
	def initialize(self, request, response):
		super(SitemapHandler, self).initialize(request, response)
		self.sitemap_group = self.get_default( 'sitemap_group')
	#
	@classmethod
	def render_route(cls, template='/sitemap.xml', name='sitemap', template_file='base/sitemap.xml', **kw):
		"""
		:param template:
		:param name:
		:param template_file:
		:param sitemap_group:
			default 'default'
		:returns:
			a new :class:`Route` for the sitemap handler
		"""
		kw['cache_control'] = CC_NO_CACHE
		kw.setdefault('sitemap_group', DEFAULT_SITEMAP_GROUP)
		return new_route(cls, template, name=name, template_file=template_file, **kw)
	@classmethod
	def rebuild_route(cls, template='/admin/rebuild_sitemap', name='rebuild_sitemap', **kw):
		"""
		:param template:
		:param name:
		:param sitemap_group:
			default 'default'
		:returns:
			a new :class:`Route` for the sitemap handler
		"""
		kw['rebuild'] = True
		kw['cache_control'] = CC_NO_CACHE
		kw.setdefault('sitemap_group', DEFAULT_SITEMAP_GROUP)
		return Route(handler=cls, template=template, name=name, **kw)
	def router_urls(self):
		"""Traverses all the routes and retrieves the possible urls for each one.
			Returns: a list of tupes (canonical, path)
		"""
		result = [] 
		#
		for r in self.app.router.match_routes:
			if r.sitemap_group != self.sitemap_group:
				continue
			for args, kwargs, priority in r.get_sitemap_args():
				 # @ToDo sitemap_args should be inmutable
				path = r.build(self.request, args, dict(kwargs))
				kwargs = dict(kwargs)
				kwargs['_canonical'] = True
				canonical = r.build(self.request, args, kwargs)
				result.append((canonical, path))
		return result
	#
	def defer_rebuild(self, router_urls, current_entries):
		from google.appengine.api import taskqueue
		entries_map = dict(map(lambda e: (e.loc, e.etag), current_entries))
		for canonical, path in router_urls:
			etag = entries_map.get(canonical, 'New')
			taskqueue.Queue("default").add(taskqueue.Task(url=path, headers={'_rebuild': etag, 'Set-Canonical': True}, method='HEAD'))
	#	
	def get(self, *args, **kwargs):
		entries = self.build_entries()
		if self.get_default('rebuild'):
			urls = self.router_urls()
			self.defer_rebuild(urls, entries)
			content = u'ok'
		else:
			template_file = self.request.route.template_file
			content = self.render_template(template_file, entries=entries)
		#
		r = self.request.route.build_response(unicode_body=content)
		return r
	#
	def build_entries(self):
		"""
			This method is here to allow a simple inheritance so you can customize the way you obtain the entries.
		:returns:
			the list of :class:`SitemapEntries` instances to include in this sitemap.
		"""
		return SitemapEntries.get_entries(self.sitemap_group)
	
		
