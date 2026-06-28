import json
import datetime
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import (
    Notification, NotificationPreference, EmployeeNotification, Employee
)

class NotificationCenter:
    @staticmethod
    async def send_notification(
        db: AsyncSession,
        business_id: str,
        employee_id: Optional[str],
        source: str,
        message: str
    ) -> Notification:
        # Default channels if no specific preference is set
        channels = ["dashboard", "whatsapp"]

        if employee_id:
            # 1. Fetch preferences for this source
            pref_query = select(NotificationPreference).where(
                NotificationPreference.employee_id == employee_id,
                NotificationPreference.notification_source == source
            )
            pref_res = await db.execute(pref_query)
            preference = pref_res.scalar_one_or_none()

            if preference:
                try:
                    channels = json.loads(preference.channels_json)
                except Exception:
                    channels = ["dashboard"]

        sent_channels = []

        # 2. Process Dashboard channel (log inside Notification table)
        if "dashboard" in channels:
            sent_channels.append("dashboard")

        # 3. Process WhatsApp channel
        if "whatsapp" in channels and employee_id:
            # Look up employee phone
            emp_query = select(Employee).where(Employee.id == employee_id)
            emp_res = await db.execute(emp_query)
            emp = emp_res.scalar_one_or_none()

            if emp and emp.phone:
                from src.services.dev_workspace import apply_dev_workspace_branding
                branded_msg = await apply_dev_workspace_branding(db, business_id, message)

                # Log in EmployeeNotification table as simulation of WhatsApp dispatch
                whats_notif = EmployeeNotification(
                    employee_id=employee_id,
                    message=branded_msg,
                    channel="WhatsApp",
                    status="SENT"
                )
                db.add(whats_notif)
                sent_channels.append("whatsapp")

        # 4. Save notification log
        notif = Notification(
            business_id=business_id,
            employee_id=employee_id,
            source=source,
            message=message,
            read_status="UNREAD",
            channels_json=json.dumps(channels),
            sent_channels_json=json.dumps(sent_channels),
            created_at=datetime.datetime.utcnow()
        )
        db.add(notif)
        await db.flush()

        return notif
