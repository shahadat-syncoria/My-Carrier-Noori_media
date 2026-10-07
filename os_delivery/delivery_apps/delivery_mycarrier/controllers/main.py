from odoo import http, _
from odoo.http import request
import json


class MyCarrierController(http.Controller):

    @http.route(['/mycarrier/shipment/webhook'], type='json', auth="public", csrf=False)
    def get_shipment_info(self, *args, **kw):
        if request.httprequest.data:
            data = json.loads(request.httprequest.data)
            MycarrierWebhook = request.env['mycarrier.webhook'].sudo()
            MycarrierWebhook.create({'data': data})
