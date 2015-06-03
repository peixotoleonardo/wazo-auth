# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import logging
import sys

from threading import Thread

from celery import Celery
from consul import Consul
from flask import Flask
from flask_restful import Api
from flask.ext.cors import CORS
from stevedore.dispatch import NameDispatchExtensionManager

from xivo_auth import http, token, extensions

logger = logging.getLogger(__name__)


class Controller(object):

    def __init__(self, config):
        self._config = config
        try:
            self._listen_addr = config['rest_api']['listen']
            self._listen_port = config['rest_api']['port']
            self._foreground = config['foreground']
            self._cors_config = config['rest_api']['cors']
            self._cors_enabled = self._cors_config['enabled']
            self._consul_config = config['consul']
            self._plugins = config['enabled_plugins']
            self._bus_uri = config['amqp']['uri']
        except KeyError:
            logger.error('Missing configuration to start the application')

        backends = self._load_backends()
        self._celery = self._configure_celery()
        consul_client = Consul(**self._consul_config)
        token_manager = token.Manager(config, consul_client, self._celery)
        self._flask_app = self._configure_flask_app(backends, token_manager)
        self._override_celery_task()

    def run(self):
        self._start_celery_worker()
        self._flask_app.run(self._listen_addr, self._listen_port)

    def _start_celery_worker(self):
        celery_thread = Thread(target=self._celery.worker_main, args=(sys.argv[:1],))
        celery_thread.daemon = True
        celery_thread.start()

    def _load_backends(self):
        return _PluginLoader(self._config).load()

    def _configure_celery(self):
        celery = Celery('xivo-auth', broker=self._bus_uri)
        celery.conf.update(self._config)
        celery.conf.update(
            CELERY_RESULT_BACKEND=self._bus_uri,
            CELERY_ACCEPT_CONTENT=['json'],
            CELERY_TASK_SERIALIZER='json',
            CELERY_RESULT_SERIALIZER='json',
            CELERY_ALWAYS_EAGER=False,
            CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
            CELERY_DEFAULT_EXCHANGE_TYPE='topic',
            CELERYD_HIJACK_ROOT_LOGGER=False,
        )
        return celery

    def _override_celery_task(self):
        TaskBase = self._celery.Task
        app = self._flask_app

        class ContextTask(TaskBase):
            abstract = True

            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return TaskBase.__call__(self, app, *args, **kwargs)

        self._celery.Task = ContextTask
        extensions.celery = self._celery
        from xivo_auth import tasks  # noqa

    def _configure_flask_app(self, backends, token_manager):
        app = Flask(__name__)
        api = Api(app)
        api.add_resource(http.Token,
                         '/0.1/token',
                         '/0.1/token/<string:token>')
        api.add_resource(http.Backends, '/0.1/backends')
        app.config.update(self._config)
        if self._cors_enabled:
            CORS(app, **self._cors_config)

        app.config['token_manager'] = token_manager
        app.config['backends'] = backends

        return app


class _PluginLoader(object):

    namespace = 'xivo_auth.backends'

    def __init__(self, config):
        self._enabled_plugins = config['enabled_plugins']
        self._config = config
        self._backends = NameDispatchExtensionManager(namespace=self.namespace,
                                                      check_func=self._check,
                                                      verify_requirements=False,
                                                      propagate_map_exceptions=True,
                                                      invoke_on_load=False)

    def load(self):
        self._backends.map(self._enabled_plugins, self._load)
        return self._backends

    def _check(self, plugin):
        return plugin.name in self._enabled_plugins

    def _load(self, extension):
        try:
            extension.obj = extension.plugin(self._config)
        except Exception:
            logger.exception('Failed to load %s', extension.name)