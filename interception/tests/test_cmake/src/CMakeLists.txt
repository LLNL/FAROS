cmake_minimum_required(VERSION "3.9.1")
project(main_exe)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fopenmp")

add_subdirectory(util)
add_subdirectory(core)

include_directories(util core)

set(main_source_files main.cpp)
add_executable(main_program ${main_source_files})

target_link_libraries(main_program server)
