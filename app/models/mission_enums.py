from enum import Enum


class MissionStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REPORTED = "reported"


class PaymentStatus(str, Enum):
    UNPAID = "unpaid"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"