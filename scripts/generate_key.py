"""CLI tool to generate an API key via the Django admin portal.

Usage:
    docker compose exec admin python ../scripts/generate_key.py --name "My App"

Or from within the admin container:
    cd /app && DJANGO_SETTINGS_MODULE=admin_portal.settings python ../scripts/generate_key.py --name "My App"
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "admin_portal"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "admin_portal.settings")

import django

django.setup()

from django.db import transaction

from keys.models import ApiKey, RateLimitPolicy


def main() -> None:
    """Generate a new API key and print it to stdout."""
    parser = argparse.ArgumentParser(
        description="Generate an API key for the AI API Gateway"
    )
    parser.add_argument("--name", required=True, help="Friendly name for the key")
    parser.add_argument(
        "--scopes", default=None, help="Comma-separated list of allowed model prefixes"
    )
    parser.add_argument(
        "--capacity", type=int, default=60, help="Rate limit bucket capacity"
    )
    parser.add_argument(
        "--refill-rate",
        type=float,
        default=1.0,
        help="Rate limit refill rate (tokens/sec)",
    )
    parser.add_argument(
        "--daily-limit", type=int, default=1_000_000, help="Daily token limit"
    )
    args = parser.parse_args()

    with transaction.atomic():
        api_key, raw_key = ApiKey.generate(name=args.name, scopes=args.scopes)
        api_key.save()

        RateLimitPolicy.objects.create(
            api_key=api_key,
            capacity=args.capacity,
            refill_rate=args.refill_rate,
            daily_token_limit=args.daily_limit,
        )

    print("\n" + "=" * 60)
    print("  API Key Generated Successfully")
    print("=" * 60)
    print(f"  Name:    {api_key.name}")
    print(f"  Prefix:  {api_key.prefix}...")
    print(f"  Key:     {raw_key}")
    print(f"  Key ID:  {api_key.id}")
    print()
    print("  ⚠️  Save this key now — it will NOT be shown again!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
