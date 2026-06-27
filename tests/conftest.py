from datetime import UTC, datetime

import pytest

from bot.config import DEFAULT_PLANS
from bot.gateways import FakePaymentGateway, RecordingChatGateway
from bot.repository import (
    InMemoryMemberRepository,
    InMemoryProcessedEventRepository,
)
from bot.service import MembershipService


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def chat() -> RecordingChatGateway:
    return RecordingChatGateway()


@pytest.fixture
def service(chat: RecordingChatGateway) -> MembershipService:
    return MembershipService(
        plans=DEFAULT_PLANS,
        members=InMemoryMemberRepository(),
        processed=InMemoryProcessedEventRepository(),
        chat=chat,
        payments=FakePaymentGateway(),
    )
