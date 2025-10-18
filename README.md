# 自动签到服务

一个基于Python的多平台自动签到工具，目前支持GLaDOS和iKuuu等机场服务的自动签到。

## 🚀 功能特性

- 🔄 **多平台支持**：支持GLaDOS、iKuuu等多个服务
- 💡 **智能状态管理**：以北京时间为准，自动记录当天签到状态，跳过已成功任务，仅重试失败项，避免重复执行。
- 📊 **详细日志与报告**：完整的签到过程日志记录，并将每日最终状态作为报告输出。
- 🛡️ **异常处理**：完善的错误处理和重试机制。
- 📈 **用量统计**：自动获取账号剩余流量等信息。
- 🔧 **灵活配置**：支持多账号配置和自定义参数。
- 📱 **易于扩展**：基于抽象基类的插件化架构。

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
| GH_ACCESS_TOKEN | 是 | 用于开启“每日状态与增量执行”模式的GitHub Token，**强烈建议配置** |
| GR_COOKIE  |  否  |  GLaDOS的登录cookie，支持多账号，每个账号的cookie用两个竖线隔开  |
| GLADOS_BASE_URL  |  否  |  GLaDOS的网址，默认填https://glados.one  |
| EMAIL  |  否  |  ikuuu的登录账号邮箱，支持多账号，用两个竖线隔开  |
| PASSWD |  否  |  ikuuu的登录账号密码，支持多账号，用两个竖线隔开  |
| IKUUU_BASE_URL  |  否  |  ikuuu的网址，默认填https://ikuuu.org  |
| USER_AGENT  |  否  |  请求时使用的user_agent标识字符串  |
| SERVERCHAN_KEY  |  否  |  Server酱密钥，不新建则不会使用Server酱推送消息  |
| PUSHPLUS_TOKEN  |  否  |  pushplus密钥，不新建则不会使用pushplus推送消息  |
| TG_BOT_TOKEN  |  否  |  telegram bot密钥，不新建则不会使用tg推送消息  |
| TG_CHAT_ID  |  否  |  telegram chat id，不新建则不会使用tg推送消息  |

3. 到`Actions`中创建一个workflow，运行一次。此后项目每天会在 **UTC 17:10 和 23:10**（即 **北京时间次日凌晨 1:10 和早上 7:10**）自动运行。这样的时间安排确保了两次执行都落在同一个北京日期内，以实现可靠的状态恢复。
4. 最后，可以到Actions的workflow日志中的Run sign部分查看签到情况，同时也可以推送到Sever酱/pushplus/telegram查看签到详情。

### ✨ 每日状态与增量执行

为了优化效率并提供更清晰的报告，项目引入了基于北京日期的状态管理机制。启用后，脚本会通过 GitHub Actions 的 Artifact 功能，以天（UTC+8）为单位持久化签到状态。

**工作原理**:
- **时区校准**：所有签到逻辑均以 **北京时间 (UTC+8)** 为基准。
- **状态持久化**：脚本通过读写一个名为 `status.json` 的文件来记录每个账号的签到状态（成功/失败、信息、时间等）。
- **跨流程传递**：
    1.  每次运行时，首先会尝试下载当天（北京时间）上一次运行产生的 `status.json` 文件。
    2.  执行任务时，自动跳过 `status.json` 中已记录为成功的账号，仅运行失败或未执行的账号。
    3.  运行结束后，将本次运行与历史状态合并，生成一份完整的当日签到报告 `status.json`。
    4.  这份最新的 `status.json` 会被上传为以当天日期命名的工件 (Artifact)，供下一次运行使用。
- **最终报告**：最终的通知内容会合并当天所有运行的结果，提供一个完整的当日报告。如果所有已配置的账号在当天均已成功签到，程序将提前退出，不再发送通知。

**如何启用**:

1. **生成 GitHub Token**:
   - 前往 `GitHub` → `Settings` → `Developer settings` → `Personal access tokens` → `Tokens (classic)`。
   - 点击 `Generate new token` → `Generate new token (classic)`。
   - **Note** 填写 `auto_checkin`，**Expiration** 选择 `No expiration` 或你希望的有效期。
   - **Select scopes** 勾选 `repo` 权限。此权限是必需的，因为它允许 Action 通过 `gh` 命令行工具下载历史工件。
   - 点击 `Generate token` 并**立即复制生成的 Token**。

