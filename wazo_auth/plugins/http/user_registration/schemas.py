# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo.mallow import fields
from xivo.mallow import validate
from wazo_auth.schemas import BaseSchema


class UserRegisterPostSchema(BaseSchema):

    username = fields.String(validate=validate.Length(min=1, max=128), required=True)
    password = fields.String(validate=validate.Length(min=1), required=True)
    email_address = fields.Email(required=True)