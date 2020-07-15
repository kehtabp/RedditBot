from datetime import datetime

import pytest

from reset_the_counter import is_real


def test_is_real():
    assert is_real("") == False
    assert is_real("don't") == False
    assert is_real("Reset the counter bois") == True
    assert is_real("Don't reset the couNter") == False
    assert is_real("Dont tell me what to do. Reset the counter") == True
    assert is_real("Do not tell me what to do! Reset the counter") == True
    assert is_real("Don't tell me what to do? reset the counter") == True
    assert is_real("Don't tell me what to do? Instead why don't you reset the counter") == False
    assert is_real("Don't you talk to me like that. But also. don't reset the counter") == False
    assert is_real("reset the counter, don't think") == True


