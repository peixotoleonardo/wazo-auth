# -*- coding: utf-8 -*-
# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os

from jinja2 import BaseLoader, Environment, TemplateNotFound
from treelib import Tree

from xivo.consul_helpers import address_from_config


class BaseService(object):

    def __init__(self, dao):
        self._dao = dao
        self._top_tenant_uuid = None

    @property
    def top_tenant_uuid(self):
        if not self._top_tenant_uuid:
            self._top_tenant_uuid = self._dao.tenant.find_top_tenant()
        return self._top_tenant_uuid


class TemplateLoader(BaseLoader):

    _templates = {
        'email_confirmation': 'email_confirmation_template',
        'email_confirmation_get_body': 'email_confirmation_get_reponse_body_template',
        'email_confirmation_subject': 'email_confirmation_subject_template',
        'reset_password': 'password_reset_email_template',
        'reset_password_subject': 'password_reset_email_subject_template',
    }

    def __init__(self, config):
        self._config = config

    def get_source(self, environment, template):
        config_key = self._templates.get(template)
        if not config_key:
            raise TemplateNotFound(template)

        template_path = self._config[config_key]
        if not os.path.exists(template_path):
            raise TemplateNotFound(template)

        mtime = os.path.getmtime(template_path)
        with file(template_path) as f:
            source = f.read().decode('utf-8')

        return source, template_path, lambda: mtime == os.path.getmtime(template_path)


class TemplateFormatter(object):

    def __init__(self, config):
        self.environment = Environment(
            loader=TemplateLoader(config),
        )
        self.environment.globals['port'] = config['service_discovery']['advertise_port']
        self.environment.globals['hostname'] = address_from_config(config['service_discovery'])

    def format_confirmation_email(self, context):
        template = self.environment.get_template('email_confirmation')
        return template.render(**context)

    def get_confirmation_email_get_body(self, context=None):
        context = context or {}
        template = self.environment.get_template('email_confirmation_get_body')
        return template.render(**context)

    def format_confirmation_subject(self, context):
        template = self.environment.get_template('email_confirmation_subject')
        return template.render(**context)

    def format_password_reset_email(self, context):
        template = self.environment.get_template('reset_password')
        return template.render(**context)

    def format_password_reset_subject(self, context):
        template = self.environment.get_template('reset_password_subject')
        return template.render(**context)


class TenantTree(object):

    def __init__(self, tenants):
        self._tree = self._build_tree(tenants)

    def list_nodes(self, nid):
        subtree = self._tree.subtree(nid)
        return [n.identifier for n in subtree.all_nodes()]

    def _build_tree(self, tenants):
        nb_tenants = len(tenants)
        inserted_tenants = set()
        tree = Tree()

        for tenant in tenants:
            if tenant['uuid'] == tenant['parent_uuid']:
                tree.create_node(tenant['name'], tenant['uuid'])
                inserted_tenants.add(tenant['uuid'])

        while True:
            if len(inserted_tenants) == nb_tenants:
                break

            for tenant in tenants:
                if tenant['uuid'] in inserted_tenants:
                    continue

                if tenant['parent_uuid'] not in inserted_tenants:
                    continue

                tree.create_node(tenant['name'], tenant['uuid'], tenant['parent_uuid'])
                inserted_tenants.add(tenant['uuid'])

        return tree
