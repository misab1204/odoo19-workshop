# -*- coding: utf-8 -*-
from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_master_artisan = fields.Boolean(string="Master Adaptive Artisan", default=False)
    artisan_identifier = fields.Char(string="Artisan Code", help="Discreet workshop code (e.g. T-02)")
