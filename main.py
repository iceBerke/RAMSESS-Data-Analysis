"""Single entry point. Argument parsing and dispatch only."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ramsess.io import list_experiments, load_experiment  # noqa: E402
from ramsess.report import (  # noqa: E402
    HardCheckFailure,
    common_window_ranges,
    hard_failures,
    load_bands_config,
    print_baseline_config,
    print_report,
    quantify_experiment,
    resolve_baseline_config,
    write_sample_overlays,
)

RAW_ROOT = PROJECT_ROOT / "data" / "raw"
FIGURES_ROOT = PROJECT_ROOT / "figures"
DERIVED_ROOT = PROJECT_ROOT / "data" / "derived"


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch to the requested subcommand.

    Args:
        argv: Command-line arguments, defaulting to ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="RAMSESS spectra tooling.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect = subparsers.add_parser("inspect", help="print an inventory and consistency report")
    inspect.add_argument("--experiment", help="name of the folder under data/raw/")
    inspect.add_argument(
        "--strict", action="store_true", help="exit non-zero if any hard check fires"
    )

    plot = subparsers.add_parser("plot", help="write one overlay figure per sample")
    plot.add_argument("--experiment", help="name of the folder under data/raw/")
    plot.add_argument("--sample", help="restrict output to this sample")
    plot.add_argument("--logy", action="store_true", help="use a log y-scale on both panels")
    plot.add_argument(
        "--force", action="store_true", help="draw even if hard checks fail"
    )
    plot.add_argument(
        "--baseline",
        action="store_true",
        help="draw baseline-corrected spectra instead of raw",
    )
    plot.add_argument(
        "--baseline-diagnostic",
        action="store_true",
        help="write a per-window figure showing each fit and its result",
    )
    plot.add_argument(
        "--annotate",
        action="store_true",
        help="label each panel with the bands configured in bands.json",
    )
    plot.add_argument("--baseline-lam", type=float, help="override the baseline smoothness")
    plot.add_argument("--baseline-p", type=float, help="override the baseline asymmetry")
    plot.add_argument(
        "--baseline-n-iter", type=int, help="override the baseline iteration count"
    )

    quantify = subparsers.add_parser(
        "quantify", help="export corrected spectra and measure the configured bands"
    )
    quantify.add_argument("--experiment", help="name of the folder under data/raw/")
    quantify.add_argument("--sample", help="restrict measurement to this sample")
    quantify.add_argument(
        "--force", action="store_true", help="continue even if hard checks fail"
    )

    args = parser.parse_args(argv)

    if args.experiment is None:
        try:
            names = list_experiments(RAW_ROOT)
        except (NotADirectoryError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print("no --experiment given. available experiments:", file=sys.stderr)
        for name in names:
            print(f"  {name}", file=sys.stderr)
        return 1

    try:
        spectra = load_experiment(RAW_ROOT, args.experiment)
    except (NotADirectoryError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.command == "inspect":
        findings = print_report(args.experiment, spectra)
        return 1 if args.strict and hard_failures(findings) else 0

    if args.command == "quantify":
        # No baseline flags here on purpose: derived data must be reproducible
        # from raw plus config alone, never from a value that lived only in
        # someone's shell history.
        try:
            values, sources = resolve_baseline_config(
                RAW_ROOT / args.experiment, {s.window for s in spectra}
            )
            print_baseline_config(values, sources)
            quantify_experiment(
                args.experiment,
                spectra,
                RAW_ROOT,
                DERIVED_ROOT,
                FIGURES_ROOT,
                values,
                sources,
                sample=args.sample,
                force=args.force,
            )
        except HardCheckFailure as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        except (FileNotFoundError, ValueError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        return 0

    baseline_mode = args.baseline or args.baseline_diagnostic
    tuning = {
        "--baseline-lam": args.baseline_lam,
        "--baseline-p": args.baseline_p,
        "--baseline-n-iter": args.baseline_n_iter,
    }
    supplied = [flag for flag, value in tuning.items() if value is not None]
    if supplied and not baseline_mode:
        print(
            f"error: {', '.join(supplied)} requires --baseline or --baseline-diagnostic",
            file=sys.stderr,
        )
        return 1

    baseline_params = None
    if baseline_mode:
        try:
            values, sources = resolve_baseline_config(
                RAW_ROOT / args.experiment,
                {spectrum.window for spectrum in spectra},
                lam=args.baseline_lam,
                p=args.baseline_p,
                n_iter=args.baseline_n_iter,
            )
        except (ValueError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print_baseline_config(values, sources)
        baseline_params = values

    # Only --annotate reads bands.json. Plain plot touches no configuration file
    # at all and must keep working in an experiment that has none.
    bands = None
    if args.annotate:
        try:
            _, bands, _ = load_bands_config(
                RAW_ROOT / args.experiment, common_window_ranges(spectra)
            )
        except FileNotFoundError as exc:
            print(f"error: --annotate needs a band configuration: {exc}", file=sys.stderr)
            return 1
        except (ValueError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    try:
        write_sample_overlays(
            args.experiment,
            spectra,
            FIGURES_ROOT,
            sample=args.sample,
            logy=args.logy,
            force=args.force,
            baseline=args.baseline,
            diagnostic=args.baseline_diagnostic,
            baseline_params=baseline_params,
            annotate=args.annotate,
            bands=bands,
        )
    except HardCheckFailure as exc:
        # The individual failures have already been printed to stderr.
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
