# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AdaptiveArtisanSettlement(models.Model):
    _name = 'adaptive.artisan.settlement'
    _description = 'Artisan Piece-Rate Settlement Ledger'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string="Settlement Ref",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    artisan_id = fields.Many2one('res.users', string="Master Artisan", required=True, tracking=True)
    artisan_code = fields.Char(string="Artisan Code", related="artisan_id.artisan_identifier", store=True)
    date_from = fields.Date(string="Period From", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="Period To", required=True, default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Approved'),
        ('paid', 'Paid'),
    ], string="Status", default='draft', tracking=True)

    order_ids = fields.Many2many('adaptive.order', string="Completed Adaptive Orders")
    completed_count = fields.Integer(string="Orders Completed", compute="_compute_payout", store=True)
    base_payout = fields.Monetary(string="Base Piece-Rate Payout", compute="_compute_payout", store=True)
    complexity_bonus = fields.Monetary(string="Medical Complexity Bonus", default=0.0)
    defect_penalty = fields.Monetary(string="Rework Deductions", default=0.0)
    total_payout = fields.Monetary(string="Net Weekly Payout", compute="_compute_payout", store=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    @api.depends('order_ids', 'order_ids.piece_rate_fee', 'complexity_bonus', 'defect_penalty')
    def _compute_payout(self):
        for rec in self:
            rec.completed_count = len(rec.order_ids)
            base = sum(rec.order_ids.mapped('piece_rate_fee'))
            rec.base_payout = base
            rec.total_payout = max(0.0, base + (rec.complexity_bonus or 0.0) - (rec.defect_penalty or 0.0))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('adaptive.artisan.settlement') or _('New')
        return super().create(vals_list)

    def action_fetch_completed_orders(self):
        for rec in self:
            orders = self.env['adaptive.order'].search([
                ('artisan_id', '=', rec.artisan_id.id),
                ('state', 'in', ('fitting', 'delivered')),
            ])
            rec.order_ids = [(6, 0, orders.ids)]
            # Auto-calculate complexity bonus for rush or multi-accommodation orders
            bonus = 0.0
            for o in orders:
                if o.urgency_level == 'clinical_rush':
                    bonus += 15.0
                if o.has_port_access_zip and o.has_flatlock_frictionless:
                    bonus += 10.0
            rec.complexity_bonus = bonus

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_mark_paid(self):
        self.write({'state': 'paid'})
