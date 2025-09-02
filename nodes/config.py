import configparser
import os

class ConfigManager:
    def __init__(self):
        self.config = configparser.ConfigParser()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(os.path.dirname(current_dir), 'config.ini')
        self.config.read(config_path)

    def get_api_config(self):
        oneapi_url = self.config.get('API', 'BASE_URL')
        oneapi_token = self.config.get('API', 'KEY')
        return oneapi_url, oneapi_token

    def set_api_key(self, key):
        """设置新的API KEY并保存到配置文件"""
        if not self.config.has_section('API'):
            self.config.add_section('API')
        self.config.set('API', 'KEY', key)
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(os.path.dirname(current_dir), 'config.ini')
        with open(config_path, 'w') as configfile:
            self.config.write(configfile)