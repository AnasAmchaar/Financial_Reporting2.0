import pytest
from pathlib import Path
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

# Create a temporary directory to use as the project root
tmp_dir = Path(__file__).parent / "tmp"
tmp_dir.mkdir(exist_ok=True)

# Set up a temporary settings file
settings_file = tmp_dir / "settings.py"
with settings_file.open("w") as f:
    f.write(
        """
DATA_RAW_DIR = Path('data/raw')
LOG_DIR = Path('logs')
LOG_FILE = 'etl.log'
LOG_LEVEL = 'INFO'
SOURCES = {
    'file1.xlsx': {'table1': {}, 'table2': {}},
    'file2.xlsx': {'table3': {}},
}
"""
    )

# Set up a temporary data directory
data_dir = tmp_dir / "data"
data_dir.mkdir(exist_ok=True)
(data_dir / "raw").mkdir(exist_ok=True)

# Create a temporary log directory
log_dir = tmp_dir / "logs"
log_dir.mkdir(exist_ok=True)

# Set up a temporary log file
log_file = log_dir / "etl.log"

# Set up the environment
os.environ["PROJECT_ROOT"] = str(tmp_dir)
sys.path.insert(0, str(tmp_dir))

# Test setup_logging
def test_setup_logging(tmp_path):
    # Create a temporary log file
    log_file = tmp_path / "etl.log"

    # Set up logging
    setup_logging()

    # Check that the log file was created
    assert log_file.exists()

    # Check that the log level is correct
    with open(log_file, "r") as f:
        lines = f.readlines()
    assert any(line.startswith("INFO") for line in lines)

# Test find_table
def test_find_table():
    # Set up the settings file
    with settings_file.open("w") as f:
        f.write(
            """
DATA_RAW_DIR = Path('data/raw')
LOG_DIR = Path('logs')
LOG_FILE = 'etl.log'
LOG_LEVEL = 'INFO'
SOURCES = {
    'file1.xlsx': {'table1': {}, 'table2': {}},
    'file2.xlsx': {'table3': {}},
}
"""
        )

    # Test finding a table that exists
    result = find_table("table1")
    assert result == (data_dir / "raw" / "file1.xlsx", {"table1": {}})

    # Test finding a table that doesn't exist
    result = find_table("table4")
    assert result is None

# Test total_tables
def test_total_tables():
    # Set up the settings file
    with settings_file.open("w") as f:
        f.write(
            """
DATA_RAW_DIR = Path('data/raw')
LOG_DIR = Path('logs')
LOG_FILE = 'etl.log'
LOG_LEVEL = 'INFO'
SOURCES = {
    'file1.xlsx': {'table1': {}, 'table2': {}},
    'file2.xlsx': {'table3': {}},
}
"""
        )

    # Test counting the total number of tables
    assert total_tables() == 4

# Test run_single
def test_run_single(tmp_path):
    # Create a temporary log file
    log_file = tmp_path / "etl.log"

    # Set up the settings file
    with settings_file.open("w") as f:
        f.write(
            """
DATA_RAW_DIR = Path('data/raw')
LOG_DIR = Path('logs')
LOG_FILE = 'etl.log'
LOG_LEVEL = 'INFO'
SOURCES = {
    'file1.xlsx': {'table1': {}},
}
"""
        )

    # Set up the data file
    (data_dir / "raw" / "file1.xlsx").touch()

    # Run the ETL pipeline
    run_single("table1")

    # Check that the log file was updated
    with open(log_file, "r") as f:
        lines = f.readlines()
    assert any(line.startswith("ETL DONE") for line in lines)

# Test run_all
def test_run_all(tmp_path):
    # Create a temporary log file
    log_file = tmp_path / "etl.log"

    # Set up the settings file
    with settings_file.open("w") as f:
        f.write(
            """
DATA_RAW_DIR = Path('data/raw')
LOG_DIR = Path('logs')
LOG_FILE = 'etl.log'
LOG_LEVEL = 'INFO'
SOURCES = {
    'file1.xlsx': {'table1': {}},
    'file2.xlsx': {'table2': {}},
}
"""
        )

    # Set up the data files
    (data_dir / "raw" / "file1.xlsx").touch()
    (data_dir / "raw" / "file2.xlsx").touch()

    # Run the ETL pipeline
    run_all()

    # Check that the log file was updated
    with open(log_file, "r") as f:
        lines = f.readlines()
    assert any(line.startswith("ETL DONE") for line in lines)

# Test running with an unknown table name
def test_run_single_unknown_table(tmp_path):
    # Create a temporary log file
    log_file = tmp_path / "etl.log"

    # Set up the settings file
    with settings_file.open("w") as f:
        f.write(
            """
DATA_RAW_DIR = Path('data/raw')
LOG_DIR = Path('logs')
LOG_FILE = 'etl.log'
LOG_LEVEL = 'INFO'
SOURCES = {
    'file1.xlsx': {'table1': {}},
}
"""
        )

    # Set up the data file
    (data_dir / "raw" / "file1.xlsx").touch()

    # Run the ETL pipeline with an unknown table name
    with pytest.raises(ValueError):
        run_single("table4")

    # Check that the log file was updated
    with open(log_file, "r") as f:
        lines = f.readlines()
    assert any(line.startswith("Unknown table") for line in lines)