from __future__ import annotations

from collections.abc import Iterator
from collections import defaultdict, deque
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Generic, Mapping, TypeAlias, TypeVar

from .resolver import (
    ResolvedGrammar,
    ResolvedNonterminal,
    ResolvedToken,
)


LookaheadWord: TypeAlias = tuple[str, ...]
LookaheadSet: TypeAlias = frozenset[LookaheadWord]
EPSILON: LookaheadWord = ()
END = "$"
DEFAULT_MATERIALIZE_ROWS = 10_000


class LookaheadMaterializationError(RuntimeError):
    def __init__(
        self,
        phase: str,
        key: object,
        estimated_rows: int,
        limit_rows: int,
    ) -> None:
        self.phase = phase
        self.key = key
        self.estimated_rows = estimated_rows
        self.limit_rows = limit_rows
        super().__init__(
            f"{phase} {key!r} may expand to {estimated_rows} rows; "
            f"limit is {limit_rows}"
        )


@dataclass(frozen=True, slots=True)
class PrefixAnalysis:
    k: int
    nullable: frozenset[str]
    first: Mapping[str, LookaheadSet]
    updates: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    k: int
    nullable: frozenset[str]
    first: Mapping[str, LookaheadSet]
    follow: Mapping[str, LookaheadSet]
    select: Mapping[tuple[str, int], LookaheadSet]
    updates: Mapping[str, int]
    _compressed: _CompressedAnalysis | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    _resolved_grammar: ResolvedGrammar | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    _start_productions: tuple[str, ...] = field(
        default=(),
        repr=False,
        compare=False,
    )


@dataclass(frozen=True, slots=True)
class SelectConflict:
    production: str
    left_alternative: int
    right_alternative: int
    witness: LookaheadWord


@dataclass(frozen=True, slots=True)
class SelectMatcherRow:
    production: str
    alternative: int
    matchers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MatcherDefinition:
    label: str
    token_types: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SelectMatcherArtifact:
    select_rows: tuple[SelectMatcherRow, ...]
    matcher_definitions: tuple[MatcherDefinition, ...]


@dataclass(frozen=True, slots=True)
class _FollowOccurrence:
    parent_id: int
    referenced_id: int
    suffix_variant_id: int


@dataclass(frozen=True, slots=True)
class _FollowTransform:
    parent_id: int
    referenced_id: int
    prefix: _PackedPrefix


@dataclass(slots=True)
class _FollowTransformGroup:
    needed: int
    transforms: list[_FollowTransform] = field(default_factory=list)
    seen_projections: set[_PackedPrefix] = field(default_factory=set)


def concat_words(
    left: LookaheadWord,
    right: LookaheadWord,
    k: int,
) -> LookaheadWord:
    if k < 1:
        raise ValueError("k must be at least 1")
    return (left + right)[:k]


def concat_languages(
    left: set[LookaheadWord] | frozenset[LookaheadWord],
    right: set[LookaheadWord] | frozenset[LookaheadWord],
    k: int,
) -> LookaheadSet:
    if k < 1:
        raise ValueError("k must be at least 1")
    return frozenset(concat_words(a, b, k) for a in left for b in right)


def compute_prefix_analysis(grammar: ResolvedGrammar, k: int) -> PrefixAnalysis:
    if k < 1:
        raise ValueError("k must be at least 1")

    nullable = _compute_nullable(grammar)
    first, updates = _compute_first(grammar, k)
    return PrefixAnalysis(
        k=k,
        nullable=nullable,
        first=MappingProxyType(first),
        updates=MappingProxyType(updates),
    )


def compute_analysis(
    grammar: ResolvedGrammar,
    k: int,
    start_productions: tuple[str, ...],
) -> AnalysisResult:
    if k < 1:
        raise ValueError("k must be at least 1")

    starts = tuple(start_productions)
    nullable = _compute_nullable(grammar)
    solver = _ContinuationFirst(grammar, k)
    packed_first = solver.run_core()
    packed_follow, follow_stats = _compute_packed_follow(
        solver,
        starts,
    )
    select_keys, select_descriptors, select_stats = _compute_factorized_select(
        grammar,
        solver,
    )
    compressed = _CompressedAnalysis(
        solver,
        packed_first,
        packed_follow,
        select_keys,
        select_descriptors,
        {**follow_stats, **select_stats},
    )
    first = _LazyPackedMapping(
        grammar.production_order,
        packed_first,
        compressed.expand_first,
        compressed.first_estimates,
        "first",
    )
    follow = _LazyPackedMapping(
        grammar.production_order,
        packed_follow,
        compressed.expand_follow,
        compressed.follow_estimates,
        "follow",
    )
    select = _LazySelectMapping(compressed)
    return AnalysisResult(
        k=k,
        nullable=nullable,
        first=first,
        follow=follow,
        select=select,
        updates=MappingProxyType(solver.updates(packed_first)),
        _compressed=compressed,
        _resolved_grammar=grammar,
        _start_productions=starts,
    )


def materialize_lookahead(
    analysis: AnalysisResult,
    phase: str,
    key: str | tuple[str, int],
    *,
    max_rows: int,
) -> LookaheadSet:
    mappings: dict[str, Mapping[object, LookaheadSet]] = {
        "first": analysis.first,
        "follow": analysis.follow,
        "select": analysis.select,
    }
    try:
        mapping = mappings[phase]
    except KeyError:
        raise ValueError("phase must be first, follow, or select") from None
    materializer = getattr(mapping, "materialize", None)
    if materializer is not None:
        return materializer(key, max_rows=max_rows)
    value = mapping[key]
    if max_rows < 1 or len(value) > max_rows:
        raise LookaheadMaterializationError(
            phase,
            key,
            len(value),
            max_rows,
        )
    return value


def build_legacy_matcher_artifact(
    analysis: AnalysisResult,
    *,
    max_rows: int,
) -> SelectMatcherArtifact:
    if analysis._compressed is None:
        raise ValueError("compressed analysis is required for matcher artifacts")
    return analysis._compressed.build_matcher_artifact(max_rows=max_rows)


def build_select_matcher_artifact(
    analysis: AnalysisResult,
    *,
    max_rows: int,
) -> SelectMatcherArtifact:
    return build_legacy_matcher_artifact(analysis, max_rows=max_rows)


def runtime_rows_overlap(left: LookaheadWord, right: LookaheadWord) -> bool:
    return left == right


def compatible_lookahead(left: LookaheadWord, right: LookaheadWord) -> bool:
    return runtime_rows_overlap(left, right)


def find_canonical_select_conflicts(
    grammar: ResolvedGrammar,
    analysis: AnalysisResult,
) -> tuple[SelectConflict, ...]:
    conflicts: list[SelectConflict] = []
    compressed = analysis._compressed
    for production_name in grammar.production_order:
        alternatives = grammar.productions[production_name]
        for left_position, _ in enumerate(alternatives):
            left_number = left_position + 1
            left_key = (production_name, left_number)
            for right_position in range(left_position + 1, len(alternatives)):
                right_number = right_position + 1
                right_key = (production_name, right_number)
                if compressed is not None:
                    witness = compressed.canonical_conflict_witness(
                        compressed._select_index[left_key],
                        compressed._select_index[right_key],
                    )
                else:
                    witness = _select_conflict_witness(
                        analysis.select[left_key],
                        analysis.select[right_key],
                    )
                if witness is not None:
                    conflicts.append(
                        SelectConflict(
                            production_name,
                            left_number,
                            right_number,
                            witness,
                        )
                    )
    return tuple(conflicts)


def find_select_conflicts(
    grammar: ResolvedGrammar,
    analysis: AnalysisResult,
) -> tuple[SelectConflict, ...]:
    return find_canonical_select_conflicts(grammar, analysis)


