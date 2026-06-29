from sqlalchemy import select, update
from sqlalchemy.dialects.mysql import insert
from backend.db.models import TableUser
from backend.db import SessionLocal
from datetime import datetime


class User:
    """
    User class
    """

    def __init__(self):
        """
        Constructor of User class
        """

    def get_admin_account(self):
        """
        return True if admin account exist
        """
        stmt = select(TableUser).where(TableUser.role == "admin")
        with SessionLocal() as session:
            res = session.execute(stmt).first()
        if res is None:
            return False
        else:
            return True

    def get_users(self):
        """
        Return list of users
        """
        with SessionLocal() as session:
            res = (
                session.execute(
                    select(
                        TableUser.id,
                        TableUser.first_name,
                        TableUser.last_name,
                        TableUser.email,
                        TableUser.login,
                        TableUser.role,
                        TableUser.last_connection,
                    )
                )
                .mappings()
                .all()
            )
        return res

    def add_user(self, data):
        """
        Add user to users table
        Return user id or None
        """
        with SessionLocal() as session:
            user = session.scalar(insert(TableUser).returning(TableUser.id), data)
            session.commit()
        return user

    def get_user(self, rowid):
        """
        Get user to users table by rowid
        Return data or None
        """
        stmt = select(TableUser).where(TableUser.id == rowid)
        with SessionLocal() as session:
            res = session.scalar(stmt)
            return res

    def update_user(self, data, operator_id):
        """
        Update user data into users table by rowid
        Return True or False
        """

        update_data = {}

        fields = ["first_name", "last_name", "email", "login", "password"]

        for field in fields:
            if field in data:
                update_data[field] = data[field]

        if not update_data:
            return False

        stmt = (
            update(TableUser).where(TableUser.id == operator_id).values(**update_data)
        )

        with SessionLocal() as session:
            session.execute(stmt)
            session.commit()
            return session.scalar(
                select(TableUser.first_name).where(TableUser.id == operator_id)
            )

    def update_user_role(self, user_id, role):
        """
        Update user data into users table by rowid
        Return True or False
        """
        stmt = update(TableUser).where(TableUser.id == user_id).values(role=role)
        with SessionLocal() as session:
            session.execute(stmt)
            session.commit()
        return True

    def user_theme(self, operator_id):
        """
        return the theme settings of the operator_id
        """
        stmt = select(
            TableUser.theme,
            TableUser.color,
            TableUser.background,
            TableUser.background_style,
            TableUser.background_color,
        ).where(TableUser.id == operator_id)
        with SessionLocal() as session:
            return session.execute(stmt).first()

    def update_theme(self, data, operator_id):
        """
        update the user theme
        """
        with SessionLocal() as session:
            session.execute(
                update(TableUser).values(data).where(TableUser.id == operator_id)
            )
            session.commit()
        return True

    def update_user_password_change_date(self, operator_id):
        """
        change the date when the user password has last been changed
        """
        with SessionLocal() as session:
            session.execute(
                update(TableUser)
                .values(last_password_change=datetime.now())
                .where(TableUser.id == operator_id)
            )
            session.commit()
        return True

    def update_last_connection(self, operator_id):
        """
        Update the field 'last_connection' to now
        """
        with SessionLocal() as session:
            session.execute(
                update(TableUser)
                .where(TableUser.id == operator_id)
                .values(last_connection=datetime.now())
            )
            session.commit()
