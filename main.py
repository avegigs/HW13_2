# app/main.py
from fastapi import FastAPI, HTTPException, Query, Depends, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from src.tokens_access import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_access_token_from_refresh_token,
    create_refresh_token,
    get_current_user,
)
from src.pidantycmod import (
    UserCreate,
    UserResponse,
    ContactUpdate,
    ContactCreate,
    ContactResponse,
    AvatarResponse,
)
from database.models import Contact, Base, User
from typing import List
from sqlalchemy import or_, and_, extract
from database.database import get_db
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from database.users import create_user, authenticate_user, get_user_by_email
from utils.token import generate_verification_token, verify_verification_token
from utils.email import send_email_verification
from fastapi_limiter.depends import RateLimiter
from fastapi.middleware.cors import CORSMiddleware
import cloudinary
from cloudinary.uploader import upload
from cloudinary.utils import cloudinary_url
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

limiter_dependency = RateLimiter(times=1, seconds=1)


@app.post("/register/", response_model=UserResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=409, detail="User with this email already exists"
        )

    verification_token = generate_verification_token(user.email)
    await send_email_verification(user.email, verification_token)

    created_user = create_user(db, user.email, user.password)

    return created_user


@app.get("/confirm-email/")
def confirm_email(token: str, email: str, db: Session = Depends(get_db)):
    user = get_user_by_email(db, email)
    if user and verify_verification_token(email, token):
        user.is_verified = True
        db.commit()
        return {"message": "Email has been confirmed"}
    raise HTTPException(status_code=400, detail="Invalid token or user not found")


@app.post("/token/", response_model=dict)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    db_user = authenticate_user(db, form_data.username, form_data.password)
    if not db_user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires.total_seconds()
    )

    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = await create_refresh_token(
        data={"sub": db_user.email},
        db=db,
        expires_delta=refresh_token_expires.total_seconds(),
    )

    avatar_url = db_user.avatar_url if db_user.avatar_url else None

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
        "avatar_url": avatar_url,
    }


@app.post("/refresh-token/", response_model=dict)
async def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    return await create_access_token_from_refresh_token(refresh_token, db=db)


@app.get("/protected-resource/")
async def get_protected_resource(current_user: User = Depends(get_current_user)):
    return {"message": "This is a protected resource", "user": current_user}


@app.post("/upload-avatar/", response_model=AvatarResponse)
async def upload_avatar(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if not file.content_type.startswith("image"):
            raise HTTPException(status_code=400, detail="Invalid image format")

        result = upload(file.file, folder="avatars")

        avatar_url, _ = cloudinary_url(result["public_id"], format=result["format"])

        current_user.avatar_url = avatar_url
        db.commit()

        return {"avatar_url": avatar_url}
    except cloudinary.exceptions.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error uploading avatar")


@app.post("/contacts/", response_model=ContactResponse)
def create_contact(
    contact: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    rate_limiter: RateLimiter = Depends(limiter_dependency),
):
    contact.birthdate = contact.birthdate.strftime("%Y-%m-%d")
    db_contact = Contact(**contact.dict(), user_email=current_user.email)
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact


@app.get("/contacts/", response_model=List[ContactResponse])
def read_contacts(
    skip: int = Query(0, description="Skip N contacts", ge=0),
    limit: int = Query(100, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contacts = (
        db.query(Contact)
        .filter(Contact.user_email == current_user.email)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return contacts


@app.get("/contacts/{contact_id}", response_model=ContactResponse)
def read_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    contact = (
        db.query(Contact)
        .filter(Contact.id == contact_id, Contact.user_email == current_user)
        .first()
    )
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@app.put("/contacts/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: int,
    contact: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    rate_limiter: RateLimiter = Depends(limiter_dependency),
):
    db_contact = (
        db.query(Contact)
        .filter(Contact.id == contact_id, Contact.user_email == current_user)
        .first()
    )
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    for key, value in contact.dict().items():
        setattr(db_contact, key, value)
    db.commit()
    db.refresh(db_contact)
    return db_contact


@app.delete("/contacts/{contact_id}", response_model=ContactResponse)
def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    db_contact = (
        db.query(Contact)
        .filter(Contact.id == contact_id, Contact.user_email == current_user)
        .first()
    )
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(db_contact)
    db.commit()
    return db_contact


@app.get("/contacts/search", response_model=List[ContactResponse])
def search_contacts(
    query: str = Query(
        ..., description="Пошук контакту за іменем, прізвищем або email"
    ),
    db: Session = Depends(get_db),
):
    contacts = (
        db.query(Contact)
        .filter(
            or_(
                Contact.first_name.ilike(f"%{query}%"),
                Contact.last_name.ilike(f"%{query}%"),
                Contact.email.ilike(f"%{query}%"),
            )
        )
        .all()
    )
    return contacts


@app.get("/contacts/birthday", response_model=List[ContactResponse])
def upcoming_birthdays(db: Session = Depends(get_db)):
    current_date = datetime.now().date()
    seven_days_from_now = current_date + timedelta(days=7)
    contacts = (
        db.query(Contact)
        .filter(
            and_(
                extract("month", Contact.birthdate) == current_date.month,
                extract("day", Contact.birthdate) >= current_date.day,
                extract("day", Contact.birthdate) <= seven_days_from_now.day,
            )
        )
        .all()
    )

    return contacts


@app.delete("/users/{user_id}/")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}
