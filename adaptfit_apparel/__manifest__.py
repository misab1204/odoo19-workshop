# -*- coding: utf-8 -*-
{
    'name': 'AdaptFit ERP',
    'version': '19.0.1.0.0',
    'category': 'Healthcare/Manufacturing',
    'summary': 'Bespoke Adaptive, Medical, and Ergonomic Apparel Engine (Clinic-to-Workshop)',
    'description': """
AdaptFit ERP transforms Odoo 19 into a unified, compassionate, and technically rigorous
operating system linking clinical intake, ergonomic recommendation algorithms, asymmetric
blueprinting, zero-waste sustainable manufacturing, and a mobile-first ArtisanChat portal.
    """,
    'author': 'AdaptFit Team - Odoo Hackathon 2026',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/adaptfit_demo_data.xml',
        'data/adaptfit_demo_qa_settlement.xml',
        'views/res_partner_views.xml',
        'views/product_views.xml',
        'views/adaptive_order_views.xml',
        'views/adaptive_order_report.xml',
        'views/adaptive_qa_settlement_views.xml',
        'views/artisan_chat_templates.xml',
        'views/adaptfit_menus.xml',
    ],
    'application': True,
    'installable': True,
}
