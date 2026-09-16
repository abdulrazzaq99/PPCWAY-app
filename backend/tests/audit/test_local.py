from ppcway.audit.local import detect_local


def test_the_main_number_and_its_region_are_read() -> None:
    loc = detect_local(["Call (905) 555-0142 today. Or 905.555.0142."], address="1 Main St, Oakville", maps_embed=True, tel_links=["tel:+19055550142"])
    assert loc.main_number == "(905) 555-0142"
    assert loc.area_code == "905" and "Toronto suburbs" in loc.region
    assert not loc.toll_free and not loc.inconsistent and loc.maps_embed


def test_toll_free_and_service_area_are_noticed() -> None:
    loc = detect_local(["1-866-555-0100. Proudly serving Oakville, Burlington and Milton."], address="", maps_embed=False, tel_links=[])
    assert loc.toll_free and loc.service_area.startswith("Proudly serving Oakville")


def test_no_number_is_empty_not_wrong() -> None:
    loc = detect_local(["We fix things."], address="", maps_embed=False, tel_links=[])
    assert loc.main_number == "" and loc.numbers == []
