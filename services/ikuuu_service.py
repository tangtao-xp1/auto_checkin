# services/ikuuu_service.py
import json
import os
from typing import Any, Dict, List

from .base_service import CheckinService


class IkuuuService(CheckinService):
    """iKuuu 签到服务（基于 Cookie 认证）。"""

    _retry_config = {
        "enabled": True,
        "max_retries": 2,
        "delay": 5,
    }

    def __init__(self):
        super().__init__()
        self.base_url = os.environ.get("IKUUU_BASE_URL", "https://ikuuu.org").rstrip("/")
        print(f"ikuuu baseurl = {self.base_url}")

    @property
    def service_name(self) -> str:
        return "iKuuu"

    def get_account_configs(self) -> List[Dict[str, Any]]:
        """从环境变量解析 iKuuu 账号配置（Cookie 方式）。"""
        cookies_str = os.environ.get("IKUUU_COOKIE", "")
        if not cookies_str:
            raise ValueError("iKuuu cookie (IKUUU_COOKIE) 未配置！")

        cookies = [cookie.strip() for cookie in cookies_str.split("||") if cookie.strip()]
        if not cookies:
            raise ValueError("iKuuu cookie 解析失败，请检查 IKUUU_COOKIE 格式！")

        configs: List[Dict[str, Any]] = []
        for cookie in cookies:
            account_id = cookie[:10] + "..."
            configs.append(
                {
                    "cookie": cookie,
                    "account_id": account_id,
                    "base_url": self.base_url,
                }
            )
        return configs

    def _is_already_checked_in(self, result: Dict[str, Any]) -> bool:
        """判断是否已经签到过。"""
        if not isinstance(result, dict):
            return False

        message = str(result.get("message", ""))
        if "\u5df2\u7ecf\u7b7e\u5230" in message or "\u5df2\u7b7e\u5230\u8fc7" in message:
            return True

        checkin_response = result.get("checkin_response")
        if isinstance(checkin_response, dict):
            response_msg = str(
                checkin_response.get("msg") or checkin_response.get("message") or ""
            )
            return "\u5df2\u7ecf\u7b7e\u5230" in response_msg or "\u5df2\u7b7e\u5230\u8fc7" in response_msg

        return False

    def login(self, account_config: Dict[str, Any]) -> bool:
        """iKuuu 基于 cookie，无需登录步骤。"""
        return True

    def _parse_checkin_json(self, response: Any, content_type: str) -> Dict[str, Any]:
        """容错解析签到响应：优先按 JSON 解析正文，不只依赖 Content-Type。"""
        try:
            checkin_data = response.json()
        except ValueError:
            try:
                checkin_data = json.loads(response.text)
            except ValueError as exc:
                if response.status_code == 200 and "<html" in response.text.lower():
                    raise ValueError(
                        "服务端返回HTML页面而非JSON，cookie可能已过期，请更新 IKUUU_COOKIE"
                    ) from exc
                raise ValueError(
                    f"服务端返回无法解析的响应(status={response.status_code}, type={content_type})，"
                    "请检查 IKUUU_BASE_URL 和 IKUUU_COOKIE 配置"
                ) from exc

        if not isinstance(checkin_data, dict):
            raise ValueError("签到响应格式异常，预期为 JSON 对象")

        return checkin_data

    def do_checkin(self, account_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行 iKuuu 签到，通过 POST 请求并附带 Cookie。"""
        checkin_url = f"{account_config['base_url']}/user/checkin"
        print(f"      checkin_url = {checkin_url}")

        headers = {
            "cookie": account_config["cookie"],
            "referer": f"{account_config['base_url']}/user",
            "origin": account_config["base_url"],
        }

        response = self.make_request("POST", checkin_url, headers=headers)

        if response.history:
            redirect_chain = " -> ".join(f"{r.status_code}({r.url})" for r in response.history)
            print(f"      [诊断] 发生重定向: {redirect_chain} -> {response.url}")
            print("      [诊断] 重定向通常意味着 cookie 过期或域名变化，请检查 IKUUU_COOKIE 和 IKUUU_BASE_URL")

        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            body_preview = response.text[:300].replace("\n", " ").strip()
            print(f"      [诊断] 响应状态码: {response.status_code}")
            print(f"      [诊断] Content-Type: {content_type}")
            print(f"      [诊断] 响应内容前300字符: {body_preview}")

        checkin_data = self._parse_checkin_json(response, content_type)

        raw_ret = checkin_data.get("ret", -1)
        try:
            ret = int(raw_ret)
        except (TypeError, ValueError):
            ret = -1

        message = str(checkin_data.get("msg") or checkin_data.get("message") or "签到失败")
        already_checked = "\u5df2\u7ecf\u7b7e\u5230" in message or "\u5df2\u7b7e\u5230\u8fc7" in message
        success = (ret == 1) or already_checked

        print(f"      ret = {ret}{'-成功' if success else '-失败'}")
        print(f"      msg = {message}")

        if already_checked and ret != 1:
            print("      [处理] 检测到已签到，按成功处理并停止重试")

        return {
            "success": success,
            "message": message,
            "checkin_response": checkin_data,
            "already_checked_in": already_checked,
            "ret": ret,
        }

    def get_usage_info(self, account_config: Dict[str, Any]) -> Dict[str, Any]:
        """iKuuu 用量信息暂无公开 API，返回 None。"""
        return None
