from urllib.parse import parse_qs, urlsplit

from corporate_scraper.models import FetchOutcomeKind
from corporate_scraper.sources import IndeedAdapter, LinkedInAdapter


LINKEDIN = """
<ul><li><h3 class='base-search-card__title'>Développeur Python</h3>
<h4 class='base-search-card__subtitle'>Acme</h4><span class='job-search-card__location'>Rabat</span>
<a class='base-card__full-link' href='https://www.linkedin.com/jobs/view/123?tracking=remove'></a><time>2 days ago</time></li></ul>
"""
INDEED = """
<div class='job_seen_beacon'><h2 class='jobTitle'><a class='jcs-JobTitle' href='/viewjob?jk=abc&from=search'>Support IT</a></h2>
<span data-testid='company-name'>Acme</span><div data-testid='text-location'>Casablanca</div><span class='date'>Today</span></div>
"""


def test_search_urls_keep_query_location_and_offset_source_specific():
    linkedin = urlsplit(LinkedInAdapter().search_url("python", "Rabat", 25))
    indeed = urlsplit(IndeedAdapter().search_url("python", "Rabat", 10))
    assert parse_qs(linkedin.query) == {"keywords": ["python"], "location": ["Rabat"], "start": ["25"]}
    assert indeed.netloc == "ma.indeed.com"
    assert parse_qs(indeed.query) == {"q": ["python"], "l": ["Rabat"], "start": ["10"]}


def test_adapters_parse_canonical_ids_and_card_metadata():
    linkedin = LinkedInAdapter().parse_search(LINKEDIN)[0]
    indeed = IndeedAdapter().parse_search(INDEED)[0]
    assert (linkedin.source_key, linkedin.canonical_url, linkedin.company) == ("123", "https://www.linkedin.com/jobs/view/123", "Acme")
    assert (indeed.source_key, indeed.canonical_url, indeed.location) == ("abc", "https://ma.indeed.com/viewjob?jk=abc", "Casablanca")


def test_linkedin_slug_urls_keep_the_stable_numeric_job_id():
    offer = LinkedInAdapter().parse_search(LINKEDIN.replace("/jobs/view/123?tracking=remove", "/jobs/view/python-engineer-at-acme-987654321?tracking=remove"))[0]
    assert offer.source_key == "987654321"


def test_description_prefers_valid_structured_job_posting_data():
    html = """<script type='application/ld+json'>{"@type":"JobPosting","description":"<p>Python requis</p>"}</script>"""
    assert LinkedInAdapter().parse_description(html) == "Python requis"
    assert IndeedAdapter().parse_description("<div id='jobDescriptionText'>Support <b>Windows</b></div>") == "Support Windows"


def test_source_outcomes_distinguish_cards_empty_and_challenge():
    adapter = LinkedInAdapter()
    assert adapter.classify(LINKEDIN).kind == FetchOutcomeKind.SUCCESS
    assert adapter.classify("<p>Aucune offre disponible</p>").kind == FetchOutcomeKind.EMPTY
    assert adapter.classify("<p>Verify you are human</p>").kind == FetchOutcomeKind.BLOCKED
    assert adapter.classify("<p>Page changed</p>").kind == FetchOutcomeKind.LAYOUT_ERROR


def test_public_contact_candidates_only_use_explicit_profile_and_company_links():
    html = """<a href='https://www.linkedin.com/in/recruiter'>Poster</a>
    <script type='application/ld+json'>{"@type":"JobPosting","hiringOrganization":{"url":"https://acme.example/contact"}}</script>"""
    assert LinkedInAdapter().public_contact_pages(html, "https://www.linkedin.com/jobs/view/1") == (
        ("public_poster", "https://www.linkedin.com/in/recruiter"),
        ("company_site", "https://acme.example/contact"),
    )
