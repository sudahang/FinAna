"""Email notification service for sending daily reports to users."""

import os
import logging
import smtplib
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass

from users.config import config
from users.schemas import UserProfile, NotificationTime
from users.service import get_user_service
from workflows.ai_research_workflow import AIResearchWorkflow
from skills.stock_info.stock_info import get_stock_quote, get_stock_news

logger = logging.getLogger(__name__)


@dataclass
class DailyReport:
    """Daily report data for a user."""
    user: UserProfile
    stock_summaries: List[dict]
    industry_summaries: List[dict]
    generated_at: datetime


class EmailService:
    """Service for sending email notifications to users."""

    def __init__(self):
        """Initialize email service with SMTP config from env."""
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_name = os.getenv("SMTP_FROM_NAME", config.app_name)
        self.enabled = bool(self.smtp_user and self.smtp_password)

        if not self.enabled:
            logger.warning("Email service not configured - SMTP credentials not set")

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send an email to the specified address."""
        if not self.enabled:
            logger.warning(f"Email service disabled - skipping send to {to_email}")
            return False

        trace_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        logger.info(f"[TRACE={trace_id}] Sending email to {to_email}: {subject}")

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self.from_name} <{self.smtp_user}>"
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(text_content or html_content, "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, to_email, msg.as_string())

            logger.info(f"[TRACE={trace_id}] Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"[TRACE={trace_id}] Failed to send email to {to_email}: {e}")
            return False

    def generate_daily_report(self, user: UserProfile) -> DailyReport:
        """Generate daily report for user's watched stocks and industries."""
        trace_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        logger.info(f"[TRACE={trace_id}] Generating daily report for user {user.user_id}")

        stock_summaries = []
        industry_summaries = []

        workflow = AIResearchWorkflow()

        for symbol in user.preferences.watched_stocks[:5]:
            try:
                quote = get_stock_quote(symbol)
                news = get_stock_news(symbol, limit=3)

                stock_summaries.append({
                    "symbol": symbol,
                    "name": quote.get("name", symbol) if quote else symbol,
                    "price": quote.get("current_price", "N/A") if quote else "N/A",
                    "change": quote.get("change_percent", 0) if quote else 0,
                    "news": [
                        {"title": n.get("title", ""), "summary": n.get("summary", "")[:100]}
                        for n in news[:2]
                    ]
                })

                query = f"分析{symbol}股票"
                report = workflow.execute(query)
                stock_summaries[-1]["analysis"] = report.investment_thesis[:200] if report else ""

            except Exception as e:
                logger.warning(f"[TRACE={trace_id}] Failed to get data for {symbol}: {e}")

        for industry in user.preferences.watched_industries[:3]:
            try:
                query = f"分析{industry}行业趋势"
                report = workflow.execute(query)

                industry_summaries.append({
                    "industry": industry,
                    "summary": report.industry_analysis.summary if report and report.industry_analysis else "",
                    "outlook": report.industry_analysis.outlook if report and report.industry_analysis else "neutral"
                })
            except Exception as e:
                logger.warning(f"[TRACE={trace_id}] Failed to analyze industry {industry}: {e}")

        return DailyReport(
            user=user,
            stock_summaries=stock_summaries,
            industry_summaries=industry_summaries,
            generated_at=datetime.now()
        )

    def render_html_report(self, report: DailyReport) -> str:
        """Render daily report as HTML."""
        user = report.user

        stocks_html = ""
        if report.stock_summaries:
            stocks_html = """
            <h2>Stocks</h2>
            <table style="width:100%; border-collapse:collapse; margin-bottom:20px;">
            <tr style="background:#f5f5f5;">
                <th style="padding:10px; text-align:left;">Stock</th>
                <th style="padding:10px; text-align:right;">Price</th>
                <th style="padding:10px; text-align:right;">Change</th>
                <th style="padding:10px; text-align:left;">Latest News</th>
            </tr>
            """
            for stock in report.stock_summaries:
                change_color = "green" if stock.get("change", 0) >= 0 else "red"
                change_str = f"{stock.get('change', 0):.2f}%"
                news_title = stock["news"][0]["title"] if stock["news"] else "No news"
                stocks_html += f"""
                <tr style="border-bottom:1px solid #eee;">
                    <td style="padding:10px;">
                        <strong>{stock.get('name', stock['symbol'])}</strong><br>
                        <small style="color:#888;">{stock['symbol']}</small>
                    </td>
                    <td style="padding:10px; text-align:right;">{stock.get('price', 'N/A')}</td>
                    <td style="padding:10px; text-align:right; color:{change_color};">{change_str}</td>
                    <td style="padding:10px; font-size:12px;">{news_title[:50]}...</td>
                </tr>
                """
            stocks_html += "</table>"

        industries_html = ""
        if report.industry_summaries:
            industries_html = """
            <h2>Sectors</h2>
            """
            for ind in report.industry_summaries:
                outlook_emoji = "📈" if ind.get("outlook") == "positive" else "📉" if ind.get("outlook") == "negative" else "➡️"
                industries_html += f"""
                <div style="margin-bottom:15px; padding:10px; background:#f9f9f9; border-radius:5px;">
                    <strong>{ind['industry']}</strong> {outlook_emoji}<br>
                    <small>{ind.get('summary', 'No analysis')[:150]}...</small>
                </div>
                """

        now_hour = datetime.now().hour
        morning_hour = int(config.notification_time_morning.split(":")[0])
        time_label = "Morning" if now_hour < morning_hour else "Evening"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height:1.6; color:#333; }}
                .container {{ max-width:600px; margin:0 auto; padding:20px; }}
                .header {{ background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white; padding:20px; border-radius:10px; margin-bottom:20px; }}
                .footer {{ text-align:center; margin-top:30px; color:#888; font-size:12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 {config.app_name} {time_label} Report</h1>
                    <p>{report.generated_at.strftime('%Y-%m-%d %H:%M')}</p>
                </div>

                <p>Hello{ f' {user.name}' if user.name else '' }, here is your daily update:</p>

                {stocks_html}

                {industries_html}

                <div class="footer">
                    <p>This email was sent by {config.app_name}. To update preferences, log in to your account.</p>
                    <p>© 2026 {config.app_name}</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def send_daily_report(self, user: UserProfile) -> bool:
        """Generate and send daily report to user."""
        if not user.preferences.email_enabled:
            logger.info(f"User {user.user_id} has email disabled, skipping")
            return False

        report = self.generate_daily_report(user)

        html_content = self.render_html_report(report)
        subject = f"📊 {config.app_name} Daily Report {datetime.now().strftime('%Y-%m-%d')}"

        return self.send_email(
            to_email=user.email,
            subject=subject,
            html_content=html_content
        )

    def send_reports_for_time(self, notification_time: NotificationTime) -> dict:
        """Send daily reports to all users with specified notification time."""
        logger.info(f"Sending reports for notification time: {notification_time}")

        user_service = get_user_service()
        all_users = user_service.list_users(limit=1000)

        results = {"success": 0, "failed": 0, "skipped": 0}

        for user in all_users:
            if not user.is_active:
                results["skipped"] += 1
                continue

            if not user.preferences.email_enabled:
                results["skipped"] += 1
                continue

            pref_time = user.preferences.notification_time
            if notification_time == NotificationTime.MORNING and pref_time not in [NotificationTime.MORNING, NotificationTime.BOTH]:
                results["skipped"] += 1
                continue
            if notification_time == NotificationTime.EVENING and pref_time not in [NotificationTime.EVENING, NotificationTime.BOTH]:
                results["skipped"] += 1
                continue

            if self.send_daily_report(user):
                results["success"] += 1
            else:
                results["failed"] += 1

        logger.info(f"Send reports results: {results}")
        return results


_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get singleton email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service