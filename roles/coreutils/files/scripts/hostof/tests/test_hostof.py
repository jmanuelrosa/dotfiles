"""`hostof` reports which service and region host a site.

The parsing is where the subtlety is, so most of these load the tool as a module and
call its functions directly. An extensionless executable cannot be imported by name,
so it is loaded through a SourceFileLoader rather than by adding a package.

Nothing here touches the network. The cases that need a provider prefix file write a
small fixture into a redirected cache directory, which is also what proves the cache
is consulted before anything is fetched.
"""

import http.client
import importlib.machinery
import importlib.util
import json
import subprocess
import sys
import urllib.error

import pytest

from dotkit.testing import CORE_SCRIPTS_DIR

TOOL = CORE_SCRIPTS_DIR / "hostof" / "hostof"

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_UNREACHABLE = 2
EXIT_REFUSED = 3


def load():
    """The tool as a module, so its pure functions can be called directly."""
    loader = importlib.machinery.SourceFileLoader("hostof_tool", str(TOOL))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tool():
    return load()


@pytest.fixture
def cli(tmp_path):
    """Run the tool as a subprocess with cache and authorization redirected."""

    def run(*argv, authorized=None):
        env = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
            "HOSTOF_CACHE": str(tmp_path / "cache"),
            "HOSTOF_AUTHORIZED": str(tmp_path / "authorized.json"),
            "NO_COLOR": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        if authorized is not None:
            (tmp_path / "authorized.json").write_text(json.dumps(authorized))
        return subprocess.run(
            [sys.executable, str(TOOL), *argv], capture_output=True, text=True, env=env, timeout=60
        )

    return run


# The three shapes observed in the wild. The two-field form is the one a naive
# "second field is the origin region" rule gets wrong: it would return the request id.
VERCEL_IDS = [
    ("fra1::iad1::7dqhk-1785945037638-ccdebf07f3d5", "fra1", "iad1"),
    ("fra1::2cshq-1785945189096-2ccdc2d6b9a4", "fra1", None),
    (
        "fra1:fra1:sfo1:sfo1:sfo1:fra1:sfo1:sfo1:sfo1::sfo1::j5mk6-1785945189600-a73a445f9d79",
        "fra1",
        "sfo1",
    ),
]


@pytest.mark.parametrize(("value", "edge", "compute"), VERCEL_IDS)
def test_vercel_id_yields_edge_and_compute_region(tool, value, edge, compute):
    assert tool.vercel_regions(value) == (edge, compute)


def test_a_vercel_id_with_no_separator_yields_nothing(tool):
    """Rather than a fabricated region, which is the failure mode port.fish avoids."""
    assert tool.vercel_regions("garbage") == (None, None)


def test_netlify_region_comes_from_server_timing(tool):
    headers = {"server-timing": 'dc;desc="aws-fra", cg;desc="global-production"'}
    assert tool.regions_from_headers(headers)["edge"][0] == "aws-fra"


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({"cf-ray": "a266f5725a420f76-MXP"}, "MXP"),
        ({"x-amz-cf-pop": "AMS1-P1"}, "AMS"),
        ({"fly-request-id": "01KZ99XZGKAK47202SDM1ZMMVY-fra"}, "fra"),
        ({"x-github-edge-region": "fra"}, "fra"),
        ({"x-served-by": "cache-sjc10025-SJC, cache-bgy-lime1210038-BGY"}, "BGY"),
    ],
)
def test_edge_region_from_each_vendor_header(tool, headers, expected):
    assert tool.regions_from_headers(headers)["edge"][0] == expected


def test_a_response_naming_two_vendors_reports_both(tool):
    """The linear.app case, and the reason detection is not first-match-wins.

    One response carries `server: cloudflare` and `via: 1.1 google` together, so a
    loop that stopped at the first hit would report the edge and hide the origin.
    """
    vendors = dict(tool.vendors_from_headers({"server": "cloudflare", "via": "1.1 google"}))
    assert "Cloudflare" in vendors
    assert "Google Cloud" in vendors


