# Contributing

- Business logic lives in `src/services/`, one module per use case.
- Raise `src.errors.AppError(code, message)` for every client-facing failure; never raise bare exceptions from services.
- Log with `src.log.get_logger(__name__)`; `print` is not allowed.
- `src/legacy/` is frozen. Do not copy its patterns.
- Tests mirror source paths under `tests/`.
