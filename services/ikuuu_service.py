# services/ikuuu_service.py
import os
import re
from typing import List, Dict, Any

from .base_service import CheckinService


class IkuuuService(CheckinService):
    """iKuuu 签到服务。"""

    # 禁用重试
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
        """从环境变量解析iKuuu账号配置"""
        emails_str = os.environ.get('EMAIL', '')
        passwords_str = os.environ.get('PASSWD', '')

        if not emails_str or not passwords_str:
            raise ValueError("iKuuu 邮箱 (EMAIL) 或密码 (PASSWD) 未配置！")

        emails = [email.strip() for email in emails_str.split('||') if email.strip()]
        passwords = [pwd.strip() for pwd in passwords_str.split('||') if pwd.strip()]

        if len(emails) != len(passwords):
            raise ValueError(f"邮箱数量 ({len(emails)}) 与密码数量 ({len(passwords)}) 不匹配！")

        if not emails:
            raise ValueError("未找到有效的邮箱和密码配置！")

        configs = []
        for email, password in zip(emails, passwords):
            config = {
                'email': email,
                'password': password,
                'account_id': email,  # 使用邮箱作为账号标识
                'base_url': self.base_url,
                'logged_in': False  # 登录状态标记
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
        
        return success == 0 and "已经签到过了" in message

    def login(self, account_config: Dict[str, Any]) -> bool:
        """登录iKuuu账号"""
        login_url = f"{account_config['base_url']}/auth/login"
        print(f"      login_url = {login_url}")

        # 设置session headers
        self.session.headers.update({
            'origin': account_config['base_url'],
            'referer': f"{account_config['base_url']}/auth/login"
        })

        data = {
            'email': account_config['email'],
            'passwd': account_config['password']
        }

        response = self.make_request('POST', login_url, data=data)
        result = response.json()

        ret = result.get('ret', -1)
        login_msg = result.get('msg', '未知错误')

        is_success = ret == 1

        print(f"      ret = {ret}-{'成功' if is_success else '失败'}")
        print(f"      msg = {login_msg}")

        if is_success:
            account_config['logged_in'] = True
        
        return is_success

    def do_checkin(self, account_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行iKuuu签到"""
        if not account_config.get('logged_in'):
            raise Exception("账号未登录，无法执行签到")

        checkin_url = f"{account_config['base_url']}/user/checkin"
        print(f"      checkin_url = {checkin_url}")

        response = self.make_request('POST', checkin_url)
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
        """获取iKuuu用量信息"""        
        try:
            if not account_config.get('logged_in'):
                raise Exception("账号未登录，无法获取用量信息")

            info_url = f"{account_config['base_url']}/user"
            print(f"      info_url = {info_url}")

            response = self.make_request('GET', info_url)
            info_html = response.text

            # 解析剩余流量
            traffic_match = re.search(r'<h4>剩余流量</h4>[\s\S]*?<span class="counter">(\d+(\.\d+)?)</span>', info_html)
            remaining_traffic = traffic_match.group(1) if traffic_match else '未知'

            return {
                'remaining_traffic': remaining_traffic,
                'traffic_unit': 'GB'
            }        
        except Exception as e:
            print(f"      获取用量信息异常: {str(e)}")
            return None
