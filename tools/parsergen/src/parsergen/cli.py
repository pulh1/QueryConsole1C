from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

from .analysis import (
    AnalysisResult,
    LookaheadMaterializationError,
    compute_analysis,
)
from .artifacts import compare_artifacts, render_artifacts, replace_artifacts
from .bsl_codegen import generate_parser
from .config import ParsergenConfig, load_config
from .diagnostics import Diagnostic, Severity
from .grammar_parser import parse_grammar
from .lowering import LoweringResult
from .model import Grammar
from .resolver import ResolvedGrammar, ResolutionResult, resolve_grammar
from .source_model import SourceGrammar
from .validation import ValidationReport, validate_grammar


@dataclass(frozen=True, slots=True)
class Compilation:
    grammar: Grammar | None
    resolved: ResolvedGrammar | None
    analysis: AnalysisResult | None
    report: ValidationReport
    source_grammar: SourceGrammar | None = None
    lowering: LoweringResult | None = None


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def compile_from_config(config: ParsergenConfig) -> Compilation:
    text = config.grammar.read_text(encoding="utf-8")
    parsed = parse_grammar(text, str(config.grammar))
    parser_has_errors = any(
        item.severity is Severity.ERROR for item in parsed.diagnostics
    )
    resolved_result = (
        resolve_grammar(parsed.grammar)
        if parsed.grammar is not None and not parser_has_errors
        else ResolutionResult(None, ())
    )
    starts = tuple(config.entrypoints.values())
    analysis = (
        compute_analysis(resolved_result.grammar, config.lookahead, starts)
        if (
            resolved_result.grammar is not None
            and all(
                start in resolved_result.grammar.productions
                for start in starts
            )
        )
        else None
    )
    grammar = parsed.grammar or Grammar((), (), str(config.grammar))
    report = validate_grammar(
        grammar,
        resolved_result.grammar,
        analysis,
        config.entrypoints,
        (*parsed.diagnostics, *resolved_result.diagnostics),
        lowering=parsed.lowering,
    )
    return Compilation(
        parsed.grammar,
        resolved_result.grammar,
        analysis,
        report,
        parsed.source_grammar,
        parsed.lowering,
    )


def main(argv: Sequence[str] | None = None) -> int:
    _configure_console_encoding()
    try:
        arguments = _build_parser().parse_args(argv)
        config = _config_from_arguments(arguments)
        compilation = compile_from_config(config)
        if compilation.report.has_errors:
            _render_diagnostics(compilation.report.diagnostics, sys.stderr)
            return 1
        if arguments.command == "validate":
            _render_diagnostics(compilation.report.diagnostics, sys.stderr)
        elif arguments.command == "analyze":
            assert compilation.analysis is not None
            if arguments.format == "json":
                json.dump(
                    _analysis_payload(compilation.analysis),
                    sys.stdout,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                sys.stdout.write("\n")
            else:
                sys.stdout.write(_analysis_text(compilation.analysis))
        elif arguments.command == "generate":
            try:
                assert compilation.grammar is not None
                assert compilation.resolved is not None
                assert compilation.analysis is not None
                artifacts = render_artifacts(
                    generate_parser(
                        compilation.grammar,
                        compilation.resolved,
                        compilation.analysis,
                        config.entrypoints,
                    )
                )
                comparison = compare_artifacts(config.target, artifacts)
                if arguments.check:
                    if comparison.changed:
                        _print_changed_paths(config.target, comparison.changed)
                        return 3
                    print("artifacts are current")
                    return 0
                replaced = replace_artifacts(config.target, artifacts)
                if replaced.changed:
                    _print_changed_paths(config.target, replaced.changed)
                else:
                    print("artifacts are current")
            except Exception as error:
                print(str(error), file=sys.stderr)
                return 2
        return 0
    except (OSError, LookaheadMaterializationError) as error:
        print(str(error), file=sys.stderr)
        return 2
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="parsergen")
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "analyze", "generate"):
        command = subcommands.add_parser(name)
        command.add_argument("--config", type=Path)
        command.add_argument("--grammar", type=Path)
        command.add_argument("--target", type=Path)
        command.add_argument("--entry", action="append", default=[])
        command.add_argument("--lookahead", type=int)
        if name == "analyze":
            command.add_argument("--format", choices=("text", "json"), default="text")
        elif name == "generate":
            command.add_argument("--check", action="store_true")
    return parser


