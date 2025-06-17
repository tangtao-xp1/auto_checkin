# main.py
import os
from typing import List, Tuple
from services.base_service import CheckinService, CheckinResult
from services.glados_service import GLaDOSService
from services.ikuuu_service import IkuuuService
from notifications import send_notification


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
        "IKUUU_BASE_URL": "https://ikuuu.one",

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

    # 1. 加载所有启用的服务
    all_services = get_enabled_services()

    if not all_services:
        print("没有任何服务被启用，程序退出。")
        notification_title = "签到 0/0/0"
        final_report = "没有任何服务被启用。请检查环境变量配置。"

    else:
        # 2. 执行所有服务的签到流程
        all_results: List[CheckinResult] = []

        for service in all_services:
            try:
                service_results = service.run()
                all_results.extend(service_results)
            except Exception as e:
                print(f"服务 {service.service_name} 执行异常: {e}")
                # 创建一个失败结果记录
                from datetime import datetime

                error_result = CheckinResult(
                    service_name=service.service_name,
                    account_id="服务异常",
                    success=False,
                    message=f"服务执行异常: {str(e)}",
                    checkin_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                all_results.append(error_result)

        # 3. 格式化结果
        # final_report = format_results_for_notification(all_results)
        notification_title, final_report = format_results_for_serverchan(all_results)

    # 4. 发送统一通知
    print("=== 开始发送统一通知 ===")
    send_notification(notification_title, final_report)
    print("=== 通知流程结束 ===")

    print(f"\n所有任务执行完毕。")
