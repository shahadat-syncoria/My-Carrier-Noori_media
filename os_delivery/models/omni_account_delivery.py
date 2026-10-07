# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import api, fields, models
import logging


_logger = logging.getLogger(__name__)

AVAILABLE_DELIVERY_TYPES = ['mycarrier']


class OmniAccountDelivery(models.Model):
    _inherit = "omni.account"

    carrier_ids = fields.One2many(
        string="Delivery Carriers",
        comodel_name="delivery.carrier",
        inverse_name="account_id",
    )

    def process_subscriptions(self, res_json):
        kwargs = super(OmniAccountDelivery, self).process_subscriptions(res_json)

        # Delivery Data Create
        self._delivery_data_creation()
        for subscription in kwargs["all_subscriptions"].get("delivery"):
            kwargs = self.process_delivery_subscriptions(kwargs, subscription)

        return kwargs

    def process_delivery_subscriptions(self, kwargs, subscription):
        """[summary]
        Args:
            res_json ([type]): [description]
        """
        service_name = subscription.get("service_name")
        if service_name not in AVAILABLE_DELIVERY_TYPES:
            _logger.info(
                "Skipping delivery creation during fetch for unavailable service: %s",
                service_name,
            )
            return kwargs

        delivery_carrier = self.env["delivery.carrier"].sudo()
        # Check exsiting service
        # domain = [("delivery_type", "=", subscription.get("service_name"))]
        domain = [("token", "=", subscription.get("service_key"))]
        existing_service = delivery_carrier.search(domain, limit=1)
        if not existing_service:
            kwargs["messages"] += "\n" + service_name.upper()

            created_val = {
                "name": service_name.upper(),
                "delivery_type": service_name,
                "company_id": self.company_id.id,
                "integration_level": "rate_and_ship",
                "omnisync_active": True,
                "account_id": self.id,
                "token": subscription.get("service_key"),
            }
            if subscription.get("service_name") == 'mycarrier':
                self.env["mycarrier.instance"].create({
                    "token": subscription.get("service_key"),
                    "name": subscription.get("service_name").upper(),
                    "account_id": self.id,
                })
                return kwargs

            try:
                created_delivery = delivery_carrier.create(created_val)
                _logger.info(created_delivery)
            except Exception as e:
                _logger.info("Payment Method Creation Failed")
                kwargs["error_messages"] += (
                        service_name.upper() + f":Delivery Creation Failed\nReason: {e}"
                )

        else:
            kwargs["error_messages"] += (
                    service_name.upper() + " already exists!"
            )

        return kwargs
