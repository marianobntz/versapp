#!/usr/bin/python
# -*- coding: utf-8 -*-
# $Id$
#
import os
import logging
import webapp2
from versapp.utils import *

CDN_NETLOCS = 'cdn_netlocs' # local CDN network locations

class Route(webapp2.Route):
	"""The Route object contains all configuration information about the route.

	All routes should extend this class, so it can use the _canonical argument in uri_for
	
	:param template:
	:param handler: 
	:param cache_control:
	:param content_type:
	:param sitemap:
		include the route in the sitemap. default True
		if True then use the default sitemap group, if string use at sitemap group.
	:param sitemap_args:
		what is used to build the URIs to include in the sitemap. 
		Can be a static attribute of a callable.
		Must be a list of tuple(args[], kwargs{})
	"""
	def __init__(self, template=None, handler=None, name=None, **kw):
		"""
		Args:
			template:
				The t
			handler: 
			cache_control:
			content_type:
			sitemap: Include this route in the sitemap. default True
				if True then use the default sitemap group, if string use at sitemap group.
			sitemap_args:
				what is used to build the URIs to include in the sitemap. 
				Can be a static attribute of a callable.
				Must be a list of tuple(args[], kwargs{})

			_netloc: network location when rendering this route in _full. Default is None (the canonical)
			_full: always render the route as full
				
		"""
		super(Route, self).__init__(template, handler=handler, name=name, build_only=kw.pop("build_only", None), defaults=kw.pop("defaults", None), methods=kw.pop("methods", ('GET', 'HEAD')), schemes=kw.pop("schemes", None))
		self.cache_control = kw.pop("cache_control", None)
		self.content_type = kw.pop("content_type", "text/html")

		s = kw.pop("sitemap", None)
		from versapp import DEFAULT_SITEMAP_GROUP # @ToDo que hacemos con el default
		self.sitemap_group = None if not s else DEFAULT_SITEMAP_GROUP if s == True else s

		self._sitemap_args = kw.pop("sitemap_args", None)
		
		self._netloc = kw.pop('_netloc', None)

		self._full = kw.pop('_full', True if self._netloc else False)

		self.defaults.update(kw)

	def _get_sitemap_args(self):
		"""
		:returns: the arguments to use in the sitemap building URIs
		"""
		if not self._sitemap_args:
			return [([], {})]
		elif callable(self._sitemap_args):
			return self._sitemap_args()
		else:
			return self._sitemap_args # @ToDo clone the map so it is not modified

	sitemap_args = property(_get_sitemap_args, doc=_get_sitemap_args.__doc__)

		
	def build_response(self, body=None, unicode_body=None):
		r = webapp2.Response()

		from versapp import CC_NO_CACHE
		r.cache_control = self.cache_control or webapp2.get_app().config.get('default_cache_control', CC_NO_CACHE)
		r.content_type = self.content_type

		if body:
			r.body = body
		if unicode_body:
			r.unicode_body = unicode_body
			
		r.md5_etag() # we always send the eTag so we can work with conditional responses
		r.conditional_response = True # revisar si podemos tocarlo esto
		#
		return r

	def build(self, request, args, kwargs):
		"""Enhance the _full argument to use a specific network location based on the host key. 
		"""
		if (kwargs.get('_full') or self._full) and self._netloc:
			cdn_netlocs = request.environ.get(CDN_NETLOCS) # this is the map of CDN hosts appropriate for the request object

			kwargs['_netloc'] = cdn_netlocs.get(self._netloc, self._netloc) # if not defined, used the same value
			
		return super(Route, self).build(request, args, kwargs)
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
def new_route(handler, template, name, **kw):
	"""Creates a new File Route
	Returns:
		a new FileRoute instance
	"""
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
	
def build_route(template, name, **kw):
	return Route(template=template, name=name, build_only=True, **kw)
