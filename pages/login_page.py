"""LoginPage — encapsulates the login screen, including optional 2FA."""
from __future__ import annotations

from playwright.sync_api import Page, expect

from core.base_page import BasePage


class LoginPage(BasePage):
    def __init__(self, page: Page, base_url: str):
        super().__init__(page, base_url)
        self.email = page.locator("#email")
        self.password = page.locator("#password")
        self.login_btn = page.locator("#login-btn")
        self.error_banner = page.locator("[data-testid='login-error']")
        self.otp_input = page.locator("#otp")  # present only for 2FA-enabled accounts
        self.otp_submit = page.locator("#otp-submit")

    def open(self, path: str = "/login") -> None:
        super().open(path)

    def login(self, email: str, password: str, totp_code: str | None = None) -> None:
        """
        Perform a full login. Handles the 2FA branch conditionally: some accounts prompt for a
        code, others don't, so we detect the OTP field rather than assuming it's always/never there.
        """
        self.email.fill(email)
        self.password.fill(password)
        self.login_btn.click()

        # If this account has 2FA, the OTP field appears. We wait a bounded time for it to *maybe*
        # show, then branch. This is deterministic — no sleep, no guesswork.
        if totp_code and self._otp_prompt_appeared():
            self.otp_input.fill(totp_code)
            self.otp_submit.click()

    def _otp_prompt_appeared(self, timeout_ms: int = 3000) -> bool:
        try:
            self.otp_input.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
            return False

    def expect_login_error(self, message: str | None = None) -> None:
        expect(self.error_banner).to_be_visible()
        if message:
            expect(self.error_banner).to_contain_text(message)
