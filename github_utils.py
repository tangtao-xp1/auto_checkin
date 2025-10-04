import json
import os

STATUS_FILE_NAME = "status.json"

def read_prior_status() -> dict:
    """
    读取由 GitHub Action 下载到本地的先前状态文件 (status.json)。

    :return: 一个包含已成功服务状态的字典，例如 {'GLaDOS': True}。如果文件不存在或为空，则返回空字典。
    """
    if not os.path.exists(STATUS_FILE_NAME):
        print(f"'{STATUS_FILE_NAME}' not found. Assuming first run of the day.")
        return {}
    
    try:
        with open(STATUS_FILE_NAME, 'r', encoding='utf-8') as f:
            # 处理文件可能为空的情况
            content = f.read()
            if not content:
                print(f"'{STATUS_FILE_NAME}' is empty. Assuming first run of the day.")
                return {}
            status_data = json.loads(content)
            print(f"Successfully read prior status: {status_data}")
            return status_data
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading or parsing '{STATUS_FILE_NAME}': {e}")
        return {} # 出错时返回空字典，确保主流程能继续

def write_current_status(data: dict):
    """
    将当前成功状态写入本地的 status.json 文件，以便 GitHub Action 后续上传。

    :param data: 要写入的状态字典。
    """
    try:
        with open(STATUS_FILE_NAME, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Current status written to '{STATUS_FILE_NAME}': {data}")
    except IOError as e:
        print(f"Error writing to '{STATUS_FILE_NAME}': {e}")