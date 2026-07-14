cmake_minimum_required(VERSION 3.24)

project(FilamentPackageTest LANGUAGES CXX)

find_package(filament CONFIG REQUIRED)

add_executable(filament_package_test src/main.cpp)
target_compile_features(filament_package_test PRIVATE cxx_std_20)
target_link_libraries(
    filament_package_test
    PRIVATE
        filament::gltfio
)
