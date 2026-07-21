from pydantic import BaseModel, Field


class PlanPublic(BaseModel):
    id: str
    name: str
    price: float
    billing_interval: str = Field(..., alias="billingInterval")
    max_parents: int = Field(..., alias="maxParents")
    max_children: int = Field(..., alias="maxChildren")

    model_config = {"populate_by_name": True}


class PlansResponse(BaseModel):
    success: bool
    plans: list[PlanPublic]

    model_config = {"populate_by_name": True}
