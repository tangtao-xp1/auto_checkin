# main.py
import os
import hashlib
from typing import List, Tuple
from datetime import datetime
from services.base_service import CheckinService, CheckinResult
from services.glados_service import GLaDOSService
from services.ikuuu_service import IkuuuService
from notifications import send_notification


def _hash_account_id(account_id: str) -> str:
    """使用 SHA-256 对 account_id 进行哈希处理，保护敏感信息"""
    return hashlib.sha256(account_id.encode('utf-8')).hexdigest()


def get_enabled_services() -> List[CheckinService]:
    """
    检测环境变量，初始化所有已启用的服务。
    """
    services: List[CheckinService] = []
    print("=== 开始检测并加载服务 ===\n")

    # 检测 GLaDOS 服务
    glados_cookie = os.environ.get("GR_COOKIE")
    if glados_cookie:
        print("检测到 GR_COOKIE, 启用 GLaDOS 服务。")
        try:
            services.append(GLaDOSService())
        except Exception as e:
            print(f"GLaDOS 服务初始化失败: {e}")
    else:
        print("未检测到 GR_COOKIE, 跳过 GLaDOS 服务。")

    # 检测 iKuuu 服务
    ikuuu_email = os.environ.get("EMAIL")
    ikuuu_passwd = os.environ.get("PASSWD")
    if ikuuu_email and ikuuu_passwd:
        print("检测到 EMAIL 和 PASSWD, 启用 iKuuu 服务。")
        try:
            services.append(IkuuuService())
        except Exception as e:
            print(f"iKuuu 服务初始化失败: {e}")
    else:
        print("未检测到 EMAIL 或 PASSWD, 跳过 iKuuu 服务。")

    # 未来可在此处添加更多服务的检测...
    # if os.environ.get("NEW_SITE_CONFIG"):
    #     services.append(NewSiteService())

    print(f"\n=== 服务加载完成，共启用 {len(services)} 个服务 ===\n")
    return services


def format_results_for_notification(all_results: List[CheckinResult]) -> str:
    """
    格式化所有结果为通知内容
    """
    if not all_results:
        return "没有执行任何签到任务。"

    # 按服务分组
    service_groups = {}
    for result in all_results:
        if result.service_name not in service_groups:
            service_groups[result.service_name] = []
        service_groups[result.service_name].append(result)

    # 构建报告
    report_lines = []
    total_success = 0
    total_accounts = len(all_results)

    for service_name, results in service_groups.items():
        success_count = sum(1 for r in results if r.success)
        report_lines.append(f"## {service_name} ({success_count}/{len(results)})")
        report_lines.append("")

        for result in results:
            status_icon = "✅" if result.success else "❌"
            report_lines.append(f"{status_icon} **{result.account_id}** - {result.message}")

            # 添加详细信息
            if result.success and result.data:
                if service_name == "GLaDOS":
                    email = result.data.get('email', '')
                    left_days = result.data.get('left_days', '')
                    if email:
                        report_lines.append(f"   - 账号: {email}")
                    if left_days:
                        report_lines.append(f"   - 剩余天数: {left_days} 天")

                elif service_name == "iKuuu":
                    remaining_traffic = result.data.get('remaining_traffic', '')
                    if remaining_traffic:
                        report_lines.append(f"   - 剩余流量: {remaining_traffic} GB")

            report_lines.append(f"   - 时间: {result.checkin_time}")
            report_lines.append("")

        total_success += success_count

    # 添加总结
    summary = f"## 总结\n\n总计: {total_success}/{total_accounts} 个账号签到成功"
    report_lines.insert(0, summary)
    report_lines.insert(1, "")

    return "\n".join(report_lines)


def format_results_for_serverchan(all_results: List[CheckinResult]) -> Tuple[str, str]:
    """
    极简对齐版签到结果格式化
    返回: (title, final_report)
    title格式: "自动签到 总数/成功/失败"
    正文使用 ✓ 和 ✗ 符号
    """
    if not all_results:
        return "自动签到 0/0/0", "无签到任务"

    # 计算各列最大宽度
    max_service_len = min(10, max(len(r.service_name) for r in all_results))  # 限制最大10字符
    max_account_len = min(10, max(len(r.account_id) for r in all_results))  # 限制最大10字符
    max_message_len = min(15, max(len(r.message) for r in all_results))  # 限制最大15字符

    lines = []
    for result in all_results:
        # 处理账号显示
        account = (result.account_id[:10] + "..") if len(result.account_id) > 10 else result.account_id
        if result.service_name == "GLaDOS":
            account = result.account_id[:10]  # GLaDOS只显示前10字符

        # 处理service_name和message的长度限制
        service_name = (result.service_name[:10] + "..") if len(result.service_name) > 10 else result.service_name
        message = (result.message[:15] + "..") if len(result.message) > 15 else result.message

        # 构建状态和数据部分 - 使用 ✓ 和 ✗ 符号
        status = "✓" if result.success else "✗"
        data = ""
        if result.data:
            if result.service_name == "GLaDOS" and 'left_days' in result.data:
                data = f"{result.data['left_days']}天\n"
            elif result.service_name == "iKuuu" and 'remaining_traffic' in result.data:
                data = f"{result.data['remaining_traffic']}G\n"

        # 对齐格式化
        line = (f"\n{service_name.ljust(max_service_len)} "
                f"{account.ljust(max_account_len)} "
                f"{status} {data} "
                f"{message.ljust(max_message_len)}")
        lines.append(line)

    # 统计信息
    total = len(all_results)
    success = sum(1 for r in all_results if r.success)
    fail = total - success

    # 添加统计到报告内容
    lines.append(f"\n统计: 总数 {total} | 成功 {success} | 失败 {fail}")
    detail_report = "\n".join(lines)

    # 生成标题（格式：签到 总数/成功/失败）
    title = f"自动签到 {total}/{success}/{fail}"

    return title, detail_report

