# -*- coding: utf-8 -*-
{
    "name": "Odoo Sync Delivery",
    "version": "18.1.6",
    'summary': """
        Dependency Module of Odoo Sync Base for delivery functionality""",
    'description': """
        It is the module for add delivery feature for Odoo Sync.
    """,
    # "category": "Customization",
    "author": "Syncoria Inc.",
    "website": "https://www.syncoria.com",
    "company": "Syncoria Inc.",
    "maintainer": "Syncoria Inc.",
    "license": "OPL-1",
    "support": "support@syncoria.com",
    "price": 5000,
    "currency": "USD",
    'depends': ['odoosync_base',"delivery","stock", "stock_delivery",],
    'data': [
        # Base Account 
        'views/omni_account_delivery.xml',

        # =====================================================================================
        # =============================Delivery:MyCarrier======================================
        # =====================================================================================

        'delivery_apps/delivery_mycarrier/data/data.xml',
        'delivery_apps/delivery_mycarrier/security/ir.model.access.csv',
        'delivery_apps/delivery_mycarrier/data/ir_cron_data.xml',
        'delivery_apps/delivery_mycarrier/data/ir_sequence_data.xml',
        'delivery_apps/delivery_mycarrier/views/mycarrier_instance_view.xml',
        'delivery_apps/delivery_mycarrier/views/mycarrier_webhook_view.xml',
        'delivery_apps/delivery_mycarrier/views/stock_picking_view.xml',
        'delivery_apps/delivery_mycarrier/views/product_template_view.xml',
        'delivery_apps/delivery_mycarrier/views/stock_quant_package_view.xml'
        
    ],
    "support": "support@syncoria.com",
}
