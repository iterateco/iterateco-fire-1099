"""
Module: Translator
Processes user-provided JSON file into an output file in the format
required by IRS Publication 1220.

Support notes:
* 1099-MISC files only.
* Singly payer only. For multiple payers, use multiple input files.
"""
import os.path
import json
from time import gmtime, strftime
import click
from jsonschema import validate

from fire.entities import transmitter, payer, payees, end_of_payer, \
                          state_totals, end_of_transmission
from .util import SequenceGenerator, combined_fed_state_code

@click.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.option('--output', type=click.Path(),
              help='system path for the output to be generated')
@click.option('--debug', is_flag=True,
              help='toggle debug/verbose mode')
def cli(input_path, output, debug):
    """
    Convert a JSON input file into the format required by IRS Publication 1220

    \b
    input_path: system path for file containing the user input JSON data
    """
    run(input_path, output, debug)

def run(input_path, output_path, debug):
    """
    Sequentially calls helper functions to fully process :
    * Load user JSON data from input file
    * Transform user data and merge into a master schema
    * Generate and insert computed values into master
    * Format ASCII string representing user- and system-generated data
    * Write ASCII string to output file

    Parameters
    ----------
    input_path : str
        system path for file containing the user input JSON data
    output : str
        optional system path for the output to be generated
    debug : bool
        optional bool to output debug information

    """
    module_path = os.path.split(os.path.realpath(__file__))[0]
    schema_path = os.path.join(module_path, '../schema', 'base_schema.json')
    input_dirname = os.path.dirname(os.path.abspath(input_path))

    user_data = extract_user_data(input_path)
    validate_user_data(user_data, schema_path)

    master = load_full_schema(user_data)
    insert_generated_values(master)
    if debug:
        print(json.dumps(master, indent=4))

    ascii_string = get_fire_format(master)

    if output_path is None:
        output_path = "{}/fire_{}_output_{}".format(input_dirname,
                                                    master["transmitter"]["payment_year"],
                                                    strftime("%Y-%m-%d %H_%M_%S", gmtime()))
    write_1099_file(ascii_string, output_path)


def extract_user_data(path):
    """
    Opens file at path specified by input parameter. Reads data as JSON and
    returns a dict containing that JSON data.

    Parameters
    ----------
    path : str
        system path for file containing the user input JSON data

    Returns
    ----------
    dict
        JSON data loaded from file at input path
    """
    user_data = {}
    with open(path, mode='r', encoding='utf-8') as file:
        user_data = json.load(file)
    return user_data

def validate_user_data(data, schema_path):
    """
    Validates data (first param) against the base schema (second param)

    Parameters
    ----------
    data : dict
        data to be validated

    schema_path: str
        system path for file containing schema to data validate against

    """
    with open(schema_path, mode='r', encoding='utf-8') as schema:
        schema = json.load(schema)
        validate(data, schema)

def load_full_schema(data):
    """
    Merges data into the master schema for records, including fields that were
    not specified in the data originally loaded (such as system-generated fields
    and optional fields).

    Parameters
    ----------
    data : dict
        JSON data to be merged into master schema

    Returns
    ----------
    dict
        Master schema with all fields provided in input parameter included

    """
    merged_data = {"transmitter": "", "payers": [], "end_of_transmission": ""}

    merged_data["transmitter"] = transmitter.xform(data["transmitter"])
    for current_payer in data["payers"]:
        payer_merged_data = payer.xform(current_payer)
        payer_merged_data["payees"] = payees.xform(current_payer["payees"])
        payer_merged_data["end_of_payer"] = end_of_payer.xform({})
        merged_data["payers"].append(payer_merged_data)
    merged_data["end_of_transmission"] = end_of_transmission.xform({})

    return merged_data

