from app.schemas.plans import PlanPublic, PlansResponse


def get_plans() -> PlansResponse:
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
