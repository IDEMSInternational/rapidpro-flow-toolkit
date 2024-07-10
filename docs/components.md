# Components

This toolkit consists of three components.

The first component ([](/src/rpft/parsers/common)) is RapidPro-agnostic and takes care of reader spreadsheets and converting them into internal data models and other output formats, see [](sheets.md)

The second component ([](/src/rpft/parsers/creation)) defines data models for a spreadsheet format for RapidPro flows, and process spreadsheets into RapidPro flows (and back) using the first component.

The third component ([](/src/rpft/rapidpro)) defines internal representations of RapidPro flows and to read and write to a JSON format that can be import to/exported from RapidPro. It is partially entangled with the second component, as it needs to be aware of the data models of the second component to convert RapidPro flows into the spreadsheet format.

The latter two components are (poorly) documented here: [](rapidpro.md)