def find_runtime_dispatch_conflicts(
    grammar: ResolvedGrammar,
    analysis: AnalysisResult,
) -> tuple[SelectConflict, ...]:
    if analysis._compressed is None:
        raise ValueError("compressed analysis is required for runtime dispatch")

    conflicts: list[SelectConflict] = []
    compressed = analysis._compressed
    for production_name in grammar.production_order:
        alternatives = grammar.productions[production_name]
        for left_position, _ in enumerate(alternatives):
            left_number = left_position + 1
            left_key = (production_name, left_number)
            packed_left = compressed._select_index[left_key]
            for right_position in range(left_position + 1, len(alternatives)):
                right_number = right_position + 1
                right_key = (production_name, right_number)
                packed_right = compressed._select_index[right_key]
                witness = compressed.runtime_dispatch_conflict_witness(
                    packed_left,
                    packed_right,
                )
                if witness is not None:
                    conflicts.append(
                        SelectConflict(
                            production_name,
                            left_number,
                            right_number,
                            witness,
                        )
                    )
    return tuple(conflicts)


def _compute_nullable(grammar: ResolvedGrammar) -> frozenset[str]:
    AlternativeKey: TypeAlias = tuple[str, int]
    remaining: dict[AlternativeKey, int] = {}
    dependents: dict[str, list[AlternativeKey]] = defaultdict(list)

    for production_name in grammar.production_order:
        for alternative in grammar.productions[production_name]:
            if any(isinstance(symbol, ResolvedToken) for symbol in alternative.symbols):
                continue
            key = (production_name, alternative.index)
            nonterminals = tuple(
                symbol
                for symbol in alternative.symbols
                if isinstance(symbol, ResolvedNonterminal)
            )
            remaining[key] = len(nonterminals)
            for symbol in nonterminals:
                dependents[symbol.name].append(key)

    nullable: set[str] = set()
    queue: deque[str] = deque()

    for (production_name, _), count in remaining.items():
        if count == 0 and production_name not in nullable:
            nullable.add(production_name)
            queue.append(production_name)

    while queue:
        nullable_name = queue.popleft()
        for key in dependents.get(nullable_name, ()):
            owner, _ = key
            if owner in nullable:
                continue
            remaining[key] -= 1
            if remaining[key] == 0:
                nullable.add(owner)
                queue.append(owner)

    return frozenset(nullable)


_PackedPrefix: TypeAlias = tuple[int, int]
_PackedLanguage: TypeAlias = frozenset[_PackedPrefix]
# The boolean is semantically meaningful only while length < budget: True
# means the variant may finish at this short fact, so an outer RHS may resume.
# At length == budget it is deliberately ignored and may remain False even
# when a complete derivation exists with the same saturated k-prefix.
_PackedFact: TypeAlias = tuple[int, int, bool]
_PackedFacts: TypeAlias = tuple[_PackedFact, ...]


@dataclass(frozen=True, slots=True)
class _SelectDescriptor:
    owner_id: int
    direct: _PackedLanguage
    prefixes: tuple[_PackedPrefix, ...]

    @property
    def prefix_count(self) -> int:
        return len(self.prefixes)


class _FirstState:
    __slots__ = (
        "sid",
        "variant_id",
        "budget",
        "results",
        "waiters",
        "waiter_keys",
        "seen_frames",
    )

    def __init__(self, sid: int, variant_id: int, budget: int) -> None:
        self.sid = sid
        self.variant_id = variant_id
        self.budget = budget
        self.results: dict[_PackedPrefix, bool] = {}
        self.waiters: list[_FirstContinuation] = []
        self.waiter_keys: set[tuple[int, int, int, int]] = set()
        self.seen_frames: set[tuple[int, int, int]] = set()


class _FirstContinuation:
    __slots__ = ("consumer", "next_pos", "base_len", "base_packed")

    def __init__(
        self,
        consumer: _FirstState,
        next_pos: int,
        base_len: int,
        base_packed: int,
    ) -> None:
        self.consumer = consumer
        self.next_pos = next_pos
        self.base_len = base_len
        self.base_packed = base_packed