def insert_generated_values(data):
    """
    Inserts system-generated values into the appropriate fields. _Note: this
    edits the dict object provided as a parameter in-place._

    Examples of fields inserted: [all]::record_sequence_number,
    payer::number_of_payees, transmitter::total_number_of_payees, etc.

    Parameters
    ----------
    data : dict
        Dictionary containing "master" set of records. It is expected that
        this includes end_of_payer and end_of_transmission records, with all
        fields captured.

    """
    insert_payers_totals(data)
    insert_transmitter_totals(data)
    create_and_insert_state_totals(data)
    insert_sequence_numbers(data)

def insert_sequence_numbers(data):
    """
    Inserts sequence numbers into each record, in the following order:
    transmitter, payer, payee(s) (each in order supplied by user),
    end of payer, state totals, end of transmission.

    _Note: this edits the input parameter in-place._

    Parameters
    ----------
    data : dict
        Dictionary into which sequence numbers will be inserted.

    """
    seq = SequenceGenerator()

    data["transmitter"]["record_sequence_number"] = seq.get_next()
    for current_payer in data["payers"]:
        current_payer["record_sequence_number"] = seq.get_next()
        for payee in current_payer["payees"]:
            payee["record_sequence_number"] = seq.get_next()
        current_payer["end_of_payer"]["record_sequence_number"] = seq.get_next()
        if "state_totals" in current_payer:
            for state_total in current_payer["state_totals"]:
                state_total["record_sequence_number"] = seq.get_next()
    data["end_of_transmission"]["record_sequence_number"] = seq.get_next()

def insert_payers_totals(data):
    """
    Inserts requried values into the payer(s) and end_of_payer records. This
    includes values for the following fields: payment_amount_*,
    amount_codes, number_of_payees, total_number_of_payees, number_of_a_records.

    _Note: this edits the input parameter in-place._

    Parameters
    ----------
    data : dict
        Dictionary containing payer, payee, and end_of_payer records, into which
        computed values will be inserted.

    """
    for current_payer in data["payers"]:
        insert_payer_totals(current_payer)

def insert_payer_totals(current_payer):
    """
    Inserts required values into a single payer record.
    _Note: this edits the input parameter in-place._
    """
    codes = ["1", "2", "3", "4", "5", "6", "7", "8", "9",
             "A", "B", "C", "D", "E", "F", "G"]
    totals = [0 for _ in range(len(codes))]
    payer_code_string = ""

    for payee in current_payer["payees"]:
        for i, code in enumerate(codes):
            try:
                totals[i] += int(payee["payment_amount_" + code])
            except ValueError:
                pass

    for i, (total, code) in enumerate(zip(totals, codes)):
        if total != 0:
            payer_code_string += code
            current_payer["end_of_payer"]["payment_amount_" + code] = f"{total:0>18}"

    current_payer["amount_codes"] = str(payer_code_string)
    payee_count = len(current_payer["payees"])
    current_payer["end_of_payer"]["number_of_payees"] = f"{payee_count:0>8}"

def insert_transmitter_totals(data):
    """
    Inserts requried values into the transmitter and end_of_transmission
    records. This includes values for the following fields:
    total_number_of_payees, number_of_a_records.

    _Note: this edits the input parameter in-place._

    Parameters
    ----------
    data : dict
        Dictionary containing transmitter and end_of_transmission records,
        into which computed values will be inserted.

    """
    payee_count = 0
    for current_payer in data["payers"]:
        payee_count += len(current_payer["payees"])
    payer_count = len(data["payers"])

    data["transmitter"]["total_number_of_payees"] = f"{payee_count:0>8}"
    data["end_of_transmission"]["total_number_of_payees"] = f"{payee_count:0>8}"
    data["end_of_transmission"]["number_of_a_records"] = f"{payer_count:0>8}"

def create_and_insert_state_totals(data):
    """
    Creates and inserts required values into the payer(s)' state totals records.
    This creates all the necessary K records, with the only requirement that
    the payer's "combined_fed_state" field be set to "1".
    If it is not set, then state totals are skipped.

    _Note: this edits the input parameter in-place._

    Parameters
    ----------
    data : dict
        Dictionary containing payer records, into which
        computed values will be inserted.

    """
    for current_payer in data["payers"]:
        insert_state_totals(current_payer)
        insert_payee_state_codes(current_payer)

