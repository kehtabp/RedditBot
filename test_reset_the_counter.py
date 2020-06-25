from datetime import datetime

import pytest

from reset_the_counter import respond_to_reset


def test_respond_to_reset():
    with pytest.raises(AttributeError):
        respond_to_reset("", "", datetime.now())
