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

from xivo_auth import BaseAuthenticationBackend

from xivo_dao.resources.user import dao as user_dao
from xivo_dao.helpers.db_utils import session_scope


class XiVOUser(BaseAuthenticationBackend):

    def get_consul_acls(self, username, args):
        identifier, _ = self.get_ids(username, args)
        rules = [{'rule': 'xivo/private/{identifier}'.format(identifier=identifier),
                  'policy': 'write'}]
        return rules

    def get_acls(self, login, args):
        return ['acl:dird']

    def get_ids(self, username, args):
        with session_scope():
            user = user_dao.get_by(username=username, enableclient=1)
            return user.uuid, user.uuid

    def verify_password(self, login, password):
        with session_scope():
            user = user_dao.find_by(username=login, password=password, enableclient=1)
            return user is not None
