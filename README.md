# What this is
Fire-1099 helps you stop wasting ~$10 per page on 1099 filings.

Specifically, it generates 1099 tax filings formatted for the IRS electronic filing system. This repo builds upon the excellent original [fire-1099](https://github.com/sdj0/fire-1099) work by Stephen Johnson by adding support for multiple payers and the combined federal/state filing program.

A lot of small companies don't realize they have to file 1099s for most payments to lawyers, as well as independent contractors. The IRS has a system called "FIRE" for electronically submitting these filings, and others like stock options exercise forms. These filings can *only* be filed through this system. If you're used to modern REST APIs, you'll probably find FIRE unpleasant to use. It's inflexible, has an ambiguous spec, and operates on the byte (ASCII code) level.

With fire-1099, you simply enter your form data in a JSON file [like this one](https://github.com/iterateco/iterateco-fire-1099/blob/master/spec/data/valid_minimal.json) and run it through the program. It validates your data against the IRS spec, auto-formats it where possible, and writes it to a file that can be uploaded straight to FIRE.

I should point out getting access to the FIRE system is non-trivial; it can take a couple of weeks. See below for a link to the form needed.

Please note that currently Fire-1099 only supports 1099-MISC filings.

# Using fire-1099
To install the fire-1099 CLI, clone this repository and run the following command from the repository root directory: `pip install .`

The CLI for generating FIRE-formatted files accepts two basic parameters: an input file path and an (optional) output file path.


`fire-1099 path/to/input-file.json --output path/to/output-file.ascii`


## The input JSON file
The input file should be JSON-formatted according to the schema defined in the `/schema` folder of this repo. The output file given by `--output` is optional, and will default to a timestamped filename in the same directory as the input file. Not all fields in the input file are required. I recommend using the file `/spec/data/valid-minimal.json` as a starting point if you're not comfortable with the schema file itself.

To determine what fields are required, take a look at the schema.

Regarding amounts, enter only whole amounts (do not use dollar signs, commas, decimals etc). For example if a payment amount is "$2.50", use the value "250" in the JSON file.

## Developers
There's one additional optional argument (`--debug`) for the cli. Including this argument will make the cli output the full processed json data that it used to generate the actual FIRE file. This argument is useful to determine what values have been processed and what will be included into the fire file.


## API (Translator Module)
As an alternative to the CLI, the `translator` module exposes a number of functions for generating FIRE-formatted files programatically.


To run the file generation process end-to-end (similar to using the CLI), use `translator.run(str, str)`. Example:

```python
import translator

input_path = "/path/to/input_file.json"
output_path = "/path/to/output_file.ascii"

translator.run(input_path, output_path)
```


A more step-by-step interaction is also available:

```python
import translator

input_path = "/path/to/input_file.json"
output_path = "/path/to/output_file.ascii"

# Load input file and validate against schema
user_data = extract_user_data(input_path)
validate_user_data(user_data, schema_path)

# Incorporate default values and system-generated data
master = load_full_schema(user_data)
insert_generated_values(master)

# Generate ASCII string formatted to IRS 1220 spec, and write to file
ascii_string = get_fire_format(master)
write_1099_file(ascii_string, output_path)
```

# Multiple payer support
You can add multiple payers as the format of the schema allows for it. The high-level organization is the following:
```
{
    "transmitter": {
        ... transmitter data here ...
    },
    "payers": [
        {
            ... payer 1 data ...
            "payees": [
                {
                    ... payee 1 data ...
                },
                {
                    ... payee 2 data ...
                },
                {
                    ... and so forth ...
                }
            ]
        },
        {
            ... payer 2 data ...
        },
        {
            ... and so forth ...
        }
    ]
}
```
If you have only one payer, just specify an array with only one payer entry.

# Combined Federal/State Filing (CF/SF)
Support for Combined Federal/State Filing coding is implemented.

For every payer, add a field named "`combined_fed_state`" with a value of "`1`" and everything else will be created/filled in with regards to CF/SF. Every applicable payee with have their state code set and all the requisite "K" records will be created for the payer(s).

Payees in states that don't participate in the CF/SF program will not be included in the K records and their state code will be blank (as specified by the IRS).

Note that the schema contains a definition for "state_totals" but you don't have to include that in your input json. That definition is used internally to create the K records.

# Access via IRS FIRE System
A few things need to happen before you can submit an output file to the IRS:

* You need a *Transmitter Control Code* or "TCC." This is done by filing From 4419 electronically (https://fire.irs.gov). It can take 45 days to get a response.
* You need to have a valid business tax identification code (EIN/TIN). This will be linked to your TCC, and is what you'll use for the "transmitter" record in your FIRE submissions.

For test file submissions, you can input fake data *except* for your TCC. The IRS FIRE test site checks your account TCC against the TCC in the submission file, so make sure it matches.

# TODO:
- Fix `/spec/data/*json` files as they are out-of-date
- Fix tests to work with new multiple payer support
- Fix tests to work with new CF/SF support

# Future Work
* Add support for "Extension of Time" requests
* Add support for filings other than 1099-MISC
* Improve schema regex validations
* Add validation logic for more obscure fields