def insert_state_totals(current_payer):
    """
    Inserts required values into a single payer record.
    If payer "combined_fed_state" is not set to "1", this is skipped
    and no modifications/additions are made.

    The following fields are calculated/inserted:
        - number_of_payees
        - combined_federal_state_code

    _Note: this edits the input parameter in-place._
    """
    codes = ["1", "2", "3", "4", "5", "6", "7", "8", "9",
             "A", "B", "C", "D", "E", "F", "G"]
    states = {}

    if current_payer["combined_fed_state"] != '1':
        return

    for payee in current_payer["payees"]:
        state = payee["payee_state"]
        state_code = combined_fed_state_code(state)
        if not state_code:
            # Payee's state not participating in CF/SF program; skip this payee
            continue

        if state not in states:
            states[state] = dict(number_of_payees=0, combined_federal_state_code=state_code)
        states[state]['number_of_payees'] += 1
        for i, code in enumerate(codes):
            try:
                payment_bucket = f"payment_amount_{code}"
                amount = int(payee[payment_bucket])
                if payment_bucket not in states[state]:
                    states[state][payment_bucket] = 0
                states[state][payment_bucket] += amount
            except ValueError:
                pass

    if states:
        # Convert calculated values to strings for output
        for key in states:
            state = states[key]
            state['number_of_payees'] = f"{state['number_of_payees']:0>8}"
            state['combined_federal_state_code'] = f"{state['combined_federal_state_code']:0>2}"
            for code in codes:
                payment_bucket = f"payment_amount_{code}"
                if payment_bucket in state:
                    state[payment_bucket] = f"{state[payment_bucket]:0>18}"

        # We couldn't do the below earlier (unlike the other record types)
        # since the number of K records has to be determined first before
        # we can xform.
        current_payer["state_totals"] = state_totals.xform(states.values())

def insert_payee_state_codes(current_payer):
    """
    Inserts the IRS FIRE state code for the payer's payees,
    but only if:
        1. The payer's "combined_fed_state" field is set to "1", and
        2. The payee's state is participating in the CF/SF program.

    _Note: this edits the input parameter in-place._
    """
    if current_payer["combined_fed_state"] != '1':
        return

    for payee in current_payer["payees"]:
        state = payee["payee_state"]
        state_code = combined_fed_state_code(state)
        if state_code:
            payee["combined_federal_state_code"] = f"{state_code:0>2}"

def get_fire_format(data):
    """
    Returns the input dictionary converted into the string format required by
    the IRS FIRE electronic filing system. It is expected that the input
    dictionary has the following correctly formatted items:
    * transmitter (dict)
    * payer(s) (dict)
    *   payees (array of dict objects)
    *   end_of_payer (dict)
    * end_of_transmission

    Parameters
    ----------
    data : dict
        Dictionary containing records to be processed into a FIRE-formatted
        string.

    Returns
    ----------
    str
        FIRE-formatted string containing data provided as the input parameter.

    """
    fire_string = ""

    fire_string += transmitter.fire(data["transmitter"])
    for current_payer in data["payers"]:
        fire_string += payer.fire(current_payer)
        fire_string += payees.fire(current_payer["payees"])
        fire_string += end_of_payer.fire(current_payer["end_of_payer"])
        if current_payer["combined_fed_state"] == '1':
            fire_string += state_totals.fire(current_payer["state_totals"])
    fire_string += end_of_transmission.fire(data["end_of_transmission"])

    return fire_string

def write_1099_file(formatted_string, path):
    """
    Writes the given string to a file at the given path. If the file does not
    exist, it will be created.

    Parameters
    ----------
    formatted_string : str
        FIRE-formatted string to be written to disk.

    path: str
        Path of file to be written.

    """
    file = open(path, mode='w+')
    file.write(formatted_string)
    file.close()
