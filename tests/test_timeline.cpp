#include <catch2/catch_test_macros.hpp>

#include "animation/timeline.hpp"

TEST_CASE("timeline samples bounded deterministic frame timestamps") {
  const mascotrender::detail::AnimationSpec animation{
      800U, 10U, mascotrender::detail::AnimationLoop::loop, true,
      mascotrender::detail::TextMotion::pop, {}};

  const auto frames = mascotrender::detail::sample_animation(animation);
  REQUIRE(frames.size() == 8U);
  REQUIRE(frames.front().timestamp_ms == 0U);
  REQUIRE(frames.at(1).timestamp_ms == 100U);
  REQUIRE(frames.back().timestamp_ms == 700U);
  REQUIRE(frames.front().state.mascot_offset_y == 0.0F);
  REQUIRE(frames.at(1).state.mascot_offset_y < 0.0F);
  REQUIRE(frames.front().state.text_opacity == 0.0F);
  REQUIRE(frames.at(1).state.text_opacity > 0.0F);
  REQUIRE(frames.back().state.mascot_offset_y ==
          frames.front().state.mascot_offset_y);
  REQUIRE(frames.back().state.mascot_scale ==
          frames.front().state.mascot_scale);
  REQUIRE(frames.back().state.text_scale == frames.front().state.text_scale);
  REQUIRE(frames.back().state.text_opacity ==
          frames.front().state.text_opacity);
  REQUIRE(mascotrender::detail::animation_loop_count(animation.loop) == 0U);
  REQUIRE(mascotrender::detail::animation_loop_count(
              mascotrender::detail::AnimationLoop::once) == 1U);
}

TEST_CASE("ping pong timeline returns to its starting transform") {
  const mascotrender::detail::AnimationSpec animation{
      1000U, 10U, mascotrender::detail::AnimationLoop::ping_pong, true,
      mascotrender::detail::TextMotion::none, {}};

  const auto frames = mascotrender::detail::sample_animation(animation);
  REQUIRE(frames.size() == 10U);
  REQUIRE(frames.at(1).state.mascot_offset_y < 0.0F);
  REQUIRE(frames.at(9).state.mascot_offset_y == 0.0F);
  REQUIRE(frames.at(5).state.mascot_offset_y == 0.0F);
}

TEST_CASE("typed node and view tracks sample delayed deterministic motion") {
  using mascotrender::detail::AnimationEasing;
  using mascotrender::detail::AnimationKeyframe;
  using mascotrender::detail::AnimationLoop;
  using mascotrender::detail::AnimationProperty;
  using mascotrender::detail::AnimationSpec;
  using mascotrender::detail::AnimationTrack;

  const AnimationSpec animation{
      1000U,
      5U,
      AnimationLoop::loop,
      false,
      mascotrender::detail::TextMotion::none,
      {AnimationTrack{
           "body",
           AnimationProperty::scale_y,
           {AnimationKeyframe{0U, 1.0F, AnimationEasing::linear},
            AnimationKeyframe{500U, 1.2F, AnimationEasing::linear},
            AnimationKeyframe{1000U, 1.0F, AnimationEasing::linear}}},
       AnimationTrack{
           "head",
           AnimationProperty::rotation_degrees,
           {AnimationKeyframe{0U, 0.0F, AnimationEasing::linear},
            AnimationKeyframe{250U, 0.0F, AnimationEasing::linear},
            AnimationKeyframe{500U, 10.0F, AnimationEasing::linear},
            AnimationKeyframe{1000U, 0.0F, AnimationEasing::linear}}},
       AnimationTrack{
           "$view",
           AnimationProperty::view_x,
           {AnimationKeyframe{0U, 0.0F, AnimationEasing::linear},
            AnimationKeyframe{500U, 20.0F, AnimationEasing::linear},
            AnimationKeyframe{1000U, 0.0F, AnimationEasing::linear}}}}};

  const auto frames = mascotrender::detail::sample_animation(animation);
  REQUIRE(frames.size() == 5U);
  REQUIRE(frames.front().state.nodes.size() == 2U);
  REQUIRE(frames.at(1).state.nodes.at(0).scale_y == 1.1F);
  REQUIRE(frames.at(1).state.nodes.at(1).rotation_degrees == 0.0F);
  REQUIRE(frames.at(2).state.nodes.at(1).rotation_degrees == 10.0F);
  REQUIRE(frames.at(2).state.view_offset_x == 20.0F);
  REQUIRE(frames.back().state.nodes.at(0).scale_y == 1.0F);
  REQUIRE(frames.back().state.view_offset_x == 0.0F);
}

TEST_CASE("caption motion modes preserve seamless loop closure") {
  using mascotrender::detail::AnimationLoop;
  using mascotrender::detail::AnimationSpec;
  using mascotrender::detail::TextMotion;

  for (const auto motion : {TextMotion::pulse, TextMotion::wobble,
                            TextMotion::float_motion}) {
    const AnimationSpec animation{800U, 10U, AnimationLoop::loop, false,
                                  motion, {}};
    const auto frames = mascotrender::detail::sample_animation(animation);
    REQUIRE(frames.front().state.text_scale ==
            frames.back().state.text_scale);
    REQUIRE(frames.front().state.text_rotation_degrees ==
            frames.back().state.text_rotation_degrees);
    REQUIRE(frames.front().state.text_translate_y ==
            frames.back().state.text_translate_y);
  }
}
