import json
import os
import time
from typing import Any, Dict, List

from .base_service import CheckinService


class WorkBuddyService(CheckinService):
    """使用最小化登录态字段调用 WorkBuddy HTTP 签到接口。"""

    _retry_config = {
        "enabled": True,
        "max_retries": 2,
        "delay": 5,
    }

    def __init__(self):
        super().__init__()
        self.base_url = os.environ.get(
            "WORKBUDDY_API_BASE", "https://copilot.tencent.com/v2/billing/meter"
        ).rstrip("/")

    @property
    def service_name(self) -> str:
        return "WorkBuddy"

    def get_account_configs(self) -> List[Dict[str, Any]]:
        """从 WORKBUDDY_ACCOUNTS_JSON 解析一个或多个账号。"""
        raw_value = os.environ.get("WORKBUDDY_ACCOUNTS_JSON", "").strip()
        if not raw_value:
            raise ValueError("WORKBUDDY_ACCOUNTS_JSON 未配置")

        try:
            accounts = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise ValueError("WORKBUDDY_ACCOUNTS_JSON 不是有效的 JSON") from exc

        if not isinstance(accounts, list) or not accounts:
            raise ValueError("WORKBUDDY_ACCOUNTS_JSON 必须是非空 JSON 数组")

        configs: List[Dict[str, Any]] = []
        account_ids = set()
        for index, account in enumerate(accounts, 1):
            if not isinstance(account, dict):
                raise ValueError(f"WorkBuddy 第 {index} 个账号配置必须是 JSON 对象")

            access_token = str(account.get("access_token") or "").strip()
            user_id = str(account.get("user_id") or "").strip()
            domain = str(account.get("domain") or "").strip()
            expires_at = account.get("expires_at")

            if not access_token:
                raise ValueError(f"WorkBuddy 第 {index} 个账号缺少 access_token")
            if not user_id:
                raise ValueError(f"WorkBuddy 第 {index} 个账号缺少 user_id")
            try:
                expires_at = int(expires_at)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"WorkBuddy 第 {index} 个账号的 expires_at 必须是毫秒时间戳"
                ) from exc
            if expires_at <= 0:
                raise ValueError(
                    f"WorkBuddy 第 {index} 个账号的 expires_at 必须大于 0"
                )

            label = str(account.get("label") or "").strip()
            account_id = label or self._default_account_id(user_id, index)
            if account_id in account_ids:
                raise ValueError(f"WorkBuddy 账号显示名重复: {account_id}")
            account_ids.add(account_id)

            configs.append(
                {
                    "account_id": account_id,
                    "access_token": access_token,
                    "user_id": user_id,
                    "domain": domain,
                    "expires_at": expires_at,
                }
            )

        return configs

    @staticmethod
    def _default_account_id(user_id: str, index: int) -> str:
        if len(user_id) <= 8:
            return f"WorkBuddy-{index}"
        return f"{user_id[:4]}***{user_id[-4:]}"

    def login(self, account_config: Dict[str, Any]) -> bool:
        """接口使用现有 Bearer Token；这里只做过期预检。"""
        if account_config["expires_at"] <= int(time.time() * 1000):
            raise ValueError(
                "WorkBuddy accessToken 已过期，请在 Windows 打开 WorkBuddy 刷新登录态，"
                "然后重新导出 WORKBUDDY_ACCOUNTS_JSON"
            )
        return True

    def _api(self, path: str, account_config: Dict[str, Any]) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {account_config['access_token']}",
            "X-User-Id": account_config["user_id"],
            "X-Domain": account_config["domain"],
            "Content-Type": "application/json",
        }
        response = self.make_request(
            "POST", f"{self.base_url}/{path}", headers=headers, json={}
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError(f"WorkBuddy {path} 返回的内容不是有效 JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"WorkBuddy {path} 返回格式异常")
        return payload

    def do_checkin(self, account_config: Dict[str, Any]) -> Dict[str, Any]:
        """先查询当天状态，仅在未签到时领取积分。"""
        status = self._api("checkin-status", account_config)
        if status.get("code") != 0:
            return {
                "success": False,
                "message": str(status.get("msg") or "查询签到状态失败"),
            }

        if (status.get("data") or {}).get("today_checked_in"):
            return {
                "success": True,
                "message": "今日已签到",
                "already_checked_in": True,
            }

        claim = self._api("daily-checkin", account_config)
        code = claim.get("code")
        if code == 0:
            credit = (claim.get("data") or {}).get("credit")
            message = "签到成功"
            if credit is not None:
                message = f"签到成功，获得积分: {credit}"
            return {
                "success": True,
                "message": message,
                "credit": credit,
            }

        if code == 10001:
            return {
                "success": True,
                "message": "今日已签到",
                "already_checked_in": True,
            }

        return {
            "success": False,
            "message": str(claim.get("msg") or f"签到失败(code={code})"),
        }

    def _is_already_checked_in(self, result: Dict[str, Any]) -> bool:
        return bool(result.get("already_checked_in"))

    def get_usage_info(self, account_config: Dict[str, Any]) -> Dict[str, Any]:
        """当前接口没有额外用量查询步骤。"""
        return {}
