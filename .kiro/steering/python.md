---
inclusion: fileMatch
fileMatchPattern: '**/*.py'
---

# Python Development Steering

## Version and compatibility

- Target the Python version required by Home Assistant 2026.8 (**Python 3.13**). Do not use
  syntax or stdlib features newer than that baseline.
- No dependencies on features removed or deprecated in the target HA version.

## Type hints

- Full type hints on every function signature, including `-> None`.
- Use modern typing: `list[...]`, `dict[...]`, `X | None`, `type` aliases. No `Optional`,
  `List`, `Dict` from `typing` unless required for a specific construct.
- Model structured data with `@dataclass(slots=True)` or `TypedDict`; avoid passing loose
  dicts across module boundaries.
- Code must pass `mypy --strict` (or the HA-recommended mypy config) with no ignores added
  casually. Justify any `# type: ignore` inline.

## Async patterns

- Public integration functions are `async`. Never call blocking I/O directly in the loop.
- Offload CPU-bound or blocking work with `hass.async_add_executor_job`.
- Guard shared mutable state (grace-period timers, in-flight sync) with `asyncio.Lock`
  where concurrent access is possible.
- Always set timeouts on awaited I/O; never `await` unbounded operations.

## Code organization

- Keep the pure categorization logic (`categorizer.py`) free of any `homeassistant` import so
  it can be unit-tested standalone.
- One responsibility per module (see architecture steering table).
- **Favour small, focused modules over a single large file.** If a module grows past a few
  hundred lines or takes on a second responsibility, split it (e.g. keep config flow, options
  flow, coordinator, services, and entities in separate files rather than one `__init__.py`).
  Smaller files are easier to review, test, and reason about.
- Constants in `const.py`. No magic strings for the domain, service names, attribute keys,
  or storage keys — reference constants.

## Dependency management

- Prefer the standard library. The categorizer should need no third-party packages; if fuzzy
  matching is added, prefer `difflib` (stdlib) before pulling in `rapidfuzz` or similar.
- Any third-party requirement must be pinned in `manifest.json` `requirements` with an exact
  version and justified in the PR and design doc.

## Error handling

- Catch narrow exceptions, never bare `except:`.
- Convert low-level failures into `HomeAssistantError` (or subclasses) at the service
  boundary with a translatable message.
- Fail loud in logs, degrade gracefully in behavior (e.g. unmatched item -> `Uncategorized`,
  never crash the coordinator).

## Logging

- Module-level logger: `_LOGGER = logging.getLogger(__name__)`.
- `debug` for per-item categorization decisions and sync detail; `info` sparingly; `warning`
  for recoverable sync failures; `error` for exhausted retries.
- Never log credentials, tokens, or full personal shopping contents at `info` or above. Item
  text may be logged at `debug` only.

## Documentation

- Module and public-function docstrings explaining intent, not mechanics.
- Keep the frontend/backend contract (sensor attribute schema, service signatures)
  documented in one place and referenced, not duplicated.
