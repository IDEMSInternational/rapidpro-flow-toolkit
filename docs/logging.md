# Logging

The logging configuration of the toolkit can be overridden via a JSON file called 'logging.json', located in the current working directory. The contents of the JSON file will be converted into a Python dictionary and passed to `logging.config.dictConfig`. See [Dictionary Schema Details] for information about what can be included in the configuration file.

## Export default configuration to JSON

As a starting point, the default configuration should be exported to JSON for modification.

```sh
python -c 'import json; from rpft.logger import DEFAULT_CONFIG; print(json.dumps(DEFAULT_CONFIG, indent=2))' > logging.json
```

## Change the log level of the console handler

A common modification, for debugging, might be to increase the verbosity of the logging messages that appear in the console. The key `handlers.console.level` should be changed to `INFO`. To set the level to `DEBUG` requires setting the key `root.level` to `DEBUG` as well.


[Dictionary Schema Details]: https://docs.python.org/3/library/logging.config.html#dictionary-schema-details
