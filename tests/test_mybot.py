import pytest
from discord.ext import commands
from src.mybot import bot, warn_user, ensure_muted_role, log_action

@pytest.fixture
def guild_mock():
    class GuildMock:
        id = 123456
        name = "Test Guild"
        def __init__(self):
            self.roles = []
            self.text_channels = []
    
    return GuildMock()

@pytest.fixture
def member_mock(guild_mock):
    class MemberMock:
        id = 78910
        display_name = "Test User"
        guild = guild_mock
        roles = []

        async def add_roles(self, role):
            self.roles.append(role)

        async def remove_roles(self, role):
            self.roles.remove(role)

    return MemberMock()

@pytest.fixture
def log_channel_mock(guild_mock):
    class LogChannelMock:
        async def send(self, embed):
            pass

    guild_mock.text_channels.append(LogChannelMock())
    return guild_mock.text_channels[0]

@pytest.mark.asyncio
async def test_warn_user(guild_mock, member_mock, log_channel_mock):
    await warn_user(guild_mock, member_mock, None, "Test warning")
    # Add assertions to verify the warning was logged correctly

@pytest.mark.asyncio
async def test_ensure_muted_role(guild_mock):
    role = await ensure_muted_role(guild_mock)
    assert role is not None
    assert role.name == "Muted"

@pytest.mark.asyncio
async def test_log_action(guild_mock, log_channel_mock):
    await log_action(guild_mock, "Test Title", "Test Description")
