"""
Module: entities.state_totals
Representation of a state totals record "K", including transformation functions
and support functions for conversion into different formats.
"""
from itertools import chain

from fire.translator.util import rjust_zero
from fire.translator.util import factor_transforms, xform_entity, fire_entity

"""
_STATE_TOTALS_TRANSFORMS
-----------------------
Stores metadata associated with each field in a Transmitter record.
Values in key-value pairs represent metadata in the following format:

(default value, length, fill character, transformation function)
"""

_ITEMS = [
    ("record_type", ("K", 1, "\x00", lambda x: x)),
    ("number_of_payees", ("", 8, "0", lambda x: x)),
    ("blank_1", ("", 6, "\x00", lambda x: x)),
]

for field in chain((x for x in range(1, 10)), \
                   (chr(x) for x in range(ord('A'), ord('H')))):
    _ITEMS.append((f"payment_amount_{field}",
                   (18*"0", 18, "0", lambda x: rjust_zero(x, 18))))

_ITEMS += [
    ("blank_2", ("", 196, "\x00", lambda x: x)),
    ("record_sequence_number", ("", 8, "0", lambda x: x)),
    ("blank_3", ("", 199, "\x00", lambda x: x)),
    ("state_income_tax_withheld", ("", 18, "\x00", lambda x: x)),
    ("local_income_tax_withheld", ("", 18, "\x00", lambda x: x)),
    ("blank_4", ("", 4, "\x00", lambda x: x)),
    ("combined_federal_state_code", ("", 2, "\x00", lambda x: x)),
    ("blank_5", ("", 2, "\x00", lambda x: x))
]

_STATE_TOTALS_SORT, _STATE_TOTALS_TRANSFORMS = factor_transforms(_ITEMS)

def xform(data):
    """
    Applies transformation functions definted in _STATE_TOTALS_TRANSFORMS to
    data supplied as parameter to respective key-value pairs provided as the
    input parameter.

    Parameters
    ----------
    data : array[dict]
        Array of dict elements containing State Totals data.
        Expects element of the array to have keys that exist in the
        _STATE_TOTALS_TRANSFORMS dict (not required to have all keys).

    Returns
    ----------
    dict
        Dictionary containing processed (transformed) data provided as a
        parameter.
    """
    state_totals = []
    for state_total in data:
        state_totals.append(xform_entity(_STATE_TOTALS_TRANSFORMS, state_total))
    return state_totals

def fire(data):
    """
    Returns the given record as a string formatted to the IRS Publication 1220
    specification, based on data supplied as parameter.

    Parameters
    ----------
    data : dict
        Expects data parameter to have all keys specified in
        _STATE_TOTALS_TRANSFORMS.

    Returns
    ----------
    str
        String formatted to meet IRS Publication 1220
    """
    state_totals_string = ""
    for state_total in data:
        state_totals_string += fire_entity(
            _STATE_TOTALS_TRANSFORMS,
            _STATE_TOTALS_SORT,
            state_total
        )
    return state_totals_string
