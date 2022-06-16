from pybudget import pybudget


def test_main():
    assert pybudget.main(["-v"]) == 0
    assert pybudget.main(["-?"]) == 0
    assert pybudget.main() == 0
