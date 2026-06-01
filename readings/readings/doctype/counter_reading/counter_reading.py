# Copyright (c) 2026, Mohanraj and contributors
# For license information, please see license.txt

import math
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, date_diff, add_days, get_first_day, get_last_day


class CounterReading(Document):

    def validate(self):

        prev_bnw_consumption      = 0
        prev_color_consumption    = 0
        prev_bnw_consumption_a3   = 0
        prev_color_consumption_a3 = 0
        prev_bnw_consumption_a5   = 0
        prev_color_consumption_a5 = 0

        self.bnw_count               = self.bnw_count               or 0
        self.color_count             = self.color_count             or 0
        self.current_bnw_readinga3   = self.current_bnw_readinga3   or 0
        self.current_color_readinga3 = self.current_color_readinga3 or 0
        self.current_bnw_readinga5   = self.current_bnw_readinga5   or 0
        self.current_color_readinga5 = self.current_color_readinga5 or 0

        if not self.reading_date:
            frappe.throw("Please select a Reading Date before saving.")

        try:
            current_read_date = getdate(self.reading_date)
        except Exception:
            frappe.throw(f"Invalid Reading Date: {self.reading_date}")

        # ============================================================
        # FETCH CONTRACT
        # ============================================================
        contract            = frappe.get_doc("Printer Contract", self.contract)
        is_combined         = contract.combined or 0
        is_combined_machine = is_combined and (contract.combined_machine_contract or 0)
        is_bnw_color_machine = (not is_combined) and (contract.combined_machine_contract or 0)

        # ============================================================
        # PREVIOUS READING FILTER
        # ============================================================
        machine_filter = {}
        if (is_combined_machine or is_bnw_color_machine) and self.machine_serial_number:
            machine_filter["machine_serial_number"] = self.machine_serial_number

        prev_fields = [
            "reading_date", "bnw_count", "color_count",
            "bnw_consumption", "color_consumption",
            "current_bnw_readinga3", "current_color_readinga3",
            "current_bnw_consumption_a3", "current_color_consumption_a3",
            "current_bnw_readinga5", "current_color_readinga5",
            "current_bnw_consumptiona5", "current_color_consumptiona5"
        ]

        # ============================================================
        # AMENDED FLOW
        # ============================================================
        if self.amended_from:
            cancelled_doc          = frappe.get_doc("Counter Reading", self.amended_from)
            cancelled_reading_date = cancelled_doc.reading_date

            previous_read_record = frappe.get_all(
                "Counter Reading",
                filters={
                    "contract":     self.contract,
                    "docstatus":    1,
                    "reading_date": ["<", cancelled_reading_date],
                    "name":         ["!=", self.amended_from],
                    **machine_filter
                },
                fields=prev_fields,
                order_by="reading_date desc",
                limit=1
            )

        # ============================================================
        # NORMAL FLOW
        # ============================================================
        else:
            previous_read_record = frappe.get_all(
                "Counter Reading",
                filters={
                    "contract":     self.contract,
                    "docstatus":    1,
                    "reading_date": ["<", self.reading_date],
                    "name":         ["!=", self.name],
                    **machine_filter
                },
                fields=prev_fields,
                order_by="reading_date desc",
                limit=1
            )

        # ============================================================
        # GET PREVIOUS RECORD DETAILS
        # ============================================================
        if previous_read_record:
            prev_rec   = previous_read_record[0]
            prev_date  = getdate(prev_rec.reading_date)
            prev_bnw   = prev_rec.bnw_count   or 0
            prev_color = prev_rec.color_count or 0

            prev_bnw_consumption      = prev_rec.bnw_consumption              or 0
            prev_color_consumption    = prev_rec.color_consumption            or 0
            prev_bnw_consumption_a3   = prev_rec.current_bnw_consumption_a3   or 0
            prev_color_consumption_a3 = prev_rec.current_color_consumption_a3 or 0
            prev_bnw_consumption_a5   = prev_rec.current_bnw_consumptiona5    or 0
            prev_color_consumption_a5 = prev_rec.current_color_consumptiona5  or 0

            prev_bnw_a3   = prev_rec.current_bnw_readinga3   or 0
            prev_color_a3 = prev_rec.current_color_readinga3 or 0
            prev_bnw_a5   = prev_rec.current_bnw_readinga5   or 0
            prev_color_a5 = prev_rec.current_color_readinga5 or 0

            opening_date = add_days(prev_date, 1)
            if not self.opening_date:
                self.opening_date = opening_date

            if current_read_date < opening_date:
                frappe.throw(
                    f"Current reading date ({self.reading_date}) must be on or after "
                    f"opening date ({opening_date})"
                )

            days = date_diff(current_read_date, prev_date)
            if days < 25:
                frappe.throw(
                    f"At least 25 days is required. Currently only {days} days have passed."
                )

        else:
            prev_date     = None
            prev_bnw      = 0
            prev_color    = 0
            prev_bnw_a3   = 0
            prev_color_a3 = 0
            prev_bnw_a5   = 0
            prev_color_a5 = 0
            days          = 0
            self.opening_date = self.reading_date

        # ============================================================
        # VALIDATE READINGS
        # ============================================================
        if self.bnw_count <= prev_bnw:
            frappe.throw(f"BnW reading ({self.bnw_count}) must be higher than previous ({prev_bnw})")
        if self.color_count <= prev_color:
            frappe.throw(f"Color reading ({self.color_count}) must be higher than previous ({prev_color})")

        # ============================================================
        # CONSUMPTION
        # ============================================================
        bnw_used   = self.bnw_count   - prev_bnw
        color_used = self.color_count - prev_color

        bnw_used_a3   = max(0, (self.current_bnw_readinga3   - prev_bnw_a3)   * 2)
        color_used_a3 = max(0, (self.current_color_readinga3 - prev_color_a3) * 2)
        bnw_used_a5   = max(0, (self.current_bnw_readinga5   - prev_bnw_a5)   / 2)
        color_used_a5 = max(0, (self.current_color_readinga5 - prev_color_a5) / 2)

        self.bnw_consumption              = bnw_used
        self.color_consumption            = color_used
        self.current_bnw_consumption_a3   = bnw_used_a3
        self.current_color_consumption_a3 = color_used_a3
        self.current_bnw_consumptiona5    = bnw_used_a5
        self.current_color_consumptiona5  = color_used_a5

        # ============================================================
        # STORE PREVIOUS READINGS
        # ============================================================
        self.previous_bnw             = prev_bnw
        self.previous_color           = prev_color
        self.previous_bnw_readinga3   = prev_bnw_a3
        self.previous_color_readinga3 = prev_color_a3
        self.previous_bnw_readinga5   = prev_bnw_a5
        self.previous_color_readinga5 = prev_color_a5
        self.previous_reading_date    = prev_date

        self.previous_bnw_consumptiona4   = prev_bnw_consumption
        self.previous_color_consumptiona4 = prev_color_consumption
        self.previous_bnw_consumptiona3   = prev_bnw_consumption_a3
        self.previous_color_consumptiona3 = prev_color_consumption_a3
        self.previous_bnw_consumptiona5   = prev_bnw_consumption_a5
        self.previous_color_consumptiona5 = prev_color_consumption_a5

        # ============================================================
        # COMBINED MACHINE CONTRACT
        # Only save actual_consumption + prorated_entitlement
        # Billing happens on submit
        # ============================================================
        if is_combined_machine:
            self.actual_consumption = (
                bnw_used + color_used +
                bnw_used_a3 + color_used_a3 +
                bnw_used_a5 + color_used_a5
            )

            # Prorated entitlement — only if previous reading exists
            individual_entitlement = contract.individual_entitlement or 0
            if previous_read_record and days > 0:
                self.prorated_entitlement = round((individual_entitlement / 30) * days, 2)
            else:
                # First reading or >= 30 days — use full entitlement
                self.prorated_entitlement = individual_entitlement

            # Clear all billing fields — invoice must NOT generate on save
            self.actual_excess_after_all_readings = 0
            self.combined_no_of_days              = 0
            self.billable_amount                  = 0
            self.machine_invoice                  = None
            self.prorated_bnw                         = 0
            self.prorated_color                        = 0
            self.bnw_billable                          = 0
            self.color_billable                        = 0
            self.bnw_amount                            = 0
            self.color_amount                          = 0
            self.prorated_combined_free_copies         = 0
            self.excess_combined_billable_consumption  = 0
            self.excess_combined_amount                = 0
            self.prorated_individual_entitlement_for_bnw = 0
            self.prorated_individual_entitlement_for_color = 0
            self.excess_bnw_actual_consumption = 0
            self.excess_color_actual_consumption = 0
            self.excess_bnw_billable_amount = 0
            self.excess_color_billable_amount = 0
            self.no_of_days_1 = 0
            self.scenario_b_invoice = None
            return  # Stop here — billing on submit only

        # ============================================================
        # NORMAL / COMBINED BILLING
        # ============================================================
        total_bnw   = bnw_used + bnw_used_a3 + bnw_used_a5
        total_color = color_used + color_used_a3 + color_used_a5

        # ============================================================
        # COMBINED MACHINE CONTRACT — BnW and Color separate
        # Only save per-machine excess preview. Billing happens on submit.
        # ============================================================
        if is_bnw_color_machine:
            individual_bnw = contract.individual_entitlement_for_bnw or 0
            individual_color = contract.individual_entitlement_for_color or 0

            if previous_read_record and days > 0:
                allowed_bnw = round((individual_bnw / 30) * days, 2)
                allowed_color = round((individual_color / 30) * days, 2)
            else:
                allowed_bnw = individual_bnw
                allowed_color = individual_color

            self.prorated_individual_entitlement_for_bnw = allowed_bnw
            self.prorated_individual_entitlement_for_color = allowed_color
            self.excess_bnw_actual_consumption = int(total_bnw)
            self.excess_color_actual_consumption = int(total_color)
            self.excess_bnw_billable_amount = 0
            self.excess_color_billable_amount = 0
            self.no_of_days_1 = days if previous_read_record else 0
            self.scenario_b_invoice = None

            self.prorated_bnw = 0
            self.prorated_color = 0
            self.bnw_billable = 0
            self.color_billable = 0
            self.bnw_amount = 0
            self.color_amount = 0
            self.prorated_combined_free_copies = 0
            self.excess_combined_billable_consumption = 0
            self.excess_combined_amount = 0
            self.actual_consumption = 0
            self.prorated_entitlement = 0
            self.actual_excess_after_all_readings = 0
            self.combined_no_of_days = 0
            self.billable_amount = 0
            self.machine_invoice = None
            return

        if is_combined:
            free_combined = contract.combined_free_copies or 0
            combined_rate = contract.combined_excess_rate or 0

            if not previous_read_record:
                allowed_combined  = free_combined
                prorated_combined = 0
            else:
                prorated_combined = (free_combined / 30) * days
                allowed_combined  = math.floor(prorated_combined)

            total_all         = total_bnw + total_color
            combined_billable = max(0, total_all - allowed_combined)

            if total_all > 0 and combined_billable > 0:
                bnw_combined_billable   = int(combined_billable * (total_bnw / total_all))
                color_combined_billable = int(combined_billable) - bnw_combined_billable
            else:
                bnw_combined_billable   = 0
                color_combined_billable = 0

            combined_amount = max(0, combined_billable * combined_rate)

            self.prorated_combined_free_copies        = allowed_combined
            self.excess_combined_billable_consumption = int(combined_billable)
            self.excess_combined_amount               = combined_amount
            self.bnw_combined_billable                = bnw_combined_billable
            self.color_combined_billable              = color_combined_billable

            self.prorated_bnw      = 0
            self.prorated_color    = 0
            self.bnw_billable      = 0
            self.color_billable    = 0
            self.a4_bnw_billable   = 0
            self.a3_bnw_billable   = 0
            self.a5_bnw_billable   = 0
            self.a4_color_billable = 0
            self.a3_color_billable = 0
            self.a5_color_billable = 0

        else:
            free_bnw   = contract.monthly_free_copies_bnw  or 0
            free_color = contract.monthly_free_copies_color or 0
            bnw_rate   = contract.extra_rate_bnw            or 0
            color_rate = contract.extra_rate_color          or 0

            if not previous_read_record:
                allowed_bnw_calc   = free_bnw
                allowed_color_calc = free_color
                prorated_bnw       = 0
                prorated_color     = 0
            else:
                prorated_bnw       = (free_bnw   / 30) * days
                prorated_color     = (free_color / 30) * days
                allowed_bnw_calc   = prorated_bnw
                allowed_color_calc = prorated_color

            self.prorated_bnw   = round(prorated_bnw,   3)
            self.prorated_color = round(prorated_color, 3)

            bnw_billable_total = max(0, total_bnw - allowed_bnw_calc)

            a4_bnw_billable, a3_bnw_billable, a5_bnw_billable = (
                self._split_billable_by_consumption(
                    bnw_billable_total,
                    [bnw_used, bnw_used_a3, bnw_used_a5]
                )
            )

            self.bnw_billable    = int(bnw_billable_total)
            self.a4_bnw_billable = int(a4_bnw_billable)
            self.a3_bnw_billable = int(a3_bnw_billable)
            self.a5_bnw_billable = int(a5_bnw_billable)

            color_billable_total = max(0, total_color - allowed_color_calc)

            a4_color_billable, a3_color_billable, a5_color_billable = (
                self._split_billable_by_consumption(
                    color_billable_total,
                    [color_used, color_used_a3, color_used_a5]
                )
            )

            self.color_billable    = math.floor(color_billable_total)
            self.a4_color_billable = int(a4_color_billable)
            self.a3_color_billable = int(a3_color_billable)
            self.a5_color_billable = int(a5_color_billable)

            self.prorated_combined_free_copies        = 0
            self.excess_combined_billable_consumption = 0
            self.excess_combined_amount               = 0
            self.bnw_combined_billable                = 0
            self.color_combined_billable              = 0

        self.prorated_individual_entitlement_for_bnw = 0
        self.prorated_individual_entitlement_for_color = 0
        self.excess_bnw_actual_consumption = 0
        self.excess_color_actual_consumption = 0
        self.excess_bnw_billable_amount = 0
        self.excess_color_billable_amount = 0
        self.no_of_days_1 = 0
        self.scenario_b_invoice = None


    def on_submit(self):
        contract = frappe.get_doc("Printer Contract", self.contract)
        if contract.combined and contract.combined_machine_contract:
            self.generate_machine_invoice()
        elif (not contract.combined) and contract.combined_machine_contract:
            self.generate_bnw_color_machine_invoice()
        else:
            self.generate_invoice()


    # ============================================================
    # GENERATE INVOICE — Normal / Combined
    # ============================================================
    def generate_invoice(self):
        contract_doc = frappe.get_doc("Printer Contract", self.contract)
        is_combined  = contract_doc.combined or 0

        old_invoice_name = None
        if self.amended_from:
            old_doc          = frappe.get_doc("Counter Reading", self.amended_from)
            old_invoice_name = old_doc.combined_invoice if is_combined else old_doc.invoice

        if old_invoice_name:
            try:
                old_inv = frappe.get_doc("Sales Invoice", old_invoice_name)
                if old_inv.docstatus == 0:
                    old_inv.items               = []
                    old_inv.posting_date        = self.reading_date
                    old_inv.custom_opening_date = self.opening_date
                    self._append_invoice_items(old_inv, contract_doc, is_combined)
                    old_inv.save()
                    frappe.msgprint(f"Invoice {old_invoice_name} updated successfully ✅")
                    if is_combined:
                        self.combined_invoice = old_invoice_name
                    else:
                        self.invoice = old_invoice_name
                    self.db_update()
                    return
                elif old_inv.docstatus == 1:
                    old_inv.cancel()
                    frappe.msgprint(f"Previous submitted invoice {old_invoice_name} cancelled")
                    if is_combined:
                        self.combined_invoice = None
                    else:
                        self.invoice = None
            except Exception as e:
                frappe.log_error(str(e), "Invoice Update Error")
                frappe.msgprint(f"⚠ Could not update invoice: {str(e)}")

        if is_combined:
            if self.combined_invoice:
                frappe.msgprint(f"Combined Invoice already created: {self.combined_invoice}")
                return
            if (self.excess_combined_billable_consumption or 0) <= 0:
                frappe.msgprint("No billable copies to invoice.")
                return
            invoice = frappe.get_doc({
                "doctype": "Sales Invoice", "customer": self.customer,
                "posting_date": self.reading_date, "due_date": None, "items": []
            })
            invoice.custom_opening_date = self.opening_date
            self._append_invoice_items(invoice, contract_doc, is_combined)
            invoice.insert()
            invoice.save()
            self.combined_invoice = invoice.name
            self.db_update()
            frappe.msgprint(f"Combined Invoice {invoice.name} created successfully")

        else:
            if self.invoice:
                frappe.msgprint(f"Invoice already created: {self.invoice}")
                return
            if (self.bnw_billable or 0) <= 0 and (self.color_billable or 0) <= 0:
                frappe.msgprint("No billable copies to invoice.")
                return
            invoice = frappe.get_doc({
                "doctype": "Sales Invoice", "customer": self.customer,
                "posting_date": self.reading_date, "due_date": None, "items": []
            })
            invoice.custom_opening_date = self.opening_date
            self._append_invoice_items(invoice, contract_doc, is_combined)
            invoice.insert()
            invoice.save()
            self.invoice = invoice.name
            self.db_update()
            frappe.msgprint(f"Invoice {invoice.name} created successfully")


    def _split_billable_by_consumption(self, billable_qty, consumptions):
        billable_qty = int(max(0, billable_qty or 0))
        positive_consumptions = [max(0, c or 0) for c in consumptions]
        total_consumption = sum(positive_consumptions)

        if billable_qty <= 0 or total_consumption <= 0:
            return [0 for _ in positive_consumptions]

        raw_allocations = [
            (billable_qty * consumption / total_consumption) if consumption > 0 else 0
            for consumption in positive_consumptions
        ]
        allocations = [math.floor(qty) for qty in raw_allocations]
        remainder = billable_qty - sum(allocations)

        remainder_order = sorted(
            range(len(raw_allocations)),
            key=lambda i: (
                positive_consumptions[i] > 0,
                raw_allocations[i] - allocations[i],
                positive_consumptions[i]
            ),
            reverse=True
        )

        for index in remainder_order:
            if remainder <= 0:
                break
            if positive_consumptions[index] <= 0:
                continue
            allocations[index] += 1
            remainder -= 1

        return allocations


    def _append_invoice_items(self, invoice, contract_doc, is_combined):
        if is_combined:
            total_bnw   = (self.bnw_consumption or 0) + (self.current_bnw_consumption_a3 or 0) + (self.current_bnw_consumptiona5 or 0)
            total_color = (self.color_consumption or 0) + (self.current_color_consumption_a3 or 0) + (self.current_color_consumptiona5 or 0)
            total_all   = total_bnw + total_color
            combined_billable = int(self.excess_combined_billable_consumption or 0)

            if total_all > 0 and combined_billable > 0:
                bnw_qty   = int(combined_billable * (total_bnw / total_all))
                color_qty = combined_billable - bnw_qty
            else:
                bnw_qty = color_qty = 0

            a4_bnw, a3_bnw, a5_bnw = self._split_billable_by_consumption(
                bnw_qty,
                [
                    self.bnw_consumption or 0,
                    self.current_bnw_consumption_a3 or 0,
                    self.current_bnw_consumptiona5 or 0
                ]
            )
            a4_color, a3_color, a5_color = self._split_billable_by_consumption(
                color_qty,
                [
                    self.color_consumption or 0,
                    self.current_color_consumption_a3 or 0,
                    self.current_color_consumptiona5 or 0
                ]
            )

            if bnw_qty > 0:
                invoice.append("items", {
                    "item_code": "A4 BnW",
                    "description": f"Additional Combined Print BnW — A4 BnW({a4_bnw}), A3 BnW({a3_bnw}), A5 BnW({a5_bnw})",
                    "qty": bnw_qty, "rate": contract_doc.combined_excess_rate
                })
            if color_qty > 0:
                invoice.append("items", {
                    "item_code": "A4 Color",
                    "description": f"Additional Combined Print Color — A4 Color({a4_color}), A3 Color({a3_color}), A5 Color({a5_color})",
                    "qty": color_qty, "rate": contract_doc.combined_excess_rate
                })
        else:
            if (self.bnw_billable or 0) > 0:
                invoice.append("items", {
                    "item_code": "A4 BnW",
                    "description": f"Additional Print A4 BnW({self.a4_bnw_billable}), A3 BnW({self.a3_bnw_billable}), A5 BnW({self.a5_bnw_billable})",
                    "qty": self.bnw_billable, "rate": contract_doc.extra_rate_bnw
                })
            if (self.color_billable or 0) > 0:
                invoice.append("items", {
                    "item_code": "A4 Color",
                    "description": f"Additional Print A4 Color({self.a4_color_billable}), A3 Color({self.a3_color_billable}), A5 Color({self.a5_color_billable})",
                    "qty": self.color_billable, "rate": contract_doc.extra_rate_color
                })


    # ============================================================
    # GENERATE MACHINE INVOICE — Combined Machine Contract
    # Scenario B Excel logic — iterative redistribution
    # prorated_entitlement used when previous reading exists
    # ============================================================
    def generate_machine_invoice(self):
        contract   = frappe.get_doc("Printer Contract", self.contract)
        total_unit = contract.total_unit or 0

        if total_unit == 0:
            frappe.msgprint("Total units not set in contract.")
            return

        first_day = get_first_day(self.reading_date)
        last_day  = get_last_day(self.reading_date)

        submitted_readings = frappe.get_all(
            "Counter Reading",
            filters={
                "contract":     self.contract,
                "docstatus":    1,
                "reading_date": ["between", [first_day, last_day]]
            },
            fields=[
                "name", "machine_serial_number",
                "actual_consumption", "no_of_days_consumed",
                "days_difference", "machine_invoice",
                "opening_date", "customer",
                "prorated_entitlement"
            ]
        )

        old_invoice_name = None
        if self.amended_from:
            old_doc = frappe.get_doc("Counter Reading", self.amended_from)
            if old_doc.machine_invoice and old_doc.machine_invoice != "No Excess":
                old_invoice_name = old_doc.machine_invoice

        # Not all units submitted yet — wait
        if len(submitted_readings) < total_unit:
            frappe.msgprint(
                f"{len(submitted_readings)} of {total_unit} printer machines submitted. "
                f"Invoice will be created when counter reading are submitted for all the machines."
            )
            return

        # Already invoiced — skip unless this is amending that same invoice
        invoice_names = {
            r.machine_invoice
            for r in submitted_readings
            if r.machine_invoice and r.machine_invoice != "No Excess"
        }
        if invoice_names and (not old_invoice_name or invoice_names - {old_invoice_name}):
            frappe.msgprint("Invoice already created for this period.")
            return

        # ============================================================
        # DETERMINE EFFECTIVE ENTITLEMENT PER MACHINE
        # Use prorated_entitlement if available (previous reading exists)
        # Otherwise use full individual_entitlement
        # ============================================================
        individual_entitlement = contract.individual_entitlement or 0
        if not individual_entitlement and total_unit:
            individual_entitlement = (contract.total_free_copies or 0) / total_unit

        excess_rate  = contract.machine_combined_excess_rate or 0
        consumptions = [r.actual_consumption or 0 for r in submitted_readings]

        # Each machine uses its own prorated_entitlement if set, else full entitlement
        effective_entitlements = []
        for r in submitted_readings:
            pe = r.prorated_entitlement or 0
            if pe > 0:
                effective_entitlements.append(pe)
            else:
                effective_entitlements.append(individual_entitlement)

        # ============================================================
        # SCENARIO B — Iterative redistribution
        # ============================================================
        initial_excess = [
            consumptions[i] - effective_entitlements[i]
            for i in range(len(submitted_readings))
        ]
        final_excess = [max(0, e) for e in initial_excess]
        unused_pool  = sum(-e for e in initial_excess if e < 0)

        while unused_pool > 0:
            positive_indices = [i for i, e in enumerate(final_excess) if e > 0]
            if not positive_indices:
                break

            per_machine    = unused_pool / len(positive_indices)
            absorbed_total = 0

            for i in positive_indices:
                absorbed         = min(final_excess[i], per_machine)
                final_excess[i] -= absorbed
                absorbed_total  += absorbed

            if absorbed_total <= 0:
                break

            unused_pool -= absorbed_total

        # ============================================================
        # CALCULATE BILLABLE AMOUNTS
        # ============================================================
        billable_excesses     = [int(max(0, e)) for e in final_excess]
        billable_amounts      = [round(e * excess_rate, 2) for e in billable_excesses]
        total_billable_amount = sum(billable_amounts)

        # Days — use max days across all submitted readings
        no_of_days = max(
            (r.days_difference or r.no_of_days_consumed or 0)
            for r in submitted_readings
        )

        # ============================================================
        # UPDATE EACH READING with calculated values
        # ============================================================
        for i, r in enumerate(submitted_readings):
            billable        = billable_excesses[i]
            billable_amount = billable_amounts[i]
            frappe.db.set_value("Counter Reading", r.name, {
                "actual_excess_after_all_readings": billable,
                "combined_no_of_days":              no_of_days,
                "billable_amount":                  billable_amount
            })

        # No billable — no invoice
        if total_billable_amount <= 0:
            if old_invoice_name:
                try:
                    old_invoice = frappe.get_doc("Sales Invoice", old_invoice_name)
                    if old_invoice.docstatus == 1:
                        old_invoice.cancel()
                        frappe.msgprint(f"Previous submitted invoice {old_invoice_name} cancelled")
                    elif old_invoice.docstatus == 0:
                        old_invoice.delete()
                        frappe.msgprint(f"Previous draft invoice {old_invoice_name} deleted")
                except Exception as e:
                    frappe.log_error(str(e), "Machine Invoice Amend Error")
                    frappe.msgprint(f"Could not clear previous machine invoice: {str(e)}")
            frappe.msgprint("No billable amount for this period — all machines within entitlement.")
            for r in submitted_readings:
                frappe.db.set_value("Counter Reading", r.name, "machine_invoice", "No Excess")
            return

        # ============================================================
        # CREATE / UPDATE INVOICE
        # ============================================================
        invoice = None
        if old_invoice_name:
            try:
                old_invoice = frappe.get_doc("Sales Invoice", old_invoice_name)
                if old_invoice.docstatus == 0:
                    invoice = old_invoice
                    invoice.items = []
                    invoice.customer = self.customer
                    invoice.posting_date = self.reading_date
                    invoice.due_date = None
                    invoice.custom_opening_date = self.opening_date
                elif old_invoice.docstatus == 1:
                    old_invoice.cancel()
                    frappe.msgprint(f"Previous submitted invoice {old_invoice_name} cancelled")
            except Exception as e:
                frappe.log_error(str(e), "Machine Invoice Amend Error")
                frappe.msgprint(f"Could not update previous machine invoice: {str(e)}")

        if not invoice:
            invoice = frappe.get_doc({
                "doctype":      "Sales Invoice",
                "customer":     self.customer,
                "posting_date": self.reading_date,
                "due_date":     None,
                "items":        []
            })
            invoice.custom_opening_date = self.opening_date

        for i, r in enumerate(submitted_readings):
            billable = billable_excesses[i]
            if billable > 0:
                invoice.append("items", {
                    "item_code": "A4 BnW",
                    "description": (
                        f"Machine: {r.machine_serial_number} | "
                        f"Consumption: {consumptions[i]} | "
                        f"Entitlement: {effective_entitlements[i]} | "
                        f"Billable Excess: {billable} | "
                        f"Days: {no_of_days}"
                    ),
                    "qty":  billable,
                    "rate": excess_rate
                })

        if invoice.is_new():
            invoice.insert()
        invoice.save()

        for r in submitted_readings:
            frappe.db.set_value("Counter Reading", r.name, "machine_invoice", invoice.name)

        frappe.msgprint(
            f"✅ Machine Invoice {invoice.name} created successfully — "
            f"{len([e for e in final_excess if e > 0])} machines billed."
        )


    # ============================================================
    # GENERATE INVOICE — Combined Machine Contract BnW / Color
    # Scenario B redistribution separately for BnW and Color.
    # ============================================================
    def generate_bnw_color_machine_invoice(self):
        contract = frappe.get_doc("Printer Contract", self.contract)
        total_unit = contract.total_unit_1 or 0

        if total_unit == 0:
            frappe.msgprint("Total units not set in contract.")
            return

        first_day = get_first_day(self.reading_date)
        last_day = get_last_day(self.reading_date)

        submitted_readings = frappe.get_all(
            "Counter Reading",
            filters={
                "contract": self.contract,
                "docstatus": 1,
                "reading_date": ["between", [first_day, last_day]]
            },
            fields=[
                "name", "machine_serial_number", "customer", "opening_date",
                "bnw_consumption", "current_bnw_consumption_a3", "current_bnw_consumptiona5",
                "color_consumption", "current_color_consumption_a3", "current_color_consumptiona5",
                "prorated_individual_entitlement_for_bnw",
                "prorated_individual_entitlement_for_color",
                "no_of_days_1", "days_difference", "scenario_b_invoice"
            ]
        )

        old_invoice_name = None
        if self.amended_from:
            old_doc = frappe.get_doc("Counter Reading", self.amended_from)
            if old_doc.scenario_b_invoice and old_doc.scenario_b_invoice != "No Excess":
                old_invoice_name = old_doc.scenario_b_invoice

        if len(submitted_readings) < total_unit:
            frappe.msgprint(
                f"{len(submitted_readings)} of {total_unit} printer machines submitted. "
                f"Invoice will be created when counter reading are submitted for all the machines."
            )
            return

        invoice_names = {
            r.scenario_b_invoice
            for r in submitted_readings
            if r.scenario_b_invoice and r.scenario_b_invoice != "No Excess"
        }
        if invoice_names and (not old_invoice_name or invoice_names - {old_invoice_name}):
            frappe.msgprint("Scenario B invoice already created for this period.")
            return

        bnw_consumptions = [
            (r.bnw_consumption or 0) +
            (r.current_bnw_consumption_a3 or 0) +
            (r.current_bnw_consumptiona5 or 0)
            for r in submitted_readings
        ]
        color_consumptions = [
            (r.color_consumption or 0) +
            (r.current_color_consumption_a3 or 0) +
            (r.current_color_consumptiona5 or 0)
            for r in submitted_readings
        ]

        default_bnw_entitlement = contract.individual_entitlement_for_bnw or 0
        default_color_entitlement = contract.individual_entitlement_for_color or 0
        bnw_entitlements = [
            r.prorated_individual_entitlement_for_bnw or default_bnw_entitlement
            for r in submitted_readings
        ]
        color_entitlements = [
            r.prorated_individual_entitlement_for_color or default_color_entitlement
            for r in submitted_readings
        ]

        bnw_billable_excesses = self._redistribute_machine_excess(
            bnw_consumptions, bnw_entitlements
        )
        color_billable_excesses = self._redistribute_machine_excess(
            color_consumptions, color_entitlements
        )

        bnw_rate = contract.excess_rate_bnw or 0
        color_rate = contract.excess_rate_color or 0
        bnw_amounts = [round(qty * bnw_rate, 2) for qty in bnw_billable_excesses]
        color_amounts = [round(qty * color_rate, 2) for qty in color_billable_excesses]
        total_billable_amount = sum(bnw_amounts) + sum(color_amounts)

        no_of_days = max(
            (r.no_of_days_1 or r.days_difference or 0)
            for r in submitted_readings
        )

        for i, r in enumerate(submitted_readings):
            frappe.db.set_value("Counter Reading", r.name, {
                "excess_bnw_billable_amount": bnw_amounts[i],
                "excess_color_billable_amount": color_amounts[i],
                "no_of_days_1": no_of_days
            })

        if total_billable_amount <= 0:
            if old_invoice_name:
                try:
                    old_invoice = frappe.get_doc("Sales Invoice", old_invoice_name)
                    if old_invoice.docstatus == 1:
                        old_invoice.cancel()
                        frappe.msgprint(f"Previous submitted invoice {old_invoice_name} cancelled")
                    elif old_invoice.docstatus == 0:
                        old_invoice.delete()
                        frappe.msgprint(f"Previous draft invoice {old_invoice_name} deleted")
                except Exception as e:
                    frappe.log_error(str(e), "Scenario B Invoice Amend Error")
                    frappe.msgprint(f"Could not clear previous Scenario B invoice: {str(e)}")
            frappe.msgprint("No billable amount for this period — all machines within entitlement.")
            for r in submitted_readings:
                frappe.db.set_value("Counter Reading", r.name, "scenario_b_invoice", "No Excess")
            return

        invoice = None
        if old_invoice_name:
            try:
                old_invoice = frappe.get_doc("Sales Invoice", old_invoice_name)
                if old_invoice.docstatus == 0:
                    invoice = old_invoice
                    invoice.items = []
                    invoice.customer = self.customer
                    invoice.posting_date = self.reading_date
                    invoice.due_date = None
                    invoice.custom_opening_date = self.opening_date
                elif old_invoice.docstatus == 1:
                    old_invoice.cancel()
                    frappe.msgprint(f"Previous submitted invoice {old_invoice_name} cancelled")
            except Exception as e:
                frappe.log_error(str(e), "Scenario B Invoice Amend Error")
                frappe.msgprint(f"Could not update previous Scenario B invoice: {str(e)}")

        if not invoice:
            invoice = frappe.get_doc({
                "doctype": "Sales Invoice",
                "customer": self.customer,
                "posting_date": self.reading_date,
                "due_date": None,
                "items": []
            })
            invoice.custom_opening_date = self.opening_date

        for i, r in enumerate(submitted_readings):
            if bnw_billable_excesses[i] > 0:
                invoice.append("items", {
                    "item_code": "A4 BnW",
                    "description": (
                        f"Machine: {r.machine_serial_number} | "
                        f"BnW Consumption: {bnw_consumptions[i]} | "
                        f"BnW Entitlement: {bnw_entitlements[i]} | "
                        f"Billable BnW Excess: {bnw_billable_excesses[i]} | "
                        f"Days: {no_of_days}"
                    ),
                    "qty": bnw_billable_excesses[i],
                    "rate": bnw_rate
                })
            if color_billable_excesses[i] > 0:
                invoice.append("items", {
                    "item_code": "A4 Color",
                    "description": (
                        f"Machine: {r.machine_serial_number} | "
                        f"Color Consumption: {color_consumptions[i]} | "
                        f"Color Entitlement: {color_entitlements[i]} | "
                        f"Billable Color Excess: {color_billable_excesses[i]} | "
                        f"Days: {no_of_days}"
                    ),
                    "qty": color_billable_excesses[i],
                    "rate": color_rate
                })

        if invoice.is_new():
            invoice.insert()
        invoice.save()

        for r in submitted_readings:
            frappe.db.set_value("Counter Reading", r.name, "scenario_b_invoice", invoice.name)

        frappe.msgprint(f"Scenario B Invoice {invoice.name} created successfully.")


    def _redistribute_machine_excess(self, consumptions, entitlements):
        excess_values = [
            consumptions[i] - entitlements[i]
            for i in range(len(consumptions))
        ]

        while True:
            positive_indices = [i for i, e in enumerate(excess_values) if e > 0]
            unused_pool = sum(abs(e) for e in excess_values if e < 0)

            if unused_pool <= 0:
                break
            if not positive_indices:
                break

            per_machine = unused_pool / len(positive_indices)
            next_excess_values = []

            for i, excess in enumerate(excess_values):
                if i in positive_indices:
                    next_excess_values.append(excess - per_machine)
                else:
                    next_excess_values.append(0)

            excess_values = next_excess_values

        return [int(max(0, e)) for e in excess_values]
