"""Shared demo fixture used by DemoStore and the Supabase seed script."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from apps.api.app.core.scoring import (
    OPPORTUNITY_SCORE_VERSION,
    OPPORTUNITY_WEIGHTS,
    RECOMMENDATION_VERSION,
    SELLER_READINESS_VERSION,
)

DEMO_USER_ID = "00000000-0000-4000-8000-000000000001"
DEMO_WORKSPACE_ID = "00000000-0000-4000-8000-000000000010"
DEMO_THESIS_ID = "00000000-0000-4000-8000-000000000020"

HVAC_SAMPLES: List[Dict[str, Any]] = [
    {
        "canonical_name": "Valley Climate Control",
        "domain": "valleyclimate.example",
        "phone_norm": "+16285550101",
        "address": "2140 Industrial Blvd, Phoenix, AZ 85034",
        "geo": {"lat": 33.4484, "lng": -112.0740, "city": "Phoenix", "state": "AZ", "country": "US"},
        "industry": "HVAC",
        "revenue_est": 4_200_000,
        "founded_year": 1994,
        "owner_name": "Robert Chen",
        "scores": {"fit": 92, "seller": 86, "timing": 88, "access": 78, "competition": 82},
        "action": "CONTACT_NOW",
        "expires_in_days": 6,
        "skip_contact": False,
        "missing": [],
        "why_now": [
            "Owner tenure estimate ~30 years (founded 1994).",
            "Website last-modified signal stale >18 months.",
            "Leadership change 15 days ago — contact window closing.",
        ],
        "counter": ["Recent 5-star review volume slightly up in last 90 days."],
        "leadership_days_ago": 15,
    },
    {
        "canonical_name": "Apex Air Phoenix",
        "domain": "apexairphx.example",
        "phone_norm": "+16025550111",
        "address": "900 E Van Buren St, Phoenix, AZ 85006",
        "geo": {"lat": 33.4510, "lng": -112.0650, "city": "Phoenix", "state": "AZ", "country": "US"},
        "industry": "HVAC",
        "revenue_est": 3_800_000,
        "founded_year": 1996,
        "owner_name": "Sandra Ortiz",
        "scores": {"fit": 89, "seller": 82, "timing": 80, "access": 76, "competition": 78},
        "action": "CONTACT_NOW",
        "expires_in_days": 28,
        "skip_contact": False,
        "missing": [],
        "why_now": [
            "Strong Phoenix HVAC fit; slightly below Valley on timing urgency.",
            "Owner identified; website freshness stale.",
        ],
        "counter": ["Same metro as Valley Climate Control — substitute platform slot."],
        "leadership_days_ago": None,
    },
    {
        "canonical_name": "Gulf Coast Air Pros",
        "domain": "gulfcoastairpros.example",
        "phone_norm": "+18135550202",
        "address": "88 Bayshore Dr, Tampa, FL 33611",
        "geo": {"lat": 27.9506, "lng": -82.4572, "city": "Tampa", "state": "FL", "country": "US"},
        "industry": "HVAC",
        "revenue_est": 6_800_000,
        "founded_year": 1987,
        "owner_name": "Diane Morales",
        "scores": {"fit": 88, "seller": 79, "timing": 72, "access": 65, "competition": 70},
        "action": "RELATIONSHIP_FIRST",
        "expires_in_days": 45,
        "skip_contact": False,
        "missing": [],
        "why_now": [
            "Business age 35+ years; succession language on About page.",
            "Hiring pages empty / careers path returns 404.",
        ],
        "counter": ["Strong Google rating (4.8) — not distressed."],
        "leadership_days_ago": None,
    },
    {
        "canonical_name": "Lone Star Mechanical",
        "domain": "lonestarmech.example",
        "phone_norm": "+17135550303",
        "address": "4500 Commerce St, Houston, TX 77011",
        "geo": {"lat": 29.7604, "lng": -95.3698, "city": "Houston", "state": "TX", "country": "US"},
        "industry": "HVAC",
        "revenue_est": 3_100_000,
        "founded_year": 2005,
        "owner_name": "James Whitaker",
        "scores": {"fit": 74, "seller": 61, "timing": 55, "access": 80, "competition": 60},
        "action": "MONITOR",
        "expires_in_days": 60,
        "skip_contact": False,
        "missing": [],
        "why_now": ["Digital presence active; limited exit-window signals."],
        "counter": ["Founded 2005 — below preferred 15+ year tenure band slightly for exit window."],
        "leadership_days_ago": None,
    },
    {
        "canonical_name": "Bay Area Comfort Systems",
        "domain": "bayareacomfort.example",
        "phone_norm": "+14155550404",
        "address": "1200 Harbor Rd, Oakland, CA 94607",
        "geo": {"lat": 37.8044, "lng": -122.2712, "city": "Oakland", "state": "CA", "country": "US"},
        "industry": "HVAC",
        "revenue_est": 9_400_000,
        "founded_year": None,
        "owner_name": None,
        "scores": {"fit": 95, "seller": 91, "timing": 84, "access": 42, "competition": 55},
        "action": "RESEARCH_MORE",
        "expires_in_days": 14,
        "skip_contact": True,
        "missing": ["contacts", "founded_year"],
        "why_now": [
            "Leadership change hint: new GM title on site, founder still listed as Principal.",
            "Stagnation: headcount signal flat across observations.",
        ],
        "counter": ["High local competition density (Places category density high)."],
        "leadership_days_ago": 40,
    },
    {
        "canonical_name": "Desert Peak Heating & Cooling",
        "domain": "desertpeakhvac.example",
        "phone_norm": "+14805550505",
        "address": "33 Mesa Ave, Scottsdale, AZ 85251",
        "geo": {"lat": 33.4942, "lng": -111.9261, "city": "Scottsdale", "state": "AZ", "country": "US"},
        "industry": "HVAC",
        "revenue_est": 3_500_000,
        "founded_year": 1999,
        "owner_name": "Carol Nguyen",
        "scores": {"fit": 81, "seller": 70, "timing": 68, "access": 88, "competition": 75},
        "action": "RELATIONSHIP_FIRST",
        "expires_in_days": 45,
        "skip_contact": False,
        "missing": [],
        "why_now": ["Verified phone + owner estimate present; digital decay moderate."],
        "counter": ["Revenue near lower band of thesis."],
        "leadership_days_ago": None,
    },
    {
        "canonical_name": "Cascade Comfort NW",
        "domain": "cascadecomfortnw.example",
        "phone_norm": "+12065550606",
        "address": "4100 Aurora Ave N, Seattle, WA 98103",
        "geo": {"lat": 47.6062, "lng": -122.3321, "city": "Seattle", "state": "WA", "country": "US"},
        "industry": "HVAC",
        "revenue_est": 5_100_000,
        "founded_year": 1988,
        "owner_name": "Tom Reeves",
        "scores": {"fit": 70, "seller": 84, "timing": 78, "access": 70, "competition": 60},
        "action": "CONTACT_NOW",
        "expires_in_days": -5,
        "skip_contact": False,
        "missing": [],
        "why_now": ["Window opened last month after leadership change — now stale."],
        "counter": ["Outside primary thesis geographies (WA)."],
        "leadership_days_ago": 50,
    },
]


def _co(
    *,
    canonical_name: str,
    domain: str,
    phone_norm: str,
    address: str,
    geo: Dict[str, Any],
    industry: str,
    revenue_est: int,
    founded_year: Optional[int],
    owner_name: Optional[str],
    scores: Dict[str, int],
    action: str,
    expires_in_days: int,
    why_now: List[str],
    counter: List[str],
    leadership_days_ago: Optional[int] = None,
    skip_contact: bool = False,
    missing: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build one seeded company record."""
    return {
        "canonical_name": canonical_name,
        "domain": domain,
        "phone_norm": phone_norm,
        "address": address,
        "geo": geo,
        "industry": industry,
        "revenue_est": revenue_est,
        "founded_year": founded_year,
        "owner_name": owner_name,
        "scores": scores,
        "action": action,
        "expires_in_days": expires_in_days,
        "skip_contact": skip_contact,
        "missing": missing or [],
        "why_now": why_now,
        "counter": counter,
        "leadership_days_ago": leadership_days_ago,
    }


