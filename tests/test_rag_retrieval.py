from pathlib import Path

from voice_triage.rag.answer import LocalRagService
from voice_triage.rag.index import build_index
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