class _ContinuationFirst:
    """Compute compressed FIRST(k) facts through direct continuations."""

    FRAME = 0
    RESUME = 1

    def __init__(self, grammar: ResolvedGrammar, k: int) -> None:
        if k < 1:
            raise ValueError("k must be at least 1")
        self.grammar = grammar
        self.k = k
        self.production_names = grammar.production_order
        self.production_ids = {
            name: position
            for position, name in enumerate(self.production_names)
        }

        matcher_ids: dict[frozenset[str], int] = {}
        matcher_tokens: list[tuple[str, ...]] = [()]
        encoded_alternatives: list[tuple[int, ...]] = []
        alternative_owners: list[int] = []

        for owner_id, owner in enumerate(self.production_names):
            for alternative in grammar.productions[owner]:
                encoded: list[int] = []
                for symbol in alternative.symbols:
                    if isinstance(symbol, ResolvedToken):
                        matcher_id = matcher_ids.get(symbol.token_types)
                        if matcher_id is None:
                            matcher_id = len(matcher_tokens)
                            matcher_ids[symbol.token_types] = matcher_id
                            matcher_tokens.append(tuple(sorted(symbol.token_types)))
                        encoded.append(matcher_id)
                    else:
                        encoded.append(-(self.production_ids[symbol.name] + 1))
                encoded_alternatives.append(tuple(encoded))
                alternative_owners.append(owner_id)

        self.end_matcher_id = len(matcher_tokens)
        matcher_tokens.append((END,))
        preferred_labels: dict[frozenset[str], str] = {}
        reserved_label_sets: dict[str, set[frozenset[str]]] = defaultdict(set)
        definition_order: list[int] = []
        for name, token_types in grammar.identifier_tokens.items():
            preferred_labels.setdefault(token_types, name)
            reserved_label_sets[name.casefold()].add(token_types)
            matcher_id = matcher_ids.get(token_types)
            if (
                matcher_id is not None
                and matcher_id not in definition_order
            ):
                definition_order.append(matcher_id)

        matcher_labels = [""]
        used_labels: set[str] = set()

        def allocate_label(
            base: str,
            token_set: frozenset[str],
            suffix: str,
        ) -> str:
            label = base
            next_suffix = 0
            while True:
                key = label.casefold()
                reserved_sets = reserved_label_sets.get(key)
                if (
                    key not in used_labels
                    and (
                        not reserved_sets
                        or reserved_sets == {token_set}
                    )
                ):
                    used_labels.add(key)
                    return label
                label_suffix = (
                    suffix if next_suffix == 0 else f"{suffix}_{next_suffix}"
                )
                label = f"{base}#{label_suffix}"
                next_suffix += 1

        for matcher_id, tokens in enumerate(matcher_tokens[1:-1], start=1):
            token_set = frozenset(tokens)
            base = preferred_labels.get(token_set)
            if base is None:
                base = tokens[0] if len(tokens) == 1 else f"Matcher{matcher_id}"
            matcher_labels.append(
                allocate_label(base, token_set, str(matcher_id))
            )
        end_label = allocate_label(
            END,
            frozenset({END}),
            "END",
        )
        matcher_labels.append(end_label)
        definition_order.extend(
            matcher_id
            for matcher_id in range(1, self.end_matcher_id)
            if matcher_id not in definition_order
        )
        definition_order.append(self.end_matcher_id)
        self.matcher_labels = tuple(matcher_labels)
        self.matcher_definition_order = tuple(definition_order)

        variants: list[tuple[int, ...]] = []
        variant_ids: dict[tuple[int, ...], int] = {}

        def intern(rhs: tuple[int, ...]) -> int:
            variant_id = variant_ids.get(rhs)
            if variant_id is None:
                variant_id = len(variants)
                variant_ids[rhs] = variant_id
                variants.append(rhs)
            return variant_id

        alternative_variant_ids = tuple(
            intern(rhs) for rhs in encoded_alternatives
        )
        alternatives_by_lhs: list[list[int]] = [
            [] for _ in self.production_names
        ]
        by_lhs: list[list[int]] = [
            [] for _ in self.production_names
        ]
        for alternative_id, owner_id in enumerate(alternative_owners):
            variant_id = alternative_variant_ids[alternative_id]
            alternatives_by_lhs[owner_id].append(variant_id)
            if variant_id not in by_lhs[owner_id]:
                by_lhs[owner_id].append(variant_id)

        occurrences: list[_FollowOccurrence] = []
        for alternative_id, rhs in enumerate(encoded_alternatives):
            parent_id = alternative_owners[alternative_id]
            for position, symbol in enumerate(rhs):
                if symbol >= 0:
                    continue
                occurrences.append(
                    _FollowOccurrence(
                        parent_id,
                        -symbol - 1,
                        intern(rhs[position + 1 :]),
                    )
                )

        self.variants = tuple(variants)
        self.alternative_variant_ids = alternative_variant_ids
        self.alternative_owners = tuple(alternative_owners)
        self.alternatives_by_lhs = tuple(
            tuple(items) for items in alternatives_by_lhs
        )
        self.by_lhs = tuple(tuple(items) for items in by_lhs)
        self.occurrences = tuple(occurrences)
        self.matcher_tokens = tuple(matcher_tokens)
        self.nvariants = len(self.variants)
        productive = [False] * len(self.production_names)
        remaining_nonterminals = [
            sum(symbol < 0 for symbol in rhs)
            for rhs in encoded_alternatives
        ]
        productive_dependents: list[list[int]] = [
            [] for _ in self.production_names
        ]
        for alternative_id, rhs in enumerate(encoded_alternatives):
            for symbol in rhs:
                if symbol < 0:
                    productive_dependents[-symbol - 1].append(alternative_id)

        productive_queue: deque[int] = deque()
        for alternative_id, remaining in enumerate(remaining_nonterminals):
            owner_id = alternative_owners[alternative_id]
            if remaining == 0 and not productive[owner_id]:
                productive[owner_id] = True
                productive_queue.append(owner_id)
        while productive_queue:
            production_id = productive_queue.popleft()
            for alternative_id in productive_dependents[production_id]:
                remaining_nonterminals[alternative_id] -= 1
                if remaining_nonterminals[alternative_id] != 0:
                    continue
                owner_id = alternative_owners[alternative_id]
                if productive[owner_id]:
                    continue
                productive[owner_id] = True
                productive_queue.append(owner_id)

        productive_suffixes: list[tuple[bool, ...]] = []
        for rhs in self.variants:
            suffix = [False] * (len(rhs) + 1)
            suffix[-1] = True
            for position in range(len(rhs) - 1, -1, -1):
                symbol = rhs[position]
                symbol_productive = (
                    symbol > 0 or productive[-symbol - 1]
                )
                suffix[position] = symbol_productive and suffix[position + 1]
            productive_suffixes.append(tuple(suffix))
        self.productive_suffixes = tuple(productive_suffixes)

        matcher_count = len(self.matcher_tokens) - 1
        self.bits = max(1, matcher_count.bit_length())
        self.prefix_masks = tuple(
            (1 << (length * self.bits)) - 1 if length else 0
            for length in range(k + 1)
        )
        self.states: list[list[_FirstState | None]] = [
            [None] * self.nvariants
            for _ in range(k + 1)
        ]
        self.queue: deque[tuple[object, ...]] = deque()
        self.stats: dict[str, int] = defaultdict(int)
        self.stats["variants"] = self.nvariants
        self.stats["real_alternatives"] = len(encoded_alternatives)
        self.stats["suffix_fact_sets"] = len(
            {occurrence.suffix_variant_id for occurrence in self.occurrences}
        )
        self.stats["occurrences"] = len(self.occurrences)
        self.stats["matcher_classes"] = matcher_count - 1
        self.stats["productive_productions"] = sum(productive)
        self.stats["productive_variants"] = sum(suffix[0] for suffix in self.productive_suffixes)

    def _get_state(self, variant_id: int, budget: int) -> _FirstState:
        state = self.states[budget][variant_id]
        if state is not None:
            self.stats["state_hits"] += 1
            return state
        state = _FirstState(
            budget * self.nvariants + variant_id,
            variant_id,
            budget,
        )
        self.states[budget][variant_id] = state
        self.stats["states_created"] += 1
        self._enqueue_frame(state, 0, 0, 0)
        return state

    def _enqueue_frame(
        self,
        state: _FirstState,
        pos: int,
        length: int,
        packed: int,
    ) -> None:
        key = (pos, length, packed)
        if key in state.seen_frames:
            self.stats["duplicate_frames_suppressed"] += 1
            return
        state.seen_frames.add(key)
        self.queue.append((self.FRAME, state, pos, length, packed))
        self.stats["frames_enqueued"] += 1

    def _add_waiter(
        self,
        producer: _FirstState,
        consumer: _FirstState,
        next_pos: int,
        base_len: int,
        base_packed: int,
    ) -> None:
        key = (consumer.sid, next_pos, base_len, base_packed)
        if key in producer.waiter_keys:
            self.stats["duplicate_waiters_suppressed"] += 1
            return
        producer.waiter_keys.add(key)
        waiter = _FirstContinuation(
            consumer,
            next_pos,
            base_len,
            base_packed,
        )
        producer.waiters.append(waiter)
        self.stats["waiters_created"] += 1

        for (child_len, child_packed), complete in producer.results.items():
            self.queue.append(
                (
                    self.RESUME,
                    waiter,
                    child_len,
                    child_packed,
                    complete,
                )
            )
            self.stats["result_replays"] += 1

    def _publish(
        self,
        state: _FirstState,
        length: int,
        packed: int,
        complete: bool,
    ) -> None:
        key = (length, packed)
        previous = state.results.get(key)
        if previous is None:
            state.results[key] = complete
            self.stats["facts_published"] += 1
        elif not previous and complete:
            state.results[key] = True
            self.stats["facts_upgraded_to_complete"] += 1
        else:
            self.stats["duplicate_facts_suppressed"] += 1
            return

        for waiter in state.waiters:
            self.queue.append(
                (self.RESUME, waiter, length, packed, complete)
            )
            self.stats["notifications_enqueued"] += 1

    def _process_frame(
        self,
        state: _FirstState,
        pos: int,
        length: int,
        packed: int,
    ) -> None:
        self.stats["frames_processed"] += 1
        rhs = self.variants[state.variant_id]

        if length >= state.budget:
            if self.productive_suffixes[state.variant_id][pos]:
                self._publish(
                    state,
                    state.budget,
                    packed & self.prefix_masks[state.budget],
                    pos >= len(rhs),
                )
            else:
                self.stats["nonproductive_saturated_facts_ignored"] += 1
            return
        if pos >= len(rhs):
            self._publish(state, length, packed, True)
            return

        symbol = rhs[pos]
        if symbol > 0:
            self.stats["terminal_steps"] += 1
            self._enqueue_frame(
                state,
                pos + 1,
                length + 1,
                packed | (symbol << (length * self.bits)),
            )
            return

        remaining = state.budget - length
        self.stats["nonterminal_steps"] += 1
        production_id = -symbol - 1
        for child_variant_id in self.by_lhs[production_id]:
            child = self._get_state(child_variant_id, remaining)
            self._add_waiter(
                child,
                state,
                pos + 1,
                length,
                packed,
            )

    def _process_resume(
        self,
        waiter: _FirstContinuation,
        child_len: int,
        child_packed: int,
        child_complete: bool,
    ) -> None:
        self.stats["resumes_processed"] += 1
        consumer = waiter.consumer
        total_len = waiter.base_len + child_len
        combined = waiter.base_packed | (
            child_packed << (waiter.base_len * self.bits)
        )

        if total_len >= consumer.budget:
            self._enqueue_frame(
                consumer,
                waiter.next_pos,
                consumer.budget,
                combined & self.prefix_masks[consumer.budget],
            )
        elif child_complete:
            self._enqueue_frame(
                consumer,
                waiter.next_pos,
                total_len,
                combined,
            )
        else:
            self.stats["short_incomplete_results_ignored"] += 1

    def run_core(self) -> tuple[_PackedLanguage, ...]:
        for variant_id in range(self.nvariants):
            self._get_state(variant_id, self.k)

        while self.queue:
            item = self.queue.popleft()
            if item[0] == self.FRAME:
                _, state, pos, length, packed = item
                assert isinstance(state, _FirstState)
                self._process_frame(state, pos, length, packed)
            else:
                _, waiter, child_len, child_packed, complete = item
                assert isinstance(waiter, _FirstContinuation)
                self._process_resume(
                    waiter,
                    child_len,
                    child_packed,
                    complete,
                )
            self.stats["work_items_processed"] += 1
            self.stats["max_queue"] = max(
                self.stats["max_queue"],
                len(self.queue),
            )

        by_production: list[set[_PackedPrefix]] = [
            set() for _ in self.production_names
        ]
        for alternative_id, owner_id in enumerate(self.alternative_owners):
            variant_id = self.alternative_variant_ids[alternative_id]
            state = self.states[self.k][variant_id]
            assert state is not None
            by_production[owner_id].update(state.results)
        raw = tuple(frozenset(items) for items in by_production)
        self.stats["raw_rows"] = sum(map(len, raw))
        self.variant_facts: tuple[_PackedFacts, ...] = tuple(
            tuple(
                (length, packed, complete)
                for (length, packed), complete in sorted(state.results.items())
            )
            if state is not None
            else ()
            for state in self.states[self.k]
        )

        for budget_states in self.states:
            for state in budget_states:
                if state is not None:
                    state.waiters.clear()
                    state.waiter_keys.clear()
                    state.seen_frames.clear()
                    state.results.clear()
        self.queue.clear()
        return raw

    def expand(
        self,
        raw: tuple[_PackedLanguage, ...],
    ) -> dict[str, LookaheadSet]:
        expanded: dict[str, LookaheadSet] = {}
        for production_id, production_name in enumerate(self.production_names):
            expanded[production_name] = self.expand_language(raw[production_id])
        self.stats["expanded_rows"] = sum(map(len, expanded.values()))
        return expanded

    def expand_language(self, language: _PackedLanguage) -> LookaheadSet:
        words: set[LookaheadWord] = set()
        matcher_mask = (1 << self.bits) - 1
        for length, packed in sorted(language):
            partials: list[LookaheadWord] = [EPSILON]
            for position in range(length):
                matcher_id = (
                    packed >> (position * self.bits)
                ) & matcher_mask
                partials = [
                    partial + (token_type,)
                    for partial in partials
                    for token_type in self.matcher_tokens[matcher_id]
                ]
            words.update(partials)
        return frozenset(words)

    def language_expanded_row_upper_bound(
        self,
        language: _PackedLanguage,
    ) -> int:
        total = 0
        matcher_mask = (1 << self.bits) - 1
        for length, packed in language:
            choices = 1
            for position in range(length):
                matcher_id = (
                    packed >> (position * self.bits)
                ) & matcher_mask
                choices *= len(self.matcher_tokens[matcher_id])
            total += choices
        return total

    def expanded_row_upper_bound(
        self,
        raw: tuple[_PackedLanguage, ...],
    ) -> int:
        total = 0
        for language in raw:
            total += self.language_expanded_row_upper_bound(language)
        self.stats["expanded_row_upper_bound"] = total
        return total

    def updates(
        self,
        raw: tuple[_PackedLanguage, ...],
    ) -> dict[str, int]:
        return {
            production_name: len(raw[production_id])
            for production_id, production_name in enumerate(
                self.production_names
            )
        }