def set_env():
    # 设置测试用的环境变量（本地测试时使用）
    os.environ.update({
        # GLaDOS 配置
        "GR_COOKIE": "koa:sess=xxx; koa:sess.sig=xxx||koa:sess=xxx; koa:sess.sig=xxx||",
        "GLADOS_BASE_URL": "https://glados.one",

        # iKuuu 配置
        "EMAIL": "xxx@xxx.com||xxx@xxx.com||",
        "PASSWD": "12345||12345||",
        "IKUUU_BASE_URL": "https://ikuuu.org",

        # 通用配置
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",

        # 通知配置（测试时可以留空或使用测试token）
        "SERVERCHAN_KEY": "",
        "PUSHPLUS_TOKEN": "",
        "TG_BOT_TOKEN": "",
        "TG_CHAT_ID": ""
    })

if __name__ == "__main__":
    # set_env()
    print("自动签到程序启动\n")

    # 增量签到逻辑：检查环境变量开关
    is_incremental_enabled = bool(os.environ.get("GH_ACCESS_TOKEN"))
    previously_successful_accounts = {}

    if is_incremental_enabled:
        print("=== 检测到 GH_ACCESS_TOKEN，启用增量签到模式 ===")
        from github_utils import read_prior_status, write_current_status
        previously_successful_accounts = read_prior_status()
    else:
        print("=== 未检测到 GH_ACCESS_TOKEN，运行完整签到 ===")

    # 1. 加载所有启用的服务
    all_services = get_enabled_services()

    # 检查是否所有账号今日已签到成功
    if is_incremental_enabled and all_services:
        all_configured_accounts_hashed = set()
        for service in all_services:
            try:
                account_configs = service.get_account_configs()
                for config in account_configs:
                    # 确保我们得到一个有效的 account_id
                    if account_id := config.get('account_id'):
                        all_configured_accounts_hashed.add(_hash_account_id(account_id))
            except Exception as e:
                print(f"获取服务 {service.service_name} 账号配置时出错: {e}")

        if all_configured_accounts_hashed and all_configured_accounts_hashed.issubset(previously_successful_accounts.keys()):
            print("\n=== 所有已配置的账号今日均已成功签到，无需重复执行。 ===")
            print("程序退出，本次不发送通知。")
            exit()  # 提前退出，节约资源和通知

    if not all_services:
        print("没有任何服务被启用，程序退出。")
        notification_title = "签到 0/0/0"
        final_report = "没有任何服务被启用。请检查环境变量配置。"

    else:
        all_results: List[CheckinResult] = []
        current_successful_accounts = previously_successful_accounts.copy()

        # 2. 执行所有服务的签到流程
        for service in all_services:
            # 在服务级别检查是否可以跳过
            # 注意：这里的实现是基于账号级别的跳过，服务级别的跳过需要更复杂的逻辑
            # 因此我们直接进入账号处理
            try:
                # 获取服务的账号配置
                account_configs = service.get_account_configs()
                if not account_configs:
                    print(f"服务 {service.service_name} 未找到任何账号配置。")
                    continue

                service_results = []
                for config in account_configs:
                    account_id = config.get('account_id', '未知账号')
                    hashed_id = _hash_account_id(account_id)
                    # 检查此账号是否在之前已成功
                    if is_incremental_enabled and previously_successful_accounts.get(hashed_id) is True:
                        print(f"账号 {account_id} 在当日已成功签到，本次将跳过。")
                        # 创建一个模拟的成功结果
                        mock_result = CheckinResult(
                            service_name=service.service_name,
                            account_id=account_id,
                            success=True,
                            message="已跳过，当日已成功",
                            checkin_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            data={}
                        )
                        service_results.append(mock_result)
                    else:
                        # 正常执行签到
                        result = service.process_single_account(config)
                        service_results.append(result)

                all_results.extend(service_results)

            except Exception as e:
                print(f"服务 {service.service_name} 执行异常: {e}")
                error_result = CheckinResult(
                    service_name=service.service_name,
                    account_id="服务异常",
                    success=False,
                    message=f"服务执行异常: {str(e)}",
                    checkin_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                all_results.append(error_result)

        # 如果启用了增量模式，则更新状态文件
        if is_incremental_enabled:
            print("\n=== 更新当日签到成功状态 ===")
            for result in all_results:
                if result.success:
                    hashed_id = _hash_account_id(result.account_id)
                    current_successful_accounts[hashed_id] = True
            write_current_status(current_successful_accounts)

        # 3. 格式化结果
        notification_title, final_report = format_results_for_serverchan(all_results)

    # 4. 发送统一通知
    print("\n=== 开始发送统一通知 ===")
    send_notification(notification_title, final_report)
    print("=== 通知流程结束 ===")

    print(f"\n所有任务执行完毕。")