# Adjacent searcher verticals — distinct from the HVAC cluster so Radar shows
# category mix without stealing Valley vs Apex outreach slots.
CATEGORY_SAMPLES: List[Dict[str, Any]] = [
    _co(
        canonical_name="Copperhead Plumbing Co",
        domain="copperheadplumbing.example",
        phone_norm="+15125550707",
        address="1800 S Lamar Blvd, Austin, TX 78704",
        geo={"lat": 30.2672, "lng": -97.7431, "city": "Austin", "state": "TX", "country": "US"},
        industry="Plumbing",
        revenue_est=3_600_000,
        founded_year=1991,
        owner_name="Miguel Santos",
        scores={"fit": 78, "seller": 74, "timing": 66, "access": 81, "competition": 72},
        action="RELATIONSHIP_FIRST",
        expires_in_days=40,
        why_now=["Owner-operated plumber, 30+ years; adjacent to HVAC roll-up thesis."],
        counter=["Industry is plumbing, not HVAC — fit is adjacency, not core."],
    ),
    _co(
        canonical_name="Red Tile Roofing",
        domain="redtileroofing.example",
        phone_norm="+14075550808",
        address="2200 W Colonial Dr, Orlando, FL 32804",
        geo={"lat": 28.5383, "lng": -81.3792, "city": "Orlando", "state": "FL", "country": "US"},
        industry="Roofing",
        revenue_est=5_400_000,
        founded_year=1985,
        owner_name="Patricia Hale",
        scores={"fit": 58, "seller": 80, "timing": 62, "access": 70, "competition": 64},
        action="MONITOR",
        expires_in_days=55,
        why_now=["Aging owner, storm-driven revenue; watch for succession listing."],
        counter=["Roofing is project-cycle, not recurring service HVAC."],
    ),
    _co(
        canonical_name="Arc & Line Electric",
        domain="arclineelectric.example",
        phone_norm="+12145550909",
        address="4100 Maple Ave, Dallas, TX 75219",
        geo={"lat": 32.7767, "lng": -96.7970, "city": "Dallas", "state": "TX", "country": "US"},
        industry="Electrical",
        revenue_est=4_800_000,
        founded_year=1989,
        owner_name="Darren Cole",
        scores={"fit": 64, "seller": 71, "timing": 60, "access": 77, "competition": 68},
        action="RELATIONSHIP_FIRST",
        expires_in_days=42,
        why_now=["Commercial electrical contractor with owner still in the truck."],
        counter=["Licensing silo vs HVAC; cross-sell only if dual-trade."],
    ),
    _co(
        canonical_name="Citrus Grove Landscape",
        domain="citrusgroveland.example",
        phone_norm="+13055551010",
        address="7800 SW 40th St, Miami, FL 33155",
        geo={"lat": 25.7617, "lng": -80.1918, "city": "Miami", "state": "FL", "country": "US"},
        industry="Landscaping",
        revenue_est=2_900_000,
        founded_year=1998,
        owner_name="Elena Ruiz",
        scores={"fit": 52, "seller": 63, "timing": 48, "access": 74, "competition": 58},
        action="MONITOR",
        expires_in_days=70,
        why_now=["Route-based maintenance accounts; seasonal labor risk."],
        counter=["Below core HVAC thesis; landscaping adjacency only."],
    ),
    _co(
        canonical_name="Sonoran Pest Defense",
        domain="sonoranpest.example",
        phone_norm="+15205551111",
        address="1600 E Broadway Blvd, Tucson, AZ 85719",
        geo={"lat": 32.2226, "lng": -110.9747, "city": "Tucson", "state": "AZ", "country": "US"},
        industry="Pest Control",
        revenue_est=3_200_000,
        founded_year=1993,
        owner_name=None,
        scores={"fit": 55, "seller": 77, "timing": 70, "access": 44, "competition": 61},
        action="RESEARCH_MORE",
        expires_in_days=18,
        skip_contact=True,
        missing=["contacts"],
        why_now=["Recurring residential routes; owner not identified on site."],
        counter=["Need decision-maker before outreach."],
        leadership_days_ago=22,
    ),
    _co(
        canonical_name="Palm Court Dental Group",
        domain="palmcourtdental.example",
        phone_norm="+16195551212",
        address="3500 5th Ave, San Diego, CA 92103",
        geo={"lat": 32.7157, "lng": -117.1611, "city": "San Diego", "state": "CA", "country": "US"},
        industry="Dental",
        revenue_est=2_400_000,
        founded_year=1982,
        owner_name="Dr. Helen Park",
        scores={"fit": 40, "seller": 88, "timing": 76, "access": 82, "competition": 50},
        action="RELATIONSHIP_FIRST",
        expires_in_days=30,
        why_now=["Practice age 40+ years; DSOs circling San Diego county."],
        counter=["Healthcare vertical — not HVAC services thesis."],
    ),
    _co(
        canonical_name="Westside Veterinary Hospital",
        domain="westsidevet.example",
        phone_norm="+19165551313",
        address="900 J St, Sacramento, CA 95814",
        geo={"lat": 38.5816, "lng": -121.4944, "city": "Sacramento", "state": "CA", "country": "US"},
        industry="Veterinary",
        revenue_est=2_150_000,
        founded_year=1979,
        owner_name="Alan Brooks",
        scores={"fit": 36, "seller": 85, "timing": 73, "access": 69, "competition": 48},
        action="MONITOR",
        expires_in_days=50,
        why_now=["Solo-owner clinic; corporate vet roll-ups active in CA."],
        counter=["Off-thesis industry; keep on watch list only."],
    ),
    _co(
        canonical_name="Harbor Auto Works",
        domain="harborautoworks.example",
        phone_norm="+19045551414",
        address="2100 Philips Hwy, Jacksonville, FL 32207",
        geo={"lat": 30.3322, "lng": -81.6557, "city": "Jacksonville", "state": "FL", "country": "US"},
        industry="Auto Repair",
        revenue_est=2_700_000,
        founded_year=1990,
        owner_name="Frank DiMarco",
        scores={"fit": 34, "seller": 68, "timing": 51, "access": 86, "competition": 55},
        action="MONITOR",
        expires_in_days=65,
        why_now=["Independent shop, owner reachable; limited services overlap."],
        counter=["Auto repair is not a home-services thesis fit."],
    ),
    _co(
        canonical_name="BrightFloor Janitorial",
        domain="brightfloorjanitorial.example",
        phone_norm="+12105551515",
        address="600 E Commerce St, San Antonio, TX 78205",
        geo={"lat": 29.4241, "lng": -98.4936, "city": "San Antonio", "state": "TX", "country": "US"},
        industry="Commercial Cleaning",
        revenue_est=6_100_000,
        founded_year=2001,
        owner_name="Nadia Grant",
        scores={"fit": 48, "seller": 57, "timing": 44, "access": 73, "competition": 42},
        action="DEPRIORITIZE",
        expires_in_days=90,
        why_now=["Contract cleaning scale is interesting; labor intensity is high."],
        counter=["Founded 2001 — thinner exit window; low thesis overlap."],
    ),
    _co(
        canonical_name="Iron Gate Security Systems",
        domain="irongatesecurity.example",
        phone_norm="+17205551616",
        address="1400 15th St, Denver, CO 80202",
        geo={"lat": 39.7392, "lng": -104.9903, "city": "Denver", "state": "CO", "country": "US"},
        industry="Security Systems",
        revenue_est=4_050_000,
        founded_year=1986,
        owner_name="Kevin Marsh",
        scores={"fit": 45, "seller": 79, "timing": 67, "access": 71, "competition": 59},
        action="MONITOR",
        expires_in_days=48,
        why_now=["RMR alarm book; owner tenure long; outside primary states."],
        counter=["Colorado is outside CA/TX/FL/AZ thesis geographies."],
        leadership_days_ago=33,
    ),
]