_MappingKey = TypeVar("_MappingKey")


class _LazyPackedMapping(Mapping[_MappingKey, LookaheadSet], Generic[_MappingKey]):
    __slots__ = (
        "_keys",
        "_index",
        "_languages",
        "_expand",
        "_estimates",
        "_phase",
        "_default_limit",
        "_cache",
    )

    def __init__(
        self,
        keys: tuple[_MappingKey, ...],
        languages: tuple[_PackedLanguage, ...],
        expand,
        estimates: tuple[int, ...],
        phase: str,
        default_limit: int = DEFAULT_MATERIALIZE_ROWS,
    ) -> None:
        self._keys = keys
        self._index = {
            key: position for position, key in enumerate(keys)
        }
        self._languages = languages
        self._expand = expand
        self._estimates = estimates
        self._phase = phase
        self._default_limit = default_limit
        self._cache: dict[_MappingKey, LookaheadSet] = {}

    def __getitem__(self, key: _MappingKey) -> LookaheadSet:
        return self.materialize(key, max_rows=self._default_limit)

    def materialize(
        self,
        key: _MappingKey,
        *,
        max_rows: int,
    ) -> LookaheadSet:
        try:
            position = self._index[key]
        except KeyError:
            raise KeyError(key) from None
        estimate = self._estimates[position]
        if max_rows < 1 or estimate > max_rows:
            raise LookaheadMaterializationError(
                self._phase,
                key,
                estimate,
                max_rows,
            )
        try:
            return self._cache[key]
        except KeyError:
            pass
        expanded = self._expand(self._languages[position])
        self._cache[key] = expanded
        return expanded

    def estimate(self, key: _MappingKey) -> int:
        try:
            return self._estimates[self._index[key]]
        except KeyError:
            raise KeyError(key) from None

    def __iter__(self) -> Iterator[_MappingKey]:
        return iter(self._keys)

    def __len__(self) -> int:
        return len(self._keys)


class _LazySelectMapping(Mapping[tuple[str, int], LookaheadSet]):
    __slots__ = ("_compressed", "_cache", "_default_limit")

    def __init__(
        self,
        compressed: _CompressedAnalysis,
        default_limit: int = DEFAULT_MATERIALIZE_ROWS,
    ) -> None:
        self._compressed = compressed
        self._cache: dict[tuple[str, int], LookaheadSet] = {}
        self._default_limit = default_limit

    def __getitem__(self, key: tuple[str, int]) -> LookaheadSet:
        return self.materialize(key, max_rows=self._default_limit)

    def materialize(
        self,
        key: tuple[str, int],
        *,
        max_rows: int,
    ) -> LookaheadSet:
        position = self._compressed.select_position(key)
        estimate = self._compressed.select_concrete_upper_bound(position)
        if max_rows < 1 or estimate > max_rows:
            raise LookaheadMaterializationError(
                "select",
                key,
                estimate,
                max_rows,
            )
        try:
            return self._cache[key]
        except KeyError:
            pass
        value = self._compressed.materialize_select(position)
        self._cache[key] = value
        return value

    def estimate(self, key: tuple[str, int]) -> int:
        return self._compressed.select_concrete_upper_bound(
            self._compressed.select_position(key)
        )

    def __iter__(self) -> Iterator[tuple[str, int]]:
        return iter(self._compressed.select_keys)

    def __len__(self) -> int:
        return len(self._compressed.select_keys)


