from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    mycarrier_commodity_class = fields.Char('MyCarrier Freight Class')
    mycarrier_commodity_nmfc = fields.Char('MyCarrier NMFC')
    mycarrier_commodity_sub = fields.Char('MyCarrier NMFC Sub')
    mycarrier_quote_build_mode = fields.Char(compute='_compute_mycarrier_quote_build_mode')

    def _compute_mycarrier_quote_build_mode(self):
        mode = self.env['mycarrier.instance']._get_quote_build_mode()
        for product in self:
            product.mycarrier_quote_build_mode = mode
