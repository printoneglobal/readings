// Copyright (c) 2026, Mohanraj and contributors
// For license information, please see license.txt

frappe.ui.form.on('Counter Reading', {

    refresh: function(frm) {
        console.log("refreshed...");
        toggle_machine_serial(frm);

        if (!frm.doc.contract) return;

        // On refresh — set correct section visibility based on contract type
        frappe.call({
            method: "frappe.client.get",
            args: { doctype: "Printer Contract", name: frm.doc.contract },
            callback: function(res) {
                let contract             = res.message;
                let is_combined          = is_checked(contract.combined);
                let has_machine_contract = is_checked(contract.combined_machine_contract);
                let is_combined_machine  = is_combined && has_machine_contract;
                let is_bnw_color_machine = !is_combined && has_machine_contract;

                if (is_combined_machine) {
                    hide_bnw_color_machine_calc_fields(frm);
                    // Hide normal + combined billing fields
                    [
                        "prorated_bnw", "prorated_color",
                        "bnw_billable", "color_billable",
                        "bnw_amount", "color_amount", "days_difference",
                        "excess_combined_billable_consumption",
                        "prorated_combined_free_copies",
                        "no_of_days_consumed", "excess_combined_amount",
                        "combined_invoice"
                    ].forEach(f => frm.set_df_property(f, "hidden", 1));

                    // Show CMC calc fields if submitted
                    if (frm.doc.docstatus === 1 && frm.doc.machine_serial_number) {
                        show_machine_calc_fields(frm);
                    } else {
                        hide_machine_calc_fields(frm);
                        frm.set_df_property("actual_consumption", "hidden", 0);
                        frm.refresh_field("actual_consumption");
                    }

                } else if (is_combined) {
                    // Hide CMC fields + normal billing fields
                    hide_machine_calc_fields(frm);
                    hide_bnw_color_machine_calc_fields(frm);
                    [
                        "prorated_bnw", "prorated_color",
                        "bnw_billable", "color_billable",
                        "bnw_amount", "color_amount", "days_difference"
                    ].forEach(f => frm.set_df_property(f, "hidden", 1));
                    // Show combined billing fields
                    [
                        "excess_combined_billable_consumption",
                        "prorated_combined_free_copies",
                        "no_of_days_consumed", "excess_combined_amount",
                        "combined_invoice"
                    ].forEach(f => frm.set_df_property(f, "hidden", 0));

                } else if (is_bnw_color_machine) {
                    hide_machine_calc_fields(frm);
                    [
                        "prorated_bnw", "prorated_color",
                        "bnw_billable", "color_billable",
                        "bnw_amount", "color_amount", "days_difference",
                        "excess_combined_billable_consumption",
                        "prorated_combined_free_copies",
                        "no_of_days_consumed", "excess_combined_amount",
                        "combined_invoice"
                    ].forEach(f => frm.set_df_property(f, "hidden", 1));
                    if (frm.doc.scenario_b_invoice) {
                        show_bnw_color_machine_calc_fields(frm);
                    } else {
                        show_bnw_color_machine_preview_fields(frm);
                    }

                } else {
                    // Normal — hide CMC + combined billing fields
                    hide_machine_calc_fields(frm);
                    hide_bnw_color_machine_calc_fields(frm);
                    [
                        "excess_combined_billable_consumption",
                        "prorated_combined_free_copies",
                        "no_of_days_consumed", "excess_combined_amount",
                        "combined_invoice"
                    ].forEach(f => frm.set_df_property(f, "hidden", 1));
                    // Show normal billing fields
                    [
                        "prorated_bnw", "prorated_color",
                        "bnw_billable", "color_billable",
                        "bnw_amount", "color_amount", "days_difference"
                    ].forEach(f => frm.set_df_property(f, "hidden", 0));
                }

                frm.refresh_fields();
            }
        });
    },

    customer: function(frm) {
        frm.set_query('contract', function() {
            return {
                filters: { customer: frm.doc.customer }
            };
        });
        debounced_calculate(frm);
    },

    reading_date: function(frm) {
        if (!frm.doc.contract || !frm.doc.reading_date) return;

        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Counter Reading",
                filters: {
                    contract:  frm.doc.contract,
                    name:      ["!=", frm.doc.name || ""],
                    docstatus: 1,
                    ...(frm.doc.machine_serial_number
                        ? { machine_serial_number: frm.doc.machine_serial_number }
                        : {})
                },
                fields: ["reading_date"],
                order_by: "reading_date desc",
                limit_page_length: 1
            },
            callback: function(r) {
                let prev = r.message.length ? r.message[0] : null;

                if (!prev) {
                    enable_all_fields(frm);
                    debounced_calculate(frm);
                    return;
                }

                let current_date = frm.doc.reading_date;
                let prev_date    = prev.reading_date;

                if (current_date <= prev_date) {
                    frappe.msgprint({
                        title: "Invalid Date",
                        message: `Current reading date (${current_date}) must be later than previous reading date (${prev_date}). Please correct the date before entering any values.`,
                        indicator: "red"
                    });
                    disable_all_fields(frm);
                    return;
                }

                enable_all_fields(frm);
                debounced_calculate(frm);
            }
        });
    },

    bnw_count:               function(frm) { debounced_calculate(frm); },
    color_count:             function(frm) { debounced_calculate(frm); },
    contract:                function(frm) { toggle_machine_serial(frm); debounced_calculate(frm); },
    machine_serial_number:   function(frm) { toggle_machine_fields(frm); debounced_calculate(frm); },
    current_bnw_readinga3:   function(frm) { debounced_calculate(frm); },
    current_color_readinga3: function(frm) { debounced_calculate(frm); },
    current_bnw_readinga5:   function(frm) { debounced_calculate(frm); },
    current_color_readinga5: function(frm) { debounced_calculate(frm); },

    before_save: function(frm) {
        if (frm.doc.docstatus !== 0 || frm._consumption_ack) return;

        if (frm._date_error) {
            frappe.msgprint({
                title: "Invalid Date",
                message: "Please fix the reading date before saving.",
                indicator: "red"
            });
            frappe.validated = false;
            return;
        }

        if (frm._reading_error) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Counter Reading",
                    filters: {
                        contract:  frm.doc.contract,
                        name:      ["!=", frm.doc.name || ""],
                        docstatus: 1,
                        ...(frm.doc.machine_serial_number
                            ? { machine_serial_number: frm.doc.machine_serial_number }
                            : {})
                    },
                    fields: [
                        "bnw_count", "color_count",
                        "current_bnw_readinga3", "current_color_readinga3",
                        "current_bnw_readinga5", "current_color_readinga5"
                    ],
                    order_by: "reading_date desc",
                    limit_page_length: 1
                },
                callback: function(r) {
                    let prev = r.message.length ? r.message[0] : null;
                    if (!prev) return;

                    let error_msg = "";

                    if ((frm.doc.bnw_count || 0) <= (prev.bnw_count || 0))
                        error_msg += `⚠ Please correct <b>BnW A4 Reading</b> — entered (${frm.doc.bnw_count}) must be higher than previous (${prev.bnw_count})<br><br>`;
                    if ((frm.doc.color_count || 0) <= (prev.color_count || 0))
                        error_msg += `⚠ Please correct <b>Color A4 Reading</b> — entered (${frm.doc.color_count}) must be higher than previous (${prev.color_count})<br><br>`;
                    if ((frm.doc.current_bnw_readinga3 || 0) < (prev.current_bnw_readinga3 || 0))
                        error_msg += `⚠ Please correct <b>BnW A3 Reading</b> — entered (${frm.doc.current_bnw_readinga3}) must be higher than previous (${prev.current_bnw_readinga3})<br><br>`;
                    if ((frm.doc.current_color_readinga3 || 0) < (prev.current_color_readinga3 || 0))
                        error_msg += `⚠ Please correct <b>Color A3 Reading</b> — entered (${frm.doc.current_color_readinga3}) must be higher than previous (${prev.current_color_readinga3})<br><br>`;
                    if ((frm.doc.current_bnw_readinga5 || 0) < (prev.current_bnw_readinga5 || 0))
                        error_msg += `⚠ Please correct <b>BnW A5 Reading</b> — entered (${frm.doc.current_bnw_readinga5}) must be higher than previous (${prev.current_bnw_readinga5})<br><br>`;
                    if ((frm.doc.current_color_readinga5 || 0) < (prev.current_color_readinga5 || 0))
                        error_msg += `⚠ Please correct <b>Color A5 Reading</b> — entered (${frm.doc.current_color_readinga5}) must be higher than previous (${prev.current_color_readinga5})<br><br>`;

                    if (error_msg) {
                        frappe.msgprint({
                            title: "Invalid Reading — Cannot Save",
                            message: error_msg,
                            indicator: "red"
                        });
                    }
                }
            });
            frappe.validated = false;
            return;
        }

        // 50% consumption warning — skip for combined_machine_contract
        if (!frm.doc.contract) return;

        frappe.call({
            method: "frappe.client.get",
            args: { doctype: "Printer Contract", name: frm.doc.contract },
            callback: function(res) {
                if (res.message && res.message.combined_machine_contract) return;

                let bnw_used   = frm.doc.bnw_consumption || 0;
                let color_used = frm.doc.color_consumption || 0;
                let prev_bnw   = frm.doc.previous_bnw_consumptiona4 || 0;
                let prev_color = frm.doc.previous_color_consumptiona4 || 0;
                let warning_msg = "";

                if (prev_bnw   > 0 && bnw_used   < (prev_bnw   * 0.50)) warning_msg += `⚠ BnW Consumption is less than 50% of previous<br>`;
                if (prev_color > 0 && color_used < (prev_color * 0.50)) warning_msg += `⚠ Color Consumption is less than 50% of previous<br>`;

                if (!warning_msg) return;

                frappe.validated = false;
                frappe.confirm(
                    `${warning_msg}<br>Do you want to continue saving?`,
                    function() { frm._consumption_ack = true; frappe.validated = true; frm.save(); },
                    function() { frappe.validated = false; }
                );
            }
        });
    }
});


