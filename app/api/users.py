from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.redis_client import get_redis
from app.models.user import User
from app.models.schemas import User as UserSchema, UserCreate, UserUpdate
import json

router = APIRouter()


@router.post("/users/", response_model=UserSchema)
def create_user(user: UserCreate, db: Session = Depends(get_db), redis_client = Depends(get_redis)):
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Cache user in Redis
    redis_client.setex(f"user:{db_user.id}", 3600, json.dumps({
        "id": db_user.id,
        "email": db_user.email,
        "username": db_user.username
    }))
    
    return db_user


@router.get("/users/", response_model=List[UserSchema])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=UserSchema)
def read_user(user_id: int, db: Session = Depends(get_db), redis_client = Depends(get_redis)):
    # Try to get from cache first
    cached_user = redis_client.get(f"user:{user_id}")
    if cached_user:
        cached_data = json.loads(cached_user)
        # Get full user data from database for complete response
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user:
            return db_user
    
    # Get from database
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Cache the user
    redis_client.setex(f"user:{user_id}", 3600, json.dumps({
        "id": db_user.id,
        "email": db_user.email,
        "username": db_user.username
    }))
    
    return db_user


@router.put("/users/{user_id}", response_model=UserSchema)
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db), redis_client = Depends(get_redis)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user
    user_data = user.dict(exclude_unset=True)
    for key, value in user_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    
    # Update cache
    redis_client.delete(f"user:{user_id}")
    redis_client.setex(f"user:{user_id}", 3600, json.dumps({
        "id": db_user.id,
        "email": db_user.email,
        "username": db_user.username
    }))
    
    return db_user


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), redis_client = Depends(get_redis)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(db_user)
    db.commit()
    
    # Remove from cache
    redis_client.delete(f"user:{user_id}")
    
    return {"message": "User deleted successfully"}
