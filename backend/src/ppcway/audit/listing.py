"""What the Google listing says, and how it sits beside the ones nearby.

These checks used to be worked out in the browser, on the page that drew the
report. That had two costs. The findings never reached the stored report, so
the counts a visitor is shown left them out and the audit's own history could
not see them. And they ran past the one thing that decides whether a check is
sensible at all — what kind of business this is — so a law firm was told that
six businesses nearby are open twenty four hours.

Here they are findings like any other, with keys `audit.kinds` knows, so the
kind can drop the ones that were never that business's question.

Nothing here is read from anything stored. Google's terms let us keep the place
id and nothing else, so the listing is read again each time and credited.
"""

from __future__ import annotations

from ppcway.audit.places import Listing
from ppcway.audit.types import Finding

#: Below this many photographs a listing is losing taps it could have had.
ENOUGH_PHOTOS = 10

WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
}


def say(n: int) -> str:
    """Small numbers read better as words in the middle of a sentence."""
    return WORDS.get(n, str(n))


def _average(numbers: list[int]) -> int:
    return round(sum(numbers) / len(numbers)) if numbers else 0


def listing_findings(mine: Listing, rivals: list[Listing]) -> list[Finding]:
    """Their own listing, check by check."""
    found: list[Finding] = []
    trade = (mine.category or "businesses").lower()
    night_owls = [r for r in rivals if r.open_24h]
    photo_average = _average([r.photos for r in rivals])
    review_average = _average([r.reviews for r in rivals])

    if mine.reviews == 0:
        found.append(
            Finding(
                key="listing_reviews",
                title="No reviews yet",
                status="needs_you",
                summary=(
                    f"The {say(len(rivals))} nearest {trade} average {review_average}. "
                    "Reviews are the first thing people compare."
                    if rivals
                    else "Reviews are the first thing people compare, and the hardest to buy."
                ),
                fix="Ask every customer you finish a job for. The first ten are the hardest.",
            )
        )
    else:
        ahead = len([r for r in rivals if r.reviews < mine.reviews])
        found.append(
            Finding(
                key="listing_reviews",
                title=f"{mine.rating} out of 5, from {mine.reviews} reviews",
                status="good",
                summary=(
                    "That is the expensive thing to build, and you already have it."
                    if not rivals
                    else f"Every one of your {say(len(rivals))} competitors has more, and "
                    "reviews are the slowest thing to build."
                    if ahead == 0
                    else f"Ahead of {say(ahead)} of your {say(len(rivals))} competitors."
                ),
            )
        )

    if mine.photos == 0:
        found.append(
            Finding(
                key="listing_photos",
                title="No photos on your listing",
                status="needs_you",
                summary=(
                    f"Your competitors carry about {photo_average}. Photos cost nothing and "
                    "they move the Maps ranking."
                    if photo_average
                    else "Photos cost nothing and they move the Maps ranking."
                ),
                fix="Add ten, of the work and the people doing it.",
            )
        )
    elif mine.photos < ENOUGH_PHOTOS:
        found.append(
            Finding(
                key="listing_photos",
                title=f"{mine.photos} {'photo' if mine.photos == 1 else 'photos'} on your listing",
                status="needs_you",
                summary=(
                    f"Your competitors carry about {photo_average}."
                    if photo_average
                    else "Listings with more photos are picked more often."
                ),
                fix="Ten or more is where it stops making a difference.",
            )
        )
    else:
        found.append(
            Finding(
                key="listing_photos",
                title="Ten or more photos",
                status="good",
                summary="This is the part most listings get wrong, and you have it.",
            )
        )

    if not mine.hours_set:
        found.append(
            Finding(
                key="listing_hours",
                title="No opening hours on your listing",
                status="needs_you",
                summary=(
                    "Google hides businesses with no hours from some searches, and people "
                    "will not ring a business that might be shut."
                ),
                fix="Set your hours, and your holiday hours with them.",
            )
        )
    else:
        found.append(
            Finding(
                key="listing_hours",
                title="Open twenty four hours" if mine.open_24h else "Opening hours are set",
                status="good",
                summary=(
                    "The night calls can reach you, which is where the expensive jobs are."
                    if mine.open_24h
                    else "People can see when you answer, which is what Google wants before "
                    "it shows you."
                ),
            )
        )

    # The one that started all of this. It is a real finding for a business
    # people ring at night and nonsense for every other kind, so it is its own
    # check rather than a branch inside the hours one, and the kind decides
    # whether it is ever asked.
    if night_owls and mine.hours_set and not mine.open_24h:
        found.append(
            Finding(
                key="listing_24h",
                title="Your listing closes; theirs do not",
                status="needs_you",
                summary=(
                    f"{say(len(night_owls))} {'business' if len(night_owls) == 1 else 'businesses'} "
                    "nearby are open twenty four hours, so Google sends them the night calls."
                ),
                fix="Answer out of hours, or say on your listing when you do.",
            )
        )

    if not mine.website:
        found.append(
            Finding(
                key="listing_website",
                title="No website link on your listing",
                status="needs_you",
                summary=(
                    "Every person who looks you up on Maps is one tap from your site, and "
                    "that tap is missing."
                ),
                fix="Add your website address to the listing.",
            )
        )
    if not mine.phone:
        found.append(
            Finding(
                key="listing_phone",
                title="No phone number on your listing",
                status="needs_you",
                summary="The call button is the cheapest thing on Google, and yours is not there.",
                fix="Add the number you answer.",
            )
        )
    if mine.category:
        found.append(
            Finding(
                key="listing_category",
                title=f"{mine.category}, the category people search",
                status="good",
                summary="Half the listings we check sit under a category nobody types.",
            )
        )
    else:
        found.append(
            Finding(
                key="listing_category",
                title="No category on your listing",
                status="needs_you",
                summary=(
                    "Google matches searches to categories first. Without one, you are hard "
                    "to find at all."
                ),
                fix="Pick the category somebody would type to find you.",
            )
        )
    return found