class _PackedTrie:
    __slots__ = ("children", "terminal", "_strict_non_end")

    def __init__(
        self,
        language: _PackedLanguage,
        bits: int,
    ) -> None:
        self.children: list[dict[int, int]] = [{}]
        self.terminal: list[bool] = [False]
        self._strict_non_end: dict[int, bool] = {}
        matcher_mask = (1 << bits) - 1
        for length, packed in sorted(language):
            node = 0
            for position in range(length):
                matcher_id = (
                    packed >> (position * bits)
                ) & matcher_mask
                child = self.children[node].get(matcher_id)
                if child is None:
                    child = len(self.children)
                    self.children[node][matcher_id] = child
                    self.children.append({})
                    self.terminal.append(False)
                node = child
            self.terminal[node] = True

    def has_strict_non_end_descendant(
        self,
        node: int,
        matcher_tokens: tuple[tuple[str, ...], ...],
    ) -> bool:
        cached = self._strict_non_end.get(node)
        if cached is not None:
            return cached
        for matcher_id, child in self.children[node].items():
            if not any(token != END for token in matcher_tokens[matcher_id]):
                continue
            if self.terminal[child] or self.has_strict_non_end_descendant(
                child,
                matcher_tokens,
            ):
                self._strict_non_end[node] = True
                return True
        self._strict_non_end[node] = False
        return False


@dataclass(slots=True)
class _FactorGraph:
    trie: _PackedTrie
    accepts_terminal: bool
    epsilon_follow: int | None = None


_FactorState: TypeAlias = tuple[tuple[int, int], ...]


