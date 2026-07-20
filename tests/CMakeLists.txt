add_executable(
    mascotrender_unit_tests
    test_pack.cpp
    test_render.cpp
    test_timeline.cpp
    test_text_layout.cpp
    test_version.cpp
)
if(MASCOTRENDER_WITH_FILAMENT)
    target_sources(mascotrender_unit_tests PRIVATE test_filament_backend.cpp)
    find_package(Python3 COMPONENTS Interpreter REQUIRED)
    add_test(
        NAME robot_004_glb_is_deterministic
        COMMAND
            "${Python3_EXECUTABLE}"
            "${PROJECT_SOURCE_DIR}/tools/generate_robot_glb.py"
            --output "${PROJECT_SOURCE_DIR}/examples/robot-004/robot-004.glb"
            --check
    )
    add_test(
        NAME canonical_human_glbs_are_deterministic
        COMMAND
            "${Python3_EXECUTABLE}"
            "${PROJECT_SOURCE_DIR}/tools/generate_canonical_human_glbs.py"
            --input "${PROJECT_SOURCE_DIR}/art/human-pack-v1/masters"
            --self-test
    )
    if(MASCOTRENDER_BUILD_CLI)
        find_program(
            MASCOTRENDER_REVIEW_PYTHON
            NAMES python3
            HINTS "$ENV{PYENV_ROOT}/shims" "$ENV{HOME}/.pyenv/shims"
        )
        if(NOT MASCOTRENDER_REVIEW_PYTHON)
            set(MASCOTRENDER_REVIEW_PYTHON "${Python3_EXECUTABLE}")
        endif()
        add_test(
            NAME canonical_human_production_review_pipeline
            COMMAND
                "${MASCOTRENDER_REVIEW_PYTHON}"
                "${PROJECT_SOURCE_DIR}/tools/build_canonical_human_production_review.py"
                --input "${PROJECT_SOURCE_DIR}/art/human-pack-v1/masters"
                --output "${PROJECT_BINARY_DIR}/canonical-human-production-review"
                --mascotrender "$<TARGET_FILE:mascotrender_cli>"
                --glb-renderer "$<TARGET_FILE:mascotrender_glb_preview>"
                --expect-verification-status technical-validation-success
                --force
        )
        set_tests_properties(canonical_human_production_review_pipeline PROPERTIES TIMEOUT 300)
    endif()
endif()

find_package(Python3 COMPONENTS Interpreter REQUIRED)
add_test(
    NAME product_direction_contracts
    COMMAND
        "${Python3_EXECUTABLE}"
        "${PROJECT_SOURCE_DIR}/tests/test_product_direction.py"
        --python "${Python3_EXECUTABLE}"
        --validator "${PROJECT_SOURCE_DIR}/tools/validate_human_pilots.py"
        --packager "${PROJECT_SOURCE_DIR}/tools/build_mascot_package.py"
        --standard "${PROJECT_SOURCE_DIR}/contracts/human-pack-production-v1.json"
        --canonical-family "${PROJECT_SOURCE_DIR}/contracts/human-canonical-family-v1.json"
        --production-design-review "${PROJECT_SOURCE_DIR}/contracts/human-canonical-production-design-review-v1.json"
        --canonical-asset "${PROJECT_SOURCE_DIR}/art/concepts/human-pack-v1/family-gate-v1.png"
)
set_tests_properties(product_direction_contracts PROPERTIES TIMEOUT 60)
add_test(
    NAME robot_004_identity_contract
    COMMAND
        "${Python3_EXECUTABLE}"
        "${PROJECT_SOURCE_DIR}/tools/validate_character_identity.py"
        --contract "${PROJECT_SOURCE_DIR}/examples/robot-004/identity.json"
        --pack "${PROJECT_SOURCE_DIR}/examples/robot-2_5d/pack.json"
        --flat-pack "${PROJECT_SOURCE_DIR}/examples/robot-2_5d/pack-flat.json"
        --glb "${PROJECT_SOURCE_DIR}/examples/robot-004/robot-004.glb"
)
add_test(
    NAME human_wave2_expansion_contract
    COMMAND
        "${Python3_EXECUTABLE}"
        "${PROJECT_SOURCE_DIR}/tests/test_human_wave2_expansion.py"
        --python "${Python3_EXECUTABLE}"
        --generator "${PROJECT_SOURCE_DIR}/tools/generate_human_wave2_candidates.py"
        --glb-generator "${PROJECT_SOURCE_DIR}/tools/generate_human_wave2_glbs.py"
        --contract "${PROJECT_SOURCE_DIR}/contracts/human-canonical-expansion-wave2.json"
        --owner-approval "${PROJECT_SOURCE_DIR}/contracts/human-canonical-expansion-wave2-owner-approval.json"
        --art-direction-approval "${PROJECT_SOURCE_DIR}/contracts/human-wave2-cross-backend-art-direction-owner-approval-v1.json"
        --production-activation "${PROJECT_SOURCE_DIR}/contracts/human-wave2-production-activation-v1.json"
        --selector "${PROJECT_SOURCE_DIR}/content/human-character-selection-v1.json"
        --phrase-eligibility "${PROJECT_SOURCE_DIR}/content/human-phrase-eligibility-v1.json"
)
set_tests_properties(human_wave2_expansion_contract PROPERTIES TIMEOUT 90)
find_program(
    MASCOTRENDER_SMALL_DISPLAY_PYTHON
    NAMES python3
    HINTS "$ENV{PYENV_ROOT}/shims" "$ENV{HOME}/.pyenv/shims"
    NO_DEFAULT_PATH
)
if(NOT MASCOTRENDER_SMALL_DISPLAY_PYTHON)
    set(MASCOTRENDER_SMALL_DISPLAY_PYTHON "${Python3_EXECUTABLE}")
