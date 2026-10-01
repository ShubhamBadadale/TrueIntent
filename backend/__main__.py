"""Start the TrueIntent API with one command (from the repo root):

    .\\.venv\\Scripts\\python.exe -m backend --port 8000

Options mirror uvicorn's most useful flags. ``--reload`` is for development;
production should run behind a process manager with explicit workers.
"""
from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='python -m backend',
        description='Start the TrueIntent FastAPI backend.',
    )
    parser.add_argument('--host', default=None,
                        help='Bind address (default: TRUEINTENT_HOST or 127.0.0.1)')
    parser.add_argument('--port', type=int, default=None,
                        help='Port (default: TRUEINTENT_PORT or 8000)')
    parser.add_argument('--reload', action='store_true',
                        help='Auto-reload on code changes (development only)')
    parser.add_argument('--workers', type=int, default=1,
                        help='Worker processes (ignored with --reload)')
    parser.add_argument('--log-level', default=None,
                        choices=['debug', 'info', 'warning', 'error', 'critical'],
                        help='Uvicorn log level (default: TRUEINTENT_LOG_LEVEL or info)')
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Read last so the CLI wins over the environment.
    from backend.app.config import SETTINGS

    host = args.host or SETTINGS.host
    port = args.port or SETTINGS.port

    import uvicorn

    try:
        uvicorn.run(
            'backend.app.main:app',
            host=host,
            port=port,
            reload=args.reload,
            workers=1 if args.reload else max(1, args.workers),
            log_level=(args.log_level or SETTINGS.log_level).lower(),
            # The application configures its own logging (request IDs,
            # structured format); uvicorn's default config would undo that.
            log_config=None,
        )
    except ValueError as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