// ============================================================
// PRINTER CONTRACT — Combined Fields Toggle
// ============================================================

frappe.ui.form.on('Printer Contract', {
    onload: function(frm) { toggle_combined_fields(frm); },
    refresh: function(frm) { toggle_combined_fields(frm); },
    combined: function(frm) { toggle_combined_fields(frm); }
});

function toggle_combined_fields(frm) {
    let is_combined = frm.doc.combined ? 1 : 0;
    frm.set_df_property('combined_free_copies',     'hidden', is_combined ? 0 : 1);
    frm.set_df_property('combined_rate',             'hidden', is_combined ? 0 : 1);
    frm.set_df_property('monthly_free_copies_bnw',  'hidden', is_combined ? 1 : 0);
    frm.set_df_property('monthly_free_copies_color', 'hidden', is_combined ? 1 : 0);
    frm.set_df_property('extra_rate_bnw',            'hidden', is_combined ? 1 : 0);
    frm.set_df_property('extra_rate_color',          'hidden', is_combined ? 1 : 0);
    frm.refresh_fields([
        'combined_free_copies', 'combined_rate',
        'monthly_free_copies_bnw', 'monthly_free_copies_color',
        'extra_rate_bnw', 'extra_rate_color'
    ]);
}


// ============================================================
// FIELD LISTS
// ============================================================

