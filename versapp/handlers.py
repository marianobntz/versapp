#!/usr/bin/python
# -*- coding: utf-8 -*-
# $Id$
#
import os
import logging

import webapp2
import webapp2_extras
import jinja2

from google.appengine.api import app_identity

from versapp.utils import *
from versapp.routes import *

import config

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

class RequestHandler(webapp2.RequestHandler):
	@webapp2.cached_property
	def jinja2(self):
		# Returns a Jinja2 renderer cached in the app registry.
		return webapp2_extras.jinja2.get_jinja2()
	#
	def render_template(self, _template, **context):
		# Renders a template and returns the result string.
		return self.jinja2.render_template(_template, **context)
	#
	def render_template_str(self, _template_str, **context):
		# Renders a template and returns the result string.
		template = self.jinja2.environment.from_string(_template_str)
		return template.render(**context)
	#
	def get_default(self, key, default=None):
		return self.request.route.defaults.get(key, default)
	#
	def update_default(self, key, value):
		""" only use to change the state of the route in runtime! Use carefully
		"""
		self.request.route.defaults[key] = value
	#
	def initialize(self, request, response):
		super(RequestHandler, self).initialize(request, response)
		m_a = {}
		# 
		# here we modify the request so it makes it believe is canonical
		if request.get('Set-Canonical', False):
			m_a['Language'] = request.app.config.get('canonical_language', config.DEFAULT_LANGUAGE)
			logging.error(m_a['Language'])
			request.host = request.app.config.get('canonical_netloc')
			# m_a['Language'] = request.app.config.get('canonical_language', config.DEFAULT_LANGUAGE)
		else:
			m_a['Language'] = request.environ['REQUEST_LANGUAGE']
		m_a.update(request.route_kwargs)
		m_a.update(request.environ)
		# add other basic attributes
		m_a['route_name'] = request.route.name
		self.mapping_args = m_a
	#
	def check_last_modified(self, response):
		prev_etag = self.request.headers.get("_rebuild", None)
		if not prev_etag:
			return
		if prev_etag != response.etag:
			# store new etag and last-modified
			logging.info("Sitemap entry updated %s" % self.request.path)
			# change the loc from request.path_url to the canonical url (then it will work fine)
			SitemapEntries.update(group=self.request.route.sitemap_group, loc=self.request.path_url, etag=response.etag, priority="0.4")
		# ToDo how to customize priority and changefreq
	
	def _fix_full_netlocs(self):
		""" 
		"""
		cdn_netlocs = self.app.config[CDN_NETLOCS]

		keep_netloc = IS_GOOGLE and not self.request.host.endswith(app_identity.get_default_version_hostname())

		netlocs_map = dict(map(lambda x: (x, x if keep_netloc else self.request.host), cdn_netlocs))
		
		self.request.environ[CDN_NETLOCS] = netlocs_map

		if keep_netloc:
			if self.request.route._netloc:
				valid_hosts = [self.request.route._netloc]
			else:
				valid_hosts = [self.app.config.get('canonical_netloc')]
		else:
			valid_hosts = [self.request.host]
		self.request.environ['valid_hosts'] = valid_hosts

	def dispatch(self):
		# 
		self._fix_full_netlocs()
		
		if self.request.host not in self.request.environ['valid_hosts']:
			self.abort(404)
		
		return super(RequestHandler, self).dispatch()
#
class TemplateHandler(RequestHandler):
	@webapp2.cached_property
	def template_file(self):
		"""This is the template file that will be used for rendering the response.
			If the route has a template_format, it will be formatted using the request arguments.
		"""
		if hasattr(self.request.route, 'template_format'):
			return self.request.route.template_format % self.mapping_args
		else:
			return self.request.route.template_file

	def build_mapping(self):
		"""This method builds the argument map to render the template. Override to customize the map"""
		return self.mapping_args

	def get(self, *args, **kwargs):
		if self.get_default('versioned'):
			versioned_arg = self.get_default('versioned')
			req_rev = kwargs[versioned_arg]
			cur_rev = self.get_default(versioned_arg)
			if req_rev == cur_rev:
				content = self.render_template(self.template_file, **self.mapping_args)
			else:
				# fetch old version from datastore
				old_template = Versioned_Files.get_content(self.template_file, req_rev)
				if not old_template:
					self.abort(404, "Old version %s no esta!" % self.request.path) # TODO (mariano) improve error
				content = self.render_template_str(old_template, **self.mapping_args)
		else:
			content = self.render_template(self.template_file, **self.build_mapping())
		r = self.request.route.build_response(unicode_body=content)
		self.check_last_modified(r)
		return r

	@classmethod
	def new_route(cls, template, name, **kw):
		return new_route(cls, template, name, **kw)
		
#
#
class StaticHandler(RequestHandler):
	def head(self, *args, **kwargs):
		self.get(*args, **kwargs)
	def get(self, *args, **kwargs):
		if self.get_default('versioned'):
			versioned_arg = self.get_default('versioned')
			template_file = self.request.route.template_file
			req_rev = kwargs[versioned_arg]
			cur_rev = self.get_default(versioned_arg)
			if req_rev == cur_rev:
				content = read_binary_file(template_file)
			else:
				# fetch old version from datastore
				content = Versioned_Files.get_content(template_file, req_rev)
				if not content:
					self.abort(404, "Old version %s no esta!" % self.request.path)
		else:
			content = read_binary_file(self.request.route.template_file)
		r = self.request.route.build_response(body=content)
		return r

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
		kw['cache_control'] = config.CC_NO_CACHE
		kw.setdefault('sitemap_group', config.DEFAULT_SITEMAP_GROUP)
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
		kw['cache_control'] = config.CC_NO_CACHE
		kw.setdefault('sitemap_group', config.DEFAULT_SITEMAP_GROUP)
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
			for args, kwargs in r.sitemap_args: # removed priority
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
			taskqueue.Queue("default").add(taskqueue.Task(url=path, headers={'_rebuild': etag, 'Set-Canonical': True}, method='GET')) # @ToDo implement HEAD method
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
