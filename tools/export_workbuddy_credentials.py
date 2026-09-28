#!/usr/bin/env python3
"""读取 WorkBuddy 本机登录态并生成最小化的 GitHub Actions Secret。

当前只在 Windows 版 WorkBuddy 登录态上验证。其他平台可以通过 --auth-dir
传入兼容目录，为后续扩展保留入口。
"""

import argparse
import base64
import hashlib
import json
import os
import struct
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests
from Crypto.Cipher import AES


DEFAULT_SECRET_NAME = "WORKBUDDY_ACCOUNTS_JSON"
DEFAULT_GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"

_AT_REST_SECRET = "Sik9U5aXhCdwTVEwsEySDOmDoB9r9ntFxHF1fst9LQI="
_WB_KEY = hashlib.sha256(_AT_REST_SECRET.encode("utf-8")).digest()
_WB_KEY_ID = hashlib.sha256(_WB_KEY).hexdigest()[:16]

_FRAMING_NUM = {"file": 1, "field": 2, "record": 3, "stream": 4}
_FRAMING_TAG = {
    "file": b"WBEF1",
    "field": b"WBEV1",
    "record": b"WBER1",
    "stream": b"WBES1",
}


def _log(message: str) -> None:
    print(message, file=sys.stderr)


def _wb_aad(framing: str, key_id: str, suite: int) -> bytes:
    return b"".join(
        [
            b"WB-AAD\x00",
            b"\x01",
            struct.pack(">I", len(_FRAMING_TAG[framing])) + _FRAMING_TAG[framing],
            struct.pack(">I", 6) + b"sym-v1",
            struct.pack(">I", suite),
            struct.pack(">I", len(key_id)) + key_id.encode("utf-8"),
            bytes([_FRAMING_NUM[framing]]),
            b"\x00",
            b"\x00",
        ]
    )


def open_wb_field(value: Any) -> Any:
    """解密 WorkBuddy 的 $wbEncrypted 字段，明文字段原样返回。"""
    if not isinstance(value, dict) or value.get("$wbEncrypted") != 1:
        return value
    if value.get("scheme") not in (None, "sym-v1"):
        raise ValueError(f"不支持的加密方案: {value.get('scheme')}")

    try:
        envelope = json.loads(base64.b64decode(value["envelope"]))
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("加密字段 envelope 格式无效") from exc

    if envelope.get("keyId") != _WB_KEY_ID:
        raise ValueError(
            "登录态密钥标识不匹配，WorkBuddy 版本可能已更新，请更新导出工具"
        )

    try:
        cipher = AES.new(
            _WB_KEY,
            AES.MODE_GCM,
            nonce=base64.b64decode(envelope["nonce"]),
        )
        cipher.update(_wb_aad("field", envelope["keyId"], envelope["suite"]))
        plain = cipher.decrypt_and_verify(
            base64.b64decode(envelope["ciphertext"]),
            base64.b64decode(envelope["authTag"]),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("WorkBuddy 登录态字段解密失败") from exc
    return plain.decode("utf-8")


def default_auth_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if not local_app_data:
        raise ValueError(
            "未检测到 LOCALAPPDATA；当前工具只验证了 Windows，"
            "其他平台请使用 --auth-dir 指定登录态目录"
        )
    return (
        Path(local_app_data)
        / "CodeBuddyExtension"
        / "Data"
        / "Public"
        / "auth"
    )


def load_accounts(auth_dir: Path) -> List[Dict[str, Any]]:
    """只读加载账号，并仅保留签到所需的最小字段。"""
    if not auth_dir.is_dir():
        raise ValueError(f"未找到 WorkBuddy 登录态目录: {auth_dir}")

    accounts: List[Dict[str, Any]] = []
    seen_tokens = set()
    errors = []
    for path in sorted(auth_dir.glob("*.info")):
        try:
            session = json.loads(path.read_text(encoding="utf-8"))
            auth = session.get("auth") or {}
            account = session.get("account") or {}

            access_token = str(open_wb_field(auth.get("accessToken")) or "").strip()
            user_id = str(open_wb_field(account.get("uid")) or "").strip()
            domain = str(open_wb_field(auth.get("domain")) or "").strip()
            expires_at_value = open_wb_field(auth.get("expiresAt"))

            if not access_token:
                raise ValueError("缺少 accessToken")
            if not user_id:
                raise ValueError("缺少 account.uid")
            try:
                expires_at = int(expires_at_value)
            except (TypeError, ValueError) as exc:
                raise ValueError("expiresAt 不是有效的毫秒时间戳") from exc
            if access_token in seen_tokens:
                continue

            seen_tokens.add(access_token)
            accounts.append(
                {
                    "label": path.stem,
                    "access_token": access_token,
                    "user_id": user_id,
                    "domain": domain,
                    "expires_at": expires_at,
                }
            )
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")

    for error in errors:
        _log(f"警告：跳过无法解析的登录态：{error}")
    if not accounts:
        raise ValueError("没有找到可用的 WorkBuddy 登录态，请先打开客户端并登录")
    return accounts


def serialize_accounts(accounts: List[Dict[str, Any]]) -> str:
    return json.dumps(accounts, ensure_ascii=False, separators=(",", ":"))


def _github_headers(token: str) -> Dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": "auto-checkin-workbuddy-tool",
    }


