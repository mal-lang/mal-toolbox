import pytest
import os

@pytest.fixture(scope="module")
def setup_test_environment(request):
    """Runs once before all tests and temporarily sets the working directory to use the file tests."""
    old_dir = os.getcwd()  
    TEST_DIR = request.param
    os.chdir(TEST_DIR)  
    yield  # Run tests
    os.chdir(old_dir)  
