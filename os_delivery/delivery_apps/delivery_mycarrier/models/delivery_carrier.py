from odoo import fields, models


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    mycarrier_carrier_code = fields.Char('MyCarrier Carrier Code', copy=False)
