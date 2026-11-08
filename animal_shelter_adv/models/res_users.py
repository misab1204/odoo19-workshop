from odoo import models, fields 

class ResUsers(models.Model):
    _inherit = "res.users"

    responsible_shelter_ids = fields.One2many(
        "animal.location", "cleaner_user_id", string="Responsible Shelters"
    )
