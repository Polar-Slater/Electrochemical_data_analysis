"""Direct initial-value editing for fitting. GPL-3.0-or-later."""
from copy import deepcopy
from math import isfinite, isnan


def parameter_rows(circuit):
    if circuit is None:
        return []
    rows = []
    for index, element in enumerate(circuit.get_elements()):
        for key, value in element.get_values().items():
            rows.append(dict(
                index=index, key=key, name=circuit.get_element_name(element),
                unit=element.get_unit(key), value=value,
                lower=element.get_lower_limit(key), upper=element.get_upper_limit(key),
                fixed=element.is_fixed(key),
            ))
    return rows


def apply_parameters(circuit, rows):
    """Validate all edits on a copy, preserving the original on any failure."""
    result = deepcopy(circuit)
    elements = result.get_elements()
    for row in rows:
        label = f"{row['name']}.{row['key']}"
        try:
            value, lower, upper = (float(row[k]) for k in ("value", "lower", "upper"))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{label}: enter numbers (for example 1e-6); bounds may use -inf or inf.") from exc
        if not isfinite(value) or isnan(lower) or isnan(upper):
            raise ValueError(f"{label}: initial value must be finite; bounds cannot be NaN.")
        if not lower < upper:
            raise ValueError(f"{label}: minimum must be less than maximum.")
        if not lower <= value <= upper:
            raise ValueError(f"{label}: initial value must be between minimum and maximum.")
        element = elements[row["index"]]
        key = row["key"]
        # Widen old bounds first so the underlying setters cannot clip new values.
        element.set_lower_limits(**{key: float("-inf")})
        element.set_upper_limits(**{key: float("inf")})
        element.set_values(**{key: value})
        element.set_lower_limits(**{key: lower})
        element.set_upper_limits(**{key: upper})
        element.set_fixed(**{key: bool(row["fixed"])})
    return result


class InitialParametersTable:
    def __init__(self, on_apply):
        import dearpygui.dearpygui as dpg
        self.on_apply = on_apply
        self.circuit = None
        self.entries = []
        dpg.add_text("Edit starting values here. Perform also applies these entries automatically.")
        with dpg.group(horizontal=True):
            dpg.add_button(label="Apply initial values", callback=self.apply)
            self.status = dpg.add_text("Enter a circuit to show its parameters.", wrap=600)
        with dpg.table(header_row=True, borders_innerH=True, borders_innerV=True,
                       borders_outerH=True, borders_outerV=True, scrollY=True,
                       freeze_rows=1, height=-1, resizable=True) as self.table:
            for label in ("Component", "Parameter / unit", "Initial value", "Minimum", "Maximum", "Fixed"):
                dpg.add_table_column(label=label, width_fixed=label == "Fixed",
                                     init_width_or_weight=48 if label == "Fixed" else 1)

    def set_circuit(self, circuit):
        import dearpygui.dearpygui as dpg
        self.circuit = circuit
        self.entries = []
        dpg.delete_item(self.table, children_only=True, slot=1)
        for row in parameter_rows(circuit):
            with dpg.table_row(parent=self.table):
                dpg.add_text(row["name"])
                dpg.add_text(f"{row['key']} ({row['unit']})" if row["unit"] else row["key"])
                fields = {key: dpg.add_input_text(default_value=format(row[key], ".12g"), width=-1)
                          for key in ("value", "lower", "upper")}
                fields["fixed"] = dpg.add_checkbox(default_value=row["fixed"])
            self.entries.append((row, fields))
        dpg.set_value(self.status, "Use scientific notation, e.g. 1e-6. Bounds accept inf." if circuit else "Enter a valid circuit first.")
        dpg.configure_item(self.status, color=(200, 200, 200))

    def commit(self):
        import dearpygui.dearpygui as dpg
        if self.circuit is None:
            return None
        rows = []
        for original, fields in self.entries:
            row = original.copy()
            for key, tag in fields.items():
                value = dpg.get_value(tag)
                # Display compact numbers without rounding untouched fitted values.
                if key != "fixed" and value == format(original[key], ".12g"):
                    value = original[key]
                row[key] = value
            rows.append(row)
        try:
            result = apply_parameters(self.circuit, rows)
        except ValueError as exc:
            dpg.set_value(self.status, str(exc))
            dpg.configure_item(self.status, color=(255, 110, 110))
            raise
        self.circuit = result
        self.on_apply(result)
        dpg.set_value(self.status, "Initial values applied.")
        dpg.configure_item(self.status, color=(150, 220, 150))
        return result

    def apply(self, *args):
        try:
            self.commit()
        except ValueError:
            pass  # Keep the invalid entry visible alongside its explanation.

    def has_active_input(self):
        import dearpygui.dearpygui as dpg
        return any(dpg.is_item_active(tag) for _, fields in self.entries for tag in fields.values())
