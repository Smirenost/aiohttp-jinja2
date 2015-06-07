import asyncio
import functools
import jinja2
from collections import Mapping
from aiohttp import web


__version__ = '0.4.3'

__all__ = ('setup', 'get_env', 'render_template', 'template')


APP_KEY = 'aiohttp_jinja2_environment'


def setup(app, *args, app_key=APP_KEY, **kwargs):
    env = jinja2.Environment(*args, **kwargs)
    app[app_key] = env

    def url(__aiohttp_jinjs2_route_name,  **kwargs):
        return app.router[__aiohttp_jinjs2_route_name].url(**kwargs)

    env.globals['url'] = url
    env.globals['app'] = app

    return env


def get_env(app, *, app_key=APP_KEY):
    return app.get(app_key)


def render_string(template_name, request, context, *, app_key):
    env = request.app.get(app_key)
    if env is None:
        text = ("Template engine is not initialized, "
                "call aiohttp_jinja2.setup(app_key={}) first"
                "".format(app_key))
        # in order to see meaningful exception message both: on console
        # output and rendered page we add same message to *reason* and
        # *text* arguments.
        raise web.HTTPInternalServerError(reason=text, text=text)
    try:
        template = env.get_template(template_name)
    except jinja2.TemplateNotFound as e:
        raise web.HTTPInternalServerError(
            text="Template '{}' not found".format(template_name)) from e
    if not isinstance(context, Mapping):
        text = "context should be mapping, not {}".format(type(context))
        # same reason as above
        raise web.HTTPInternalServerError(reason=text, text=text)
    text = template.render(context)
    return text


def render_template(template_name, request, context, *,
                    app_key=APP_KEY, encoding='utf-8'):
    response = web.Response()
    text = render_string(template_name, request, context, app_key=app_key)
    response.content_type = 'text/html'
    response.charset = encoding
    response.text = text
    return response


def template(template_name, *, app_key=APP_KEY, encoding='utf-8', status=200):

    def wrapper(func):
        @asyncio.coroutine
        @functools.wraps(func)
        def wrapped(*args):
            if asyncio.iscoroutinefunction(func):
                coro = func
            else:
                coro = asyncio.coroutine(func)
            context = yield from coro(*args)
            request = args[-1]
            response = render_template(template_name, request, context,
                                       app_key=app_key, encoding=encoding)
            response.set_status(status)
            return response
        return wrapped
    return wrapper
