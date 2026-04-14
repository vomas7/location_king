#!/usr/bin/env python3
"""
Test Location King setup without Docker
"""

import os
import sys
import subprocess

def check_python():
    print("🐍 Checking Python...")
    try:
        result = subprocess.run([sys.executable, '--version'], capture_output=True, text=True)
        print(f"  ✅ {result.stdout.strip()}")
        return True
    except Exception as e:
        print(f"  ❌ Python error: {e}")
        return False

def check_requirements():
    print("📦 Checking requirements...")
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    req_file = os.path.join(backend_dir, 'requirements.txt')
    
    if os.path.exists(req_file):
        print(f"  ✅ requirements.txt found")
        with open(req_file, 'r') as f:
            deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            print(f"  📋 {len(deps)} dependencies listed")
        return True
    else:
        print("  ❌ requirements.txt not found")
        return False

def check_env():
    print("⚙️  Checking environment...")
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    
    if os.path.exists(env_file):
        print("  ✅ .env file found")
        # Read and show non-sensitive info
        with open(env_file, 'r') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            for line in lines[:5]:  # Show first 5 lines
                if 'PASSWORD' not in line and 'TOKEN' not in line:
                    print(f"    {line}")
        return True
    else:
        print("  ❌ .env file not found")
        return False

def check_structure():
    print("📁 Checking project structure...")
    required_dirs = [
        'backend',
        'backend/app',
        'backend/alembic',
        'frontend',
        'nginx/conf.d'
    ]
    
    all_ok = True
    for dir_path in required_dirs:
        full_path = os.path.join(os.path.dirname(__file__), dir_path)
        if os.path.exists(full_path):
            print(f"  ✅ {dir_path}/")
        else:
            print(f"  ❌ {dir_path}/ - missing")
            all_ok = False
    
    return all_ok

def check_frontend():
    print("🌐 Checking frontend...")
    index_file = os.path.join(os.path.dirname(__file__), 'frontend', 'index.html')
    
    if os.path.exists(index_file):
        print("  ✅ index.html found")
        # Check for ESRI integration
        with open(index_file, 'r') as f:
            content = f.read()
            if 'server.arcgisonline.com' in content:
                print("  ✅ ESRI World Imagery configured")
            else:
                print("  ⚠️  ESRI not found in index.html")
        return True
    else:
        print("  ❌ index.html not found")
        return False

def main():
    print("🔍 Location King Setup Test")
    print("=" * 40)
    
    tests = [
        check_python,
        check_structure,
        check_env,
        check_requirements,
        check_frontend
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    passed = sum(results)
    total = len(results)
    
    print("📊 Summary:")
    print(f"  ✅ {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All checks passed! Project structure is ready.")
        print("\n🚀 Next steps:")
        print("   1. Install Docker (if needed for production)")
        print("   2. Run: ./deploy.sh")
        print("   3. Configure DNS for locationking.ru")
    else:
        print("\n⚠️  Some checks failed. Please fix issues above.")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)