def test_render_origin_is_seen_behind_a_cloudflare_edge(tool):
    vendors = dict(
        tool.vendors_from_headers({"server": "cloudflare", "x-render-origin-server": "Render"})
    )
    assert {"Cloudflare", "Render"} <= set(vendors)


def test_every_vendor_is_reported_once(tool):
    """CloudFront sets several headers; the report should not list it three times."""
    vendors = tool.vendors_from_headers(
        {"x-amz-cf-id": "abc", "x-amz-cf-pop": "AMS1-P1", "via": "1.1 x.cloudfront.net (CloudFront)"}
    )
    names = [vendor for vendor, _ in vendors]
    assert names.count("AWS CloudFront") == 1


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("my-lb-123456.eu-west-1.elb.amazonaws.com", "eu-west-1"),
        ("b123abcde4.execute-api.us-west-2.amazonaws.com", "us-west-2"),
        ("assets.s3.eu-central-1.amazonaws.com", "eu-central-1"),
        ("svc-123456789.europe-west1.run.app", "europe-west1"),
        ("www.example.com", None),
    ],
)
def test_region_encoded_in_the_hostname(tool, host, expected):
    assert tool.region_from_host(host) == expected


@pytest.mark.parametrize(
    ("hosts", "vendor"),
    [
        (["x.netlifyglobalcdn.com"], "Netlify"),
        (["cname.vercel-dns.com"], "Vercel"),
        (["e6858.dsce9.akamaiedge.net"], "Akamai"),
        (["reddit.map.fastly.net"], "Fastly"),
        (["dr49lng3n1n2s.cloudfront.net"], "AWS CloudFront"),
        (["shops.myshopify.com"], "Shopify"),
        (["nothing.example.org"], None),
    ],
)
def test_cname_suffix_names_the_vendor(tool, hosts, vendor):
    """The durable fingerprint, because the vendor owns the suffix."""
    assert tool.vendor_from_hosts(hosts)[0] == vendor


@pytest.mark.parametrize(
    ("target", "host"),
    [
        ("example.com", "example.com"),
        ("https://example.com/a/b", "example.com"),
        ("http://example.com:8080/", "example.com"),
        ("", None),
    ],
)
def test_normalise_accepts_a_url_or_a_bare_host(tool, target, host):
    assert tool.normalise(target)[0] == host


@pytest.mark.parametrize(
    ("layer", "expected"),
    [
        ({"vendor": "Vercel", "region": "iad1"}, "Vercel (iad1)"),
        ({"vendor": "Vercel"}, "Vercel"),
        ({"region": "iad1"}, "iad1"),
        ({}, "unknown"),
    ],
)
def test_describe_never_pads_a_missing_vendor(tool, layer, expected):
    """A region with no vendor prints alone rather than as "unknown (iad1)"."""
    assert tool.describe(layer) == expected


def write_aws_cache(tool, tmp_path, prefixes):
    cache = tmp_path / "cache"
    cache.mkdir(exist_ok=True)
    (cache / "aws-ip-ranges.json").write_text(json.dumps({"prefixes": prefixes}))
    return cache


def test_a_global_region_is_reported_as_undeterminable(tool, tmp_path, monkeypatch):
    """The finding that decides what the IP layer may claim.

    Over half of CloudFront prefixes and a third of Global Accelerator prefixes carry
    `GLOBAL`, which is not a region. Printing it as one would be a fabricated answer,
    so the field stays empty and a note explains why.
    """
    monkeypatch.setattr(
        tool, "CACHE_DIR", write_aws_cache(tool, tmp_path, [
            {"ip_prefix": "15.197.128.0/17", "service": "GLOBALACCELERATOR", "region": "GLOBAL"},
        ])
    )
    result = tool.attribute_ip("15.197.167.90")
    assert result["service"] == "GLOBALACCELERATOR"
    assert result["region"] is None
    # The raw value, with the phrasing left to render so the payload stays factual.
    assert result["region_note"] == "GLOBAL"


