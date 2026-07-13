#include <catch2/catch_test_macros.hpp>

#include "animation/timeline.hpp"

TEST_CASE("timeline samples bounded deterministic frame timestamps") {
    const mascotrender::detail::AnimationSpec animation{
        800U, 10U, mascotrender::detail::AnimationLoop::loop, true, true};

    const auto frames = mascotrender::detail::sample_animation(animation);
    REQUIRE(frames.size() == 8U);
    REQUIRE(frames.front().timestamp_ms == 0U);
    REQUIRE(frames.at(1).timestamp_ms == 100U);
    REQUIRE(frames.back().timestamp_ms == 700U);
    REQUIRE(frames.front().state.mascot_offset_y == 0.0F);
    REQUIRE(frames.at(1).state.mascot_offset_y < 0.0F);
    REQUIRE(frames.front().state.text_opacity == 0.0F);
    REQUIRE(frames.at(1).state.text_opacity > 0.0F);
    REQUIRE(mascotrender::detail::animation_loop_count(animation.loop) == 0U);
    REQUIRE(mascotrender::detail::animation_loop_count(
                mascotrender::detail::AnimationLoop::once) == 1U);
}

TEST_CASE("ping pong timeline returns toward its starting transform") {
    const mascotrender::detail::AnimationSpec animation{
        1000U, 10U, mascotrender::detail::AnimationLoop::ping_pong, true,
        false};

    const auto frames = mascotrender::detail::sample_animation(animation);
    REQUIRE(frames.size() == 10U);
    REQUIRE(frames.at(1).state.mascot_offset_y < 0.0F);
    REQUIRE(frames.at(9).state.mascot_offset_y < 0.0F);
    REQUIRE(frames.at(5).state.mascot_offset_y == 0.0F);
}
