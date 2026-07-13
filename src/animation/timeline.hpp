#pragma once

#include <cstdint>
#include <vector>

#include "model/scene.hpp"

namespace mascotrender::detail {

struct TimedFrameState {
    std::uint32_t timestamp_ms{};
    FrameState state;
};

[[nodiscard]] std::vector<TimedFrameState> sample_animation(
    const AnimationSpec& animation);

[[nodiscard]] std::uint32_t animation_loop_count(AnimationLoop loop);

}  // namespace mascotrender::detail
