"""
Main API router for v1 endpoints.

This module aggregates all v1 API routes into a single router
that can be included in the main application.
"""

from fastapi import APIRouter

from app.api.v1 import health

# Create the main v1 router
router = APIRouter()

# Include sub-routers
router.include_router(health.router, prefix="/health", tags=["Health"])

# Placeholder routers for future implementation
# These will be implemented in subsequent tasks:
# - analysis.router (BACKEND-002)
# - users.router (BACKEND-003)
# - session.router (BACKEND-004)
