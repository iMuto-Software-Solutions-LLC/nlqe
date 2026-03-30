"""Command-line interface for evaluation framework."""

import argparse
import sys
from pathlib import Path

from query_engine.config import QueryEngineConfig
from query_engine.engine import QueryEngine
from query_engine.testing.datasets import DatasetLoader
from query_engine.testing.evaluator import Evaluator
from query_engine.testing.metrics import AnswerQualityEvaluator
from query_engine.testing.reporter import ReportGenerator
from query_engine.utils import get_logger

logger = get_logger(__name__)


def main() -> int:
    """Main CLI entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Query Engine Evaluation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full evaluation with all test cases
  python -m query_engine.testing.cli evaluate --config .env --dataset fixtures/golden_datasets.yaml

  # Evaluate only easy tests
  python -m query_engine.testing.cli evaluate --config .env --dataset fixtures/golden_datasets.yaml --difficulty easy

  # Evaluate specific category
  python -m query_engine.testing.cli evaluate --config .env --dataset fixtures/golden_datasets.yaml --category aggregation

  # Generate reports in all formats
  python -m query_engine.testing.cli evaluate --config .env --dataset fixtures/golden_datasets.yaml --output reports/ --report-formats json csv markdown
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Evaluate command
    eval_parser = subparsers.add_parser("evaluate", help="Run evaluation on golden dataset")
    eval_parser.add_argument(
        "--config",
        type=str,
        default=".env",
        help="Path to configuration file (default: .env)",
    )
    eval_parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="Path to golden dataset YAML file",
    )
    eval_parser.add_argument(
        "--datasource",
        type=str,
        default="fixtures/transactions.parquet",
        help="Path to datasource file for queries (default: fixtures/transactions.parquet)",
    )
    eval_parser.add_argument(
        "--difficulty",
        type=str,
        choices=["easy", "medium", "hard"],
        help="Filter tests by difficulty level",
    )
    eval_parser.add_argument(
        "--category",
        type=str,
        help="Filter tests by category",
    )
    eval_parser.add_argument(
        "--tag",
        type=str,
        help="Filter tests by tag",
    )
    eval_parser.add_argument(
        "--output",
        type=str,
        default="reports/",
        help="Output directory for reports (default: reports/)",
    )
    eval_parser.add_argument(
        "--report-formats",
        type=str,
        nargs="+",
        choices=["json", "csv", "markdown"],
        default=["json", "csv", "markdown"],
        help="Report formats to generate (default: json csv markdown)",
    )
    eval_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Run evaluate command
    if args.command == "evaluate":
        return _run_evaluate(args)

    return 1


def _run_evaluate(args: argparse.Namespace) -> int:
    """Run evaluation command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Load configuration
        logger.info("Loading configuration")
        config = QueryEngineConfig()

        # Load golden dataset
        logger.info(f"Loading golden dataset from {args.dataset}")
        dataset = DatasetLoader.load_from_yaml(args.dataset)

        # Filter dataset if requested
        test_cases = dataset.datasets
        total_original = len(test_cases)

        if args.difficulty:
            test_cases = [tc for tc in test_cases if tc.difficulty == args.difficulty]
            logger.info(f"Filtered to {len(test_cases)} tests with difficulty={args.difficulty}")

        if args.category:
            test_cases = [tc for tc in test_cases if tc.category == args.category]
            logger.info(f"Filtered to {len(test_cases)} tests with category={args.category}")

        if args.tag:
            test_cases = [tc for tc in test_cases if args.tag in tc.tags]
            logger.info(f"Filtered to {len(test_cases)} tests with tag={args.tag}")

        if not test_cases:
            logger.error("No test cases match the specified filters")
            return 1

        # Create filtered dataset
        filtered_dataset = dataset.__class__(
            version=dataset.version,
            created_date=dataset.created_date,
            datasets=test_cases,
        )

        logger.info(f"Running {len(test_cases)} test cases (filtered from {total_original})")

        # Initialize query engine
        logger.info(f"Initializing QueryEngine with datasource {args.datasource}")
        engine = QueryEngine(config)
        engine.load_datasource(args.datasource)

        # Create evaluator
        answer_quality_evaluator = AnswerQualityEvaluator(llm_client=engine.llm_client)
        evaluator = Evaluator(engine, filtered_dataset, answer_quality_evaluator=answer_quality_evaluator)

        # Run evaluation
        logger.info("Starting evaluation...")
        metrics = evaluator.evaluate_all()

        # Print summary
        print("\n" + "=" * 60)
        print("EVALUATION SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {metrics.total_tests}")
        print(f"Passed: {metrics.passed_tests}")
        print(f"Failed: {metrics.failed_tests}")
        print(f"Pass Rate: {metrics.pass_rate:.1%}")
        print(f"Accuracy: {metrics.accuracy:.1%}")
        print(f"Execution Time: {metrics.execution_time_ms:.2f}ms")
        print(f"\nResult Correctness: {metrics.avg_result_correctness:.1%}")
        print(f"Answer Quality: {metrics.avg_answer_quality:.1%}")
        print(f"Avg Confidence: {metrics.avg_confidence_score:.1%}")
        print(f"Calibration Error: {metrics.confidence_calibration_error:.4f}")
        print("=" * 60)

        # Print by category
        if metrics.by_category:
            print("\nBY CATEGORY:")
            for category in sorted(metrics.by_category.keys()):
                cat_data = metrics.by_category[category]
                print(
                    f"  {category}: {cat_data['passed']}/{cat_data['total']} "
                    f"({cat_data['passed'] / cat_data['total'] * 100:.0f}%)"
                )

        # Print by difficulty
        if metrics.by_difficulty:
            print("\nBY DIFFICULTY:")
            for difficulty in ["easy", "medium", "hard"]:
                if difficulty in metrics.by_difficulty:
                    diff_data = metrics.by_difficulty[difficulty]
                    print(
                        f"  {difficulty}: {diff_data['passed']}/{diff_data['total']} "
                        f"({diff_data['passed'] / diff_data['total'] * 100:.0f}%)"
                    )

        # Generate reports
        output_dir = Path(args.output)
        logger.info(f"Generating reports to {output_dir}")

        for report_format in args.report_formats:
            if report_format == "json":
                ReportGenerator.generate_json_report(
                    evaluator, metrics, output_dir / "evaluation_report.json"
                )
            elif report_format == "csv":
                ReportGenerator.generate_csv_report(evaluator, output_dir / "evaluation_report.csv")
            elif report_format == "markdown":
                ReportGenerator.generate_markdown_report(
                    evaluator, metrics, output_dir / "evaluation_report.md"
                )

        print(f"\nReports written to: {output_dir}")

        # Print failed tests if any
        failed = evaluator.get_failed_tests()
        if failed:
            print(f"\nFailed Tests ({len(failed)}):")
            for result in failed[:10]:  # Show first 10 failed tests
                print(f"  - {result.test_case.id}: {result.test_case.description}")
            if len(failed) > 10:
                print(f"  ... and {len(failed) - 10} more")

        engine.close()
        logger.info("Evaluation complete")

        return 0

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Value error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Error during evaluation: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
