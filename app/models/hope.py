from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class HopeCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Enter the name for the support")
    details: str = Field(..., description="Enter the details for this program")
    type_of_donation: str
    support_field: str = Field(..., alias="fields", description="Category or field of donation")
    amount: float
    
    # Extra fields from the UI card (optional for now)
    grade_requirement: Optional[str] = None
    students: List[str] = Field(default_factory=list)

class HopeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    details: str
    type_of_donation: str
    support_field: str = Field(..., alias="fields")
    amount: float
    grade_requirement: Optional[str] = None
    students: List[str] = Field(default_factory=list)
    created_at: datetime