def test_a_real_region_is_reported(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(
        tool, "CACHE_DIR", write_aws_cache(tool, tmp_path, [
            {"ip_prefix": "3.4.12.0/24", "service": "EC2", "region": "eu-west-1"},
        ])
    )
    result = tool.attribute_ip("3.4.12.4")
    assert result["region"] == "eu-west-1"
    assert result["region_note"] is None


def test_the_longest_prefix_wins(tool, tmp_path, monkeypatch):
    """One address sits in several prefixes at once.

    AWS lists 15.197.128.0/17 as both AMAZON and GLOBALACCELERATOR, so the specific
    entry has to beat the general one or the service name is a coin toss.
    """
    monkeypatch.setattr(
        tool, "CACHE_DIR", write_aws_cache(tool, tmp_path, [
            {"ip_prefix": "15.0.0.0/8", "service": "AMAZON", "region": "GLOBAL"},
            {"ip_prefix": "15.197.167.0/24", "service": "GLOBALACCELERATOR", "region": "GLOBAL"},
        ])
    )
    assert tool.attribute_ip("15.197.167.90")["prefix"] == "15.197.167.0/24"


def test_a_specific_service_beats_the_umbrella_at_the_same_prefix_length(tool, tmp_path, monkeypatch):
    """The bug a live run against www.netlify.com surfaced.

    AWS lists 3.33.128.0/17 twice, as AMAZON and as GLOBALACCELERATOR, at the *same*
    length and with AMAZON first in the file. Longest-prefix match cannot break that
    tie, so the report said AMAZON and lost the one fact that identifies the address
    as an anycast edge rather than an origin.
    """
    monkeypatch.setattr(
        tool, "CACHE_DIR", write_aws_cache(tool, tmp_path, [
            {"ip_prefix": "3.33.128.0/17", "service": "AMAZON", "region": "GLOBAL"},
            {"ip_prefix": "3.33.128.0/17", "service": "GLOBALACCELERATOR", "region": "GLOBAL"},
        ])
    )
    assert tool.attribute_ip("3.33.186.135")["service"] == "GLOBALACCELERATOR"


def test_the_umbrella_still_answers_when_it_is_the_only_match(tool, tmp_path, monkeypatch):
    """Preferring the specific service must not mean discarding the only one there is."""
    monkeypatch.setattr(
        tool, "CACHE_DIR", write_aws_cache(tool, tmp_path, [
            {"ip_prefix": "52.0.0.0/8", "service": "AMAZON", "region": "us-east-1"},
        ])
    )
    result = tool.attribute_ip("52.1.2.3")
    assert result["service"] == "AMAZON"
    assert result["region"] == "us-east-1"


def test_an_unmatched_address_yields_nothing(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(
        tool, "CACHE_DIR", write_aws_cache(tool, tmp_path, [
            {"ip_prefix": "3.4.12.0/24", "service": "EC2", "region": "eu-west-1"},
        ])
    )
    assert tool.attribute_ip("192.0.2.1") is None
    assert tool.attribute_ip("not-an-ip") is None


def test_a_truncated_error_body_does_not_crash_the_run(tool, monkeypatch):
    """The crash a live run against docs.netlify.com found.

    A 404 whose body is a truncated chunked response raises IncompleteRead from
    exc.read(). That is an http.client.HTTPException rather than an OSError, and
    because it is raised inside an except clause it escapes the whole try instead of
    reaching the broad handler, so the tool exited 1 with a traceback.
    """

    class Truncated(urllib.error.HTTPError):
        def __init__(self):
            super().__init__("https://example.com/", 404, "Not Found", {}, None)

        def read(self, *_args):
            raise http.client.IncompleteRead(b"partial")

    def boom(*_args, **_kwargs):
        raise Truncated()

    monkeypatch.setattr(tool.urllib.request, "urlopen", boom)
    status, _, body, error = tool.http_get("https://example.com/", tool.Budget(interval=0))
    assert status == 404
    assert body == ""
    assert error is None


def test_a_rate_limited_response_is_a_final_answer(tool, monkeypatch):
    """429 stops rather than retrying, and says so."""

    class Limited(urllib.error.HTTPError):
        def __init__(self):
            super().__init__(
                "https://example.com/", 429, "Too Many", {"Retry-After": "120"}, None
            )

        def read(self, *_args):
            return b""

    monkeypatch.setattr(tool.urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(Limited()))
    _, _, _, error = tool.http_get("https://example.com/", tool.Budget(interval=0))
    assert "120" in error
    assert "stopping" in error


def test_an_unwritable_cache_degrades_instead_of_crashing(tool, tmp_path, monkeypatch):
    """The cache is an optimisation and must never be able to end the run.

    A sandbox or a read-only HOME makes the directory uncreatable, which used to
    escape as a PermissionError traceback halfway through an otherwise good report.
    """
    blocked = tmp_path / "blocked"
    blocked.write_text("not a directory")
    monkeypatch.setattr(tool, "CACHE_DIR", blocked / "cache")
    assert tool.attribute_ip("3.4.12.4") is None


@pytest.mark.parametrize(
    ("text", "kind", "value"),
    [
        (
            'dsn:"https://abc123@o1.ingest.us.sentry.io/4511259601338368"',
            "Sentry org and project",
            "1/4511259601338368",
        ),
        ('{"projectId":"my-app-1234"}', "Firebase project", "my-app-1234"),
        ("https://abcdefghijklmnopqrst.supabase.co", "Supabase project ref", "abcdefghijklmnopqrst"),
        ("/vc-ap-vercel-marketing/_next/static/x.js", "Vercel project", "vercel-marketing"),
        ("gtag('config','G-D66RRD8GF2')", "Google Analytics", "G-D66RRD8GF2"),
    ],
)
def test_project_identifiers_are_read_from_what_the_page_serves(tool, text, kind, value):
    found = tool.scan_project_ids(text)
    assert {"kind": kind, "value": value} in found


def test_nothing_is_invented_when_the_bundle_is_clean(tool):
    assert tool.scan_project_ids("export const x = 1;") == []


def test_the_request_ceiling_stops_a_burst(tool):
    """The guardrail that keeps a run from reading as degrading the service."""
    budget = tool.Budget(interval=0, ceiling=3)
    assert [budget.take("example.com") for _ in range(4)] == [True, True, True, False]


def test_the_ceiling_is_per_host(tool):
    budget = tool.Budget(interval=0, ceiling=1)
    assert budget.take("a.example.com") is True
    assert budget.take("b.example.com") is True
    assert budget.take("a.example.com") is False


def test_authorization_is_required_and_honours_expiry(tool, tmp_path, monkeypatch):
    target = tmp_path / "authorized.json"
    monkeypatch.setattr(tool, "AUTHORIZED_FILE", target)
    assert tool.authorized("example.com") is None

    target.write_text(json.dumps({"hosts": [{"host": "example.com", "basis": "own-infra"}]}))
    assert tool.authorized("example.com") == "own-infra"
    assert tool.authorized("other.example.com") is None

    target.write_text(
        json.dumps(
            {"hosts": [{"host": "example.com", "basis": "own-infra", "expires": "2000-01-01"}]}
        )
    )
    assert tool.authorized("example.com") is None


def test_a_corrupt_authorization_file_authorises_nothing(tool, tmp_path, monkeypatch):
    """It fails closed. A malformed file must not read as a blanket permission."""
    target = tmp_path / "authorized.json"
    target.write_text("{not json")
    monkeypatch.setattr(tool, "AUTHORIZED_FILE", target)
    assert tool.authorized("example.com") is None


def test_no_secret_hunting_path_is_reachable(tool):
    """The guardrail is that these are absent from the code, not flag-gated.

    Requesting a path like /.git/config evidences knowing it was not meant to be
    public, which is the element the French line turns on, so no flag may reach one.
    """
    forbidden = (".git", ".env", "server-status", "wp-config", ".bak", "actuator/env", "admin")
    joined = " ".join(tool.DEEP_PATHS)
    for needle in forbidden:
        assert needle not in joined, f"{needle} must not be reachable"


def test_actuator_health_is_gated_on_the_exact_path(tool):
    """`/actuator/health` is fine and `/actuator/env` dumps config, so the gate is
    the whole path rather than the prefix."""
    assert "/actuator/health" in tool.DEEP_PATHS
    assert not any(path.startswith("/actuator/") and path != "/actuator/health" for path in tool.DEEP_PATHS)


def test_the_user_agent_identifies_the_tool_and_carries_a_contact(tool):
    """Never a browser string: impersonating one is what turns a lawful request into
    an evasive one."""
    assert tool.USER_AGENT.startswith("hostof/")
    assert "+http" in tool.USER_AGENT
    assert "Mozilla" not in tool.USER_AGENT


def test_brief_keeps_a_short_string_and_collapses_whitespace(tool):
    assert tool.brief("a  b\n c") == "a b c"


def test_brief_bounds_a_long_value(tool):
    """A wrapped evidence line destroys the column alignment it sits in."""
    assert tool.brief("x" * 200, limit=20) == "x" * 17 + "..."


@pytest.mark.parametrize(
    ("holder", "expected"),
    [
        ("AMAZON-02 - Amazon.com, Inc.", "Amazon.com, Inc."),
        ("Vercel, Inc", "Vercel, Inc"),
        (None, ""),
    ],
)
def test_the_readable_half_of_an_asn_holder_is_shown(tool, holder, expected):
    assert tool.holder_name(holder) == expected


def report_for(edge, origin, ids=()):
    return {
        "target": "example.com",
        "edge": edge,
        "origin": origin,
        "project": {"exposed": bool(ids), "ids": list(ids)},
    }


def test_the_summary_answers_rather_than_scores(tool):
    """A count of identified layers graded the run instead of answering the question."""
    line = tool.summarise(
        report_for({"vendor": "Vercel", "region": "fra1"}, {"vendor": "Vercel", "region": "iad1"})
    )
    assert line == "Vercel (fra1), computing in iad1"


def test_the_summary_says_when_the_origin_is_masked(tool):
    line = tool.summarise(report_for({"vendor": "Netlify", "region": "aws-fra"}, {}))
    assert line == "Netlify (aws-fra), origin masked"


def test_the_summary_names_a_different_origin_vendor(tool):
    line = tool.summarise(report_for({"vendor": "Cloudflare"}, {"vendor": "Google Cloud"}))
    assert "origin on Google Cloud" in line


def test_the_summary_pluralises_identifiers(tool):
    one = tool.summarise(report_for({"vendor": "Vercel"}, {}, ids=[{"kind": "a", "value": "1"}]))
    two = tool.summarise(
        report_for({"vendor": "Vercel"}, {}, ids=[{"kind": "a", "value": "1"}, {"kind": "b", "value": "2"}])
    )
    assert "1 identifier exposed" in one
    assert "2 identifiers exposed" in two


def test_the_summary_admits_an_unidentified_vendor(tool):
    assert tool.summarise(report_for({}, {})) == "example.com: no vendor identified"


def test_help_exits_ok(cli):
    result = cli("--help")
    assert result.returncode == EXIT_OK
    assert "hostof" in result.stdout


def test_a_missing_target_is_a_usage_error(cli):
    """argparse would exit 2, which is not in this tool's vocabulary."""
    result = cli()
    assert result.returncode == EXIT_USAGE
    assert "✗" in result.stderr


def test_deep_refuses_an_unauthorised_host(cli):
    result = cli("--deep", "example.com")
    assert result.returncode == EXIT_REFUSED
    assert "not authorised" in result.stderr


def test_deep_names_the_file_that_would_authorise_it(cli):
    """A refusal that does not say how to proceed is a dead end."""
    result = cli("--deep", "example.com")
    assert "authorized.json" in result.stderr
