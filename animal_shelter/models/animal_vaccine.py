from odoo import api, models, fields

class AnimalVaccine(models.Model):
    _name="animal.vaccine"
    _description="Animal Vaccines"

    name=fields.Char(string="Vaccine Treatment",required=True) 

    _unique_vaccine_name = models.Constraint("UNIQUE(name)","Vaccine treatments must be unique")

    