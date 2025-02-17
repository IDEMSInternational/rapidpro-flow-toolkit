# Google Sheets

It is possible to read in spreadsheets via the Google Sheets API by specifying `--format=google_sheets` on the command line. Spreadsheets must be in the Google Sheets format rather than XLSX, CSV, etc.

Instead of specifying paths to individual spreadsheets on your local filesystem, you must supply the IDs of the Sheets you want to process. The ID can be extracted from the URL of the Sheet i.e. docs.google.com/spreadsheets/d/**ID**/edit.

The toolkit will need to authenticate with the Google Sheets API and be authorized to access your spreadsheets. Two methods for doing this are supported.

- **OAuth 2.0 for installed applications**: for cases where human interaction is possible e.g. when using the CLI
- **Service accounts**: for cases where interaction is not possible or desired e.g. in automated pipelines

## Installed applications

Follow the steps in the [setup your environment section][1] of the Google Sheets quickstart for Python.

Once you have a `credentials.json` file in your current working directory, the toolkit will automatically use it to authenticate whenever you use the toolkit. The refresh token (`token.json`) will be saved automatically in the current working directory so that it is not necessary to go through the full authentication process every time.

## Service accounts

Follow the steps in the [creating a service account section][2] to obtain a service account key. The toolkit will accept the key as an environment variable called `CREDENTIALS`.

```sh
export CREDENTIALS=$(cat service-account-key.json)
rpft ...
```


[1]: https://developers.google.com/sheets/api/quickstart/python#set_up_your_environment
[2]: https://developers.google.com/identity/protocols/oauth2/service-account#creatinganaccount
