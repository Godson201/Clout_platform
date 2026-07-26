from fastapi import APIRouter

from app.api.v1 import (
    admin,
    admin_announcements,
    admin_pricing,
    admin_settlement,
    admin_templates,
    advertisements,
    announcements,
    auth,
    brands,
    campaigns,
    contracts,
    influencers,
    marketplace,
    messaging,
    payments,
    payouts,
    profile_highlights,
    slots,
    social_accounts,
    templates,
    users,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(brands.router)
api_router.include_router(influencers.router)
api_router.include_router(admin.router)
api_router.include_router(admin_templates.router)
api_router.include_router(admin_pricing.router)
api_router.include_router(admin_settlement.router)
api_router.include_router(admin_announcements.router)
api_router.include_router(templates.router)
api_router.include_router(advertisements.router)
api_router.include_router(campaigns.router)
api_router.include_router(marketplace.router)
api_router.include_router(slots.router)
api_router.include_router(payments.router)
api_router.include_router(payouts.router)
api_router.include_router(social_accounts.router)
api_router.include_router(messaging.router)
api_router.include_router(contracts.router)
api_router.include_router(announcements.router)
api_router.include_router(profile_highlights.router)
