from odoo import api, models, fields

class Animals(models.Model):
    _name = "animals"
    _description = "Animals"

    name = fields.Char(required=True)
    picture = fields.Image()
    birth_date = fields.Date()
    description = fields.Text()
    weight = fields.Float()
    arrival_time = fields.Datetime()
    feeding_time = fields.Float()
    all_vaccinated = fields.Boolean(string="All Vaccinations Completed", compute = "_compute_all_vaccinated", store = True)

    diet = fields.Selection(selection=[("omnivore", "Omnivore"), ("carnivore", "Carnivore"), ("herbivore", "Herbivore")])

    gender = fields.Selection(selection=[("male", "Male"), ("female", "Female")])

    animal_type_id = fields.Many2one("animal.type")
    sponsor_id = fields.Many2one("res.partner")
    location_id = fields.Many2one("animal.location", string="shelter Location")
    animal_vaccination_ids = fields.One2many("animal.vaccination", "animal_id")
    animal_status = fields.Selection(
        selection=[
            ("not_received", "Not Received"),
            ("at_the_shelter", "At the Shelter"),
            ("released", "Released")
        ],
        default="not_received"
    )

    _check_animal_weight = models.Constraint("CHECK(weight > 0)", "Animal weight must be greater than 0!")
    
    def at_center(self):
        for record in self:
            if record.animal_status == "released":
                raise UserError("A released animal cannot be returned to the center U FOOL!!")
        record.animal_status = "at_the_shelter"

    def release_animal(self):
        for record in self:
            if record.animal_status == "not_recieved":
                raise UserError("An animal cannot be released if it hasnt reached the shelter POTTA!!")
        record.animal_status = "released"


    @api.depends("animal_vaccination_ids.status")
    def _compute_all_vaccinated(self):
        for animal in self:
            animal.all_vaccinated = bool(animal.animal_vaccination_ids) and all(vaccination.status == "vaccinated" for vaccination in animal.animal_vaccination_ids)