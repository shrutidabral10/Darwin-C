#!/usr/bin/env python3

"""
Compiler module for the evolutionary optimizer
----------------------------------------------
This module handles compiling C code, applying optimizations, and measuring execution time.
"""

import os
import re
import time
import subprocess
import tempfile
import signal
import random
import shutil

# Available optimization techniques
OPTIMIZATIONS = [
    "constant_folding", 
    "loop_unrolling", 
    "copy_propagation",
    "common_subexpression_elimination",
    "dead_code_elimination"
]

def compile_original(source_file, output_dir):
    """Compile the original C source file without extra optimizations."""
    base_name = os.path.basename(source_file).rsplit('.', 1)[0]
    output_path = os.path.join(output_dir, f"{base_name}_original")

    # Standard compilation with basic optimizations
    cmd = ["gcc", "-O0", source_file, "-o", output_path]
    
    try:
        subprocess.run(cmd, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Compilation error for original code: {e.stderr.decode()}")
        return None

def get_execution_time(executable_path, timeout=5):
    """Measure the execution time of a compiled executable."""
    # Run the executable and measure its execution time
    try:
        start_time = time.time()
        result = subprocess.run([executable_path], timeout=timeout, 
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        end_time = time.time()
        
        if result.returncode != 0:
            print(f"Warning: Executable {executable_path} returned non-zero exit code: {result.returncode}")
            print(f"Output: {result.stdout.decode()}")
            print(f"Error: {result.stderr.decode()}")
            return float('inf')  # Return infinity to indicate failure
        
        return end_time - start_time
    except subprocess.TimeoutExpired:
        print(f"Warning: Executable {executable_path} timed out after {timeout} seconds")
        return float('inf')  # Return infinity to indicate timeout
    except Exception as e:
        print(f"Error running executable {executable_path}: {e}")
        return float('inf')  # Return infinity to indicate failure

def apply_constant_folding(code):
    """Apply constant folding optimization to the code."""
    # Replace constant expressions with their computed values
    # Look for simple arithmetic expressions in variable assignments
    pattern = r'(\w+\s*=\s*)(\d+\s*[\+\-\*\/]\s*\d+)(\s*;)'
    
    def replace_expression(match):
        prefix = match.group(1)
        expr = match.group(2)
        suffix = match.group(3)
        
        try:
            # Clean up the expression
            expr = re.sub(r'\s+', '', expr)
            # Safely evaluate simple arithmetic
            if re.match(r'^\d+[\+\-\*\/]\d+$', expr):
                result = eval(expr)
                return f"{prefix}{int(result)}{suffix}"
        except:
            pass
        
        return match.group(0)  # Return original if can't fold
    
    folded_code = re.sub(pattern, replace_expression, code)
    return folded_code

def apply_loop_unrolling(code):
    """Apply loop unrolling optimization to the code."""
    # Find simple for loops with constant iteration counts
    pattern = r'for\s*\(\s*int\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(\d+)\s*;\s*\1\s*<\s*(\d+)\s*;\s*\1\s*\+\+\s*\)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
    
    def unroll_loop(match):
        var_name = match.group(1)
        start_val = int(match.group(2))
        end_val = int(match.group(3))
        loop_body = match.group(4).strip()
        
        # Only unroll short loops with few iterations
        if end_val - start_val > 4 or end_val - start_val <= 0:
            return match.group(0)  # Return original if loop is too long or invalid
        
        unrolled_code = "{\n"
        for i in range(start_val, end_val):
            # Replace variable with its value in the loop body
            iteration_code = loop_body
            # Replace whole-word matches of the variable
            iteration_code = re.sub(r'\b' + re.escape(var_name) + r'\b', str(i), iteration_code)
            unrolled_code += "    " + iteration_code.strip() + "\n"
        unrolled_code += "}"
        
        return unrolled_code
    
    unrolled_code = re.sub(pattern, unroll_loop, code, flags=re.DOTALL)
    return unrolled_code

def apply_copy_propagation(code):
    """Apply copy propagation optimization to the code."""
    # Find simple copy assignments like: int x = y;
    lines = code.split('\n')
    result_lines = []
    
    # Simple approach - look for copies and propagate within a function scope
    copy_vars = {}
    
    for line in lines:
        # Reset copy vars at function boundaries
        if 'int main(' in line or ') {' in line:
            copy_vars = {}
        
        # Check for copy assignment pattern: type var = other_var;
        match = re.search(r'^\s*(?:int|long|float|double|char)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*;', line)
        if match:
            target_var = match.group(1)
            source_var = match.group(2)
            # Only propagate if source is not a function call or complex expression
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', source_var):
                copy_vars[target_var] = source_var
        
        # Apply propagation for known copies
        modified_line = line
        for target_var, source_var in copy_vars.items():
            # Replace whole-word matches of the target variable, but not in declarations
            if not re.search(r'^\s*(?:int|long|float|double|char)\s+' + re.escape(target_var), modified_line):
                modified_line = re.sub(r'\b' + re.escape(target_var) + r'\b', source_var, modified_line)
        
        result_lines.append(modified_line)
        
        # Clear copy vars at end of function
        if line.strip() == '}' and copy_vars:
            copy_vars = {}
    
    return '\n'.join(result_lines)

def apply_common_subexpression_elimination(code):
    """Apply common subexpression elimination to the code."""
    lines = code.split('\n')
    result_lines = []
    
    # Look for repeated arithmetic expressions within a function
    expressions_seen = {}
    temp_var_counter = 0
    in_function = False
    
    for line in lines:
        # Track function boundaries
        if '{' in line and ('int main(' in line or ') {' in line):
            in_function = True
            expressions_seen = {}
            temp_var_counter = 0
        elif line.strip() == '}' and in_function:
            in_function = False
            expressions_seen = {}
        
        if not in_function:
            result_lines.append(line)
            continue
        
        modified_line = line
        
        # Look for simple arithmetic expressions (var op var)
        expr_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*\s*[\+\-\*]\s*[a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(expr_pattern, line)
        
        for expr in matches:
            # Clean up whitespace
            clean_expr = re.sub(r'\s+', ' ', expr.strip())
            
            if clean_expr in expressions_seen:
                # This expression has been seen before
                temp_var = expressions_seen[clean_expr]
                modified_line = modified_line.replace(expr, temp_var)
            else:
                # First time seeing this expression
                # Only create temp var if the expression appears complex enough
                if len(matches) > 1:  # Multiple expressions in this line
                    temp_var = f"cse_temp_{temp_var_counter}"
                    # Insert temp variable declaration
                    indent = len(line) - len(line.lstrip())
                    temp_declaration = ' ' * indent + f"int {temp_var} = {clean_expr};"
                    result_lines.append(temp_declaration)
                    
                    expressions_seen[clean_expr] = temp_var
                    modified_line = modified_line.replace(expr, temp_var)
                    temp_var_counter += 1
        
        result_lines.append(modified_line)
    
    return '\n'.join(result_lines)

def apply_dead_code_elimination(code):
    """Remove unreachable code after return statements."""
    lines = code.split('\n')
    result = []
    in_dead = False
    brace_depth = 0
    dead_start_depth = 0
    
    for line in lines:
        # Count braces to track scope depth
        open_braces = line.count('{')
        close_braces = line.count('}')
        
        # If we're not in dead code and find a return statement
        if not in_dead and 'return' in line and ';' in line:
            result.append(line)
            in_dead = True
            dead_start_depth = brace_depth
            brace_depth += open_braces - close_braces
            continue
        
        # Update brace depth
        brace_depth += open_braces - close_braces
        
        # If we're in dead code, check if we've exited the scope
        if in_dead:
            # If we've closed back to the original scope level or beyond
            if brace_depth <= dead_start_depth:
                in_dead = False
                result.append(line)
            # Otherwise, skip this line (it's dead code)
            continue
        
        # Normal line - not in dead code
        result.append(line)
    
    return '\n'.join(result)

def apply_random_optimization(source_code):
    """Apply a randomly selected optimization technique to the source code."""
    optimization = random.choice(OPTIMIZATIONS)
    
    if optimization == "constant_folding":
        return apply_constant_folding(source_code), optimization
    elif optimization == "loop_unrolling":
        return apply_loop_unrolling(source_code), optimization
    elif optimization == "copy_propagation":
        return apply_copy_propagation(source_code), optimization
    elif optimization == "common_subexpression_elimination":
        return apply_common_subexpression_elimination(source_code), optimization
    elif optimization == "dead_code_elimination":
        return apply_dead_code_elimination(source_code), optimization
    else:
        return source_code, None

def compile_optimized_variant(source_file, optimized_code, variant_id, output_dir):
    """Compile an optimized variant of the source code."""
    base_name = os.path.basename(source_file).rsplit('.', 1)[0]
    variant_file = os.path.join(output_dir, f"{base_name}_variant_{variant_id}.c")
    output_path = os.path.join(output_dir, f"{base_name}_variant_{variant_id}")
    
    # Write the optimized code to a file
    with open(variant_file, 'w') as f:
        f.write(optimized_code)
    
    # Compile the variant
    cmd = ["gcc", "-O0", variant_file, "-o", output_path]
    
    try:
        subprocess.run(cmd, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Compilation error for variant {variant_id}: {e.stderr.decode()}")
        return None
