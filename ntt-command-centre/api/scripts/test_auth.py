"""Run python -m unittest api.scripts.test_auth (no live model calls)."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["NTT_LLM_ENABLED"] = "0"
os.environ["NTT_AS_OF"] = "2026-09-15"

from fastapi.testclient import TestClient
from api import auth
from api.main import app
from api.scripts.setup_demo_accounts import setup
from api.semantic import personas as PR
from api.semantic import predict as P
from api.semantic import ds_model as DS
from api.semantic import anomalies as ANOM
from api.semantic import crosssell as XS
from api.semantic.loader import facts
from api.semantic.measures import money
from api.semantic.measures import FilterState


class AuthFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.registry_path = Path(cls.tmp.name) / "accounts.json"
        cls.sheet = Path(cls.tmp.name) / "credentials.md"
        setup(cls.registry_path, cls.sheet)
        cls.env = patch.dict(os.environ, {"NTT_DEMO_ACCOUNTS_FILE": str(cls.registry_path), "NTT_ACCESS_DISABLED": "1"})
        cls.env.start()
        cls.registry = json.loads(cls.registry_path.read_text(encoding="utf-8"))
        cls.passwords = {}
        for line in cls.sheet.read_text(encoding="utf-8").splitlines():
            if line.startswith("| ") and "@" in line:
                fields = [v.strip().strip("`") for v in line.split("|")[1:-1]]
                cls.passwords[fields[1]] = fields[2]
        cls.client = TestClient(app)
        cls.tokens = {}
        for account in cls.registry["accounts"]:
            response = cls.client.post("/api/auth/login", json={"email": account["email"], "password": cls.passwords[account["email"]]})
            if response.status_code != 200:
                raise AssertionError(f"Login failed for {account['id']}: {response.status_code}")
            cls.tokens[account["id"]] = response.json()["token"]

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.env.stop()
        cls.tmp.cleanup()

    def headers(self, account_id="sales-brian.thompson"):
        return {"Authorization": "Bearer " + self.tokens[account_id]}

    def test_focused_executive_experience(self):
        headers = self.headers("executive-na")
        meta = self.client.get("/api/meta", headers=headers).json()
        self.assertEqual([p["key"] for p in meta["pages"]],
                         ["tldr", "closure-risk", "anomalies", "opportunities", "action-center"])
        self.assertEqual({d["key"] for d in meta["dimensions"]}, {"country", "quarter"})
        self.assertEqual(meta["measures"], [{"key": "revenue", "label": "ACV GP", "default": True}])

        payloads = {}
        forbidden = ("gross profit", "gross-profit", '"gp"', "margin", "budget",
                     "coverage", "plan gap", "profit plan", "acvgp", "valueatstake")
        for page in ["tldr", "opportunities", "anomalies", "closure-risk", "action-center"]:
            response = self.client.get(f"/api/view?page={page}&measure=gp&lob=Security", headers=headers)
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            payloads[page] = payload
            self.assertEqual(payload["measure"], "revenue")
            self.assertEqual(payload["charts"], [])
            self.assertEqual(payload["kpis"], [])
            self.assertEqual(payload["metricBanners"], [])
            encoded = json.dumps(payload).lower()
            self.assertTrue(all(term not in encoded for term in forbidden), (page, encoded))

        brief_messages = {m["key"]: m for m in payloads["tldr"]["executive"]["messages"]}
        weekly = payloads["tldr"]["executive"]
        self.assertIsNotNone(weekly["weeklyBanner"])
        self.assertEqual(len(weekly["weeklyBanner"]["supporting"]), 3)
        self.assertTrue(all(b["headline"] and b["subline"]
                            for b in weekly["weeklyBanner"]["supporting"]))
        supporting = {banner["key"]: banner for banner in weekly["weeklyBanner"]["supporting"]}
        closure = weekly["closureOverview"]
        anomalies = weekly["anomalyOverview"]
        opportunities = weekly["opportunityOverview"]
        self.assertIn(closure["formattedLowProbabilityRevenue"], weekly["weeklyBanner"]["headline"])
        self.assertIn(str(closure["lowProbabilityDeals"]), weekly["weeklyBanner"]["subline"])
        self.assertIn(str(anomalies["stalledDeals"]), weekly["weeklyBanner"]["subline"])
        self.assertIn(closure["formattedLowProbabilityRevenue"], supporting["closure"]["headline"])
        self.assertIn(anomalies["formattedStalledRevenue"], supporting["anomalies"]["headline"])
        self.assertIn(opportunities["formattedPeerRevenueBenchmark"], supporting["opportunities"]["headline"])
        self.assertEqual(len(weekly["weeklyInsights"]), 4)
        self.assertEqual([i["rank"] for i in weekly["weeklyInsights"]], [1, 2, 3, 4])
        self.assertEqual([i["key"] for i in weekly["weeklyInsights"]], [
            "weekly:forecast-probability", "weekly:stuck", "weekly:anomaly",
            "weekly:cross-sell",
        ])
        action_keys = {a["key"] for a in payloads["action-center"]["executive"]["actions"]}
        self.assertEqual(
            {a["key"] for a in weekly["actions"]},
            {i["actionKey"] for i in weekly["weeklyInsights"]},
        )
        self.assertTrue(all(a["description"] and a["nextStep"]
                            for a in payloads["action-center"]["executive"]["actions"]))
        self.assertTrue(all({o["status"] for o in a["options"]}
                            == {"Actioned", "In Review", "Monitoring", "Dismissed"}
                            for a in payloads["action-center"]["executive"]["actions"]))
        self.assertTrue(all(i["actionKey"] in action_keys for i in weekly["weeklyInsights"]))
        weekly_actions = {a["key"]: a for a in weekly["actions"]}
        expected_pages = {
            "closure": "closure-risk",
            "anomalies": "anomalies",
            "opportunities": "opportunities",
        }
        for insight in weekly["weeklyInsights"]:
            self.assertEqual(insight["page"], expected_pages[insight["theme"]])
            action = weekly_actions[insight["actionKey"]]
            self.assertEqual(action["theme"], insight["theme"])
            self.assertTrue(action["description"])
            self.assertTrue(action["nextStep"])
            if insight["theme"] == "closure":
                self.assertEqual(action["headline"], f"Review {insight['entity']}")
            elif insight["theme"] == "anomalies":
                self.assertEqual(action["headline"], f"Investigate {insight['entity']}")
            else:
                self.assertTrue(action["headline"].startswith("Pilot "))
        for page, key in (("opportunities", "opportunities"), ("anomalies", "anomalies"),
                          ("closure-risk", "closure")):
            detail = {m["key"]: m for m in payloads[page]["executive"]["messages"]}
            self.assertEqual(brief_messages[key], detail[key])
            self.assertIsNone(payloads[page]["executive"]["weeklyBanner"])
            self.assertEqual(payloads[page]["executive"]["weeklyInsights"], [])
        executive_principal = PR.resolve("executive", "north-america")
        revenue_fs = FilterState(measure="revenue")
        # The focused growth overview is a direct count of the scoped cross-sell export.
        xs_summary = XS.summary(revenue_fs, executive_principal)
        opportunity_overview = payloads["opportunities"]["executive"]["opportunityOverview"]
        self.assertEqual(opportunity_overview["recommendations"], xs_summary["recommendations"])
        self.assertEqual(opportunity_overview["accounts"], xs_summary["accounts"])
        self.assertEqual(opportunity_overview["strongRecommendations"], xs_summary["strong"])
        self.assertEqual(opportunity_overview["repeatablePlays"], xs_summary["themes"])
        self.assertIn(money(xs_summary["peerWonRevenueMedian"]), supporting["opportunities"]["headline"])
        self.assertNotIn("upside", supporting["opportunities"]["headline"].lower())

        anomaly_rows = payloads["anomalies"]["executive"]["anomalyFindings"]
        self.assertTrue(anomaly_rows)
        self.assertTrue(all(row["entityType"] == "Account" for row in anomaly_rows))
        self.assertTrue(all("agreement" not in row for row in anomaly_rows))
        account_findings = ANOM.scoped(
            ANOM.for_persona("executive"), revenue_fs, executive_principal
        )
        account_findings = account_findings[
            (account_findings["entity_type"] == "Account")
            & (account_findings["framing"] == "risk")
        ]
        anomaly_overview = payloads["anomalies"]["executive"]["anomalyOverview"]
        stalled = P.risk_table()
        stalled = stalled[stalled["is_stalled"]]
        self.assertEqual(anomaly_overview["accountFindings"], len(account_findings))
        self.assertEqual(anomaly_overview["accountsAffected"],
                         account_findings["entity_id"].nunique())
        self.assertIn(money(anomaly_overview["stalledRevenue"]), supporting["anomalies"]["headline"])
        self.assertIn(str(anomaly_overview["stalledDeals"]), supporting["anomalies"]["subline"])
        expected_bands = (("60–90 days", 60, 90), ("91–180 days", 91, 180),
                          ("181+ days", 181, None))
        for actual, (label, minimum, maximum) in zip(anomaly_overview["stagnationBands"], expected_bands):
            expected = stalled[stalled["quiet_days"] >= minimum]
            if maximum is not None:
                expected = expected[expected["quiet_days"] <= maximum]
            self.assertEqual(actual["label"], label)
            self.assertEqual(actual["deals"], len(expected))
            self.assertAlmostEqual(actual["revenue"], float(expected["acv_revenue"].sum()))
        call_summary = {row["call"]: row for row in anomaly_overview["forecastCalls"]}
        for call in ("Commit", "Best Case", "Pipeline", "Omitted"):
            expected = stalled[stalled["forecast_category"] == call]
            self.assertEqual(call_summary[call]["deals"], len(expected))
            self.assertAlmostEqual(call_summary[call]["revenue"], float(expected["acv_revenue"].sum()))
        stalled_rows = payloads["anomalies"]["executive"]["stalledDeals"]
        self.assertLessEqual(len(stalled_rows), 5)
        self.assertTrue(all(row["silenceDays"] >= 60 for row in stalled_rows))
        anomaly_actions = {
            action["key"]: action
            for action in payloads["anomalies"]["executive"]["actions"]
        }
        action_center_keys = {
            action["key"]
            for action in payloads["action-center"]["executive"]["actions"]
        }
        source_stalls = ANOM.enriched()
        source_stalls = source_stalls[
            (source_stalls["entity_type"] == "Opportunity")
            & (source_stalls["anomaly_type"] == "stalled_pipeline")
        ].drop_duplicates("entity_id").set_index("entity_id")
        for row in stalled_rows:
            self.assertIn(row["key"], source_stalls.index)
            source = source_stalls.loc[row["key"]]
            self.assertEqual(row["evidence"], source["evidence"])
            self.assertEqual(row["nextStep"], source["recommended_action"])
            self.assertIn(row["actionKey"], anomaly_actions)
            self.assertIn(row["actionKey"], action_center_keys)
            action = anomaly_actions[row["actionKey"]]
            self.assertEqual(action["description"], source["evidence"])
            self.assertEqual(action["nextStep"], source["recommended_action"])
            self.assertNotIn("revenueImpact", action)
            self.assertNotIn("formattedRevenueImpact", action)
        closure_rows = payloads["closure-risk"]["executive"]["closureExceptions"]
        self.assertTrue(closure_rows)
        self.assertTrue(all(row["deterioration"] for row in closure_rows))
        self.assertEqual([row["forecastCategory"] for row in closure_rows[:2]],
                         ["Commit", "Best Case"])
        for row in closure_rows:
            if row["accountCycleContext"] is not None:
                self.assertGreaterEqual(row["accountCycleSampleSize"], 3)
                self.assertIsNotNone(row["accountCycleDays"])
                self.assertIsNotNone(row["plannedCycleDays"])
                if row["accountCycleMismatch"]:
                    self.assertGreaterEqual(row["accountCycleGapDays"], 30)
                    self.assertGreaterEqual(
                        row["accountCycleGapDays"], row["accountCycleDays"] * .25
                    )
                    self.assertIn("shorter than that median", row["accountCycleContext"])
        closure_actions = payloads["closure-risk"]["executive"]["actions"]
        self.assertEqual(len(closure_actions), len(closure_rows))
        self.assertEqual({a["key"] for a in closure_actions},
                         {f"closure:{row['key']}" for row in closure_rows})
        closure_overview = payloads["closure-risk"]["executive"]["closureOverview"]
        predictions = DS.predictions().drop_duplicates("opportunity_code").set_index("opportunity_code")
        scored_risk = risk.copy()
        scored_risk["p_win"] = scored_risk["opportunity_code"].map(predictions["p_win"])
        for series, (forecast, threshold) in zip(
                closure_overview["series"], (("Commit", .35), ("Best Case", .25))):
            declared = scored_risk[scored_risk["forecast_category"] == forecast]
            defensible = declared[declared["p_win"] >= threshold]
            self.assertEqual(series["forecast"], forecast)
            self.assertEqual(series["declaredDeals"], len(declared))
            self.assertEqual(series["defensibleDeals"], len(defensible))
            self.assertAlmostEqual(series["declaredRevenue"], float(declared["acv_revenue"].sum()))
            self.assertAlmostEqual(series["defensibleRevenue"], float(defensible["acv_revenue"].sum()))
        self.assertEqual(closure_overview["stats"], {
            "openDeals": len(risk),
            "highRiskDeals": len(hot),
            "pastDueDeals": int(risk["is_past_due"].sum()),
            "stalledDeals": int(risk["is_stalled"].sum()),
            "slippedDeals": int((risk["close_date_slips"] > 0).sum()),
        })
        self.assertEqual({a["theme"] for a in payloads["tldr"]["executive"]["actions"]},
                         {"opportunities", "anomalies", "closure"})

        for old, new in (("growth", "opportunities"), ("risks", "anomalies"),
                         ("actions", "action-center"), ("performance", "tldr"),
                         ("structure", "tldr")):
            self.assertEqual(self.client.get(f"/api/view?page={old}", headers=headers).json()["page"], new)

        refused = self.client.get("/api/ai/ask?q=Show%20gross%20profit%20margin", headers=headers).json()
        self.assertTrue(refused["refused"])
        deal_key = payloads["closure-risk"]["executive"]["closureExceptions"][0]["key"]
        detail = self.client.get(f"/api/deal/{deal_key}", headers=headers)
        self.assertEqual(detail.status_code, 200)
        encoded_detail = json.dumps(detail.json()).lower()
        self.assertTrue(all(term not in encoded_detail for term in forbidden), encoded_detail)
        self.assertEqual(self.client.get("/api/v1/measures", headers=headers).status_code, 403)

    def test_setup_is_idempotent(self):
        original = self.registry_path.read_bytes(), self.sheet.read_bytes()
        self.assertEqual(setup(self.registry_path, self.sheet)[0], 0)
        self.assertEqual(original, (self.registry_path.read_bytes(), self.sheet.read_bytes()))
        self.assertEqual(len(self.tokens), facts()["owner"].nunique() + 7)
        self.assertEqual(
            {a["name"] for a in self.registry["accounts"] if a["role"] == "ae"},
            set(facts()["owner"].unique()),
        )
        self.assertEqual(
            {a["name"] for a in self.registry["accounts"] if a["role"] == "manager"},
            {"Dana Whitfield", "Marcus Lindqvist", "Priya Raghavan", "Tomás Oliveira",
             "Hannah Brecht", "Kenji Nakamura"},
        )
        self.assertEqual(
            [a["identity"] for a in self.registry["accounts"] if a["role"] == "executive"],
            ["north-america"],
        )

    def test_all_accounts_have_correct_session_and_scope(self):
        for account in self.registry["accounts"]:
            with self.subTest(account=account["id"]):
                headers = self.headers(account["id"])
                me = self.client.get("/api/auth/me", headers=headers)
                self.assertEqual(me.status_code, 200)
                profile = me.json()
                self.assertEqual(profile["role"], account["role"])
                self.assertEqual(profile["identity"], account["identity"])
                self.assertNotIn("passwordHash", profile)
                meta = self.client.get("/api/meta", headers=headers).json()
                self.assertEqual(meta["persona"]["active"]["identity"], account["identity"])
                self.assertTrue(all(not ids for ids in meta["persona"]["identities"].values()))
                self.assertEqual([p["key"] for p in meta["pages"]], profile["pages"])
                risks = self.client.get("/api/risk?limit=300", headers=headers).json()["deals"]
                principal = PR.resolve(account["role"], account["identity"])
                owners = principal.predicate.get("owner")
                if owners:
                    self.assertTrue(all(d["owner"] in owners for d in risks))
                page = self.client.get("/api/view?page=not-a-page", headers=headers)
                self.assertEqual(page.status_code, 200)
                self.assertEqual(page.json()["page"], profile["home"])

    def test_sales_aliases_and_case(self):
        for account in self.registry["accounts"][:4]:
            for email in [account["email"], *account["aliases"]]:
                result = self.client.post("/api/auth/login", json={"email": " " + email.upper() + " ", "password": self.passwords[account["email"]]})
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()["user"]["id"], account["id"])

    def test_bad_credentials_and_expired_or_legacy_tokens(self):
        for email in ["missing@example.com", self.registry["accounts"][0]["email"]]:
            response = self.client.post("/api/auth/login", json={"email": email, "password": "wrong"})
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["detail"], "Email or password is incorrect")
        expired, _ = auth.issue(self.registry["accounts"][0], self.registry, now=0)
        for token in ["", "legacy-token", expired, self.tokens["executive-na"] + "modified"]:
            self.assertEqual(self.client.get("/api/meta", headers={"Authorization": f"Bearer {token}"}).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", json={"password": "ntt@2026"}).status_code, 422)
        self.assertEqual(self.client.get("/api/meta?token=" + self.tokens["executive-na"]).status_code, 401)

    def test_user_selection_cannot_override_token(self):
        headers = {**self.headers(), "X-User-UPN": "executive@global.ntt"}
        response = self.client.get("/api/v1/measures?persona=executive&identity=north-america", headers=headers)
        self.assertEqual(response.json()["principal"]["identity"], "Brian Thompson")
        page = self.client.get("/api/view?page=tldr&persona=executive", headers=headers).json()
        self.assertEqual(page["page"], "my-day")
        for path in ["/api/budget", "/api/health/details", "/api/v1/catalog"]:
            self.assertEqual(self.client.get(path, headers=headers).status_code, 403)

    def test_cross_user_details_and_forged_explanations_denied(self):
        frame = facts()
        brian = frame[frame["owner"] == "Brian Thompson"]
        foreign = frame[(frame["owner"] != "Brian Thompson") & frame["is_open"]].iloc[0]
        code = foreign["opportunity_code"]
        for path in [f"/api/deal/{code}", f"/api/ai/next-action/{code}"]:
            self.assertEqual(self.client.get(path, headers=self.headers()).status_code, 404)
        account = frame[~frame["account_code"].isin(brian["account_code"])].iloc[0]["account_code"]
        self.assertEqual(self.client.get(f"/api/account/{account}", headers=self.headers()).status_code, 404)
        result = self.client.post("/api/ai/explain", headers=self.headers(), json={"key": "forged", "entity": {"type": "Opportunity", "id": code}})
        self.assertEqual(result.status_code, 404)
        own = brian.iloc[0]["account_code"]
        detail = self.client.get(f"/api/account/{own}", headers=self.headers())
        self.assertEqual(detail.status_code, 200)
        self.assertAlmostEqual(detail.json()["gp"], float(brian.loc[brian["account_code"] == own, "acv_gp"].sum()))

    def test_anomaly_summary_matches_scoped_findings(self):
        response = self.client.get("/api/anomalies?limit=500", headers=self.headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["summary"]["total"], response.json()["total"])

    def test_filtered_empty_book_returns_empty_account_aggregates(self):
        response = self.client.get("/api/accounts?rep=Karen%20Phillips", headers=self.headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["whitespace"], [])
        self.assertEqual(response.json()["lobValue"], [])
        self.assertEqual(response.json()["concentration"]["totalGp"], 0)
        self.assertTrue(all(r["accountsWithGiven"] == 0 for r in response.json()["attach"]))

    def test_liveness_and_no_auth_bypass(self):
        self.assertEqual(self.client.get("/api/health").json(), {"ok": True})
        self.assertEqual(self.client.get("/api/meta").status_code, 401)
        self.assertEqual(self.client.get("/api/auth/me", headers=self.headers()).headers["cache-control"], "no-store")

    def test_disabled_and_invalid_scope_accounts_fail_closed(self):
        account = self.registry["accounts"][0]
        bad = {**account, "identity": "unknown-rep"}
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):
            auth.principal_for(bad)
        modified = {**self.registry, "accounts": [{**a, "enabled": False} for a in self.registry["accounts"]]}
        self.assertIsNone(auth.verify(self.tokens[account["id"]], modified))


if __name__ == "__main__":
    unittest.main()
