cmake_minimum_required(VERSION 3.24)

project(
    MascotRender
    VERSION 0.7.0
    DESCRIPTION "Deterministic procedural character rendering engine"
    LANGUAGES CXX
)

include(CMakePackageConfigHelpers)
include(GNUInstallDirs)

option(MASCOTRENDER_BUILD_CLI "Build the mascotrender command-line application" ON)
option(MASCOTRENDER_BUILD_TESTS "Build MascotRender unit tests" OFF)
option(
    MASCOTRENDER_WITH_FILAMENT
    "Enable the optional Filament 3D backend dependency"
    OFF
)

find_package(thorvg CONFIG REQUIRED)
find_package(WebP CONFIG REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)

if(MASCOTRENDER_WITH_FILAMENT)
    find_package(filament CONFIG REQUIRED)
endif()

add_library(
    MascotRender
    src/engine.cpp
    src/animation/timeline.cpp
    src/export/webp_encoder.cpp
    src/model/scene.cpp
    src/render/caption_layout.cpp
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

if(MASCOTRENDER_WITH_FILAMENT)
    target_sources(
        MascotRender
        PRIVATE
            src/render/caption_compositor.cpp
            src/render/filament_backend.cpp
    )
    target_link_libraries(MascotRender PRIVATE filament::gltfio)
    target_compile_definitions(MascotRender PRIVATE MASCOTRENDER_WITH_FILAMENT=1)
endif()

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

if(
    MASCOTRENDER_WITH_FILAMENT
    AND (MASCOTRENDER_BUILD_CLI OR MASCOTRENDER_BUILD_TESTS)
)
    add_executable(
        mascotrender_glb_preview
        apps/mascotrender/glb_preview.cpp
    )
    set_target_properties(
        mascotrender_glb_preview
        PROPERTIES
            CXX_EXTENSIONS OFF
            CXX_STANDARD 20
            CXX_STANDARD_REQUIRED ON
            OUTPUT_NAME mascotrender-glb-preview
    )
    target_include_directories(
        mascotrender_glb_preview
        PRIVATE "${PROJECT_SOURCE_DIR}/src"
    )
    target_link_libraries(
        mascotrender_glb_preview
        PRIVATE
            MascotRender::MascotRender
            libwebp::libwebp
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
    if(MASCOTRENDER_WITH_FILAMENT)
        install(
            TARGETS mascotrender_glb_preview
            RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}"
        )
    endif()
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
    DIRECTORY schemas examples contracts content
    DESTINATION "${CMAKE_INSTALL_DATADIR}/mascotrender"
    PATTERN ".DS_Store" EXCLUDE
)
install(
    DIRECTORY
        art/calendar-pop-v1
        art/congratulations-pop-v1
        art/workday-reactions-v1
        art/human-pack-v1
        art/human-pack-wave2
        art/micro-reactions-v1
    DESTINATION "${CMAKE_INSTALL_DATADIR}/mascotrender/art"
    PATTERN ".DS_Store" EXCLUDE
)
install(
    FILES
        LICENSE
        docs/MANIFESTO.md
        docs/VISION.md
        docs/ROADMAP.md
        docs/ARCHITECTURE.md
        docs/HUMAN_PACK_VISUAL_STANDARD.md
        docs/HUMAN_PACK_V1_ART_BRIEF.md
        docs/HUMAN_PACK_PRODUCTION_RECOVERY.md
        docs/MICRO_REACTIONS.md
        docs/WORKDAY_REACTIONS.md
        docs/MASCOT_PACKAGE_SPEC.md
        docs/BUNDLE_PROTOCOL.md
        docs/RELEASE_0.1.0.md
        docs/RELEASE_0.2.0.md
        docs/RELEASE_0.3.0.md
        docs/RELEASE_0.4.0.md
        docs/RELEASE_0.5.0.md
        docs/RELEASE_0.6.0.md
        docs/RELEASE_0.7.0.md
        docs/ROADMAP_3D_ANIMATION.md
        docs/THIRD_PARTY_NOTICES.md
    DESTINATION "${CMAKE_INSTALL_DATADIR}/mascotrender"
)
install(
    PROGRAMS
        tools/generate_robot_glb.py
        tools/generate_mascot_packs.py
        tools/generate_human_pilots.py
        tools/human_contracts.py
        tools/validate_human_pilots.py
        tools/build_human_pilot_review.py
        tools/generate_canonical_human_masters.py
        tools/generate_canonical_human_glbs.py
        tools/generate_human_wave2_candidates.py
        tools/generate_human_wave2_glbs.py
        tools/generate_micro_reactions_pack.py
        tools/generate_micro_orbit_2_5d_proof.py
        tools/generate_micro_orbit_glb.py
        tools/generate_micro_styled_glbs.py
        tools/generate_calendar_typography_pack.py
        tools/generate_congratulations_pack.py
        tools/generate_workday_reactions_pack.py
        tools/build_micro_reactions_bundle.py
        tools/build_canonical_human_review.py
        tools/build_canonical_human_production_review.py
        tools/build_mascot_package.py
        tools/render_caption_backend_review.py
        tools/render_character_identity_review.py
        tools/render_robot_glb_review.py
        tools/render_micro_orbit_glb_review.py
        tools/render_micro_styled_glb_family_review.py
        tools/validate_character_identity.py
        tools/render_mascot_packs.py
        tools/build_sticker_review.py
        tools/mascot_bundle.py
        tools/package_bundle_release.py
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