def rival_findings(mine: Listing, rivals: list[Listing]) -> list[Finding]:
    """How they sit beside the same trade nearby. Maps only, never who advertises."""
    if not rivals:
        return []
    trade = (mine.category or "business").lower()
    better_reviews = len([r for r in rivals if r.reviews > mine.reviews])
    better_rating = len([r for r in rivals if (r.rating or 0) > (mine.rating or 0)])
    more_photos = len([r for r in rivals if r.photos > mine.photos])
    night_owls = len([r for r in rivals if r.open_24h])
    found: list[Finding] = []

    if better_reviews:
        one = better_reviews == 1
        found.append(
            Finding(
                key="rivals_reviews",
                title=(
                    f"{say(better_reviews).capitalize()} {trade}"
                    f"{' has' if one else 's have'} more reviews than you"
                ),
                status="needs_you",
                summary=(
                    "Reviews decide who gets rung first, and they are the slowest thing to build."
                ),
                fix="Ask the next ten customers, on the day you finish.",
            )
        )
    else:
        found.append(
            Finding(
                key="rivals_reviews",
                title="You have more reviews than every competitor nearby",
                status="good",
                summary="That is the expensive thing to build, and you already have it.",
            )
        )

    if night_owls and not mine.open_24h:
        one = night_owls == 1
        found.append(
            Finding(
                key="rivals_24h",
                title=f"{say(night_owls).capitalize()} of them {'is' if one else 'are'} open twenty four hours",
                status="needs_you",
                summary=(
                    "Nights and weekends are when the urgent jobs happen, and when nobody is "
                    "answering yours."
                ),
                fix="Answer out of hours, or say when you do.",
            )
        )

    if more_photos:
        one = more_photos == 1
        found.append(
            Finding(
                key="rivals_photos",
                title=f"{say(more_photos).capitalize()} of them {'has' if one else 'have'} more photos than you",
                status="needs_you",
                summary="Photos are free, and the listing with more of them gets the tap.",
                fix="Add ten of your own.",
            )
        )

    if better_rating == 0 and mine.rating is not None:
        found.append(
            Finding(
                key="rivals_rating",
                title=f"Yours is the best rating of the {say(len(rivals) + 1)}",
                status="good",
                summary=f"{mine.rating} out of 5, against everyone within fifteen kilometres.",
            )
        )
    return found
