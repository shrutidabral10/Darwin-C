#!/usr/bin/env python3
"""
Evolutionary Algorithm-Based C Code Optimizer
---------------------------------------------
This program optimizes C code using evolutionary algorithms by applying various
compiler optimizations and selecting the fastest version.
"""

import os
import sys
import argparse
from optimizer import evolve_code
from compiler import compile_original, get_execution_time

def main():
    parser = argparse.ArgumentParser(description='Evolutionary Algorithm-Based C Code Optimizer')
    parser.add_argument('source_file', help='Path to the C source file to optimize')
    parser.add_argument('--generations', type=int, default=10, help='Maximum number of generations (default: 10)')
    parser.add_argument('--population', type=int, default=5, help='Number of variants per generation (default: 5)')
    parser.add_argument('--timeout', type=int, default=5, help='Maximum execution time in seconds for a single run (default: 5)')
    parser.add_argument('--output', help='Output directory for optimized code (default: same as input)')
    parser.add_argument('--keep-all', action='store_true', help='Keep all variants (default: only keep the best)')
    args = parser.parse_args()

    # Validate input file
    if not os.path.isfile(args.source_file):
        print(f"Error: Source file '{args.source_file}' not found.")
        sys.exit(1)

    # Set output directory
    if args.output:
        output_dir = args.output
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = os.path.dirname(args.source_file) or '.'

    print(f"Starting optimization for {args.source_file}")
    print(f"Maximum generations: {args.generations}")
    print(f"Population size: {args.population}")
    print(f"Keeping all variants: {args.keep_all}")
    
    # Compile the original code first
    original_executable = compile_original(args.source_file, output_dir)
    if not original_executable:
        print("Failed to compile the original code. Exiting.")
        sys.exit(1)
    
    # Get the execution time of the original code
    original_time = get_execution_time(original_executable, args.timeout)
    print(f"Original code execution time: {original_time:.6f} seconds")
    
    # Run the evolutionary optimization
    best_executable, best_time, best_optimizations = evolve_code(
        args.source_file, 
        output_dir, 
        original_time, 
        args.generations, 
        args.population,
        args.timeout
    )
    
    # Print results
    if best_executable:
        improvement = (original_time - best_time) / original_time * 100
        print("\n=== OPTIMIZATION RESULTS ===")
        print(f"Original execution time: {original_time:.6f} seconds")
        print(f"Best optimized time: {best_time:.6f} seconds")
        print(f"Improvement: {improvement:.2f}%")
        print(f"Best optimizations applied: {', '.join(best_optimizations)}")
        print(f"Optimized executable: {best_executable}")
    else:
        print("\nNo optimizations improved execution time")

if __name__ == '__main__':
    main()
