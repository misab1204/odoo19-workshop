# -*- coding: utf-8 -*-
import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AdaptiveOrder(models.Model):
    _name = 'adaptive.order'
    _description = 'Adaptive Medical Garment Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'urgency_level desc, create_date desc'

    name = fields.Char(
        string="Order Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    partner_id = fields.Many2one(
        'res.partner',
        string="Patient",
        required=True,
        tracking=True,
    )
    patient_ref = fields.Char(
        string="Patient Ref ID",
        related="partner_id.patient_identifier",
        store=True,
        readonly=True,
    )
    state = fields.Selection([
        ('draft', 'Intake & Sizing'),
        ('pattern', 'Pattern & Cutting'),
        ('stitching', 'Artisan Assembly'),
        ('transit', 'Clinic Transit'),
        ('fitting', 'Clinical Fitting Trial'),
        ('delivered', 'Delivered & Settled'),
        ('cancel', 'Cancelled'),
    ], string="Production Stage", default='draft', tracking=True)

    urgency_level = fields.Selection([
        ('standard', 'Standard Schedule'),
        ('urgent', 'Urgent (Fitting < 48h)'),
        ('clinical_rush', 'Clinical Rush (Surgery / Chemo Date)'),
    ], string="Urgency Priority", default='standard', tracking=True)

    target_date = fields.Date(
        string="Required Clinical Date",
        required=True,
        default=fields.Date.context_today,
    )

    # Garment Type & Material Specification
    garment_type = fields.Selection([
        ('shirt_top', 'Adaptive Shirt / Blouse'),
        ('trousers_pant', 'Adaptive Seated / Split Pants'),
        ('post_op_recovery', 'Full Recovery Romper / Suit'),
        ('compression_sleeve', 'Custom Pressure / Compression Sleeve'),
        ('outerwear_jacket', 'Easy-On Outerwear / Coat'),
    ], string="Garment Category", required=True, default='shirt_top')

    fabric_id = fields.Many2one(
        'product.product',
        string="Sustainable Fabric",
        required=True,
        domain="[('is_sustainable_fabric', '=', True)]",
    )
    calculated_yardage = fields.Float(
        string="Required Fabric (m)",
        compute="_compute_yardage",
        store=True,
    )
    eco_carbon_saved_kg = fields.Float(
        string="CO2 Prevented (kg)",
        compute="_compute_yardage",
        store=True,
    )
    eco_water_saved_l = fields.Float(
        string="Water Saved (L)",
        compute="_compute_yardage",
        store=True,
    )

    # Clinical Advisor Input
    clinical_notes_input = fields.Text(
        string="Clinical Notes / AI Advisor Input",
        help="Enter freeform clinical notes (e.g., 'pacemaker on upper left chest, reduced grip in left hand, burn graft').",
    )
    advisor_summary = fields.Text(
        string="Clinical Advisor Recommendations",
        readonly=True,
    )

    # Active Medical Accommodations for this Garment
    has_magnetic_placket = fields.Boolean(string="Magnetic Placket (One-Handed)")
    has_port_access_zip = fields.Boolean(string="Concealed 2-Way Port Zipper")
    port_location = fields.Selection([
        ('chest_right', 'Right Collarbone / Chest'),
        ('chest_left', 'Left Collarbone / Chest'),
        ('arm_right', 'Right Bicep / Arm'),
        ('arm_left', 'Left Bicep / Arm'),
        ('abdomen', 'Abdominal Catheter'),
    ], string="Port Access Coordinates")
    has_prosthetic_reinforcement = fields.Boolean(string="Abrasion-Proof Socket Shield")
    has_flatlock_frictionless = fields.Boolean(string="Zero-Friction Flat-Lock Seams")
    has_high_seated_rise = fields.Boolean(string="Seated Ergonomic High-Rise Back")
    has_tagless_label = fields.Boolean(string="Strictly Tag-Less Heat Label", default=True)

    # Snapshot of Measurements Applied to this Order
    order_neck = fields.Float(string="Neck (in)")
    order_shoulder = fields.Float(string="Shoulder (in)")
    order_arm_left = fields.Float(string="Left Arm (in)")
    order_arm_right = fields.Float(string="Right Arm (in)")
    order_stump_left = fields.Float(string="Left Limb Circ. (in)")
    order_stump_right = fields.Float(string="Right Limb Circ. (in)")
    order_chest = fields.Float(string="Chest (in)")
    order_waist = fields.Float(string="Waist (in)")
    order_inseam_left = fields.Float(string="Left Inseam (in)")
    order_inseam_right = fields.Float(string="Right Inseam (in)")
    order_seated_rise = fields.Float(string="Seated Rear Rise (in)")

    # Blueprint Coordinate Mapping
    blueprint_marker_json = fields.Text(
        string="Coordinate Pinpoints JSON",
        default='[]',
    )
    blueprint_svg_preview = fields.Html(
        string="Anatomical Blueprint",
        compute="_compute_blueprint_svg",
        sanitize=False,
    )

    # Workshop & Artisan Allocation
    artisan_id = fields.Many2one(
        'res.users',
        string="Assigned Master Artisan",
        tracking=True,
    )
    artisan_code = fields.Char(
        string="Artisan Code",
        related="artisan_id.artisan_identifier",
        store=True,
    )
    piece_rate_fee = fields.Float(string="Artisan Compensation (AED)", default=45.0)
    clinic_dispatch_batch = fields.Char(string="Transit Batch Ref", readonly=True, copy=False)

    # QA Links
    qa_check_ids = fields.One2many('adaptive.qa.check', 'order_id', string="QA Checks")
    qa_passed = fields.Boolean(string="QA Passed", compute="_compute_qa_passed", store=True)

    # Financial Ledger
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    total_amount = fields.Monetary(string="Total Garment Price", required=True, default=450.0)
    advance_deposit = fields.Monetary(string="Advance / Copay Paid", required=True, default=225.0)
    balance_due = fields.Monetary(
        string="Remaining Balance",
        compute="_compute_balance",
        store=True,
    )

    @api.depends('qa_check_ids.state')
    def _compute_qa_passed(self):
        for rec in self:
            rec.qa_passed = any(qa.state == 'passed' for qa in rec.qa_check_ids)

    @api.depends('total_amount', 'advance_deposit')
    def _compute_balance(self):
        for rec in self:
            rec.balance_due = max(0.0, rec.total_amount - rec.advance_deposit)

    @api.depends(
        'order_arm_left', 'order_arm_right',
        'order_inseam_left', 'order_inseam_right',
        'garment_type', 'fabric_id',
    )
    def _compute_yardage(self):
        for rec in self:
            max_arm = max(rec.order_arm_left or 0.0, rec.order_arm_right or 0.0, 24.0)
            max_leg = max(rec.order_inseam_left or 0.0, rec.order_inseam_right or 0.0, 30.0)
            if rec.garment_type in ('shirt_top', 'compression_sleeve'):
                meters = (max_arm * 2.2 + 20.0) / 100.0
            elif rec.garment_type == 'post_op_recovery':
                meters = ((max_arm + max_leg) * 1.8 + 30.0) / 100.0
            else:
                meters = (max_leg * 2.2 + 25.0) / 100.0
            meters = round(meters, 2)
            co2_rate = rec.fabric_id.product_tmpl_id.eco_co2_saved_per_m or 1.85
            water_rate = rec.fabric_id.product_tmpl_id.eco_water_saved_per_m or 270.0
            rec.calculated_yardage = meters
            rec.eco_carbon_saved_kg = round(meters * co2_rate, 2)
            rec.eco_water_saved_l = round(meters * water_rate, 1)

    @api.depends(
        'blueprint_marker_json', 'has_port_access_zip', 'port_location',
        'has_prosthetic_reinforcement', 'has_flatlock_frictionless',
        'has_magnetic_placket', 'order_arm_left', 'order_arm_right',
    )
    def _compute_blueprint_svg(self):
        port_coords = {
            'chest_right': (120, 110, 'Port (Rt Chest)'),
            'chest_left': (180, 110, 'Port (Lt Chest)'),
            'arm_right': (82, 130, 'Port (Rt Arm)'),
            'arm_left': (218, 130, 'Port (Lt Arm)'),
            'abdomen': (150, 175, 'Abdominal Port'),
        }
        for rec in self:
            markers = []
            try:
                markers = json.loads(rec.blueprint_marker_json or '[]')
            except Exception:
                markers = []

            pins_svg = ''
            if rec.has_port_access_zip and rec.port_location in port_coords:
                cx, cy, label = port_coords[rec.port_location]
                pins_svg += (
                    f'<circle cx="{cx}" cy="{cy}" r="8" fill="#e53935" stroke="#fff" stroke-width="2"/>'
                    f'<text x="{cx + 12}" y="{cy + 4}" font-size="10" fill="#b71c1c" font-weight="bold">{label}</text>'
                )

            if rec.has_magnetic_placket:
                for my in (100, 125, 150, 175):
                    pins_svg += f'<rect x="146" y="{my}" width="8" height="8" rx="2" fill="#1e88e5"/>'
                pins_svg += '<text x="158" y="108" font-size="9" fill="#0d47a1" font-weight="bold">Magnetic Placket</text>'

            for m in markers:
                m_type = m.get('type', 'port')
                mx = int(m.get('x', 150))
                my = int(m.get('y', 130))
                mlabel = str(m.get('label', 'Marker'))
                color = '#e53935' if m_type == 'port' else ('#fbc02d' if m_type == 'sensitive' else '#1e88e5')
                pins_svg += (
                    f'<circle cx="{mx}" cy="{my}" r="7" fill="{color}" stroke="#222" stroke-width="1.5"/>'
                    f'<text x="{mx + 10}" y="{my + 4}" font-size="10" fill="#222">{mlabel}</text>'
                )

            left_arm_lbl = f'{rec.order_arm_left:.1f}"' if rec.order_arm_left else '--'
            right_arm_lbl = f'{rec.order_arm_right:.1f}"' if rec.order_arm_right else '--'
            seam_stroke = '#fb8c00' if rec.has_flatlock_frictionless else '#546e7a'
            seam_dash = 'stroke-dasharray="4,3"' if rec.has_flatlock_frictionless else ''

            rec.blueprint_svg_preview = f"""
            <div style="background:#f8fafc;border:1px solid #cbd5e1;border-radius:10px;padding:12px;text-align:center;">
                <div style="font-weight:700;color:#0f172a;margin-bottom:6px;font-size:13px;">
                    Asymmetric Anatomical Blueprint (Front Vector)
                </div>
                <svg viewBox="0 0 300 260" width="280" height="240" xmlns="http://www.w3.org/2000/svg">
                    <!-- Head / Collar -->
                    <circle cx="150" cy="40" r="20" fill="#e2e8f0" stroke="#64748b" stroke-width="2"/>
                    <!-- Torso -->
                    <path d="M105,70 L195,70 L188,205 L112,205 Z" fill="#ffffff" stroke="{seam_stroke}" stroke-width="2.5" {seam_dash}/>
                    <!-- Right Sleeve (viewer left) -->
                    <path d="M105,70 L65,145 L85,155 L110,100" fill="#f1f5f9" stroke="{seam_stroke}" stroke-width="2" {seam_dash}/>
                    <!-- Left Sleeve (viewer right) -->
                    <path d="M195,70 L235,145 L215,155 L190,100" fill="#f1f5f9" stroke="{seam_stroke}" stroke-width="2" {seam_dash}/>
                    <!-- Arm Length Callouts -->
                    <text x="20" y="150" font-size="11" fill="#334155" font-weight="bold">Rt: {right_arm_lbl}</text>
                    <text x="238" y="150" font-size="11" fill="#334155" font-weight="bold">Lt: {left_arm_lbl}</text>
                    {pins_svg}
                </svg>
                <div style="font-size:11px;color:#475569;margin-top:4px;">
                    🔴 Port Access &nbsp;|&nbsp; 🟡 Graft / Sensitive Zone &nbsp;|&nbsp; 🔵 Reinforcement / Magnets
                </div>
            </div>
            """

    def _build_clinical_recommendations(self):
        self.ensure_one()
        notes = (self.clinical_notes_input or '').lower()
        p = self.partner_id
        recs = []

        if p.condition_burn_graft or p.pref_flatlock_seams or any(k in notes for k in ('burn', 'graft', 'scar', 'friction', 'sensitive')):
            self.has_flatlock_frictionless = True
            self.has_tagless_label = True
            recs.append("Flat-lock frictionless seams & tagless heat-transfer labels enabled.")

        if p.condition_stroke_mobility or p.pref_magnetic_closures or any(k in notes for k in ('stroke', 'grip', 'hemiplegia', 'dexterity', 'one-hand', 'magnet')):
            self.has_magnetic_placket = True
            recs.append("One-handed magnetic placket with faux buttons enabled.")

        if p.condition_medical_port or any(k in notes for k in ('port', 'chemo', 'dialysis', 'catheter', 'pacemaker', 'picc')):
            self.has_port_access_zip = True
            if 'left' in notes:
                self.port_location = 'chest_left'
            elif 'right' in notes:
                self.port_location = 'chest_right'
            elif not self.port_location:
                self.port_location = 'chest_right'
            recs.append(f"Concealed 2-way port zipper enabled ({self.port_location}).")

        if p.condition_amputation or any(k in notes for k in ('amput', 'bionic', 'prosthe', 'socket', 'stump')):
            self.has_prosthetic_reinforcement = True
            recs.append("Abrasion-proof socket shield reinforcement enabled.")

        if p.condition_wheelchair or any(k in notes for k in ('wheelchair', 'seated', 'pressure')):
            self.has_high_seated_rise = True
            recs.append("Seated ergonomic high-rise back enabled.")

        if not self.fabric_id:
            bamboo = self.env['product.product'].search([('is_sustainable_fabric', '=', True)], limit=1)
            if bamboo:
                self.fabric_id = bamboo

        self.advisor_summary = "\n".join(f"• {r}" for r in recs) if recs else "Standard adaptive configuration."

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if not self.partner_id:
            return
        p = self.partner_id
        self.order_neck = p.meas_neck
        self.order_shoulder = p.meas_shoulder
        self.order_arm_left = p.meas_arm_left
        self.order_arm_right = p.meas_arm_right
        self.order_stump_left = p.meas_stump_circ_left
        self.order_stump_right = p.meas_stump_circ_right
        self.order_chest = p.meas_chest
        self.order_waist = p.meas_waist
        self.order_inseam_left = p.meas_inseam_left
        self.order_inseam_right = p.meas_inseam_right
        self.order_seated_rise = p.meas_seated_rise
        self.has_tagless_label = p.pref_tagless_only
        self._build_clinical_recommendations()

    @api.onchange('clinical_notes_input')
    def _onchange_clinical_notes_input(self):
        if self.clinical_notes_input:
            self._build_clinical_recommendations()

    def action_run_clinical_advisor(self):
        for rec in self:
            rec._build_clinical_recommendations()

    def _append_marker(self, marker_type, x, y, label):
        self.ensure_one()
        try:
            markers = json.loads(self.blueprint_marker_json or '[]')
        except Exception:
            markers = []
        markers.append({'type': marker_type, 'x': x, 'y': y, 'label': label})
        self.blueprint_marker_json = json.dumps(markers)

    def action_add_port_marker(self):
        for rec in self:
            rec._append_marker('port', 120, 110, 'Port Access')

    def action_add_sensitive_marker(self):
        for rec in self:
            rec._append_marker('sensitive', 170, 155, 'Graft Sensitive')

    def action_add_reinforcement_marker(self):
        for rec in self:
            rec._append_marker('reinforce', 218, 128, 'Socket Shield')

    def action_clear_markers(self):
        for rec in self:
            rec.blueprint_marker_json = '[]'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('adaptive.order') or _('New')
        return super().create(vals_list)

    # Production Stage Transitions
    def action_start_pattern(self):
        self.write({'state': 'pattern'})

    def action_start_stitching(self):
        self.write({'state': 'stitching'})

    def action_send_transit(self):
        self.write({'state': 'transit'})

    def action_start_fitting(self):
        self.write({'state': 'fitting'})

    def action_deliver_settle(self):
        self.write({'state': 'delivered'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_prepare_dispatch_batch(self):
        if not self:
            raise UserError(_("Select at least one order to dispatch."))
        batch_ref = self.env['ir.sequence'].next_by_code('adaptfit.batch') or 'BATCH-001'
        for rec in self:
            rec.write({
                'state': 'transit',
                'clinic_dispatch_batch': batch_ref,
            })
            rec.message_post(body=_("Dispatched to Clinic in Transit Batch <b>%s</b>.") % batch_ref)

    def action_open_artisan_chat(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/adaptfit/artisan/{self.id}',
            'target': 'new',
        }
