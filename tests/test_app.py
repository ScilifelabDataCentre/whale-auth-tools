from pathlib import Path

from altcha import Challenge, Payload, Solution, solve_challenge
from fastapi.testclient import TestClient

from whale_auth_tools.app import create_app
from whale_auth_tools.settings import Settings


def make_client(tmp_path: Path, *, altcha_required: bool = False) -> TestClient:
    settings = Settings(
        WHALE_AUTH_API_TOKEN="test-api-token",
        ALTCHA_HMAC_SECRET="test-signing-secret",
        ALTCHA_HMAC_KEY_SECRET="test-key-signing-secret",
        DATABASE_PATH=tmp_path / "questionnaires.sqlite3",
        ALTCHA_REQUIRED=altcha_required,
        ALTCHA_COST=1,
    )
    return TestClient(create_app(settings))


def headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-api-token"}


def valid_submission() -> dict:
    return {
        "organisation": "SciLifeLab",
        "positions": ["Bioinformatician"],
        "scilifelabAffiliation": "Infrastructure unit staff",
        "plannedUses": ["Research and data analysis"],
        "addToSlack": False,
    }


def test_api_routes_require_a_token(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        assert client.get("/healthz").status_code == 200
        assert client.get("/api/v1/questionnaire/schema").status_code == 401
        assert client.get(
            "/api/v1/questionnaire/schema", headers={"X-API-Token": "test-api-token"}
        ).status_code == 401
        assert client.get("/api/v1/questionnaire/schema", headers=headers()).status_code == 200


def test_questionnaire_is_persisted(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        created = client.post(
            "/api/v1/questionnaire/submissions", json=valid_submission(), headers=headers()
        )
        assert created.status_code == 201
        response_id = created.json()["id"]

        listed = client.get("/api/v1/questionnaire/submissions", headers=headers())
        assert listed.status_code == 200
        assert listed.json()[0]["id"] == response_id
        assert listed.json()[0]["organisation"] == "SciLifeLab"


def test_other_and_slack_answers_need_details(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        invalid = valid_submission() | {
            "positions": ["Other"],
            "addToSlack": True,
        }
        response = client.post(
            "/api/v1/questionnaire/submissions", json=invalid, headers=headers()
        )
        assert response.status_code == 422


def test_altcha_can_be_required_for_questionnaire_submission(tmp_path: Path) -> None:
    with make_client(tmp_path, altcha_required=True) as client:
        response = client.post(
            "/api/v1/questionnaire/submissions", json=valid_submission(), headers=headers()
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "altchaPayload is required."


def test_altcha_endpoint_generates_and_verifies_official_payload(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        challenge_response = client.post("/api/v1/altcha/challenge", headers=headers())
        assert challenge_response.status_code == 200
        challenge = Challenge.from_dict(challenge_response.json())

        # Cost=1 gives a fast deterministic test; production defaults to 5000.
        solution = solve_challenge(challenge)
        assert isinstance(solution, Solution)
        payload = Payload(challenge, solution).to_base64()
        verified = client.post(
            "/api/v1/altcha/verify", json={"altchaPayload": payload}, headers=headers()
        )
        assert verified.status_code == 200
        assert verified.json()["verified"] is True
