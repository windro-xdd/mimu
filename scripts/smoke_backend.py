"""Smoke test script for backend imports and app creation."""

from __future__ import annotations

import sys


def main() -> None:
    """Test that the backend app can be imported and created without errors."""
    try:
        # Test import of create_app
        from backend import create_app
        
        # Test app creation
        app = create_app()
        
        # Test app context
        with app.app_context():
            # Test that we can access the app config
            _ = app.config
            
        print("✅ Backend smoke test passed!")
        print("✅ Successfully imported create_app")
        print("✅ Successfully created Flask app")
        print("✅ Successfully pushed app context")
        return 0
        
    except Exception as e:
        print(f"❌ Backend smoke test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())