class _CompressedAnalysis:
    __slots__ = (
        "k",
        "production_names",
        "select_keys",
        "first",
        "follow",
        "select_descriptors",
        "matcher_tokens",
        "matcher_labels",
        "matcher_definition_order",
        "bits",
        "prefix_masks",
        "_select_index",
        "_first_estimates",
        "_follow_estimates",
        "_projection_rows",
        "_projection_concrete",
        "_graphs",
        "_follow_graphs",
        "_direct_graphs",
        "_prefix_graphs",
        "_descriptor_states",
        "_runtime_tries",
        "_variants",
        "_alternative_variant_ids",
        "_alternative_owners",
        "_alternatives_by_lhs",
        "_state_children",
        "_state_terminal",
        "_strict_non_end",
        "_conflict_memo",
        "_matcher_intersections",
        "_stats",
        "stats",
    )

    def __init__(
        self,
        solver: _ContinuationFirst,
        first: tuple[_PackedLanguage, ...],
        follow: tuple[_PackedLanguage, ...],
        select_keys: tuple[tuple[str, int], ...],
        select_descriptors: tuple[_SelectDescriptor, ...],
        phase_stats: Mapping[str, int],
    ) -> None:
        self.k = solver.k
        self.production_names = solver.production_names
        self.select_keys = select_keys
        self.first = first
        self.follow = follow
        self.select_descriptors = select_descriptors
        self.matcher_tokens = solver.matcher_tokens
        self.matcher_labels = solver.matcher_labels
        self.matcher_definition_order = solver.matcher_definition_order
        self.bits = solver.bits
        self.prefix_masks = solver.prefix_masks
        self._select_index = {
            key: position for position, key in enumerate(select_keys)
        }
        self._first_estimates = tuple(
            self._language_concrete_upper_bound(language)
            for language in first
        )
        self._follow_estimates = tuple(
            self._language_concrete_upper_bound(language)
            for language in follow
        )
        self._projection_rows: dict[tuple[int, int], int] = {}
        self._projection_concrete: dict[tuple[int, int], int] = {}
        self._graphs: list[_FactorGraph] = []
        self._follow_graphs: list[int | None] = [
            None for _ in self.production_names
        ]
        self._direct_graphs: list[int | None] = [
            None for _ in select_descriptors
        ]
        self._prefix_graphs: list[int | None] = [
            None for _ in select_descriptors
        ]
        self._descriptor_states: list[_FactorState | None] = [
            None for _ in select_descriptors
        ]
        self._runtime_tries: list[_PackedTrie | None] = [
            None for _ in select_descriptors
        ]
        self._variants = solver.variants
        self._alternative_variant_ids = solver.alternative_variant_ids
        self._alternative_owners = solver.alternative_owners
        self._alternatives_by_lhs = solver.alternatives_by_lhs
        self._state_children: dict[
            _FactorState,
            tuple[tuple[int, _FactorState], ...],
        ] = {}
        self._state_terminal: dict[_FactorState, bool] = {}
        self._strict_non_end: dict[tuple[_FactorState, int], bool] = {}
        self._conflict_memo: dict[
            tuple[_FactorState, _FactorState, int],
            LookaheadWord | None,
        ] = {}
        self._matcher_intersections: dict[
            tuple[int, int],
            tuple[str, ...],
        ] = {}
        self._stats = dict(solver.stats)
        self._stats.update(phase_stats)
        self._stats.setdefault("public_first_expansions", 0)
        self._stats.setdefault("public_follow_expansions", 0)
        self._stats.setdefault("public_select_expansions", 0)
        self._stats.setdefault("conflict_work_items", 0)
        self._stats.setdefault("select_cartesian_materializations", 0)
        self._stats.setdefault("select_packed_product_rows", 0)
        self._stats.setdefault("artifact_matcher_materializations", 0)
        self._stats.setdefault("artifact_matcher_rows", 0)
        self.stats = MappingProxyType(self._stats)

    def _language_concrete_upper_bound(
        self,
        language: _PackedLanguage,
    ) -> int:
        total = 0
        matcher_mask = (1 << self.bits) - 1
        for length, packed in language:
            choices = 1
            for position in range(length):
                matcher_id = (
                    packed >> (position * self.bits)
                ) & matcher_mask
                choices *= len(self.matcher_tokens[matcher_id])
            total += choices
        return total

    def _expand(
        self,
        language: _PackedLanguage,
        counter: str,
    ) -> LookaheadSet:
        self._stats[counter] += 1
        words: set[LookaheadWord] = set()
        matcher_mask = (1 << self.bits) - 1
        for length, packed in sorted(language):
            partials: list[LookaheadWord] = [EPSILON]
            for position in range(length):
                matcher_id = (
                    packed >> (position * self.bits)
                ) & matcher_mask
                partials = [
                    partial + (token,)
                    for partial in partials
                    for token in self.matcher_tokens[matcher_id]
                ]
            words.update(partials)
        return frozenset(words)

    def expand_first(self, language: _PackedLanguage) -> LookaheadSet:
        return self._expand(language, "public_first_expansions")

    def expand_follow(self, language: _PackedLanguage) -> LookaheadSet:
        return self._expand(language, "public_follow_expansions")

    def expand_select(self, language: _PackedLanguage) -> LookaheadSet:
        return self._expand(language, "public_select_expansions")

    @property
    def first_estimates(self) -> tuple[int, ...]:
        return self._first_estimates

    @property
    def follow_estimates(self) -> tuple[int, ...]:
        return self._follow_estimates

    def select_position(self, key: tuple[str, int]) -> int:
        try:
            return self._select_index[key]
        except KeyError:
            raise KeyError(key) from None

    def select_descriptor(self, key: tuple[str, int]) -> _SelectDescriptor:
        return self.select_descriptors[self.select_position(key)]

    def select_nonempty(self, key: tuple[str, int]) -> bool:
        position = self._select_index.get(key)
        if position is None:
            return False
        descriptor = self.select_descriptors[position]
        return bool(
            descriptor.direct
            or (
                descriptor.prefixes
                and self.follow[descriptor.owner_id]
            )
        )

    def _projected_follow(
        self,
        owner_id: int,
        budget: int,
    ) -> _PackedLanguage:
        projected: set[_PackedPrefix] = set()
        for length, packed in self.follow[owner_id]:
            taken = min(length, budget)
            projected.add((taken, packed & self.prefix_masks[taken]))
        return frozenset(projected)

    def _projected_follow_row_count(
        self,
        owner_id: int,
        budget: int,
    ) -> int:
        key = (owner_id, budget)
        cached = self._projection_rows.get(key)
        if cached is not None:
            return cached
        projected = self._projected_follow(owner_id, budget)
        count = len(projected)
        self._projection_rows[key] = count
        self._projection_concrete[key] = (
            self._language_concrete_upper_bound(projected)
        )
        return count

    def _projected_follow_concrete_upper_bound(
        self,
        owner_id: int,
        budget: int,
    ) -> int:
        key = (owner_id, budget)
        if key not in self._projection_concrete:
            self._projected_follow_row_count(owner_id, budget)
        return self._projection_concrete[key]

    def _prefix_concrete_choices(self, prefix: _PackedPrefix) -> int:
        length, packed = prefix
        matcher_mask = (1 << self.bits) - 1
        choices = 1
        for position in range(length):
            matcher_id = (
                packed >> (position * self.bits)
            ) & matcher_mask
            choices *= len(self.matcher_tokens[matcher_id])
        return choices

    def select_packed_upper_bound(self, position: int) -> int:
        descriptor = self.select_descriptors[position]
        return len(descriptor.direct) + sum(
            self._projected_follow_row_count(
                descriptor.owner_id,
                self.k - prefix[0],
            )
            for prefix in descriptor.prefixes
        )

    def select_concrete_upper_bound(self, position: int) -> int:
        descriptor = self.select_descriptors[position]
        return self._language_concrete_upper_bound(
            descriptor.direct
        ) + sum(
            self._prefix_concrete_choices(prefix)
            * self._projected_follow_concrete_upper_bound(
                descriptor.owner_id,
                self.k - prefix[0],
            )
            for prefix in descriptor.prefixes
        )

    def expanded_row_upper_bounds(self) -> dict[str, int]:
        return {
            "first": sum(self._first_estimates),
            "follow": sum(self._follow_estimates),
            "select": sum(
                self.select_concrete_upper_bound(position)
                for position in range(len(self.select_descriptors))
            ),
        }

    def packed_select_upper_bound(self) -> int:
        return sum(
            self.select_packed_upper_bound(position)
            for position in range(len(self.select_descriptors))
        )

    def _add_graph(
        self,
        language: _PackedLanguage,
        *,
        accepts_terminal: bool,
        epsilon_follow: int | None = None,
    ) -> int:
        graph_id = len(self._graphs)
        trie = _PackedTrie(language, self.bits)
        self._graphs.append(
            _FactorGraph(trie, accepts_terminal, epsilon_follow)
        )
        self._stats["factor_graphs"] = len(self._graphs)
        self._stats["factor_graph_nodes"] = sum(
            len(graph.trie.children) for graph in self._graphs
        )
        return graph_id

    def _follow_graph(self, owner_id: int) -> int:
        graph_id = self._follow_graphs[owner_id]
        if graph_id is None:
            graph_id = self._add_graph(
                self.follow[owner_id],
                accepts_terminal=True,
            )
            self._follow_graphs[owner_id] = graph_id
            self._stats["shared_follow_tries"] = sum(
                item is not None for item in self._follow_graphs
            )
        return graph_id

    def _closure(self, nodes: set[tuple[int, int]]) -> _FactorState:
        pending = list(nodes)
        closed = set(nodes)
        while pending:
            graph_id, node = pending.pop()
            graph = self._graphs[graph_id]
            target = graph.epsilon_follow
            if target is None or not graph.trie.terminal[node]:
                continue
            follow_root = (target, 0)
            if follow_root not in closed:
                closed.add(follow_root)
                pending.append(follow_root)
            if not graph.trie.children[node]:
                closed.discard((graph_id, node))
        return tuple(sorted(closed))

    def _descriptor_state(self, position: int) -> _FactorState:
        cached = self._descriptor_states[position]
        if cached is not None:
            return cached
        descriptor = self.select_descriptors[position]
        nodes: set[tuple[int, int]] = set()
        if descriptor.direct:
            graph_id = self._direct_graphs[position]
            if graph_id is None:
                graph_id = self._add_graph(
                    descriptor.direct,
                    accepts_terminal=True,
                )
                self._direct_graphs[position] = graph_id
            nodes.add((graph_id, 0))
        if descriptor.prefixes and self.follow[descriptor.owner_id]:
            graph_id = self._prefix_graphs[position]
            if graph_id is None:
                follow_graph = self._follow_graph(descriptor.owner_id)
                graph_id = self._add_graph(
                    frozenset(descriptor.prefixes),
                    accepts_terminal=False,
                    epsilon_follow=follow_graph,
                )
                self._prefix_graphs[position] = graph_id
            nodes.add((graph_id, 0))
        state = self._closure(nodes)
        self._descriptor_states[position] = state
        return state

    def _children(
        self,
        state: _FactorState,
    ) -> tuple[tuple[int, _FactorState], ...]:
        cached = self._state_children.get(state)
        if cached is not None:
            return cached
        by_matcher: dict[int, set[tuple[int, int]]] = defaultdict(set)
        for graph_id, node in state:
            graph = self._graphs[graph_id]
            for matcher_id, child in graph.trie.children[node].items():
                by_matcher[matcher_id].add((graph_id, child))
        children = tuple(
            (
                matcher_id,
                self._closure(nodes),
            )
            for matcher_id, nodes in sorted(by_matcher.items())
        )
        self._state_children[state] = children
        return children

    def _terminal(self, state: _FactorState) -> bool:
        cached = self._state_terminal.get(state)
        if cached is not None:
            return cached
        terminal = any(
            self._graphs[graph_id].accepts_terminal
            and self._graphs[graph_id].trie.terminal[node]
            for graph_id, node in state
        )
        self._state_terminal[state] = terminal
        return terminal

    def _has_strict_non_end_descendant(
        self,
        state: _FactorState,
        remaining: int,
    ) -> bool:
        if remaining <= 0:
            return False
        cache_key = (state, remaining)
        cached = self._strict_non_end.get(cache_key)
        if cached is not None:
            return cached
        for matcher_id, child in self._children(state):
            if not any(
                token != END
                for token in self.matcher_tokens[matcher_id]
            ):
                continue
            if (
                remaining == 1
                or self._terminal(child)
                or self._has_strict_non_end_descendant(
                    child,
                    remaining - 1,
                )
            ):
                self._strict_non_end[cache_key] = True
                return True
        self._strict_non_end[cache_key] = False
        return False

    def _intersection(self, left: int, right: int) -> tuple[str, ...]:
        key = (min(left, right), max(left, right))
        cached = self._matcher_intersections.get(key)
        if cached is None:
            cached = tuple(
                sorted(
                    set(self.matcher_tokens[left]).intersection(
                        self.matcher_tokens[right]
                    )
                )
            )
            self._matcher_intersections[key] = cached
        return cached

    def runtime_dispatch_conflict_witness(
        self,
        left_position: int,
        right_position: int,
    ) -> LookaheadWord | None:
        # Legacy compatibility: validate the raw FIRST rows consumed by the
        # reference runtime. Canonical SELECT conflict detection would also
        # expand FOLLOW for nullable alternatives and flag strict prefixes.
        left_trie = self._runtime_trie(left_position)
        right_trie = self._runtime_trie(right_position)
        memo: dict[tuple[int, int, int], LookaheadWord | None] = {}

        def visit(
            left_node: int,
            right_node: int,
            remaining: int,
        ) -> LookaheadWord | None:
            key = (left_node, right_node, remaining)
            if key in memo:
                return memo[key]
            self._stats["conflict_work_items"] += 1

            if remaining == 0:
                memo[key] = EPSILON
                return EPSILON
            if (
                left_trie.terminal[left_node]
                and right_trie.terminal[right_node]
            ):
                memo[key] = EPSILON
                return EPSILON
            if (
                left_trie.terminal[left_node]
                or right_trie.terminal[right_node]
            ):
                memo[key] = None
                return None
            candidates: list[LookaheadWord] = []
            for left_matcher, left_child in left_trie.children[
                left_node
            ].items():
                for right_matcher, right_child in right_trie.children[
                    right_node
                ].items():
                    intersection = self._intersection(
                        left_matcher,
                        right_matcher,
                    )
                    if not intersection:
                        continue
                    token_candidates = []
                    non_end = tuple(
                        token for token in intersection if token != END
                    )
                    if non_end:
                        token_candidates.append(non_end[0])
                    if END in intersection:
                        token_candidates.append(END)
                    for token in token_candidates:
                        suffix = visit(
                            left_child,
                            right_child,
                            remaining - 1,
                        )
                        if suffix is not None:
                            candidates.append((token, *suffix))
            result = min(
                candidates,
                key=lambda word: (len(word), word),
                default=None,
            )
            memo[key] = result
            return result

        return visit(0, 0, self.k)

    def canonical_conflict_witness(
        self,
        left_position: int,
        right_position: int,
    ) -> LookaheadWord | None:
        def visit(
            left: _FactorState,
            right: _FactorState,
            remaining: int,
        ) -> LookaheadWord | None:
            if right < left:
                left, right = right, left
            key = (left, right, remaining)
            if key in self._conflict_memo:
                return self._conflict_memo[key]
            self._stats["conflict_work_items"] += 1

            if remaining == 0 or (
                self._terminal(left) and self._terminal(right)
            ):
                result: LookaheadWord | None = EPSILON
            else:
                candidates: list[LookaheadWord] = []
                for left_matcher, left_child in self._children(left):
                    for right_matcher, right_child in self._children(right):
                        tokens = self._intersection(left_matcher, right_matcher)
                        if not tokens:
                            continue
                        suffix = visit(left_child, right_child, remaining - 1)
                        if suffix is not None:
                            candidates.append((tokens[0], *suffix))
                result = min(
                    candidates,
                    key=lambda word: (len(word), word),
                    default=None,
                )
            self._conflict_memo[key] = result
            return result

        return visit(
            self._descriptor_state(left_position),
            self._descriptor_state(right_position),
            self.k,
        )

    def _runtime_trie(self, position: int) -> _PackedTrie:
        cached = self._runtime_tries[position]
        if cached is not None:
            return cached
        descriptor = self.select_descriptors[position]
        language = frozenset(
            (*descriptor.direct, *descriptor.prefixes)
        )
        trie = _PackedTrie(language, self.bits)
        self._runtime_tries[position] = trie
        return trie

    def iter_runtime_matcher_rows(
        self,
        position: int,
    ) -> Iterator[tuple[int, ...]]:
        trie = self._runtime_trie(position)

        def walk(
            node: int,
            prefix: tuple[int, ...],
        ) -> Iterator[tuple[int, ...]]:
            if trie.terminal[node]:
                yield prefix
            if len(prefix) == self.k:
                return
            for matcher_id, child in sorted(trie.children[node].items()):
                yield from walk(child, (*prefix, matcher_id))

        yield from walk(0, ())

    def iter_legacy_cycle_prefix_rows(
        self,
        position: int,
    ) -> Iterator[tuple[int, ...]]:
        owner = self._alternative_owners[position]
        variant = self._alternative_variant_ids[position]
        found: set[tuple[int, ...]] = set()

        def walk(
            rhs: tuple[int, ...],
            rhs_position: int,
            prefix: tuple[int, ...],
            active: frozenset[int],
            continuations: tuple[
                tuple[tuple[int, ...], int, frozenset[int]],
                ...,
            ],
        ) -> None:
            if len(prefix) >= self.k:
                return
            if rhs_position >= len(rhs):
                if not continuations:
                    return
                next_rhs, next_position, next_active = continuations[0]
                walk(
                    next_rhs,
                    next_position,
                    prefix,
                    next_active,
                    continuations[1:],
                )
                return

            symbol = rhs[rhs_position]
            if symbol > 0:
                walk(
                    rhs,
                    rhs_position + 1,
                    (*prefix, symbol),
                    active,
                    continuations,
                )
                return

            child = -symbol - 1
            if child in active:
                if prefix:
                    found.add(prefix)
                return
            child_active = active | {child}
            continuation = (
                (rhs, rhs_position + 1, active),
                *continuations,
            )
            for child_variant in self._alternatives_by_lhs[child]:
                walk(
                    self._variants[child_variant],
                    0,
                    prefix,
                    child_active,
                    continuation,
                )

        # Legacy compatibility: the reference 1C fixed-point traversal keeps
        # the prefix accumulated when it cuts a recursive dependency. A
        # canonical FIRST(k) solver discards that incomplete word.
        walk(
            self._variants[variant],
            0,
            (),
            frozenset({owner}),
            (),
        )
        yield from sorted(found, key=lambda word: (len(word), word))

    def iter_matcher_rows(
        self,
        position: int,
    ) -> Iterator[tuple[int, ...]]:
        state = self._descriptor_state(position)

        def walk(
            current: _FactorState,
            prefix: tuple[int, ...],
        ) -> Iterator[tuple[int, ...]]:
            if len(prefix) == self.k:
                yield prefix
                return
            if self._terminal(current):
                yield prefix
            for matcher_id, child in self._children(current):
                yield from walk(child, (*prefix, matcher_id))

        yield from walk(state, ())

    def materialize_select(self, position: int) -> LookaheadSet:
        self._stats["select_cartesian_materializations"] += 1
        words: set[LookaheadWord] = set()
        packed_rows = 0
        for matcher_row in self.iter_matcher_rows(position):
            packed_rows += 1
            partials: list[LookaheadWord] = [EPSILON]
            for matcher_id in matcher_row:
                partials = [
                    (*partial, token)
                    for partial in partials
                    for token in self.matcher_tokens[matcher_id]
                ]
            words.update(partials)
        self._stats["select_packed_product_rows"] += packed_rows
        self._stats["public_select_expansions"] += 1
        return frozenset(words)

    def build_matcher_artifact(
        self,
        *,
        max_rows: int,
    ) -> SelectMatcherArtifact:
        if max_rows < 1:
            raise LookaheadMaterializationError(
                "select-matcher-artifact",
                "all",
                1,
                max_rows,
            )
        rows: list[SelectMatcherRow] = []
        for position, (production, alternative) in enumerate(
            self.select_keys
        ):
            concrete_words: set[LookaheadWord] = set()
            for matcher_rows in (
                self.iter_runtime_matcher_rows(position),
                self.iter_legacy_cycle_prefix_rows(position),
            ):
                for matcher_row in matcher_rows:
                    concrete_rows: list[LookaheadWord] = [EPSILON]
                    for matcher_id in matcher_row:
                        token_types = self.matcher_tokens[matcher_id]
                        estimated_rows = (
                            len(rows)
                            + len(concrete_words)
                            + (len(concrete_rows) * len(token_types))
                        )
                        if estimated_rows > max_rows:
                            raise LookaheadMaterializationError(
                                "select-matcher-artifact",
                                "all",
                                estimated_rows,
                                max_rows,
                            )
                        concrete_rows = [
                            (*prefix, token)
                            for prefix in concrete_rows
                            for token in token_types
                        ]
                    concrete_words.update(concrete_rows)

            minimized: list[LookaheadWord] = []
            kept: set[LookaheadWord] = set()
            for concrete_word in sorted(
                concrete_words,
                key=lambda word: (len(word), word),
            ):
                shadowed = bool(concrete_word) and any(
                    concrete_word[:length] in kept
                    for length in range(1, len(concrete_word))
                )
                if shadowed:
                    continue
                minimized.append(concrete_word)
                kept.add(concrete_word)

            # Legacy compatibility: canonical SELECT(k) retains all complete
            # lookahead words (and compressed matcher classes). The reference
            # 1C generator expands classes to concrete tokens, then collapses
            # longer words shadowed by a non-empty prefix in the same
            # alternative. EPSILON remains alongside consuming descendants.
            rows.extend(
                SelectMatcherRow(
                    production,
                    alternative,
                    concrete_word,
                )
                for concrete_word in minimized
            )
            if len(rows) > max_rows:
                raise LookaheadMaterializationError(
                    "select-matcher-artifact",
                    "all",
                    len(rows),
                    max_rows,
                )
        self._stats["artifact_matcher_materializations"] += 1
        self._stats["artifact_matcher_rows"] += len(rows)
        return SelectMatcherArtifact(tuple(rows), ())


