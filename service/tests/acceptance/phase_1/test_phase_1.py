"""Independent acceptance audit tests for Phase 1 (models, data, normalizer, ranking)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from typer.testing import CliRunner

from skillgap.classifier import classify, classify_role, is_ambiguous, validate_category
from skillgap.cli import app
from skillgap.config import AliasConfig, RolesConfig, load_config
from skillgap.dedup import dedup_extracted_skills, dedup_gaps, merge_to_gap
from skillgap.models import (
    Category,
    ExtractedSkill,
    Gap,
    Level,
    Posting,
    RankedGap,
    Resume,
    Role,
    Skill,
)
from skillgap.normalizer import build_lookup, get_parents, normalize, normalize_batch
from skillgap.ranking import rank_gaps, score_gap

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "tech"
nonblank = st.text(min_size=1, max_size=30).filter(lambda s: s.strip() != "")
categories = st.sampled_from(list(Category))
levels = st.sampled_from(list(Level))


@pytest.fixture(scope="module")
def cfgs() -> tuple[AliasConfig, RolesConfig]:
    return load_config()


@pytest.fixture(scope="module")
def aliases(cfgs: tuple[AliasConfig, RolesConfig]) -> AliasConfig:
    return cfgs[0]


@pytest.fixture(scope="module")
def roles(cfgs: tuple[AliasConfig, RolesConfig]) -> RolesConfig:
    return cfgs[1]


@pytest.fixture(scope="module")
def lookup(aliases: AliasConfig) -> dict[str, str]:
    return build_lookup(aliases)


def _gap(skill: str = "python", score: float = 1.0, count: int = 1, **kw: int) -> Gap:
    return Gap(skill=skill, category=Category.language, score=score, posting_count=count, **kw)


def _ex(name: str, level: Level, evidence: str = "ev") -> ExtractedSkill:
    return ExtractedSkill(name=name, category=Category.language, level=level, evidence=evidence)


# ---------------------------------------------------------------- models


def test_enums_values() -> None:
    assert {c.value for c in Category} == {
        "language",
        "framework",
        "cloud_infra",
        "data",
        "ai_ml",
        "practice",
        "customer_facing",
        "soft_skill",
    }
    assert {lv.value for lv in Level} == {"required", "preferred", "unspecified"}
    assert {r.value for r in Role} >= {"software_engineer", "ai_engineer", "fde", "excluded"}


def test_skill_valid_and_defaults() -> None:
    s = Skill(canonical_name="python", category=Category.language)
    assert s.ambiguous is False
    assert s.canonical_name == "python"


@pytest.mark.parametrize("bad", ["", "   ", "\n\t"])
def test_skill_rejects_blank_name(bad: str) -> None:
    with pytest.raises(ValidationError):
        Skill(canonical_name=bad, category=Category.language)


def test_skill_rejects_invalid_category() -> None:
    with pytest.raises(ValidationError):
        Skill(canonical_name="x", category="nonsense")  # type: ignore[arg-type]


def test_models_are_frozen() -> None:
    s = Skill(canonical_name="python", category=Category.language)
    with pytest.raises(ValidationError):
        s.canonical_name = "java"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        _gap().score = 3.0  # type: ignore[misc]


def test_posting_valid() -> None:
    p = Posting(id="p1", title="Backend Engineer", text="Build services.")
    assert p.role is None and p.url is None and p.posted_date is None
    assert p.sections == {}


@pytest.mark.parametrize("field", ["title", "text"])
def test_posting_rejects_blank(field: str) -> None:
    kw = {"id": "p1", "title": "T", "text": "body"}
    kw[field] = "  "
    with pytest.raises(ValidationError):
        Posting(**kw)


def test_posting_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        Posting(id="p1", title="T")  # type: ignore[call-arg]


def test_resume_valid_and_blank_text() -> None:
    r = Resume(id="r1", text="Python dev")
    assert r.skills == ()
    with pytest.raises(ValidationError):
        Resume(id="r1", text="   ")


def test_extracted_skill_validation() -> None:
    assert _ex("python", Level.required).evidence == "ev"
    with pytest.raises(ValidationError):
        _ex("", Level.required)
    with pytest.raises(ValidationError):
        _ex("python", Level.required, evidence=" ")


def test_gap_valid_defaults() -> None:
    g = _gap()
    assert g.required_count == 0 and g.preferred_count == 0


def test_gap_score_boundary() -> None:
    assert _gap(score=0.0).score == 0.0
    with pytest.raises(ValidationError):
        _gap(score=-0.01)


def test_gap_posting_count_boundary() -> None:
    assert _gap(count=1).posting_count == 1
    with pytest.raises(ValidationError):
        _gap(count=0)
    with pytest.raises(ValidationError):
        _gap(count=-1)


def test_gap_counts_constraints() -> None:
    assert _gap(count=2, required_count=1, preferred_count=1).posting_count == 2
    with pytest.raises(ValidationError):
        _gap(count=2, required_count=2, preferred_count=1)
    with pytest.raises(ValidationError):
        _gap(count=2, required_count=-1)
    with pytest.raises(ValidationError):
        _gap(count=2, preferred_count=-1)


def test_gap_blank_skill() -> None:
    with pytest.raises(ValidationError):
        _gap(skill=" ")


def test_ranked_gap_rank_boundary() -> None:
    assert RankedGap(rank=1, gap=_gap()).rank == 1
    for bad in (0, -3):
        with pytest.raises(ValidationError):
            RankedGap(rank=bad, gap=_gap())


@given(name=nonblank, cat=categories, amb=st.booleans())
def test_skill_roundtrip(name: str, cat: Category, amb: bool) -> None:
    s = Skill(canonical_name=name, category=cat, ambiguous=amb)
    assert Skill.model_validate(s.model_dump()) == s
    assert Skill.model_validate_json(s.model_dump_json()) == s


@given(
    skill=nonblank,
    cat=categories,
    score=st.floats(min_value=0, max_value=1000, allow_nan=False),
    req=st.integers(0, 5),
    pref=st.integers(0, 5),
    extra=st.integers(0, 5),
)
def test_gap_and_ranked_roundtrip(
    skill: str, cat: Category, score: float, req: int, pref: int, extra: int
) -> None:
    g = Gap(
        skill=skill,
        category=cat,
        score=score,
        posting_count=max(1, req + pref + extra),
        required_count=req,
        preferred_count=pref,
    )
    assert Gap.model_validate_json(g.model_dump_json()) == g
    rg = RankedGap(rank=1, gap=g)
    assert RankedGap.model_validate_json(rg.model_dump_json()) == rg


@given(id_=nonblank, title=nonblank, text=nonblank)
def test_posting_resume_roundtrip(id_: str, title: str, text: str) -> None:
    p = Posting(id=id_, title=title, text=text)
    assert Posting.model_validate_json(p.model_dump_json()) == p
    r = Resume(id=id_, text=text, skills=(_ex("python", Level.required),))
    assert Resume.model_validate_json(r.model_dump_json()) == r


# ---------------------------------------------------------------- data files


def test_data_files_exist_and_parse() -> None:
    for name in ("aliases.yaml", "roles.yaml"):
        data = yaml.safe_load((DATA_DIR / name).read_text())
        assert isinstance(data, dict) and data


def test_load_config_returns_valid_models(cfgs: tuple[AliasConfig, RolesConfig]) -> None:
    a, r = cfgs
    assert isinstance(a, AliasConfig) and isinstance(r, RolesConfig)
    assert len(a.skills) >= 50
    assert "python" in a.skills


def test_load_config_missing_dir(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path)


def test_alias_entries_well_formed(aliases: AliasConfig) -> None:
    for name, entry in aliases.skills.items():
        assert name == name.strip().lower() and name
        assert isinstance(entry.category, Category)
        for al in entry.aliases:
            assert al == al.strip().lower() and al
        if entry.parent is not None:
            assert entry.parent in aliases.skills, f"{name} parent missing"


def test_aliases_unique_across_skills(aliases: AliasConfig) -> None:
    seen: dict[str, str] = {}
    for name, entry in aliases.skills.items():
        for al in entry.aliases:
            assert al not in aliases.skills or al == name
            assert al not in seen, f"{al} duplicated"
            seen[al] = name


def test_parent_chains_acyclic(aliases: AliasConfig) -> None:
    for name in aliases.skills:
        seen = {name}
        cur = aliases.skills[name].parent
        while cur is not None:
            assert cur not in seen, f"cycle at {name}"
            seen.add(cur)
            cur = aliases.skills[cur].parent


def test_alias_config_rejects_duplicate_alias() -> None:
    with pytest.raises(ValidationError):
        AliasConfig(
            skills={
                "a": {"category": "language", "aliases": ["x"]},
                "b": {"category": "language", "aliases": ["x"]},
            }  # type: ignore[arg-type]
        )


def test_alias_config_rejects_alias_equal_to_other_canonical() -> None:
    with pytest.raises(ValidationError):
        AliasConfig(
            skills={
                "a": {"category": "language", "aliases": ["b"]},
                "b": {"category": "language"},
            }  # type: ignore[arg-type]
        )


def test_alias_config_rejects_parent_cycle() -> None:
    with pytest.raises(ValidationError):
        AliasConfig(
            skills={
                "a": {"category": "language", "parent": "b"},
                "b": {"category": "language", "parent": "a"},
            }  # type: ignore[arg-type]
        )


def test_alias_config_rejects_unknown_parent() -> None:
    with pytest.raises(ValidationError):
        AliasConfig(
            skills={"a": {"category": "language", "parent": "ghost"}}  # type: ignore[arg-type]
        )


def test_alias_config_rejects_bad_category() -> None:
    with pytest.raises(ValidationError):
        AliasConfig(skills={"a": {"category": "bogus"}})  # type: ignore[arg-type]


def test_alias_config_lowercases() -> None:
    cfg = AliasConfig(
        skills={"Python": {"category": "language", "aliases": ["  PY "]}}  # type: ignore[arg-type]
    )
    assert "python" in cfg.skills
    assert cfg.skills["python"].aliases == ["py"]


def test_roles_config_structure(roles: RolesConfig) -> None:
    assert set(roles.roles) == {Role.software_engineer, Role.ai_engineer, Role.fde}
    assert all(rp.include for rp in roles.roles.values())
    assert roles.exclude
    assert sorted(roles.precedence) == sorted([Role.software_engineer, Role.ai_engineer, Role.fde])
    assert len(set(roles.precedence)) == 3


def test_roles_config_rejects_bad_regex() -> None:
    with pytest.raises(ValidationError):
        RolesConfig(
            roles={Role.fde: {"include": ["("]}},  # type: ignore[arg-type]
            exclude=[],
            precedence=[Role.fde, Role.ai_engineer, Role.software_engineer],
        )
    with pytest.raises(ValidationError):
        RolesConfig(
            roles={Role.fde: {"include": ["fde"]}},  # type: ignore[arg-type]
            exclude=["["],
            precedence=[Role.fde, Role.ai_engineer, Role.software_engineer],
        )


def test_roles_config_rejects_bad_precedence() -> None:
    base = {Role.fde: {"include": ["fde"]}}
    for prec in (
        [Role.fde, Role.ai_engineer],
        [Role.fde, Role.fde, Role.ai_engineer, Role.software_engineer],
        [Role.fde, Role.ai_engineer, Role.excluded],
    ):
        with pytest.raises(ValidationError):
            RolesConfig(roles=base, exclude=[], precedence=prec)  # type: ignore[arg-type]


# ---------------------------------------------------------------- normalizer


def test_every_alias_resolves_to_canonical(aliases: AliasConfig, lookup: dict[str, str]) -> None:
    count = 0
    for canonical, entry in aliases.skills.items():
        for raw in [canonical, *entry.aliases]:
            sk = normalize(raw, lookup, aliases)
            assert sk is not None, raw
            assert sk.canonical_name == canonical, raw
            assert sk.category == entry.category
            assert sk.ambiguous == entry.ambiguous
            count += 1
    assert count > len(aliases.skills)


def test_normalize_case_and_whitespace(aliases: AliasConfig, lookup: dict[str, str]) -> None:
    for raw in ["Python", "PYTHON", "  python  ", "\tPy\n", "PY", "Python3"]:
        sk = normalize(raw, lookup, aliases)
        assert sk is not None and sk.canonical_name == "python"
    sk = normalize("C++", lookup, aliases)
    assert sk is not None and sk.canonical_name == "c_plus_plus"
    sk = normalize("GoLang", lookup, aliases)
    assert sk is not None and sk.canonical_name == "go"


def test_normalize_unknown_and_empty(aliases: AliasConfig, lookup: dict[str, str]) -> None:
    assert normalize("definitely-not-a-skill-xyz", lookup, aliases) is None
    assert normalize("", lookup, aliases) is None
    assert normalize("   ", lookup, aliases) is None


def test_build_lookup_keys(aliases: AliasConfig, lookup: dict[str, str]) -> None:
    for canonical, entry in aliases.skills.items():
        assert lookup[canonical] == canonical
        for al in entry.aliases:
            assert lookup[al] == canonical
    assert all(k == k.strip().lower() for k in lookup)
    assert set(lookup.values()) <= set(aliases.skills)


def test_normalize_batch(aliases: AliasConfig, lookup: dict[str, str]) -> None:
    out = normalize_batch(["py", "nonexistent-zzz", "Java", "py"], lookup, aliases)
    assert len(out) == 4
    assert out[0] is not None and out[0].canonical_name == "python"
    assert out[1] is None
    assert out[2] is not None and out[2].canonical_name == "java"
    assert out[3] == out[0]
    assert normalize_batch([], lookup, aliases) == []


def test_get_parents(aliases: AliasConfig) -> None:
    child = next(n for n, e in aliases.skills.items() if e.parent)
    chain = get_parents(child, aliases)
    assert chain
    assert chain[0].canonical_name == aliases.skills[child].parent
    root = next(n for n, e in aliases.skills.items() if e.parent is None)
    assert get_parents(root, aliases) == []
    for sk in chain:
        assert sk.canonical_name in aliases.skills


@given(raw=st.text(max_size=30))
def test_normalizer_idempotent(raw: str) -> None:
    aliases, _ = load_config()
    lk = build_lookup(aliases)
    first = normalize(raw, lk, aliases)
    if first is None:
        return
    second = normalize(first.canonical_name, lk, aliases)
    assert second == first


@given(data=st.data())
def test_normalizer_alias_casing_property(data: st.DataObject) -> None:
    aliases, _ = load_config()
    lk = build_lookup(aliases)
    key = data.draw(st.sampled_from(sorted(lk)))
    variant = data.draw(st.sampled_from([key, key.upper(), key.title(), f"  {key}  "]))
    sk = normalize(variant, lk, aliases)
    assert sk is not None and sk.canonical_name == lk[key]


# ---------------------------------------------------------------- classifier


def test_classify_matches_dictionary(aliases: AliasConfig) -> None:
    for name, entry in aliases.skills.items():
        assert classify(name, aliases) == entry.category


def test_classify_unknown(aliases: AliasConfig) -> None:
    assert classify("not_in_dictionary_zzz", aliases) is None


def test_ambiguity_flag(aliases: AliasConfig) -> None:
    for name, entry in aliases.skills.items():
        assert is_ambiguous(name, aliases) == entry.ambiguous
    assert is_ambiguous("go", aliases) is True
    assert is_ambiguous("python", aliases) is False
    assert is_ambiguous("not_in_dictionary_zzz", aliases) is False


def test_validate_category(aliases: AliasConfig) -> None:
    assert validate_category("python", Category.language, aliases) is True
    assert validate_category("python", Category.soft_skill, aliases) is False
    assert validate_category("unknown_zzz", Category.soft_skill, aliases) is True


@pytest.mark.parametrize(
    ("title", "role"),
    [
        ("Software Engineer", Role.software_engineer),
        ("Senior Backend Engineer", Role.software_engineer),
        ("Site Reliability Engineer", Role.software_engineer),
        ("Machine Learning Engineer", Role.ai_engineer),
        ("AI Engineer", Role.ai_engineer),
        ("Forward Deployed Engineer", Role.fde),
        ("Solutions Architect", Role.fde),
        ("FORWARD-DEPLOYED ENGINEER", Role.fde),
        ("  software engineer  ", Role.software_engineer),
        ("Software Engineering Intern", Role.excluded),
        ("Engineering Manager", Role.excluded),
        ("Data Scientist", Role.excluded),
        ("Pastry Chef", Role.excluded),
        ("", Role.excluded),
    ],
)
def test_classify_role(roles: RolesConfig, title: str, role: Role) -> None:
    assert classify_role(title, roles) == role


def test_classify_role_precedence_and_exclude_first(roles: RolesConfig) -> None:
    # matches both ai_engineer and software_engineer patterns; ai has higher precedence
    assert classify_role("AI Platform Engineer", roles) == Role.ai_engineer
    # exclusion beats inclusion
    assert classify_role("Junior Software Engineer", roles) == Role.excluded
    assert classify_role("Sales Engineer", roles) == Role.excluded


# ---------------------------------------------------------------- ranking


def test_score_constants() -> None:
    assert score_gap([Level.required]) == 1.0
    assert score_gap([Level.unspecified]) == 0.75
    assert score_gap([Level.preferred]) == 0.5
    assert score_gap([]) == 0.0


def test_score_sums_across_postings() -> None:
    assert score_gap([Level.required, Level.required, Level.preferred]) == pytest.approx(2.5)
    assert score_gap([Level.unspecified] * 4) == pytest.approx(3.0)
    assert score_gap(list(Level)) == pytest.approx(2.25)


@given(ls=st.lists(levels, max_size=20))
def test_score_property(ls: list[Level]) -> None:
    expected = (
        ls.count(Level.required) * 1.0
        + ls.count(Level.unspecified) * 0.75
        + ls.count(Level.preferred) * 0.5
    )
    assert score_gap(ls) == pytest.approx(expected)
    assert score_gap(list(reversed(ls))) == pytest.approx(expected)


def test_rank_empty() -> None:
    assert rank_gaps([]) == []


def test_rank_sorted_desc_with_one_based_ranks() -> None:
    out = rank_gaps([_gap("a", 0.5), _gap("b", 3.0), _gap("c", 1.0)])
    assert [r.gap.skill for r in out] == ["b", "c", "a"]
    assert [r.rank for r in out] == [1, 2, 3]
    assert all(isinstance(r, RankedGap) for r in out)


def test_rank_single_and_does_not_mutate_input() -> None:
    gaps = [_gap("a", 0.5), _gap("b", 2.0)]
    snapshot = list(gaps)
    out = rank_gaps(gaps)
    assert gaps == snapshot
    assert len(out) == 2
    assert [r.rank for r in rank_gaps([_gap("z")])] == [1]


def test_rank_ties_are_deterministic() -> None:
    gaps = [_gap("b", 1.0), _gap("a", 1.0), _gap("c", 1.0)]
    out1 = rank_gaps(gaps)
    out2 = rank_gaps(list(reversed(gaps)))
    assert out1 == out2
    assert [r.gap.skill for r in out1] == ["a", "b", "c"]


@given(
    items=st.lists(
        st.tuples(
            st.sampled_from(["a", "b", "c", "d", "e"]),
            st.sampled_from([0.5, 0.75, 1.0, 1.5, 2.0]),
            st.integers(1, 3),
        ),
        max_size=15,
    ),
    seed=st.randoms(),
)
def test_rank_order_property(items: list[tuple[str, float, int]], seed: object) -> None:
    gaps = [_gap(s, sc, c) for s, sc, c in items]
    shuffled = list(gaps)
    seed.shuffle(shuffled)  # type: ignore[attr-defined]
    out = rank_gaps(gaps)
    assert out == rank_gaps(shuffled)
    assert [r.rank for r in out] == list(range(1, len(gaps) + 1))
    scores = [r.gap.score for r in out]
    assert scores == sorted(scores, reverse=True)
    assert sorted(r.gap.model_dump_json() for r in out) == sorted(g.model_dump_json() for g in gaps)


# ---------------------------------------------------------------- dedup


def test_dedup_extracted_groups_by_canonical(lookup: dict[str, str]) -> None:
    skills = [
        _ex("Python", Level.required),
        _ex("py", Level.preferred),
        _ex("Java", Level.required),
    ]
    groups = dedup_extracted_skills(skills, lookup)
    assert set(groups) == {"python", "java"}
    assert len(groups["python"]) == 2
    assert len(groups["java"]) == 1


def test_dedup_extracted_empty_and_unknown(lookup: dict[str, str]) -> None:
    assert dedup_extracted_skills([], lookup) == {}
    groups = dedup_extracted_skills(
        [_ex("Zorblax", Level.required), _ex(" zorblax ", Level.preferred)], lookup
    )
    assert list(groups) == ["zorblax"]
    assert len(groups["zorblax"]) == 2


def test_dedup_preserves_all_mentions(lookup: dict[str, str]) -> None:
    skills = [
        _ex(n, Level.required, evidence=f"e{i}") for i, n in enumerate(["py", "python3", "PY"])
    ]
    groups = dedup_extracted_skills(skills, lookup)
    assert sorted(m.evidence for m in groups["python"]) == ["e0", "e1", "e2"]


def test_merge_to_gap_counts_and_score() -> None:
    mentions = [
        _ex("python", Level.required),
        _ex("python", Level.required),
        _ex("python", Level.preferred),
        _ex("python", Level.unspecified),
    ]
    g = merge_to_gap("python", Category.language, mentions)
    assert g.skill == "python"
    assert g.category == Category.language
    assert g.posting_count == 4
    assert g.required_count == 2
    assert g.preferred_count == 1
    assert g.score == pytest.approx(2 * 1.0 + 0.5 + 0.75)


def test_merge_single_mention() -> None:
    g = merge_to_gap("python", Category.language, [_ex("python", Level.preferred)])
    assert (g.posting_count, g.required_count, g.preferred_count) == (1, 0, 1)
    assert g.score == pytest.approx(0.5)


def test_dedup_gaps_merges_same_skill() -> None:
    a = _gap("python", 1.0, 1, required_count=1)
    b = _gap("python", 0.5, 1, preferred_count=1)
    c = _gap("java", 1.0, 1, required_count=1)
    out = dedup_gaps([a, b, c])
    assert len(out) == 2
    py = next(g for g in out if g.skill == "python")
    assert py.posting_count == 2
    assert py.required_count == 1
    assert py.preferred_count == 1
    assert py.score == pytest.approx(1.5)
    assert next(g for g in out if g.skill == "java") == c


def test_dedup_gaps_empty_and_no_duplicates() -> None:
    assert dedup_gaps([]) == []
    gaps = [_gap("a"), _gap("b")]
    assert sorted(g.skill for g in dedup_gaps(gaps)) == ["a", "b"]


@given(st.lists(st.sampled_from(["a", "b", "c"]), max_size=12))
def test_dedup_gaps_unique_and_conserves_counts(names: list[str]) -> None:
    gaps = [_gap(n, 1.0, 1, required_count=1) for n in names]
    out = dedup_gaps(gaps)
    assert len({g.skill for g in out}) == len(out)
    assert sum(g.posting_count for g in out) == len(names)
    assert sum(g.required_count for g in out) == len(names)


# ---------------------------------------------------------------- CLI

runner = CliRunner()


def test_cli_analyze_placeholder(tmp_path: Path) -> None:
    p = tmp_path / "posting.txt"
    p.write_text("Backend engineer posting")
    result = runner.invoke(app, ["analyze", str(p)])
    assert result.exit_code == 0
    assert result.output.strip() != ""


def test_cli_analyze_with_resume_option(tmp_path: Path) -> None:
    p = tmp_path / "posting.txt"
    p.write_text("x")
    result = runner.invoke(app, ["analyze", str(p), "--resume", str(tmp_path / "r.txt")])
    assert result.exit_code == 0


def test_cli_analyze_requires_postings() -> None:
    result = runner.invoke(app, ["analyze"])
    assert result.exit_code != 0


def test_cli_help_lists_analyze() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "analyze" in result.output


def test_cli_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "analyze" in result.output
