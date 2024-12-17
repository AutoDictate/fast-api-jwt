from typing import List, Annotated, Literal

from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette import status
import uvicorn

import models
from auth import router, get_current_user
from database import engine, SessionLocal
from exception import add_exception_handlers

app = FastAPI()
app.include_router(router)
add_exception_handlers(app)

models.Base.metadata.create_all(bind=engine)

class ChoiceBase(BaseModel):
    choice_text: str
    is_correct: bool

class QuestionBase(BaseModel):
    question_text: str
    choices: List[ChoiceBase]

class FilterParams(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    order_by: Literal["created_at", "updated_at"] = "created_at"
    tags: list[str]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

val = Annotated[str | None, Query(min_length=3, max_length=50)]

@app.get('/', status_code=status.HTTP_200_OK)
async def get_user(user: user_dependency):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Authentication Failed')
    return {'User': user}

# Testing Purpose API endpoint
@app.get('/hello/bro')
async def read_items(filter_: Annotated[FilterParams, Query()]):
    return filter_

@app.get('/questions/{question_id}')
async def get_question_by_id(question_id: int, db: db_dependency):
    result = db.query(models.Questions).filter(question_id == models.Questions.id).first()
    if not result:
        raise HTTPException(status_code=404, detail='Question not found')
    return result

@app.post('/questions')
async def create_question(question: QuestionBase, db: db_dependency):
    db_question = models.Questions(question_text=question.question_text)
    db.add(db_question)
    db.commit()
    db.refresh(db_question)

    for choice in question.choices:
        db_choice = models.Choices(
            choice_text=choice.choice_text,
            is_correct=choice.is_correct,
            question_id=db_question.id
        )
        db.add(db_choice)

    db.commit()
    return db_question

if __name__ == "__main__":
    config = uvicorn.Config("main:app", port=5000, log_level="info", reload=True)
    server = uvicorn.Server(config)
    server.run()