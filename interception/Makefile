__NVCC_WRAPPER__ = \"$(PWD)/nvcc_faros.py\"
__CLANG_WRAPPER__ = \"$(PWD)/clang-faros\"
__CLANGPP_WRAPPER__ = \"$(PWD)/clang++-faros\"
__GCC_WRAPPER__ = \"$(PWD)/clang_faros.py\"
__GPP_WRAPPER__ = \"$(PWD)/clang_faros.py\"
__MPI_WRAPPER__ = \"$(PWD)/mpicc_faros.py\"
__MPIPP_WRAPPER__ = \"$(PWD)/mpic_faros.py\"

WRAPPER_PATHS = -D__NVCC_WRAPPER__=$(__NVCC_WRAPPER__) \
      -D__CLANG_WRAPPER__=$(__CLANG_WRAPPER__) -D__CLANGPP_WRAPPER__=$(__CLANGPP_WRAPPER__) \
      -D__MPI_WRAPPER__=$(__MPI_WRAPPER__) -D__MPIPP_WRAPPER__=$(__MPIPP_WRAPPER__)

all:
	cc $(WRAPPER_PATHS) -std=c99 -o intercept.so -shared intercept.c -Wall -fPIC -g -ldl

clean:
	rm -rf *.so