def _parse_repository(repository: str) -> Tuple[str, str]:
    parts = [part.strip() for part in repository.split("/")]
    if len(parts) != 2 or not all(parts):
        raise ValueError("--github-repo 必须使用 OWNER/REPO 格式")
    return parts[0], parts[1]


def _get_github_token(env_name: str) -> str:
    token = os.environ.get(env_name, "").strip()
    if token:
        return token
    _log(
        f"未检测到 {env_name}，将使用普通输入读取 Token；"
        "输入内容会显示在 IDE/终端中，但工具不会保存。"
    )
    token = input("请输入 GitHub Token：").strip()
    if not token:
        raise ValueError(f"未获得 GitHub Token，请设置 {env_name} 或在提示时输入")
    return token


def _encrypt_github_secret(public_key: str, secret_value: str) -> str:
    try:
        from nacl import encoding, public
    except ImportError as exc:
        raise RuntimeError(
            "自动更新 GitHub Secret 需要 PyNaCl，请运行 "
            "pip install -r requirements-tools.txt"
        ) from exc

    key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def update_github_secret(
    repository: str,
    secret_name: str,
    secret_value: str,
    token: str,
    api_base: str,
) -> None:
    """通过 GitHub REST API 创建或覆盖仓库级 Actions Secret。"""
    owner, repo = _parse_repository(repository)
    base_url = api_base.rstrip("/")
    encoded_owner = quote(owner, safe="")
    encoded_repo = quote(repo, safe="")
    secret_path = f"repos/{encoded_owner}/{encoded_repo}/actions/secrets"
    headers = _github_headers(token)

    public_key_response = requests.get(
        f"{base_url}/{secret_path}/public-key", headers=headers, timeout=30
    )
    if public_key_response.status_code != 200:
        raise RuntimeError(
            "获取 GitHub 仓库 Secret 公钥失败："
            f"HTTP {public_key_response.status_code}，请检查仓库名和 Token 权限"
        )
    try:
        public_key_data = public_key_response.json()
        public_key = public_key_data["key"]
        key_id = public_key_data["key_id"]
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError("GitHub 返回的仓库 Secret 公钥格式异常") from exc

    encrypted_value = _encrypt_github_secret(public_key, secret_value)
    encoded_secret_name = quote(secret_name, safe="")
    update_response = requests.put(
        f"{base_url}/{secret_path}/{encoded_secret_name}",
        headers=headers,
        json={"encrypted_value": encrypted_value, "key_id": key_id},
        timeout=30,
    )
    if update_response.status_code not in (201, 204):
        raise RuntimeError(
            "更新 GitHub Actions Secret 失败："
            f"HTTP {update_response.status_code}，请检查 Token 的 Secrets 写权限"
        )


def _describe_accounts(accounts: List[Dict[str, Any]]) -> None:
    _log(f"已读取 {len(accounts)} 个 WorkBuddy 账号：")
    now_ms = int(datetime.now().timestamp() * 1000)
    for account in accounts:
        expires_at = account["expires_at"]
        expires_text = datetime.fromtimestamp(expires_at / 1000).astimezone().strftime(
            "%Y-%m-%d %H:%M:%S %z"
        )
        state = "已过期" if expires_at <= now_ms else "有效"
        _log(f"  - {account['label']}: {state}，到期时间 {expires_text}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="读取 Windows WorkBuddy 登录态并更新 WORKBUDDY_ACCOUNTS_JSON"
    )
    parser.add_argument(
        "--auth-dir",
        type=Path,
        help="登录态目录；Windows 默认从 LOCALAPPDATA 自动定位",
    )
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--print-secret",
        action="store_true",
        help="将 Secret JSON 输出到终端，供手工粘贴到 GitHub",
    )
    action_group.add_argument(
        "--github-repo",
        metavar="OWNER/REPO",
        help="通过 GitHub REST API 自动创建或覆盖仓库 Secret",
    )
    parser.add_argument(
        "--secret-name",
        default=DEFAULT_SECRET_NAME,
        help=f"GitHub Actions Secret 名称，默认 {DEFAULT_SECRET_NAME}",
    )
    parser.add_argument(
        "--github-token-env",
        default="GITHUB_TOKEN",
        help="读取 GitHub Token 的环境变量名，默认 GITHUB_TOKEN",
    )
    parser.add_argument(
        "--github-api-base",
        default=DEFAULT_GITHUB_API_BASE,
        help="GitHub API 根地址，为 GitHub Enterprise 扩展保留",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        auth_dir = args.auth_dir or default_auth_dir()
        accounts = load_accounts(auth_dir)
        _describe_accounts(accounts)
        secret_value = serialize_accounts(accounts)

        if args.print_secret:
            _log("警告：下一行包含敏感登录态，请勿保存到代码、日志或聊天记录。")
            print(secret_value)
            return 0

        if args.github_repo:
            token = _get_github_token(args.github_token_env)
            update_github_secret(
                repository=args.github_repo,
                secret_name=args.secret_name,
                secret_value=secret_value,
                token=token,
                api_base=args.github_api_base,
            )
            _log(
                f"已更新 {args.github_repo} 的 GitHub Actions Secret: "
                f"{args.secret_name}"
            )
            return 0

        _log("登录态读取验证通过。")
        _log("手工更新请增加 --print-secret；自动更新请增加 --github-repo OWNER/REPO。")
        return 0
    except Exception as exc:
        _log(f"错误：{exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
