
#include <stdio.h>
#include <mpi.h>

#if defined(_OPENMP)
#include <omp.h>
#endif

int main(int argc, char **argv) {

  MPI_Init(&argc, &argv);

#if defined(_OPENMP)
  omp_set_num_threads(4);
#endif

#pragma omp parallel
  {
#if defined(_OPENMP)
    printf("Thread ID: %d\n", omp_get_thread_num());
#endif
  }  

  printf("Done!\n");

  MPI_Finalize();
  return 0;
}
