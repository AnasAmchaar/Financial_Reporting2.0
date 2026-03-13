import pytest
from pathlib import Path
import os
import sys
from run_etl import (
    setup_logging,
    find_table,
    total_tables,
    run_single,
    run_all,
    DATA_RAW_DIR,
    LOG_DIR,
    LOG_FILE,
    LOG_LEVEL,
    SOURCES,
)


def create_tmp_project_root(tmp_path: Path) -> Path:
    """
    Create a temporary project root directory.

    Args:
    tmp_path: The temporary path where the project root will be created.

    Returns:
    The created project root directory.
    """
    project_root = tmp_path / "tmp"
    project_root.mkdir(exist_ok=True)
    return project_root


def setup_tmp_settings(project_root: Path) -> Path:
    """
    Set up a temporary settings file.

    Args:
    project_root: The project root directory where the settings file will be created.

    Returns:
    The created settings file.
    """
    settings_file = project_root / "settings.py"
    with settings_file.open("w") as f:
        f.write("""
DATA_RAW_DIR = Path('data/raw')
LOG_DIR = Path('logs')
LOG_FILE = 'etl.log'
LOG_LEVEL = 'INFO'
SOURCES = {
    'file1.xlsx': {'table1': {}, 'table2': {}},
    'file2.xlsx': {'table3': {}},
}
""")
    return settings_file


def setup_tmp_data_dir(project_root: Path) -> Path:
    """
    Set up a temporary data directory.

    Args:
    project_root: The project root directory where the data directory will be created.

    Returns:
    The created data directory.
    """
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "raw").mkdir(exist_ok=True)
    return data_dir


def setup_tmp_log_dir(project_root: Path) -> Path:
    """
    Set up a temporary log directory.

    Args:
    project_root: The project root directory where the log directory will be created.

    Returns:
    The created log directory.
    """
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    return log_dir


def setup_env(project_root: Path) -> None:
    """
    Set up the environment.

    Args:
    project_root: The project root directory.
    """
    os.environ["PROJECT_ROOT"] = str(project_root)
    sys.path.insert(0, str(project_root))


def test_setup_logging(tmp_path: Path) -> None:
    """
    Test the setup_logging function.
    """
    project_root = create_tmp_project_root(tmp_path)
    setup_tmp_settings(project_root)
    setup_tmp_data_dir(project_root)
    setup_tmp_log_dir(project_root)
    setup_env(project_root)
    setup_logging()
    log_file = project_root / "logs" / "etl.log"
    assert log_file.exists()


def test_find_table() -> None:
    """
    Test the find_table function.
    """
    project_root = create_tmp_project_root(Path(__file__).parent)
    settings_file = setup_tmp_settings(project_root)
    data_dir = setup_tmp_data_dir(project_root)
    (data_dir / "raw" / "file1.xlsx").touch()
    result = find_table("table1")
    assert result == (data_dir / "raw" / "file1.xlsx", {"table1": {}})


def test_total_tables() -> None:
    """
    Test the total_tables function.
    """
    project_root = create_tmp_project_root(Path(__file__).parent)
    settings_file = setup_tmp_settings(project_root)
    data_dir = setup_tmp_data_dir(project_root)
    (data_dir / "raw" / "file1.xlsx").touch()
    (data_dir / "raw" / "file2.xlsx").touch()
    assert total_tables() == 4


def test_run_single(tmp_path: Path) -> None:
    """
    Test the run_single function.
    """
    project_root = create_tmp_project_root(tmp_path)
    setup_tmp_settings(project_root)
    setup_tmp_data_dir(project_root)
    setup_tmp_log_dir(project_root)
    setup_env(project_root)
    (data_dir / "raw" / "file1.xlsx").touch()
    run_single("table1")
    log_file = project_root / "logs" / "etl.log"
    with open(log_file, "r") as f:
        lines = f.readlines()
    assert any(line.startswith("ETL DONE") for line in lines)


def test_run_all(tmp_path: Path) -> None:
    """
    Test the run_all function.
    """
    project_root = create_tmp_project_root(tmp_path)
    setup_tmp_settings(project_root)
    setup_tmp_data_dir(project_root)
    setup_tmp_log_dir(project_root)
    setup_env(project_root)
    (data_dir / "raw" / "file1.xlsx").touch()
    (data_dir / "raw" / "file2.xlsx").touch()
    run_all()
    log_file = project_root / "logs" / "etl.log"
    with open(log_file, "r") as f:
        lines = f.readlines()
    assert any(line.startswith("ETL DONE") for line in lines)


def test_run_single_unknown_table(tmp_path: Path) -> None:
    """
    Test running with an unknown table name.
    """
    project_root = create_tmp_project_root(tmp_path)
    setup_tmp_settings(project_root)
    setup_tmp_data_dir(project_root)
    setup_tmp_log_dir(project_root)
    setup_env(project_root)
    (data_dir / "raw" / "file1.xlsx").touch()
    with pytest.raises(ValueError):
        run_single("table4")
    log_file = project_root / "logs" / "etl.log"
    with open(log_file, "r") as f:
        lines = f.readlines()
    assert any(line.startswith("Unknown table") for line in lines)
