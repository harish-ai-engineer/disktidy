"""disktidy command-line interface.

Philosophy (same as DevTidy): analysis is free and safe; anything that
deletes or modifies the filesystem requires an explicit --apply flag.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__, analyze as analyze_mod
from . import caches as caches_mod
from . import consumers as consumers_mod
from . import docker_reclaim as docker_mod
from .util import human_size, make_style


# --------------------------------------------------------------------------- #
# Tiny table renderer (no third-party deps)
# --------------------------------------------------------------------------- #
def render_table(headers: list[str], rows: list[list[str]], style) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    line = "+".join("-" * (w + 2) for w in widths)
    out = [f"+{line}+"]
    out.append("| " + " | ".join(style.bold(h.ljust(widths[i])) for i, h in enumerate(headers)) + " |")
    out.append(f"+{line}+")
    for row in rows:
        out.append("| " + " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) + " |")
    out.append(f"+{line}+")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# report / default overview
# --------------------------------------------------------------------------- #
def cmd_report(args, style) -> int:
    consumers = consumers_mod.scan_consumers()
    drives = analyze_mod.list_drives()

    if args.json:
        print(json.dumps({
            "drives": [vars(d) | {"pct_free": round(d.pct_free, 1)} for d in drives],
            "consumers": [vars(c) for c in consumers],
        }, indent=2))
        return 0

    print(style.bold("\nDrives"))
    rows = [[d.name, human_size(d.used), human_size(d.free), human_size(d.total),
             f"{d.pct_free:.0f}%"] for d in drives]
    print(render_table(["Drive", "Used", "Free", "Total", "Free%"], rows, style))
    for d in drives:
        if d.pct_free < 10:
            print(style.red(f"  ! {d.name} is critically full ({human_size(d.free)} free)"))

    print(style.bold("\nBiggest known space consumers"))
    if not consumers:
        print("  (none detected)")
        return 0
    colors = {"safe": style.green, "caution": style.yellow, "manual": style.dim}
    rows = []
    for c in consumers:
        tag = colors.get(c.safety, str)(c.safety)
        rows.append([human_size(c.size), c.name, tag, c.what])
    print(render_table(["Size", "What", "Safety", "Description"], rows, style))
    print(style.dim("\n  Reclaim commands:"))
    for c in consumers:
        print(style.dim(f"    - {c.name}: {c.reclaim}"))
    return 0


# --------------------------------------------------------------------------- #
# analyze
# --------------------------------------------------------------------------- #
def cmd_analyze(args, style) -> int:
    root = args.path or os.path.expanduser("~")
    result = analyze_mod.analyze(root, top=args.top, want_files=args.files)

    if args.json:
        print(json.dumps({
            "root": result.root,
            "folders": [vars(f) for f in result.folders],
            "files": [vars(f) for f in result.files],
        }, indent=2))
        return 0

    print(style.bold(f"\nBiggest folders under {result.root}"))
    rows = [[human_size(f.size), f.path] for f in result.folders]
    print(render_table(["Size", "Folder"], rows, style) if rows else "  (nothing found)")

    if args.files:
        print(style.bold("\nBiggest individual files"))
        rows = [[human_size(f.size), f.path] for f in result.files]
        print(render_table(["Size", "File"], rows, style) if rows else "  (nothing found)")
    return 0


# --------------------------------------------------------------------------- #
# docker
# --------------------------------------------------------------------------- #
def cmd_docker(args, style) -> int:
    if not docker_mod.docker_available():
        if args.json:
            print(json.dumps({"error": "docker unavailable"}))
        else:
            print(style.yellow("Docker is not running or not installed — start Docker Desktop first."))
        return 1

    if args.json:
        prune = docker_mod.safe_prune(apply=args.apply)
        result = {"applied": bool(args.apply),
                  "prune": [vars(s) for s in prune]}
        if args.compact:
            result["compact"] = [vars(s) for s in docker_mod.compact_vhdx(apply=args.apply)]
        print(json.dumps(result, indent=2))
        return 0

    mode = style.green("APPLY") if args.apply else style.cyan("DRY-RUN")
    print(style.bold(f"\nDocker reclaim [{mode}]"))
    print(style.dim("Only build cache, dangling images and stopped containers are touched."))
    print(style.dim("Volumes and tagged images are never removed.\n"))

    if not args.apply:
        print(docker_mod.df())

    for step in docker_mod.safe_prune(apply=args.apply):
        mark = style.green("ok") if step.ok else style.red("!!")
        print(f"  [{mark}] {step.label}: {step.detail}")

    if args.compact:
        print(style.bold("\nCompact virtual disk"))
        for step in docker_mod.compact_vhdx(apply=args.apply):
            mark = style.green("ok") if step.ok else style.red("!!")
            print(f"  [{mark}] {step.label}: {step.detail}")

    if not args.apply:
        print(style.dim("\nRe-run with --apply to execute (add --compact to shrink the vhdx)."))
    return 0


# --------------------------------------------------------------------------- #
# caches
# --------------------------------------------------------------------------- #
def cmd_caches(args, style) -> int:
    entries = caches_mod.detect()

    if args.json:
        print(json.dumps({
            "total": sum(e.size for e in entries),
            "caches": [{"name": e.name, "path": e.path, "size": e.size} for e in entries],
            "applied": bool(args.apply),
        }, indent=2))
        if args.apply:
            for e in entries:
                caches_mod.clean(e)
        return 0

    if not entries:
        print("No package-manager caches detected.")
        return 0

    total = sum(e.size for e in entries)
    mode = style.green("APPLY") if args.apply else style.cyan("DRY-RUN")
    print(style.bold(f"\nPackage caches [{mode}] — {human_size(total)} total"))
    rows = [[human_size(e.size), e.name, e.path] for e in entries]
    print(render_table(["Size", "Tool", "Path"], rows, style))

    if not args.apply:
        print(style.dim("\nRe-run with --apply to clean (safe — caches rebuild on demand)."))
        return 0

    for e in entries:
        ok, detail = caches_mod.clean(e)
        mark = style.green("ok") if ok else style.red("!!")
        print(f"  [{mark}] {e.name}: {detail}")
    return 0


# --------------------------------------------------------------------------- #
# argument parsing
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    # Common flags usable both before and after the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--no-color", action="store_true", help="disable colored output")
    common.add_argument("--json", action="store_true", help="machine-readable JSON output")

    p = argparse.ArgumentParser(
        prog="disktidy",
        parents=[common],
        description="Analyze disk usage and safely reclaim space (Docker, caches, more).",
    )
    p.add_argument("--version", action="version", version=f"disktidy {__version__}")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("report", parents=[common],
                   help="drive overview + biggest known consumers (default)")

    a = sub.add_parser("analyze", parents=[common], help="biggest folders/files under a path")
    a.add_argument("path", nargs="?", help="path to analyze (default: home)")
    a.add_argument("--top", type=int, default=15, help="how many entries to show")
    a.add_argument("--files", action="store_true", help="also list biggest individual files")

    d = sub.add_parser("docker", parents=[common], help="safely reclaim Docker space")
    d.add_argument("--apply", action="store_true", help="actually prune (default: dry-run)")
    d.add_argument("--compact", action="store_true", help="also compact the vhdx (Windows, admin)")

    c = sub.add_parser("caches", parents=[common], help="inspect / clean package-manager caches")
    c.add_argument("--apply", action="store_true", help="actually clean (default: dry-run)")

    return p


def main(argv: list[str] | None = None) -> int:
    # Windows consoles often default to a legacy codepage; force UTF-8 so
    # box-drawing and dashes render correctly.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass

    parser = build_parser()
    args = parser.parse_args(argv)
    style = make_style(args.no_color)

    try:
        if args.command == "analyze":
            return cmd_analyze(args, style)
        if args.command == "docker":
            return cmd_docker(args, style)
        if args.command == "caches":
            return cmd_caches(args, style)
        # default / "report"
        return cmd_report(args, style)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
