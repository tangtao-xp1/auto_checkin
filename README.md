# 自动签到服务

一个基于 Python 的多平台自动签到工具，目前支持 GLaDOS、iKuuu 和 WorkBuddy。

## 🚀 功能特性

- 🔄 **多平台支持**：支持GLaDOS、iKuuu等多个服务
- 💡 **智能状态管理**：以北京时间为准，自动记录当天签到状态，跳过已成功任务，仅重试失败项，避免重复执行。
- 📊 **详细日志与报告**：完整的签到过程日志记录，并将每日最终状态作为报告输出。
- 🛡️ **异常处理**：完善的错误处理和重试机制。
- 🔧 **灵活配置**：支持多账号配置和自定义参数。
- 📱 **易于扩展**：基于抽象基类的插件化架构。

## 📋 支持的服务

| 服务   | 状态 | 认证方式 | 备注                                                                                                                          |
| ------ | ---- | -------- | ----------------------------------------------------------------------------------------------------------------------------- |
| GLaDOS | ✅   | Cookie   | 支持多账号                                                                                                                    |
| iKuuu  | ✅   | Cookie   | 支持多账号，从2026年4月4日起，ikuuu不再支持通过邮箱+密码的API方式登录签到，需使用浏览器Cookie方式。剩余流量信息暂不支持获取。 |
| WorkBuddy | ✅ | Bearer Token | 支持多账号；从 Windows 客户端本地登录态提取，Token 过期后需要重新导出。 |

## 🚦 使用方法

1. 右上角Fork此仓库
2. 然后到`Settings`→`Secrets and variables`→`Actions`→`Repository secrets`→`New repository secrets` 新建以下参数：

| 参数            | 是否必需 | 内容                                                                                                        |
| --------------- | -------- | ----------------------------------------------------------------------------------------------------------- |
| GH_ACCESS_TOKEN | 是       | 用于开启“每日状态与增量执行”模式的GitHub Token，**强烈建议配置**                                            |
| GR_COOKIE       | 否       | GLaDOS的登录cookie，支持多账号，每个账号的cookie用两个竖线隔开                                              |
| GLADOS_BASE_URL | 否       | GLaDOS的网址，默认填https://glados.cloud                                                                    |
| IKUUU_COOKIE    | 否       | iKuuu的登录cookie，支持多账号，每个账号的cookie用两个竖线隔开                                               |
| WORKBUDDY_ACCOUNTS_JSON | 否 | WorkBuddy 最小登录态 JSON；建议使用本项目工具读取并更新，不要手工拆分 Token。 |
| ~~EMAIL~~       | ~~否~~   | ~~废除，iKuuu的登录邮~~箱                                                                                   |
| ~~PASSWORD~~    | ~~否~~   | ~~废除，iKuuu的登录密~~码                                                                                   |
| IKUUU_BASE_URL  | 否       | iKuuu的网址，默认填https://ikuuu.org                                                                        |
| USER_AGENT      | 否       | 请求时使用的user_agent标识字符串                                                                            |
| SERVERCHAN_KEY  | 否       | Server酱密钥，不新建则不会使用Server酱推送消息                                                              |
| PUSHPLUS_TOKEN  | 否       | pushplus密钥，不新建则不会使用pushplus推送消息                                                              |
| TG_BOT_TOKEN    | 否       | telegram bot密钥，不新建则不会使用tg推送消息，由 @BotFather 生成，格式为**10位数字:一串字符**，全部填写进去 |
| TG_CHAT_ID      | 否       | telegram chat id，不新建则不会使用tg推送消息，tg用户ID，可通过 @userinfobot 查询，是一串数字                |

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

状态文件的新键由“服务名 + 账号标识”共同生成，避免不同服务的相同账号标识互相覆盖；读取时仍兼容旧版仅按账号生成的状态键。

### 推送说明

1. 该脚本可选择采用<a href='https://sct.ftqq.com/'>Server酱</a>或<a href = 'https://www.pushplus.plus/'>pushplus</a>或telegram的推送方式
2. 想使用哪一种推送方式就将密钥填入参数。例如要使用Server酱，只需要设置actions变量SERVERCHAN_KEY，并为该变量填入Server酱密钥即可
3. 如若不想使用推送，删除对应的actions变量即可。例如在actions中删除或不设置变量SERVERCHAN_KEY，则不会使用Server酱推送
4. 同时设置SERVERCHAN_KEY和PUSHPLUS_TOKEN，则会同时使用Server酱和pushplus进行推送，同理telegram

### GLaDOS变量配置说明

```bash
# GLaDOS Cookie（多个账号用||分隔）
GR_COOKIE="gld:sess=gld_xxxx; gld:sess.sig=xxx||gld:sess=gld_yyyy; gld:sess.sig=yyy"

# GLaDOS基础URL（可选，默认为https://glados.cloud）
GLADOS_BASE_URL="https://glados.cloud"
```

