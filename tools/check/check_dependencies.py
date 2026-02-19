import sys

print("Checking dependencies...")

dependencies = [
    'Flask',
    'psycopg2-binary',
    'pymysql',
    'sqlalchemy',
    'python-dateutil',
    'pandas',
    'openpyxl'
]

for dep in dependencies:
    try:
        __import__(dep)
        print(f"✓ {dep} is installed")
    except ImportError as e:
        print(f"✗ {dep} is not installed: {e}")

print("\nChecking specific modules...")

try:
    from app import create_app
    print("✓ app module is importable")
except Exception as e:
    print(f"✗ app module is not importable: {e}")
    import traceback
    traceback.print_exc()
