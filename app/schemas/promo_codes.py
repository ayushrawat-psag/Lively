from pydantic import BaseModel, Field


class ValidatePromoCodeRequest(BaseModel):
    code: str = Field(..., min_length=1)


class ValidatePromoCodeResponse(BaseModel):
    success: bool
    valid: bool
    code: str
    discount_percent: int | None = Field(default=None, alias="discountPercent")
    message: str

    model_config = {"populate_by_name": True}
