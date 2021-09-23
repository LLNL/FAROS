
#include <cstdio>
#include "util.h"
#include "server.h"

#if defined(_OPENMP)
#include <omp.h>
#endif

int main() {
  double x = 1.3;
  double y = 10.0;
  double tmp = compute_util(x, y);
  tmp = server_compute(tmp, y);

  printf("simple program: %f\n", tmp);

#if defined(_OPENMP)
  omp_set_num_threads(4);
#endif

#pragma omp parallel
  {
#if defined(_OPENMP)
    printf("Thread ID: %d\n", omp_get_thread_num());
#endif
  }  


  return 0;
}
