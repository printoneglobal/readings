# Copyright (c) 2026, Trizenix Technologies and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document

class PrinterContract(Document):
    def validate(self):
        is_combined_machine_contract = self.combined and self.combined_machine_contract
        is_combined_machine_only     = not self.combined and self.combined_machine_contract

        # ── Combined free copies logic ────────────────────────
        if self.combined or is_combined_machine_only:
            self.monthly_free_copies_bnw   = 0
            self.monthly_free_copies_color = 0
            self.extra_rate_bnw            = 0
            self.extra_rate_color          = 0

        if not self.combined or self.combined_machine_contract:
            self.combined_free_copies = 0
            self.combined_excess_rate = 0

        # ── Combined machine contract logic ───────────────────
        if is_combined_machine_contract:
            self.monthly_free_copies_bnw   = 0
            self.monthly_free_copies_color = 0
            self.extra_rate_bnw            = 0
            self.extra_rate_color          = 0

            if self.total_unit and self.total_unit > 0:
                self.individual_entitlement = self.total_free_copies / self.total_unit
            else:
                self.individual_entitlement = 0
        else:
            self.total_free_copies      = 0
            self.total_unit             = 0
            self.individual_entitlement = 0
            self.combined_machine_table = []

        # ── Combined machine BnW and Color logic ──────────────
        if is_combined_machine_only:
            if self.total_unit_1 and self.total_unit_1 > 0:
                self.individual_entitlement_for_bnw   = self.total_free_copies_bnw   // self.total_unit_1
                self.individual_entitlement_for_color = self.total_free_copies_color // self.total_unit_1
            else:
                self.individual_entitlement_for_bnw   = 0
                self.individual_entitlement_for_color = 0
        else:
            self.total_free_copies_bnw            = 0
            self.total_free_copies_color          = 0
            self.individual_entitlement_for_bnw   = 0
            self.individual_entitlement_for_color = 0
            self.excess_rate_bnw                  = 0
            self.excess_rate_color                = 0
            self.total_unit_1                     = 0

        # ── Standby contract logic ────────────────────────────
        if self.standby_contract:
            self.rental_amount           = 0
            self.contract_start_date     = None
            self.rental_frequency        = None
            self.reading_frequency       = None
            self.monthly_free_copies_bnw  = 0    # ADD
            self.monthly_free_copies_color = 0   # ADD
            self.extra_rate_bnw           = 0    # ADD
            self.extra_rate_color         = 0    # ADD
            self.combined_free_copies     = 0  # ADD
            self.combined_excess_rate     = 0  # ADD
            
            if self.status == "Active":
                frappe.db.set_value(self.doctype, self.name, 'status', 'Active')
            elif self.status == "Returned":
                frappe.db.set_value(self.doctype, self.name, 'status', 'Returned')
        else:
            self.exchange_machine_serial = None
            self.exchange_date           = None
            self.return_date             = None