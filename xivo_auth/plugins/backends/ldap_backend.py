# -*- coding: utf-8 -*-

# Copyright (C) 2007-2014 Avencall
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

from __future__ import absolute_import

import ldap
import logging

logger = logging.getLogger('ldap')

class XivoLDAP(object):

    def __init__(self, config):
        self.config = config
        self.ldapobj = None

        try:
            logger.info('LDAP config requested: %s', self.config)
            self.ldapobj = self._create_ldap_obj(self.config)
        except ldap.LDAPError, exc:
            logger.exception('__init__: ldap.LDAPError (%r, %r, %r)', self.ldapobj, self.config, exc)
            self.ldapobj = None

    def _create_ldap_obj(self, config):
        ldapobj = ldap.initialize(config['uri'], 0)
        ldapobj.set_option(ldap.OPT_REFERRALS, 0)
        ldapobj.set_option(ldap.OPT_NETWORK_TIMEOUT, 2)
        ldapobj.set_option(ldap.OPT_TIMEOUT, 2)
        return ldapobj

    def perform_bind(self, username, password):
        if not self.ldapobj:
            logger.warning('LDAP SERVER not responding')
            self.ldapobj = None
            return

        usetls = False
        if usetls:
            self.ldapobj.set_option(ldap.OPT_X_TLS, 1)

        try:
            self.ldapobj.simple_bind_s(username, password)
            logger.info('LDAP : simple bind done on %(uri)s', self.config)
            return True
        except ldap.INVALID_CREDENTIALS:
            logger.info('LDAP : simple bind failed on %(uri)s : invalid credentials!', self.config)
        return False