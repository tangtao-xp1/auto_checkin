# -*- coding: utf-8 -*-
# 该脚本通过 GitHub REST API 批量删除 GitHub 仓库中的工作流运行。
# 每次删除之间会暂停指定秒数以避免速率限制，并在最后提供详细的执行摘要。
# 需要安装 requests 库：pip install requests

import os
import sys
import json
import argparse
import getpass
import requests
import time


def get_workflow_runs(owner, repo, gh_token, count):
    """
    通过 GitHub API 获取指定仓库的工作流运行列表。
    """
    print(f"正在获取仓库 '{owner}/{repo}' 的工作流运行列表...")

    api_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {gh_token}"
    }
    params = {
        "per_page": 100  # GitHub API 默认每页最大 100 个
    }

    all_runs = []
    page = 1

    while True:
        params["page"] = page
        try:
            print(f"\n---> 正在调用获取 API: {api_url} (页码: {page})")
            response = requests.get(api_url, headers=headers, params=params)

            # 打印完整的 API 响应信息
            print(f"    - API 响应状态码: {response.status_code}")
            try:
                print(f"    - API 响应内容: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            except json.JSONDecodeError:
                print(f"    - API 响应内容（非 JSON）: {response.text}")

            response.raise_for_status()  # 如果响应状态码不是 2xx，则引发异常
            data = response.json()

            runs = data.get('workflow_runs', [])
            if not runs:
                break

            all_runs.extend(runs)

            # 如果指定了数量，且已获取足够多的数据，则停止分页
            if count and len(all_runs) >= count:
                break

            # 如果没有下一页，则停止
            if 'next' not in response.links:
                break

            page += 1

        except requests.exceptions.RequestException as e:
            print("错误：获取工作流运行列表失败。请检查仓库名称或 GitHub Token 是否正确、或其权限是否足够。")
            print("原始错误信息:", e)
            return None

    if not all_runs:
        print("警告：未找到任何工作流运行。")
        return []

    # 按创建时间降序排序
    all_runs.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    # 根据指定的数量进行截取
    if count and count > 0:
        all_runs = all_runs[:count]

    print(f"找到 {len(all_runs)} 个可供删除的工作流运行。")
    return all_runs


def delete_workflow_runs(owner, repo, gh_token, runs_to_delete, delay):
    """
    批量删除工作流运行，并在每次调用之间暂停。
    """
    total_runs = len(runs_to_delete)
    success_count = 0
    failure_count = 0

    print(f"\n开始批量删除... (共 {total_runs} 个，每次间隔 {delay} 秒)")

    for i, run in enumerate(runs_to_delete):
        run_id = run['id']
        delete_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {gh_token}"
        }

        print(
            f"\n---> [{i + 1}/{total_runs}] 正在删除工作流运行 ID: {run_id} (名称: {run['name']}, 状态: {run['status']})...")

        try:
            response = requests.delete(delete_url, headers=headers)

            # 打印完整的 API 响应信息
            print(f"    - API 响应状态码: {response.status_code}")
            print(f"    - API 响应内容: {response.text}")

            response.raise_for_status()
            print("    -> 删除成功！")
            success_count += 1
        except requests.exceptions.RequestException as e:
            print(f"    -> 删除失败！错误信息：{e}")
            failure_count += 1

        # 暂停以避免速率限制，如果不是最后一个则暂停
        if i < total_runs - 1:
            time.sleep(delay)

    print("\n--- 批量删除完成 ---")
    print(f"总计处理数量: {total_runs}")
    print(f"成功删除数量: {success_count}")
    print(f"失败数量: {failure_count}")


def main(args=None):
    """
    主脚本逻辑。
    """
    # 如果没有传入参数，则从命令行解析
    if args is None:
        parser = argparse.ArgumentParser(description="批量删除 GitHub 仓库中的工作流运行。",
                                         epilog="该脚本使用 GitHub REST API 来执行操作。")
        parser.add_argument('-o', '--owner', type=str, default="tangtao-xp1", help="GitHub 仓库的拥有者或组织名称。")
        parser.add_argument('-r', '--repo', type=str, default="auto_checkin", help="GitHub 仓库的名称。")
        parser.add_argument('-c', '--count', type=int, help="如果指定，脚本将仅处理最近的指定数量的工作流运行。")
        parser.add_argument('-t', '--gh_token', type=str,
                            help="如果你不想手动登录，可以直接在此处提供 GitHub Personal Access Token。")
        parser.add_argument('-f', '--force', action='store_true',
                            help="如果指定，脚本将跳过用户确认步骤，直接执行删除操作。")
        parser.add_argument('-d', '--delay', type=int, default=3, help="每次 API 调用之间的延迟秒数，默认值是3秒。")
        args = parser.parse_args()

    # 1. 检查必备参数
    if not args.owner or not args.repo:
        print("错误：请提供仓库拥有者和仓库名称。")
        print("用法示例：python delete_workflow_runs.py --owner <GitHub-Owner> --repo <GitHub-Repo>")
        sys.exit(1)

    gh_token = args.gh_token
    # 2. 如果未提供 Token，则进行交互式输入
    if not gh_token:
        print("\n请输入您的 GitHub Personal Access Token：")
        gh_token = getpass.getpass(prompt='Token: ')
        if not gh_token:
            print("错误：未提供 Token。操作已取消。")
            sys.exit(1)

    # 3. 获取工作流运行列表
    runs_to_delete = get_workflow_runs(args.owner, args.repo, gh_token, args.count)

    if runs_to_delete is None:
        sys.exit(1)

    if not runs_to_delete:
        print("没有找到要删除的工作流运行。")
        sys.exit(0)

    # 4. 安全确认
    if not args.force:
        print("\n警告：此操作不可逆！")
        plural = "s" if len(runs_to_delete) > 1 else ""
        response = input(
            f"你确定要删除仓库 '{args.owner}/{args.repo}' 中的所有 ({len(runs_to_delete)} 个) 工作流运行吗？\n输入 'yes' 确认删除: ")
        if response.lower() != 'yes':
            print("操作已取消。")
            sys.exit(0)

    # 5. 批量删除
    delete_workflow_runs(args.owner, args.repo, gh_token, runs_to_delete, args.delay)


if __name__ == "__main__":
    main()
