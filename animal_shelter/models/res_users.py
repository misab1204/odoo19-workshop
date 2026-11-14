from odoo import models,fields
class ResUser(models.Model):
    _inherit = "res.users" 

    responisible_shelter_ids = fields.One2many(
        'animal_location','cleaner_user_id', string='Responsible Shelters'
    )