const READING_FIELDS = [
    "bnw_count", "color_count",
    "current_bnw_readinga3", "current_color_readinga3",
    "current_bnw_readinga5", "current_color_readinga5",
    "customer", "contract"
];


// ============================================================
// DATE ERROR — lock / unlock
// ============================================================

function disable_all_fields(frm) {
    frm._date_error = true;
    READING_FIELDS.forEach(f => frm.set_df_property(f, "read_only", 1));
    frm.refresh_fields();
}

function enable_all_fields(frm) {
    frm._date_error = false;
    if (!frm._reading_error) {
        READING_FIELDS.forEach(f => frm.set_df_property(f, "read_only", 0));
        frm.refresh_fields();
    }
}


// ============================================================
// READING VALUE ERROR — lock / unlock
// ============================================================

function disable_reading_fields(frm) {
    frm._reading_error = true;
    ["customer", "contract"].forEach(f => frm.set_df_property(f, "read_only", 1));
    frm.refresh_fields();
}

function enable_reading_fields(frm) {
    frm._reading_error = false;
    if (!frm._date_error) {
        READING_FIELDS.forEach(f => frm.set_df_property(f, "read_only", 0));
        frm.refresh_fields();
    }
}


// ============================================================
// MACHINE SERIAL — show only for combined_machine_contract
// ============================================================

