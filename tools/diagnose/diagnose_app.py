import sys
import traceback

print("Starting diagnosis...")

try:
    print("Importing create_app...")
    from app import create_app
    print("Import successful!")
    
    print("Creating app...")
    app = create_app()
    print("App created successfully!")
    
    print("App configuration:")
    print(f"Host: 0.0.0.0")
    print(f"Port: 5001")
    print(f"Debug: True")
    
    print("\nDiagnosis complete. App appears to be initialized correctly.")
    
except Exception as e:
    print(f"Error: {e}")
    print("\nTraceback:")
    traceback.print_exc()
    print("\nDiagnosis failed. There's an issue with the app initialization.")
