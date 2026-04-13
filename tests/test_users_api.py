"""Tests for user API endpoints - unit tests for user service."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from users.schemas import (
    UserProfile, UserCreate, UserUpdate, UserPreference,
    NotificationTime, MarketType
)


class TestUserServiceUnit:
    """Unit tests for user service logic."""

    @pytest.fixture
    def mock_redis(self):
        redis_mock = Mock()
        redis_mock.client = Mock()
        return redis_mock

    def test_create_user_with_preferences(self, mock_redis):
        from users.service import UserService
        
        with patch('users.service.get_redis_client', return_value=mock_redis):
            service = UserService(redis_client=mock_redis)
            
            request = UserCreate(
                email="test@example.com",
                name="Test",
                preferences=UserPreference(
                    watched_stocks=["TSLA", "AAPL"],
                    watched_industries=["科技"],
                    notification_time=NotificationTime.MORNING
                )
            )
            
            user = service.create_user(request)
            
            assert user.email == "test@example.com"
            assert user.preferences.watched_stocks == ["TSLA", "AAPL"]
            assert user.preferences.notification_time == NotificationTime.MORNING
            mock_redis.client.set.assert_called_once()
            mock_redis.client.hset.assert_called_once()

    def test_get_user_found(self, mock_redis):
        from users.service import UserService
        
        test_user = UserProfile(
            user_id="test123",
            email="test@example.com"
        )
        mock_redis.client.get.return_value = test_user.model_dump_json()
        
        with patch('users.service.get_redis_client', return_value=mock_redis):
            service = UserService(redis_client=mock_redis)
            result = service.get_user("test123")
            
            assert result is not None
            assert result.user_id == "test123"

    def test_get_user_not_found(self, mock_redis):
        from users.service import UserService
        
        mock_redis.client.get.return_value = None
        
        with patch('users.service.get_redis_client', return_value=mock_redis):
            service = UserService(redis_client=mock_redis)
            result = service.get_user("nonexistent")
            
            assert result is None

    def test_update_user_name(self, mock_redis):
        from users.service import UserService
        
        test_user = UserProfile(
            user_id="test123",
            email="test@example.com",
            name="Old Name"
        )
        mock_redis.client.get.return_value = test_user.model_dump_json()
        
        with patch('users.service.get_redis_client', return_value=mock_redis):
            service = UserService(redis_client=mock_redis)
            
            update_req = UserUpdate(name="New Name")
            updated = service.update_user("test123", update_req)
            
            assert updated.name == "New Name"

    def test_update_preferences_stocks(self, mock_redis):
        from users.service import UserService
        
        test_user = UserProfile(
            user_id="test123",
            email="test@example.com",
            preferences=UserPreference(watched_stocks=["TSLA"])
        )
        mock_redis.client.get.return_value = test_user.model_dump_json()
        
        with patch('users.service.get_redis_client', return_value=mock_redis):
            service = UserService(redis_client=mock_redis)
            
            updated = service.update_preferences(
                user_id="test123",
                watched_stocks=["TSLA", "NVDA", "AAPL"]
            )
            
            assert len(updated.preferences.watched_stocks) == 3

    def test_update_email_enabled(self, mock_redis):
        from users.service import UserService
        
        test_user = UserProfile(
            user_id="test123",
            email="test@example.com",
            preferences=UserPreference(email_enabled=True)
        )
        mock_redis.client.get.return_value = test_user.model_dump_json()
        
        with patch('users.service.get_redis_client', return_value=mock_redis):
            service = UserService(redis_client=mock_redis)
            
            updated = service.update_preferences(
                user_id="test123",
                email_enabled=False
            )
            
            assert updated.preferences.email_enabled is False

    def test_delete_user(self, mock_redis):
        from users.service import UserService
        
        test_user = UserProfile(
            user_id="test123",
            email="test@example.com"
        )
        mock_redis.client.get.return_value = test_user.model_dump_json()
        
        with patch('users.service.get_redis_client', return_value=mock_redis):
            service = UserService(redis_client=mock_redis)
            result = service.delete_user("test123")
            
            assert result is True
            mock_redis.client.delete.assert_called_once()

    def test_list_users(self, mock_redis):
        from users.service import UserService
        
        users = [
            UserProfile(user_id="u1", email="user1@example.com"),
            UserProfile(user_id="u2", email="user2@example.com")
        ]
        
        mock_redis.client.hkeys.return_value = ["user1@example.com", "user2@example.com"]
        mock_redis.client.hget.side_effect = ["u1", "u2"]
        mock_redis.client.get.side_effect = [u.model_dump_json() for u in users]
        
        with patch('users.service.get_redis_client', return_value=mock_redis):
            service = UserService(redis_client=mock_redis)
            result = service.list_users(limit=10)
            
            assert len(result) == 2

    def test_get_users_by_industry(self, mock_redis):
        from users.service import UserService
        
        users = [
            UserProfile(
                user_id="u1",
                email="user1@example.com",
                preferences=UserPreference(watched_industries=["科技"])
            ),
            UserProfile(
                user_id="u2",
                email="user2@example.com",
                preferences=UserPreference(watched_industries=["医疗"])
            )
        ]
        
        mock_redis.client.hkeys.return_value = ["user1@example.com", "user2@example.com"]
        mock_redis.client.hget.side_effect = ["u1", "u2"]
        mock_redis.client.get.side_effect = [u.model_dump_json() for u in users]
        
        with patch('users.service.get_redis_client', return_value=mock_redis):
            service = UserService(redis_client=mock_redis)
            result = service.get_users_by_industry("科技")
            
            assert len(result) == 1
            assert result[0].user_id == "u1"

    def test_get_users_by_stock(self, mock_redis):
        from users.service import UserService
        
        users = [
            UserProfile(
                user_id="u1",
                email="user1@example.com",
                preferences=UserPreference(watched_stocks=["TSLA"])
            ),
            UserProfile(
                user_id="u2",
                email="user2@example.com",
                preferences=UserPreference(watched_stocks=["AAPL"])
            )
        ]
        
        mock_redis.client.hkeys.return_value = ["user1@example.com", "user2@example.com"]
        mock_redis.client.hget.side_effect = ["u1", "u2"]
        mock_redis.client.get.side_effect = [u.model_dump_json() for u in users]
        
        with patch('users.service.get_redis_client', return_value=mock_redis):
            service = UserService(redis_client=mock_redis)
            result = service.get_users_by_stock("TSLA")
            
            assert len(result) == 1
            assert result[0].user_id == "u1"


class TestEmailServiceUnit:
    """Unit tests for email service logic."""

    def test_email_service_init_disabled(self):
        with patch.dict('os.environ', {}, clear=True):
            from users import email_service
            import importlib
            importlib.reload(email_service)
            service = email_service.EmailService()
            assert service.enabled is False

    def test_email_service_init_enabled(self):
        with patch.dict('os.environ', {
            'SMTP_USER': 'test@example.com',
            'SMTP_PASSWORD': 'test123'
        }):
            from users import email_service
            import importlib
            importlib.reload(email_service)
            service = email_service.EmailService()
            assert service.enabled is True
            assert service.smtp_host == "smtp.gmail.com"

    def test_render_html_report_stocks(self):
        from users.email_service import EmailService, DailyReport
        from datetime import datetime
        
        service = EmailService()
        
        test_user = UserProfile(
            user_id="test123",
            email="test@example.com",
            name="Test User"
        )
        
        report = DailyReport(
            user=test_user,
            stock_summaries=[
                {"symbol": "TSLA", "name": "Tesla", "price": 250.0, "change": 2.5, "news": []},
                {"symbol": "NVDA", "name": "NVIDIA", "price": 500.0, "change": -1.2, "news": []}
            ],
            industry_summaries=[],
            generated_at=datetime(2026, 4, 13, 8, 0, 0)
        )
        
        html = service.render_html_report(report)
        
        assert "TSLA" in html
        assert "NVDA" in html
        assert "Test User" in html
        assert "250" in html

    def test_render_html_report_industries(self):
        from users.email_service import EmailService, DailyReport
        from datetime import datetime
        
        service = EmailService()
        
        test_user = UserProfile(
            user_id="test123",
            email="test@example.com"
        )
        
        report = DailyReport(
            user=test_user,
            stock_summaries=[],
            industry_summaries=[
                {"industry": "科技", "summary": "技术创新活跃", "outlook": "positive"},
                {"industry": "新能源", "summary": "政策支持力度大", "outlook": "positive"}
            ],
            generated_at=datetime.now()
        )
        
        html = service.render_html_report(report)
        
        assert "科技" in html
        assert "新能源" in html
        assert "📈" in html


class TestSchedulerServiceUnit:
    """Unit tests for scheduler service logic."""

    @patch('users.scheduler.BackgroundScheduler')
    def test_scheduler_add_jobs(self, mock_scheduler_class):
        from users.scheduler import SchedulerService
        
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        scheduler = SchedulerService()
        scheduler.start()
        
        assert mock_scheduler.add_job.call_count == 2
        mock_scheduler.start.assert_called_once()
        
        scheduler.stop()
        mock_scheduler.shutdown.assert_called_once()

    @patch('users.scheduler.BackgroundScheduler')
    def test_scheduler_get_jobs(self, mock_scheduler_class):
        from users.scheduler import SchedulerService
        
        mock_scheduler = Mock()
        mock_scheduler.get_jobs.return_value = [
            Mock(id="job1", name="Job 1", next_run_time=None)
        ]
        mock_scheduler_class.return_value = mock_scheduler
        
        scheduler = SchedulerService()
        jobs = scheduler.get_jobs()
        
        assert len(jobs) == 1


class TestUserSchemas:
    """Unit tests for user schemas."""

    def test_user_preference_default(self):
        prefs = UserPreference()
        assert prefs.watched_industries == []
        assert prefs.watched_stocks == []
        assert prefs.email_enabled is True

    def test_user_preference_custom(self):
        prefs = UserPreference(
            watched_industries=["科技", "医疗"],
            watched_stocks=["TSLA", "NVDA"],
            notification_time=NotificationTime.EVENING,
            email_enabled=False
        )
        assert prefs.watched_industries == ["科技", "医疗"]
        assert prefs.notification_time == NotificationTime.EVENING

    def test_user_profile_create(self):
        user = UserProfile(
            user_id="test123",
            email="test@example.com"
        )
        assert user.user_id == "test123"
        assert user.is_active is True
        assert user.created_at is not None

    def test_user_create_request(self):
        request = UserCreate(email="test@example.com", name="Test")
        assert request.email == "test@example.com"
        assert request.name == "Test"

    def test_user_update_request(self):
        update = UserUpdate(name="New Name", is_active=False)
        assert update.name == "New Name"
        assert update.is_active is False

    def test_notification_time_enum(self):
        assert NotificationTime.MORNING.value == "08:00"
        assert NotificationTime.EVENING.value == "20:00"
        assert NotificationTime.BOTH.value == "both"

    def test_market_type_enum(self):
        assert MarketType.A_STOCK.value == "a_stock"
        assert MarketType.HK_STOCK.value == "hk_stock"
        assert MarketType.US_STOCK.value == "us_stock"
        assert MarketType.ALL.value == "all"