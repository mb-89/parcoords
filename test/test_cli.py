from parcoords import parcoords as module


def test_main():
    assert module.main(["-v"]) == 0
    assert module.main(["-?"]) == 0
    assert module.main() == 0
