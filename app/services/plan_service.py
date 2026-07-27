from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import BillingInterval
from app.models.pricing_plan import PricingPlan
from app.schemas.plans import PlanPublic, PlansResponse

_BILLING_INTERVAL_API = {
    BillingInterval.MONTHLY: "month",
    BillingInterval.YEARLY: "year",
    BillingInterval.ONE_TIME: "one_time",
}


def get_plans(db: Session | None = None) -> PlansResponse:
    if db is None:
        from app.db.session import SessionLocal

        local_db = SessionLocal()
        try:
            return _load_plans(local_db)
        finally:
            local_db.close()
    return _load_plans(db)


def _load_plans(db: Session) -> PlansResponse:
    plans = list(
        db.scalars(
            select(PricingPlan).where(PricingPlan.active.is_(True)).order_by(PricingPlan.plan_name)
        ).all()
    )
    if not plans:
        return PlansResponse(
            success=True,
            plans=[
                PlanPublic(
                    id="monthly",
                    name="Monthly",
                    price=15.99,
                    billingInterval="month",
                    maxParents=1,
                    maxChildren=6,
                ),
                PlanPublic(
                    id="yearly",
                    name="Yearly",
                    price=149.49,
                    billingInterval="year",
                    maxParents=1,
                    maxChildren=6,
                ),
            ],
        )

    return PlansResponse(
        success=True,
        plans=[
            PlanPublic(
                id=plan.plan_name.lower().replace(" ", "_"),
                name=plan.plan_name,
                price=float(plan.price_amount),
                billingInterval=_BILLING_INTERVAL_API.get(plan.billing_interval, plan.billing_interval.value.lower()),
                maxParents=1,
                maxChildren=6,
            )
            for plan in plans
        ],
    )
