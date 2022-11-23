#define _GNU_SOURCE
#include <unistd.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

typedef ssize_t (*execve_func_t)  (const char* filename, char* const argv[], char* const envp[]);
typedef ssize_t (*execv_func_t)   (const char* path, char* const argv[]);
typedef ssize_t (*execvp_func_t)  (const char* file, char* const argv[]);
typedef ssize_t (*execvpe_func_t) (const char *file, char *const argv[], char *const envp[]);

/* Function pointers for unused exec system calls */
//typedef ssize_t (*execl_func_t)   (const char* path, const char *arg, ...);
//typedef ssize_t (*execlp_func_t)  (const char* file, const char *arg, ...);
//typedef ssize_t (*execle_func_t)  (const char *path, const char *arg, ..., char * const envp[]);

static execve_func_t    old_execve = NULL;
static execv_func_t     old_execv = NULL;
static execvp_func_t    old_execvp = NULL;
static execvpe_func_t   old_execvpe = NULL;

/* Unused globals */
//static execl_func_t     old_execl = NULL;
//static execlp_func_t    old_execlp = NULL;
//static execle_func_t    old_execle = NULL;

static const char *nvcc_faros = __NVCC_WRAPPER__;
static const char *clang_faros = __CLANG_WRAPPER__;
static const char *clangpp_faros = __CLANGPP_WRAPPER__;

/** Return: one if the string t occurs at the end of the string s, and zero otherwise **/
int str_end(const char *s, const char *t)
{
    if (strlen(s) < strlen(t)) return 0;
    return 0 == strcmp(&s[strlen(s)-strlen(t)], t);
}

int isNVCC(const char* filename) {
  return (str_end(filename, "/nvcc") ||
          strcmp(filename, "nvcc")==0
          );
}

int isClang(const char* filename) {
  return (str_end(filename, "/clang") || 
          strcmp(filename, "clang")==0
          );
}

int isClangPP(const char* filename) {
  return (str_end(filename, "/clang++") || 
          strcmp(filename, "clang++")==0
          );
}

int isGCC(const char* filename) {
  return (str_end(filename, "/gcc") || 
          strcmp(filename, "gcc")==0
          );
}

int isGPP(const char* filename) {
  return (str_end(filename, "/g++") || 
          strcmp(filename, "g++")==0
          );
}

int isMPI(const char* filename) {
  return (str_end(filename, "/mpicc") || 
          strcmp(filename, "mpicc")==0
          );
}

int isMPIPP(const char* filename) {
  return (str_end(filename, "/mpicxx") || 
          str_end(filename, "/mpic++") ||
          strcmp(filename, "mpicxx")==0 ||
          strcmp(filename, "mpic++")==0
          );
}

void printEnvironment(char* const envp[]) {
  size_t elems = 0;
  while (envp != NULL) {
    if (*envp == NULL)
      break;

    elems++;
    printf("VAR: %s\n", *envp);
    envp++;
  }
  printf("Elems: %lu\n", elems);
}

/* Copy the environment without LD_PRELOAD */
void copy_env_variables(char* const envp[], char *** new_envp) {
  char **ptr = (char **)envp;
  size_t elems = 0;
  while (ptr != NULL) {
    if (*ptr == NULL)
      break;
    elems++;
    ptr++;
  }

  *new_envp = (char **)malloc(sizeof(char *)*elems+1); 
  for (size_t i=0; i < elems; ++i) {
    (*new_envp)[i] = (char *)malloc(strlen(envp[i]) * sizeof(char) + 1);
    if (strstr (envp[i], "LD_PRELOAD=") == NULL) { // do not copy ld_preload
      strcpy((*new_envp)[i], envp[i]);
    } else {
      strcpy((*new_envp)[i], "LD_PRELOAD=");
    }
  }
  (*new_envp)[elems] = NULL;
}

/* Remove LD_PRELOAD library to avoid a cycle in pre-loading */
void remove_ld_preload() {
    unsetenv("LD_PRELOAD");
    unsetenv("DYLD_INSERT_LIBRARIES");
}

int execve(const char* filename, char* const argv[], char* const envp[]) {
    // Copy env variables
    char ** new_envp;
    copy_env_variables(envp, &new_envp);
    old_execve = dlsym(RTLD_NEXT, "execve");

    if (isNVCC(filename))         return old_execve(nvcc_faros, argv, new_envp);
    else if (isClang(filename))   return old_execve(clang_faros, argv, new_envp);
    else if (isClangPP(filename)) return old_execve(clangpp_faros, argv, new_envp);
    else if (isGCC(filename))     return old_execve(clang_faros, argv, new_envp);
    else if (isGPP(filename))     return old_execve(clangpp_faros, argv, new_envp);
    return old_execve(filename, argv, envp); // else run original call
}

int execv(const char *path, char *const argv[]) {
    if (isNVCC(path) || isClang(path) || isClangPP(path))
      remove_ld_preload();
    old_execv = dlsym(RTLD_NEXT, "execv");

    if (isNVCC(path))         return old_execv(nvcc_faros, argv);
    else if (isClang(path))   return old_execv(clang_faros, argv);
    else if (isClangPP(path)) return old_execv(clangpp_faros, argv);
    else if (isGCC(path))     return old_execv(clang_faros, argv);
    else if (isGPP(path))     return old_execv(clangpp_faros, argv);
    return old_execv(path, argv); // else run original call
}

int execvp (const char *file, char *const argv[]) {
    if (isNVCC(file) || isClang(file) || isClangPP(file))
      remove_ld_preload();
    old_execvp = dlsym(RTLD_NEXT, "execvp");

    if (isNVCC(file))         return old_execvp(nvcc_faros, argv);
    else if (isClang(file))   return old_execvp(clang_faros, argv);
    else if (isClangPP(file)) return old_execvp(clangpp_faros, argv);
    else if (isGCC(file))     return old_execvp(clang_faros, argv);
    else if (isGPP(file))     return old_execvp(clangpp_faros, argv);
    return old_execvp(file, argv); // else run original call
}

int execvpe(const char *file, char *const argv[], char *const envp[]) {
    char ** new_envp;
    copy_env_variables(envp, &new_envp);
    old_execvpe = dlsym(RTLD_NEXT, "execvpe");

    if (isNVCC(file))         return old_execvpe(nvcc_faros, argv, new_envp);
    else if (isClang(file))   return old_execvpe(clang_faros, argv, new_envp);
    else if (isClangPP(file)) return old_execvpe(clangpp_faros, argv, new_envp);
    else if (isGCC(file))     return old_execvpe(clang_faros, argv, new_envp);
    else if (isGPP(file))     return old_execvpe(clangpp_faros, argv, new_envp);
    return old_execvpe(file, argv, envp); // else run original call
}
