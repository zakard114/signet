from app.main import digits


def test_digits_keep_numbers_only():
    assert digits("4242-4242-4242-4242") == "4242424242424242"
    assert digits(" 4000 0000 0000 0002 ") == "4000000000000002"
