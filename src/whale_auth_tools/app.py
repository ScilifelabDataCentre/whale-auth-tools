"""FastAPI application for ALTCHA and OpenLLM registration intake."""

from contextlib import asynccontextmanager
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from whale_auth_tools.altcha_service import (
    create_altcha_challenge,
    generate_secrets,
    verify_altcha_payload,
)
from whale_auth_tools.models import (
    QuestionnaireSchema,
    QuestionnaireSubmission,
    StoredSubmission,
    SubmissionAccepted,
    questionnaire_schema,
)
from whale_auth_tools.security import api_token_guard
from whale_auth_tools.settings import Settings
from whale_auth_tools.store import QuestionnaireStore


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an independently configurable application instance."""

    runtime_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime_settings.validate_secrets()
        store = QuestionnaireStore(runtime_settings.database_path)
        store.initialise()
        app.state.store = store
        yield

    app = FastAPI(
        title="Whale Auth Tools",
        description="ALTCHA and OpenLLM questionnaire intake API.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if runtime_settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if runtime_settings.docs_enabled else None,
    )
    if runtime_settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=runtime_settings.cors_origin_list,
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )

    require_api_token = api_token_guard(runtime_settings)
    Protected = Annotated[None, Depends(require_api_token)]

    def store_for(request: Request) -> QuestionnaireStore:
        return request.app.state.store

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["health"])
    async def readyz(request: Request) -> dict[str, str]:
        if not hasattr(request.app.state, "store"):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        return {"status": "ready"}

    @app.get(
        "/api/v1/questionnaire/schema",
        response_model=QuestionnaireSchema,
        tags=["questionnaire"],
    )
    async def get_questionnaire_schema(_: Protected) -> QuestionnaireSchema:
        return questionnaire_schema()

    @app.post(
        "/api/v1/questionnaire/submissions",
        response_model=SubmissionAccepted,
        status_code=status.HTTP_201_CREATED,
        tags=["questionnaire"],
    )
    async def create_questionnaire_submission(
        submission: QuestionnaireSubmission,
        _: Protected,
        store: QuestionnaireStore = Depends(store_for),
    ) -> SubmissionAccepted:
        if runtime_settings.altcha_required:
            if not submission.altcha_payload:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="altchaPayload is required.",
                )
            verification = verify_altcha_payload(submission.altcha_payload, runtime_settings)
            if not verification["verified"]:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="ALTCHA verification failed.",
                )
        return store.create(submission)

    @app.get(
        "/api/v1/questionnaire/submissions",
        response_model=list[StoredSubmission],
        tags=["questionnaire"],
    )
    async def list_questionnaire_submissions(
        _: Protected,
        store: QuestionnaireStore = Depends(store_for),
        limit: int = 100,
    ) -> list[StoredSubmission]:
        if not 1 <= limit <= 500:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="limit must be between 1 and 500.",
            )
        return store.list(limit)

    @app.delete(
        "/api/v1/questionnaire/submissions/{submission_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["questionnaire"],
    )
    async def delete_questionnaire_submission(
        submission_id: UUID,
        _: Protected,
        store: QuestionnaireStore = Depends(store_for),
    ) -> None:
        if not store.delete(submission_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    @app.post("/api/v1/altcha/secrets", tags=["altcha"])
    async def create_altcha_secrets(_: Protected) -> dict[str, str]:
        return generate_secrets()

    @app.post("/api/v1/altcha/challenge", tags=["altcha"])
    async def create_challenge(_: Protected) -> dict[str, Any]:
        return create_altcha_challenge(runtime_settings)

    @app.post("/api/v1/altcha/verify", tags=["altcha"])
    async def verify_challenge(payload: dict[str, str], _: Protected) -> dict[str, Any]:
        altcha_payload = payload.get("altchaPayload")
        if not altcha_payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="altchaPayload is required.",
            )
        return verify_altcha_payload(altcha_payload, runtime_settings)

    return app


app = create_app()
