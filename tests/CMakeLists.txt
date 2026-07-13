add_executable(
    mascotrender_unit_tests
    test_pack.cpp
    test_render.cpp
    test_text_layout.cpp
    test_version.cpp
)
target_link_libraries(
    mascotrender_unit_tests
    PRIVATE
        MascotRender::MascotRender
        Catch2::Catch2WithMain
        libwebp::libwebp
)
target_compile_features(mascotrender_unit_tests PRIVATE cxx_std_20)
target_include_directories(mascotrender_unit_tests PRIVATE "${PROJECT_SOURCE_DIR}/src")
target_compile_definitions(
    mascotrender_unit_tests
    PRIVATE MASCOTRENDER_TEST_SOURCE_DIR="${PROJECT_SOURCE_DIR}"
)

include(Catch)
catch_discover_tests(mascotrender_unit_tests)

if(MASCOTRENDER_BUILD_CLI)
    find_package(Python3 COMPONENTS Interpreter REQUIRED)
    add_test(
        NAME generated_mascot_pipeline
        COMMAND
            "${Python3_EXECUTABLE}"
            "${PROJECT_SOURCE_DIR}/tests/test_generated_pipeline.py"
            --python "${Python3_EXECUTABLE}"
            --generator "${PROJECT_SOURCE_DIR}/tools/generate_mascot_packs.py"
            --renderer "${PROJECT_SOURCE_DIR}/tools/render_mascot_packs.py"
            --cli "$<TARGET_FILE:mascotrender_cli>"
            --font-source "${PROJECT_SOURCE_DIR}/examples/cat/fonts/changa-one"
    )
    set_tests_properties(generated_mascot_pipeline PROPERTIES TIMEOUT 120)
endif()
