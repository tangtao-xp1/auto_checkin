# services/glados_service.py
import os
import json
from typing import List, Dict, Any
from .base_service import CheckinService


class GLaDOSService(CheckinService):
    """GLaDOS 签到服务。"""

    def __init__(self):
        super().__init__()
        self.base_url = os.environ.get('GLADOS_BASE_URL', 'https://glados.one')

    @property
    def service_name(self) -> str:
        return "GLaDOS"

    def get_account_configs(self) -> List[Dict[str, Any]]:
        """从环境变量解析GLaDOS账号配置"""
        cookies_str = os.environ.get('GR_COOKIE', '')
        if not cookies_str:
            raise ValueError("GLaDOS cookie (GR_COOKIE) 未配置！")
        
        cookies = [cookie.strip() for cookie in cookies_str.split('||') if cookie.strip()]
        if not cookies:
            raise ValueError("GLaDOS cookie 解析失败，请检查 GR_COOKIE 格式！")
        
        configs = []
        for cookie in cookies:
            config = {
                'cookie': cookie,
                'account_id': cookie[:10] + '...',  # 使用cookie前10字符作为账号标识
                'base_url': self.base_url
            }
            configs.append(config)
        
        return configs

    def login(self, account_config: Dict[str, Any]) -> bool:
        """GLaDOS基于cookie，无需登录步骤"""
        return True

    def do_checkin(self, account_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行GLaDOS签到"""
        checkin_url = f"{account_config['base_url']}/api/user/checkin"
        print(f"      checkin_url = {checkin_url}")
        
        headers = {
            'cookie': account_config['cookie'],
            'referer': os.environ.get('GLADOS_REFERER', f"{account_config['base_url']}/console/checkin"),
            'origin': account_config['base_url'],
            'content-type': 'application/json;charset=UTF-8'
        }
        
        # 发起签到请求
        response = self.make_request(
            'POST', 
            checkin_url, 
            headers=headers, 
            data=json.dumps({'token': 'glados.one'})
        )
        
        checkin_data = response.json()
        code = checkin_data.get('code', -1)
        print(f"      code = {code}{'-成功' if code == 1 else '-失败'}")
        message = checkin_data.get('message', '未知结果')
        success = (code == 0)
        
        return {
            'success': success,
            'message': message,
            'checkin_response': checkin_data
        }

    def get_usage_info(self, account_config: Dict[str, Any]) -> Dict[str, Any]:
        """获取GLaDOS用量信息"""
        try:
            status_url = f"{account_config['base_url']}/api/user/status"
            print(f"      status_url = {status_url}")

            headers = {
                'cookie': account_config['cookie'],
                'referer': os.environ.get('GLADOS_REFERER', f"{account_config['base_url']}/console/checkin"),
                'origin': account_config['base_url']
            }

            # 获取用户状态
            response = self.make_request('GET', status_url, headers=headers)
            status_data = response.json().get('data', {})

            email = status_data.get('email', '未知邮箱')
            left_days = status_data.get('leftDays', '未知')
            if isinstance(left_days, str) and '.' in left_days:
                left_days = left_days.split('.')[0]

            return {
                'email': email,
                'left_days': left_days,
                'status_response': status_data
            }
        except Exception as e:
            print(f"      获取用量信息异常: {str(e)}")
            return None