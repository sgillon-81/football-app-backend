from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from supabase import create_client
from passlib.hash import bcrypt
from uuid import uuid4
import os

router = APIRouter()

SUPABASE_URL = os.getenv("https://izwwqzpvnrijarabwink.supabase.co")
SUPABASE_KEY = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml6d3dxenB2bnJpamFyYWJ3aW5rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIxNjA0MTIsImV4cCI6MjA1NzczNjQxMn0.FoB5Zp-NTlJf74VG4NgZ_j0s-n85JHdbdQr425suaQI")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class SignupUser(BaseModel):
    name: str
    email: EmailStr
    team_name: str
    is_admin: bool = False

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class PasswordChangeRequest(BaseModel):
    email: EmailStr
    old_password: str
    new_password: str

class ResetRequest(BaseModel):
    email: EmailStr

class ResetConfirm(BaseModel):
    email: EmailStr
    token: str
    new_password: str

# 🔐 Admin adds a user (generate one-time password)
@router.post("/admin/add_user")
def add_user(user: SignupUser):
    otp = uuid4().hex[:8]
    password_hash = bcrypt.hash(otp)
    response = supabase.table("users").insert({
        "name": user.name,
        "email": user.email,
        "team_name": user.team_name,
        "password_hash": password_hash,
        "is_admin": user.is_admin,
        "first_login": True
    }).execute()

    return {"message": "✅ User added", "email": user.email, "one_time_password": otp}

# 🔐 Login endpoint
@router.post("/login")
def login(data: LoginRequest):
    user = supabase.table("users").select("*").eq("email", data.email).execute()
    if not user.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_data = user.data[0]
    if not bcrypt.verify(data.password, user_data["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {
        "message": "✅ Login successful",
        "user": {
            "id": user_data["id"],
            "name": user_data["name"],
            "email": user_data["email"],
            "team_name": user_data["team_name"],
            "is_admin": user_data["is_admin"],
            "first_login": user_data["first_login"]
        }
    }

# 🔐 Force password change on first login
@router.post("/change_password")
def change_password(data: PasswordChangeRequest):
    user = supabase.table("users").select("*").eq("email", data.email).execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found")
    user_data = user.data[0]
    if not bcrypt.verify(data.old_password, user_data["password_hash"]):
        raise HTTPException(status_code=401, detail="Old password incorrect")

    new_hash = bcrypt.hash(data.new_password)
    supabase.table("users").update({
        "password_hash": new_hash,
        "first_login": False
    }).eq("email", data.email).execute()

    return {"message": "✅ Password changed successfully"}

# 🔐 Forgot password
@router.post("/request_reset")
def request_reset(data: ResetRequest):
    token = uuid4().hex
    user = supabase.table("users").select("*").eq("email", data.email).execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found")
    supabase.table("users").update({"reset_token": token}).eq("email", data.email).execute()

    # ✉️ Send token via email (e.g. via Resend, SendGrid, etc)
    print(f"🔐 Password reset token for {data.email}: {token}")

    return {"message": "✅ Reset token sent"}

# 🔐 Confirm password reset
@router.post("/confirm_reset")
def confirm_reset(data: ResetConfirm):
    user = supabase.table("users").select("*").eq("email", data.email).eq("reset_token", data.token).execute()
    if not user.data:
        raise HTTPException(status_code=400, detail="Invalid token or email")

    supabase.table("users").update({
        "password_hash": bcrypt.hash(data.new_password),
        "reset_token": None,
        "first_login": False
    }).eq("email", data.email).execute()

    return {"message": "✅ Password reset successfully"}
