# main.py
import hashlib
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Type

from notifications import send_notification
from services.base_service import CheckinResult, CheckinService
from services.glados_service import GLaDOSService
from services.ikuuu_service import IkuuuService
from services.workbuddy_service import WorkBuddyService
from status_manager import read_prior_status, write_current_status


ServiceDefinition = Tuple[str, str, Type[CheckinService]]

SERVICE_DEFINITIONS: Tuple[ServiceDefinition, ...] = (
    ("GR_COOKIE", "GLaDOS", GLaDOSService),
    ("IKUUU_COOKIE", "iKuuu", IkuuuService),
    ("WORKBUDDY_ACCOUNTS_JSON", "WorkBuddy", WorkBuddyService),
)


def _hash_account_id(account_id: str) -> str:
    """兼容旧版 status.json 的账号哈希。"""
    return hashlib.sha256(account_id.encode("utf-8")).hexdigest()


def _account_state_key(service_name: str, account_id: str) -> str:
    """生成包含服务名的状态键，避免不同服务的相同账号标识互相覆盖。"""
    raw_key = f"{service_name}:{account_id}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def prepare_runtime() -> None:
    """报告运行环境；实际配置始终由调用方通过环境变量传入。"""
    run_env = os.environ.get("RUN_ENV", "").strip().lower()
    if run_env == "prod":
        print("检测到 GitHub Actions 生产环境。\n")
    else:
        print("检测到本地环境，请通过环境变量传入测试配置。\n")
    print("自动签到程序启动\n")


def load_valid_prior_status() -> Dict[str, dict]:
    """读取并验证当天的历史状态；旧版列表格式会被安全忽略。"""
    prior_status = read_prior_status()
    if not prior_status:
        return {}

    first_value = next(iter(prior_status.values()))
    if isinstance(first_value, dict):
        return prior_status

    print("\n警告：检测到旧版 status.json 文件格式。")
    print("本次将执行所有签到任务，并在结束后自动生成新版格式文件。")
    print("如下次运行仍看到此警告，请手动删除 status.json 文件。\n")
    return {}


def get_enabled_services() -> List[CheckinService]:
    """根据环境变量初始化已启用的服务。"""
    services: List[CheckinService] = []
    print("=== 开始检测并加载服务 ===\n")

    for env_name, display_name, service_class in SERVICE_DEFINITIONS:
        if not os.environ.get(env_name):
            print(f"未检测到 {env_name}，跳过 {display_name} 服务。")
            continue

        print(f"检测到 {env_name}，启用 {display_name} 服务。")
        try:
            services.append(service_class())
        except Exception as exc:
            print(f"{display_name} 服务初始化失败: {exc}")

    print(f"\n=== 服务加载完成，共启用 {len(services)} 个服务 ===\n")
    return services


def _find_previous_record(
    prior_status: Dict[str, dict], service_name: str, account_id: str
) -> Optional[dict]:
    """优先读取新状态键，并兼容旧版仅按账号生成的状态键。"""
    return prior_status.get(_account_state_key(service_name, account_id)) or prior_status.get(
        _hash_account_id(account_id)
    )


def all_configured_accounts_succeeded(
    services: List[CheckinService], prior_status: Dict[str, dict]
) -> bool:
    """判断所有当前配置的账号是否都已有当天成功记录。"""
    if not prior_status or not services:
        return False

    configured_account_count = 0
    for service in services:
        try:
            account_configs = service.get_account_configs()
        except Exception as exc:
            print(f"获取服务 {service.service_name} 账号配置时出错: {exc}")
            return False

        for config in account_configs:
            account_id = config.get("account_id")
            if not account_id:
                return False
            configured_account_count += 1
            previous_record = _find_previous_record(
                prior_status, service.service_name, account_id
            )
            if not previous_record or previous_record.get("success") is not True:
                return False

    return configured_account_count > 0


def _build_skipped_result(
    service: CheckinService, account_id: str, previous_record: dict
) -> CheckinResult:
    """将当天已有的成功记录恢复为统一结果。"""
    return CheckinResult(
        service_name=previous_record.get("service_name", service.service_name),
        account_id=account_id,
        success=True,
        message=previous_record.get("message", "今日已签到"),
        checkin_time=previous_record.get("checkin_time", "未知时间"),
        data={**previous_record.get("data", {}), "skipped": True},
    )


def _build_service_error_result(service: CheckinService, exc: Exception) -> CheckinResult:
    """把服务级异常转换成可通知的统一结果。"""
    return CheckinResult(
        service_name=service.service_name,
        account_id="服务异常",
        success=False,
        message=f"服务执行异常: {exc}",
        checkin_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        data={},
    )


