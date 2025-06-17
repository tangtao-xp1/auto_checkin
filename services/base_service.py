# services/base_service.py
import os
import requests
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime


class CheckinResult:
    """签到结果类"""
    def __init__(self, 
                 service_name: str, 
                 account_id: str,
                 success: bool, 
                 message: str,
                 checkin_time: str,
                 data: Dict[str, Any] = None):
        self.service_name = service_name
        self.account_id = account_id
        self.success = success
        self.message = message
        self.checkin_time = checkin_time
        self.data = data or {}

    def __str__(self):
        status = "成功" if self.success else "失败"
        return f"[{self.service_name}] {self.account_id} - {status}: {self.message}"


class CheckinService(ABC):
    """
    签到服务的抽象基类。
    """
    # 默认重试配置
    _retry_config = {
        'enabled': False,  # 默认不启用重试
        'max_retries': 3,  # 重试次数
        'delay': 5  # 重试间隔，单位：秒
    }

    @classmethod
    def get_retry_config(cls) -> Dict[str, Any]:
        """
        获取重试配置
        子类可以重写此方法来自定义重试配置
        """
        return cls._retry_config

    def _is_already_checked_in(self, result: Dict[str, Any]) -> bool:
        """
        判断是否已经签到过
        需要子类根据具体服务实现此方法
        """
        raise NotImplementedError("子类必须实现此方法")

    def __init__(self):
        self.session = requests.Session()
        self.config = self.load_config()

    def load_config(self) -> Dict[str, str]:
        """加载HTTP配置"""
        return {
            'user_agent': os.environ.get('USER_AGENT', 
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'),
            'timeout': 30
        }

    def make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """统一的HTTP请求方法"""
        # 设置默认headers
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        
        if self.config.get('user_agent'):
            kwargs['headers']['user-agent'] = self.config['user_agent']
        
        # 设置超时
        kwargs['timeout'] = self.config['timeout']
        
        # 发起请求
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    @property
    @abstractmethod
    def service_name(self) -> str:
        """返回服务的可读名称，用于日志和通知。"""
        pass

    @abstractmethod
    def get_account_configs(self) -> List[Dict[str, Any]]:
        """从环境变量解析账号配置，返回账号配置列表"""
        pass

    @abstractmethod
    def login(self, account_config: Dict[str, Any]) -> bool:
        """登录账号，返回是否成功。对于基于cookie的服务，此方法为空实现"""
        pass

    @abstractmethod
    def do_checkin(self, account_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行签到，返回签到结果数据"""
        pass

    @abstractmethod
    def get_usage_info(self, account_config: Dict[str, Any]) -> Dict[str, Any]:
        """获取用量信息，返回用量数据"""
        pass

    def _desensitize_account_id(self, account_id: str) -> str:
        """简单的账号脱敏处理，保留前3位和后3位，中间用*代替"""
        if len(account_id) <= 6:
            return account_id  # 太短的账号不做处理
        return account_id[:3] + '*' * (len(account_id) - 6) + account_id[-3:]

    def process_single_account(self, account_config: Dict[str, Any]) -> CheckinResult:
        """处理单个账号的完整流程"""
        account_id = account_config.get('account_id', '未知账号')
        checkin_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        retry_config = self.get_retry_config()
        
        try:
            print(f"  - 开始处理账号: {self._desensitize_account_id(account_id)}")
            
            # 步骤1: 登录
            print(f"    * 正在登录...")
            login_success = self.login(account_config)
            if not login_success:
                return CheckinResult(
                    service_name=self.service_name,
                    account_id=account_id,
                    success=False,
                    message="登录失败",
                    checkin_time=checkin_time
                )
            
            # 步骤2: 签到
            print(f"    * 正在执行签到...")
            checkin_result = None
            retries = 0
            while retries < retry_config['max_retries']:
                try:
                    checkin_result = self.do_checkin(account_config)
                    
                    # 如果已经签到过，直接返回结果
                    if self._is_already_checked_in(checkin_result):
                        print(f"      已签到过，无需重试，视为处理成功")
                        checkin_result['success'] = True
                        checkin_result['message'] = checkin_result.get('message', '已签到过')
                        break
                    
                    # 如果签到成功，直接返回
                    if checkin_result.get('success', False):
                        print(f"      签到成功")
                        break
                    
                    # 需要重试的情况
                    retries += 1
                    if retries < retry_config['max_retries']:
                        print(f"      第 {retries} 次重试，等待 {retry_config['delay']} 秒...")
                        time.sleep(retry_config['delay'])
                    else:
                        print(f"      达到最大重试次数")
                        
                except Exception as e:
                    retries += 1
                    if retries < retry_config['max_retries']:
                        print(f"      发生异常: {str(e)}，第 {retries} 次重试，等待 {retry_config['delay']} 秒...")
                        time.sleep(retry_config['delay'])
                    else:
                        print(f"      达到最大重试次数，签到失败: {str(e)}")
                        checkin_result = {
                            'success': False,
                            'message': f'签到失败: {str(e)}'
                        }
                        break
            
            # 步骤3: 获取用量信息
            print(f"    * 正在获取用量信息...")
            try:
                usage_info = self.get_usage_info(account_config)
                if usage_info is None:
                    usage_info = {'usage_error': '获取用量信息失败'}
            except Exception as e:
                print(f"      获取用量信息失败: {str(e)}")
                usage_info = {'usage_error': f'获取用量信息失败: {str(e)}'}
            
            # 合并数据
            result_data = {**(checkin_result or {}), **usage_info}
            
            print(f"    * 账号 {self._desensitize_account_id(account_id)} 处理完成")
            return CheckinResult(
                service_name=self.service_name,
                account_id=account_id,
                success=checkin_result.get('success', False) if checkin_result else False,
                message=checkin_result.get('message', '签到完成') if checkin_result else '签到失败',
                checkin_time=checkin_time,
                data=result_data
            )
            
        except Exception as e:
            print(f"    * 账号 {self._desensitize_account_id(account_id)} 处理失败: {str(e)}")
            return CheckinResult(
                service_name=self.service_name,
                account_id=account_id,
                success=False,
                message=f"处理失败: {str(e)}",
                checkin_time=checkin_time
            )

    def run(self) -> List[CheckinResult]:
        """
        执行完整的签到流程。
        返回所有账号的处理结果列表。
        """
        print("-" * 50)
        print(f"开始执行服务: 【{self.service_name}】")
        
        try:
            # 获取所有账号配置
            account_configs = self.get_account_configs()
            if not account_configs:
                print(f"  - 未找到任何账号配置")
                return []
            
            print(f"  - 找到 {len(account_configs)} 个账号")
            
            # 处理每个账号
            results = []
            for i, account_config in enumerate(account_configs, 1):
                print(f"  - 处理第 {i}/{len(account_configs)} 个账号")
                result = self.process_single_account(account_config)
                results.append(result)
            
            success_count = sum(1 for r in results if r.success)
            print(f"服务【{self.service_name}】执行完成: {success_count}/{len(results)} 个账号成功")
            
        except Exception as e:
            print(f"服务【{self.service_name}】执行失败: {str(e)}")
            results = [CheckinResult(
                service_name=self.service_name,
                account_id="配置错误",
                success=False,
                message=f"服务配置错误: {str(e)}",
                checkin_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )]
        
        print("-" * 50 + "\n")
        return results
