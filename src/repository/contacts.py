from typing import List, Optional
from datetime import datetime, timedelta, date

from sqlalchemy import and_, or_, select, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import Contact, Group, User
from src.schemas import ContactModel, ContactUpdate, ContactIsActiveUpdate


class ContactRepository:
    def __init__(self, session: AsyncSession):
        self.db = session

    async def get_contacts(
        self, skip: int, limit: int, query: str | None, user: User
    ) -> List[Contact]:
        # selectinload - to get groups connected with this contact
        # skip and limit - pagination realization
        query = query.lower() if query is not None else ""
        stmt = (
            select(Contact)
            .filter_by(user=user)
            .options(selectinload(Contact.groups))
            .filter(
                (Contact.name.ilike(f"%{query}%"))
                | (Contact.surname.ilike(f"%{query}%"))
                | (Contact.email.ilike(f"%{query}%"))
            )
            .offset(skip)
            .limit(limit)
        )
        contacts = await self.db.execute(stmt)
        return contacts.scalars().all()

    async def get_contact_by_id(self, contact_id: int, user: User) -> Contact | None:
        stmt = (
            select(Contact)
            .options(selectinload(Contact.groups))
            .filter_by(id=contact_id, user=user)
        )
        contact = await self.db.execute(stmt)
        return contact.scalar_one_or_none()

    async def create_contact(
        self, body: ContactModel, groups: List[Group], user: User
    ) -> Contact:
        contact = Contact(
            **body.model_dump(exclude={"groups"}, exclude_unset=True),
            groups=groups,
            user=user,
        )
        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)
        return await self.get_contact_by_id(contact.id, user)

    async def remove_contact(self, contact_id: int, user: User) -> Contact | None:
        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            await self.db.delete(contact)
            await self.db.commit()
        return contact

    async def update_contact(
        self, contact_id: int, body: ContactUpdate, groups: List[Group], user: User
    ) -> Contact | None:
        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            for key, value in body.dict(exclude_unset=True, exclude={"groups"}).items():
                setattr(contact, key, value)

            if groups is not None:
                contact.groups = groups

            await self.db.commit()
            await self.db.refresh(contact)

        return contact

    async def update_contact_is_active(
        self, contact_id: int, body: ContactIsActiveUpdate, user: User
    ) -> Contact | None:
        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            contact.is_active = body.is_active
            await self.db.commit()
            await self.db.refresh(contact)

        return contact

    async def get_contacts_by_birthday(
        self, from_date: date | None, to_date: date | None, user: User
    ) -> List[Contact]:
        # Default range: next 7 days
        from_date = from_date or datetime.now().date()
        to_date = to_date or (from_date + timedelta(days=7))

        print("From", from_date, "To", to_date)

        # extract month and day for the given range
        from_month, from_day = from_date.month, from_date.day
        to_month, to_day = to_date.month, to_date.day
        print("from_month", from_month, "from_day", from_day)
        print("to_month", to_month, "to_day", to_day)
        # construct the SQL query
        if from_month == to_month:  # Same month case
            stmt = (
                select(Contact)
                .filter_by(user=user)
                .options(selectinload(Contact.groups))
                .filter(
                    extract("month", Contact.birthday) == from_month,
                    extract("day", Contact.birthday) >= from_day,
                    extract("day", Contact.birthday) < to_day,
                )
            )
        else:  # cross-month case (e.g., December -> January)
            stmt = (
                select(Contact)
                .filter_by(user=user)
                .options(selectinload(Contact.groups))
                .filter(
                    or_(
                        # remaining days in the starting month
                        and_(
                            extract("month", Contact.birthday) == from_month,
                            extract("day", Contact.birthday) >= from_day,
                        ),
                        # days in the next month
                        and_(
                            extract("month", Contact.birthday) == to_month,
                            extract("day", Contact.birthday) < to_day,
                        ),
                    )
                )
            )

        contacts = await self.db.execute(stmt)
        return contacts.scalars().all()
