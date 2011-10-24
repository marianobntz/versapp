#!/usr/bin/env python
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
import re
import webob
import webapp2
import webapp2_extras
import jinja2
from webapp2_extras import jinja2 as jinja2e
from utils import *

DEFAULT_LANGUAGE = APP_LANGUAGE_DEFAULT
# DEFAULT_CACHE_CONTROL = "public, max-age=31536000"  # 1 year (365 * 86400)
DEFAULT_CACHE_CONTROL = "no-cache"
NO_CACHE = "no-cache"


class WSGIApplication(webapp2.WSGIApplication):
	def __init__(self, *args, **kwargs):
		super(WSGIApplication, self).__init__(*args, **kwargs)
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
def initialize(template_path, *args, **kwargs):
	jinja2_globals = {'uri_for': webapp2.uri_for }
	if kwargs.get('globals'):
		jinja2_globals.update(kwargs['globals'])
		del kwargs['globals']
	jinja2e.default_config = {
		'template_path': template_path, 
		'compiled_path': None,
		'filters': None,
		'force_compiled': False,
		'globals': jinja2_globals, 
		'environment_args': {'autoescape': True, 'extensions': ['jinja2.ext.autoescape', 'jinja2.ext.with_']}, 
	}
	return WSGIApplication(*args, **kwargs)
#
class Response(webapp2.Response):
	def header_data(self):
		#
		# First the eTag
		self.md5_etag()
		#
		# Last-Modified
		self.last_modified = get_set_response_data('path', self.eTag)
		
		
class Route(webapp2.Route):
	"""The Route object contains all configuration information about the route.

    :template:
	:handler: 
	:cache_control:
    """
    
	def __init__(self, template=None, handler=None, name=None, **kw):
		super(Route, self).__init__(template, handler=handler, name=name, build_only=kw.pop("build_only", None), defaults=kw.pop("defaults", None), methods=kw.pop("methods", ('GET', 'HEAD')), schemes=kw.pop("schemes", None))
		self.cache_control = kw.pop("cache_control", DEFAULT_CACHE_CONTROL)
		self.content_type = kw.pop("content_type", "text/html")
		self.in_sitemap = kw.pop("in_sitemap", False)
		self.defaults.update(kw)
	#
	def build_response(self, body=None, unicode_body=None):
		r = webapp2.Response()
		r.cache_control = self.cache_control
		r.content_type = self.content_type
		if body:
			r.body = body
		if unicode_body:
			r.unicode_body = unicode_body
		if r.cache_control != NO_CACHE:
			r.md5_etag()
		#
		return r
#
class FileRoute(Route):
	"""A Route based on rendering a file.
    :template:
	:handler: 
	:cache_control:
    """
	def __init__(self, template=None, handler=None, name=None, template_file=None, template_format=None, validate_file=False, content_type_from_extension=True, **kw):
		super(FileRoute, self).__init__(template=template, handler=handler, name=name, **kw)
		if template_file:
			self.template_file = template_file
			f = template_file
		elif template_format:
			self.template_format = template_format
			f = template_format
		else:
			raise AssertionError("Route must have template_file or template_format")
		if validate_file:
			pass
		if content_type_from_extension:
			k = f[f.rfind('.')+1:]
			self.content_type = CONTENT_TYPES.get(k, 'text/plain')			
	#
#
class RequestHandler(webapp2.RequestHandler):
	@webapp2.cached_property
	def jinja2(self):
		# Returns a Jinja2 renderer cached in the app registry.
		return webapp2_extras.jinja2.get_jinja2(app=self.app)
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
		m_a.update(request.route_kwargs)
		m_a.update(request.environ)
		# add other basic attributes
		m_a['Language'] = request.environ['REQUEST_LANGUAGE']
		m_a['route_name'] = request.route.name
		self.mapping_args = m_a
#
class TemplateHandler(RequestHandler):
	def get_file(self):
		if hasattr(self.request.route, 'template_format'):
			return self.request.route.template_format % self.mapping_args
		else:
			return self.request.route.template_file
	def build_mapping(self):
		return self.mapping_args
	def get(self, *args, **kwargs):
		template_file = self.get_file()
		if self.get_default('versioned'):
			versioned_arg = self.get_default('versioned')
			req_rev = kwargs[versioned_arg]
			cur_rev = self.get_default(versioned_arg)
			if req_rev == cur_rev:
				content = self.render_template(template_file, **self.mapping_args)
			else:
				# fetch old version from datastore
				old_template = Versioned_Files.get_content(template_file, req_rev)
				if not old_template:
					self.abort(404, "Old version %s no esta!" % self.request.path)
				content = self.render_template_str(old_template, **self.mapping_args)
		else:
			content = self.render_template(template_file, **self.build_mapping())
		r = self.request.route.build_response(unicode_body=content)
		return r
#
#
class StaticHandler(RequestHandler):
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
def new_route(handler, template, name, **kw):
	defaults = kw.setdefault('defaults', {})
	if kw.get('versioned_arg'):
		assert kw.get('template_file'), "Versioned routes must use template_file"
		versioned_arg = kw.get('versioned_arg')
		template_file = kw['template_file'] 
		file_version, content = read_file_version(os.path.join("templates", template_file))
		#
		defaults[versioned_arg] = file_version
		defaults['versioned'] = versioned_arg
		#
		# check if the version is saved in datastore and store it if not exists
		Versioned_Files.check_version(template_file, file_version, content)
		#
	return FileRoute(template=template, handler=handler, name=name, **kw)
