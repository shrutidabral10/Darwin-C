#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define SIZE 100

// Function to initialize matrices with random values
void initialize_matrix(int matrix[SIZE][SIZE]) {
    for (int i = 0; i < SIZE; i++) {
        for (int j = 0; j < SIZE; j++) {
            matrix[i][j] = rand() % 10;
        }
    }
}

// Function to multiply matrices
void multiply_matrices(int A[SIZE][SIZE], int B[SIZE][SIZE], int C[SIZE][SIZE]) {
    for (int i = 0; i < SIZE; i++) {
        for (int j = 0; j < SIZE; j++) {
            C[i][j] = 0;
            for (int k = 0; k < SIZE; k++) {
                // This common subexpression can be optimized
                int temp = A[i][k] * B[k][j];
                C[i][j] = C[i][j] + temp;
            }
        }
    }
}

// Function to print a small part of the matrix for verification
void print_matrix_sample(int matrix[SIZE][SIZE]) {
    printf("Matrix sample (top-left 3x3):\n");
    for (int i = 0; i < 3; i++) {
        for (int j = 0; j < 3; j++) {
            printf("%4d ", matrix[i][j]);
        }
        printf("\n");
    }
}

int main() {
    // Seed random number generator
    srand(time(NULL));
    
    // Declare matrices
    int A[SIZE][SIZE];
    int B[SIZE][SIZE];
    int C[SIZE][SIZE];
    
    // Initialize matrices with random values
    initialize_matrix(A);
    initialize_matrix(B);
    
    // Perform matrix multiplication
    multiply_matrices(A, B, C);
    
    // Print a sample of the result
    print_matrix_sample(A);
    print_matrix_sample(B);
    print_matrix_sample(C);
    
    // Calculate and print a checksum
    int checksum = 0;
    for (int i = 0; i < SIZE; i++) {
        for (int j = 0; j < SIZE; j++) {
            checksum += C[i][j];
        }
    }
    printf("Result checksum: %d\n", checksum);
    
    return 0;
}
