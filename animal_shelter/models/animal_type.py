from odoo import api, models, fields

class AnimalType(models.Model):
    _name = "animal.type"
    _description = "Animal Types"

    name = fields.Char(string = "Animal Type", required = True)