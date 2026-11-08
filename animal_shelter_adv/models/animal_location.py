from odoo import fields,models

class AnimalLocation(models.Model):
    _inherit = "animal.location"

    cleaner_user_id = fields.Many2one('res.users', string = "Responsible Cleaner")