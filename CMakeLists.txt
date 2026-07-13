cmake_minimum_required(VERSION 3.24)

project(
    MascotRender
    VERSION 0.1.0
    DESCRIPTION "Procedural mascot and sticker rendering engine"
    LANGUAGES CXX
)

include(CMakePackageConfigHelpers)
include(GNUInstallDirs)

option(MASCOTRENDER_BUILD_CLI "Build the mascotrender command-line application" ON)
option(MASCOTRENDER_BUILD_TESTS "Build MascotRender unit tests" OFF)

find_package(thorvg CONFIG REQUIRED)
find_package(WebP CONFIG REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)

add_library(
    MascotRender
    src/engine.cpp
    src/animation/timeline.cpp
    src/export/webp_encoder.cpp
    src/model/scene.cpp
    src/render/text_layout.cpp
    src/render/thorvg_backend.cpp
    src/version.cpp
)
add_library(MascotRender::MascotRender ALIAS MascotRender)

set_target_properties(
    MascotRender
    PROPERTIES
        CXX_EXTENSIONS OFF
        CXX_STANDARD 20
        CXX_STANDARD_REQUIRED ON
        EXPORT_NAME MascotRender
        OUTPUT_NAME mascotrender
        VERSION "${PROJECT_VERSION}"
        SOVERSION "${PROJECT_VERSION_MAJOR}"
        CXX_VISIBILITY_PRESET hidden
        VISIBILITY_INLINES_HIDDEN YES
)

configure_file(
    cmake/version.hpp.in
    "${PROJECT_BINARY_DIR}/generated/mascotrender/version.hpp"
    @ONLY
)

target_include_directories(
    MascotRender
    PUBLIC
        "$<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>"
        "$<BUILD_INTERFACE:${PROJECT_BINARY_DIR}/generated>"
        "$<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>"
)
target_include_directories(MascotRender PRIVATE "${PROJECT_SOURCE_DIR}/src")
target_link_libraries(
    MascotRender
    PRIVATE
        thorvg::thorvg
        libwebp::libwebp
        nlohmann_json::nlohmann_json
)

target_compile_definitions(MascotRender PRIVATE MASCOTRENDER_BUILDING_LIBRARY)
if(BUILD_SHARED_LIBS)
    target_compile_definitions(MascotRender PUBLIC MASCOTRENDER_SHARED)
endif()

if(MSVC)
    target_compile_options(MascotRender PRIVATE /W4 /permissive-)
else()
    target_compile_options(MascotRender PRIVATE -Wall -Wextra -Wpedantic)
endif()

if(MASCOTRENDER_BUILD_CLI)
    find_package(CLI11 CONFIG REQUIRED)

    add_executable(mascotrender_cli apps/mascotrender/main.cpp)
    set_target_properties(
        mascotrender_cli
        PROPERTIES
            CXX_EXTENSIONS OFF
            CXX_STANDARD 20
            CXX_STANDARD_REQUIRED ON
            OUTPUT_NAME mascotrender
    )
    target_link_libraries(
        mascotrender_cli
        PRIVATE
            MascotRender::MascotRender
            CLI11::CLI11
    )
endif()

if(MASCOTRENDER_BUILD_TESTS)
    enable_testing()
    find_package(Catch2 3 CONFIG REQUIRED)
    add_subdirectory(tests)
endif()

install(
    TARGETS MascotRender
    EXPORT MascotRenderTargets
    RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}"
    LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}"
    ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}"
    INCLUDES DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
)

if(MASCOTRENDER_BUILD_CLI)
    install(TARGETS mascotrender_cli RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}")
endif()

install(
    DIRECTORY include/mascotrender
    DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
    FILES_MATCHING PATTERN "*.hpp"
)
install(
    FILES "${PROJECT_BINARY_DIR}/generated/mascotrender/version.hpp"
    DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}/mascotrender"
)
install(
    DIRECTORY schemas examples
    DESTINATION "${CMAKE_INSTALL_DATADIR}/mascotrender"
    PATTERN ".DS_Store" EXCLUDE
)
install(
    FILES
        LICENSE
        docs/RELEASE_0.1.0.md
        docs/ROADMAP_3D_ANIMATION.md
        docs/THIRD_PARTY_NOTICES.md
    DESTINATION "${CMAKE_INSTALL_DATADIR}/mascotrender"
)
install(
    PROGRAMS
        tools/generate_mascot_packs.py
        tools/render_mascot_packs.py
    DESTINATION "${CMAKE_INSTALL_DATADIR}/mascotrender/tools"
)

set(MASCOTRENDER_INSTALL_CMAKEDIR "${CMAKE_INSTALL_LIBDIR}/cmake/MascotRender")

configure_package_config_file(
    cmake/MascotRenderConfig.cmake.in
    "${PROJECT_BINARY_DIR}/MascotRenderConfig.cmake"
    INSTALL_DESTINATION "${MASCOTRENDER_INSTALL_CMAKEDIR}"
)
write_basic_package_version_file(
    "${PROJECT_BINARY_DIR}/MascotRenderConfigVersion.cmake"
    VERSION "${PROJECT_VERSION}"
    COMPATIBILITY SameMajorVersion
)

install(
    EXPORT MascotRenderTargets
    FILE MascotRenderTargets.cmake
    NAMESPACE MascotRender::
    DESTINATION "${MASCOTRENDER_INSTALL_CMAKEDIR}"
)
install(
    FILES
        "${PROJECT_BINARY_DIR}/MascotRenderConfig.cmake"
        "${PROJECT_BINARY_DIR}/MascotRenderConfigVersion.cmake"
    DESTINATION "${MASCOTRENDER_INSTALL_CMAKEDIR}"
)