def _packed_concat(
    left: _PackedPrefix,
    right: _PackedPrefix,
    solver: _ContinuationFirst,
) -> _PackedPrefix:
    left_length, left_packed = left
    if left_length >= solver.k:
        return solver.k, left_packed & solver.prefix_masks[solver.k]
    right_length, right_packed = right
    taken = min(right_length, solver.k - left_length)
    return (
        left_length + taken,
        left_packed
        | (
            (right_packed & solver.prefix_masks[taken])
            << (left_length * solver.bits)
        ),
    )


def _packed_project(
    value: _PackedPrefix,
    max_length: int,
    solver: _ContinuationFirst,
) -> _PackedPrefix:
    length, packed = value
    taken = min(length, max_length)
    return taken, packed & solver.prefix_masks[taken]


def _compute_packed_follow(
    solver: _ContinuationFirst,
    start_productions: tuple[str, ...],
) -> tuple[tuple[_PackedLanguage, ...], dict[str, int]]:
    follow: list[set[_PackedPrefix]] = [
        set() for _ in solver.production_names
    ]
    outgoing: list[dict[int, _FollowTransformGroup]] = [
        {} for _ in solver.production_names
    ]
    transform_keys: set[tuple[int, int, _PackedPrefix]] = set()
    direct: list[tuple[int, _PackedPrefix]] = []
    direct_keys: set[tuple[int, _PackedPrefix]] = set()
    stats: dict[str, int] = defaultdict(int)

    for occurrence in solver.occurrences:
        for length, packed, complete in solver.variant_facts[
            occurrence.suffix_variant_id
        ]:
            prefix = (length, packed)
            if length == solver.k:
                key = (occurrence.referenced_id, prefix)
                if key not in direct_keys:
                    direct_keys.add(key)
                    direct.append(key)
                else:
                    stats["duplicate_follow_direct_facts"] += 1
                continue
            if not complete:
                stats["short_incomplete_follow_facts_ignored"] += 1
                continue
            transform_key = (
                occurrence.parent_id,
                occurrence.referenced_id,
                prefix,
            )
            if transform_key in transform_keys:
                stats["duplicate_follow_transforms"] += 1
                continue
            transform_keys.add(transform_key)
            transform = _FollowTransform(*transform_key)
            needed = solver.k - prefix[0]
            group = outgoing[occurrence.parent_id].get(needed)
            if group is None:
                group = _FollowTransformGroup(needed)
                outgoing[occurrence.parent_id][needed] = group
            group.transforms.append(transform)

    delta_queues: list[deque[_PackedPrefix]] = [
        deque() for _ in solver.production_names
    ]
    production_queue: deque[int] = deque()
    in_production_queue: set[int] = set()

    def publish(production_id: int, fact: _PackedPrefix) -> None:
        if fact in follow[production_id]:
            stats["duplicate_follow_facts"] += 1
            return
        follow[production_id].add(fact)
        delta_queues[production_id].append(fact)
        if production_id not in in_production_queue:
            production_queue.append(production_id)
            in_production_queue.add(production_id)
        stats["follow_delta_facts"] += 1

    seen_starts: set[int] = set()
    for production_name in start_productions:
        production_id = solver.production_ids[production_name]
        if production_id in seen_starts:
            continue
        seen_starts.add(production_id)
        publish(production_id, (1, solver.end_matcher_id))
    for referenced_id, prefix in direct:
        publish(referenced_id, prefix)

    while production_queue:
        parent_id = production_queue.popleft()
        deltas = delta_queues[parent_id]
        while deltas:
            delta = deltas.popleft()
            stats["follow_work_items"] += 1
            for group in outgoing[parent_id].values():
                stats["follow_projection_checks"] += 1
                projection = _packed_project(delta, group.needed, solver)
                if projection in group.seen_projections:
                    stats["duplicate_follow_projections"] += 1
                    continue
                group.seen_projections.add(projection)
                for transform in group.transforms:
                    stats["follow_transform_applications"] += 1
                    publish(
                        transform.referenced_id,
                        _packed_concat(transform.prefix, projection, solver),
                    )
        in_production_queue.remove(parent_id)

    packed = tuple(frozenset(items) for items in follow)
    stats["follow_transforms"] = len(transform_keys)
    stats["follow_direct_facts"] = len(direct_keys)
    stats["follow_facts"] = sum(map(len, packed))
    stats["follow_expanded_row_upper_bound"] = sum(
        solver.language_expanded_row_upper_bound(language)
        for language in packed
    )
    for name in (
        "duplicate_follow_direct_facts",
        "short_incomplete_follow_facts_ignored",
        "duplicate_follow_transforms",
        "duplicate_follow_facts",
        "follow_transform_applications",
        "follow_projection_checks",
        "duplicate_follow_projections",
    ):
        stats.setdefault(name, 0)
    return packed, dict(stats)


