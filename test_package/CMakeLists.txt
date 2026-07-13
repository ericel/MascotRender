cmake_minimum_required(VERSION 3.24)

project(MascotRenderPackageTest LANGUAGES CXX)

find_package(MascotRender CONFIG REQUIRED)

add_executable(mascotrender_package_test src/main.cpp)
target_compile_features(mascotrender_package_test PRIVATE cxx_std_20)
target_link_libraries(
    mascotrender_package_test
    PRIVATE MascotRender::MascotRender
)
