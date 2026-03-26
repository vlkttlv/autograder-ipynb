from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.assignment.services.dao_service import AssignmentDAO, DisciplinesDAO
from app.auth.dependencies import check_tutor_role, get_current_user
from app.db import get_db_session


router = APIRouter(prefix="/disciplines", tags=["Disciplines"])


@router.post("/",
             dependencies=[Depends(check_tutor_role)])
async def create_discipline(
    name: str,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Добавление новой дисциплины"""
    new_discipline_id = await DisciplinesDAO.add(
                session=session, name=name, teacher_id=current_user.id
            )
    
    return {
        "new_discipline_name": name,
        "id": new_discipline_id
    }


@router.get("/",
            dependencies=[Depends(check_tutor_role)])
async def get_disciplines(
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user)
):
    """Получение списка дисциплин преподавателя"""
    return await DisciplinesDAO.find_all(session=session, teacher_id=current_user.id)


@router.patch("/{discipline_id}",
              dependencies=[Depends(check_tutor_role)])
async def update_discipline(
    discipline_id: int,
    name: str,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user)
):
    discipline = await DisciplinesDAO.find_one_or_none(
        session=session, id=discipline_id, teacher_id=current_user.id
    )
    if not discipline:
        raise HTTPException(
                status_code=400,
                detail="Студент не может изменять дисциплину"
            )
    await DisciplinesDAO.update(model_id=discipline_id, session=session, name=name)
    


@router.delete("/{discipline_id}",
               dependencies=[Depends(check_tutor_role)])
async def delete_discipline(
    discipline_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user)
):
    discipline = await DisciplinesDAO.find_one_or_none(
        session=session, id=discipline_id, teacher_id=current_user.id
    )
    if not discipline:
        raise HTTPException(
                status_code=400,
                detail="Студент не может изменять дисциплину"
            )
    
    assignments = await AssignmentDAO.find_all(session=session, discipline_id=discipline_id)
    if assignments:
        raise HTTPException(
                status_code=400,
                detail="По данной дисциплине есть задания"
            )
    
    await DisciplinesDAO.delete(session=session, id=discipline_id, teacher_id=current_user.id)