function is_checked(value) {
    return Number(value) === 1;
}

function toggle_machine_serial(frm) {
    if (!frm.doc.contract) {
        frm.set_df_property("machine_serial_number", "hidden", 1);
        frm.refresh_field("machine_serial_number");
        return;
    }

    frappe.call({
        method: "frappe.client.get",
        args: { doctype: "Printer Contract", name: frm.doc.contract },
        callback: function(res) {
            let is_cmc = res.message.combined_machine_contract ? 1 : 0;
            frm.set_df_property("machine_serial_number", "hidden", is_cmc ? 0 : 1);
            frm.refresh_field("machine_serial_number");
        }
    });
}


// ============================================================
// MACHINE FIELDS TOGGLE
// ============================================================

function toggle_machine_fields(frm) {
    if (!frm.doc.machine_serial_number || !frm.doc.contract) {
        hide_machine_calc_fields(frm);
        return;
    }

    // Always calculate actual_consumption
    let actual_consumption =
        (frm.doc.bnw_consumption || 0) +
        (frm.doc.color_consumption || 0) +
        (frm.doc.current_bnw_consumption_a3 || 0) +
        (frm.doc.current_color_consumption_a3 || 0) +
        (frm.doc.current_bnw_consumptiona5 || 0) +
        (frm.doc.current_color_consumptiona5 || 0);

    frm.set_value("actual_consumption", actual_consumption);

    frappe.call({
        method: "frappe.client.get",
        args: { doctype: "Printer Contract", name: frm.doc.contract },
        callback: function(res) {
            let total_unit = res.message.total_unit || 0;

            if (!frm.doc.reading_date) {
                hide_machine_calc_fields(frm);
                frm.set_df_property("actual_consumption", "hidden", 0);
                frm.refresh_field("actual_consumption");
                return;
            }

            let month_start = frappe.datetime.month_start(frm.doc.reading_date);
            let month_end   = frappe.datetime.month_end(frm.doc.reading_date);

            frappe.call({
                method: "frappe.client.get_count",
                args: {
                    doctype: "Counter Reading",
                    filters: {
                        contract:     frm.doc.contract,
                        docstatus:    1,
                        name:         ["!=", frm.doc.name || ""],
                        reading_date: ["between", [month_start, month_end]]
                    }
                },
                callback: function(count_res) {
                    let submitted_count = count_res.message || 0;
                    let effective_count = submitted_count + 1;

                    if (effective_count >= total_unit) {
                        show_machine_calc_fields(frm);
                    } else {
                        hide_machine_calc_fields(frm);
                        frm.set_df_property("actual_consumption", "hidden", 0);
                        frm.refresh_field("actual_consumption");
                    }
                }
            });
        }
    });
}


function hide_machine_calc_fields(frm) {
    [
        "actual_consumption",
        "actual_excess_after_all_readings",
        "combined_no_of_days",
        "billable_amount",
        "machine_invoice",
        "prorated_entitlement"
    ].forEach(f => frm.set_df_property(f, "hidden", 1));
    frm.refresh_fields();
}

function show_machine_calc_fields(frm) {
    [
        "actual_consumption",
        "actual_excess_after_all_readings",
        "combined_no_of_days",
        "billable_amount",
        "machine_invoice",
        "prorated_entitlement"
    ].forEach(f => frm.set_df_property(f, "hidden", 0));
    frm.refresh_fields();
}

function hide_bnw_color_machine_calc_fields(frm) {
    [
        "combined_machine_billing_calculation__bnw_and_white_section",
        "prorated_individual_entitlement_for_bnw",
        "prorated_individual_entitlement_for_color",
        "excess_bnw_actual_consumption",
        "excess_color_actual_consumption",
        "excess_bnw_billable_amount",
        "excess_color_billable_amount",
        "no_of_days_1",
        "scenario_b_invoice"
    ].forEach(f => frm.set_df_property(f, "hidden", 1));
    frm.refresh_fields();
}

