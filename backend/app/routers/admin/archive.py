"""Read-only access to the official archive extractions and the content taxonomy."""
from fastapi import APIRouter, Depends, HTTPException

from ... import models as m
from ...security import admin_user

router = APIRouter(tags=["acervo"])


@router.get('/archive')
def archive_inventory(year: int | None = None, application: str | None = None, user: m.User = Depends(admin_user)):
    from ...archive import inventory
    return inventory(year,application)


@router.get('/archive/questions')
def archive_questions(year: int, application: str | None = None, number: int | None = None,
                      offset: int = 0, limit: int = 25, user: m.User = Depends(admin_user)):
    from ...archive import questions
    if not 1998<=year<=2100 or not 0<=offset or not 1<=limit<=100 or (number is not None and not 1<=number<=1000):
        raise HTTPException(422,'Filtros do acervo inválidos.')
    return questions(year,application,number,offset,limit)


@router.get('/archive/questions/{occurrence_id}')
def archive_question(occurrence_id: str, user: m.User = Depends(admin_user)):
    from ...archive import detail
    result=detail(occurrence_id)
    if not result:raise HTTPException(404,'Extração não encontrada neste ambiente; sincronize o banco do acervo.')
    return result


@router.get('/taxonomy')
def content_taxonomy(user: m.User = Depends(admin_user)):
    from ...taxonomy import taxonomy
    return taxonomy()
