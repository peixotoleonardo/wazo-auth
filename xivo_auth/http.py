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

import time

from flask import current_app, request, make_response
from flask_restful import Resource
from flask.ext.httpauth import HTTPBasicAuth

from xivo_auth.token import ManagerException

httpauth = HTTPBasicAuth()


def _error(code, msg):
    return {'reason': [msg],
            'timestamp': [time.time()],
            'status_code': code}, code


class Token(Resource):

    @httpauth.login_required
    def post(self):
        data = request.get_json()
        args = {}
        if 'expiration' in data:
            if not data['expiration'] > 0:
                return _error(400, 'Invalid expiration')

            args['expiration'] = data['expiration']

        uuid = _call_backend('get_uuid', httpauth.username())
        try:
            token = current_app.config['token_manager'].new_token(uuid, **args)
        except ManagerException as e:
            return _error(e.code, str(e))

        response = {'data': token.to_dict()}
        return response, 200

    def delete(self, token):
        try:
            current_app.config['token_manager'].remove_token(token)
        except ManagerException as e:
            return _error(e.code, str(e))

        return {'data': {'message': 'success'}}

    def get(self, token):
        try:
            token = current_app.config['token_manager'].get(token)
            return {'data': token.to_dict()}
        except ManagerException as e:
            return _error(e.code, str(e))

    def head(self, token):
        try:
            token = current_app.config['token_manager'].get(token)
            return make_response('', 204)
        except ManagerException as e:
            return _error(e.code, str(e))


class Backends(Resource):

    def get(self):
        return {'data': current_app.config['enabled_plugins']}


@httpauth.verify_password
def verify_password(login, passwd):
    try:
        return _call_backend('verify_password', login, passwd)
    except IndexError:
        return False


def _call_backend(fn, *args, **kwargs):
    backend_names = [request.get_json()['backend']]
    results = current_app.config['backends'].map_method(backend_names, fn, *args, **kwargs)
    return results[0]
