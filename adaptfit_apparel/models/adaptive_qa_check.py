# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AdaptiveQaCheck(models.Model):
    _name = 'adaptive.qa.check'
    _description = 'Clinical Fitting & Discharge QA Checklist'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string="QA Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    order_id = fields.Many2one('adaptive.order', string="Adaptive Order", required=True, tracking=True)
    patient_ref = fields.Char(string="Patient Ref", related="order_id.patient_ref", store=True)
    artisan_id = fields.Many2one('res.users', string="Artisan", related="order_id.artisan_id", store=True)
    inspector_id = fields.Many2one('res.users', string="Clinical Inspector", default=lambda self: self.env.user)
    check_date = fields.Datetime(string="Inspection Date", default=fields.Datetime.now)
    state = fields.Selection([
        ('pending', 'Pending Audit'),
        ('passed', 'Passed Clinical QA'),
        ('rework', 'Rework Needed'),
    ], string="QA Status", default='pending', tracking=True)

    # 4-Point Clinical Quality Checklist
    tactile_seam_audit = fields.Boolean(string="Tactile Seam Audit (Zero Chafing)")
    magnetic_polarity_test = fields.Boolean(string="Magnetic Polarity & One-Handed Snap")
    port_access_clearance = fields.Boolean(string="Port Access Clearance Verified")
    asymmetric_tolerance_ok = fields.Boolean(string="Asymmetric Dimension Tolerance (±0.25 in)")

    rework_reason = fields.Text(string="Defect / Rework Instructions")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('adaptive.qa.check') or _('New')
        return super().create(vals_list)

    def action_pass_qa(self):
        for rec in self:
            if not (rec.tactile_seam_audit and rec.asymmetric_tolerance_ok):
                raise UserError(_("Please verify at least Tactile Seam Audit and Asymmetric Dimension Tolerance before passing QA."))
            rec.state = 'passed'
            rec.order_id.message_post(body=_("Clinical QA Checklist <b>%s</b> PASSED.") % rec.name)

    def action_flag_rework(self):
        for rec in self:
            rec.state = 'rework'
            rec.order_id.state = 'stitching'
            rec.order_id.message_post(
                body=_("⚠️ Clinical QA <b>%s</b> flagged REWORK NEEDED: %s") % (
                    rec.name, rec.rework_reason or _('See QA sheet')
                )
            )
