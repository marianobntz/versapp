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
			m_a['Language'] = request.app.config.get('canonical_language', DEFAULT_LANGUAGE)
			logging.error(m_a['Language'])
			request.host = request.app.config.get('canonical_netloc')
			# m_a['Language'] = request.app.config.get('canonical_language', DEFAULT_LANGUAGE)
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
