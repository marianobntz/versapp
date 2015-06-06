# Routes #
The framework works only with versapp.Route instances.

# Sitemap #

Listing a Route in the sitemap requires that you define a default value of "sitemap\_group".

## Building the sitemap entries is independent of rendering a sitemap ##
To optimize and simplify the framework, the sitemap handler will just query the SitemapEntries table filtering with the sitemap group.

The same handler in a different hole will take care of dispatching the rebuild of each route\_group

The sitemap is part of the framework, and each route defines an **in\_sitemap** attribute, plus a **sitemap\_args** used to retrieve the list of arguments used to build the sitemap uris.

# Response Headers #

For simplicity we decided to use **eTag** as the validator and **max-age** as the refresh information.

We discarded _Last-Modified_ because it would force us to keep the date for every page, plus the variations of language, etc.
We discarded _Expires_ because it is simpler to just include the seconds, than calculate every time.

Each route defines the cache control directive, plus a default value is set.

# Multi-Language support #

it is based on the server host, the _HTTP\_X\_APPENGINE\_COUNTRY_ environment var,  a cookie or a query param.

# Canonical URIs #

It is a good practice to include the rel="canonical" header, but we need to know the canonical network location, so we decided to accept the _**canonical\_netloc** config parameter, and enhance the_uri\_for**method to accept the canonical** argument to use that network location.

# Jinja #

We  use a single instance of jinja2 object. The default configuration is modified, so we do not use the instance specific params. This is simpler than allowing multiple app instances, which is complex to setup for simple apps.

**trim\_blocks** to remove new lines