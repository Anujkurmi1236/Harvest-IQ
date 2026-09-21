"""Run the Harvest-IQ FastAPI application with Uvicorn."""

import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Harvest-IQ API.")
    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "127.0.0.1"),
        help="Host interface to bind to (default: HOST or 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port to listen on (default: PORT or 8000).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Reload the server when source files change.",
    )
    args = parser.parse_args()

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
