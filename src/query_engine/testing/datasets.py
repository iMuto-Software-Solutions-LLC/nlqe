"""Golden dataset management and loading."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class GoldenTestCase(BaseModel):
    """A single test case in a golden dataset."""

    id: str
    category: str
    difficulty: str = Field(default="medium")
    description: str
    datasource: dict[str, str]
    user_query: str
    expected_sql: str | None = None
    expected_results: list[dict[str, Any]]
    expected_answer_summary: str
    acceptable_variance: float = Field(default=0.0, ge=0.0, le=1.0)
    priority: str = Field(default="medium")
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class GoldenDataset(BaseModel):
    """Collection of test cases for evaluation."""

    version: str
    created_date: str
    datasets: list[GoldenTestCase] = Field(default_factory=list)

    def get_by_category(self, category: str) -> list[GoldenTestCase]:
        """Get test cases by category.

        Args:
            category: Category name

        Returns:
            List of test cases in category
        """
        return [tc for tc in self.datasets if tc.category == category]

    def get_by_difficulty(self, difficulty: str) -> list[GoldenTestCase]:
        """Get test cases by difficulty.

        Args:
            difficulty: Difficulty level (easy, medium, hard)

        Returns:
            List of test cases with that difficulty
        """
        return [tc for tc in self.datasets if tc.difficulty == difficulty]

    def get_by_tag(self, tag: str) -> list[GoldenTestCase]:
        """Get test cases by tag.

        Args:
            tag: Tag name

        Returns:
            List of test cases with that tag
        """
        return [tc for tc in self.datasets if tag in tc.tags]

    def get_by_priority(self, priority: str) -> list[GoldenTestCase]:
        """Get test cases by priority.

        Args:
            priority: Priority level (high, medium, low)

        Returns:
            List of test cases with that priority
        """
        return [tc for tc in self.datasets if tc.priority == priority]

    @property
    def count(self) -> int:
        """Total number of test cases."""
        return len(self.datasets)

    @property
    def categories(self) -> set[str]:
        """All unique categories."""
        return {tc.category for tc in self.datasets}

    @property
    def difficulties(self) -> set[str]:
        """All unique difficulty levels."""
        return {tc.difficulty for tc in self.datasets}

    @property
    def all_tags(self) -> set[str]:
        """All unique tags."""
        tags = set()
        for tc in self.datasets:
            tags.update(tc.tags)
        return tags


class DatasetLoader:
    """Load golden datasets from YAML files."""

    @staticmethod
    def load_from_yaml(path: str | Path) -> GoldenDataset:
        """Load golden dataset from YAML file.

        Args:
            path: Path to YAML file

        Returns:
            Loaded GoldenDataset

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {path}")

        try:
            with open(path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML file: {e}") from e

        if not data:
            raise ValueError("Empty dataset file")

        # Parse using Pydantic
        try:
            dataset = GoldenDataset(
                version=data.get("version", "1.0"),
                created_date=data.get("created_date", ""),
                datasets=[GoldenTestCase(**test_case) for test_case in data.get("datasets", [])],
            )
        except Exception as e:
            raise ValueError(f"Invalid dataset structure: {e}") from e

        return dataset

    @staticmethod
    def load_from_directory(
        directory: str | Path, pattern: str = "*.yaml"
    ) -> dict[str, GoldenDataset]:
        """Load all golden datasets from a directory.

        Args:
            directory: Path to directory
            pattern: File pattern to match (default: *.yaml)

        Returns:
            Dictionary mapping filename to GoldenDataset

        Raises:
            FileNotFoundError: If directory doesn't exist
        """
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        datasets = {}
        for file_path in directory.glob(pattern):
            try:
                dataset = DatasetLoader.load_from_yaml(file_path)
                datasets[file_path.stem] = dataset
            except Exception as e:
                # Log but continue loading other files
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to load {file_path}: {e}")

        return datasets

    @staticmethod
    def save_to_yaml(dataset: GoldenDataset, path: str | Path) -> None:
        """Save golden dataset to YAML file.

        Args:
            dataset: Dataset to save
            path: Path to output file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": dataset.version,
            "created_date": dataset.created_date,
            "datasets": [test_case.model_dump() for test_case in dataset.datasets],
        }

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
