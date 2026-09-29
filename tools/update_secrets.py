#!/usr/bin/env python3
"""文本菜单：提取 WorkBuddy 登录态或粘贴 Cookie，更新仓库 Actions Secret。"""

import argparse
import sys

if __package__:
    from . import export_workbuddy_credentials as exporter
else:
    import export_workbuddy_credentials as exporter


SERVICES = {
    "1": ("WorkBuddy", "WORKBUDDY_ACCOUNTS_JSON"),
    "2": ("iKuuu", "IKUUU_COOKIE"),
    "3": ("GLaDOS", "GR_COOKIE"),
}


def validate_cookies(value, service):
    """校验输入结构，保留 Cookie 内容；不发起服务登录请求。"""
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("Cookie 不能包含换行或控制字符")
    cookies = [part.strip() for part in value.split("||")]
    if not all(cookies):
        raise ValueError("Cookie 不能为空，多个账号之间使用 || 分隔")
    for index, cookie in enumerate(cookies, 1):
        if cookie.startswith(("'", '"')) or cookie.endswith(("'", '"')) or cookie.lower().startswith("cookie:"):
            raise ValueError(f"第 {index} 个账号请去掉外层引号和 Cookie: 前缀")
        if "\\" in cookie:
            raise ValueError(f"第 {index} 个账号包含反斜杠，请重新复制原始 Cookie")
        fields = {}
        for part in cookie.split(";"):
            if not part.strip():
                continue
            key, separator, field_value = part.strip().partition("=")
            if not separator or not key.strip() or any(c.isspace() for c in key):
                raise ValueError(f"第 {index} 个账号不是有效的 Cookie 键值格式")
            fields[key] = field_value.strip()
        if service == "GLaDOS" and not any(
            fields.get(f"{prefix}:sess") and fields.get(f"{prefix}:sess.sig")
            for prefix in ("gld", "koa")
        ):
            raise ValueError(f"第 {index} 个账号需要完整的 gld 或 koa 会话及签名")
    return "||".join(cookies), len(cookies)


def read_cookie_secret(service):
    print(f"粘贴 {service} 的完整 Cookie；多账号可用 || 分隔。")
    print("不要包含 Cookie:、外层引号或转义反斜杠。输入会显示在控制台，工具不会保存。")
    return validate_cookies(input("Cookie："), service)


def run_menu(args):
    repository = args.github_repo
    token = None
    while True:
        print("\nGitHub Actions Secret 更新工具")
        for choice, (service, secret_name) in SERVICES.items():
            print(f"{choice}. {service} → {secret_name}")
        print("0. 退出")
        choice = input("请选择：").strip()
        if choice == "0":
            return 0
        if choice not in SERVICES:
            print("请输入 0、1、2 或 3。")
            continue
        service, secret_name = SERVICES[choice]
        try:
            if service == "WorkBuddy":
                accounts = exporter.load_accounts(args.auth_dir or exporter.default_auth_dir())
                exporter._describe_accounts(accounts)
                value, count = exporter.serialize_accounts(accounts), len(accounts)
            else:
                value, count = read_cookie_secret(service)
            candidate = input(f"目标仓库 OWNER/REPO [{repository or '未设置'}]：").strip()
            candidate = candidate or repository or ""
            owner, repo = exporter._parse_repository(candidate)
            repository = f"{owner}/{repo}"
            print(f"即将覆盖 {repository} 的 {secret_name}，共 {count} 个账号。")
            print("此操作替换整个 Secret；保留多个账号时，请一次提供全部账号。")
            if input("输入 y 确认上传，其他输入取消：").strip().lower() != "y":
                print("已取消。")
                continue
            if token is None:
                token = exporter._get_github_token(args.github_token_env)
            exporter.update_github_secret(
                repository, secret_name, value, token, args.github_api_base
            )
            print(f"已更新 {repository} 的 {secret_name}（{count} 个账号）。")
        except (ValueError, RuntimeError) as exc:
            print(f"更新失败：{exc}")
            token = None
        except exporter.requests.RequestException:
            print("GitHub 网络请求失败，请检查网络后重试。")
            token = None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--github-repo", help="默认目标仓库 OWNER/REPO，菜单中可修改")
    parser.add_argument("--auth-dir", type=exporter.Path, help="WorkBuddy 登录态目录")
    parser.add_argument("--github-token-env", default="GITHUB_TOKEN")
    parser.add_argument("--github-api-base", default=exporter.DEFAULT_GITHUB_API_BASE)
    args = parser.parse_args(argv)
    try:
        return run_menu(args)
    except (EOFError, KeyboardInterrupt):
        print("\n已退出。")
        return 0


if __name__ == "__main__":
    sys.exit(main())
