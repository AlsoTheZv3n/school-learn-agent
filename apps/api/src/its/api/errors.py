"""Unified error model (API-3): safety exceptions -> neutral 403, lookups -> 404.

Neutral messages avoid leaking detail (e.g. whether a specific student exists).
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from its.safety.cohort import CohortTooSmall
from its.safety.scoping import ScopeError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ScopeError)
    async def _scope(_: Request, __: ScopeError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": "forbidden"})

    @app.exception_handler(CohortTooSmall)
    async def _cohort(_: Request, __: CohortTooSmall) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={"detail": "too few learners for an anonymous aggregate"},
        )

    @app.exception_handler(LookupError)
    async def _lookup(_: Request, __: LookupError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "not found"})
