# Components

This toolkit consists of three components.

`rpft.parsers.common` is RapidPro-agnostic and takes care of reader spreadsheets and converting them into internal data models and other output formats, see [sheets.md](sheets.md).

`rpft.parsers.creation` defines data models for a spreadsheet format for RapidPro flows, and process spreadsheets into RapidPro flows (and back) using `rpft.parsers.common`.

`rpft.rapidpro` defines internal representations of RapidPro flows, and reads and writes to a JSON format that can be imported to and exported from RapidPro. It is partially entangled with `rpft.parsers.creation` as it needs to be aware of the data models of the second component to convert RapidPro flows into the spreadsheet format.

The latter two components are [documented](rapidpro.md).
