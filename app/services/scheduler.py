from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.schedule import Schedule, ScheduleStatus
from app.models.notification import Notification, NotificationSourceType

scheduler = BackgroundScheduler()


def check_due_notifications():
    """알림 시간이 도래한 일정을 찾아 notifications에 추가."""
    db: Session = SessionLocal()
    try:
        now = datetime.now()
        due_schedules = (
            db.query(Schedule)
            .filter(
                Schedule.notify_at.isnot(None),
                Schedule.notify_at <= now,
                Schedule.status == ScheduleStatus.pending,
            )
            .all()
        )

        for schedule in due_schedules:
            already_notified = (
                db.query(Notification)
                .filter(
                    Notification.source_type == NotificationSourceType.schedule,
                    Notification.source_id == schedule.id,
                    Notification.message.like("%알림%"),
                )
                .first()
            )
            if already_notified:
                continue

            notification = Notification(
                user_id=schedule.user_id,
                source_type=NotificationSourceType.schedule,
                source_id=schedule.id,
                message=f"곧 일정이 시작돼요: {schedule.title} ({schedule.start_at.strftime('%H:%M')})",
            )
            db.add(notification)

        db.commit()
    finally:
        db.close()


def check_overdue_followups():
    """일정 시간이 지났는데 상태 미확인(pending)인 건에 대해 follow-up 알림 생성."""
    db: Session = SessionLocal()
    try:
        now = datetime.now()
        grace_period = now - timedelta(minutes=10)  # 시작 후 10분 지나야 follow-up

        overdue_schedules = (
            db.query(Schedule)
            .filter(
                Schedule.start_at <= grace_period,
                Schedule.status == ScheduleStatus.pending,
            )
            .all()
        )

        for schedule in overdue_schedules:
            already_followed_up = (
                db.query(Notification)
                .filter(
                    Notification.source_type == NotificationSourceType.schedule,
                    Notification.source_id == schedule.id,
                    Notification.message.like("%어떻게 됐어요%"),
                )
                .first()
            )
            if already_followed_up:
                continue

            notification = Notification(
                user_id=schedule.user_id,
                source_type=NotificationSourceType.schedule,
                source_id=schedule.id,
                message=f"'{schedule.title}' 일정 어떻게 됐어요? 완료 또는 취소로 표시해주세요.",
            )
            db.add(notification)

        db.commit()
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(check_due_notifications, "interval", minutes=1, id="check_due_notifications")
    scheduler.add_job(check_overdue_followups, "interval", minutes=1, id="check_overdue_followups")
    scheduler.start()


def stop_scheduler():
    scheduler.shutdown(wait=False)