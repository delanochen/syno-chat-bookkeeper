import os
import requests
import json

CONFIG_PATH = 'rob_config.json'

def download_image(url, save_dir, filename=None):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    if not filename:
        filename = url.split('/')[-1]
    save_path = os.path.join(save_dir, filename)
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open(save_path, 'wb') as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)
        return save_path
    return None

# 简单商品自动分类（可扩展）
def auto_categorize(details):
    mapping = {
        '食品': ['food', 'snack', 'grocery', '超市', '食品'],
        '交通': ['bus', 'taxi', 'uber', '交通'],
        '加油': ['gas', 'fuel', '加油'],
        '文具': ['stationery', 'pen', 'notebook', '文具'],
        '衣帽': ['clothes', 'hat', '衣服', '帽']
    }
    for cat, keywords in mapping.items():
        for kw in keywords:
            if kw.lower() in details.lower():
                return cat
    return '其它'

def get_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def set_config(data):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2) 