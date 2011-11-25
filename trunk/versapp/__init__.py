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
from config import *


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
