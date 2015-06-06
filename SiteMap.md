# Sitemap Handling #

The application defines a sitemap (by default located in _/sitemap.xml_), that includes all urls handled by the application.

## Request Handlers setup ##

Each new _route_ can define a **sitemap** attribute that defines if the handler URLs are included in the sitemap.
If the route defines a pattern instead of a simple path, the route has to define a _sitemap\_args_ argument to define the list of arguments to use building URLs for the sitemap.

Sitemap args is a list used in [URI Routing](http://webapp-improved.appspot.com/guide/routing.html#guide-routing).
```
models_args = []
for model in all_models:
	models_args.append(([], {'model_id': model.id}))

route = versapp.new_route(versapp.TemplateHandler, '/models/<model_id>', name='model', 
       template_file='html/model_.html', sitemap=True, sitemap_args=['model1', 'model2', 'model3', ])
```

# Details #

Add your content here.  Format your content with:
  * Text in **bold** or _italic_
  * Headings, paragraphs, and lists
  * Automatic links to other wiki pages


# Raw #

Sitemap
+ handlers
> - define si esta incluido y cual (True o string). (Sitemap-Group)
> - define sus propios valores para incluir las urls (args, kwargs),
> - priority, changefreq e imageloc se definen y graban junto con el lastmod (ver si puedo obtener el contexto modificado dsps del render)
> - header "Check-Lastmod" que marca la validacion. Busca los args y si no lo encuentra los trae del db.

+ sitemap handler
> - tiene asociado un Sitemap-Group.
> - busca todas las entradas del grupo y pinta directo
- solo responde en el canonico, sino 404, si es appspot devuelve las urls que devuelven los handlers, sin lastmod ni nada
> > (Es asi: si es canonico: full. Si es appspot: urls solo. Sino: 404)

+ sitemap rebuild handler

> - busca los paths de los handlers (se puede sobrescribir)
> - busca todas las entradas del grupo y borra los que no van mas)
> - manda a pintar los path que quedan mandando los headers de check + etag, lastmod, priority, etc
- si esta en background no devuelve nada, sino un redirect al referer o al home (x default)

+ wsgi app
- tiene un mtd statico q devuelve los handlers default (sitemap, rebuild)
- incluir en sitemap.xml un  comment que lo dejen en ese lugar si van con el default

+ app.yaml
- rebuild en admin section