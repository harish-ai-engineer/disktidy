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
from . import render
from .util import human_size, make_style


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

    print(render.banner(style))

    print(render.heading(style, "Drives"))

    def plain_bar(frac, width=14):
        frac = min(max(frac, 0.0), 1.0)
        filled = int(round(frac * width))
        return "█" * filled + "░" * (width - filled)

    drow = [[d.name, human_size(d.used), human_size(d.free), human_size(d.total),
             f"{d.pct_free:.0f}%", plain_bar((d.used / d.total) if d.total else 0)]
            for d in drives]

    def drive_style(ri, ci, padded, raw):
        d = drives[ri]
        if ci == 4:  # Free%
            fn = style.bright_red if d.pct_free < 10 else style.bright_yellow if d.pct_free < 20 else style.bright_green
            return fn(padded)
        if ci == 5:  # usage bar — color by how full the drive is
            frac = (d.used / d.total) if d.total else 0
            fn = style.bright_red if frac >= 0.9 else style.bright_yellow if frac >= 0.8 else style.bright_cyan
            return fn(padded)
        return style.dim(padded)

    print(render.table(
        ["Drive", "Used", "Free", "Total", "Free%", "Usage"],
        drow, style, aligns=["l", "r", "r", "r", "r", "l"], cell_style=drive_style))
    for d in drives:
        if d.pct_free < 10:
            print(style.bright_red(f"  ⚠ {d.name} is critically full — {human_size(d.free)} free"))

    print(render.heading(style, "Biggest known space consumers"))
    if not consumers:
        print(style.gray("  (none detected)"))
        return 0

    rows = [[human_size(c.size), c.name, c.safety, c.what] for c in consumers]

    def cons_style(ri, ci, padded, raw):
        c = consumers[ri]
        if ci == 0:
            return render.size_color(style, c.size, padded)
        if ci == 2:
            return render.safety_badge(style, c.safety, padded)
        if ci == 1:
            return style.bold(style.bright_cyan(padded))
        return style.dim(padded)

    print(render.table(["Size", "What", "Safety", "Description"], rows, style,
                       aligns=["r", "l", "l", "l"], cell_style=cons_style))

    safe_total = sum(c.size for c in consumers if c.safety == "safe")
    print(render.kv_line(style, "safe to reclaim now:",
                         style.bright_green(style.bold(human_size(safe_total)))))
    print(style.dim("\n  reclaim commands:"))
    for c in consumers:
        print(f"    {style.bright_magenta('›')} {style.bold(style.bright_cyan(c.name))}: {style.dim(c.reclaim)}")
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

    print(render.banner(style))
    print(render.heading(style, f"Biggest folders under {result.root}"))
    if result.folders:
        rows = [[human_size(f.size), f.path] for f in result.folders]

        def folder_style(ri, ci, padded, raw):
            if ci == 0:
                return render.size_color(style, result.folders[ri].size, padded)
            return style.bright_cyan(padded)

        print(render.table(["Size", "Folder"], rows, style,
                           aligns=["r", "l"], cell_style=folder_style))
    else:
        print(style.gray("  (nothing found)"))

    if args.files:
        print(render.heading(style, "Biggest individual files"))
        if result.files:
            rows = [[human_size(f.size), f.path] for f in result.files]

            def file_style(ri, ci, padded, raw):
                if ci == 0:
                    return render.size_color(style, result.files[ri].size, padded)
                return style.bright_cyan(padded)

            print(render.table(["Size", "File"], rows, style,
                               aligns=["r", "l"], cell_style=file_style))
        else:
            print(style.gray("  (nothing found)"))
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

    print(render.banner(style))
    mode = style.bright_green(style.bold(" APPLY ")) if args.apply else style.bright_blue(style.bold(" DRY-RUN "))
    print(render.heading(style, "Docker reclaim") + f"  {mode}")
    print(style.dim("  only build cache, dangling images and stopped containers are touched"))
    print(style.dim("  volumes and tagged images are never removed"))

    if not args.apply:
        print()
        print(docker_mod.df())

    print()
    for step in docker_mod.safe_prune(apply=args.apply):
        mark = style.bright_green("✓") if step.ok else style.bright_red("✗")
        print(f"  {mark} {style.bold(style.bright_cyan(step.label))}: {style.dim(step.detail)}")

    if args.compact:
        print(render.heading(style, "Compact virtual disk"))
        for step in docker_mod.compact_vhdx(apply=args.apply):
            mark = style.bright_green("✓") if step.ok else style.bright_red("✗")
            print(f"  {mark} {style.bold(style.bright_cyan(step.label))}: {style.dim(step.detail)}")

    if not args.apply:
        print(style.dim("\n  re-run with ") + style.bright_magenta("--apply") +
              style.dim(" to execute (add ") + style.bright_magenta("--compact") +
              style.dim(" to shrink the vhdx)"))
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
    print(render.banner(style))
    mode = style.bright_green(style.bold(" APPLY ")) if args.apply else style.bright_blue(style.bold(" DRY-RUN "))
    print(render.heading(style, "Package caches") +
          f"  {mode}  {style.dim('total')} {style.bold(style.bright_yellow(human_size(total)))}")

    rows = [[human_size(e.size), e.name, e.path] for e in entries]

    def cache_style(ri, ci, padded, raw):
        if ci == 0:
            return render.size_color(style, entries[ri].size, padded)
        if ci == 1:
            return style.bold(style.bright_magenta(padded))
        return style.bright_blue(padded)

    print(render.table(["Size", "Tool", "Path"], rows, style,
                       aligns=["r", "l", "l"], cell_style=cache_style))

    if not args.apply:
        print(style.dim("\n  re-run with ") + style.bright_magenta("--apply") +
              style.dim(" to clean (safe — caches rebuild on demand)"))
        return 0

    print()
    for e in entries:
        ok, detail = caches_mod.clean(e)
        mark = style.bright_green("✓") if ok else style.bright_red("✗")
        print(f"  {mark} {style.bold(style.bright_cyan(e.name))}: {style.dim(detail)}")
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
