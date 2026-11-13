# C++ Decklist SAX Parser

The C++20 `_deck_sax` module contained here handles all decklist JSON parsing and filtering for `mtgo_decklist_analyzer` when retrieving, filtering, and displaying metagame stats. This results in virtually no waiting for query results, regardless of what filters are chosen or what dataset is used.

It replaces the traditional Python parser (e.g. `orjson`) which had to read all JSON contents before filtering. The new SAX parser built with `RapidJSON` rejects entries efficiently during parsing as soon as one filter condition is violated. It also aggregates card frequency statistics during the same pass. Several techniques are used to reduce memory usage and improve speed compared to the previously used Python solution. Its results are seamlessly integrated into the existing modules via `nanobind`.



## Performance Benchmarks

Tested in November 2026 on the full Modern dataset (125 MB) in a WSL environment.

Each query filters decks using realistic parameters and outputs card frequencies, averaged over 50 runs from scratch per parser.

| Filter Scenario | Original Python Parser | C++ SAX Parser | Speedup |
| :--- | :---: | :---: | :---: |
| No filters | 2.27s | 0.25s | **9.2x** |
| Only mainboard | 1.62s | 0.25s | **6.4x** |
| Only leagues | 1.22s | 0.24s | **5.1x** |
| Only 1 player | 0.72s | 0.10s | **7.1x** |
| 1 card whitelist | 1.23s | 0.18s | **6.8x** |
| 2 card whitelist | 1.12s | 0.19s | **6.0x** |
| 1 card blacklist | 1.56s | 0.23s | **7.0x** |
| 1 card whitelist + 1 card blacklist | 1.17s | 0.19s | **6.3x** |
| Date range (`1-1-2026` to `11-1-2026`) | 0.79s | 0.11s | **7.1x** |
| **Total (all queries)** | **11.70s** | **1.73s** | **6.8x** |
