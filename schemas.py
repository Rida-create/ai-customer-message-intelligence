from enum import Enum
from typing import List
from pydantic import BaseModel, Field

class Category(str, Enum):
    BILLING = "Billing"
    TECHNICAL = "Technical Support"
    ACCOUNT = "Account Management"
    SUBSCRIPTION = "Subscription"
    GENERAL = "General Inquiry"

class Priority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"

class Sentiment(str, Enum):
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"
    FRUSTRATED = "Frustrated"

class AnalysisResult(BaseModel):
    category: Category
    intent: str
    priority: Priority
    sentiment: Sentiment
    key_information: List[str]
    suggested_response: str
