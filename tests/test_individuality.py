from server.individuality import (
    check_signed_individualities,
    divide_unsigned_and_signed,
    filter_by_traits,
)


def test_divide_unsigned_and_signed_splits_negative_traits():
    assert divide_unsigned_and_signed([300, -1002, 303]) == ([300, 303], [1002])


def test_check_signed_individualities_requires_positive_and_excludes_negative():
    traits = [300, 303, 2002]

    assert check_signed_individualities(traits, [300, -1002])
    assert not check_signed_individualities(traits, [301, -1002])
    assert not check_signed_individualities(traits, [300, -2002])


def test_filter_by_traits_uses_required_and_exclude_and_logic():
    traits = [300, 303, 2002]

    assert filter_by_traits(traits, [300, 303], [1002])
    assert not filter_by_traits(traits, [300, 304], None)
    assert not filter_by_traits(traits, [300], [2002])
