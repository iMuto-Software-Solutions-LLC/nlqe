"""Unit tests for GoldenDataset and DatasetLoader."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from nlqe.testing.datasets import DatasetLoader, GoldenDataset, GoldenTestCase

# ---------------------------------------------------------------------------
# GoldenTestCase construction
# ---------------------------------------------------------------------------


class TestGoldenTestCase:
    def test_minimal_construction(self) -> None:
        tc = GoldenTestCase(
            id="t1",
            category="aggregation",
            description="A test",
            datasource={"path": "data.parquet"},
            user_query="How many rows?",
            expected_results=[{"n": 1}],
            expected_answer_summary="1 row",
        )
        assert tc.difficulty == "medium"  # default
        assert tc.priority == "medium"  # default
        assert tc.acceptable_variance == 0.0

    def test_variance_must_be_non_negative(self) -> None:
        with pytest.raises(Exception):
            GoldenTestCase(
                id="t",
                category="a",
                description="d",
                datasource={},
                user_query="q",
                expected_results=[],
                expected_answer_summary="s",
                acceptable_variance=-0.1,
            )


# ---------------------------------------------------------------------------
# GoldenDataset filtering
# ---------------------------------------------------------------------------


class TestGoldenDataset:
    @pytest.fixture
    def dataset(self) -> GoldenDataset:
        def _make(id: str, category: str, difficulty: str, tags: list[str]) -> GoldenTestCase:
            return GoldenTestCase(
                id=id,
                category=category,
                difficulty=difficulty,
                description=f"test {id}",
                datasource={"path": "p"},
                user_query="q",
                expected_results=[],
                expected_answer_summary="s",
                tags=tags,
            )

        return GoldenDataset(
            version="1.0",
            created_date="2026-01-01",
            datasets=[
                _make("a1", "aggregation", "easy", ["count"]),
                _make("a2", "aggregation", "medium", ["sum"]),
                _make("j1", "join", "hard", ["join", "count"]),
                _make("j2", "join", "easy", ["join"]),
            ],
        )

    def test_count(self, dataset: GoldenDataset) -> None:
        assert dataset.count == 4

    def test_get_by_category(self, dataset: GoldenDataset) -> None:
        agg = dataset.get_by_category("aggregation")
        assert len(agg) == 2
        assert all(tc.category == "aggregation" for tc in agg)

    def test_get_by_category_empty(self, dataset: GoldenDataset) -> None:
        assert dataset.get_by_category("nonexistent") == []

    def test_get_by_difficulty(self, dataset: GoldenDataset) -> None:
        easy = dataset.get_by_difficulty("easy")
        assert len(easy) == 2
        assert all(tc.difficulty == "easy" for tc in easy)

    def test_get_by_tag(self, dataset: GoldenDataset) -> None:
        tagged = dataset.get_by_tag("count")
        assert len(tagged) == 2

    def test_categories_property(self, dataset: GoldenDataset) -> None:
        assert dataset.categories == {"aggregation", "join"}

    def test_difficulties_property(self, dataset: GoldenDataset) -> None:
        assert dataset.difficulties == {"easy", "medium", "hard"}

    def test_all_tags_property(self, dataset: GoldenDataset) -> None:
        assert "count" in dataset.all_tags
        assert "join" in dataset.all_tags


# ---------------------------------------------------------------------------
# DatasetLoader
# ---------------------------------------------------------------------------


class TestDatasetLoader:
    def _write_yaml(self, path: Path, data: dict) -> None:
        with open(path, "w") as f:
            yaml.dump(data, f)

    def _minimal_yaml_data(self) -> dict:
        return {
            "version": "1.0",
            "created_date": "2026-01-01",
            "datasets": [
                {
                    "id": "t1",
                    "category": "aggregation",
                    "difficulty": "easy",
                    "description": "d",
                    "datasource": {"path": "p"},
                    "user_query": "q",
                    "expected_results": [{"n": 1}],
                    "expected_answer_summary": "s",
                }
            ],
        }

    def test_loads_valid_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ds.yaml"
            self._write_yaml(path, self._minimal_yaml_data())
            ds = DatasetLoader.load_from_yaml(path)
            assert ds.count == 1
            assert ds.datasets[0].id == "t1"

    def test_raises_on_missing_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            DatasetLoader.load_from_yaml("/nonexistent/path.yaml")

    def test_raises_on_invalid_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.yaml"
            path.write_text(": : invalid: yaml: {{{{")
            with pytest.raises(ValueError, match="Invalid YAML"):
                DatasetLoader.load_from_yaml(path)

    def test_raises_on_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.yaml"
            path.write_text("")
            with pytest.raises(ValueError, match="Empty dataset"):
                DatasetLoader.load_from_yaml(path)

    def test_load_from_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            self._write_yaml(d / "ds1.yaml", self._minimal_yaml_data())
            self._write_yaml(d / "ds2.yaml", self._minimal_yaml_data())
            result = DatasetLoader.load_from_directory(d)
            assert len(result) == 2

    def test_load_from_directory_missing(self) -> None:
        with pytest.raises(FileNotFoundError):
            DatasetLoader.load_from_directory("/nonexistent/dir")

    def test_save_and_reload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.yaml"
            original_data = self._minimal_yaml_data()
            ds = GoldenDataset(
                version=original_data["version"],
                created_date=original_data["created_date"],
                datasets=[GoldenTestCase(**original_data["datasets"][0])],
            )
            DatasetLoader.save_to_yaml(ds, path)
            reloaded = DatasetLoader.load_from_yaml(path)
            assert reloaded.count == 1
            assert reloaded.datasets[0].id == "t1"

    def test_loads_real_fixture(self) -> None:
        ds = DatasetLoader.load_from_yaml("fixtures/golden_datasets.yaml")
        assert ds.count > 0
        assert "aggregation" in ds.categories
