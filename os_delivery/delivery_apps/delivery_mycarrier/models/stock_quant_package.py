from odoo import fields, models


class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    mycarrier_commodity_class = fields.Char('MyCarrier Freight Class')
    mycarrier_commodity_nmfc = fields.Char('MyCarrier NMFC')
    mycarrier_commodity_sub = fields.Char('MyCarrier NMFC Sub')
    mycarrier_package_count = fields.Integer('MyCarrier Package Count', default=1)
    mycarrier_quote_build_mode = fields.Char(compute='_compute_mycarrier_quote_build_mode')

    def _compute_mycarrier_quote_build_mode(self):
        mode = self.env['mycarrier.instance']._get_quote_build_mode()
        for package in self:
            package.mycarrier_quote_build_mode = mode
