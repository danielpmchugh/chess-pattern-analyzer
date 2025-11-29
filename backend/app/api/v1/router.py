"""
Main API router for v1 endpoints.

This module aggregates all v1 API routes into a single router
that can be included in the main application.
"""

from fastapi import APIRouter

from app.api.v1 import health, analysis

# Create the main v1 router
router = APIRouter()

# Include sub-routers
router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(analysis.router, tags=["Analysis"])

# Placeholder routers for future implementation
# These will be implemented in subsequent tasks:
# - users.router (BACKEND-003)
# - session.router (BACKEND-004)
