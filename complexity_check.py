import ast
import os

class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.complexity = 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)

def analyze_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content)
        
        results = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visitor = ComplexityVisitor()
                visitor.visit(node)
                if visitor.complexity > 6:
                    results.append((node.name, node.lineno, visitor.complexity))
        
        if results:
            print(f"File: {filepath}")
            for name, lineno, complexity in sorted(results, key=lambda x: x[2], reverse=True):
                print(f"  Line {lineno}: {name} (Complexity: {complexity})")
    except Exception as e:
        pass

for root, dirs, files in os.walk("api/app"):
    for file in files:
        if file.endswith(".py"):
            analyze_file(os.path.join(root, file))
