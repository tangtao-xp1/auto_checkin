import json
import os

STATUS_FILE_NAME = "status.json"

import os
import json
import glob

STATUS_FILE_NAME = "status.json"

def read_prior_status() -> dict:
    """
    读取由 GitHub Action 下载到本地的先前状态文件 (status.json)。
    优先读取根目录，若不在根目录则递归搜索子目录。
    """
    target_path = STATUS_FILE_NAME

    # 1. 如果根目录不存在 status.json，全局递归搜索所有子目录下的 status.json
    if not os.path.exists(target_path):
        # 搜索当前目录及任意子目录下的 status.json
        found_files = glob.glob(f"**/{STATUS_FILE_NAME}", recursive=True)
        if found_files:
            target_path = found_files[0]
            print(f"found in sub directory: {target_path}")

    # 2. 如果依然找不到文件，判定为首次运行
    if not os.path.exists(target_path):
        print(f"'{STATUS_FILE_NAME}' not found. Assuming first run of the day.")
        return {}

    try:
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                print(f"'{target_path}' is empty. Assuming first run of the day.")
                return {}
            status_data = json.loads(content)
            print(f"Successfully read prior status from '{target_path}': {status_data}")
            return status_data
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading or parsing '{target_path}': {e}")
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