function show_bnw_color_machine_calc_fields(frm) {
    [
        "combined_machine_billing_calculation__bnw_and_white_section",
        "prorated_individual_entitlement_for_bnw",
        "prorated_individual_entitlement_for_color",
        "excess_bnw_actual_consumption",
        "excess_color_actual_consumption",
        "excess_bnw_billable_amount",
        "excess_color_billable_amount",
        "no_of_days_1",
        "scenario_b_invoice"
    ].forEach(f => frm.set_df_property(f, "hidden", 0));
    frm.refresh_fields();
}

function show_bnw_color_machine_preview_fields(frm) {
    frm.set_df_property("combined_machine_billing_calculation__bnw_and_white_section", "hidden", 0);
    [
        "excess_bnw_actual_consumption",
        "excess_color_actual_consumption"
    ].forEach(f => frm.set_df_property(f, "hidden", 0));
    [
        "prorated_individual_entitlement_for_bnw",
        "prorated_individual_entitlement_for_color",
        "excess_bnw_billable_amount",
        "excess_color_billable_amount",
        "no_of_days_1",
        "scenario_b_invoice"
    ].forEach(f => frm.set_df_property(f, "hidden", 1));
    frm.refresh_fields();
}


// ============================================================
// DEBOUNCE
// ============================================================

let _calc_timer = null;

function debounced_calculate(frm) {
    if (_calc_timer) clearTimeout(_calc_timer);
    _calc_timer = setTimeout(() => run_calculation(frm), 400);
}


// ============================================================
// MAIN CALCULATION
// ============================================================

