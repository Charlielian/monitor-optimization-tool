#!/usr/bin/env python3
"""
生成密码哈希工具
用于生成用户密码的哈希值，可以添加到 config.json 中
"""
from werkzeug.security import generate_password_hash
import sys


def main():
    if len(sys.argv) < 2:
        print("用法: python generate_password_hash.py <密码>")
        print("\n示例:")
        print("  python generate_password_hash.py admin123")
        print("  python generate_password_hash.py user123")
        sys.exit(1)
    
    password = sys.argv[1]
    password_hash = generate_password_hash(password)
    
    print(f"\n密码: {password}")
    print(f"哈希: {password_hash}")
    print("\n将此哈希值复制到 config.json 的 auth_config.users 中")
    print("\n示例配置:")
    print(f'''
{{
    "auth_config": {{
        "users": {{
            "username": {{
                "password_hash": "{password_hash}",
                "role": "user",
                "name": "用户名"
            }}
        }}
    }}
}}
''')


if __name__ == "__main__":
    main()
