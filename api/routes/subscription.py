from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import api.crud.subscription as crud
import api.schemas.subscription as sub_schema
from api.schemas.extras import SubscriptionExtra
from api.schemas.token import StudentJWT
from api.utils.dependencies import get_db, get_current_student
from api.crud.student import get_student
from api.crud.channel import get_channel

router = APIRouter(
    prefix="/subscriptions",
    tags=["Subscriptions"],
    dependencies=[]
)


@router.get("/", response_model=list[SubscriptionExtra], status_code=status.HTTP_200_OK)
def get_subscriptions(channel_id: Optional[int] = None, student_id: Optional[int] = None,
                      skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    - Can get subscriptions filtered by channel_id and student_id.
    - Can get subscriptions filtered by channel_id only.
    - Can get subscriptions filtered by student_id only.
    - Can get subscriptions with no filter
    """
    if channel_id is not None and student_id is not None:
        return crud.get_sub_by_channel_and_student(db,channel_id, student_id)
    elif channel_id:
        return crud.get_subscriptions_for_channel(db, channel_id)
    elif student_id:
        return crud.get_subscriptions_for_student(db, student_id)

    return crud.get_subscriptions(db, skip, limit)


@router.post("/", response_model=sub_schema.Subscription, status_code=status.HTTP_201_CREATED)
def create_new_subscription(subscription: sub_schema.SubscriptionCreate, current_student: Annotated[StudentJWT, Depends(get_current_student)], db: Session = Depends(get_db)):
    """
    # Logic
    - If user subscribing has the permissions to
    - It checks if Subscription already exists
    - Verifies if Channel ID is valid
    - Also verified if Student ID is correct
    """

    db_subscription = crud.get_sub_by_channel_and_student(db, subscription.channel_id, subscription.student_id)

    if subscription.student_id != current_student.student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    if db_subscription is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already subscribed")

    channel_exists = get_channel(db, subscription.channel_id)
    if channel_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel with specified ID does not exist")

    student_exists = get_student(db, subscription.student_id)
    if student_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student with specified ID does not exist")

    return crud.subscribe(db, subscription)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe(channel_id: int, student_id: int, current_student: Annotated[StudentJWT, Depends(get_current_student)], db: Session = Depends(get_db)):
    """
    - Checks if the user unsubscribing has the permissions to
    - Verifies if channel exists already
    """
    if student_id != current_student.student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    db_subscription = crud.get_sub_by_channel_and_student(db, channel_id, student_id)
    if db_subscription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such entry found in database")

    crud.unsubscribe(db, channel_id, student_id)
    return JSONResponse(content={"detail": "Unsubscribed"})
