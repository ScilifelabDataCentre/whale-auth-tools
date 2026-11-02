"""Command-line utilities for deployment secret generation."""

import argparse
import json

from whale_auth_tools.altcha_service import generate_secrets


def main() -> None:
    parser = argparse.ArgumentParser(description="Whale Auth Tools utilities")
    parser.add_argument(
        "command", choices=["generate-altcha-secrets"], help="Utility to run"
    )
    arguments = parser.parse_args()
    if arguments.command == "generate-altcha-secrets":
        print(json.dumps(generate_secrets(), indent=2))