def run_service(
    service: CheckinService, prior_status: Dict[str, dict]
) -> List[CheckinResult]:
    """执行一个服务的全部账号，并复用当天已成功的结果。"""
    account_configs = service.get_account_configs()
    if not account_configs:
        print(f"服务 {service.service_name} 未找到任何账号配置。")
        return []

    results: List[CheckinResult] = []
    for config in account_configs:
        account_id = config.get("account_id", "未知账号")
        previous_record = _find_previous_record(
            prior_status, service.service_name, account_id
        )
        if previous_record and previous_record.get("success") is True:
            print(f"账号 {account_id} 在当日已成功签到，本次将跳过。")
            results.append(_build_skipped_result(service, account_id, previous_record))
            continue

        results.append(service.process_single_account(config))

    return results


def run_services(
    services: List[CheckinService], prior_status: Dict[str, dict]
) -> List[CheckinResult]:
    """依次执行所有服务，并隔离单个服务的异常。"""
    all_results: List[CheckinResult] = []
    for service in services:
        try:
            all_results.extend(run_service(service, prior_status))
        except Exception as exc:
            print(f"服务 {service.service_name} 执行异常: {exc}")
            all_results.append(_build_service_error_result(service, exc))
    return all_results


def build_status_records(all_results: List[CheckinResult]) -> Dict[str, dict]:
    """构造可供下一次运行复用的当天状态。"""
    status_records: Dict[str, dict] = {}
    for result in all_results:
        if result.account_id == "服务异常":
            continue
        state_key = _account_state_key(result.service_name, result.account_id)
        status_records[state_key] = {
            "service_name": result.service_name,
            "success": result.success,
            "message": result.message,
            "checkin_time": result.checkin_time,
        }
    return status_records


def format_results_for_serverchan(
    all_results: List[CheckinResult],
) -> Tuple[str, str]:
    """将所有结果格式化为统一通知标题和正文。"""
    if not all_results:
        return "自动签到 0/0/0", "无签到任务"

    max_service_len = min(10, max(len(r.service_name) for r in all_results))
    max_account_len = min(10, max(len(r.account_id) for r in all_results))
    max_message_len = min(15, max(len(r.message) for r in all_results))

    lines = []
    for result in all_results:
        account = (
            result.account_id[:10] + ".."
            if len(result.account_id) > 10
            else result.account_id
        )
        if result.service_name == "GLaDOS":
            account = result.account_id[:10]

        service_name = (
            result.service_name[:10] + ".."
            if len(result.service_name) > 10
            else result.service_name
        )
        message = (
            result.message[:15] + ".."
            if len(result.message) > 15
            else result.message
        )
        status = "✓" if result.success else "✗"
        data = ""
        if result.data and result.service_name == "GLaDOS":
            if "left_days" in result.data:
                data = f"{result.data['left_days']}天\n"
        elif result.data and result.service_name == "WorkBuddy":
            if result.data.get("credit") is not None:
                data = f"+{result.data['credit']}积分\n"

        lines.append(
            f"\n{service_name.ljust(max_service_len)} "
            f"{account.ljust(max_account_len)} "
            f"{status} {data} "
            f"{message.ljust(max_message_len)}"
        )

    total = len(all_results)
    success = sum(1 for result in all_results if result.success)
    fail = total - success
    lines.append(f"\n统计: 总数 {total} | 成功 {success} | 失败 {fail}")
    return f"自动签到 {total}/{success}/{fail}", "\n".join(lines)


def save_and_notify(all_results: List[CheckinResult]) -> None:
    """保存当天状态并发送一次统一通知。"""
    print("\n=== 更新当日签到状态 ===")
    write_current_status(build_status_records(all_results))

    notification_title, final_report = format_results_for_serverchan(all_results)
    print("\n=== 开始发送统一通知 ===")
    send_notification(notification_title, final_report)
    print("=== 通知流程结束 ===")


def main() -> None:
    """自动签到主流程。"""
    prepare_runtime()
    prior_status = load_valid_prior_status()
    services = get_enabled_services()

    if not services:
        print("没有任何服务被启用，程序退出。")
        return

    if all_configured_accounts_succeeded(services, prior_status):
        print("\n=== 所有已配置的账号今日均已成功签到，无需重复执行。 ===")
        print("程序退出，本次不发送通知。")
        return

    all_results = run_services(services, prior_status)
    save_and_notify(all_results)
    print("\n所有任务执行完毕。")


if __name__ == "__main__":
    main()