def _config_from_arguments(arguments: argparse.Namespace) -> ParsergenConfig:
    if arguments.config is not None:
        config = load_config(arguments.config)
        grammar = (
            arguments.grammar.resolve()
            if arguments.grammar is not None
            else config.grammar
        )
        target = (
            arguments.target.resolve()
            if arguments.target is not None
            else config.target
        )
        lookahead = (
            arguments.lookahead
            if arguments.lookahead is not None
            else config.lookahead
        )
        entrypoints = (
            _parse_entrypoints(arguments.entry)
            if arguments.entry
            else config.entrypoints
        )
        return replace(
            config,
            grammar=grammar,
            target=target,
            lookahead=_valid_lookahead(lookahead),
            entrypoints=entrypoints,
        )

    if arguments.grammar is None:
        raise ValueError("--grammar is required when --config is not used")
    if not arguments.entry:
        raise ValueError("--entry is required when --config is not used")
    return ParsergenConfig(
        grammar=arguments.grammar.resolve(),
        target=(
            arguments.target.resolve()
            if arguments.target is not None
            else Path.cwd()
        ),
        lookahead=_valid_lookahead(
            arguments.lookahead if arguments.lookahead is not None else 2
        ),
        entrypoints=_parse_entrypoints(arguments.entry),
    )


def _valid_lookahead(value: int) -> int:
    if isinstance(value, bool) or value < 1:
        raise ValueError("--lookahead must be an integer at least 1")
    return value


def _parse_entrypoints(values: Sequence[str]) -> Mapping[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        name, separator, production = value.partition("=")
        if not separator or not name.strip() or not production.strip():
            raise ValueError("--entry must use non-empty NAME=PRODUCTION values")
        if name in parsed:
            raise ValueError(f"duplicate entrypoint: {name}")
        parsed[name] = production
    return MappingProxyType(parsed)


def _render_diagnostics(
    diagnostics: Sequence[Diagnostic],
    stream: object,
) -> None:
    for diagnostic in diagnostics:
        start = diagnostic.span.start
        print(
            (
                f"{diagnostic.span.path}:{start.line}:{start.column}: "
                f"{diagnostic.severity.value} {diagnostic.code}: "
                f"{diagnostic.message}"
            ),
            file=stream,
        )
        for related in diagnostic.related:
            related_start = related.span.start
            print(
                (
                    f"  related {related.span.path}:{related_start.line}:"
                    f"{related_start.column}: {related.message}"
                ),
                file=stream,
            )


def _analysis_payload(analysis: AnalysisResult) -> dict[str, object]:
    return {
        "k": analysis.k,
        "nullable": sorted(analysis.nullable),
        "first": {
            name: _sorted_words(analysis.first[name])
            for name in sorted(analysis.first)
        },
        "follow": {
            name: _sorted_words(analysis.follow[name])
            for name in sorted(analysis.follow)
        },
        "select": {
            f"{name}:{alternative}": _sorted_words(analysis.select[key])
            for key in sorted(analysis.select)
            for name, alternative in (key,)
        },
    }


def _sorted_words(words: Sequence[tuple[str, ...]]) -> list[list[str]]:
    return [list(word) for word in sorted(words, key=lambda word: (len(word), word))]


def _analysis_text(analysis: AnalysisResult) -> str:
    lines = [
        f"lookahead: {analysis.k}",
        f"nullable: {', '.join(sorted(analysis.nullable)) or '-'}",
    ]
    for name in sorted(analysis.first):
        lines.append(f"FIRST {name}: {_format_words(analysis.first[name])}")
    for name in sorted(analysis.follow):
        lines.append(f"FOLLOW {name}: {_format_words(analysis.follow[name])}")
    for name, alternative in sorted(analysis.select):
        lines.append(
            f"SELECT {name}:{alternative}: "
            f"{_format_words(analysis.select[(name, alternative)])}"
        )
    return "\n".join(lines) + "\n"


def _format_words(words: Sequence[tuple[str, ...]]) -> str:
    ordered = sorted(words, key=lambda word: (len(word), word))
    return " | ".join(" ".join(word) if word else "ε" for word in ordered)


def _print_changed_paths(target: Path, changed: Sequence[Path]) -> None:
    for path in changed:
        print(path.relative_to(target).as_posix())


def _configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")
