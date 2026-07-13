#include <cmath>
#include <mascotrender/engine.hpp>
#include <memory>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include "animation/timeline.hpp"
#include "export/webp_encoder.hpp"
#include "model/scene.hpp"
#include "render/thorvg_backend.hpp"

namespace mascotrender {
namespace {

[[nodiscard]] std::optional<Error> validate_options(
    const RenderOptions& options) {
    if (options.width == 0 || options.height == 0 || options.width > 4096 ||
        options.height > 4096) {
        return Error{ErrorCode::invalid_argument,
                     "Render width and height must be between 1 and 4096"};
    }
    if (!std::isfinite(options.webp_quality) || options.webp_quality < 0.0F ||
        options.webp_quality > 100.0F) {
        return Error{ErrorCode::invalid_argument,
                     "WebP quality must be finite and between 0 and 100"};
    }
    return std::nullopt;
}

}  // namespace

class Engine::Impl final {
public:
    [[nodiscard]] Result<EncodedImage> render_sample(
        const RenderOptions& options) const {
        if (auto error = validate_options(options)) {
            return Result<EncodedImage>::failure(std::move(*error));
        }

        auto pixels = backend_.render_sample(options.width, options.height);
        if (!pixels) {
            return Result<EncodedImage>::failure(pixels.error());
        }
        return detail::encode_webp(pixels.value(), options);
    }

    [[nodiscard]] Result<EncodedImage> render(
        const RenderRequest& request) const {
        const auto& options = request.options;
        if (auto error = validate_options(options)) {
            return Result<EncodedImage>::failure(std::move(*error));
        }

        auto scene =
            detail::load_scene(request.pack_file, request.sticker_file);
        if (!scene) {
            return Result<EncodedImage>::failure(scene.error());
        }
        if (scene.value().animation && !options.animation_first_frame_only) {
            const auto samples =
                detail::sample_animation(*scene.value().animation);
            constexpr std::uint64_t max_animation_buffer_bytes =
                256ULL * 1024ULL * 1024ULL;
            const auto required_buffer_bytes =
                static_cast<std::uint64_t>(options.width) * options.height *
                4U * samples.size();
            if (required_buffer_bytes > max_animation_buffer_bytes) {
                return Result<EncodedImage>::failure(Error{
                    ErrorCode::invalid_argument,
                    "Animation frame buffer exceeds the 256 MiB safety limit"});
            }
            std::vector<detail::AnimationFrame> frames;
            frames.reserve(samples.size());
            for (const auto& sample : samples) {
                auto pixels = backend_.render_scene(
                    scene.value(), options.width, options.height, sample.state);
                if (!pixels) {
                    return Result<EncodedImage>::failure(pixels.error());
                }
                frames.push_back(detail::AnimationFrame{
                    sample.timestamp_ms, std::move(pixels).value()});
            }
            return detail::encode_animated_webp(
                frames, scene.value().animation->duration_ms,
                detail::animation_loop_count(scene.value().animation->loop),
                options);
        }

        auto pixels = backend_.render_scene(
            scene.value(), options.width, options.height, detail::FrameState{});
        if (!pixels) {
            return Result<EncodedImage>::failure(pixels.error());
        }
        return detail::encode_webp(pixels.value(), options);
    }

private:
    detail::ThorvgBackend backend_;
};

Engine::Engine() : impl_{std::make_unique<Impl>()} {}
Engine::~Engine() = default;
Engine::Engine(Engine&&) noexcept = default;
Engine& Engine::operator=(Engine&&) noexcept = default;

Result<EncodedImage> Engine::render_sample(const RenderOptions& options) const {
    if (!impl_) {
        return Result<EncodedImage>::failure(
            Error{ErrorCode::render_failed, "Cannot use a moved-from Engine"});
    }
    return impl_->render_sample(options);
}

Result<EncodedImage> Engine::render(const RenderRequest& request) const {
    if (!impl_) {
        return Result<EncodedImage>::failure(
            Error{ErrorCode::render_failed, "Cannot use a moved-from Engine"});
    }
    return impl_->render(request);
}

}  // namespace mascotrender
