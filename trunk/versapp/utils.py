#!/usr/bin/env python
# -*- coding: utf-8 -*-
# $Id$
#
import os
import logging
#
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.runtime.apiproxy_errors import CapabilityDisabledError

CONTENT_TYPES = {
	'html': 'text/html',
	'txt': 'text/plain',
	'xml': 'text/xml',
	'css': 'text/css',
	'csv': 'text/csv',	
	'js':  'text/javascript',
	'htc': 'text/x-component',
	'ico': 'image/x-icon',
	'jpg': 'image/jpeg',
	'images.jpg': 'image/jpeg',
	'images.png': 'image/png',	
	'swf': 'application/x-shockwave-flash',
}
APP_LANGUAGES = ['es', 'en', ]
APP_LANGUAGE_DEFAULT = 'es'
COUNTRY_2_LANGUAGE = { 'AR': 'es', 'BR': 'pt', 'US': 'en'}
#
def request_language(request):
	result = request.get("hl", default_value=None)
	if result in APP_LANGUAGES:
		return result
	#
	# try to find a cookie
	# logging.error(environ['HTTP_COOKIE'] if 'HTTP_COOKIE' in environ else "No Cookies")
	#
	# use server name to detect language
	serverName = os.environ.get('SERVER_NAME', os.environ['HTTP_HOST'])
	if serverName and serverName[2] == '.' and serverName[:2] in APP_LANGUAGES:
		return serverName[:2]
	#
	# use HTTP country
	country = os.environ.get('HTTP_X_APPENGINE_COUNTRY')
	if country in COUNTRY_2_LANGUAGE:
		return COUNTRY_2_LANGUAGE[country]
	#
	# default to spanish
	return APP_LANGUAGE_DEFAULT
#
def read_file(path):
	f = None
	try:
		f = open(path, mode='rb')
		content = f.read()
	finally:
		if f: f.close()
	return content.decode("utf-8")
#
def read_binary_file(path):
	f = None
	try:
		f = open(path, mode='rb')
		return f.read()
	finally:
		if f: f.close()
#
def read_file_version(path):
	""""Uses SVN format to obtain version number (%05d)."""
	data = read_binary_file(path)
	if not data:
		return None
	x1 = data.find("$Id:")
	line = data[x1: x1+100]
	sp = line.split()
	return sp[2].rjust(5,'0'), data
#
def walk_tree(root):
	""""Returns the list of files (complete with subpaths) inside the root tree."""
	result = []
	for base, dirs, files in os.walk(root):
		base_prefix = "" if root == base else base[len(root)+1:]
		for f in files:
			path = os.path.join(base_prefix, f)
			result.append(path)
	result.sort()
	return result
#
class Response_Data(db.Model):
	group = db.StringProperty()
	path = db.StringProperty()
	eTag = db.StringProperty()
	lastModified = db.DateTimeProperty()
	#
	@classmethod
	def get_data(cls, group):
		data = []
		q = db.Query(Response_Data).filter("group =", group)
		for r in q:
			data.append((r.path, r.eTag, r.lastModified))
		return data
		
#
def get_response_data(response):
	data_key_str = response.path
	data_key = db.Key.from_path(Response_Data.kind(), data_key_str)
#
class Versioned_Files(db.Model):
	template_file = db.StringProperty()
	file_version = db.StringProperty()
	content = db.BlobProperty()
	#
	@classmethod
	def check_version(cls, template_file, file_version, content):
		q = db.Query(Versioned_Files, keys_only=True).filter("template_file =", template_file). filter("file_version =", file_version)
		r = q.get()
		if not r:
			Versioned_Files(template_file=template_file, file_version=file_version, content=content).put()
			logging.info("stored version!!! %s %s " % (template_file, file_version))
	#
	@classmethod
	def get_content(cls, template_file, file_version):
		q = Versioned_Files.gql("WHERE template_file = :1 and file_version = :2", template_file, file_version)
		r = q.get()
		return r.content if r else None
#