function run_calculation(frm) {
    if (!frm.doc.contract) return;

    let current_date = frm.doc.reading_date
        ? frappe.datetime.str_to_obj(frm.doc.reading_date)
        : null;

    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Counter Reading",
            filters: {
                contract:     frm.doc.contract,
                name:         ["!=", frm.doc.name || ""],
                reading_date: ["<", frm.doc.reading_date || "9999-12-31"],
                docstatus:    1,
                ...(frm.doc.machine_serial_number
                    ? { machine_serial_number: frm.doc.machine_serial_number }
                    : {})
            },
            fields: [
                "bnw_count", "color_count",
                "current_bnw_readinga3", "current_color_readinga3",
                "current_bnw_readinga5", "current_color_readinga5",
                "reading_date",
                "bnw_consumption", "color_consumption",
                "current_bnw_consumption_a3", "current_color_consumption_a3",
                "current_bnw_consumptiona5", "current_color_consumptiona5"
            ],
            order_by: "reading_date desc",
            limit_page_length: 1
        },
        callback: function(r) {
            let prev = r.message.length ? r.message[0] : null;

            // Validate readings
            if (prev) {
                let errors = "";
                if ((frm.doc.bnw_count || 0) > 0 && (frm.doc.bnw_count || 0) <= (prev.bnw_count || 0))
                    errors += `⚠ <b>BnW A4 Reading</b> (${frm.doc.bnw_count}) must be higher than previous (${prev.bnw_count})<br><br>`;
                if ((frm.doc.color_count || 0) > 0 && (frm.doc.color_count || 0) <= (prev.color_count || 0))
                    errors += `⚠ <b>Color A4 Reading</b> (${frm.doc.color_count}) must be higher than previous (${prev.color_count})<br><br>`;
                if ((frm.doc.current_bnw_readinga3 || 0) > 0 && (frm.doc.current_bnw_readinga3 || 0) < (prev.current_bnw_readinga3 || 0))
                    errors += `⚠ <b>BnW A3 Reading</b> (${frm.doc.current_bnw_readinga3}) must be higher than previous (${prev.current_bnw_readinga3})<br><br>`;
                if ((frm.doc.current_color_readinga3 || 0) > 0 && (frm.doc.current_color_readinga3 || 0) < (prev.current_color_readinga3 || 0))
                    errors += `⚠ <b>Color A3 Reading</b> (${frm.doc.current_color_readinga3}) must be higher than previous (${prev.current_color_readinga3})<br><br>`;
                if ((frm.doc.current_bnw_readinga5 || 0) > 0 && (frm.doc.current_bnw_readinga5 || 0) < (prev.current_bnw_readinga5 || 0))
                    errors += `⚠ <b>BnW A5 Reading</b> (${frm.doc.current_bnw_readinga5}) must be higher than previous (${prev.current_bnw_readinga5})<br><br>`;
                if ((frm.doc.current_color_readinga5 || 0) > 0 && (frm.doc.current_color_readinga5 || 0) < (prev.current_color_readinga5 || 0))
                    errors += `⚠ <b>Color A5 Reading</b> (${frm.doc.current_color_readinga5}) must be higher than previous (${prev.current_color_readinga5})<br><br>`;

                if (errors) {
                    frappe.msgprint({ title: "Invalid Reading", message: errors + "Please correct before proceeding.", indicator: "red" });
                    disable_reading_fields(frm);
                    return;
                }
            }

            enable_reading_fields(frm);

            let prev_bnw              = prev ? (prev.bnw_count || 0) : 0;
            let prev_color            = prev ? (prev.color_count || 0) : 0;
            let prev_bnw_a3           = prev ? (prev.current_bnw_readinga3 || 0) : 0;
            let prev_color_a3         = prev ? (prev.current_color_readinga3 || 0) : 0;
            let prev_bnw_a5           = prev ? (prev.current_bnw_readinga5 || 0) : 0;
            let prev_color_a5         = prev ? (prev.current_color_readinga5 || 0) : 0;
            let prev_date             = prev ? frappe.datetime.str_to_obj(prev.reading_date) : null;
            let prev_bnw_consumption      = prev ? (prev.bnw_consumption || 0) : 0;
            let prev_color_consumption    = prev ? (prev.color_consumption || 0) : 0;
            let prev_bnw_consumption_a3   = prev ? (prev.current_bnw_consumption_a3 || 0) : 0;
            let prev_color_consumption_a3 = prev ? (prev.current_color_consumption_a3 || 0) : 0;
            let prev_bnw_consumption_a5   = prev ? (prev.current_bnw_consumptiona5 || 0) : 0;
            let prev_color_consumption_a5 = prev ? (prev.current_color_consumptiona5 || 0) : 0;

            frm.set_value("previous_bnw",             prev_bnw);
            frm.set_value("previous_color",           prev_color);
            frm.set_value("previous_bnw_readinga3",   prev_bnw_a3);
            frm.set_value("previous_color_readinga3", prev_color_a3);
            frm.set_value("previous_bnw_readinga5",   prev_bnw_a5);
            frm.set_value("previous_color_readinga5", prev_color_a5);
            frm.set_value("previous_reading_date",    prev ? prev.reading_date : null);

            let days = 0;

            if (prev_date && current_date) {
                days = frappe.datetime.get_diff(current_date, prev_date);
                if (current_date <= prev_date) return;

                frm._date_error = false;
                frm.set_value("days_difference",     days);
                frm.set_value("no_of_days_consumed", days);

                let opening_date_obj = frappe.datetime.add_days(prev_date, 1);
                frm.set_value("opening_date", opening_date_obj);
                frm.set_df_property("opening_date", "hidden", 0);

                if (days < 25) frappe.msgprint(`At least 25 days is required. Only ${days} days have passed.`);

            } else {
                frm._date_error = false;
                frm.set_value("days_difference", 0);
                frm.set_value("opening_date",    null);
                frm.set_df_property("opening_date", "hidden", 1);
            }

            // Consumption
            let bnw_used      = Math.max(0, prev ? (frm.doc.bnw_count || 0) - prev_bnw   : (frm.doc.bnw_count || 0));
            let color_used    = Math.max(0, prev ? (frm.doc.color_count || 0) - prev_color : (frm.doc.color_count || 0));
            let bnw_used_a3   = Math.max(0, ((frm.doc.current_bnw_readinga3 || 0) - prev_bnw_a3) * 2);
            let color_used_a3 = Math.max(0, ((frm.doc.current_color_readinga3 || 0) - prev_color_a3) * 2);
            let bnw_used_a5   = Math.max(0, ((frm.doc.current_bnw_readinga5 || 0) - prev_bnw_a5) / 2);
            let color_used_a5 = Math.max(0, ((frm.doc.current_color_readinga5 || 0) - prev_color_a5) / 2);

            frm.set_value("bnw_consumption",              bnw_used);
            frm.set_value("color_consumption",            color_used);
            frm.set_value("current_bnw_consumption_a3",   bnw_used_a3);
            frm.set_value("current_color_consumption_a3", color_used_a3);
            frm.set_value("current_bnw_consumptiona5",    bnw_used_a5);
            frm.set_value("current_color_consumptiona5",  color_used_a5);

            frm.set_value("previous_bnw_consumptiona4",   prev_bnw_consumption);
            frm.set_value("previous_color_consumptiona4", prev_color_consumption);
            frm.set_value("previous_bnw_consumptiona3",   prev_bnw_consumption_a3);
            frm.set_value("previous_color_consumptiona3", prev_color_consumption_a3);
            frm.set_value("previous_bnw_consumptiona5",   prev_bnw_consumption_a5);
            frm.set_value("previous_color_consumptiona5", prev_color_consumption_a5);

            // Fetch contract
            frappe.call({
                method: "frappe.client.get",
                args: { doctype: "Printer Contract", name: frm.doc.contract },
                callback: function(res) {
                    let contract             = res.message;
                    let is_combined          = is_checked(contract.combined);
                    let has_machine_contract = is_checked(contract.combined_machine_contract);
                    let is_combined_machine  = is_combined && has_machine_contract;
                    let is_bnw_color_machine = !is_combined && has_machine_contract;

                    // ============================================================
                    // COMBINED MACHINE CONTRACT
                    // ============================================================
                    if (is_combined_machine) {
                        hide_bnw_color_machine_calc_fields(frm);
                        [
                            "prorated_bnw", "prorated_color",
                            "bnw_billable", "color_billable",
                            "bnw_amount", "color_amount", "days_difference",
                            "excess_combined_billable_consumption",
                            "prorated_combined_free_copies",
                            "no_of_days_consumed", "excess_combined_amount",
                            "combined_invoice"
                        ].forEach(f => frm.set_df_property(f, "hidden", 1));
                        frm.refresh_fields();

                        let actual_consumption =
                            bnw_used + color_used +
                            bnw_used_a3 + color_used_a3 +
                            bnw_used_a5 + color_used_a5;
                        frm.set_value("actual_consumption", actual_consumption);

                        // Show prorated_entitlement on form (preview)
                        let individual_entitlement = contract.individual_entitlement || 0;
                        let prorated = prev
                            ? Math.round((individual_entitlement / 30) * days * 100) / 100
                            : individual_entitlement;
                        frm.set_value("prorated_entitlement", prorated);

                        toggle_machine_fields(frm);
                        return;
                    }

                    // ============================================================
                    // NORMAL / COMBINED BILLING
                    // ============================================================
                    let total_bnw   = bnw_used + bnw_used_a3 + bnw_used_a5;
                    let total_color = color_used + color_used_a3 + color_used_a5;

                    // ============================================================
                    // COMBINED MACHINE CONTRACT — BnW and Color separate
                    // ============================================================
                    if (is_bnw_color_machine) {
                        hide_machine_calc_fields(frm);
                        [
                            "prorated_bnw", "prorated_color",
                            "bnw_billable", "color_billable",
                            "bnw_amount", "color_amount", "days_difference",
                            "excess_combined_billable_consumption",
                            "prorated_combined_free_copies",
                            "no_of_days_consumed", "excess_combined_amount",
                            "combined_invoice"
                        ].forEach(f => frm.set_df_property(f, "hidden", 1));
                        show_bnw_color_machine_preview_fields(frm);

                        let individual_bnw = contract.individual_entitlement_for_bnw || 0;
                        let individual_color = contract.individual_entitlement_for_color || 0;
                        let allowed_bnw = individual_bnw;
                        let allowed_color = individual_color;

                        if (prev) {
                            allowed_bnw = Math.round((individual_bnw / 30) * days * 100) / 100;
                            allowed_color = Math.round((individual_color / 30) * days * 100) / 100;
                        }

                        frm.set_value("prorated_individual_entitlement_for_bnw", allowed_bnw);
                        frm.set_value("prorated_individual_entitlement_for_color", allowed_color);
                        frm.set_value("excess_bnw_actual_consumption", Math.floor(total_bnw));
                        frm.set_value("excess_color_actual_consumption", Math.floor(total_color));
                        frm.set_value("excess_bnw_billable_amount", 0);
                        frm.set_value("excess_color_billable_amount", 0);
                        frm.set_value("no_of_days_1", prev ? days : 0);
                        frm.refresh_fields([
                            "prorated_individual_entitlement_for_bnw",
                            "prorated_individual_entitlement_for_color",
                            "excess_bnw_actual_consumption",
                            "excess_color_actual_consumption",
                            "excess_bnw_billable_amount",
                            "excess_color_billable_amount",
                            "no_of_days_1"
                        ]);
                        return;
                    }

                    [
                        "excess_combined_billable_consumption",
                        "prorated_combined_free_copies",
                        "no_of_days_consumed", "excess_combined_amount",
                        "combined_invoice"
                    ].forEach(f => frm.set_df_property(f, "hidden", is_combined ? 0 : 1));
                    hide_bnw_color_machine_calc_fields(frm);

                    [
                        "prorated_bnw", "prorated_color",
                        "bnw_billable", "color_billable",
                        "bnw_amount", "color_amount", "days_difference"
                    ].forEach(f => frm.set_df_property(f, "hidden", is_combined ? 1 : 0));

                    frm.refresh_fields();

                    if (is_combined) {
                        let free_combined     = contract.combined_free_copies || 0;
                        let combined_rate     = contract.combined_excess_rate  || 0;
                        let allowed_combined  = 0;
                        let prorated_combined = 0;

                        if (!prev) {
                            allowed_combined = free_combined;
                        } else {
                            prorated_combined = (free_combined / 30) * days;
                            allowed_combined  = Math.floor(prorated_combined);
                        }

                        let total_all         = total_bnw + total_color;
                        let combined_billable = Math.max(0, total_all - allowed_combined);
                        let combined_amount   = Math.max(0, combined_billable * combined_rate);

                        frm.set_value("prorated_combined_free_copies",        allowed_combined);
                        frm.set_value("excess_combined_billable_consumption", combined_billable);
                        frm.set_value("excess_combined_amount",               combined_amount);
                        frm.set_value("prorated_bnw",   0);
                        frm.set_value("prorated_color",  0);
                        frm.set_value("bnw_billable",    0);
                        frm.set_value("color_billable",  0);
                        frm.set_value("bnw_amount",      0);
                        frm.set_value("color_amount",    0);

                    } else {
                        let free_bnw   = contract.monthly_free_copies_bnw  || 0;
                        let free_color = contract.monthly_free_copies_color || 0;
                        let bnw_rate   = contract.extra_rate_bnw            || 0;
                        let color_rate = contract.extra_rate_color          || 0;
                        let prorated_bnw = 0, prorated_color = 0;
                        let allowed_bnw  = 0, allowed_color  = 0;

                        if (!prev) {
                            allowed_bnw   = free_bnw;
                            allowed_color = free_color;
                        } else {
                            prorated_bnw   = (free_bnw   / 30) * days;
                            prorated_color = (free_color / 30) * days;
                            allowed_bnw    = prorated_bnw;
                            allowed_color  = prorated_color;
                        }

                        let bnw_billable   = Math.max(0, total_bnw   - allowed_bnw);
                        let color_billable = Math.max(0, total_color - allowed_color);
                        let bnw_amount     = Math.max(0, Math.floor(bnw_billable)   * bnw_rate);
                        let color_amount   = Math.max(0, Math.floor(color_billable) * color_rate);

                        frm.set_value("prorated_bnw",   prorated_bnw);
                        frm.set_value("prorated_color",  prorated_color);
                        frm.set_value("bnw_billable",    Math.floor(bnw_billable));
                        frm.set_value("color_billable",  Math.floor(color_billable));
                        frm.set_value("bnw_amount",      bnw_amount);
                        frm.set_value("color_amount",    color_amount);
                        frm.set_value("excess_combined_billable_consumption", 0);
                        frm.set_value("excess_combined_amount",               0);
                    }
                }
            });
        }
    });
}


// ============================================================
// Sales Invoice
// ============================================================

frappe.ui.form.on('Sales Invoice', {
    onload: function(frm) {
        if (!frm.is_new()) frm.refresh_fields();
    }
});
