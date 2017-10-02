# -*- coding: utf-8 -*-
#
# Copyright 2015-2017 The Wazo Authors  (see the AUTHORS file)
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

from wazo_auth import BaseAuthenticationBackend


class BackendMock(BaseAuthenticationBackend):

    def get_acls(self, login, args):
        return ['foo', 'bar', 'auth.#']

    def get_ids(self, login, agrs):
        return 'a-mocked-uuid', None

    def verify_password(self, login, password, args):
        return login == 'foo' and password == 'bar'


class BackendMockWithUUID(BaseAuthenticationBackend):

    def get_acls(self, login, args):
        return ['foo', 'bar']

    def get_ids(self, login, args):
        return 'a-mocked-auth-id', 'a-mocked-xivo-user-uuid'

    def verify_password(self, login, password, args):
        return login == 'foo' and password == 'bar'