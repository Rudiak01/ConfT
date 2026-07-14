from sqlalchemy import select
from backend.db.models import TableUser
from backend.db import SessionLocal


class Auth:
    """
    Auth class
    """

    def __init__(self):
        """
        Constructor of Auth class
        """

    def get_user(self, login):
        """
        get user data from login
        return the userid, login, password and role from the login
        """
        stmt = select(
            TableUser.id, TableUser.login, TableUser.password, TableUser.role
        ).where(TableUser.login == login)
        with SessionLocal() as session:
            res = session.execute(stmt)
            session.commit()
        return res.first()

    def get_user_for_update(self, rowid):
        """
        get user data from token
        return the password from the token rowid
        """
        stmt = select(TableUser.password).where(TableUser.id == rowid)
        with SessionLocal() as session:
            res = session.execute(stmt)
            session.commit()
        return res.scalar()

    def pass_update_date(self, operator_id):
        """
        get user last password change date
        """
        with SessionLocal() as session:
            return session.scalar(
                select(TableUser.last_password_change).where(
                    TableUser.id == operator_id
                )
            )
