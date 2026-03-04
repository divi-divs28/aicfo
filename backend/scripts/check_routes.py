"""
Check if all routes are properly registered in the FastAPI app
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server import app

print("\n" + "="*60)
print("REGISTERED ROUTES")
print("="*60)

admin_routes = []
other_routes = []

for route in app.routes:
    if hasattr(route, 'path'):
        if '/admin/' in route.path:
            admin_routes.append((route.path, route.methods if hasattr(route, 'methods') else []))
        else:
            other_routes.append((route.path, route.methods if hasattr(route, 'methods') else []))

print(f"\n[OK] Admin Routes ({len(admin_routes)}):")
for path, methods in sorted(admin_routes):
    methods_str = ', '.join(sorted(methods)) if methods else 'N/A'
    print(f"   {methods_str:20} {path}")

if not admin_routes:
    print("   [WARNING] NO ADMIN ROUTES FOUND!")
    print("   This is the problem - admin endpoints are not registered")

print(f"\n[INFO] Other API Routes ({len(other_routes)}):")
for path, methods in sorted(other_routes)[:10]:  # Show first 10
    methods_str = ', '.join(sorted(methods)) if methods else 'N/A'
    print(f"   {methods_str:20} {path}")

if len(other_routes) > 10:
    print(f"   ... and {len(other_routes) - 10} more routes")

print("\n" + "="*60)

