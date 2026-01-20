from datetime import datetime, timedelta

from database import Booking, DbSession
from sqlmodel import select


def check_availability(db: DbSession, date_str: str) -> str:
    """
    Check available time slots for a given date.

    Args:
        db: Database session
        date_str: Date in format YYYY-MM-DD

    Returns:
        String describing available slots
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Get all bookings for the target date
        bookings = db.exec(
            select(Booking).where(
                Booking.start_time
                >= datetime.combine(target_date, datetime.min.time()),
                Booking.start_time
                < datetime.combine(
                    target_date + timedelta(days=1), datetime.min.time()
                ),
            )
        ).all()

        # All possible 1 hour slots
        all_hours = list(range(9, 17))

        # Mark booked hours
        booked_hours = {booking.start_time.hour for booking in bookings}

        # Available = all hours - booked hours
        available_hours = [h for h in all_hours if h not in booked_hours]

        if not available_hours:
            return f"No slots available on {date_str}. All hours from 9 AM to 5 PM are booked."

        # Format available hours
        available_slots = [f"{h}:00-{h + 1}:00" for h in available_hours]
        return f"Available slots on {date_str}: {', '.join(available_slots)}"

    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD format."
    except Exception as e:
        return f"Error checking availability: {str(e)}"


def book_slot(db: DbSession, user_name: str, date_str: str, hour: int) -> str:
    """
    Book a time slot for a user.

    Args:
        db: Database session
        user_name: Name of the user booking
        date_str: Date in format YYYY-MM-DD
        hour: Starting hour (9-16)

    Returns:
        Success or error message
    """
    try:
        # Validate inputs
        if hour < 9 or hour > 16:
            return "Invalid hour. Please choose between 9 AM (9) and 4 PM (16)."

        # Parse date
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        start_time = datetime.combine(
            target_date, datetime.min.time().replace(hour=hour)
        )

        # Check for already booked bookings
        booking = db.exec(
            select(Booking).where(Booking.start_time == start_time)
        ).first()

        if booking:
            return f"Time slot conflicts with existing booking at {booking.start_time.strftime('%H:%M')}."

        # Create new booking
        new_booking = Booking(
            user_name=user_name,
            start_time=start_time,
        )

        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)

        return f"✓ Booking confirmed! Confirmation ID: {new_booking.id}. {user_name} booked from {hour}:00 to {hour + 1}:00 on {date_str}."

    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD format."
    except Exception as e:
        db.rollback()
        return f"Error booking slot: {str(e)}"
