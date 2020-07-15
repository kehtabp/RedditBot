from datetime import datetime

import pytest

from reset_the_counter import is_real


def test_is_real():
    assert is_real("Reset the counter bois") == True
    assert is_real("Don't reset the couNter") == False


