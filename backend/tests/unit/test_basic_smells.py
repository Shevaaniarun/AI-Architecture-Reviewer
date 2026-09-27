from app.analyzer.detectors.basic_smells import SmellThresholds, detect_smells
from app.analyzer.graph import build_dependency_graph
from app.analyzer.metrics import calculate_metrics
from app.analyzer.parser import ParsedPythonFile, PythonAstParser


def parse(filename: str, source: str) -> ParsedPythonFile:
    import ast

    from app.analyzer.parser.python_parser import _StructureCollector

    result = ParsedPythonFile(filename=filename, loc=len(source.splitlines()))
    _StructureCollector(result).visit(ast.parse(source, filename=filename))
    return result


def test_detects_exactly_the_five_initial_smell_types():
    files = [
        parse(
            "src/hub.py",
            """import src.left
import src.right

class Large:
    def long(self, one, two, three):
        if one:
            first()
            second()
            third()

    def another(self):
        return None
""",
        ),
        parse("src/left.py", "import src.hub\n"),
        parse("src/right.py", "VALUE = 1\n"),
    ]
    metrics = calculate_metrics(files)
    graph = build_dependency_graph(files)
    findings = detect_smells(
        files,
        metrics,
        graph,
        SmellThresholds(
            long_method_lines=3,
            large_class_methods=1,
            long_parameter_count=2,
            high_fan_out=1,
        ),
    )

    assert {finding.type for finding in findings} == {
        "Long Method",
        "Large Class",
        "Long Parameter List",
        "Excessive Coupling",
        "Circular Dependency",
    }
    assert len(findings) == 5

    long_method = next(finding for finding in findings if finding.type == "Long Method")
    assert long_method.file == "src/hub.py"
    assert long_method.line == 5
    assert long_method.evidence["lines"] == 5
    assert long_method.evidence["complexity"] == 2

    large_class = next(finding for finding in findings if finding.type == "Large Class")
    assert large_class.evidence["method_count"] == 2

    long_parameters = next(finding for finding in findings if finding.type == "Long Parameter List")
    assert long_parameters.evidence["parameter_count"] == 3
    assert long_parameters.evidence["parameters"] == ["one", "two", "three"]

    coupling = next(finding for finding in findings if finding.type == "Excessive Coupling")
    assert coupling.evidence["fan_out"] == 2

    cycle = next(finding for finding in findings if finding.type == "Circular Dependency")
    assert cycle.evidence["files"] == ["src/hub.py", "src/left.py"]


def test_default_thresholds_do_not_report_small_clean_function():
    files = [parse("clean.py", "def add(a, b):\n    return a + b\n")]
    findings = detect_smells(files, calculate_metrics(files), build_dependency_graph(files))

    assert findings == []


def test_can_create_smell_thresholds_from_application_settings():
    from app.core.config import Settings
    from app.analyzer.detectors.basic_smells import thresholds_from_settings

    settings = Settings(
        _env_file=None,
        long_method_lines=12,
        large_class_methods=7,
        long_parameter_count=4,
        high_fan_out=6,
    )

    assert thresholds_from_settings(settings) == SmellThresholds(12, 7, 4, 6)
