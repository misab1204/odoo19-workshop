from odoo import api, models, fields

class AnimalVaccination(models.Model):
    _name = "animal.vaccination"
    _description = "Animal Vaccination"

    animal_id = fields.Many2one("animals")
    vaccine_id = fields.Many2one("animal.vaccine")
    status = fields.Selection(
        selection=[
            ("not_vaccinated", "Not Vaccinated"),
            ("vaccinated", "Vaccinated")
        ],
        string="Vaccination Status",
        default="not_vaccinated",
        required=True
    )

    def vaccinated_action(self):
        for vaccine in self:
            vaccine.status = "vaccinated"