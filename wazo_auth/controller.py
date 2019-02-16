# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import signal
import sys

from functools import partial

from xivo import plugin_helpers
from xivo.consul_helpers import ServiceCatalogRegistration

from . import bus, services, token
from .database import queries
from .flask_helpers import Tenant
from .helpers import LocalTokenManager
from .http_server import api, CoreRestApi
from .purpose import Purposes
from .service_discovery import self_check

logger = logging.getLogger(__name__)


def _signal_handler(signum, frame):
    sys.exit(0)


class Controller:

    def __init__(self, config):
        self._config = config
        try:
            self._listen_addr = config['rest_api']['https']['listen']
            self._listen_port = config['rest_api']['https']['port']
            self._foreground = config['foreground']
            self._consul_config = config['consul']
            self._service_discovery_config = config['service_discovery']
            self._plugins = config['enabled_backend_plugins']
            self._bus_config = config['amqp']
            self._log_level = config['log_level']
            self._debug = config['debug']
            self._bind_addr = (self._listen_addr, self._listen_port)
            self._max_threads = config['rest_api']['max_threads']
            self._xivo_uuid = config.get('uuid')
        except KeyError as e:
            logger.error('Missing configuration to start the application: %s', e)
            sys.exit(1)

        template_formatter = services.helpers.TemplateFormatter(config)
        self._bus_publisher = bus.BusPublisher(config)
        dao = queries.DAO.from_config(self._config)
        self._tenant_tree = services.helpers.CachedTenantTree(dao.tenant)
        self._token_manager = token.Manager(config, dao, self._tenant_tree, self._bus_publisher)
        self._backends = BackendsProxy()
        email_service = services.EmailService(dao, self._tenant_tree, config, template_formatter)
        external_auth_service = services.ExternalAuthService(
            dao, self._tenant_tree, config, self._bus_publisher, config['enabled_external_auth_plugins'])
        group_service = services.GroupService(dao, self._tenant_tree)
        policy_service = services.PolicyService(dao, self._tenant_tree)
        session_service = services.SessionService(dao, self._tenant_tree)
        self._user_service = services.UserService(dao, self._tenant_tree)
        self._tenant_service = services.TenantService(dao, self._tenant_tree, self._bus_publisher)

        self._metadata_plugins = plugin_helpers.load(
            namespace='wazo_auth.metadata',
            names=self._config['enabled_metadata_plugins'],
            dependencies={
                'user_service': self._user_service,
                'group_service': group_service,
                'tenant_service': self._tenant_service,
                'token_manager': self._token_manager,
                'backends': self._backends,
                'config': config,
            },
        )

        self._purposes = Purposes(
            self._config['purpose_metadata_mapping'],
            self._metadata_plugins,
        )

        backends = plugin_helpers.load(
            namespace='wazo_auth.backends',
            names=self._config['enabled_backend_plugins'],
            dependencies={
                'user_service': self._user_service,
                'group_service': group_service,
                'tenant_service': self._tenant_service,
                'purposes': self._purposes,
                'config': config,
            },
        )
        self._backends.set_backends(backends)
        self._config['loaded_plugins'] = self._loaded_plugins_names(self._backends)
        dependencies = {
            'api': api,
            'backends': self._backends,
            'config': config,
            'email_service': email_service,
            'external_auth_service': external_auth_service,
            'group_service': group_service,
            'user_service': self._user_service,
            'token_manager': self._token_manager,
            'policy_service': policy_service,
            'tenant_service': self._tenant_service,
            'session_service': session_service,
            'template_formatter': template_formatter,
        }
        Tenant.setup(self._token_manager, self._user_service, self._tenant_service)

        plugin_helpers.load(
            namespace='wazo_auth.http',
            names=config['enabled_http_plugins'],
            dependencies=dependencies,
        )
        manager = plugin_helpers.load(
            namespace='wazo_auth.external_auth',
            names=config['enabled_external_auth_plugins'],
            dependencies=dependencies,
        )

        config['external_auth_plugin_info'] = {}
        if manager:
            for extension in manager:
                plugin_info = getattr(extension.obj, 'plugin_info', {})
                config['external_auth_plugin_info'][extension.name] = plugin_info

        self._rest_api = CoreRestApi(config, self._token_manager, self._user_service)

        self._expired_token_remover = token.ExpiredTokenRemover(config, dao, self._bus_publisher)

    def run(self):
        signal.signal(signal.SIGTERM, _signal_handler)  # TODO use sigterm_handler

        with bus.publisher_thread(self._bus_publisher):
            with ServiceCatalogRegistration('wazo-auth',
                                            self._xivo_uuid,
                                            self._consul_config,
                                            self._service_discovery_config,
                                            self._bus_config,
                                            partial(self_check,
                                                    self._listen_port)):
                self._expired_token_remover.run()
                local_token_manager = self._get_local_token_manager()
                self._config['local_token_manager'] = local_token_manager
                try:
                    self._rest_api.run()
                finally:
                    self._rest_api.stop()
                local_token_manager.revoke_token()

    def _get_local_token_manager(self):
        try:
            backend = self._backends['wazo_user']
        except KeyError:
            logger.info('wazo_user disabled no internal token will be created for wazo-auth')
            return

        return LocalTokenManager(backend, self._token_manager, self._user_service)

    def _loaded_plugins_names(self, backends):
        return [backend.name for backend in backends]


class BackendsProxy:

    def __init__(self):
        self._backends = {}

    def set_backends(self, backends):
        self._backends = backends

    def __getitem__(self, key):
        return self._backends[key]

    def __iter__(self):
        return iter(self._backends)
