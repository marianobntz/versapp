from utils import APP_LANGUAGE_DEFAULT

DEFAULT_LANGUAGE = APP_LANGUAGE_DEFAULT
DEFAULT_SITEMAP_GROUP = "default"
DEFAULT_TEMPLATES_PATH = 'templates'
CC_NO_CACHE = "no-cache"
CC_PUBLIC = lambda max_age: "public, max-age=%s" % max_age
CC_PRIVATE = lambda max_age: "private, max-age=%s" % max_age
day = 24*60*60
year = 365*day
