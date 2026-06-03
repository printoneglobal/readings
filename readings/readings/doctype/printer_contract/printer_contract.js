frappe.ui.form.on('Printer Contract', {
    onload:   function(frm) { toggle_all_contract_fields(frm); toggle_standby_fields(frm); },
    refresh:  function(frm) { toggle_all_contract_fields(frm); toggle_standby_fields(frm); },
    combined: function(frm) { toggle_all_contract_fields(frm); },
    combined_machine_contract: function(frm) {
        toggle_all_contract_fields(frm);
        calculate_bnw_color_entitlement(frm);
    },
    total_free_copies:       function(frm) { calculate_individual_entitlement(frm); },
    total_unit:              function(frm) { calculate_individual_entitlement(frm); },
    total_free_copies_bnw:   function(frm) { calculate_bnw_color_entitlement(frm); },
    total_free_copies_color: function(frm) { calculate_bnw_color_entitlement(frm); },
    total_unit_1:            function(frm) { calculate_bnw_color_entitlement(frm); },

    // ── Standby contract ──────────────────────────────
    standby_contract: function(frm) { toggle_standby_fields(frm); },

    status: function(frm) {
        if (frm.doc.standby_contract) {
            frm.set_value('status', frm.doc.status);
        }
    }
});

// ── Existing functions (unchanged) ────────────────────
function toggle_all_contract_fields(frm) {
    let is_combined         = frm.doc.combined ? 1 : 0;
    let is_combined_machine = frm.doc.combined_machine_contract ? 1 : 0;
    let is_standby          = frm.doc.standby_contract ? 1 : 0;  // ADD THIS
    let is_combined_machine_contract = is_combined && is_combined_machine;
    let is_combined_machine_only     = !is_combined && is_combined_machine;
    let is_combined_only             = is_combined && !is_combined_machine;

    [
        'monthly_free_copies_bnw',
        'monthly_free_copies_color',
        'extra_rate_bnw',
        'extra_rate_color'
    ].forEach(field => frm.toggle_display(field, !is_combined && !is_combined_machine));

    [
        'combined_contract_details_section',
        'combined_free_copies',
        'combined_excess_rate'
    ].forEach(field => frm.toggle_display(field, is_combined_only && !is_standby));

    [
        'combined_machine_contract_details_section',
        'total_free_copies',
        'total_unit',
        'individual_entitlement',
        'machine_combined_excess_rate'
    ].forEach(field => frm.toggle_display(field, is_combined_machine_contract));

    [
        'combined_machine_bnw_and_color_details_section',
        'total_free_copies_bnw',
        'total_free_copies_color',
        'individual_entitlement_for_bnw',
        'individual_entitlement_for_color',
        'excess_rate_bnw',
        'excess_rate_color',
        'total_unit_1'
    ].forEach(field => frm.toggle_display(field, is_combined_machine_only));

    frm.refresh_fields([
        'combined_contract_details_section',
        'monthly_free_copies_bnw', 'monthly_free_copies_color',
        'extra_rate_bnw', 'extra_rate_color',
        'combined_free_copies', 'combined_excess_rate',
        'combined_machine_contract_details_section',
        'total_free_copies', 'total_unit', 'individual_entitlement', 'machine_combined_excess_rate',
        'combined_machine_bnw_and_color_details_section',
        'total_free_copies_bnw', 'total_free_copies_color',
        'individual_entitlement_for_bnw', 'individual_entitlement_for_color',
        'excess_rate_bnw', 'excess_rate_color', 'total_unit_1'
    ]);

    calculate_bnw_color_entitlement(frm);
}

function calculate_individual_entitlement(frm) {
    let total_free_copies = frm.doc.total_free_copies || 0;
    let total_unit        = frm.doc.total_unit        || 0;
    let entitlement = total_unit > 0 ? Math.floor(total_free_copies / total_unit) : 0;
    frm.set_value('individual_entitlement', entitlement);
}

function calculate_bnw_color_entitlement(frm) {
    let total_free_copies_bnw   = frm.doc.total_free_copies_bnw   || 0;
    let total_free_copies_color = frm.doc.total_free_copies_color || 0;
    let total_unit              = frm.doc.total_unit_1             || 0;

    frm.set_value(
        'individual_entitlement_for_bnw',
        total_unit > 0 ? Math.floor(total_free_copies_bnw / total_unit) : 0
    );
    frm.set_value(
        'individual_entitlement_for_color',
        total_unit > 0 ? Math.floor(total_free_copies_color / total_unit) : 0
    );
}

// ── New: standby contract toggle ──────────────────────
function toggle_standby_fields(frm) {
    let is_standby = frm.doc.standby_contract ? 1 : 0;

    [
        'rental_amount',
        'contract_start_date',
        'rental_frequency',
        'reading_frequency',
        'monthly_free_copies_bnw',
        'monthly_free_copies_color',
        'extra_rate_bnw',
        'extra_rate_color'
    ].forEach(field => frm.toggle_display(field, !is_standby));

    [
        'standby_section',
        'exchange_machine_serial',
        'exchange_date',
        'status',
        'return_date'
    ].forEach(field => frm.toggle_display(field, is_standby));

    frm.refresh_fields([
        'rental_amount', 'contract_start_date',
        'rental_frequency', 'reading_frequency',
        'monthly_free_copies_bnw', 'monthly_free_copies_color',
        'extra_rate_bnw', 'extra_rate_color',
        'standby_section',
        'exchange_machine_serial', 'exchange_date', 'status', 'return_date'
    ]);
}