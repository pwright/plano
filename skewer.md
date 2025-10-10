# Skewer variant of plano

## Implementation Differences
- Directory discovery: `find()` uses `str.removeprefix()` in the native code (`src/plano/main.py:281`), while the Skewer snapshot backports the behaviour through a custom `remove_prefix()` helper (`skewer-plano/src/plano/main.py:281`, `skewer-plano/src/plano/main.py:1435`). This keeps Skewer/Transom compatible with older Python runtimes that lack `str.removeprefix`.
- String replacement API: The native library offers `string_replace_in_file()` (`src/plano/main.py:695`), a literal string replace. Skewer renames this to `string_replace_file()` and routes it through the regex-powered `string_replace()` wrapper (`skewer-plano/src/plano/main.py:698`, `skewer-plano/src/plano/main.py:1433`), changing both the name and the matching semantics.
- HTTP helpers: Support for supplying client certificates and CA bundles through `_run_curl()` and the `http_*` wrappers exists only in the native tree (`src/plano/main.py:762-817`). The Skewer/Transom copy removed those keyword arguments (`skewer-plano/src/plano/main.py:762-814`), so TLS client-auth scenarios are no longer surfaced.
- String utilities: The native build exposes `string_replace_re()`, `string_matches_re()`, and `string_matches_glob()` (`src/plano/main.py:1470-1484`). Skewer replaces them with `string_replace()` plus the new `remove_prefix()` / `remove_suffix()` helpers but omits the regex/glob predicates entirely (`skewer-plano/src/plano/main.py:1433-1461`), reducing the public API surface.
- Builder helper removal: The convenience `StringBuilder` class is present only in the native variant (`src/plano/main.py:1539-1567`). Skewer/Transom dropped the class, so callers that rely on it must import from the root module.
- Formatting tweak: Native code uses `str.removesuffix()` in `format_bytes()` (`src/plano/main.py:1678`), whereas Skewer keeps parity by reusing `remove_suffix()` (`skewer-plano/src/plano/main.py:1623`).

## Test Suite Adjustments
- The native tests exercise the regex/glob helpers and `StringBuilder` behaviours (`src/plano/_tests.py:867-975`).
- Skewer’s `_tests.py` substitutes coverage for the new `remove_prefix()` / `remove_suffix()` helpers and drops the `StringBuilder` assertions to reflect the trimmed API (`skewer-plano/src/plano/_tests.py:867-947`).
