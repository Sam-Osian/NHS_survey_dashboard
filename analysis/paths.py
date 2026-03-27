from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
INPUTS_DIR = DATA_DIR / "inputs"
ARTIFACTS_DIR = DATA_DIR / "artifacts"
OUTPUTS_DIR = DATA_DIR / "outputs"


def year_input_dir(year: int) -> Path:
    return INPUTS_DIR / str(year)


def year_output_dir(year: int) -> Path:
    return OUTPUTS_DIR / str(year)


def year_artifact_dir(year: int) -> Path:
    return ARTIFACTS_DIR / str(year)


def squashed_path(year: int) -> Path:
    return year_artifact_dir(year) / "merged_survey.csv"


def canonical_output_path(year: int) -> Path:
    return year_output_dir(year) / f"comments_{year}.csv"


def baseline_manifest_path(year: int) -> Path:
    return REPO_ROOT / "analysis" / "baselines" / f"{year}_outputs.sha256"