COMPANY_SAMPLES: List[Dict[str, Any]] = HVAC_SAMPLES + CATEGORY_SAMPLES

DEMO_THESIS = {
    "name": "US HVAC owner-operated $2–10M",
    "criteria": {
        "industries": ["HVAC", "heating", "air conditioning", "plumbing"],
        "geographies": [{"country": "US", "states": ["CA", "TX", "FL", "AZ"]}],
        "revenue_min": 2_000_000,
        "revenue_max": 10_000_000,
        "owner_operated": True,
        "min_years_in_business": 15,
        "keywords": ["commercial HVAC", "residential HVAC", "service"],
    },
    "strategy": {
        "rationale": "Recurring service revenue, fragmented market, aging owners",
        "adjacent_segments": ["refrigeration", "building maintenance"],
    },
}


def apply_hvac_seed(store: Any, workspace_id: str, thesis_id: str) -> None:
    """Write seeded companies, scores, and recommendations onto any store."""
    now = datetime.now(timezone.utc)

    for sample in COMPANY_SAMPLES:
        founded = sample["founded_year"]
        company = store.upsert_company(
            {
                "canonical_name": sample["canonical_name"],
                "domain": sample["domain"],
                "phone_norm": sample["phone_norm"],
                "address": sample["address"],
                "geo": sample["geo"],
                "industry": sample["industry"],
                "revenue_est": sample["revenue_est"],
                "founded_year": founded,
                "workspace_id": workspace_id,
            }
        )
        cid = company["id"]
        store.add_company_source(cid, "seed", sample["domain"], confidence=1.0)

        if not sample.get("skip_contact") and sample.get("owner_name"):
            store.add_contact(
                cid,
                name=sample["owner_name"],
                title="Owner / Principal",
                phone=sample["phone_norm"],
                owner_estimate=True,
                confidence=0.7,
            )

        age_for_snippet = founded or 1995
        ev_ids = []
        for etype, snippet in [
            ("website_snippet", f"About {sample['canonical_name']} — family-owned since {age_for_snippet}."),
            ("places_stats", f"Places rating present; industry={sample['industry']}."),
            ("domain_meta", f"Domain {sample['domain']} observed."),
        ]:
            ev = store.add_evidence(
                cid,
                source="seed",
                type=etype,
                url=f"https://{sample['domain']}/",
                snippet=snippet,
                confidence=0.8,
            )
            ev_ids.append(ev["id"])

        signal_specs = [
            ("website_freshness", "stale" if sample["scores"]["seller"] > 75 else "active", 0.75),
            ("owner_identified", not sample.get("skip_contact"), 0.7),
            ("review_trend", "flat", 0.6),
        ]
        if founded:
            signal_specs.insert(0, ("business_age_years", 2026 - founded, 0.9))
        if sample.get("leadership_days_ago") is not None:
            observed = (now - timedelta(days=int(sample["leadership_days_ago"]))).isoformat()
            store.upsert_signal(
                cid,
                "leadership_change",
                True,
                0.7,
                observed_at=observed,
            )

        for stype, value, conf in signal_specs:
            store.upsert_signal(cid, stype, value, conf)

        s = sample["scores"]
        age_proxy = founded or 1995
        store.add_seller_score(
            {
                "company_id": cid,
                "exit_window": min(100, (2026 - age_proxy) * 2.5),
                "succession_vacuum": s["seller"] * 0.9,
                "digital_decay": 85 if s["seller"] > 75 else 35,
                "stagnation": 55,
                "recent_change": s["timing"] * 0.6,
                "sri_total": round(s["seller"], 1),
                "confidence": 0.72,
                "model_version": SELLER_READINESS_VERSION,
                "explanation": {"components": ["seeded"]},
            }
        )

        opp = round(
            OPPORTUNITY_WEIGHTS["thesis_fit"] * s["fit"]
            + OPPORTUNITY_WEIGHTS["seller_readiness"] * s["seller"]
            + OPPORTUNITY_WEIGHTS["timing"] * s["timing"]
            + OPPORTUNITY_WEIGHTS["access"] * s["access"]
            + OPPORTUNITY_WEIGHTS["competition_advantage"] * s["competition"],
            1,
        )
        timing_bucket = (
            "ready_now"
            if sample["action"] == "CONTACT_NOW" and sample["expires_in_days"] >= 0
            else "warming_up"
            if sample["action"] in ("RELATIONSHIP_FIRST", "RESEARCH_MORE")
            else "watch"
        )
        store.add_opportunity_score(
            {
                "company_id": cid,
                "thesis_id": thesis_id,
                "fit": s["fit"],
                "seller": s["seller"],
                "timing": s["timing"],
                "access": s["access"],
                "competition": s["competition"],
                "opportunity_score": opp,
                "confidence": 0.55 if sample.get("missing") else 0.74,
                "model_version": OPPORTUNITY_SCORE_VERSION,
                "explanation": {
                    "why_now": sample["why_now"],
                    "counter_signals": sample["counter"],
                    "missing": list(sample.get("missing") or []),
                    "timing_bucket": timing_bucket,
                },
            }
        )

        expires_at = (now + timedelta(days=int(sample["expires_in_days"]))).isoformat()
        store.upsert_recommendation(
            cid,
            thesis_id,
            action=sample["action"],
            priority=int(opp),
            reason=sample["why_now"][0] if sample["why_now"] else "Seeded recommendation",
            model_version=RECOMMENDATION_VERSION,
            expires_at=expires_at,
        )
        store.upsert_pipeline(cid, thesis_id, stage="identified", probability=0.1, notes="")
