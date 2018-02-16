# -*- coding: utf-8 -*-
# Copyright 2017-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo.mallow import fields
from xivo.mallow import validate
from wazo_auth.schemas import BaseSchema


class UserPostSchema(BaseSchema):

    uuid = fields.UUID()
    username = fields.String(validate=validate.Length(min=1, max=128), required=True)
    password = fields.String(validate=validate.Length(min=1))
    email_address = fields.Email()
    firstname = fields.String(missing=None, allow_none=True)
    lastname = fields.String(missing=None, allow_none=True)


class UserPutSchema(BaseSchema):

    username = fields.String(validate=validate.Length(min=1, max=128), required=True)
    firstname = fields.String(missing=None, allow_none=True)
    lastname = fields.String(missing=None, allow_none=True)


class ChangePasswordSchema(BaseSchema):

    old_password = fields.String(validate=validate.Length(min=1), required=True)
    new_password = fields.String(validate=validate.Length(min=1), required=True)
