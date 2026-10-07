# -*- coding: utf-8 -*-
{
    "name": "Odoo Sync Base",
    "version": "18.1.1",
    "summary": "Odoo Sync Base",
    "description": """Odoo Sync Base""",
    "category": "Customization",
    "author": "Syncoria Inc.",
    "website": "https://www.syncoria.com",
    "company": "Syncoria Inc.",
    "maintainer": "Syncoria Inc.",
    "depends": [
        "base",
        "mail",
        "sale_management",
        "account"
    ],
    'images': [
            'static/description/banner.gif',
        ],
    "data": [
        "security/omniaccount_security.xml",
        "security/ir.model.access.csv",
        "views/omni_account.xml",
    ],
    "price": 5000,
    "currency": "USD",
    "license": "OPL-1",
    "support": "support@syncoria.com",
    "installable": True,
    "application": False,
    "auto_install": False,
    "pre_init_hook": "pre_init_check",
}
