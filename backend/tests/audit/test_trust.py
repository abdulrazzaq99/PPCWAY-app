from ppcway.audit.trust import detect_trust

HTML = """
<html><head><script type="application/ld+json">
{"@context":"https://schema.org","@type":"Plumber","name":"Alpha","openingHoursSpecification":[],
 "aggregateRating":{"@type":"AggregateRating","ratingValue":"4.9","reviewCount":"212"}}
</script></head><body><a href="/privacy">Privacy policy</a></body></html>
"""


def test_structured_data_gives_hours_and_reviews() -> None:
    t = detect_trust([("https://x.ca/", HTML)], address="1 Main St", page_text="TSSA licence no. 0012345 Licensed and insured", links=["https://x.ca/privacy"])
    assert t.structured_local_business and t.hours
    assert t.reviews.startswith("4.9 stars from 212 reviews")
    assert t.licence.endswith("0012345") and t.insured and t.privacy_policy


def test_licensed_without_a_number_is_not_a_licence() -> None:
    t = detect_trust([], address="", page_text="Licensed emergency plumber", links=[])
    assert t.licence == "" and t.insured
    assert not t.hours and not t.reviews and not t.privacy_policy


def test_visible_hours_are_read_from_text() -> None:
    t = detect_trust([], address="", page_text="Open Mon to Fri 8am - 6pm", links=[])
    assert t.hours
