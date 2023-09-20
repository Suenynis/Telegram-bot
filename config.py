# config.py - Configuration module

import os

class Config:
    def __init__(self):
        self.admin_ids = []

    def load_config(self):
        # Read the configuration from the .env file or another file
        admin_ids_str = os.getenv('ADMIN_ID', '')
        self.admin_ids = [admin_id.strip() for admin_id in admin_ids_str.split(',')]

    def update_config(self, admin_ids):
        # Update the configuration with new admin IDs
        self.admin_ids = admin_ids

config = Config()
config.load_config()
