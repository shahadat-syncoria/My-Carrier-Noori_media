from odoo import api, fields, models
from odoo.exceptions import ValidationError
import copy
from logging import getLogger
import requests
from requests.auth import HTTPBasicAuth
import json
_logger = getLogger(__name__)


class MycarrierInstance(models.Model):
    _name = 'mycarrier.product.mappings'
    _description = 'MyCarrier Product Mappings'

    product_id = fields.Many2one('product.product', string='Product')
    mycarrier_product_id = fields.Char(string='Product ID', required=True)
    sku = fields.Char(string='SKU', related='product_id.default_code')
    mycarrier_instance_id = fields.Many2one('mycarrier.instance')

    _sql_constraints = [
        ('product_uniq', 'unique (product_id, mycarrier_instance_id)', "Products must be unique.")
    ]
