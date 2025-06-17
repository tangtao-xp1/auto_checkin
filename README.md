# 自动签到服务

一个基于Python的多平台自动签到工具，目前支持GLaDOS和iKuuu等机场服务的自动签到。

## 🚀 功能特性

- 🔄 **多平台支持**：支持GLaDOS、iKuuu等多个服务
- 📊 **详细日志**：完整的签到过程日志记录
- 🛡️ **异常处理**：完善的错误处理和重试机制  
- 📈 **用量统计**：自动获取账号剩余流量等信息
- 🔧 **灵活配置**：支持多账号配置和自定义参数
- 📱 **易于扩展**：基于抽象基类的插件化架构

## 📋 支持的服务

| 服务 | 状态 | 认证方式 | 备注 |
|------|------|----------|------|
| GLaDOS | ✅ | Cookie | 支持多账号 |
| iKuuu | ✅ | 邮箱+密码 | 支持多账号 |

## 🚦 使用方法
 
1. 右上角Fork此仓库
2. 然后到`Settings`→`Secrets and variables`→`Actions`→`Repository secrets`→`New repository secrets` 新建以下参数：

| 参数   |  是否必需  | 内容  | 
| ------------ |  ------------ |  ------------ |
| GR_COOKIE  |  否  |  GLaDOS的登录cookie，支持多账号，每个账号的cookie用两个竖线隔开  |
| GLADOS_BASE_URL  |  否  |  GLaDOS的网址，默认填https://glados.one  |
| EMAIL  |  否  |  ikuuu的登录账号邮箱，支持多账号，用两个竖线隔开  |
| PASSWD |  否  |  ikuuu的登录账号密码，支持多账号，用两个竖线隔开  |
| IKUUU_BASE_URL  |  否  |  ikuuu的网址，默认填https://ikuuu.one  |
| USER_AGENT  |  否  |  请求时使用的user_agent标识字符串  |
| SERVERCHAN_KEY  |  否  |  Server酱密钥，不新建则不会使用Server酱推送消息  |
| PUSHPLUS_TOKEN  |  否  |  pushplus密钥，不新建则不会使用pushplus推送消息  |
| TG_BOT_TOKEN  |  否  |  telegrame bot密钥，不新建则不会使用tg推送消息  |
| TG_CHAT_ID  |  否  |  telegrame chat id，不新建则不会使用tg推送消息  |

3. 到`Actions`中创建一个workflow，运行一次，以后每天项目都会在北京时间6点自动运行
4. 最后，可以到Actions的workflow日志中的Run sign部分查看签到情况，同时也可以推送到Sever酱/pushplus/telegram查看签到详情

### 推送说明
1. 该脚本可选择采用<a href='https://sct.ftqq.com/'>Server酱</a>或<a href = 'https://www.pushplus.plus/'>pushplus</a>或telegrame的推送方式
2. 想使用哪一种推送方式就将密钥填入参数。例如要使用Server酱，只需要设置actions变量SERVERCHAN_KEY，并为该变量填入Server酱密钥即可
3. 如若不想使用推送，删除对应的actions变量即可。例如在actions中删除或不设置变量SERVERCHAN_KEY，则不会使用Server酱推送
4. 同时设置SERVERCHAN_KEY和PUSHPLUS_TOKEN，则会同时使用Server酱和pushplus进行推送，同理telegrame

### GLaDOS变量配置说明

```bash
# GLaDOS Cookie（多个账号用||分隔）
GR_COOKIE="koa:sess=xxxx; koa:sess.sig=xxx||koa:sess=xxxx; koa:sess.sig=xxx"

# GLaDOS基础URL（可选，默认为https://glados.one）
GLADOS_BASE_URL="https://glados.one"
```
GLADOS的cookie获取办法：`登录glados`→`首页`→`会员签到`→`打开Chrome开发者工具`→`点击签到`→`在Chrom开发者工具中查询cookie`
具体获取cookie的操作见下图
![get_cookie](https://github.com/user-attachments/assets/68870bee-9542-4485-bfe5-f3de58aa5c0c)


### iKuuu变量配置说明

```bash
# iKuuu邮箱（多个账号用||分隔）
EMAIL="user1@example.com||user2@example.com"

# iKuuu密码（多个账号用||分隔，需与邮箱一一对应）
PASSWD="password1||password2"

# iKuuu基础URL（可选，默认为https://ikuuu.one）
IKUUU_BASE_URL="https://ikuuu.one"
```

### 通用配置（可选）

```bash
# User-Agent
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
```

## 🏗️ 项目结构

```
auto_checkin/
├── main.py                 # 主程序入口
├── notifications.py        # 通知实现方法
├── services/
│   ├──base_service.py      # 抽象基类
│   ├── glados_service.py   # GLaDOS服务实现
│   └── ikuuu_service.py    # iKuuu服务实现
├── README.md
└── requirements.txt
```

## 🔧 开发指南

### 添加新服务

1. 在`services/`目录下创建新的服务文件
2. 继承`CheckinService`抽象基类
3. 实现所有抽象方法：

```python
from base_service import CheckinService

class NewService(CheckinService):
    @property
    def service_name(self) -> str:
        return "新服务名称"
    
    def get_account_configs(self) -> List[Dict[str, Any]]:
        # 实现账号配置解析
        pass
    
    def login(self, account_config: Dict[str, Any]) -> bool:
        # 实现登录逻辑
        pass
    
    def do_checkin(self, account_config: Dict[str, Any]) -> Dict[str, Any]:
        # 实现签到逻辑，必须返回包含success和message的字典
        pass
    
    def get_usage_info(self, account_config: Dict[str, Any]) -> Dict[str, Any]:
        # 实现用量信息获取
        pass
```

4. 在`main.py`中注册新服务

### 签到结果格式

`do_checkin`方法必须返回包含以下字段的字典：

```python
{
    'success'         : bool,      # 签到是否成功
    'message'         : str,       # 签到结果消息
    'checkin_response': obj,       # 签到结果数据
}
```

## 📝 更新日志

### v1.0.0
- 初始版本发布
- 支持GLaDOS和iKuuu自动签到
- 完善的错误处理和日志记录
- 支持多账号配置

## ⚠️ 免责声明

本工具仅供学习和研究使用，请遵守相关服务的使用条款。使用本工具产生的任何后果由使用者自行承担。
