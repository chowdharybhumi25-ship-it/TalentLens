from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.auth import RecruiterCreate, RecruiterLogin, Token, RecruiterOut
from app.models.recruiter import Recruiter
from app.core.security import (
    get_password_hash, verify_password, create_access_token, get_current_user
)

router = APIRouter()


@router.post("/register", response_model=Token, status_code=201)
def register(user_data: RecruiterCreate, db: Session = Depends(get_db)):
    # Check if email exists
    existing = db.query(Recruiter).filter(Recruiter.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create recruiter
    recruiter = Recruiter(
        email=user_data.email,
        full_name=user_data.full_name,
        company=user_data.company,
        hashed_password=get_password_hash(user_data.password),
    )
    db.add(recruiter)
    db.commit()
    db.refresh(recruiter)

    token = create_access_token({"sub": str(recruiter.id)})
    return Token(
        access_token=token,
        recruiter=RecruiterOut.model_validate(recruiter)
    )


@router.post("/login", response_model=Token)
def login(credentials: RecruiterLogin, db: Session = Depends(get_db)):
    recruiter = db.query(Recruiter).filter(Recruiter.email == credentials.email).first()
    if not recruiter or not verify_password(credentials.password, recruiter.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not recruiter.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    token = create_access_token({"sub": str(recruiter.id)})
    return Token(
        access_token=token,
        recruiter=RecruiterOut.model_validate(recruiter)
    )


@router.get("/me", response_model=RecruiterOut)
def get_me(current_user: Recruiter = Depends(get_current_user)):
    return current_user
