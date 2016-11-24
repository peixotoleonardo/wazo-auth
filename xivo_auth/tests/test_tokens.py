# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Avencall
# Copyright (C) 2016 Proformatique, Inc.
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

import unittest
import json
import time
import uuid

from datetime import datetime, timedelta

from hamcrest import assert_that, contains_inanyorder, equal_to
from mock import ANY, Mock, sentinel

from xivo_auth import token, extensions, BaseAuthenticationBackend


def later(expiration):
    delta = timedelta(seconds=expiration)
    return (datetime.now() + delta).isoformat()


class AnyUUID(object):

    def __eq__(self, other):
        try:
            uuid.UUID(other)
            return True
        except ValueError:
            return False

    def __ne__(self, other):
        return not self == other


ANY_UUID = AnyUUID()


class TestManager(unittest.TestCase):

    def setUp(self):
        self.config = {'default_token_lifetime': sentinel.default_expiration_delay}
        self.storage = Mock(token.Storage)
        extensions.celery = self.celery = Mock()
        self.manager = token.Manager(self.config, self.storage, self.celery)

    def _new_backend_mock(self, auth_id=None, uuid=None):
        get_ids = Mock(return_value=(auth_id or sentinel.auth_id,
                                     uuid or sentinel.uuid))
        return Mock(BaseAuthenticationBackend, get_ids=get_ids)

    def test_remove_token(self):
        token_id = 'my-token'
        self.manager._get_token_hash = Mock()

        self.manager.remove_token(token_id)

        self.celery.control.revoke.assert_called_once_with(self.manager._get_token_hash.return_value)
        self.storage.remove_token.assert_called_once_with(token_id)


class TestToken(unittest.TestCase):

    def setUp(self):
        self.id_ = 'the-token-id'
        self.auth_id = 'the-auth-id'
        self.xivo_user_uuid = 'the-user-uuid'
        self.xivo_uuid = 'the-xivo-uuid'
        self.issued_at = 1480011471.53537
        self.expires_at = 1480011513.53537
        self.acls = ['confd']
        self.token = token.Token(
            self.id_,
            auth_id=self.auth_id,
            xivo_user_uuid=self.xivo_user_uuid,
            xivo_uuid=self.xivo_uuid,
            issued_t=self.issued_at,
            expire_t=self.expires_at,
            acls=self.acls)
        self.utc_issued_at = '2016-11-24T18:17:51.535370'
        self.utc_expires_at = '2016-11-24T18:18:33.535370'

    def test_to_consul(self):
        expected = {
            'token': self.id_,
            'auth_id': self.auth_id,
            'xivo_uuid': self.xivo_uuid,
            'issued_at': ANY,
            'expires_at': ANY,
            'xivo_user_uuid': self.xivo_user_uuid,
            'utc_expires_at': self.utc_expires_at,
            'utc_issued_at': self.utc_issued_at,
            'acls': ['confd'],
        }

        assert_that(self.token.to_consul(), equal_to(expected))

    def test_matches_required_acls_when_user_acl_ends_with_hashtag(self):
        self.token.acls = ['foo.bar.#']

        assert_that(self.token.matches_required_acl('foo.bar'), equal_to(False))
        assert_that(self.token.matches_required_acl('foo.bar.toto'))
        assert_that(self.token.matches_required_acl('foo.bar.toto.tata'))
        assert_that(self.token.matches_required_acl('other.bar.toto'), equal_to(False))

    def test_matches_required_acls_when_user_acl_has_not_special_character(self):
        self.token.acls = ['foo.bar.toto']

        assert_that(self.token.matches_required_acl('foo.bar.toto'))
        assert_that(self.token.matches_required_acl('foo.bar.toto.tata'), equal_to(False))
        assert_that(self.token.matches_required_acl('other.bar.toto'), equal_to(False))

    def test_matches_required_acls_when_user_acl_has_asterisks(self):
        self.token.acls = ['foo.*.*']

        assert_that(self.token.matches_required_acl('foo.bar.toto'))
        assert_that(self.token.matches_required_acl('foo.bar.toto.tata'), equal_to(False))
        assert_that(self.token.matches_required_acl('other.bar.toto'), equal_to(False))

    def test_matches_required_acls_with_multiple_acls(self):
        self.token.acls = ['foo', 'foo.bar.toto', 'other.#']

        assert_that(self.token.matches_required_acl('foo'))
        assert_that(self.token.matches_required_acl('foo.bar'), equal_to(False))
        assert_that(self.token.matches_required_acl('foo.bar.toto'))
        assert_that(self.token.matches_required_acl('foo.bar.toto.tata'), equal_to(False))
        assert_that(self.token.matches_required_acl('other.bar.toto'))

    def test_matches_required_acls_when_user_acl_has_hashtag_in_middle(self):
        self.token.acls = ['foo.bar.#.titi']

        assert_that(self.token.matches_required_acl('foo.bar'), equal_to(False))
        assert_that(self.token.matches_required_acl('foo.bar.toto'), equal_to(False))
        assert_that(self.token.matches_required_acl('foo.bar.toto.tata'), equal_to(False))
        assert_that(self.token.matches_required_acl('foo.bar.toto.tata.titi'))

    def test_matches_required_acls_when_user_acl_ends_with_me(self):
        self.token.acls = ['foo.#.me']
        self.token.auth_id = '123'

        assert_that(self.token.matches_required_acl('foo.bar'), equal_to(False))
        assert_that(self.token.matches_required_acl('foo.bar.me'), equal_to(True))
        assert_that(self.token.matches_required_acl('foo.bar.123'))
        assert_that(self.token.matches_required_acl('foo.bar.toto.me'))
        assert_that(self.token.matches_required_acl('foo.bar.toto.123'))
        assert_that(self.token.matches_required_acl('foo.bar.toto.me.titi'), equal_to(False))
        assert_that(self.token.matches_required_acl('foo.bar.toto.123.titi'), equal_to(False))

    def test_matches_required_acls_when_user_acl_has_me_in_middle(self):
        self.token.acls = ['foo.#.me.bar']
        self.token.auth_id = '123'

        assert_that(self.token.matches_required_acl('foo.bar.123'), equal_to(False))
        assert_that(self.token.matches_required_acl('foo.bar.me'), equal_to(False))
        assert_that(self.token.matches_required_acl('foo.bar.123.bar'))
        assert_that(self.token.matches_required_acl('foo.bar.me.bar'), equal_to(True))
        assert_that(self.token.matches_required_acl('foo.bar.toto.123.bar'))
        assert_that(self.token.matches_required_acl('foo.bar.toto.me.bar'))

    def test_is_expired_when_time_is_in_the_future(self):
        self.token.expire_t = time.time() + 60

        self.assertFalse(self.token.is_expired())

    def test_is_expired_when_time_is_in_the_past(self):
        self.token.expire_t = time.time() - 60

        self.assertTrue(self.token.is_expired())

    def test_is_expired_when_no_expiration(self):
        self.token.expire_t = None

        self.assertFalse(self.token.is_expired())