endif()
add_test(
    NAME human_small_display_profiles
    COMMAND
        "${MASCOTRENDER_SMALL_DISPLAY_PYTHON}"
        "${PROJECT_SOURCE_DIR}/tests/test_human_display_profiles.py"
)
set_tests_properties(human_small_display_profiles PROPERTIES TIMEOUT 30)
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
        NAME micro_reactions_pack_contract
        COMMAND
            "${MASCOTRENDER_SMALL_DISPLAY_PYTHON}"
            "${PROJECT_SOURCE_DIR}/tests/test_micro_reactions.py"
            --python "${MASCOTRENDER_SMALL_DISPLAY_PYTHON}"
            --generator "${PROJECT_SOURCE_DIR}/tools/generate_micro_reactions_pack.py"
            --cli "$<TARGET_FILE:mascotrender_cli>"
            --contract "${PROJECT_SOURCE_DIR}/contracts/micro-reactions-pack-v1.json"
            --matrix "${PROJECT_SOURCE_DIR}/content/micro-reactions-emotion-matrix-v1.json"
            --owner-approval "${PROJECT_SOURCE_DIR}/contracts/micro-reactions-reaction-and-orbit-2_5d-owner-approval-v1.json"
            --final-owner-approval "${PROJECT_SOURCE_DIR}/contracts/micro-reactions-final-pack-owner-approval-v1.json"
    )
    # Full review regeneration invokes the instrumented CLI for every frame.
    # ASan/UBSan runners need more headroom than optimized package jobs.
    set_tests_properties(micro_reactions_pack_contract PROPERTIES TIMEOUT 480)
    add_test(
        NAME micro_orbit_layered_and_glb_proofs
        COMMAND
            "${MASCOTRENDER_SMALL_DISPLAY_PYTHON}"
            "${PROJECT_SOURCE_DIR}/tests/test_micro_orbit_proofs.py"
            --python "${MASCOTRENDER_SMALL_DISPLAY_PYTHON}"
            --layered-generator "${PROJECT_SOURCE_DIR}/tools/generate_micro_orbit_2_5d_proof.py"
            --glb-generator "${PROJECT_SOURCE_DIR}/tools/generate_micro_orbit_glb.py"
            --cli "$<TARGET_FILE:mascotrender_cli>"
            --glb "${PROJECT_SOURCE_DIR}/art/micro-reactions-v1/orbit-glb-proof/micro-orbit-004.glb"
            --owner-decision "${PROJECT_SOURCE_DIR}/contracts/micro-reactions-reaction-and-orbit-2_5d-owner-approval-v1.json"
            --final-owner-decision "${PROJECT_SOURCE_DIR}/contracts/micro-orbit-final-glb-face-parity-owner-approval-v1.json"
    )
    set_tests_properties(micro_orbit_layered_and_glb_proofs PROPERTIES TIMEOUT 60)
    add_test(
        NAME micro_styled_glb_family_contract
        COMMAND
            "${MASCOTRENDER_SMALL_DISPLAY_PYTHON}"
            "${PROJECT_SOURCE_DIR}/tests/test_micro_styled_glb_family.py"
            --python "${MASCOTRENDER_SMALL_DISPLAY_PYTHON}"
            --generator "${PROJECT_SOURCE_DIR}/tools/generate_micro_styled_glbs.py"
            --contract "${PROJECT_SOURCE_DIR}/content/micro-styled-glb-identities-v1.json"
            --glb-root "${PROJECT_SOURCE_DIR}/art/micro-reactions-v1/styled-glb-proofs"
            --orbit-owner-approval "${PROJECT_SOURCE_DIR}/contracts/micro-orbit-final-glb-face-parity-owner-approval-v1.json"
            --family-owner-approval "${PROJECT_SOURCE_DIR}/contracts/micro-reactions-styled-glb-family-owner-approval-v1.json"
    )
    set_tests_properties(micro_styled_glb_family_contract PROPERTIES TIMEOUT 30)
    add_test(
        NAME micro_reactions_distribution_bundle
        COMMAND
            "${MASCOTRENDER_SMALL_DISPLAY_PYTHON}"
            "${PROJECT_SOURCE_DIR}/tests/test_micro_reactions_bundle.py"
            --python "${MASCOTRENDER_SMALL_DISPLAY_PYTHON}"
            --generator "${PROJECT_SOURCE_DIR}/tools/generate_micro_reactions_pack.py"
            --builder "${PROJECT_SOURCE_DIR}/tools/build_micro_reactions_bundle.py"
            --bundle-tool "${PROJECT_SOURCE_DIR}/tools/mascot_bundle.py"
            --archive-tool "${PROJECT_SOURCE_DIR}/tools/package_bundle_release.py"
            --cli "$<TARGET_FILE:mascotrender_cli>"
            --matrix "${PROJECT_SOURCE_DIR}/content/micro-reactions-emotion-matrix-v1.json"
            --orbit-glb "${PROJECT_SOURCE_DIR}/art/micro-reactions-v1/orbit-glb-proof/micro-orbit-004.glb"
            --family-glb-root "${PROJECT_SOURCE_DIR}/art/micro-reactions-v1/styled-glb-proofs"
            --orbit-approval "${PROJECT_SOURCE_DIR}/contracts/micro-orbit-final-glb-face-parity-owner-approval-v1.json"
            --family-approval "${PROJECT_SOURCE_DIR}/contracts/micro-reactions-styled-glb-family-owner-approval-v1.json"
    )
    set_tests_properties(micro_reactions_distribution_bundle PROPERTIES TIMEOUT 600)
    add_test(
        NAME generated_mascot_pipeline
        COMMAND
            "${Python3_EXECUTABLE}"
            "${PROJECT_SOURCE_DIR}/tests/test_generated_pipeline.py"
            --python "${Python3_EXECUTABLE}"
            --generator "${PROJECT_SOURCE_DIR}/tools/generate_mascot_packs.py"
            --renderer "${PROJECT_SOURCE_DIR}/tools/render_mascot_packs.py"
            --reviewer "${PROJECT_SOURCE_DIR}/tools/build_sticker_review.py"
            --bundle-tool "${PROJECT_SOURCE_DIR}/tools/mascot_bundle.py"
            --cli "$<TARGET_FILE:mascotrender_cli>"
            --font-source "${PROJECT_SOURCE_DIR}/examples/cat/fonts/changa-one"
    )
    set_tests_properties(generated_mascot_pipeline PROPERTIES TIMEOUT 120)
    add_test(
        NAME human_mascot_pilot_pipeline
        COMMAND
            "${Python3_EXECUTABLE}"
            "${PROJECT_SOURCE_DIR}/tests/test_human_pilot_pipeline.py"
            --python "${Python3_EXECUTABLE}"
            --validator "${PROJECT_SOURCE_DIR}/tools/validate_human_pilots.py"
            --generator "${PROJECT_SOURCE_DIR}/tools/generate_human_pilots.py"
            --reviewer "${PROJECT_SOURCE_DIR}/tools/build_human_pilot_review.py"
            --renderer "${PROJECT_SOURCE_DIR}/tools/render_mascot_packs.py"
            --cli "$<TARGET_FILE:mascotrender_cli>"
            --font-source "${PROJECT_SOURCE_DIR}/examples/cat/fonts/changa-one"
    )
    set_tests_properties(human_mascot_pilot_pipeline PROPERTIES TIMEOUT 180)
    add_test(
        NAME canonical_human_master_pipeline
        COMMAND
            "${Python3_EXECUTABLE}"
            "${PROJECT_SOURCE_DIR}/tests/test_canonical_human_masters.py"
            --python "${Python3_EXECUTABLE}"
            --generator "${PROJECT_SOURCE_DIR}/tools/generate_canonical_human_masters.py"
            --glb-generator "${PROJECT_SOURCE_DIR}/tools/generate_canonical_human_glbs.py"
            --reviewer "${PROJECT_SOURCE_DIR}/tools/build_canonical_human_review.py"
            --cli "$<TARGET_FILE:mascotrender_cli>"
            --rig-contract "${PROJECT_SOURCE_DIR}/contracts/humanoid-production-v2.json"
    )
    set_tests_properties(canonical_human_master_pipeline PROPERTIES TIMEOUT 180)
endif()
