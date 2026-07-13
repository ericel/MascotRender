#include "animation/timeline.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>

namespace mascotrender::detail {
namespace {

enum class Easing { linear, ease_out, pop };

struct Keyframe {
    float progress{};
    float value{};
    Easing easing_to_next{Easing::linear};
};

[[nodiscard]] float apply_easing(Easing easing, float value) {
    const auto t = std::clamp(value, 0.0F, 1.0F);
    switch (easing) {
        case Easing::linear:
            return t;
        case Easing::ease_out:
            return 1.0F - (1.0F - t) * (1.0F - t);
        case Easing::pop: {
            constexpr float overshoot = 1.70158F;
            constexpr float factor = overshoot + 1.0F;
            const auto shifted = t - 1.0F;
            return 1.0F + factor * shifted * shifted * shifted +
                   overshoot * shifted * shifted;
        }
    }
    return t;
}

[[nodiscard]] float sample_track(const std::vector<Keyframe>& track,
                                 float progress, float fallback) {
    if (track.empty()) {
        return fallback;
    }
    if (progress <= track.front().progress) {
        return track.front().value;
    }
    if (progress >= track.back().progress) {
        return track.back().value;
    }
    const auto right = std::upper_bound(track.begin(), track.end(), progress,
                                        [](float value, const Keyframe& frame) {
                                            return value < frame.progress;
                                        });
    const auto& left = *(right - 1);
    const auto duration = right->progress - left.progress;
    const auto local = apply_easing(left.easing_to_next,
                                    (progress - left.progress) / duration);
    return left.value + (right->value - left.value) * local;
}

[[nodiscard]] float loop_progress(AnimationLoop loop, float progress) {
    if (loop != AnimationLoop::ping_pong) {
        return progress;
    }
    return progress <= 0.5F ? progress * 2.0F : (1.0F - progress) * 2.0F;
}

}  // namespace

std::vector<TimedFrameState> sample_animation(const AnimationSpec& animation) {
    const auto calculated =
        (static_cast<std::uint64_t>(animation.duration_ms) * animation.fps +
         999U) /
        1000U;
    const auto frame_count =
        std::max<std::uint32_t>(2U, static_cast<std::uint32_t>(calculated));

    const std::vector<Keyframe> bounce_y{
        {0.0F, 0.0F, Easing::ease_out},  {0.18F, -14.0F, Easing::ease_out},
        {0.35F, 0.0F, Easing::ease_out}, {0.52F, -5.0F, Easing::ease_out},
        {0.70F, 0.0F, Easing::linear},   {1.0F, 0.0F, Easing::linear}};
    const std::vector<Keyframe> bounce_scale{
        {0.0F, 1.0F, Easing::pop},        {0.18F, 1.08F, Easing::ease_out},
        {0.35F, 0.96F, Easing::ease_out}, {0.52F, 1.02F, Easing::ease_out},
        {0.70F, 1.0F, Easing::linear},    {1.0F, 1.0F, Easing::linear}};
    const std::vector<Keyframe> text_scale{{0.0F, 0.6F, Easing::pop},
                                           {0.12F, 1.15F, Easing::ease_out},
                                           {0.24F, 1.0F, Easing::linear},
                                           {1.0F, 1.0F, Easing::linear}};
    const std::vector<Keyframe> text_opacity{{0.0F, 0.0F, Easing::ease_out},
                                             {0.12F, 1.0F, Easing::linear},
                                             {1.0F, 1.0F, Easing::linear}};

    std::vector<TimedFrameState> frames;
    frames.reserve(frame_count);
    for (std::uint32_t index = 0; index < frame_count; ++index) {
        const auto timestamp = static_cast<std::uint32_t>(
            (static_cast<std::uint64_t>(index) * animation.duration_ms) /
            frame_count);
        auto progress = static_cast<float>(timestamp) /
                        static_cast<float>(animation.duration_ms);
        progress = loop_progress(animation.loop, progress);

        FrameState state;
        if (animation.body_bounce) {
            state.mascot_offset_y = sample_track(bounce_y, progress, 0.0F);
            state.mascot_scale = sample_track(bounce_scale, progress, 1.0F);
        }
        if (animation.text_pop) {
            state.text_scale = sample_track(text_scale, progress, 1.0F);
            state.text_opacity = sample_track(text_opacity, progress, 1.0F);
        }
        frames.push_back(TimedFrameState{timestamp, state});
    }
    return frames;
}

std::uint32_t animation_loop_count(AnimationLoop loop) {
    return loop == AnimationLoop::loop || loop == AnimationLoop::ping_pong ? 0U
                                                                           : 1U;
}

}  // namespace mascotrender::detail
