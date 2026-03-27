import sys
from unittest.mock import MagicMock

import pytest

from query_engine.testing.cli import main
from query_engine.testing.metrics import EvaluationMetrics


@pytest.fixture
def mock_metrics():
    return EvaluationMetrics(
        total_tests=2,
        passed_tests=2,
        failed_tests=0,
        accuracy=1.0,
        avg_result_correctness=1.0,
        avg_answer_quality=1.0,
        avg_confidence_score=0.9,
        confidence_calibration_error=0.0,
        execution_time_ms=10.0,
        by_category={},
        by_difficulty={},
    )


@pytest.fixture
def mock_modules(mock_metrics):
    with pytest.MonkeyPatch.context() as m:
        # Mock components to avoid actually executing LLM and datasets
        mock_config = MagicMock()
        mock_evaluator_cls = MagicMock()
        mock_evaluator_inst = MagicMock()
        mock_evaluator_cls.return_value = mock_evaluator_inst

        mock_evaluator_inst.evaluate_all.return_value = mock_metrics

        class MockTestCase:
            def __init__(self, cat, diff, tgs):
                self.category = cat
                self.difficulty = diff
                self.tags = tgs

        tc_cat1 = MockTestCase("cat1", "easy", ["tag1"])
        tc_hard = MockTestCase("cat2", "hard", ["tag2"])

        mock_dataset = MagicMock()
        mock_dataset.datasets = [tc_cat1, tc_hard]
        mock_dataset.version = "1.0"
        mock_dataset.created_date = "2026"

        mock_loader = MagicMock()
        mock_loader.load_from_yaml.return_value = mock_dataset

        m.setattr("query_engine.testing.cli.QueryEngineConfig", mock_config)
        m.setattr("query_engine.testing.cli.Evaluator", mock_evaluator_cls)
        m.setattr("query_engine.testing.cli.ReportGenerator.generate_markdown_report", MagicMock())
        m.setattr("query_engine.testing.cli.ReportGenerator.generate_json_report", MagicMock())
        m.setattr("query_engine.testing.cli.ReportGenerator.generate_csv_report", MagicMock())
        m.setattr("query_engine.testing.cli.DatasetLoader", mock_loader)
        m.setattr("query_engine.testing.cli.QueryEngine", MagicMock())

        yield {"evaluator": mock_evaluator_inst, "config": mock_config}


def test_cli_help(capsys):
    with pytest.MonkeyPatch.context() as m:
        m.setattr(sys, "argv", ["cli.py", "--help"])
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0
        out, _err = capsys.readouterr()
        assert "usage:" in out.lower()


def test_evaluate_command_help(capsys):
    with pytest.MonkeyPatch.context() as m:
        m.setattr(sys, "argv", ["cli.py", "evaluate", "--help"])
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0
        out, _err = capsys.readouterr()
        assert "usage:" in out.lower()


def test_evaluate_command_basic(mock_modules, tmp_path):
    dataset_path = tmp_path / "dataset.yaml"
    dataset_path.write_text("dummy yaml")

    with pytest.MonkeyPatch.context() as m:
        m.setenv("OPENAI_API_KEY", "test-key")
        m.setattr(
            sys,
            "argv",
            ["cli.py", "evaluate", "--dataset", str(dataset_path), "--datasource", "fixtures"],
        )

        result = main()
        assert result == 0
        mock_modules["evaluator"].evaluate_all.assert_called()


def test_evaluate_command_missing_api_key(mock_modules, tmp_path):
    dataset_path = tmp_path / "dataset.yaml"
    dataset_path.write_text("dummy yaml")

    with pytest.MonkeyPatch.context() as m:
        m.delenv("OPENAI_API_KEY", raising=False)
        m.setattr(
            sys,
            "argv",
            ["cli.py", "evaluate", "--dataset", str(dataset_path), "--datasource", "fixtures"],
        )

        # Simulate config validation error
        mock_modules["config"].side_effect = ValueError("Missing API key")

        result = main()
        assert result != 0


def test_evaluate_command_filters(mock_modules, tmp_path):
    dataset_path = tmp_path / "dataset.yaml"
    dataset_path.write_text("dummy yaml")

    with pytest.MonkeyPatch.context() as m:
        m.setenv("OPENAI_API_KEY", "test-key")
        m.setattr(
            sys,
            "argv",
            [
                "cli.py",
                "evaluate",
                "--dataset",
                str(dataset_path),
                "--datasource",
                "fixtures",
                "--category",
                "cat1",
                "--difficulty",
                "easy",
            ],
        )

        result = main()
        assert result == 0
        mock_modules["evaluator"].evaluate_all.assert_called()


def test_evaluate_with_reports(mock_modules, tmp_path):
    dataset_path = tmp_path / "dataset.yaml"
    dataset_path.write_text("dummy yaml")

    output_dir = tmp_path / "reports"
    output_dir.mkdir()

    with pytest.MonkeyPatch.context() as m:
        m.setenv("OPENAI_API_KEY", "test-key")
        m.setattr(
            sys,
            "argv",
            [
                "cli.py",
                "evaluate",
                "--dataset",
                str(dataset_path),
                "--datasource",
                "fixtures",
                "--output",
                str(output_dir),
                "--report-formats",
                "json",
            ],
        )

        result = main()
        assert result == 0
