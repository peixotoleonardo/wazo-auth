# -*- coding: utf-8 -*-
# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from flask import request
from wazo_auth import exceptions, http

from .exceptions import EmailAlreadyConfirmedException
from .schemas import new_email_put_schema

logger = logging.getLogger(__name__)

AdminUserEmailPutSchema = new_email_put_schema('admin')


class _EmailUpdate(http.AuthResource):

    def __init__(self, user_service):
        self.user_service = user_service

    def put(self, user_uuid):
        args, errors = self.EmailPutSchema().load(request.get_json())
        if errors:
            raise exceptions.EmailUpdateException(errors)

        logger.debug('updating user %s emails: %s', user_uuid, args)
        result = self.user_service.update_emails(user_uuid, args)
        return result, 200


class AdminUserEmailUpdate(_EmailUpdate):

    EmailPutSchema = new_email_put_schema('admin')

    @http.required_acl('auth.admin.users.{user_uuid}.emails.edit')
    def put(self, user_uuid):
        return super(AdminUserEmailUpdate, self).put(user_uuid)


class UserEmailUpdate(_EmailUpdate):

    EmailPutSchema = new_email_put_schema('user')

    @http.required_acl('auth.users.{user_uuid}.emails.edit')
    def put(self, user_uuid):
        return super(UserEmailUpdate, self).put(user_uuid)


class UserEmailConfirm(http.AuthResource):

    def __init__(self, email_service, user_service):
        self.email_service = email_service
        self.user_service = user_service

    @http.required_acl('auth.users.{user_uuid}.emails.{email_uuid}.confirm.read')
    def get(self, user_uuid, email_uuid):
        logger.debug('sending a new email confirmation user_uuid: %s email_uuid: %s',
                     user_uuid, email_uuid)

        user = self.user_service.get_user(user_uuid)
        email = self._get_email_details(user, email_uuid)

        username, uuid, address = user['username'], str(email_uuid), email['address']
        self.email_service.send_confirmation_email(username, uuid, address)

        return '', 204

    def _get_email_details(self, user, email_uuid):
        email = self._find_email(user['emails'], email_uuid)
        if not email:
            raise exceptions.UnknownEmailException(email_uuid)

        if email['confirmed']:
            raise EmailAlreadyConfirmedException(email_uuid)

        return email

    def _find_email(self, user_emails, email_uuid):
        for email in user_emails:
            if email['uuid'] == str(email_uuid):
                return email
        return None