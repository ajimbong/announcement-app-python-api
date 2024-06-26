from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import api.crud.student as crud
from api.db.models import Student as StudentModel
import api.schemas.student as student_schema
from api.schemas.extras import StudentExtra
from api.schemas.token import StudentJWT
from api.utils.dependencies import get_db, get_current_student

router = APIRouter(
    prefix="/students",
    tags=["Students"],
    dependencies=[],
)


@router.get("/", response_model=list[student_schema.Student], status_code=status.HTTP_200_OK)
def get_students(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    students = crud.get_students(db=db, skip=skip, limit=limit)
    return students


@router.get("/{student_id}", response_model=StudentExtra, status_code=status.HTTP_200_OK)
def get_single_student(student_id: int, db: Session = Depends(get_db)):
    db_student = crud.get_student(db, student_id)
    if db_student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Student with id {student_id} could not be found")
    return db_student


@router.post("/", response_model=student_schema.Student, status_code=status.HTTP_201_CREATED)
def create_student(student: student_schema.StudentCreate, db: Session = Depends(get_db)):
    """
    - Checks if a student already exists with same email
    - Checks if a student already exists with same matricule
    """

    student_with_email = crud.get_student_by_email(db, student.email)
    if student_with_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Email already exists")

    student_with_matricule = crud.get_student_by_matricule(db, student.matricule)
    if student_with_matricule:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Matricule already exists")

    return crud.create_student(db, student)


@router.put("/{student_id}", response_model=student_schema.Student, status_code=status.HTTP_200_OK)
def update_student(student_id: int, student: student_schema.StudentUpdate, current_student: Annotated[StudentJWT, Depends(get_current_student)], db: Session = Depends(get_db)):
    """
    - We first of all verify if the Student exists, to make sure we have
      something to update
    - Verify if student updating has permissions to update
    - Then we verify if the updated email has been taken by another user
    - Or the updated matricule is taken by another user
    """

    db_student: StudentModel = crud.get_student(db, student_id)
    if db_student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No student with ID {student_id}")

    if db_student.id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    if crud.other_student_with_same_email(db, student_id, student):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Email already exists")

    if crud.other_student_with_same_matricule(db, student_id, student):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Matricule already exists")

    return crud.update_student(db, student, student_id)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, current_student: Annotated[StudentJWT, Depends(get_current_student)], db: Session = Depends(get_db)):
    """
    - We first of all verify if the Student exists
    - And see if the current logged in student has permissions to delete
    """

    db_student = crud.get_student(db, student_id)
    if db_student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No student with ID {student_id}")

    if db_student.id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    crud.delete_student(db, student_id)
    return JSONResponse(content={"detail": "Student deleted"})
