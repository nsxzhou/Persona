import py_compile
import os
import sys

has_error = False
for root, dirs, files in os.walk('api/app'):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            try:
                py_compile.compile(path, doraise=True)
            except py_compile.PyCompileError as e:
                print(f"Error in {path}: {e}")
                has_error = True

if not has_error:
    print("No syntax errors found!")
    sys.exit(0)
else:
    sys.exit(1)
