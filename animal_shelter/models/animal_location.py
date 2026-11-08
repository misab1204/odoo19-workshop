from odoo import api, models, fields

class AnimalLocation(models.Model):
    _name = "animal.location"
    _description = "Animal Location"

    name = fields.Char(string = "Animal Location", required = True)