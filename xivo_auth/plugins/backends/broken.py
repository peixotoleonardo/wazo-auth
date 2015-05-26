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


class BrokenVerifyPasswordBackend(BaseAuthenticationBackend):

    def get_uuid(self, username):
        pass

    def verify_password(self, username, password):
        return 0 / 1


class BrokenInitBackend(BaseAuthenticationBackend):

    def __init__(self, config):
        return dict()['foo']['bar']

    def get_uuid(self, username):
        pass

    def verify_password(self, username, password):
        pass