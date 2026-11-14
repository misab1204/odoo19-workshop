from odoo import api, models, fields

class AnimalLocation(models.Model):
    _name = "animal.location"
    _description = "Animal locations in the shelter"

    name = fields.Char(string = "Shelter Locations", required = True)