# services/glados_service.py
import os
import json
import hashlib
from typing import List, Dict, Any
from .base_service import CheckinService


class GLaDOSService(CheckinService):
    """GLaDOS 签到服务。"""

    # glados经常出现签到失败的情况，启用重试，自定义重试配置，
    _retry_config = {
        'enabled': True,  # 启用重试
        'max_retries': 3,  # 重试次数
        'delay': 10  # 重试间隔，单位：秒
    }

    def __init__(self):
        super().__init__()
        self.base_url = os.environ.get('GLADOS_BASE_URL', 'https://glados.cloud')

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
            fields = {}
            for part in cookie.split(';'):
                key, separator, value = part.strip().partition('=')
                if separator:
                    fields[key] = value.strip()
            if fields.get('gld:sess.sig'):
                # 使用完整签名生成标识，避免相同前缀的账号共用签到状态。
                account_id = 'gld-' + hashlib.sha256(
                    fields['gld:sess.sig'].encode('utf-8')
                ).hexdigest()[:24]
            elif fields.get('koa:sess.sig'):
                # 保留旧格式的账号标识，兼容已有签到记录。
                account_id = fields['koa:sess.sig'][:10] + '...'
            else:
                account_id = 'cookie-' + hashlib.sha256(
                    cookie.encode('utf-8')
                ).hexdigest()[:24]
    
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
        GLaDOS的签到重复判断：
        - code = 1 且 message 包含 "Checkin Repeats"
        """
        if not isinstance(result, dict):
            return False
            
        success = result.get('success', False)
        message = result.get('message', '')
        
        return success is False and "Checkin Repeats" in message

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
            data=json.dumps({'token': 'glados.cloud'}) # 请求要上传固定参数
        )
        
        checkin_data = response.json()
        code = checkin_data.get('code', -1)        
        message = checkin_data.get('message', '未知结果')
        print(f"      code = {code}{'-成功' if code == 0 else '-失败'}")
        print(f"      message = {message}")
        
        return {
            'success': (code == 0),
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
