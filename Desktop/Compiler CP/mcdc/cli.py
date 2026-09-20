from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from .compiler import BACKENDS, build_ir, compile_file
from .diagnostics import Diagnostic, has_errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mcdc")
    sub = parser.add_subparsers(dest="command", required=True)
    compile_p = sub.add_parser("compile")
    compile_p.add_argument("file")
    compile_p.add_argument("--target", choices=[*BACKENDS, "all"], required=True)
    compile_p.add_argument("--out", default="./build")
    compile_p.add_argument("--json-diagnostics", action="store_true")
    check_p = sub.add_parser("check")
    check_p.add_argument("file")
    check_p.add_argument("--json-diagnostics", action="store_true")
    ast_p = sub.add_parser("ast")
    ast_p.add_argument("file")
    ast_p.add_argument("--dot")
    ir_p = sub.add_parser("ir")
    ir_p.add_argument("file")
    ir_p.add_argument("--dot")
    eval_p = sub.add_parser("evaluate")
    eval_p.add_argument("--examples", default="examples")
    args = parser.parse_args(argv)

    if args.command == "compile":
        result = compile_file(Path(args.file), args.target)
        _print_diags(result.diagnostics, args.json_diagnostics)
        if has_errors(result.diagnostics):
            return 1
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        for target, output in result.outputs.items():
            target_dir = out_dir / target
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "main.tf").write_text(output.text)
            (target_dir / "report.json").write_text(json.dumps(output.report | {"timings": result.timings}, indent=2))
        return 0
    if args.command == "check":
        _, diagnostics, _ = build_ir(Path(args.file))
        _print_diags(diagnostics, args.json_diagnostics)
        return 1 if has_errors(diagnostics) else 0
    if args.command == "ast":
        from .lexer_parser import parse_source
        app, diagnostics = parse_source(Path(args.file).read_text(), args.file)
        _print_diags(diagnostics, False)
        if app and args.dot:
            Path(args.dot).write_text(_ast_dot(app))
        return 1 if has_errors(diagnostics) else 0
    if args.command == "ir":
        module, diagnostics, _ = build_ir(Path(args.file))
        _print_diags(diagnostics, False)
        if module and args.dot:
            Path(args.dot).write_text(_ir_dot(module))
        return 1 if has_errors(diagnostics) else 0
    if args.command == "evaluate":
        return _evaluate(Path(args.examples))
    return 1


def _print_diags(diagnostics: list[Diagnostic], as_json: bool) -> None:
    if as_json:
        print(json.dumps([d.to_dict() for d in diagnostics], indent=2))
    else:
        for diag in diagnostics:
            print(diag.format())


def _ast_dot(app) -> str:
    lines = ["digraph AST {", f'  app [label="cloud app {app.name}"];']
    for i, res in enumerate(app.resources):
        lines.append(f'  r{i} [label="{res.kind} {res.name}"];')
        lines.append(f"  app -> r{i};")
    lines.append("}")
    return "\n".join(lines)


def _ir_dot(module) -> str:
    lines = ["digraph IR {"]
    for res in module.resources:
        lines.append(f'  "{res.ir_id}" [label="{res.ir_type}\\n{res.ir_id}"];')
        for dep in res.depends_on:
            lines.append(f'  "{dep}" -> "{res.ir_id}";')
    lines.append("}")
    return "\n".join(lines)


def _evaluate(examples: Path) -> int:
    validator = shutil.which("terraform") or shutil.which("tofu")
    for file in sorted(examples.glob("*.mcd")):
        lines = len(file.read_text().splitlines())
        result = compile_file(file, "all")
        status = "error" if has_errors(result.diagnostics) else "ok"
        print(f"{file.name}: source_lines={lines} status={status} diagnostics={len(result.diagnostics)} timings={result.timings}")
        for target, output in result.outputs.items():
            print(f"  {target}: generated_lines={len(output.text.splitlines())}")
        if validator:
            subprocess.run([validator, "version"], check=False, stdout=subprocess.DEVNULL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
