# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_adaptive_patient = fields.Boolean(string="Adaptive Apparel Patient", default=False)
    patient_identifier = fields.Char(string="Patient Ref ID", readonly=True, copy=False, default='New')

    # Medical Condition Flags (Confidential)
    condition_amputation = fields.Boolean(string="Limb Difference / Amputation")
    condition_burn_graft = fields.Boolean(string="Burn Survivor / Skin Graft")
    condition_stroke_mobility = fields.Boolean(string="Stroke / Limited Dexterity")
    condition_medical_port = fields.Boolean(string="Chemo Port / Dialysis / Catheter")
    condition_wheelchair = fields.Boolean(string="Wheelchair User (Seated Fit)")
    condition_sensory = fields.Boolean(string="Sensory Sensitive / Tactile Defense")
    medical_notes = fields.Text(string="Confidential Clinical Instructions")

    # Asymmetric Body Metrics (Inches)
    meas_neck = fields.Float(string="Neck Circumference (in)")
    meas_shoulder = fields.Float(string="Shoulder Width (in)")
    meas_arm_left = fields.Float(string="Left Arm Length (in)")
    meas_arm_right = fields.Float(string="Right Arm Length (in)")
    meas_stump_circ_left = fields.Float(string="Left Limb Circumference (in)")
    meas_stump_circ_right = fields.Float(string="Right Limb Circumference (in)")
    meas_chest = fields.Float(string="Chest / Bust (in)")
    meas_waist = fields.Float(string="Waist (in)")
    meas_hip = fields.Float(string="Hip (in)")
    meas_inseam_left = fields.Float(string="Left Inseam (in)")
    meas_inseam_right = fields.Float(string="Right Inseam (in)")
    meas_seated_rise = fields.Float(string="Seated Rear Rise (in)")

    # Permanent Accommodation Preferences
    pref_magnetic_closures = fields.Boolean(string="Always Use Magnetic Closures", default=False)
    pref_tagless_only = fields.Boolean(string="Strictly Tagless Heat Labels", default=True)
    pref_flatlock_seams = fields.Boolean(string="Strictly Flat-Lock Frictionless Seams", default=False)
    pref_bamboo_lining = fields.Boolean(string="Require Hypoallergenic Bamboo Lining", default=False)

    adaptive_order_ids = fields.One2many('adaptive.order', 'partner_id', string="Adaptive Orders")
    adaptive_order_count = fields.Integer(string="Order Count", compute="_compute_adaptive_order_count")

    @api.depends('adaptive_order_ids')
    def _compute_adaptive_order_count(self):
        for rec in self:
            rec.adaptive_order_count = len(rec.adaptive_order_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_adaptive_patient') and vals.get('patient_identifier', _('New')) == _('New'):
                vals['patient_identifier'] = self.env['ir.sequence'].next_by_code('adaptfit.patient') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_adaptive_patient'):
            for rec in self:
                if not rec.patient_identifier or rec.patient_identifier == _('New'):
                    rec.patient_identifier = self.env['ir.sequence'].next_by_code('adaptfit.patient') or _('New')
        return res

    def action_view_adaptive_orders(self):
        self.ensure_one()
        return {
            'name': _('Adaptive Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'adaptive.order',
            'view_mode': 'list,kanban,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_create_adaptive_order(self):
        self.ensure_one()
        return {
            'name': _('New Adaptive Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'adaptive.order',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_partner_id': self.id,
            },
        }
