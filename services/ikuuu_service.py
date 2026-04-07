# services/ikuuu_service.py
import os
from typing import List, Dict, Any

from .base_service import CheckinService


class IkuuuService(CheckinService):
    """iKuuu 签到服务（基于Cookie认证）。"""

    # 启用重试
    _retry_config = {
        'enabled': True,  # 启用重试   
        'max_retries': 2,  # 重试次数
        'delay': 5  # 重试间隔，单位：秒
    }

    def __init__(self):
        super().__init__()
        self.base_url = os.environ.get('IKUUU_BASE_URL', 'https://ikuuu.one').rstrip('/')

    @property
    def service_name(self) -> str:
        return "iKuuu"

    def get_account_configs(self) -> List[Dict[str, Any]]:
        """从环境变量解析iKuuu账号配置（Cookie方式）"""
        cookies_str = os.environ.get('IKUUU_COOKIE', '')

        if not cookies_str:
            raise ValueError("iKuuu cookie (IKUUU_COOKIE) 未配置！")

        cookies = [cookie.strip() for cookie in cookies_str.split('||') if cookie.strip()]
        if not cookies:
            raise ValueError("iKuuu cookie 解析失败，请检查 IKUUU_COOKIE 格式！")

        configs = []
        for cookie in cookies:
            # 使用cookie前10个字符作为账号标识（脱敏）
            account_id = cookie[:10] + '...'
            config = {
                'cookie': cookie,
                'account_id': account_id,
                'base_url': self.base_url
            }
            configs.append(config)

        return configs
    
    def _is_already_checked_in(self, result: Dict[str, Any]) -> bool:
        """
        判断是否已经签到过
        iKuuu的签到重复判断：
        - ret = 0 且 message 包含 "已经签到过了"
        """
        if not isinstance(result, dict):
            return False

        success = result.get('success', False)
        message = result.get('message', '')
        
        return success is False and "已经签到过了" in message

    def login(self, account_config: Dict[str, Any]) -> bool:
        """iKuuu基于cookie，无需登录步骤"""
        return True

    def do_checkin(self, account_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行iKuuu签到，通过POST请求带cookie完成"""
        checkin_url = f"{account_config['base_url']}/user/checkin"
        print(f"      checkin_url = {checkin_url}")

        headers = {
            'cookie': account_config['cookie'],
            'referer': f"{account_config['base_url']}/user",
            'origin': account_config['base_url']
        }

        response = self.make_request('POST', checkin_url, headers=headers)
        checkin_data = response.json()
        ret = checkin_data.get('ret', -1)
        message = checkin_data.get('msg', '签到失败')
        print(f"      ret = {ret}{'-成功' if ret == 1 else '-失败'}")
        print(f"      msg = {message}")
        return {
            'success': (ret == 1),
            'message': message,
            'checkin_response': checkin_data
        }

    def get_usage_info(self, account_config: Dict[str, Any]) -> Dict[str, Any]:
        """iKuuu用量信息已无法通过API获取，返回None"""
        return None
