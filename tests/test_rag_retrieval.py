import sqlite3
from pathlib import Path

import pytest

from voice_triage.rag.answer import LocalRagService
from voice_triage.rag.index import build_index, init_index
from voice_triage.rag.retrieve import SqliteRetriever


def test_retrieval_prefers_garden_waste_doc(tmp_path: Path) -> None:
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / "bins_garden_waste.md").write_text(
        "Garden waste collection is a paid subscription. "
        "You can order an extra garden waste wheelie bin and collections are every 2 weeks.",
        encoding="utf-8",
    )
    (kb_dir / "council_tax_discount.md").write_text(
        "Single person council tax discount is available when only one adult "
        "lives in the property.",
        encoding="utf-8",
    )

    index_db = tmp_path / "rag.db"
    build_index(kb_dir=kb_dir, index_db_path=index_db)

    service = LocalRagService(retriever=SqliteRetriever(index_db))
    answer, metadata = service.answer("How do I order a garden waste bin?")

    assert "garden waste" in answer.lower()
    assert metadata["used_kb"] is True
    assert metadata["hits"][0]["source"] == "bins_garden_waste.md"


def test_structured_kb_answer_omits_metadata_labels(tmp_path: Path) -> None:
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / "voting.md").write_text(
        "\n".join(
            [
                "title: Register to vote (UK)",
                "tags: [voting, register-to-vote]",
                "summary:",
                "- Register online and re-register after moving.",
                "key_points:",
                "- Registration usually needs your National Insurance number.",
                "demo_questions:",
                '- "Do I need to re-register?"',
            ]
        ),
        encoding="utf-8",
    )

    index_db = tmp_path / "rag.db"
    build_index(kb_dir=kb_dir, index_db_path=index_db)
    service = LocalRagService(retriever=SqliteRetriever(index_db))

    answer, metadata = service.answer("How do I register to vote?")

    assert metadata["used_kb"] is True
    assert "title:" not in answer.lower()
    assert "tags:" not in answer.lower()
    assert "demo_questions:" not in answer.lower()
    assert "register" in answer.lower()


def test_structured_kb_answer_excludes_demo_questions_content(tmp_path: Path) -> None:
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / "voting.md").write_text(
        "\n".join(
            [
                "title: Register to vote (UK)",
                "tags: [voting, register-to-vote]",
                "summary:",
                "- You should register online and re-register after moving.",
                "key_points:",
                "- You usually need your National Insurance number.",
                "demo_questions:",
                '- "Do I need to re-register to vote?"',
            ]
        ),
        encoding="utf-8",
    )

    index_db = tmp_path / "rag.db"
    build_index(kb_dir=kb_dir, index_db_path=index_db)
    service = LocalRagService(retriever=SqliteRetriever(index_db))

    answer, metadata = service.answer("Do I need to re-register to vote?")

    assert metadata["used_kb"] is True
    assert "register" in answer.lower()
    assert "do i need to re-register to vote" not in answer.lower()


def test_unknown_topic_returns_clear_plain_language_message(tmp_path: Path) -> None:
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / "bins.md").write_text(
        "Bin collection schedules are available online.",
        encoding="utf-8",
    )

    index_db = tmp_path / "rag.db"
    build_index(kb_dir=kb_dir, index_db_path=index_db)
    service = LocalRagService(retriever=SqliteRetriever(index_db))

    answer, metadata = service.answer("How do I apply for a passport?")

    assert metadata["used_kb"] is False
    assert "do not have an answer" in answer.lower()
    assert "different way" in answer.lower()


def test_structured_kb_answer_targets_specific_subtopic(tmp_path: Path) -> None:
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / "allotments_sites.md").write_text(
        "\n".join(
            [
                "title: Allotment sites and locations",
                "tags: [allotments, sites, facilities]",
                "summary:",
                "- There are multiple allotment sites across the city.",
                "key_points:",
                "- Some sites provide secure tool storage lockers.",
                "- Some sites provide shared water taps.",
                "- Contact the allotments team for exact site facilities.",
            ]
        ),
        encoding="utf-8",
    )

    index_db = tmp_path / "rag.db"
    build_index(kb_dir=kb_dir, index_db_path=index_db)
    service = LocalRagService(retriever=SqliteRetriever(index_db))

    answer, metadata = service.answer("Do allotment sites have tool storage?")

    assert metadata["used_kb"] is True
    assert "tool storage" in answer.lower()
    assert "water taps" not in answer.lower()


def test_build_index_reports_in_progress_when_db_writer_lock_is_held(tmp_path: Path) -> None:
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / "bins.md").write_text("Garden waste is available.", encoding="utf-8")

    index_db = tmp_path / "rag.db"
    init_index(index_db)

    with sqlite3.connect(index_db, timeout=0.1) as connection:
        connection.execute("BEGIN IMMEDIATE")
        with pytest.raises(RuntimeError, match="Reindex already in progress"):
            build_index(kb_dir=kb_dir, index_db_path=index_db)