def _compute_factorized_select(
    grammar: ResolvedGrammar,
    solver: _ContinuationFirst,
) -> tuple[
    tuple[tuple[str, int], ...],
    tuple[_SelectDescriptor, ...],
    dict[str, int],
]:
    keys: list[tuple[str, int]] = []
    descriptors: list[_SelectDescriptor] = []
    stats: dict[str, int] = defaultdict(int)
    alternative_id = 0
    for production_id, production_name in enumerate(
        grammar.production_order
    ):
        for alternative_number, _ in enumerate(
            grammar.productions[production_name],
            start=1,
        ):
            variant_id = solver.alternative_variant_ids[alternative_id]
            alternative_id += 1
            direct: set[_PackedPrefix] = set()
            prefixes: set[_PackedPrefix] = set()
            for length, packed, complete in solver.variant_facts[variant_id]:
                prefix = (length, packed)
                if length == solver.k:
                    direct.add(prefix)
                    continue
                if not complete:
                    stats["short_incomplete_select_facts_ignored"] += 1
                    continue
                prefixes.add(prefix)
            keys.append((production_name, alternative_number))
            descriptors.append(
                _SelectDescriptor(
                    production_id,
                    frozenset(direct),
                    tuple(sorted(prefixes)),
                )
            )
    factorized = tuple(descriptors)
    stats["select_descriptors"] = len(factorized)
    stats["select_direct_facts"] = sum(
        len(descriptor.direct) for descriptor in factorized
    )
    stats["select_short_complete_prefixes"] = sum(
        len(descriptor.prefixes) for descriptor in factorized
    )
    stats["select_concatenations"] = 0
    stats["select_cartesian_materializations"] = 0
    stats["select_packed_product_rows"] = 0
    for name in (
        "short_incomplete_select_facts_ignored",
    ):
        stats.setdefault(name, 0)
    return tuple(keys), factorized, dict(stats)


def _compute_first(
    grammar: ResolvedGrammar,
    k: int,
) -> tuple[dict[str, LookaheadSet], dict[str, int]]:
    solver = _ContinuationFirst(grammar, k)
    raw = solver.run_core()
    return solver.expand(raw), solver.updates(raw)


def _select_conflict_witness(
    left: LookaheadSet,
    right: LookaheadSet,
) -> LookaheadWord | None:
    return min(
        left.intersection(right),
        key=lambda word: (len(word), word),
        default=None,
    )