2. **添加到仓库 Secrets**:
   - 回到你的项目仓库，进入 `Settings` → `Secrets and variables` → `Actions`。
   - 在 `Repository secrets` 中点击 `New repository secret`。
   - **Name** 填写 `GH_ACCESS_TOKEN`。
   - **Secret** 粘贴上一步复制的 Token。

完成以上步骤后，智能状态管理功能将自动启用。如果想恢复原有的完整签到模式，只需删除 `GH_ACCESS_TOKEN` 这个 Secret 即可。

### 推送说明
1. 该脚本可选择采用<a href='https://sct.ftqq.com/'>Server酱</a>或<a href = 'https://www.pushplus.plus/'>pushplus</a>或telegram的推送方式
2. 想使用哪一种推送方式就将密钥填入参数。例如要使用Server酱，只需要设置actions变量SERVERCHAN_KEY，并为该变量填入Server酱密钥即可
3. 如若不想使用推送，删除对应的actions变量即可。例如在actions中删除或不设置变量SERVERCHAN_KEY，则不会使用Server酱推送
4. 同时设置SERVERCHAN_KEY和PUSHPLUS_TOKEN，则会同时使用Server酱和pushplus进行推送，同理telegram

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

# iKuuu基础URL（可选，默认为https://ikuuu.org）
IKUUU_BASE_URL="https://ikuuu.org"
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
├── status_manager.py       # 状态管理工具，用于读写 status.json
├── notifications.py        # 通知实现方法
├── batch_del_workflows.py  # 单独可执行代码，用于删除批量删除action执行历史
├── services/
│   ├──base_service.py      # 抽象基类
│   ├── glados_service.py   # GLaDOS服务实现
│   └── ikuuu_service.py    # iKuuu服务实现
├── README.md
└── requirements.txt
```

## 🗺️ 未来计划

- **代码结构优化**：优化当前 Python 文件的目录结构，使其更加清晰。
- **服务实现增强**：优化现有签到服务的实现逻辑。
- **新服务支持**：增加对 `serv00` 的延期签到支持。

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

### 重试机制说明

服务类可以通过重写`_retry_config`类变量来自定义重试行为：

```python
class NewService(CheckinService):
    # 重试配置
    _retry_config = {
        'enabled': True,     # 是否启用重试
        'max_retries': 3,    # 最大重试次数
        'delay': 5          # 重试间隔（秒）
    }
```

重试机制的工作流程：
1. 当签到失败时，系统会自动进行重试
2. 每次重试前会等待指定的延迟时间
3. 达到最大重试次数后仍未成功，则返回失败结果
4. 如果检测到已经签到过（通过`_is_already_checked_in`方法），则不会进行重试

注意事项：
- 默认情况下重试机制是禁用的（`enabled=False`）
- 建议根据服务的稳定性来配置重试参数
- 重试间隔不宜设置过短，以免对服务器造成压力

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

### v1.2.0
- **时区统一**：修复了时区问题，GitHub Action 触发时间虽为 UTC，但所有签到状态判断均以北京时间（UTC+8）为准。
- **Action 时间优化**：调整 Action 触发时间为 UTC `17:10` 和 `23:10`，确保两次运行落在同一北京日，保证状态恢复的可靠性。
- **核心逻辑重构**：
  - 优化 `main.py` 逻辑，移除冗余的增量标志。
  - `status.json` 现在作为完整的每日签到报告，包含每个账号的详细状态。
  - 对于未配置任何服务的用户，程序会提前退出，不再发送不必要的消息。
- **代码结构调整**：重命名 `github_util.py` 为 `status_manager.py`，使其职责更清晰。

### v1.1.0
- 新增“增量签到模式”，可以减少重复签到和重复发送消息的次数

### v1.0.0
- 初始版本发布
- 支持GLaDOS和iKuuu自动签到
- 完善的错误处理和日志记录
- 支持多账号配置

## ⚠️ 免责声明

本工具仅供学习和研究使用，请遵守相关服务的使用条款。使用本工具产生的任何后果由使用者自行承担。