GLADOS的cookie获取办法：`登录glados`→`首页`→`会员签到`→`打开Chrome开发者工具`→`点击签到`→`在Chrom开发者工具中查询cookie`
具体获取cookie的操作见下图
![get_cookie](https://github.com/user-attachments/assets/68870bee-9542-4485-bfe5-f3de58aa5c0c)

同时兼容旧的 `koa:sess=...; koa:sess.sig=...` 格式，也可与新格式混合配置。请复制浏览器请求中的原始 Cookie，不要自行给下划线添加反斜杠。新格式按完整签名生成账号标识，避免多账号共用签到状态；旧格式保留原有标识。

### iKuuu变量配置说明

```bash
# iKuuu Cookie（多个账号用||分隔）
IKUUU_COOKIE="cookie_string_1||cookie_string_2"

# iKuuu基础URL（可选，默认为https://ikuuu.org）
IKUUU_BASE_URL="https://ikuuu.org"
```

iKuuu的cookie获取办法：`登录ikuuu网站`→`打开Chrome开发者工具`→`控制台`→`输入 document.cookie`→`复制所有cookie值（默认会有引号，需要手动去掉）`

> **注意**：iKuuu已不再支持通过邮箱+密码的API方式登录签到，需使用浏览器Cookie方式。用量信息由于网页加密，暂不支持获取。

### WorkBuddy 配置说明

WorkBuddy 签到需要以下最小字段，统一保存在一个仓库级 Actions Secret `WORKBUDDY_ACCOUNTS_JSON` 中：

```json
[
  {
    "label": "主账号",
    "access_token": "<访问令牌>",
    "user_id": "<用户ID>",
    "domain": "<登录域>",
    "expires_at": 1790000000000
  }
]
```

- `access_token`、`user_id`、`expires_at` 必填。
- `domain` 可以为空字符串。
- `label` 只用于日志和通知；多账号的 `label` 不能重复。
- `expires_at` 是毫秒时间戳。工具会显示登录态是否已经过期。
- 不要对 JSON 再做 Base64；Base64 不是加密。

#### 1. 在 Windows 读取 WorkBuddy 登录态

当前工具只在 Windows 版 WorkBuddy 上验证。默认只读以下目录，不会修改客户端文件：

```text
%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth
```

先安装工具专用依赖：

```powershell
python -m pip install -r requirements-tools.txt
```

只验证登录态并查看脱敏摘要：

```powershell
python .\tools\export_workbuddy_credentials.py
```

其他平台或未来目录发生变化时，可以显式指定目录：

```powershell
python .\tools\export_workbuddy_credentials.py --auth-dir "D:\path\to\auth"
```

`--auth-dir` 是扩展入口，不代表其他平台已经验证通过。

#### 2. 手工更新 GitHub Secret

运行：

```powershell
python .\tools\export_workbuddy_credentials.py --print-secret
```

工具会明确警告后输出一行敏感 JSON。复制这一整行，然后进入：

```text
GitHub 仓库 → Settings → Secrets and variables → Actions
→ New repository secret
```

名称填写 `WORKBUDDY_ACCOUNTS_JSON`，值粘贴刚才的完整 JSON。不要把输出保存到源码、日志、聊天记录或截图中。

#### 3. 不安装 GitHub CLI，直接自动更新 Secret

工具可以直接使用 GitHub REST API，不依赖 `gh`：

```powershell
python .\tools\export_workbuddy_credentials.py --github-repo OWNER/REPO
```

请把 `OWNER/REPO` 替换为真实仓库，例如 `alice/auto_checkin`。如果没有预先设置 `GITHUB_TOKEN`，工具会使用普通 `input()` 提示输入。Token 会显示在 IDE/终端中，但工具不会保存；请注意控制台记录、录屏和旁观风险。

GitHub Token 可使用以下任一类型：

- Fine-grained personal access token：只授权目标仓库，并授予仓库 `Secrets: Read and write` 权限。
- Classic personal access token：私有仓库需要 `repo` scope。

权限及接口要求可参考 [GitHub Actions Secrets REST API](https://docs.github.com/en/rest/actions/secrets) 和 [GitHub Secret 加密说明](https://docs.github.com/en/rest/guides/encrypting-secrets-for-the-rest-api)。

也可以提前将 Token 放入当前进程环境变量：

```powershell
$env:GITHUB_TOKEN = "<仅在当前 PowerShell 会话使用的 Token>"
python .\tools\export_workbuddy_credentials.py --github-repo OWNER/REPO
Remove-Item Env:\GITHUB_TOKEN
```

不要把 GitHub Token 作为命令行参数；工具只从普通输入或指定的环境变量读取。在共享屏幕、录屏或终端会留存输入的环境中，优先使用临时环境变量。GitHub REST API 要求先获取仓库公钥，再使用 LibSodium 加密 Secret，因此自动更新模式使用 `PyNaCl`，但不需要 GitHub CLI。

#### 4. Token 过期后的处理

目前尚未确认 WorkBuddy 登录态的实际有效期，项目也没有未经验证的自动刷新逻辑。收到“`accessToken 已过期`”通知后：

1. 在 Windows 打开 WorkBuddy 并确认已经登录，让客户端刷新本地登录态。
2. 重新运行手工更新或 REST 自动更新命令。
3. 在 GitHub Actions 中手工触发一次工作流验证。

WorkBuddy 使用的是客户端内部 HTTP 接口，而不是已承诺稳定的公开 API。客户端升级后如果出现“密钥标识不匹配”或接口响应变化，需要同步更新导出和签到实现。

### 文本菜单更新三个服务的 Secret

安装 `requirements-tools.txt` 后，在项目根目录运行（也可在 PyCharm 直接运行该文件）：

```powershell
python .\tools\update_secrets.py
```

菜单支持：

| 选项 | 凭据来源 | 更新的仓库级 Actions Secret |
| --- | --- | --- |
| 1. WorkBuddy | 自动读取本机登录态 | `WORKBUDDY_ACCOUNTS_JSON` |
| 2. iKuuu | 手工粘贴完整 Cookie | `IKUUU_COOKIE` |
| 3. GLaDOS | 手工粘贴完整 Cookie，支持 gld/koa | `GR_COOKIE` |
| 0. 退出 | — | — |

选服务后，按提示输入凭据和 `OWNER/REPO`，检查 Secret 名称、账号数量，再输入 `y` 上传。Cookie 多账号用 `||` 分隔；每次会覆盖整个 Secret，请一次提供该服务全部需要保留的账号。工具不会从 GitHub 读取或合并旧 Secret。

Token 优先读取 `GITHUB_TOKEN`，没有则使用普通输入，兼容 IDE 控制台。Cookie 和 Token 输入会在控制台显示，工具不写入文件；本次运行会复用仓库和 Token，退出后不保存。上传使用现有公钥加密流程。输入校验只检查结构，不代表 Cookie 未过期或签到一定成功。

也可以预设仓库或 WorkBuddy 登录态目录：

```powershell
python .\tools\update_secrets.py --github-repo OWNER/REPO
python .\tools\update_secrets.py --auth-dir "D:\path\to\auth"
```

原来的 `export_workbuddy_credentials.py` 命令及参数保持可用。

### 通用配置（可选）

```bash
# User-Agent
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
```

本地运行时不会再自动注入示例 Cookie。请仅在当前终端设置需要测试的真实环境变量，再执行 `python .\main.py`；这样可以避免占位配置意外触发网络请求。

## 🏗️ 项目结构

```
auto_checkin/
├── main.py                 # 主程序入口
├── status_manager.py       # 状态管理工具，用于读写 status.json
├── notifications.py        # 通知实现方法
├── requirements-tools.txt  # WorkBuddy 本机导出及 GitHub Secret 更新依赖
├── tools/
│   ├── batch_del_workflows.py           # 批量删除 GitHub Actions 历史
│   └── export_workbuddy_credentials.py  # 只读提取最小登录态
├── services/
│   ├── base_service.py     # HTTP签到抽象基类
│   ├── browser_service.py  # 浏览器签到占位，不引入浏览器依赖
│   ├── glados_service.py   # GLaDOS服务实现
│   ├── ikuuu_service.py    # iKuuu服务实现
│   └── workbuddy_service.py # WorkBuddy服务实现
├── README.md
└── requirements.txt
```

### 维护工具

批量删除 GitHub Actions 历史运行记录的脚本已经归入 `tools/`：

```powershell
python .\tools\batch_del_workflows.py --owner YOUR_OWNER --repo YOUR_REPO --count 10
```

其中 `YOUR_OWNER` 和 `YOUR_REPO` 是需要替换的占位符，不是原样输入的固定文本。Token 的读取顺序是 `--gh_token` 参数、`GITHUB_TOKEN` 环境变量、普通交互输入；交互输入会在 PyCharm 等 IDE 终端中明文显示，但脚本不会保存。若不希望 Token 显示，建议仅在当前终端临时设置 `GITHUB_TOKEN`。

脚本会先列出准备删除的运行记录，并要求输入 `yes` 确认。删除工作流历史不可恢复，请先使用较小的 `--count` 核对目标仓库和记录；除非已经人工核对，不要使用 `--force`。

## 🗺️ 未来计划

- **代码结构优化**：继续保持入口编排、服务逻辑、状态和通知职责分离。
- **服务实现增强**：优化现有签到服务的实现逻辑。
- **新服务支持**：后续评估 DDNSTO 七天签到和 newapi 相关网站。
- **浏览器签到**：已经保留 `BrowserCheckinService` 占位；等首个必须使用浏览器的服务确认后，再按真实需求引入 Playwright、登录态和截图机制。

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

### v1.3.0

- **修改ikuuu签到方式**：邮箱+密码的API方式已失效，改为cookie方式；同步更新相关文档。

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