class TestStorage(unittest.TestCase):

    expiration = 42

    def setUp(self):
        self.token_id = 'tok-id'
        self.auth_id = 'the-auth-id'
        self.issued_t = time.time()
        self.expire_t = self.issued_t + self.expiration
        self.consul = Mock()
        self.storage = token.Storage(self.consul)

    def test_get_token(self):
        token_id = '12345678-1234-5678-1234-567812345678'
        raw_token = json.dumps({'token': token_id,
                                'auth_id': '',
                                'xivo_user_uuid': '',
                                'issued_at': '',
                                'expires_at': '',
                                'utc_issued_at': '2016-11-24T13:18:33.535370',
                                'utc_expires_at': '2016-11-24T13:18:33.535370',
                                'acls': []})
        self.consul.kv.get.return_value = 42, {'Key': 'xivo/xivo-auth/tokens/12345678-1234-5678-1234-567812345678',
                                               'Value': raw_token}

        token = self.storage.get_token(token_id)

        assert_that(token.token, equal_to(token_id))
        self.consul.kv.get.assert_called_once_with('xivo/xivo-auth/tokens/12345678-1234-5678-1234-567812345678')

    def test_create_token(self):
        token_payload = self.new_payload(self.auth_id, issued_t=self.issued_t)

        t = self.storage.create_token(token_payload)

        assert_that(t.token, equal_to(ANY_UUID))
        expected = {'token': t.token,
                    'auth_id': self.auth_id,
                    'xivo_user_uuid': None,
                    'xivo_uuid': None,
                    'issued_at': ANY,
                    'utc_issued_at': ANY,
                    'utc_expires_at': ANY,
                    'expires_at': ANY,
                    'acls': []}
        self.assert_kv_put_json('xivo/xivo-auth/tokens/{}'.format(t.token), expected)

    def test_remove_token(self):
        token_id = '12345678-1234-5678-1234-567812345678'
        self.consul.kv.get.return_value = (42, None)

        self.storage.remove_token(token_id)

        self.consul.kv.delete.assert_called_once_with('xivo/xivo-auth/tokens/12345678-1234-5678-1234-567812345678',
                                                      recurse=True)

    @staticmethod
    def new_payload(auth_id,
                    xivo_user_uuid=None,
                    xivo_uuid=None,
                    issued_t=None,
                    expire_t=None,
                    acls=None):
        return token.TokenPayload(auth_id, xivo_user_uuid, xivo_uuid, issued_t,
                                  expire_t, acls)

    def assert_kv_put_json(self, expected_path, expected_value):
        raw_calls = self.consul.kv.put.call_args_list
        calls = [(path, json.loads(value)) for path, value in [args for args, kwargs in raw_calls]]
        assert_that(calls, contains_inanyorder((expected_path, expected_value)))
