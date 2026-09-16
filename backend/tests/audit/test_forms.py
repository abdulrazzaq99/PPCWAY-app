from ppcway.audit.forms import detect_forms

CONTACT = """
<html><body>
<form action="/send" method="post" class="wpforms-form">
  <input name="name" type="text"><input name="phone" type="tel"><textarea name="message"></textarea>
  <button type="submit">Send</button>
</form>
</body></html>
"""
SEARCH = '<form role="search"><input type="search" name="s"><input type="submit"></form>'


def test_a_contact_form_is_found_and_its_provider_named() -> None:
    f = detect_forms([("https://x.ca/contact", CONTACT)], ["https://x.ca/", "https://x.ca/thank-you"])
    assert f.contact_form and f.provider == "WPForms" and f.on_page == "https://x.ca/contact"
    assert f.thank_you_url == "https://x.ca/thank-you"
    assert f.has_action


def test_a_search_box_is_not_a_contact_form() -> None:
    f = detect_forms([("https://x.ca/", SEARCH)], [])
    assert f.forms_found == 1 and not f.contact_form


def test_no_thank_you_page_means_none() -> None:
    f = detect_forms([("https://x.ca/contact", CONTACT)], ["https://x.ca/about"])
    assert f.contact_form and f.thank_you_url is None
