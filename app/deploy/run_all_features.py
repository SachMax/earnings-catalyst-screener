"""Run active feature scripts in explicit dependency order."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
FEATURES_DIR = ROOT / "app" / "features"

# Scripts execute from top to bottom. Keep prerequisites before dependents.
FEATURE_ORDER = [
    # Prerequisites
    "feature_sector.py",
    "feature_sector_relative_strength.py",
    "feature_runup.py",
    "feature_implied_move.py",
    # Fundamental and analyst features
    "feature_analyst_consensus.py",
    "feature_analyst_momentum.py",
    "feature_analyst_revision.py",
    "feature_current_earnings_quality.py",
    "feature_historical_earnings_quality.py",
    "feature_gaap_profit.py",
    "feature_eps_streak.py",
    "feature_valuation.py",
    "feature_valuation_v2.py",
    # Independent technical and market features
    "feature_rsi.py",
    "feature_volume_confirmation.py",
    "feature_short_interest.py",
    "feature_sue.py",
    "feature_insider_transactions.py",
    "feature_past_earnings_action.py",
    "feature_post_earnings_drift.py",
    "feature_pullback_bounce.py",
    "feature_options_sentiment.py",
    # Dependent and final features
    "feature_iv_hv_ratio.py",
    "feature_runup_hist_avg.py",
    "feature_seasonality.py",
    "feature_capex_sentiment.py",
    "feature_remaining.py",
    "feature_trifecta.py",
]


def validate_features():
    """Check the explicit list before executing any scripts."""
    registered = set(FEATURE_ORDER)
    if len(registered) != len(FEATURE_ORDER):
        raise SystemExit("Duplicate feature filenames in FEATURE_ORDER.")

    discovered = {p.name for p in FEATURES_DIR.glob("feature_*.py") if p.is_file()}
    missing = registered - discovered
    unregistered = discovered - registered
    if missing or unregistered:
        raise SystemExit(
            f"Feature registration error. Missing: {sorted(missing)}; "
            f"Unregistered: {sorted(unregistered)}"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print order without executing")
    args = parser.parse_args()
    validate_features()
    print(f"Found {len(FEATURE_ORDER)} registered feature scripts", flush=True)
    # Allow direct execution as well as execution from run_daily.bat.
    env = os.environ.copy()
    paths = [str(ROOT / "app"), str(ROOT)]
    if env.get("PYTHONPATH"):
        paths.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(paths)
    for i, name in enumerate(FEATURE_ORDER, 1):
        print(f"[{i}/{len(FEATURE_ORDER)}] {name}", flush=True)
        if args.dry_run:
            continue
        result = subprocess.run(
            [sys.executable, "-u", str(FEATURES_DIR / name)],
            cwd=ROOT, env=env, check=False,
        )
        if result.returncode != 0:
            print(f"Stopped: {name} exited with {result.returncode}", file=sys.stderr)
            raise SystemExit(result.returncode if result.returncode > 0 else 1)
    print("Dry run completed." if args.dry_run else "All feature scripts completed.")


if __name__ == "__main__":
    main()
