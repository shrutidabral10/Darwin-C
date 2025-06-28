#!/usr/bin/env python3

"""
Optimizer module for evolutionary C code optimization
----------------------------------------------------
This module implements the evolutionary algorithm to optimize C code.
"""

import os
import random
import copy
import shutil  # Added for file operations
from compiler import (
    compile_optimized_variant, 
    apply_random_optimization,
    get_execution_time,
    OPTIMIZATIONS
)

def read_source_code(source_file):
    """Read the source code from file."""
    with open(source_file, 'r') as f:
        return f.read()

def create_initial_population(source_code, source_file, output_dir, population_size):
    """Create the initial population by applying random optimizations."""
    population = []
    
    # Create variants
    for i in range(population_size):
        # Apply a random optimization
        optimized_code, optimization = apply_random_optimization(source_code)
        
        # Compile the optimized code
        executable_path = compile_optimized_variant(source_file, optimized_code, i, output_dir)
        
        if executable_path:
            source_path = os.path.join(output_dir, f"{os.path.basename(source_file).rsplit('.', 1)[0]}_variant_{i}.c")
            population.append({
                'code': optimized_code,
                'executable': executable_path,
                'source_path': source_path,  # Save the source path for cleanup
                'optimizations': [optimization] if optimization else [],
                'variant_id': i
            })
    
    return population

def evaluate_population(population, timeout):
    """Measure execution time for all individuals in the population."""
    for individual in population:
        execution_time = get_execution_time(individual['executable'], timeout)
        individual['fitness'] = execution_time
    
    # Sort by fitness (lower execution time is better)
    population.sort(key=lambda x: x['fitness'])
    return population

def select_best(population, top_n=1):
    """Select the top N individuals from the population."""
    return population[:top_n]

def create_next_generation(best_individuals, source_file, output_dir, generation, population_size):
    """Create the next generation based on the best individuals from the previous generation."""
    next_generation = []
    
    # Keep the best individuals
    for i, individual in enumerate(best_individuals):
        next_generation.append(individual)
    
    # Fill the rest of the population with mutations of the best individuals
    while len(next_generation) < population_size:
        # Select a random individual from the best ones
        parent = random.choice(best_individuals)
        
        # Create a child by applying a random optimization to the parent
        child_code, optimization = apply_random_optimization(parent['code'])
        
        # New variant ID based on generation and position
        variant_id = f"{generation}_{len(next_generation)}"
        
        # Compile the child
        executable_path = compile_optimized_variant(source_file, child_code, variant_id, output_dir)
        
        if executable_path:
            # Add the source path for cleanup later
            source_path = os.path.join(output_dir, f"{os.path.basename(source_file).rsplit('.', 1)[0]}_variant_{variant_id}.c")
            
            # Add to the new optimizations list
            optimizations = parent['optimizations'].copy()
            if optimization:
                optimizations.append(optimization)
            
            next_generation.append({
                'code': child_code,
                'executable': executable_path,
                'source_path': source_path,  # Save the source path
                'optimizations': optimizations,
                'variant_id': variant_id
            })
    
    return next_generation

def cleanup_variants(best_individual, population, output_dir, source_file):
    """Delete all variant files except the best one."""
    base_name = os.path.basename(source_file).rsplit('.', 1)[0]
    best_source = best_individual['source_path']
    best_executable = best_individual['executable']
    
    # Rename the best variant to a more recognizable name
    optimized_source = os.path.join(output_dir, f"{base_name}_optimized.c")
    optimized_executable = os.path.join(output_dir, f"{base_name}_optimized")
    
    # Rename the best files
    try:
        shutil.copy2(best_source, optimized_source)
        shutil.copy2(best_executable, optimized_executable)
        print(f"Best variant saved as {optimized_source}")
        print(f"Best executable saved as {optimized_executable}")
    except Exception as e:
        print(f"Error saving best variant: {e}")
    
    # Delete all variant files
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if file.startswith(f"{base_name}_variant_"):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
    
    print("All other variants have been deleted.")
    
    # Return the paths to the optimized files
    return optimized_executable, optimized_source

def evolve_code(source_file, output_dir, original_time, max_generations, population_size, timeout):
    """Main evolutionary algorithm logic."""
    source_code = read_source_code(source_file)
    
    # Create initial population
    print("\nCreating initial population...")
    population = create_initial_population(source_code, source_file, output_dir, population_size)
    
    if not population:
        print("Failed to create initial population. Exiting.")
        return None, None, None
    
    # Evaluate initial population
    print("Evaluating initial population...")
    population = evaluate_population(population, timeout)
    
    # Keep track of the best individual across all generations
    best_individual = population[0]
    all_populations = [population]  # Keep track of all populations for cleanup
    
    print(f"Generation 0: Best time = {best_individual['fitness']:.6f} seconds")
    
    # Early termination if original code is better than all optimized variants
    if best_individual['fitness'] >= original_time:
        print("No optimization improved execution time in the initial generation.")
        # Clean up all variants since none are better
        for ind in population:
            try:
                os.remove(ind['source_path'])
                os.remove(ind['executable'])
            except:
                pass
        return None, None, None
    
    # Evolution loop
    for generation in range(1, max_generations + 1):
        print(f"\nGeneration {generation}:")
        
        # Select best individuals
        best_individuals = select_best(population, top_n=max(1, population_size // 3))
        
        # Create next generation
        population = create_next_generation(best_individuals, source_file, output_dir, generation, population_size)
        all_populations.append(population)
        
        # Evaluate new population
        population = evaluate_population(population, timeout)
        
        # Check if we found a better individual
        if population[0]['fitness'] < best_individual['fitness']:
            best_individual = population[0]
            print(f"New best time: {best_individual['fitness']:.6f} seconds")
            print(f"Optimizations: {', '.join(best_individual['optimizations'])}")
        else:
            print(f"No improvement. Best time remains: {best_individual['fitness']:.6f} seconds")
        
        # Early termination if no improvement for 3 consecutive generations
        if generation >= 3:
            last_three_best = [gen[0]['fitness'] for gen in [population]]
            if len(set(last_three_best)) == 1:
                print("No improvement for multiple generations. Stopping.")
                break
    
    # Clean up all variants except the best one
    optimized_executable, optimized_source = cleanup_variants(best_individual, sum(all_populations, []), output_dir, source_file)
    
    # Return the best individual found
    return optimized_executable, best_individual['fitness'], best_individual['optimizations']
