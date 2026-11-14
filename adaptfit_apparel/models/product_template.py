# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_sustainable_fabric = fields.Boolean(string="Sustainable Adaptive Fabric", default=False)
    fabric_certification = fields.Char(string="Eco Certification", help="e.g., GOTS Organic Bamboo, OEKO-TEX 100")
    eco_co2_saved_per_m = fields.Float(string="CO2 Prevented (kg/m)", default=1.85)
    eco_water_saved_per_m = fields.Float(string="Water Saved (L/m)", default=270.0)
