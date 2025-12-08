# ********************************************************************
# YOU NEED TO COMMENT THIS IF YOU WILL USE THIS MODULE IN REAL TESTS
# ********************************************************************
import pytest

skip_message = "Due to not having a mongoDB to test on in the CI/CD, the live tests are disabled and set for manual testing only where you will have tp define your own actual mongoDB to test on"
#pytest.skip(skip_message, allow_module_level=True)
# ********************************************************************
# ********************************************************************
# ********************************************************************