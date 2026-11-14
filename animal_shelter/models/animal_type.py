from odoo import api, models, fields

class AnimalType(models.Model):
    _name="animal.type"
    _description="Animal Types"

    name=fields.Char(string="Animal Type",
    required=True)

    _unique_animal_type = models.Constraint("UNIQUE(name)","The animal type must be unique")
    