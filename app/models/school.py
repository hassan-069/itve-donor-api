from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator, field_validator
from typing import Optional , Literal
from datetime import datetime
import re
import html


# 1. NESTED MODELS 


class SchoolRatings(BaseModel):
    technology: int = Field(..., ge=1, le=5, description="Must be between 1 and 5")
    leadership: int = Field(..., ge=1, le=5)
    communication: int = Field(..., ge=1, le=5)
    management: int = Field(..., ge=1, le=5)
    motivation: int = Field(..., ge=1, le=5)
    teaching: int = Field(..., ge=1, le=5)

class SchoolStats(BaseModel):
    followers: int = Field(default=0, ge=0)
    students: int = Field(default=0, ge=0)
    followings: int = Field(default=0, ge=0)

class SchoolDetails(BaseModel):
    rank: int = Field(default=0, ge=0)
    principal: str = ""
    totalStudentsEnrolled: int = Field(default=0, ge=0)
    alumni: int = Field(default=0, ge=0)


# 2. SIGN-UP API MODEL 

class SchoolSignup(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    instituteName: str
    name: str
    phone: str
    cnic: str
    gender: Literal["Male", "Female", "Other"]
    username: str
    email: EmailStr
    password: str
    confirmPassword: str
    locationName: str
    dateOfBirth: str
    instituteAge: str
    experience: str
    ratings: SchoolRatings
    promoCode: Optional[str] = None

    @field_validator("instituteName")
    @classmethod
    def validate_institute_name(cls, v: str) -> str:
        if len(v) < 2 or len(v) > 150:
            raise ValueError("Institute Name must be between 2 and 150 characters.")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if len(v) < 2 or len(v) > 100:
            raise ValueError("Name must be between 2 and 100 characters.")
        return v

    @field_validator("experience")
    @classmethod
    def validate_experience(cls, v: str) -> str:
        valid_exp = ["5 years", "10 years", "16 years", "20 years", "25+ years"]
        if v not in valid_exp:
            raise ValueError("Invalid Experience level. Please select a valid option (e.g., '16 years').")
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: EmailStr) -> str:
        return str(v).lower()

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.lower()
        if not re.fullmatch(r"^[a-z0-9_.]+$", v):
            raise ValueError("Username can only contain letters, numbers, underscores (_), and dots (.). Spaces are not allowed.")
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be between 3 and 50 characters.")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        normalized = re.sub(r"[\s-]", "", v)
        if not re.fullmatch(r"^\+92\d{10}$", normalized):
            raise ValueError("Phone format must be +92XXXXXXXXXX (exactly 10 digits after +92).")
        return normalized

    @field_validator("cnic")
    @classmethod
    def validate_cnic(cls, v: str) -> str:
        normalized = re.sub(r"-", "", v)
        if not re.fullmatch(r"^\d{13}$", normalized):
            raise ValueError("CNIC must be exactly 13 digits long.")
        return normalized
    


    @field_validator("dateOfBirth")
    @classmethod
    def validate_dob(cls, v: str) -> str:
        try:
            date_obj = datetime.strptime(v, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Enter a valid date of birth in DD/MM/YYYY format.")

        if date_obj > datetime.today():
            raise ValueError("Date of birth cannot be in the future.")

        return v

    @field_validator("instituteAge")
    @classmethod
    def validate_institute_age(cls, v: str) -> str:
        try:
            date_obj = datetime.strptime(v, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Enter a valid institute founding date in DD/MM/YYYY format.")

        if date_obj > datetime.today():
            raise ValueError("Institute founding date cannot be in the future.")

        return v
    

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter (A-Z).")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter (a-z).")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number (0-9).")
        if not re.search(r"[^A-Za-z0-9]", v):
            raise ValueError("Password must contain at least one special character (e.g., @, #, $, !).")
        return v

    @model_validator(mode="after")
    def check_passwords_match(self) -> "SchoolSignup":
        if self.password != self.confirmPassword:
            raise ValueError("Passwords do not match. Please ensure both passwords are exactly the same.")
        return self



# 3. PROFILE API MODEL 


class SchoolProfileResponse(BaseModel):
    schoolId: str
    username: str
    instituteName: str
    name: str
    email: str
    phone: str
    cnic: str
    gender: str
    bio: str = ""
    profilePicture: str = ""
    badge: bool = False
    stats: SchoolStats
    details: SchoolDetails
    facilities: list[str] = Field(default_factory=list)
    labs: list[str] = Field(default_factory=list)
    location: str

# 4. EDIT PROFILE API MODEL (Form Data Validation)
class SchoolProfileUpdate(BaseModel):
    name: str
    instituteName: str
    bio: Optional[str] = ""
    gender: Literal["Male", "Female", "Other"]
    dateOfBirth: str
    username: str
    locationName: str

    @field_validator("name", "instituteName")
    @classmethod
    def validate_lengths(cls, v: str) -> str:
        if len(v) < 2 or len(v) > 100:
            raise ValueError("Name and Institute Name must be between 2 and 100 characters.")
        return v

    @field_validator("bio")
    @classmethod
    def sanitize_bio(cls, v: str) -> str:
        if v:
            if len(v) > 500:
                raise ValueError("Bio cannot exceed 500 characters.")
            # XSS Protection: Strip HTML tags to prevent script injection
            clean_text = re.sub(r'<[^>]*?>', '', v)
            return html.escape(clean_text)
        return v


    @field_validator("dateOfBirth")
    @classmethod
    def validate_dob(cls, v: str) -> str:
        try:
            date_obj = datetime.strptime(v, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Enter a valid date in DD/MM/YYYY format.")
        
        if date_obj > datetime.today():
            raise ValueError("Date cannot be in the future.")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.lower()
        if not re.fullmatch(r"^[a-z0-9_.]+$", v):
            raise ValueError("Username can only contain letters, numbers, underscores, and dots.")
        return v
    
# 5. LOGIN API MODEL
class SchoolLogin(BaseModel):
    identifier: str  # Can be email or username
    password: str