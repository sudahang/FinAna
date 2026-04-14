"""Tests for user module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from users.schemas import (
    UserPreference, UserProfile, UserCreate, UserUpdate,
    NotificationTime, MarketType
)
from users.service import UserService


class TestUserPreference:
    def test_default_preferences(self):
        prefs = UserPreference()
        assert prefs.watched_industries == []
        assert prefs.watched_stocks == []
        assert prefs.notification_time == NotificationTime.BOTH
        assert prefs.email_enabled is True
        assert MarketType.ALL in prefs.preferred_markets

    def test_custom_preferences(self):
        prefs = UserPreference(
            watched_industries=["科技", "新能源"],
            watched_stocks=["TSLA", "NVDA"],
            notification_time=NotificationTime.MORNING,
            email_enabled=False
        )
        assert prefs.watched_industries == ["科技", "新能源"]
        assert prefs.watched_stocks == ["TSLA", "NVDA"]
        assert prefs.notification_time == NotificationTime.MORNING
        assert prefs.email_enabled is False

    def test_preferences_model_dump(self):
        prefs = UserPreference(
            watched_industries=["科技"],
            watched_stocks=["TSLA"]
        )
        dump = prefs.model_dump()
        assert dump["watched_industries"] == ["科技"]
        assert dump["watched_stocks"] == ["TSLA"]


class TestUserProfile:
    def test_create_profile(self):
        user = UserProfile(
            user_id="test123",
            email="test@example.com"
        )
        assert user.user_id == "test123"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.created_at is not None

    def test_profile_with_all_fields(self):
        prefs = UserPreference(
            watched_stocks=["TSLA"],
            notification_time=NotificationTime.EVENING
        )
        user = UserProfile(
            user_id="test123",
            email="test@example.com",
            name="Test User",
            preferences=prefs,
            is_active=False
        )
        assert user.name == "Test User"
        assert user.preferences.notification_time == NotificationTime.EVENING
        assert user.is_active is False

    def test_profile_model_dump(self):
        user = UserProfile(
            user_id="test123",
            email="test@example.com",
            name="Test"
        )
        dump = user.model_dump()
        assert dump["user_id"] == "test123"
        assert dump["email"] == "test@example.com"


class TestUserCreate:
    def test_create_user_request(self):
        request = UserCreate(
            email="test@example.com",
            name="Test User"
        )
        assert request.email == "test@example.com"
        assert request.name == "Test User"
        assert request.preferences is None

    def test_create_user_with_preferences(self):
        prefs = UserPreference(watched_stocks=["TSLA"])
        request = UserCreate(
            email="test@example.com",
            preferences=prefs
        )
        assert request.preferences.watched_stocks == ["TSLA"]


class TestUserUpdate:
    def test_update_name_only(self):
        update = UserUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.preferences is None
        assert update.is_active is None

    def test_update_preferences_only(self):
        prefs = UserPreference(watched_stocks=["NVDA"])
        update = UserUpdate(preferences=prefs)
        assert update.preferences.watched_stocks == ["NVDA"]


class TestUserService:
    @pytest.fixture
    def mock_redis(self):
        redis_mock = Mock()
        redis_mock.client = Mock()
        return redis_mock

    def test_generate_user_id(self, mock_redis):
        service = UserService(redis_client=mock_redis)
        user_id = service._generate_user_id("Test@Example.com")
        assert len(user_id) == 16
        assert user_id == service._generate_user_id("test@example.com")

    def test_generate_user_id_unique(self):
        mock_redis = Mock()
        service = UserService(redis_client=mock_redis)
        id1 = service._generate_user_id("user1@example.com")
        id2 = service._generate_user_id("user2@example.com")
        assert id1 != id2

    def test_get_user_key(self, mock_redis):
        service = UserService(redis_client=mock_redis)
        key = service._get_user_key("test123")
        assert key == "user:test123"

    @patch('users.service.get_redis_client')
    def test_create_user(self, mock_get_redis):
        mock_redis = Mock()
        mock_redis.client = Mock()
        mock_get_redis.return_value = mock_redis

        service = UserService(redis_client=mock_redis)
        request = UserCreate(
            email="test@example.com",
            name="Test User",
            preferences=UserPreference(
                watched_stocks=["TSLA", "AAPL"],
                watched_industries=["科技"]
            )
        )

        user = service.create_user(request)

        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.preferences.watched_stocks == ["TSLA", "AAPL"]
        assert user.is_active is True
        assert user.user_id is not None

        mock_redis.client.set.assert_called_once()
        mock_redis.client.hset.assert_called_once()

    @patch('users.service.get_redis_client')
    def test_get_user_found(self, mock_get_redis):
        mock_redis = Mock()
        mock_client = Mock()
        mock_redis.client = mock_client

        test_user = UserProfile(
            user_id="test123",
            email="test@example.com"
        )
        mock_client.get.return_value = test_user.model_dump_json()
        mock_get_redis.return_value = mock_redis

        service = UserService(redis_client=mock_redis)
        result = service.get_user("test123")

        assert result is not None
        assert result.user_id == "test123"

    @patch('users.service.get_redis_client')
    def test_get_user_not_found(self, mock_get_redis):
        mock_redis = Mock()
        mock_redis.client = Mock()
        mock_redis.client.get.return_value = None
        mock_get_redis.return_value = mock_redis

        service = UserService(redis_client=mock_redis)
        result = service.get_user("nonexistent")

        assert result is None

    @patch('users.service.get_redis_client')
    def test_get_user_by_email(self, mock_get_redis):
        mock_redis = Mock()
        mock_client = Mock()
        mock_redis.client = mock_client

        mock_client.hget.return_value = "test123"

        test_user = UserProfile(
            user_id="test123",
            email="test@example.com"
        )
        mock_client.get.return_value = test_user.model_dump_json()
        mock_get_redis.return_value = mock_redis

        service = UserService(redis_client=mock_redis)
        result = service.get_user_by_email("test@example.com")

        assert result is not None
        assert result.email == "test@example.com"

    @patch('users.service.get_redis_client')
    def test_update_user(self, mock_get_redis):
        mock_redis = Mock()
        mock_redis.client = Mock()
        
        test_user = UserProfile(
            user_id="test123",
            email="test@example.com",
            name="Old Name"
        )
        
        mock_redis.client.get.return_value = test_user.model_dump_json()
        mock_get_redis.return_value = mock_redis

        service = UserService(redis_client=mock_redis)
        
        update_req = UserUpdate(name="New Name")
        updated = service.update_user("test123", update_req)

        assert updated.name == "New Name"
        assert updated.updated_at > test_user.updated_at

    @patch('users.service.get_redis_client')
    def test_update_user_not_found(self, mock_get_redis):
        mock_redis = Mock()
        mock_redis.client = Mock()
        mock_redis.client.get.return_value = None
        mock_get_redis.return_value = mock_redis

        service = UserService(redis_client=mock_redis)
        result = service.update_user("nonexistent", UserUpdate(name="test"))

        assert result is None

    @patch('users.service.get_redis_client')
    def test_delete_user(self, mock_get_redis):
        mock_redis = Mock()
        mock_client = Mock()
        mock_redis.client = mock_client

        test_user = UserProfile(
            user_id="test123",
            email="test@example.com"
        )
        mock_client.get.return_value = test_user.model_dump_json()
        mock_get_redis.return_value = mock_redis

        service = UserService(redis_client=mock_redis)
        result = service.delete_user("test123")

        assert result is True
        mock_client.delete.assert_called_once()
        mock_client.hdel.assert_called_once()

    @patch('users.service.get_redis_client')
    def test_delete_user_not_found(self, mock_get_redis):
        mock_redis = Mock()
        mock_redis.client = Mock()
        mock_redis.client.get.return_value = None
        mock_get_redis.return_value = mock_redis

        service = UserService(redis_client=mock_redis)
        result = service.delete_user("nonexistent")

        assert result is False

    @patch('users.service.get_redis_client')
    def test_update_preferences(self, mock_get_redis):
        mock_redis = Mock()
        mock_redis.client = Mock()
        
        test_user = UserProfile(
            user_id="test123",
            email="test@example.com",
            preferences=UserPreference(watched_stocks=["TSLA"])
        )
        
        mock_redis.client.get.return_value = test_user.model_dump_json()
        mock_get_redis.return_value = mock_redis

        service = UserService(redis_client=mock_redis)
        
        updated = service.update_preferences(
            user_id="test123",
            watched_stocks=["TSLA", "NVDA"],
            notification_time=NotificationTime.EVENING
        )

        assert updated.preferences.watched_stocks == ["TSLA", "NVDA"]
        assert updated.preferences.notification_time == NotificationTime.EVENING

    @patch('users.service.get_redis_client')
    def test_update_email_enabled(self, mock_get_redis):
        mock_redis = Mock()
        mock_redis.client = Mock()
        
        test_user = UserProfile(
            user_id="test123",
            email="test@example.com",
            preferences=UserPreference(email_enabled=True)
        )
        
        mock_redis.client.get.return_value = test_user.model_dump_json()
        mock_get_redis.return_value = mock_redis

        service = UserService(redis_client=mock_redis)
        
        updated = service.update_preferences(
            user_id="test123",
            email_enabled=False
        )

        assert updated.preferences.email_enabled is False

    @patch('users.service.get_redis_client')
    def test_list_users(self, mock_get_redis):
        mock_redis = Mock()
        mock_client = Mock()
        mock_redis.client = mock_client

        user1 = UserProfile(user_id="u1", email="user1@example.com")
        user2 = UserProfile(user_id="u2", email="user2@example.com")

        mock_client.hkeys.return_value = ["user1@example.com", "user2@example.com"]
        mock_client.hget.side_effect = ["u1", "u2"]
        mock_client.get.side_effect = [
            user1.model_dump_json(),
            user2.model_dump_json()
        ]
        mock_get_redis.return_value = mock_redis

        service = UserService(redis_client=mock_redis)
        users = service.list_users(limit=10)

        assert len(users) == 2

    @patch('users.service.get_redis_client')
    def test_get_users_by_industry(self, mock_get_redis):
        mock_redis = Mock()
        mock_client = Mock()
        mock_redis.client = mock_client

        user1 = UserProfile(
            user_id="u1",
            email="user1@example.com",
            preferences=UserPreference(watched_industries=["科技"])
        )
        user2 = UserProfile(
            user_id="u2",
            email="user2@example.com",
            preferences=UserPreference(watched_industries=["医疗"])
        )

        mock_client.hkeys.return_value = ["user1@example.com", "user2@example.com"]
        mock_client.hget.side_effect = ["u1", "u2"]
        mock_client.get.side_effect = [
            user1.model_dump_json(),
            user2.model_dump_json()
        ]
        mock_get_redis.return_value = mock_redis

        service = UserService(redis_client=mock_redis)
        users = service.get_users_by_industry("科技")

        assert len(users) == 1
        assert users[0].user_id == "u1"

    @patch('users.service.get_redis_client')
    def test_get_users_by_stock(self, mock_get_redis):
        mock_redis = Mock()
        mock_client = Mock()
        mock_redis.client = mock_client

        user1 = UserProfile(
            user_id="u1",
            email="user1@example.com",
            preferences=UserPreference(watched_stocks=["TSLA"])
        )
        user2 = UserProfile(
            user_id="u2",
            email="user2@example.com",
            preferences=UserPreference(watched_stocks=["AAPL"])
        )

        mock_client.hkeys.return_value = ["user1@example.com", "user2@example.com"]
        mock_client.hget.side_effect = ["u1", "u2"]
        mock_client.get.side_effect = [
            user1.model_dump_json(),
            user2.model_dump_json()
        ]
        mock_get_redis.return_value = mock_redis

        service = UserService(redis_client=mock_redis)
        users = service.get_users_by_stock("TSLA")

        assert len(users) == 1
        assert users[0].user_id == "u1"


class TestEmailService:
    def test_email_service_disabled_without_config(self):
        with patch.dict('os.environ', {}, clear=True):
            from users import email_service
            import importlib
            importlib.reload(email_service)
            service = email_service.EmailService()
            assert service.enabled is False

    def test_email_service_enabled_with_config(self):
        with patch.dict('os.environ', {
            'SMTP_USER': 'test@example.com',
            'SMTP_PASSWORD': 'password123'
        }):
            from users import email_service
            import importlib
            importlib.reload(email_service)
            service = email_service.EmailService()
            assert service.enabled is True
            assert service.smtp_host == "smtp.gmail.com"

    def test_render_html_report_morning(self):
        from users.email_service import EmailService, DailyReport
        
        service = EmailService()
        
        test_user = UserProfile(
            user_id="test123",
            email="test@example.com",
            name="Test User"
        )
        
        report = DailyReport(
            user=test_user,
            stock_summaries=[
                {"symbol": "TSLA", "name": "Tesla", "price": 250.0, "change": 2.5, "news": [{"title": "Test News"}]}
            ],
            industry_summaries=[],
            generated_at=datetime(2026, 4, 13, 8, 0, 0)
        )
        
        html = service.render_html_report(report)
        assert "FinAna" in html
        assert "Test User" in html
        assert "TSLA" in html
        assert "Morning" in html

    def test_render_html_report_evening(self):
        from users.email_service import EmailService, DailyReport
        
        service = EmailService()
        
        test_user = UserProfile(
            user_id="test123",
            email="test@example.com"
        )
        
        report = DailyReport(
            user=test_user,
            stock_summaries=[],
            industry_summaries=[
                {"industry": "科技", "summary": "行业分析", "outlook": "positive"}
            ],
            generated_at=datetime(2026, 4, 13, 20, 0, 0)
        )
        
        html = service.render_html_report(report)
        assert "科技" in html
        assert "科技" in html

    def test_render_html_report_with_industry(self):
        from users.email_service import EmailService, DailyReport
        
        service = EmailService()
        
        test_user = UserProfile(
            user_id="test123",
            email="test@example.com",
            name="张三"
        )
        
        report = DailyReport(
            user=test_user,
            stock_summaries=[],
            industry_summaries=[
                {"industry": "新能源汽车", "summary": "行业增长迅速", "outlook": "positive"},
                {"industry": "人工智能", "summary": "技术创新活跃", "outlook": "neutral"}
            ],
            generated_at=datetime.now()
        )
        
        html = service.render_html_report(report)
        assert "新能源汽车" in html
        assert "人工智能" in html
        assert "📈" in html
        assert "张三" in html


class TestSchedulerService:
    @patch('users.scheduler.CronTrigger')
    @patch('users.scheduler.BackgroundScheduler')
    def test_scheduler_init(self, mock_scheduler_class, mock_cron):
        from users.scheduler import SchedulerService
        
        scheduler = SchedulerService()
        assert scheduler.running is False

    @patch('users.scheduler.BackgroundScheduler')
    def test_scheduler_start_stop(self, mock_scheduler_class):
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler

        from users.scheduler import SchedulerService
        
        scheduler = SchedulerService()
        scheduler.start()
        
        assert scheduler.running is True
        assert mock_scheduler.add_job.call_count == 2
        mock_scheduler.start.assert_called_once()

        scheduler.stop()
        assert scheduler.running is False
        mock_scheduler.shutdown.assert_called_once()


class TestNotificationTime:
    def test_notification_time_enum(self):
        from users.config import config
        assert NotificationTime.MORNING.value == config.notification_time_morning
        assert NotificationTime.EVENING.value == config.notification_time_evening
        assert NotificationTime.BOTH.value == "both"

    def test_notification_time_values(self):
        assert NotificationTime.MORNING == "08:00"
        assert NotificationTime.EVENING == "20:00"


class TestMarketType:
    def test_market_type_enum(self):
        assert MarketType.A_STOCK.value == "a_stock"
        assert MarketType.HK_STOCK.value == "hk_stock"
        assert MarketType.US_STOCK.value == "us_stock"
        assert MarketType.ALL.value == "all"

    def test_market_type_values(self):
        assert MarketType.A_STOCK == "a_stock"
        assert MarketType.HK_STOCK == "hk_stock"


class TestUserResponse:
    def test_user_response_model(self):
        from users.schemas import UserResponse
        
        user = UserProfile(
            user_id="test123",
            email="test@example.com",
            name="Test"
        )
        
        response = UserResponse(
            user_id=user.user_id,
            email=user.email,
            name=user.name,
            preferences=user.preferences,
            created_at=user.created_at,
            updated_at=user.updated_at,
            is_active=user.is_active
        )
        assert response.user_id == "test123"
        assert response.email == "test@example.com"


class TestIntegration:
    @patch('users.service.get_redis_client')
    def test_full_user_lifecycle(self, mock_get_redis):
        mock_redis = Mock()
        mock_client = Mock()
        mock_redis.client = mock_client
        mock_get_redis.return_value = mock_redis

        service = UserService(redis_client=mock_redis)
        
        request = UserCreate(
            email="lifecycle@test.com",
            name="Lifecycle Test",
            preferences=UserPreference(
                watched_stocks=["TSLA", "NVDA"],
                watched_industries=["科技", "新能源"],
                notification_time=NotificationTime.BOTH
            )
        )
        
        created = service.create_user(request)
        assert created.user_id is not None
        
        mock_client.get.return_value = created.model_dump_json()
        
        updated = service.update_preferences(
            user_id=created.user_id,
            watched_stocks=["TSLA", "NVDA", "AAPL"],
            email_enabled=False
        )
        assert len(updated.preferences.watched_stocks) == 3
        assert updated.preferences.email_enabled is False
        
        mock_client.get.return_value = updated.model_dump_json()
        mock_client.get.return_value = created.model_dump_json()
        
        deleted = service.delete_user(created.user_id)
        assert deleted is True